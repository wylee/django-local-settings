import re
from collections import Mapping, Sequence

from .util import NO_DEFAULT, NO_DEFAULT as PLACEHOLDER


class DottedAccessMixin:

    """Provides dotted access to nested items in dict-like containers.

    Mix with any type that supports item access to allow dotted access
    to nested items.

    >>> class MyMapping(dict, DottedAccessMixin):
    ...
    ...     pass
    >>>
    >>> my_map = MyMapping({'a': {'b': {'c': '123', '3': ['x', 'y', 'z']}}})

    Check whether an item is in the container, then get it:

    >>> my_map.contains_dotted('a.b.c')
    True
    >>> my_map.get_dotted('a.b.c')
    '123'

    Get an item from a sequence (the 3 is wrapped in parentheses to keep
    it from being interpreted as a sequence index):

    >>> my_map.contains_dotted('a.b.(3).0')
    True
    >>> my_map.get_dotted('a.b.(3).0')
    'x'

    Try getting an item that doesn't exist (without a default, this
    would raise a KeyError):

    >>> my_map.get_dotted('a.b.see', default=None)

    Add the missing item and then get it:

    >>> my_map.contains_dotted('a.b.see')
    False
    >>> my_map.set_dotted('a.b.see', 1)
    >>> my_map.contains_dotted('a.b.see')
    True
    >>> my_map.get_dotted('a.b.see')
    1

    """

    def contains_dotted(self, name):
        try:
            self._traverse(name)
        except KeyError:
            return False
        return True

    def get_dotted(self, name, default=NO_DEFAULT, action=None):
        try:
            return self._traverse(name, action=action)
        except KeyError:
            if default is NO_DEFAULT:
                raise
            return default

    def set_dotted(self, name, value, create_missing=True):
        self._traverse(name, create_missing=create_missing, value=value)

    def pop_dotted(self, name, default=NO_DEFAULT):
        action = lambda obj, segment: obj.pop(segment)
        return self.get_dotted(name, default=default, action=action)

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

            next_obj = obj[segment]

            if not last:
                obj = next_obj
            else:
                if action:
                    value = action(obj, segment)
                elif value is not NO_DEFAULT:
                    obj[segment] = value
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
        if isinstance(obj, Mapping):
            if segment not in obj:
                obj[segment] = value
        elif isinstance(obj, Sequence):
            old_len = len(obj)
            new_len = segment + 1
            if new_len > old_len:
                obj.extend([PLACEHOLDER] * (new_len - old_len))
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
            >>> settings._parse_path('WORD.0.z')
            ['WORD', 0, 'z']
            >>> settings._parse_path('WORD.(0).z')
            ['WORD', '0', 'z']
            >>> settings._parse_path('WORD.(0)X.z')
            ['WORD', '0X', 'z']

        An example of where compound names are actually useful is in
        logger settings::

            LOGGING.loggers.(package.module).handlers = ["console"]
            LOGGING.loggers.(package.module).level = "DEBUG"

        Paths may also contain interpolation groups. Dotted names in
        these groups will not be split (so there's no need to group them
        inside parentheses)::

            >>> settings = Settings()
            >>> settings._parse_path('WORD.{{ x }}')
            ['WORD', '{{ x }}']
            >>> settings._parse_path('WORD.{{ x.y }}')
            ['WORD', '{{ x.y }}']
            >>> settings._parse_path('WORD.{{ x.y.z }}XYZ')
            ['WORD', '{{ x.y.z }}XYZ']

        Interpolation groups *can* be wrapped in parentheses, but doing
        so is redundant::

            >>> settings._parse_path('WORD.({{ x.y.z }}XYZ)')
            ['WORD', '{{ x.y.z }}XYZ']

        Any segment that A) looks like an int and B) is *not* within
        a (...) or {{ ... }} group will be converted to an int. Segments
        that start with a leading "0" followed by other digits will not
        be converted.

        """
        if not path:
            raise ValueError('path cannot be empty')

        i = 0
        length = len(path)
        stack = []
        collector = []
        segments = []
        group = False
        convert_name = self._convert_name

        def append_segment():
            segment = ''.join(collector)
            if not group:
                segment = convert_name(segment)
            segments.append(segment)
            del collector[:]

        while i < length:
            c = path[i]

            try:
                d = path[i + 1]
            except IndexError:
                d = ' '

            if c == '.' and not stack:
                append_segment()
                group = False
            elif c == '(':
                # Consume everything inside outer parentheses, including
                # inner parentheses. We'll know we've reached the right
                # outer paren when the stack is back to its height before
                # entering the group.
                stack_len = len(stack)
                stack.append(c)
                i += 1  # Skip outer left paren
                while i < length:
                    e = path[i]
                    if e == '(':
                        stack.append(e)
                    elif e == ')':
                        item = stack.pop()
                        if item != '(':
                            raise ValueError('Unclosed (...) in %s' % path)
                        if len(stack) == stack_len:
                            group = True
                            break
                    # Add char here so outer right paren isn't collected.
                    collector.append(e)
                    i += 1
            elif c == '{' and d == '{':
                stack.append('{{')
                collector.append('{{')
                i += 1
            elif c == '}' and d == '}':
                item = stack.pop()
                if item != '{{':
                    raise ValueError('Unclosed {{ ... }} in %s' % path)
                collector.append('}}')
                group = True
                i += 1
            else:
                collector.append(c)

            i += 1

        if stack:
            bracket = stack[-1]
            close_bracket = ')' if bracket == '(' else '}}'
            raise ValueError('Unclosed %s...%s in %s' % (bracket, close_bracket, path))

        if collector:
            append_segment()

        return segments

    def _convert_name(self, name):
        """Convert ``name`` to int if it looks like an int.

        Otherwise, return it as is.

        """
        if re.search(r'^\d+$', name):
            if len(name) > 1 and name[0] == '0':
                # Don't treat strings beginning with "0" as ints
                return name
            return int(name)
        return name


class DottedAccessDict(dict, DottedAccessMixin):

    """Default implementation of a dict providing dotted item access.

    Typically used to wrap an existing dict to get dotted item access:

    >>> d = {'a': {'b': 'c'}}
    >>> d = DottedAccessDict(d)
    >>> d.get_dotted('a.b')
    'c'

    """


class Settings(dict, DottedAccessMixin):

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
        >>> settings.set_dotted('NAMESPACE.name', 'nested name')
        >>> settings.get_dotted('NAMESPACE.name')
        'nested name'

    These are all equivalent::

        >>> settings['NAMESPACE']['name']
        'nested name'
        >>> settings.NAMESPACE.name
        'nested name'
        >>> settings.get_dotted('NAMESPACE.name')
        'nested name'

    Adding an item with a dotted name will create nested settings like
    so::

        >>> settings = Settings()
        >>> settings.set_dotted('NAMESPACE.name', 'nested name')
        >>> settings
        {'NAMESPACE': {'name': 'nested name'}}

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

    """

    def __init__(self, *args, **kwargs):
        # Call our update() instead of super().__init__() so that our
        # __setitem__() will be used.
        self.update(*args, **kwargs)

    def __setitem__(self, name, value):
        if isinstance(value, Mapping):
            value = Settings(value)
        super(Settings, self).__setitem__(name, value)

    # Implementation of attribute access.

    def __getattr__(self, name):
        # This is only invoked if the named attribute isn't found as an
        # instance or class attribute of the Settings instance. In other
        # words, this will only be called for settings stored in the
        # instance's internal dict storage. For methods such as `get`,
        # this won't be called.
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value

    # Support for copying and pickling.

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__.update(state)

    # The following are required because these methods on the built-in
    # dict type will *not* call our __setitem__ method above. These
    # implementations were copied from collections.MutableMapping in the
    # standard library and tweaked slightly.

    def setdefault(self, name, default=None):
        try:
            return self[name]
        except KeyError:
            self[name] = default
        return self[name]

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
