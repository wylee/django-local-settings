import json
import json.scanner
import math
import re
from functools import partial

import arrow
import dateutil

from .exc import (
    ExpectedBracket,
    ExpectedDelimiter,
    ExpectedKey,
    ExpectedValue,
    UnexpectedToken,
    UnknownToken,
    UnmatchedBracket,
)
from .obj import JSONObject


WHITESPACE = " \f\n\r\t\v"
WHITESPACE_RE = re.compile(r"[ \f\n\r\t\v]*")


def skip_whitespace(
    string,
    i,
    *,
    comments=True,
    whitespace=WHITESPACE,
    whitespace_re=WHITESPACE_RE,
):
    if string[i : i + 1] in whitespace:
        i = whitespace_re.match(string, i).end()
    if comments and string[i : i + 2] == "//":
        i = string.find("\n", i + 3)
        i = len(string) if i == -1 else i + 1
        return skip_whitespace(string, i, comments=True)
    return i


def scan_object(
    scanner,
    string,
    i,
    *,
    converter=JSONObject,
    disable_extras=False,
    skip_whitespace=skip_whitespace,
):
    if string[i : i + 1] != "{":
        raise ExpectedBracket(string, i, "{")

    strip_comments = not disable_extras

    i += 1
    i = skip_whitespace(string, i, comments=strip_comments)

    if string[i : i + 1] == "}":
        return converter() if converter else {}, i + 1

    obj = {}
    stack = scanner.stack
    stack_pop = scanner.pop
    stack.append(("{", i - 1))

    while True:
        # Key
        if string[i : i + 1] != '"':
            raise ExpectedKey(string, i)

        key, i = scanner.scan(string, i)

        # Delimiting colon, which may be followed by whitespace
        if string[i : i + 1] == ":":
            i += 1
            i = skip_whitespace(string, i, comments=strip_comments)
        else:
            raise ExpectedDelimiter(string, i, ":")

        # Value
        value, i = scanner.scan(string, i)

        # Add entry
        obj[key] = value

        # Comma, which may be followed by whitespace
        if string[i : i + 1] == ",":
            comma_i = i
            i += 1
            i = skip_whitespace(string, i, comments=strip_comments)
        else:
            comma_i = None

        if not string[i : i + 1]:
            break

        # Closing brace
        if string[i : i + 1] == "}":
            if disable_extras and comma_i is not None:
                raise UnexpectedToken(string, comma_i, ",")
            stack_pop(string, "{", "}", i)
            i += 1
            break

    return converter(**obj) if converter else obj, i


def scan_array(
    scanner,
    string,
    i,
    *,
    disable_extras=False,
    skip_whitespace=skip_whitespace,
):
    if string[i : i + 1] != "[":
        raise ExpectedBracket(string, i, "[")

    strip_comments = not disable_extras

    i += 1
    i = skip_whitespace(string, i, comments=strip_comments)

    if string[i : i + 1] == "]":
        return [], i + 1

    array = []
    array_append = array.append
    stack = scanner.stack
    stack_pop = scanner.pop
    stack.append(("[", i - 1))

    while True:
        # Value
        value, i = scanner.scan(string, i)
        array_append(value)

        # Comma, which may be followed by whitespace
        if string[i : i + 1] == ",":
            comma_i = i
            i += 1
            i = skip_whitespace(string, i, comments=strip_comments)
        else:
            comma_i = None

        if not string[i : i + 1]:
            break

        if string[i : i + 1] == "]":
            if disable_extras and comma_i is not None:
                raise UnexpectedToken(string, comma_i, ",")
            stack_pop(string, "[", "]", i)
            i += 1
            break

    return array, i


scan_string = json.decoder.scanstring


# NOTE: To avoid ambiguity with ints, dates must have at least a year
#       and month part and times must have at least a hour and minute
#       part.
YEAR = r"\d\d\d[1-9]"
MONTH = r"0[1-9]|1[1-2]"
DAY = r"[0-2][1-9]|3[0-1]"
HOUR = r"[0-2]\d"
MINUTE = r"[0-5]\d"
SECOND = r"[0-5]\d"
MICROSECOND = r"\d{1,6}"
DATE = rf"{YEAR}-({MONTH})(-({DAY}))?"
TIME_ZONE = rf"Z|[+-]{HOUR}:{MINUTE}"
TIME = rf"{HOUR}:{MINUTE}(:{SECOND}(\.{MICROSECOND})?)?"
DATE_TIME = rf"{DATE}T{TIME}(?P<tz>{TIME_ZONE})?"
# Regex, time only flag
# NOTE: The order of these items matters!
DATETIME_CONVERTERS = (
    (re.compile(DATE_TIME), False),
    (re.compile(DATE), False),
    (re.compile(TIME), True),
)

TZ_LOCAL = dateutil.tz.tzlocal()


def scan_date(
    scanner,
    string,
    i,
    *,
    today,
    converters=DATETIME_CONVERTERS,
    # NOTE: Arrow requires this to be a *list*
    time_formats=["HH:mm", "HH:mm:ss", "HH:mm:ss.S"],
    tz_local=TZ_LOCAL,
):
    for (regex, is_time_only) in converters:
        match: re.Match = regex.match(string, i)
        if match is not None:
            end = match.end()
            str_val = string[i:end]
            if is_time_only:
                try:
                    val = arrow.get(str_val, time_formats)
                except ValueError:
                    raise ValueError(f"Could not convert matched time: {str_val}")
                val = val.replace(
                    year=today.year,
                    month=today.month,
                    day=today.day,
                    tzinfo=today.tzinfo,
                )
            else:
                args = {}
                if "tz" not in match.groupdict():
                    args["tzinfo"] = tz_local
                try:
                    val = arrow.get(str_val, **args)
                except ValueError:
                    raise ValueError(f"Could not convert matched date/time: {str_val}")
            val = val.datetime
            return val, end
    return None


