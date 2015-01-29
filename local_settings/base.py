import json
import os.path
import pkg_resources
from collections import Mapping, Sequence
from configparser import ConfigParser

from six import string_types

from .color_printer import ColorPrinter
from .util import get_file_name


class Base(ColorPrinter):

    def __init__(self, file_name=None, section=None, extender=None, colors=None):
        """Initialize config file name and section.

        The file name will be selected from the following list, in order
        of precedence:

            - Explicitly passed file name
            - If the environment variable `LOCAL_SETTINGS_FILE` is set,
              its value will be used
            - Otherwise, local.cfg in the current working directory will
              be used

        File names can take one of the following forms:

            - Absolute
            - Relative: When a file name is specified in a settings file
              (i.e., via extends), it will be made absolute by
              prepending the directory containing the settings file
            - Asset spec: A string like '{package}:{path}`

        The section will be selected from the following list, in order
        of precedence:

            - Explicitly passed section
            - Section passed via file name (using file_name#section
              syntax)
            - The section that's being extended, if applicable
            - The first section in the file
            - [DEFAULT]

        """
        super(Base, self).__init__(colors)

        if not file_name:
            file_name = get_file_name()
            parsed_section = None
        elif '#' in file_name:
            file_name, parsed_section = file_name.rsplit('#', 1)
        else:
            parsed_section = None

        if ':' in file_name:
            package, path = file_name.split(':', 1)
            file_name = pkg_resources.resource_filename(package, path)

        if extender:
            if not file_name:
                file_name = extender.file_name
            elif not os.path.isabs(file_name):
                # When a file is extended by another (the "extender"),
                # ensure that the path to the extended file is correct.
                file_name = os.path.join(os.path.dirname(extender.file_name), file_name)

        if section:
            pass
        elif parsed_section:
            section = parsed_section
        elif extender:
            section = extender.section
        else:
            parser = self._make_parser()
            with open(file_name) as fp:
                parser.read_file(fp)
            sections = parser.sections()
            section = sections[0] if len(sections) > 0 else 'DEFAULT'

        self.file_name = file_name
        self.section = section

    def _make_parser(self, *args, **kwargs):
        parser = ConfigParser(*args, **kwargs)
        parser.optionxform = lambda option: option
        return parser

    def _parse_setting(self, v, expand_vars=False):
        """Parse the string ``v`` and return the parsed value.

        If ``v`` is an empty string, ``None`` will be returned.
        Otherwise, ``v`` will be parsed as JSON.

        Raises a ``ValueError`` when ``v`` can't be parsed.

        """
        v = v.strip()
        if not v:
            return ''
        try:
            v = json.loads(v)
        except ValueError:
            raise ValueError('Could not parse `{0}` as JSON'.format(v))
        if expand_vars:
            return self._expand_vars(v)
        return v

    def _expand_vars(self, v):
        """Expand all env. vars in all strings in/under ``v``."""
        if isinstance(v, string_types):
            v = os.path.expandvars(v)
        elif isinstance(v, Mapping):
            for k in v:
                v[k] = self._expand_vars(v[k])
        elif isinstance(v, Sequence):
            for i, item in enumerate(v):
                v[i] = self._expand_vars(item)
        return v
