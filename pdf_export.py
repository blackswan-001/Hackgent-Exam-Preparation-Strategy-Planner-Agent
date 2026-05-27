"""
pdf_export.py — Standalone PDF export for the Exam Preparation Strategy Agent.
Converts the generated markdown strategy into a styled, downloadable PDF.

Zero dependencies on existing files except reading the markdown string.
Drop this file into the project folder — no other file needs changing.

Usage (from main.py or standalone):
    from pdf_export import export_strategy_to_pdf
    pdf_path = export_strategy_to_pdf(markdown_text, days_remaining, strategy_mode)

Requires:
    pip install reportlab
"""

import os
import re
import tempfile
from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.platypus.flowables import HRFlowable


# ─────────────────────────────────────────────
# Colour Palette
# ─────────────────────────────────────────────

NAVY       = colors.HexColor("#1a2f5a")
TEAL       = colors.HexColor("#2a9d8f")
AMBER      = colors.HexColor("#e9c46a")
LIGHT_BLUE = colors.HexColor("#e8f4f8")
LIGHT_GREY = colors.HexColor("#f5f5f5")
DARK_GREY  = colors.HexColor("#4a4a4a")
MID_GREY   = colors.HexColor("#888888")
WHITE      = colors.white
RED_SOFT   = colors.HexColor("#e76f51")


# ─────────────────────────────────────────────
# Style Sheet
# ─────────────────────────────────────────────

