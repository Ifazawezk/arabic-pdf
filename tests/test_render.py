import json

from arabic_pdf.document import Block, Document, Page
from arabic_pdf.render import markdown_table, to_json, to_markdown, to_text


def sample():
    table = Block("table", "", (0, 0, 10, 10), rows=[["الاسم", "القسم"], ["سارة", "البيانات"]])
    head = Block("heading", "عنوان", (0, 0, 10, 10), level=2)
    para = Block("paragraph", "نص الفقرة", (0, 0, 10, 10))
    return Document("x.pdf", [Page(1, 595, 842, [head, para, table])])


def test_markdown_output():
    assert to_markdown(sample()) == (
        "## عنوان\n\nنص الفقرة\n\n| الاسم | القسم |\n| --- | --- |\n| سارة | البيانات |"
    )


def test_text_output_uses_tabs_for_cells():
    assert to_text(sample()).endswith("الاسم\tالقسم\nسارة\tالبيانات")


def test_pipe_in_cell_is_escaped():
    assert r"a\|b" in markdown_table([["a|b"], ["c"]])


def test_short_rows_are_padded():
    assert markdown_table([["a", "b"], ["c"]]).splitlines()[-1] == "| c |  |"


def test_json_keeps_positions_and_arabic():
    data = json.loads(to_json(sample()))
    assert data["pages"][0]["blocks"][0]["bbox"] == [0, 0, 10, 10]
    assert "عنوان" in to_json(sample())
