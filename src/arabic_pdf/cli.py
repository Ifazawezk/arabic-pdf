"""Command line interface: ``arpdf file.pdf -o out.txt``."""

from __future__ import annotations

import argparse
import sys

from .extract import extract_text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="arpdf", description="Extract clean text from Arabic PDFs.")
    parser.add_argument("pdf", help="input PDF file")
    parser.add_argument("-o", "--output", help="output file (default: stdout)")
    args = parser.parse_args(argv)

    text = extract_text(args.pdf)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
