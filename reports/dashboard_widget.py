"""Reporting Dashboard widget (first screen after login).

Admin KPIs: Total Sales this Month, Total Expenses this Month,
Pending Orders, Low Stock Items + bar chart (Monthly Sales vs
Expenses, last 6 months) + pie chart (Expense breakdown by Category).
Staff sees the Low Stock card only (RBAC).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtCharts import (
    QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis,
    QPieSeries,
)
from PyQt6.QtGui import QPainter, QColor

from database.database import get_connection
from reports.reports import ReportManager
from ui.kpi_card import (
    KpiCard, TONE_NEGATIVE, TONE_NEUTRAL, TONE_POSITIVE,
)

# Rich Gold theme (Phase 1) palette.
GOLD = QColor("#D4AF37")
CHART_SERIES_COLORS = {"Sales": QColor("#D4AF37"),
                       "Expenses": QColor("#8C7A2B")}
PIE_SLICE_COLORS = [
    "#D4AF37", "#1A1A1A", "#B5952F", "#8C7A2B", "#E6D9A3", "#6B6B6B",
]


def _month_bounds(year: int, month: int) -> tuple[str, str]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start.isoformat(), end.isoformat()


def _last_6_months() -> list[tuple[int, int, str]]:
    out = []
    y, m = date.today().year, date.today().month
    for _ in range(6):
        out.append((y, m, date(y, m, 1).strftime("%b %Y")))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return list(reversed(out))


class DashboardWidget(QWidget):
    def __init__(self, user: dict | None = None, parent=None):
        super().__init__(parent)
        self.user = user or {}
        self._is_admin = (self.user.get("role") or "Staff") == "Admin"
        layout = QVBoxLayout(self)

        title = QLabel("Dashboard")
        title.setObjectName("DashboardTitle")
        layout.addWidget(title)
        sub = QLabel("AkoNi Printing Services — business overview")
        sub.setObjectName("DashboardSub")
        layout.addWidget(sub)

        grid = QGridLayout()
        grid.setSpacing(12)
        self._cards: dict[str, KpiCard] = {}
        # key, title, icon — values/subtitles are filled by refresh()
        defs = ([("sales", "Total Sales", "\U0001F4B0"),
                 ("expenses", "Total Expenses", "\U0001F4B8"),
                 ("pending", "Pending Orders", "\U0001F4CB"),
                 ("low", "Low Stock Items", "\U0001F4E6")]
                if self._is_admin else [("low", "Low Stock Items", "\U0001F4E6")])
        for i, (key, title, icon) in enumerate(defs):
            card = KpiCard(title, icon=icon, value="—", subtitle="—")
            grid.addWidget(card, 0, i)
            self._cards[key] = card
        layout.addLayout(grid)

        if self._is_admin:
            charts = QHBoxLayout()
            self.bar_view = QChartView()
            self.bar_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.bar_view.setMinimumHeight(300)
            self.pie_view = QChartView()
            self.pie_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.pie_view.setMinimumHeight(300)
            charts.addWidget(self.bar_view, 3)
            charts.addWidget(self.pie_view, 2)
            layout.addLayout(charts)

        btns = QHBoxLayout()
        refresh_btn = QPushButton("Refresh overview")
        refresh_btn.clicked.connect(self.refresh)
        btns.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        btns.addStretch(1)
        layout.addLayout(btns)
        layout.addStretch(1)
        self.refresh()

    # -- data --
    def _kpis(self) -> dict:
        conn = self._conn()
        try:
            mgr = ReportManager(conn)
            first = date.today().replace(day=1).isoformat()
            prev_y, prev_m = (date.today().year - 1, 12) \
                if date.today().month == 1 else \
                (date.today().year, date.today().month - 1)
            prev_first, prev_end = _month_bounds(prev_y, prev_m)
            sales = Decimal(str(mgr.sales_summary(start=first)["totals"].get("revenue", 0)))
            sales_prev = Decimal(str(mgr.sales_summary(start=prev_first, end=prev_end)["totals"].get("revenue", 0)))
            expenses = Decimal(str(mgr.expenses_summary(start=first)["totals"].get("total", 0)))
            expenses_prev = Decimal(str(mgr.expenses_summary(start=prev_first, end=prev_end)["totals"].get("total", 0)))
            cur = conn.cursor()
            try:
                cur.execute("SELECT COUNT(*) FROM customer_orders WHERE status = 'Pending'")
                (pending,) = cur.fetchone()
            finally:
                cur.close()
            low = [m for m in mgr.inventory_status()
                   if int(m["current_stock_qty"]) <= int(m["low_stock_threshold"])]
            return {"sales": sales, "sales_prev": sales_prev,
                    "expenses": expenses, "expenses_prev": expenses_prev,
                    "pending": int(pending), "low": low,
                    "by_category": mgr.expenses_summary(start=first)["by_category"]}
        finally:
            conn.close()

    def _monthly(self) -> tuple[list[str], list[float], list[float]]:
        conn = self._conn()
        try:
            mgr = ReportManager(conn)
            labels, sales, expenses = [], [], []
            for y, m, lab in _last_6_months():
                start, end = _month_bounds(y, m)
                s = mgr.sales_summary(start=start, end=end)["totals"]
                e = mgr.expenses_summary(start=start, end=end)["totals"]
                labels.append(lab)
                sales.append(float(s.get("revenue") or 0))
                expenses.append(float(e.get("total") or 0))
            return labels, sales, expenses
        finally:
            conn.close()

    def _conn(self):
        return get_connection()

    # -- render --
    @staticmethod
    def _month_delta(current: float, previous: float) -> dict:
        """Month-over-month comparison -> {'text', 'tone'} for a KPI card.

        An increase renders green and a decrease red (the right semantics
        for both sales and expenses KPIs).
        """
        if previous <= 0:
            return {"text": "No data last month", "tone": TONE_NEUTRAL}
        pct = ((current - previous) / previous) * 100.0
        if pct >= 0:
            return {"text": f"+{pct:.0f}% vs last month", "tone": TONE_POSITIVE}
        return {"text": f"{pct:.0f}% vs last month", "tone": TONE_NEGATIVE}

    def _set_low_card(self, low_count: int) -> None:
        """Low Stock KPI + dynamic red alert when items need restocking."""
        self._cards["low"].set_value(str(low_count))
        if low_count > 0:
            self._cards["low"].set_subtitle("Restock needed", TONE_NEGATIVE)
            self._cards["low"].set_alert(True)
        else:
            self._cards["low"].set_subtitle("Inventory healthy", TONE_NEUTRAL)
            self._cards["low"].set_alert(False)

    def refresh(self) -> None:
        try:
            kpis = self._kpis()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
            return
        if self._is_admin:
            sales_d = self._month_delta(float(kpis["sales"]), float(kpis["sales_prev"]))
            exp_d = self._month_delta(float(kpis["expenses"]), float(kpis["expenses_prev"]))
            self._cards["sales"].set_value(f"P{kpis['sales']:,.2f}")
            self._cards["sales"].set_subtitle(sales_d["text"], sales_d["tone"])
            self._cards["expenses"].set_value(f"P{kpis['expenses']:,.2f}")
            self._cards["expenses"].set_subtitle(exp_d["text"], exp_d["tone"])
            self._cards["pending"].set_value(str(kpis["pending"]))
            self._cards["pending"].set_subtitle(
                "All caught up!" if kpis["pending"] == 0 else "Awaiting processing",
                TONE_NEUTRAL)
            self._set_low_card(len(kpis["low"]))
            try:
                labels, sales, expenses = self._monthly()
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Error", str(exc))
                return
            self._render_bar(labels, sales, expenses)
            self._render_pie(kpis["by_category"])
        else:
            self._set_low_card(len(kpis["low"]))

    def _render_bar(self, labels: list[str], sales: list[float],
                    expenses: list[float]) -> None:
        sales_set = QBarSet("Sales")
        exp_set = QBarSet("Expenses")
        sales_set.setColor(CHART_SERIES_COLORS["Sales"])
        exp_set.setColor(CHART_SERIES_COLORS["Expenses"])
        for v in sales:
            sales_set.append(v)
        for v in expenses:
            exp_set.append(v)
        series = QBarSeries()
        series.append(sales_set)
        series.append(exp_set)
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Monthly Sales vs Expenses (last 6 months)")
        axis_x = QBarCategoryAxis()
        axis_x.append(labels)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)
        axis_y = QValueAxis()
        axis_y.setLabelFormat("P%.0f")
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)
        chart.legend().setVisible(True)
        self.bar_view.setChart(chart)

    def _render_pie(self, by_category: list[dict]) -> None:
        series = QPieSeries()
        rows = [(r.get("category"), float(r.get("total") or 0)) for r in by_category]
        rows = [(c, t) for c, t in rows if t > 0]
        if not rows:
            series.append("No expenses this month", 1)
        else:
            for idx, (cat, total) in enumerate(rows):
                sl = series.append(f"{cat} (P{total:.0f})", total)
                sl.setLabelVisible(True)
                sl.setBrush(QColor(PIE_SLICE_COLORS[idx % len(PIE_SLICE_COLORS)]))
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Expense breakdown by Category (this month)")
        chart.legend().setVisible(True)
        self.pie_view.setChart(chart)
