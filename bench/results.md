Corpus: 24 documents, 28 pages. CER is micro averaged (total edits / total characters), lower is better. Word order is the share of reference word pairs found in the same order, higher is better.

| Extractor | CER | Word order | CER simple | CER mixed | CER two-column | CER headers | CER table | CER diacritics | CER scanned | Time / page |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| pdftotext | 51.7% | 45.6% | 35.7% | 25.9% | 72.7% | 47.9% | 60.0% | 44.2% | 100.0% | 12 ms |
| pymupdf | 46.2% | 35.3% | 39.3% | 57.8% | 30.5% | 49.9% | 26.3% | 70.3% | 100.0% | 3 ms |
| pdfplumber | 87.2% | 5.3% | 88.3% | 69.0% | 89.4% | 93.1% | 77.6% | 92.1% | 100.0% | 27 ms |
| pdfplumber+bidi | 28.6% | 57.0% | 5.0% | 10.6% | 56.1% | 13.2% | 27.5% | 64.8% | 100.0% | 24 ms |
| **arpdf** | 46.2% | 35.3% | 39.3% | 57.8% | 30.5% | 49.9% | 26.3% | 70.3% | 100.0% | 3 ms |

Per document (CER / word order):

| Document | Category | pdftotext | pymupdf | pdfplumber | pdfplumber+bidi | arpdf |
|---|---|---|---|---|---|---|
| legacy_simple_arial | simple | 81.1% / 0.0% | 82.0% / 0.0% | 91.5% / 0.0% | 2.4% / 85.6% | 82.0% / 0.0% |
| legacy_simple_times | simple | 80.5% / 0.0% | 81.5% / 0.0% | 90.3% / 0.0% | 3.2% / 83.2% | 81.5% / 0.0% |
| legacy_simple_tahoma | simple | 81.6% / 0.0% | 83.3% / 0.0% | 91.3% / 0.0% | 3.5% / 80.0% | 83.3% / 0.0% |
| legacy_simple_trado | simple | 80.8% / 0.0% | 82.1% / 0.0% | 92.2% / 0.0% | 0.4% / 97.5% | 82.1% / 0.0% |
| legacy_mixed_arial | mixed | 65.2% / 2.3% | 83.4% / 2.3% | 83.1% / 5.3% | 12.6% / 78.8% | 83.4% / 2.3% |
| legacy_two_column_arial | two-column | 91.8% / 0.0% | 82.7% / 0.0% | 92.0% / 0.0% | 23.6% / 78.4% | 82.7% / 0.0% |
| legacy_headers_tahoma | headers | 90.4% / 0.0% | 91.2% / 0.0% | 96.5% / 0.0% | 12.0% / 80.4% | 91.2% / 0.0% |
| legacy_table_arial | table | 88.7% / 21.7% | 69.2% / 17.4% | 75.3% / 17.4% | 34.8% / 54.3% | 69.2% / 17.4% |
| browser_simple_arial | simple | 0.0% / 100.0% | 3.9% / 75.0% | 85.5% / 0.0% | 9.2% / 39.2% | 3.9% / 75.0% |
| browser_simple_segoe | simple | 0.0% / 100.0% | 0.8% / 93.2% | 88.2% / 0.0% | 0.0% / 100.0% | 0.8% / 93.2% |
| browser_simple_majalla | simple | 0.0% / 100.0% | 5.5% / 68.6% | 86.4% / 0.0% | 4.7% / 72.0% | 5.5% / 68.6% |
| browser_simple_simplified | simple | 0.6% / 96.4% | 3.9% / 75.0% | 84.6% / 0.0% | 4.0% / 75.0% | 3.9% / 75.0% |
| browser_simple_typesetting | simple | 0.0% / 100.0% | 18.4% / 24.1% | 85.3% / 0.0% | 22.1% / 11.4% | 18.4% / 24.1% |
| browser_mixed_tahoma | mixed | 7.4% / 50.0% | 60.7% / 31.8% | 80.6% / 5.3% | 15.1% / 68.9% | 60.7% / 31.8% |
| browser_mixed_indic_times | mixed | 7.2% / 43.1% | 61.3% / 41.7% | 82.8% / 0.0% | 5.8% / 65.3% | 61.3% / 41.7% |
| browser_english_arabic | mixed | 4.1% / 77.0% | 2.8% / 95.9% | 9.9% / 82.4% | 2.8% / 95.9% | 2.8% / 95.9% |
| browser_two_column_times | two-column | 76.6% / 99.6% | 3.1% / 78.1% | 88.7% / 0.0% | 72.1% / 35.5% | 3.1% / 78.1% |
| browser_three_column_arial | two-column | 49.1% / 99.1% | 4.0% / 69.0% | 87.5% / 0.0% | 73.6% / 33.2% | 4.0% / 69.0% |
| browser_headers_arial | headers | 5.9% / 99.2% | 9.2% / 75.1% | 89.7% / 0.0% | 14.3% / 39.0% | 9.2% / 75.1% |
| browser_table_arial | table | 64.8% / 45.7% | 30.0% / 34.8% | 72.9% / 17.4% | 36.8% / 39.1% | 30.0% / 34.8% |
| browser_table_tahoma | table | 44.3% / 55.7% | 4.4% / 59.1% | 80.9% / 0.0% | 19.7% / 51.1% | 4.4% / 59.1% |
| browser_diacritics_arial | diacritics | 44.2% / 5.0% | 70.3% / 5.0% | 92.1% / 0.0% | 64.8% / 5.0% | 70.3% / 5.0% |
| scanned_simple_arial | scanned | 100.0% / 0.0% | 100.0% / 0.0% | 100.0% / 0.0% | 100.0% / 0.0% | 100.0% / 0.0% |
| scanned_mixed_tahoma | scanned | 100.0% / 0.0% | 100.0% / 0.0% | 100.0% / 0.0% | 100.0% / 0.0% | 100.0% / 0.0% |
