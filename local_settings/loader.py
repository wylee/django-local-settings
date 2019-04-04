from collections import Mapping, MutableMapping, MutableSequence, Sequence

from django.utils.module_loading import import_string

from six import string_types

from .base import Base
from .checker import Checker
from .settings import DottedAccessDict, Settings
from .strategy import RawValue
from .types import LocalSetting


class Loader(Base):

    def __init__(self, file_name, section=None, registry=None, strategy_type=None):
        super(Loader, self).__init__(file_name, section, registry, strategy_type)

    def load_and_check(self, base_settings, prompt=None):
        """Load settings and check them.

        Loads the settings from ``base_settings``, then checks them.

        Returns:
            (merged settings, True) on success
            (None, False) on failure

        """
        checker = Checker(self.file_name, self.section, self.registry, self.strategy_type, prompt)
        settings = self.load(base_settings)
        if checker.check(settings):
            return settings, True
        return None, False

    def load(self, base_settings):
        """Merge local settings from file with ``base_settings``.

        Returns a new settings dict containing the base settings and the
        loaded settings. Includes:

            - base settings
            - settings from extended file(s), if any
            - settings from file

        """
        is_valid_key = lambda k: k.isupper() and not k.startswith('_')

        # Base settings, including `LocalSetting`s, loaded from the
        # Django settings module.
        valid_keys = (k for k in base_settings if is_valid_key(k))
        base_settings = DottedAccessDict((k, base_settings[k]) for k in valid_keys)

        # Settings read from the settings file; values are unprocessed.
        settings_from_file = self.strategy.read_file(self.file_name, self.section)

        # The fully resolved settings.
        settings = Settings(base_settings)

        for name, value in settings_from_file.items():
            for prefix in ('PREPEND.', 'APPEND.', 'SWAP.'):
                if name.startswith(prefix):
                    name = name[len(prefix):]
                    name = '{prefix}({name})'.format(**locals())
                    break

            settings.set_dotted(name, value)

            # See if this setting corresponds to a `LocalSetting`. If
            # so, note that the `LocalSetting` has a value by putting it
            # in the registry. This also makes it easy to retrieve the
            # `LocalSetting` later so its value can be set.
            current_value = base_settings.get_dotted(name, None)
            if isinstance(current_value, LocalSetting):
                self.registry[current_value] = name

        self._interpolate_values(settings, settings)
        self._interpolate_keys(settings, settings)
        self._prepend_extras(settings, settings.pop('PREPEND', None))
        self._append_extras(settings, settings.pop('APPEND', None))
        self._swap_list_items(settings, settings.pop('SWAP', None))
        self._import_from_string(settings, settings.pop('IMPORT_FROM_STRING', None))
        self._delete_settings(settings, settings.pop('DELETE', None))

        for local_setting, name in self.registry.items():
            local_setting.value = settings.get_dotted(name)

        return settings

    # Post-processing

    def _interpolate_values(self, obj, settings):
        def inject(value):
            new_value, changed = self._inject(value, settings)
            if changed:
                if isinstance(value, RawValue):
                    new_value = RawValue(new_value)
                interpolated.append((value, new_value))
            return new_value

        while True:
            interpolated = []
            obj = self._traverse_object(obj, action=inject)
            if not interpolated:
                break

        def decode(value):
            if isinstance(value, RawValue):
                value = self.strategy.decode_value(value)
            return value

        return self._traverse_object(obj, action=decode)

    def _traverse_object(self, obj, action):
        if isinstance(obj, string_types):
            obj = action(obj)
        elif isinstance(obj, MutableMapping):
            for k, v in obj.items():
                v = self._traverse_object(v, action)
                obj[k] = v
        elif isinstance(obj, Mapping):
            items = []
            for k, v in obj.items():
                v = self._traverse_object(v, action)
                items.append((k, v))
            obj = obj.__class__(items)
        elif isinstance(obj, MutableSequence):
            for i, v in enumerate(obj):
                v = self._traverse_object(v, action)
                obj[i] = v
        elif isinstance(obj, Sequence):
            items = []
            for v in obj:
                v = self._traverse_object(v, action)
                items.append(v)
            obj = obj.__class__(items)
        return obj

    def _interpolate_keys(self, obj, settings):
        if isinstance(obj, Mapping):
            replacements = {}
            for k, v in obj.items():
                if isinstance(k, string_types):
                    new_k, changed = self._inject(k, settings)
                    if changed:
                        replacements[k] = new_k
                self._interpolate_keys(v, settings)
            for k, new_k in replacements.items():
                obj[new_k] = obj[k]
                del obj[k]
        elif isinstance(obj, Sequence) and not isinstance(obj, string_types):
            for item in obj:
                self._interpolate_keys(item, settings)

    def _prepend_extras(self, settings, extras):
        if not extras:
            return
        for name, extra_val in extras.items():
            if not extra_val:
                continue
            current_val = settings.get_dotted(name)
            if not isinstance(current_val, Sequence):
                raise TypeError('PREPEND only works with list-type settings')
            settings.set_dotted(name, extra_val + current_val)

    def _append_extras(self, settings, extras):
        if not extras:
            return
        for name, extra_val in extras.items():
            if not extra_val:
                continue
            current_val = settings.get_dotted(name)
            if not isinstance(current_val, Sequence):
                raise TypeError('APPEND only works with list-type settings')
            settings.set_dotted(name, current_val + extra_val)

    def _swap_list_items(self, settings, swap):
        if not swap:
            return
        for name, swap_map in swap.items():
            if not swap_map:
                continue
            current_val = settings.get_dotted(name)
            if not isinstance(current_val, Sequence):
                raise TypeError('SWAP only works with list-type settings')
            for old_item, new_item in swap_map.items():
                k = current_val.index(old_item)
                current_val[k] = new_item

    def _import_from_string(self, settings, import_from_string):
        if not import_from_string:
            return
        for name in import_from_string:
            current_val = settings.get_dotted(name)
            if isinstance(current_val, string_types):
                settings.set_dotted(name, import_string(current_val))

    def _delete_settings(self, settings, names):
        if names:
            for name in names:
                settings.pop_dotted(name)

    def _inject(self, value, settings):
        """Inject ``settings`` into ``value``.

        Go through ``value`` looking for ``{{ NAME }}`` groups and
        replace each group with the value of the named item from
        ``settings``.

        Args:
            value (str): The value to inject settings into
            settings: An object that provides the dotted access interface

        Returns:
            (str, bool): The new value and whether the new value is
                different from the original value

        """
        assert isinstance(value, string_types), 'Expected str; got {0.__class__}'.format(value)

        if '{{' not in value:
            return value, False

        i = 0
        stack = []
        new_value = value

        while True:
            try:
                c = new_value[i]
            except IndexError:
                break

            try:
                d = new_value[i + 1]
            except IndexError:
                d = ' '

            if c == '{' and d == '{':
                stack.append(i)
                i += 2
            elif c == '}' and d == '}':
                # g:h => {{ name }}
                g = stack.pop()
                h = i + 2

                # m:n => name
                m = g + 2
                n = i

                name = new_value[m:n]
                name = name.strip()

                try:
                    v = settings.get_dotted(name)
                except KeyError:
                    raise KeyError('{name} not found in {settings}'.format(**locals()))

                if not isinstance(v, string_types):
                    v = self.strategy.encode_value(v)

                before = new_value[:g]
                after = new_value[h:]
                new_value = ''.join((before, v, after))

                i = len(before) + len(v)
            else:
                i += 1

        if stack:
            raise ValueError('Unclosed {{ ... }} in %s' % value)

        return new_value, new_value != value
