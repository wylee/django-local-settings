"""JSONish Encoder

This passes through to the stdlib `json` module with handling of
:class:`JSONObject` and :class:`datetime.datetime` values.

"""
import datetime
import json

from .obj import JSONObject


__all__ = ["encode", "encode_to_file", "Encoder"]


class Encoder(json.JSONEncoder):
    def __init__(
        self,
        *,
        skipkeys=False,
        ensure_ascii=True,
        check_circular=True,
        allow_nan=True,
        sort_keys=False,
        indent=None,
        separators=None,
        default=None,
        enable_extras=True,
    ):
        super().__init__(
            skipkeys=skipkeys,
            ensure_ascii=ensure_ascii,
            check_circular=check_circular,
            allow_nan=allow_nan,
            sort_keys=sort_keys,
            indent=indent,
            separators=separators,
            default=default,
        )
        self.enable_extras = enable_extras

    def jsonish_default(self, obj):
        if self.enable_extras:
            if isinstance(obj, JSONObject):
                return dict(obj)
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
        # Raise TypeError
        return super().default(obj)


def encode(
    obj,
    *,
    cls=Encoder,
    skipkeys=False,
    ensure_ascii=True,
    check_circular=True,
    allow_nan=True,
    sort_keys=False,
    indent=None,
    separators=None,
    default=None,
    enable_extras=True,
):
    instance = cls(
        skipkeys=skipkeys,
        ensure_ascii=ensure_ascii,
        check_circular=check_circular,
        allow_nan=allow_nan,
        sort_keys=sort_keys,
        indent=indent,
        separators=separators,
        default=default,
        enable_extras=enable_extras,
    )
    return instance.encode(obj)


def encode_to_file(
    obj,
    fp,
    *,
    cls=Encoder,
    skipkeys=False,
    ensure_ascii=True,
    check_circular=True,
    allow_nan=True,
    sort_keys=False,
    indent=None,
    separators=None,
    default=None,
    enable_extras=True,
):
    instance = cls(
        skipkeys=skipkeys,
        ensure_ascii=ensure_ascii,
        check_circular=check_circular,
        allow_nan=allow_nan,
        sort_keys=sort_keys,
        indent=indent,
        separators=separators,
        default=default,
        enable_extras=enable_extras,
    )
    iterable = instance.iterencode(obj)
    for chunk in iterable:
        fp.write(chunk)
