"""Customer Management module widget (Professional SaaS / HCI format).

Features:
  - Visual hierarchy: Section title + descriptive subtitle.
  - Action toolbar: Global search bar + Edit, Delete, Refresh, and primary '+ Add Customer' action.
  - Elevated card container wrapping the data table.
  - User-friendly table columns with auto-formatting and row selection.
  - Double-click to edit affordance.
  - Modern modal dialog with field validation.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QDialog, QFormLayout, QMessageBox,
    QHeaderView, QAbstractItemView, QLabel, QFrame,
)
from PyQt6.QtCore import Qt

from customers.customer_management import CustomerManager
from database.database import get_connection

_CUSTOMER_HEADERS = ["ID", "Customer Name", "Contact Number", "Email Address", "Delivery Address", "Date Registered"]


class CustomerDialog(QDialog):
    """Add / Edit Customer Dialog with clean form layout and validation."""

    def __init__(self, parent=None, customer: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Customer" if customer else "Add New Customer")
        self.setMinimumWidth(440)
        data = customer or {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Edit Customer Profile" if customer else "Create New Customer Profile")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        sub = QLabel("Fill in the customer's contact and billing information.")
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
            ("contact_number", "Contact Number:", "e.g. 0917-123-4567"),
            ("email_address", "Email Address:", "name@example.com"),
            ("address", "Delivery Address:", "Street, Barangay, City"),
        ]

        for key, label, placeholder in fields:
            edit = QLineEdit(str(data.get(key) or ""))
            edit.setPlaceholderText(placeholder)
            self._edits[key] = edit
            form.addRow(label, edit)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("SecondaryBtn")
        cancel.clicked.connect(self.reject)

        save = QPushButton("Save Customer")
        save.clicked.connect(self._on_save)

        btns.addWidget(cancel)
        btns.addWidget(save)
        layout.addLayout(btns)

    def _on_save(self) -> None:
        if not self._edits["first_name"].text().strip() or not self._edits["last_name"].text().strip():
            QMessageBox.warning(self, "Validation Error", "First Name and Last Name are required.")
            return
        self.accept()

    def values(self) -> dict:
        return {k: e.text().strip() for k, e in self._edits.items()}


class CustomerWidget(QWidget):
    """Customer Management module with HCI-focused modern layout."""

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
        sub = QLabel("Manage customer contact profiles, delivery addresses, and account history.")
        sub.setObjectName("ModuleHeaderSub")
        header_lay.addWidget(title)
        header_lay.addWidget(sub)
        layout.addLayout(header_lay)

        # 2. Action Toolbar (Search on left, actions on right)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.search = QLineEdit()
        self.search.setObjectName("TableSearchInput")
        self.search.setPlaceholderText("🔍  Search by customer name, phone number, or email...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refresh)
        toolbar.addWidget(self.search, 1)

        self.refresh_btn = QPushButton("↻ Refresh")
        self.refresh_btn.setObjectName("SecondaryBtn")
        self.refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self.refresh_btn)

        self.edit_btn = QPushButton("✏️ Edit")
        self.edit_btn.setObjectName("SecondaryBtn")
        self.edit_btn.clicked.connect(self.edit_customer)
        toolbar.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.setObjectName("DangerBtn")
        self.delete_btn.clicked.connect(self.delete_customer)
        toolbar.addWidget(self.delete_btn)

        self.add_btn = QPushButton("+ Add Customer")
        self.add_btn.clicked.connect(self.add_customer)
        toolbar.addWidget(self.add_btn)

        layout.addLayout(toolbar)

        # 3. Card Container wrapping the Table
        card = QFrame()
        card.setObjectName("ModuleCardContainer")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        self.table = QTableWidget()
        self.table.setColumnCount(len(_CUSTOMER_HEADERS))
        self.table.setHorizontalHeaderLabels(_CUSTOMER_HEADERS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.doubleClicked.connect(self.edit_customer)

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

    def refresh(self) -> None:
        conn = self._conn()
        try:
            rows = CustomerManager(conn).list_customers(self.search.text())
            self.table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                full_name = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
                date_str = str(row.get("created_at") or "")[:10]
                vals = [
                    f"#{row.get('customer_id', '')}",
                    full_name,
                    str(row.get("contact_number") or "—"),
                    str(row.get("email_address") or "—"),
                    str(row.get("address") or "—"),
                    date_str or "—",
                ]
                for c, val in enumerate(vals):
                    item = QTableWidgetItem(val)
                    if c == 0:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(r, c, item)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to load customers:\n{exc}")
        finally:
            conn.close()

    def add_customer(self) -> None:
        dlg = CustomerDialog(self)
        if dlg.exec():
            conn = self._conn()
            try:
                vals = dlg.values()
                CustomerManager(conn).create_customer(
                    vals["first_name"], vals["last_name"],
                    vals["contact_number"], vals["email_address"], vals["address"])
                self.refresh()
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Error", f"Failed to add customer:\n{exc}")
            finally:
                conn.close()

    def edit_customer(self) -> None:
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
            conn = self._conn()
            try:
                CustomerManager(conn).update_customer(cid, **dlg.values())
                self.refresh()
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Error", f"Failed to update customer:\n{exc}")
            finally:
                conn.close()

    def delete_customer(self) -> None:
        cid = self._selected_id()
        if cid is None:
            QMessageBox.information(self, "Select Customer", "Please select a customer to delete.")
            return
        if QMessageBox.question(
                self, "Confirm Deletion",
                f"Are you sure you want to delete customer ID #{cid}?\n"
                "Customers with active orders cannot be removed.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        conn = self._conn()
        try:
            CustomerManager(conn).delete_customer(cid)
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Cannot Delete", str(exc))
        finally:
            conn.close()
