class LocalSettingsError(Exception):

    pass


class StrategyError(LocalSettingsError):

    pass


class SettingsFileNotFoundError(LocalSettingsError):

    pass


class SettingsFileSectionNotFoundError(LocalSettingsError, LookupError):

    pass


class SettingsFileDidNotPassCheck(LocalSettingsError):

    pass


class NoDefaultError(LocalSettingsError):

    pass


class NoValueError(LocalSettingsError):

    pass
