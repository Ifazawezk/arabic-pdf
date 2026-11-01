"""Turn a line of glyphs from visual order (left to right on the page) into logical order.

A PDF stores where each glyph is painted, not the order a reader reads
them. For an Arabic line, painting order and reading order are mirrored,
except for the runs of Latin text and numbers inside it, which keep their
left to right order. This is the job the Unicode Bidirectional Algorithm
(UAX #9) does when text is displayed, and its reordering step can be run
backwards: resolve an embedding level for every glyph from its bidi class
and its neighbours, then reverse runs of glyphs from the highest level down.

Each unit is one glyph, never a single code point, so a ligature such as
lam-alef that stands for two letters is moved as one piece and its letters
stay in order.

Running the algorithm on visual input is exact for Arabic text, numbers,
dates, percentages and brackets. The one real ambiguity is a number next to
a Latin word: "Windows 11" and "500 QAR" are painted the same way (word on
the left, number on the right). We read the number as part of the Latin
run, as UAX #9 rule W7 would, unless the word is a known unit or currency.
"""

from __future__ import annotations

import unicodedata

STRONG_L = "L"
STRONG_R = "R"
NUMBER = "NUM"  # a digit before we know if it is European (EN) or Arabic (AN)
NEUTRAL = "ON"

# Latin words that follow the number they belong to ("500 QAR", "8 GB").
UNIT_WORDS = {
    # currencies
    "qar", "qr", "sar", "sr", "aed", "dhs", "kwd", "bhd", "omr", "egp", "jod", "usd", "eur", "gbp",
    "jpy", "cny", "inr", "try", "mad", "tnd", "dzd", "iqd", "lbp", "syp", "yer", "lyd", "sdg",
    # data and rates
    "b", "kb", "mb", "gb", "tb", "pb", "kbps", "mbps", "gbps", "bps",
    # length, area, mass, volume
    "mm", "cm", "m", "km", "mi", "ft", "m2", "km2", "ha", "mg", "g", "kg", "t", "lb", "lbs", "oz",
    "ml", "l", "cl",
    # time, frequency, energy
    "ms", "s", "sec", "min", "h", "hr", "hrs", "am", "pm", "hz", "khz", "mhz", "ghz",
    "w", "kw", "mw", "gw", "kwh", "mwh", "v", "mah", "kcal", "cal", "rpm", "bpm",
    # temperature, screens
    "c", "f", "px", "pt", "dpi", "ppi", "fps",
}

MIRRORS = {
    "(": ")", ")": "(", "[": "]", "]": "[", "{": "}", "}": "{", "<": ">", ">": "<",
    "\u00ab": "\u00bb", "\u00bb": "\u00ab", "\u2039": "\u203a", "\u203a": "\u2039",
    "\u2264": "\u2265", "\u2265": "\u2264", "\u27e8": "\u27e9", "\u27e9": "\u27e8",
}


def bidi_class(text: str) -> str:
    """Bidi class of a glyph: the class of its first character that has one.

    Returns L, R (also for AL), EN, AN, ES, ET, CS or ON.
    """
    for ch in text:
        cls = unicodedata.bidirectional(ch)
        if cls in ("NSM", "BN", ""):
            continue
        if cls == "L" and 0xE000 <= ord(ch) <= 0xF8FF:
            return NEUTRAL  # private use: an unmapped glyph, direction unknown
        if cls in ("R", "AL"):
            return STRONG_R
        if cls in ("L", "EN", "AN", "ES", "ET", "CS"):
            return cls
        return NEUTRAL
    return NEUTRAL


def _latin_word_before(units: list[str], classes: list[str], i: int) -> str:
    """The Latin word painted just left of position i, skipping spaces."""
    j = i - 1
    while j >= 0 and not units[j].strip():
        j -= 1
    end = j
    while j >= 0 and classes[j] == STRONG_L:
        j -= 1
    return "".join(units[j + 1:end + 1])


