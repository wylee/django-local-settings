"""JSONish Encoder

This passes through to the stdlib `json` module with handling of
:class:`JSONObject` and :class:`datetime.datetime` values.

"""
import datetime
import json
import functools

from .obj import JSONObject


__all__ = ["encode", "encode_to_file", "Encoder"]


def default(obj):
    if isinstance(obj, JSONObject):
        return dict(obj)
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


encode = functools.partial(json.dumps, default=default)
encode_to_file = functools.partial(json.dump, default=default)


class Encoder(json.JSONEncoder):
    def default(self, obj):
        return default(obj)
