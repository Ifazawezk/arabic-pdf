"""Regressions for problems found on real government PDFs.

Each test rebuilds the condition in a small PDF, so the suite does not need
the third party files themselves. See bench/real_world.py for the sources.
"""

from collections import Counter
from pathlib import Path

import pymupdf
import pytest

from arabic_pdf import extract, extract_text
from arabic_pdf.glyphs import (
    choose_ligatures,
    quarter_turns,
    read_glyphs,
    rotate_rect,
    scan_actual_text,
    unrotate_rect,
)
from arabic_pdf.ocr import _line_glyphs
from arabic_pdf.tables import TableGrid, rotate_grid

CORPUS = Path(__file__).resolve().parent.parent / "corpus"
SENTENCE = "The rotated table must not be lost"


def pdf_path(tmp_path, build):
    path = tmp_path / "doc.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    build(doc, page)
    doc.save(path)
    return path


@pytest.mark.parametrize("dx,dy,expected", [(1, 0, 0), (0, -1, 1), (-1, 0, 2), (0, 1, 3), (0.7, 0.7, None)])
def test_quarter_turns(dx, dy, expected):
    assert quarter_turns(dx, dy) == expected


@pytest.mark.parametrize("quarter", [0, 1, 2, 3])
def test_rotation_round_trip(quarter):
    rect = (100.0, 200.0, 180.0, 215.0)
    turned = rotate_rect(rect, quarter, 595.0, 842.0)
    assert unrotate_rect(turned, quarter, 595.0, 842.0) == pytest.approx(rect)


@pytest.mark.parametrize("rotate", [90, 180, 270])
def test_text_set_at_a_right_angle_is_kept(tmp_path, rotate):
    def build(doc, page):
        page.insert_text((300, 400), SENTENCE, fontsize=12, rotate=rotate)

    assert extract_text(pdf_path(tmp_path, build)).strip() == SENTENCE


def test_sideways_lines_stay_in_order(tmp_path):
    # a landscape block on a portrait page: lines run up the page, left to right
    def build(doc, page):
        for i, word in enumerate(["first line here", "second line here", "third line here"]):
            page.insert_text((100 + i * 20, 500), word, fontsize=12, rotate=90)

    assert extract_text(pdf_path(tmp_path, build)).split() == (
        "first line here second line here third line here".split()
    )


def test_diagonal_watermark_is_dropped(tmp_path):
    def build(doc, page):
        page.insert_text((72, 100), SENTENCE, fontsize=12)
        matrix = pymupdf.Matrix(45)
        shape = page.new_shape()
        shape.insert_text((200, 400), "DRAFT COPY", fontsize=40, morph=(pymupdf.Point(200, 400), matrix))
        shape.commit()

    assert extract_text(pdf_path(tmp_path, build)).strip() == SENTENCE


def test_upright_and_sideways_text_on_one_page(tmp_path):
    def build(doc, page):
        page.insert_text((72, 100), "main text of the page", fontsize=12)
        page.insert_text((40, 700), "a note in the margin", fontsize=9, rotate=90)

    text = extract_text(pdf_path(tmp_path, build))
    assert "main text of the page" in text and "a note in the margin" in text


def test_sideways_block_has_page_coordinates_and_rotation(tmp_path):
    def build(doc, page):
        page.insert_text((300, 500), SENTENCE, fontsize=12, rotate=90)

    document = extract(pdf_path(tmp_path, build))
    block = document.pages[0].blocks[0]
    x0, y0, x1, y1 = block.bbox
    assert block.rotation == 90
    assert y1 - y0 > x1 - x0  # tall and narrow on the page
    assert 280 < x0 < x1 < 320 and y1 <= 510


def test_page_level_rotation(tmp_path):
    # /Rotate on the page is a different mechanism from rotated text
    def build(doc, page):
        page.insert_text((72, 100), SENTENCE, fontsize=12)
        page.set_rotation(90)

    assert extract_text(pdf_path(tmp_path, build)).strip() == SENTENCE


def test_rotated_grid_rebuilds_rows_and_columns():
    # two rows of two cells, turned a quarter: rows become columns
    grid = TableGrid((100, 100, 300, 160), [
        [(100, 100, 200, 130), (200, 100, 300, 130)],
        [(100, 130, 200, 160), (200, 130, 300, 160)],
    ])
    turned = rotate_grid(grid, 1, 595, 842)
    assert len(turned.cells) == 2 and len(turned.cells[0]) == 2
    assert all(c is not None for row in turned.cells for c in row)
    assert turned.cells[0][0][1] < turned.cells[1][0][1]


def test_rotated_grid_keeps_merged_cells_empty():
    grid = TableGrid((100, 100, 300, 160), [
        [(100, 100, 300, 130), None],
        [(100, 130, 200, 160), (200, 130, 300, 160)],
    ])
    turned = rotate_grid(grid, 3, 595, 842)
    assert sum(c is None for row in turned.cells for c in row) == 1


