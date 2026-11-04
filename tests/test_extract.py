import pymupdf

from arabic_pdf import extract, extract_markdown, extract_text


def test_extract_simple_latin_pdf(tmp_path):
    path = tmp_path / "hello.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello PDF", fontsize=14)
    doc.save(path)

    assert extract_text(str(path)) == "Hello PDF"


def pages_pdf(path, pages):
    """One line of Latin text per entry, 18 points apart, starting well clear of the header band."""
    doc = pymupdf.open()
    for lines in pages:
        page = doc.new_page()
        for i, text in enumerate(lines):
            page.insert_text((72, 300 + 18 * i), text, fontsize=12)
    doc.save(path)
    return path


CUT = [
    ["Reading a few pages every day builds a habit that lasts",
     "for years, and the time just before sleep is often the"],
    ["easiest part of the day to keep free for a short book.",
     "Phones stay in the other room."],
]


def test_paragraph_cut_by_a_page_break_is_joined(tmp_path):
    path = pages_pdf(tmp_path / "cut.pdf", CUT)
    assert extract_text(path) == (
        "Reading a few pages every day builds a habit that lasts for years, and the time just before "
        "sleep is often the easiest part of the day to keep free for a short book. Phones stay in the other room."
    )
    document = extract(path)
    assert [b.continues for p in document.pages for b in p.blocks] == [True, False]
    assert "easiest part" in extract_markdown(path).split("\n\n")[0]


def test_paragraph_that_ends_on_a_page_stays_separate(tmp_path):
    ended = [CUT[0][:1] + ["for years, and the time before sleep is best for it."], CUT[1]]
    path = pages_pdf(tmp_path / "ended.pdf", ended)
    assert len(extract_text(path).split("\n\n")) == 2


def test_pages_that_are_not_next_to_each_other_are_not_joined(tmp_path):
    path = pages_pdf(tmp_path / "gap.pdf", [CUT[0], ["A page in between."], CUT[1]])
    document = extract(path, pages=[1, 3])
    assert not any(b.continues for p in document.pages for b in p.blocks)
