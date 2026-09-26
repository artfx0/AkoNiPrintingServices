"""Admin/Owner dashboard — full access to all 7 use cases + user accounts."""
from __future__ import annotations

from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QPushButton, QDialog, QFormLayout, QLineEdit, QMessageBox,
    QComboBox, QDoubleSpinBox, QSpinBox, QCheckBox, QTextEdit, QLabel,
    QFileDialog, QHeaderView, QDateEdit, QAbstractItemView, QToolBar,
)
from PyQt6.QtCore import QDateTime

from database.database import get_connection
from customers.customer_management import CustomerManager
from sales_orders.sales_order_management import (
    OrderManager, ORDER_TYPES, ORDER_STATUSES, DESIGN_ASSURANCE_DEDUCTION)
from payments.payment_management import (
    PaymentManager, PAYMENT_TYPES, PAYMENT_METHODS)
from inventory.inventory_management import (
    MaterialManager, StockMovementManager, MOVEMENT_TYPES)
from expenses.expense_management import ExpenseManager, EXPENSE_CATEGORIES
from reports.reports import ReportManager
from backup.backup_restore import BackupManager
from auth.user_management import UserManager


def _table(rows: list[dict], headers: list[str], table: QTableWidget) -> None:
    table.setRowCount(len(rows))
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    for r, row in enumerate(rows):
        for c, h in enumerate(headers):
            val = row.get(h, "")
            if val is None:
                val = ""
            table.setItem(r, c, QTableWidgetItem(str(val)))
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)


def _selected_id(table: QTableWidget, id_col: int = 0) -> int | None:
    row = table.currentRow()
    if row < 0:
        return None
    try:
        return int(table.item(row, id_col).text())
    except (AttributeError, ValueError):
        return None


