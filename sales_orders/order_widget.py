"""Sales and Order Management module widget (Admin access only).

Spec (Phase 5):
  OrderWidget (QWidget) with orders QTableWidget, search bar,
  New Order / View Details / Update Status buttons.
  NewOrderDialog with customer combo, order_type combo, conditional
  LayoutOnly amount vs ProductOrder items grid, P500 deduction checkbox,
  dynamic total QLabel. Save inserts CustomerOrder then OrderItems.
  Generate Invoice via ReportLab PDF.
"""
from __future__ import annotations

from decimal import Decimal

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QDialog, QFormLayout, QMessageBox, QLabel,
    QComboBox, QDoubleSpinBox, QCheckBox, QStackedWidget, QDateEdit,
    QHeaderView, QAbstractItemView, QFileDialog,
)
from PyQt6.QtCore import QDate

from customers.customer_management import CustomerManager
from database.database import get_connection
from sales_orders.invoice import generate_invoice_pdf
from sales_orders.sales_order_management import (
    OrderManager, ORDER_TYPES, ORDER_STATUSES,
    DESIGN_ASSURANCE_DEDUCTION, compute_totals,
)

_ORDER_HEADERS = ["order_id", "customer_name", "order_type", "order_date",
                  "total_amount", "status"]
_ITEM_COLS = ["Packaging Type", "Size", "Quantity", "Unit Price", "Discount"]


def _to_decimal(value) -> Decimal:
    if value is None or value == "":
        return Decimal("0.00")
    return Decimal(str(value))


class NewOrderDialog(QDialog):
    """Customer combo + type combo + conditional amount/items + totals."""

    def __init__(self, parent=None, customers: list[dict] | None = None):
        super().__init__(parent)
        self.setWindowTitle("New Order")
        self.setMinimumSize(640, 480)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.customer_box = QComboBox()
        for c in customers or []:
            self.customer_box.addItem(
                f"{c['customer_id']}: {c['first_name']} {c['last_name']}",
                c["customer_id"])
        form.addRow("Customer:", self.customer_box)

        self.type_box = QComboBox()
        self.type_box.addItems(list(ORDER_TYPES))
        self.type_box.setCurrentText("ProductOrder")
        form.addRow("Order type:", self.type_box)
        layout.addLayout(form)

        # Conditional pages
        self.pages = QStackedWidget()
        # LayoutOnly page: single service amount
        svc = QWidget()
        svc_layout = QFormLayout(svc)
        self.service_amount = QDoubleSpinBox()
        self.service_amount.setRange(0, 10_000_000)
        self.service_amount.setValue(500)
        svc_layout.addRow("Service amount:", self.service_amount)
        self.pages.addWidget(svc)
        # ProductOrder page: items grid + add/remove
        items_page = QWidget()
        items_layout = QVBoxLayout(items_page)
        self.items_table = QTableWidget(0, len(_ITEM_COLS))
        self.items_table.setHorizontalHeaderLabels(_ITEM_COLS)
        self.items_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        items_layout.addWidget(self.items_table)
        row_btns = QHBoxLayout()
        add_btn = QPushButton("Add row")
        remove_btn = QPushButton("Remove row")
        add_btn.clicked.connect(self.add_item_row)
        remove_btn.clicked.connect(self.remove_item_row)
        row_btns.addWidget(add_btn)
        row_btns.addWidget(remove_btn)
        items_layout.addLayout(row_btns)
        self.pages.addWidget(items_page)
        layout.addWidget(self.pages)

        extra = QFormLayout()
        self.rush = QDoubleSpinBox()
        self.rush.setRange(0, 1_000_000)
        extra.addRow("Rush charge:", self.rush)
        self.expected = QDateEdit()
        self.expected.setCalendarPopup(True)
        self.expected.setDate(QDate.currentDate().addDays(3))
        extra.addRow("Expected delivery:", self.expected)
        self.address = QLineEdit()
        self.address.setPlaceholderText("Delivery address (optional)")
        extra.addRow("Delivery address:", self.address)
        layout.addLayout(extra)

        self.deduct = QCheckBox(
            f"Apply Design Assurance Deduction ({DESIGN_ASSURANCE_DEDUCTION})")
        layout.addWidget(self.deduct)

        self.total_label = QLabel("Total: P0.00")
        self.total_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.total_label)

        btns = QHBoxLayout()
        save = QPushButton("Save order")
        cancel = QPushButton("Cancel")
        save.clicked.connect(self._on_save)
        cancel.clicked.connect(self.reject)
        btns.addWidget(save)
        btns.addWidget(cancel)
        layout.addLayout(btns)

        self.type_box.currentTextChanged.connect(self._sync_pages)
        self.service_amount.valueChanged.connect(lambda _v: self._recalc())
        self.rush.valueChanged.connect(lambda _v: self._recalc())
        self.deduct.toggled.connect(lambda _v: self._recalc())
        self.items_table.itemChanged.connect(lambda _i: self._recalc())
        self.add_item_row()
        self._sync_pages()

    # -- conditional UI --
    def _sync_pages(self) -> None:
        is_layout = self.type_box.currentText() == "LayoutOnly"
        self.pages.setCurrentIndex(0 if is_layout else 1)
        self._recalc()

    # -- items grid --
    def add_item_row(self) -> None:
        r = self.items_table.rowCount()
        self.items_table.insertRow(r)
        defaults = ["Box", "M", "1", "100.00", "0.00"]
        for c, val in enumerate(defaults):
            self.items_table.setItem(r, c, QTableWidgetItem(val))

    def remove_item_row(self) -> None:
        r = self.items_table.currentRow()
        if r >= 0:
            self.items_table.removeRow(r)
            self._recalc()

    def _collect_items(self) -> list[dict]:
        if self.type_box.currentText() == "LayoutOnly":
            return [{"packaging_type": "Service", "finish_type": "Layout",
                     "size": "Layout Service", "quantity": 1,
                     "unit_price": self.service_amount.value(), "discount": 0}]
        items = []
        for r in range(self.items_table.rowCount()):
            def text(c: int) -> str:
                it = self.items_table.item(r, c)
                return it.text().strip() if it else ""
            qty = int(text(2) or 1)
            items.append({"packaging_type": text(0) or None,
                          "size": text(1) or None, "quantity": qty,
                          "unit_price": text(3) or 0, "discount": text(4) or 0})
        return items

    def _recalc(self) -> None:
        try:
            total = compute_totals(self._collect_items(), self.rush.value(),
                                   self.deduct.isChecked())
        except Exception:  # noqa: BLE001 — live-typing in grid
            total = Decimal("0.00")
        self.total_label.setText(f"Total: P{total:.2f}")

    def _on_save(self) -> None:
        try:
            self.values()
        except ValueError as exc:
            QMessageBox.warning(self, "New Order", str(exc))
            return
        self.accept()

    def values(self) -> dict:
        if self.customer_box.count() == 0 or self.customer_box.currentData() is None:
            raise ValueError("Select a customer first (add a customer).")
        if self.type_box.currentText() not in ORDER_TYPES:
            raise ValueError(f"order_type must be one of {ORDER_TYPES}")
        items = self._collect_items()
        if not items:
            raise ValueError("A ProductOrder needs at least one item row.")
        if self.type_box.currentText() == "LayoutOnly" \
                and self.service_amount.value() <= 0:
            raise ValueError("Service amount must be greater than zero.")
        return {"customer_id": int(self.customer_box.currentData()),
                "order_type": self.type_box.currentText(),
                "items": items, "rush_charge": self.rush.value(),
                "is_design_fee_deducted": self.deduct.isChecked(),
                "expected_delivery_date":
                    self.expected.date().toPyDate().isoformat(),
                "delivery_address": self.address.text().strip()}


