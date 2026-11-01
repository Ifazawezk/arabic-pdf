import pymupdf

from arabic_pdf import extract_text


def test_extract_simple_latin_pdf(tmp_path):
    path = tmp_path / "hello.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello PDF", fontsize=14)
    doc.save(path)

    assert extract_text(str(path)) == "Hello PDF"
