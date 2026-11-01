"""Extraction entry points."""

from __future__ import annotations

import os
import statistics
from dataclasses import dataclass

import pymupdf

from . import ocr as ocr_engine
from .blocks import mark_headings, page_blocks
from .document import Document, Page
from .glyphs import Glyph, attach_marks, read_glyphs, remove_duplicates
from .layout import Line, is_rtl, page_lines, page_needs_mirroring, remove_running_text, table_line
from .normalize import uses_non_arabic_letters
from .render import to_markdown, to_text
from .tables import find_grids, read_table, split_table_glyphs

OCR_MODES = ("auto", "always", "never")


@dataclass
class _PageRead:
    page: pymupdf.Page
    lines: list[Line]
    rtl: bool = True
    arabic_variants: bool = True
    ocr: bool = False
    needs_ocr: bool = False
    unmapped: int = 0


def _page_glyphs(page: pymupdf.Page, mode: str, language: str, dpi: int) -> tuple[list[Glyph], bool, bool]:
    """Glyphs from the text layer or from OCR, whether OCR ran, and whether it should have."""
    glyphs = attach_marks(remove_duplicates(read_glyphs(page)))
    wanted = ocr_engine.needs_ocr(page, glyphs)
    if mode == "always" or (mode == "auto" and wanted):
        result = ocr_engine.ocr_glyphs(page, language, dpi)
        if result is not None:
            return attach_marks(result), True, False
    return glyphs, False, wanted


def read_page(page: pymupdf.Page, tables: bool, mode: str, language: str, dpi: int) -> _PageRead:
    """Lines of one page in reading order, with what we learned about the page."""
    glyphs, used_ocr, flagged = _page_glyphs(page, mode, language, dpi)
    if not glyphs:
        return _PageRead(page, [], needs_ocr=flagged)
    rtl = is_rtl(glyphs)
    variants = not uses_non_arabic_letters("".join(g.text for g in glyphs))
    mirror = page_needs_mirroring(glyphs, rtl)
    grids = find_grids(page) if tables else []
    flow, table_glyphs = split_table_glyphs(glyphs, grids)
    entries = []
    for grid, inside in zip(grids, table_glyphs):
        rows, table_rtl = read_table(grid, inside, rtl, variants, mirror)
        size = statistics.median(g.size for g in inside) if inside else 0.0
        entries.append(table_line(grid.bbox, rows, size, table_rtl))
    return _PageRead(page, page_lines(flow, rtl, variants, entries, mirror), rtl, variants, used_ocr, flagged,
                     sum(ocr_engine.is_unmapped(g.text) for g in glyphs))


def extract(
    path: str | os.PathLike,
    pages: list[int] | None = None,
    keep_running_text: bool = False,
    tables: bool = True,
    ocr: str = "auto",
    ocr_language: str = ocr_engine.DEFAULT_LANGUAGE,
    ocr_dpi: int = ocr_engine.DEFAULT_DPI,
) -> Document:
    """Read a PDF into a Document of pages and blocks.

    ``pages`` holds 1 based page numbers; numbers past the end are ignored.
    ``ocr`` is "auto" (scanned pages only), "always" or "never". Pages that
    need OCR when it is off or unavailable come back empty with ``needs_ocr`` set.
    """
    if ocr not in OCR_MODES:
        raise ValueError(f"ocr must be one of {OCR_MODES}")
    document = Document(source=os.fspath(path))
    with pymupdf.open(path) as pdf:
        if pdf.needs_pass:
            raise ValueError(f"{path} is password protected")
        numbers = range(pdf.page_count) if pages is None else [n - 1 for n in pages if n <= pdf.page_count]
        reads = [read_page(pdf[n], tables, ocr, ocr_language, ocr_dpi) for n in numbers]
        all_lines = [r.lines for r in reads]
        if not keep_running_text:
            all_lines = remove_running_text(all_lines, [r.page.rect.height for r in reads])
        for read, lines in zip(reads, all_lines):
            document.pages.append(Page(
                number=read.page.number + 1, width=read.page.rect.width, height=read.page.rect.height,
                blocks=page_blocks(lines, read.rtl, read.arabic_variants), rtl=read.rtl, ocr=read.ocr,
                needs_ocr=read.needs_ocr, unmapped_glyphs=read.unmapped,
            ))
    mark_headings(document)
    return document


def extract_text(path: str | os.PathLike, **options) -> str:
    """Plain text: blocks separated by blank lines."""
    return to_text(extract(path, **options))


def extract_markdown(path: str | os.PathLike, **options) -> str:
    """Markdown with headings and tables."""
    return to_markdown(extract(path, **options))
