"""Run the whole pipeline over the corpus and compare with the ground truth."""

import json
from pathlib import Path

import pytest

from arabic_pdf import extract, extract_markdown, extract_text
from arabic_pdf.metrics import cer, word_order
from arabic_pdf.normalize import is_presentation_form

CORPUS = Path(__file__).resolve().parent.parent / "corpus"
MANIFEST = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
TEXT_DOCS = [d["id"] for d in MANIFEST if d["category"] != "scanned"]

# documents with a known leftover, and what causes it
KNOWN_ERRORS = {
    "browser_simple_typesetting": 0.01,  # glyphs the PDF does not map to Unicode
    "browser_simple_majalla": 0.01,      # same
    "browser_english_arabic": 0.03,      # one number between Arabic and Latin words is ambiguous
}


def truth(doc_id):
    return (CORPUS / f"{doc_id}.txt").read_text(encoding="utf-8")


@pytest.mark.parametrize("doc_id", TEXT_DOCS)
def test_text_layer_documents_match_the_ground_truth(doc_id):
    text = extract_text(CORPUS / f"{doc_id}.pdf")
    assert cer(truth(doc_id), text) <= KNOWN_ERRORS.get(doc_id, 0.0)


@pytest.mark.parametrize("doc_id", TEXT_DOCS)
def test_word_order_is_right(doc_id):
    assert word_order(truth(doc_id), extract_text(CORPUS / f"{doc_id}.pdf")) >= 0.9


@pytest.mark.parametrize("doc_id", TEXT_DOCS)
def test_no_presentation_forms_left(doc_id):
    text = extract_text(CORPUS / f"{doc_id}.pdf")
    assert not [c for c in text if is_presentation_form(c)]


def test_lam_alef_survives_in_both_kinds_of_pdf():
    for doc_id in ("legacy_simple_arial", "browser_simple_segoe"):
        text = extract_text(CORPUS / f"{doc_id}.pdf")
        assert "لا" in text
        assert "العملية" in text or "الع" in text


def test_two_columns_read_right_column_first():
    text = extract_text(CORPUS / "browser_two_column_times.pdf")
    assert text.index("تشير دراسات") < text.index("تحظى الصقور")


def test_running_text_is_gone():
    text = extract_text(CORPUS / "legacy_headers_tahoma.pdf")
    assert "التقرير السنوي" not in text
    assert "صفحة 2 من 3" not in text


def test_markdown_has_headings_and_table():
    md = extract_markdown(CORPUS / "legacy_table_arial.pdf")
    assert md.startswith("# فاتورة مشتريات")
    assert "| --- |" in md


def test_blocks_carry_positions_on_the_page():
    document = extract(CORPUS / "browser_simple_arial.pdf")
    page = document.pages[0]
    for block in page.blocks:
        x0, y0, x1, y1 = block.bbox
        assert 0 <= x0 < x1 <= page.width and 0 <= y0 < y1 <= page.height
