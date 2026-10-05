"""Customer Management module widget (Professional SaaS / HCI format).

Features:
  1. Load & View: Populates QTableWidget with ID, First Name, Last Name, Contact, Email, Address, Date Added.
     Alternating row color (#F9F9F9) for enhanced readability.
  2. Search: Real-time SQL LIKE query on first_name, last_name, contact_number, or email_address.
     Displays 'No customers found' label when no records match.
  3. Add Customer: CustomerDialog with empty fields and strict validation (PH 11-digit mobile, valid email, non-empty names).
     Red error messages on validation failure.
  4. Edit Customer: CustomerDialog pre-filled with selected customer's data.
  5. Delete Customer: Confirmation dialog with business logic check blocking deletion if customer has orders.
  6. View Details: CustomerDetailDialog showing profile, lifetime spend KPI, order history table,
     and quick 'New Order' button that switches to Orders module with customer pre-selected.
  7. Integration Points: Auto-fills delivery address and links foreign keys across Orders, Payments, and Reports.
"""
from __future__ import annotations

import re
from decimal import Decimal

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QDialog, QFormLayout, QMessageBox,
    QHeaderView, QAbstractItemView, QLabel, QFrame, QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor

from customers.customer_management import CustomerManager
from database.database import get_connection
from ui.icons import get_icon, get_action_icon, get_pixmap

_CUSTOMER_HEADERS = [
    "ID", "First Name", "Last Name", "Contact", "Email", "Address", "Date Added", "Status"
]

_ORDER_HISTORY_HEADERS = [
    "Order #", "Order Date", "Type", "Status", "Total Amount", "Paid", "Balance"
]


class CustomerDialog(QDialog):
    """Add / Edit Customer Dialog with clean form layout and strict validation."""

    def __init__(self, parent=None, customer: dict | None = None):
        super().__init__(parent)
        self._is_edit = customer is not None
        self.setWindowTitle("Edit Customer Profile" if self._is_edit else "Add New Customer")
        self.setMinimumWidth(480)
        data = customer or {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Dialog Header
        title = QLabel("Edit Customer Profile" if self._is_edit else "Create New Customer Profile")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        sub = QLabel("Fill in the customer's contact details and default delivery address.")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(title)
        layout.addWidget(sub)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._edits: dict[str, QLineEdit] = {}

        fields = [
            ("first_name", "First Name *:", "e.g. Juan"),
            ("last_name", "Last Name *:", "e.g. Dela Cruz"),
            ("contact_number", "Contact Number *:", "09XXXXXXXXX (11 digits)"),
            ("email_address", "Email Address *:", "name@example.com"),
            ("address", "Delivery Address:", "Street, Barangay, City, Province"),
        ]

        for key, label, placeholder in fields:
            edit = QLineEdit(str(data.get(key) or ""))
            edit.setPlaceholderText(placeholder)
            edit.setFixedHeight(38)
            edit.setStyleSheet("""
                QLineEdit {
                    background-color: #F8FAFC;
                    color: #0F172A;
                    border: 1px solid #CBD5E1;
                    border-radius: 8px;
                    padding: 6px 12px;
                    font-size: 13px;
                }
                QLineEdit:focus {
                    border: 1.5px solid #D4AF37;
                    background-color: #FFFFFF;
                }
            """)
            self._edits[key] = edit
            form.addRow(label, edit)

        layout.addLayout(form)

        # Action Buttons
        btns = QHBoxLayout()
        btns.addStretch(1)
        btns.setSpacing(10)

        cancel = QPushButton("Cancel")
        cancel.setObjectName("SecondaryBtn")
        cancel.setFixedHeight(38)
        cancel.clicked.connect(self.reject)

        save = QPushButton("Save Customer")
        save.setIcon(get_action_icon("check", "primary", 15))
        save.setFixedHeight(38)
        save.clicked.connect(self._on_save)

        btns.addWidget(cancel)
        btns.addWidget(save)
        layout.addLayout(btns)

    def _show_validation_error(self, message: str) -> None:
        """Display red error text in QMessageBox as required by workflow specification."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Validation Error")
        msg.setText(f"<div style='color: #DC2626; font-size: 13px; font-weight: bold;'>{message}</div>")
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #FFFFFF;
            }
            QLabel {
                color: #DC2626;
                font-size: 13px;
            }
            QPushButton {
                background-color: #0F172A;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: bold;
            }
        """)
        msg.exec()

    def _on_save(self) -> None:
        first = self._edits["first_name"].text().strip()
        last = self._edits["last_name"].text().strip()
        contact = self._edits["contact_number"].text().strip()
        email = self._edits["email_address"].text().strip()

        # 1. First/Last Name cannot be empty
        if not first or not last:
            self._show_validation_error("First Name and Last Name cannot be empty.")
            return

        # 2. Contact Number must be 11 digits (PH format)
        cleaned_contact = re.sub(r"\D", "", contact)
        if len(cleaned_contact) != 11 or not cleaned_contact.startswith("09"):
            self._show_validation_error("Contact Number must be 11 digits in Philippine format (e.g. 09171234567).")
            return

        # 3. Email must contain "@" and "."
        if not email or "@" not in email or "." not in email:
            self._show_validation_error("Email must contain '@' and '.' (e.g. customer@example.com).")
            return

        self.accept()

    def values(self) -> dict:
        contact = self._edits["contact_number"].text().strip()
        cleaned_contact = re.sub(r"\D", "", contact)
        return {
            "first_name": self._edits["first_name"].text().strip(),
            "last_name": self._edits["last_name"].text().strip(),
            "contact_number": cleaned_contact or contact,
            "email_address": self._edits["email_address"].text().strip(),
            "address": self._edits["address"].text().strip(),
        }


