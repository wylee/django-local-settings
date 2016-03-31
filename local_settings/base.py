import os

from .exc import SettingsFileNotFoundError


class Base:

    def __init__(self, file_name, section=None, registry=None, strategy_type=None,
                 check_exists=True):
        strategy = strategy_type()
        file_name, section = strategy.parse_file_name_and_section(file_name, section)
        if check_exists and not os.path.exists(file_name):
            raise SettingsFileNotFoundError(file_name)
        self.file_name = file_name
        self.section = section
        # Registry of local settings with a value in the settings file
        self.registry = {} if registry is None else registry
        self.strategy_type = strategy_type
        self.strategy = strategy
