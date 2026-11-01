"""Render docs/banner.png: real extractor output, before and after.

The strings are not typed in. They are extracted from a corpus PDF when this
script runs, so the banner cannot drift away from what the tools really do.

    python docs/make_banner.py

Needs a Chromium based browser, found the same way as in bench/make_corpus.py.
"""

from __future__ import annotations

import html
import subprocess
import sys
import tempfile
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "bench"))

from arabic_pdf import extract_text  # noqa: E402
from make_corpus import find_browser  # noqa: E402

SOURCE = ROOT / "corpus" / "legacy_mixed_arial.pdf"
OUTPUT = ROOT / "docs" / "banner.png"
MARKER = "Windows 11"


def line_with(text: str, marker: str) -> str:
    return next(line.strip() for line in text.splitlines() if marker in line)


def page_html(before: str, after: str) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><style>
    html, body {{ margin: 0; width: 1280px; height: 640px; overflow: hidden; }}
    body {{ background: #10231f; color: #f2efe6; font-family: 'Segoe UI', Arial, sans-serif;
            display: flex; flex-direction: column; justify-content: center; padding: 0 72px; box-sizing: border-box; }}
    h1 {{ font-size: 76px; margin: 0; letter-spacing: -1px; }}
    p.tag {{ font-size: 28px; margin: 8px 0 44px; color: #b9c9c2; }}
    .row {{ border-radius: 12px; padding: 18px 26px; margin-bottom: 18px; }}
    .label {{ font-size: 18px; font-weight: 600; letter-spacing: .5px; margin-bottom: 8px; }}
    .text {{ font-family: Arial, sans-serif; font-size: 27px; line-height: 1.5; direction: rtl; text-align: right; }}
    .before {{ background: #3a1f1f; }} .before .label {{ color: #f0a58f; }}
    .after {{ background: #17423a; }} .after .label {{ color: #8fe0c0; }}
    </style></head><body>
    <h1>arabic-pdf</h1>
    <p class="tag">Clean Unicode text and Markdown from Arabic PDFs</p>
    <div class="row before"><div class="label">PyMuPDF get_text()</div><div class="text">{html.escape(before)}</div></div>
    <div class="row after"><div class="label">arpdf</div><div class="text">{html.escape(after)}</div></div>
    </body></html>"""


def main() -> None:
    with pymupdf.open(SOURCE) as doc:
        raw = "\n".join(page.get_text() for page in doc)
    before = line_with(raw, MARKER)
    after = line_with(extract_text(SOURCE), MARKER)
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "banner.html"
        page.write_text(page_html(before, after), encoding="utf-8")
        subprocess.run(
            [find_browser(), "--headless", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
             f"--user-data-dir={Path(tmp) / 'profile'}", "--window-size=1280,640",
             f"--screenshot={OUTPUT}", page.resolve().as_uri()],
            check=True, capture_output=True, timeout=60,
        )
    print(f"before: {before}\nafter:  {after}\nwrote {OUTPUT}")


if __name__ == "__main__":
    main()
