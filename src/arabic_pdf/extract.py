"""Extraction entry points."""

from __future__ import annotations

import os

import pymupdf

from .blocks import mark_headings, page_blocks
from .document import Document, Page
from .glyphs import attach_marks, read_glyphs, remove_duplicates
from .layout import Line, is_rtl, page_lines, remove_running_text
from .normalize import uses_non_arabic_letters
from .render import to_markdown, to_text


def _page_flags(glyphs) -> tuple[bool, bool]:
    return is_rtl(glyphs), not uses_non_arabic_letters("".join(g.text for g in glyphs))


def read_lines(page: pymupdf.Page) -> tuple[list[Line], bool, bool]:
    """Lines in reading order, plus the page direction and the letter variant setting."""
    glyphs = attach_marks(remove_duplicates(read_glyphs(page)))
    if not glyphs:
        return [], True, True
    page_rtl, arabic_variants = _page_flags(glyphs)
    return page_lines(glyphs, page_rtl, arabic_variants), page_rtl, arabic_variants


def extract(path: str | os.PathLike, keep_running_text: bool = False) -> Document:
    """Read a PDF into a Document of pages and blocks."""
    document = Document(source=os.fspath(path))
    with pymupdf.open(path) as pdf:
        pages = [(page, *read_lines(page)) for page in pdf]
        heights = [page.rect.height for page, *_ in pages]
        all_lines = [lines for _, lines, _, _ in pages]
        if not keep_running_text:
            all_lines = remove_running_text(all_lines, heights)
        for (page, _, page_rtl, arabic_variants), lines in zip(pages, all_lines):
            document.pages.append(Page(
                number=page.number + 1, width=page.rect.width, height=page.rect.height, rtl=page_rtl,
                blocks=page_blocks(lines, page_rtl, arabic_variants),
            ))
    mark_headings(document)
    return document


def extract_text(path: str | os.PathLike, **options) -> str:
    """Plain text: blocks separated by blank lines."""
    return to_text(extract(path, **options))


def extract_markdown(path: str | os.PathLike, **options) -> str:
    """Markdown with headings and tables."""
    return to_markdown(extract(path, **options))
