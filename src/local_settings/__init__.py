import inspect
import os
import sys
from json import loads

from .color_printer import color_printer as printer
from .exc import LocalSettingsError, SettingsFileDidNotPassCheck
from .loader import Loader
from .util import abs_path, get_file_name, load_dotenv

# Exported (but unused locally)
from .checker import Checker  # noqa: exported
from .exc import SettingsFileNotFoundError  # noqa: exported
from .settings import Settings  # noqa: exported
from .types import EnvSetting, LocalSetting, SecretSetting  # noqa: exported
from .util import NO_DEFAULT  # noqa: exported
from .util import get_default_file_names
from .__main__ import make_local_settings  # noqa: exported


__version__ = "2.0a5"


def load_and_check_settings(
    base_settings,
    file_name=None,
    section=None,
    base_path=None,
    strategy_type=None,
    disable=None,
    prompt=None,
    quiet=None,
    env_only=False,
    dotenv_file=None,
    dotenv_file_name=".env",
):
    """Merge local settings from file with base settings, then check.

    Returns a new dict containing the base settings and the loaded
    settings. Includes:

        - base settings
        - settings from extended file(s), if any
        - settings from file
        - settings from env, if any env settings are defined

    Settings loaded from the local settings file(s) will override base
    settings. If any env settings are defined and set in the environ,
    they will override base settings and settings loaded from file(s).

    After all settings are loaded from the various sources, they will be
    checked to ensure that all local settings have been set.

    If a file name is passed and the file exists, local settings will be
    loaded from it and, if ``prompt=True`` (see below), any missing
    settings will be appended to it. If the file doesn't exist, it will
    be created and, if ``prompt=True``, all settings will be added to
    it.

    If a file name isn't passed: if the ``LOCAL_SETTINGS_FILE``
    environment variable is set, the specified file will be used;
    otherwise ``{base_path}/local.{ext}`` will be used. Settings will be
    appended or added as described above.

    ``base_path`` is used when ``file_name`` is relative; if it's not
    passed, it will be set to the current working directory.

    When ``prompt`` is ``True``, the user will be prompted for missing
    local settings, which will be added to the specified or discovered
    local settings file. By default, the user is prompted only when
    running on TTY. The ``LOCAL_SETTINGS_CONFIG_PROMPT`` environment
    variable can be used to set ``prompt``.

    When ``quiet`` is ``True``, informational messages will not be
    printed. The ``LOCAL_SETTINGS_CONFIG_QUIET`` environment variable
    can be used to set ``quiet``.

    When ``env_only`` is ``True``, only env settings will be loaded--
    all the file loading steps noted above will be skipped. Note that
    if other, non-env local settings are defined, this will cause an
    error when ``env_only=True``.

    ``dotenv_file`` can be used to specify a .env file for loading
    local settings configuration environment variables. This can be the
    same .env file used for local settings or a different one. It can be
    specified as an absolute, relative (to ``base_path``), or asset
    path.

    .. note:: When setting flags via environment variables, use a JSON
        value like 'true', '1', 'false', or '0'.

    See :meth:`.Loader.load` and :meth:`.Checker.check` for more info.

    """
    environ_config = get_config_from_environ(dotenv_file, base_path, dotenv_file_name)
    disable = environ_config["disable"] if disable is None else disable
    if disable:
        return {}
    prompt = get_prompt(environ_config, prompt, env_only)
    quiet = environ_config["quiet"] if quiet is None else quiet
    file_name = get_local_settings_file_name(file_name, base_path, env_only)
    try:
        loader = Loader(file_name, section, strategy_type=strategy_type)
        settings, success = loader.load_and_check(base_settings, prompt)
    except KeyboardInterrupt:
        # Loading/checking of local settings was aborted with Ctrl-C
        # during prompting. This isn't an error, but we don't want to
        # continue.
        if not quiet:
            printer.print_warning("\nAborted loading/checking of local settings")
        # XXX: It seems wonky sys.exit() here; seems like the exception
        #      should just be re-raised.
        sys.exit(0)
    if loader.section:
        file_name = f"{loader.file_name}#{loader.section}"
    else:
        file_name = loader.file_name
    if not success:
        raise SettingsFileDidNotPassCheck(file_name)
    if not quiet:
        printer.print_success(f"Settings loaded successfully from {file_name}")
    return settings


def get_prompt(environ_config, prompt, env_only):
    if env_only:
        if prompt:
            raise LocalSettingsError("The prompt flag can't be set when env_only=True")
        prompt = False
    else:
        prompt = environ_config["prompt"] if prompt is None else prompt
    return prompt


def get_local_settings_file_name(file_name, base_path, env_only):
    if env_only:
        if file_name:
            raise LocalSettingsError(
                "A local settings file can't be specified when env_only=True"
            )
        file_name = None
    else:
        if file_name is None:
            file_name = get_file_name()
        if file_name is None:
            cwd = os.getcwd()
            default_file_names = ", ".join(get_default_file_names())
            raise SettingsFileNotFoundError(
                f"No local settings file was specified and no default "
                f"settings file was found in the current working directory "
                f"(cwd = {cwd}, defaults = {default_file_names})"
            )
        base_path = base_path or os.getcwd()
        file_name = abs_path(file_name, relative_to=base_path)
    return file_name


def inject_settings(base_settings=None, **kwargs):
    """Inject local settings into settings module.

    Call this from the global scope of your Django settings module to
    load settings from the local settings file and inject them into the
    settings module::

        from local_settings import inject_settings
        inject_settings()

    This is equivalent to, but much less tedious than, the following::

        from local_settings import load_and_check_settings
        globals.update(load_and_check_settings(globals()))

    """
    if base_settings is None:
        frame = inspect.stack()[1][0]
        base_settings = frame.f_globals
    settings = load_and_check_settings(base_settings, **kwargs)
    base_settings.update(settings)


def get_config_from_environ(dotenv_file, base_path, file_name=".env"):
    def get(name, default="null"):
        name = name.upper()
        name = f"LOCAL_SETTINGS_CONFIG_{name}"
        return loads(os.environ.get(name, default))

    load_dotenv(dotenv_file, base_path, file_name)
    options = (
        ("disable", "false"),
        ("prompt", "null"),
        ("quiet", "false"),
    )
    return {n: get(n, default) for (n, default) in options}
