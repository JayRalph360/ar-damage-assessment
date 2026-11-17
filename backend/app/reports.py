"""Inspection report generation (Save Inspection Report use case) – produces a PDF."""
import io
import json
import os
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

from .db import DATA_DIR
from .detector import DAMAGE_TYPES, recommendation

NAVY = colors.HexColor("#0f2a43")
ACCENT = colors.HexColor("#f59e0b")
SEV_COL = {"High": colors.HexColor("#dc2626"), "Medium": colors.HexColor("#f59e0b"), "Low": colors.HexColor("#16a34a")}


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("H1x", parent=ss["Title"], textColor=NAVY, fontSize=18, leading=22, spaceAfter=4))
    ss.add(ParagraphStyle("H2x", parent=ss["Heading2"], textColor=NAVY, fontSize=13, spaceBefore=10, spaceAfter=6))
    ss.add(ParagraphStyle("Small", parent=ss["Normal"], fontSize=8.5, textColor=colors.HexColor("#475569")))
    ss.add(ParagraphStyle("Cell", parent=ss["Normal"], fontSize=9, leading=11))
    return ss


def _table(data, widths, header=True):
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9)]
    else:
        style += [("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                  ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9)]
    t.setStyle(TableStyle(style))
    return t


def build_report(inspection: dict, findings: list, inspector: dict) -> bytes:
    ss = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"Inspection Report #{inspection['id']}")
    W = A4[0] - 32 * mm
    el = []

    el.append(Paragraph("Infrastructure Damage Assessment Report", ss["H1x"]))
    el.append(Paragraph("AR-Based Real-Time Infrastructure Damage Assessment System", ss["Small"]))
    el.append(Spacer(1, 8))

    all_dets = [d for f in findings for d in json.loads(f["detections_json"])]
    condition = inspection.get("condition") or "Not assessed"
    info = [
        ["Report No.", f"INS-{inspection['id']:05d}"],
        ["Asset", inspection["asset_name"]],
        ["Infrastructure type", inspection["infrastructure_type"]],
        ["Location", inspection.get("location") or "-"],
        ["GPS", f"{inspection['latitude']:.5f}, {inspection['longitude']:.5f}" if inspection.get("latitude") else "-"],
        ["Inspector", f"{inspector['full_name']} ({inspector['role']})"],
        ["Started", inspection["created_at"] + " UTC"],
        ["Status", inspection["status"] + (f" – {inspection['completed_at']} UTC" if inspection.get("completed_at") else "")],
        ["Overall condition", condition],
    ]
    el.append(_table(info, [45 * mm, W - 45 * mm], header=False))

    el.append(Paragraph("Summary of Findings", ss["H2x"]))
    summary = [["Damage type", "Detected", "High", "Medium", "Low"]]
    for key, label in DAMAGE_TYPES.items():
        ds = [d for d in all_dets if d["type"] == key]
        summary.append([label, len(ds)] + [sum(1 for d in ds if d["severity"] == s) for s in ("High", "Medium", "Low")])
    summary.append(["Total", len(all_dets)] + [sum(1 for d in all_dets if d["severity"] == s) for s in ("High", "Medium", "Low")])
    t = _table(summary, [W * 0.36] + [W * 0.16] * 4)
    t.setStyle(TableStyle([("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 9), ("ALIGN", (1, 0), (-1, -1), "CENTER")]))
    el.append(t)
    el.append(Spacer(1, 6))
    el.append(Paragraph(f"<b>Recommendation:</b> {recommendation(condition) or '-'}", ss["Normal"]))
    if inspection.get("description"):
        el.append(Spacer(1, 4))
        el.append(Paragraph(f"<b>Inspection details:</b> {inspection['description']}", ss["Normal"]))
    if inspection.get("notes"):
        el.append(Spacer(1, 4))
        el.append(Paragraph(f"<b>Inspector notes:</b> {inspection['notes']}", ss["Normal"]))

    for n, f in enumerate(findings, 1):
        dets = json.loads(f["detections_json"])
        block = [Paragraph(f"Capture {n} — {f['created_at']} UTC — condition: {f['condition']}", ss["H2x"])]
        img_path = os.path.join(DATA_DIR, f["annotated_path"])
        if os.path.exists(img_path):
            img = Image(img_path)
            ratio = img.imageHeight / img.imageWidth
            img.drawWidth = W
            img.drawHeight = min(W * ratio, 120 * mm)
            img.drawWidth = img.drawHeight / ratio
            block.append(img)
            block.append(Spacer(1, 4))
        if dets:
            rows = [["#", "Damage", "Severity", "Confidence", "Measurements"]]
            for i, d in enumerate(dets, 1):
                m = ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in d.get("metrics", {}).items() if k != "open_path")
                rows.append([i, d["label"], d["severity"], f"{int(d['confidence'] * 100)}%", Paragraph(m, ss["Cell"])])
            dt = _table(rows, [8 * mm, 32 * mm, 22 * mm, 22 * mm, W - 84 * mm])
            for i, d in enumerate(dets, 1):
                dt.setStyle(TableStyle([("TEXTCOLOR", (2, i), (2, i), SEV_COL.get(d["severity"], colors.black)),
                                        ("FONT", (2, i), (2, i), "Helvetica-Bold", 9)]))
            block.append(dt)
        else:
            block.append(Paragraph("No visible damage detected in this capture.", ss["Normal"]))
        if f.get("notes"):
            block.append(Spacer(1, 3))
            block.append(Paragraph(f"<b>Notes:</b> {f['notes']}", ss["Normal"]))
        block.append(Paragraph(f"Engine: {f.get('engine') or '-'} · processing time {f.get('processing_ms') or 0:.0f} ms", ss["Small"]))
        el.append(KeepTogether(block))

    el.append(Spacer(1, 14))
    el.append(Paragraph(
        "Automated detections support, but do not replace, the professional judgement of a qualified engineer. "
        f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC.", ss["Small"]))

    def footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(16 * mm, 9 * mm, f"INS-{inspection['id']:05d} · {inspection['asset_name']}")
        canvas.drawRightString(A4[0] - 16 * mm, 9 * mm, f"Page {doc_.page}")
        canvas.setStrokeColor(ACCENT)
        canvas.setLineWidth(2)
        canvas.line(16 * mm, A4[1] - 10 * mm, A4[0] - 16 * mm, A4[1] - 10 * mm)
        canvas.restoreState()

    doc.build(el, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
