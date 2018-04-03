from .exc import StrategyError
from .strategy import guess_strategy_type
from .util import parse_file_name_and_section


class Base(object):

    def __init__(self, file_name, section=None, registry=None, strategy_type=None):
        original_file_name = file_name
        file_name, section = parse_file_name_and_section(file_name, section)
        if strategy_type is None:
            strategy_type = guess_strategy_type(file_name)
            if strategy_type is None:
                raise StrategyError(
                    'No strategy type was specified and no strategy corresponds to the specified '
                    'settings file: {original_file_name}'.format(**locals()))
        self.original_file_name = original_file_name
        self.file_name = file_name
        self.section = section
        # Registry of local settings with a value in the settings file
        self.registry = {} if registry is None else registry
        self.strategy_type = strategy_type
        self.strategy = strategy_type()
