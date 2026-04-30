"""
generators/pdf_generator.py
Produces a professionally formatted PDF from a ParsedDoc using ReportLab.
Pure Python — no system dependencies beyond: pip install reportlab
"""

import re
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    HRFlowable, Table, TableStyle, KeepTogether,
)

from agent.parser import ParsedDoc, Block, BT, Seg
from config import APP_NAME, APP_VERSION

# ── colour palette ───────────────────────────────────────────
_C1     = colors.HexColor("#1F497D")
_C2     = colors.HexColor("#2E74B5")
_C3     = colors.HexColor("#5A96C8")
_CM     = colors.HexColor("#666666")
_EQ_BG  = colors.HexColor("#EFF4FB")
_DG_BG  = colors.HexColor("#FFF8E7")
_QT_BG  = colors.HexColor("#F0F8FF")
_BDR    = colors.HexColor("#CCCCCC")
_AMBER  = colors.HexColor("#D29922")
_WHITE  = colors.white
_STRIPE = colors.HexColor("#F2F7FF")


class PdfGenerator:

    def generate(self, doc: ParsedDoc, path: str) -> None:
        styles = _make_styles()
        story  = []

        # Title
        story.append(Paragraph(_esc(doc.title), styles["T"]))
        story.append(Paragraph(
            f"Extracted by {APP_NAME} v{APP_VERSION}  ·  "
            f"{datetime.now().strftime('%d %b %Y  %H:%M')}",
            styles["Sub"]))
        story.append(HRFlowable(width="100%", thickness=1, color=_BDR))
        story.append(Spacer(1, 0.3*cm))

        for block in doc.blocks:
            story.extend(self._block(block, styles))

        # Footer
        story.append(Spacer(1, 0.6*cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=_BDR))
        story.append(Paragraph(
            f"<font size='8' color='#888888'>"
            f"{APP_NAME}  ·  FAST-NUCES  ·  "
            f"{doc.stats.get('words',0)} words  ·  "
            f"{doc.stats.get('equations',0)} equations extracted</font>",
            styles["Cen"]))

        pdf = SimpleDocTemplate(
            path, pagesize=A4,
            leftMargin=2.5*cm, rightMargin=2.5*cm,
            topMargin=2*cm,    bottomMargin=2*cm,
        )
        pdf.build(story)

    # ── block dispatcher ─────────────────────────────────────
    def _block(self, block: Block, styles) -> list:
        bt  = block.btype
        out = []

        if   bt == BT.H1:  out.append(Paragraph(_esc(block.raw), styles["H1"]))
        elif bt == BT.H2:  out.append(Paragraph(_esc(block.raw), styles["H2"]))
        elif bt == BT.H3:  out.append(Paragraph(_esc(block.raw), styles["H3"]))
        elif bt == BT.H4:  out.append(Paragraph(_esc(block.raw), styles["H4"]))

        elif bt == BT.PARA:
            html = _segs_html(block.segs) or _esc(block.raw)
            out.append(Paragraph(html, styles["Body"]))

        elif bt == BT.BULLETS:
            for child in block.children:
                html = _segs_html(child.segs) or _esc(child.raw)
                out.append(Paragraph(f"• {html}", styles["Blt"]))

        elif bt == BT.NUMBERED:
            for i, child in enumerate(block.children, 1):
                html = _segs_html(child.segs) or _esc(child.raw)
                out.append(Paragraph(f"{i}. {html}", styles["Blt"]))

        elif bt == BT.EQUATION:
            eq   = _esc(block.raw)
            data = [[Paragraph(
                f'<font face="Courier" color="#1A3A6E"><b>{eq}</b></font>',
                styles["Cen"])]]
            t = Table(data, colWidths=[14*cm])
            t.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), _EQ_BG),
                ("BOX",           (0,0),(-1,-1), 0.5, _C2),
                ("TOPPADDING",    (0,0),(-1,-1), 7),
                ("BOTTOMPADDING", (0,0),(-1,-1), 7),
            ]))
            out.append(KeepTogether([Spacer(1,0.2*cm), t, Spacer(1,0.2*cm)]))

        elif bt == BT.DIAGRAM:
            desc = _esc(block.raw)
            data = [[Paragraph(
                f'<b><font color="#D29922">📊 Diagram</font></b><br/>{desc}',
                styles["Body"])]]
            t = Table(data, colWidths=[14*cm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0,0),(-1,-1), _DG_BG),
                ("BOX",        (0,0),(-1,-1), 0.5, _AMBER),
                ("PADDING",    (0,0),(-1,-1), 7),
            ]))
            out.append(KeepTogether([Spacer(1,0.2*cm), t, Spacer(1,0.2*cm)]))

        elif bt == BT.QUOTE:
            html = _segs_html(block.segs) or _esc(block.raw)
            data = [[Paragraph(html, styles["Body"])]]
            t = Table(data, colWidths=[13*cm])
            t.setStyle(TableStyle([
                ("BACKGROUND",  (0,0),(-1,-1), _QT_BG),
                ("LEFTPADDING", (0,0),(-1,-1), 14),
                ("LINEAFTER",   (0,0),(0,-1),  3, _C2),
                ("PADDING",     (0,0),(-1,-1), 6),
            ]))
            out.append(KeepTogether([Spacer(1,0.1*cm), t, Spacer(1,0.1*cm)]))

        elif bt == BT.TABLE:
            t = _md_table(block.raw, styles)
            if t:
                out.append(KeepTogether([Spacer(1,0.2*cm), t, Spacer(1,0.2*cm)]))

        elif bt == BT.DIVIDER:
            out.append(HRFlowable(width="100%", thickness=0.5, color=_BDR))

        out.append(Spacer(1, 0.12*cm))
        return out


