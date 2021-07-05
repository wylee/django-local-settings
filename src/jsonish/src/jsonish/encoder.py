"""JSONish Encoder

For now, this just passes through to the stdlib `json` module.

"""
import json


__all__ = ["encode", "encode_to_file", "Encoder"]


encode = json.dumps
encode_to_file = json.dump
Encoder = json.JSONEncoder
