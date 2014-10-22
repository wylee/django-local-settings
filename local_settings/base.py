import json
from configparser import ConfigParser

from .color_printer import ColorPrinter
from .util import get_file_name


class Base(ColorPrinter):

    def __init__(self, file_name=None, colors=None):
        super(Base, self).__init__(colors)
        if file_name is None:
            file_name = get_file_name()
        self.file_name = file_name

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
