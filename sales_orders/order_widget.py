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
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QDialog, QFormLayout, QMessageBox, QLabel,
    QComboBox, QDoubleSpinBox, QCheckBox, QStackedWidget, QDateEdit,
    QHeaderView, QAbstractItemView, QFileDialog, QFrame, QScrollArea,
)
from PyQt6.QtCore import Qt, QDate

from customers.customer_management import CustomerManager
from database.database import get_connection
from sales_orders.invoice import generate_invoice_pdf
from sales_orders.sales_order_management import (
    OrderManager, ORDER_TYPES, ORDER_STATUSES,
    CANCELLABLE_STATUSES, NON_CANCELLABLE_STATUSES,
    DESIGN_ASSURANCE_DEDUCTION, compute_totals,
)
from ui.icons import get_icon, get_action_icon
from ui.kpi_card import StatusKpiCard

_ORDER_HEADERS = ["Order #", "Customer Name", "Order Type", "Order Date", "Total Amount", "Status"]
_ITEM_COLS = ["Packaging / Product Type", "Size / Spec", "Quantity", "Unit Price (P)", "Discount (P)"]


def _to_decimal(value) -> Decimal:
    if value is None or value == "":
        return Decimal("0.00")
    return Decimal(str(value))


class NewOrderDialog(QDialog):
    """Modern New Order dialog with conditional items grid and live summary."""

    def __init__(self, parent=None, customers: list[dict] | None = None, preselected_customer_id: int | None = None):
        super().__init__(parent)
        self.setWindowTitle("Create New Customer Order")
        self.setMinimumSize(700, 540)
        self._customers_map = {c["customer_id"]: c for c in customers or []}

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
        if preselected_customer_id is not None:
            for idx in range(self.customer_box.count()):
                if self.customer_box.itemData(idx) == preselected_customer_id:
                    self.customer_box.setCurrentIndex(idx)
                    break
        self.customer_box.currentIndexChanged.connect(self._on_customer_changed)
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

        self._on_customer_changed()

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

    def _on_customer_changed(self) -> None:
        cid = self.customer_box.currentData()
        c = self._customers_map.get(cid)
        if c and c.get("address"):
            self.address.setText(str(c["address"]).strip())

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


