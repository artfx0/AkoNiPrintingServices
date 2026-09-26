"""Staff dashboard — inventory use case only."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QPushButton, QDialog, QFormLayout, QLineEdit, QMessageBox, QComboBox,
    QSpinBox, QDoubleSpinBox, QLabel, QHeaderView, QAbstractItemView, QToolBar,
)

from database.database import get_connection
from inventory.inventory_management import (
    MaterialManager, StockMovementManager, MOVEMENT_TYPES)


def _table(rows: list[dict], headers: list[str], table: QTableWidget) -> None:
    table.setRowCount(len(rows))
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    for r, row in enumerate(rows):
        for c, h in enumerate(headers):
            table.setItem(r, c, QTableWidgetItem(str(row.get(h, "") or "")))
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)


class StaffDashboard(QMainWindow):
    """Staff can manage inventory only — no customers, orders, payments, etc."""

    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.logout_requested = False
        self.setWindowTitle(f"AkoNi Printing — Staff ({user['username']})")
        self.resize(900, 600)
        self._setup_header()
        tabs = QTabWidget()
        self.setCentralWidget(tabs)
        self.mat_table = QTableWidget()
        self.mov_table = QTableWidget()
        tabs.addTab(self._materials_tab(), "Materials")
        tabs.addTab(self._movements_tab(), "Stock Movements")
        self.refresh()

    def _setup_header(self) -> None:
        bar = QToolBar("Session")
        bar.setMovable(False)
        bar.addWidget(QLabel(f"Logged in: {self.user.get('username', '')} (Staff)  "))
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

    def _materials_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Materials — record stock IN / OUT / ADJUSTMENT below."))
        layout.addWidget(self.mat_table)
        row = QHBoxLayout()
        for label, fn in [("Refresh", self.refresh), ("Stock IN/OUT", self.stock_move)]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            row.addWidget(b)
        layout.addLayout(row)
        return w

    def _movements_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(self.mov_table)
        b = QPushButton("Refresh")
        b.clicked.connect(self.refresh)
        layout.addWidget(b)
        return w

    def refresh(self):
        conn = None
        try:
            conn = get_connection()
            mats = MaterialManager(conn).list_materials()
            _table(mats, ["material_id", "material_name", "unit_of_measure",
                          "current_stock_qty", "low_stock_threshold"], self.mat_table)
            movs = StockMovementManager(conn).list_movements(limit=100)
            _table(movs, ["movement_id", "material_name", "movement_type", "quantity",
                          "reason", "movement_date", "recorded_by"], self.mov_table)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            if conn is not None:
                conn.close()

    def stock_move(self):
        row = self.mat_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Inventory", "Select a material first.")
            return
        try:
            mid = int(self.mat_table.item(row, 0).text())
        except (AttributeError, ValueError):
            return
        d = QDialog(self)
        d.setWindowTitle("Stock movement")
        form = QFormLayout(d)
        type_box = QComboBox()
        type_box.addItems(list(MOVEMENT_TYPES))
        qty = QSpinBox()
        qty.setRange(1, 1_000_000)
        reason = QLineEdit()
        form.addRow("Type:", type_box)
        form.addRow("Qty:", qty)
        form.addRow("Reason:", reason)
        btns = QHBoxLayout()
        ok, cancel = QPushButton("Save"), QPushButton("Cancel")
        ok.clicked.connect(d.accept)
        cancel.clicked.connect(d.reject)
        btns.addWidget(ok)
        btns.addWidget(cancel)
        form.addRow(btns)
        if d.exec():
            conn = None
            try:
                conn = get_connection()
                StockMovementManager(conn).record_movement(
                    mid, self.user["user_id"], type_box.currentText(),
                    qty.value(), reason.text())
                self.refresh()
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Error", str(exc))
            finally:
                if conn is not None:
                    conn.close()
