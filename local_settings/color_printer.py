from __future__ import print_function

import sys

from six import add_metaclass

from .util import is_a_tty


class ColorPrinterMeta(type):

    def __init__(cls, *args, **kwargs):
        def _make_methods(_color):
            def _print(self, *a, **kw):
                kw['color'] = _color
                return self.print(*a, **kw)

            def _string(self, *a, **kw):
                return self.string(_color, *a, **kw)

            setattr(cls, 'print_{0}'.format(color), _print)
            setattr(cls, 'string_{0}'.format(color), _string)

        for color in cls.colors:
            _make_methods(color)


@add_metaclass(ColorPrinterMeta)
class ColorPrinter(object):

    """Prints things in color (or not).

    Default colors can be overridden by passing a dict of colors to
    the constructor.

    Use stand-alone or as a mixin::

        >>> printer = ColorPrinter()
        >>> printer.print('boring old message')
        boring old message
        >>> printer.string('none', 'boring old message')
        'boring old message\\x1b[0m'
        >>> printer.print_info('check this out')
        check this out
        >>> printer.print_error('whoopsie')
        whoopsie
        >>> printer.string('error', 'whoopsie')
        '\\x1b[91mwhoopsie\\x1b[0m'
        >>> MyClass = type('MyClass', (ColorPrinter,), {})
        >>> my_obj = MyClass(colors={'header': '\033[96m'})
        >>> my_obj.print_header('Header')
        Header
        >>> my_obj.string('header', 'Header')
        '\\x1b[96mHeader\\x1b[0m'

    Note: This uses the print function from Python 3.

    """

    colors = {
        'header': '\033[95m',
        'info': '\033[94m',
        'success': '\033[92m',
        'warning': '\033[93m',
        'error': '\033[91m',
        'reset': '\033[0m',
        'none': '',
    }

    def __init__(self, colors=None):
        if colors is not None:
            self.colors = self.colors.copy()
            self.colors.update(colors)

    def print(self, *args, **kwargs):
        """Like built-in ``print()`` but colorizes strings.

        Pass ``color`` as a keyword arg to colorize ``*args`` before
        printing them. If no ``color`` is passed, *args will printed
        without color.

        """
        color = kwargs.pop('color', None)
        file = kwargs.get('file', sys.stdout)
        if color and is_a_tty(file):
            string = self.string(color, *args, **kwargs)
            print(string, **kwargs)
        else:
            print(*args, **kwargs)

    def string(self, color, *args, **kwargs):
        """Returns a colorized string (joining ``args`` into one str).

        The arguments for this are similar to the built-in ``print()``.
        ``sep`` is a space by default, but ``end`` is an empty string.

        """
        color = self.colors[color]
        sep = kwargs.get('sep', ' ')
        end = kwargs.get('end', '')
        template = '{color}{string}{reset}'
        string = sep.join(str(a) for a in args)
        string = template.format(
            color=color, string=string, reset=self.colors['reset'])
        if end:
            string += end
        return string


color_printer = ColorPrinter()
