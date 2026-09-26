"""Charge-invoice PDF generation (ReportLab).

generate_invoice_pdf(order, filepath) -> filepath
`order` is the dict returned by OrderManager.get_order() (with
items / payments / amount_paid / balance keys).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path


def _money(value) -> str:
    return f"P{Decimal(str(value or 0)):.2f}"


def generate_invoice_pdf(order: dict, filepath: str | Path) -> str:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle)

    path = str(filepath)
    doc = SimpleDocTemplate(path, pagesize=LETTER,
                            leftMargin=40, rightMargin=40,
                            topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("AkoNi Printing Services", styles["Title"]),
        Paragraph("Charge Invoice", styles["Heading2"]),
        Spacer(1, 6),
        Paragraph(
            f"Order #{order.get('order_id')} &nbsp;|&nbsp; "
            f"Date: {order.get('order_date')} &nbsp;|&nbsp; "
            f"Type: {order.get('order_type')} &nbsp;|&nbsp; "
            f"Status: {order.get('status')}",
            styles["Normal"]),
        Paragraph(
            f"Customer ID: {order.get('customer_id')} &nbsp;|&nbsp; "
            f"Delivery: {order.get('delivery_address') or '—'} &nbsp;|&nbsp; "
            f"Expected: {order.get('expected_delivery_date') or '—'}",
            styles["Normal"]),
        Spacer(1, 12),
    ]

    rows = [["#", "Packaging", "Size", "Qty", "Unit Price", "Discount", "Line Total"]]
    subtotal = Decimal("0.00")
    for i, it in enumerate(order.get("items", []), 1):
        qty = Decimal(str(it.get("quantity", 1)))
        price = Decimal(str(it.get("unit_price", 0)))
        disc = Decimal(str(it.get("discount", 0)))
        line = qty * price - disc
        subtotal += line
        rows.append([str(i), str(it.get("packaging_type") or ""),
                     str(it.get("size") or ""), str(it.get("quantity")),
                     _money(price), _money(disc), _money(line)])
    table = Table(rows, repeatRows=1, colWidths=[25, 110, 80, 40, 70, 70, 80])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story += [table, Spacer(1, 12)]

    totals = [
        ["Subtotal (items):", _money(subtotal)],
        ["Rush charge:", _money(order.get("rush_charge", 0))],
        ["Design assurance deduction:",
         _money("-500.00") if order.get("is_design_fee_deducted") else _money(0)],
        ["TOTAL AMOUNT:", _money(order.get("total_amount", 0))],
        ["Amount paid:", _money(order.get("amount_paid", 0))],
        ["BALANCE:", _money(order.get("balance", 0))],
    ]
    t2 = Table(totals, colWidths=[300, 180])
    t2.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("LINEABOVE", (0, 3), (-1, 3), 1, colors.black),
        ("LINEABOVE", (0, 5), (-1, 5), 1, colors.black),
    ]))
    story += [t2, Spacer(1, 18),
              Paragraph(f"Generated {datetime.now():%Y-%m-%d %H:%M} — "
                        "Thank you for printing with AkoNi!",
                        styles["Normal"])]
    doc.build(story)
    return path
