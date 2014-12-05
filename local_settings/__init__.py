import os
import sys

from .color_printer import ColorPrinter
from .checker import Checker
from .exc import LocalSettingsError, SettingsFileNotFoundError
from .loader import Loader
from .types import LocalSetting, SecretSetting
from .util import get_file_name
from .__main__ import make_local_settings


def load_and_check_settings(base_settings,  file_name=None, section=None,
                            base_path=None):
    """Load settings from file into base settings, then check settings.

    Settings loaded from the specified file will override base settings,
    then the settings will be checked to ensure that all required local
    settings have been set. Note that this modifies ``base_settings`` in
    place.

    If a file name is passed: if the file exists, local settings will be
    loaded from it and any missing settings will be appended to it; if
    the file does not exist, it will be created and all settings will be
    added to it.

    If a file name isn't passed: if the ``LOCAL_SETTINGS_FILE_NAME``
    environment variable is set, the specified file will be used;
    otherwise ``{base_path}/local.cfg`` will be used.

    ``base_path`` is used when ``file_name`` is relative; if it's not
    passed, it will be set to the current working directory.

    See :meth:`.Loader.load` and :meth:`.Checker.check` for more info.

    """
    printer = ColorPrinter()
    key = 'DISABLE_LOCAL_SETTINGS'
    disable_local_settings = os.environ.get(key, base_settings.get(key, False))
    if disable_local_settings:
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
            loader.load(base_settings)
            registry = loader.registry
        except SettingsFileNotFoundError:
            registry = None
        checker = Checker(file_name, section, registry=registry)
        success = checker.check(base_settings)
    except KeyboardInterrupt:
        # Loading/checking of local settings was aborted with Ctrl-C.
        # This isn't an error, but we don't want to continue.
        printer.print_warning('\nAborted loading/checking of local settings')
        sys.exit(0)
    if success:
        printer.print_success('Settings loaded successfully from {0}'.format(file_name))
    else:
        raise LocalSettingsError(
            'Could not load local settings from {0}'.format(file_name))