DECIMAL = r"[0-9](_?[0-9]+)*"
FLOAT_WITH_EXP = rf"{DECIMAL}(\.{DECIMAL})?[eE][+-]?{DECIMAL}"
FLOAT_WITHOUT_EXP = rf"{DECIMAL}\.{DECIMAL}"
FLOAT = rf"[+-]?({FLOAT_WITH_EXP}|{FLOAT_WITHOUT_EXP})"

# Regex, converter (const or callable), const flag
# NOTE: The const flag is used to can avoid the function call overhead
#       of checking `callable(converter)`
# NOTE: The order of these items matters!
NUMBER_CONVERTERS = (
    # Constants
    (re.compile(r"([+-])?(inf|Infinity)"), math.inf, True),
    (re.compile(r"([+-])?(nan|NaN)"), math.nan, True),
    (re.compile(r"([+-])?(E)"), math.e, True),
    (re.compile(r"([+-])?(π|PI)"), math.pi, True),
    (re.compile(r"([+-])?(τ|TAU)"), math.tau, True),
    # Floats
    (re.compile(FLOAT), float, False),
    # Integers
    (re.compile(r"[+-]?0[bB]_?[0-1](_?[0-1]+)*"), partial(int, base=2), False),
    (re.compile(r"[+-]?0[oO]_?[0-7](_?[0-7]+)*"), partial(int, base=8), False),
    (re.compile(r"[+-]?0[xX]_?[0-f](_?[0-9a-f]+)*"), partial(int, base=16), False),
    (re.compile(r"[+-]?((0(_?0+)*|[1-9](_?[0-9]+)*))"), int, False),
)


def scan_number(
    scanner,
    string,
    i,
    *,
    converters=NUMBER_CONVERTERS,
):
    for (regex, converter, is_const) in converters:
        match = regex.match(string, i)
        if match is not None:
            end = match.end()
            str_val = string[i:end]
            if is_const:
                pre = match.groups()[0] or "+"
                val = converter if pre == "+" else -converter
            else:
                try:
                    val = converter(str_val)
                except ValueError:
                    raise ValueError(f"Could not convert matched number: {str_val}")
            return val, end
    return None


class Scanner:

    """Scan JSONesque string and return Python object."""

    def __init__(
        self,
        *,
        strict=True,
        scan_object=scan_object,
        object_converter=JSONObject,
        scan_array=scan_array,
        scan_string=scan_string,
        scan_date=scan_date,
        scan_number=scan_number,
        disable_extras=False,
        fallback_scanner=None,
    ):
        self.scan_object = scan_object
        self.object_converter = object_converter
        self.scan_array = scan_array
        self.scan_string = scan_string
        self.scan_date = scan_date
        self.scan_number = scan_number
        self.fallback_scanner = fallback_scanner
        self.disable_extras = disable_extras
        self.strict = strict
        self.stack = []
        # Make sure all bare times use the same today value
        self.today = arrow.now(tz=TZ_LOCAL).floor("day")

    def scan(
        self,
        string,
        i=0,
        *,
        skip_whitespace=skip_whitespace,
        no_val=object(),
        default_scan_number=json.scanner.NUMBER_RE.match,
    ):
        start = i
        strip_comments = not self.disable_extras
        i = skip_whitespace(string, i, comments=strip_comments)

        if not string[i:]:
            if start == 0:
                return None, len(string)
            raise ExpectedValue(string, i)

        val = no_val
        token = string[i]

        if token == "{":
            val, i = self.scan_object(
                self,
                string,
                i,
                converter=self.object_converter,
                disable_extras=self.disable_extras,
            )

        elif token == "[":
            val, i = self.scan_array(
                self,
                string,
                i,
                disable_extras=self.disable_extras,
            )

        elif token == '"':
            val, i = self.scan_string(string, i + 1, self.strict)

        elif token == "n" and string[i : i + 4] == "null":
            val, i = None, i + 4

        elif token == "t" and string[i : i + 4] == "true":
            val, i = True, i + 4

        elif token == "f" and string[i : i + 5] == "false":
            val, i = False, i + 5

        elif not self.disable_extras:
            result = self.scan_date(self, string, i, today=self.today)
            if result is not None:
                val, i = result
            else:
                result = self.scan_number(self, string, i)
                if result is not None:
                    val, i = result
                elif self.fallback_scanner:
                    result = self.fallback_scanner(self, string, i)
                    if result is not None:
                        val, i = result

        else:
            match = default_scan_number(string, i)
            if match is not None:
                integer, fraction, exponent = match.groups()
                if fraction or exponent:
                    val = float(f"{integer}{fraction or ''}{exponent or ''}")
                else:
                    val = int(integer)
                i = match.end()

        if val is no_val:
            raise UnknownToken(string, i, token)

        if start == 0 and token in "{[" and self.stack:
            raise UnmatchedBracket(string, *self.stack[-1])

        i = skip_whitespace(string, i, comments=strip_comments)
        return val, i

    def pop(self, string, left, right, right_i):
        stack = self.stack
        if not stack:
            raise UnmatchedBracket(string, right, right_i)
        top, left_i = stack.pop()
        if top != left:
            raise UnmatchedBracket(string, left, left_i)
