class DecodeError(ValueError):
    def __init__(self, string, position, message):
        line = string.count("\n", 0, position) + 1
        column = position - string.rfind("\n", 0, position)
        super_message = (
            f"{message} at line {line} column {column} (position {position})"
        )
        super().__init__(super_message)
        self.string = string
        self.message = message
        self.position = position
        self.line = line
        self.column = column


class ExpectedBracket(DecodeError):
    def __init__(self, string, position, bracket, message=None):
        if message is None:
            message = f"Expected bracket `{bracket}`"
        super().__init__(string, position, message)
        self.bracket = bracket


class ExpectedDelimiter(DecodeError):
    def __init__(self, string, position, delimiter, message=None):
        if message is None:
            message = f"Expected delimiter `{delimiter}`"
        super().__init__(string, position, message)
        self.delimiter = delimiter


class ExpectedKey(DecodeError):
    def __init__(self, string, position, message="Expected key"):
        super().__init__(string, position, message)


class ExpectedValue(DecodeError):
    def __init__(self, string, position, message="Expected value"):
        super().__init__(string, position, message)


class ExtraneousData(DecodeError):
    def __init__(
        self,
        string,
        position,
        message="Extraneous data (likely indicating a malformed JSON document)",
    ):
        super().__init__(string, position, message)


class UnexpectedToken(DecodeError):
    def __init__(self, string, position, token, message=None):
        if message is None:
            message = f"Unexpected token `{token}`"
        super().__init__(string, position, message)
        self.token = token


class UnknownToken(DecodeError):
    def __init__(self, string, position, token, message=None):
        if message is None:
            message = f"Unknown token `{token}`"
        super().__init__(string, position, message)
        self.token = token


class UnmatchedBracket(DecodeError):
    def __init__(self, string, bracket, position, message=None):
        if message is None:
            message = f"Unmatched bracket `{bracket}`"
        super().__init__(string, position, message)
        self.bracket = bracket
