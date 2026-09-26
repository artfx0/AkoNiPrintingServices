"""Inventory Management module widget (Professional SaaS / HCI format).

Supports both Admin and Staff roles:
  - Admin: Full material CRUD + Stock IN/OUT/ADJUSTMENT.
  - Staff: Stock IN and Stock OUT only.

Features:
  - Visual hierarchy: Section title + descriptive subtitle.
  - Top summary cards: Total Items Tracked, Low Stock Alerts, and Total Movements.
  - Tabbed interface separating Material Stock List and Stock Movement Audit Log.
  - Live search and Low Stock filter.
  - Stock level pills: '● In Stock' (emerald) vs '● Low Stock' (amber).
  - Modernized MaterialDialog and StockMovementDialog.
"""
from __future__ import annotations

from decimal import Decimal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QDialog, QFormLayout, QMessageBox, QLabel,
    QComboBox, QHeaderView, QAbstractItemView, QDoubleSpinBox, QSpinBox,
    QFrame, QTabWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIntValidator

from database.database import get_connection
from inventory.inventory_management import (
    MaterialManager, StockMovementManager, MOVEMENT_TYPES,
)
from ui.icons import get_icon, get_action_icon, get_pixmap

_MATERIAL_HEADERS = [
    "ID", "Material Name", "Unit", "On Hand",
    "Min. Threshold", "Cost / Unit", "Stock Status"
]

_MOVEMENT_HEADERS = [
    "Movement #", "Material Name", "Type",
    "Quantity", "Reason / Reference", "Date Recorded", "Recorded By"
]


