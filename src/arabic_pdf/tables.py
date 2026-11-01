"""Find ruled tables and read them cell by cell.

Table cells must leave the normal text flow early: to the column detector
the gaps between table columns look exactly like gutters. PyMuPDF finds the
grid from the lines drawn on the page, then the glyphs inside each cell go
through the same line building and bidi reordering as any other text.

Cells keep reading order, so the first cell of a row in an Arabic table is
the rightmost one on the page.
"""

from __future__ import annotations

from dataclasses import dataclass

import pymupdf

from .glyphs import Glyph, rotate_rect
from .layout import Line, build_rows, is_rtl, line_text

Rect = tuple[float, float, float, float]


@dataclass
class TableGrid:
    bbox: Rect
    cells: list[list[Rect | None]]  # rows of cell boxes, left to right; None for a merged cell


def find_grids(page: pymupdf.Page) -> list[TableGrid]:
    """Ruled tables on the page, ignoring single boxes and single rows or columns."""
    # find_tables() otherwise prints a package recommendation to stdout
    getattr(pymupdf, "no_recommend_layout", lambda: None)()
    grids = []
    for table in page.find_tables().tables:
        if table.row_count < 2 or table.col_count < 2:
            continue
        grids.append(TableGrid(tuple(table.bbox), [list(row.cells) for row in table.rows]))
    return grids


def rotate_grid(grid: TableGrid, quarter: int, width: float, height: float) -> TableGrid:
    """The same grid in the upright frame of turned text: rows and columns swap,
    so they are rebuilt from the positions of the turned cells."""
    if not quarter:
        return grid
    boxes = [rotate_rect(c, quarter, width, height) for row in grid.cells for c in row if c is not None]
    tops = sorted({round(b[1]) for b in boxes})
    lefts = sorted({round(b[0]) for b in boxes})
    cells: list[list[Rect | None]] = [[None] * len(lefts) for _ in tops]
    for box in boxes:
        cells[tops.index(round(box[1]))][lefts.index(round(box[0]))] = box
    return TableGrid(rotate_rect(grid.bbox, quarter, width, height), cells)


def _inside(glyph: Glyph, box: Rect) -> bool:
    return box[0] <= glyph.cx <= box[2] and box[1] <= glyph.cy <= box[3]


def split_table_glyphs(glyphs: list[Glyph], grids: list[TableGrid]) -> tuple[list[Glyph], list[list[Glyph]]]:
    """Separate glyphs into the normal text flow and one list per table."""
    flow: list[Glyph] = []
    inside: list[list[Glyph]] = [[] for _ in grids]
    for g in glyphs:
        for i, grid in enumerate(grids):
            if _inside(g, grid.bbox):
                inside[i].append(g)
                break
        else:
            flow.append(g)
    return flow, inside


def cell_text(glyphs: list[Glyph], rtl: bool, arabic_variants: bool, mirror: bool = True) -> str:
    """Text of one cell. Direction comes from the table, not the cell: a cell
    like "2,450 QAR" in an Arabic table is laid out right to left."""
    if not any(not g.is_space for g in glyphs):
        return ""
    lines = [Line(row, mirror=mirror) for row in build_rows(glyphs)]
    return " ".join(t for t in (line_text(ln, rtl, arabic_variants) for ln in lines) if t)


def read_table(grid: TableGrid, glyphs: list[Glyph], default_rtl: bool, arabic_variants: bool,
               mirror: bool = True) -> tuple[list[list[str]], bool]:
    """Rows of cell texts in reading order, and the table direction."""
    rtl = is_rtl(glyphs, default=default_rtl)
    rows = []
    for row in grid.cells:
        cells = []
        for box in row:
            cell_glyphs = [g for g in glyphs if box is not None and _inside(g, box)]
            cells.append(cell_text(cell_glyphs, rtl, arabic_variants, mirror))
        rows.append(cells[::-1] if rtl else cells)
    return rows, rtl
