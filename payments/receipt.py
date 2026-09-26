"""Service Receipt PDF generation (ReportLab).

generate_receipt_pdf(payment, order, filepath) -> filepath
`payment` is a payments row dict; `order` is the linked
OrderManager.get_order() dict or None for Layout-Only payments.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path


def _money(value) -> str:
    return f"P{Decimal(str(value or 0)):.2f}"


def generate_receipt_pdf(payment: dict, order: dict | None,
                         filepath: str | Path) -> str:
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
        Paragraph("Service Receipt", styles["Heading2"]),
        Spacer(1, 6),
        Paragraph(
            f"Receipt #{payment.get('payment_id')} &nbsp;|&nbsp; "
            f"Date: {payment.get('payment_date')} &nbsp;|&nbsp; "
            f"Status: {payment.get('status')}",
            styles["Normal"]),
        Paragraph(
            f"Type: {payment.get('payment_type')} &nbsp;|&nbsp; "
            f"Method: {payment.get('payment_method')} &nbsp;|&nbsp; "
            f"Order: {payment.get('order_id') or 'Layout-Only / walk-in'}",
            styles["Normal"]),
        Spacer(1, 12),
    ]

    if order:
        rows = [["Order #", "Type", "Status", "Total", "Paid", "Balance"],
                [str(order.get("order_id")), str(order.get("order_type")),
                 str(order.get("status")), _money(order.get("total_amount")),
                 _money(order.get("amount_paid")), _money(order.get("balance"))]]
        t = Table(rows, repeatRows=1, colWidths=[60, 90, 90, 80, 80, 80])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        story += [t, Spacer(1, 12)]

    totals = [["AMOUNT PAID:", _money(payment.get("amount_paid"))]]
    if order:
        totals += [["Order balance after payment:", _money(order.get("balance"))]]
    t2 = Table(totals, colWidths=[300, 180])
    t2.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("LINEABOVE", (0, 0), (-1, 0), 1, colors.black),
    ]))
    story += [t2, Spacer(1, 18),
              Paragraph(f"Issued {datetime.now():%Y-%m-%d %H:%M} — "
                        "Thank you for your payment!",
                        styles["Normal"])]
    doc.build(story)
    return path