class MaterialDialog(QDialog):
    """Add / Edit Material dialog with modern SaaS styling and validation."""

    def __init__(self, parent=None, material: dict | None = None):
        super().__init__(parent)
        self._is_edit = material is not None
        self.setWindowTitle("Edit Material" if self._is_edit else "Add New Material")
        self.setMinimumWidth(440)
        data = material or {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Edit Material Item" if self._is_edit else "Create New Material Item")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        sub = QLabel("Configure inventory supply specifications and minimum reorder thresholds.")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(title)
        layout.addWidget(sub)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.name_edit = QLineEdit(str(data.get("material_name") or ""))
        self.name_edit.setPlaceholderText("e.g. Tarpaulin 10oz, Glossy Photo Paper A4")
        form.addRow("Material Name *:", self.name_edit)

        self.uom_edit = QLineEdit(str(data.get("unit_of_measure") or "pcs"))
        self.uom_edit.setPlaceholderText("e.g. pcs, rolls, sheets, meters")
        form.addRow("Unit of Measure:", self.uom_edit)

        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(0, 1_000_000)
        self.qty_spin.setValue(int(data.get("current_stock_qty") or 0))
        self.qty_spin.setEnabled(not self._is_edit)
        form.addRow("Initial Stock Qty:" if not self._is_edit else "Current Stock Qty:", self.qty_spin)

        self.thresh_spin = QSpinBox()
        self.thresh_spin.setRange(0, 1_000_000)
        self.thresh_spin.setValue(int(data.get("low_stock_threshold") or 10))
        form.addRow("Low-Stock Threshold:", self.thresh_spin)

        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setRange(0.00, 1_000_000.00)
        self.cost_spin.setPrefix("P")
        self.cost_spin.setValue(float(data.get("cost_per_unit") or 0))
        form.addRow("Cost per Unit:", self.cost_spin)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("SecondaryBtn")
        cancel.clicked.connect(self.reject)

        save = QPushButton("Save Material")
        save.setIcon(get_action_icon("check", "primary", 15))
        save.clicked.connect(self._on_save)

        btns.addWidget(cancel)
        btns.addWidget(save)
        layout.addLayout(btns)

    def _on_save(self) -> None:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Material Name is required.")
            return
        self.accept()

    def values(self) -> dict:
        return {
            "material_name": self.name_edit.text().strip(),
            "unit_of_measure": self.uom_edit.text().strip() or "pcs",
            "current_stock_qty": self.qty_spin.value(),
            "low_stock_threshold": self.thresh_spin.value(),
            "cost_per_unit": self.cost_spin.value(),
        }


class StockMovementDialog(QDialog):
    """Record Stock IN, OUT, or ADJUSTMENT with modern form controls."""

    def __init__(self, parent=None, materials: list[dict] | None = None,
                 material_id: int | None = None,
                 movement_type: str | None = None,
                 allowed_types: tuple | None = None):
        super().__init__(parent)
        self.setWindowTitle("Record Stock Movement")
        self.setMinimumWidth(440)
        self.materials = materials or []
        self._mats_by_id = {m["material_id"]: m for m in self.materials}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Record Stock Movement")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        sub = QLabel("Record additions (IN), consumption (OUT), or manual reconciliation (ADJUSTMENT).")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(title)
        layout.addWidget(sub)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.material_box = QComboBox()
        for m in self.materials:
            self.material_box.addItem(
                f"{m['material_name']} (On hand: {m['current_stock_qty']} {m['unit_of_measure']})",
                m["material_id"]
            )
        if material_id is not None:
            idx = self.material_box.findData(material_id)
            if idx >= 0:
                self.material_box.setCurrentIndex(idx)
        form.addRow("Material Item:", self.material_box)

        self.type_box = QComboBox()
        self.type_box.addItems(list(allowed_types or MOVEMENT_TYPES))
        if movement_type in (allowed_types or MOVEMENT_TYPES):
            self.type_box.setCurrentText(movement_type)
        form.addRow("Movement Type:", self.type_box)

        self.qty_edit = QLineEdit("1")
        self.qty_edit.setPlaceholderText("Enter quantity...")
        self.qty_edit.setValidator(QIntValidator(1, 1_000_000))
        form.addRow("Quantity:", self.qty_edit)

        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText("e.g. Supplier PO #123, Order #45 Print Run, Physical Audit")
        form.addRow("Reason / Note:", self.reason_edit)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("SecondaryBtn")
        cancel.clicked.connect(self.reject)

        save = QPushButton("Save Movement")
        save.setIcon(get_action_icon("check", "primary", 15))
        save.clicked.connect(self._on_save)

        btns.addWidget(cancel)
        btns.addWidget(save)
        layout.addLayout(btns)

    def _on_save(self) -> None:
        try:
            self.values()
        except ValueError as exc:
            QMessageBox.warning(self, "Validation Error", str(exc))
            return
        self.accept()

    def values(self) -> dict:
        if self.material_box.currentData() is None:
            raise ValueError("Please select a material item.")
        try:
            qty = int(self.qty_edit.text().strip())
        except (ValueError, AttributeError):
            raise ValueError("Quantity must be a valid positive whole number.")
        if qty <= 0:
            raise ValueError("Quantity must be greater than zero.")
        if self.type_box.currentText() not in MOVEMENT_TYPES:
            raise ValueError(f"Movement type must be one of {MOVEMENT_TYPES}")

        return {
            "material_id": int(self.material_box.currentData()),
            "movement_type": self.type_box.currentText(),
            "quantity": qty,
            "reason": self.reason_edit.text().strip(),
        }


class InventoryWidget(QWidget):
    """Inventory Management module with HCI-focused modern layout and tabs."""

    def __init__(self, user: dict | None = None, parent=None):
        super().__init__(parent)
        self.user = user or {}
        self._is_admin = (self.user.get("role") or "Staff") == "Admin"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(18)

        # 1. Page Header (Title + Subtitle)
        header_lay = QVBoxLayout()
        header_lay.setSpacing(4)
        title = QLabel("Inventory & Materials")
        title.setObjectName("ModuleHeaderTitle")
        sub = QLabel("Monitor raw material supplies, track stock adjustments, and handle inbound / outbound movements.")
        sub.setObjectName("ModuleHeaderSub")
        header_lay.addWidget(title)
        header_lay.addWidget(sub)
        layout.addLayout(header_lay)

        # 2. Summary Status Chips / Badges
        self.stat_bar = QHBoxLayout()
        self.stat_bar.setSpacing(14)

        self.total_chip = QFrame()
        self.total_chip.setStyleSheet(
            "background: #F1F5F9; border-radius: 8px; border: 1px solid #E2E8F0;"
        )
        tc_lay = QHBoxLayout(self.total_chip)
        tc_lay.setContentsMargins(10, 6, 12, 6)
        tc_lay.setSpacing(8)
        self.total_chip_icon = QLabel()
        self.total_chip_icon.setPixmap(get_pixmap("inventory", color="#475569", size=15))
        self.total_chip_text = QLabel("0 Materials Tracked")
        self.total_chip_text.setStyleSheet("color: #334155; font-size: 12px; font-weight: 600;")
        tc_lay.addWidget(self.total_chip_icon)
        tc_lay.addWidget(self.total_chip_text)

        self.low_stock_chip = QFrame()
        self.low_stock_chip.setStyleSheet(
            "background: #DCFCE7; border-radius: 8px; border: 1px solid #BBF7D0;"
        )
        lc_lay = QHBoxLayout(self.low_stock_chip)
        lc_lay.setContentsMargins(10, 6, 12, 6)
        lc_lay.setSpacing(8)
        self.low_stock_chip_icon = QLabel()
        self.low_stock_chip_icon.setPixmap(get_pixmap("check-circle", color="#15803D", size=15))
        self.low_stock_chip_text = QLabel("Stock Levels Healthy")
        self.low_stock_chip_text.setStyleSheet("color: #15803D; font-size: 12px; font-weight: 600;")
        lc_lay.addWidget(self.low_stock_chip_icon)
        lc_lay.addWidget(self.low_stock_chip_text)

        self.stat_bar.addWidget(self.total_chip)
        self.stat_bar.addWidget(self.low_stock_chip)
        self.stat_bar.addStretch(1)
        layout.addLayout(self.stat_bar)

        # 3. Main Tab Container
        self.tabs = QTabWidget()
        self.tabs.setObjectName("ModuleTabs")

        # Tab 1: Materials
        self.materials_tab = self._build_materials_tab()
        self.tabs.addTab(self.materials_tab, "Material Stock List")
        self.tabs.setTabIcon(0, get_icon("inventory", color="#475569", size=16))

        # Tab 2: Movements
        self.movements_tab = self._build_movements_tab()
        self.tabs.addTab(self.movements_tab, "Stock Movement Audit Log")
        self.tabs.setTabIcon(1, get_icon("clipboard-list", color="#475569", size=16))

        layout.addWidget(self.tabs, 1)

        self.refresh()

    def _build_materials_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.mat_search = QLineEdit()
        self.mat_search.setObjectName("TableSearchInput")
        self.mat_search.addAction(get_icon("search", color="#94A3B8", size=16), QLineEdit.ActionPosition.LeadingPosition)
        self.mat_search.setPlaceholderText("Search materials by name or unit...")
        self.mat_search.setClearButtonEnabled(True)
        self.mat_search.setMinimumWidth(240)
        self.mat_search.textChanged.connect(self.refresh_materials_table)
        toolbar.addWidget(self.mat_search, 1)

        self.stock_filter = QComboBox()
        self.stock_filter.setObjectName("TableFilterCombo")
        self.stock_filter.addItem("All Stock Levels", "ALL")
        self.stock_filter.addItem("Low Stock Only", "LOW")
        self.stock_filter.currentIndexChanged.connect(self.refresh_materials_table)
        toolbar.addWidget(self.stock_filter)

        self.mat_refresh_btn = QPushButton("Refresh")
        self.mat_refresh_btn.setObjectName("SecondaryBtn")
        self.mat_refresh_btn.setIcon(get_action_icon("refresh", "secondary", 15))
        self.mat_refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self.mat_refresh_btn)

        self.in_btn = QPushButton("Stock In")
        self.in_btn.setObjectName("SecondaryBtn")
        self.in_btn.setIcon(get_action_icon("stock-in", "secondary", 15))
        self.in_btn.clicked.connect(lambda: self.stock_move("IN"))
        toolbar.addWidget(self.in_btn)

        self.out_btn = QPushButton("Stock Out")
        self.out_btn.setObjectName("SecondaryBtn")
        self.out_btn.setIcon(get_action_icon("stock-out", "secondary", 15))
        self.out_btn.clicked.connect(lambda: self.stock_move("OUT"))
        toolbar.addWidget(self.out_btn)

        if self._is_admin:
            self.adj_btn = QPushButton("Adjust")
            self.adj_btn.setObjectName("SecondaryBtn")
            self.adj_btn.setIcon(get_action_icon("adjust", "secondary", 15))
            self.adj_btn.clicked.connect(lambda: self.stock_move("ADJUSTMENT"))
            toolbar.addWidget(self.adj_btn)

            self.edit_btn = QPushButton("Edit")
            self.edit_btn.setObjectName("SecondaryBtn")
            self.edit_btn.setIcon(get_action_icon("edit", "secondary", 15))
            self.edit_btn.clicked.connect(self.edit_material)
            toolbar.addWidget(self.edit_btn)

            self.delete_btn = QPushButton("Delete")
            self.delete_btn.setObjectName("DangerBtn")
            self.delete_btn.setIcon(get_action_icon("trash", "danger", 15))
            self.delete_btn.clicked.connect(self.delete_material)
            toolbar.addWidget(self.delete_btn)

            self.add_btn = QPushButton("Add Material")
            self.add_btn.setIcon(get_action_icon("plus", "primary", 16))
            self.add_btn.clicked.connect(self.add_material)
            toolbar.addWidget(self.add_btn)

        lay.addLayout(toolbar)

        # Table inside Card
        card = QFrame()
        card.setObjectName("ModuleCardContainer")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        self.mat_table = QTableWidget()
        self.mat_table.setColumnCount(len(_MATERIAL_HEADERS))
        self.mat_table.setHorizontalHeaderLabels(_MATERIAL_HEADERS)
        self.mat_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.mat_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.mat_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.mat_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.mat_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.mat_table.verticalHeader().setVisible(False)
        self.mat_table.verticalHeader().setDefaultSectionSize(40)
        self.mat_table.doubleClicked.connect(self.edit_material if self._is_admin else lambda: self.stock_move("IN"))

        card_lay.addWidget(self.mat_table)
        lay.addWidget(card, 1)

        return w

    def _build_movements_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.mov_search = QLineEdit()
        self.mov_search.setObjectName("TableSearchInput")
        self.mov_search.addAction(get_icon("search", color="#94A3B8", size=16), QLineEdit.ActionPosition.LeadingPosition)
        self.mov_search.setPlaceholderText("Search movement log by material, reason, or recorder...")
        self.mov_search.setClearButtonEnabled(True)
        self.mov_search.textChanged.connect(self.refresh_movements_table)
        toolbar.addWidget(self.mov_search, 1)

        self.mov_type_filter = QComboBox()
        self.mov_type_filter.setObjectName("TableFilterCombo")
        self.mov_type_filter.addItem("All Types", "")
        for t in MOVEMENT_TYPES:
            self.mov_type_filter.addItem(t, t)
        self.mov_type_filter.currentIndexChanged.connect(self.refresh_movements_table)
        toolbar.addWidget(self.mov_type_filter)

        self.mov_refresh_btn = QPushButton("Refresh Logs")
        self.mov_refresh_btn.setObjectName("SecondaryBtn")
        self.mov_refresh_btn.setIcon(get_action_icon("refresh", "secondary", 15))
        self.mov_refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self.mov_refresh_btn)

        lay.addLayout(toolbar)

        # Table inside Card
        card = QFrame()
        card.setObjectName("ModuleCardContainer")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        self.mov_table = QTableWidget()
        self.mov_table.setColumnCount(len(_MOVEMENT_HEADERS))
        self.mov_table.setHorizontalHeaderLabels(_MOVEMENT_HEADERS)
        self.mov_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.mov_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.mov_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.mov_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.mov_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.mov_table.verticalHeader().setVisible(False)
        self.mov_table.verticalHeader().setDefaultSectionSize(40)

        card_lay.addWidget(self.mov_table)
        lay.addWidget(card, 1)

        return w

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

    def _selected_mat_id(self) -> int | None:
        r = self.mat_table.currentRow()
        if r < 0:
            return None
        try:
            text = self.mat_table.item(r, 0).text().replace("#", "")
            return int(text)
        except (AttributeError, ValueError):
            return None

    def _create_stock_pill(self, is_low: bool) -> QWidget:
        container = QWidget()
        lay = QHBoxLayout(container)
        lay.setContentsMargins(6, 4, 6, 4)
        pill = QLabel("● Low Stock" if is_low else "● In Stock")
        pill.setObjectName("StockPill")
        pill.setProperty("alert", "true" if is_low else "false")
        pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pill.style().unpolish(pill)
        pill.style().polish(pill)
        lay.addWidget(pill)
        return container

    def _create_type_pill(self, mov_type: str) -> QWidget:
        container = QWidget()
        lay = QHBoxLayout(container)
        lay.setContentsMargins(6, 4, 6, 4)
        pill = QLabel(mov_type)
        pill.setObjectName("StatusPill")

        # Map movement types to status pill colors
        if mov_type == "IN":
            pill.setProperty("status", "paid")  # Green
        elif mov_type == "OUT":
            pill.setProperty("status", "processing")  # Blue
        else:
            pill.setProperty("status", "pending")  # Amber

        pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pill.style().unpolish(pill)
        pill.style().polish(pill)
        lay.addWidget(pill)
        return container

    # -- Data loading --
    def refresh(self) -> None:
        self.refresh_materials_table()
        self.refresh_movements_table()

    def refresh_materials_table(self) -> None:
        conn = self._conn()
        try:
            mats = MaterialManager(conn).list_materials()
            low_items = [
                m for m in mats
                if int(m.get("current_stock_qty", 0)) <= int(m.get("low_stock_threshold", 0))
            ]

            # Update Top Summary Chips
            self.total_chip_text.setText(f"{len(mats)} Materials Tracked")
            if low_items:
                self.low_stock_chip_text.setText(f"{len(low_items)} Items Low on Stock")
                self.low_stock_chip_text.setStyleSheet("color: #DC2626; font-size: 12px; font-weight: 600;")
                self.low_stock_chip_icon.setPixmap(get_pixmap("alert-triangle", color="#DC2626", size=15))
                self.low_stock_chip.setStyleSheet(
                    "background: #FEE2E2; border-radius: 8px; border: 1px solid #FCA5A5;"
                )
            else:
                self.low_stock_chip_text.setText("Stock Levels Healthy")
                self.low_stock_chip_text.setStyleSheet("color: #15803D; font-size: 12px; font-weight: 600;")
                self.low_stock_chip_icon.setPixmap(get_pixmap("check-circle", color="#15803D", size=15))
                self.low_stock_chip.setStyleSheet(
                    "background: #DCFCE7; border-radius: 8px; border: 1px solid #BBF7D0;"
                )

            # Filter materials
            needle = self.mat_search.text().strip().lower()
            filter_mode = self.stock_filter.currentData()

            filtered = []
            for m in mats:
                is_low = int(m.get("current_stock_qty", 0)) <= int(m.get("low_stock_threshold", 0))
                if filter_mode == "LOW" and not is_low:
                    continue
                if needle:
                    mname = str(m.get("material_name") or "").lower()
                    uom = str(m.get("unit_of_measure") or "").lower()
                    if needle not in mname and needle not in uom:
                        continue
                filtered.append(m)

            self.mat_table.setRowCount(len(filtered))
            for r, m in enumerate(filtered):
                mid = m.get("material_id")
                name = m.get("material_name", "")
                uom = m.get("unit_of_measure", "pcs")
                qty = int(m.get("current_stock_qty", 0))
                thresh = int(m.get("low_stock_threshold", 0))
                cost = Decimal(str(m.get("cost_per_unit", 0)))
                is_low = qty <= thresh

                self.mat_table.setItem(r, 0, QTableWidgetItem(f"#{mid}"))
                self.mat_table.setItem(r, 1, QTableWidgetItem(name))
                self.mat_table.setItem(r, 2, QTableWidgetItem(uom))
                self.mat_table.setItem(r, 3, QTableWidgetItem(f"{qty:,} {uom}"))
                self.mat_table.setItem(r, 4, QTableWidgetItem(f"{thresh:,} {uom}"))
                self.mat_table.setItem(r, 5, QTableWidgetItem(f"P{cost:,.2f}"))
                self.mat_table.setCellWidget(r, 6, self._create_stock_pill(is_low))

        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to load materials:\n{exc}")
        finally:
            conn.close()

    def refresh_movements_table(self) -> None:
        conn = self._conn()
        try:
            movs = StockMovementManager(conn).list_movements(limit=250)

            needle = self.mov_search.text().strip().lower()
            tfilter = self.mov_type_filter.currentData() or ""

            filtered = []
            for mv in movs:
                if tfilter and mv.get("movement_type") != tfilter:
                    continue
                if needle:
                    mat = str(mv.get("material_name") or "").lower()
                    rsn = str(mv.get("reason") or "").lower()
                    by = str(mv.get("recorded_by") or "").lower()
                    if needle not in mat and needle not in rsn and needle not in by:
                        continue
                filtered.append(mv)

            self.mov_table.setRowCount(len(filtered))
            for r, mv in enumerate(filtered):
                mvid = mv.get("movement_id")
                mat = mv.get("material_name", "")
                mtype = mv.get("movement_type", "IN")
                qty = int(mv.get("quantity", 0))
                reason = mv.get("reason", "—") or "—"
                date_str = str(mv.get("movement_date") or "")
                rec_by = str(mv.get("recorded_by") or "—")

                self.mov_table.setItem(r, 0, QTableWidgetItem(f"#{mvid}"))
                self.mov_table.setItem(r, 1, QTableWidgetItem(mat))
                self.mov_table.setCellWidget(r, 2, self._create_type_pill(mtype))
                self.mov_table.setItem(r, 3, QTableWidgetItem(f"{qty:,}"))
                self.mov_table.setItem(r, 4, QTableWidgetItem(reason))
                self.mov_table.setItem(r, 5, QTableWidgetItem(date_str))
                self.mov_table.setItem(r, 6, QTableWidgetItem(rec_by))

        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to load movements:\n{exc}")
        finally:
            conn.close()

    # -- Admin Material CRUD --
    def add_material(self) -> None:
        dlg = MaterialDialog(self)
        if not dlg.exec():
            return
        conn = self._conn()
        try:
            vals = dlg.values()
            MaterialManager(conn).create_material(
                vals["material_name"], vals["unit_of_measure"],
                vals["current_stock_qty"], vals["low_stock_threshold"],
                vals["cost_per_unit"]
            )
            QMessageBox.information(self, "Material Added", f"'{vals['material_name']}' created successfully.")
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            conn.close()

    def edit_material(self) -> None:
        mid = self._selected_mat_id()
        if mid is None:
            QMessageBox.warning(self, "Inventory", "Please select a material from the table first.")
            return

        conn = self._conn()
        try:
            cur = MaterialManager(conn).get_material(mid)
        finally:
            conn.close()

        if not cur:
            QMessageBox.warning(self, "Inventory", "Material record not found.")
            return

        dlg = MaterialDialog(self, material=cur)
        if not dlg.exec():
            return

        conn = self._conn()
        try:
            vals = dlg.values()
            MaterialManager(conn).update_material(
                mid, material_name=vals["material_name"],
                unit_of_measure=vals["unit_of_measure"],
                low_stock_threshold=vals["low_stock_threshold"],
                cost_per_unit=vals["cost_per_unit"]
            )
            QMessageBox.information(self, "Material Updated", f"Material #{mid} updated successfully.")
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            conn.close()

    def delete_material(self) -> None:
        mid = self._selected_mat_id()
        if mid is None:
            QMessageBox.warning(self, "Inventory", "Please select a material from the table first.")
            return

        if QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete material #{mid}?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return

        conn = self._conn()
        try:
            MaterialManager(conn).delete_material(mid)
            QMessageBox.information(self, "Deleted", f"Material #{mid} has been removed.")
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to delete material:\n{exc}")
        finally:
            conn.close()

    # -- Stock movement --
    def stock_move(self, movement_type: str | None = None) -> None:
        conn = self._conn()
        try:
            mats = MaterialManager(conn).list_materials()
        finally:
            conn.close()

        if not mats:
            QMessageBox.warning(self, "Inventory", "Please add at least one material first.")
            return

        mid = self._selected_mat_id()
        allowed = list(MOVEMENT_TYPES) if self._is_admin else ("IN", "OUT")
        if movement_type not in allowed:
            movement_type = allowed[0]

        dlg = StockMovementDialog(
            self, materials=mats, material_id=mid,
            movement_type=movement_type,
            allowed_types=tuple(allowed)
        )
        if not dlg.exec():
            return

        try:
            vals = dlg.values()
        except ValueError as exc:
            QMessageBox.warning(self, "Stock Movement", str(exc))
            return

        conn = self._conn()
        try:
            StockMovementManager(conn).record_movement(
                vals["material_id"], self._user_id(), vals["movement_type"],
                vals["quantity"], vals["reason"]
            )
            QMessageBox.information(
                self, "Stock Movement Recorded",
                f"{vals['movement_type']} movement of {vals['quantity']} units recorded successfully."
            )
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to record movement:\n{exc}")
        finally:
            conn.close()
