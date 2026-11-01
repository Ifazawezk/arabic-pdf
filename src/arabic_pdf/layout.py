"""Group glyphs into lines and put the lines in reading order."""

from __future__ import annotations

import re
import statistics
from collections import Counter
from dataclasses import dataclass

from .bidi import STRONG_L, STRONG_R, bidi_class, reorder
from .glyphs import Glyph
from .normalize import fold

# a gap wider than this (in font sizes) splits a row into separate lines
SPLIT_GAP = 2.5
# a gap wider than this (in font sizes) between two glyphs is a word space
SPACE_GAP = 0.18
# a hole in a row at least this wide (in font sizes) may be a column gutter
GUTTER_HOLE = 0.8
# holes must line up over at least this width (in font sizes) and this many rows
GUTTER_WIDTH = 0.6
GUTTER_ROWS = 3


@dataclass
class Line:
    glyphs: list[Glyph]  # left to right on the page
    text: str = ""
    rtl: bool = True
    column: int | None = 0  # None when the line spans several columns
    table: list[list[str]] | None = None  # set when this entry stands for a whole table

    @property
    def ink(self) -> list[Glyph]:
        return [g for g in self.glyphs if not g.is_space]

    @property
    def x0(self) -> float:
        return min(g.x0 for g in self.ink or self.glyphs)

    @property
    def x1(self) -> float:
        return max(g.x1 for g in self.ink or self.glyphs)

    @property
    def y0(self) -> float:
        return min(g.y0 for g in self.glyphs)

    @property
    def y1(self) -> float:
        return max(g.y1 for g in self.glyphs)

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def baseline(self) -> float:
        return statistics.median(g.baseline for g in self.glyphs)

    @property
    def size(self) -> float:
        return statistics.median(g.size for g in self.ink or self.glyphs)

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
    for g in sorted(glyphs, key=lambda g: (g.baseline, g.cx)):
        if rows:
            row = rows[-1]
            ref = row[0]
            if abs(g.baseline - ref.baseline) <= 0.45 * max(ref.size, g.size):
                row.append(g)
                continue
        rows.append([g])
    # sort by centre: fonts tuck alef into the advance of a preceding reh, so
    # the left edges of overlapping glyphs can come in the wrong order
    return [sorted(r, key=lambda g: g.cx) for r in rows]


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


def ink_intervals(row: list[Glyph]) -> list[tuple[float, float]]:
    """Painted stretches of a row, ignoring word gaps."""
    spans: list[list[float]] = []
    for g in row:
        if g.is_space:
            continue
        if spans and g.x0 - spans[-1][1] <= GUTTER_HOLE * g.size:
            spans[-1][1] = max(spans[-1][1], g.x1)
        else:
            spans.append([g.x0, g.x1])
    return [(a, b) for a, b in spans]


def find_gutters(rows: list[list[Glyph]]) -> list[tuple[float, float]]:
    """Vertical bands of white space that separate columns.

    A gutter shows up as a hole at the same x position in many rows. Word gaps
    can line up by chance, so a band only counts if the rows with the hole
    outnumber the rows running straight through it. Those through-rows are
    fine in small numbers: a title or a full width paragraph above the columns.
    """
    sizes = [g.size for row in rows for g in row if not g.is_space]
    if not sizes:
        return []
    size = statistics.median(sizes)
    intervals = [ink_intervals(row) for row in rows]
    holes = []  # (x0, x1, row index)
    for i, spans in enumerate(intervals):
        for (_, a), (b, _) in zip(spans, spans[1:]):
            holes.append((a, b, i))
    # narrow holes first: a row that skips a whole column has a very wide hole
    # that contains the gutters but must not widen them
    holes.sort(key=lambda h: h[1] - h[0])
    clusters: list[dict] = []
    for a, b, i in holes:
        for c in clusters:
            lo, hi = max(a, c["a"]), min(b, c["b"])
            if hi - lo >= GUTTER_WIDTH * size:
                c["a"], c["b"] = lo, hi
                c["rows"].add(i)
                break
        else:
            if b - a >= GUTTER_WIDTH * size:
                clusters.append({"a": a, "b": b, "rows": {i}})
    gutters = []
    for c in clusters:
        if len(c["rows"]) < GUTTER_ROWS:
            continue
        first, last = min(c["rows"]), max(c["rows"])
        crossing = sum(
            1 for i in range(first, last + 1)
            if i not in c["rows"] and any(a < c["b"] and b > c["a"] for a, b in intervals[i])
        )
        if len(c["rows"]) >= crossing:
            gutters.append((c["a"], c["b"]))
    return sorted(gutters)


