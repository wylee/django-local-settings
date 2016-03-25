import os
import re
from collections import Mapping, MutableSequence, Sequence
from itertools import takewhile

from django.utils.module_loading import import_string

from six import string_types

from .base import Base
from .exc import SettingsFileNotFoundError
from .types import LocalSetting
from .util import NO_DEFAULT, NO_DEFAULT as PLACEHOLDER


class Loader(Base):

    def __init__(self, file_name=None, section=None, extender=None):
        super(Loader, self).__init__(file_name, section, extender)
        if not os.path.exists(self.file_name):
            raise SettingsFileNotFoundError(file_name)
        # Registry of local settings with a value in the settings file
        self.registry = {}

    def read_file(self):
        """Read settings from specified ``section`` of config file."""
        parser = self._make_parser()
        with open(self.file_name) as fp:
            parser.read_file(fp)
        extends = parser[self.section].get('extends')
        settings = {}
        if extends:
            extends = self._parse_setting(extends)
            settings.update(self.__class__(extends, extender=self).read_file())
        settings_from_file = parser[self.section]
        settings.update(settings_from_file)
        return settings

    def load(self, base_settings: Mapping) -> dict:
        """Merge local settings from file with ``base_settings``.

        Returns a new dict containing the base settings and the loaded
        settings. Includes:

            - base settings
            - settings from extended file(s), if any
            - settings from file

        """
        settings = {k: v for (k, v) in base_settings.items() if k.isupper()}

        for name, value in self.read_file().items():
            value = self._parse_setting(value)

            def visit(obj, segment, item, next_segment, args):
                if next_segment is None:  # Reached setting
                    obj[segment] = value
                    # If there's already a LocalSetting in this slot, set the
                    # value of that LocalSetting and put it in the registry so
                    # it can be easily retrieved later.
                    if isinstance(item, LocalSetting):
                        item.value = value
                        self.registry[item] = segment

            self._traverse(settings, name, visit=visit, create_missing=True, default=None)

        settings.pop('extends', None)
        self._interpolate(settings)
        self._append_extras(settings)
        self._swap_list_items(settings)
        self._import_from_string(settings)
        return settings

    # Traversal

    def _traverse(self, obj, name, visit=None, args=None, last_only=False, create_missing=False,
                  default=NO_DEFAULT):
        """Traverse to the item specified by ``name``.

        If no ``visit`` function is passed, this will simply retrieve
        the value of the item specified by ``name``. Otherwise...

        For each object along the way, starting with ``obj``, call
        ``visit`` with the following args:

            - Current object
            - Key (next key to retrieve from current object)
            - Value (value of next key)
            - Next key
            - ``args``

        As an example, imagine ``obj`` is the following settings dict::

            {
                'PANTS': {
                    'types': ['jeans', 'slacks'],
                    'total': 10,
                }
            }

        Then calling this method with ``name='PANTS.types.0'`` would
        result in the following calls to ``visit``::

            visit(
                obj,
                'PANTS',
                {'types': ['jeans', 'slacks'], 'total': 10},
                'types',
                args)

            visit(
                {'types': ['jeans', 'slacks'], 'total': 10},
                'types',
                ['jeans', 'slacks'],
                0,
                args)

            visit(
                ['jeans', 'slacks'],
                0,
                'jeans',
                NO_DEFAULT,
                args)

        Generally, the ``visit`` function shouldn't return anything
        other than ``None``; if it does, the returned value will become
        the next object instead of getting the next object from the
        current object. This is esoteric and should probably be ignored.

        In the common case where you just want to process the value of
        the setting specified by ``name``, pass ``last_only=True``.

        To create missing items on the way to the ``name``d item, pass
        ``create_missing=True``. This will insert an item for each
        missing segment in ``name``. The type and value of item that
        will be inserted for a missing segment depends on the *next*
        segment. If a ``default`` value is passed, the ``name``d item
        will be set to this value; otherwise, a default default will
        be used. See :meth:`_get_or_create_segment` for more info.

        """
        segments = self._parse_path(name)
        visit_segments = visit is not None
        visit_all = not last_only
        for segment, next_segment in zip(segments, segments[1:] + [None]):
            last = next_segment is None
            if create_missing:
                segment_default = default if last else NO_DEFAULT
                val = self._get_or_create_segment(obj, segment, next_segment, segment_default)
            else:
                val = obj[segment]
            if visit_segments and (visit_all or last):
                result = visit(obj, segment, val, next_segment, args)
                obj = result if result is not None else val
            else:
                obj = val
        return obj

    def _get_or_create_segment(self, obj, segment, next_segment, default=NO_DEFAULT) -> object:
        """Get ``obj[segment]``; create ``obj[segment]`` if missing.

        The default value for a missing segment is based on the *next*
        segment, unless a ``default`` is explicitly passed.

        If the next segment is an int, the default will be a list with
        the indicated number of items. Otherwise the default will be
        a dict.

        """
        if default is NO_DEFAULT:
            if isinstance(next_segment, int):
                default = [PLACEHOLDER] * (next_segment + 1)
            else:
                default = {}
        if isinstance(obj, Mapping):
            if segment not in obj:
                obj[segment] = default
        elif isinstance(obj, Sequence):
            while segment >= len(obj):
                obj.append(PLACEHOLDER)
            if obj[segment] is PLACEHOLDER:
                obj[segment] = default
        return obj[segment]

    def _parse_path(self, path):
        """Parse ``path`` into segments.

        Paths must start with a WORD (i.e., a top level Django setting
        name). Path segments are separated by dots. Compound path
        segments (i.e., a name with a dot in it) can be grouped inside
        parentheses.

        Examples::

            >>> loader = Loader()
            >>> loader._parse_path('WORD')
            ['WORD']
            >>> loader._parse_path('WORD.x')
            ['WORD', 'x']
            >>> loader._parse_path('WORD.(x)')
            ['WORD', 'x']
            >>> loader._parse_path('WORD.(x.y)')
            ['WORD', 'x.y']
            >>> loader._parse_path('WORD.(x.y).z')
            ['WORD', 'x.y', 'z']

        An example of where compound names are actually useful is in
        logger settings::

            LOGGING.loggers.(package.module).handlers = ["console"]
            LOGGING.loggers.(package.module).level = "DEBUG"

        Any segment that looks like an int will be converted to an int.
        Segments that start with a leading '0' followed by other digits
        will not be converted.

        """
        segments = []
        ipath = iter(path)
        for char in ipath:
            segment, end = ([], ')') if char == '(' else ([char], '.')
            # Note: takewhile() consumes the end character
            segment.extend(takewhile(lambda c: c != end, ipath))
            segment = ''.join(segment)
            segment = self._convert_name(segment)
            segments.append(segment)
            if end == ')':
                # Consume dot after right paren
                next(ipath, None)
        return segments

    def _convert_name(self, name):
        """Convert ``name`` to int if it looks like an int.

        Otherwise, return it as is.

        """
        if re.search('^\d+$', name):
            if len(name) > 1 and name[0] == '0':
                # Don't treat strings beginning with "0" as ints
                return name
            return int(name)
        return name

    # Post-processing

    def _interpolate(self, settings):
        interpolated = True
        while interpolated:
            interpolated = []
            self._interpolate_values(settings, settings, interpolated)
        self._interpolate_keys(settings, settings)

    def _interpolate_values(self, obj, settings, interpolated):
        if isinstance(obj, string_types):
            try:
                new_value = obj.format(**settings)
            except KeyError:
                new_value = obj
            if new_value != obj:
                obj = new_value
                interpolated.append((obj, new_value))
        elif isinstance(obj, Mapping):
            for k, v in obj.items():
                obj[k] = self._interpolate_values(v, settings, interpolated)
        elif isinstance(obj, MutableSequence):
            for i, item in enumerate(obj):
                obj[i] = self._interpolate_values(item, settings, interpolated)
        elif isinstance(obj, Sequence):
            obj = obj.__class__(
                self._interpolate_values(item, settings, interpolated) for item in obj)
        return obj

    def _interpolate_keys(self, obj, settings):
        if isinstance(obj, Mapping):
            replacements = {}
            for k, v in obj.items():
                if isinstance(k, str):
                    new_k = k.format(**settings)
                    if k != new_k:
                        replacements[k] = new_k
                self._interpolate_keys(v, settings)
            for k, new_k in replacements.items():
                obj[new_k] = obj[k]
                del obj[k]
        elif isinstance(obj, Sequence) and not isinstance(obj, string_types):
            for item in obj:
                self._interpolate_keys(item, settings)

    def _append_extras(self, settings):
        extras = settings.get('EXTRA')
        if not extras:
            return

        def visit(obj, key, val, next_key, args):
            if not isinstance(val, Sequence):
                raise TypeError('EXTRA only works with list-type settings')
            extra_val = args['extra_val']
            if extra_val:
                obj[key] = val + extra_val

        for name, extra_val in extras.items():
            visit_args = {'extra_val': extra_val}
            self._traverse(settings, name, visit, args=visit_args, last_only=True)

    def _swap_list_items(self, settings):
        swap = settings.get('SWAP')
        if not swap:
            return

        def visit(obj, key, val, next_key, args):
            if not isinstance(val, Sequence):
                raise TypeError('SWAP only works with list-type settings')
            swap_map = args['swap_map']
            if swap_map:
                for old_item, new_item in swap_map.items():
                    k = val.index(old_item)
                    val[k] = new_item

        for name, swap_map in swap.items():
            args = {'swap_map': swap_map}
            self._traverse(settings, name, visit, args=args, last_only=True)

    def _import_from_string(self, settings):
        import_ = settings.get('IMPORT_FROM_STRING')
        if not import_:
            return

        def visit(obj, key, val, next_key, args):
            if isinstance(val, string_types):
                obj[key] = import_string(val)

        for name in import_:
            self._traverse(settings, name, visit, last_only=True)
