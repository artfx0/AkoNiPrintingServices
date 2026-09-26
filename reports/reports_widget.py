"""Reports & Analytics Center widget (Professional SaaS / HCI format).

Features:
  - Visual hierarchy: Section title + descriptive subtitle.
  - Interactive Report Cards for Monthly Sales, Inventory Valuation, and Operating Expenses.
  - Instant PDF Generation (ReportLab formatted) and CSV Data Exports.
  - Accounts Receivable / Unpaid Customer Orders quick export card.
  - Current reporting period and live metrics display.
"""
from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
    QMessageBox, QFileDialog, QFrame, QScrollArea,
)
from PyQt6.QtCore import Qt

from database.database import get_connection
from reports.reports import ReportManager


def _month_range() -> tuple[str, str, str]:
    today = date.today()
    first = today.replace(day=1)
    if today.month == 12:
        nxt = date(today.year + 1, 1, 1)
    else:
        nxt = date(today.year, today.month + 1, 1)
    return first.isoformat(), nxt.isoformat(), today.strftime("%B %Y")


def _write_csv(path: str, headers: list[str], rows: list[dict]) -> str:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_pdf(path: str, title: str, subtitle: str,
               sections: list[tuple[str, list[str], list[list]]]) -> str:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    )

    doc = SimpleDocTemplate(
        path, pagesize=LETTER,
        leftMargin=40, rightMargin=40,
        topMargin=40, bottomMargin=40
    )
    styles = getSampleStyleSheet()

    # Brand Title Header
    brand_style = ParagraphStyle(
        "BrandHeader",
        parent=styles["Title"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0F172A"),
    )
    story = [
        Paragraph("AkoNi Printing Services", brand_style),
        Paragraph(title, styles["Heading2"]),
        Paragraph(subtitle, styles["Normal"]),
        Spacer(1, 14),
    ]

    for heading, headers, rows in sections:
        story.append(Paragraph(heading, styles["Heading3"]))
        data = [headers] + [[str(c) if c is not None else "" for c in r] for r in rows]
        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]))
        story += [t, Spacer(1, 14)]

    doc.build(story)
    return path


