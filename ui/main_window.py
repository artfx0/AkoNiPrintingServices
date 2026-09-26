"""Main Window shell: modern SaaS layout (Rhombus reference style).

Structure:
  - Top App Header: Global search input, live alert notifications, user profile pill (avatar + name + role), and logout.
  - Left Sidebar: Clean white branded sidebar with AkoNi logo, icon-adorned nav items, active pill highlighting, and footer info.
  - Central Area: QStackedWidget hosting Dashboard and all business modules.
  - Interactive Navigation: Dashboard action links ('View full report >') automatically switch to the corresponding module.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem,
    QStackedWidget, QLabel, QPushButton, QLineEdit, QFrame, QMessageBox,
)
from PyQt6.QtCore import Qt, QSize

from database.database import get_connection

# Navigation items per role
ADMIN_NAV = [
    "Dashboard", "Customers", "Orders", "Payments", "Inventory",
    "Expenses", "Reports", "Backup", "Users",
]
STAFF_NAV = ["Dashboard", "Inventory"]

NAV_ICONS = {
    "Dashboard": "📊",
    "Customers": "👥",
    "Orders": "🛒",
    "Payments": "💳",
    "Inventory": "📦",
    "Expenses": "💸",
    "Reports": "📈",
    "Backup": "💾",
    "Users": "👤",
}


class MainWindow(QMainWindow):
    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.logout_requested = False
        self._is_admin = user.get("role") == "Admin"

        role_label = "Admin" if self._is_admin else "Staff"
        username = user.get("username", "")
        self.setWindowTitle(f"AkoNi Printing Services — {role_label} ({username})")
        self.resize(1280, 800)
        self.setMinimumSize(1080, 680)

        self._setup_ui()

    def _setup_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Top App Header (Search + User profile + Logout)
        header_widget = self._build_header()
        root_layout.addWidget(header_widget)

        # 2. Main Body: Left Sidebar + Central QStackedWidget
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        sidebar_widget = self._build_sidebar()
        body_layout.addWidget(sidebar_widget)

        self.stack = QStackedWidget()
        self.stack.setObjectName("MainContentStack")
        body_layout.addWidget(self.stack, 1)

        root_layout.addLayout(body_layout, 1)

        # 3. Populate Pages
        self._build_pages()

        # Connect navigation selection
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        if self.nav.count():
            self.nav.setCurrentRow(0)

        # Clear initial focus from search bar
        self.setFocus()

    # -- Top Header Bar ------------------------------------------------
    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("AppHeader")
        header.setFixedHeight(62)

        lay = QHBoxLayout(header)
        lay.setContentsMargins(20, 0, 24, 0)
        lay.setSpacing(16)
        lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Global search input (styled rounded input matching reference)
        self.search_input = QLineEdit()
        self.search_input.setObjectName("GlobalSearchBar")
        self.search_input.setPlaceholderText("🔍  Search orders, customers, inventory...")
        self.search_input.setFixedWidth(360)
        self.search_input.returnPressed.connect(self._handle_global_search)
        lay.addWidget(self.search_input)

        lay.addStretch(1)

        # Right Action Items: Help, Notification Bell, User Capsule, Logout
        right_box = QHBoxLayout()
        right_box.setSpacing(14)
        right_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Notification / Low stock bell button
        self.bell_btn = QPushButton("🔔")
        self.bell_btn.setObjectName("HeaderIconBtn")
        self.bell_btn.setToolTip("Inventory Alerts")
        self.bell_btn.clicked.connect(lambda: self.navigate_to_tab("Inventory"))
        right_box.addWidget(self.bell_btn)

        # Divider
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setObjectName("HeaderDivider")
        sep.setFixedSize(1, 24)
        right_box.addWidget(sep)

        # User Initials Avatar
        first = self.user.get("first_name", "")
        last = self.user.get("last_name", "")
        username = self.user.get("username", "admin")
        initials = (first[:1] + last[:1]).upper() if (first and last) else username[:2].upper()

        avatar = QLabel(initials)
        avatar.setObjectName("UserAvatar")
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_box.addWidget(avatar)

        # User details (Name + Role pill)
        user_info = QVBoxLayout()
        user_info.setSpacing(1)
        user_info.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        display_name = f"{first} {last}".strip() or username
        name_lbl = QLabel(display_name)
        name_lbl.setObjectName("HeaderUserName")

        role_lbl = QLabel(self.user.get("role", "Staff"))
        role_lbl.setObjectName("HeaderUserRole")

        user_info.addWidget(name_lbl)
        user_info.addWidget(role_lbl)
        right_box.addLayout(user_info)

        # Logout Button
        logout_btn = QPushButton("Logout")
        logout_btn.setObjectName("LogoutBtn")
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.clicked.connect(self.request_logout)
        right_box.addWidget(logout_btn)

        lay.addLayout(right_box)
        return header

    # -- Left Sidebar --------------------------------------------------
    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("SidebarContainer")
        sidebar.setFixedWidth(220)

        lay = QVBoxLayout(sidebar)
        lay.setContentsMargins(12, 18, 12, 18)
        lay.setSpacing(12)

        # Brand Logo Header
        brand_box = QHBoxLayout()
        brand_box.setSpacing(10)
        brand_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        brand_icon = QLabel("🖨️")
        brand_icon.setObjectName("BrandLogoIcon")
        brand_icon.setFixedSize(34, 34)
        brand_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_box.addWidget(brand_icon)

        brand_text_box = QVBoxLayout()
        brand_text_box.setSpacing(0)
        brand_title = QLabel("AkoNi")
        brand_title.setObjectName("BrandTitle")
        brand_sub = QLabel("Printing Services")
        brand_sub.setObjectName("BrandSub")
        brand_text_box.addWidget(brand_title)
        brand_text_box.addWidget(brand_sub)
        brand_box.addLayout(brand_text_box, 1)

        lay.addLayout(brand_box)

        # Sidebar Separator line
        sep = QFrame()
        sep.setObjectName("SidebarDivider")
        sep.setFixedHeight(1)
        lay.addWidget(sep)

        # Navigation List Widget
        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lay.addWidget(self.nav, 1)

        # Footer branding tag
        footer = QLabel("AkoNi Printing Services\nPOS & Management ERP")
        footer.setObjectName("SidebarFooter")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(footer)

        return sidebar

    # -- Pages Setup ---------------------------------------------------
    def _build_pages(self) -> None:
        nav_labels = ADMIN_NAV if self._is_admin else STAFF_NAV

        # Setup navigation items with icons
        for label in nav_labels:
            icon = NAV_ICONS.get(label, "●")
            item = QListWidgetItem(f" {icon}   {label}")
            item.setSizeHint(QSize(190, 42))
            self.nav.addItem(item)

        if self._is_admin:
            from auth.user_widget import UserWidget
            from backup.settings_widget import SettingsWidget
            from customers.customer_widget import CustomerWidget
            from expenses.expense_widget import ExpenseWidget
            from inventory.inventory_widget import InventoryWidget
            from payments.payment_widget import PaymentWidget
            from reports.dashboard_widget import DashboardWidget
            from reports.reports_widget import ReportsWidget
            from sales_orders.order_widget import OrderWidget

            self.dashboard_page = DashboardWidget(user=self.user)
            self.dashboard_page.navigation_requested.connect(self.navigate_to_tab)

            self.customer_page = CustomerWidget()
            self.order_page = OrderWidget(user=self.user)
            self.payment_page = PaymentWidget(user=self.user)
            self.inventory_page = InventoryWidget(user=self.user)
            self.expense_page = ExpenseWidget(user=self.user)
            self.reports_page = ReportsWidget()
            self.settings_page = SettingsWidget(user=self.user)
            self.users_page = UserWidget(current_user=self.user)

            self.stack.addWidget(self.dashboard_page)  # 0: Dashboard
            self.stack.addWidget(self.customer_page)   # 1: Customers
            self.stack.addWidget(self.order_page)      # 2: Orders
            self.stack.addWidget(self.payment_page)    # 3: Payments
            self.stack.addWidget(self.inventory_page)  # 4: Inventory
            self.stack.addWidget(self.expense_page)    # 5: Expenses
            self.stack.addWidget(self.reports_page)    # 6: Reports
            self.stack.addWidget(self.settings_page)   # 7: Backup
            self.stack.addWidget(self.users_page)      # 8: Users
        else:
            from inventory.inventory_widget import InventoryWidget
            from reports.dashboard_widget import DashboardWidget
            from ui.staff_dashboard import StaffDashboard

            self._backend = StaffDashboard(self.user)

            self.dashboard_page = DashboardWidget(user=self.user)
            self.dashboard_page.navigation_requested.connect(self.navigate_to_tab)
            self.inventory_page = InventoryWidget(user=self.user)

            self.stack.addWidget(self.dashboard_page)  # 0: Dashboard
            self.stack.addWidget(self.inventory_page)  # 1: Inventory

    # -- Interactive Navigation Handler --------------------------------
    def navigate_to_tab(self, tab_name: str) -> None:
        """Switch active page by module label (e.g. from Dashboard quick-links)."""
        labels = ADMIN_NAV if self._is_admin else STAFF_NAV
        if tab_name in labels:
            idx = labels.index(tab_name)
            self.nav.setCurrentRow(idx)

    def _handle_global_search(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            return
        # If user searches, navigate to Orders or Customers and fill search
        if self._is_admin:
            self.navigate_to_tab("Orders")
            if hasattr(self, "order_page") and hasattr(self.order_page, "search"):
                self.order_page.search.setText(query)

    def request_logout(self) -> None:
        from auth.session import Session
        Session.clear()
        self.logout_requested = True
        self.close()
