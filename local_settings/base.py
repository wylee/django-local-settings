import json
from configparser import ConfigParser

from .color_printer import ColorPrinter
from .util import get_file_name


class Base(ColorPrinter):

    def __init__(self, file_name=None, section=None, extends=None, colors=None):
        """Initialize config file name and section.

        The file name will be selected from the following list, in order
        of precedence:

            - Explicitly passed file name
            - If the environment variable `LOCAL_SETTINGS_FILE` is set,
              its value will be used
            - Otherwise, local.cfg in the current working directory will
              be used

        The section will be selected from the following list, in order
        of precedence:

            - Explicitly passed section
            - Section passed via file name (using file_name#section
              syntax)
            - The section that's being extended, if applicable
            - The only section in the file, *iff* there's exactly one
              section
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

        if section:
            pass
        elif parsed_section:
            section = parsed_section
        elif extends:
            section = extends.section
        else:
            parser = self._make_parser()
            with open(file_name) as fp:
                parser.read_file(fp)
            sections = parser.sections()
            if len(sections) == 1:
                section = sections[0]
            else:
                section = 'DEFAULT'

        self.file_name = file_name
        self.section = section

    def _make_parser(self, *args, **kwargs):
        parser = ConfigParser(*args, **kwargs)
        parser.optionxform = lambda option: option
        return parser

    def _parse_setting(self, v):
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
        return v
