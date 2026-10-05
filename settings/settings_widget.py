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
    QDialog, QSizePolicy,
)
from PyQt6.QtCore import Qt, QEvent

from settings.settings_manager import SettingsManager
from ui.icons import get_icon, get_action_icon, get_pixmap


class ExpenseAccountDialog(QDialog):
    """Dialog to create or edit an expense account."""

    def __init__(self, parent=None, account: dict | None = None):
        super().__init__(parent)
        self._is_edit = account is not None
        self.setWindowTitle("Edit Expense Account" if self._is_edit else "Add Expense Account")
        self.setMinimumWidth(400)
        data = account or {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Edit Expense Account" if self._is_edit else "Add New Expense Account")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        sub = QLabel("Configure account ledger code and descriptive category title.")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(title)
        layout.addWidget(sub)

        form = QFormLayout()
        form.setSpacing(10)
        form.setVerticalSpacing(10)
        form.setHorizontalSpacing(16)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        def make_lbl(txt: str) -> QLabel:
            lbl = QLabel(txt)
            lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #334155;")
            return lbl

        self.code_edit = QLineEdit(data.get("code", ""))
        self.code_edit.setPlaceholderText("e.g. 401 (Optional)")
        self.code_edit.setFixedHeight(34)
        form.addRow(make_lbl("Account Code:"), self.code_edit)

        self.name_edit = QLineEdit(data.get("name", ""))
        self.name_edit.setPlaceholderText("e.g. Office Supplies")
        self.name_edit.setFixedHeight(34)
        form.addRow(make_lbl("Account Name *:"), self.name_edit)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        btns.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.setFixedHeight(34)
        cancel_btn.setFixedWidth(90)
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)

        save_btn = QPushButton("Save Account" if self._is_edit else "Add Account")
        save_btn.setIcon(get_action_icon("check", "primary", 15))
        save_btn.setFixedHeight(34)
        save_btn.setFixedWidth(120)
        save_btn.clicked.connect(self._on_save)
        btns.addWidget(save_btn)

        layout.addLayout(btns)

    def _on_save(self) -> None:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Account Name is required.")
            self.name_edit.setFocus()
            return
        self.accept()

    def get_data(self) -> tuple[str, str]:
        return self.code_edit.text().strip(), self.name_edit.text().strip()