class OrderDetailsDialog(QDialog):
    """Read-only order view with Generate Invoice (ReportLab PDF)."""

    def __init__(self, parent, order: dict):
        super().__init__(parent)
        self.order = order
        self.setWindowTitle(f"Order #{order.get('order_id')} — Details")
        self.setMinimumSize(620, 480)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"Order #{order.get('order_id')} — {order.get('order_type')} — "
            f"{order.get('status')} | Customer #{order.get('customer_id')} | "
            f"Date {order.get('order_date')}"))
        self.items = QTableWidget()
        self.items.setRowCount(len(order.get("items", [])))
        self.items.setColumnCount(6)
        self.items.setHorizontalHeaderLabels(
            ["#", "Packaging", "Size", "Qty", "Unit Price", "Discount"])
        for r, it in enumerate(order.get("items", [])):
            for c, k in enumerate(["order_item_id", "packaging_type", "size",
                                   "quantity", "unit_price", "discount"]):
                self.items.setItem(r, c, QTableWidgetItem(str(it.get(k, ""))))
        self.items.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.items.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.items)
        layout.addWidget(QLabel(
            f"Total: {order.get('total_amount')} | Paid: {order.get('amount_paid')} "
            f"| Balance: {order.get('balance')} | Rush: {order.get('rush_charge')}"))
        btns = QHBoxLayout()
        inv = QPushButton("Generate Invoice")
        close = QPushButton("Close")
        inv.clicked.connect(self._invoice)
        close.clicked.connect(self.accept)
        btns.addWidget(inv)
        btns.addWidget(close)
        layout.addLayout(btns)

    def _invoice(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save invoice",
            f"invoice_order_{self.order.get('order_id')}.pdf",
            "PDF (*.pdf)")
        if not path:
            return
        try:
            generate_invoice_pdf(self.order, path)
            QMessageBox.information(self, "Invoice", f"Saved to {path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Invoice", str(exc))


