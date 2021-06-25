# flake8: noqa

from .exc import DecodeError

# Decode from JSON to Python
from .decoder import (
    decode,
    decode as loads,
    decode_file,
    decode_file as load,
    Decoder,
)

# Encode from Python to JSON
from .encoder import (
    encode,
    encode as dumps,
    encode_to_file,
    encode_to_file as dump,
    Encoder,
)
