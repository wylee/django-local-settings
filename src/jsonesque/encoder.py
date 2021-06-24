"""JSONesque Encoder

For now, this just passes through to the stdlib :func:`json.dumps`.

"""
import json


encode = json.dumps