def test_digit_shown_by_actual_text(tmp_path):
    # the glyph is the digit 3, /ActualText says the Arabic-Indic digit on the page
    def build(doc, page):
        page.insert_text((72, 100), "3", fontsize=12)
        page.clean_contents()
        xref = page.get_contents()[0]
        body = doc.xref_stream(xref)
        doc.update_stream(xref, b"/Span <</ActualText <FEFF0663>>> BDC\n" + body + b"\nEMC\n")

    path = pdf_path(tmp_path, build)
    with pymupdf.open(path) as doc:
        assert [g.text for g in read_glyphs(doc[0])] == ["٣"]


def test_western_digits_stay_without_actual_text(tmp_path):
    def build(doc, page):
        page.insert_text((72, 100), "2026", fontsize=12)

    path = pdf_path(tmp_path, build)
    with pymupdf.open(path) as doc:
        assert "".join(g.text for g in read_glyphs(doc[0])) == "2026"


def char(text, x0, x1, y1):
    return {"c": text, "bbox": (x0, y1 - 12, x1, y1), "origin": (x0, y1)}


def ocr_line(chars, size=12.0):
    return {"spans": [{"size": size, "chars": chars}]}


def test_ocr_lines_with_the_same_box_are_not_woven_together():
    # Tesseract can report two close lines with one vertical range
    placed = []
    first = _line_glyphs(ocr_line([char("a", 100, 110, 150), char("b", 110, 120, 150)]), placed)
    second = _line_glyphs(ocr_line([char("c", 100, 110, 150), char("d", 110, 120, 150)]), placed)
    assert first[0].baseline < second[0].baseline
    assert second[0].baseline - first[0].baseline > 0.45 * 12


def test_ocr_words_side_by_side_share_a_line():
    placed = []
    right = _line_glyphs(ocr_line([char("a", 300, 310, 150)]), placed)
    left = _line_glyphs(ocr_line([char("b", 100, 110, 150)]), placed)
    assert right[0].baseline == left[0].baseline


def test_ocr_spaces_are_dropped():
    assert [g.text for g in _line_glyphs(ocr_line([char(" ", 100, 200, 150), char("a", 100, 110, 150)]), [])] == ["a"]


def test_actual_text_is_read_per_glyph_and_font():
    content = (b"/T1 1 Tf /Span<</ActualText<FEFF06440627>>> BDC <0085>Tj EMC "
               b"/T2 1 Tf /Span<</ActualText<FEFF064A0646>>> BDC <00F5>Tj EMC")
    counts = {}
    scan_actual_text(content, {"T1": "Muna", "T2": "MunaBold"}, counts)
    assert counts == {("Muna", 0x85): Counter({"لا": 1}), ("MunaBold", 0xF5): Counter({"ين": 1})}


def test_spans_over_several_glyphs_teach_nothing():
    counts = {}
    scan_actual_text(b"/T1 1 Tf /Span<</ActualText<FEFF06630661>>> BDC <009D009B>Tj EMC", {"T1": "Muna"}, counts)
    assert counts == {}


def test_a_font_set_inside_the_span_counts():
    counts = {}
    scan_actual_text(b"/Span<</ActualText<FEFF06440627>>> BDC /T1 1 Tf <0085>Tj EMC", {"T1": "Muna"}, counts)
    assert ("Muna", 0x85) in counts


def test_clear_majority_is_learned():
    chosen = choose_ligatures({("Muna", 133): Counter({"لا": 259, "ا": 10})})
    assert chosen == {("Muna", 133): "لا"}


def test_contradicting_declarations_are_ignored():
    assert choose_ligatures({("Muna", 245): Counter({"ين": 5, "ن": 5})}) == {}


def test_single_letters_and_symbols_are_not_ligatures():
    assert choose_ligatures({("Muna", 3): Counter({".": 9}), ("Muna", 73): Counter({"٫": 9})}) == {}


def test_learned_ligature_replaces_the_mapped_letter():
    with pymupdf.open(CORPUS / "browser_simple_arial.pdf") as doc:
        page = doc[0]
        span = next(s for s in page.get_texttrace() if any(c[0] == 0x0627 for c in s["chars"]))
        gid = next(c[1] for c in span["chars"] if c[0] == 0x0627)
        learned = {(span["font"].split("+")[-1], gid): "لا"}
        texts = [g.text for g in read_glyphs(page, ligatures=learned)]
    assert "لا" in texts


def test_learned_ligature_must_contain_the_mapped_letter():
    with pymupdf.open(CORPUS / "browser_simple_arial.pdf") as doc:
        page = doc[0]
        span = next(s for s in page.get_texttrace() if any(c[0] == 0x0627 for c in s["chars"]))
        gid = next(c[1] for c in span["chars"] if c[0] == 0x0627)
        learned = {(span["font"].split("+")[-1], gid): "ين"}
        texts = [g.text for g in read_glyphs(page, ligatures=learned)]
    assert "ين" not in texts
