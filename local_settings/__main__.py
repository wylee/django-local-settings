import argparse
import importlib
import os
import sys
import textwrap

from setuptools import find_packages

from .color_printer import color_printer as printer
from .loader import Loader
from .strategy import get_file_type_map, guess_strategy_type


class ArgParser(argparse.ArgumentParser):

    def error(self, message):
        message = '{self.prog} error: {message}\n'.format(**locals())
        message = printer.string_error(message)
        self.print_usage(sys.stderr)
        self.exit(2, message)


def make_local_settings(argv=None):
    """Generate a local settings file.

    The most common usage is:

        make-local-settings <env>

    where env is replaced with and environment name such as stage or
    prod. For example:

        make-local-settings prod

    This will create a local settings file named local.prod.cfg with
    a prod section if local.prod.cfg does not exist. If local.prod.cfg
    already exists, the prod section will be added if it doesn't exist,
    and any missing local settings will be prompted for and added.

    """
    description = textwrap.dedent('    %s' % make_local_settings.__doc__)

    parser = ArgParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('env', nargs='?', help='Environment name (e.g., dev or prod)')
    parser.add_argument('-t', '--type', default='cfg')
    parser.add_argument(
        '-b', '--base-settings-module', default=None,
        help='Base settings module as a dotted path')
    parser.add_argument(
        '-f', '--file-name', default=None,
        help='Name of file to write settings into')
    parser.add_argument(
        '-s', '--section', default=None,
        help='Section to read/write settings from/to (default = <env>)')
    parser.add_argument(
        '-e', '--extends', default=None,
        help='File name and section to extend from as file_name.ext#section (section is optional)')
    parser.add_argument('-o', '--overwrite', action='store_true', default=False)

    args = parser.parse_args(argv)

    if args.type:
        strategy_type = get_file_type_map()[args.type]
        strategy = strategy_type()

    if args.base_settings_module is None:
        package = find_packages()[0]
        path = os.path.join(os.getcwd(), package, 'settings.py')
        if os.path.exists(path):
            args.base_settings_module = '{package}.settings'.format(package=package)
            printer.print_info(
                'Using {0.base_settings_module} as base settings module'.format(args))
        else:
            parser.error('Could not guess which base settings module to use; specify with -b')

    if args.file_name:
        file_name = args.file_name
        if not args.type:
            strategy_type = guess_strategy_type(file_name)
            strategy = strategy_type()
    elif args.env:
        file_name = 'local.{0.env}.{ext}'.format(args, ext=strategy.file_types[0])
    else:
        parser.error('Either env or file name must be specified')
    file_name = os.path.normpath(os.path.abspath(file_name))

    if args.section:
        section = args.section
    elif args.env:
        section = args.env
    else:
        parser.error('Either env or section must be specified')

    if os.path.exists(file_name):
        if args.overwrite:
            printer.print_warning('Overwriting', file_name)
            os.remove(file_name)

    # This will create the file if it doesn't exist. The extends
    # settings will be written whether or not the file exists.
    settings = {}
    if args.extends:
        settings['extends'] = args.extends
    strategy.write_settings(settings, file_name, section)

    # Load base settings from settings module while A) ensuring that
    # local settings aren't loaded in the process and B) accounting for
    # the fact that the base settings might not load local settings.
    original_disable_value = os.environ.get('LOCAL_SETTINGS_CONFIG_DISABLE')
    os.environ['LOCAL_SETTINGS_CONFIG_DISABLE'] = '1'
    settings_module = importlib.import_module(args.base_settings_module)
    base_settings = vars(settings_module)
    os.environ.pop('LOCAL_SETTINGS_CONFIG_DISABLE')
    if original_disable_value is not None:
        os.environ['LOCAL_SETTINGS_CONFIG_DISABLE'] = original_disable_value

    loader = Loader(file_name, section, strategy_type=strategy_type)
    loader.load_and_check(base_settings, prompt=True)


if __name__ == '__main__':
    make_local_settings()
