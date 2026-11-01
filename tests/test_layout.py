from helpers import visual_glyphs

from arabic_pdf.layout import build_rows, page_lines, split_row, with_spaces


def test_rows_group_by_baseline():
    a = visual_glyphs("abc", baseline=100)
    b = visual_glyphs("def", baseline=130)
    rows = build_rows(b + a)
    assert ["".join(x.text for x in r) for r in rows] == ["abc", "def"]


def test_space_inserted_at_gap():
    left = visual_glyphs("ab", x=100)
    right = visual_glyphs("cd", x=100 + 12 + 5)  # 5pt gap at size 12
    assert "".join(x.text for x in with_spaces(left + right)) == "ab cd"


def test_wide_gap_splits_row():
    left = visual_glyphs("ab", x=100)
    right = visual_glyphs("cd", x=300)
    assert len(split_row(left + right)) == 2


def test_page_lines_arabic_logical_order():
    glyphs = visual_glyphs("\ufee2\ufedc\ufef4\ufee0\ufecb \ufee1\ufefc\ufeb3", baseline=100) + visual_glyphs("\ufe8e\ufe92\ufea3\ufeae\ufee3", baseline=130)
    lines = page_lines(glyphs, page_rtl=True)
    assert [ln.text for ln in lines] == ["سلام عليكم", "مرحبا"]


def test_overlapping_glyphs_sort_by_centre():
    from arabic_pdf.glyphs import Glyph

    alef = Glyph("a", 211.4, 90, 214.3, 103, 100, 12)
    reh = Glyph("b", 210.9, 90, 217.8, 103, 100, 12)  # starts left of alef, ends right of it
    assert [g.text for g in build_rows([reh, alef])[0]] == ["a", "b"]
