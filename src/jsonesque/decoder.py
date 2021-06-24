"""JSONesque Decoder

In addition to standard JSON, the JSONesque decoder also supports/
handles the following:

- *All* scanning methods can be overridden if some additional
  customization is required
- An object converter can be specified to convert plain Python dicts
  parsed from JSON into specialized objects; by default, objects will
  be converted to :class:`scanner.JSONObject`, which allows items to be
  accessed with either dotted or bracket notation
- A fallback scanner method can be provided to handle additional types
  of values
- Trailing commas
- Line comments starting with //
- Any valid Python int or float:
  - Literal binary, octal, and hex values
  - Underscore separators in numbers
  - Unary plus operator
- Literal (unquoted) dates & times:
  - 2021-06
  - 2021-06-23
  - 2021-06-23T12:00
  - 2021-06-23T12:00Z
  - 2021-06-23T12:00-07:00
  - 12:00 (today's date at noon)

.. note:: For dates and times, when a time zone isn't specified, the
    local time zone will be used.

Examples::

    >>> decode("+1")
    1
    >>> decode("1_000")
    1000
    >>> decode("[0b11]")
    [3]
    >>> d = decode("2021-06-24")
    >>> d.timetuple()[:5]
    (2021, 6, 24, 0, 0)
    >>> d.tzinfo
    tzlocal()
    >>> decode(" [1, 2 ,  3  ,   ] ")
    [1, 2, 3]
    >>> decode("[[]]")
    [[]]

"""
from typing import Any, Callable, Optional, Tuple, Union

from . import scanner
from .exc import ExtraneousData


def decode(
    string: str,
    *,
    strict: bool = True,
    scan_object: Callable = scanner.scan_object,
    object_converter: Callable = scanner.JSONObject,
    scan_array: Callable = scanner.scan_array,
    scan_string: Callable = scanner.scan_string,
    scan_date: Callable = scanner.scan_date,
    scan_number: Callable = scanner.scan_number,
    fallback_scanner: Optional[Callable] = None,
    disable_extras: bool = False,
    ignore_extra_data: bool = False,
) -> Union[Any, Tuple[Any, int]]:
    """Scan JSONesque string and return a Python object.

    The type of the object is determined by the ``object_converter``
    callable. By default, JSON objects are converted to simple Python
    namespace objects that allow attributes to be accessed via dotted or
    bracket notation. These objects can be converted to plain dicts with
    ``dict(obj)`` or you can use ``object_converter=None`` to get back a
    plain dicts.

    A different object converter can be passed to customize object
    creation, perhaps based on a type field::

        def converter(obj):
            if "__type__" in obj:
                # Convert to type based on __type__
                ...
            # Don't convert since no type was specified
            return obj

    When errors are encountered, various kinds of exceptions are
    thrown. These all derive from :class:`DecodeError`, which in turn
    derives from the builtin :class:`ValueError`.

    Examples::

        >>> import arrow, math

        >>> decode("") is None
        True

        >>> d = decode("2021-06-23")
        >>> d.timetuple()[:5]
        (2021, 6, 23, 0, 0)

        >>> t = arrow.now()
        >>> d = decode("12:00")
        >>> d.timetuple()[:5] == (t.year, t.month, t.day, 12, 0)
        True

        >>> d = decode("2021-06-23T12:00")
        >>> d.timetuple()[:6]
        (2021, 6, 23, 12, 0, 0)

        >>> decode("[inf, nan]")
        [inf, nan]

        >>> decode("E") == math.e
        True
        >>> (decode("π"), decode("PI")) == (math.pi, math.pi)
        True
        >>> (decode("τ"), decode("TAU")) == (math.tau, math.tau)
        True

        >>> decode("0"), decode("+0"), decode("-0"), decode("000")
        (0, 0, 0, 0)
        >>> decode("1"), decode("+1"), decode("-1")
        (1, 1, -1)

        >>> decode("1.0"), decode("+1.0"), decode("-1.0")
        (1.0, 1.0, -1.0)

        >>> decode("0b11"), decode("0o11"), decode("0x11")
        (3, 9, 17)

        >>> decode("{}", object_converter=None), decode("[]")
        ({}, [])

        >>> decode("[0b11, 11, 0x11]")
        [3, 11, 17]

    When the ``ignore_extra_data`` flag is set, a tuple will be
    returned containing 1) a Python object representing the part of the
    JSON string that was successfully parsed and 2) the index in the
    JSON string where the extra data starts. In most cases, extra data
    indicates an error, but this functionality can be used intentionally
    include extra data:

        >>> decode('{} # ignored', object_converter=None, ignore_extra_data=True)
        ({}, 3)

    An advanced/esoteric feature for use where additional customization
    is required is the ``fallback_scanner``. This is a callable that
    accepts a :class:`Scanner` instance, the JSON string, and the
    current index/position and returns a Python value along with the
    next index/position in the JSON string. See the scanners in
    :mod:`jsonesque.scanner` for examples.

    """
    instance = scanner.Scanner(
        strict=strict,
        scan_object=scan_object,
        object_converter=object_converter,
        scan_array=scan_array,
        scan_string=scan_string,
        scan_date=scan_date,
        scan_number=scan_number,
        disable_extras=disable_extras,
        fallback_scanner=fallback_scanner,
    )
    obj, i = instance.scan(string)
    if ignore_extra_data:
        return obj, i
    elif i != len(string):
        raise ExtraneousData(string, i)
    return obj