def build_styles():
    base = getSampleStyleSheet()

    styles = {
        "cover_title": ParagraphStyle(
            "cover_title",
            fontName="Helvetica-Bold",
            fontSize=26,
            textColor=WHITE,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub",
            fontName="Helvetica",
            fontSize=12,
            textColor=colors.HexColor("#d0e8f0"),
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "cover_meta": ParagraphStyle(
            "cover_meta",
            fontName="Helvetica-Oblique",
            fontSize=10,
            textColor=AMBER,
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
        "h1": ParagraphStyle(
            "h1",
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=NAVY,
            spaceBefore=14,
            spaceAfter=6,
            borderPad=4,
        ),
        "h2": ParagraphStyle(
            "h2",
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=TEAL,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "h3": ParagraphStyle(
            "h3",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=NAVY,
            spaceBefore=8,
            spaceAfter=3,
            leftIndent=4,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=10,
            textColor=DARK_GREY,
            spaceAfter=4,
            leading=15,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            fontName="Helvetica",
            fontSize=10,
            textColor=DARK_GREY,
            spaceAfter=3,
            leftIndent=16,
            bulletIndent=6,
            leading=14,
        ),
        "mini_goal_edu": ParagraphStyle(
            "mini_goal_edu",
            fontName="Helvetica",
            fontSize=9,
            textColor=colors.HexColor("#1a6b5a"),
            spaceAfter=2,
            leftIndent=20,
            leading=13,
        ),
        "mini_goal_fun": ParagraphStyle(
            "mini_goal_fun",
            fontName="Helvetica-Oblique",
            fontSize=9,
            textColor=colors.HexColor("#c45a20"),
            spaceAfter=2,
            leftIndent=20,
            leading=13,
        ),
        "motivation": ParagraphStyle(
            "motivation",
            fontName="Helvetica-BoldOblique",
            fontSize=12,
            textColor=TEAL,
            alignment=TA_CENTER,
            spaceBefore=10,
            spaceAfter=10,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName="Helvetica-Oblique",
            fontSize=8,
            textColor=MID_GREY,
            alignment=TA_CENTER,
        ),
        "table_header": ParagraphStyle(
            "table_header",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=WHITE,
            alignment=TA_CENTER,
        ),
        "table_cell": ParagraphStyle(
            "table_cell",
            fontName="Helvetica",
            fontSize=9,
            textColor=DARK_GREY,
            alignment=TA_LEFT,
            leading=12,
        ),
    }
    return styles


# ─────────────────────────────────────────────
# Markdown Parser → ReportLab Flowables
# ─────────────────────────────────────────────

def _clean(text: str) -> str:
    """Escape XML special chars for ReportLab Paragraph."""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    # Convert **bold** to <b>bold</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Convert *italic* to <i>italic</i>
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    # Convert `code` to styled span
    text = re.sub(r'`(.*?)`', r'<font name="Courier" size="9">\1</font>', text)
    return text


def _parse_table(lines: list, styles: dict) -> Optional[Table]:
    """Parse markdown table lines into a ReportLab Table."""
    rows = []
    for line in lines:
        if re.match(r'^\s*\|[-:| ]+\|\s*$', line):
            continue  # skip separator row
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(cells)

    if len(rows) < 2:
        return None

    # Build table data with styled paragraphs
    table_data = []
    for i, row in enumerate(rows):
        if i == 0:
            table_data.append([
                Paragraph(_clean(cell), styles["table_header"]) for cell in row
            ])
        else:
            table_data.append([
                Paragraph(_clean(cell), styles["table_cell"]) for cell in row
            ])

    col_count = max(len(r) for r in table_data)
    page_width = A4[0] - 40 * mm
    col_width = page_width / col_count

    t = Table(table_data, colWidths=[col_width] * col_count, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR",   (0, 0), (-1, 0), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BLUE]),
        ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def markdown_to_flowables(markdown_text: str, styles: dict) -> list:
    """
    Convert markdown string into a list of ReportLab flowables.
    Handles: ## headings, ### headings, tables, bullet lists, mini goals, body text.
    """
    flowables = []
    lines = markdown_text.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            flowables.append(Spacer(1, 3))
            i += 1
            continue

        # HR separator ---
        if re.match(r'^-{3,}$', stripped):
            flowables.append(HRFlowable(
                width="100%", thickness=0.5,
                color=colors.HexColor("#cccccc"),
                spaceAfter=4, spaceBefore=4
            ))
            i += 1
            continue

        # H1: # Title
        if stripped.startswith("# ") and not stripped.startswith("## "):
            text = stripped[2:].strip()
            # Strip emoji for cleaner rendering
            text = re.sub(r'[^\x00-\x7F]', '', text).strip()
            flowables.append(Paragraph(_clean(text), styles["h1"]))
            flowables.append(HRFlowable(
                width="100%", thickness=1.5,
                color=NAVY, spaceAfter=4
            ))
            i += 1
            continue

        # H2: ## Section
        if stripped.startswith("## ") and not stripped.startswith("### "):
            text = stripped[3:].strip()
            text = re.sub(r'[^\x00-\x7F]', '', text).strip()
            flowables.append(Paragraph(_clean(text), styles["h2"]))
            i += 1
            continue

        # H3: ### Day heading
        if stripped.startswith("### "):
            text = stripped[4:].strip()
            text = re.sub(r'[^\x00-\x7F]', '', text).strip()
            flowables.append(Paragraph(_clean(text), styles["h3"]))
            i += 1
            continue

        # Markdown table — collect all consecutive table lines
        if stripped.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            tbl = _parse_table(table_lines, styles)
            if tbl:
                flowables.append(Spacer(1, 3))
                flowables.append(tbl)
                flowables.append(Spacer(1, 4))
            continue

        # Mini goals (Educational / Fun)
        if re.match(r'^-\s*educational:', stripped, re.IGNORECASE):
            text = re.sub(r'^-\s*educational:\s*', '', stripped, flags=re.IGNORECASE)
            text = re.sub(r'[^\x00-\x7F]', '', text).strip()
            flowables.append(Paragraph(f"  Study: {_clean(text)}", styles["mini_goal_edu"]))
            i += 1
            continue

        if re.match(r'^-\s*fun:', stripped, re.IGNORECASE):
            text = re.sub(r'^-\s*fun:\s*', '', stripped, flags=re.IGNORECASE)
            text = re.sub(r'[^\x00-\x7F]', '', text).strip()
            flowables.append(Paragraph(f"  Play: {_clean(text)}", styles["mini_goal_fun"]))
            i += 1
            continue

        # Generic bullet point
        if stripped.startswith("- ") or stripped.startswith("* "):
            text = stripped[2:].strip()
            text = re.sub(r'[^\x00-\x7F]', '', text).strip()
            flowables.append(Paragraph(
                f"&bull; {_clean(text)}", styles["bullet"]
            ))
            i += 1
            continue

        # Final Motivation line (bold italic, centred)
        if "final motivation" in stripped.lower():
            i += 1
            # Grab the next non-empty line as the motivation
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i < len(lines):
                mot = lines[i].strip()
                mot = re.sub(r'[^\x00-\x7F]', '', mot).strip()
                if mot:
                    flowables.append(Spacer(1, 6))
                    flowables.append(HRFlowable(
                        width="60%", thickness=1,
                        color=TEAL, spaceAfter=6,
                        hAlign="CENTER"
                    ))
                    flowables.append(Paragraph(_clean(mot), styles["motivation"]))
                i += 1
            continue

        # "Mini Goals:" label line
        if stripped.lower().startswith("mini goals"):
            text = re.sub(r'[^\x00-\x7F]', '', stripped).strip()
            flowables.append(Paragraph(
                f"<b>{_clean(text)}</b>", styles["body"]
            ))
            i += 1
            continue

        # Default: body paragraph
        text = re.sub(r'[^\x00-\x7F]', '', stripped).strip()
        if text:
            flowables.append(Paragraph(_clean(text), styles["body"]))
        i += 1

    return flowables


# ─────────────────────────────────────────────
# Cover Page Builder
# ─────────────────────────────────────────────

def build_cover_page(
    strategy_mode: str,
    days_remaining: int,
    generated_at: str,
    styles: dict,
) -> list:
    """Build a styled cover page as a list of flowables."""
    flowables = []

    # Top colour band via a single-cell Table
    mode_emoji = "INTENSIVE REVISION" if "Intensive" in strategy_mode else "PROGRESSIVE MASTERY"
    band_color = RED_SOFT if "Intensive" in strategy_mode else TEAL

    cover_data = [[
        Paragraph("EXAM PREPARATION", styles["cover_title"]),
    ]]
    cover_table = Table(cover_data, colWidths=[A4[0] - 40 * mm])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 30),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    flowables.append(cover_table)

    subtitle_data = [[
        Paragraph("STRATEGY AGENT", styles["cover_title"]),
    ]]
    subtitle_table = Table(subtitle_data, colWidths=[A4[0] - 40 * mm])
    subtitle_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 30),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    flowables.append(subtitle_table)

    flowables.append(Spacer(1, 16))

    # Mode badge
    badge_data = [[Paragraph(mode_emoji + " MODE", ParagraphStyle(
        "badge",
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=WHITE,
        alignment=TA_CENTER,
    ))]]
    badge_table = Table(badge_data, colWidths=[80 * mm])
    badge_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), band_color),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
    ]))

    # Centre the badge using a wrapper table
    wrapper = Table([[badge_table]], colWidths=[A4[0] - 40 * mm])
    wrapper.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    flowables.append(wrapper)
    flowables.append(Spacer(1, 20))

    # Info grid
    info_data = [
        ["Days Until Exam", str(days_remaining)],
        ["Strategy Mode",   strategy_mode],
        ["Generated",       generated_at],
        ["Powered By",      "Groq + LangGraph"],
    ]
    info_table = Table(info_data, colWidths=[55 * mm, 95 * mm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), LIGHT_BLUE),
        ("BACKGROUND",    (1, 0), (1, -1), WHITE),
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",      (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 10),
        ("TEXTCOLOR",     (0, 0), (0, -1), NAVY),
        ("TEXTCOLOR",     (1, 0), (1, -1), DARK_GREY),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_GREY, WHITE]),
    ]))

    # Centre the info table
    info_wrapper = Table([[info_table]], colWidths=[A4[0] - 40 * mm])
    info_wrapper.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    flowables.append(info_wrapper)
    flowables.append(Spacer(1, 30))

    # Disclaimer
    disclaimer = (
        "This strategy was generated by an AI planning agent. "
        "Adjust timings to suit your personal needs. Good luck!"
    )
    flowables.append(Paragraph(disclaimer, ParagraphStyle(
        "disc",
        fontName="Helvetica-Oblique",
        fontSize=9,
        textColor=MID_GREY,
        alignment=TA_CENTER,
    )))

    flowables.append(PageBreak())
    return flowables


