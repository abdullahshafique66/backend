"""Server-side report files: CSV, Excel (.xlsx) and PDF."""
import csv
import io

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .. import schemas

UNIT_LABELS = {"piece": "Piece", "kg": "Kg", "gram": "Gram", "liter": "Liter", "dozen": "Dozen", "pack": "Pack", "other": "Other"}
EMERALD = "087F5B"


def _qty(e: schemas.ExpenseOut) -> str:
    if e.quantity is None:
        return ""
    q = int(e.quantity) if float(e.quantity).is_integer() else e.quantity
    return f"{q} {UNIT_LABELS.get(e.unit or '', '')}".strip()


def _rs(n: int | float) -> str:
    return f"Rs. {round(n):,}"


def to_csv(report: schemas.Report, cat_names: dict[str, str]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Date", "Item", "Category", "Quantity", "Amount (Rs.)", "Note"])
    for e in report.expenses:
        w.writerow([e.date.isoformat(), e.item_name, cat_names.get(e.category_id, "Other"), _qty(e), e.amount, e.note or ""])
    w.writerow([])
    w.writerow(["Total Items", report.total_items])
    w.writerow(["Total Expense (Rs.)", report.total_expense])
    return ("﻿" + buf.getvalue()).encode("utf-8")


def to_xlsx(report: schemas.Report, cat_names: dict[str, str]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Expenses"
    head_font = Font(bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor=EMERALD)
    money = '"Rs. "#,##0'
    ws.append([f"APNA HISAB KITAAB — {report.title}"])
    ws["A1"].font = Font(bold=True, size=14, color=EMERALD)
    ws.append([report.period_label])
    ws.append([])
    ws.append(["Date", "Item", "Category", "Quantity", "Amount (Rs.)", "Note"])
    for c in ws[4]:
        c.font, c.fill = head_font, head_fill
    for e in report.expenses:
        ws.append([e.date.isoformat(), e.item_name, cat_names.get(e.category_id, "Other"), _qty(e), e.amount, e.note or ""])
        ws.cell(ws.max_row, 5).number_format = money
    ws.append([])
    ws.append(["Total Items", report.total_items])
    ws.append(["Total Expense", report.total_expense])
    ws.cell(ws.max_row, 2).number_format = money
    ws.cell(ws.max_row, 1).font = ws.cell(ws.max_row, 2).font = Font(bold=True)
    for col, width in zip("ABCDEF", [12, 24, 14, 12, 14, 30]):
        ws.column_dimensions[col].width = width

    cs = wb.create_sheet("Categories")
    cs.append(["Category", "Entries", "Total (Rs.)", "Share %"])
    for c in cs[1]:
        c.font, c.fill = head_font, head_fill
    for c in report.by_category:
        cs.append([c.name, c.count, c.total, round(c.share * 100, 1)])
        cs.cell(cs.max_row, 3).number_format = money
    for col, width in zip("ABCD", [18, 10, 16, 10]):
        cs.column_dimensions[col].width = width

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def to_pdf(report: schemas.Report, cat_names: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    W, H = A4
    M = 16 * mm
    c = canvas.Canvas(buf, pagesize=A4)
    emerald = colors.HexColor("#087F5B")
    ink = colors.HexColor("#17211D")
    muted = colors.HexColor("#66736D")

    def footer():
        c.setFont("Helvetica", 8)
        c.setFillColor(muted)
        c.drawString(M, 10 * mm, "Apna Hisab Kitaab · Write your expense. We'll do the hisab.")
        c.drawRightString(W - M, 10 * mm, f"Page {c.getPageNumber()}")

    # header band
    c.setFillColor(emerald)
    c.rect(0, H - 32 * mm, W, 32 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#F4A340"))
    c.rect(0, H - 33.5 * mm, W, 1.5 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(M, H - 16 * mm, "APNA HISAB KITAAB")
    c.setFont("Helvetica", 10)
    c.drawString(M, H - 23 * mm, "Har Kharchay Ka Apna Hisab.")
    c.drawRightString(W - M, H - 16 * mm, f"Generated {report.generated_at:%d %b %Y}")

    y = H - 48 * mm
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(M, y, report.title)
    c.setFont("Helvetica", 11)
    c.setFillColor(muted)
    c.drawString(M, y - 7 * mm, report.period_label)

    y -= 26 * mm
    bw = (W - 2 * M - 6 * mm) / 2
    for i, (label, value) in enumerate([("Total Items", str(report.total_items)), ("Total Expense", _rs(report.total_expense))]):
        x = M + i * (bw + 6 * mm)
        c.setFillColor(colors.HexColor("#FAFAF7"))
        c.setStrokeColor(colors.HexColor("#E4E9E6"))
        c.roundRect(x, y, bw, 20 * mm, 3 * mm, fill=1, stroke=1)
        c.setFillColor(muted)
        c.setFont("Helvetica", 9)
        c.drawString(x + 5 * mm, y + 13 * mm, label)
        c.setFillColor(ink)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(x + 5 * mm, y + 5 * mm, value)

    y -= 12 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(M, y, "Category Breakdown")
    y -= 7 * mm
    bar_max = W - 2 * M - 75 * mm
    for cat in report.by_category:
        c.setFont("Helvetica", 9.5)
        c.setFillColor(ink)
        c.drawString(M, y, cat.name)
        c.setFillColor(colors.HexColor("#F0F3F1"))
        c.roundRect(M + 30 * mm, y - 1, bar_max, 3.2 * mm, 1 * mm, fill=1, stroke=0)
        c.setFillColor(colors.HexColor(cat.color))
        c.roundRect(M + 30 * mm, y - 1, max(1.5 * mm, bar_max * cat.share), 3.2 * mm, 1 * mm, fill=1, stroke=0)
        c.setFillColor(muted)
        c.drawString(M + 32 * mm + bar_max, y, f"{round(cat.share * 100)}%")
        c.setFillColor(ink)
        c.drawRightString(W - M, y, _rs(cat.total))
        y -= 6.5 * mm

    cols = [(M, "Date", False), (M + 24 * mm, "Item", False), (M + 80 * mm, "Category", False), (M + 115 * mm, "Qty", False), (W - M, "Amount", True)]

    def table_header(yy: float) -> float:
        c.setFillColor(emerald)
        c.rect(M - 2 * mm, yy - 2 * mm, W - 2 * M + 4 * mm, 7 * mm, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9.5)
        for x, h, right in cols:
            (c.drawRightString if right else c.drawString)(x, yy, h)
        return yy - 7 * mm

    y = table_header(y - 6 * mm)
    for i, e in enumerate(report.expenses):
        if y < 22 * mm:
            footer()
            c.showPage()
            y = table_header(H - 20 * mm)
        if i % 2 == 0:
            c.setFillColor(colors.HexColor("#FAFAF7"))
            c.rect(M - 2 * mm, y - 2 * mm, W - 2 * M + 4 * mm, 6.2 * mm, fill=1, stroke=0)
        c.setFillColor(ink)
        c.setFont("Helvetica", 9.5)
        vals = [e.date.isoformat(), e.item_name[:32], cat_names.get(e.category_id, "Other"), _qty(e) or "-", _rs(e.amount)]
        for (x, _, right), v in zip(cols, vals):
            (c.drawRightString if right else c.drawString)(x, y, v)
        y -= 6.2 * mm
    c.setStrokeColor(emerald)
    c.line(M, y + 2 * mm, W - M, y + 2 * mm)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(M, y - 4 * mm, "Total")
    c.drawRightString(W - M, y - 4 * mm, _rs(report.total_expense))
    footer()
    c.save()
    return buf.getvalue()