# ── helpers ──────────────────────────────────────────────────

def _esc(text: str) -> str:
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))

def _segs_html(segs: list[Seg]) -> str:
    parts = []
    for s in segs:
        t = _esc(s.text)
        if s.is_eq:
            parts.append(f'<font face="Courier" color="#1A3A6E">{t}</font>')
        elif s.bold:
            parts.append(f"<b>{t}</b>")
        elif s.italic:
            parts.append(f"<i>{t}</i>")
        elif s.is_code:
            parts.append(f'<font face="Courier">{t}</font>')
        else:
            parts.append(t)
    return "".join(parts)

def _md_table(raw: str, styles) -> Table | None:
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    rows  = []
    for line in lines:
        if re.match(r'\|[-| :]+\|', line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)
    if not rows:
        return None

    ncols = max(len(r) for r in rows)
    rows  = [r + [""]*(ncols-len(r)) for r in rows]
    col_w = [14*cm / ncols] * ncols
    data  = [[Paragraph(_esc(c), styles["Body"]) for c in row] for row in rows]

    t = Table(data, colWidths=col_w)
    t.setStyle(TableStyle([
        ("GRID",         (0,0),(-1,-1), 0.5, _BDR),
        ("BACKGROUND",   (0,0),(-1, 0), _C1),
        ("TEXTCOLOR",    (0,0),(-1, 0), _WHITE),
        ("FONTNAME",     (0,0),(-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0),(-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[_WHITE, _STRIPE]),
        ("TOPPADDING",   (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
    ]))
    return t

def _make_styles() -> dict:
    s = {}
    s["T"]    = ParagraphStyle("T",
        fontName="Helvetica-Bold", fontSize=22,
        textColor=_C1, alignment=TA_CENTER, spaceAfter=4)
    s["Sub"]  = ParagraphStyle("Sub",
        fontName="Helvetica", fontSize=9,
        textColor=_CM, alignment=TA_CENTER, spaceAfter=8)
    s["H1"]   = ParagraphStyle("H1",
        fontName="Helvetica-Bold", fontSize=16,
        textColor=_C1, spaceBefore=12, spaceAfter=4)
    s["H2"]   = ParagraphStyle("H2",
        fontName="Helvetica-Bold", fontSize=13,
        textColor=_C2, spaceBefore=10, spaceAfter=3)
    s["H3"]   = ParagraphStyle("H3",
        fontName="Helvetica-Bold", fontSize=11,
        textColor=_C3, spaceBefore=8, spaceAfter=2)
    s["H4"]   = ParagraphStyle("H4",
        fontName="Helvetica-Bold", fontSize=10,
        textColor=_CM, spaceBefore=6, spaceAfter=2)
    s["Body"] = ParagraphStyle("Body",
        fontName="Helvetica", fontSize=10,
        leading=14, spaceAfter=4, alignment=TA_JUSTIFY)
    s["Blt"]  = ParagraphStyle("Blt",
        fontName="Helvetica", fontSize=10,
        leading=13, spaceAfter=2,
        leftIndent=14, firstLineIndent=0)
    s["Cen"]  = ParagraphStyle("Cen",
        fontName="Helvetica", fontSize=10, alignment=TA_CENTER)
    return s
