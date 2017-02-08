from collections import Mapping, MutableSequence, OrderedDict, Sequence

from django.utils.module_loading import import_string

from six import string_types

from .base import Base
from .checker import Checker
from .settings import DottedAccessDict, Settings
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

        # Base settings, including `LocalSetting`s, loaded from the
        # Django settings module.
        valid_keys = (k for k in base_settings if is_valid_key(k))
        base_settings = DottedAccessDict((k, base_settings[k]) for k in valid_keys)

        # Settings read from the settings file; values are unprocessed.
        settings_from_file = self.strategy.read_file(self.file_name, self.section)
        settings_from_file.pop('extends', None)

        # Settings read from file are copied here. We do this because
        # some of the setting names may need to be adjusted and we need
        # to keep them in their original order.
        raw_settings = OrderedDict()

        # The fully resolved settings.
        settings = Settings(base_settings)

        for name, value in settings_from_file.items():
            for prefix in ('PREPEND.', 'APPEND.', 'SWAP.'):
                if name.startswith(prefix):
                    name = name[len(prefix):]
                    name = '{prefix}({name})'.format(**locals())
                    break

            # See if this setting corresponds to a `LocalSetting`. If
            # so, note that the `LocalSetting` has a value by putting it
            # in the registry. This also makes it easy to retrieve the
            # `LocalSetting` later so its value can be set.
            current_value = base_settings.get_dotted(name, None)
            if isinstance(current_value, LocalSetting):
                self.registry[current_value] = name

            raw_settings[name] = value

        self._resolve_values(base_settings, raw_settings, settings)
        self._interpolate_keys(settings, settings)
        self._prepend_extras(settings, settings.pop('PREPEND', None))
        self._append_extras(settings, settings.pop('APPEND', None))
        self._swap_list_items(settings, settings.pop('SWAP', None))
        self._import_from_string(settings, settings.pop('IMPORT_FROM_STRING', None))

        return settings

    # Post-processing

    def _resolve_values(self, base_settings, raw_settings, settings):
        # - Decode raw values according to strategy
        # - Resolve local settings values
        # - Interpolate all settings values

        for name in raw_settings:
            value = raw_settings[name]
            value = self.strategy.decode_value(value)
            settings.set_dotted(name, value)

        for local_setting, name in self.registry.items():
            local_setting.value = settings.get_dotted(name)

        interpolated = []
        while interpolated is not None:
            _, interpolated = self._interpolate_values(settings, settings)

    def _interpolate_values(self, obj, settings, _interpolated=None):
        if _interpolated is None:
            _interpolated = []
        if isinstance(obj, Mapping):
            for k, v in obj.items():
                obj[k], _interpolated = self._interpolate_values(v, settings, _interpolated)
        elif isinstance(obj, MutableSequence):
            for i, item in enumerate(obj):
                obj[i], _interpolated = self._interpolate_values(item, settings, _interpolated)
        elif isinstance(obj, Sequence) and not isinstance(obj, string_types):
            obj, _interpolated = obj.__class__(
                self._interpolate_values(item, settings, _interpolated) for item in obj)
        elif isinstance(obj, string_types):
            new_value, changed = self._inject(settings, obj)
            if changed:
                obj = new_value
                _interpolated.append((obj, new_value))
        return obj, _interpolated or None

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

    def _inject(self, settings, value):
        """Inject ``obj`` into ``value``.

        Go through value looking for ``{{SETTING_NAME}}`` groups and
        replace each group with the str value of the named setting.

        Args:
            settings: A settings object that provides the dotted access
                interface
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
