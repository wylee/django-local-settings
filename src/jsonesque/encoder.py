"""JSONesque Encoder

For now, this just passes through to the stdlib
:class:`json.JSONEncoder` and :func:`json.dumps`.

"""
import json


encode = json.dumps