# ─────────────────────────────────────────────
# Header / Footer Canvas
# ─────────────────────────────────────────────

class HeaderFooterCanvas:
    """Mixin to draw header and footer on every page except cover."""

    def __init__(self, strategy_mode: str, total_pages_placeholder: list):
        self.strategy_mode = strategy_mode
        self._total = total_pages_placeholder

    def on_later_pages(self, canvas, doc):
        if doc.page <= 1:
            return
        canvas.saveState()
        w, h = A4

        # Header bar
        canvas.setFillColor(NAVY)
        canvas.rect(20 * mm, h - 18 * mm, w - 40 * mm, 10 * mm, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(23 * mm, h - 12 * mm, "Exam Preparation Strategy Agent")
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(w - 23 * mm, h - 12 * mm, self.strategy_mode)

        # Footer
        canvas.setFillColor(MID_GREY)
        canvas.setFont("Helvetica-Oblique", 8)
        canvas.drawString(20 * mm, 12 * mm, "Generated by Exam Preparation Strategy Agent")
        canvas.drawRightString(w - 20 * mm, 12 * mm, f"Page {doc.page}")
        canvas.setStrokeColor(colors.HexColor("#cccccc"))
        canvas.line(20 * mm, 16 * mm, w - 20 * mm, 16 * mm)

        canvas.restoreState()


# ─────────────────────────────────────────────
# Main Export Function
# ─────────────────────────────────────────────

def export_strategy_to_pdf(
    markdown_text: str,
    days_remaining: int = 0,
    strategy_mode: str = "Progressive Mastery Mode",
    output_path: Optional[str] = None,
) -> str:
    """
    Convert the agent's markdown output into a styled PDF.

    Args:
        markdown_text:  The full markdown string from the agent.
        days_remaining: Number of days until exam (for cover page).
        strategy_mode:  Strategy mode string (for cover + header).
        output_path:    Where to save the PDF. Uses temp dir if None.

    Returns:
        Absolute path to the generated PDF file.
    """
    if not output_path:
        tmp_dir = tempfile.gettempdir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(tmp_dir, f"exam_strategy_{timestamp}.pdf")

    generated_at = datetime.now().strftime("%d %b %Y, %H:%M")
    styles = build_styles()

    # Build document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=22 * mm,
        bottomMargin=22 * mm,
        title="Exam Preparation Strategy",
        author="Exam Preparation Strategy Agent",
    )

    hf = HeaderFooterCanvas(strategy_mode, [])

    # Assemble flowables
    story = []
    story += build_cover_page(strategy_mode, days_remaining, generated_at, styles)
    story += markdown_to_flowables(markdown_text, styles)

    # Build with header/footer on pages > 1
    doc.build(
        story,
        onFirstPage=lambda c, d: None,  # cover — no header/footer
        onLaterPages=hf.on_later_pages,
    )

    print(f"[pdf_export] PDF saved: {output_path}")
    return output_path


