"""Sales and Order Management module widget (Professional SaaS / HCI format).

Features:
  - Visual hierarchy: Section title + descriptive subtitle.
  - Action toolbar: Live search input + status filter + quick actions + prominent '+ New Order' action.
  - Elevated card container wrapping the orders table.
  - Status pills formatting (Pending, Processing, Paid, Ready, Delivered, Cancelled).
  - Modern NewOrderDialog with conditional layout/items grid and live total calculation.
  - Interactive details dialog with built-in ReportLab PDF invoice generation.
"""
from __future__ import annotations

from decimal import Decimal

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QDialog, QFormLayout, QMessageBox, QLabel,
    QComboBox, QDoubleSpinBox, QCheckBox, QStackedWidget, QDateEdit,
    QHeaderView, QAbstractItemView, QFileDialog, QFrame,
)
from PyQt6.QtCore import Qt, QDate

from customers.customer_management import CustomerManager
from database.database import get_connection
from sales_orders.invoice import generate_invoice_pdf
from sales_orders.sales_order_management import (
    OrderManager, ORDER_TYPES, ORDER_STATUSES,
    DESIGN_ASSURANCE_DEDUCTION, compute_totals,
)
from ui.icons import get_icon, get_action_icon

_ORDER_HEADERS = ["Order #", "Customer Name", "Order Type", "Order Date", "Total Amount", "Status"]
_ITEM_COLS = ["Packaging / Product Type", "Size / Spec", "Quantity", "Unit Price (P)", "Discount (P)"]


def _to_decimal(value) -> Decimal:
    if value is None or value == "":
        return Decimal("0.00")
    return Decimal(str(value))


