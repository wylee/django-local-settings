import json

from .exc import NoDefaultError
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

    def __init__(self, default=NO_DEFAULT, prompt=True, doc=None):
        self.default = default
        self.derived_default = False
        if default is not NO_DEFAULT:
            if isinstance(default, LocalSetting):
                self.derived_default = True
            else:
                try:
                    json.dumps(default)
                except TypeError as exc:
                    msg = (
                        '{exc}\nDefault value for LocalSetting must be JSON '
                        'serializable'.format(exc=exc))
                    raise TypeError(msg)
        self.prompt = prompt
        self.doc = doc
        self.value = NO_DEFAULT

    @property
    def has_default(self):
        return self.default is not NO_DEFAULT

    @property
    def has_value(self):
        return self.value is not NO_DEFAULT

    def get_default(self):
        default = self.default
        if isinstance(default, LocalSetting):
            default = default.value
        if default is NO_DEFAULT:
            raise NoDefaultError('Local setting has no default value')
        return default


class SecretSetting(LocalSetting):

    """Used to mark secret settings.

    Secret settings have no default and should never be stored in
    version control. They will always be prompted for if not present in
    the local settings file.

    """

    def __init__(self, doc=None):
        super(SecretSetting, self).__init__(NO_DEFAULT, True, doc)
