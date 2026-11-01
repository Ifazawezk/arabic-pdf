"""Read the glyphs a PDF page paints, with their positions.

We use PyMuPDF's ``get_texttrace()`` instead of ``get_text()``: it reports
every glyph exactly as the content stream draws it, without the line
building and partial right-to-left handling MuPDF applies on top. Our own
layout code then decides the order from the positions alone.
"""

from __future__ import annotations

import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field

import pymupdf

from .normalize import fold


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
    marks: list[tuple[str, float]] = field(default_factory=list)  # (mark, x position)

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
        """The glyph text with its marks, each after the letter it belongs to.

        A ligature is one glyph for several letters, so a mark on it is placed
        by where it sits: Arabic ligatures run right to left inside the glyph.
        """
        if not self.marks:
            return self.text
        letters = fold(self.text, keep_tatweel=True)
        if len(letters) < 2 or unicodedata.bidirectional(letters[0]) not in ("R", "AL") or self.width <= 0:
            return self.text + "".join(m for m, _ in self.marks)
        slots: list[list[str]] = [[] for _ in letters]
        for mark, x in self.marks:
            share = min(max((self.x1 - x) / self.width, 0.0), 0.999)
            slots[int(share * len(letters))].append(mark)
        return "".join(letter + "".join(slot) for letter, slot in zip(letters, slots))


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
        previous = None
        for ucs, gid, origin, bbox in span["chars"]:
            ch = chr(ucs) if 0 <= ucs < 0x110000 else "\ufffd"
            if gid == -1:
                if previous is not None:
                    previous.text += ch
                continue
            x0, y0, x1, y1 = bbox
            if x1 < area.x0 or x0 > area.x1 or y1 < area.y0 or y0 > area.y1:
                previous = None
                continue  # clipped away or off the page
            previous = Glyph(ch, x0, y0, x1, y1, origin[1], size, font, bold, seq)
            glyphs.append(previous)
    return glyphs


def is_mark(text: str) -> bool:
    """True for a glyph that is only diacritics (harakat, shadda, hamza above...)."""
    folded = fold(text, keep_tatweel=True).replace("\u0640", "")
    return bool(folded) and all(unicodedata.category(c) in ("Mn", "Me") for c in folded)


def remove_duplicates(glyphs: list[Glyph]) -> list[Glyph]:
    """Drop glyphs painted twice at almost the same spot.

    Some producers fake bold text by painting every glyph two or three times
    with a tiny offset, which otherwise doubles every letter.
    """
    kept: list[Glyph] = []
    buckets: dict[tuple, list[Glyph]] = defaultdict(list)
    for g in glyphs:
        key = (g.text, round(g.baseline / 2))
        duplicate = False
        for near in (key, (g.text, key[1] - 1), (g.text, key[1] + 1)):
            for other in buckets.get(near, ()):
                tol = 0.12 * g.size
                if abs(other.x0 - g.x0) < tol and abs(other.baseline - g.baseline) < tol:
                    overlap = min(other.x1, g.x1) - max(other.x0, g.x0)
                    if g.width == 0 or overlap >= 0.6 * g.width:
                        duplicate = True
                        break
            if duplicate:
                break
        if not duplicate:
            buckets[key].append(g)
            kept.append(g)
    return kept


def attach_marks(glyphs: list[Glyph]) -> list[Glyph]:
    """Attach diacritic glyphs to the letter they sit on.

    Marks are painted as separate glyphs with no width, often before their
    letter, and their x position can fall anywhere inside the letter. Left
    alone they get sorted to the wrong side of the letter and split words.
    """
    bases = [g for g in glyphs if not g.is_space and not is_mark(g.text)]
    index: dict[int, list[Glyph]] = defaultdict(list)
    for b in bases:
        index[round(b.baseline / 4)].append(b)
    out = []
    for g in glyphs:
        if g.is_space or not is_mark(g.text):
            out.append(g)
            continue
        key = round(g.baseline / 4)
        best, best_rank = None, None
        for k in (key - 1, key, key + 1):
            for b in index.get(k, ()):
                if abs(b.baseline - g.baseline) > 0.5 * b.size:
                    continue
                tol = 0.15 * b.size
                if not b.x0 - tol <= g.cx <= b.x1 + tol:
                    continue
                # shaping engines paint a letter and its marks together, so the
                # same drawing run beats geometry; then the glyph really under
                # the mark; then the closest one
                rank = (b.seq != g.seq, not b.x0 <= g.cx <= b.x1, abs(b.cx - g.cx))
                if best_rank is None or rank < best_rank:
                    best, best_rank = b, rank
        if best is None:
            out.append(g)  # an orphan mark stays where it is painted
        else:
            best.marks.append((g.text, g.cx))
    return out
