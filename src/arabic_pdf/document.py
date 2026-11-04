"""The structured result of an extraction."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Block:
    """A heading, paragraph or table, in reading order."""

    kind: str  # "heading", "paragraph" or "table"
    text: str
    bbox: tuple[float, float, float, float]
    rtl: bool = True
    size: float = 0.0
    level: int = 0  # heading level, 1 is the largest
    rows: list[list[str]] = field(default_factory=list)  # table rows in reading order
    rotation: int = 0  # degrees the text is turned on the page; bbox is always in page coordinates
    continues: bool = False  # the paragraph runs on into the first block of the next page


@dataclass
class Page:
    number: int  # 1 based page number in the source file
    width: float
    height: float
    blocks: list[Block] = field(default_factory=list)
    rtl: bool = True
    ocr: bool = False  # the text came from OCR
    needs_ocr: bool = False  # no usable text and OCR was not available or not allowed
    unmapped_glyphs: int = 0  # glyphs the PDF gives no Unicode value for


@dataclass
class Document:
    source: str
    pages: list[Page] = field(default_factory=list)

    @property
    def blocks(self) -> list[Block]:
        return [block for page in self.pages for block in page.blocks]