class _FormDialog(QDialog):
    """Generic form dialog; `fields` = list of (key, label, widget)."""
    def __init__(self, title: str, fields, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._widgets = {}
        layout = QVBoxLayout(self)
        form = QFormLayout()
        for key, label, widget in fields:
            form.addRow(label, widget)
            self._widgets[key] = widget
        layout.addLayout(form)
        btns = QHBoxLayout()
        ok = QPushButton("Save")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        btns.addWidget(ok)
        btns.addWidget(cancel)
        layout.addLayout(btns)

    def widget(self, key):
        return self._widgets[key]


class AdminDashboard(QMainWindow):
    """Full-access Admin window (all 7 use cases + users). Staff gets StaffDashboard."""

    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.logout_requested = False
        self.setWindowTitle(f"AkoNi Printing — Admin ({user['username']})")
        self.resize(1100, 700)
        self._setup_header()
        tabs = QTabWidget()
        self.setCentralWidget(tabs)
        tabs.addTab(self._customers_tab(), "Customers")
        tabs.addTab(self._orders_tab(), "Sales / Orders")
        tabs.addTab(self._payments_tab(), "Payments")
        tabs.addTab(self._inventory_tab(), "Inventory")
        tabs.addTab(self._expenses_tab(), "Expenses")
        tabs.addTab(self._reports_tab(), "Reports")
        tabs.addTab(self._backup_tab(), "Backup")
        tabs.addTab(self._users_tab(), "Users")

    # ---------- session / header ----------
    def _setup_header(self) -> None:
        bar = QToolBar("Session")
        bar.setMovable(False)
        name = f"{self.user.get('first_name', '')} {self.user.get('last_name', '')}".strip()
        bar.addWidget(QLabel(f"Logged in: {self.user.get('username', '')}"
                             f" ({self.user.get('role', '')})"
                             f"{' — ' + name if name else ''}  "))
        bar.addSeparator()
        logout_btn = QPushButton("Logout")
        logout_btn.clicked.connect(self.request_logout)
        bar.addWidget(logout_btn)
        self.addToolBar(bar)

    def request_logout(self) -> None:
        from auth.session import Session
        Session.clear()
        self.logout_requested = True
        self.close()

    # ---------- helpers ----------
    def _conn(self):
        return get_connection()

    def _err(self, exc: Exception):
        QMessageBox.critical(self, "Error", str(exc))

    # ---------- Customers ----------
    def _customers_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.cust_search = QLineEdit()
        self.cust_search.setPlaceholderText("Search name / contact / email…")
        self.cust_table = QTableWidget()
        layout.addWidget(self.cust_search)
        layout.addWidget(self.cust_table)
        btns = QHBoxLayout()
        for label, fn in [("Refresh", self.refresh_customers), ("Add", self.add_customer),
                          ("Edit", self.edit_customer), ("Delete", self.delete_customer)]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            btns.addWidget(b)
        layout.addLayout(btns)
        self.cust_search.textChanged.connect(self.refresh_customers)
        self.refresh_customers()
        return w

    def refresh_customers(self):
        conn = self._conn()
        try:
            rows = CustomerManager(conn).list_customers(self.cust_search.text())
            _table(rows, ["customer_id", "first_name", "last_name", "contact_number",
                          "email_address", "address", "created_at"], self.cust_table)
        except Exception as exc:  # noqa: BLE001
            self._err(exc)
        finally:
            conn.close()

    def add_customer(self):
        d = _FormDialog("Add customer", [
            ("first_name", "First name:", QLineEdit()),
            ("last_name", "Last name:", QLineEdit()),
            ("contact_number", "Contact #:", QLineEdit()),
            ("email_address", "Email:", QLineEdit()),
            ("address", "Address:", QLineEdit()),
        ], self)
        if d.exec():
            conn = self._conn()
            try:
                CustomerManager(conn).create_customer(
                    d.widget("first_name").text(), d.widget("last_name").text(),
                    d.widget("contact_number").text(), d.widget("email_address").text(),
                    d.widget("address").text())
                self.refresh_customers()
            except Exception as exc:  # noqa: BLE001
                self._err(exc)
            finally:
                conn.close()

    def edit_customer(self):
        cid = _selected_id(self.cust_table)
        if cid is None:
            QMessageBox.warning(self, "Customers", "Select a row first.")
            return
        conn = self._conn()
        try:
            cur = CustomerManager(conn).get_customer(cid)
        finally:
            conn.close()
        fields = []
        for key, label in [("first_name", "First name:"), ("last_name", "Last name:"),
                           ("contact_number", "Contact #:"), ("email_address", "Email:"),
                           ("address", "Address:")]:
            edit = QLineEdit(str(cur.get(key) or ""))
            fields.append((key, label, edit))
        d = _FormDialog("Edit customer", fields, self)
        if d.exec():
            conn = self._conn()
            try:
                CustomerManager(conn).update_customer(
                    cid, **{k: d.widget(k).text() for k in
                            ["first_name", "last_name", "contact_number",
                             "email_address", "address"]})
                self.refresh_customers()
            except Exception as exc:  # noqa: BLE001
                self._err(exc)
            finally:
                conn.close()

    def delete_customer(self):
        cid = _selected_id(self.cust_table)
        if cid is None:
            return
        if QMessageBox.question(self, "Delete", f"Delete customer {cid}?") \
                != QMessageBox.StandardButton.Yes:
            return
        conn = self._conn()
        try:
            CustomerManager(conn).delete_customer(cid)
            self.refresh_customers()
        except Exception as exc:  # noqa: BLE001
            self._err(exc)
        finally:
            conn.close()

    # ---------- Orders ----------
    def _orders_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        filt = QHBoxLayout()
        self.order_status = QComboBox()
        self.order_status.addItems([""] + list(ORDER_STATUSES))
        self.order_search = QLineEdit()
        self.order_search.setPlaceholderText("Customer search…")
        filt.addWidget(QLabel("Status:"))
        filt.addWidget(self.order_status)
        filt.addWidget(self.order_search)
        layout.addLayout(filt)
        self.order_table = QTableWidget()
        layout.addWidget(self.order_table)
        btns = QHBoxLayout()
        for label, fn in [("Refresh", self.refresh_orders), ("New order", self.new_order),
                          ("View / Pay info", self.view_order),
                          ("Set status", self.set_order_status)]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            btns.addWidget(b)
        layout.addLayout(btns)
        self.order_status.currentTextChanged.connect(self.refresh_orders)
        self.order_search.textChanged.connect(self.refresh_orders)
        self.refresh_orders()
        return w

    def refresh_orders(self):
        conn = self._conn()
        try:
            rows = OrderManager(conn).list_orders(self.order_status.currentText(),
                                                  self.order_search.text())
            _table(rows, ["order_id", "customer_name", "order_type", "order_date",
                          "expected_delivery_date", "status", "rush_charge",
                          "total_amount", "is_design_fee_deducted"], self.order_table)
        except Exception as exc:  # noqa: BLE001
            self._err(exc)
        finally:
            conn.close()

    def new_order(self):
        conn = self._conn()
        try:
            customers = CustomerManager(conn).list_customers()
        finally:
            conn.close()
        if not customers:
            QMessageBox.warning(self, "Orders", "Add a customer first.")
            return
        cust_box = QComboBox()
        for c in customers:
            cust_box.addItem(f"{c['customer_id']}: {c['first_name']} {c['last_name']}",
                             c["customer_id"])
        type_box = QComboBox()
        type_box.addItems(list(ORDER_TYPES))
        qty = QSpinBox()
        qty.setRange(1, 100000)
        price = QDoubleSpinBox()
        price.setRange(0, 10_000_000)
        price.setValue(100)
        discount = QDoubleSpinBox()
        discount.setRange(0, 10_000_000)
        rush = QDoubleSpinBox()
        rush.setRange(0, 1_000_000)
        deduct = QCheckBox(f"Deduct P{DESIGN_ASSURANCE_DEDUCTION} assurance/design fee")
        size, pack, finish = QLineEdit(), QLineEdit(), QLineEdit()
        d = _FormDialog("New order (single-item quick entry)", [
            ("customer", "Customer:", cust_box), ("order_type", "Type:", type_box),
            ("quantity", "Qty:", qty), ("unit_price", "Unit price:", price),
            ("discount", "Discount:", discount), ("rush", "Rush charge:", rush),
            ("deduct", "Deduction:", deduct), ("size", "Size:", size),
            ("packaging", "Packaging:", pack), ("finish", "Finish:", finish),
        ], self)
        if d.exec():
            conn = self._conn()
            try:
                oid = OrderManager(conn).create_order(
                    cust_box.currentData(), self.user["user_id"],
                    order_type=type_box.currentText(), rush_charge=rush.value(),
                    is_design_fee_deducted=deduct.isChecked(),
                    items=[{"quantity": qty.value(), "unit_price": price.value(),
                            "discount": discount.value(), "size": size.text(),
                            "packaging_type": pack.text(), "finish_type": finish.text()}])
                QMessageBox.information(self, "Orders", f"Order {oid} created.")
                self.refresh_orders()
            except Exception as exc:  # noqa: BLE001
                self._err(exc)
            finally:
                conn.close()

    def view_order(self):
        oid = _selected_id(self.order_table)
        if oid is None:
            QMessageBox.warning(self, "Orders", "Select a row first.")
            return
        conn = self._conn()
        try:
            order = OrderManager(conn).get_order(oid)
            bal = PaymentManager(conn).order_balance(oid)
        except Exception as exc:  # noqa: BLE001
            conn.close()
            self._err(exc)
            return
        conn.close()
        items = "\n".join(
            f"#{i['order_item_id']} {i.get('size','')} x{i['quantity']} @ {i['unit_price']}"
            for i in order["items"])
        QMessageBox.information(
            self, f"Order {oid}",
            f"Total: {order['total_amount']}\nPaid: {bal['paid']}\n"
            f"Balance: {bal['balance']}\nStatus: {order['status']}\n\nItems:\n{items}")

    def set_order_status(self):
        oid = _selected_id(self.order_table)
        if oid is None:
            return
        box = QComboBox()
        box.addItems(list(ORDER_STATUSES))
        d = _FormDialog("Set status", [("status", "Status:", box)], self)
        if d.exec():
            conn = self._conn()
            try:
                OrderManager(conn).update_status(oid, box.currentText())
                self.refresh_orders()
            except Exception as exc:  # noqa: BLE001
                self._err(exc)
            finally:
                conn.close()

    # ---------- Payments ----------
    def _payments_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.pay_table = QTableWidget()
        layout.addWidget(self.pay_table)
        btns = QHBoxLayout()
        for label, fn in [("Refresh", self.refresh_payments), ("Record payment", self.add_payment),
                          ("Void", self.void_payment)]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            btns.addWidget(b)
        layout.addLayout(btns)
        self.refresh_payments()
        return w

    def refresh_payments(self):
        conn = self._conn()
        try:
            rows = PaymentManager(conn).list_payments()
            _table(rows, ["payment_id", "order_id", "payment_type", "payment_method",
                          "amount_paid", "payment_date", "status", "processed_by"],
                   self.pay_table)
        except Exception as exc:  # noqa: BLE001
            self._err(exc)
        finally:
            conn.close()

    def add_payment(self):
        order_edit = QLineEdit()
        order_edit.setPlaceholderText("blank = Layout-Only payment")
        type_box = QComboBox()
        type_box.addItems(list(PAYMENT_TYPES))
        method_box = QComboBox()
        method_box.addItems(list(PAYMENT_METHODS))
        amount = QDoubleSpinBox()
        amount.setRange(0.01, 10_000_000)
        amount.setValue(500)
        d = _FormDialog("Record payment", [
            ("order_id", "Order ID (optional):", order_edit),
            ("payment_type", "Type:", type_box),
            ("payment_method", "Method:", method_box),
            ("amount", "Amount:", amount),
        ], self)
        if d.exec():
            raw = order_edit.text().strip()
            oid = int(raw) if raw else None
            conn = self._conn()
            try:
                pid = PaymentManager(conn).record_payment(
                    self.user["user_id"], amount.value(),
                    payment_type=type_box.currentText(),
                    payment_method=method_box.currentText(), order_id=oid)
                QMessageBox.information(self, "Payments", f"Payment {pid} recorded.")
                self.refresh_payments()
            except Exception as exc:  # noqa: BLE001
                self._err(exc)
            finally:
                conn.close()

    def void_payment(self):
        pid = _selected_id(self.pay_table)
        if pid is None:
            return
        conn = self._conn()
        try:
            PaymentManager(conn).void_payment(pid)
            self.refresh_payments()
        except Exception as exc:  # noqa: BLE001
            self._err(exc)
        finally:
            conn.close()

    # ---------- Inventory (shared logic) ----------
    def _inventory_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Materials"))
        self.mat_table = QTableWidget()
        layout.addWidget(self.mat_table)
        row = QHBoxLayout()
        for label, fn in [("Refresh", self.refresh_inventory), ("Add material", self.add_material),
                          ("Edit material", self.edit_material),
                          ("Stock IN/OUT", self.stock_move)]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            row.addWidget(b)
        layout.addLayout(row)
        layout.addWidget(QLabel("Recent movements"))
        self.mov_table = QTableWidget()
        layout.addWidget(self.mov_table)
        self.refresh_inventory()
        return w

    def refresh_inventory(self):
        conn = self._conn()
        try:
            mats = MaterialManager(conn).list_materials()
            _table(mats, ["material_id", "material_name", "unit_of_measure",
                          "current_stock_qty", "low_stock_threshold", "cost_per_unit"],
                   self.mat_table)
            movs = StockMovementManager(conn).list_movements(limit=100)
            _table(movs, ["movement_id", "material_name", "movement_type", "quantity",
                          "reason", "movement_date", "recorded_by"], self.mov_table)
        except Exception as exc:  # noqa: BLE001
            self._err(exc)
        finally:
            conn.close()

    def add_material(self):
        name = QLineEdit()
        uom = QLineEdit()
        uom.setText("pcs")
        stock = QSpinBox()
        stock.setRange(0, 1_000_000)
        thresh = QSpinBox()
        thresh.setRange(0, 1_000_000)
        thresh.setValue(10)
        cost = QDoubleSpinBox()
        cost.setRange(0, 1_000_000)
        d = _FormDialog("Add material", [
            ("name", "Name:", name), ("uom", "Unit:", uom), ("stock", "Opening qty:", stock),
            ("thresh", "Low-stock at:", thresh), ("cost", "Cost/unit:", cost)], self)
        if d.exec():
            conn = self._conn()
            try:
                MaterialManager(conn).create_material(
                    name.text(), uom.text(), stock.value(), thresh.value(), cost.value())
                self.refresh_inventory()
            except Exception as exc:  # noqa: BLE001
                self._err(exc)
            finally:
                conn.close()

    def edit_material(self):
        mid = _selected_id(self.mat_table)
        if mid is None:
            QMessageBox.warning(self, "Inventory", "Select a material first.")
            return
        thresh = QSpinBox()
        thresh.setRange(0, 1_000_000)
        cost = QDoubleSpinBox()
        cost.setRange(0, 1_000_000)
        name = QLineEdit()
        d = _FormDialog("Edit material", [
            ("name", "Name:", name), ("thresh", "Low-stock at:", thresh),
            ("cost", "Cost/unit:", cost)], self)
        if d.exec():
            conn = self._conn()
            try:
                kwargs = {"low_stock_threshold": thresh.value(), "cost_per_unit": cost.value()}
                if name.text().strip():
                    kwargs["material_name"] = name.text().strip()
                MaterialManager(conn).update_material(mid, **kwargs)
                self.refresh_inventory()
            except Exception as exc:  # noqa: BLE001
                self._err(exc)
            finally:
                conn.close()

    def stock_move(self):
        mid = _selected_id(self.mat_table)
        if mid is None:
            QMessageBox.warning(self, "Inventory", "Select a material first.")
            return
        type_box = QComboBox()
        type_box.addItems(list(MOVEMENT_TYPES))
        qty = QSpinBox()
        qty.setRange(1, 1_000_000)
        reason = QLineEdit()
        d = _FormDialog("Stock movement", [
            ("type", "Type:", type_box), ("qty", "Qty (OUT deducts; ADJUSTMENT sets):", qty),
            ("reason", "Reason:", reason)], self)
        if d.exec():
            conn = self._conn()
            try:
                StockMovementManager(conn).record_movement(
                    mid, self.user["user_id"], type_box.currentText(),
                    qty.value(), reason.text())
                self.refresh_inventory()
            except Exception as exc:  # noqa: BLE001
                self._err(exc)
            finally:
                conn.close()

    # ---------- Expenses ----------
    def _expenses_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.exp_table = QTableWidget()
        layout.addWidget(self.exp_table)
        btns = QHBoxLayout()
        for label, fn in [("Refresh", self.refresh_expenses), ("Add", self.add_expense),
                          ("Delete", self.delete_expense)]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            btns.addWidget(b)
        layout.addLayout(btns)
        self.refresh_expenses()
        return w

    def refresh_expenses(self):
        conn = self._conn()
        try:
            rows = ExpenseManager(conn).list_expenses()
            _table(rows, ["expense_id", "category", "amount", "expense_date",
                          "description", "recorded_by"], self.exp_table)
        except Exception as exc:  # noqa: BLE001
            self._err(exc)
        finally:
            conn.close()

    def add_expense(self):
        cat = QComboBox()
        cat.setEditable(False)
        cat.addItems(list(EXPENSE_CATEGORIES))
        amount = QDoubleSpinBox()
        amount.setRange(0.01, 10_000_000)
        desc = QLineEdit()
        d = _FormDialog("Add expense", [
            ("category", "Category:", cat), ("amount", "Amount:", amount),
            ("description", "Description:", desc)], self)
        if d.exec():
            conn = self._conn()
            try:
                ExpenseManager(conn).create_expense(
                    cat.currentText(), amount.value(), desc.text(),
                    recorded_by_user_id=self.user["user_id"])
                self.refresh_expenses()
            except Exception as exc:  # noqa: BLE001
                self._err(exc)
            finally:
                conn.close()

    def delete_expense(self):
        eid = _selected_id(self.exp_table)
        if eid is None:
            return
        conn = self._conn()
        try:
            ExpenseManager(conn).delete_expense(eid)
            self.refresh_expenses()
        except Exception as exc:  # noqa: BLE001
            self._err(exc)
        finally:
            conn.close()

    # ---------- Reports ----------
    def _reports_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.report_out = QTextEdit()
        self.report_out.setReadOnly(True)
        layout.addWidget(self.report_out)
        row = QHBoxLayout()
        gen = QPushButton("Generate summary")
        gen.clicked.connect(self.generate_report)
        export = QPushButton("Export unpaid orders CSV")
        export.clicked.connect(self.export_unpaid)
        row.addWidget(gen)
        row.addWidget(export)
        layout.addLayout(row)
        return w

    def generate_report(self):
        conn = self._conn()
        try:
            mgr = ReportManager(conn)
            pl = mgr.profit_loss()
            unpaid = mgr.unpaid_orders()
            inv = [m for m in mgr.inventory_status() if m["current_stock_qty"]
                   <= m["low_stock_threshold"]]
            self.report_out.setPlainText(
                f"Revenue collected: {pl['revenue_collected']}\n"
                f"Expenses: {pl['expenses']}\nProfit: {pl['profit']}\n"
                f"Orders: {pl['orders']} (booked revenue {pl['order_revenue']})\n\n"
                f"Unpaid orders: {len(unpaid)}\n"
                + "\n".join(f"#{u['order_id']} {u['customer']} bal {u['balance']}"
                            for u in unpaid[:20])
                + f"\n\nLow-stock materials: {len(inv)}\n"
                + "\n".join(f"{m['material_name']}: {m['current_stock_qty']} left"
                            for m in inv))
        except Exception as exc:  # noqa: BLE001
            self._err(exc)
        finally:
            conn.close()

    def export_unpaid(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "unpaid_orders.csv",
                                              "CSV (*.csv)")
        if not path:
            return
        conn = self._conn()
        try:
            rows = ReportManager(conn).unpaid_orders()
            ReportManager.export_to_csv(
                rows, ["order_id", "customer", "total_amount", "paid", "balance", "status"],
                path)
            QMessageBox.information(self, "Reports", f"Exported to {path}")
        except Exception as exc:  # noqa: BLE001
            self._err(exc)
        finally:
            conn.close()

    # ---------- Backup ----------
    def _backup_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Backup and restore the MySQL database."))
        row = QHBoxLayout()
        b1 = QPushButton("Backup now…")
        b1.clicked.connect(self.do_backup)
        b2 = QPushButton("Restore from file…")
        b2.clicked.connect(self.do_restore)
        row.addWidget(b1)
        row.addWidget(b2)
        layout.addLayout(row)
        layout.addStretch(1)
        return w

    def do_backup(self):
        mgr = BackupManager()
        path, _ = QFileDialog.getSaveFileName(self, "Backup to", mgr.default_filename(),
                                              "SQL (*.sql)")
        if not path:
            return
        try:
            mgr.backup(path)
            QMessageBox.information(self, "Backup", f"Saved to {path}")
        except Exception as exc:  # noqa: BLE001
            self._err(exc)

    def do_restore(self):
        path, _ = QFileDialog.getOpenFileName(self, "Restore from", "", "SQL (*.sql)")
        if not path:
            return
        if QMessageBox.question(self, "Restore",
                                "Restore will overwrite current data. Continue?") \
                != QMessageBox.StandardButton.Yes:
            return
        try:
            BackupManager().restore(path)
            QMessageBox.information(self, "Restore", "Restore completed.")
        except Exception as exc:  # noqa: BLE001
            self._err(exc)

    # ---------- Users ----------
    def _users_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        self.user_table = QTableWidget()
        layout.addWidget(self.user_table)
        btns = QHBoxLayout()
        for label, fn in [("Refresh", self.refresh_users), ("Add user", self.add_user),
                          ("Deactivate/Activate", self.toggle_user),
                          ("Reset password", self.reset_password)]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            btns.addWidget(b)
        layout.addLayout(btns)
        self.refresh_users()
        return w

    def refresh_users(self):
        conn = self._conn()
        try:
            rows = UserManager(conn).list_users()
            _table(rows, ["user_id", "username", "first_name", "last_name", "role",
                          "is_active", "created_at"], self.user_table)
        except Exception as exc:  # noqa: BLE001
            self._err(exc)
        finally:
            conn.close()

    def add_user(self):
        username, first, last = QLineEdit(), QLineEdit(), QLineEdit()
        password = QLineEdit()
        password.setEchoMode(QLineEdit.EchoMode.Password)
        role = QComboBox()
        role.addItems(["Staff", "Admin"])
        d = _FormDialog("Add user", [
            ("username", "Username:", username), ("password", "Password:", password),
            ("first", "First name:", first), ("last", "Last name:", last),
            ("role", "Role:", role)], self)
        if d.exec():
            conn = self._conn()
            try:
                UserManager(conn).create_user(
                    username.text(), password.text(), first.text(), last.text(),
                    role.currentText())
                self.refresh_users()
            except Exception as exc:  # noqa: BLE001
                self._err(exc)
            finally:
                conn.close()

    def toggle_user(self):
        uid = _selected_id(self.user_table)
        if uid is None:
            return
        conn = self._conn()
        try:
            u = UserManager(conn).get_user(uid)
            UserManager(conn).set_active(uid, not u["is_active"])
            self.refresh_users()
        except Exception as exc:  # noqa: BLE001
            self._err(exc)
        finally:
            conn.close()

    def reset_password(self):
        uid = _selected_id(self.user_table)
        if uid is None:
            return
        pw = QLineEdit()
        pw.setEchoMode(QLineEdit.EchoMode.Password)
        d = _FormDialog("Reset password", [("pw", "New password:", pw)], self)
        if d.exec():
            conn = self._conn()
            try:
                UserManager(conn).change_password(uid, pw.text())
                QMessageBox.information(self, "Users", "Password updated.")
            except Exception as exc:  # noqa: BLE001
                self._err(exc)
            finally:
                conn.close()
