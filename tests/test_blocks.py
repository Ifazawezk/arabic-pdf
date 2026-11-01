from helpers import visual_glyphs

from arabic_pdf.blocks import group_paragraphs, mark_headings, page_blocks
from arabic_pdf.document import Block, Document, Page
from arabic_pdf.layout import Line, page_lines


def lines_of(*spec):
    """spec: (text, baseline) tuples, one line each, all flush with x=100."""
    out = []
    for text, base in spec:
        ln = Line(visual_glyphs(text, baseline=base))
        ln.text = text
        out.append(ln)
    return out


def test_lines_with_normal_spacing_form_one_paragraph():
    lines = lines_of(("a" * 40, 100), ("b" * 40, 120), ("c" * 20, 140))
    assert [len(g) for g in group_paragraphs(lines)] == [3]


def test_wider_gap_starts_a_new_paragraph():
    lines = lines_of(("a" * 40, 100), ("b" * 40, 120), ("c" * 40, 140), ("d" * 40, 175), ("e" * 40, 195))
    assert [len(g) for g in group_paragraphs(lines)] == [3, 2]


def test_short_line_ends_a_paragraph():
    lines = lines_of(("a" * 40, 100), ("b" * 10, 120), ("c" * 40, 140), ("d" * 40, 160))
    assert [len(g) for g in group_paragraphs(lines)] == [2, 2]


def test_paragraph_decides_direction_for_a_mostly_latin_line():
    # an Arabic paragraph whose second line is mostly Latin must stay right to left
    first = visual_glyphs("ﺔﻠﻳﻮﻃ ﺔﻴﺑﺮﻋ ﺔﻠﻤﺟ ﻩﺬﻫ ﺔﻠﻤﺟ ﻩﺬﻫ ﺔﻠﻤﺟ ﻩﺬﻫ", baseline=100)
    second = visual_glyphs("Power BI ﻭ Microsoft Excel", baseline=120)
    blocks = page_blocks(page_lines(first + second, page_rtl=True), page_rtl=True)
    assert len(blocks) == 1
    assert blocks[0].text.endswith("Microsoft Excel و Power BI")


def doc_with(*sizes):
    blocks = [Block("paragraph", "x" * 200, (0, i * 100, 400, i * 100 + 80), size=12.0) for i in range(3)]
    blocks += [Block("paragraph", "title", (0, 400 + i * 50, 100, 400 + i * 50 + s * 1.3), size=s)
               for i, s in enumerate(sizes)]
    return Document("x.pdf", [Page(1, 595, 842, blocks)])


def test_headings_by_size_with_levels():
    doc = doc_with(24.0, 18.0, 24.0, 18.0)
    mark_headings(doc)
    heads = [b for b in doc.blocks if b.kind == "heading"]
    assert [b.level for b in heads] == [1, 2, 1, 2]


def test_body_text_is_not_a_heading():
    doc = doc_with(12.0)
    mark_headings(doc)
    assert all(b.kind == "paragraph" for b in doc.blocks)


def test_a_long_block_of_big_text_is_not_a_heading():
    doc = doc_with()
    doc.pages[0].blocks.append(Block("paragraph", "x" * 900, (0, 500, 400, 800), size=16.0))
    mark_headings(doc)
    assert all(b.kind == "paragraph" for b in doc.blocks)


def test_one_line_paragraphs_stay_apart():
    # every step on this page is a paragraph step, so the median alone can't show it
    lines = lines_of(("a" * 40, 100), ("b" * 40, 130), ("c" * 40, 160), ("d" * 40, 190))
    assert [len(g) for g in group_paragraphs(lines)] == [1, 1, 1, 1]


def test_double_spaced_text_stays_one_paragraph():
    lines = lines_of(("a" * 40, 100), ("b" * 40, 124), ("c" * 40, 148), ("d" * 40, 172))
    assert [len(g) for g in group_paragraphs(lines)] == [4]