class ReportsWidget(QWidget):
    """Reports & Analytics Center with modern HCI cards and export workflows."""

    def __init__(self, parent=None):
        super().__init__(parent)

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # Scroll Area for responsive sizing
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("DashboardScrollArea")
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container.setObjectName("DashboardContent")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(22)

        # 1. Page Header (Title + Subtitle)
        header_lay = QVBoxLayout()
        header_lay.setSpacing(4)
        title = QLabel("Reports & Analytics Center")
        title.setObjectName("ModuleHeaderTitle")
        sub = QLabel("Generate executive-ready PDF documents and raw CSV data exports across business operations.")
        sub.setObjectName("ModuleHeaderSub")
        header_lay.addWidget(title)
        header_lay.addWidget(sub)
        layout.addLayout(header_lay)

        # Active reporting period indicator
        _, _, period_label = _month_range()
        period_badge = QLabel(f"🗓️  Current Reporting Period:  <b>{period_label}</b>")
        period_badge.setStyleSheet(
            "background: #FEF3C7; color: #92400E; font-size: 13px; "
            "padding: 8px 14px; border-radius: 8px; border: 1px solid #FDE68A;"
        )
        layout.addWidget(period_badge)

        # 2. Grid of 3 Major Report Cards
        grid = QGridLayout()
        grid.setSpacing(18)

        # Card 1: Monthly Sales
        sales_card = self._build_report_card(
            icon="📊",
            title="Monthly Sales & Revenue Report",
            tag="Sales Analytics",
            desc="Consolidates total sales orders, collected revenue, rush charge fees, and daily turnover breakdown.",
            pdf_slot=self.sales_pdf,
            csv_slot=self.sales_csv,
        )
        grid.addWidget(sales_card, 0, 0)

        # Card 2: Inventory Valuation
        inv_card = self._build_report_card(
            icon="📦",
            title="Inventory Valuation & Stock Report",
            tag="Warehouse Audit",
            desc="Physical stock-on-hand audit, item reorder thresholds, low-stock warnings, and unit valuation.",
            pdf_slot=self.inventory_pdf,
            csv_slot=self.inventory_csv,
        )
        grid.addWidget(inv_card, 0, 1)

        # Card 3: Operating Expenses
        exp_card = self._build_report_card(
            icon="💸",
            title="Operating Expenses & Disbursements",
            tag="Financial Outflow",
            desc="Itemized log of operational expenditures categorized by raw materials, labor, utilities, and overhead.",
            pdf_slot=self.expense_pdf,
            csv_slot=self.expense_csv,
        )
        grid.addWidget(exp_card, 1, 0)

        # Card 4: Accounts Receivable / Unpaid Orders
        unpaid_card = self._build_report_card(
            icon="💳",
            title="Accounts Receivable & Unpaid Orders",
            tag="Cashflow Control",
            desc="Export pending customer balances, partial payments, and overdue order receivables for follow-up.",
            pdf_slot=None,  # CSV only
            csv_slot=self.unpaid_csv,
        )
        grid.addWidget(unpaid_card, 1, 1)

        layout.addLayout(grid)
        layout.addStretch(1)

        scroll.setWidget(container)
        main_lay.addWidget(scroll)

    def _build_report_card(
        self, icon: str, title: str, tag: str, desc: str,
        pdf_slot, csv_slot
    ) -> QFrame:
        """Constructs an elevated card container for a report export module."""
        card = QFrame()
        card.setObjectName("ModuleCardContainer")
        card.setStyleSheet(
            "QFrame#ModuleCardContainer { background: #FFFFFF; border: 1px solid #E2E8F0; "
            "border-radius: 12px; padding: 20px; }"
        )

        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        # Header row: Icon + Title & Tag
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(
            "font-size: 22px; background: #F8FAFC; border-radius: 10px; "
            "border: 1px solid #E2E8F0; padding: 8px 10px;"
        )
        top_row.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #0F172A;")
        tag_lbl = QLabel(tag.upper())
        tag_lbl.setStyleSheet("font-size: 10px; font-weight: bold; color: #94A3B8; letter-spacing: 0.5px;")
        title_box.addWidget(tag_lbl)
        title_box.addWidget(t_lbl)
        top_row.addLayout(title_box, 1)

        lay.addLayout(top_row)

        # Description
        desc_lbl = QLabel(desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("font-size: 12px; color: #64748B; line-height: 16px;")
        lay.addWidget(desc_lbl)

        lay.addStretch(1)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("background-color: #F1F5F9; border: none; height: 1px;")
        lay.addWidget(div)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_box.addStretch(1)

        if csv_slot:
            csv_btn = QPushButton("📊 Export CSV")
            csv_btn.setObjectName("SecondaryBtn")
            csv_btn.clicked.connect(csv_slot)
            btn_box.addWidget(csv_btn)

        if pdf_slot:
            pdf_btn = QPushButton("📄 Download PDF")
            pdf_btn.clicked.connect(pdf_slot)
            btn_box.addWidget(pdf_btn)

        lay.addLayout(btn_box)
        return card

    # -- helpers --
    def _conn(self):
        return get_connection()

    def _ask(self, default: str, filt: str) -> str | None:
        path, _ = QFileDialog.getSaveFileName(self, "Save Report", default, filt)
        return path or None

    # -- Monthly Sales --
    def _sales_data(self) -> tuple[str, dict, list[dict], list[dict]]:
        conn = self._conn()
        try:
            mgr = ReportManager(conn)
            start, end, label = _month_range()
            summary = mgr.sales_summary(start=start, end=end)
            return label, summary["totals"], summary["by_status"], summary["daily"]
        finally:
            conn.close()

    def sales_csv(self) -> None:
        path = self._ask("monthly_sales.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            label, totals, by_status, daily = self._sales_data()
            _write_csv(path, ["day", "orders", "revenue"], daily)
            ReportManager.export_to_csv(
                by_status, ["status", "n", "revenue"],
                str(Path(path).with_name("monthly_sales_by_status.csv"))
            )
            QMessageBox.information(self, "Export Successful", f"Monthly Sales Report ({label}) saved to:\n{path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Export Error", str(exc))

    def sales_pdf(self) -> None:
        path = self._ask("monthly_sales.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            label, totals, by_status, daily = self._sales_data()
            _write_pdf(
                path, "Monthly Sales Report", f"Reporting Period: {label} — AkoNi Printing Services",
                [
                    ("Period Overview", ["Metric", "Value"],
                     [["Total Orders Booked", str(totals.get("orders") or 0)],
                      ["Total Revenue Collected", f"P{Decimal(str(totals.get('revenue') or 0)):,.2f}"],
                      ["Rush Order Charges", f"P{Decimal(str(totals.get('rush') or 0)):,.2f}"]]),
                    ("Orders by Status", ["Status", "Order Count", "Total Value (P)"],
                     [[r.get("status"), r.get("n"), f"P{Decimal(str(r.get('revenue') or 0)):,.2f}"]
                      for r in by_status]),
                    ("Daily Sales Volume", ["Date", "Orders", "Revenue (P)"],
                     [[r.get("day"), r.get("orders"), f"P{Decimal(str(r.get('revenue') or 0)):,.2f}"]
                      for r in daily]),
                ]
            )
            QMessageBox.information(self, "Export Successful", f"Monthly Sales PDF saved to:\n{path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Export Error", str(exc))

    # -- Inventory --
    def _inventory_data(self) -> list[dict]:
        conn = self._conn()
        try:
            return ReportManager(conn).inventory_status()
        finally:
            conn.close()

    def inventory_csv(self) -> None:
        path = self._ask("inventory_report.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            rows = self._inventory_data()
            _write_csv(
                path,
                ["material_id", "material_name", "unit_of_measure",
                 "current_stock_qty", "low_stock_threshold", "cost_per_unit", "is_low"],
                rows
            )
            QMessageBox.information(self, "Export Successful", f"Inventory Audit Report saved to:\n{path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Export Error", str(exc))

    def inventory_pdf(self) -> None:
        path = self._ask("inventory_report.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            rows = self._inventory_data()
            _write_pdf(
                path, "Inventory Valuation & Stock Report", "Current Stock Audit — AkoNi Printing Services",
                [
                    ("Raw Materials Inventory",
                     ["Material Name", "Unit", "On Hand", "Min Reorder", "Cost/Unit (P)", "Status"],
                     [[r.get("material_name"), r.get("unit_of_measure"),
                       r.get("current_stock_qty"), r.get("low_stock_threshold"),
                       f"P{Decimal(str(r.get('cost_per_unit') or 0)):,.2f}",
                       "LOW STOCK" if r.get("is_low") else "NORMAL"]
                      for r in rows])
                ]
            )
            QMessageBox.information(self, "Export Successful", f"Inventory Report PDF saved to:\n{path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Export Error", str(exc))

    # -- Expense --
    def _expense_data(self) -> tuple[str, dict, list[dict]]:
        conn = self._conn()
        try:
            mgr = ReportManager(conn)
            start, end, label = _month_range()
            summary = mgr.expenses_summary(start=start, end=end)
            return label, summary["totals"], summary["by_category"]
        finally:
            conn.close()

    def expense_csv(self) -> None:
        path = self._ask("expense_report.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            label, totals, by_category = self._expense_data()
            _write_csv(path, ["category", "n", "total"], by_category)
            QMessageBox.information(self, "Export Successful", f"Expense Report ({label}) saved to:\n{path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Export Error", str(exc))

    def expense_pdf(self) -> None:
        path = self._ask("expense_report.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            label, totals, by_category = self._expense_data()
            _write_pdf(
                path, "Operating Expense Report", f"Reporting Period: {label} — AkoNi Printing Services",
                [
                    ("Total Disbursements", ["Disbursement Count", "Total Amount (P)"],
                     [[str(totals.get("n") or 0), f"P{Decimal(str(totals.get('total') or 0)):,.2f}"]]),
                    ("Disbursements by Category", ["Category", "Count", "Total Amount (P)"],
                     [[r.get("category"), r.get("n"), f"P{Decimal(str(r.get('total') or 0)):,.2f}"]
                      for r in by_category]),
                ]
            )
            QMessageBox.information(self, "Export Successful", f"Expense Report PDF saved to:\n{path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Export Error", str(exc))

    # -- Unpaid Orders --
    def unpaid_csv(self) -> None:
        path = self._ask("unpaid_orders_receivable.csv", "CSV (*.csv)")
        if not path:
            return
        conn = self._conn()
        try:
            rows = ReportManager(conn).unpaid_orders()
            ReportManager.export_to_csv(
                rows,
                ["order_id", "customer", "total_amount", "paid", "balance", "status"],
                path
            )
            QMessageBox.information(self, "Export Successful", f"Unpaid Orders Export saved to:\n{path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Export Error", str(exc))
        finally:
            conn.close()
