from collections import Mapping, MutableSequence, Sequence

from django.utils.module_loading import import_string

from six import string_types

from .base import Base
from .checker import Checker
from .settings import Settings
from .types import LocalSetting

from .strategy import INIJSONStrategy


class Loader(Base):

    def __init__(self, file_name, section=None, registry=None, strategy_type=INIJSONStrategy):
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
        base_settings = {k: v for (k, v) in base_settings.items() if is_valid_key(k)}
        settings = Settings(base_settings)

        for name, value in self.strategy.read_file(self.file_name, self.section).items():
            value = self.strategy.decode_value(value)

            for prefix in ('PREPEND.', 'APPEND.', 'SWAP.'):
                if name.startswith(prefix):
                    name = name[len(prefix):]
                    name = '{prefix}({name})'.format(**locals())

            # If there's already a LocalSetting in this slot, set the
            # value of that LocalSetting and put it in the registry so
            # it can be easily retrieved later.
            current_value = settings.get_dotted(name, None)
            if isinstance(current_value, LocalSetting):
                current_value.value = value
                self.registry[current_value] = name

            settings.set_dotted(name, value)

        settings.pop('extends', None)
        self._interpolate(settings)
        self._prepend_extras(settings, settings.pop('PREPEND', None))
        self._append_extras(settings, settings.pop('APPEND', None))
        self._swap_list_items(settings, settings.pop('SWAP', None))
        self._import_from_string(settings, settings.pop('IMPORT_FROM_STRING', None))

        return settings

    # Post-processing

    def _interpolate(self, settings):
        interpolated = True
        while interpolated:
            interpolated = []
            self._interpolate_values(settings, settings, interpolated)
        self._interpolate_keys(settings, settings)

    def _inject(self, settings, value):
        """Inject ``obj`` into ``value``.

        Go through value looking for ``{{SETTING_NAME}}`` groups and
        replace each group with the str value of the named setting.

        Args:
            settings (object): An object, usually a dict
            value (str): The value to inject obj into

        Returns:
            (str, bool): The new value and whether the new value is
                different from the original value

        """
        assert isinstance(value, string_types), 'Expected str; got {0.__class__}'.format(value)

        begin, end = '{{', '}}'

        if begin not in value:
            return value, False

        new_value = value
        begin_pos, end_pos = 0, None
        len_begin, len_end = len(begin), len(end)
        len_value = len(new_value)

        while begin_pos < len_value:
            # Find next {{.
            begin_pos = new_value.find(begin, begin_pos)

            if begin_pos == -1:
                break

            # Save everything before {{.
            before = new_value[:begin_pos]

            # Find }} after {{.
            begin_pos += len_begin
            end_pos = new_value.find(end, begin_pos)
            if end_pos == -1:
                raise ValueError('Unmatched {begin}...{end} in {value}'.format(**locals()))

            # Get name between {{ and }}, ignoring leading and trailing
            # whitespace.
            name = new_value[begin_pos:end_pos]
            name = name.strip()

            if not name:
                raise ValueError('Empty name in {value}'.format(**locals()))

            # Save everything after }}.
            after_pos = end_pos + len_end
            try:
                after = new_value[after_pos:]
            except IndexError:
                # Reached end of value.
                after = ''

            # Retrieve string value for named setting (the "injection
            # value").
            try:
                injection_value = str(settings.get_dotted(name))
            except KeyError:
                raise ValueError('{name} not found in {obj}'.format(**locals()))

            # Combine before, inject value, and after to get the new
            # value.
            new_value = ''.join((before, injection_value, after))

            # Continue after injected value.
            begin_pos = len(before) + len(injection_value)
            len_value = len(new_value)

        return new_value, (new_value != value)

    def _interpolate_values(self, obj, settings, interpolated):
        if isinstance(obj, Mapping):
            for k, v in obj.items():
                obj[k] = self._interpolate_values(v, settings, interpolated)
        elif isinstance(obj, MutableSequence):
            for i, item in enumerate(obj):
                obj[i] = self._interpolate_values(item, settings, interpolated)
        elif isinstance(obj, Sequence) and not isinstance(obj, string_types):
            obj = obj.__class__(
                self._interpolate_values(item, settings, interpolated) for item in obj)
        elif isinstance(obj, string_types):
            new_value, changed = self._inject(settings, obj)
            if changed:
                obj = new_value
                interpolated.append((obj, new_value))
        return obj

    def _interpolate_keys(self, obj, settings):
        if isinstance(obj, Mapping):
            replacements = {}
            for k, v in obj.items():
                if isinstance(k, string_types):
                    new_k, changed = self._inject(settings, k)
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
