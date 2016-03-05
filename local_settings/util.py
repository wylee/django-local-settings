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
    # We could set this as a global, but late binding is better in this
    # case. E.g., someone might import this module but not have set
    # os.environ['LOCAL_SETTINGS_FILE'] yet. We don't want them to have
    # to worry about the order of imports.
    file_name = os.environ.get('LOCAL_SETTINGS_FILE')
    if not file_name:
        file_name = os.path.join(os.getcwd(), 'local.cfg')
    return file_name


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
