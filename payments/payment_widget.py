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
    QFrame, QDoubleSpinBox, QScrollArea,
)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QDoubleValidator

from database.database import get_connection
from payments.payment_management import (
    PaymentManager, PAYMENT_TYPES, PAYMENT_METHODS, PAYMENT_STATUSES,
    PAYMENT_KPI_STATUSES,
)
from payments.receipt import generate_receipt_pdf
from ui.icons import get_icon, get_action_icon
from ui.kpi_card import StatusKpiCard
from sales_orders.sales_order_management import OrderManager

_PAYMENT_HEADERS = [
    "Payment #", "Customer Name", "Order #", "Type", "Method",
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
        self.selected_status: str | None = None
        self._orders_by_id: dict[int, dict] = {}

        # Root wrapper hosting a smooth QScrollArea so all controls and table remain fully accessible
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        scroll_content = QWidget()
        scroll_content.setObjectName("PaymentWidgetScrollContent")
        scroll_content.setStyleSheet("QWidget#PaymentWidgetScrollContent { background-color: #F8FAFC; }")

        layout = QVBoxLayout(scroll_content)
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

        # 2. KPI Summary Cards Row (5 Cards horizontally stretching equally)
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)

        self.status_cards: dict[str, StatusKpiCard] = {}
        for status in PAYMENT_KPI_STATUSES:
            card = StatusKpiCard(status, value=0, parent=self)
            card.clicked.connect(self._on_status_card_clicked)
            self.status_cards[status] = card
            kpi_row.addWidget(card, 1)

        layout.addLayout(kpi_row)

        # 3. Inline Record Payment Card (Directly above search bar, no pop-up dialog)
        form_card = QFrame()
        form_card.setObjectName("ModuleCardContainer")
        form_lay = QVBoxLayout(form_card)
        form_lay.setContentsMargins(18, 14, 18, 14)
        form_lay.setSpacing(10)

        form_header = QHBoxLayout()
        form_header.setSpacing(8)
        form_title = QLabel("Record Payment")
        form_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #0F172A;")
        form_subtitle = QLabel("— Process customer payments and settle active orders directly")
        form_subtitle.setStyleSheet("font-size: 12px; color: #64748B;")
        form_header.addWidget(form_title)
        form_header.addWidget(form_subtitle)
        form_header.addStretch(1)
        form_lay.addLayout(form_header)

        # Dynamic Order Balance / Selection Hint Label
        self.inline_preview_label = QLabel("Standalone payment — not linked to any order.")
        self.inline_preview_label.setStyleSheet("color: #475569; font-size: 12px; padding: 2px 0px;")
        form_lay.addWidget(self.inline_preview_label)

        # Row 1: Linked Order, Payment Type, Payment Method, Payment Date
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        self.input_order = QComboBox()
        self.input_order.setFixedHeight(36)
        self.input_order.currentIndexChanged.connect(self._on_inline_order_changed)

        self.input_type = QComboBox()
        self.input_type.addItems(list(PAYMENT_TYPES))
        self.input_type.setCurrentText("ProductOrder")
        self.input_type.setFixedHeight(36)

        self.input_method = QComboBox()
        self.input_method.addItems(list(PAYMENT_METHODS))
        self.input_method.setCurrentText("Cash")
        self.input_method.setFixedHeight(36)

        self.input_date = QDateEdit()
        self.input_date.setCalendarPopup(True)
        self.input_date.setDate(QDate.currentDate())
        self.input_date.setFixedHeight(36)

        row1.addWidget(self.input_order, 4)
        row1.addWidget(self.input_type, 2)
        row1.addWidget(self.input_method, 2)
        row1.addWidget(self.input_date, 2)
        form_lay.addLayout(row1)

        # Row 2: Amount Paid, Payment Status, Record Payment Button, Clear Button
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        self.input_amount = QDoubleSpinBox()
        self.input_amount.setRange(0.00, 10_000_000.00)
        self.input_amount.setDecimals(2)
        self.input_amount.setValue(0.00)
        self.input_amount.setPrefix("Amount: P")
        self.input_amount.setFixedHeight(36)

        self.input_status = QComboBox()
        self.input_status.addItems(list(PAYMENT_STATUSES))
        self.input_status.setCurrentText("Completed")
        self.input_status.setFixedHeight(36)

        self.record_payment_btn = QPushButton("Record Payment")
        self.record_payment_btn.setIcon(get_action_icon("plus", "primary", 15))
        self.record_payment_btn.setFixedHeight(36)
        self.record_payment_btn.setFixedWidth(150)
        self.record_payment_btn.clicked.connect(self.record_payment)

        self.clear_payment_btn = QPushButton("Clear")
        self.clear_payment_btn.setObjectName("SecondaryBtn")
        self.clear_payment_btn.setFixedHeight(36)
        self.clear_payment_btn.clicked.connect(self.clear_payment_form)

        row2.addWidget(self.input_amount, 3)
        row2.addWidget(self.input_status, 2)
        row2.addWidget(self.record_payment_btn)
        row2.addWidget(self.clear_payment_btn)
        form_lay.addLayout(row2)

        layout.addWidget(form_card)

        # Alias for backward compatibility
        self.record_btn = self.record_payment_btn

        # 4. Action Toolbar (Search & Payment Type on left, Actions on right)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        # Live Search
        self.search = QLineEdit()
        self.search.setObjectName("TableSearchInput")
        self.search.addAction(get_icon("search", color="#94A3B8", size=16), QLineEdit.ActionPosition.LeadingPosition)
        self.search.setPlaceholderText("Search customer name, order #, method, or recorder...")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(260)
        self.search.textChanged.connect(self._load_table_data)
        toolbar.addWidget(self.search, 1)

        # Payment Type Filter
        self.type_filter = QComboBox()
        self.type_filter.setObjectName("TableFilterCombo")
        self.type_filter.addItem("All Payment Types", "")
        for t in PAYMENT_TYPES:
            self.type_filter.addItem(t, t)
        self.type_filter.currentIndexChanged.connect(self._load_table_data)
        toolbar.addWidget(self.type_filter)

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

        layout.addLayout(toolbar)

        # 5. Card Container wrapping Table
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
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        # Status column fixed and well-proportioned
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(7, 130)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.doubleClicked.connect(self.print_receipt)
        # Visually hide the ID column (#1, #2, etc.) while retaining row item at column 0 for internal logic
        self.table.setColumnHidden(0, True)

        card_lay.addWidget(self.table)
        layout.addWidget(card, 1)

        self.scroll_area.setWidget(scroll_content)
        root_layout.addWidget(self.scroll_area, 1)

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
        container.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(container)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        st_upper = (status_prop or "").strip().upper()
        if "COMPLETED" in st_upper:
            bg_col, text_col, border_col = "#DCFCE7", "#15803D", "#86EFAC"  # Emerald / Green
        elif "PENDING" in st_upper:
            bg_col, text_col, border_col = "#FEF3C7", "#92400E", "#FCD34D"  # Warm Amber
        elif "REFUNDED" in st_upper:
            bg_col, text_col, border_col = "#F3E8FF", "#6B21A8", "#D8B4FE"  # Royal Purple
        elif "CANCELLED" in st_upper or "CANCELED" in st_upper:
            bg_col, text_col, border_col = "#FEE2E2", "#B91C1C", "#FCA5A5"  # Crimson Red
        else:
            bg_col, text_col, border_col = "#F1F5F9", "#475569", "#CBD5E1"  # Neutral Slate

        pill = QLabel(f" {text} ")
        pill.setFixedHeight(26)
        pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pill.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_col};
                color: {text_col};
                border: 1.5px solid {border_col};
                border-radius: 13px;
                padding: 2px 14px;
                font-size: 11px;
                font-weight: 700;
            }}
        """)
        lay.addWidget(pill)
        return container

    # -- Core logic --
    def _on_status_card_clicked(self, status: str) -> None:
        if self.selected_status == status:
            # Clicked active card again: toggle off, clear filter
            self.selected_status = None
            if status in self.status_cards:
                self.status_cards[status].set_active(False)
        else:
            # Activate clicked card, reset all others to default white
            self.selected_status = status
            for s, card in self.status_cards.items():
                card.set_active(s == status)

        self._load_table_data()

    def _load_status_counts(self) -> None:
        conn = self._conn()
        try:
            counts = PaymentManager(conn).count_payments_by_status()
            for s, card in self.status_cards.items():
                card.set_value(counts.get(s, 0))
        except Exception:  # noqa: BLE001
            pass
        finally:
            conn.close()

    def _load_table_data(self) -> None:
        conn = self._conn()
        try:
            ptype = self.type_filter.currentData() or ""
            rows = PaymentManager(conn).list_payments(payment_type=ptype)

            # Filter by selected KPI status if active
            if self.selected_status:
                rows = [
                    r for r in rows
                    if (r.get("status") or "").lower() == self.selected_status.lower()
                ]

            # Filter by search needle
            needle = self.search.text().strip().lower()
            if needle:
                rows = [
                    r for r in rows
                    if needle in str(r.get("payment_id") or "").lower()
                    or needle in str(r.get("customer_name") or "").lower()
                    or needle in str(r.get("order_id") or "").lower()
                    or needle in str(r.get("payment_type") or "").lower()
                    or needle in str(r.get("payment_method") or "").lower()
                    or needle in str(r.get("processed_by") or "").lower()
                ]

            self.table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                pid = row.get("payment_id")
                cname = row.get("customer_name") or "—"
                oid = row.get("order_id")
                ptype = row.get("payment_type") or "ProductOrder"
                method = row.get("payment_method") or "Cash"
                amt = Decimal(str(row.get("amount_paid") or 0))
                pdate = str(row.get("payment_date") or "")
                status = str(row.get("status") or "Completed")
                by_user = str(row.get("processed_by") or "—")

                # Column 0: Payment #
                self.table.setItem(r, 0, QTableWidgetItem(f"#{pid}"))
                # Column 1: Customer Name (NEW)
                self.table.setItem(r, 1, QTableWidgetItem(str(cname)))
                # Column 2: Order #
                self.table.setItem(r, 2, QTableWidgetItem(f"#{oid}" if oid is not None else "— (Layout)"))
                # Column 3: Type
                self.table.setItem(r, 3, QTableWidgetItem(str(ptype)))
                # Column 4: Method
                self.table.setItem(r, 4, QTableWidgetItem(str(method)))
                # Column 5: Amount Paid
                self.table.setItem(r, 5, QTableWidgetItem(f"P{amt:,.2f}"))
                # Column 6: Date
                self.table.setItem(r, 6, QTableWidgetItem(pdate))
                # Column 7: Status (Pill)
                self.table.setCellWidget(r, 7, self._create_pill_widget(status, status))
                # Column 8: Processed By
                self.table.setItem(r, 8, QTableWidgetItem(by_user))

        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to load payments:\n{exc}")
        finally:
            conn.close()

    def refresh(self) -> None:
        self._populate_orders_dropdown()
        self._load_status_counts()
        self._load_table_data()

    def _open_orders(self) -> list[dict]:
        from reports.reports import ReportManager
        conn = self._conn()
        try:
            return ReportManager(conn).unpaid_orders()
        except Exception:  # noqa: BLE001
            return []
        finally:
            conn.close()

    def _populate_orders_dropdown(self) -> None:
        if not hasattr(self, "input_order"):
            return
        current_data = self.input_order.currentData()
        orders = self._open_orders()
        self._orders_by_id = {o["order_id"]: o for o in orders}

        self.input_order.blockSignals(True)
        self.input_order.clear()
        self.input_order.addItem("Standalone Payment (No order linked)", None)
        for o in orders:
            oid = o.get("order_id")
            cname = o.get("customer") or "Customer"
            bal = Decimal(str(o.get("balance", 0)))
            self.input_order.addItem(f"Order #{oid:05d} — {cname} (Bal: P{bal:,.2f})", oid)

        # Restore selection if still present
        if current_data is not None:
            idx = self.input_order.findData(current_data)
            if idx >= 0:
                self.input_order.setCurrentIndex(idx)
        self.input_order.blockSignals(False)
        self._on_inline_order_changed()

    def _on_inline_order_changed(self) -> None:
        if not hasattr(self, "input_order") or not hasattr(self, "inline_preview_label"):
            return
        oid = self.input_order.currentData()
        if oid is None or oid not in self._orders_by_id:
            self.inline_preview_label.setText("Standalone payment — not linked to any order.")
            return

        order = self._orders_by_id[oid]
        total = Decimal(str(order.get("total_amount", 0)))
        paid = Decimal(str(order.get("paid", 0)))
        balance = Decimal(str(order.get("balance", total - paid)))

        self.inline_preview_label.setText(
            f"<b>Order #{oid:05d}</b> for <i>{order.get('customer', 'Customer')}</i> &nbsp;|&nbsp; "
            f"Total: <b>P{total:,.2f}</b> &nbsp;|&nbsp; Paid: <b>P{paid:,.2f}</b> &nbsp;|&nbsp; "
            f"<span style='color: #B45309;'>Remaining Balance: <b>P{balance:,.2f}</b></span>"
        )
        if self.input_amount.value() <= 0:
            self.input_amount.setValue(float(balance))

    def clear_payment_form(self) -> None:
        if hasattr(self, "input_order"):
            self.input_order.setCurrentIndex(0)
        if hasattr(self, "input_type"):
            self.input_type.setCurrentText("ProductOrder")
        if hasattr(self, "input_method"):
            self.input_method.setCurrentText("Cash")
        if hasattr(self, "input_amount"):
            self.input_amount.setValue(0.00)
        if hasattr(self, "input_date"):
            self.input_date.setDate(QDate.currentDate())
        if hasattr(self, "input_status"):
            self.input_status.setCurrentText("Completed")
        if hasattr(self, "inline_preview_label"):
            self.inline_preview_label.setText("Standalone payment — not linked to any order.")

    def record_payment(self) -> None:
        amt = Decimal(str(self.input_amount.value()))
        if amt <= 0:
            QMessageBox.warning(self, "Record Payment", "Please enter a valid payment amount greater than zero.")
            self.input_amount.setFocus()
            return

        order_id = self.input_order.currentData()
        ptype = self.input_type.currentText()
        pmethod = self.input_method.currentText()
        pdate = self.input_date.date().toPyDate().isoformat()
        status = self.input_status.currentText()

        conn = self._conn()
        try:
            mgr = PaymentManager(conn)
            pid = mgr.record_payment(
                self._user_id(), str(amt),
                payment_type=ptype,
                payment_method=pmethod,
                order_id=order_id, status=status
            )
            if pdate:
                cur = conn.cursor()
                try:
                    cur.execute("UPDATE payments SET payment_date = %s WHERE payment_id = %s",
                                (pdate, pid))
                    conn.commit()
                finally:
                    cur.close()

            bal_str = ""
            if order_id is not None:
                bal = mgr.order_balance(order_id)
                bal_str = f"\nOrder #{order_id:05d} Balance: P{bal['balance']:,.2f}"

            QMessageBox.information(
                self, "Payment Recorded",
                f"Payment recorded successfully for P{amt:,.2f}.{bal_str}"
            )
            self.clear_payment_form()
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
