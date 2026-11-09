#!/usr/bin/env python3
"""Render the sample knowledge-base documents as PDFs (for demoing PDF ingestion).

Usage: python scripts/generate_sample_docs.py   ->  sample-data/*.pdf
Needs reportlab (installed with the AI service requirements).
"""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "ai-service" / "knowledge_base"
EXTRA = ROOT / "sample-data"  # supplier_terms.md: a demo document that is NOT pre-loaded in the knowledge base
OUT = ROOT / "sample-data"


def render(md: Path, pdf: Path) -> None:
    styles = getSampleStyleSheet()
    flow = []
    for block in re.split(r"\n\s*\n", md.read_text(encoding="utf-8")):
        block = block.strip()
        if block.startswith("# "):
            flow.append(Paragraph(block[2:], styles["Title"]))
        elif block.startswith("## "):
            head, _, body = block.partition("\n")
            flow.append(Paragraph(head[3:], styles["Heading2"]))
            if body.strip():
                flow.append(Paragraph(body.strip(), styles["BodyText"]))
        else:
            flow.append(Paragraph(block, styles["BodyText"]))
        flow.append(Spacer(1, 8))
    SimpleDocTemplate(str(pdf), pagesize=A4, title=md.stem.replace("_", " ").title()).build(flow)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for md in sorted(list(SRC.glob("*.md")) + list(EXTRA.glob("*.md"))):
        pdf = OUT / f"{md.stem}.pdf"
        render(md, pdf)
        print("wrote", pdf.relative_to(ROOT))


if __name__ == "__main__":
    main()
