import importlib
import io
import os


NO_DEFAULT = type('NO_DEFAULT', (), {
    '__nonzero__': (lambda self: False),  # Python 2
    '__bool__': (lambda self: False),  # Python 3
    '__str__': (lambda self: self.__class__.__name__),
    '__repr__': (lambda self: str(self)),
    '__copy__': (lambda self: self),
})()


def get_file_name():
    """Get local settings file from environ or discover it.

    If the ``LOCAL_SETTINGS_FILE`` environment variable is set, its
    value is returned directly.

    Otherwise, the current working directory is searched for
    `local.{ext}` for each file extension handled by each loading
    :mod:`strategy`. Note that the search is done in alphabetical order
    so that if ``local.cfg`` and ``local.yaml`` both exist, the former
    will be returned.

    Returns:
        str: File name if set via environ or discovered
        None: File name isn't set and wasn't discovered

    """
    file_name = os.environ.get('LOCAL_SETTINGS_FILE')
    if file_name:
        return file_name
    cwd = os.getcwd()
    default_file_names = get_default_file_names()
    for file_name in default_file_names:
        file_name = os.path.join(cwd, file_name)
        if os.path.exists(file_name):
            return file_name


def get_default_file_names():
    """Get default file names for all loading strategies, sorted."""
    from .strategy import get_file_type_map  # noqa: Avoid circular import
    return sorted('local.{ext}'.format(ext=ext) for ext in get_file_type_map())


def parse_file_name_and_section(file_name, section=None, extender=None, extender_section=None):
    """Parse file name and (maybe) section.

    File names can be absolute paths, relative paths, or asset
    specs::

        /home/user/project/local.cfg
        local.cfg
        some.package:local.cfg

    File names can also include a section::

        some.package:local.cfg#dev

    If a ``section`` is passed, it will take precedence over a
    section parsed out of the file name.

    """
    if '#' in file_name:
        file_name, parsed_section = file_name.rsplit('#', 1)
    else:
        parsed_section = None

    if ':' in file_name:
        file_name = asset_path(file_name)

    if extender:
        if not file_name:
            # Extended another section in the same file
            file_name = extender
        elif not os.path.isabs(file_name):
            # Extended by another file in the same directory
            file_name = abs_path(file_name, relative_to=os.path.dirname(extender))

    if section:
        pass
    elif parsed_section:
        section = parsed_section
    elif extender_section:
        section = extender_section
    else:
        section = None

    return file_name, section


# Path utilities


def abs_path(path, relative_to=None):
    """Make path absolute and normalize it."""
    if os.path.isabs(path):
        path = os.path.normpath(path)
    elif ':' in path:
        path = asset_path(path)
    else:
        path = os.path.expanduser(path)
        if relative_to:
            path = os.path.join(relative_to, path)
        path = os.path.abspath(path)
        path = os.path.normpath(path)
    return path


def asset_path(path):
    """Get absolute path from asset spec and normalize it."""
    if ':' in path:
        package_name, rel_path = path.split(':', 1)
    else:
        package_name, rel_path = path, ''

    try:
        package = importlib.import_module(package_name)
    except ImportError:
        raise ValueError(
            'Could not get asset path for {path}; could not import package: {package_name}'
            .format_map(locals()))

    if not hasattr(package, '__file__'):
        raise ValueError("Can't compute path relative to namespace package")

    package_path = os.path.dirname(package.__file__)
    if rel_path:
        path = os.path.join(package_path, rel_path)
    path = os.path.normpath(path)

    return path


# These TTY functions were copied from Invoke


def is_a_tty(stream):
    if hasattr(stream, 'isatty') and callable(stream.isatty):
        return stream.isatty()
    elif has_fileno(stream):
        return os.isatty(stream.fileno())
    return False


def has_fileno(stream):
    try:
        return isinstance(stream.fileno(), int)
    except (AttributeError, io.UnsupportedOperation):
        return False
