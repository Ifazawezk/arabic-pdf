"""Command line interface: ``arpdf file.pdf -o out.md``."""

from __future__ import annotations

import argparse
import sys

import pymupdf

from .extract import extract
from .render import to_markdown, to_text

FORMATS = {"text": to_text, "markdown": to_markdown}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="arpdf", description="Extract clean text from Arabic PDFs.")
    parser.add_argument("pdf", help="input PDF file")
    parser.add_argument("-o", "--output", help="output file (default: stdout)")
    parser.add_argument("-f", "--format", choices=sorted(FORMATS), default="text")
    args = parser.parse_args(argv)

    # MuPDF prints warnings to stdout by default, which would end up in the output
    pymupdf.set_messages(stream=sys.stderr)
    pymupdf.set_log(stream=sys.stderr)

    text = FORMATS[args.format](extract(args.pdf))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
