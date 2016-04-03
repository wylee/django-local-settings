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

            for prefix in ('EXTRA.', 'SWAP.'):
                if name.startswith(prefix):
                    name = name[len(prefix):]
                    name = '{prefix}({name})'.format_map(locals())

            # If there's already a LocalSetting in this slot, set the
            # value of that LocalSetting and put it in the registry so
            # it can be easily retrieved later.
            current_value = settings.get(name)
            if isinstance(current_value, LocalSetting):
                current_value.value = value
                self.registry[current_value] = name
            settings[name] = value

        settings.pop('extends', None)
        self._interpolate(settings)
        self._append_extras(settings, settings.pop('EXTRA', None))
        self._swap_list_items(settings, settings.pop('SWAP', None))
        self._import_from_string(settings, settings.pop('IMPORT_FROM_STRING', None))

        if 'LOGGING' in settings:
            settings['LOGGING'] = dict(settings['LOGGING'])

        return settings

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
                # if '.' in k:
                #     k = '(%s)' % k
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

    def _append_extras(self, settings, extras):
        if not extras:
            return
        for name, extra_val in extras.items():
            if not extra_val:
                continue
            if name.startswith('(') and name.endswith(')'):
                name = name[1:-1]
            current_val = settings[name]
            if not isinstance(current_val, Sequence):
                raise TypeError('EXTRA only works with list-type settings')
            settings[name] = current_val + extra_val

    def _swap_list_items(self, settings, swap):
        if not swap:
            return
        for name, swap_map in swap.items():
            if not swap_map:
                continue
            if name.startswith('(') and name.endswith(')'):
                name = name[1:-1]
            current_val = settings[name]
            if not isinstance(current_val, Sequence):
                raise TypeError('SWAP only works with list-type settings')
            for old_item, new_item in swap_map.items():
                k = current_val.index(old_item)
                current_val[k] = new_item

    def _import_from_string(self, settings, import_from_string):
        if not import_from_string:
            return
        for name in import_from_string:
            current_val = settings[name]
            if isinstance(current_val, string_types):
                settings[name] = import_string(current_val)