class CustomerDetailDialog(QDialog):
    """Customer Details modal with customer profile info, aggregate spend, and order history."""

    new_order_requested = pyqtSignal(int)

    def __init__(self, customer: dict, orders: list[dict], total_spent: Decimal, parent=None):
        super().__init__(parent)
        self.customer = customer
        self.cid = customer.get("customer_id", 0)
        full_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()

        self.setWindowTitle(f"Customer Profile — {full_name}")
        self.setMinimumSize(820, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # 1. Header Profile Banner
        header_card = QFrame()
        header_card.setObjectName("ModuleCardContainer")
        header_lay = QHBoxLayout(header_card)
        header_lay.setContentsMargins(18, 16, 18, 16)
        header_lay.setSpacing(16)

        # Avatar initials badge
        first = customer.get("first_name", "")
        last = customer.get("last_name", "")
        initials = (first[:1] + last[:1]).upper() if (first and last) else "CU"
        avatar = QLabel(initials)
        avatar.setObjectName("UserAvatar")
        avatar.setFixedSize(52, 52)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet("font-size: 18px; font-weight: bold; background-color: #FEF3C7; color: #92400E; border: 2px solid #D4AF37; border-radius: 26px;")
        header_lay.addWidget(avatar)

        # Info Box
        info_lay = QVBoxLayout()
        info_lay.setSpacing(3)
        name_title = QLabel(full_name)
        name_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F172A;")

        date_added = str(customer.get("created_at") or "")[:10]
        meta_sub = QLabel(f"Customer #{self.cid} • Registered: {date_added or '—'}")
        meta_sub.setStyleSheet("font-size: 12px; color: #64748B;")
        info_lay.addWidget(name_title)
        info_lay.addWidget(meta_sub)
        header_lay.addLayout(info_lay, 1)

        # Lifetime Spend KPI Box
        kpi_box = QFrame()
        kpi_box.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 6px 14px;")
        kpi_lay = QVBoxLayout(kpi_box)
        kpi_lay.setSpacing(2)
        kpi_lay.setAlignment(Qt.AlignmentFlag.AlignRight)

        spent_title = QLabel("TOTAL SPENT")
        spent_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B; letter-spacing: 0.5px;")
        spent_val = QLabel(f"P{total_spent:,.2f}")
        spent_val.setStyleSheet("font-size: 18px; font-weight: bold; color: #D4AF37;")

        kpi_lay.addWidget(spent_title)
        kpi_lay.addWidget(spent_val)
        header_lay.addWidget(kpi_box)

        layout.addWidget(header_card)

        # 2. Detailed Contact / Delivery Information Grid
        details_card = QFrame()
        details_card.setObjectName("ModuleCardContainer")
        details_lay = QHBoxLayout(details_card)
        details_lay.setContentsMargins(18, 14, 18, 14)
        details_lay.setSpacing(24)

        contact_lbl = QLabel(f"<b>Contact:</b> {customer.get('contact_number') or '—'}")
        contact_lbl.setStyleSheet("color: #334155; font-size: 13px;")
        email_lbl = QLabel(f"<b>Email:</b> {customer.get('email_address') or '—'}")
        email_lbl.setStyleSheet("color: #334155; font-size: 13px;")
        addr_lbl = QLabel(f"<b>Address:</b> {customer.get('address') or '—'}")
        addr_lbl.setStyleSheet("color: #334155; font-size: 13px;")

        details_lay.addWidget(contact_lbl)
        details_lay.addWidget(email_lbl)
        details_lay.addWidget(addr_lbl, 1)
        layout.addWidget(details_card)

        # 3. Order History Section Header
        sec_title = QLabel("Order History")
        sec_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #0F172A; margin-top: 4px;")
        layout.addWidget(sec_title)

        # 4. Order History Table
        history_card = QFrame()
        history_card.setObjectName("ModuleCardContainer")
        history_lay = QVBoxLayout(history_card)
        history_lay.setContentsMargins(0, 0, 0, 0)
        history_lay.setSpacing(0)

        self.order_table = QTableWidget()
        self.order_table.setColumnCount(len(_ORDER_HISTORY_HEADERS))
        self.order_table.setHorizontalHeaderLabels(_ORDER_HISTORY_HEADERS)
        self.order_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.order_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.order_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.order_table.setAlternatingRowColors(True)
        self.order_table.setStyleSheet("alternate-background-color: #F9F9F9; background-color: #FFFFFF;")
        self.order_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.order_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.order_table.verticalHeader().setVisible(False)
        self.order_table.verticalHeader().setDefaultSectionSize(38)

        self.order_table.setRowCount(len(orders))
        for r, o in enumerate(orders):
            oid = o.get("order_id", 0)
            date_str = str(o.get("order_date") or "")[:16]
            otype = str(o.get("order_type") or "ProductOrder")
            status = str(o.get("status") or "Pending")
            tot = Decimal(str(o.get("total_amount") or 0))
            paid = Decimal(str(o.get("paid_amount") or 0))
            bal = Decimal(str(o.get("balance") or 0))

            self.order_table.setItem(r, 0, QTableWidgetItem(f"#{oid:05d}"))
            self.order_table.setItem(r, 1, QTableWidgetItem(date_str))
            self.order_table.setItem(r, 2, QTableWidgetItem(otype))
            self.order_table.setCellWidget(r, 3, self._create_status_pill(status))
            self.order_table.setItem(r, 4, QTableWidgetItem(f"P{tot:,.2f}"))
            self.order_table.setItem(r, 5, QTableWidgetItem(f"P{paid:,.2f}"))
            self.order_table.setItem(r, 6, QTableWidgetItem(f"P{bal:,.2f}"))

        history_lay.addWidget(self.order_table)
        layout.addWidget(history_card, 1)

        if not orders:
            empty_lbl = QLabel("No order history recorded for this customer yet.")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("color: #64748B; font-size: 13px; padding: 24px;")
            history_lay.addWidget(empty_lbl)

        # 5. Dialog Footer Buttons
        footer_lay = QHBoxLayout()
        footer_lay.setSpacing(12)

        # Quick Action: Jump to Order Module with customer pre-selected
        new_order_btn = QPushButton("New Order for this Customer")
        new_order_btn.setIcon(get_action_icon("plus", "primary", 15))
        new_order_btn.setFixedHeight(40)
        new_order_btn.clicked.connect(self._on_new_order)
        footer_lay.addWidget(new_order_btn)

        footer_lay.addStretch(1)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("SecondaryBtn")
        close_btn.setFixedHeight(40)
        close_btn.clicked.connect(self.accept)
        footer_lay.addWidget(close_btn)

        layout.addLayout(footer_lay)

    def _create_status_pill(self, status: str) -> QWidget:
        container = QWidget()
        lay = QHBoxLayout(container)
        lay.setContentsMargins(6, 4, 6, 4)
        pill = QLabel(f"● {status}")
        pill.setObjectName("StatusPill")

        s = status.lower()
        if s in ("paid", "completed"):
            pill.setProperty("status", "paid")
        elif s == "pending":
            pill.setProperty("status", "pending")
        elif s == "processing":
            pill.setProperty("status", "processing")
        elif s == "ready":
            pill.setProperty("status", "ready")
        elif s == "delivered":
            pill.setProperty("status", "delivered")
        else:
            pill.setProperty("status", "cancelled")

        pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pill.style().unpolish(pill)
        pill.style().polish(pill)
        lay.addWidget(pill)
        return container

    def _on_new_order(self) -> None:
        self.accept()
        self.new_order_requested.emit(self.cid)


class CustomerWidget(QWidget):
    """Customer Management module with complete workflow and HCI design."""

    new_order_requested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(18)

        # 1. Page Header (Title + Subtitle)
        header_lay = QVBoxLayout()
        header_lay.setSpacing(4)
        title = QLabel("Customer Directory")
        title.setObjectName("ModuleHeaderTitle")
        sub = QLabel("Centralize client data, contact profiles, delivery addresses, and account history.")
        sub.setObjectName("ModuleHeaderSub")
        header_lay.addWidget(title)
        header_lay.addWidget(sub)
        layout.addLayout(header_lay)

        # 2. Inline Add Customer Card (Directly above search bar, no pop-up dialog)
        form_card = QFrame()
        form_card.setObjectName("ModuleCardContainer")
        form_lay = QVBoxLayout(form_card)
        form_lay.setContentsMargins(18, 14, 18, 14)
        form_lay.setSpacing(10)

        form_header = QHBoxLayout()
        form_header.setSpacing(8)
        form_title = QLabel("Add New Customer")
        form_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #0F172A;")
        form_subtitle = QLabel("— Enter details to register customer directly")
        form_subtitle.setStyleSheet("font-size: 12px; color: #64748B;")
        form_header.addWidget(form_title)
        form_header.addWidget(form_subtitle)
        form_header.addStretch(1)
        form_lay.addLayout(form_header)

        # Row 1: Name, Contact, Email
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        self.input_first_name = QLineEdit()
        self.input_first_name.setObjectName("CustomerFormInput")
        self.input_first_name.setPlaceholderText("First Name *")
        self.input_first_name.setFixedHeight(36)

        self.input_last_name = QLineEdit()
        self.input_last_name.setObjectName("CustomerFormInput")
        self.input_last_name.setPlaceholderText("Last Name *")
        self.input_last_name.setFixedHeight(36)

        self.input_contact = QLineEdit()
        self.input_contact.setObjectName("CustomerFormInput")
        self.input_contact.setPlaceholderText("Contact (09XXXXXXXXX) *")
        self.input_contact.setFixedHeight(36)

        self.input_email = QLineEdit()
        self.input_email.setObjectName("CustomerFormInput")
        self.input_email.setPlaceholderText("Email Address * (name@example.com)")
        self.input_email.setFixedHeight(36)

        row1.addWidget(self.input_first_name, 1)
        row1.addWidget(self.input_last_name, 1)
        row1.addWidget(self.input_contact, 1)
        row1.addWidget(self.input_email, 1)
        form_lay.addLayout(row1)

        # Row 2: Delivery Address + Add Button + Clear Button
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        self.input_address = QLineEdit()
        self.input_address.setObjectName("CustomerFormInput")
        self.input_address.setPlaceholderText("Delivery Address (Street, Barangay, City, Province)")
        self.input_address.setFixedHeight(36)
        row2.addWidget(self.input_address, 1)

        self.add_customer_btn = QPushButton("Add Customer")
        self.add_customer_btn.setIcon(get_action_icon("plus", "primary", 15))
        self.add_customer_btn.setFixedHeight(36)
        self.add_customer_btn.setFixedWidth(130)
        self.add_customer_btn.clicked.connect(self.add_customer)
        row2.addWidget(self.add_customer_btn)

        self.clear_form_btn = QPushButton("Clear")
        self.clear_form_btn.setObjectName("SecondaryBtn")
        self.clear_form_btn.setFixedHeight(36)
        self.clear_form_btn.setFixedWidth(80)
        self.clear_form_btn.clicked.connect(self.clear_inputs)
        row2.addWidget(self.clear_form_btn)

        form_lay.addLayout(row2)
        layout.addWidget(form_card)

        # 3. Action Toolbar (Search on left, actions on right)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.search = QLineEdit()
        self.search.setObjectName("TableSearchInput")
        self.search.addAction(get_icon("search", color="#94A3B8", size=16), QLineEdit.ActionPosition.LeadingPosition)
        self.search.setPlaceholderText("Search by customer name, phone number, or email...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refresh)
        toolbar.addWidget(self.search, 1)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("SecondaryBtn")
        self.refresh_btn.setIcon(get_action_icon("refresh", "secondary", 15))
        self.refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self.refresh_btn)

        self.details_btn = QPushButton("View Details")
        self.details_btn.setObjectName("SecondaryBtn")
        self.details_btn.setIcon(get_action_icon("eye", "secondary", 15))
        self.details_btn.setToolTip("View full customer profile and order history")
        self.details_btn.clicked.connect(self.view_customer_details)
        toolbar.addWidget(self.details_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setObjectName("SecondaryBtn")
        self.edit_btn.setIcon(get_action_icon("edit", "secondary", 15))
        self.edit_btn.clicked.connect(self.edit_customer)
        toolbar.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setObjectName("DangerBtn")
        self.delete_btn.setIcon(get_action_icon("trash", "danger", 15))
        self.delete_btn.clicked.connect(self.delete_customer)
        toolbar.addWidget(self.delete_btn)

        self.add_btn = self.add_customer_btn

        layout.addLayout(toolbar)

        # 4. Card Container wrapping the Table & Empty State Label
        card = QFrame()
        card.setObjectName("ModuleCardContainer")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        # Empty State Label
        self.empty_label = QLabel("No customers found.")
        self.empty_label.setObjectName("TableEmptyLabel")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #64748B; font-size: 14px; font-weight: 500; padding: 48px;")
        self.empty_label.setVisible(False)
        card_lay.addWidget(self.empty_label)

        # Customer Data Table
        self.table = QTableWidget()
        self.table.setColumnCount(len(_CUSTOMER_HEADERS))
        self.table.setHorizontalHeaderLabels(_CUSTOMER_HEADERS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("alternate-background-color: #F9F9F9; background-color: #FFFFFF;")

        # Hide ID column in system so it does not display in the UI
        self.table.setColumnHidden(0, True)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(42)
        self.table.doubleClicked.connect(self.view_customer_details)

        card_lay.addWidget(self.table)
        layout.addWidget(card, 1)

        self.refresh()

    def _conn(self):
        return get_connection()

    def _selected_id(self) -> int | None:
        r = self.table.currentRow()
        if r < 0:
            return None
        try:
            return int(self.table.item(r, 0).text().replace("#", ""))
        except (AttributeError, ValueError):
            return None

    def _show_validation_error(self, message: str) -> None:
        """Display red error text in QMessageBox for input validation."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Validation Error")
        msg.setText(f"<div style='color: #DC2626; font-size: 13px; font-weight: bold;'>{message}</div>")
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #FFFFFF;
            }
            QLabel {
                color: #DC2626;
                font-size: 13px;
            }
            QPushButton {
                background-color: #0F172A;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: bold;
            }
        """)
        msg.exec()

    def clear_inputs(self) -> None:
        """Clear all inputs in the inline customer registration form."""
        self.input_first_name.clear()
        self.input_last_name.clear()
        self.input_contact.clear()
        self.input_email.clear()
        self.input_address.clear()

    def _create_status_btn(self, cid: int, is_active: bool, customer_name: str) -> QWidget:
        """Create interactive Active / Inactive pill button for table row."""
        container = QWidget()
        lay = QHBoxLayout(container)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn = QPushButton("Active" if is_active else "Inactive")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(26)
        btn.setFixedWidth(84)

        if is_active:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #DCFCE7;
                    color: #15803D;
                    border: 1px solid #86EFAC;
                    border-radius: 13px;
                    font-size: 11px;
                    font-weight: 700;
                    padding: 2px 8px;
                }
                QPushButton:hover {
                    background-color: #BBF7D0;
                    border: 1px solid #4ADE80;
                    color: #14532D;
                }
            """)
            btn.setToolTip(f"Click to set {customer_name} to Inactive")
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #F1F5F9;
                    color: #64748B;
                    border: 1px solid #CBD5E1;
                    border-radius: 13px;
                    font-size: 11px;
                    font-weight: 700;
                    padding: 2px 8px;
                }
                QPushButton:hover {
                    background-color: #E2E8F0;
                    border: 1px solid #94A3B8;
                    color: #334155;
                }
            """)
            btn.setToolTip(f"Click to set {customer_name} to Active")

        btn.clicked.connect(lambda checked, c=cid, a=is_active, n=customer_name: self._toggle_customer_status(c, a, n))
        lay.addWidget(btn)
        return container

    def _toggle_customer_status(self, cid: int, current_active: bool, customer_name: str) -> None:
        new_status = not current_active
        action_word = "deactivate" if current_active else "activate"

        conn = self._conn()
        try:
            CustomerManager(conn).set_active(cid, new_status)
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to {action_word} customer:\n{exc}")
        finally:
            conn.close()

    def refresh(self) -> None:
        """Query customers sorted newest first (SELECT * FROM Customers ORDER BY created_at DESC)."""
        conn = self._conn()
        try:
            needle = self.search.text().strip()
            rows = CustomerManager(conn).list_customers(needle)

            if len(rows) == 0:
                self.table.setVisible(False)
                if needle:
                    self.empty_label.setText(f"No customers found matching '{needle}'.")
                else:
                    self.empty_label.setText("No customers registered yet. Fill the form above to add one.")
                self.empty_label.setVisible(True)
                self.table.setRowCount(0)
            else:
                self.empty_label.setVisible(False)
                self.table.setVisible(True)
                self.table.setRowCount(len(rows))

                for r, row in enumerate(rows):
                    cid = row.get("customer_id", "")
                    first = str(row.get("first_name") or "")
                    last = str(row.get("last_name") or "")
                    contact = str(row.get("contact_number") or "—")
                    email = str(row.get("email_address") or "—")
                    addr = str(row.get("address") or "—")
                    date_str = str(row.get("created_at") or "")[:10] or "—"
                    is_active = bool(row.get("is_active", True))

                    vals = [
                        f"#{cid}",
                        first,
                        last,
                        contact,
                        email,
                        addr,
                        date_str,
                    ]

                    for c, val in enumerate(vals):
                        item = QTableWidgetItem(val)
                        if c in (0, 3, 6):
                            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.table.setItem(r, c, item)

                    # Col 7: Status button (Active / Inactive)
                    self.table.setCellWidget(r, 7, self._create_status_btn(cid, is_active, f"{first} {last}"))

        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to load customers:\n{exc}")
        finally:
            conn.close()

    def add_customer(self) -> None:
        """Add New Customer directly from the inline form fields without a pop-up dialog."""
        first = self.input_first_name.text().strip()
        last = self.input_last_name.text().strip()
        contact = self.input_contact.text().strip()
        email = self.input_email.text().strip()
        address = self.input_address.text().strip()

        # 1. First/Last Name cannot be empty
        if not first or not last:
            self._show_validation_error("First Name and Last Name cannot be empty.")
            return

        # 2. Contact Number must be 11 digits (PH format)
        cleaned_contact = re.sub(r"\D", "", contact)
        if len(cleaned_contact) != 11 or not cleaned_contact.startswith("09"):
            self._show_validation_error("Contact Number must be 11 digits in Philippine format (e.g. 09XXXXXXXXX).")
            return

        # 3. Email must contain "@" and "."
        if not email or "@" not in email or "." not in email:
            self._show_validation_error("Email must contain '@' and '.' (e.g. customer@example.com).")
            return

        conn = self._conn()
        try:
            CustomerManager(conn).create_customer(
                first, last, cleaned_contact, email, address, is_active=True
            )
            self.clear_inputs()
            self.refresh()
            QMessageBox.information(
                self, "Customer Added",
                f"Customer '{first} {last}' was added successfully."
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to add customer:\n{exc}")
        finally:
            conn.close()

    def edit_customer(self) -> None:
        """Edit Selected Customer workflow with pre-filled fields."""
        cid = self._selected_id()
        if cid is None:
            QMessageBox.information(self, "Select Customer", "Please select a customer from the table first.")
            return

        conn = self._conn()
        try:
            cur = CustomerManager(conn).get_customer(cid)
        finally:
            conn.close()

        if not cur:
            QMessageBox.warning(self, "Error", "Customer record not found.")
            return

        dlg = CustomerDialog(self, customer=cur)
        if dlg.exec():
            vals = dlg.values()
            conn = self._conn()
            try:
                CustomerManager(conn).update_customer(cid, **vals)
                QMessageBox.information(
                    self, "Customer Updated",
                    f"Customer profile for '{vals['first_name']} {vals['last_name']}' was updated successfully.")
                self.refresh()
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Error", f"Failed to update customer:\n{exc}")
            finally:
                conn.close()

    def delete_customer(self) -> None:
        """Delete Customer workflow with critical business logic check blocking deletion if orders exist."""
        cid = self._selected_id()
        if cid is None:
            QMessageBox.information(self, "Select Customer", "Please select a customer from the table first.")
            return

        conn = self._conn()
        try:
            cust = CustomerManager(conn).get_customer(cid)
            if not cust:
                QMessageBox.warning(self, "Error", "Customer record not found.")
                return

            full_name = f"{cust.get('first_name', '')} {cust.get('last_name', '')}".strip() or f"#{cid}"

            # Confirmation dialog
            if QMessageBox.question(
                self,
                "Confirm Deletion",
                f"Are you sure you want to delete {full_name}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            ) != QMessageBox.StandardButton.Yes:
                return

            # Critical Business Logic Check
            order_count = CustomerManager(conn).count_orders(cid)
            if order_count > 0:
                QMessageBox.critical(
                    self,
                    "Cannot Delete",
                    "<div style='color: #DC2626; font-size: 13px; font-weight: bold;'>Cannot delete. Customer has existing orders.</div>",
                )
                return

            # Execute deletion
            CustomerManager(conn).delete_customer(cid)
            QMessageBox.information(self, "Customer Deleted", f"Customer '{full_name}' was deleted successfully.")
            self.refresh()

        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to delete customer:\n{exc}")
        finally:
            conn.close()

    def view_customer_details(self) -> None:
        """View Details dialog on double-click or button press with order history & Quick Action."""
        cid = self._selected_id()
        if cid is None:
            QMessageBox.information(self, "Select Customer", "Please select a customer from the table first.")
            return

        conn = self._conn()
        try:
            mgr = CustomerManager(conn)
            cust = mgr.get_customer(cid)
            if not cust:
                QMessageBox.warning(self, "Error", "Customer record not found.")
                return
            orders = mgr.order_history(cid)
            total_spent = mgr.customer_total_spent(cid)
        finally:
            conn.close()

        dlg = CustomerDetailDialog(cust, orders, total_spent, self)
        dlg.new_order_requested.connect(self.new_order_requested.emit)
        dlg.exec()
