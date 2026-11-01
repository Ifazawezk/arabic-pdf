"""Command line interface.

    arpdf report.pdf                       text to stdout
    arpdf report.pdf -o report.md          format follows the extension
    arpdf report.pdf -f json -p 1-3,7      chosen pages as JSON
    arpdf scans/ -o out/ -f markdown       a whole folder
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import pymupdf

from .document import Document
from .extract import OCR_MODES, extract
from .ocr import DEFAULT_DPI, DEFAULT_LANGUAGE
from .render import to_json, to_markdown, to_text

RENDERERS = {"text": to_text, "markdown": to_markdown, "json": to_json}
EXTENSIONS = {"text": ".txt", "markdown": ".md", "json": ".json"}
FORMAT_OF_SUFFIX = {".txt": "text", ".md": "markdown", ".markdown": "markdown", ".json": "json"}


def parse_pages(spec: str) -> list[int]:
    """Turn "1-3,7" into [1, 2, 3, 7]."""
    pages: set[int] = set()
    for part in spec.split(","):
        first, dash, last = part.strip().partition("-")
        try:
            start = int(first)
            end = int(last) if dash else start
        except ValueError:
            raise argparse.ArgumentTypeError(f"bad page range: {part.strip()!r}") from None
        if start < 1 or end < start:
            raise argparse.ArgumentTypeError(f"bad page range: {part.strip()!r}")
        pages.update(range(start, end + 1))
    return sorted(pages)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arpdf", description="Extract clean Unicode text and Markdown from Arabic and mixed PDFs."
    )
    parser.add_argument("input", nargs="+", help="PDF files or folders")
    parser.add_argument("-o", "--output", help="output file, or output folder for several inputs (default: stdout)")
    parser.add_argument("-f", "--format", choices=sorted(RENDERERS),
                        help="output format (default: from the -o extension, otherwise text)")
    parser.add_argument("-p", "--pages", type=parse_pages, help='pages to read, for example "1-3,7"')
    parser.add_argument("-r", "--recursive", action="store_true", help="search folders recursively")
    parser.add_argument("--ocr", choices=OCR_MODES, default="auto", help="when to run OCR (default: auto)")
    parser.add_argument("--ocr-lang", default=DEFAULT_LANGUAGE, help=f"Tesseract languages (default: {DEFAULT_LANGUAGE})")
    parser.add_argument("--ocr-dpi", type=int, default=DEFAULT_DPI, help=f"OCR resolution (default: {DEFAULT_DPI})")
    parser.add_argument("--keep-headers", action="store_true", help="keep repeated headers, footers and page numbers")
    parser.add_argument("--no-tables", action="store_true", help="read tables as plain text")
    return parser


def find_inputs(inputs: list[str], recursive: bool) -> tuple[list[Path], list[Path]]:
    """Input PDFs, and the top folders that were given (which means batch mode)."""
    files: list[Path] = []
    folders: list[Path] = []
    for item in inputs:
        path = Path(item)
        if path.is_dir():
            folders.append(path)
            pattern = "**/*" if recursive else "*"
            files.extend(sorted(p for p in path.glob(pattern) if p.is_file() and p.suffix.lower() == ".pdf"))
        else:
            files.append(path)
    return files, folders


def output_path(source: Path, folders: list[Path], out_dir: Path | None, suffix: str) -> Path:
    """Where a batch result goes. Subfolders are kept so equal file names cannot collide."""
    if out_dir is None:
        return source.with_suffix(suffix)
    for folder in folders:
        if source.is_relative_to(folder):
            return (out_dir / source.relative_to(folder)).with_suffix(suffix)
    return out_dir / (source.stem + suffix)


def report_problems(source: Path, document: Document) -> None:
    missing = [p.number for p in document.pages if p.needs_ocr]
    if missing:
        print(f"{source}: no text on page(s) {missing}: OCR is off or its language data is missing "
              "(see the OCR section of the README)", file=sys.stderr)
    unmapped = sum(p.unmapped_glyphs for p in document.pages if not p.ocr)
    if unmapped:
        print(f"{source}: {unmapped} glyph(s) have no Unicode mapping and appear as U+FFFD", file=sys.stderr)


def run_one(source: Path, args: argparse.Namespace) -> Document:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # report_problems() words these for the command line
        return extract(
            source, pages=args.pages, keep_running_text=args.keep_headers, tables=not args.no_tables,
            ocr=args.ocr, ocr_language=args.ocr_lang, ocr_dpi=args.ocr_dpi,
        )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # MuPDF prints warnings to stdout by default, which would end up in the output
    pymupdf.set_messages(stream=sys.stderr)
    pymupdf.set_log(stream=sys.stderr)
    pymupdf.TOOLS.mupdf_display_errors(False)

    files, folders = find_inputs(args.input, args.recursive)
    if not files:
        print("no PDF files found", file=sys.stderr)
        return 1
    batch = bool(folders) or len(files) > 1
    target = Path(args.output) if args.output else None
    if batch and target is not None and target.suffix.lower() in FORMAT_OF_SUFFIX:
        parser.error("several inputs need an output folder, not a file")

    fmt = args.format
    if fmt is None and target is not None and not batch:
        fmt = FORMAT_OF_SUFFIX.get(target.suffix.lower())
    fmt = fmt or "text"

    failed = 0
    if batch or target is None:
        sys.stdout.reconfigure(encoding="utf-8")
    for source in files:
        try:
            document = run_one(source, args)
        except Exception as exc:  # one bad file must not stop a batch
            print(f"{source}: failed: {exc}", file=sys.stderr)
            failed += 1
            continue
        report_problems(source, document)
        text = RENDERERS[fmt](document)
        if batch:
            path = output_path(source, folders, target, EXTENSIONS[fmt])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text + "\n", encoding="utf-8", newline="\n")
            print(f"{source} -> {path}")
        elif target is not None:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text + "\n", encoding="utf-8", newline="\n")
        else:
            sys.stdout.write(text + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
