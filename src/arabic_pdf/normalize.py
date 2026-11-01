"""Turn glyph codes from a PDF back into plain Arabic letters.

PDF producers often map Arabic glyphs to the Unicode *presentation forms*
(U+FB50 to U+FDFF and U+FE70 to U+FEFF): one code point per contextual shape
and per ligature. They look right on screen but share no code point with
normal text, so search, tokenizers and language models treat them as noise.

``fold()`` maps every presentation form to the letters it stands for. It is
meant to run on one glyph at a time, after the glyphs are in logical order:
a lam-alef ligature is a single glyph, and expanding it before reordering
is how so many tools end up writing ``ال`` instead of ``لا``.
"""

from __future__ import annotations

import re
import unicodedata

TATWEEL = "\u0640"

# Fonts often share one glyph between an Arabic letter and a Persian or Urdu
# variant that looks the same in that position. A producer that maps glyphs
# back through the font's cmap can then pick the variant code point, so an
# Arabic document comes out with Farsi yeh or heh doachashmee. In Arabic text
# we map these shapes back to the Arabic letter that is actually displayed.
ARABIC_VARIANTS = {
    0xFBFC: "\u0649",  # Farsi yeh isolated -> alef maksura (same dotless shape)
    0xFBFD: "\u0649",  # Farsi yeh final -> alef maksura
    0xFBFE: "\u064a",  # Farsi yeh initial -> yeh (same dotted shape)
    0xFBFF: "\u064a",  # Farsi yeh medial -> yeh
    0xFBAA: "\u0647",  # heh doachashmee forms -> heh
    0xFBAB: "\u0647",
    0xFBAC: "\u0647",
    0xFBAD: "\u0647",
    0xFB90: "\u0643",  # keheh initial -> kaf
    0xFB91: "\u0643",  # keheh medial -> kaf
    0x06BE: "\u0647",  # Arial maps its initial heh glyph to heh doachashmee
}

# Farsi yeh as a plain letter: dotted inside a word, dotless at the end
_FARSI_YEH = re.compile("\u06cc(?=[\u0620-\u064a\u066e-\u06d3])")

# A few fonts draw alef with hamza as an alef variant that has no Unicode
# mapping plus a hamza mark. With the mark attached, the pair can only be
# alef with hamza.
_UNMAPPED_ALEF_HAMZA = {"\ufffd\u0654": "\u0623", "\ufffd\u0655": "\u0625"}

# Letters that only Persian, Urdu and related languages use. If a page has
# any of them we keep the variant letters as they are.
_NON_ARABIC_LETTERS = re.compile(
    "[\u067e\u0686\u0698\u06af\u0679\u0688\u0691\u06ba\u06d2\u06c1"
    "\ufb56-\ufb59\ufb7a-\ufb7d\ufb8a\ufb8b\ufb92-\ufb95\ufb66-\ufb69\ufb88\ufb89\ufb8c\ufb8d"
    "\ufb9e\ufb9f\ufba6-\ufba9\ufbae-\ufbb1]"
)


def is_presentation_form(ch: str) -> bool:
    cp = ord(ch)
    return 0xFB50 <= cp <= 0xFDFF or 0xFE70 <= cp <= 0xFEFC


def uses_non_arabic_letters(text: str) -> bool:
    """True if the text contains letters specific to Persian, Urdu and similar."""
    return bool(_NON_ARABIC_LETTERS.search(text))


def _fold_char(ch: str, arabic_variants: bool) -> str:
    cp = ord(ch)
    if arabic_variants and cp in ARABIC_VARIANTS:
        return ARABIC_VARIANTS[cp]
    if 0xFB50 <= cp <= 0xFDFF or 0xFE70 <= cp <= 0xFEFC or 0xFB00 <= cp <= 0xFB06:
        folded = unicodedata.normalize("NFKC", ch)
        marks = [c for c in folded if unicodedata.category(c) == "Mn"]
        # isolated and medial forms of harakat decompose to a space or a
        # tatweel plus the mark; only the mark belongs in the text
        if marks and all(c in " \u0640" or unicodedata.category(c) == "Mn" for c in folded):
            return "".join(marks)
        return folded
    if cp == 0xFEFF:  # byte order mark, sometimes left in text strings
        return ""
    return ch


def fold(text: str, *, arabic_variants: bool = True, keep_tatweel: bool = False) -> str:
    """Map presentation forms and Latin ligatures to plain letters.

    ``arabic_variants`` maps Persian and Urdu look-alike shapes to the Arabic
    letter (see ``ARABIC_VARIANTS``); turn it off for Persian or Urdu text.
    Tatweel (kashida), which PDFs use for justification, is removed unless
    ``keep_tatweel`` is set. The result is NFC normalized.
    """
    out = "".join(_fold_char(ch, arabic_variants) for ch in text)
    if not keep_tatweel:
        out = out.replace(TATWEEL, "")
    if arabic_variants:
        out = _FARSI_YEH.sub("\u064a", out).replace("\u06cc", "\u0649")
    out = unicodedata.normalize("NFC", out)
    for broken, letter in _UNMAPPED_ALEF_HAMZA.items():
        out = out.replace(broken, letter)
    return out
