"""Expense Management module widget (Admin access only).

Spec (Phase 8):
  ExpenseWidget (QWidget) with expenses QTableWidget
  (Date, Category, Amount, Description) + filter section
  (From/To QDateEdit + Category QComboBox, SQL WHERE filtering).
  ExpenseDialog with expense_date QDateEdit, category QComboBox,
  amount + description QLineEdits, optional Stock IN movement link.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QDialog, QFormLayout, QMessageBox, QLabel,
    QComboBox, QDateEdit, QCheckBox, QHeaderView, QAbstractItemView,
)
from PyQt6.QtCore import QDate
from PyQt6.QtGui import QDoubleValidator

from database.database import get_connection
from expenses.expense_management import ExpenseManager, EXPENSE_CATEGORIES
from inventory.inventory_management import StockMovementManager

_EXPENSE_HEADERS = ["expense_id", "expense_date", "category", "amount", "description"]
_EXPENSE_LABELS = ["ID", "Date", "Category", "Amount", "Description"]


def _unlinked_in_movements(conn) -> list[dict]:
    movs = StockMovementManager(conn).list_movements(limit=200)
    return [m for m in movs
            if m.get("movement_type") == "IN" and not m.get("expense_id")]


class ExpenseDialog(QDialog):
    """Add-expense dialog per Phase-8 spec."""

    def __init__(self, parent=None, in_movements: list[dict] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Add Expense")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Expense date:", self.date_edit)

        self.category_box = QComboBox()
        self.category_box.addItems(list(EXPENSE_CATEGORIES))
        form.addRow("Category:", self.category_box)

        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("e.g. 1500.00")
        self.amount_edit.setValidator(QDoubleValidator(0.01, 10_000_000, 2))
        form.addRow("Amount:", self.amount_edit)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Description (optional)")
        form.addRow("Description:", self.desc_edit)

        self.link_box = QComboBox()
        self.link_box.addItem("(no stock link)", None)
        for m in in_movements or []:
            self.link_box.addItem(
                f"IN #{m['movement_id']} {m.get('material_name', '')} "
                f"x{m.get('quantity')} ({m.get('movement_date')})",
                m["movement_id"])
        form.addRow("Link Stock IN:", self.link_box)
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
        try:
            self.values()
        except ValueError as exc:
            QMessageBox.warning(self, "Add Expense", str(exc))
            return
        self.accept()

    def values(self) -> dict:
        try:
            amount = Decimal(self.amount_edit.text().strip())
        except (InvalidOperation, AttributeError):
            raise ValueError("Enter a valid amount greater than zero.")
        if amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        if self.category_box.currentText() not in EXPENSE_CATEGORIES:
            raise ValueError(f"category must be one of {EXPENSE_CATEGORIES}")
        return {"expense_date": self.date_edit.date().toPyDate().isoformat(),
                "category": self.category_box.currentText(),
                "amount": str(amount),
                "description": self.desc_edit.text().strip(),
                "movement_id": self.link_box.currentData()}


class ExpenseWidget(QWidget):
    """Standalone Admin-only page for QStackedWidget."""

    def __init__(self, user: dict | None = None, parent=None):
        super().__init__(parent)
        self.user = user or {}
        layout = QVBoxLayout(self)

        # Filter section: From/To dates + category.
        filt = QHBoxLayout()
        self.from_check = QCheckBox("From:")
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDate(QDate.currentDate().addMonths(-1))
        self.to_check = QCheckBox("To:")
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDate(QDate.currentDate())
        self.category_box = QComboBox()
        self.category_box.addItem("All categories", "")
        for c in EXPENSE_CATEGORIES:
            self.category_box.addItem(c, c)
        self.apply_btn = QPushButton("Apply Filter")
        self.clear_btn = QPushButton("Clear")
        for w in (self.from_check, self.from_date, self.to_check, self.to_date,
                  QLabel("Category:"), self.category_box,
                  self.apply_btn, self.clear_btn):
            filt.addWidget(w)
        layout.addLayout(filt)

        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.total_label = QLabel("Total: P0.00")
        self.total_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.total_label)

        btns = QHBoxLayout()
        self.add_btn = QPushButton("Add Expense")
        self.delete_btn = QPushButton("Delete")
        self.refresh_btn = QPushButton("Refresh")
        for b, fn in [(self.refresh_btn, self.refresh),
                      (self.add_btn, self.add_expense),
                      (self.delete_btn, self.delete_expense)]:
            b.clicked.connect(fn)
            btns.addWidget(b)
        layout.addLayout(btns)

        self.apply_btn.clicked.connect(self.refresh)
        self.clear_btn.clicked.connect(self.clear_filters)
        self.category_box.currentTextChanged.connect(self.refresh)
        self.refresh()

    # -- helpers --
    def _conn(self):
        return get_connection()

    def _user_id(self) -> int | None:
        if self.user.get("user_id"):
            return self.user["user_id"]
        try:
            from auth.session import Session
            return Session.user_id()
        except Exception:  # noqa: BLE001
            return None

    def _filter_values(self) -> dict:
        start = self.from_date.date().toPyDate().isoformat() \
            if self.from_check.isChecked() else None
        end = self.to_date.date().toPyDate().isoformat() \
            if self.to_check.isChecked() else None
        if end is not None:
            end = f"{end} 23:59:59"  # DATETIME column: include the whole To day
        return {"category": self.category_box.currentData() or "",
                "start": start, "end": end}

    def _selected_id(self) -> int | None:
        r = self.table.currentRow()
        if r < 0:
            return None
        try:
            return int(self.table.item(r, 0).text())
        except (AttributeError, ValueError):
            return None

    # -- spec logic --
    def clear_filters(self) -> None:
        self.from_check.setChecked(False)
        self.to_check.setChecked(False)
        self.category_box.setCurrentIndex(0)
        self.refresh()

    def refresh(self) -> None:
        f = self._filter_values()
        conn = self._conn()
        try:
            rows = ExpenseManager(conn).list_expenses(
                category=f["category"], start=f["start"], end=f["end"])
            self.table.setRowCount(len(rows))
            self.table.setColumnCount(len(_EXPENSE_HEADERS))
            self.table.setHorizontalHeaderLabels(_EXPENSE_LABELS)
            total = Decimal("0.00")
            for r, row in enumerate(rows):
                total += Decimal(str(row.get("amount", 0)))
                for c, h in enumerate(_EXPENSE_HEADERS):
                    val = row.get(h, "")
                    self.table.setItem(r, c, QTableWidgetItem(
                        "" if val is None else str(val)))
            self.table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch)
            self.total_label.setText(f"Total ({len(rows)} rows): P{total:.2f}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            conn.close()

    def add_expense(self) -> None:
        conn = self._conn()
        try:
            in_movs = _unlinked_in_movements(conn)
        finally:
            conn.close()
        dlg = ExpenseDialog(self, in_movements=in_movs)
        if not dlg.exec():
            return
        try:
            vals = dlg.values()
        except ValueError as exc:
            QMessageBox.warning(self, "Add Expense", str(exc))
            return
        conn = self._conn()
        try:
            mgr = ExpenseManager(conn)
            eid = mgr.create_expense(
                vals["category"], vals["amount"], vals["description"],
                recorded_by_user_id=self._user_id(),
                expense_date=vals["expense_date"])
            if vals.get("movement_id") is not None:
                mgr.link_movement(eid, vals["movement_id"])
            QMessageBox.information(self, "Expenses", f"Expense {eid} recorded.")
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            conn.close()

    def delete_expense(self) -> None:
        eid = self._selected_id()
        if eid is None:
            QMessageBox.warning(self, "Expenses", "Select a row first.")
            return
        if QMessageBox.question(
                self, "Delete", f"Delete expense {eid}?"
        ) != QMessageBox.StandardButton.Yes:
            return
        conn = self._conn()
        try:
            ExpenseManager(conn).delete_expense(eid)
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            conn.close()

    # -- compatibility with legacy dashboard slot names --
    def refresh_expenses(self) -> None:
        self.refresh()

    def add_expenses(self) -> None:  # pragma: no cover - alias
        self.add_expense()
