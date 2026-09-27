"""Reports & Analytics Module (Modern SaaS / Interactive Analytics Dashboard).

Features:
  - Top Header: Title, descriptive subtitle, and repositioned export buttons (Export CSV, Download PDF, Refresh).
  - Top Row: 4 Live KPI Cards (Total Sales, Total Expenses, Net Income, Pending Orders).
  - Second Row: Global Date Range Filter (This Month, Last Month, This Quarter, This Year, All Time, Custom Range)
    plus real-time text search bar and active chart filter indicators.
  - Third Row: 4 Interactive QtCharts:
      1. Monthly Sales & Revenue Trend (Bar Chart, Rich Gold #D4AF37, hover exact amount, click to filter table).
      2. Operating Expenses Breakdown (Donut Chart, distinct category colors, hover explode & %, click to filter table).
      3. Inventory Valuation & Stock Levels (Horizontal Bar Chart, Top 5 materials by Quantity x Unit Cost).
      4. Accounts Receivable (Stacked Bar Chart, Paid vs Unpaid orders per month).
  - Fourth Row: Detailed Data Table showing raw transaction data powering the analytics,
    supporting interactive chart filtering, text search, custom pill badges, and no column overlap.
"""
from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
    QMessageBox, QFileDialog, QFrame, QScrollArea, QComboBox, QDateEdit,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QSizePolicy, QToolTip,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QPainter, QColor, QCursor, QFont
from PyQt6.QtCharts import (
    QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis,
    QPieSeries, QPieSlice, QHorizontalBarSeries, QStackedBarSeries,
)

from database.database import get_connection
from reports.reports import ReportManager
from ui.icons import get_icon, get_action_icon, get_pixmap
from ui.kpi_card import KpiCard, TONE_NEGATIVE, TONE_NEUTRAL, TONE_POSITIVE

# Distinct Category Color Palette (Matching Expense Management)
CATEGORY_COLORS: dict[str, str] = {
    "Labor": "#3B82F6",         # Blue
    "Materials": "#2E7D32",     # Green
    "Miscellaneous": "#8B5CF6", # Purple
    "Utility": "#F57C00",       # Orange
    "Other": "#64748B",         # Slate Grey
}


def _date_presets() -> list[str]:
    return [
        "This Month",
        "Last Month",
        "This Quarter",
        "This Year",
        "All Time",
        "Custom Range",
    ]


def _calc_preset_dates(preset: str) -> tuple[date, date]:
    today = date.today()
    if preset == "This Month":
        start = date(today.year, today.month, 1)
        end = today
    elif preset == "Last Month":
        if today.month == 1:
            lm_y, lm_m = today.year - 1, 12
        else:
            lm_y, lm_m = today.year, today.month - 1
        start = date(lm_y, lm_m, 1)
        end = date(today.year, today.month, 1) - timedelta(days=1)
    elif preset == "This Quarter":
        q = (today.month - 1) // 3 + 1
        q_start = (q - 1) * 3 + 1
        start = date(today.year, q_start, 1)
        end = today
    elif preset == "This Year":
        start = date(today.year, 1, 1)
        end = today
    elif preset == "All Time":
        start = date(2020, 1, 1)
        end = today
    else:  # Custom Range fallback
        start = date(today.year, today.month, 1)
        end = today
    return start, end


