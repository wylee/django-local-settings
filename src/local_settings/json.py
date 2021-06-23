import json

import arrow


class JSONDecoder(json.JSONDecoder):

    """Custom JSON decoder.

    Handles:

    - Trailing commas
    - Binary, octal, and hex values
    - Unary + prefix on ints and floats
    - Underscore separators in numbers
    - Dates & times

    .. note:: Number, date, and time conversions currently only work
        for *non-nested* values. The JSON decoder in the Python standard
        libary isn't easy, or perhaps even possible at all, to convert
        nested values.

    Examples::

        >>> loads = JSONDecoder.loads

        >>> loads('["a", "b", 1,]')
        ['a', 'b', 1]
        >>> loads('""')
        ''
        >>> loads('1')
        1
        >>> loads('"abc"')
        'abc'
        >>> loads("[1, 2, 3]")
        [1, 2, 3]
        >>> loads("[1, 2, 3,]")
        [1, 2, 3]
        >>> loads('{"a": 1, "b": 2}')
        {'a': 1, 'b': 2}
        >>> loads('{"a": 1, "b": 2,}')
        {'a': 1, 'b': 2}
        >>> loads('["\\\\"a", "b",]')
        ['"a', 'b']

        >>> loads("0b11")
        3
        >>> loads("-0b11")
        -3
        >>> loads("0b_1_1")
        3
        >>> loads("0o11")
        9
        >>> loads("-0o11")
        -9
        >>> loads("0x11")
        17
        >>> loads("-0x11")
        -17
        >>> loads("+1")
        1
        >>> loads("-1")
        -1
        >>> loads("1_000_000")
        1000000

        >>> loads("+1e3")
        1000.0
        >>> loads("-1e3")
        -1000.0
        >>> loads("1e-3")
        0.001
        >>> loads("1_000.0")
        1000.0

        >>> d = loads("2021-06-23")
        >>> (d.year, d.month, d.day, d.hour, d.minute) == (2021, 6, 23, 0, 0)
        True

        >>> d = loads("2021-06-23T12:30")
        >>> (d.year, d.month, d.day, d.hour, d.minute) == (2021, 6, 23, 12, 30)
        True

        >>> t = arrow.now()
        >>> d = loads("12:30:00.000000")
        >>> (d.year, d.month, d.day, d.hour, d.minute) == (t.year, t.month, t.day, 12, 30)
        True


    """

    @classmethod
    def loads(cls, s, **kwargs):
        return json.loads(s, cls=cls, **kwargs)

    def decode(self, s):
        try:
            return super().decode(s)
        except ValueError:
            try:
                return self._try_alternative_decodings(s)
            except ValueError:
                message = f"Could not convert string to JSON: {s}"
                raise ValueError(message) from None

    def _try_alternative_decodings(self, s):
        """Try alternative decodings.

        This is used only when the original value wasn't parsed
        successfully as JSON. The following strategies are attempted:

        - If the value appears to be a JSON list or dict, trailing
          commas will be removed and the object will be decoded again;
          if the second attempt fails, the error is propagated
        - The value will be converted to an int if possible by calling
          `int(value, <base>)`
        - The value will be converted to a float if possible by calling
          `float(value)`
        - The value will be converted to a datetime if possible

        .. note:: Currently, the last three strategies only work for
            non-nested values.

        """
        if s[0] in "{[":
            s = self._remove_trailing_commas(s)
            return super().decode(s)

        try:
            return self._try_int(s)
        except ValueError:
            pass

        try:
            return float(s)
        except ValueError:
            pass

        try:
            return arrow.get(s).datetime
        except ValueError:
            pass

        return self._try_time(s)

    def _try_time(self, s):
        """Convert time to a date/time on today's date."""
        formats = ["HH:mm", "HH:mm:ss", "HH:mm:ss.S"]
        for f in formats:
            try:
                time = arrow.get(s, f)
            except ValueError:
                pass
            else:
                value = arrow.now().floor("day")
                value = value.replace(
                    hour=time.hour,
                    minute=time.minute,
                    second=time.second,
                )
                return value.datetime
        raise ValueError(f"Could not parse value as time: {s}")

    def _remove_trailing_commas(self, s):
        """Remove trailing commas from all JSON object and arrays."""
        stack = []
        collector = []
        in_string = False
        pairs = {"{": "}", "[": "]"}
        opening = None
        closing = None

        # Previous non-whitespace index & char
        prev = None, None

        for i, c in enumerate(s):
            if c == '"' and prev[1] != "\\":
                in_string = not in_string
            elif not in_string:
                if c.isspace():
                    collector.append(c)
                    continue
                elif c in pairs:
                    opening = c
                    closing = pairs[c]
                    stack.append(opening)
                elif c == closing:
                    if stack and stack[-1] == opening:
                        stack.pop()
                        if stack:
                            opening = stack[-1]
                            closing = pairs[opening]
                        else:
                            opening = None
                            closing = None
                        prev_i, prev_c = prev
                        if prev_c == ",":
                            collector[prev_i] = None
                    else:
                        raise ValueError(f"Mismatched {closing}")

            collector.append(c)
            prev = i, c

        return "".join(c for c in collector if c)

    def _try_int(self, s, bases={"0b": 2, "0o": 8, "0x": 16}):
        """Try converting value to int.

        Handles binary, octal, and hex values. Also handles + and -
        prefixes (JSON only handles -).

        """
        s = s.lower()
        if s[0] in "+-":
            prefix = s[0]
            s = s[1:]
        else:
            prefix = ""
        base = bases.get(s[:2]) or 10
        return int(f"{prefix}{s}", base)
