"""Read the glyphs a PDF page paints, with their positions.

We use PyMuPDF's ``get_texttrace()`` instead of ``get_text()``: it reports
every glyph exactly as the content stream draws it, without the line
building and partial right-to-left handling MuPDF applies on top. Our own
layout code then decides the order from the positions alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pymupdf


@dataclass
class Glyph:
    """One painted glyph (or a glyph plus its attached diacritics)."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    baseline: float
    size: float
    font: str = ""
    bold: bool = False
    seq: int = 0
    marks: list[str] = field(default_factory=list)

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def is_space(self) -> bool:
        return not self.text.strip()

    @property
    def full_text(self) -> str:
        return self.text + "".join(self.marks)


def _is_bold(span: dict) -> bool:
    name = span.get("font", "").lower()
    return bool(span.get("flags", 0) & 16) or "bold" in name or name.endswith("bd") or "black" in name


def read_glyphs(page: pymupdf.Page, clip: pymupdf.Rect | None = None) -> list[Glyph]:
    """All horizontal glyphs on the page, in drawing order.

    A glyph that the PDF maps to several characters (for example a lam-alef
    ligature mapped to "لا") arrives as one entry plus continuation entries
    with glyph id -1; we join them so the ligature stays one unit.
    """
    area = clip or page.rect
    glyphs: list[Glyph] = []
    for span in page.get_texttrace():
        dx, dy = span["dir"]
        if abs(dy) > 0.05 or dx <= 0 or span.get("wmode", 0):
            continue  # rotated or vertical text (watermarks, stamps)
        size = float(span["size"])
        font = span.get("font", "")
        bold = _is_bold(span)
        seq = span.get("seqno", 0)
        for ucs, gid, origin, bbox in span["chars"]:
            ch = chr(ucs) if 0 <= ucs < 0x110000 else "�"
            if gid == -1 and glyphs and glyphs[-1].seq == seq:
                glyphs[-1].text += ch
                continue
            x0, y0, x1, y1 = bbox
            if x1 < area.x0 or x0 > area.x1 or y1 < area.y0 or y0 > area.y1:
                continue  # clipped away or off the page
            glyphs.append(Glyph(ch, x0, y0, x1, y1, origin[1], size, font, bold, seq))
    return glyphs
