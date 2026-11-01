import subprocess
import sys
from pathlib import Path

import pymupdf
from helpers import visual_glyphs

from arabic_pdf import extract, extract_markdown
from arabic_pdf.layout import is_rtl
from arabic_pdf.tables import TableGrid, cell_text, find_grids, read_table, split_table_glyphs

CORPUS = Path(__file__).resolve().parent.parent / "corpus"


def grid_2x2():
    left, right = (100, 100, 200, 130), (200, 100, 300, 130)
    left2, right2 = (100, 130, 200, 160), (200, 130, 300, 160)
    return TableGrid((100, 100, 300, 160), [[left, right], [left2, right2]])


def cell(text, x, baseline):
    return visual_glyphs(text, x=x, baseline=baseline, size=10, advance=5)


def test_arabic_table_cells_read_right_to_left():
    # visual strings: the right column holds the first logical cell
    glyphs = cell("ةيمكلا", 110, 120) + cell("مسالا", 210, 120) + cell("3", 110, 150) + cell("ةراس", 210, 150)
    rows, rtl = read_table(grid_2x2(), glyphs, True, True)
    assert rtl
    assert rows == [["الاسم", "الكمية"], ["سارة", "3"]]


def test_latin_table_keeps_left_to_right_cells():
    glyphs = cell("name", 110, 120) + cell("team", 210, 120) + cell("sara", 110, 150) + cell("data", 210, 150)
    rows, rtl = read_table(grid_2x2(), glyphs, True, True)
    assert not rtl
    assert rows == [["name", "team"], ["sara", "data"]]


def test_number_with_unit_in_arabic_table():
    # "7,350 QAR" alone in a right to left cell is painted "QAR 7,350"
    assert cell_text(cell("QAR 7,350", 110, 120), rtl=True, arabic_variants=True) == "7,350 QAR"


def test_merged_cell_stays_empty():
    grid = grid_2x2()
    grid.cells[1][1] = None
    rows, _ = read_table(grid, cell("abcd", 110, 120), False, True)
    assert rows[1] == ["", ""]


def test_glyphs_inside_a_table_leave_the_text_flow():
    inside = cell("abcd", 110, 120)
    outside = cell("wxyz", 110, 300)
    flow, tables = split_table_glyphs(inside + outside, [grid_2x2()])
    assert flow == outside
    assert tables == [inside]
    assert not is_rtl(flow)


def test_one_box_is_not_a_table():
    doc = pymupdf.open()
    page = doc.new_page()
    page.draw_rect((100, 100, 400, 300))
    page.insert_text((120, 150), "boxed note", fontsize=12)
    assert find_grids(page) == []


def test_corpus_tables_become_markdown_tables():
    md = extract_markdown(CORPUS / "browser_table_arial.pdf")
    assert "| المنتج | الكمية | سعر الوحدة | الإجمالي |" in md
    assert "| حاسوب محمول | 3 | 2,450 QAR | 7,350 QAR |" in md


def test_table_sits_between_the_text_around_it():
    kinds = [b.kind for b in extract(CORPUS / "legacy_table_arial.pdf").blocks]
    assert kinds == ["heading", "paragraph", "table", "paragraph"]


def test_two_tables_on_a_page_keep_their_order():
    blocks = extract(CORPUS / "browser_table_tahoma.pdf").blocks
    tables = [b for b in blocks if b.kind == "table"]
    assert [t.rows[0][0] for t in tables] == ["الشهر", "الاسم"]


def test_no_tables_option_leaves_text_in_the_flow():
    assert all(b.kind != "table" for b in extract(CORPUS / "browser_table_arial.pdf", tables=False).blocks)


def test_cli_stdout_holds_only_the_extracted_text():
    # find_tables() prints a package recommendation unless it is switched off
    out = subprocess.run(
        [sys.executable, "-m", "arabic_pdf.cli", str(CORPUS / "browser_table_arial.pdf")],
        capture_output=True, check=True,
    ).stdout.decode("utf-8")
    assert "pymupdf" not in out.lower()
    assert out.startswith("فاتورة مشتريات")
