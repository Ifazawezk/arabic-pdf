"""Text extraction entry points."""

from __future__ import annotations

import pymupdf


def extract_text(path: str) -> str:
    """Return the text of every page, pages separated by a blank line."""
    with pymupdf.open(path) as doc:
        pages = [page.get_text() for page in doc]
    return "\n\n".join(p.strip() for p in pages)
