"""JSONesque Encoder

For now, this just passes through to the stdlib :func:`json.dump` and
:func:`dumps`.

"""
import json


encode = json.dumps
encode_to_file = json.dump
