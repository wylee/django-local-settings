import os
import re
from collections import Mapping, OrderedDict, Sequence

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
        settings = OrderedDict()
        if extends:
            extends = self._parse_setting(extends)
            if isinstance(extends, str):
                extends = [extends]
            for e in reversed(extends):
                settings.update(self.__class__(e, extender=self).read_file())
        settings_from_file = parser[self.section]
        remove = [k for k in settings if k in settings_from_file]
        for k in remove:
            del settings[k]
        settings.update(settings_from_file)
        return settings

    def load(self, base_settings):
        """Merge local settings from file with ``base_settings``.

        Returns a new OrderedDict containing the base settings and the
        loaded settings. Ordering is:

            - base settings
            - settings from extended file(s), if any
            - settings from file

        When a setting is overridden, it gets moved to the end.

        TODO: Rewrite this using :meth:`_traverse`.

        """
        if not os.path.exists(self.file_name):
            self.print_warning(
                'Local settings file `{0}` not found'.format(self.file_name))
            return
        is_upper = lambda k: k == k.upper()
        settings = OrderedDict((k, v) for (k, v) in base_settings.items() if is_upper(k))
        for k, v in self.read_file().items():
            names = k.split('.')
            v = self._parse_setting(v)
            obj = settings
            for name, next_name in zip(names[:-1], names[1:]):
                next_name = self._convert_name(next_name)
                next_is_seq = isinstance(next_name, int)
                default = [PLACEHOLDER] * (next_name + 1) if next_is_seq else {}
                if isinstance(obj, Mapping):
                    if name not in obj:
                        obj[name] = default
                elif isinstance(obj, Sequence):
                    name = int(name)
                    while name >= len(obj):
                        obj.append(PLACEHOLDER)
                    if obj[name] is PLACEHOLDER:
                        obj[name] = default
                obj = obj[name]
            name = self._convert_name(names[-1])
            try:
                curr_v = obj[name]
            except (KeyError, IndexError):
                pass
            else:
                if isinstance(curr_v, LocalSetting):
                    curr_v.value = v
                    self.registry[curr_v] = name
            obj[name] = v
            settings.move_to_end(names[0])
        settings.pop('extends', None)
        self._interpolate(settings, settings)
        self._import_from_string(settings)
        return settings

    def _traverse(self, settings, name, visit_func=None, last_only=False, args=NO_DEFAULT):
        """Traverse to the setting indicated by ``name``.

        For each object along the way, starting with ``settings``, call
        ``visit_func`` with the following args:

            - Current object
            - Next key
            - NO_DEFAULT or value of setting (when settings is reached)
            - ``args``

        As an example, imagine ``settings`` is the following dict::

            {
                'PANTS': {
                    'types': ['jeans', 'slacks'],
                    'total': 10,
                }
            }

        Then calling this method with ``name='PANTS.types.0'`` would
        result in the following calls to ``visit_func``::

            visit_func(settings,                  'PANTS', NO_DEFAULT, args)
            visit_func(settings['PANTS'],         'types', NO_DEFAULT, args)
            visit_func(settings['PANTS']['types'], 0,      'jeans', args)

        Calling this method with ``name='PANTS.total'`` would result in
        the following calls to ``visit_func``::

            visit_func(settings,          'PANTS', NO_DEFAULT, args)
            visit_func(settings['PANTS'], 'jeans', 10, args)

        In the common case where you just want to process the value of
        the setting specified by ``name``, pass ``last_only=True``.

        """
        obj = settings
        keys = [self._convert_name(n) for n in name.split('.')]
        for k in keys[:-1]:
            if visit_func is not None and not last_only:
                visit_func(obj, k, NO_DEFAULT, args)
            obj = obj[k]
        last_k = keys[-1]
        val = obj[last_k]
        if visit_func is not None:
            visit_func(obj, last_k, val, args)

    def _interpolate(self, v, settings):
        if isinstance(v, string_types):
            v = v.format(**settings)
        elif isinstance(v, Mapping):
            for k in v:
                v[k] = self._interpolate(v[k], settings)
        elif isinstance(v, Sequence):
            v = v.__class__(self._interpolate(item, settings) for item in v)
        return v

    def _import_from_string(self, settings):
        def visit_func(obj, key, val, args):
            if isinstance(val, string_types):
                obj[key] = import_string(val)
        for name in settings.get('IMPORT_FROM_STRING', ()):
            self._traverse(settings, name, visit_func, last_only=True)

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
