"""Render the submission Markdown report as a self-contained, printable PDF."""

from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "output" / "report" / "AI_Economic_Perceptions_Consumer_Sentiment_Report.md"
OUTPUT = ROOT / "output" / "report" / "AI_Economic_Perceptions_Consumer_Sentiment_Report.pdf"


def inline(text: str) -> str:
    text = html.escape(text.strip())
    text = re.sub(r"!\[[^]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r"<font name=\"Courier\">\1</font>", text)
    return text


def table_rows(lines: list[str]) -> list[list[str]]:
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells):
            continue
        rows.append(cells)
    return rows


def build_pdf() -> None:
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, leading=27, textColor=colors.HexColor("#17365D"), spaceAfter=16))
    styles.add(ParagraphStyle("ReportH1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=colors.HexColor("#17365D"), spaceBefore=14, spaceAfter=7))
    styles.add(ParagraphStyle("ReportH2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=colors.HexColor("#2F75B5"), spaceBefore=10, spaceAfter=5))
    styles.add(ParagraphStyle("ReportBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=12, spaceAfter=6))
    styles.add(ParagraphStyle("TableCell", parent=styles["BodyText"], fontName="Helvetica", fontSize=7, leading=8.5))
    styles.add(ParagraphStyle("TableHead", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7, leading=8.5, textColor=colors.white))
    styles.add(ParagraphStyle("Caption", parent=styles["BodyText"], fontName="Helvetica-Oblique", fontSize=8, leading=10, textColor=colors.HexColor("#555555"), spaceAfter=7))

    def page_number(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D9E2F3"))
        canvas.line(doc.leftMargin, 0.38 * inch, landscape(letter)[0] - doc.rightMargin, 0.38 * inch)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#5B6573"))
        canvas.drawString(doc.leftMargin, 0.22 * inch, "AI Economic Perceptions and Consumer Sentiment")
        canvas.drawRightString(landscape(letter)[0] - doc.rightMargin, 0.22 * inch, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(OUTPUT), pagesize=landscape(letter), leftMargin=0.48 * inch, rightMargin=0.48 * inch, topMargin=0.5 * inch, bottomMargin=0.58 * inch, title="AI Economic Perceptions and Consumer Sentiment")
    source_lines = SOURCE.read_text(encoding="utf-8").splitlines()
    story = []
    index = 0
    usable_width = landscape(letter)[0] - doc.leftMargin - doc.rightMargin

    while index < len(source_lines):
        line = source_lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith("!"):
            story.append(Paragraph("Figure available in the companion Markdown report.", styles["Caption"]))
            index += 1
            continue
        if line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), styles["ReportTitle"]))
            index += 1
            continue
        if line.startswith("## "):
            story.append(Paragraph(inline(line[3:]), styles["ReportH1"]))
            index += 1
            continue
        if line.startswith("### "):
            story.append(Paragraph(inline(line[4:]), styles["ReportH2"]))
            index += 1
            continue
        if line.startswith("|"):
            end = index
            while end < len(source_lines) and source_lines[end].startswith("|"):
                end += 1
            rows = table_rows(source_lines[index:end])
            if rows:
                columns = max(len(row) for row in rows)
                normalized = [row + [""] * (columns - len(row)) for row in rows]
                width = usable_width / columns
                data = [[Paragraph(inline(cell), styles["TableHead"] if row_no == 0 else styles["TableCell"]) for cell in row] for row_no, row in enumerate(normalized)]
                table = Table(data, colWidths=[width] * columns, repeatRows=1, hAlign="LEFT")
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D9D9D9")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FB")]),
                ]))
                story.extend([table, Spacer(1, 8)])
            index = end
            continue
        if line.startswith("- "):
            story.append(Paragraph("&bull; " + inline(line[2:]), styles["ReportBody"]))
            index += 1
            continue
        if re.match(r"^Figure \d+\.", line):
            story.append(Paragraph(inline(line), styles["Caption"]))
            index += 1
            continue
        story.append(Paragraph(inline(line), styles["ReportBody"]))
        index += 1

    doc.build(story, onFirstPage=page_number, onLaterPages=page_number)


if __name__ == "__main__":
    build_pdf()
