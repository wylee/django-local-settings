import json

from .exc import NoDefaultError, NoValueError
from .util import NO_DEFAULT


class LocalSetting(object):

    """Used to mark settings that should be set in the local environment.

    If a default value isn't specified, the local setting must be set.
    Generally, local settings with no default value should not be stored
    in version control.

    If a local setting doesn't have a default value, it will be prompted
    for by default. Pass ``prompt=False`` to disable this (or use
    :class:`.SecretSetting`).

    """

    def __init__(self, default=NO_DEFAULT, prompt=True, doc=None, validator=None):
        self.default = default
        self.derived_default = NO_DEFAULT
        if default is not NO_DEFAULT:
            if isinstance(default, LocalSetting):
                self.derived_default = default
            else:
                if callable(default):
                    default = default()
                try:
                    json.dumps(default)
                except TypeError as exc:
                    msg = (
                        '{exc}\nDefault value for LocalSetting must be JSON '
                        'serializable'.format(exc=exc))
                    raise TypeError(msg)
        self.prompt = prompt
        self.doc = doc
        self.validator = validator
        self._value = NO_DEFAULT

    @property
    def has_default(self):
        return self._get_default() is not NO_DEFAULT

    @property
    def has_value(self):
        return self._value is not NO_DEFAULT or self.has_default

    def _get_default(self):
        if self.derived_default:
            default = self.derived_default.value
        else:
            default = self._default
            if callable(default):
                default = default()
        return default

    @property
    def default(self):
        default = self._get_default()
        if default is NO_DEFAULT:
            raise NoDefaultError('Local setting has no default value')
        return default

    @default.setter
    def default(self, default):
        self._default = default

    @property
    def value(self):
        value = self._value
        if value is NO_DEFAULT:
            value = self._get_default()
        if value is NO_DEFAULT:
            raise NoValueError('Local setting has no value')
        return value

    @value.setter
    def value(self, value):
        if not self.validate(value):
            raise ValueError('`{0}` is not a valid value'.format(value))
        self._value = value

    def validate(self, v):
        if self.validator:
            return self.validator(v)
        return True

    def __str__(self):
        try:
            default = repr(self.default)
        except NoDefaultError:
            default = '[NO DEFAULT VALUE]'
        try:
            value = repr(self.value)
        except NoValueError:
            value = '[NO VALUE SET]'
        s = '<{0.__class__.__name__} with default `{default}` and value `{value}`>'
        s = s.format(self, default=default, value=value)
        return s


class SecretSetting(LocalSetting):

    """Used to mark secret settings.

    Secret settings have no default and should never be stored in
    version control. They will always be prompted for if not present in
    the local settings file.

    """

    def __init__(self, doc=None, validator=None):
        super(SecretSetting, self).__init__(NO_DEFAULT, True, doc, validator)
