"""Small helpers to build glyph lists and PDFs in tests."""

from __future__ import annotations

import arabic_pdf.glyphs as g


def visual_glyphs(visual: str, x: float = 100.0, baseline: float = 100.0, size: float = 12.0, advance: float = 6.0):
    """Glyphs painted left to right from a visual-order string, one glyph per character."""
    out = []
    for ch in visual:
        out.append(g.Glyph(ch, x, baseline - size, x + advance, baseline + size * 0.25, baseline, size))
        x += advance
    return out
