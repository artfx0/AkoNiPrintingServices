"""Settings Module Widget (Phase 1: Foundation & General Tab).

Admin-only configuration interface matching the AkoNi Printing Services
Design System (Rhombus/SaaS format).

Features:
  - Header: Module title + descriptive subtitle.
  - Horizontal tab navigation:
      1. General (Default active tab)
      2. Sales (Placeholder)
      3. Payments (Placeholder)
      4. Expenses (Placeholder)
      5. Fulfillment (Placeholder)
      6. User Access (Placeholder)
  - General Tab -> 'Business Information' card container with thin border:
      - Form fields: Business Name, Business Address, Contact Number,
        Email Address, Social / Facebook Contact, Invoice Payment Instructions,
        and Invoice Reminder.
      - Edit button (Secondary outlined button) toggling to Save / Cancel.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QTabWidget, QFrame, QScrollArea,
    QFormLayout, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QInputDialog, QComboBox,
)
from PyQt6.QtCore import Qt, QEvent

from settings.settings_manager import SettingsManager
from ui.icons import get_icon, get_action_icon, get_pixmap


class SettingsWidget(QWidget):
    """Admin-only Settings Module with tabbed configuration hierarchy."""

    def __init__(self, user: dict | None = None, parent=None):
        super().__init__(parent)
        self.user = user or {}

        # Admin-only access enforcement
        if (self.user.get("role") or "") != "Admin":
            raise PermissionError("Settings module is Admin-only.")

        self._is_editing = False

        # Root Layout matching page standards
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(18)

        # 1. Page Header (Title + Subtitle)
        header_lay = QVBoxLayout()
        header_lay.setSpacing(4)
        title = QLabel("Settings")
        title.setObjectName("ModuleHeaderTitle")
        sub = QLabel("Configure business information, sales policies, payment defaults, and system preferences.")
        sub.setObjectName("ModuleHeaderSub")
        header_lay.addWidget(title)
        header_lay.addWidget(sub)
        layout.addLayout(header_lay)

        # 2. Horizontal Tab Navigation
        self.tabs = QTabWidget()
        self.tabs.setObjectName("ModuleTabs")
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E2E8F0;
                background-color: #F8FAFC;
                border-radius: 12px;
                top: -1px;
            }
        """)

        # Add tabs
        self.general_tab = self._create_general_tab()
        self.sales_tab = self._create_sales_tab()
        self.payments_tab = self._create_payments_tab()
        self.expenses_tab = self._create_placeholder_tab(
            title="Expense Categories & Thresholds",
            icon_name="expenses",
            description="Manage operational expenditure classification, overhead alerts, and financial tracking limits."
        )
        self.fulfillment_tab = self._create_placeholder_tab(
            title="Fulfillment & Dispatch",
            icon_name="truck",
            description="Set default delivery addresses, local courier partner preferences, and packaging presets."
        )
        self.user_access_tab = self._create_placeholder_tab(
            title="User Access & Role Permissions",
            icon_name="users",
            description="Configure administrative privileges, staff operational boundaries, and audit logging options."
        )

        self.tabs.addTab(self.general_tab, "General")
        self.tabs.addTab(self.sales_tab, "Sales")
        self.tabs.addTab(self.payments_tab, "Payments")
        self.tabs.addTab(self.expenses_tab, "Expenses")
        self.tabs.addTab(self.fulfillment_tab, "Fulfillment")
        self.tabs.addTab(self.user_access_tab, "User Access")

        # Set 'General' as the default active tab
        self.tabs.setCurrentIndex(0)

        layout.addWidget(self.tabs, 1)

    # -----------------------------------------------------------------------
    # Tab 1: General (Business Information Section)
    # -----------------------------------------------------------------------
    def _create_general_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(16, 16, 16, 16)
        c_lay.setSpacing(14)

        # Business Information Card
        card = QFrame()
        card.setObjectName("ModuleCardContainer")
        card.setStyleSheet(
            "QFrame#ModuleCardContainer { background-color: #FFFFFF; border: 1px solid #E2E8F0; "
            "border-radius: 12px; }"
        )
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(22, 18, 22, 18)
        card_lay.setSpacing(12)

        # Section Title and Subtitle
        sec_header = QVBoxLayout()
        sec_header.setSpacing(2)
        sec_title = QLabel("Business Information")
        sec_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        sec_sub = QLabel("Primary company identity, public contact details, and invoice remittance instructions.")
        sec_sub.setStyleSheet("font-size: 12px; color: #64748B;")
        sec_header.addWidget(sec_title)
        sec_header.addWidget(sec_sub)
        card_lay.addLayout(sec_header)

        # Separator line
        sep = QFrame()
        sep.setObjectName("SidebarDivider")
        sep.setFixedHeight(1)
        card_lay.addWidget(sep)

        # Form Layout
        form = QFormLayout()
        form.setSpacing(10)
        form.setVerticalSpacing(10)
        form.setHorizontalSpacing(18)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        def make_label(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #334155;")
            return lbl

        # 1. Business Name
        self.business_name_edit = QLineEdit()
        self.business_name_edit.setPlaceholderText("e.g. AkoNi Printing Services")
        self.business_name_edit.setFixedHeight(34)
        form.addRow(make_label("Business Name *:"), self.business_name_edit)

        # 2. Business Address
        self.business_address_edit = QLineEdit()
        self.business_address_edit.setPlaceholderText("e.g. 124 Rizal St., Brgy. Poblacion, Makati City")
        self.business_address_edit.setFixedHeight(34)
        form.addRow(make_label("Business Address:"), self.business_address_edit)

        # 3. Contact Number
        self.contact_number_edit = QLineEdit()
        self.contact_number_edit.setPlaceholderText("e.g. 0917-123-4567 / (02) 8123-4567")
        self.contact_number_edit.setFixedHeight(34)
        form.addRow(make_label("Contact Number:"), self.contact_number_edit)

        # 4. Email Address
        self.email_address_edit = QLineEdit()
        self.email_address_edit.setPlaceholderText("e.g. info@akoniprinting.com")
        self.email_address_edit.setFixedHeight(34)
        form.addRow(make_label("Email Address:"), self.email_address_edit)

        # 5. Social / Facebook Contact
        self.social_contact_edit = QLineEdit()
        self.social_contact_edit.setPlaceholderText("e.g. facebook.com/AkoNiPrintingServices or @akoniprinting")
        self.social_contact_edit.setFixedHeight(34)
        form.addRow(make_label("Social / Facebook Contact:"), self.social_contact_edit)

        # 6. Invoice Payment Instructions (textarea)
        self.payment_instructions_edit = QTextEdit()
        self.payment_instructions_edit.setPlaceholderText(
            "Instructions printed on customer invoices (e.g. GCash number, bank accounts, payment terms)..."
        )
        self.payment_instructions_edit.setFixedHeight(68)
        form.addRow(make_label("Invoice Payment Instructions:"), self.payment_instructions_edit)

        # 7. Invoice Reminder (textarea)
        self.invoice_reminder_edit = QTextEdit()
        self.invoice_reminder_edit.setPlaceholderText(
            "Terms or reminders printed on invoices (e.g. Turnaround times, proof approval policy, pickup rules)..."
        )
        self.invoice_reminder_edit.setFixedHeight(60)
        form.addRow(make_label("Invoice Reminder:"), self.invoice_reminder_edit)

        card_lay.addLayout(form)

        # Action Buttons Row at bottom
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_box.setContentsMargins(0, 4, 0, 0)

        # Edit button (Secondary outlined button)
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setObjectName("SecondaryBtn")
        self.edit_btn.setIcon(get_action_icon("edit", "secondary", 15))
        self.edit_btn.setFixedHeight(34)
        self.edit_btn.setFixedWidth(100)
        self.edit_btn.clicked.connect(self._enable_editing)
        btn_box.addWidget(self.edit_btn)

        # Save Changes (Primary gold button) - initially hidden
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.setIcon(get_action_icon("check", "primary", 15))
        self.save_btn.setFixedHeight(34)
        self.save_btn.setFixedWidth(130)
        self.save_btn.clicked.connect(self._save_business_info)
        self.save_btn.setVisible(False)
        btn_box.addWidget(self.save_btn)

        # Cancel button (Secondary button) - initially hidden
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("SecondaryBtn")
        self.cancel_btn.setFixedHeight(34)
        self.cancel_btn.setFixedWidth(90)
        self.cancel_btn.clicked.connect(self._cancel_editing)
        self.cancel_btn.setVisible(False)
        btn_box.addWidget(self.cancel_btn)

        btn_box.addStretch(1)
        card_lay.addLayout(btn_box)

        c_lay.addWidget(card)
        c_lay.addStretch(1)

        scroll.setWidget(container)

        # Load values into form and set initial read-only state
        self._load_saved_values()
        self._set_form_editable(False)

        return scroll

    # -----------------------------------------------------------------------
    # Tab 2: Sales (Product Reference Section)
    # -----------------------------------------------------------------------
    def _create_sales_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(16, 16, 16, 16)
        c_lay.setSpacing(14)

        # Product Reference Card
        card = QFrame()
        card.setObjectName("ModuleCardContainer")
        card.setStyleSheet(
            "QFrame#ModuleCardContainer { background-color: #FFFFFF; border: 1px solid #E2E8F0; "
            "border-radius: 12px; }"
        )
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(22, 18, 22, 18)
        card_lay.setSpacing(14)

        # Section Title and Subtitle
        sec_header = QVBoxLayout()
        sec_header.setSpacing(2)
        sec_title = QLabel("Product Reference")
        sec_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        sec_sub = QLabel("Standard product reference catalog and active packaging categories for sales orders.")
        sec_sub.setStyleSheet("font-size: 12px; color: #64748B;")
        sec_header.addWidget(sec_title)
        sec_header.addWidget(sec_sub)
        card_lay.addLayout(sec_header)

        # Separator line
        sep = QFrame()
        sep.setObjectName("SidebarDivider")
        sep.setFixedHeight(1)
        card_lay.addWidget(sep)

        # Table: Columns (Name, Status, Actions)
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(3)
        self.products_table.setHorizontalHeaderLabels(["Name", "Status", "Actions"])
        self.products_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.products_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.products_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.products_table.verticalHeader().setVisible(False)
        self.products_table.verticalHeader().setDefaultSectionSize(42)
        self.products_table.setAlternatingRowColors(True)

        header = self.products_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 140)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(2, 210)

        card_lay.addWidget(self.products_table)

        # Below Table: Input field + Solid gold 'Add' button
        add_box = QHBoxLayout()
        add_box.setSpacing(10)
        add_box.setContentsMargins(0, 4, 0, 0)

        self.new_product_input = QLineEdit()
        self.new_product_input.setPlaceholderText("New product name")
        self.new_product_input.setFixedHeight(36)
        self.new_product_input.returnPressed.connect(self._add_product)
        add_box.addWidget(self.new_product_input, 1)

        self.add_product_btn = QPushButton("Add")
        self.add_product_btn.setIcon(get_action_icon("plus", "primary", 15))
        self.add_product_btn.setFixedHeight(36)
        self.add_product_btn.setFixedWidth(90)
        self.add_product_btn.clicked.connect(self._add_product)
        add_box.addWidget(self.add_product_btn)

        card_lay.addLayout(add_box)

        c_lay.addWidget(card)
        c_lay.addStretch(1)

        scroll.setWidget(container)

        # Populate rows
        self._load_products()

        return scroll

    def _load_products(self) -> None:
        """Populate the Product Reference table with saved/mock products."""
        self.products = SettingsManager.load_product_references()
        self.products_table.clearContents()
        self.products_table.setRowCount(len(self.products))

        for r, prod in enumerate(self.products):
            # 1. Name
            name_text = prod.get("name", "")
            name_item = QTableWidgetItem(f"  {name_text}")
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.products_table.setItem(r, 0, name_item)

            # 2. Status Badge (light green rounded badge)
            status_text = prod.get("status", "Active")
            self.products_table.setCellWidget(r, 1, self._create_status_badge(status_text))

            # 3. Actions (Edit & Archive outlined buttons)
            self.products_table.setCellWidget(r, 2, self._create_action_buttons(r))

        # Size table comfortably so no internal scrollbar appears
        row_h = self.products_table.verticalHeader().defaultSectionSize() or 42
        header_h = self.products_table.horizontalHeader().height() or 42
        table_h = header_h + (len(self.products) * row_h) + 8
        self.products_table.setFixedHeight(max(94, min(420, table_h)))

    def _create_status_badge(self, status: str) -> QWidget:
        """Return a centered light green rounded status pill widget."""
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(container)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        badge = QLabel(f"● {status}")
        badge.setObjectName("StatusPill")
        badge.setProperty("status", "active" if status.lower() == "active" else "other")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.style().unpolish(badge)
        badge.style().polish(badge)
        lay.addWidget(badge)
        return container

    def _create_action_buttons(self, row_idx: int) -> QWidget:
        """Return Edit and Archive outlined secondary buttons."""
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(container)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Edit button (outlined SecondaryBtn)
        edit_btn = QPushButton("Edit")
        edit_btn.setObjectName("SecondaryBtn")
        edit_btn.setIcon(get_action_icon("edit", "secondary", 13))
        edit_btn.setFixedHeight(28)
        edit_btn.setFixedWidth(72)
        edit_btn.clicked.connect(lambda _, idx=row_idx: self._edit_product(idx))
        lay.addWidget(edit_btn)

        # Archive / Restore button (outlined SecondaryBtn)
        is_active = (self.products[row_idx].get("status", "Active") == "Active")
        archive_btn = QPushButton("Archive" if is_active else "Restore")
        archive_btn.setObjectName("SecondaryBtn")
        archive_btn.setIcon(get_action_icon("archive", "secondary", 13))
        archive_btn.setFixedHeight(28)
        archive_btn.setFixedWidth(82)
        archive_btn.clicked.connect(lambda _, idx=row_idx: self._toggle_archive_product(idx))
        lay.addWidget(archive_btn)

        return container

    def _add_product(self) -> None:
        """Add a new product reference from the bottom input field."""
        name = self.new_product_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Product name cannot be empty.")
            self.new_product_input.setFocus()
            return

        self.products.append({"name": name, "status": "Active"})
        SettingsManager.save_product_references(self.products)
        self.new_product_input.clear()
        self._load_products()

    def _edit_product(self, idx: int) -> None:
        """Edit the product name via input dialog."""
        if idx < 0 or idx >= len(self.products):
            return
        current_name = self.products[idx].get("name", "")
        new_name, ok = QInputDialog.getText(
            self, "Edit Product Reference", "Update product name:", text=current_name
        )
        if ok and new_name.strip():
            self.products[idx]["name"] = new_name.strip()
            SettingsManager.save_product_references(self.products)
            self._load_products()

    def _toggle_archive_product(self, idx: int) -> None:
        """Toggle active/archived status for the selected product."""
        if idx < 0 or idx >= len(self.products):
            return
        curr = self.products[idx].get("status", "Active")
        new_status = "Archived" if curr == "Active" else "Active"
        self.products[idx]["status"] = new_status
        SettingsManager.save_product_references(self.products)
        self._load_products()

    # -----------------------------------------------------------------------
    # Tab 3: Payments (Payment Methods & Accounts Sections)
    # -----------------------------------------------------------------------
    def _create_payments_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(16, 16, 16, 16)
        c_lay.setSpacing(18)

        # ===================================================================
        # Section 1: Payment Methods Section
        # ===================================================================
        methods_card = QFrame()
        methods_card.setObjectName("ModuleCardContainer")
        methods_card.setStyleSheet(
            "QFrame#ModuleCardContainer { background-color: #FFFFFF; border: 1px solid #E2E8F0; "
            "border-radius: 12px; }"
        )
        m_lay = QVBoxLayout(methods_card)
        m_lay.setContentsMargins(22, 18, 22, 18)
        m_lay.setSpacing(14)

        # Header
        m_header = QVBoxLayout()
        m_header.setSpacing(2)
        m_title = QLabel("Payment Methods")
        m_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        m_sub = QLabel("Supported customer remittance channels and tender options accepted at checkout.")
        m_sub.setStyleSheet("font-size: 12px; color: #64748B;")
        m_header.addWidget(m_title)
        m_header.addWidget(m_sub)
        m_lay.addLayout(m_header)

        # Separator line
        sep1 = QFrame()
        sep1.setObjectName("SidebarDivider")
        sep1.setFixedHeight(1)
        m_lay.addWidget(sep1)

        # Table: Name, Status, Actions
        self.methods_table = QTableWidget()
        self.methods_table.setColumnCount(3)
        self.methods_table.setHorizontalHeaderLabels(["Name", "Status", "Actions"])
        self.methods_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.methods_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.methods_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.methods_table.verticalHeader().setVisible(False)
        self.methods_table.verticalHeader().setDefaultSectionSize(42)
        self.methods_table.setAlternatingRowColors(True)

        m_hdr = self.methods_table.horizontalHeader()
        m_hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        m_hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        m_hdr.resizeSection(1, 140)
        m_hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        m_hdr.resizeSection(2, 210)

        m_lay.addWidget(self.methods_table)

        # Below Table: Input field + Solid gold 'Add' button
        m_add_box = QHBoxLayout()
        m_add_box.setSpacing(10)
        m_add_box.setContentsMargins(0, 4, 0, 0)

        self.new_method_input = QLineEdit()
        self.new_method_input.setPlaceholderText("New payment method name")
        self.new_method_input.setFixedHeight(36)
        self.new_method_input.returnPressed.connect(self._add_payment_method)
        m_add_box.addWidget(self.new_method_input, 1)

        self.add_method_btn = QPushButton("Add")
        self.add_method_btn.setIcon(get_action_icon("plus", "primary", 15))
        self.add_method_btn.setFixedHeight(36)
        self.add_method_btn.setFixedWidth(90)
        self.add_method_btn.clicked.connect(self._add_payment_method)
        m_add_box.addWidget(self.add_method_btn)

        m_lay.addLayout(m_add_box)
        c_lay.addWidget(methods_card)

        # ===================================================================
        # Section 2: Payment Accounts Section
        # ===================================================================
        accounts_card = QFrame()
        accounts_card.setObjectName("ModuleCardContainer")
        accounts_card.setStyleSheet(
            "QFrame#ModuleCardContainer { background-color: #FFFFFF; border: 1px solid #E2E8F0; "
            "border-radius: 12px; }"
        )
        a_lay = QVBoxLayout(accounts_card)
        a_lay.setContentsMargins(22, 18, 22, 18)
        a_lay.setSpacing(14)

        # Header
        a_header = QVBoxLayout()
        a_header.setSpacing(2)
        a_title = QLabel("Payment Accounts")
        a_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        a_sub = QLabel("Configured receiving accounts, merchant details, and automated invoice routing.")
        a_sub.setStyleSheet("font-size: 12px; color: #64748B;")
        a_header.addWidget(a_title)
        a_header.addWidget(a_sub)
        a_lay.addLayout(a_header)

        # Separator line
        sep2 = QFrame()
        sep2.setObjectName("SidebarDivider")
        sep2.setFixedHeight(1)
        a_lay.addWidget(sep2)

        # Table: Method, Label, Account Name, Number/Details, Invoice, Order, Status, Actions
        self.accounts_table = QTableWidget()
        acc_headers = ["Method", "Label", "Account Name", "Number/Details", "Invoice", "Order", "Status", "Actions"]
        self.accounts_table.setColumnCount(len(acc_headers))
        self.accounts_table.setHorizontalHeaderLabels(acc_headers)
        self.accounts_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.accounts_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.accounts_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.accounts_table.verticalHeader().setVisible(False)
        self.accounts_table.verticalHeader().setDefaultSectionSize(42)
        self.accounts_table.setAlternatingRowColors(True)

        a_hdr = self.accounts_table.horizontalHeader()
        a_hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        a_hdr.resizeSection(0, 110)
        a_hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        a_hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        a_hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        a_hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        a_hdr.resizeSection(4, 75)
        a_hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        a_hdr.resizeSection(5, 75)
        a_hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        a_hdr.resizeSection(6, 95)
        a_hdr.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        a_hdr.resizeSection(7, 110)

        self.accounts_table.setFixedHeight(120)

        # Empty table placeholder: "No payment accounts yet" in light gray
        self.no_accounts_label = QLabel("No payment accounts yet", self.accounts_table.viewport())
        self.no_accounts_label.setObjectName("NoAccountsPlaceholder")
        self.no_accounts_label.setStyleSheet("color: #94A3B8; font-size: 13px; font-style: italic; background: transparent;")
        self.no_accounts_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.accounts_table.viewport().installEventFilter(self)

        a_lay.addWidget(self.accounts_table)

        # Form below the empty table
        form_box = QVBoxLayout()
        form_box.setSpacing(10)
        form_box.setContentsMargins(0, 8, 0, 0)

        form_subhead = QLabel("Add New Payment Account")
        form_subhead.setStyleSheet("font-size: 13px; font-weight: bold; color: #0F172A;")
        form_box.addWidget(form_subhead)

        form = QFormLayout()
        form.setSpacing(10)
        form.setVerticalSpacing(10)
        form.setHorizontalSpacing(18)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        def make_label(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #334155;")
            return lbl

        # 1. Dropdown for 'Payment Method'
        self.account_method_combo = QComboBox()
        self.account_method_combo.setFixedHeight(34)
        form.addRow(make_label("Payment Method *:"), self.account_method_combo)

        # 2. Text input for 'Display Label'
        self.account_label_input = QLineEdit()
        self.account_label_input.setPlaceholderText("Display Label (e.g. Primary GCash / Store QR)")
        self.account_label_input.setFixedHeight(34)
        form.addRow(make_label("Display Label *:"), self.account_label_input)

        # 3. Text input for 'Account Name'
        self.account_name_input = QLineEdit()
        self.account_name_input.setPlaceholderText("Account Name (e.g. Juan Dela Cruz / AkoNi Printing)")
        self.account_name_input.setFixedHeight(34)
        form.addRow(make_label("Account Name *:"), self.account_name_input)

        form_box.addLayout(form)

        # Action button to save new account
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 4, 0, 0)

        self.add_account_btn = QPushButton("Add Account")
        self.add_account_btn.setIcon(get_action_icon("plus", "primary", 15))
        self.add_account_btn.setFixedHeight(34)
        self.add_account_btn.setFixedWidth(130)
        self.add_account_btn.clicked.connect(self._add_payment_account)
        btn_row.addWidget(self.add_account_btn)
        btn_row.addStretch(1)

        form_box.addLayout(btn_row)
        a_lay.addLayout(form_box)

        c_lay.addWidget(accounts_card)
        c_lay.addStretch(1)

        scroll.setWidget(container)

        # Populate tables
        self._load_payment_methods()
        self._load_payment_accounts()

        return scroll

    def eventFilter(self, watched, event):
        """Keep empty table placeholder label centered over viewport."""
        if hasattr(self, "accounts_table") and watched == self.accounts_table.viewport():
            if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
                if hasattr(self, "no_accounts_label"):
                    self.no_accounts_label.resize(self.accounts_table.viewport().size())
        return super().eventFilter(watched, event)

    # -----------------------------------------------------------------------
    # Payment Methods Logic
    # -----------------------------------------------------------------------
    def _load_payment_methods(self) -> None:
        """Populate the Payment Methods table with mock/persisted rows."""
        self.payment_methods = SettingsManager.load_payment_methods()
        self.methods_table.clearContents()
        self.methods_table.setRowCount(len(self.payment_methods))

        for r, m in enumerate(self.payment_methods):
            name_text = m.get("name", "")
            name_item = QTableWidgetItem(f"  {name_text}")
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.methods_table.setItem(r, 0, name_item)

            status_text = m.get("status", "Active")
            self.methods_table.setCellWidget(r, 1, self._create_status_badge(status_text))
            self.methods_table.setCellWidget(r, 2, self._create_method_action_buttons(r))

        row_h = self.methods_table.verticalHeader().defaultSectionSize() or 42
        hdr_h = self.methods_table.horizontalHeader().height() or 42
        table_h = hdr_h + (len(self.payment_methods) * row_h) + 8
        self.methods_table.setFixedHeight(max(94, min(360, table_h)))

        # Update the Payment Method combo in the Accounts form below
        if hasattr(self, "account_method_combo"):
            current_choice = self.account_method_combo.currentText()
            self.account_method_combo.clear()
            for m in self.payment_methods:
                if m.get("status", "Active") == "Active":
                    self.account_method_combo.addItem(m.get("name", ""))
            idx = self.account_method_combo.findText(current_choice)
            if idx >= 0:
                self.account_method_combo.setCurrentIndex(idx)

    def _create_method_action_buttons(self, row_idx: int) -> QWidget:
        """Outlined Edit and Archive buttons for payment methods."""
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(container)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        edit_btn = QPushButton("Edit")
        edit_btn.setObjectName("SecondaryBtn")
        edit_btn.setIcon(get_action_icon("edit", "secondary", 13))
        edit_btn.setFixedHeight(28)
        edit_btn.setFixedWidth(72)
        edit_btn.clicked.connect(lambda _, idx=row_idx: self._edit_payment_method(idx))
        lay.addWidget(edit_btn)

        is_active = (self.payment_methods[row_idx].get("status", "Active") == "Active")
        archive_btn = QPushButton("Archive" if is_active else "Restore")
        archive_btn.setObjectName("SecondaryBtn")
        archive_btn.setIcon(get_action_icon("archive", "secondary", 13))
        archive_btn.setFixedHeight(28)
        archive_btn.setFixedWidth(82)
        archive_btn.clicked.connect(lambda _, idx=row_idx: self._toggle_archive_payment_method(idx))
        lay.addWidget(archive_btn)

        return container

    def _add_payment_method(self) -> None:
        name = self.new_method_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Payment method name cannot be empty.")
            self.new_method_input.setFocus()
            return

        self.payment_methods.append({"name": name, "status": "Active"})
        SettingsManager.save_payment_methods(self.payment_methods)
        self.new_method_input.clear()
        self._load_payment_methods()

    def _edit_payment_method(self, idx: int) -> None:
        if idx < 0 or idx >= len(self.payment_methods):
            return
        curr_name = self.payment_methods[idx].get("name", "")
        new_name, ok = QInputDialog.getText(
            self, "Edit Payment Method", "Update payment method name:", text=curr_name
        )
        if ok and new_name.strip():
            self.payment_methods[idx]["name"] = new_name.strip()
            SettingsManager.save_payment_methods(self.payment_methods)
            self._load_payment_methods()

    def _toggle_archive_payment_method(self, idx: int) -> None:
        if idx < 0 or idx >= len(self.payment_methods):
            return
        curr = self.payment_methods[idx].get("status", "Active")
        new_status = "Archived" if curr == "Active" else "Active"
        self.payment_methods[idx]["status"] = new_status
        SettingsManager.save_payment_methods(self.payment_methods)
        self._load_payment_methods()

    # -----------------------------------------------------------------------
    # Payment Accounts Logic
    # -----------------------------------------------------------------------
    def _load_payment_accounts(self) -> None:
        """Populate the Payment Accounts table or show the empty placeholder."""
        self.payment_accounts = SettingsManager.load_payment_accounts()
        self.accounts_table.clearContents()
        self.accounts_table.setRowCount(len(self.payment_accounts))

        if not self.payment_accounts:
            self.no_accounts_label.setVisible(True)
            self.no_accounts_label.resize(self.accounts_table.viewport().size())
            self.accounts_table.setFixedHeight(120)
        else:
            self.no_accounts_label.setVisible(False)
            for r, acc in enumerate(self.payment_accounts):
                self.accounts_table.setItem(r, 0, QTableWidgetItem(f"  {acc.get('method', '')}"))
                self.accounts_table.setItem(r, 1, QTableWidgetItem(str(acc.get('label', ''))))
                self.accounts_table.setItem(r, 2, QTableWidgetItem(str(acc.get('account_name', ''))))
                self.accounts_table.setItem(r, 3, QTableWidgetItem(str(acc.get('number_details', '—'))))
                self.accounts_table.setItem(r, 4, QTableWidgetItem(str(acc.get('invoice', 'Yes'))))
                self.accounts_table.setItem(r, 5, QTableWidgetItem(str(acc.get('order', 'Yes'))))
                self.accounts_table.setCellWidget(r, 6, self._create_status_badge(acc.get('status', 'Active')))
                self.accounts_table.setCellWidget(r, 7, self._create_account_action_buttons(r))

            row_h = self.accounts_table.verticalHeader().defaultSectionSize() or 42
            hdr_h = self.accounts_table.horizontalHeader().height() or 42
            table_h = hdr_h + (len(self.payment_accounts) * row_h) + 8
            self.accounts_table.setFixedHeight(max(120, min(360, table_h)))

    def _create_account_action_buttons(self, row_idx: int) -> QWidget:
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(container)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(6)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        del_btn = QPushButton("Remove")
        del_btn.setObjectName("SecondaryBtn")
        del_btn.setIcon(get_action_icon("trash", "secondary", 13))
        del_btn.setFixedHeight(28)
        del_btn.setFixedWidth(84)
        del_btn.clicked.connect(lambda _, idx=row_idx: self._remove_payment_account(idx))
        lay.addWidget(del_btn)
        return container

    def _remove_payment_account(self, idx: int) -> None:
        if idx < 0 or idx >= len(self.payment_accounts):
            return
        self.payment_accounts.pop(idx)
        SettingsManager.save_payment_accounts(self.payment_accounts)
        self._load_payment_accounts()

    def _add_payment_account(self) -> None:
        method = self.account_method_combo.currentText().strip()
        label = self.account_label_input.text().strip()
        name = self.account_name_input.text().strip()

        if not label:
            QMessageBox.warning(self, "Validation Error", "Display Label is required.")
            self.account_label_input.setFocus()
            return
        if not name:
            QMessageBox.warning(self, "Validation Error", "Account Name is required.")
            self.account_name_input.setFocus()
            return

        new_acc = {
            "method": method or "GCash",
            "label": label,
            "account_name": name,
            "number_details": "—",
            "invoice": "Yes",
            "order": "Yes",
            "status": "Active",
        }
        self.payment_accounts.append(new_acc)
        SettingsManager.save_payment_accounts(self.payment_accounts)
        self.account_label_input.clear()
        self.account_name_input.clear()
        self._load_payment_accounts()



    # -----------------------------------------------------------------------
    # Placeholder Tabs Generator
    # -----------------------------------------------------------------------
    def _create_placeholder_tab(self, title: str, icon_name: str, description: str) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background-color: transparent;")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(16, 16, 16, 16)

        card = QFrame()
        card.setObjectName("ModuleCardContainer")
        card.setStyleSheet(
            "QFrame#ModuleCardContainer { background-color: #FFFFFF; border: 1px solid #E2E8F0; "
            "border-radius: 12px; }"
        )
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(36, 40, 36, 40)
        card_lay.setSpacing(12)
        card_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(52, 52)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("background-color: #FEF3C7; border-radius: 26px;")
        icon_lbl.setPixmap(get_pixmap(icon_name, color="#B45309", size=22))
        card_lay.addWidget(icon_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        card_lay.addWidget(title_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setStyleSheet("font-size: 13px; color: #64748B;")
        desc_lbl.setFixedWidth(480)
        card_lay.addWidget(desc_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        badge_lbl = QLabel("Configuration section planned for next phase")
        badge_lbl.setStyleSheet(
            "font-size: 11px; font-weight: 600; color: #94A3B8; "
            "background-color: #F8FAFC; border: 1px solid #E2E8F0; "
            "border-radius: 12px; padding: 4px 14px; margin-top: 6px;"
        )
        card_lay.addWidget(badge_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        lay.addWidget(card)
        lay.addStretch(1)
        return panel

    # -----------------------------------------------------------------------
    # Business Info Form State & Logic
    # -----------------------------------------------------------------------
    def _load_saved_values(self) -> None:
        data = SettingsManager.load_business_info()
        self.business_name_edit.setText(data.get("business_name", ""))
        self.business_address_edit.setText(data.get("business_address", ""))
        self.contact_number_edit.setText(data.get("contact_number", ""))
        self.email_address_edit.setText(data.get("email_address", ""))
        self.social_contact_edit.setText(data.get("social_contact", ""))
        self.payment_instructions_edit.setPlainText(data.get("payment_instructions", ""))
        self.invoice_reminder_edit.setPlainText(data.get("invoice_reminder", ""))

    def _set_form_editable(self, editable: bool) -> None:
        self._is_editing = editable
        for widget in (
            self.business_name_edit,
            self.business_address_edit,
            self.contact_number_edit,
            self.email_address_edit,
            self.social_contact_edit,
            self.payment_instructions_edit,
            self.invoice_reminder_edit,
        ):
            widget.setReadOnly(not editable)

        self.edit_btn.setVisible(not editable)
        self.save_btn.setVisible(editable)
        self.cancel_btn.setVisible(editable)

    def _enable_editing(self) -> None:
        self._set_form_editable(True)
        self.business_name_edit.setFocus()

    def _cancel_editing(self) -> None:
        self._load_saved_values()
        self._set_form_editable(False)

    def _save_business_info(self) -> None:
        name = self.business_name_edit.text().strip()
        if not name:
            QMessageBox.warning(
                self, "Validation Error", "Business Name is required and cannot be empty."
            )
            self.business_name_edit.setFocus()
            return

        payload = {
            "business_name": name,
            "business_address": self.business_address_edit.text().strip(),
            "contact_number": self.contact_number_edit.text().strip(),
            "email_address": self.email_address_edit.text().strip(),
            "social_contact": self.social_contact_edit.text().strip(),
            "payment_instructions": self.payment_instructions_edit.toPlainText().strip(),
            "invoice_reminder": self.invoice_reminder_edit.toPlainText().strip(),
        }

        try:
            SettingsManager.save_business_info(payload)
            self._set_form_editable(False)
            QMessageBox.information(
                self,
                "Settings Saved",
                "Business information has been updated successfully."
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to save settings:\n{exc}")