class ReportsWidget(QWidget):
    """Interactive Reports & Analytics Dashboard."""

    def __init__(self, user: dict | None = None, parent=None):
        super().__init__(parent)
        self.user = user or {}

        # Internal State
        self._raw_transactions: list[dict] = []
        self._filtered_transactions: list[dict] = []
        self._sales_trend_data: list[dict] = []
        self._expenses_breakdown_data: list[dict] = []
        self._active_kpis: dict = {}

        # Interactive Chart Filter State
        # type can be: None, 'sales_month', 'expense_category'
        self._active_filter_type: str | None = None
        self._active_filter_val: str | None = None
        self._active_filter_label: str | None = None

        self._build_ui()
        self._apply_preset("This Month", trigger_refresh=False)
        self.refresh()

    def _conn(self):
        return get_connection()

    # -- UI Construction ------------------------------------------------
    def _build_ui(self) -> None:
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # Smooth Scroll Area wrapping
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("DashboardScrollArea")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setObjectName("DashboardContent")
        self.content_lay = QVBoxLayout(container)
        self.content_lay.setContentsMargins(28, 24, 28, 28)
        self.content_lay.setSpacing(18)

        # 1. Header (Title, Subtitle, and Repositioned Export Buttons)
        self._build_header()

        # 2. Top Row: Summary KPI Strip
        self._build_kpi_strip()

        # 3. Second Row: Global Date Range Filter & Search Bar
        self._build_filter_toolbar()

        # 4. Third Row: Interactive Charts (2x2 Grid)
        self._build_charts_grid()

        # 5. Fourth Row: Detailed Data Table
        self._build_data_table()

        scroll.setWidget(container)
        main_lay.addWidget(scroll)

    def _build_header(self) -> None:
        header_bar = QHBoxLayout()
        header_bar.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Left: Title + Subtitle
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("Reports & Analytics")
        title.setObjectName("ModuleHeaderTitle")
        sub = QLabel("Interactive business analytics, financial trends, and operational data breakdown.")
        sub.setObjectName("ModuleHeaderSub")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header_bar.addLayout(title_box, 1)

        # Right: Repositioned Export Buttons + Refresh Button
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        self.btn_export_csv = QPushButton(" Export CSV")
        self.btn_export_csv.setObjectName("SecondaryBtn")
        self.btn_export_csv.setIcon(get_action_icon("file-spreadsheet", "secondary", 15))
        self.btn_export_csv.setToolTip("Export the currently displayed raw data table to CSV")
        self.btn_export_csv.clicked.connect(self.export_csv)
        btn_box.addWidget(self.btn_export_csv)

        self.btn_download_pdf = QPushButton(" Download PDF")
        self.btn_download_pdf.setIcon(get_action_icon("download", "primary", 15))
        self.btn_download_pdf.setToolTip("Generate an executive-ready PDF report of the active analytics view")
        self.btn_download_pdf.clicked.connect(self.download_pdf)
        btn_box.addWidget(self.btn_download_pdf)

        self.btn_refresh = QPushButton(" Refresh")
        self.btn_refresh.setObjectName("SecondaryBtn")
        self.btn_refresh.setIcon(get_action_icon("refresh", "secondary", 15))
        self.btn_refresh.setToolTip("Reload live metrics and data from MySQL")
        self.btn_refresh.clicked.connect(self.refresh)
        btn_box.addWidget(self.btn_refresh)

        header_bar.addLayout(btn_box)
        self.content_lay.addLayout(header_bar)

    def _build_kpi_strip(self) -> None:
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(14)

        # 4 KPI Cards
        self.card_sales = KpiCard(
            title="Total Sales",
            icon="trending-up",
            value="P0.00",
            subtitle="Booked sales in period",
            subtitle_tone=TONE_POSITIVE,
            icon_theme="gold",
        )
        self.card_expenses = KpiCard(
            title="Total Expenses",
            icon="expenses",
            value="P0.00",
            subtitle="Operational outflows",
            subtitle_tone=TONE_POSITIVE,
            icon_theme="coral",
        )
        self.card_net_income = KpiCard(
            title="Net Income",
            icon="credit-card",
            value="P0.00",
            subtitle="Sales minus expenses",
            subtitle_tone=TONE_POSITIVE,
            icon_theme="green",
        )
        self.card_pending = KpiCard(
            title="Pending Orders",
            icon="clock",
            value="0",
            subtitle="Orders awaiting fulfillment",
            subtitle_tone=TONE_NEUTRAL,
            icon_theme="blue",
        )

        kpi_grid.addWidget(self.card_sales, 0, 0)
        kpi_grid.addWidget(self.card_expenses, 0, 1)
        kpi_grid.addWidget(self.card_net_income, 0, 2)
        kpi_grid.addWidget(self.card_pending, 0, 3)

        self.content_lay.addLayout(kpi_grid)

    def _build_filter_toolbar(self) -> None:
        toolbar_card = QFrame()
        toolbar_card.setObjectName("DashboardPanel")
        tb_lay = QHBoxLayout(toolbar_card)
        tb_lay.setContentsMargins(16, 12, 16, 12)
        tb_lay.setSpacing(12)

        # 1. Preset Dropdown
        preset_lbl = QLabel("Date Range:")
        preset_lbl.setStyleSheet("font-weight: 600; color: #475569; font-size: 13px;")
        tb_lay.addWidget(preset_lbl)

        self.combo_preset = QComboBox()
        self.combo_preset.addItems(_date_presets())
        self.combo_preset.setFixedWidth(130)
        self.combo_preset.currentIndexChanged.connect(self._on_preset_changed)
        tb_lay.addWidget(self.combo_preset)

        # 2. From / To Date Pickers
        from_lbl = QLabel("From:")
        from_lbl.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 500;")
        tb_lay.addWidget(from_lbl)

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setFixedWidth(115)
        self.date_from.dateChanged.connect(self._on_custom_date_changed)
        tb_lay.addWidget(self.date_from)

        to_lbl = QLabel("To:")
        to_lbl.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 500;")
        tb_lay.addWidget(to_lbl)

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setFixedWidth(115)
        self.date_to.dateChanged.connect(self._on_custom_date_changed)
        tb_lay.addWidget(self.date_to)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.VLine)
        div.setStyleSheet("background-color: #E2E8F0; width: 1px; max-height: 24px;")
        tb_lay.addWidget(div)

        # 3. Real-Time Search Bar
        search_icon = QLabel()
        search_icon.setPixmap(get_pixmap("search", color="#94A3B8", size=15))
        tb_lay.addWidget(search_icon)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search raw data (reference #, entity, description, category)...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._apply_table_filters)
        tb_lay.addWidget(self.search_input, 1)

        # 4. Active Chart Filter Badge (Initially Hidden)
        self.filter_chip_frame = QFrame()
        self.filter_chip_frame.setStyleSheet(
            "background-color: #FEF3C7; border: 1px solid #FDE68A; border-radius: 6px; padding: 2px 6px;"
        )
        chip_lay = QHBoxLayout(self.filter_chip_frame)
        chip_lay.setContentsMargins(6, 2, 6, 2)
        chip_lay.setSpacing(6)

        self.filter_chip_label = QLabel("")
        self.filter_chip_label.setStyleSheet("color: #92400E; font-size: 12px; font-weight: 600;")
        chip_lay.addWidget(self.filter_chip_label)

        self.btn_clear_filter = QPushButton("x Reset")
        self.btn_clear_filter.setStyleSheet(
            "background: transparent; color: #B45309; border: none; font-size: 12px; font-weight: bold; cursor: pointer;"
        )
        self.btn_clear_filter.clicked.connect(self._clear_active_chart_filter)
        chip_lay.addWidget(self.btn_clear_filter)

        self.filter_chip_frame.setVisible(False)
        tb_lay.addWidget(self.filter_chip_frame)

        self.content_lay.addWidget(toolbar_card)

    def _build_charts_grid(self) -> None:
        grid = QGridLayout()
        grid.setSpacing(16)

        # Chart 1: Top-Left — Monthly Sales & Revenue Trend (Bar Chart)
        self.panel_sales = self._create_chart_panel(
            title="Monthly Sales & Revenue Trend",
            subtitle="Last 6 months • Rich Gold (#D4AF37) • Click bar to filter table • Hover for details"
        )
        self.sales_chart_view = QChartView()
        self.sales_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.sales_chart_view.setMinimumHeight(280)
        self.sales_chart_view.setStyleSheet("background: transparent;")
        self.panel_sales["body"].addWidget(self.sales_chart_view)
        grid.addWidget(self.panel_sales["frame"], 0, 0)

        # Chart 2: Top-Right — Operating Expenses Breakdown (Donut Chart)
        self.panel_expenses = self._create_chart_panel(
            title="Operating Expenses Breakdown",
            subtitle="Grouped by category • Click slice to filter table • Hover for share"
        )
        self.expense_chart_view = QChartView()
        self.expense_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.expense_chart_view.setMinimumHeight(280)
        self.expense_chart_view.setStyleSheet("background: transparent;")
        self.panel_expenses["body"].addWidget(self.expense_chart_view)
        grid.addWidget(self.panel_expenses["frame"], 0, 1)

        # Chart 3: Bottom-Left — Inventory Valuation & Stock Levels (Horizontal Bar Chart)
        self.panel_inventory = self._create_chart_panel(
            title="Inventory Valuation & Stock Levels",
            subtitle="Top 5 materials by total value (Quantity × Cost per Unit)"
        )
        self.inventory_chart_view = QChartView()
        self.inventory_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.inventory_chart_view.setMinimumHeight(280)
        self.inventory_chart_view.setStyleSheet("background: transparent;")
        self.panel_inventory["body"].addWidget(self.inventory_chart_view)
        grid.addWidget(self.panel_inventory["frame"], 1, 0)

        # Chart 4: Bottom-Right — Accounts Receivable (Stacked Bar Chart)
        self.panel_receivables = self._create_chart_panel(
            title="Accounts Receivable (Paid vs Unpaid)",
            subtitle="Monthly collections vs outstanding balances (Last 6 months)"
        )
        self.receivable_chart_view = QChartView()
        self.receivable_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.receivable_chart_view.setMinimumHeight(280)
        self.receivable_chart_view.setStyleSheet("background: transparent;")
        self.panel_receivables["body"].addWidget(self.receivable_chart_view)
        grid.addWidget(self.panel_receivables["frame"], 1, 1)

        self.content_lay.addLayout(grid)

    def _create_chart_panel(self, title: str, subtitle: str) -> dict:
        frame = QFrame()
        frame.setObjectName("DashboardPanel")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)

        # Panel Header
        t_lbl = QLabel(title)
        t_lbl.setObjectName("PanelTitle")
        sub_lbl = QLabel(subtitle)
        sub_lbl.setStyleSheet("font-size: 11px; color: #64748B;")

        lay.addWidget(t_lbl)
        lay.addWidget(sub_lbl)

        # Body Layout where chart view sits
        body = QVBoxLayout()
        body.setContentsMargins(0, 4, 0, 0)
        lay.addLayout(body, 1)

        return {"frame": frame, "body": body, "title": t_lbl, "sub": sub_lbl}

    def _build_data_table(self) -> None:
        table_panel = QFrame()
        table_panel.setObjectName("DashboardPanel")
        panel_lay = QVBoxLayout(table_panel)
        panel_lay.setContentsMargins(18, 16, 18, 16)
        panel_lay.setSpacing(12)

        # Header Row above Table
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        t_lbl = QLabel("Detailed Source Transactions")
        t_lbl.setObjectName("PanelTitle")
        top_row.addWidget(t_lbl)

        self.lbl_table_count = QLabel("(0 records)")
        self.lbl_table_count.setStyleSheet("font-size: 12px; color: #64748B; font-weight: 500;")
        top_row.addWidget(self.lbl_table_count)
        top_row.addStretch(1)

        desc_lbl = QLabel("Raw data powering live KPI metrics and visual charts")
        desc_lbl.setStyleSheet("font-size: 12px; color: #94A3B8;")
        top_row.addWidget(desc_lbl)

        panel_lay.addLayout(top_row)

        # Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Date", "Reference #", "Customer/Supplier", "Description", "Category", "Amount"
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(320)

        # Enforce exact column sizing and single Stretch on Description to prevent collisions
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 150)  # Date

        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 120)  # Reference #

        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 180)  # Customer/Supplier

        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Description fills remainder

        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 140)  # Category Pill

        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 140)  # Amount

        panel_lay.addWidget(self.table)
        self.content_lay.addWidget(table_panel)

    # -- Date Filter Signals --------------------------------------------
    def _apply_preset(self, preset: str, trigger_refresh: bool = True) -> None:
        idx = self.combo_preset.findText(preset)
        if idx >= 0:
            self.combo_preset.blockSignals(True)
            self.combo_preset.setCurrentIndex(idx)
            self.combo_preset.blockSignals(False)

        start, end = _calc_preset_dates(preset)
        self.date_from.blockSignals(True)
        self.date_to.blockSignals(True)
        self.date_from.setDate(QDate(start.year, start.month, start.day))
        self.date_to.setDate(QDate(end.year, end.month, end.day))
        self.date_from.blockSignals(False)
        self.date_to.blockSignals(False)

        if trigger_refresh:
            self.refresh()

    def _on_preset_changed(self, index: int) -> None:
        preset = self.combo_preset.currentText()
        if preset == "Custom Range":
            return
        self._apply_preset(preset, trigger_refresh=True)

    def _on_custom_date_changed(self) -> None:
        # Switch combo to 'Custom Range'
        self.combo_preset.blockSignals(True)
        idx = self.combo_preset.findText("Custom Range")
        if idx >= 0:
            self.combo_preset.setCurrentIndex(idx)
        self.combo_preset.blockSignals(False)
        self.refresh()

    def _get_active_date_strings(self) -> tuple[str, str]:
        s = self.date_from.date().toPyDate().isoformat()
        e = self.date_to.date().toPyDate().isoformat()
        return s, e

    # -- Live Refresh & Data Loading ------------------------------------
    def refresh(self) -> None:
        """Fetch updated analytics from MySQL and redraw all components."""
        start_str, end_str = self._get_active_date_strings()
        conn = self._conn()
        try:
            mgr = ReportManager(conn)

            # 1. KPIs
            self._active_kpis = mgr.get_kpis(start=start_str, end=end_str)
            self._update_kpi_cards(self._active_kpis)

            # 2. Charts
            self._sales_trend_data = mgr.get_monthly_sales_trend(num_months=6)
            self._render_sales_trend_chart(self._sales_trend_data)

            self._expenses_breakdown_data = mgr.get_expenses_breakdown(start=start_str, end=end_str)
            self._render_expenses_breakdown_chart(self._expenses_breakdown_data)

            top_materials = mgr.get_top_materials_valuation(limit=5)
            self._render_inventory_valuation_chart(top_materials)

            receivables_data = mgr.get_accounts_receivable_monthly(num_months=6)
            self._render_receivables_chart(receivables_data)

            # 3. Raw Transactions Table
            self._raw_transactions = mgr.get_detailed_transactions(start=start_str, end=end_str)
            self._apply_table_filters()

        finally:
            conn.close()

    def _update_kpi_cards(self, kpis: dict) -> None:
        sales = kpis.get("total_sales", Decimal("0.00"))
        expenses = kpis.get("total_expenses", Decimal("0.00"))
        net = kpis.get("net_income", Decimal("0.00"))
        pending = kpis.get("pending_orders", 0)

        self.card_sales.set_value(f"P{sales:,.2f}")
        self.card_sales.set_subtitle("Completed & active orders", tone=TONE_POSITIVE)

        self.card_expenses.set_value(f"P{expenses:,.2f}")
        self.card_expenses.set_subtitle("Operational outflows", tone=TONE_POSITIVE)

        net_tone = TONE_POSITIVE if net >= 0 else TONE_NEGATIVE
        self.card_net_income.set_value(f"P{net:,.2f}")
        self.card_net_income.set_subtitle("Net operational margin", tone=net_tone)

        self.card_pending.set_value(str(pending))
        pending_sub = "All caught up!" if pending == 0 else f"{pending} awaiting action"
        self.card_pending.set_subtitle(pending_sub, tone=TONE_NEUTRAL)

    # -- Chart 1: Monthly Sales Trend (Bar Chart) -----------------------
    def _render_sales_trend_chart(self, months_data: list[dict]) -> None:
        chart = QChart()
        chart.setTheme(QChart.ChartTheme.ChartThemeLight)
        chart.setBackgroundVisible(False)
        chart.legend().setVisible(False)
        chart.layout().setContentsMargins(0, 0, 0, 0)

        bar_set = QBarSet("Monthly Sales")
        bar_set.setColor(QColor("#D4AF37"))  # Rich Gold

        max_val = 0.0
        for m in months_data:
            val = float(m["amount"])
            bar_set.append(val)
            if val > max_val:
                max_val = val

        series = QBarSeries()
        series.append(bar_set)
        chart.addSeries(series)

        # Axes
        cat_axis = QBarCategoryAxis()
        cat_axis.append([m["label"] for m in months_data])
        cat_axis.setLabelsColor(QColor("#475569"))
        cat_axis.setLabelsFont(QFont("Segoe UI", 9))
        chart.addAxis(cat_axis, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(cat_axis)

        val_axis = QValueAxis()
        val_axis.setRange(0, max(max_val * 1.18, 1000.0))
        val_axis.setLabelFormat("P%d")
        val_axis.setLabelsColor(QColor("#475569"))
        val_axis.setLabelsFont(QFont("Segoe UI", 9))
        val_axis.setGridLineColor(QColor("#F1F5F9"))
        chart.addAxis(val_axis, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(val_axis)

        # Hover & Click Interactivity
        def on_hovered(status: bool, index: int):
            if status and 0 <= index < len(months_data):
                item = months_data[index]
                QToolTip.showText(
                    QCursor.pos(),
                    f"Month: {item['label']}\nTotal Sales: P{item['amount']:,.2f}\n(Click bar to filter table)"
                )
            else:
                QToolTip.hideText()

        def on_clicked(index: int):
            if 0 <= index < len(months_data):
                ym = months_data[index]["ym"]
                lbl = months_data[index]["label"]
                if self._active_filter_type == "sales_month" and self._active_filter_val == ym:
                    self._clear_active_chart_filter()
                else:
                    self._set_active_chart_filter("sales_month", ym, f"Sales Month: {lbl}")

        bar_set.hovered.connect(on_hovered)
        bar_set.clicked.connect(on_clicked)

        self.sales_chart_view.setChart(chart)

    # -- Chart 2: Operating Expenses Breakdown (Donut Chart) ------------
    def _render_expenses_breakdown_chart(self, breakdown: list[dict]) -> None:
        chart = QChart()
        chart.setTheme(QChart.ChartTheme.ChartThemeLight)
        chart.setBackgroundVisible(False)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignRight)
        chart.legend().setFont(QFont("Segoe UI", 9))
        chart.legend().setLabelColor(QColor("#334155"))
        chart.layout().setContentsMargins(0, 0, 0, 0)

        series = QPieSeries()
        series.setHoleSize(0.48)

        total_exp = sum(r["total"] for r in breakdown)

        if not breakdown or total_exp == 0:
            empty_slice = series.append("No Expenses", 1)
            empty_slice.setColor(QColor("#E2E8F0"))
            empty_slice.setLabelVisible(True)
        else:
            for item in breakdown:
                cat = item["category"]
                amt = item["total"]
                val = float(amt)
                pct = (val / float(total_exp)) * 100.0 if total_exp > 0 else 0.0

                slice_label = f"{cat} ({pct:.0f}%)"
                pie_slice = series.append(slice_label, val)
                color_hex = CATEGORY_COLORS.get(cat, "#64748B")
                pie_slice.setColor(QColor(color_hex))
                pie_slice.setLabelVisible(True)
                pie_slice.setLabelFont(QFont("Segoe UI", 9))
                pie_slice.setLabelBrush(QColor("#1E293B"))

                # Connect Hover & Click for each slice
                def make_hover_handler(s: QPieSlice, c: str, a: Decimal, p: float):
                    def handler(state: bool):
                        s.setExploded(state)
                        if state:
                            QToolTip.showText(
                                QCursor.pos(),
                                f"Category: {c}\nAmount: P{a:,.2f} ({p:.1f}%)\n(Click slice to filter table)"
                            )
                        else:
                            QToolTip.hideText()
                    return handler

                def make_click_handler(c: str):
                    def handler():
                        if self._active_filter_type == "expense_category" and self._active_filter_val == c:
                            self._clear_active_chart_filter()
                        else:
                            self._set_active_chart_filter("expense_category", c, f"Expense Category: {c}")
                    return handler

                pie_slice.hovered.connect(make_hover_handler(pie_slice, cat, amt, pct))
                pie_slice.clicked.connect(make_click_handler(cat))

        chart.addSeries(series)
        self.expense_chart_view.setChart(chart)

    # -- Chart 3: Inventory Valuation (Horizontal Bar Chart) ------------
    def _render_inventory_valuation_chart(self, top_materials: list[dict]) -> None:
        chart = QChart()
        chart.setTheme(QChart.ChartTheme.ChartThemeLight)
        chart.setBackgroundVisible(False)
        chart.legend().setVisible(False)
        chart.layout().setContentsMargins(0, 0, 0, 0)

        # Reverse list so the highest value item sits on the top row
        items = list(reversed(top_materials)) if top_materials else []

        series = QHorizontalBarSeries()
        bar_set = QBarSet("Valuation")
        bar_set.setColor(QColor("#0284C7"))  # Vivid Sky Blue

        max_val = 0.0
        for m in items:
            val = float(m["total_val"])
            bar_set.append(val)
            if val > max_val:
                max_val = val

        series.append(bar_set)
        chart.addSeries(series)

        cat_axis = QBarCategoryAxis()
        cat_axis.append([m["material_name"] for m in items])
        cat_axis.setLabelsColor(QColor("#475569"))
        cat_axis.setLabelsFont(QFont("Segoe UI", 9))
        chart.addAxis(cat_axis, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(cat_axis)

        val_axis = QValueAxis()
        val_axis.setRange(0, max(max_val * 1.20, 500.0))
        val_axis.setLabelFormat("P%d")
        val_axis.setLabelsColor(QColor("#475569"))
        val_axis.setLabelsFont(QFont("Segoe UI", 9))
        val_axis.setGridLineColor(QColor("#F1F5F9"))
        chart.addAxis(val_axis, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(val_axis)

        # Tooltip Hover
        def on_hovered(status: bool, index: int):
            if status and 0 <= index < len(items):
                m = items[index]
                QToolTip.showText(
                    QCursor.pos(),
                    f"Material: {m['material_name']}\n"
                    f"Stock: {m['current_stock_qty']} units @ P{m['cost_per_unit']:,.2f}\n"
                    f"Total Valuation: P{m['total_val']:,.2f}"
                )
            else:
                QToolTip.hideText()

        bar_set.hovered.connect(on_hovered)
        self.inventory_chart_view.setChart(chart)

    # -- Chart 4: Accounts Receivable (Stacked Bar Chart) ---------------
    def _render_receivables_chart(self, receivables_data: list[dict]) -> None:
        chart = QChart()
        chart.setTheme(QChart.ChartTheme.ChartThemeLight)
        chart.setBackgroundVisible(False)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignTop)
        chart.legend().setFont(QFont("Segoe UI", 9))
        chart.legend().setLabelColor(QColor("#334155"))
        chart.layout().setContentsMargins(0, 0, 0, 0)

        series = QStackedBarSeries()
        set_paid = QBarSet("Paid Amount")
        set_paid.setColor(QColor("#10B981"))  # Emerald Green

        set_unpaid = QBarSet("Unpaid / Balance")
        set_unpaid.setColor(QColor("#EF4444"))  # Coral Red

        max_total = 0.0
        for m in receivables_data:
            p_val = float(m["paid"])
            u_val = float(m["unpaid"])
            set_paid.append(p_val)
            set_unpaid.append(u_val)
            tot = p_val + u_val
            if tot > max_total:
                max_total = tot

        series.append(set_paid)
        series.append(set_unpaid)
        chart.addSeries(series)

        cat_axis = QBarCategoryAxis()
        cat_axis.append([m["label"] for m in receivables_data])
        cat_axis.setLabelsColor(QColor("#475569"))
        cat_axis.setLabelsFont(QFont("Segoe UI", 9))
        chart.addAxis(cat_axis, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(cat_axis)

        val_axis = QValueAxis()
        val_axis.setRange(0, max(max_total * 1.20, 1000.0))
        val_axis.setLabelFormat("P%d")
        val_axis.setLabelsColor(QColor("#475569"))
        val_axis.setLabelsFont(QFont("Segoe UI", 9))
        val_axis.setGridLineColor(QColor("#F1F5F9"))
        chart.addAxis(val_axis, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(val_axis)
        # Tooltip Hover
        def on_paid_hovered(status: bool, index: int):
            if status and 0 <= index < len(receivables_data):
                m = receivables_data[index]
                QToolTip.showText(
                    QCursor.pos(),
                    f"Period: {m['label']}\n"
                    f"Paid / Collected: P{m['paid']:,.2f}\n"
                    f"Outstanding Balance: P{m['unpaid']:,.2f}"
                )
            else:
                QToolTip.hideText()

        set_paid.hovered.connect(on_paid_hovered)
        set_unpaid.hovered.connect(on_paid_hovered)

        self.receivable_chart_view.setChart(chart)

    # -- Interactive Chart Filtering ------------------------------------
    def _set_active_chart_filter(self, filter_type: str, filter_val: str, label: str) -> None:
        self._active_filter_type = filter_type
        self._active_filter_val = filter_val
        self._active_filter_label = label
        self.filter_chip_label.setText(label)
        self.filter_chip_frame.setVisible(True)
        self._apply_table_filters()

    def _clear_active_chart_filter(self) -> None:
        self._active_filter_type = None
        self._active_filter_val = None
        self._active_filter_label = None
        self.filter_chip_frame.setVisible(False)
        self._apply_table_filters()

    def _apply_table_filters(self) -> None:
        query = self.search_input.text().strip().lower()
        filtered = []

        for row in self._raw_transactions:
            # 1. Chart filter
            if self._active_filter_type == "sales_month":
                if row.get("record_type") != "sales" or row.get("ym") != self._active_filter_val:
                    continue
            elif self._active_filter_type == "expense_category":
                if row.get("record_type") != "expense" or row.get("category") != self._active_filter_val:
                    continue

            # 2. Text Search filter
            if query:
                ref = row.get("reference_no", "").lower()
                ent = row.get("entity_name", "").lower()
                desc = row.get("description", "").lower()
                cat = row.get("category", "").lower()
                amt = f"{row.get('amount', 0):,.2f}".lower()
                if not any(query in field for field in (ref, ent, desc, cat, amt)):
                    continue

            filtered.append(row)

        self._filtered_transactions = filtered
        self._populate_table(filtered)

    # -- Table Population -----------------------------------------------
    def _populate_table(self, rows: list[dict]) -> None:
        self.table.clearContents()
        self.table.setRowCount(len(rows))
        self.lbl_table_count.setText(f"({len(rows)} records displayed)")

        for r_idx, row in enumerate(rows):
            # Col 0: Date (Fixed: 150px, Center)
            dt_raw = row.get("tx_date")
            if isinstance(dt_raw, datetime):
                dt_str = dt_raw.strftime("%Y-%m-%d %H:%M")
            elif isinstance(dt_raw, date):
                dt_str = dt_raw.strftime("%Y-%m-%d")
            else:
                dt_str = str(dt_raw or "")
            item_date = QTableWidgetItem(dt_str)
            item_date.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r_idx, 0, item_date)

            # Col 1: Reference # (Fixed: 120px, Center)
            ref_str = row.get("reference_no", "")
            item_ref = QTableWidgetItem(ref_str)
            item_ref.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r_idx, 1, item_ref)

            # Col 2: Customer / Supplier (Fixed: 180px, Left)
            ent_str = row.get("entity_name", "")
            item_ent = QTableWidgetItem(ent_str)
            item_ent.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(r_idx, 2, item_ent)

            # Col 3: Description (Stretch, Left, with tooltip)
            desc_str = row.get("description", "")
            item_desc = QTableWidgetItem(desc_str)
            item_desc.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            item_desc.setToolTip(desc_str)
            self.table.setItem(r_idx, 3, item_desc)

            # Col 4: Category Pill (Fixed: 140px, Centered Widget)
            cat_str = row.get("category", "Other")
            pill_widget = self._create_category_pill(cat_str)
            self.table.setCellWidget(r_idx, 4, pill_widget)

            # Col 5: Amount (Fixed: 140px, Right)
            amt = row.get("amount", Decimal("0.00"))
            is_sales = row.get("record_type") == "sales"
            sign_str = "+" if is_sales else "-"
            amt_str = f"{sign_str}P{amt:,.2f}"

            item_amt = QTableWidgetItem(amt_str)
            item_amt.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
            if is_sales:
                item_amt.setForeground(QColor("#15803D"))  # Green
            else:
                item_amt.setForeground(QColor("#DC2626"))  # Red
            self.table.setItem(r_idx, 5, item_amt)

            self.table.setRowHeight(r_idx, 40)

    def _create_category_pill(self, cat: str) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pill = QLabel(f" {cat} ")
        pill.setObjectName("StatusPill")

        c_lower = cat.lower()
        if "sales" in c_lower:
            pill.setProperty("status", "sales")
        elif "material" in c_lower:
            pill.setProperty("status", "materials")
        elif "labor" in c_lower:
            pill.setProperty("status", "labor")
        elif "util" in c_lower:
            pill.setProperty("status", "utility")
        elif "misc" in c_lower:
            pill.setProperty("status", "miscellaneous")
        else:
            pill.setProperty("status", "other")

        lay.addWidget(pill)
        return w

    # -- Export Functionality (Repositioned to Top-Right Header) ---------
    def export_csv(self) -> None:
        """Export currently filtered/displayed table data to a CSV file."""
        if not self._filtered_transactions:
            QMessageBox.warning(self, "No Records", "There are no transactions displayed to export.")
            return

        default_name = f"analytics_data_{date.today().strftime('%Y%m%d')}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Export Analytics Data", default_name, "CSV (*.csv)")
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Reference #", "Customer / Supplier", "Description", "Category", "Amount (PHP)"])
                for row in self._filtered_transactions:
                    dt = row.get("tx_date")
                    dt_str = dt.strftime("%Y-%m-%d %H:%M") if isinstance(dt, datetime) else str(dt or "")
                    sign = "+" if row.get("record_type") == "sales" else "-"
                    amt_str = f"{sign}{row.get('amount', 0):,.2f}"
                    writer.writerow([
                        dt_str,
                        row.get("reference_no", ""),
                        row.get("entity_name", ""),
                        row.get("description", ""),
                        row.get("category", ""),
                        amt_str,
                    ])

            QMessageBox.information(
                self,
                "Export Successful",
                f"Successfully exported {len(self._filtered_transactions)} transactions to:\n{path}"
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Export Error", f"Failed to export CSV: {exc}")

    def download_pdf(self) -> None:
        """Generate and export a styled ReportLab PDF of the active analytics report."""
        if not self._filtered_transactions:
            QMessageBox.warning(self, "No Records", "There are no transactions displayed to export.")
            return

        default_name = f"analytics_report_{date.today().strftime('%Y%m%d')}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Download Analytics Report", default_name, "PDF (*.pdf)")
        if not path:
            return

        try:
            self._generate_pdf_report(path)
            QMessageBox.information(
                self,
                "Export Successful",
                f"Executive Analytics PDF Report saved to:\n{path}"
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Export Error", f"Failed to generate PDF: {exc}")

    def _generate_pdf_report(self, path: str) -> None:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

        doc = SimpleDocTemplate(
            path, pagesize=LETTER,
            leftMargin=36, rightMargin=36,
            topMargin=36, bottomMargin=36
        )
        styles = getSampleStyleSheet()

        brand_style = ParagraphStyle(
            "BrandHeader",
            parent=styles["Title"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0F172A"),
            alignment=0,
        )
        sub_style = ParagraphStyle(
            "SubHeader",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#64748B"),
        )
        cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1E293B"),
        )
        header_style = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontSize=8.5,
            leading=11,
            fontName="Helvetica-Bold",
            textColor=colors.white,
        )

        start_str, end_str = self._get_active_date_strings()
        filter_scope = self._active_filter_label or "All Categories"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        story = [
            Paragraph("AkoNi Printing Services", brand_style),
            Paragraph("Executive Analytics & Operational Performance Report", styles["Heading2"]),
            Paragraph(f"Reporting Range: {start_str} to {end_str}  |  Filter Scope: {filter_scope}  |  Generated: {timestamp}", sub_style),
            Spacer(1, 14),
        ]

        # 1. Summary KPI Metrics Block
        story.append(Paragraph("Key Performance Summary", styles["Heading3"]))
        sales = self._active_kpis.get("total_sales", Decimal("0.00"))
        exp = self._active_kpis.get("total_expenses", Decimal("0.00"))
        net = self._active_kpis.get("net_income", Decimal("0.00"))
        pending = self._active_kpis.get("pending_orders", 0)

        kpi_data = [
            ["Total Sales", "Total Expenses", "Net Margin", "Pending Orders"],
            [f"P{sales:,.2f}", f"P{exp:,.2f}", f"P{net:,.2f}", f"{pending} orders"]
        ]
        kpi_table = Table(kpi_data, colWidths=[135, 135, 135, 135])
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F8FAFC")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("FONTSIZE", (0, 1), (-1, 1), 10),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ]))
        story += [kpi_table, Spacer(1, 16)]

        # 2. Detailed Transactions Table
        story.append(Paragraph(f"Filtered Transactions Log ({len(self._filtered_transactions)} records)", styles["Heading3"]))
        tx_headers = [
            Paragraph("Date", header_style),
            Paragraph("Ref #", header_style),
            Paragraph("Customer/Supplier", header_style),
            Paragraph("Description", header_style),
            Paragraph("Category", header_style),
            Paragraph("Amount", header_style),
        ]

        table_data = [tx_headers]
        for r in self._filtered_transactions:
            dt = r.get("tx_date")
            dt_s = dt.strftime("%Y-%m-%d %H:%M") if isinstance(dt, datetime) else str(dt or "")
            sign = "+" if r.get("record_type") == "sales" else "-"
            amt_s = f"{sign}P{r.get('amount', 0):,.2f}"

            table_data.append([
                Paragraph(dt_s, cell_style),
                Paragraph(r.get("reference_no", ""), cell_style),
                Paragraph(r.get("entity_name", ""), cell_style),
                Paragraph(r.get("description", ""), cell_style),
                Paragraph(r.get("category", ""), cell_style),
                Paragraph(amt_s, cell_style),
            ])

        col_widths = [72, 60, 95, 175, 65, 73]
        tx_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        tx_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]))
        story += [tx_table]

        doc.build(story)
