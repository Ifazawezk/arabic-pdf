"""Read the glyphs a PDF page paints, with their positions.

We use PyMuPDF's ``get_texttrace()`` instead of ``get_text()``: it reports
every glyph exactly as the content stream draws it, without the line
building and partial right-to-left handling MuPDF applies on top. Our own
layout code then decides the order from the positions alone.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
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
    quarter: int = 0  # quarter turns of the text: coordinates are in its own upright frame

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


def quarter_turns(dx: float, dy: float) -> int | None:
    """How many quarter turns a text direction is from horizontal, None if it is diagonal."""
    if abs(dy) <= 0.05:
        return 0 if dx > 0 else 2
    if abs(dx) <= 0.05:
        return 1 if dy < 0 else 3
    return None


def rotate_point(x: float, y: float, quarter: int, width: float, height: float) -> tuple[float, float]:
    """Page coordinates to the upright frame of text turned by ``quarter`` quarter turns."""
    if quarter == 1:  # text runs up the page
        return height - y, x
    if quarter == 2:  # upside down
        return width - x, height - y
    if quarter == 3:  # text runs down the page
        return y, width - x
    return x, y


def rotate_rect(rect, quarter: int, width: float, height: float) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = rect
    ax, ay = rotate_point(x0, y0, quarter, width, height)
    bx, by = rotate_point(x1, y1, quarter, width, height)
    return min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)


def unrotate_rect(rect, quarter: int, width: float, height: float) -> tuple[float, float, float, float]:
    """The inverse of ``rotate_rect``, for a page of the given size."""
    if quarter % 2:
        return rotate_rect(rect, (4 - quarter) % 4, height, width)
    return rotate_rect(rect, (4 - quarter) % 4, width, height)


def _is_bold(span: dict) -> bool:
    name = span.get("font", "").lower()
    return bool(span.get("flags", 0) & 16) or "bold" in name or name.endswith("bd") or "black" in name


_ACTUAL_TEXT = re.compile(rb"/ActualText\s*<([0-9A-Fa-f]+)>(.*?)EMC", re.S)
_SET_FONT = re.compile(rb"/([A-Za-z0-9_+.\-]+)\s+[\d.]+\s+Tf")
_GLYPH_CODES = re.compile(rb"<([0-9A-Fa-f]+)>")
# share of the declarations for a glyph that must agree before we trust them
LIGATURE_AGREEMENT = 0.75


def scan_actual_text(content: bytes, fonts: dict[str, str], counts: dict) -> None:
    """Count what /ActualText says about single glyphs in one content stream."""
    events = [(m.start(), m) for m in _SET_FONT.finditer(content)]
    events += [(m.start(), m) for m in _ACTUAL_TEXT.finditer(content)]
    font = None
    for _, match in sorted(events, key=lambda e: e[0]):
        if match.re is _SET_FONT:
            font = match.group(1).decode("latin-1")
            continue
        body = match.group(2)
        inner = _SET_FONT.search(body)
        if inner:
            font = inner.group(1).decode("latin-1")
        code = b"".join(_GLYPH_CODES.findall(body))
        if len(code) == 4 and font in fonts:  # exactly one two byte glyph
            text = bytes.fromhex(match.group(1).decode("ascii")).decode("utf-16", "replace")
            counts.setdefault((fonts[font], int(code, 16)), Counter())[text] += 1


def choose_ligatures(counts: dict) -> dict[tuple[str, int], str]:
    """Keep glyphs that stand for several letters, if their declarations agree."""
    chosen = {}
    for key, texts in counts.items():
        text, votes = texts.most_common(1)[0]
        letters = fold(text)
        if len(letters) >= 2 and letters.isalpha() and votes >= LIGATURE_AGREEMENT * sum(texts.values()):
            chosen[key] = letters
    return chosen


def learn_ligatures(pdf: pymupdf.Document) -> dict[tuple[str, int], str]:
    """Find ligature glyphs whose Unicode map only names one of their letters.

    Arabic PDFs from Adobe tools can map a lam-alef glyph to plain alef, which
    silently turns "الطلاب" into "الطاب" in every extractor that trusts the map.
    The same files often declare the truth in /ActualText, but only on some of
    the occurrences. What a glyph is declared to be in one place holds everywhere.
    """
    counts: dict = {}
    for page in pdf:
        content = page.read_contents()
        if b"ActualText" in content:
            fonts = {f[4]: f[3].split("+")[-1] for f in page.get_fonts()}
            scan_actual_text(content, fonts, counts)
    return choose_ligatures(counts)


def actual_digits(page: pymupdf.Page) -> dict[tuple[float, float], str]:
    """Arabic-Indic digits that exist only in the /ActualText of a page, by position.

    Arabic layout programs often reuse one glyph for a digit in both scripts:
    its Unicode map says 3 while the page shows the Arabic digit and /ActualText
    says so. The raw glyph trace ignores /ActualText, the text page does not.
    """
    if b"ActualText" not in page.read_contents():
        return {}
    digits = {}
    for block in page.get_text("rawdict")["blocks"]:
        for line in block.get("lines", ()):
            for span in line["spans"]:
                for char in span["chars"]:
                    if "\u0660" <= char["c"] <= "\u0669" or "\u06f0" <= char["c"] <= "\u06f9":
                        digits[(round(char["origin"][0], 1), round(char["origin"][1], 1))] = char["c"]
    return digits


def read_glyphs(page: pymupdf.Page, clip: pymupdf.Rect | None = None,
                ligatures: dict[tuple[str, int], str] | None = None) -> list[Glyph]:
    """All glyphs on the page, in drawing order.

    A glyph that the PDF maps to several characters (for example a lam-alef
    ligature mapped to "لا") arrives as one entry plus continuation entries
    with glyph id -1; we join them so the ligature stays one unit.

    Text set at a right angle is kept, in coordinates turned so that it reads
    upright: wide tables are often laid sideways on a portrait page. Only
    diagonal text is dropped, which in practice is a watermark.
    """
    area = clip or page.rect
    width, height = page.rect.width, page.rect.height
    digits = actual_digits(page)
    glyphs: list[Glyph] = []
    for span in page.get_texttrace():
        dx, dy = span["dir"]
        quarter = quarter_turns(dx, dy)
        if quarter is None or span.get("wmode", 0):
            continue
        size = float(span["size"])
        font = span.get("font", "")
        short_font = font.split("+")[-1]
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
            if ligatures:
                letters = ligatures.get((short_font, gid))
                if letters and ch in letters:
                    ch = letters
            if digits and ch.isascii() and ch.isdigit():
                ch = digits.get((round(origin[0], 1), round(origin[1], 1)), ch)
            if quarter:
                x0, y0, x1, y1 = rotate_rect(bbox, quarter, width, height)
                baseline = rotate_point(origin[0], origin[1], quarter, width, height)[1]
            else:
                baseline = origin[1]
            previous = Glyph(ch, x0, y0, x1, y1, baseline, size, font, bold, seq, quarter=quarter)
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
