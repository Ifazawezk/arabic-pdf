from helpers import visual_glyphs

from arabic_pdf.layout import build_rows, find_gutters, page_lines, split_row, with_spaces


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


def two_column_rows(rows=6, left_x=60, right_x=320, width=30):
    """Glyphs of a page with two columns of aligned lines."""
    glyphs = []
    for i in range(rows):
        base = 100 + i * 20
        glyphs += visual_glyphs("a" * width, x=left_x, baseline=base)
        glyphs += visual_glyphs("b" * width, x=right_x, baseline=base)
    return glyphs


def test_gutter_found_between_two_columns():
    gutters = find_gutters(build_rows(two_column_rows()))
    assert len(gutters) == 1
    a, b = gutters[0]
    assert a >= 240 and b <= 320


def test_no_gutter_in_single_column_with_word_gaps():
    glyphs = []
    for i in range(10):
        glyphs += visual_glyphs(("word " * 12).strip(), x=60 + (i % 3) * 7, baseline=100 + i * 20)
    assert find_gutters(build_rows(glyphs)) == []


def test_two_columns_are_not_interleaved():
    lines = page_lines(two_column_rows(rows=3), page_rtl=False)
    assert [ln.text[0] for ln in lines] == ["a", "a", "a", "b", "b", "b"]


def test_rtl_page_reads_right_column_first():
    lines = page_lines(two_column_rows(rows=3), page_rtl=True)
    assert [ln.text[0] for ln in lines] == ["b", "b", "b", "a", "a", "a"]


def test_full_width_title_stays_above_the_columns():
    title = visual_glyphs("t" * 75, x=60, baseline=70)
    lines = page_lines(title + two_column_rows(rows=4), page_rtl=True)
    assert lines[0].text.startswith("t")
    assert [ln.text[0] for ln in lines[1:]] == ["b"] * 4 + ["a"] * 4


def test_unbalanced_columns_still_found():
    # the left column has only three lines, the right one has many
    glyphs = two_column_rows(rows=3)
    for i in range(3, 12):
        glyphs += visual_glyphs("b" * 30, x=320, baseline=100 + i * 20)
    lines = page_lines(glyphs, page_rtl=True)
    assert [ln.text[0] for ln in lines] == ["b"] * 12 + ["a"] * 3
