# flake8: noqa

# Decode from JSON to Python
from .decoder import (
    decode,
    decode as loads,
    decode_file,
    decode_file as load,
)

# Encode from Python to JSON
from .encoder import (
    encode,
    encode as dumps,
    encode_to_file,
    encode_to_file as dump,
)

from .exc import DecodeError
