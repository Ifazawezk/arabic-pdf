from helpers import visual_glyphs

from arabic_pdf.layout import Line, line_signature, remove_running_text


def line(text, y, x=100):
    ln = Line(visual_glyphs(text, x=x, baseline=y))
    ln.text = text
    return ln


def page(body, header=None, footer=None):
    lines = []
    if header:
        lines.append(line(header, 40))
    lines.append(line(body, 400))
    if footer:
        lines.append(line(footer, 810))
    return lines


def texts(pages):
    return [[ln.text for ln in p] for p in pages]


def test_signature_ignores_western_and_arabic_digits():
    assert line_signature("page 3 of 10") == line_signature("page 12 of 10")
    assert line_signature("صفحة ٣") == line_signature("صفحة 12")


def test_repeated_header_and_page_numbers_removed():
    pages = [page(f"body {i}", "Annual report", f"page {i} of 3") for i in range(1, 4)]
    out = remove_running_text(pages, [842.0] * 3)
    assert texts(out) == [["body 1"], ["body 2"], ["body 3"]]


def test_bare_page_numbers_removed():
    pages = [page(f"body {i}", footer=str(i)) for i in range(1, 5)]
    assert texts(remove_running_text(pages, [842.0] * 4)) == [[f"body {i}"] for i in range(1, 5)]


def test_alternating_headers_removed():
    pages = [page(f"body {i}", "Odd title" if i % 2 else "Even title") for i in range(1, 7)]
    assert texts(remove_running_text(pages, [842.0] * 6)) == [[f"body {i}"] for i in range(1, 7)]


def test_repeated_line_in_the_middle_of_a_page_is_kept():
    pages = [[line("same line", 400)] for _ in range(3)]
    assert texts(remove_running_text(pages, [842.0] * 3)) == [["same line"]] * 3


def test_single_page_keeps_everything():
    pages = [page("body", "title", "1")]
    assert texts(remove_running_text(pages, [842.0])) == [["title", "body", "1"]]


def test_one_off_margin_line_is_kept():
    pages = [page("body 1", "only here"), page("body 2"), page("body 3")]
    assert texts(remove_running_text(pages, [842.0] * 3))[0] == ["only here", "body 1"]
