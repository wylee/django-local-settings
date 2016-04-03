import re
from collections import Mapping, Sequence

from .util import NO_DEFAULT, NO_DEFAULT as PLACEHOLDER


class Settings(dict):

    """Dict-ish container for settings.

    Provides access to settings via regular item access, attribute
    access, and dotted names::

        >>> settings = Settings()
        >>> settings['name'] = 'name'
        >>> settings['name']
        'name'
        >>> settings.name = 'name'
        >>> settings.name
        'name'
        >>> settings['NAMESPACE.name'] = 'nested name'
        >>> settings['NAMESPACE.name']
        'nested name'

    These are all equivalent::

        >>> settings['NAMESPACE']['name']
        'nested name'
        >>> settings.NAMESPACE.name
        'nested name'
        >>> settings['NAMESPACE.name']
        'nested name'

    Adding an item with a dotted name will create nested settings like
    so::

        >>> settings = Settings()
        >>> settings['NAMESPACE.name'] = 'nested name'
        >>> settings
        {'NAMESPACE': {'name': 'nested name'}}

    To add an item with a dotted name without nesting, a special syntax
    can be used::

        >>> settings = Settings()
        >>> settings['(not.nested)'] = 'not nested'
        >>> settings
        {'not.nested': 'not nested'}
        >>> settings['(not.nested)']
        'not nested'

    Implementation Notes
    ====================

    This is a subclass of dict because certain settings consumers, such
    as ``logging.dictConfig`` from the standard library, won't work with
    a non-dict mapping type because they do things like
    ``isinstance(something, dict)``.

    Where a setting has a name that's the same as an attribute name
    (e.g., ``get`` or ``update``), the attribute will take precedence.
    To get at such a setting, item access must be used. This is
    necessary because we can't allow settings to override the dict
    interface (because this might cause problems with outside consumers
    of the settings that aren't aware of the magic we're doing here).

    Setting names may not start with an underscore. In general, all
    non-setting attributes should begin with an underscore. This keeps
    clashes between settings and non-setting attributes to a minimum.

    """

    def _traverse(self, name, create_missing=False, action=None, value=NO_DEFAULT):
        """Traverse to the item specified by ``name``.

        To create missing items on the way to the ``name``d item, pass
        ``create_missing=True``. This will insert an item for each
        missing segment in ``name``. The type and value of item that
        will be inserted for a missing segment depends on the *next*
        segment. If a ``default`` value is passed, the ``name``d item
        will be set to this value; otherwise, a default default will
        be used. See :meth:`_create_segment` for more info.

        """
        obj = self
        segments = self._parse_path(name)

        for segment, next_segment in zip(segments, segments[1:] + [None]):
            last = next_segment is None

            if create_missing:
                self._create_segment(obj, segment, next_segment)

            try:
                if isinstance(obj, Settings):
                    next_obj = super(Settings, obj).__getitem__(segment)
                else:
                    next_obj = obj[segment]
            except IndexError:
                raise KeyError(segment)

            if not last:
                obj = next_obj
            else:
                if action:
                    value = action(obj, segment)
                elif value is not NO_DEFAULT:
                    if isinstance(obj, Settings):
                        # Avoid recursive traversal
                        super(Settings, obj).__setitem__(segment, value)
                    else:
                        obj[segment] = value
                else:
                    if isinstance(obj, Settings):
                        value = super(Settings, obj).__getitem__(segment)
                    else:
                        value = obj[segment]

        return value

    def _create_segment(self, obj, segment, next_segment):
        """Create ``obj[segment]`` if missing.

        The default value for a missing segment is based on the *next*
        segment, unless a ``default`` is explicitly passed.

        If the next segment is an int, the default will be a list with
        the indicated number of items. Otherwise the default will be
        a :class:`Settings` dict.

        """
        if isinstance(next_segment, int):
            value = [PLACEHOLDER] * (next_segment + 1)
        else:
            value = Settings()
        if isinstance(obj, Settings):
            if segment not in obj:
                super(Settings, obj).__setitem__(segment, value)
        elif isinstance(obj, Mapping):
            if segment not in obj:
                obj[segment] = value
        elif isinstance(obj, Sequence):
            while segment >= len(obj):
                obj.append(PLACEHOLDER)
            if obj[segment] is PLACEHOLDER:
                obj[segment] = value

    def _parse_path(self, path):
        """Parse ``path`` into segments.

        Paths must start with a WORD (i.e., a top level Django setting
        name). Path segments are separated by dots. Compound path
        segments (i.e., a name with a dot in it) can be grouped inside
        parentheses.

        Examples::

            >>> settings = Settings()
            >>> settings._parse_path('WORD')
            ['WORD']
            >>> settings._parse_path('WORD.x')
            ['WORD', 'x']
            >>> settings._parse_path('WORD.(x)')
            ['WORD', 'x']
            >>> settings._parse_path('WORD.(x.y)')
            ['WORD', 'x.y']
            >>> settings._parse_path('WORD.(x.y).z')
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
        convert_name = self._convert_name
        group_chars = {
            '(': ')',
            '{': '}',
        }

        for char in ipath:
            is_grouped = char in group_chars
            
            if is_grouped:
                segment, end = [], group_chars[char]
            else:
                segment, end = [char], '.'

            nested = 0
            for c in ipath:
                if c == end:
                    if nested:
                        nested -= 1
                    else:
                        break
                elif is_grouped and c == char:
                    nested += 1
                segment.append(c)
            else:
                if is_grouped:
                    raise ValueError('Matching end char not found for %s' % char)

            segment = ''.join(segment)

            if char == '{':
                segment = '{%s}' % segment

            if not is_grouped:
                segment = convert_name(segment)

            segments.append(segment)

            if is_grouped:
                # Consume dot after end group char
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

    def __contains__(self, name):
        try:
            self._traverse(name)
        except KeyError:
            return False
        return True

    def __delitem__(self, name):
        action = lambda obj, segment: super(Settings, self).__delitem__(segment)
        self._traverse(name, action=action)

    def __getitem__(self, name):
        return self._traverse(name)

    def __setitem__(self, name, value):
        if name.startswith('_'):
            raise KeyError('Settings keys may not start with an underscore')
        self._traverse(name, create_missing=True, value=value)

    def __getattribute__(self, name):
        try:
            return dict.__getattribute__(self, name)
        except AttributeError:
            try:
                return self[name]
            except KeyError:
                raise AttributeError(name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            dict.__setattr__(self, name, value)
        else:
            self[name] = value

    def __iter__(self):
        iterator = super(Settings, self).__iter__()
        for k in iterator:
            if '.' in k:
                is_bracketed_group = k[0] == '{' and k[-1] == '}'
                if not is_bracketed_group:
                    k = '(%s)' % k if '.' in k else k
            yield k

    # The following are required because these methods on the built-in
    # dict type will *not* call our __getitem__, __setitem__, __iter__,
    # etc methods above. These implementations and the views below were
    # copied from abc.MutableMapping in the standard library and tweaked
    # slightly.

    def get(self, name, default=None):
        try:
            return self[name]
        except KeyError:
            return default

    def keys(self):
        return KeysView(self)

    def items(self):
        return ItemsView(self)

    def values(self):
        return ValuesView(self)

    def pop(self, name, default=NO_DEFAULT):
        try:
            value = self[name]
        except KeyError:
            if default is NO_DEFAULT:
                raise
            return default
        else:
            del self[name]
            return value

    def setdefault(self, name, default=None):
        try:
            return self[name]
        except KeyError:
            self[name] = default
        return default

    def update(*args, **kwargs):
        if len(args) > 2:
            raise TypeError(
                'update() takes at most 2 positional arguments ({} given)'.format(len(args)))
        elif not args:
            raise TypeError('update() takes at least 1 argument (0 given)')
        self = args[0]
        other = args[1] if len(args) >= 2 else ()
        if isinstance(other, Mapping):
            for name in other:
                self[name] = other[name]
        elif hasattr(other, 'keys'):
            for name in other.keys():
                self[name] = other[name]
        else:
            for name, value in other:
                self[name] = value
        for name, value in kwargs.items():
            self[name] = value


class SettingsView:

    def __init__(self, settings):
        self._settings = settings

    def __len__(self):
        return len(self._settings)


class KeysView(SettingsView):

    def __contains__(self, name):
        return name in self._settings

    def __iter__(self):
        for k in self._settings:
            yield k


class ItemsView(SettingsView):

    def __contains__(self, item):
        name, value = item
        try:
            v = self._settings[name]
        except KeyError:
            return False
        return v == value

    def __iter__(self):
        for k in self._settings:
            yield (k, self._settings[k])


class ValuesView(SettingsView):

    def __contains__(self, value):
        for k in self._settings:
            if self._settings[k] == value:
                return True
        return False

    def __iter__(self):
        for key in self._settings:
            yield self._settings[key]
