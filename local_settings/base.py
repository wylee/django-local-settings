class Base(object):

    def __init__(self, file_name, section=None, registry=None, strategy_type=None):
        strategy = strategy_type()
        file_name, section = strategy.parse_file_name_and_section(file_name, section)
        self.file_name = file_name
        self.section = section
        # Registry of local settings with a value in the settings file
        self.registry = {} if registry is None else registry
        self.strategy_type = strategy_type
        self.strategy = strategy
