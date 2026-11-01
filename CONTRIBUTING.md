# Contributing

The most valuable thing you can send is a PDF that comes out wrong. Every failure in the real world that becomes a test stays fixed.

## Setup

```bash
git clone https://github.com/Ifazawezk/arabic-pdf
cd arabic-pdf
pip install -e ".[dev,bench]"
python -m pytest
```

OCR tests are skipped if the Arabic Tesseract data is missing. See the OCR section of the README.

## Add a failing PDF as a test case

### 1. Check that you may share it

Only add PDFs you have the right to publish: your own documents, or files with a license that allows it. If you can't share the file, skip to [Rebuild the problem](#rebuild-the-problem-instead), which is often better anyway.

### 2. Cut it down

One page that shows the problem is enough. Keep the file small: all corpus PDFs together must stay under 5 MB, and a test checks that.

```python
import pymupdf

doc = pymupdf.open("failing.pdf")
doc.select([11])  # page 12, counted from 0
doc.save("corpus/real_short_name.pdf", garbage=4, deflate=True)
```

### 3. Write the ground truth

Create `corpus/real_short_name.txt` with the text a person would read, in reading order:

- One line per heading, blank line between blocks.
- Table rows on separate lines, cells separated by a tab, first logical cell first. In an Arabic table that is the rightmost cell.
- Leave out headers, footers and page numbers.
- Plain Arabic letters only. A test rejects presentation forms.

Type or correct it by hand. Don't paste the output of an extractor without reading every word, or the test will just confirm the bug.

### 4. Add it to the manifest

Add an entry to `corpus/manifest.json`:

```json
{
  "id": "real_short_name",
  "engine": "real",
  "category": "mixed",
  "font": "unknown",
  "pages": 1
}
```

`category` is one of `simple`, `mixed`, `two-column`, `headers`, `table`, `diacritics` or `scanned`. `bench/make_corpus.py` keeps entries like this one when it rebuilds the corpus.

### 5. Run it

```bash
python bench/run_bench.py --docs real_short_name --tools arpdf pymupdf
python -m pytest tests/test_end_to_end.py
```

The end to end tests read the manifest, so your document is already covered, and they should now fail. That's a good pull request on its own: a failing case with a clear description is useful even without a fix. If the document can't reach 0.0% for a known reason, add it to `KNOWN_ERRORS` in `tests/test_end_to_end.py` with a comment saying why.

## Rebuild the problem instead

Many bugs come down to one PDF feature, and a tiny file built in a test explains it better than a page of someone's report. `tests/test_real_world_fixes.py` does this for rotated text and `/ActualText` digits, without any third party file. `tests/helpers.py` builds glyph lists from a visual-order string, for bidi and layout problems.

To add a whole synthetic document, add it to `DOCUMENTS` in `bench/corpus_text.py` and run:

```bash
python bench/make_corpus.py --only your_document_id
```

This needs Windows fonts and a Chromium based browser. Set `ARPDF_BROWSER` if yours isn't found.

## Change the code

- One fix per pull request, with a test that fails before it.
- Run `python bench/run_bench.py` and include the numbers if a score changes. Commit the updated `bench/results.md` and `bench/results.json`.
- Never edit a number in the README by hand without running the benchmark.
- A score can only go down for a reason you can explain.
- The corpus is a development set. If you tune something, also read the output on a real document with `python bench/real_world.py`. Reading output is what found the worst bugs here: a text loss that the CER table could not show.

## Report a bug without a PDF

Open an issue with the producer of the file (`Producer` in the PDF properties), the output you got, what the page actually shows, and if you can, a screenshot of the line.
