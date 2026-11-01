"""Text extraction entry points."""

from __future__ import annotations

import pymupdf

from .normalize import fold, uses_non_arabic_letters


def extract_text(path: str) -> str:
    """Return the text of every page, pages separated by a blank line."""
    with pymupdf.open(path) as doc:
        pages = []
        for page in doc:
            text = page.get_text()
            pages.append(fold(text, arabic_variants=not uses_non_arabic_letters(text)).strip())
    return "\n\n".join(pages)