class OrderDetailDialog(QDialog):
    """Modern modal dialog displaying complete order details, customer info, payments, and PDF generation."""

    def __init__(self, parent, order: dict):
        super().__init__(parent)
        self.order = order
        ord_id = order.get("order_id", 0)
        self.setWindowTitle(f"Order #{ord_id:05d} — Order Details")
        self.setModal(True)
        self.setMinimumSize(840, 680)
        self.resize(880, 720)

        # Root layout holding scroll area and sticky footer buttons
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Scroll Area for responsive height
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; }")

        content = QWidget()
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(28, 24, 28, 24)
        content_lay.setSpacing(20)

        # 1. Header (Title + Subtitle + Status Pill)
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        header_text_lay = QVBoxLayout()
        header_text_lay.setSpacing(4)
        title = QLabel(f"Order #{ord_id:05d} Overview")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #0F172A;")
        order_date_str = str(order.get("order_date") or "—")[:19]
        sub = QLabel(f"Recorded on {order_date_str} • Type: {order.get('order_type', 'ProductOrder')}")
        sub.setStyleSheet("font-size: 13px; color: #64748B;")
        header_text_lay.addWidget(title)
        header_text_lay.addWidget(sub)
        header_row.addLayout(header_text_lay, 1)

        # Status Badge Pill
        status_str = str(order.get("status") or "Pending")
        status_color = StatusKpiCard.STATUS_CONFIG.get(status_str, {}).get("color", "#64748B")
        status_badge = QLabel(f"  {status_str}  ")
        status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_badge.setFixedHeight(30)
        status_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {status_color};
                color: #FFFFFF;
                font-size: 13px;
                font-weight: bold;
                border-radius: 6px;
                padding: 4px 12px;
            }}
        """)
        header_row.addWidget(status_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        content_lay.addLayout(header_row)

        # 2. Two-Column Info Cards: Order Info & Customer Info
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)

        # Card A: Order Info
        order_card = QFrame()
        order_card.setObjectName("DetailCard")
        order_card.setStyleSheet("""
            QFrame#DetailCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)
        order_lay = QVBoxLayout(order_card)
        order_lay.setContentsMargins(16, 14, 16, 14)
        order_lay.setSpacing(8)

        order_card_title = QLabel("Order Information")
        order_card_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #B45309; border-bottom: 1.5px solid #FDE68A; padding-bottom: 4px;")
        order_lay.addWidget(order_card_title)

        order_form = QFormLayout()
        order_form.setSpacing(6)
        order_form.addRow("<b>Order ID:</b>", QLabel(f"#{ord_id:05d}"))
        order_form.addRow("<b>Order Type:</b>", QLabel(str(order.get("order_type") or "ProductOrder")))
        order_form.addRow("<b>Order Date:</b>", QLabel(order_date_str))
        exp_date = str(order.get("expected_delivery_date") or "None")[:10]
        order_form.addRow("<b>Expected Delivery:</b>", QLabel(exp_date))
        act_date = str(order.get("actual_delivery_date") or "Pending")[:19]
        order_form.addRow("<b>Actual Delivery:</b>", QLabel(act_date))
        order_form.addRow("<b>Status:</b>", QLabel(f"<b>{status_str}</b>"))
        order_lay.addLayout(order_form)
        cards_row.addWidget(order_card, 1)

        # Card B: Customer Info
        cust_card = QFrame()
        cust_card.setObjectName("DetailCard")
        cust_card.setStyleSheet("""
            QFrame#DetailCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)
        cust_lay = QVBoxLayout(cust_card)
        cust_lay.setContentsMargins(16, 14, 16, 14)
        cust_lay.setSpacing(8)

        cust_card_title = QLabel("Customer & Delivery")
        cust_card_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #B45309; border-bottom: 1.5px solid #FDE68A; padding-bottom: 4px;")
        cust_lay.addWidget(cust_card_title)

        cust_form = QFormLayout()
        cust_form.setSpacing(6)
        cust_name = order.get("customer_name") or f"Customer #{order.get('customer_id', '')}"
        cust_form.addRow("<b>Customer Name:</b>", QLabel(str(cust_name)))
        contact_str = str(order.get("contact_number") or order.get("contact") or "—")
        cust_form.addRow("<b>Contact:</b>", QLabel(contact_str))
        email_str = str(order.get("email_address") or order.get("email") or "—")
        cust_form.addRow("<b>Email:</b>", QLabel(email_str))
        addr_str = str(order.get("delivery_address") or order.get("customer_registered_address") or order.get("address") or "—")
        cust_form.addRow("<b>Delivery Address:</b>", QLabel(addr_str))
        cust_lay.addLayout(cust_form)
        cards_row.addWidget(cust_card, 1)

        content_lay.addLayout(cards_row)

        # 3. Order Items Section
        items_sec_title = QLabel("Order Items & Specifications")
        items_sec_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0F172A;")
        content_lay.addWidget(items_sec_title)

        items_table = QTableWidget()
        items = order.get("items", [])
        items_table.setRowCount(len(items))
        items_table.setColumnCount(6)
        items_table.setHorizontalHeaderLabels([
            "Packaging Type", "Size / Spec", "Quantity", "Unit Price", "Discount", "Subtotal"
        ])
        items_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        items_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        items_table.setAlternatingRowColors(True)
        items_table.setStyleSheet("QTableWidget { background-color: #FFFFFF; alternate-background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; }")

        for r, it in enumerate(items):
            pkg = str(it.get("packaging_type") or "Item")
            sz = str(it.get("size") or "—")
            qty = int(it.get("quantity") or 1)
            uprice = _to_decimal(it.get("unit_price") or 0)
            disc = _to_decimal(it.get("discount") or 0)
            subtot = max(Decimal("0.00"), qty * uprice - disc)

            items_table.setItem(r, 0, QTableWidgetItem(pkg))
            items_table.setItem(r, 1, QTableWidgetItem(sz))
            items_table.setItem(r, 2, QTableWidgetItem(str(qty)))
            items_table.setItem(r, 3, QTableWidgetItem(f"P{uprice:,.2f}"))
            items_table.setItem(r, 4, QTableWidgetItem(f"P{disc:,.2f}"))
            items_table.setItem(r, 5, QTableWidgetItem(f"P{subtot:,.2f}"))

        items_table.setFixedHeight(max(100, min(240, 42 * (len(items) + 1))))
        content_lay.addWidget(items_table)

        # 4. Payments Table Section
        payments_sec_title = QLabel("Payments")
        payments_sec_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0F172A;")
        content_lay.addWidget(payments_sec_title)

        payments = order.get("payments", [])
        if payments:
            pay_table = QTableWidget()
            pay_table.setRowCount(len(payments))
            pay_table.setColumnCount(5)
            pay_table.setHorizontalHeaderLabels(["Type", "Method", "Amount", "Date", "Status"])
            pay_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            pay_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            pay_table.setAlternatingRowColors(True)
            pay_table.setStyleSheet("QTableWidget { background-color: #FFFFFF; alternate-background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; }")

            for r, p in enumerate(payments):
                ptype = str(p.get("payment_type") or "Payment")
                pmethod = str(p.get("payment_method") or "Cash")
                pamt = _to_decimal(p.get("amount_paid") or 0)
                pdate = str(p.get("payment_date") or "—")[:19]
                pst = str(p.get("status") or "Completed")

                pay_table.setItem(r, 0, QTableWidgetItem(ptype))
                pay_table.setItem(r, 1, QTableWidgetItem(pmethod))
                pay_table.setItem(r, 2, QTableWidgetItem(f"P{pamt:,.2f}"))
                pay_table.setItem(r, 3, QTableWidgetItem(pdate))
                pay_table.setItem(r, 4, QTableWidgetItem(pst))

            pay_table.setFixedHeight(max(80, min(180, 42 * (len(payments) + 1))))
            content_lay.addWidget(pay_table)
        else:
            no_pay_card = QFrame()
            no_pay_card.setStyleSheet("background-color: #FFFFFF; border: 1px dashed #CBD5E1; border-radius: 6px; padding: 12px;")
            no_pay_lay = QHBoxLayout(no_pay_card)
            no_pay_lbl = QLabel("No payment transactions recorded yet for this order.")
            no_pay_lbl.setStyleSheet("color: #94A3B8; font-style: italic; font-size: 13px;")
            no_pay_lay.addWidget(no_pay_lbl)
            content_lay.addWidget(no_pay_card)

        # 5. Financials Card Section
        fin_sec_title = QLabel("Financials")
        fin_sec_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0F172A;")
        content_lay.addWidget(fin_sec_title)

        fin_card = QFrame()
        fin_card.setObjectName("FinancialCard")
        fin_card.setStyleSheet("""
            QFrame#FinancialCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-left: 4px solid #D4AF37;
                border-radius: 8px;
            }
        """)
        fin_grid = QGridLayout(fin_card)
        fin_grid.setContentsMargins(18, 16, 18, 16)
        fin_grid.setHorizontalSpacing(24)
        fin_grid.setVerticalSpacing(10)

        tot = _to_decimal(order.get("total_amount") or 0)
        rush = _to_decimal(order.get("rush_charge") or 0)
        deducted = bool(order.get("is_design_fee_deducted"))
        deduct_str = f"Yes (-P{DESIGN_ASSURANCE_DEDUCTION:.2f})" if deducted else "No (P0.00)"
        paid = _to_decimal(order.get("amount_paid") or 0)
        bal = _to_decimal(order.get("balance") or (tot - paid))

        fin_grid.addWidget(QLabel("<b>Total Amount:</b>"), 0, 0)
        fin_grid.addWidget(QLabel(f"<span style='font-size: 15px; font-weight: bold; color: #0F172A;'>P{tot:,.2f}</span>"), 0, 1)

        fin_grid.addWidget(QLabel("<b>Rush Charge:</b>"), 0, 2)
        fin_grid.addWidget(QLabel(f"P{rush:,.2f}"), 0, 3)

        fin_grid.addWidget(QLabel("<b>Design Fee Deducted:</b>"), 1, 0)
        fin_grid.addWidget(QLabel(deduct_str), 1, 1)

        fin_grid.addWidget(QLabel("<b>Amount Paid:</b>"), 1, 2)
        fin_grid.addWidget(QLabel(f"<span style='color: #16A34A; font-weight: bold;'>P{paid:,.2f}</span>"), 1, 3)

        fin_grid.addWidget(QLabel("<b>Balance Due:</b>"), 2, 0)
        bal_color = "#DC2626" if bal > 0 else "#16A34A"
        fin_grid.addWidget(QLabel(f"<span style='color: {bal_color}; font-size: 15px; font-weight: bold;'>P{bal:,.2f}</span>"), 2, 1)

        content_lay.addWidget(fin_card)

        # Place content into scroll area
        scroll.setWidget(content)
        root_layout.addWidget(scroll, 1)

        # 6. Sticky Bottom Action Buttons Footer
        footer = QFrame()
        footer.setStyleSheet("background-color: #FFFFFF; border-top: 1px solid #E2E8F0;")
        footer_lay = QHBoxLayout(footer)
        footer_lay.setContentsMargins(24, 14, 24, 14)
        footer_lay.setSpacing(12)

        order_form_btn = QPushButton("Generate Order Form")
        order_form_btn.setObjectName("GoldPrimaryBtn")
        order_form_btn.setIcon(get_action_icon("download", "primary", 15))
        order_form_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        order_form_btn.setStyleSheet("""
            QPushButton#GoldPrimaryBtn {
                background-color: #D4AF37;
                color: #0F172A;
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #B45309;
                border-radius: 6px;
                padding: 9px 20px;
            }
            QPushButton#GoldPrimaryBtn:hover {
                background-color: #C5A028;
            }
            QPushButton#GoldPrimaryBtn:pressed {
                background-color: #B45309;
                color: #FFFFFF;
            }
        """)
        order_form_btn.clicked.connect(self._generate_order_form)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("SecondaryBtn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton#SecondaryBtn {
                background-color: #FFFFFF;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 9px 20px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton#SecondaryBtn:hover {
                background-color: #F8FAFC;
                color: #0F172A;
                border-color: #94A3B8;
            }
        """)
        close_btn.clicked.connect(self.accept)

        footer_lay.addWidget(order_form_btn)

        # Show Cancel Order button if order is in a cancellable status
        cur_st = str(order.get("status") or "Pending")
        if cur_st in CANCELLABLE_STATUSES:
            cancel_order_btn = QPushButton("Cancel Order")
            cancel_order_btn.setObjectName("DangerBtn")
            cancel_order_btn.setIcon(get_action_icon("trash", "danger", 14))
            cancel_order_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            cancel_order_btn.clicked.connect(self._cancel_order)
            footer_lay.addWidget(cancel_order_btn)

        footer_lay.addStretch(1)
        footer_lay.addWidget(close_btn)
        root_layout.addWidget(footer)

    def _generate_order_form(self) -> None:
        oid = self.order.get("order_id", 0)
        path, _ = QFileDialog.getSaveFileName(
            self, "Generate Order Form",
            f"order_form_{oid:05d}.pdf",
            "PDF (*.pdf)"
        )
        if not path:
            return
        try:
            generate_invoice_pdf(self.order, path)
            QMessageBox.information(
                self, "Order Form Generated",
                f"Order Form PDF successfully generated and saved to:\n{path}"
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to generate Order Form PDF:\n{exc}")

    def _cancel_order(self) -> None:
        oid = self.order.get("order_id", 0)
        cur_st = str(self.order.get("status") or "Pending")
        reply = QMessageBox.question(
            self, "Confirm Cancellation",
            f"Are you sure you want to cancel Order #{oid:05d} ({cur_st})?\n\n"
            f"This will mark the order as Cancelled.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        conn = get_connection()
        try:
            OrderManager(conn).cancel_order(oid)
            QMessageBox.information(self, "Order Cancelled", f"Order #{oid:05d} has been successfully cancelled.")
            if self.parent() and hasattr(self.parent(), "refresh"):
                self.parent().refresh()
            self.accept()
        except ValueError as exc:
            QMessageBox.warning(self, "Business Rule Violation", str(exc))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to cancel order:\n{exc}")
        finally:
            conn.close()


OrderDetailsDialog = OrderDetailDialog  # Backward-compatible alias


class OrderWidget(QWidget):
    """Sales & Order Management module with professional HCI layout."""

    def __init__(self, user: dict | None = None, parent=None):
        super().__init__(parent)
        self.user = user or {}
        self._active_status: str | None = None

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

        # 2. KPI Summary Cards Row (7 Status Cards + "All Orders" Reset Button)
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)

        # "All Orders" reset button on the left
        self.all_orders_btn = QPushButton("All Orders")
        self.all_orders_btn.setObjectName("AllOrdersFilterBtn")
        self.all_orders_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.all_orders_btn.setToolTip("View all orders without status filtering")
        self.all_orders_btn.setFixedHeight(76)
        self.all_orders_btn.setFixedWidth(105)
        self.all_orders_btn.clicked.connect(self._on_all_orders_clicked)
        kpi_row.addWidget(self.all_orders_btn, 0)

        self.status_cards: dict[str, StatusKpiCard] = {}
        for status in ORDER_STATUSES:
            card = StatusKpiCard(status, value=0, parent=self)
            card.clicked.connect(self._on_status_card_clicked)
            self.status_cards[status] = card
            kpi_row.addWidget(card, 1)

        layout.addLayout(kpi_row)

        # 3. Action Toolbar (Search & Date filters on left, action buttons on right)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.search = QLineEdit()
        self.search.setObjectName("TableSearchInput")
        self.search.addAction(get_icon("search", color="#94A3B8", size=16), QLineEdit.ActionPosition.LeadingPosition)
        self.search.setPlaceholderText("Search by order # or customer name...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._load_table_data)
        toolbar.addWidget(self.search, 2)

        # Date Pickers with Checkboxes
        self.from_check = QCheckBox("From:")
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDate(QDate.currentDate().addMonths(-1))
        self.from_date.dateChanged.connect(lambda: self.from_check.isChecked() and self._load_table_data())
        self.from_check.toggled.connect(self._load_table_data)

        self.to_check = QCheckBox("To:")
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDate(QDate.currentDate())
        self.to_date.dateChanged.connect(lambda: self.to_check.isChecked() and self._load_table_data())
        self.to_check.toggled.connect(self._load_table_data)

        toolbar.addWidget(self.from_check)
        toolbar.addWidget(self.from_date)
        toolbar.addWidget(self.to_check)
        toolbar.addWidget(self.to_date)

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

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("DangerBtn")
        self.cancel_btn.setIcon(get_action_icon("x-circle", "danger", 15))
        self.cancel_btn.setToolTip("Cancel selected order (Pending, Processing, In Progress only)")
        self.cancel_btn.clicked.connect(self.cancel_order)
        toolbar.addWidget(self.cancel_btn)

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

        # 4. Card Container wrapping the Table
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

        self.empty_label = QLabel("No orders found matching the selected filter.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #94A3B8; font-size: 14px; font-weight: 500; padding: 40px;")
        self.empty_label.setVisible(False)

        card_lay.addWidget(self.table)
        card_lay.addWidget(self.empty_label)
        layout.addWidget(card, 1)

        self._update_all_orders_btn(True)
        self.refresh()

    def _update_all_orders_btn(self, is_active: bool) -> None:
        self.all_orders_btn.setProperty("active", "true" if is_active else "false")
        if is_active:
            self.all_orders_btn.setIcon(get_action_icon("orders", "primary", 15))
            self.all_orders_btn.setStyleSheet("""
                QPushButton#AllOrdersFilterBtn {
                    background-color: #0F172A;
                    color: #FFFFFF;
                    border: 2px solid #0F172A;
                    border-radius: 8px;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 8px;
                }
                QPushButton#AllOrdersFilterBtn:hover {
                    background-color: #1E293B;
                    border-color: #1E293B;
                }
            """)
        else:
            self.all_orders_btn.setIcon(get_action_icon("orders", "secondary", 15))
            self.all_orders_btn.setStyleSheet("""
                QPushButton#AllOrdersFilterBtn {
                    background-color: #FFFFFF;
                    color: #475569;
                    border: 1px solid #E0E0E0;
                    border-radius: 8px;
                    font-size: 12px;
                    font-weight: 500;
                    padding: 8px;
                }
                QPushButton#AllOrdersFilterBtn:hover {
                    background-color: #F8FAFC;
                    border-color: #CBD5E1;
                    color: #0F172A;
                }
            """)
        style = self.all_orders_btn.style()
        if style:
            style.unpolish(self.all_orders_btn)
            style.polish(self.all_orders_btn)

    def _on_status_card_clicked(self, status: str) -> None:
        if self._active_status == status:
            # On Click Again (Toggle Off): Clear the filter (show all orders), Reset card to Default State
            self._active_status = None
        else:
            # On Click: Filter QTableWidget to show only orders with that status.
            # Change the clicked card to its Pressed/Active State (specific color).
            # Reset all other cards to the Default State (neutral white).
            self._active_status = status

        self._sync_status_ui()
        self._load_table_data()

    def _on_all_orders_clicked(self) -> None:
        self._active_status = None
        self._sync_status_ui()
        self._load_table_data()

    def _sync_status_ui(self) -> None:
        for st, card in self.status_cards.items():
            card.set_active(st == self._active_status)
        self._update_all_orders_btn(self._active_status is None)

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
        self.refresh_kpis()
        self._load_table_data()

    def refresh_kpis(self) -> None:
        conn = self._conn()
        try:
            counts = OrderManager(conn).count_orders_by_status()
            for status, card in self.status_cards.items():
                card.set_value(counts.get(status, 0))
        except Exception as exc:  # noqa: BLE001
            print(f"Warning: Failed to refresh status counts: {exc}")
        finally:
            conn.close()

    def _load_table_data(self) -> None:
        conn = self._conn()
        try:
            status_filter = self._active_status or ""
            from_date_str = self.from_date.date().toPyDate().isoformat() if self.from_check.isChecked() else None
            to_date_str = self.to_date.date().toPyDate().isoformat() if self.to_check.isChecked() else None
            rows = OrderManager(conn).list_orders(
                status_filter, self.search.text(),
                from_date=from_date_str, to_date=to_date_str
            )

            if not rows:
                self.table.setRowCount(0)
                self.table.setVisible(False)
                self.empty_label.setVisible(True)
                return

            self.empty_label.setVisible(False)
            self.table.setVisible(True)
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

    def new_order(self, preselected_customer_id: int | None = None) -> None:
        conn = self._conn()
        try:
            customers = CustomerManager(conn).list_customers()
        finally:
            conn.close()
        if not customers:
            QMessageBox.warning(self, "No Customers", "Please add at least one customer before creating an order.")
            return

        dlg = NewOrderDialog(self, customers=customers, preselected_customer_id=preselected_customer_id)
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
        order = self._load_selected()
        if not order:
            return
        oid = order.get("order_id", 0)
        current_status = str(order.get("status") or "Pending")

        d = QDialog(self)
        d.setWindowTitle(f"Update Order #{oid:05d} Status")
        d.setMinimumWidth(340)
        lay = QVBoxLayout(d)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(14)

        info_lbl = QLabel(f"Current Status: <b>{current_status}</b>")
        info_lbl.setStyleSheet("font-size: 13px; color: #1E293B;")
        lay.addWidget(info_lbl)

        lay.addWidget(QLabel("Select new production/delivery status:"))
        box = QComboBox()
        box.addItems(list(ORDER_STATUSES))
        idx = box.findText(current_status)
        if idx >= 0:
            box.setCurrentIndex(idx)
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
            new_status = box.currentText()
            if new_status == current_status:
                return

            if new_status == "Cancelled":
                if current_status in NON_CANCELLABLE_STATUSES:
                    QMessageBox.warning(
                        self,
                        "Cannot Cancel Order",
                        f"Business Rule Violation:\n\n"
                        f"Order #{oid:05d} currently has status '{current_status}' and cannot be cancelled.\n\n"
                        f"Business Rule:\n"
                        f"• Cannot cancel if status is: Paid, Ready, or Delivered.\n"
                        f"• Can cancel only if status is: Pending, Processing, or In Progress."
                    )
                    return
                reply = QMessageBox.question(
                    self,
                    "Confirm Cancellation",
                    f"Are you sure you want to cancel Order #{oid:05d}?\n\n"
                    f"This will mark the order as Cancelled.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

            conn = self._conn()
            try:
                OrderManager(conn).update_status(oid, new_status)
                self.refresh()
                QMessageBox.information(
                    self,
                    "Status Updated",
                    f"Order #{oid:05d} status updated to '{new_status}'."
                )
            except ValueError as exc:
                QMessageBox.warning(self, "Business Rule Violation", str(exc))
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Error", f"Failed to update status:\n{exc}")
            finally:
                conn.close()

    def cancel_order(self) -> None:
        order = self._load_selected()
        if not order:
            return
        oid = order.get("order_id", 0)
        current_status = str(order.get("status") or "Pending")

        if current_status in NON_CANCELLABLE_STATUSES:
            QMessageBox.warning(
                self,
                "Cannot Cancel Order",
                f"Business Rule Violation:\n\n"
                f"Order #{oid:05d} currently has status '{current_status}' and cannot be cancelled.\n\n"
                f"Business Rule:\n"
                f"• Cannot cancel if status is: Paid, Ready, or Delivered.\n"
                f"• Can cancel only if status is: Pending, Processing, or In Progress."
            )
            return

        if current_status == "Cancelled":
            QMessageBox.information(
                self,
                "Already Cancelled",
                f"Order #{oid:05d} is already marked as Cancelled."
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirm Cancellation",
            f"Are you sure you want to cancel Order #{oid:05d}?\n\n"
            f"Customer: {order.get('customer_name', 'N/A')}\n"
            f"Current Status: {current_status}\n"
            f"Total Amount: P{float(order.get('total_amount', 0)):,.2f}\n\n"
            f"This will mark the order as Cancelled.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        conn = self._conn()
        try:
            OrderManager(conn).cancel_order(oid)
            QMessageBox.information(
                self,
                "Order Cancelled",
                f"Order #{oid:05d} has been successfully cancelled."
            )
            self.refresh()
        except ValueError as exc:
            QMessageBox.warning(self, "Business Rule Violation", str(exc))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to cancel order:\n{exc}")
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
