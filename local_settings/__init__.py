import json
import os
import sys

from .color_printer import color_printer as printer
from .exc import SettingsFileDidNotPassCheck
from .loader import Loader
from .util import abs_path, get_file_name

# Exported (but unused locally)
from .checker import Checker  # noqa: exported
from .exc import SettingsFileNotFoundError  # noqa: exported
from .settings import Settings  # noqa: exported
from .types import LocalSetting, SecretSetting  # noqa: exported
from .util import NO_DEFAULT  # noqa: exported
from .util import get_default_file_names
from .__main__ import make_local_settings  # noqa: exported


__version__ = '1.0b10'


def load_and_check_settings(base_settings, file_name=None, section=None, base_path=None,
                            strategy_type=None, disable=None, prompt=None, quiet=None):
    """Merge local settings from file with base settings, then check.

    Returns a new dict containing the base settings and the loaded
    settings. Includes:

        - base settings
        - settings from extended file(s), if any
        - settings from file

    Settings loaded from the specified file will override base settings,
    then the settings will be checked to ensure that all required local
    settings have been set.

    If a file name is passed: if the file exists, local settings will be
    loaded from it and any missing settings will be appended to it; if
    the file does not exist, it will be created and all settings will be
    added to it.

    If a file name isn't passed: if the ``LOCAL_SETTINGS_FILE_NAME``
    environment variable is set, the specified file will be used;
    otherwise ``{base_path}/local.{ext}`` will be used.

    ``base_path`` is used when ``file_name`` is relative; if it's not
    passed, it will be set to the current working directory.

    When ``prompt`` is ``True``, the user will be prompted for missing
    local settings. By default, the user is prompted only when running
    on TTY. The ``LOCAL_SETTINGS_CONFIG_PROMPT`` environment variable
    can be used to set ``prompt``.

    When ``quiet`` is ``True``, informational messages will not be
    printed. The ``LOCAL_SETTINGS_CONFIG_QUIET`` environment variable
    can be used to set ``quiet``.

    .. note:: When setting flags via environment variables, use a JSON
        value like 'true', '1', 'false', or '0'.

    See :meth:`.Loader.load` and :meth:`.Checker.check` for more info.

    """
    environ_config = get_config_from_environ()
    disable = environ_config['disable'] if disable is None else disable
    prompt = environ_config['prompt'] if prompt is None else prompt
    quiet = environ_config['quiet'] if quiet is None else quiet
    if disable:
        return {}
    if file_name is None:
        file_name = get_file_name()
    if file_name is None:
        cwd = os.getcwd()
        default_file_names = ', '.join(get_default_file_names())
        raise SettingsFileNotFoundError(
            'No local settings file was specified and no default settings file was found in the '
            'current working directory (cwd = {cwd}, defaults = {default_file_names})'
            .format(**locals()))
    base_path = base_path or os.getcwd()
    file_name = abs_path(file_name, relative_to=base_path)
    try:
        loader = Loader(file_name, section, strategy_type=strategy_type)
        settings, success = loader.load_and_check(base_settings, prompt)
    except KeyboardInterrupt:
        # Loading/checking of local settings was aborted with Ctrl-C.
        # This isn't an error, but we don't want to continue.
        if not quiet:
            printer.print_warning('\nAborted loading/checking of local settings')
        sys.exit(0)
    if loader.section:
        file_name = '{loader.file_name}#{loader.section}'.format(loader=loader)
    else:
        file_name = loader.file_name
    if not success:
        raise SettingsFileDidNotPassCheck(file_name)
    if not quiet:
        printer.print_success('Settings loaded successfully from {0}'.format(file_name))
    return settings


def get_config_from_environ():
    def get(name, default='null'):
        name = name.upper()
        name = 'LOCAL_SETTINGS_CONFIG_{name}'.format(name=name)
        return json.loads(os.environ.get(name, default))
    options = (
        ('disable', 'false'),
        ('prompt', 'null'),
        ('quiet', 'false'),
    )
    return {n: get(n, default) for (n, default) in options}
