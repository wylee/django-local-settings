"""Strategies for reading from & writing to config files."""
import logging
import json
import os
import pkg_resources
from abc import ABCMeta, abstractmethod
from configparser import RawConfigParser

from six import with_metaclass

from .exc import SettingsFileNotFoundError, SettingsFileSectionNotFoundError


__all__ = [
    'Strategy',
    'INIStrategy',
    'INIJSONStrategy',
]


log = logging.getLogger(__name__)


class Strategy(with_metaclass(ABCMeta)):

    @abstractmethod
    def read_file(self, file_name, section=None):
        """Read settings from file."""

    @abstractmethod
    def write_settings(self, settings, file_name, section=None):
        """Write settings to file."""

    def parse_file_name_and_section(self, file_name, section=None, extender=None,
                                    extender_section=None):
        """Parse file name and (maybe) section.

        File names can be absolute paths, relative paths, or asset
        specs::

            /home/user/project/local.cfg
            local.cfg
            some.package:local.cfg

        File names can also include a section::

            some.package:local.cfg#dev

        If a ``section`` is passed, it will take precedence over a
        section parsed out of the file name.

        """
        if '#' in file_name:
            file_name, parsed_section = file_name.rsplit('#', 1)
        else:
            parsed_section = None

        if ':' in file_name:
            package, path = file_name.split(':', 1)
            file_name = pkg_resources.resource_filename(package, path)

        if extender:
            if not file_name:
                # Extended another section in the same file
                file_name = extender
            elif not os.path.isabs(file_name):
                # Extended by another file in the same directory
                file_name = os.path.join(os.path.dirname(extender), file_name)

        if section:
            pass
        elif parsed_section:
            section = parsed_section
        elif extender_section:
            section = extender_section
        else:
            section = self.get_default_section(file_name)

        return file_name, section

    def get_default_section(self, file_name):
        return None

    def decode_value(self, value):
        """Decode value read from file to Python object."""
        return value

    def encode_value(self, value):
        """Encode Python object as value that can be written to file."""
        return value


class LocalSettingsConfigParser(RawConfigParser):

    def optionxform(self, option):
        return option


class INIStrategy(Strategy):

    def read_file(self, file_name, section=None):
        """Read settings from specified ``section`` of config file."""
        file_name, section = self.parse_file_name_and_section(file_name, section)
        if not os.path.isfile(file_name):
            raise SettingsFileNotFoundError(file_name)
        parser = self.make_parser()
        with open(file_name) as fp:
            parser.read_file(fp)
        if section not in parser:
            raise SettingsFileSectionNotFoundError(section)
        extends = parser[section].get('extends')
        settings = {}
        if extends:
            extends = self.decode_value(extends)
            extends, extends_section = self.parse_file_name_and_section(
                extends, extender=file_name, extender_section=section)
            settings.update(self.read_file(extends, extends_section))
        settings.update(parser[section])
        return settings

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
        parser = self.make_parser()
        with open(file_name) as fp:
            parser.read_file(fp)
        sections = parser.sections()
        section = sections[0] if len(sections) > 0 else 'DEFAULT'
        return section

    def make_parser(self, *args, **kwargs):
        return LocalSettingsConfigParser(*args, **kwargs)


class INIJSONStrategy(INIStrategy):

    def decode_value(self, value):
        value = value.strip()
        if not value:
            return ''
        try:
            value = json.loads(value)
        except ValueError:
            raise ValueError('Could not parse `{value}` as JSON'.format_map(locals()))
        return value

    def encode_value(self, value):
        return json.dumps(value)