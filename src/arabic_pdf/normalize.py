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

TATWEEL = "ـ"

# Fonts often share one glyph between an Arabic letter and a Persian or Urdu
# variant that looks the same in that position. A producer that maps glyphs
# back through the font's cmap can then pick the variant code point, so an
# Arabic document comes out with Farsi yeh or heh doachashmee. In Arabic text
# we map these shapes back to the Arabic letter that is actually displayed.
ARABIC_VARIANTS = {
    0xFBFC: "ى",  # Farsi yeh isolated -> alef maksura (same dotless shape)
    0xFBFD: "ى",  # Farsi yeh final -> alef maksura
    0xFBFE: "ي",  # Farsi yeh initial -> yeh (same dotted shape)
    0xFBFF: "ي",  # Farsi yeh medial -> yeh
    0xFBAA: "ه",  # heh doachashmee forms -> heh
    0xFBAB: "ه",
    0xFBAC: "ه",
    0xFBAD: "ه",
    0xFB90: "ك",  # keheh initial -> kaf
    0xFB91: "ك",  # keheh medial -> kaf
}

# Letters that only Persian, Urdu and related languages use. If a page has
# any of them we keep the variant letters as they are.
_NON_ARABIC_LETTERS = re.compile(
    "[پچژگٹڈڑںےہ"
    "ﭖ-ﭙﭺ-ﭽﮊﮋﮒ-ﮕﭦ-ﭩﮈﮉﮌﮍ"
    "ﮞﮟﮦ-ﮩﮮ-ﮱ]"
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
        if marks and all(c in " ـ" or unicodedata.category(c) == "Mn" for c in folded):
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
    return unicodedata.normalize("NFC", out)
