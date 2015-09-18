import json
import os
import sys

from .color_printer import ColorPrinter
from .checker import Checker
from .exc import LocalSettingsError, SettingsFileNotFoundError
from .loader import Loader
from .types import LocalSetting, SecretSetting
from .util import NO_DEFAULT, get_file_name
from .__main__ import make_local_settings


def load_and_check_settings(base_settings,  file_name=None, section=None, base_path=None,
                            quiet=NO_DEFAULT):
    """Merge local settings from file with base settings, then check.

    Returns a new OrderedDict containing the base settings and the
    loaded settings. Ordering is:

        - base settings
        - settings from extended file(s), if any
        - settings from file

    When a setting is overridden, it gets moved to the end.

    Settings loaded from the specified file will override base settings,
    then the settings will be checked to ensure that all required local
    settings have been set.

    If a file name is passed: if the file exists, local settings will be
    loaded from it and any missing settings will be appended to it; if
    the file does not exist, it will be created and all settings will be
    added to it.

    If a file name isn't passed: if the ``LOCAL_SETTINGS_FILE_NAME``
    environment variable is set, the specified file will be used;
    otherwise ``{base_path}/local.cfg`` will be used.

    ``base_path`` is used when ``file_name`` is relative; if it's not
    passed, it will be set to the current working directory.

    When ``quiet`` is ``True``, informational messages will not be
    printed. The ``LOCAL_SETTINGS_CONFIG_QUIET`` can be used to set
    ``quiet`` (use a JSON value like 'true', '1', 'false', or '0').

    See :meth:`.Loader.load` and :meth:`.Checker.check` for more info.

    """
    if quiet is NO_DEFAULT:
        quiet = json.loads(os.environ.get('LOCAL_SETTINGS_CONFIG_QUIET', 'false'))
    if not quiet:
        printer = ColorPrinter()
    key = 'LOCAL_SETTINGS_DISABLE'
    disable_local_settings = os.environ.get(key, base_settings.get(key, False))
    if disable_local_settings:
        if not quiet:
            printer.print_warning('Loading of local settings disabled')
        return
    else:
        if file_name is None:
            file_name = get_file_name()
        if not os.path.isabs(file_name):
            base_path = base_path or os.getcwd()
            file_name = os.path.normpath(os.path.join(base_path, file_name))
    try:
        try:
            loader = Loader(file_name, section)
            settings = loader.load(base_settings)
            registry = loader.registry
        except SettingsFileNotFoundError:
            registry = None
            settings = base_settings
        checker = Checker(file_name, section, registry=registry)
        success = checker.check(settings)
    except KeyboardInterrupt:
        # Loading/checking of local settings was aborted with Ctrl-C.
        # This isn't an error, but we don't want to continue.
        if not quiet:
            printer.print_warning('\nAborted loading/checking of local settings')
        sys.exit(0)
    if not success:
        raise LocalSettingsError(
            'Could not load local settings from {0}'.format(file_name))
    if not quiet:
        printer.print_success('Settings loaded successfully from {0}'.format(file_name))
    return settings
