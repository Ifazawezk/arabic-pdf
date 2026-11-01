from pathlib import Path

import pymupdf
import pytest

from arabic_pdf import extract, extract_text, ocr
from arabic_pdf.glyphs import Glyph, read_glyphs
from arabic_pdf.metrics import cer

CORPUS = Path(__file__).resolve().parent.parent / "corpus"
needs_data = pytest.mark.skipif(ocr.find_tessdata("ara") is None, reason="Arabic Tesseract data not installed")


def glyph(text):
    return Glyph(text, 0, 0, 5, 10, 8, 10)


def test_is_unmapped():
    assert ocr.is_unmapped(chr(0xFFFD))
    assert ocr.is_unmapped(chr(0xE123))
    assert not ocr.is_unmapped("ب")


def test_scanned_page_needs_ocr():
    with pymupdf.open(CORPUS / "scanned_simple_arial.pdf") as doc:
        assert ocr.needs_ocr(doc[0], read_glyphs(doc[0]))


def test_page_with_text_does_not_need_ocr():
    with pymupdf.open(CORPUS / "browser_simple_arial.pdf") as doc:
        assert not ocr.needs_ocr(doc[0], read_glyphs(doc[0]))


def test_blank_page_does_not_need_ocr():
    doc = pymupdf.open()
    page = doc.new_page()
    assert not ocr.needs_ocr(page, [])


def test_text_layer_of_unmapped_glyphs_needs_ocr():
    doc = pymupdf.open()
    page = doc.new_page()
    assert ocr.needs_ocr(page, [glyph(chr(0xFFFD))] * 30 + [glyph("a")] * 10)
    assert not ocr.needs_ocr(page, [glyph(chr(0xFFFD))] * 2 + [glyph("a")] * 40)


def test_usable_languages_skips_missing_data(tmp_path):
    (tmp_path / "ara.traineddata").write_bytes(b"x")
    assert ocr.usable_languages("ara+eng", str(tmp_path)) == "ara"
    assert ocr.usable_languages("fra", str(tmp_path)) is None


def test_prefix_variable_wins(tmp_path, monkeypatch):
    (tmp_path / "ara.traineddata").write_bytes(b"x")
    monkeypatch.setenv("TESSDATA_PREFIX", str(tmp_path))
    assert ocr.find_tessdata("ara") == str(tmp_path)


def test_missing_language_data_is_reported_not_fatal(monkeypatch):
    monkeypatch.setattr(ocr, "find_tessdata", lambda language="ara": None)
    with pytest.warns(UserWarning, match="Tesseract"):
        document = extract(CORPUS / "scanned_simple_arial.pdf")
    assert document.pages[0].needs_ocr
    assert not document.pages[0].ocr
    assert document.blocks == []


def test_ocr_never_flags_the_page():
    document = extract(CORPUS / "scanned_simple_arial.pdf", ocr="never")
    assert document.pages[0].needs_ocr and document.blocks == []


def test_bad_ocr_mode_is_rejected():
    with pytest.raises(ValueError):
        extract(CORPUS / "browser_simple_arial.pdf", ocr="sometimes")


def test_text_pages_skip_ocr():
    assert not extract(CORPUS / "browser_simple_arial.pdf").pages[0].ocr


def test_unmapped_glyphs_are_counted():
    assert extract(CORPUS / "browser_simple_typesetting.pdf").pages[0].unmapped_glyphs > 0
    assert extract(CORPUS / "browser_simple_arial.pdf").pages[0].unmapped_glyphs == 0


@needs_data
def test_scanned_arabic_page_is_read():
    truth = (CORPUS / "scanned_simple_arial.txt").read_text(encoding="utf-8")
    document = extract(CORPUS / "scanned_simple_arial.pdf")
    assert document.pages[0].ocr
    assert cer(truth, extract_text(CORPUS / "scanned_simple_arial.pdf")) < 0.25
