import types


__all__ = ["JSONObject"]


class JSONObject(types.SimpleNamespace):
    """A simple bucket of attributes.

    JSON objects will be converted to this type by default.

    .. note:: In cases where you generally need/want to work with dicts,
        .pass ``None`` as the ``object_converter`` to :func:`decode`,
        .:class:`Scanner`, etc.

    Items can be accessed via dotted or bracket notation::

        >>> obj = JSONObject(x=1)
        >>> obj.x
        1
        >>> obj["x"]
        1

    An object can be converted to a dict by calling `dict` on it::

        >>> obj = JSONObject(x=1)
        >>> dict(obj)
        {'x': 1}

    """

    def __getitem__(self, name):
        return self.__dict__.__getitem__(name)

    def __setitem__(self, name, value):
        self.__dict__[name] = value

    def __iter__(self):
        return iter(self.__dict__.items())
