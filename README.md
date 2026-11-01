# arabic-pdf

Turn Arabic and mixed Arabic/English PDFs into clean Unicode text.

Work in progress. Right now `arpdf` only dumps what PyMuPDF gives back, which is
the starting point the rest of the project has to beat.

```bash
pip install -e .
arpdf file.pdf -o out.txt
```
