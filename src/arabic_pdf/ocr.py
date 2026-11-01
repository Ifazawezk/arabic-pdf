"""OCR fallback for scanned pages.

PyMuPDF ships with Tesseract built in, so OCR needs no extra program: only
the language data files ``ara.traineddata`` and ``eng.traineddata``. They are
looked up in ``TESSDATA_PREFIX``, then in the usual install locations. If they
are missing the page is flagged in the result and extraction carries on.
"""

from __future__ import annotations

import os
import shutil
import warnings
from pathlib import Path

import pymupdf

from .glyphs import Glyph

DEFAULT_LANGUAGE = "ara+eng"
DEFAULT_DPI = 300

# a page with fewer painted glyphs than this has no real text layer
MIN_GLYPHS = 20
# ...if images cover at least this share of it
MIN_IMAGE_COVER = 0.3
# a text layer with more unmapped glyphs than this share is not usable
MAX_UNMAPPED = 0.3


def is_unmapped(text: str) -> bool:
    """True for a glyph the PDF gives no real Unicode value for."""
    return any(ch == chr(0xFFFD) or 0xE000 <= ord(ch) <= 0xF8FF for ch in text)


def _candidates() -> list[Path]:
    paths = []
    if os.environ.get("TESSDATA_PREFIX"):
        paths.append(Path(os.environ["TESSDATA_PREFIX"]))
    exe = shutil.which("tesseract")
    if exe:
        paths.append(Path(exe).resolve().parent / "tessdata")
    for base in (os.environ.get("LOCALAPPDATA"), os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if base:
            paths += [Path(base) / "tessdata", Path(base) / "Tesseract-OCR" / "tessdata",
                      Path(base) / "Programs" / "Tesseract-OCR" / "tessdata"]
    paths.append(Path.home() / ".local" / "share" / "tessdata")
    for root in ("/usr/share/tesseract-ocr/5", "/usr/share/tesseract-ocr/4.00", "/usr/share/tesseract-ocr",
                 "/usr/share", "/usr/local/share", "/opt/homebrew/share"):
        paths.append(Path(root) / "tessdata")
    return paths


def find_tessdata(language: str = "ara") -> str | None:
    """The first folder that holds the data file for ``language``."""
    for folder in _candidates():
        if (folder / f"{language}.traineddata").is_file():
            return str(folder)
    return None


def usable_languages(language: str, tessdata: str) -> str | None:
    """The requested languages that have data files, joined with +."""
    found = [lang for lang in language.split("+") if (Path(tessdata) / f"{lang}.traineddata").is_file()]
    return "+".join(found) or None


def needs_ocr(page: pymupdf.Page, glyphs: list[Glyph]) -> bool:
    """True if the page is a scan, or its text layer has no usable Unicode."""
    ink = [g for g in glyphs if not g.is_space]
    if ink and sum(is_unmapped(g.text) for g in ink) / len(ink) > MAX_UNMAPPED:
        return True
    if len(ink) >= MIN_GLYPHS:
        return False
    area = abs(page.rect) or 1.0
    covered = sum(abs(pymupdf.Rect(info["bbox"]) & page.rect) for info in page.get_image_info())
    return covered / area >= MIN_IMAGE_COVER


def ocr_glyphs(page: pymupdf.Page, language: str = DEFAULT_LANGUAGE, dpi: int = DEFAULT_DPI) -> list[Glyph] | None:
    """Run OCR on a page and return glyphs, or None if language data is missing.

    Space characters are dropped: OCR spaces come with boxes that cover the
    whole next word, and the gaps between words are clear without them.
    """
    tessdata = find_tessdata(language.split("+")[0])
    languages = usable_languages(language, tessdata) if tessdata else None
    if not languages:
        warnings.warn(f"no Tesseract data for {language}, see the OCR section of the README", stacklevel=2)
        return None
    textpage = page.get_textpage_ocr(language=languages, dpi=dpi, full=True, tessdata=tessdata)
    glyphs = []
    for block in page.get_text("rawdict", textpage=textpage)["blocks"]:
        for line in block.get("lines", ()):
            for span in line["spans"]:
                for char in span["chars"]:
                    if char["c"].strip():
                        x0, y0, x1, y1 = char["bbox"]
                        glyphs.append(Glyph(char["c"], x0, y0, x1, y1, y1, span["size"]))
    return glyphs
