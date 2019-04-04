"""Strategies for reading from & writing to config files."""
import logging
import json
import os
from abc import ABCMeta, abstractmethod
from collections import OrderedDict
from configparser import NoSectionError, RawConfigParser

from six import raise_from, text_type, with_metaclass

from .exc import SettingsFileNotFoundError, SettingsFileSectionNotFoundError
from .util import parse_file_name_and_section


__all__ = [
    'Strategy',
    'INIStrategy',
    'INIJSONStrategy',
]


log = logging.getLogger(__name__)


class RawValue(text_type):

    """Marker for values that couldn't be decoded when reading."""


class Strategy(with_metaclass(ABCMeta)):

    file_types = ()

    @abstractmethod
    def get_defaults(self, file_name):
        """Get default settings from file.

        Returns:
            - Settings from the default section.

        """

    @abstractmethod
    def read_section(self, file_name, section=None):
        """Read settings from specified ``section`` of config file.

        This is where the strategy-specific file-reading logic goes.

        Returns:
            - Settings from the specified section or an empty dict if
              the section isn't present.
            - Whether the section is present.

        """

    @abstractmethod
    def write_settings(self, settings, file_name, section=None):
        """Write settings to file."""

    def parse_file_name_and_section(self, file_name, section=None, extender=None,
                                    extender_section=None):
        """Parse file name and (maybe) section.

        Delegates to :func:`.util.parse_file_name_and_section` to parse
        the file name and section. If that function doesn't find a
        section, this method should return the default section for the
        strategy via :meth:`get_default_section` (if applicable).

        """
        file_name, section = parse_file_name_and_section(
            file_name, section, extender, extender_section)
        if section is None:
            section = self.get_default_section(file_name)
        return file_name, section

    def read_file(self, file_name, section=None, _finalize=True):
        """Read settings from config file."""
        if _finalize:
            file_name, section = self.parse_file_name_and_section(file_name, section)

        if not os.path.isfile(file_name):
            raise SettingsFileNotFoundError(file_name)

        settings = OrderedDict()

        file_settings, section_present, extends, extends_section = \
            self._read_one_file(file_name, section)

        if extends:
            if extends != file_name:
                extends_settings, extends_section_present = \
                    self.read_file(extends, extends_section, _finalize=False)
                section_present = section_present or extends_section_present
                settings.update(extends_settings)

        settings.update(file_settings)

        if _finalize:
            if not section_present:
                raise SettingsFileSectionNotFoundError(section)
        else:
            return settings, section_present

        return settings

    def _read_one_file(self, file_name, section, settings=None):
        """Read settings from a single config file."""
        if settings is None:
            settings = self.get_defaults(file_name)

        items, section_present = self.read_section(file_name, section)
        default_extends = settings.get('extends', None)
        extends = items.pop('extends', default_extends)

        if extends:
            extends, extends_section = \
                self.parse_file_name_and_section(
                    extends, extender=file_name, extender_section=section)

            if extends == file_name:
                extends_items, extends_section_present, _, __ = \
                    self._read_one_file(file_name, extends_section, settings)
                settings.update(extends_items)
                section_present = section_present or extends_section_present
        else:
            extends_section = None

        settings.update(items)
        settings.pop('extends', None)
        return settings, section_present, extends, extends_section

    def get_default_section(self, file_name):
        return None

    def decode_items(self, items):
        """Bulk decode items read from file to Python objects.

        Args:
            items: A sequence of items as would be returned from
                ``dict.items()``.

        Returns:
            OrderedDict: A new ordered dict with item values decoded
                where possible. Values that can't be decoded will be
                wrapped with :class:`RawValue`.

        """
        decoded_items = OrderedDict()
        for k, v in items:
            try:
                v = self.decode_value(v)
            except ValueError:
                v = RawValue(v)
            decoded_items[k] = v
        return decoded_items

    def decode_value(self, value):
        """Decode value read from file to Python object."""
        return value

    def encode_value(self, value):
        """Encode Python object as value that can be written to file."""
        return value


