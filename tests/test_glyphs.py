import re
from pathlib import Path

import pymupdf

from arabic_pdf.glyphs import Glyph, attach_marks, is_mark, read_glyphs, remove_duplicates

CORPUS = Path(__file__).resolve().parent.parent / "corpus"


def glyph(text, x0, x1, baseline=100.0, size=12.0, seq=0):
    return Glyph(text, x0, baseline - size, x1, baseline + 3, baseline, size, seq=seq)


def test_is_mark():
    assert is_mark("\u064e")  # fatha
    assert is_mark("\ufc60")  # shadda with fatha, isolated presentation form
    assert not is_mark("\u0628")
    assert not is_mark(" ")


def test_mark_attaches_to_the_letter_it_sits_on():
    meem = glyph("\u0645", 100, 106, seq=1)
    fatha = glyph("\u064e", 103, 103, seq=1)  # zero width, painted before the letter
    lam = glyph("\u0644", 106, 110, seq=2)
    out = attach_marks([fatha, meem, lam])
    assert [g.text for g in out] == ["\u0645", "\u0644"]
    assert meem.full_text == "\u0645\u064e"


def test_orphan_mark_is_kept():
    out = attach_marks([glyph("\u064e", 300, 300)])
    assert [g.text for g in out] == ["\u064e"]


def test_fake_bold_duplicates_removed():
    a = glyph("\u0628", 100, 106)
    b = glyph("\u0628", 100.3, 106.3)  # same glyph painted again, slightly shifted
    c = glyph("\u0628", 106, 112)      # a real second letter right after it
    assert remove_duplicates([a, b, c]) == [a, c]


def test_multi_character_glyph_stays_one_unit(tmp_path):
    # Remap the lam-alef glyph of a corpus file to the two letters it stands
    # for, the way many producers write their ToUnicode maps.
    doc = pymupdf.open(CORPUS / "browser_simple_arial.pdf")
    for xref in range(1, doc.xref_length()):
        if not doc.xref_is_stream(xref):
            continue
        data = doc.xref_stream(xref)
        if b"beginbfchar" in data or b"beginbfrange" in data:
            text = data.decode("latin-1")
            new = re.sub(r"<([0-9A-Fa-f]{4})> <FEFB>", r"<\1> <06440627>", text, flags=re.I)
            if new != text:
                doc.update_stream(xref, new.encode("latin-1"))
    path = tmp_path / "multi.pdf"
    doc.save(path)
    with pymupdf.open(path) as d:
        texts = [g.text for g in read_glyphs(d[0])]
    assert "\u0644\u0627" in texts
    assert "\ufefb" not in texts


def test_mark_prefers_the_letter_in_its_drawing_run():
    # the mark sits on the shared edge of two letters; the run decides
    teh = glyph("ط", 100, 106, seq=1)
    alef = glyph("ا", 96, 100, seq=2)
    shadda = glyph("ّ", 100, 100, seq=1)
    attach_marks([alef, shadda, teh])
    assert teh.marks and not alef.marks


def test_mark_on_ligature_goes_after_the_right_letter():
    lam_alef = glyph("ﻻ", 100, 112, seq=1)
    fatha = glyph("َ", 109, 109, seq=1)  # right part of the glyph: the lam
    attach_marks([fatha, lam_alef])
    assert lam_alef.full_text == "لَا"
