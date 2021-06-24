import types


class JSONObject(types.SimpleNamespace):
    """A simple bucket of attributes.

    JSON objects will be converted to this type by default.

    .. note:: In cases where you generally need/want to work with dicts,
        pass ``None`` as the ``object_converter`` to :class:`Scanner`
        and/or its callers.

    Items can be accessed via dotted or bracket notation::

        >>> obj = JSONObject(x=1)
        >>> obj.x
        1
        >>> obj["x"]
        1

    Objects can be converted dicts by calling `dict` on them::

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
