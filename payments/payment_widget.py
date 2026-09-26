"""Payment Processing module widget (Admin access only).

Spec (Phase 6):
  PaymentWidget (QWidget) with payments QTableWidget,
  Record Payment / Verify Payment buttons.
  PaymentDialog with order combo (blank = Layout-Only), payment_type
  combo, payment_method combo, amount QLineEdit, payment_date QDateEdit.
  On save the linked order flips to Paid/Processing + a Service
  Receipt PDF (ReportLab) is generated.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QDialog, QFormLayout, QMessageBox, QLabel,
    QComboBox, QDateEdit, QHeaderView, QAbstractItemView, QFileDialog,
)
from PyQt6.QtCore import QDate
from PyQt6.QtGui import QDoubleValidator

from database.database import get_connection
from payments.payment_management import (
    PaymentManager, PAYMENT_TYPES, PAYMENT_METHODS, PAYMENT_STATUSES,
)
from payments.receipt import generate_receipt_pdf
from sales_orders.sales_order_management import OrderManager

_PAYMENT_HEADERS = ["payment_id", "order_id", "payment_type", "payment_method",
                    "amount_paid", "payment_date", "status", "processed_by"]


class PaymentDialog(QDialog):
    """Record-payment dialog per Phase-6 spec."""

    def __init__(self, parent=None, orders: list[dict] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Record Payment")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.order_box = QComboBox()
        self.order_box.addItem("(blank — Layout-Only payment)", None)
        for o in orders or []:
            bal = o.get("balance", "?")
            self.order_box.addItem(
                f"#{o['order_id']} {o.get('customer', '')} "
                f"(Total {o.get('total_amount')}, Bal {bal})",
                o["order_id"])
        form.addRow("Order:", self.order_box)

        self.type_box = QComboBox()
        self.type_box.addItems(list(PAYMENT_TYPES))
        form.addRow("Payment type:", self.type_box)

        self.method_box = QComboBox()
        self.method_box.addItems(list(PAYMENT_METHODS))
        if "GCash" in PAYMENT_METHODS:
            self.method_box.setCurrentText("GCash")
        form.addRow("Payment method:", self.method_box)

        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("e.g. 500.00")
        self.amount_edit.setValidator(QDoubleValidator(0.01, 10_000_000, 2))
        form.addRow("Amount paid:", self.amount_edit)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Payment date:", self.date_edit)

        self.status_box = QComboBox()
        self.status_box.addItems(list(PAYMENT_STATUSES))
        self.status_box.setCurrentText("Completed")
        form.addRow("Status:", self.status_box)
        layout.addLayout(form)

        btns = QHBoxLayout()
        save = QPushButton("Save payment")
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
            QMessageBox.warning(self, "Record Payment", str(exc))
            return
        self.accept()

    def values(self) -> dict:
        try:
            amount = Decimal(self.amount_edit.text().strip())
        except (InvalidOperation, AttributeError):
            raise ValueError("Enter a valid amount greater than zero.")
        if amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        if self.type_box.currentText() not in PAYMENT_TYPES:
            raise ValueError(f"payment_type must be one of {PAYMENT_TYPES}")
        if self.method_box.currentText() not in PAYMENT_METHODS:
            raise ValueError(f"payment_method must be one of {PAYMENT_METHODS}")
        return {"order_id": self.order_box.currentData(),
                "payment_type": self.type_box.currentText(),
                "payment_method": self.method_box.currentText(),
                "amount_paid": str(amount),
                "payment_date": self.date_edit.date().toPyDate().isoformat(),
                "status": self.status_box.currentText()}


class PaymentWidget(QWidget):
    """Standalone Admin-only page for QStackedWidget."""

    def __init__(self, user: dict | None = None, parent=None):
        super().__init__(parent)
        self.user = user or {}
        layout = QVBoxLayout(self)
        filt = QHBoxLayout()
        self.type_filter = QComboBox()
        self.type_filter.addItems([""] + list(PAYMENT_TYPES))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter by order ID…")
        filt.addWidget(QLabel("Type:"))
        filt.addWidget(self.type_filter)
        filt.addWidget(self.search)
        layout.addLayout(filt)
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        btns = QHBoxLayout()
        self.record_btn = QPushButton("Record Payment")
        self.verify_btn = QPushButton("Verify Payment")
        self.refresh_btn = QPushButton("Refresh")
        for b, fn in [(self.refresh_btn, self.refresh),
                      (self.record_btn, self.record_payment),
                      (self.verify_btn, self.verify_payment)]:
            b.clicked.connect(fn)
            btns.addWidget(b)
        layout.addLayout(btns)
        self.type_filter.currentTextChanged.connect(self.refresh)
        self.search.textChanged.connect(self.refresh)
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

    def _selected_id(self) -> int | None:
        r = self.table.currentRow()
        if r < 0:
            return None
        try:
            return int(self.table.item(r, 0).text())
        except (AttributeError, ValueError):
            return None

    # -- spec logic --
    def refresh(self) -> None:
        conn = self._conn()
        try:
            rows = PaymentManager(conn).list_payments(
                payment_type=self.type_filter.currentText())
            needle = self.search.text().strip()
            if needle:
                rows = [r for r in rows if needle in str(r.get("order_id") or "")]
            self.table.setRowCount(len(rows))
            self.table.setColumnCount(len(_PAYMENT_HEADERS))
            self.table.setHorizontalHeaderLabels(
                ["Payment ID", "Order ID", "Type", "Method",
                 "Amount Paid", "Date", "Status", "Processed By"])
            for r, row in enumerate(rows):
                for c, h in enumerate(_PAYMENT_HEADERS):
                    val = row.get(h, "")
                    self.table.setItem(r, c, QTableWidgetItem(
                        "" if val is None else str(val)))
            self.table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            conn.close()

    def _open_orders(self) -> list[dict]:
        from reports.reports import ReportManager
        conn = self._conn()
        try:
            return ReportManager(conn).unpaid_orders()
        finally:
            conn.close()

    def record_payment(self) -> None:
        try:
            orders = self._open_orders()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
            return
        dlg = PaymentDialog(self, orders=orders)
        if not dlg.exec():
            return
        try:
            vals = dlg.values()
        except ValueError as exc:
            QMessageBox.warning(self, "Record Payment", str(exc))
            return
        conn = self._conn()
        try:
            mgr = PaymentManager(conn)
            pid = mgr.record_payment(
                self._user_id(), vals["amount_paid"],
                payment_type=vals["payment_type"],
                payment_method=vals["payment_method"],
                order_id=vals["order_id"], status=vals["status"])
            # Stamp the chosen date when it differs from NOW().
            if vals.get("payment_date"):
                cur = conn.cursor()
                try:
                    cur.execute("UPDATE payments SET payment_date = %s WHERE payment_id = %s",
                                (vals["payment_date"], pid))
                    conn.commit()
                finally:
                    cur.close()
            QMessageBox.information(
                self, "Payments",
                f"Payment {pid} recorded."
                + (f" Order #{vals['order_id']} → "
                   f"{mgr.order_balance(vals['order_id'])['balance']} balance."
                   if vals["order_id"] is not None else ""))
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
            return
        finally:
            conn.close()
        self._issue_receipt(pid)

    def verify_payment(self) -> None:
        pid = self._selected_id()
        if pid is None:
            QMessageBox.warning(self, "Payments", "Select a row first.")
            return
        conn = self._conn()
        try:
            try:
                PaymentManager(conn).verify_payment(pid)
            except ValueError as exc:
                QMessageBox.warning(self, "Verify Payment", str(exc))
                return
            QMessageBox.information(self, "Payments", f"Payment {pid} verified.")
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
            return
        finally:
            conn.close()
        self._issue_receipt(pid)

    def _issue_receipt(self, payment_id: int) -> None:
        """Generate the Service Receipt PDF (triggered after save/verify)."""
        conn = self._conn()
        try:
            mgr = PaymentManager(conn)
            pay = mgr.get_payment(payment_id)
            if not pay:
                return
            order = None
            if pay.get("order_id") is not None:
                order = OrderManager(conn).get_order(pay["order_id"])
                if order is not None:
                    bal = mgr.order_balance(pay["order_id"])
                    order["amount_paid"] = bal["paid"]
                    order["balance"] = bal["balance"]
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Receipt", str(exc))
            return
        finally:
            conn.close()
        path, _ = QFileDialog.getSaveFileName(
            self, "Save service receipt",
            f"receipt_payment_{payment_id}.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            generate_receipt_pdf(pay, order, path)
            QMessageBox.information(self, "Receipt", f"Saved to {path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Receipt", str(exc))
