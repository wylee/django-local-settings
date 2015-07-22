import os
import re
from collections import Mapping, OrderedDict, Sequence

from six import string_types

from .base import Base
from .exc import SettingsFileNotFoundError
from .types import LocalSetting
from .util import NO_DEFAULT as PLACEHOLDER


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
            extends = self._parse_setting(extends, expand_vars=True)
            if isinstance(extends, str):
                extends = [extends]
            for e in reversed(extends):
                settings.update(self.__class__(e, extender=self).read_file())
        settings_from_file = parser[self.section]
        for k in settings:
            if k in settings_from_file:
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

        """
        if not os.path.exists(self.file_name):
            self.print_warning(
                'Local settings file `{0}` not found'.format(self.file_name))
            return
        is_upper = lambda k: k == k.upper()
        settings = OrderedDict((k, v) for (k, v) in base_settings.items() if is_upper(k))
        for k, v in self.read_file().items():
            names = k.split('.')
            v = self._parse_setting(v, expand_vars=True)
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
        self._do_interpolation(settings, settings)
        return settings

    def _do_interpolation(self, v, settings):
        if isinstance(v, string_types):
            v = v.format(**settings)
        elif isinstance(v, Mapping):
            for k in v:
                v[k] = self._do_interpolation(v[k], settings)
        elif isinstance(v, Sequence):
            v = v.__class__(self._do_interpolation(item, settings) for item in v)
        return v

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
