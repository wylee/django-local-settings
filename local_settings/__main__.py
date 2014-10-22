import argparse
import os
from pkg_resources import find_distributions

from .checker import Checker
from .loader import Loader


def make_local_settings(argv=None):
    """Generate a local settings file."""
    parser = argparse.ArgumentParser(
        description=make_local_settings.__doc__,
    )

    parser.add_argument('env', help='Environment name (e.g., dev or prod)')
    parser.add_argument(
        '-b', '--base-settings-module', default=None,
        help='Base settings module as a dotted path')
    parser.add_argument(
        '-f', '--file-name', default=None,
        help='Name of file to write settings into')
    parser.add_argument('-o', '--overwrite', action='store_true', default=False)

    args = parser.parse_args(argv)

    os.environ['DISABLE_LOCAL_SETTINGS'] = '1'
    if args.base_settings_module is None:
        dist = next(find_distributions('.', only=True), None)
        if dist is not None:
            args.base_settings_module = '{0.project_name}.settings.base'.format(dist)
        else:
            msg = 'Could not guess which base settings module to use; specify with -b'
            parser.exit(1, msg)

    module = __import__(args.base_settings_module, fromlist=[''])
    base_settings = vars(module)

    if args.file_name is None:
        args.file_name = 'local.{0.env}.cfg'.format(args)
    file_name = os.path.normpath(os.path.abspath(args.file_name))
    registry = None
    if os.path.exists(file_name):
        if args.overwrite:
            print('Overwriting {0.file_name}'.format(args))
            with open(file_name, 'w'):
                pass
        else:
            loader = Loader(file_name)
            loader.load(base_settings)
            registry = loader.registry

    checker = Checker(file_name, registry)
    try:
        checker.check(base_settings)
    except KeyboardInterrupt:
        print('\nAborted')


if __name__ == '__main__':
    make_local_settings()
