import argparse
import pathlib
import sys

from .decoder import decode, decode_file
from .encoder import encode, encode_to_file


def main(argv=None):
    parser = argparse.ArgumentParser(prog="jsonish")

    type_group = parser.add_mutually_exclusive_group(required=True)
    type_group.add_argument("-j", "--json", help="JSON string to decode")
    type_group.add_argument("-f", "--file", help="File to decode")

    parser.add_argument(
        "-c",
        "--ini",
        action="store_true",
        default=None,
        help="Force INI+JSON",
    )

    parser.add_argument("-o", "--out-file", help="Write decoded JSON to file")

    parser.add_argument(
        "-i",
        "--indent",
        type=int,
        default=None,
        help="Pretty print with specified indent level",
    )

    parser.add_argument(
        "-d",
        "--disable-extras",
        dest="enable_extras",
        action="store_false",
        default=True,
    )

    args = parser.parse_args(argv)
    json = args.json
    file = args.file
    out_file = args.out_file
    ini = args.ini
    indent = args.indent
    enable_extras = args.enable_extras

    if json:
        obj = decode(json, enable_extras=enable_extras, ini=ini)
    elif file:
        obj = decode_file(file, enable_extras=enable_extras, ini=ini)

    if out_file:
        path = pathlib.Path(out_file)
        with path.open("w") as fp:
            encode_to_file(obj, fp, indent=indent, enable_extras=enable_extras)
    else:
        print(encode(obj, indent=indent, enable_extras=enable_extras))


if __name__ == "__main__":
    sys.exit(sys.argv)
