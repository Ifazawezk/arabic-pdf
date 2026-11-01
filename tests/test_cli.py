import argparse
import json
import shutil
from pathlib import Path

import pymupdf
import pytest

from arabic_pdf import extract
from arabic_pdf.cli import main, output_path, parse_pages

CORPUS = Path(__file__).resolve().parent.parent / "corpus"
SIMPLE = CORPUS / "browser_simple_arial.pdf"
PAGED = CORPUS / "browser_headers_arial.pdf"


def test_parse_pages():
    assert parse_pages("1-3,7") == [1, 2, 3, 7]
    assert parse_pages("5") == [5]
    assert parse_pages("3,1-2,2") == [1, 2, 3]


@pytest.mark.parametrize("bad", ["0", "3-1", "a", "1-b", ""])
def test_parse_pages_rejects_bad_input(bad):
    with pytest.raises(argparse.ArgumentTypeError):
        parse_pages(bad)


@pytest.mark.parametrize("name,marker", [("out.md", "# "), ("out.txt", None), ("out.json", '"pages"')])
def test_format_follows_the_extension(tmp_path, name, marker):
    out = tmp_path / name
    assert main([str(SIMPLE), "-o", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    if marker:
        assert marker in text
    else:
        assert not text.startswith("#")


def test_explicit_format_wins_over_the_extension(tmp_path):
    out = tmp_path / "out.txt"
    assert main([str(SIMPLE), "-o", str(out), "-f", "markdown"]) == 0
    assert out.read_text(encoding="utf-8").startswith("# ")


def test_stdout_is_utf8_text(capfdbinary):
    assert main([str(SIMPLE)]) == 0
    assert capfdbinary.readouterr().out.decode("utf-8").startswith("البيئة والطاقة")


def test_json_has_pages_blocks_and_positions(tmp_path):
    out = tmp_path / "out.json"
    assert main([str(SIMPLE), "-o", str(out)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    block = data["pages"][0]["blocks"][0]
    assert block["kind"] == "heading" and block["level"] == 1
    assert len(block["bbox"]) == 4 and block["bbox"][2] > block["bbox"][0]
    assert data["pages"][0]["number"] == 1


def test_page_range_selects_pages(tmp_path):
    out = tmp_path / "out.json"
    assert main([str(PAGED), "-o", str(out), "-p", "2-3"]) == 0
    assert [p["number"] for p in json.loads(out.read_text(encoding="utf-8"))["pages"]] == [2, 3]


def test_pages_past_the_end_are_ignored():
    assert [p.number for p in extract(PAGED, pages=[3, 99]).pages] == [3]


def test_keep_headers_flag(tmp_path):
    out = tmp_path / "out.txt"
    assert main([str(PAGED), "-o", str(out), "--keep-headers"]) == 0
    assert "دليل الطالب" in out.read_text(encoding="utf-8")
    assert main([str(PAGED), "-o", str(out)]) == 0
    assert "دليل الطالب" not in out.read_text(encoding="utf-8")


def test_batch_folder(tmp_path):
    folder = tmp_path / "in"
    (folder / "sub").mkdir(parents=True)
    shutil.copy(SIMPLE, folder / "a.pdf")
    shutil.copy(SIMPLE, folder / "sub" / "b.pdf")
    (folder / "notes.txt").write_text("skip me", encoding="utf-8")
    out = tmp_path / "out"

    assert main([str(folder), "-o", str(out), "-f", "markdown"]) == 0
    assert sorted(p.name for p in out.iterdir()) == ["a.md"]

    assert main([str(folder), "-o", str(out), "-f", "markdown", "-r"]) == 0
    assert (out / "sub" / "b.md").exists()


def test_same_name_in_two_folders_does_not_collide(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    out = tmp_path / "out"
    assert output_path(a / "x.pdf", [a], out, ".md") == out / "x.md"
    nested = output_path(a / "s" / "x.pdf", [a], out, ".md")
    assert nested == out / "s" / "x.md" and nested != output_path(a / "x.pdf", [a], out, ".md")


def test_batch_survives_a_broken_file(tmp_path, capsys):
    folder = tmp_path / "in"
    folder.mkdir()
    shutil.copy(SIMPLE, folder / "good.pdf")
    (folder / "bad.pdf").write_bytes(b"this is not a pdf")
    out = tmp_path / "out"
    assert main([str(folder), "-o", str(out)]) == 1
    assert (out / "good.txt").exists()
    assert "failed" in capsys.readouterr().err


def test_empty_folder_is_an_error(tmp_path, capsys):
    assert main([str(tmp_path)]) == 1
    assert "no PDF" in capsys.readouterr().err


def test_several_inputs_cannot_go_to_one_file(tmp_path):
    with pytest.raises(SystemExit):
        main([str(SIMPLE), str(PAGED), "-o", str(tmp_path / "out.md")])


def test_scan_without_ocr_is_reported(capsys):
    assert main([str(CORPUS / "scanned_simple_arial.pdf"), "--ocr", "never"]) == 0
    assert "no text on page" in capsys.readouterr().err


def test_password_protected_pdf_fails_cleanly(tmp_path):
    path = tmp_path / "locked.pdf"
    doc = pymupdf.open(SIMPLE)
    doc.save(path, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="secret", owner_pw="secret")
    with pytest.raises(ValueError, match="password"):
        extract(path)
    assert main([str(path)]) == 1
