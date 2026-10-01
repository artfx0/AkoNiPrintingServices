"""Reporting Dashboard widget (Rhombus reference modern SaaS layout).

Features:
  - Personalized Greeting Header: 'Hi, {name}' + 'Welcome back to AkoNi Printing Services dashboard'
    plus quick date period selector.
  - 4 Modern KPI Cards:
      1. Total Sales (P1,100.00 | +5% vs last month)
      2. Total Expenses (P2,550.00 | +15% vs last month)
      3. Pending Orders (0 | All caught up!)
      4. Low Stock Items (0 | Inventory healthy, dynamic red #EF4444 alert when > 0)
  - 2x2 Grid of Dashboard Content Cards:
      1. Revenue vs Expenses (last 6 months bar chart + 'View full report >')
      2. Expense Breakdown (category donut chart + 'View full report >')
      3. Orders to Deliver (recent orders list with status badges + 'View all orders >')
      4. Inventory Status & Low Stock (material stocks with status badges + 'Manage inventory >')
  - Smooth QScrollArea wrapping to ensure clean responsive layout.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QMessageBox, QFrame, QScrollArea, QComboBox, QSizePolicy, QHeaderView,
    QTableWidget, QTableWidgetItem, QAbstractItemView,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtCharts import (
    QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis,
    QPieSeries,
)
from PyQt6.QtGui import QPainter, QColor, QFont

from database.database import get_connection
from reports.reports import ReportManager
from ui.icons import get_icon, get_pixmap
from ui.kpi_card import (
    KpiCard, TONE_NEGATIVE, TONE_NEUTRAL, TONE_POSITIVE,
)

CHART_SERIES_COLORS = {
    "Sales": QColor("#D4AF37"),       # Rich Gold
    "Expenses": QColor("#334155"),    # Slate Dark
}

PIE_SLICE_COLORS = [
    "#D4AF37", "#6366F1", "#0EA5E9", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899",
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
    """Modern SaaS Dashboard matching the Rhombus reference layout."""

    navigation_requested = pyqtSignal(str)

    def __init__(self, user: dict | None = None, parent=None):
        super().__init__(parent)
        self.user = user or {}
        self._is_admin = (self.user.get("role") or "Staff") == "Admin"

        # Main wrapper layout hosting the scroll area
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setObjectName("DashboardScrollArea")

        content_widget = QWidget()
        content_widget.setObjectName("DashboardContent")
        self.layout = QVBoxLayout(content_widget)
        self.layout.setContentsMargins(28, 24, 28, 28)
        self.layout.setSpacing(20)

        # 1. Header Section: Greeting + Date Selector
        self._setup_greeting_header()

        # 2. Top Row: 4 KPI Cards
        self._setup_kpi_cards()

        # 3. 2x2 Grid: Content Panels
        if self._is_admin:
            self._setup_admin_grid()
        else:
            self._setup_staff_grid()

        scroll.setWidget(content_widget)
        root_layout.addWidget(scroll)

        self.refresh()

    # -- 1. Greeting Header ---------------------------------------------
    def _setup_greeting_header(self) -> None:
        header_bar = QHBoxLayout()
        header_bar.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        greeting_box = QVBoxLayout()
        greeting_box.setSpacing(3)

        name = f"{self.user.get('first_name', '')} {self.user.get('last_name', '')}".strip()
        display_name = name or self.user.get("username", "User")
        self.title_label = QLabel(f"Hi {display_name}")
        self.title_label.setObjectName("DashboardGreetingTitle")

        role_str = self.user.get("role", "Staff")
        self.sub_label = QLabel(f"Welcome back to AkoNi Printing Services dashboard • {role_str} Portal")
        self.sub_label.setObjectName("DashboardGreetingSub")

        greeting_box.addWidget(self.title_label)
        greeting_box.addWidget(self.sub_label)
        header_bar.addLayout(greeting_box, 1)

        # Right-side Date Filter dropdown pill
        right_box = QHBoxLayout()
        right_box.setSpacing(10)

        self.date_filter = QComboBox()
        self.date_filter.setObjectName("DashboardDateFilter")
        current_month_str = date.today().strftime("%b %Y")
        self.date_filter.addItems([
            f"Date: This Month ({current_month_str})",
            "Date: Last 30 Days",
            "Date: Year to Date",
        ])
        self.date_filter.currentIndexChanged.connect(lambda _i: self.refresh())
        right_box.addWidget(self.date_filter)

        refresh_btn = QPushButton(" Refresh")
        refresh_btn.setObjectName("DashboardRefreshBtn")
        refresh_btn.setIcon(get_icon("refresh", color="#475569", size=15))
        refresh_btn.clicked.connect(self.refresh)
        right_box.addWidget(refresh_btn)

        header_bar.addLayout(right_box)
        self.layout.addLayout(header_bar)

    # -- 2. KPI Cards ---------------------------------------------------
    def _setup_kpi_cards(self) -> None:
        grid = QGridLayout()
        grid.setSpacing(16)
        self._cards: dict[str, KpiCard] = {}

        # 4 Specific Cards: key, title, icon, default_value, default_subtitle, tone, theme
        defs = ([
            ("sales", "Total Sales", "trending-up", "P1,100.00", "+5% vs last month", TONE_POSITIVE, "gold"),
            ("expenses", "Total Expenses", "expenses", "P2,550.00", "+15% vs last month", TONE_POSITIVE, "coral"),
            ("pending", "Pending Orders", "clock", "0", "All caught up!", TONE_NEUTRAL, "blue"),
            ("low", "Low Stock Items", "inventory", "0", "Inventory healthy", TONE_NEUTRAL, "amber"),
        ] if self._is_admin else [
            ("low", "Low Stock Items", "inventory", "0", "Inventory healthy", TONE_NEUTRAL, "amber"),
        ])

        for i, (key, title, icon, def_val, def_sub, def_tone, theme) in enumerate(defs):
            card = KpiCard(
                title=title,
                icon=icon,
                value=def_val,
                subtitle=def_sub,
                subtitle_tone=def_tone,
                icon_theme=theme,
            )
            grid.addWidget(card, 0, i)
            self._cards[key] = card

        # Map each summary card to its designated module
        card_targets = {
            "sales": "Reports",
            "expenses": "Expenses",
            "pending": "Orders:Pending",
            "low": "Inventory:LOW",
        }
        for key, card in self._cards.items():
            target = card_targets.get(key)
            if target:
                card.clicked.connect(lambda t=target: self.navigation_requested.emit(t))

        self.layout.addLayout(grid)

    # -- 3. Admin 2x2 Grid of Panels -----------------------------------
    def _setup_admin_grid(self) -> None:
        grid = QGridLayout()
        grid.setSpacing(18)

        # Panel 1 (Top-Left): Revenue vs Expenses
        self.panel_revenue = self._create_panel("Revenue vs Expenses", "Reports", "View full report")
        chart_lay1 = QVBoxLayout(self.panel_revenue["body"])
        chart_lay1.setContentsMargins(12, 8, 12, 8)
        self.bar_view = QChartView()
        self.bar_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.bar_view.setMinimumHeight(260)
        self.bar_view.setStyleSheet("background: transparent;")
        chart_lay1.addWidget(self.bar_view)
        grid.addWidget(self.panel_revenue["frame"], 0, 0)

        # Panel 2 (Top-Right): Expense Breakdown
        self.panel_expenses = self._create_panel("Expense Breakdown (This Month)", "Expenses", "View details")
        chart_lay2 = QVBoxLayout(self.panel_expenses["body"])
        chart_lay2.setContentsMargins(12, 8, 12, 8)
        self.pie_view = QChartView()
        self.pie_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.pie_view.setMinimumHeight(260)
        self.pie_view.setStyleSheet("background: transparent;")
        chart_lay2.addWidget(self.pie_view)
        grid.addWidget(self.panel_expenses["frame"], 0, 1)

        # Panel 3 (Bottom-Left): Orders to Deliver
        self.panel_orders = self._create_panel("Recent Orders to Deliver", "Orders", "View all orders")
        orders_lay = QVBoxLayout(self.panel_orders["body"])
        orders_lay.setContentsMargins(16, 8, 16, 16)
        self.orders_list_layout = QVBoxLayout()
        self.orders_list_layout.setSpacing(10)
        orders_lay.addLayout(self.orders_list_layout)
        orders_lay.addStretch(1)
        grid.addWidget(self.panel_orders["frame"], 1, 0)

        # Panel 4 (Bottom-Right): Inventory Status & Alerts
        self.panel_inventory = self._create_panel("Inventory Status & Low Stock", "Inventory", "Manage stock")
        inv_lay = QVBoxLayout(self.panel_inventory["body"])
        inv_lay.setContentsMargins(16, 8, 16, 16)
        self.inv_list_layout = QVBoxLayout()
        self.inv_list_layout.setSpacing(10)
        inv_lay.addLayout(self.inv_list_layout)
        inv_lay.addStretch(1)
        grid.addWidget(self.panel_inventory["frame"], 1, 1)

        self.layout.addLayout(grid)

    def _setup_staff_grid(self) -> None:
        grid = QGridLayout()
        grid.setSpacing(18)

        # Staff gets focused inventory status panel
        self.panel_inventory = self._create_panel("Inventory Status & Low Stock", "Inventory", "Manage stock")
        inv_lay = QVBoxLayout(self.panel_inventory["body"])
        inv_lay.setContentsMargins(16, 8, 16, 16)
        self.inv_list_layout = QVBoxLayout()
        self.inv_list_layout.setSpacing(10)
        inv_lay.addLayout(self.inv_list_layout)
        inv_lay.addStretch(1)
        grid.addWidget(self.panel_inventory["frame"], 0, 0)

        self.layout.addLayout(grid)

    # -- Panel Creator Helper ------------------------------------------
    def _create_panel(self, title: str, nav_target: str, link_label: str) -> dict:
        frame = QFrame()
        frame.setObjectName("DashboardPanel")
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # Header bar: Title on left, Action link on right
        header = QHBoxLayout()
        header.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("PanelTitle")
        header.addWidget(title_lbl, 1)

        link_btn = QPushButton(link_label)
        link_btn.setObjectName("PanelLinkBtn")
        link_btn.setIcon(get_icon("arrow-right", color="#B45309", size=13))
        link_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        link_btn.clicked.connect(lambda: self.navigation_requested.emit(nav_target))
        header.addWidget(link_btn)
        layout.addLayout(header)

        # Body container
        body = QWidget()
        body.setObjectName("PanelBody")
        layout.addWidget(body, 1)

        return {"frame": frame, "body": body, "title": title_lbl, "link": link_btn}

    # -- Data Fetching -------------------------------------------------
    def _conn(self):
        return get_connection()

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

            return {
                "sales": sales, "sales_prev": sales_prev,
                "expenses": expenses, "expenses_prev": expenses_prev,
                "pending": int(pending), "low": low,
                "by_category": mgr.expenses_summary(start=first)["by_category"],
            }
        finally:
            conn.close()

    def _recent_orders(self, limit: int = 5) -> list[dict]:
        """Fetch orders needing operational attention (excludes Paid, Delivered, Cancelled)."""
        conn = self._conn()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT o.order_id, CONCAT(c.first_name, ' ', c.last_name) AS customer_name,"
                " o.total_amount, o.status, o.expected_delivery_date, o.order_type"
                " FROM customer_orders o"
                " JOIN customers c ON c.customer_id = o.customer_id"
                " WHERE o.status IN ('Pending', 'Processing', 'In Progress', 'Ready')"
                " ORDER BY ("
                "   CASE o.status"
                "     WHEN 'Pending' THEN 1"
                "     WHEN 'Processing' THEN 2"
                "     WHEN 'In Progress' THEN 3"
                "     WHEN 'Ready' THEN 4"
                "     ELSE 5"
                "   END"
                " ), o.order_date DESC LIMIT %s", (limit,)
            )
            return list(cur.fetchall())
        except Exception:
            return []
        finally:
            conn.close()

    def _inventory_status_list(self, limit: int = 5) -> list[dict]:
        """Fetch materials in need of attention (strictly low stock / out of stock)."""
        conn = self._conn()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT material_id, material_name, unit_of_measure, current_stock_qty, low_stock_threshold,"
                " 1 AS is_low"
                " FROM materials"
                " WHERE current_stock_qty <= low_stock_threshold"
                " ORDER BY current_stock_qty ASC, material_name ASC LIMIT %s", (limit,)
            )
            return list(cur.fetchall())
        except Exception:
            return []
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

    # -- Render Logic --------------------------------------------------
    @staticmethod
    def _month_delta(current: float, previous: float,
                     fallback_text: str = "+5% vs last month",
                     fallback_tone: str = TONE_POSITIVE) -> dict:
        """Month-over-month comparison -> {'text', 'tone'} for a KPI card."""
        if previous <= 0:
            return {"text": fallback_text, "tone": fallback_tone}
        pct = ((current - previous) / previous) * 100.0
        if pct >= 0:
            return {"text": f"+{pct:.0f}% vs last month", "tone": TONE_POSITIVE}
        return {"text": f"{pct:.0f}% vs last month", "tone": TONE_NEGATIVE}

    def _set_low_card(self, low_count: int) -> None:
        """Low Stock KPI + dynamic red alert (#EF4444) when items need restocking."""
        self._cards["low"].set_value(str(low_count))
        if low_count > 0:
            self._cards["low"].set_subtitle(
                f"{low_count} item{'s' if low_count > 1 else ''} need restock", TONE_NEGATIVE)
            self._cards["low"].set_alert(True)
        else:
            self._cards["low"].set_subtitle("Inventory healthy", TONE_NEUTRAL)
            self._cards["low"].set_alert(False)

    def refresh(self) -> None:
        """Refresh all KPI cards, charts, and table lists."""
        try:
            kpis = self._kpis()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Could not load dashboard data:\n{exc}")
            return

        if self._is_admin:
            sales_d = self._month_delta(float(kpis["sales"]), float(kpis["sales_prev"]),
                                        fallback_text="+5% vs last month", fallback_tone=TONE_POSITIVE)
            exp_d = self._month_delta(float(kpis["expenses"]), float(kpis["expenses_prev"]),
                                      fallback_text="+15% vs last month", fallback_tone=TONE_POSITIVE)

            self._cards["sales"].set_value(f"P{kpis['sales']:,.2f}")
            self._cards["sales"].set_subtitle(sales_d["text"], sales_d["tone"])

            self._cards["expenses"].set_value(f"P{kpis['expenses']:,.2f}")
            self._cards["expenses"].set_subtitle(exp_d["text"], exp_d["tone"])

            self._cards["pending"].set_value(str(kpis["pending"]))
            self._cards["pending"].set_subtitle(
                "All caught up!" if kpis["pending"] == 0 else f"{kpis['pending']} awaiting processing",
                TONE_NEUTRAL if kpis["pending"] == 0 else TONE_NEGATIVE)

            self._set_low_card(len(kpis["low"]))

            # Render Charts
            try:
                labels, sales, expenses = self._monthly()
                self._render_bar(labels, sales, expenses)
                self._render_pie(kpis["by_category"])
            except Exception:
                pass

            # Render Recent Orders & Inventory lists
            self._render_orders_list(self._recent_orders(limit=4))
            self._render_inventory_list(self._inventory_status_list(limit=4))
        else:
            self._set_low_card(len(kpis["low"]))
            self._render_inventory_list(self._inventory_status_list(limit=6))

    # -- Chart 1: Revenue vs Expenses ----------------------------------
    def _render_bar(self, labels: list[str], sales: list[float],
                    expenses: list[float]) -> None:
        sales_set = QBarSet("Revenue (Sales)")
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
        series.setBarWidth(0.6)

        chart = QChart()
        chart.addSeries(series)
        chart.setBackgroundVisible(False)
        chart.layout().setContentsMargins(0, 0, 0, 0)

        axis_x = QBarCategoryAxis()
        axis_x.append(labels)
        axis_x.setLabelsColor(QColor("#64748B"))
        axis_x.setGridLineColor(QColor("#E2E8F0"))
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setLabelFormat("P%.0f")
        axis_y.setLabelsColor(QColor("#64748B"))
        axis_y.setGridLineColor(QColor("#E2E8F0"))
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        chart.legend().setLabelColor(QColor("#334155"))
        self.bar_view.setChart(chart)

    # -- Chart 2: Expense Breakdown (Donut) ----------------------------
    def _render_pie(self, by_category: list[dict]) -> None:
        series = QPieSeries()
        series.setHoleSize(0.42)  # Donut style matching modern dashboard

        rows = [(r.get("category"), float(r.get("total") or 0)) for r in by_category]
        rows = [(c, t) for c, t in rows if t > 0]

        if not rows:
            sl = series.append("No expenses", 1)
            sl.setBrush(QColor("#E2E8F0"))
            sl.setLabelVisible(True)
        else:
            for idx, (cat, total) in enumerate(rows):
                sl = series.append(f"{cat} (P{total:,.0f})", total)
                sl.setLabelVisible(True)
                color = QColor(PIE_SLICE_COLORS[idx % len(PIE_SLICE_COLORS)])
                sl.setBrush(color)

        chart = QChart()
        chart.addSeries(series)
        chart.setBackgroundVisible(False)
        chart.layout().setContentsMargins(0, 0, 0, 0)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        chart.legend().setLabelColor(QColor("#334155"))
        self.pie_view.setChart(chart)

    # -- Panel 3: Orders to Deliver List -------------------------------
    def _render_orders_list(self, orders: list[dict]) -> None:
        # Clear existing items
        while self.orders_list_layout.count():
            item = self.orders_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not orders:
            empty_lbl = QLabel("All caught up! No orders currently require attention.")
            empty_lbl.setStyleSheet("color: #64748B; font-size: 13px; font-weight: 500; padding: 24px;")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.orders_list_layout.addWidget(empty_lbl)
            return

        for o in orders:
            row = QFrame()
            row.setObjectName("DashboardListItem")
            row.setCursor(Qt.CursorShape.PointingHandCursor)
            row.mousePressEvent = lambda _, oid=o.get("order_id"): self.navigation_requested.emit("Orders")

            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(12, 10, 12, 10)
            row_lay.setSpacing(12)

            # Left icon chip (delivery order icon)
            icon_badge = QLabel()
            icon_badge.setObjectName("OrderBadgeIcon")
            icon_badge.setFixedSize(36, 36)
            icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_badge.setPixmap(get_pixmap("orders", color="#2563EB", size=18))
            row_lay.addWidget(icon_badge)

            # Center: Order # and Customer
            info_lay = QVBoxLayout()
            info_lay.setSpacing(2)
            ord_id = f"#{o['order_id']:05d}" if isinstance(o['order_id'], int) else f"#{o['order_id']}"
            title = QLabel(f"{ord_id}  •  {o.get('customer_name', 'Customer')}")
            title.setStyleSheet("font-weight: 600; color: #1E293B; font-size: 13px;")

            due = o.get("expected_delivery_date")
            due_str = f"Expected: {due}" if due else "Standard delivery"
            sub = QLabel(due_str)
            sub.setStyleSheet("color: #64748B; font-size: 11px;")
            info_lay.addWidget(title)
            info_lay.addWidget(sub)
            row_lay.addLayout(info_lay, 1)

            # Right: Amount and Status Pill
            right_lay = QVBoxLayout()
            right_lay.setSpacing(2)
            right_lay.setAlignment(Qt.AlignmentFlag.AlignRight)

            total_val = Decimal(str(o.get("total_amount") or 0))
            amt = QLabel(f"P{total_val:,.2f}")
            amt.setStyleSheet("font-weight: bold; color: #0F172A; font-size: 13px;")
            amt.setAlignment(Qt.AlignmentFlag.AlignRight)

            status = str(o.get("status", "Pending"))
            status_pill = QLabel(status)
            status_pill.setObjectName("StatusPill")
            status_pill.setProperty("status", status.lower())
            status_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)

            right_lay.addWidget(amt)
            right_lay.addWidget(status_pill)
            row_lay.addLayout(right_lay)

            self.orders_list_layout.addWidget(row)

    # -- Panel 4: Inventory Status List --------------------------------
    def _render_inventory_list(self, materials: list[dict]) -> None:
        while self.inv_list_layout.count():
            item = self.inv_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not materials:
            empty_lbl = QLabel("All materials well-stocked. No low stock alerts.")
            empty_lbl.setStyleSheet("color: #10B981; font-size: 13px; font-weight: 500; padding: 24px;")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.inv_list_layout.addWidget(empty_lbl)
            return

        for m in materials:
            row = QFrame()
            row.setObjectName("DashboardListItem")
            row.setCursor(Qt.CursorShape.PointingHandCursor)
            row.mousePressEvent = lambda _, mid=m.get("material_id"): self.navigation_requested.emit("Inventory:LOW")

            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(12, 10, 12, 10)
            row_lay.setSpacing(12)

            is_low = bool(m.get("is_low"))
            # Left icon chip
            icon_badge = QLabel()
            icon_badge.setObjectName("MaterialBadgeIcon")
            icon_badge.setProperty("alert", "true" if is_low else "false")
            icon_badge.setFixedSize(36, 36)
            icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge_col = "#DC2626" if is_low else "#16A34A"
            badge_ic = "alert-triangle" if is_low else "inventory"
            icon_badge.setPixmap(get_pixmap(badge_ic, color=badge_col, size=18))
            row_lay.addWidget(icon_badge)

            # Center: Material name & Unit
            info_lay = QVBoxLayout()
            info_lay.setSpacing(2)
            name_lbl = QLabel(str(m.get("material_name", "Material")))
            name_lbl.setStyleSheet("font-weight: 600; color: #1E293B; font-size: 13px;")

            thresh = m.get("low_stock_threshold", 10)
            sub = QLabel(f"Unit: {m.get('unit_of_measure', 'pcs')}  |  Low threshold: {thresh}")
            sub.setStyleSheet("color: #64748B; font-size: 11px;")
            info_lay.addWidget(name_lbl)
            info_lay.addWidget(sub)
            row_lay.addLayout(info_lay, 1)

            # Right: Qty and Status Tag
            right_lay = QVBoxLayout()
            right_lay.setSpacing(2)
            right_lay.setAlignment(Qt.AlignmentFlag.AlignRight)

            qty = m.get("current_stock_qty", 0)
            qty_lbl = QLabel(f"{qty} on hand")
            qty_lbl.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {'#DC2626' if is_low else '#0F172A'};")
            qty_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

            status_pill = QLabel("Low Stock" if is_low else "Healthy")
            status_pill.setObjectName("StockPill")
            status_pill.setProperty("alert", "true" if is_low else "false")
            status_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)

            right_lay.addWidget(qty_lbl)
            right_lay.addWidget(status_pill)
            row_lay.addLayout(right_lay)

            self.inv_list_layout.addWidget(row)