class LocalSettingsConfigParser(RawConfigParser):

    def options(self, section):
        # Order [DEFAULT] options before section options; the default
        # implementation orders them after.
        options = list(self._defaults.keys())
        try:
            section = self._sections[section]
        except KeyError:
            raise_from(NoSectionError(section), None)
        options.extend(k for k in section.keys() if k not in self._defaults)
        return options

    def optionxform(self, option):
        # Don't alter option names; the default implementation lower
        # cases them.
        return option

    def get_section(self, section):
        """Get section without defaults.

        When retrieving a section from a :class:`RawConfigParser` using
        ``parser[section]``, defaults are included. To get a section's
        items without defaults, we have to access the semi-private
        ``_sections`` instance variable, which is encapsulated here.

        """
        return self._sections[section]


class INIStrategy(Strategy):

    file_types = ('ini',)

    def __init__(self):
        # Cache parsers by file name
        self._parser_cache = {}

    def get_defaults(self, file_name):
        """Get default settings from ``[DEFAULT]`` section of file."""
        parser = self.get_parser(file_name)
        defaults = parser.defaults()
        return self.decode_items(defaults.items())

    def read_section(self, file_name, section):
        parser = self.get_parser(file_name)
        if parser.has_section(section):
            items, section_present = parser.get_section(section), True
        else:
            items, section_present = {}, False
        decoded_items = self.decode_items(items.items())
        return decoded_items, section_present

    def write_settings(self, settings, file_name, section):
        file_name, section = self.parse_file_name_and_section(file_name, section)
        parser = self.make_parser()
        if os.path.exists(file_name):
            with open(file_name) as fp:
                parser.read_file(fp)
        else:
            log.info('Creating new local settings file: %s', file_name)
        if section not in parser:
            log.info('Adding new section to %s: %s', file_name, section)
            parser.add_section(section)
        sorted_keys = sorted(settings.keys())
        for name in sorted_keys:
            value = self.encode_value(settings[name])
            settings[name] = value
            parser[section][name] = value
        with open(file_name, 'w') as fp:
            parser.write(fp)
        for name in sorted_keys:
            value = settings[name]
            log.info('Saved %s to %s as: %s', name, file_name, value)

    def get_default_section(self, file_name):
        """Returns first non-DEFAULT section; falls back to DEFAULT."""
        if not os.path.isfile(file_name):
            return 'DEFAULT'
        parser = self.get_parser(file_name)
        sections = parser.sections()
        section = sections[0] if len(sections) > 0 else 'DEFAULT'
        return section

    def get_parser(self, file_name):
        if file_name not in self._parser_cache:
            parser = self.make_parser()
            with open(file_name) as fp:
                parser.read_file(fp)
            self._parser_cache[file_name] = parser
        return self._parser_cache[file_name]

    def make_parser(self):
        return LocalSettingsConfigParser()


class INIJSONStrategy(INIStrategy):

    file_types = ('cfg',)

    def decode_value(self, value):
        value = value.strip()
        if not value:
            return None
        try:
            value = json.loads(value)
        except ValueError:
            raise ValueError('Could not parse `{value}` as JSON'.format(**locals()))
        return value

    def encode_value(self, value):
        return json.dumps(value)


def get_strategy_types():
    """Get a list of all :class:`Strategy` subclasses.

    The list will be ordered by file type extension.

    """
    def get_subtypes(type_):
        subtypes = type_.__subclasses__()
        for subtype in subtypes:
            subtypes.extend(get_subtypes(subtype))
        return subtypes
    sub_types = get_subtypes(Strategy)
    return sorted(sub_types, key=lambda t: t.file_types[0])


def get_file_type_map():
    """Map file types (extensions) to strategy types."""
    file_type_map = OrderedDict()
    for strategy_type in get_strategy_types():
        for ext in strategy_type.file_types:
            if ext in file_type_map:
                raise KeyError(
                    'File type {ext} already registered to {file_type_map[ext]}'
                    .format(**locals()))
            file_type_map[ext] = strategy_type
    return file_type_map


def guess_strategy_type(file_name_or_ext):
    """Guess strategy type to use for file by extension.

    Args:
        file_name_or_ext: Either a file name with an extension or just
            an extension

    Returns:
        Strategy: Type corresponding to extension or None if there's no
            corresponding strategy type

    """
    if '.' not in file_name_or_ext:
        ext = file_name_or_ext
    else:
        name, ext = os.path.splitext(file_name_or_ext)
    ext = ext.lstrip('.')
    file_type_map = get_file_type_map()
    return file_type_map.get(ext, None)