class OrderWidget(QWidget):
    """Standalone Admin-only page for QStackedWidget."""

    def __init__(self, user: dict | None = None, parent=None):
        super().__init__(parent)
        self.user = user or {}
        layout = QVBoxLayout(self)
        filt = QHBoxLayout()
        self.status_box = QComboBox()
        self.status_box.addItems([""] + list(ORDER_STATUSES))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search customer…")
        filt.addWidget(QLabel("Status:"))
        filt.addWidget(self.status_box)
        filt.addWidget(self.search)
        layout.addLayout(filt)
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        btns = QHBoxLayout()
        self.new_btn = QPushButton("New Order")
        self.view_btn = QPushButton("View Details")
        self.status_btn = QPushButton("Update Status")
        self.invoice_btn = QPushButton("Generate Invoice")
        self.refresh_btn = QPushButton("Refresh")
        for b, fn in [(self.refresh_btn, self.refresh),
                      (self.new_btn, self.new_order),
                      (self.view_btn, self.view_details),
                      (self.status_btn, self.update_status),
                      (self.invoice_btn, self.generate_invoice)]:
            b.clicked.connect(fn)
            btns.addWidget(b)
        layout.addLayout(btns)
        self.status_box.currentTextChanged.connect(self.refresh)
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
            rows = OrderManager(conn).list_orders(
                self.status_box.currentText(), self.search.text())
            self.table.setRowCount(len(rows))
            self.table.setColumnCount(len(_ORDER_HEADERS))
            self.table.setHorizontalHeaderLabels(
                ["Order ID", "Customer Name", "Type", "Date",
                 "Total Amount", "Status"])
            for r, row in enumerate(rows):
                for c, h in enumerate(_ORDER_HEADERS):
                    val = row.get(h, "")
                    self.table.setItem(r, c, QTableWidgetItem(
                        "" if val is None else str(val)))
            self.table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            conn.close()

    def new_order(self) -> None:
        conn = self._conn()
        try:
            customers = CustomerManager(conn).list_customers()
        finally:
            conn.close()
        if not customers:
            QMessageBox.warning(self, "Orders", "Add a customer first.")
            return
        dlg = NewOrderDialog(self, customers=customers)
        if not dlg.exec():
            return
        try:
            vals = dlg.values()
        except ValueError as exc:
            QMessageBox.warning(self, "New Order", str(exc))
            return
        conn = self._conn()
        try:
            oid = OrderManager(conn).create_order(
                vals["customer_id"], self._user_id(),
                order_type=vals["order_type"],
                expected_delivery_date=vals["expected_delivery_date"],
                delivery_address=vals["delivery_address"],
                rush_charge=vals["rush_charge"],
                is_design_fee_deducted=vals["is_design_fee_deducted"],
                items=vals["items"])
            QMessageBox.information(self, "Orders", f"Order {oid} created.")
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            conn.close()

    def _load_selected(self) -> dict | None:
        oid = self._selected_id()
        if oid is None:
            QMessageBox.warning(self, "Orders", "Select a row first.")
            return None
        conn = self._conn()
        try:
            from payments.payment_management import PaymentManager
            order = OrderManager(conn).get_order(oid)
            bal = PaymentManager(conn).order_balance(oid)
            if order is not None:
                order["amount_paid"] = order.get("amount_paid", bal["paid"])
                order["balance"] = bal["balance"]
            return order
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
            return None
        finally:
            conn.close()

    def view_details(self) -> None:
        order = self._load_selected()
        if order:
            OrderDetailsDialog(self, order).exec()

    def update_status(self) -> None:
        oid = self._selected_id()
        if oid is None:
            QMessageBox.warning(self, "Orders", "Select a row first.")
            return
        box = QComboBox()
        box.addItems(list(ORDER_STATUSES))
        d = QDialog(self)
        d.setWindowTitle("Update Status")
        lay = QVBoxLayout(d)
        lay.addWidget(QLabel(f"Order #{oid} status:"))
        lay.addWidget(box)
        btns = QHBoxLayout()
        ok, cancel = QPushButton("Save"), QPushButton("Cancel")
        ok.clicked.connect(d.accept)
        cancel.clicked.connect(d.reject)
        btns.addWidget(ok)
        btns.addWidget(cancel)
        lay.addLayout(btns)
        if d.exec():
            conn = self._conn()
            try:
                OrderManager(conn).update_status(oid, box.currentText())
                self.refresh()
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Error", str(exc))
            finally:
                conn.close()

    def generate_invoice(self) -> None:
        order = self._load_selected()
        if not order:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save invoice", f"invoice_order_{order.get('order_id')}.pdf",
            "PDF (*.pdf)")
        if not path:
            return
        try:
            generate_invoice_pdf(order, path)
            QMessageBox.information(self, "Invoice", f"Saved to {path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Invoice", str(exc))
