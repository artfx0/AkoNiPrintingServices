"""Reports widget (Admin access only): PDF/CSV exports.

Buttons: Monthly Sales Report (PDF/CSV), Inventory Report (PDF/CSV),
Expense Report (PDF/CSV). CSV via stdlib csv, PDF via ReportLab.
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QPushButton, QLabel, QMessageBox,
    QFileDialog,
)

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
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle)

    doc = SimpleDocTemplate(path, pagesize=LETTER,
                            leftMargin=40, rightMargin=40,
                            topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    story = [Paragraph("AkoNi Printing Services", styles["Title"]),
             Paragraph(title, styles["Heading2"]),
             Paragraph(subtitle, styles["Normal"]), Spacer(1, 12)]
    for heading, headers, rows in sections:
        story.append(Paragraph(heading, styles["Heading3"]))
        data = [headers] + [[str(c) for c in r] for r in rows]
        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        story += [t, Spacer(1, 12)]
    doc.build(story)
    return path


class ReportsWidget(QWidget):
    """Standalone Admin-only page for QStackedWidget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        title = QLabel("Reports")
        title.setObjectName("DashboardTitle")
        layout.addWidget(title)
        self.info = QLabel("Generate monthly sales, inventory and expense reports.")
        self.info.setObjectName("DashboardSub")
        layout.addWidget(self.info)

        grid = QGridLayout()
        specs = [
            ("Monthly Sales Report — PDF", self.sales_pdf),
            ("Monthly Sales Report — CSV", self.sales_csv),
            ("Inventory Report — PDF", self.inventory_pdf),
            ("Inventory Report — CSV", self.inventory_csv),
            ("Expense Report — PDF", self.expense_pdf),
            ("Expense Report — CSV", self.expense_csv),
        ]
        for i, (label, fn) in enumerate(specs):
            btn = QPushButton(label)
            btn.clicked.connect(fn)
            grid.addWidget(btn, i // 2, i % 2)
        layout.addLayout(grid)
        layout.addStretch(1)

    # -- helpers --
    def _conn(self):
        return get_connection()

    def _ask(self, default: str, filt: str) -> str | None:
        path, _ = QFileDialog.getSaveFileName(self, "Save report", default, filt)
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
                str(Path(path).with_name("monthly_sales_by_status.csv")))
            QMessageBox.information(self, "Reports",
                                    f"Monthly Sales Report ({label}) saved to {path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))

    def sales_pdf(self) -> None:
        path = self._ask("monthly_sales.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            label, totals, by_status, daily = self._sales_data()
            _write_pdf(path, "Monthly Sales Report", f"{label} — AkoNi Printing",
                       [("Totals", ["orders", "revenue", "rush"],
                         [[totals.get("orders"), totals.get("revenue"),
                           totals.get("rush")]]),
                        ("By status", ["status", "count", "revenue"],
                         [[r.get("status"), r.get("n"), r.get("revenue")]
                          for r in by_status]),
                        ("Daily", ["day", "orders", "revenue"],
                         [[r.get("day"), r.get("orders"), r.get("revenue")]
                          for r in daily])])
            QMessageBox.information(self, "Reports", f"Saved to {path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))

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
            _write_csv(path, ["material_id", "material_name", "unit_of_measure",
                              "current_stock_qty", "low_stock_threshold",
                              "cost_per_unit", "is_low"], rows)
            QMessageBox.information(self, "Reports", f"Saved to {path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))

    def inventory_pdf(self) -> None:
        path = self._ask("inventory_report.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            rows = self._inventory_data()
            _write_pdf(path, "Inventory Report", "Current stock levels — AkoNi Printing",
                       [("Materials",
                         ["name", "unit", "qty", "low-at", "cost", "low?"],
                         [[r.get("material_name"), r.get("unit_of_measure"),
                           r.get("current_stock_qty"), r.get("low_stock_threshold"),
                           r.get("cost_per_unit"),
                           "LOW" if r.get("is_low") else ""]
                          for r in rows])])
            QMessageBox.information(self, "Reports", f"Saved to {path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))

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
            QMessageBox.information(self, "Reports",
                                    f"Expense Report ({label}) saved to {path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))

    def expense_pdf(self) -> None:
        path = self._ask("expense_report.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            label, totals, by_category = self._expense_data()
            _write_pdf(path, "Expense Report", f"{label} — AkoNi Printing",
                       [("Totals", ["count", "total"],
                         [[totals.get("n"), totals.get("total")]]),
                        ("By category", ["category", "count", "total"],
                         [[r.get("category"), r.get("n"), r.get("total")]
                          for r in by_category])])
            QMessageBox.information(self, "Reports", f"Saved to {path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
