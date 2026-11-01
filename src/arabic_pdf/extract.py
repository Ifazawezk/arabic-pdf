"""Text extraction entry points."""

from __future__ import annotations

import pymupdf

from .glyphs import read_glyphs
from .layout import is_rtl, page_lines
from .normalize import uses_non_arabic_letters


def page_text(page: pymupdf.Page) -> str:
    glyphs = read_glyphs(page)
    if not glyphs:
        return ""
    page_rtl = is_rtl(glyphs)
    arabic_variants = not uses_non_arabic_letters("".join(g.text for g in glyphs))
    return "\n".join(line.text for line in page_lines(glyphs, page_rtl, arabic_variants))


def extract_text(path: str) -> str:
    """Return the text of every page, pages separated by a blank line."""
    with pymupdf.open(path) as doc:
        pages = [page_text(page) for page in doc]
    return "\n\n".join(p for p in pages if p)