def resolve_levels(units: list[str], rtl: bool) -> list[int]:
    """Embedding level for every unit of a line given in visual order."""
    n = len(units)
    cls = [bidi_class(u) for u in units]
    original = list(cls)

    # W2 and W7, decided from the painted neighbours: a digit with Latin text
    # on its left is part of that Latin run; a digit next to Arabic text is an
    # Arabic number (it does not absorb %, + or -); otherwise it is European.
    # The decision is made once per number, separators included (1,250.75).
    i = 0
    while i < n:
        if original[i] != "EN":
            i += 1
            continue
        j = i
        while j + 1 < n and (original[j + 1] == "EN" or (original[j + 1] in ("CS", "ES", "ET")
                                                          and j + 2 < n and original[j + 2] == "EN")):
            j += 1
        left = next((original[k] for k in range(i - 1, -1, -1) if original[k] in (STRONG_L, STRONG_R)), None)
        right = next((original[k] for k in range(j + 1, n) if original[k] in (STRONG_L, STRONG_R)), None)
        if left == STRONG_L and not (rtl and _latin_word_before(units, original, i).lower() in UNIT_WORDS):
            new = STRONG_L
        elif STRONG_R in (left, right):
            new = "AN"
        else:
            new = "EN"
        for k in range(i, j + 1):
            if original[k] == "EN":
                cls[k] = new
        i = j + 1

    # W4: one separator between two numbers of the same kind joins them
    for i in range(1, n - 1):
        a, b = cls[i - 1], cls[i + 1]
        if cls[i] == "CS" and a == b and a in ("EN", "AN"):
            cls[i] = a
        elif cls[i] == "ES" and a == b == "EN":
            cls[i] = "EN"
        elif cls[i] in ("CS", "ES") and a == b == STRONG_L and original[i - 1] == original[i + 1] == "EN":
            cls[i] = STRONG_L  # 3.12 inside a Latin run
    # W5: terminators next to a European number belong to it (15%, $20)
    for i in range(n):
        if cls[i] == "ET":
            j = i
            while j < n and cls[j] == "ET":
                j += 1
            if (i > 0 and cls[i - 1] == "EN") or (j < n and cls[j] == "EN"):
                for k in range(i, j):
                    cls[k] = "EN"
    # W6: anything left over is neutral
    cls = [NEUTRAL if c in ("ES", "ET", "CS") else c for c in cls]

    # N1/N2: neutrals take the direction of their surroundings if both sides
    # agree (numbers count as right to left here), otherwise the line direction
    base = STRONG_R if rtl else STRONG_L
    i = 0
    while i < n:
        if cls[i] != NEUTRAL:
            i += 1
            continue
        j = i
        while j < n and cls[j] == NEUTRAL:
            j += 1
        before = base if i == 0 else (STRONG_R if cls[i - 1] in ("EN", "AN") else cls[i - 1])
        after = base if j == n else (STRONG_R if cls[j] in ("EN", "AN") else cls[j])
        direction = before if before == after else base
        for k in range(i, j):
            cls[k] = direction
        i = j

    # I1/I2: implicit levels
    base_level = 1 if rtl else 0
    levels = []
    for c in cls:
        if c == STRONG_L:
            levels.append(base_level + (base_level % 2))
        elif c == STRONG_R:
            levels.append(base_level + 1 - (base_level % 2))
        else:  # EN or AN
            levels.append(base_level + 1 if base_level % 2 else base_level + 2)
    return levels


def reorder(units: list[str], rtl: bool) -> list[str]:
    """Reorder glyph texts given left to right on the page into reading order.

    Brackets painted in a right to left run are mirrored back: the glyph a
    reader sees as ")" at the start of an Arabic parenthesis is a "(" in the text.
    """
    if not units:
        return []
    levels = resolve_levels(units, rtl)
    order = list(range(len(units)))
    odd = [lv for lv in levels if lv % 2]
    if odd:
        for level in range(max(levels), min(odd) - 1, -1):
            i = 0
            while i < len(order):
                if levels[order[i]] >= level:
                    j = i
                    while j < len(order) and levels[order[j]] >= level:
                        j += 1
                    order[i:j] = order[i:j][::-1]
                    i = j
                else:
                    i += 1
    out = []
    for k in order:
        unit = units[k]
        if levels[k] % 2 and unit in MIRRORS:
            unit = MIRRORS[unit]
        out.append(unit)
    return out
