"""Extraction entry points."""

from __future__ import annotations

import os
import statistics
from dataclasses import dataclass

import pymupdf

from . import ocr as ocr_engine
from .blocks import mark_headings, page_blocks
from .document import Block, Document, Page
from .glyphs import Glyph, attach_marks, learn_ligatures, read_glyphs, remove_duplicates, unrotate_rect
from .layout import Line, is_rtl, page_lines, page_needs_mirroring, remove_running_text, table_line
from .normalize import uses_non_arabic_letters
from .render import to_markdown, to_text
from .tables import TableGrid, find_grids, read_table, rotate_grid, split_table_glyphs

OCR_MODES = ("auto", "always", "never")


@dataclass
class _Frame:
    """Text of one orientation on a page, with its own direction and settings."""

    quarter: int
    lines: list[Line]
    rtl: bool
    arabic_variants: bool
    size: int  # number of glyphs, the largest frame is read first


@dataclass
class _PageRead:
    page: pymupdf.Page
    frames: list[_Frame]
    ocr: bool = False
    needs_ocr: bool = False
    unmapped: int = 0


def _page_glyphs(page: pymupdf.Page, mode: str, language: str, dpi: int,
                 ligatures: dict) -> tuple[list[Glyph], bool, bool]:
    """Glyphs from the text layer or from OCR, whether OCR ran, and whether it should have."""
    glyphs = attach_marks(remove_duplicates(read_glyphs(page, ligatures=ligatures)))
    wanted = ocr_engine.needs_ocr(page, glyphs)
    if mode == "always" or (mode == "auto" and wanted):
        result = ocr_engine.ocr_glyphs(page, language, dpi)
        if result is not None:
            return attach_marks(result), True, False
    return glyphs, False, wanted


def read_frame(glyphs: list[Glyph], quarter: int, grids: list[TableGrid], width: float, height: float) -> _Frame:
    """Layout for the text of one orientation."""
    rtl = is_rtl(glyphs)
    variants = not uses_non_arabic_letters("".join(g.text for g in glyphs))
    mirror = page_needs_mirroring(glyphs, rtl)
    turned = [rotate_grid(grid, quarter, width, height) for grid in grids]
    flow, table_glyphs = split_table_glyphs(glyphs, turned)
    entries = []
    for grid, inside in zip(turned, table_glyphs):
        if not any(not g.is_space for g in inside):
            continue  # a drawn frame, or a table of another orientation
        rows, table_rtl = read_table(grid, inside, rtl, variants, mirror)
        entries.append(table_line(grid.bbox, rows, statistics.median(g.size for g in inside), table_rtl))
    return _Frame(quarter, page_lines(flow, rtl, variants, entries, mirror), rtl, variants, len(glyphs))


def read_page(page: pymupdf.Page, tables: bool, mode: str, language: str, dpi: int,
              ligatures: dict | None = None) -> _PageRead:
    """Lines of one page in reading order, one frame for each text orientation."""
    glyphs, used_ocr, flagged = _page_glyphs(page, mode, language, dpi, ligatures or {})
    if not glyphs:
        return _PageRead(page, [], needs_ocr=flagged)
    grids = find_grids(page) if tables else []
    width, height = page.rect.width, page.rect.height
    frames = [read_frame([g for g in glyphs if g.quarter == quarter], quarter, grids, width, height)
              for quarter in sorted({g.quarter for g in glyphs})]
    frames.sort(key=lambda f: f.size, reverse=True)
    return _PageRead(page, frames, used_ocr, flagged, sum(ocr_engine.is_unmapped(g.text) for g in glyphs))


def frame_blocks(frame: _Frame, lines: list[Line], page: pymupdf.Page) -> list[Block]:
    blocks = page_blocks(lines, frame.rtl, frame.arabic_variants)
    if frame.quarter:
        for block in blocks:
            block.bbox = unrotate_rect(block.bbox, frame.quarter, page.rect.width, page.rect.height)
            block.rotation = frame.quarter * 90
    return blocks


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
        ligatures = learn_ligatures(pdf)
        reads = [read_page(pdf[n], tables, ocr, ocr_language, ocr_dpi, ligatures) for n in numbers]
        # margins only mean something for upright text
        upright = [next((f for f in r.frames if f.quarter == 0), None) for r in reads]
        lines = [f.lines if f else [] for f in upright]
        if not keep_running_text:
            lines = remove_running_text(lines, [r.page.rect.height for r in reads])
        for read, frame, kept in zip(reads, upright, lines):
            if frame:
                frame.lines = kept
            page = read.page
            document.pages.append(Page(
                number=page.number + 1, width=page.rect.width, height=page.rect.height,
                blocks=[b for f in read.frames for b in frame_blocks(f, f.lines, page)],
                rtl=read.frames[0].rtl if read.frames else True, ocr=read.ocr,
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
