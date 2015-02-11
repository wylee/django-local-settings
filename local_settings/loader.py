import os
import re
from collections import Mapping, Sequence

from six import string_types

from .base import Base
from .exc import SettingsFileNotFoundError
from .types import LocalSetting
from .util import NO_DEFAULT


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
        extends = parser[self.section].get('extends', None)
        settings = {}
        if extends:
            extends = self._parse_setting(extends, expand_vars=True)
            if isinstance(extends, str):
                extends = [extends]
            for e in extends:
                settings.update(self.__class__(e, extender=self).read_file())
        settings.update(parser[self.section])
        return settings

    def load(self, base_settings):
        """Load local settings from file into base settings."""
        if not os.path.exists(self.file_name):
            self.print_warning(
                'Local settings file `{0}` not found'.format(self.file_name))
            return
        for k, v in self.read_file().items():
            names = k.split('.')
            v = self._parse_setting(v, expand_vars=True)
            obj = base_settings
            for i, name in enumerate(names[:-1], 1):
                name = self._convert_name(name)
                is_mapping = isinstance(obj, Mapping)
                is_seq = isinstance(obj, Sequence)
                # Look at next name to see if dict or list should be added
                next_name = self._convert_name(names[i])
                if isinstance(next_name, int):
                    item = [NO_DEFAULT] * (next_name + 1)
                else:
                    item = {}
                # If there's already a list in the current slot...
                # If the existing list is longer, use it.
                # If the new list is longer, copy the items from the
                # existing list to the front of the new list.
                if isinstance(item, Sequence):
                    if is_mapping:
                        curr_item = obj.get(name)
                    elif is_seq:
                        curr_item = obj[name] if name < len(obj) else None
                    if isinstance(curr_item, Sequence):
                        if len(curr_item) >= len(item):
                            item = curr_item
                        else:
                            item[:len(curr_item)] = curr_item
                if is_mapping:
                    obj = obj.setdefault(name, item)
                elif is_seq:
                    obj[name] = item
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
        self._do_interpolation(base_settings, base_settings)

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
