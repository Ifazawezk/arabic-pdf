"""Rebuild paragraphs and headings from lines in reading order."""

from __future__ import annotations

import statistics
from collections import Counter

from .document import Block, Document
from .layout import Line, is_rtl, line_text

# a baseline step this many times the normal one starts a new paragraph
PARAGRAPH_STEP = 1.3
# normal line spacing is at most this many font sizes: on a page of one line
# paragraphs, the median step is really the paragraph step
MAX_LINE_STEP = 1.75
# a line shorter than this share of its column ends its paragraph
SHORT_LINE = 0.6
# a line this close to the full column width may continue in the next column
FULL_LINE = 0.9
# text this many times larger than the body text is a heading
HEADING_SIZE = 1.15
HEADING_MAX_LINES = 3
# font sizes closer than this ratio share a heading level
SAME_LEVEL = 1.03
SAME_SIZE = 1.1
# a paragraph that stops at the foot of a page without one of these runs on to the next page
SENTENCE_END = (".", "!", "?", ":", "؟", "۔", "…")
CLOSING = "\"')]}»”’"


def is_bold(line: Line) -> bool:
    ink = line.ink
    return bool(ink) and sum(g.bold for g in ink) * 2 > len(ink)


def normal_step(lines: list[Line]) -> float:
    """The usual distance between baselines of consecutive lines on the page."""
    steps = []
    for a, b in zip(lines, lines[1:]):
        step = b.baseline - a.baseline
        if a.column == b.column and step > 0 and _same_size(a, b) and not (a.table or b.table):
            steps.append(step)
    return statistics.median(steps) if steps else 0.0


def _same_size(a: Line, b: Line) -> bool:
    return max(a.size, b.size) <= SAME_SIZE * min(a.size, b.size)


def column_widths(lines: list[Line]) -> dict:
    widths: dict = {}
    for line in lines:
        if line.table is None:
            widths[line.column] = max(widths.get(line.column, 0.0), line.x1 - line.x0)
    return widths


def continues(prev: Line, line: Line, step: float, widths: dict) -> bool:
    """True if ``line`` belongs to the same paragraph as ``prev``."""
    if prev.table is not None or line.table is not None:
        return False
    if not _same_size(prev, line) or is_bold(prev) != is_bold(line):
        return False
    if prev.column is None or line.column is None:
        if prev.column != line.column:
            return False
    width = widths.get(prev.column, 0.0)
    filled = (prev.x1 - prev.x0) / width if width else 1.0
    if prev.column != line.column:  # a paragraph can run on into the next column
        return filled >= FULL_LINE
    gap = line.baseline - prev.baseline
    usual = min(step, MAX_LINE_STEP * prev.size) if step else MAX_LINE_STEP * prev.size
    if gap <= 0 or gap > PARAGRAPH_STEP * usual:
        return False
    return filled >= SHORT_LINE


def runs_on(lines: list[Line], following: list[Line]) -> bool:
    """True if the last of ``lines`` is cut off mid paragraph and the first of
    ``following``, the lines of the next page, carries on with it."""
    if not lines or not following:
        return False
    prev, line = lines[-1], following[0]
    if prev.table is not None or line.table is not None:
        return False
    if not _same_size(prev, line) or is_bold(prev) != is_bold(line):
        return False
    width = column_widths(lines).get(prev.column, 0.0)
    if width and (prev.x1 - prev.x0) / width < SHORT_LINE:
        return False
    return not prev.text.rstrip().rstrip(CLOSING).endswith(SENTENCE_END)


def group_paragraphs(lines: list[Line]) -> list[list[Line]]:
    step = normal_step(lines)
    widths = column_widths(lines)
    groups: list[list[Line]] = []
    for line in lines:
        if groups and continues(groups[-1][-1], line, step, widths):
            groups[-1].append(line)
        else:
            groups.append([line])
    return groups


def paragraph_block(group: list[Line], page_rtl: bool, arabic_variants: bool) -> Block:
    """Lines to one block. The direction comes from the whole paragraph, so a
    wrapped line that happens to be mostly Latin stays in an Arabic paragraph."""
    first = group[0]
    if first.table is not None:
        return Block("table", first.text, first.bbox, rtl=first.rtl, size=first.size, rows=first.table)
    glyphs = [g for line in group for g in line.ink]
    rtl = is_rtl(glyphs, default=page_rtl)
    text = " ".join(t for t in (line_text(ln, rtl, arabic_variants) for ln in group) if t)
    bbox = (min(ln.x0 for ln in group), min(ln.y0 for ln in group),
            max(ln.x1 for ln in group), max(ln.y1 for ln in group))
    size = statistics.median(g.size for g in glyphs) if glyphs else group[0].size
    return Block("paragraph", text, bbox, rtl=rtl, size=size)


def page_blocks(lines: list[Line], page_rtl: bool, arabic_variants: bool = True) -> list[Block]:
    blocks = [paragraph_block(g, page_rtl, arabic_variants) for g in group_paragraphs(lines)]
    return [b for b in blocks if b.text]


def body_size(document: Document) -> float:
    """The font size that carries the most text in the document."""
    weights: Counter = Counter()
    for block in document.blocks:
        if block.kind == "paragraph":
            weights[round(block.size * 2) / 2] += len(block.text)
    return weights.most_common(1)[0][0] if weights else 0.0


def mark_headings(document: Document) -> None:
    """Turn paragraphs set larger than the body text into headings, with levels by size."""
    body = body_size(document)
    if not body:
        return
    candidates = [b for b in document.blocks
                  if b.kind == "paragraph" and b.size >= HEADING_SIZE * body
                  and (b.bbox[3] - b.bbox[1]) <= (HEADING_MAX_LINES + 1) * b.size * 1.6]
    levels: list[float] = []
    for size in sorted({b.size for b in candidates}, reverse=True):
        if not levels or levels[-1] > SAME_LEVEL * size:
            levels.append(size)
    for block in candidates:
        block.kind = "heading"
        rank = next(i for i, size in enumerate(levels) if size <= block.size * SAME_LEVEL)
        block.level = min(rank + 1, 6)
