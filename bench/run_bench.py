"""Run every extractor over the corpus and score it against the ground truth.

    python bench/run_bench.py                 # all extractors, writes bench/results.md and .json
    python bench/run_bench.py --tools arpdf   # only some extractors
    python bench/run_bench.py --show browser_mixed_tahoma --tools arpdf pymupdf

Extractors:
    pdftotext          the pdftotext command line tool, default settings
    pymupdf            PyMuPDF page.get_text()
    pdfplumber         pdfplumber page.extract_text()
    pdfplumber+bidi    pdfplumber, then NFKC and python-bidi get_display() on every
                       line: the fix most often suggested on forums
    arpdf              this project, text output

Raw outputs are written to bench/out/<extractor>/<doc>.txt for inspection.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from arabic_pdf.metrics import score  # noqa: E402

logging.getLogger("pdfminer").setLevel(logging.ERROR)

CORPUS = ROOT / "corpus"
OUT = ROOT / "bench" / "out"
CATEGORIES = ["simple", "mixed", "two-column", "headers", "table", "diacritics", "scanned"]


def run_pdftotext(path: Path) -> str:
    exe = shutil.which("pdftotext")
    if not exe:
        raise RuntimeError("pdftotext not installed")
    out = subprocess.run([exe, "-enc", "UTF-8", str(path), "-"], capture_output=True, check=True)
    return out.stdout.decode("utf-8", errors="replace")


def run_pymupdf(path: Path) -> str:
    import pymupdf

    with pymupdf.open(path) as doc:
        return "\n".join(page.get_text() for page in doc)


def run_pdfplumber(path: Path) -> str:
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def run_pdfplumber_bidi(path: Path) -> str:
    from bidi.algorithm import get_display

    text = unicodedata.normalize("NFKC", run_pdfplumber(path))
    return "\n".join(get_display(line) for line in text.splitlines())


def run_arpdf(path: Path) -> str:
    from arabic_pdf import extract_text

    return extract_text(str(path))


EXTRACTORS = {
    "pdftotext": run_pdftotext,
    "pymupdf": run_pymupdf,
    "pdfplumber": run_pdfplumber,
    "pdfplumber+bidi": run_pdfplumber_bidi,
    "arpdf": run_arpdf,
}



def load_manifest():
    return json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))


def evaluate(tools, docs):
    results = {}
    for tool in tools:
        fn = EXTRACTORS[tool]
        (OUT / tool).mkdir(parents=True, exist_ok=True)
        rows = []
        for doc in docs:
            pdf = CORPUS / f"{doc['id']}.pdf"
            truth = (CORPUS / f"{doc['id']}.txt").read_text(encoding="utf-8")
            start = time.perf_counter()
            try:
                text = fn(pdf)
                error = None
            except Exception as exc:  # a crash counts as empty output
                text, error = "", f"{type(exc).__name__}: {exc}"
            elapsed = time.perf_counter() - start
            (OUT / tool / f"{doc['id']}.txt").write_text(text, encoding="utf-8")
            row = {"id": doc["id"], "category": doc["category"], "engine": doc["engine"],
                   "pages": doc["pages"], "seconds": elapsed, **score(truth, text)}
            if error:
                row["error"] = error
            rows.append(row)
        results[tool] = rows
    return results


def summarize(rows):
    """Micro averaged CER (total edits / total characters) and mean word order."""
    if not rows:
        return None
    chars = sum(r["ref_chars"] for r in rows)
    edits = sum(r["edits"] for r in rows)
    return {
        "cer": edits / chars if chars else 0.0,
        "word_order": sum(r["word_order"] for r in rows) / len(rows),
        "docs": len(rows),
    }


def seconds_per_page(rows):
    """Speed on pages with a text layer. Scanned pages are left out: there the OCR engine dominates."""
    text_rows = [r for r in rows if r["category"] != "scanned"]
    return sum(r["seconds"] for r in text_rows) / max(1, sum(r["pages"] for r in text_rows))


def pct(x):
    return "n/a" if x is None else f"{100 * x:.1f}%"


def markdown_report(results, docs) -> str:
    lines = []
    cats = [c for c in CATEGORIES if any(d["category"] == c for d in docs)]
    lines.append(f"Corpus: {len(docs)} documents, {sum(d['pages'] for d in docs)} pages. "
                 "CER is micro averaged (total edits / total characters), lower is better. "
                 "Word order is the share of reference word pairs found in the same order, higher is better. "
                 "Time / page covers pages with a text layer only.")
    lines.append("")
    lines.append("| Extractor | CER | Word order | " + " | ".join(f"CER {c}" for c in cats) + " | Time / page |")
    lines.append("|---|---:|---:|" + "---:|" * len(cats) + "---:|")
    for tool, rows in results.items():
        overall = summarize(rows)
        per_cat = [summarize([r for r in rows if r["category"] == c]) for c in cats]
        cells = [pct(overall["cer"]), pct(overall["word_order"])]
        cells += [pct(s["cer"]) if s else "n/a" for s in per_cat]
        cells.append(f"{seconds_per_page(rows) * 1000:.0f} ms")
        name = f"**{tool}**" if tool == "arpdf" else tool
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("Per document (CER / word order):")
    lines.append("")
    tools = list(results)
    lines.append("| Document | Category | " + " | ".join(tools) + " |")
    lines.append("|---|---|" + "---|" * len(tools))
    for i, doc in enumerate(docs):
        cells = []
        for tool in tools:
            r = results[tool][i]
            cells.append(f"{pct(r['cer'])} / {pct(r['word_order'])}")
        lines.append(f"| {doc['id']} | {doc['category']} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tools", nargs="*", default=list(EXTRACTORS), choices=list(EXTRACTORS))
    ap.add_argument("--docs", nargs="*", help="only these document ids")
    ap.add_argument("--show", help="print the outputs for one document and exit")
    ap.add_argument("--no-write", action="store_true", help="do not update bench/results.*")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    docs = load_manifest()
    if args.docs:
        docs = [d for d in docs if d["id"] in args.docs]
    if args.show:
        docs = [d for d in docs if d["id"] == args.show]
        print("TRUTH:\n" + (CORPUS / f"{args.show}.txt").read_text(encoding="utf-8"))
        for tool in args.tools:
            text = EXTRACTORS[tool](CORPUS / f"{args.show}.pdf")
            s = score((CORPUS / f"{args.show}.txt").read_text(encoding="utf-8"), text)
            print(f"--- {tool}: CER {pct(s['cer'])}, word order {pct(s['word_order'])}\n{text}")
        return

    results = evaluate(args.tools, docs)
    report = markdown_report(results, docs)
    print(report)
    if not args.no_write and not args.docs:
        (ROOT / "bench" / "results.md").write_text(report, encoding="utf-8", newline="\n")
        (ROOT / "bench" / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1) + "\n",
                                                     encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
