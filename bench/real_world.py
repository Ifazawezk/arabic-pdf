"""Qualitative checks on real Arabic PDFs.

There is no ground truth here, so this script reports what can be counted
without one (leftover presentation forms, Arabic words that look reversed,
unmapped glyphs, pages sent to OCR) and prints short excerpts to read by eye.

The PDFs are not committed: they belong to their publishers. They are
downloaded into bench/real/, which git ignores. Downloads say what they are
in the User-Agent header. A source that refuses is skipped and reported, and
never retried another way.

    python bench/real_world.py                 # download if needed, then report
    python bench/real_world.py --pages 12 40   # choose pages (1 based)
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from arabic_pdf import extract  # noqa: E402

REAL = ROOT / "bench" / "real"
USER_AGENT = "arabic-pdf-benchmark/0.1 (+https://github.com/Ifazawezk/arabic-pdf)"

SOURCES = {
    "qatar_nds2": {
        "title": "Qatar Second National Development Strategy 2018-2022 (Arabic)",
        "publisher": "Planning and Statistics Authority, State of Qatar, copy hosted by FAOLEX",
        "url": "https://faolex.fao.org/docs/pdf/qat181692.pdf",
        "pages": [41, 121],
    },
    "who_constitution": {
        "title": "Constitution of the World Health Organization (Arabic)",
        "publisher": "World Health Organization, Basic Documents",
        "url": "https://apps.who.int/gb/bd/PDF/bd47/AR/constitution-ar.pdf",
        "pages": [1, 4],
    },
}

_PRESENTATION = re.compile("[\ufb50-\ufdff\ufe70-\ufefc]")
_ARABIC_WORD = re.compile("[\u0621-\u064a]{3,}")


def fetch(name: str, url: str) -> Path:
    """Download once. Refuses anything that is not a PDF: some hosts answer with an HTML page."""
    path = REAL / name / f"{name}.pdf"
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
    if not data.startswith(b"%PDF-"):
        raise ValueError(f"{url} did not return a PDF")
    path.write_bytes(data)
    return path


def reversed_share(text: str) -> float:
    """Share of the definite article that looks reversed.

    About one Arabic word in five starts with the article (al). In reversed
    text those words end in the same two letters the other way round, so the
    balance between the two patterns shows the direction with no ground truth.
    """
    words = _ARABIC_WORD.findall(text)
    forward = sum(w.startswith("\u0627\u0644") for w in words)
    backward = sum(w.endswith("\u0644\u0627") for w in words)
    return backward / (forward + backward) if forward + backward else 0.0


def describe(label: str, text: str) -> None:
    print(f"  {label:9s} presentation forms {len(_PRESENTATION.findall(text)):5d}   "
          f"reversed article share {reversed_share(text):5.1%}   chars {len(text)}")


def report(path: Path, source: dict, pages: list[int]) -> None:
    print(f"\n{source['title']}\n{source['publisher']}\n{source['url']}")
    with pymupdf.open(path) as pdf:
        print(f"{pdf.page_count} pages")
        raw = {n: pdf[n - 1].get_text() for n in pages}
    document = extract(path, pages=pages)
    for page in document.pages:
        ours = "\n".join(b.text for b in page.blocks)
        print(f"\npage {page.number}: ocr={page.ocr} needs_ocr={page.needs_ocr} unmapped={page.unmapped_glyphs}")
        describe("PyMuPDF", raw[page.number])
        describe("arpdf", ours)
        for line in ours.splitlines()[:4]:
            print("   ", line[:110])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pages", nargs="*", type=int, help="pages to check in every document")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    pymupdf.TOOLS.mupdf_display_errors(False)
    for name, source in SOURCES.items():
        try:
            path = fetch(name, source["url"])
        except (OSError, ValueError) as exc:  # URLError and HTTPError are OSErrors
            print(f"\nskipped {source['title']}: {exc}")
            continue
        report(path, source, args.pages or source["pages"])


if __name__ == "__main__":
    main()