# ─────────────────────────────────────────────
# Gradio Integration Helper
# ─────────────────────────────────────────────

def add_pdf_export_to_ui(demo, get_state_fn):
    """
    Attach a PDF export button to an existing Gradio Blocks demo.

    This is the zero-modification integration point.
    Call this from a separate launcher file — main.py never changes.

    Args:
        demo:         The existing Gradio Blocks object from build_ui()
        get_state_fn: A callable that returns (markdown_text, days_remaining, strategy_mode)
                      from the current UI state.
    """
    import gradio as gr

    with demo:
        with gr.Row():
            export_btn = gr.Button(
                "📄 Export Strategy as PDF",
                variant="secondary",
                size="sm",
            )
            pdf_output = gr.File(
                label="Download PDF",
                visible=False,
            )

        def handle_export(plan_markdown: str, summary_markdown: str):
            """Generate PDF from current plan output."""
            if not plan_markdown or "will be generated here" in plan_markdown:
                return gr.update(visible=False), gr.update(
                    value=None, visible=False
                )

            # Extract mode and days from summary card if present
            days = 0
            mode = "Progressive Mastery Mode"

            days_match = re.search(r"\*\*Days Remaining:\*\*\s*(\d+)", summary_markdown or "")
            if days_match:
                days = int(days_match.group(1))

            mode_match = re.search(r"\*\*Strategy Mode:\*\*\s*(.+)", summary_markdown or "")
            if mode_match:
                mode = mode_match.group(1).strip()

            try:
                pdf_path = export_strategy_to_pdf(plan_markdown, days, mode)
                return gr.update(value=pdf_path, visible=True)
            except Exception as e:
                print(f"[pdf_export] Export failed: {e}")
                return gr.update(visible=False)

        export_btn.click(
            fn=handle_export,
            inputs=get_state_fn(),
            outputs=[pdf_output],
        )

    return demo
