"""One-off utility: render a simple markdown file (title + ## headings + paragraphs)
as a PDF, matching the look of the existing sample PDFs used by 01_create_search_index.py
and 04_multi_document_index.py. Not part of the numbered article scripts - this just
generates data/*.pdf from data/*.md so a second document exists for the multi-document
demos. Run it once whenever you add a new markdown source file.

Usage:
    python make_pdf_from_markdown.py data/neuromorphic-computing-rag-test.md
"""

from __future__ import annotations

import sys
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer


def markdown_to_pdf(md_path: Path, pdf_path: Path) -> None:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("DocTitle", parent=styles["Title"], fontSize=18, spaceAfter=18)
    h2_style = ParagraphStyle("H2", parent=styles["Heading2"], spaceBefore=14, spaceAfter=8)
    body_style = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=10.5, leading=15, spaceAfter=10)

    story = []
    for raw_line in md_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            story.append(Paragraph(line[2:], title_style))
        elif line.startswith("## "):
            story.append(Paragraph(line[3:], h2_style))
        else:
            # Reportlab's Paragraph understands basic <b>/<i> tags but not raw markdown
            # backticks; keep it simple by stripping backticks so inline code doesn't
            # break XML parsing inside Paragraph.
            story.append(Paragraph(line.replace("`", ""), body_style))
            story.append(Spacer(1, 2))

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=LETTER,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
    )
    doc.build(story)
    print(f"Wrote {pdf_path} from {md_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python make_pdf_from_markdown.py <path-to-markdown-file>")

    md_file = Path(sys.argv[1])
    markdown_to_pdf(md_file, md_file.with_suffix(".pdf"))
