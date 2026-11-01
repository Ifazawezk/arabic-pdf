"""Group glyphs into lines and put the lines in reading order."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from .bidi import STRONG_L, STRONG_R, bidi_class, reorder
from .glyphs import Glyph
from .normalize import fold

# a gap wider than this (in font sizes) splits a row into separate lines
SPLIT_GAP = 2.5
# a gap wider than this (in font sizes) between two glyphs is a word space
SPACE_GAP = 0.18


@dataclass
class Line:
    glyphs: list[Glyph]  # left to right on the page
    text: str = ""
    rtl: bool = True
    tags: set = field(default_factory=set)

    @property
    def x0(self) -> float:
        return min(g.x0 for g in self.glyphs)

    @property
    def x1(self) -> float:
        return max(g.x1 for g in self.glyphs)

    @property
    def y0(self) -> float:
        return min(g.y0 for g in self.glyphs)

    @property
    def y1(self) -> float:
        return max(g.y1 for g in self.glyphs)

    @property
    def baseline(self) -> float:
        return statistics.median(g.baseline for g in self.glyphs)

    @property
    def size(self) -> float:
        return statistics.median(g.size for g in self.glyphs if not g.is_space) if self.ink else self.glyphs[0].size

    @property
    def ink(self) -> list[Glyph]:
        return [g for g in self.glyphs if not g.is_space]

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return (self.x0, self.y0, self.x1, self.y1)


def letter_balance(glyphs) -> tuple[int, int]:
    """Number of right to left and left to right letters."""
    r = l = 0
    for g in glyphs:
        c = bidi_class(g.text)
        if c == STRONG_R:
            r += 1
        elif c == STRONG_L:
            l += 1
    return r, l


def is_rtl(glyphs, default: bool = True) -> bool:
    r, l = letter_balance(glyphs)
    if r == 0 and l == 0:
        return default
    return r >= l


def build_rows(glyphs: list[Glyph]) -> list[list[Glyph]]:
    """Cluster glyphs that share a baseline."""
    rows: list[list[Glyph]] = []
    for g in sorted(glyphs, key=lambda g: (g.baseline, g.x0)):
        if rows:
            row = rows[-1]
            ref = row[0]
            if abs(g.baseline - ref.baseline) <= 0.45 * max(ref.size, g.size):
                row.append(g)
                continue
        rows.append([g])
    return [sorted(r, key=lambda g: g.x0) for r in rows]


def split_row(row: list[Glyph]) -> list[list[Glyph]]:
    """Split a row where the gap between glyphs is too wide to be a word space."""
    parts = [[row[0]]]
    last_ink = row[0] if not row[0].is_space else None
    for g in row[1:]:
        if not g.is_space and last_ink is not None:
            if g.x0 - last_ink.x1 > SPLIT_GAP * max(g.size, last_ink.size):
                parts.append([])
        parts[-1].append(g)
        if not g.is_space:
            last_ink = g
    return [p for p in parts if any(not g.is_space for g in p)]


def with_spaces(glyphs: list[Glyph]) -> list[Glyph]:
    """Add space units where glyphs are separated by a visible gap but no space glyph."""
    out: list[Glyph] = []
    for g in glyphs:
        if out:
            prev = out[-1]
            gap = g.x0 - prev.x1
            if not g.is_space and not prev.is_space and gap > SPACE_GAP * min(g.size, prev.size):
                out.append(Glyph(" ", prev.x1, prev.y0, g.x0, prev.y1, prev.baseline, prev.size))
        out.append(g)
    return out


def line_text(line: Line, rtl: bool, arabic_variants: bool = True) -> str:
    """Logical text of one line."""
    units = with_spaces(line.glyphs)
    ordered = reorder([u.full_text for u in units], rtl)
    text = fold("".join(ordered), arabic_variants=arabic_variants)
    return " ".join(text.split())


def page_lines(glyphs: list[Glyph], page_rtl: bool, arabic_variants: bool = True) -> list[Line]:
    """Lines of a page in reading order, top to bottom."""
    lines = []
    for row in build_rows(glyphs):
        parts = [Line(p) for p in split_row(row)]
        if page_rtl:
            parts.reverse()
        lines.extend(parts)
    for line in lines:
        line.rtl = is_rtl(line.glyphs, default=page_rtl)
        line.text = line_text(line, line.rtl, arabic_variants)
    return [ln for ln in lines if ln.text]
