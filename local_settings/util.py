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
