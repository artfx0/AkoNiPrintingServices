"""Main Window shell: left nav + QStackedWidget + status bar.

The global Rich Gold theme (ui/styles.qss) is applied once in main.py
via app.setStyleSheet(); windows must not override it.

RBAC:
  Admin -> Dashboard, Customers, Orders, Payments, Inventory, Expenses,
           Reports, Backup, Users (full access).
  Staff -> Dashboard, Inventory only.

Module pages are reused from the existing AdminDashboard / StaffDashboard
tab builders so all business logic stays in one place. The backend
dashboard instance is kept alive (never shown) as the slot owner.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget,
    QStackedWidget, QToolBar, QLabel, QPushButton, QStatusBar,
    QMessageBox, QGridLayout,
)
from PyQt6.QtCore import Qt

from database.database import get_connection
from reports.reports import ReportManager

# Nav labels per role. Admin keeps the full spec set + Backup/Users.
ADMIN_NAV = ["Dashboard", "Customers", "Orders", "Payments", "Inventory",
             "Expenses", "Reports", "Backup", "Users"]
STAFF_NAV = ["Dashboard", "Inventory"]


class MainWindow(QMainWindow):
    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.logout_requested = False
        self._is_admin = user.get("role") == "Admin"
        self.setWindowTitle(
            f"AkoNi Printing — {'Admin' if self._is_admin else 'Staff'}"
            f" ({user.get('username', '')})")
        self.resize(1200, 750)

        self._setup_toolbar()
        self._setup_body()
        self._setup_statusbar()

    # ---------- chrome ----------
    def _setup_toolbar(self) -> None:
        bar = QToolBar("Session")
        bar.setMovable(False)
        name = f"{self.user.get('first_name', '')} {self.user.get('last_name', '')}".strip()
        bar.addWidget(QLabel(
            f"AkoNi Printing Services   |   {self.user.get('username', '')}"
            f" ({self.user.get('role', '')})"
            f"{' — ' + name if name else ''}  "))
        bar.addSeparator()
        logout_btn = QPushButton("Logout")
        logout_btn.clicked.connect(self.request_logout)
        bar.addWidget(logout_btn)
        self.addToolBar(bar)

    def _setup_body(self) -> None:
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        self.nav.setMaximumWidth(190)
        self.nav.setMinimumWidth(170)
        self.nav.setVerticalScrollMode(self.nav.ScrollMode.ScrollPerPixel)
        layout.addWidget(self.nav)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self._build_pages()
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        if self.nav.count():
            self.nav.setCurrentRow(0)

    def _setup_statusbar(self) -> None:
        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage(
            f"Logged in as: {self.user.get('username', '')}"
            f" - {self.user.get('role', '')}")

    def request_logout(self) -> None:
        from auth.session import Session
        Session.clear()
        self.logout_requested = True
        self.close()

    # ---------- pages ----------
    def _build_pages(self) -> None:
        """Create nav + stacked pages, reusing existing dashboard builders."""
        if self._is_admin:
            from backup.settings_widget import SettingsWidget
            from customers.customer_widget import CustomerWidget
            from expenses.expense_widget import ExpenseWidget
            from inventory.inventory_widget import InventoryWidget
            from payments.payment_widget import PaymentWidget
            from reports.dashboard_widget import DashboardWidget
            from reports.reports_widget import ReportsWidget
            from sales_orders.order_widget import OrderWidget
            from ui.admin_dashboard import AdminDashboard
            # Hidden owner of all slots/signals; never shown.
            self._backend = AdminDashboard(self.user)
            hidden_tabs = self._backend.centralWidget()
            by_title = {hidden_tabs.tabText(i): hidden_tabs.widget(i)
                        for i in range(hidden_tabs.count())}
            # Standalone Phase-4/5/6/7/8/9/10 widgets (spec).
            self.customer_page = CustomerWidget()
            self.order_page = OrderWidget(user=self.user)
            self.payment_page = PaymentWidget(user=self.user)
            self.inventory_page = InventoryWidget(user=self.user)
            self.expense_page = ExpenseWidget(user=self.user)
            self.reports_page = ReportsWidget()
            self.settings_page = SettingsWidget(user=self.user)
            self.dashboard_page = DashboardWidget(user=self.user)
            title_map = {
                "Users": "Users",
            }
            self.nav.addItem("Dashboard")
            self.stack.addWidget(self.dashboard_page)
            for label in ADMIN_NAV[1:]:
                self.nav.addItem(label)
                if label == "Customers":
                    self.stack.addWidget(self.customer_page)
                elif label == "Orders":
                    self.stack.addWidget(self.order_page)
                elif label == "Payments":
                    self.stack.addWidget(self.payment_page)
                elif label == "Inventory":
                    self.stack.addWidget(self.inventory_page)
                elif label == "Expenses":
                    self.stack.addWidget(self.expense_page)
                elif label == "Reports":
                    self.stack.addWidget(self.reports_page)
                elif label == "Backup":
                    self.stack.addWidget(self.settings_page)
                else:
                    self.stack.addWidget(by_title[title_map[label]])
        else:
            from inventory.inventory_widget import InventoryWidget
            from reports.dashboard_widget import DashboardWidget
            self.inventory_page = InventoryWidget(user=self.user)
            self.dashboard_page = DashboardWidget(user=self.user)
            # Keep the legacy backend alive (harmless); the spec page is above.
            from ui.staff_dashboard import StaffDashboard
            self._backend = StaffDashboard(self.user)
            self.nav.addItem("Dashboard")
            self.stack.addWidget(self.dashboard_page)
            self.nav.addItem("Inventory")
            self.stack.addWidget(self.inventory_page)

    def _dashboard_home(self, is_admin: bool) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel("Dashboard")
        title.setObjectName("DashboardTitle")
        sub = QLabel("Overview of sales, payments, expenses and stock — AkoNi Printing Services")
        sub.setObjectName("DashboardSub")
        sub.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(sub)

        grid = QGridLayout()
        self._stat_cards: dict[str, QLabel] = {}
        defs = ([("Revenue collected", "revenue"), ("Expenses", "expenses"),
                 ("Profit", "profit"), ("Orders", "orders"),
                 ("Unpaid orders", "unpaid"), ("Low-stock items", "low")]
                if is_admin else [("Low-stock items", "low")])
        for i, (label, key) in enumerate(defs):
            card = QLabel(f"{label}\n—")
            card.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card.setMinimumHeight(90)
            grid.addWidget(card, i // 3, i % 3)
            self._stat_cards[key] = card
        layout.addLayout(grid)

        refresh_btn = QPushButton("Refresh overview")
        refresh_btn.clicked.connect(self.refresh_dashboard)
        layout.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        self.refresh_dashboard()
        return page

    def refresh_dashboard(self) -> None:
        try:
            conn = get_connection()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
            return
        try:
            mgr = ReportManager(conn)
            if self._is_admin:
                pl = mgr.profit_loss()
                unpaid = mgr.unpaid_orders()
                low = [m for m in mgr.inventory_status()
                       if m["current_stock_qty"] <= m["low_stock_threshold"]]
                self._set_stat("revenue", f"Revenue collected\n{pl['revenue_collected']}")
                self._set_stat("expenses", f"Expenses\n{pl['expenses']}")
                self._set_stat("profit", f"Profit\n{pl['profit']}")
                self._set_stat("orders",
                               f"Orders\n{pl['orders']} (booked {pl['order_revenue']})")
                self._set_stat("unpaid", f"Unpaid orders\n{len(unpaid)}")
                self._set_stat("low", f"Low-stock items\n{len(low)}")
            else:
                low = [m for m in mgr.inventory_status()
                       if m["current_stock_qty"] <= m["low_stock_threshold"]]
                self._set_stat("low", f"Low-stock items\n{len(low)}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            conn.close()

    def _set_stat(self, key: str, text: str) -> None:
        card = getattr(self, "_stat_cards", {}).get(key)
        if card is not None:
            card.setText(text)
