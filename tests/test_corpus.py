"""Sanity checks for the committed benchmark corpus."""

import json
import re
from pathlib import Path

import pymupdf

CORPUS = Path(__file__).resolve().parent.parent / "corpus"
PRESENTATION_FORMS = re.compile("[\ufb50-\ufdff\ufe70-\ufeff]")


def manifest():
    return json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))


def test_every_document_has_pdf_and_ground_truth():
    docs = manifest()
    assert len(docs) >= 20
    for doc in docs:
        assert (CORPUS / f"{doc['id']}.pdf").exists(), doc["id"]
        truth = (CORPUS / f"{doc['id']}.txt").read_text(encoding="utf-8")
        assert truth.strip(), doc["id"]


def test_ground_truth_is_plain_logical_unicode():
    for doc in manifest():
        truth = (CORPUS / f"{doc['id']}.txt").read_text(encoding="utf-8")
        assert not PRESENTATION_FORMS.search(truth), doc["id"]


def test_page_counts_match_manifest():
    for doc in manifest():
        with pymupdf.open(CORPUS / f"{doc['id']}.pdf") as pdf:
            assert pdf.page_count == doc["pages"], doc["id"]


def test_corpus_stays_small():
    total = sum(p.stat().st_size for p in CORPUS.glob("*.pdf"))
    assert total < 5 * 1024 * 1024
