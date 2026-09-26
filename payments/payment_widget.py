"""Payment Processing module widget (Professional SaaS / HCI format).

Features:
  - Visual hierarchy: Section title + descriptive subtitle.
  - Action toolbar: Filter by Order/Payment ID, Payment Type, and Payment Status.
  - Actions: Refresh, Print Receipt, Verify Payment, and primary '+ Record Payment'.
  - Elevated card container wrapping the data table.
  - Colored status pills (Completed, Pending, Refunded, Cancelled).
  - Currency formatting in Philippine Peso (P{:,.2f}).
  - Modernized PaymentDialog with live order balance preview.
  - Generates Service Receipt PDF on demand or after recording/verification.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QDialog, QFormLayout, QMessageBox, QLabel,
    QComboBox, QDateEdit, QHeaderView, QAbstractItemView, QFileDialog,
    QFrame,
)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QDoubleValidator

from database.database import get_connection
from payments.payment_management import (
    PaymentManager, PAYMENT_TYPES, PAYMENT_METHODS, PAYMENT_STATUSES,
)
from payments.receipt import generate_receipt_pdf
from ui.icons import get_icon, get_action_icon
from sales_orders.sales_order_management import OrderManager

_PAYMENT_HEADERS = [
    "Payment #", "Order #", "Type", "Method",
    "Amount Paid", "Date", "Status", "Processed By"
]


class PaymentDialog(QDialog):
    """Record-payment dialog with HCI-aligned form and order balance preview."""

    def __init__(self, parent=None, orders: list[dict] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Record Payment")
        self.setMinimumWidth(460)
        self.orders = orders or []
        self._orders_by_id = {o["order_id"]: o for o in self.orders}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Title & Subtitle
        title = QLabel("Record Customer Payment")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        sub = QLabel("Select an unpaid customer order or record a standalone service fee.")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(title)
        layout.addWidget(sub)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Order combo
        self.order_box = QComboBox()
        self.order_box.addItem("(None — Layout-Only / Walk-in Service)", None)
        for o in self.orders:
            bal = o.get("balance", "0.00")
            self.order_box.addItem(
                f"Order #{o['order_id']} — {o.get('customer', 'Unknown')} (Bal: P{Decimal(str(bal)):,.2f})",
                o["order_id"]
            )
        self.order_box.currentIndexChanged.connect(self._update_order_preview)
        form.addRow("Linked Order:", self.order_box)

        # Order summary preview card
        self.preview_card = QFrame()
        self.preview_card.setObjectName("SummaryBox")
        prev_lay = QVBoxLayout(self.preview_card)
        prev_lay.setContentsMargins(12, 10, 12, 10)
        prev_lay.setSpacing(4)
        self.preview_label = QLabel("Standalone payment (no order deduction).")
        self.preview_label.setStyleSheet("color: #475569; font-size: 12px;")
        prev_lay.addWidget(self.preview_label)
        form.addRow("", self.preview_card)

        # Payment Type
        self.type_box = QComboBox()
        self.type_box.addItems(list(PAYMENT_TYPES))
        form.addRow("Payment Type:", self.type_box)

        # Payment Method
        self.method_box = QComboBox()
        self.method_box.addItems(list(PAYMENT_METHODS))
        if "GCash" in PAYMENT_METHODS:
            self.method_box.setCurrentText("GCash")
        form.addRow("Payment Method:", self.method_box)

        # Amount
        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("0.00")
        self.amount_edit.setValidator(QDoubleValidator(0.01, 10_000_000, 2))
        form.addRow("Amount Paid (P):", self.amount_edit)

        # Date
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Payment Date:", self.date_edit)

        # Status
        self.status_box = QComboBox()
        self.status_box.addItems(list(PAYMENT_STATUSES))
        self.status_box.setCurrentText("Completed")
        form.addRow("Payment Status:", self.status_box)

        layout.addLayout(form)

        # Action Buttons
        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("SecondaryBtn")
        cancel.clicked.connect(self.reject)

        save = QPushButton("Save Payment")
        save.setIcon(get_action_icon("check", "primary", 15))
        save.clicked.connect(self._on_save)

        btns.addWidget(cancel)
        btns.addWidget(save)
        layout.addLayout(btns)

        self._update_order_preview()

    def _update_order_preview(self) -> None:
        oid = self.order_box.currentData()
        if oid is None or oid not in self._orders_by_id:
            self.preview_label.setText("Standalone payment — not linked to any order.")
            return

        order = self._orders_by_id[oid]
        total = Decimal(str(order.get("total_amount", 0)))
        paid = Decimal(str(order.get("paid", 0)))
        balance = Decimal(str(order.get("balance", total - paid)))

        self.preview_label.setText(
            f"<b>Order #{oid}</b> for <i>{order.get('customer', 'Customer')}</i><br>"
            f"Total: <b>P{total:,.2f}</b> | Paid: <b>P{paid:,.2f}</b> | "
            f"<span style='color: #B45309;'>Remaining Balance: <b>P{balance:,.2f}</b></span>"
        )
        if not self.amount_edit.text().strip():
            self.amount_edit.setText(f"{balance:.2f}")

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
            raise ValueError("Enter a valid payment amount greater than zero.")
        if amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        if self.type_box.currentText() not in PAYMENT_TYPES:
            raise ValueError(f"Payment type must be one of {PAYMENT_TYPES}")
        if self.method_box.currentText() not in PAYMENT_METHODS:
            raise ValueError(f"Payment method must be one of {PAYMENT_METHODS}")

        return {
            "order_id": self.order_box.currentData(),
            "payment_type": self.type_box.currentText(),
            "payment_method": self.method_box.currentText(),
            "amount_paid": str(amount),
            "payment_date": self.date_edit.date().toPyDate().isoformat(),
            "status": self.status_box.currentText(),
        }


class PaymentWidget(QWidget):
    """Payment Transactions module with modern HCI layout."""

    def __init__(self, user: dict | None = None, parent=None):
        super().__init__(parent)
        self.user = user or {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(18)

        # 1. Header (Title + Subtitle)
        header_lay = QVBoxLayout()
        header_lay.setSpacing(4)
        title = QLabel("Payment Transactions")
        title.setObjectName("ModuleHeaderTitle")
        sub = QLabel("Track order settlements, process incoming customer payments, and generate official service receipts.")
        sub.setObjectName("ModuleHeaderSub")
        header_lay.addWidget(title)
        header_lay.addWidget(sub)
        layout.addLayout(header_lay)

        # 2. Action Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        # Live Search
        self.search = QLineEdit()
        self.search.setObjectName("TableSearchInput")
        self.search.addAction(get_icon("search", color="#94A3B8", size=16), QLineEdit.ActionPosition.LeadingPosition)
        self.search.setPlaceholderText("Search by payment ID or order ID...")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(240)
        self.search.textChanged.connect(self.refresh)
        toolbar.addWidget(self.search, 1)

        # Payment Type Filter
        self.type_filter = QComboBox()
        self.type_filter.setObjectName("TableFilterCombo")
        self.type_filter.addItem("All Payment Types", "")
        for t in PAYMENT_TYPES:
            self.type_filter.addItem(t, t)
        self.type_filter.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.type_filter)

        # Status Filter
        self.status_filter = QComboBox()
        self.status_filter.setObjectName("TableFilterCombo")
        self.status_filter.addItem("All Statuses", "")
        for s in PAYMENT_STATUSES:
            self.status_filter.addItem(s, s)
        self.status_filter.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.status_filter)

        # Actions
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("SecondaryBtn")
        self.refresh_btn.setIcon(get_action_icon("refresh", "secondary", 15))
        self.refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self.refresh_btn)

        self.receipt_btn = QPushButton("Print Receipt")
        self.receipt_btn.setObjectName("SecondaryBtn")
        self.receipt_btn.setIcon(get_action_icon("receipt", "secondary", 15))
        self.receipt_btn.clicked.connect(self.print_receipt)
        toolbar.addWidget(self.receipt_btn)

        self.verify_btn = QPushButton("Verify Payment")
        self.verify_btn.setObjectName("SecondaryBtn")
        self.verify_btn.setIcon(get_action_icon("shield-check", "secondary", 15))
        self.verify_btn.clicked.connect(self.verify_payment)
        toolbar.addWidget(self.verify_btn)

        self.record_btn = QPushButton("Record Payment")
        self.record_btn.setIcon(get_action_icon("plus", "primary", 16))
        self.record_btn.clicked.connect(self.record_payment)
        toolbar.addWidget(self.record_btn)

        layout.addLayout(toolbar)

        # 3. Card Container wrapping Table
        card = QFrame()
        card.setObjectName("ModuleCardContainer")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        self.table = QTableWidget()
        self.table.setColumnCount(len(_PAYMENT_HEADERS))
        self.table.setHorizontalHeaderLabels(_PAYMENT_HEADERS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.doubleClicked.connect(self.print_receipt)

        card_lay.addWidget(self.table)
        layout.addWidget(card, 1)

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
            return 1

    def _selected_id(self) -> int | None:
        r = self.table.currentRow()
        if r < 0:
            return None
        try:
            text = self.table.item(r, 0).text().replace("#", "")
            return int(text)
        except (AttributeError, ValueError):
            return None

    def _create_pill_widget(self, text: str, status_prop: str) -> QWidget:
        container = QWidget()
        lay = QHBoxLayout(container)
        lay.setContentsMargins(6, 4, 6, 4)
        pill = QLabel(text)
        pill.setObjectName("StatusPill")
        pill.setProperty("status", status_prop.lower())
        pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pill.style().unpolish(pill)
        pill.style().polish(pill)
        lay.addWidget(pill)
        return container

    # -- Core logic --
    def refresh(self) -> None:
        conn = self._conn()
        try:
            ptype = self.type_filter.currentData() or ""
            rows = PaymentManager(conn).list_payments(payment_type=ptype)

            # Filter by status if set
            status_filter = self.status_filter.currentData()
            if status_filter:
                rows = [r for r in rows if r.get("status") == status_filter]

            # Filter by search needle
            needle = self.search.text().strip().lower()
            if needle:
                rows = [
                    r for r in rows
                    if needle in str(r.get("order_id") or "").lower()
                    or needle in str(r.get("payment_id") or "").lower()
                    or needle in str(r.get("payment_method") or "").lower()
                    or needle in str(r.get("processed_by") or "").lower()
                ]

            self.table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                pid = row.get("payment_id")
                oid = row.get("order_id")
                ptype = row.get("payment_type") or "ProductOrder"
                method = row.get("payment_method") or "Cash"
                amt = Decimal(str(row.get("amount_paid") or 0))
                pdate = str(row.get("payment_date") or "")
                status = str(row.get("status") or "Completed")
                by_user = str(row.get("processed_by") or "—")

                self.table.setItem(r, 0, QTableWidgetItem(f"#{pid}"))
                self.table.setItem(r, 1, QTableWidgetItem(f"#{oid}" if oid is not None else "— (Layout)"))
                self.table.setItem(r, 2, QTableWidgetItem(str(ptype)))
                self.table.setItem(r, 3, QTableWidgetItem(str(method)))
                self.table.setItem(r, 4, QTableWidgetItem(f"P{amt:,.2f}"))
                self.table.setItem(r, 5, QTableWidgetItem(pdate))

                # Status pill
                self.table.setCellWidget(r, 6, self._create_pill_widget(status, status))
                self.table.setItem(r, 7, QTableWidgetItem(by_user))

        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to load payments:\n{exc}")
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
                order_id=vals["order_id"], status=vals["status"]
            )
            if vals.get("payment_date"):
                cur = conn.cursor()
                try:
                    cur.execute("UPDATE payments SET payment_date = %s WHERE payment_id = %s",
                                (vals["payment_date"], pid))
                    conn.commit()
                finally:
                    cur.close()

            bal_str = ""
            if vals["order_id"] is not None:
                bal = mgr.order_balance(vals["order_id"])
                bal_str = f"\nOrder #{vals['order_id']} Balance: P{bal['balance']:,.2f}"

            QMessageBox.information(
                self, "Payment Recorded",
                f"Payment #{pid} of P{Decimal(vals['amount_paid']):,.2f} recorded successfully.{bal_str}"
            )
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
            QMessageBox.warning(self, "Verify Payment", "Please select a payment from the table first.")
            return

        conn = self._conn()
        try:
            try:
                PaymentManager(conn).verify_payment(pid)
            except ValueError as exc:
                QMessageBox.warning(self, "Verify Payment", str(exc))
                return
            QMessageBox.information(self, "Payment Verified", f"Payment #{pid} has been marked as Completed.")
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
            return
        finally:
            conn.close()

        self._issue_receipt(pid)

    def print_receipt(self) -> None:
        pid = self._selected_id()
        if pid is None:
            QMessageBox.warning(self, "Print Receipt", "Please select a payment from the table first.")
            return
        self._issue_receipt(pid)

    def _issue_receipt(self, payment_id: int) -> None:
        """Generate official Service Receipt PDF."""
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
            QMessageBox.critical(self, "Receipt Error", str(exc))
            return
        finally:
            conn.close()

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Service Receipt",
            f"receipt_payment_{payment_id}.pdf", "PDF (*.pdf)"
        )
        if not path:
            return

        try:
            generate_receipt_pdf(pay, order, path)
            QMessageBox.information(self, "Receipt Saved", f"Service Receipt saved successfully to:\n{path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Receipt Error", f"Failed to generate receipt PDF:\n{exc}")
