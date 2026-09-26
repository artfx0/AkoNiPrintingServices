"""Customer Management module widget (Admin access only).

Spec (Phase 4):
  CustomerWidget (QWidget) for QStackedWidget with QTableWidget,
  search QLineEdit (SQL LIKE), Add / Edit / Delete buttons.
  CustomerDialog (QDialog) with First/Last/Contact/Email/Address fields.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QDialog, QFormLayout, QMessageBox,
    QHeaderView, QAbstractItemView,
)

from customers.customer_management import CustomerManager
from database.database import get_connection

_CUSTOMER_HEADERS = ["customer_id", "first_name", "last_name", "contact_number",
                     "email_address", "address", "created_at"]


class CustomerDialog(QDialog):
    """Add/Edit dialog with QLineEdit fields for all customer columns."""

    def __init__(self, parent=None, customer: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Edit customer" if customer else "Add customer")
        self.setMinimumWidth(380)
        data = customer or {}
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._edits: dict[str, QLineEdit] = {}
        for key, label in [("first_name", "First Name:"),
                           ("last_name", "Last Name:"),
                           ("contact_number", "Contact Number:"),
                           ("email_address", "Email:"),
                           ("address", "Address:")]:
            edit = QLineEdit(str(data.get(key) or ""))
            if "Email" in label:
                edit.setPlaceholderText("name@example.com")
            self._edits[key] = edit
            form.addRow(label, edit)
        layout.addLayout(form)
        btns = QHBoxLayout()
        save = QPushButton("Save")
        cancel = QPushButton("Cancel")
        save.clicked.connect(self._on_save)
        cancel.clicked.connect(self.reject)
        btns.addWidget(save)
        btns.addWidget(cancel)
        layout.addLayout(btns)

    def _on_save(self) -> None:
        if not self._edits["first_name"].text().strip() \
                or not self._edits["last_name"].text().strip():
            QMessageBox.warning(self, "Customers",
                                "First Name and Last Name are required.")
            return
        self.accept()

    def values(self) -> dict:
        return {k: e.text().strip() for k, e in self._edits.items()}


class CustomerWidget(QWidget):
    """Standalone Admin-only page: table + search + Add/Edit/Delete."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by name or contact number…")
        layout.addWidget(self.search)
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        row = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.edit_btn = QPushButton("Edit")
        self.delete_btn = QPushButton("Delete")
        self.refresh_btn = QPushButton("Refresh")
        for btn, fn in [(self.refresh_btn, self.refresh),
                        (self.add_btn, self.add_customer),
                        (self.edit_btn, self.edit_customer),
                        (self.delete_btn, self.delete_customer)]:
            btn.clicked.connect(fn)
            row.addWidget(btn)
        layout.addLayout(row)
        self.search.textChanged.connect(self.refresh)
        self.refresh()

    # -- helpers --
    def _conn(self):
        return get_connection()

    def _selected_id(self) -> int | None:
        r = self.table.currentRow()
        if r < 0:
            return None
        try:
            return int(self.table.item(r, 0).text())
        except (AttributeError, ValueError):
            return None

    # -- logic (per spec) --
    def refresh(self) -> None:
        conn = self._conn()
        try:
            rows = CustomerManager(conn).list_customers(self.search.text())
            self.table.setRowCount(len(rows))
            self.table.setColumnCount(len(_CUSTOMER_HEADERS))
            self.table.setHorizontalHeaderLabels(_CUSTOMER_HEADERS)
            for r, row in enumerate(rows):
                for c, h in enumerate(_CUSTOMER_HEADERS):
                    val = row.get(h, "")
                    self.table.setItem(r, c, QTableWidgetItem("" if val is None else str(val)))
            self.table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
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
                QMessageBox.critical(self, "Error", str(exc))
            finally:
                conn.close()

    def edit_customer(self) -> None:
        cid = self._selected_id()
        if cid is None:
            QMessageBox.warning(self, "Customers", "Select a row first.")
            return
        conn = self._conn()
        try:
            cur = CustomerManager(conn).get_customer(cid)
        finally:
            conn.close()
        if not cur:
            QMessageBox.warning(self, "Customers", "Customer not found.")
            return
        dlg = CustomerDialog(self, customer=cur)
        if dlg.exec():
            conn = self._conn()
            try:
                CustomerManager(conn).update_customer(cid, **dlg.values())
                self.refresh()
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Error", str(exc))
            finally:
                conn.close()

    def delete_customer(self) -> None:
        cid = self._selected_id()
        if cid is None:
            QMessageBox.warning(self, "Customers", "Select a row first.")
            return
        if QMessageBox.question(
                self, "Delete",
                f"Are you sure you want to delete this customer (ID {cid})?"
        ) != QMessageBox.StandardButton.Yes:
            return
        conn = self._conn()
        try:
            CustomerManager(conn).delete_customer(cid)
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            conn.close()