class EditAdminDialog(QDialog):
    """Dialog to edit administrator account name and username."""

    def __init__(self, parent=None, admin_data: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Admin Account")
        self.setMinimumWidth(400)
        data = admin_data or {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Edit Administrator Account")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        sub = QLabel("Update administrator display identity and username handle.")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(title)
        layout.addWidget(sub)

        form = QFormLayout()
        form.setSpacing(10)
        form.setVerticalSpacing(10)
        form.setHorizontalSpacing(16)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        def make_lbl(txt: str) -> QLabel:
            lbl = QLabel(txt)
            lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #334155;")
            return lbl

        self.name_edit = QLineEdit(data.get("name", ""))
        self.name_edit.setPlaceholderText("e.g. Earth Justin Anne Lim")
        self.name_edit.setFixedHeight(34)
        form.addRow(make_lbl("Full Name *:"), self.name_edit)

        self.username_edit = QLineEdit(data.get("username", ""))
        self.username_edit.setPlaceholderText("e.g. earth")
        self.username_edit.setFixedHeight(34)
        form.addRow(make_lbl("Username *:"), self.username_edit)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        btns.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.setFixedHeight(34)
        cancel_btn.setFixedWidth(90)
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)

        save_btn = QPushButton("Save Changes")
        save_btn.setIcon(get_action_icon("check", "primary", 15))
        save_btn.setFixedHeight(34)
        save_btn.setFixedWidth(130)
        save_btn.clicked.connect(self._on_save)
        btns.addWidget(save_btn)

        layout.addLayout(btns)

    def _on_save(self) -> None:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Full Name is required.")
            self.name_edit.setFocus()
            return
        if not self.username_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Username is required.")
            self.username_edit.setFocus()
            return
        self.accept()

    def get_data(self) -> tuple[str, str]:
        return self.name_edit.text().strip(), self.username_edit.text().strip().lstrip("@")


class ChangeAdminPasswordDialog(QDialog):
    """Dialog to update administrator password credentials."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Change Admin Password")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Change Administrator Password")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        sub = QLabel("Update security credentials for root administrative access.")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(title)
        layout.addWidget(sub)

        form = QFormLayout()
        form.setSpacing(10)
        form.setVerticalSpacing(10)
        form.setHorizontalSpacing(16)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        def make_lbl(txt: str) -> QLabel:
            lbl = QLabel(txt)
            lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #334155;")
            return lbl

        self.current_pw = QLineEdit()
        self.current_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.current_pw.setPlaceholderText("Current password")
        self.current_pw.setFixedHeight(34)
        form.addRow(make_lbl("Current Password:"), self.current_pw)

        self.new_pw = QLineEdit()
        self.new_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pw.setPlaceholderText("New password")
        self.new_pw.setFixedHeight(34)
        form.addRow(make_lbl("New Password *:"), self.new_pw)

        self.confirm_pw = QLineEdit()
        self.confirm_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pw.setPlaceholderText("Confirm new password")
        self.confirm_pw.setFixedHeight(34)
        form.addRow(make_lbl("Confirm Password *:"), self.confirm_pw)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        btns.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.setFixedHeight(34)
        cancel_btn.setFixedWidth(90)
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)

        save_btn = QPushButton("Update Password")
        save_btn.setIcon(get_action_icon("check", "primary", 15))
        save_btn.setFixedHeight(34)
        save_btn.setFixedWidth(150)
        save_btn.clicked.connect(self._on_save)
        btns.addWidget(save_btn)

        layout.addLayout(btns)

    def _on_save(self) -> None:
        new_val = self.new_pw.text().strip()
        conf_val = self.confirm_pw.text().strip()
        if not new_val:
            QMessageBox.warning(self, "Validation Error", "New password cannot be empty.")
            self.new_pw.setFocus()
            return
        if new_val != conf_val:
            QMessageBox.warning(self, "Validation Error", "Passwords do not match.")
            self.confirm_pw.setFocus()
            return
        self.accept()


class StaffAccountDialog(QDialog):
    """Dialog to add or edit a staff account."""

    def __init__(self, parent=None, staff: dict | None = None):
        super().__init__(parent)
        self._is_edit = staff is not None
        self.setWindowTitle("Edit Staff Account" if self._is_edit else "Add New Staff Account")
        self.setMinimumWidth(400)
        data = staff or {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Edit Staff Account" if self._is_edit else "Add New Staff Account")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        sub = QLabel("Configure employee identification and POS login credentials.")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(title)
        layout.addWidget(sub)

        form = QFormLayout()
        form.setSpacing(10)
        form.setVerticalSpacing(10)
        form.setHorizontalSpacing(16)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        def make_lbl(txt: str) -> QLabel:
            lbl = QLabel(txt)
            lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #334155;")
            return lbl

        self.name_edit = QLineEdit(data.get("name", ""))
        self.name_edit.setPlaceholderText("e.g. Carlo Reyes")
        self.name_edit.setFixedHeight(34)
        form.addRow(make_lbl("Staff Name *:"), self.name_edit)

        self.username_edit = QLineEdit(data.get("username", ""))
        self.username_edit.setPlaceholderText("e.g. dev_staff")
        self.username_edit.setFixedHeight(34)
        form.addRow(make_lbl("Username *:"), self.username_edit)

        if not self._is_edit:
            self.pw_edit = QLineEdit()
            self.pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.pw_edit.setPlaceholderText("Initial account password (Optional)")
            self.pw_edit.setFixedHeight(34)
            form.addRow(make_lbl("Password:"), self.pw_edit)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        btns.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.setFixedHeight(34)
        cancel_btn.setFixedWidth(90)
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)

        save_btn = QPushButton("Save Staff" if self._is_edit else "Add Staff")
        save_btn.setIcon(get_action_icon("check", "primary", 15))
        save_btn.setFixedHeight(34)
        save_btn.setFixedWidth(120)
        save_btn.clicked.connect(self._on_save)
        btns.addWidget(save_btn)

        layout.addLayout(btns)

    def _on_save(self) -> None:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Staff Name is required.")
            self.name_edit.setFocus()
            return
        if not self.username_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Username is required.")
            self.username_edit.setFocus()
            return
        self.accept()

    def get_data(self) -> tuple[str, str]:
        return self.name_edit.text().strip(), self.username_edit.text().strip().lstrip("@")


class ResetStaffPasswordDialog(QDialog):
    """Dialog to reset a staff member's password."""

    def __init__(self, parent=None, staff_name: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Reset Staff Password")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel(f"Reset Password for {staff_name}" if staff_name else "Reset Staff Password")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        sub = QLabel("Assign a new temporary or permanent password for this account.")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(title)
        layout.addWidget(sub)

        form = QFormLayout()
        form.setSpacing(10)
        form.setVerticalSpacing(10)
        form.setHorizontalSpacing(16)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        def make_lbl(txt: str) -> QLabel:
            lbl = QLabel(txt)
            lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #334155;")
            return lbl

        self.new_pw = QLineEdit()
        self.new_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pw.setPlaceholderText("New password")
        self.new_pw.setFixedHeight(34)
        form.addRow(make_lbl("New Password *:"), self.new_pw)

        self.confirm_pw = QLineEdit()
        self.confirm_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pw.setPlaceholderText("Confirm new password")
        self.confirm_pw.setFixedHeight(34)
        form.addRow(make_lbl("Confirm Password *:"), self.confirm_pw)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        btns.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.setFixedHeight(34)
        cancel_btn.setFixedWidth(90)
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)

        save_btn = QPushButton("Reset Password")
        save_btn.setIcon(get_action_icon("check", "primary", 15))
        save_btn.setFixedHeight(34)
        save_btn.setFixedWidth(145)
        save_btn.clicked.connect(self._on_save)
        btns.addWidget(save_btn)

        layout.addLayout(btns)

    def _on_save(self) -> None:
        new_val = self.new_pw.text().strip()
        conf_val = self.confirm_pw.text().strip()
        if not new_val:
            QMessageBox.warning(self, "Validation Error", "Password cannot be empty.")
            self.new_pw.setFocus()
            return
        if new_val != conf_val:
            QMessageBox.warning(self, "Validation Error", "Passwords do not match.")
            self.confirm_pw.setFocus()
            return
        self.accept()


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
        self.expenses_tab = self._create_expenses_tab()
        self.fulfillment_tab = self._create_fulfillment_tab()
        self.user_access_tab = self._create_user_access_tab()

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
    # Tab 4: Expenses (Expense Accounts Section)
    # -----------------------------------------------------------------------
    def _create_expenses_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(16, 16, 16, 16)
        c_lay.setSpacing(14)

        # Expense Accounts Card
        card = QFrame()
        card.setObjectName("ModuleCardContainer")
        card.setStyleSheet(
            "QFrame#ModuleCardContainer { background-color: #FFFFFF; border: 1px solid #E2E8F0; "
            "border-radius: 12px; }"
        )
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(22, 18, 22, 18)
        card_lay.setSpacing(14)

        # Header with Top-Right '+ Add Expense Account' button
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        sec_header = QVBoxLayout()
        sec_header.setSpacing(2)
        sec_title = QLabel("Expense Accounts")
        sec_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        sec_sub = QLabel("Chart of operational expense categories and accounting reference codes.")
        sec_sub.setStyleSheet("font-size: 12px; color: #64748B;")
        sec_header.addWidget(sec_title)
        sec_header.addWidget(sec_sub)
        header_row.addLayout(sec_header, 1)

        # Top-right secondary outlined button
        self.add_expense_btn = QPushButton("Add Expense Account")
        self.add_expense_btn.setObjectName("SecondaryBtn")
        self.add_expense_btn.setIcon(get_action_icon("plus", "secondary", 14))
        self.add_expense_btn.setFixedHeight(34)
        self.add_expense_btn.setFixedWidth(170)
        self.add_expense_btn.clicked.connect(self._add_expense_account_dialog)
        header_row.addWidget(self.add_expense_btn)

        card_lay.addLayout(header_row)

        # Separator line
        sep = QFrame()
        sep.setObjectName("SidebarDivider")
        sep.setFixedHeight(1)
        card_lay.addWidget(sep)

        # Table: Account Code, Account Name, Status
        self.expenses_table = QTableWidget()
        self.expenses_table.setColumnCount(3)
        self.expenses_table.setHorizontalHeaderLabels(["Account Code", "Account Name", "Status"])
        self.expenses_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.expenses_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.expenses_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.expenses_table.verticalHeader().setVisible(False)
        self.expenses_table.verticalHeader().setDefaultSectionSize(42)
        self.expenses_table.setAlternatingRowColors(True)

        e_hdr = self.expenses_table.horizontalHeader()
        e_hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        e_hdr.resizeSection(0, 160)
        e_hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        e_hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        e_hdr.resizeSection(2, 140)

        card_lay.addWidget(self.expenses_table)

        # Buttons near the bottom of the table
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_box.setContentsMargins(0, 4, 0, 0)

        self.edit_expense_btn = QPushButton("Edit Expense Account")
        self.edit_expense_btn.setObjectName("SecondaryBtn")
        self.edit_expense_btn.setIcon(get_action_icon("edit", "secondary", 14))
        self.edit_expense_btn.setFixedHeight(34)
        self.edit_expense_btn.setFixedWidth(175)
        self.edit_expense_btn.clicked.connect(self._edit_selected_expense_account)
        btn_box.addWidget(self.edit_expense_btn)

        self.archive_expense_btn = QPushButton("Archive Expense Account")
        self.archive_expense_btn.setObjectName("SecondaryBtn")
        self.archive_expense_btn.setIcon(get_action_icon("archive", "secondary", 14))
        self.archive_expense_btn.setFixedHeight(34)
        self.archive_expense_btn.setFixedWidth(190)
        self.archive_expense_btn.clicked.connect(self._toggle_archive_selected_expense_account)
        btn_box.addWidget(self.archive_expense_btn)

        btn_box.addStretch(1)
        card_lay.addLayout(btn_box)

        c_lay.addWidget(card)
        c_lay.addStretch(1)

        scroll.setWidget(container)

        self._load_expense_accounts()

        return scroll

    def _load_expense_accounts(self) -> None:
        """Populate the Expense Accounts table with mock or saved records."""
        self.expense_accounts = SettingsManager.load_expense_accounts()
        self.expenses_table.clearContents()
        self.expenses_table.setRowCount(len(self.expense_accounts))

        for r, acc in enumerate(self.expense_accounts):
            code_text = acc.get("code", "")
            code_display = code_text if code_text else "—"
            code_item = QTableWidgetItem(f"  {code_display}")
            code_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.expenses_table.setItem(r, 0, code_item)

            name_text = acc.get("name", "")
            name_item = QTableWidgetItem(f"  {name_text}")
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.expenses_table.setItem(r, 1, name_item)

            status_text = acc.get("status", "Active")
            self.expenses_table.setCellWidget(r, 2, self._create_status_badge(status_text))

        row_h = self.expenses_table.verticalHeader().defaultSectionSize() or 42
        hdr_h = self.expenses_table.horizontalHeader().height() or 42
        table_h = hdr_h + (len(self.expense_accounts) * row_h) + 8
        self.expenses_table.setFixedHeight(max(140, min(420, table_h)))

    def _add_expense_account_dialog(self) -> None:
        dlg = ExpenseAccountDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            code, name = dlg.get_data()
            self.expense_accounts.append({"code": code, "name": name, "status": "Active"})
            SettingsManager.save_expense_accounts(self.expense_accounts)
            self._load_expense_accounts()

    def _edit_selected_expense_account(self) -> None:
        r = self.expenses_table.currentRow()
        if r < 0 or r >= len(self.expense_accounts):
            QMessageBox.warning(
                self, "Select Account", "Please select an expense account row from the table first."
            )
            return
        curr = self.expense_accounts[r]
        dlg = ExpenseAccountDialog(self, account=curr)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            code, name = dlg.get_data()
            self.expense_accounts[r]["code"] = code
            self.expense_accounts[r]["name"] = name
            SettingsManager.save_expense_accounts(self.expense_accounts)
            self._load_expense_accounts()
            self.expenses_table.selectRow(r)

    def _toggle_archive_selected_expense_account(self) -> None:
        r = self.expenses_table.currentRow()
        if r < 0 or r >= len(self.expense_accounts):
            QMessageBox.warning(
                self, "Select Account", "Please select an expense account row from the table first."
            )
            return
        curr_status = self.expense_accounts[r].get("status", "Active")
        new_status = "Archived" if curr_status == "Active" else "Active"
        self.expense_accounts[r]["status"] = new_status
        SettingsManager.save_expense_accounts(self.expense_accounts)
        self._load_expense_accounts()
        self.expenses_table.selectRow(r)

    # -----------------------------------------------------------------------
    # Tab 5: Fulfillment (Courier Options)
    # -----------------------------------------------------------------------
    def _create_fulfillment_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(24, 24, 24, 24)
        c_lay.setSpacing(20)

        # Courier Options Card
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
        sec_title = QLabel("Courier Options")
        sec_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        sec_sub = QLabel("Supported shipping couriers, third-party logistics partners, and dispatch delivery services.")
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
        self.couriers_table = QTableWidget()
        self.couriers_table.setColumnCount(3)
        self.couriers_table.setHorizontalHeaderLabels(["Name", "Status", "Actions"])
        self.couriers_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.couriers_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.couriers_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.couriers_table.verticalHeader().setVisible(False)
        self.couriers_table.verticalHeader().setDefaultSectionSize(42)
        self.couriers_table.setAlternatingRowColors(True)

        header = self.couriers_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 140)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(2, 210)

        card_lay.addWidget(self.couriers_table)

        # Below Table: Input field + Solid gold 'Add' button
        add_box = QHBoxLayout()
        add_box.setSpacing(10)
        add_box.setContentsMargins(0, 4, 0, 0)

        self.new_courier_input = QLineEdit()
        self.new_courier_input.setPlaceholderText("New courier name")
        self.new_courier_input.setFixedHeight(36)
        self.new_courier_input.returnPressed.connect(self._add_courier)
        add_box.addWidget(self.new_courier_input, 1)

        self.add_courier_btn = QPushButton("Add")
        self.add_courier_btn.setIcon(get_action_icon("plus", "primary", 15))
        self.add_courier_btn.setFixedHeight(36)
        self.add_courier_btn.setFixedWidth(90)
        self.add_courier_btn.clicked.connect(self._add_courier)
        add_box.addWidget(self.add_courier_btn)

        card_lay.addLayout(add_box)

        c_lay.addWidget(card)
        c_lay.addStretch(1)

        scroll.setWidget(container)

        # Populate rows
        self._load_couriers()

        return scroll

    def _load_couriers(self) -> None:
        """Populate the Courier Options table with saved or mock couriers."""
        self.couriers = SettingsManager.load_courier_options()
        self.couriers_table.clearContents()
        self.couriers_table.setRowCount(len(self.couriers))

        for r, cour in enumerate(self.couriers):
            # 1. Name
            name_text = cour.get("name", "")
            name_item = QTableWidgetItem(f"  {name_text}")
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.couriers_table.setItem(r, 0, name_item)

            # 2. Status Badge (light green rounded badge)
            status_text = cour.get("status", "Active")
            self.couriers_table.setCellWidget(r, 1, self._create_status_badge(status_text))

            # 3. Actions (Edit & Archive outlined buttons)
            self.couriers_table.setCellWidget(r, 2, self._create_courier_action_buttons(r))

        row_h = self.couriers_table.verticalHeader().defaultSectionSize() or 42
        header_h = self.couriers_table.horizontalHeader().height() or 42
        table_h = header_h + (len(self.couriers) * row_h) + 8
        self.couriers_table.setFixedHeight(max(94, min(420, table_h)))

    def _create_courier_action_buttons(self, row_idx: int) -> QWidget:
        """Return Edit and Archive outlined secondary buttons for courier row."""
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
        edit_btn.clicked.connect(lambda _, idx=row_idx: self._edit_courier(idx))
        lay.addWidget(edit_btn)

        # Archive / Restore button (outlined SecondaryBtn)
        is_active = (self.couriers[row_idx].get("status", "Active") == "Active")
        archive_btn = QPushButton("Archive" if is_active else "Restore")
        archive_btn.setObjectName("SecondaryBtn")
        archive_btn.setIcon(get_action_icon("archive", "secondary", 13))
        archive_btn.setFixedHeight(28)
        archive_btn.setFixedWidth(82)
        archive_btn.clicked.connect(lambda _, idx=row_idx: self._toggle_archive_courier(idx))
        lay.addWidget(archive_btn)

        return container

    def _add_courier(self) -> None:
        """Add a new courier from the input field."""
        name = self.new_courier_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Courier name cannot be empty.")
            self.new_courier_input.setFocus()
            return

        self.couriers.append({"name": name, "status": "Active"})
        SettingsManager.save_courier_options(self.couriers)
        self.new_courier_input.clear()
        self._load_couriers()

    def _edit_courier(self, idx: int) -> None:
        """Edit the courier name via input dialog."""
        if idx < 0 or idx >= len(self.couriers):
            return
        current_name = self.couriers[idx].get("name", "")
        new_name, ok = QInputDialog.getText(
            self, "Edit Courier Option", "Update courier name:", text=current_name
        )
        if ok and new_name.strip():
            self.couriers[idx]["name"] = new_name.strip()
            SettingsManager.save_courier_options(self.couriers)
            self._load_couriers()

    def _toggle_archive_courier(self, idx: int) -> None:
        """Toggle active/archived status for the courier."""
        if idx < 0 or idx >= len(self.couriers):
            return
        curr = self.couriers[idx].get("status", "Active")
        new_status = "Archived" if curr == "Active" else "Active"
        self.couriers[idx]["status"] = new_status
        SettingsManager.save_courier_options(self.couriers)
        self._load_couriers()

    # -----------------------------------------------------------------------
    # Tab 6: User Access (Admin Account & Staff Accounts Sections)
    # -----------------------------------------------------------------------
    def _create_user_access_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(24, 24, 24, 24)
        c_lay.setSpacing(20)

        # -------------------------------------------------------------------
        # 1. Admin Account Section
        # -------------------------------------------------------------------
        admin_card = QFrame()
        admin_card.setObjectName("ModuleCardContainer")
        admin_card.setStyleSheet(
            "QFrame#ModuleCardContainer { background-color: #FFFFFF; border: 1px solid #E2E8F0; "
            "border-radius: 12px; }"
        )
        admin_lay = QVBoxLayout(admin_card)
        admin_lay.setContentsMargins(22, 18, 22, 18)
        admin_lay.setSpacing(14)

        # Header
        admin_header = QVBoxLayout()
        admin_header.setSpacing(2)
        admin_title = QLabel("Admin Account")
        admin_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        admin_sub = QLabel("Primary administrator identity, system credentials, and master security privileges.")
        admin_sub.setStyleSheet("font-size: 12px; color: #64748B;")
        admin_header.addWidget(admin_title)
        admin_header.addWidget(admin_sub)
        admin_lay.addLayout(admin_header)

        # Divider
        sep1 = QFrame()
        sep1.setObjectName("SidebarDivider")
        sep1.setFixedHeight(1)
        admin_lay.addWidget(sep1)

        # Details Row: Avatar + Info + Action Buttons
        details_box = QHBoxLayout()
        details_box.setSpacing(16)
        details_box.setContentsMargins(4, 6, 4, 6)

        # Avatar
        self.admin_avatar_lbl = QLabel("EJ")
        self.admin_avatar_lbl.setObjectName("UserAvatar")
        self.admin_avatar_lbl.setFixedSize(48, 48)
        self.admin_avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.admin_avatar_lbl.setStyleSheet(
            "QLabel#UserAvatar { background-color: #FEF3C7; color: #B45309; "
            "font-size: 16px; font-weight: bold; border-radius: 24px; border: 1px solid #FDE68A; }"
        )
        details_box.addWidget(self.admin_avatar_lbl)

        # Info Col
        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        info_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        top_line = QHBoxLayout()
        top_line.setSpacing(8)
        top_line.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.admin_name_lbl = QLabel("Earth Justin Anne Lim")
        self.admin_name_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #0F172A;")
        top_line.addWidget(self.admin_name_lbl)

        sep_pipe1 = QLabel("|")
        sep_pipe1.setStyleSheet("color: #CBD5E1; font-weight: 300; font-size: 14px;")
        top_line.addWidget(sep_pipe1)

        self.admin_handle_lbl = QLabel("@earth")
        self.admin_handle_lbl.setStyleSheet("font-size: 14px; font-weight: 500; color: #475569;")
        top_line.addWidget(self.admin_handle_lbl)

        sep_pipe2 = QLabel("|")
        sep_pipe2.setStyleSheet("color: #CBD5E1; font-weight: 300; font-size: 14px;")
        top_line.addWidget(sep_pipe2)

        self.admin_status_widget = self._create_status_badge("Active")
        top_line.addWidget(self.admin_status_widget)

        top_line.addStretch(1)
        info_col.addLayout(top_line)

        admin_desc = QLabel("Super Administrator · Root System Management & Access")
        admin_desc.setStyleSheet("font-size: 12px; color: #64748B;")
        info_col.addWidget(admin_desc)

        details_box.addLayout(info_col, 1)

        # Action Buttons: Edit Account & Change Password
        admin_btn_box = QHBoxLayout()
        admin_btn_box.setSpacing(10)
        admin_btn_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.edit_admin_btn = QPushButton("Edit Account")
        self.edit_admin_btn.setObjectName("SecondaryBtn")
        self.edit_admin_btn.setIcon(get_action_icon("edit", "secondary", 14))
        self.edit_admin_btn.setFixedHeight(34)
        self.edit_admin_btn.setFixedWidth(125)
        self.edit_admin_btn.clicked.connect(self._edit_admin_account)
        admin_btn_box.addWidget(self.edit_admin_btn)

        self.change_admin_pw_btn = QPushButton("Change Password")
        self.change_admin_pw_btn.setObjectName("SecondaryBtn")
        self.change_admin_pw_btn.setIcon(get_action_icon("key", "secondary", 14))
        self.change_admin_pw_btn.setFixedHeight(34)
        self.change_admin_pw_btn.setFixedWidth(145)
        self.change_admin_pw_btn.clicked.connect(self._change_admin_password)
        admin_btn_box.addWidget(self.change_admin_pw_btn)

        details_box.addLayout(admin_btn_box)
        admin_lay.addLayout(details_box)

        c_lay.addWidget(admin_card)

        # -------------------------------------------------------------------
        # 2. Staff Accounts Section
        # -------------------------------------------------------------------
        staff_card = QFrame()
        staff_card.setObjectName("ModuleCardContainer")
        staff_card.setStyleSheet(
            "QFrame#ModuleCardContainer { background-color: #FFFFFF; border: 1px solid #E2E8F0; "
            "border-radius: 12px; }"
        )
        staff_lay = QVBoxLayout(staff_card)
        staff_lay.setContentsMargins(22, 18, 22, 18)
        staff_lay.setSpacing(14)

        # Header
        staff_header = QVBoxLayout()
        staff_header.setSpacing(2)
        staff_title = QLabel("Staff Accounts")
        staff_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        staff_sub = QLabel("Operational staff credentials, terminal access permissions, and active login statuses.")
        staff_sub.setStyleSheet("font-size: 12px; color: #64748B;")
        staff_header.addWidget(staff_title)
        staff_header.addWidget(staff_sub)
        staff_lay.addLayout(staff_header)

        # Divider
        sep2 = QFrame()
        sep2.setObjectName("SidebarDivider")
        sep2.setFixedHeight(1)
        staff_lay.addWidget(sep2)

        # Staff Table: Columns (Name, Username, Status, Action)
        self.staff_table = QTableWidget()
        self.staff_table.setColumnCount(4)
        self.staff_table.setHorizontalHeaderLabels(["Name", "Username", "Status", "Action"])
        self.staff_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.staff_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.staff_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.staff_table.verticalHeader().setVisible(False)
        self.staff_table.verticalHeader().setDefaultSectionSize(44)
        self.staff_table.setAlternatingRowColors(True)

        s_hdr = self.staff_table.horizontalHeader()
        s_hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        s_hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        s_hdr.resizeSection(1, 160)
        s_hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        s_hdr.resizeSection(2, 130)
        s_hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        s_hdr.resizeSection(3, 340)

        staff_lay.addWidget(self.staff_table)

        # Full-width outlined 'Add Staff' button
        self.add_staff_btn = QPushButton("Add Staff")
        self.add_staff_btn.setObjectName("SecondaryBtn")
        self.add_staff_btn.setIcon(get_action_icon("plus", "secondary", 14))
        self.add_staff_btn.setFixedHeight(38)
        self.add_staff_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.add_staff_btn.clicked.connect(self._add_staff_dialog)
        staff_lay.addWidget(self.add_staff_btn)

        c_lay.addWidget(staff_card)
        c_lay.addStretch(1)

        scroll.setWidget(container)

        self._load_user_access_data()

        return scroll

    def _load_user_access_data(self) -> None:
        """Load admin and staff data from SettingsManager."""
        self.admin_data = SettingsManager.load_admin_account()
        name = self.admin_data.get("name", "Earth Justin Anne Lim")
        uname = self.admin_data.get("username", "earth").lstrip("@")
        status = self.admin_data.get("status", "Active")

        self.admin_name_lbl.setText(name)
        self.admin_handle_lbl.setText(f"@{uname}")

        # Update Avatar Initials
        parts = [p for p in name.split() if p]
        if len(parts) >= 2:
            initials = f"{parts[0][0]}{parts[-1][0]}".upper()
        elif parts:
            initials = parts[0][:2].upper()
        else:
            initials = "EJ"
        self.admin_avatar_lbl.setText(initials)

        # Load Staff Table
        self.staff_accounts = SettingsManager.load_staff_accounts()
        self.staff_table.clearContents()
        self.staff_table.setRowCount(len(self.staff_accounts))

        for r, st in enumerate(self.staff_accounts):
            # 0. Name
            name_item = QTableWidgetItem(f"  {st.get('name', '')}")
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.staff_table.setItem(r, 0, name_item)

            # 1. Username
            uname_item = QTableWidgetItem(f"  {st.get('username', '')}")
            uname_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.staff_table.setItem(r, 1, uname_item)

            # 2. Status Badge
            st_status = st.get("status", "Active")
            self.staff_table.setCellWidget(r, 2, self._create_status_badge(st_status))

            # 3. Actions
            self.staff_table.setCellWidget(r, 3, self._create_staff_action_buttons(r))

        row_h = self.staff_table.verticalHeader().defaultSectionSize() or 44
        hdr_h = self.staff_table.horizontalHeader().height() or 42
        table_h = hdr_h + (len(self.staff_accounts) * row_h) + 8
        self.staff_table.setFixedHeight(max(94, min(360, table_h)))

    def _create_staff_action_buttons(self, row_idx: int) -> QWidget:
        """Return Edit, Reset Password, and Deactivate outlined secondary buttons."""
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(container)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(6)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Edit button
        edit_btn = QPushButton("Edit")
        edit_btn.setObjectName("SecondaryBtn")
        edit_btn.setIcon(get_action_icon("edit", "secondary", 13))
        edit_btn.setFixedHeight(28)
        edit_btn.setFixedWidth(64)
        edit_btn.clicked.connect(lambda _, idx=row_idx: self._edit_staff(idx))
        lay.addWidget(edit_btn)

        # Reset Password button
        reset_btn = QPushButton("Reset Password")
        reset_btn.setObjectName("SecondaryBtn")
        reset_btn.setIcon(get_action_icon("key", "secondary", 13))
        reset_btn.setFixedHeight(28)
        reset_btn.setFixedWidth(120)
        reset_btn.clicked.connect(lambda _, idx=row_idx: self._reset_staff_password(idx))
        lay.addWidget(reset_btn)

        # Deactivate / Activate button
        is_active = (self.staff_accounts[row_idx].get("status", "Active") == "Active")
        deact_btn = QPushButton("Deactivate" if is_active else "Activate")
        deact_btn.setObjectName("SecondaryBtn")
        deact_btn.setIcon(get_action_icon("alert-circle", "secondary", 13))
        deact_btn.setFixedHeight(28)
        deact_btn.setFixedWidth(92)
        deact_btn.clicked.connect(lambda _, idx=row_idx: self._toggle_deactivate_staff(idx))
        lay.addWidget(deact_btn)

        return container

    def _edit_admin_account(self) -> None:
        """Edit admin name and username."""
        dlg = EditAdminDialog(self, admin_data=self.admin_data)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, uname = dlg.get_data()
            self.admin_data["name"] = name
            self.admin_data["username"] = uname
            SettingsManager.save_admin_account(self.admin_data)
            self._load_user_access_data()

    def _change_admin_password(self) -> None:
        """Change admin password."""
        dlg = ChangeAdminPasswordDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(
                self, "Password Updated", "Administrator password has been successfully updated."
            )

    def _add_staff_dialog(self) -> None:
        """Add new staff account."""
        dlg = StaffAccountDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, uname = dlg.get_data()
            self.staff_accounts.append({
                "name": name,
                "username": uname,
                "status": "Active"
            })
            SettingsManager.save_staff_accounts(self.staff_accounts)
            self._load_user_access_data()

    def _edit_staff(self, idx: int) -> None:
        """Edit staff account details."""
        if idx < 0 or idx >= len(self.staff_accounts):
            return
        curr = self.staff_accounts[idx]
        dlg = StaffAccountDialog(self, staff=curr)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, uname = dlg.get_data()
            self.staff_accounts[idx]["name"] = name
            self.staff_accounts[idx]["username"] = uname
            SettingsManager.save_staff_accounts(self.staff_accounts)
            self._load_user_access_data()

    def _reset_staff_password(self, idx: int) -> None:
        """Reset staff member password."""
        if idx < 0 or idx >= len(self.staff_accounts):
            return
        curr_name = self.staff_accounts[idx].get("name", "Staff")
        dlg = ResetStaffPasswordDialog(self, staff_name=curr_name)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(
                self, "Password Reset", f"Password for {curr_name} has been reset successfully."
            )

    def _toggle_deactivate_staff(self, idx: int) -> None:
        """Toggle active / deactivated status for staff."""
        if idx < 0 or idx >= len(self.staff_accounts):
            return
        curr = self.staff_accounts[idx].get("status", "Active")
        new_status = "Deactivated" if curr == "Active" else "Active"
        self.staff_accounts[idx]["status"] = new_status
        SettingsManager.save_staff_accounts(self.staff_accounts)
        self._load_user_access_data()

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
