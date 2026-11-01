"""Build the synthetic benchmark corpus in ``corpus/``.

Each document in ``corpus_text.DOCUMENTS`` becomes ``corpus/<id>.pdf`` plus
``corpus/<id>.txt`` (the exact ground truth in logical order). Three engines
are used:

* legacy:  reportlab + arabic-reshaper + python-bidi. Text is stored as
           presentation forms in visual order, like many older generators.
* browser: an HTML page printed to PDF by headless Edge or Chrome, so a real
           shaping engine produces the glyphs (like Word or Google Docs).
* scanned: a browser document rasterised to grayscale JPEG pages with no
           text layer at all.

Usage:
    python bench/make_corpus.py            # build everything
    python bench/make_corpus.py --only browser_table_arial

Needs Windows fonts (Arial, Tahoma, Times New Roman, Traditional Arabic,
Sakkal Majalla, Simplified Arabic, Arabic Typesetting, Segoe UI) and a
Chromium based browser. Set ARPDF_BROWSER to the browser executable if it is
not found automatically. The generated files are committed, so you only need
this script when you add or change a document.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpus_text import DOCUMENTS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "corpus"
FONT_DIRS = [Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts", Path("/usr/share/fonts"), Path.home() / ".fonts"]

LEGACY_FONTS = {
    "arial": ("arial.ttf", "arialbd.ttf"),
    "times": ("times.ttf", "timesbd.ttf"),
    "tahoma": ("tahoma.ttf", "tahomabd.ttf"),
    "trado": ("trado.ttf", "tradbdo.ttf"),
}


# --------------------------------------------------------------------------
# ground truth

def ground_truth(blocks) -> str:
    parts = []
    for block in blocks:
        kind = block[0]
        if kind == "page":
            continue
        if kind == "table":
            parts.append("\n".join("\t".join(row) for row in block[1]))
        else:
            parts.append(block[1])
    return "\n\n".join(parts) + "\n"


# --------------------------------------------------------------------------
# legacy engine: reportlab + arabic-reshaper + python-bidi

def find_font(name: str) -> Path:
    for d in FONT_DIRS:
        for candidate in (d / name, d / name.lower()):
            if candidate.exists():
                return candidate
    raise FileNotFoundError(f"font {name} not found in {FONT_DIRS}")


class LegacyWriter:
    page_w, page_h = 595.0, 842.0
    margin = 60.0

    def __init__(self, path: Path, spec: dict):
        import arabic_reshaper
        from bidi.algorithm import get_display
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas

        self.reshape = arabic_reshaper.reshape
        self.get_display = get_display
        self.metrics = pdfmetrics
        regular, bold = LEGACY_FONTS[spec["font"]]
        self.font = f"{spec['font']}-regular"
        self.bold = f"{spec['font']}-bold"
        pdfmetrics.registerFont(TTFont(self.font, str(find_font(regular))))
        pdfmetrics.registerFont(TTFont(self.bold, str(find_font(bold))))
        self.canvas = canvas.Canvas(str(path), pagesize=(self.page_w, self.page_h))
        self.canvas.setTitle(path.stem)
        self.spec = spec
        self.size = spec.get("size", 13)
        self.columns = spec.get("columns", 1)
        self.gutter = 30.0
        self.page_no = 1
        self.pages = 1 + sum(1 for b in spec["blocks"] if b[0] == "page")
        self.new_page_state()

    # visual form of one logical line, as python-bidi would display it
    def visual(self, text: str) -> str:
        return self.get_display(self.reshape(text), base_dir="R")

    def width(self, text: str, font: str, size: float) -> float:
        return self.metrics.stringWidth(self.reshape(text), font, size)

    def new_page_state(self):
        self.top = self.page_h - self.margin - (25 if self.spec.get("header") else 0)
        self.bottom = self.margin + (25 if self.spec.get("footer") else 0)
        self.y = self.top
        self.col = 0
        self.draw_running_text()

    def draw_running_text(self):
        c = self.canvas
        if self.spec.get("header"):
            c.setFont(self.font, 10)
            c.drawCentredString(self.page_w / 2, self.page_h - 40, self.visual(self.spec["header"]))
            c.line(self.margin, self.page_h - 48, self.page_w - self.margin, self.page_h - 48)
        if self.spec.get("footer"):
            text = self.spec["footer"].format(page=self.page_no, pages=self.pages)
            c.setFont(self.font, 10)
            c.drawCentredString(self.page_w / 2, 35, self.visual(text))

    def next_page(self):
        self.canvas.showPage()
        self.page_no += 1
        self.new_page_state()

    def column_box(self):
        content = self.page_w - 2 * self.margin
        col_w = (content - (self.columns - 1) * self.gutter) / self.columns
        right = self.page_w - self.margin - self.col * (col_w + self.gutter)
        return right, col_w

    def next_column(self):
        if self.col + 1 < self.columns:
            self.col += 1
            self.y = self.col_top
        else:
            self.next_page()
            self.col_top = self.top

    def wrap(self, text: str, font: str, size: float, width: float) -> list[str]:
        lines, current = [], ""
        for word in text.split():
            candidate = f"{current} {word}".strip()
            if current and self.width(candidate, font, size) > width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines

    def paragraph(self, text: str, font: str, size: float, full_width: bool = False):
        leading = size * 1.6
        if full_width:
            right, width = self.page_w - self.margin, self.page_w - 2 * self.margin
        else:
            right, width = self.column_box()
        for line in self.wrap(text, font, size, width):
            if self.y - leading < self.bottom:
                self.next_column()
                right, width = self.column_box()
            self.y -= leading
            self.canvas.setFont(font, size)
            self.canvas.drawRightString(right, self.y, self.visual(line))
        self.y -= size * 0.8

    def table(self, rows):
        size = self.size - 1
        width = self.page_w - 2 * self.margin
        col_w = width / len(rows[0])
        row_h = size * 2.2
        right = self.page_w - self.margin
        c = self.canvas
        self.y -= 6
        top = self.y
        for r, row in enumerate(rows):
            font = self.bold if r == 0 else self.font
            baseline = self.y - row_h + size * 0.75
            for i, cell in enumerate(row):
                cell_right = right - i * col_w
                if cell:
                    c.setFont(font, size)
                    c.drawRightString(cell_right - 6, baseline, self.visual(cell))
            self.y -= row_h
        # grid
        c.setLineWidth(0.8)
        for r in range(len(rows) + 1):
            yy = top - r * row_h
            c.line(self.margin, yy, right, yy)
        for i in range(len(rows[0]) + 1):
            xx = right - i * col_w
            c.line(xx, top, xx, self.y)
        self.y -= size

    def build(self):
        self.col_top = self.top
        for block in self.spec["blocks"]:
            kind = block[0]
            if kind == "page":
                self.next_page()
                self.col_top = self.top
            elif kind in ("h1", "h2"):
                size = 20 if kind == "h1" else 16
                self.paragraph(block[1], self.bold, size, full_width=True)
                self.col_top = self.y
            elif kind == "p":
                self.paragraph(block[1], self.font, self.size)
            elif kind == "table":
                self.table(block[1])
        self.canvas.save()


# --------------------------------------------------------------------------
# browser engine: HTML printed to PDF by headless Edge or Chrome

BROWSER_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/microsoft-edge",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def find_browser() -> str:
    env = os.environ.get("ARPDF_BROWSER")
    if env:
        return env
    for c in BROWSER_CANDIDATES:
        if Path(c).exists():
            return c
    for name in ("msedge", "google-chrome", "chromium", "chrome"):
        found = shutil.which(name)
        if found:
            return found
    raise FileNotFoundError("no Chromium based browser found, set ARPDF_BROWSER")


def block_html(block) -> str:
    kind = block[0]
    if kind in ("h1", "h2", "p"):
        return f"<{kind}>{html.escape(block[1])}</{kind}>"
    if kind == "table":
        rows = block[1]
        head = "".join(f"<th>{html.escape(c)}</th>" for c in rows[0])
        body = "".join("<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
        return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    raise ValueError(kind)


def document_html(spec: dict) -> str:
    direction = spec.get("dir", "rtl")
    size = spec.get("size", 14)
    columns = spec.get("columns", 1)
    css = f"""
    @page {{ size: A4; margin: 0; }}
    html, body {{ margin: 0; padding: 0; }}
    body {{ font-family: '{spec['font']}'; font-size: {size}pt; line-height: 1.5; color: #111; }}
    .page {{ width: 210mm; height: 297mm; box-sizing: border-box; padding: 22mm 20mm; position: relative;
             page-break-after: always; overflow: hidden; }}
    .page:last-child {{ page-break-after: auto; }}
    .header {{ position: absolute; top: 9mm; left: 20mm; right: 20mm; text-align: center; font-size: 10pt;
               border-bottom: 1px solid #888; padding-bottom: 2mm; }}
    .footer {{ position: absolute; bottom: 9mm; left: 20mm; right: 20mm; text-align: center; font-size: 10pt; }}
    .cols {{ column-count: {columns}; column-gap: 2em; text-align: justify; }}
    h1 {{ font-size: 1.7em; margin: 0 0 0.6em; }}
    h2 {{ font-size: 1.3em; margin: 0.8em 0 0.4em; }}
    p {{ margin: 0 0 0.8em; }}
    table {{ border-collapse: collapse; width: 100%; margin: 0.6em 0 1em; }}
    th, td {{ border: 1px solid #444; padding: 4px 8px; text-align: start; }}
    th {{ background: #eee; }}
    """
    pages, current = [], []
    for block in spec["blocks"]:
        if block[0] == "page":
            pages.append(current)
            current = []
        else:
            current.append(block)
    pages.append(current)

    body = []
    for number, blocks in enumerate(pages, start=1):
        parts = []
        if spec.get("header"):
            parts.append(f"<div class='header'>{html.escape(spec['header'])}</div>")
        if spec.get("footer"):
            footer = spec["footer"].format(page=number, pages=len(pages))
            parts.append(f"<div class='footer'>{html.escape(footer)}</div>")
        if columns > 1:
            headings = [b for b in blocks if b[0] in ("h1", "h2")]
            rest = [b for b in blocks if b[0] not in ("h1", "h2")]
            parts += [block_html(b) for b in headings]
            parts.append("<div class='cols'>" + "".join(block_html(b) for b in rest) + "</div>")
        else:
            parts += [block_html(b) for b in blocks]
        body.append("<div class='page'>" + "".join(parts) + "</div>")
    lang = "ar" if direction == "rtl" else "en"
    return (f"<!doctype html><html lang='{lang}' dir='{direction}'><head><meta charset='utf-8'>"
            f"<style>{css}</style></head><body>{''.join(body)}</body></html>")


def print_html(html_text: str, out: Path, browser: str):
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "doc.html"
        src.write_text(html_text, encoding="utf-8")
        profile = Path(tmp) / "profile"
        cmd = [browser, "--headless", "--disable-gpu", "--no-first-run", "--no-pdf-header-footer",
               f"--user-data-dir={profile}", f"--print-to-pdf={out}", src.resolve().as_uri()]
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    if not out.exists():
        raise RuntimeError(f"browser did not write {out}")
    # browsers stamp the creation date into the file; drop it so rebuilds are stable
    with pymupdf.open(out) as doc:
        doc.set_metadata({"title": out.stem, "producer": "arabic-pdf corpus"})
        data = doc.tobytes(garbage=3, deflate=True)
    out.write_bytes(data)


# --------------------------------------------------------------------------
# scanned engine

def rasterise(source: Path, out: Path, dpi: int):
    src = pymupdf.open(source)
    dst = pymupdf.open()
    for page in src:
        pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
        jpg = pix.tobytes("jpeg", jpg_quality=70)
        new = dst.new_page(width=page.rect.width, height=page.rect.height)
        new.insert_image(new.rect, stream=jpg)
    dst.set_metadata({"title": out.stem, "producer": "arabic-pdf corpus"})
    dst.save(out, garbage=3, deflate=True)


# --------------------------------------------------------------------------

def build(doc_id: str, spec: dict, browser: str | None):
    pdf = OUT / f"{doc_id}.pdf"
    engine = spec["engine"]
    if engine == "legacy":
        LegacyWriter(pdf, spec).build()
        truth = ground_truth(spec["blocks"])
    elif engine == "browser":
        print_html(document_html(spec), pdf, browser or find_browser())
        truth = ground_truth(spec["blocks"])
    elif engine == "scanned":
        source = OUT / f"{spec['source']}.pdf"
        rasterise(source, pdf, spec.get("dpi", 200))
        truth = (OUT / f"{spec['source']}.txt").read_text(encoding="utf-8")
    else:
        raise ValueError(engine)
    (OUT / f"{doc_id}.txt").write_text(truth, encoding="utf-8", newline="\n")
    with pymupdf.open(pdf) as d:
        pages = d.page_count
    return {"id": doc_id, "engine": engine, "category": spec["category"],
            "font": spec.get("font") or DOCUMENTS[spec["source"]]["font"], "pages": pages}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", help="document ids to rebuild")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    manifest_path = OUT / "manifest.json"
    manifest = {}
    if manifest_path.exists():
        manifest = {d["id"]: d for d in json.loads(manifest_path.read_text(encoding="utf-8"))}
    browser = None
    # scanned documents depend on browser documents, so build them last
    order = sorted(DOCUMENTS, key=lambda k: DOCUMENTS[k]["engine"] == "scanned")
    for doc_id in order:
        if args.only and doc_id not in args.only:
            continue
        spec = DOCUMENTS[doc_id]
        if spec["engine"] == "browser" and browser is None:
            browser = find_browser()
        manifest[doc_id] = build(doc_id, spec, browser)
        size = (OUT / f"{doc_id}.pdf").stat().st_size
        print(f"{doc_id:32s} {manifest[doc_id]['pages']} page(s) {size / 1024:7.1f} KB")
    entries = [manifest[k] for k in DOCUMENTS if k in manifest]
    manifest_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