def split_at_gutters(row: list[Glyph], gutters: list[tuple[float, float]]) -> list[list[Glyph]]:
    """Cut a row at every gutter it does not paint across."""
    cuts = [(a + b) / 2 for a, b in gutters
            if not any(not g.is_space and g.x0 < b and g.x1 > a for g in row)]
    parts: list[list[Glyph]] = [[] for _ in range(len(cuts) + 1)]
    for g in row:
        parts[sum(1 for c in cuts if g.cx > c)].append(g)
    return [p for p in parts if p]


def column_of(line: Line, gutters: list[tuple[float, float]]) -> int | None:
    """Column index counted from the left, or None if the line crosses a gutter."""
    if any(line.x0 < a and line.x1 > b for a, b in gutters):
        return None
    return sum(1 for a, b in gutters if line.cx > (a + b) / 2)


def reading_order(lines: list[Line], page_rtl: bool) -> list[Line]:
    """Sort lines column by column, in bands separated by lines that span columns."""
    ordered: list[Line] = []
    band: list[Line] = []

    def flush():
        for col in sorted({ln.column for ln in band}, reverse=page_rtl):
            ordered.extend(ln for ln in band if ln.column == col)
        band.clear()

    for line in lines:  # already top to bottom, and in order inside a row
        if line.column is None:
            flush()
            ordered.append(line)
        else:
            band.append(line)
    flush()
    return ordered


def table_line(bbox, rows: list[list[str]], size: float, rtl: bool) -> Line:
    """A placeholder that lets a table take its place in the reading order."""
    x0, y0, x1, y1 = bbox
    box = Glyph(chr(0xFFFC), x0, y0, x1, y1, y0, size)
    text = "\n".join("\t".join(row) for row in rows)
    return Line([box], text=text, rtl=rtl, table=rows)


def page_lines(glyphs: list[Glyph], page_rtl: bool, arabic_variants: bool = True,
               tables: list[Line] | None = None) -> list[Line]:
    """Lines of a page in reading order, with any tables in their place."""
    rows = build_rows(glyphs)
    gutters = find_gutters(rows)
    lines = []
    for row in rows:
        parts = [Line(p) for piece in split_at_gutters(row, gutters) for p in split_row(piece)]
        if page_rtl:
            parts.reverse()
        lines.extend(parts)
    for line in lines:
        line.column = column_of(line, gutters)
        line.rtl = is_rtl(line.glyphs, default=page_rtl)
        line.text = line_text(line, line.rtl, arabic_variants)
    for table in tables or ():
        table.column = column_of(table, gutters)
        position = next((i for i, ln in enumerate(lines) if ln.baseline > table.baseline), len(lines))
        lines.insert(position, table)
    return [ln for ln in reading_order(lines, page_rtl) if ln.text]


_DIGITS = re.compile("[0-9\u0660-\u0669\u06f0-\u06f9]+")
# share of the page height, at the top and at the bottom, where running text lives
MARGIN_BAND = 0.12


def line_signature(text: str) -> str:
    """Text with numbers blanked, so "page 3" and "page 4" count as the same line."""
    return "".join(_DIGITS.sub("#", text).split())


def remove_running_text(pages: list[list[Line]], heights: list[float]) -> list[list[Line]]:
    """Drop headers, footers and page numbers: lines that repeat in the page margins.

    A line goes only if it sits in the top or bottom band of the page and the
    same text, ignoring numbers, shows up there on at least half of the pages.
    A one page document has nothing to compare with, so it is left alone.
    """
    if len(pages) < 2:
        return pages
    needed = max(2, (len(pages) + 1) // 2)
    seen: Counter = Counter()
    for lines, height in zip(pages, heights):
        found = set()
        for line in lines:
            if line.y1 <= MARGIN_BAND * height:
                found.add(("top", line_signature(line.text)))
            elif line.y0 >= (1 - MARGIN_BAND) * height:
                found.add(("bottom", line_signature(line.text)))
        seen.update(found)
    running = {key for key, count in seen.items() if count >= needed}

    def is_running(line: Line, height: float) -> bool:
        sig = line_signature(line.text)
        if line.y1 <= MARGIN_BAND * height:
            return ("top", sig) in running
        if line.y0 >= (1 - MARGIN_BAND) * height:
            return ("bottom", sig) in running
        return False

    return [[ln for ln in lines if not is_running(ln, height)] for lines, height in zip(pages, heights)]
