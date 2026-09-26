"""Inventory Management module widget (Admin & Staff shared).

Spec (Phase 7):
  InventoryWidget (QWidget) with materials QTableWidget
  (Name, Unit, Current Qty, Low Stock Threshold, Cost per Unit).
  Admin: Add / Edit / Delete Material (+ Stock In / Stock Out).
  Staff: Stock In / Stock Out only (material buttons hidden).
  StockMovementDialog with material combo, movement_type combo
  (IN/OUT/ADJUSTMENT), quantity + reason QLineEdits; on save inserts
  the movement and updates Materials.current_stock_qty.
  Red low-stock QLabel when any current_stock_qty <= low_stock_threshold.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QDialog, QFormLayout, QMessageBox, QLabel,
    QComboBox, QHeaderView, QAbstractItemView, QDoubleSpinBox, QSpinBox,
)
from PyQt6.QtGui import QIntValidator

from database.database import get_connection
from inventory.inventory_management import (
    MaterialManager, StockMovementManager, MOVEMENT_TYPES,
)

_MATERIAL_HEADERS = ["material_id", "material_name", "unit_of_measure",
                     "current_stock_qty", "low_stock_threshold", "cost_per_unit"]
_MATERIAL_LABELS = ["ID", "Name", "Unit", "Current Qty",
                    "Low Stock At", "Cost per Unit"]


class MaterialDialog(QDialog):
    """Add/Edit material (Admin only)."""

    def __init__(self, parent=None, material: dict | None = None):
        super().__init__(parent)
        self._is_edit = material is not None
        self.setWindowTitle("Edit material" if material else "Add material")
        self.setMinimumWidth(380)
        data = material or {}
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit(str(data.get("material_name") or ""))
        self.uom_edit = QLineEdit(str(data.get("unit_of_measure") or "pcs"))
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(0, 1_000_000)
        self.qty_spin.setValue(int(data.get("current_stock_qty") or 0))
        self.qty_spin.setEnabled(not self._is_edit)  # stock via movements after
        self.thresh_spin = QSpinBox()
        self.thresh_spin.setRange(0, 1_000_000)
        self.thresh_spin.setValue(int(data.get("low_stock_threshold") or 10))
        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setRange(0, 1_000_000)
        self.cost_spin.setValue(float(data.get("cost_per_unit") or 0))
        form.addRow("Name:", self.name_edit)
        form.addRow("Unit:", self.uom_edit)
        form.addRow("Opening qty:", self.qty_spin)
        form.addRow("Low-stock at:", self.thresh_spin)
        form.addRow("Cost/unit:", self.cost_spin)
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
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Materials", "Material name is required.")
            return
        self.accept()

    def values(self) -> dict:
        return {"material_name": self.name_edit.text().strip(),
                "unit_of_measure": self.uom_edit.text().strip() or "pcs",
                "current_stock_qty": self.qty_spin.value(),
                "low_stock_threshold": self.thresh_spin.value(),
                "cost_per_unit": self.cost_spin.value()}


class StockMovementDialog(QDialog):
    """Record IN / OUT / ADJUSTMENT with quantity + reason QLineEdits."""

    def __init__(self, parent=None, materials: list[dict] | None = None,
                 material_id: int | None = None,
                 movement_type: str | None = None,
                 allowed_types: tuple | None = None):
        super().__init__(parent)
        self.setWindowTitle("Stock movement")
        self.setMinimumWidth(380)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.material_box = QComboBox()
        for m in materials or []:
            self.material_box.addItem(
                f"{m['material_id']}: {m['material_name']} "
                f"(on hand {m['current_stock_qty']})", m["material_id"])
        if material_id is not None:
            idx = self.material_box.findData(material_id)
            if idx >= 0:
                self.material_box.setCurrentIndex(idx)
        form.addRow("Material:", self.material_box)

        self.type_box = QComboBox()
        self.type_box.addItems(list(allowed_types or MOVEMENT_TYPES))
        if movement_type in (allowed_types or MOVEMENT_TYPES):
            self.type_box.setCurrentText(movement_type)
        form.addRow("Movement type:", self.type_box)

        self.qty_edit = QLineEdit()
        self.qty_edit.setPlaceholderText("OUT deducts; ADJUSTMENT sets on-hand")
        self.qty_edit.setValidator(QIntValidator(1, 1_000_000))
        self.qty_edit.setText("1")
        form.addRow("Quantity:", self.qty_edit)

        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText("Reason (optional)")
        form.addRow("Reason:", self.reason_edit)
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
            QMessageBox.warning(self, "Stock movement", str(exc))
            return
        self.accept()

    def values(self) -> dict:
        if self.material_box.currentData() is None:
            raise ValueError("Select a material.")
        try:
            qty = int(self.qty_edit.text().strip())
        except (ValueError, AttributeError):
            raise ValueError("Quantity must be a positive whole number.")
        if qty <= 0:
            raise ValueError("Quantity must be greater than zero.")
        if self.type_box.currentText() not in MOVEMENT_TYPES:
            raise ValueError(f"movement_type must be one of {MOVEMENT_TYPES}")
        return {"material_id": int(self.material_box.currentData()),
                "movement_type": self.type_box.currentText(),
                "quantity": qty, "reason": self.reason_edit.text().strip()}


class InventoryWidget(QWidget):
    """Shared Admin/Staff page for QStackedWidget."""

    def __init__(self, user: dict | None = None, parent=None):
        super().__init__(parent)
        self.user = user or {}
        self._is_admin = (self.user.get("role") or "Staff") == "Admin"
        layout = QVBoxLayout(self)

        self.alert = QLabel()
        self.alert.setWordWrap(True)
        self.alert.setStyleSheet("background:#FEE2E2;color:#B91C1C;"
                                 "border:1px solid #FCA5A5;border-radius:8px;"
                                 "padding:8px;font-weight:bold;")
        self.alert.hide()
        layout.addWidget(self.alert)

        layout.addWidget(QLabel("Materials"))
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        row = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        row.addWidget(self.refresh_btn)
        if self._is_admin:
            self.add_btn = QPushButton("Add Material")
            self.edit_btn = QPushButton("Edit Material")
            self.delete_btn = QPushButton("Delete Material")
            self.add_btn.clicked.connect(self.add_material)
            self.edit_btn.clicked.connect(self.edit_material)
            self.delete_btn.clicked.connect(self.delete_material)
            row.addWidget(self.add_btn)
            row.addWidget(self.edit_btn)
            row.addWidget(self.delete_btn)
        self.in_btn = QPushButton("Stock In")
        self.out_btn = QPushButton("Stock Out")
        self.in_btn.clicked.connect(lambda: self.stock_move("IN"))
        self.out_btn.clicked.connect(lambda: self.stock_move("OUT"))
        row.addWidget(self.in_btn)
        row.addWidget(self.out_btn)
        if self._is_admin:
            self.adjust_btn = QPushButton("Adjust")
            self.adjust_btn.clicked.connect(lambda: self.stock_move("ADJUSTMENT"))
            row.addWidget(self.adjust_btn)
        layout.addLayout(row)

        layout.addWidget(QLabel("Recent movements"))
        self.mov_table = QTableWidget()
        self.mov_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.mov_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.mov_table)
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
            mats = MaterialManager(conn).list_materials()
            self.table.setRowCount(len(mats))
            self.table.setColumnCount(len(_MATERIAL_HEADERS))
            self.table.setHorizontalHeaderLabels(_MATERIAL_LABELS)
            for r, m in enumerate(mats):
                for c, h in enumerate(_MATERIAL_HEADERS):
                    val = m.get(h, "")
                    self.table.setItem(r, c, QTableWidgetItem(
                        "" if val is None else str(val)))
            self.table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch)
            # Low-stock alert (spec): red banner when any qty <= threshold.
            low = [m for m in mats
                   if int(m["current_stock_qty"]) <= int(m["low_stock_threshold"])]
            if low:
                names = ", ".join(f"{m['material_name']} ({m['current_stock_qty']} left)"
                                  for m in low[:8])
                more = f" +{len(low) - 8} more" if len(low) > 8 else ""
                self.alert.setText(f"LOW STOCK WARNING: {names}{more}")
                self.alert.show()
            else:
                self.alert.hide()
            movs = StockMovementManager(conn).list_movements(limit=100)
            mov_headers = ["movement_id", "material_name", "movement_type",
                           "quantity", "reason", "movement_date", "recorded_by"]
            self.mov_table.setRowCount(len(movs))
            self.mov_table.setColumnCount(len(mov_headers))
            self.mov_table.setHorizontalHeaderLabels(
                ["ID", "Material", "Type", "Qty", "Reason", "Date", "By"])
            for r, m in enumerate(movs):
                for c, h in enumerate(mov_headers):
                    val = m.get(h, "")
                    self.mov_table.setItem(r, c, QTableWidgetItem(
                        "" if val is None else str(val)))
            self.mov_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            conn.close()

    # -- Admin material CRUD --
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
                vals["cost_per_unit"])
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            conn.close()

    def edit_material(self) -> None:
        mid = self._selected_id()
        if mid is None:
            QMessageBox.warning(self, "Inventory", "Select a material first.")
            return
        conn = self._conn()
        try:
            cur = MaterialManager(conn).get_material(mid)
        finally:
            conn.close()
        if not cur:
            QMessageBox.warning(self, "Inventory", "Material not found.")
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
                cost_per_unit=vals["cost_per_unit"])
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            conn.close()

    def delete_material(self) -> None:
        mid = self._selected_id()
        if mid is None:
            QMessageBox.warning(self, "Inventory", "Select a material first.")
            return
        if QMessageBox.question(
                self, "Delete", f"Delete material {mid}?"
        ) != QMessageBox.StandardButton.Yes:
            return
        conn = self._conn()
        try:
            MaterialManager(conn).delete_material(mid)
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            conn.close()

    # -- shared stock movement --
    def stock_move(self, movement_type: str | None = None) -> None:
        conn = self._conn()
        try:
            mats = MaterialManager(conn).list_materials()
        finally:
            conn.close()
        if not mats:
            QMessageBox.warning(self, "Inventory", "Add a material first.")
            return
        mid = self._selected_id()
        allowed = list(MOVEMENT_TYPES) if self._is_admin else ("IN", "OUT")
        if movement_type not in allowed:
            movement_type = allowed[0]
        dlg = StockMovementDialog(self, materials=mats, material_id=mid,
                                  movement_type=movement_type,
                                  allowed_types=tuple(allowed))
        if not dlg.exec():
            return
        try:
            vals = dlg.values()
        except ValueError as exc:
            QMessageBox.warning(self, "Stock movement", str(exc))
            return
        conn = self._conn()
        try:
            StockMovementManager(conn).record_movement(
                vals["material_id"], self._user_id(), vals["movement_type"],
                vals["quantity"], vals["reason"])
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            conn.close()
