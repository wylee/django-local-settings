class LocalSettingsError(Exception):

    pass


class NoDefaultError(LocalSettingsError):

    pass


class NoValueError(LocalSettingsError):

    pass