class NewOrderDialog(QDialog):
    """Modern New Order dialog with conditional items grid and live summary."""

    def __init__(self, parent=None, customers: list[dict] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Create New Customer Order")
        self.setMinimumSize(700, 540)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Dialog Title
        title = QLabel("New Customer Order")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        sub = QLabel("Select a customer, order type, and specify line items.")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(title)
        layout.addWidget(sub)

        form = QFormLayout()
        form.setSpacing(10)

        self.customer_box = QComboBox()
        for c in customers or []:
            self.customer_box.addItem(
                f"#{c['customer_id']}: {c['first_name']} {c['last_name']}",
                c["customer_id"])
        form.addRow("Customer *:", self.customer_box)

        self.type_box = QComboBox()
        self.type_box.addItems(list(ORDER_TYPES))
        self.type_box.setCurrentText("ProductOrder")
        form.addRow("Order Type *:", self.type_box)
        layout.addLayout(form)

        # Conditional Pages: LayoutOnly vs ProductOrder
        self.pages = QStackedWidget()

        # Page 0: LayoutOnly (Single service fee)
        svc_page = QWidget()
        svc_layout = QFormLayout(svc_page)
        svc_layout.setContentsMargins(0, 8, 0, 8)
        self.service_amount = QDoubleSpinBox()
        self.service_amount.setRange(0, 10_000_000)
        self.service_amount.setValue(500)
        self.service_amount.setPrefix("P ")
        svc_layout.addRow("Service Amount (Layout Fee):", self.service_amount)
        self.pages.addWidget(svc_page)

        # Page 1: ProductOrder (Line items grid)
        items_page = QWidget()
        items_layout = QVBoxLayout(items_page)
        items_layout.setContentsMargins(0, 4, 0, 4)
        items_layout.setSpacing(8)

        self.items_table = QTableWidget(0, len(_ITEM_COLS))
        self.items_table.setHorizontalHeaderLabels(_ITEM_COLS)
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.items_table.setMinimumHeight(140)
        items_layout.addWidget(self.items_table)

        row_btns = QHBoxLayout()
        add_btn = QPushButton("Add Item")
        add_btn.setObjectName("SecondaryBtn")
        add_btn.setIcon(get_action_icon("plus", "secondary", 14))
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setObjectName("SecondaryBtn")
        remove_btn.setIcon(get_action_icon("trash", "secondary", 14))
        add_btn.clicked.connect(self.add_item_row)
        remove_btn.clicked.connect(self.remove_item_row)
        row_btns.addWidget(add_btn)
        row_btns.addWidget(remove_btn)
        row_btns.addStretch(1)
        items_layout.addLayout(row_btns)

        self.pages.addWidget(items_page)
        layout.addWidget(self.pages)

        # Extra delivery & deduction fields
        extra = QFormLayout()
        extra.setSpacing(10)

        self.rush = QDoubleSpinBox()
        self.rush.setRange(0, 1_000_000)
        self.rush.setPrefix("P ")
        extra.addRow("Rush Charge:", self.rush)

        self.expected = QDateEdit()
        self.expected.setCalendarPopup(True)
        self.expected.setDate(QDate.currentDate().addDays(3))
        extra.addRow("Expected Delivery:", self.expected)

        self.address = QLineEdit()
        self.address.setPlaceholderText("Delivery address or pickup instructions (optional)")
        extra.addRow("Delivery Address:", self.address)
        layout.addLayout(extra)

        self.deduct = QCheckBox(
            f"Apply Design Assurance Deduction (-P{DESIGN_ASSURANCE_DEDUCTION:.2f})")
        layout.addWidget(self.deduct)

        # Live Total Summary Card
        summary_card = QFrame()
        summary_card.setObjectName("SummaryBox")
        sum_lay = QHBoxLayout(summary_card)
        sum_lay.setContentsMargins(14, 10, 14, 10)
        sum_title = QLabel("Order Grand Total:")
        sum_title.setStyleSheet("font-weight: 600; color: #475569; font-size: 14px;")
        self.total_label = QLabel("P0.00")
        self.total_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F172A;")
        sum_lay.addWidget(sum_title)
        sum_lay.addStretch(1)
        sum_lay.addWidget(self.total_label)
        layout.addWidget(summary_card)

        # Action Buttons
        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("SecondaryBtn")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save Order")
        save.setIcon(get_action_icon("check", "primary", 15))
        save.clicked.connect(self._on_save)
        btns.addWidget(cancel)
        btns.addWidget(save)
        layout.addLayout(btns)

        # Connect live updates
        self.type_box.currentTextChanged.connect(self._sync_pages)
        self.service_amount.valueChanged.connect(lambda _v: self._recalc())
        self.rush.valueChanged.connect(lambda _v: self._recalc())
        self.deduct.toggled.connect(lambda _v: self._recalc())
        self.items_table.itemChanged.connect(lambda _i: self._recalc())

        self.add_item_row()
        self._sync_pages()

    def _sync_pages(self) -> None:
        is_layout = self.type_box.currentText() == "LayoutOnly"
        self.pages.setCurrentIndex(0 if is_layout else 1)
        self._recalc()

    def add_item_row(self) -> None:
        r = self.items_table.rowCount()
        self.items_table.insertRow(r)
        defaults = ["Boxes", "Medium (A4)", "100", "15.00", "0.00"]
        for c, val in enumerate(defaults):
            self.items_table.setItem(r, c, QTableWidgetItem(val))

    def remove_item_row(self) -> None:
        r = self.items_table.currentRow()
        if r >= 0:
            self.items_table.removeRow(r)
            self._recalc()

    def _collect_items(self) -> list[dict]:
        if self.type_box.currentText() == "LayoutOnly":
            return [{
                "packaging_type": "Layout Service", "finish_type": "Design",
                "size": "Digital File", "quantity": 1,
                "unit_price": self.service_amount.value(), "discount": 0,
            }]
        items = []
        for r in range(self.items_table.rowCount()):
            def text(c: int) -> str:
                it = self.items_table.item(r, c)
                return it.text().strip() if it else ""
            try:
                qty = int(text(2) or 1)
            except ValueError:
                qty = 1
            items.append({
                "packaging_type": text(0) or None,
                "size": text(1) or None,
                "quantity": max(qty, 1),
                "unit_price": text(3) or 0,
                "discount": text(4) or 0,
            })
        return items

    def _recalc(self) -> None:
        try:
            total = compute_totals(self._collect_items(), self.rush.value(),
                                   self.deduct.isChecked())
        except Exception:  # noqa: BLE001
            total = Decimal("0.00")
        self.total_label.setText(f"P{total:,.2f}")

    def _on_save(self) -> None:
        try:
            self.values()
        except ValueError as exc:
            QMessageBox.warning(self, "Validation Error", str(exc))
            return
        self.accept()

    def values(self) -> dict:
        if self.customer_box.count() == 0 or self.customer_box.currentData() is None:
            raise ValueError("Select a customer first.")
        if self.type_box.currentText() not in ORDER_TYPES:
            raise ValueError(f"order_type must be one of {ORDER_TYPES}")
        items = self._collect_items()
        if not items:
            raise ValueError("Product orders require at least one line item.")
        if self.type_box.currentText() == "LayoutOnly" and self.service_amount.value() <= 0:
            raise ValueError("Service amount must be greater than zero.")
        return {
            "customer_id": int(self.customer_box.currentData()),
            "order_type": self.type_box.currentText(),
            "items": items,
            "rush_charge": self.rush.value(),
            "is_design_fee_deducted": self.deduct.isChecked(),
            "expected_delivery_date": self.expected.date().toPyDate().isoformat(),
            "delivery_address": self.address.text().strip(),
        }


class OrderDetailsDialog(QDialog):
    """Order details modal with item breakdown and invoice generator."""

    def __init__(self, parent, order: dict):
        super().__init__(parent)
        self.order = order
        ord_id = order.get("order_id", "")
        self.setWindowTitle(f"Order #{ord_id} — Details & Invoice")
        self.setMinimumSize(660, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header info
        title = QLabel(f"Order #{ord_id} Overview")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        sub = QLabel(f"Customer: {order.get('customer_name', 'Customer')}  •  Type: {order.get('order_type')}  •  Date: {order.get('order_date')}")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(title)
        layout.addWidget(sub)

        # Items Table
        self.items_table = QTableWidget()
        items = order.get("items", [])
        self.items_table.setRowCount(len(items))
        self.items_table.setColumnCount(5)
        self.items_table.setHorizontalHeaderLabels(["Product / Packaging", "Size", "Qty", "Unit Price", "Discount"])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.items_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        for r, it in enumerate(items):
            self.items_table.setItem(r, 0, QTableWidgetItem(str(it.get("packaging_type") or "Item")))
            self.items_table.setItem(r, 1, QTableWidgetItem(str(it.get("size") or "—")))
            self.items_table.setItem(r, 2, QTableWidgetItem(str(it.get("quantity") or "1")))
            self.items_table.setItem(r, 3, QTableWidgetItem(f"P{Decimal(str(it.get('unit_price') or 0)):,.2f}"))
            self.items_table.setItem(r, 4, QTableWidgetItem(f"P{Decimal(str(it.get('discount') or 0)):,.2f}"))

        layout.addWidget(self.items_table)

        # Financial breakdown card
        fin_card = QFrame()
        fin_card.setObjectName("SummaryBox")
        fin_lay = QGridLayout(fin_card)
        fin_lay.setContentsMargins(14, 10, 14, 10)

        total = Decimal(str(order.get("total_amount") or 0))
        paid = Decimal(str(order.get("amount_paid") or 0))
        bal = Decimal(str(order.get("balance") or 0))

        fin_lay.addWidget(QLabel("Total Amount:"), 0, 0)
        fin_lay.addWidget(QLabel(f"<b>P{total:,.2f}</b>"), 0, 1)
        fin_lay.addWidget(QLabel("Amount Paid:"), 0, 2)
        fin_lay.addWidget(QLabel(f"<span style='color: #16A34A;'><b>P{paid:,.2f}</b></span>"), 0, 3)
        fin_lay.addWidget(QLabel("Balance Due:"), 1, 0)
        fin_lay.addWidget(QLabel(f"<span style='color: {'#EF4444' if bal > 0 else '#16A34A'};'><b>P{bal:,.2f}</b></span>"), 1, 1)
        fin_lay.addWidget(QLabel("Status:"), 1, 2)
        fin_lay.addWidget(QLabel(f"<b>{order.get('status')}</b>"), 1, 3)

        layout.addWidget(fin_card)

        # Action Buttons
        btns = QHBoxLayout()
        inv_btn = QPushButton("Download PDF Invoice")
        inv_btn.setIcon(get_action_icon("download", "primary", 15))
        inv_btn.clicked.connect(self._invoice)
        close_btn = QPushButton("Close")
        close_btn.setObjectName("SecondaryBtn")
        close_btn.clicked.connect(self.accept)

        btns.addWidget(inv_btn)
        btns.addStretch(1)
        btns.addWidget(close_btn)
        layout.addLayout(btns)

    def _invoice(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Invoice",
            f"invoice_order_{self.order.get('order_id')}.pdf",
            "PDF (*.pdf)")
        if not path:
            return
        try:
            generate_invoice_pdf(self.order, path)
            QMessageBox.information(self, "Invoice Generated", f"Invoice saved successfully to:\n{path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to generate invoice:\n{exc}")


class OrderWidget(QWidget):
    """Sales & Order Management module with professional HCI layout."""

    def __init__(self, user: dict | None = None, parent=None):
        super().__init__(parent)
        self.user = user or {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(18)

        # 1. Page Header (Title + Subtitle)
        header_lay = QVBoxLayout()
        header_lay.setSpacing(4)
        title = QLabel("Sales & Customer Orders")
        title.setObjectName("ModuleHeaderTitle")
        sub = QLabel("Track active print jobs, generate charge invoices, and update production progress.")
        sub.setObjectName("ModuleHeaderSub")
        header_lay.addWidget(title)
        header_lay.addWidget(sub)
        layout.addLayout(header_lay)

        # 2. Action Toolbar (Search & Filter on left, action buttons on right)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.search = QLineEdit()
        self.search.setObjectName("TableSearchInput")
        self.search.addAction(get_icon("search", color="#94A3B8", size=16), QLineEdit.ActionPosition.LeadingPosition)
        self.search.setPlaceholderText("Search by order # or customer name...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refresh)
        toolbar.addWidget(self.search, 1)

        self.status_box = QComboBox()
        self.status_box.setObjectName("TableFilterCombo")
        self.status_box.addItems(["All Statuses"] + list(ORDER_STATUSES))
        self.status_box.currentTextChanged.connect(self.refresh)
        toolbar.addWidget(self.status_box)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("SecondaryBtn")
        self.refresh_btn.setIcon(get_action_icon("refresh", "secondary", 15))
        self.refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self.refresh_btn)

        self.view_btn = QPushButton("Details")
        self.view_btn.setObjectName("SecondaryBtn")
        self.view_btn.setIcon(get_action_icon("eye", "secondary", 15))
        self.view_btn.clicked.connect(self.view_details)
        toolbar.addWidget(self.view_btn)

        self.status_btn = QPushButton("Status")
        self.status_btn.setObjectName("SecondaryBtn")
        self.status_btn.setIcon(get_action_icon("check-circle", "secondary", 15))
        self.status_btn.clicked.connect(self.update_status)
        toolbar.addWidget(self.status_btn)

        self.invoice_btn = QPushButton("Invoice")
        self.invoice_btn.setObjectName("SecondaryBtn")
        self.invoice_btn.setIcon(get_action_icon("file-text", "secondary", 15))
        self.invoice_btn.clicked.connect(self.generate_invoice)
        toolbar.addWidget(self.invoice_btn)

        self.new_btn = QPushButton("New Order")
        self.new_btn.setIcon(get_action_icon("plus", "primary", 16))
        self.new_btn.clicked.connect(self.new_order)
        toolbar.addWidget(self.new_btn)

        layout.addLayout(toolbar)

        # 3. Card Container wrapping the Table
        card = QFrame()
        card.setObjectName("ModuleCardContainer")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        self.table = QTableWidget()
        self.table.setColumnCount(len(_ORDER_HEADERS))
        self.table.setHorizontalHeaderLabels(_ORDER_HEADERS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.doubleClicked.connect(self.view_details)

        card_lay.addWidget(self.table)
        layout.addWidget(card, 1)

        self.refresh()

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
            item_text = self.table.item(r, 0).text().replace("#", "")
            return int(item_text)
        except (AttributeError, ValueError):
            return None

    def refresh(self) -> None:
        conn = self._conn()
        try:
            st = self.status_box.currentText()
            status_filter = "" if st == "All Statuses" else st
            rows = OrderManager(conn).list_orders(status_filter, self.search.text())

            self.table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                oid = row.get("order_id", 0)
                tot = Decimal(str(row.get("total_amount") or 0))
                date_str = str(row.get("order_date") or "")[:10]
                status_str = str(row.get("status") or "Pending")

                self.table.setItem(r, 0, QTableWidgetItem(f"#{oid:05d}"))
                self.table.setItem(r, 1, QTableWidgetItem(str(row.get("customer_name") or "—")))
                self.table.setItem(r, 2, QTableWidgetItem(str(row.get("order_type") or "ProductOrder")))
                self.table.setItem(r, 3, QTableWidgetItem(date_str or "—"))
                self.table.setItem(r, 4, QTableWidgetItem(f"P{tot:,.2f}"))

                # Status pill widget
                pill = QLabel(status_str)
                pill.setObjectName("StatusPill")
                pill.setProperty("status", status_str.lower())
                pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
                pill.style().unpolish(pill)
                pill.style().polish(pill)

                pill_container = QWidget()
                pill_lay = QHBoxLayout(pill_container)
                pill_lay.setContentsMargins(6, 4, 6, 4)
                pill_lay.addWidget(pill)
                self.table.setCellWidget(r, 5, pill_container)

        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to load orders:\n{exc}")
        finally:
            conn.close()

    def new_order(self) -> None:
        conn = self._conn()
        try:
            customers = CustomerManager(conn).list_customers()
        finally:
            conn.close()
        if not customers:
            QMessageBox.warning(self, "No Customers", "Please add at least one customer before creating an order.")
            return

        dlg = NewOrderDialog(self, customers=customers)
        if not dlg.exec():
            return
        try:
            vals = dlg.values()
        except ValueError as exc:
            QMessageBox.warning(self, "Error", str(exc))
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
            QMessageBox.information(self, "Order Created", f"Order #{oid:05d} has been successfully created.")
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to save order:\n{exc}")
        finally:
            conn.close()

    def _load_selected(self) -> dict | None:
        oid = self._selected_id()
        if oid is None:
            QMessageBox.information(self, "Select Order", "Please select an order from the table first.")
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
            QMessageBox.information(self, "Select Order", "Please select an order to update.")
            return

        d = QDialog(self)
        d.setWindowTitle(f"Update Order #{oid} Status")
        d.setMinimumWidth(320)
        lay = QVBoxLayout(d)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        lay.addWidget(QLabel("Select new production/delivery status:"))
        box = QComboBox()
        box.addItems(list(ORDER_STATUSES))
        lay.addWidget(box)

        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("SecondaryBtn")
        cancel.clicked.connect(d.reject)
        save = QPushButton("Update Status")
        save.clicked.connect(d.accept)
        btns.addWidget(cancel)
        btns.addWidget(save)
        lay.addLayout(btns)

        if d.exec():
            conn = self._conn()
            try:
                OrderManager(conn).update_status(oid, box.currentText())
                self.refresh()
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Error", f"Failed to update status:\n{exc}")
            finally:
                conn.close()

    def generate_invoice(self) -> None:
        order = self._load_selected()
        if not order:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Invoice", f"invoice_order_{order.get('order_id')}.pdf",
            "PDF (*.pdf)")
        if not path:
            return
        try:
            generate_invoice_pdf(order, path)
            QMessageBox.information(self, "Invoice", f"Invoice saved to {path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to generate invoice:\n{exc}")
