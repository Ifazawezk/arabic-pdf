"""Clean text extraction for Arabic and mixed Arabic/English PDFs."""

from .document import Block, Document, Page
from .extract import extract, extract_markdown, extract_text
from .render import to_json, to_markdown, to_text

__all__ = [
    "Block", "Document", "Page", "extract", "extract_markdown", "extract_text",
    "to_json", "to_markdown", "to_text",
]
__version__ = "0.1.0"
