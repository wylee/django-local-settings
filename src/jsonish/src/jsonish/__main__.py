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

    args = parser.parse_args(argv)

    if args.json:
        obj = decode(args.json, ini=args.ini)
    elif args.file:
        obj = decode_file(args.file, ini=args.ini)

    if args.out_file:
        path = pathlib.Path(args.out_file)
        with path.open("w") as fp:
            encode_to_file(obj, fp, indent=args.indent)
    else:
        print(encode(obj, indent=args.indent))


if __name__ == "__main__":
    sys.exit(sys.argv)
