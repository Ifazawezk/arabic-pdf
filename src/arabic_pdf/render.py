"""Write a Document as plain text, Markdown or JSON."""

from __future__ import annotations

import json
from dataclasses import asdict, replace

from .document import Block, Document


def _escape_cell(cell: str) -> str:
    return cell.replace("|", "\\|").replace("\n", " ").strip()


def markdown_table(rows: list[list[str]]) -> str:
    """A pipe table. Cells keep reading order: the first cell of an Arabic table is its rightmost one."""
    width = max(len(r) for r in rows)
    padded = [[_escape_cell(c) for c in r] + [""] * (width - len(r)) for r in rows]
    lines = ["| " + " | ".join(padded[0]) + " |", "|" + " --- |" * width]
    lines += ["| " + " | ".join(r) + " |" for r in padded[1:]]
    return "\n".join(lines)


def _block_text(block: Block) -> str:
    if block.kind == "table":
        return "\n".join("\t".join(row) for row in block.rows)
    return block.text


def _block_markdown(block: Block) -> str:
    if block.kind == "table":
        return markdown_table(block.rows)
    if block.kind == "heading":
        return "#" * block.level + " " + block.text
    return block.text


def joined_blocks(document: Document) -> list[Block]:
    """Blocks with each paragraph that runs over a page break put back together."""
    blocks: list[Block] = []
    for block in document.blocks:
        if blocks and blocks[-1].continues:
            blocks[-1] = replace(blocks[-1], text=blocks[-1].text + " " + block.text, continues=block.continues)
        else:
            blocks.append(block)
    return blocks


def to_text(document: Document) -> str:
    """Blocks separated by blank lines; table cells separated by tabs."""
    return "\n\n".join(_block_text(b) for b in joined_blocks(document))


def to_markdown(document: Document) -> str:
    return "\n\n".join(_block_markdown(b) for b in joined_blocks(document))


def to_json(document: Document, indent: int | None = 2) -> str:
    """Pages and blocks with their positions in PDF points, origin at the top left."""
    return json.dumps(asdict(document), ensure_ascii=False, indent=indent)
