"""Text extraction entry points."""

from __future__ import annotations

import pymupdf

from .glyphs import attach_marks, read_glyphs, remove_duplicates
from .layout import Line, is_rtl, page_lines, remove_running_text
from .normalize import uses_non_arabic_letters


def read_page(page: pymupdf.Page) -> list[Line]:
    glyphs = attach_marks(remove_duplicates(read_glyphs(page)))
    if not glyphs:
        return []
    page_rtl = is_rtl(glyphs)
    arabic_variants = not uses_non_arabic_letters("".join(g.text for g in glyphs))
    return page_lines(glyphs, page_rtl, arabic_variants)


def extract_text(path: str, keep_running_text: bool = False) -> str:
    """Return the text of every page, pages separated by a blank line."""
    with pymupdf.open(path) as doc:
        pages = [read_page(page) for page in doc]
        heights = [page.rect.height for page in doc]
    if not keep_running_text:
        pages = remove_running_text(pages, heights)
    texts = ["\n".join(line.text for line in lines) for lines in pages]
    return "\n\n".join(t for t in texts if t)
