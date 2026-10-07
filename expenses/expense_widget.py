"""Expense Management module widget (Professional SaaS / HCI format).

Features:
  - Visual hierarchy: Section title + descriptive subtitle.
  - Financial summary banner displaying filtered total and record count.
  - Action toolbar: Live search, category dropdown filter, and date range filters.
  - Elevated card container wrapping the data table.
  - Category pills and Philippine Peso currency formatting (P{:,.2f}).
  - Modernized ExpenseDialog with optional Stock IN movement linkage.
"""
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QDialog, QFormLayout, QMessageBox, QLabel,
    QComboBox, QDateEdit, QCheckBox, QHeaderView, QAbstractItemView,
    QFrame, QDoubleSpinBox, QScrollArea,
)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QDoubleValidator

from database.database import get_connection
from expenses.expense_management import ExpenseManager, EXPENSE_CATEGORIES
from inventory.inventory_management import StockMovementManager
from ui.icons import get_icon, get_action_icon
from ui.kpi_card import StatusKpiCard

_EXPENSE_HEADERS = [
    "Expense #", "Date", "Category", "Amount", "Description", "Recorded By"
]


def _format_datetime(val) -> str:
    """Format expense datetime into human-readable YYYY-MM-DD HH:MM."""
    if val is None or val == "":
        return "—"
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d %H:%M")
    s = str(val).strip()
    try:
        s = s.replace("T", " ")
        parts = s.split(":")
        if len(parts) >= 2:
            return f"{parts[0]}:{parts[1]}"
    except Exception:
        pass
    return s


def _unlinked_in_movements(conn) -> list[dict]:
    movs = StockMovementManager(conn).list_movements(limit=200)
    return [m for m in movs if m.get("movement_type") == "IN" and not m.get("expense_id")]


class ExpenseDialog(QDialog):
    """Add Expense dialog with modern SaaS styling and validation."""

    def __init__(self, parent=None, in_movements: list[dict] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Record Operating Expense")
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Record Business Expense")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        sub = QLabel("Log operational expenditures, utility bills, raw material supplies, or labor costs.")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(title)
        layout.addWidget(sub)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Expense Date:", self.date_edit)

        self.category_box = QComboBox()
        self.category_box.addItems(list(EXPENSE_CATEGORIES))
        form.addRow("Category *:", self.category_box)

        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("0.00")
        self.amount_edit.setValidator(QDoubleValidator(0.01, 10_000_000, 2))
        form.addRow("Amount (P) *:", self.amount_edit)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("e.g. Meralco electric bill, 50 rolls Vinyl sticker from supplier")
        form.addRow("Description:", self.desc_edit)

        self.link_box = QComboBox()
        self.link_box.addItem("(None — General operating expense)", None)
        for m in in_movements or []:
            self.link_box.addItem(
                f"IN #{m['movement_id']}: {m.get('material_name', '')} x{m.get('quantity')} ({m.get('movement_date')})",
                m["movement_id"]
            )
        form.addRow("Link Stock IN:", self.link_box)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("SecondaryBtn")
        cancel.clicked.connect(self.reject)

        save = QPushButton("Save Expense")
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
        try:
            amount = Decimal(self.amount_edit.text().strip())
        except (InvalidOperation, AttributeError):
            raise ValueError("Please enter a valid expense amount greater than zero.")
        if amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        if self.category_box.currentText() not in EXPENSE_CATEGORIES:
            raise ValueError(f"Category must be one of {EXPENSE_CATEGORIES}")

        return {
            "expense_date": self.date_edit.date().toPyDate().isoformat(),
            "category": self.category_box.currentText(),
            "amount": str(amount),
            "description": self.desc_edit.text().strip(),
            "movement_id": self.link_box.currentData(),
        }


class ExpenseWidget(QWidget):
    """Expense Management module with HCI-focused modern layout."""

    def __init__(self, user: dict | None = None, parent=None):
        super().__init__(parent)
        self.user = user or {}
        self.selected_category: str | None = None

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
        scroll_content.setObjectName("ExpenseWidgetScrollContent")
        scroll_content.setStyleSheet("QWidget#ExpenseWidgetScrollContent { background-color: #F8FAFC; }")

        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(18)

        # 1. Page Header (Title + Subtitle)
        header_lay = QVBoxLayout()
        header_lay.setSpacing(4)
        title = QLabel("Expense Management")
        title.setObjectName("ModuleHeaderTitle")
        sub = QLabel("Record business operating overheads, raw material purchase disbursements, and monitor outflows.")
        sub.setObjectName("ModuleHeaderSub")
        header_lay.addWidget(title)
        header_lay.addWidget(sub)
        layout.addLayout(header_lay)

        # 2. Total Disbursements Summary Banner
        summary_card = QFrame()
        summary_card.setObjectName("SummaryBox")
        sum_lay = QHBoxLayout(summary_card)
        sum_lay.setContentsMargins(16, 12, 16, 12)

        total_title = QLabel("Filtered Total Disbursements:")
        total_title.setStyleSheet("font-weight: 600; color: #475569; font-size: 13px;")
        self.total_label = QLabel("P0.00")
        self.total_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #0F172A;")

        self.count_label = QLabel("0 transactions recorded")
        self.count_label.setStyleSheet("color: #64748B; font-size: 12px; margin-left: 8px;")

        sum_lay.addWidget(total_title)
        sum_lay.addWidget(self.total_label)
        sum_lay.addWidget(self.count_label)
        sum_lay.addStretch(1)
        layout.addWidget(summary_card)

        # 3. KPI Summary Cards Row (Below banner, above search bar)
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)

        self.category_cards: dict[str, StatusKpiCard] = {}
        for cat in EXPENSE_CATEGORIES:
            card = StatusKpiCard(cat, value=0, parent=self)
            card.clicked.connect(self._on_category_card_clicked)
            self.category_cards[cat] = card
            kpi_row.addWidget(card, 1)

        layout.addLayout(kpi_row)

        # 4. Inline Record Expense Card (Directly above search bar, no pop-up dialog)
        form_card = QFrame()
        form_card.setObjectName("ModuleCardContainer")
        form_lay = QVBoxLayout(form_card)
        form_lay.setContentsMargins(18, 14, 18, 14)
        form_lay.setSpacing(10)

        form_header = QHBoxLayout()
        form_header.setSpacing(8)
        form_title = QLabel("Record Operating Expense")
        form_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #0F172A;")
        form_subtitle = QLabel("— Log material purchases, overhead, labor, and disbursements directly")
        form_subtitle.setStyleSheet("font-size: 12px; color: #64748B;")
        form_header.addWidget(form_title)
        form_header.addWidget(form_subtitle)
        form_header.addStretch(1)
        form_lay.addLayout(form_header)

        # Row 1: Date, Category, Amount, Description
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        self.input_date = QDateEdit()
        self.input_date.setCalendarPopup(True)
        self.input_date.setDate(QDate.currentDate())
        self.input_date.setFixedHeight(36)

        self.input_category = QComboBox()
        self.input_category.addItems(list(EXPENSE_CATEGORIES))
        self.input_category.setCurrentText("Materials")
        self.input_category.setFixedHeight(36)

        self.input_amount = QDoubleSpinBox()
        self.input_amount.setRange(0.00, 10_000_000.00)
        self.input_amount.setDecimals(2)
        self.input_amount.setValue(0.00)
        self.input_amount.setPrefix("Amount: P")
        self.input_amount.setFixedHeight(36)

        self.input_desc = QLineEdit()
        self.input_desc.setObjectName("CustomerFormInput")
        self.input_desc.setPlaceholderText("Expense Description / Vendor / Purpose *")
        self.input_desc.setFixedHeight(36)

        row1.addWidget(self.input_date, 2)
        row1.addWidget(self.input_category, 2)
        row1.addWidget(self.input_amount, 2)
        row1.addWidget(self.input_desc, 4)
        form_lay.addLayout(row1)

        # Row 2: Linked Inbound Supply Movement, Record Button, Clear Button
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        self.input_link_movement = QComboBox()
        self.input_link_movement.setFixedHeight(36)

        self.record_expense_btn = QPushButton("Record Expense")
        self.record_expense_btn.setIcon(get_action_icon("plus", "primary", 15))
        self.record_expense_btn.setFixedHeight(36)
        self.record_expense_btn.setFixedWidth(150)
        self.record_expense_btn.clicked.connect(self.add_expense)

        self.clear_expense_btn = QPushButton("Clear")
        self.clear_expense_btn.setObjectName("SecondaryBtn")
        self.clear_expense_btn.setFixedHeight(36)
        self.clear_expense_btn.clicked.connect(self.clear_expense_form)

        row2.addWidget(self.input_link_movement, 5)
        row2.addWidget(self.record_expense_btn)
        row2.addWidget(self.clear_expense_btn)
        form_lay.addLayout(row2)

        layout.addWidget(form_card)

        # Backward compatibility alias
        self.add_btn = self.record_expense_btn

        # 5. Action Toolbar (Search on left, Date range, Actions on right)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        # Search bar
        self.search = QLineEdit()
        self.search.setObjectName("TableSearchInput")
        self.search.addAction(get_icon("search", color="#94A3B8", size=16), QLineEdit.ActionPosition.LeadingPosition)
        self.search.setPlaceholderText("Search description, recorder, or expense...")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(260)
        self.search.textChanged.connect(self._load_table_data)
        toolbar.addWidget(self.search, 1)

        # Date Pickers with Checkboxes
        self.from_check = QCheckBox("From:")
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDate(QDate.currentDate().addMonths(-1))
        self.from_date.dateChanged.connect(lambda: self.from_check.isChecked() and self.refresh())
        self.from_check.toggled.connect(self.refresh)

        self.to_check = QCheckBox("To:")
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDate(QDate.currentDate())
        self.to_date.dateChanged.connect(lambda: self.to_check.isChecked() and self.refresh())
        self.to_check.toggled.connect(self.refresh)

        toolbar.addWidget(self.from_check)
        toolbar.addWidget(self.from_date)
        toolbar.addWidget(self.to_check)
        toolbar.addWidget(self.to_date)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("SecondaryBtn")
        self.refresh_btn.setIcon(get_action_icon("refresh", "secondary", 15))
        self.refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self.refresh_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setObjectName("DangerBtn")
        self.delete_btn.setIcon(get_action_icon("trash", "danger", 15))
        self.delete_btn.clicked.connect(self.delete_expense)
        toolbar.addWidget(self.delete_btn)

        layout.addLayout(toolbar)

        # 6. Card Container wrapping the Table
        card = QFrame()
        card.setObjectName("ModuleCardContainer")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        self.table = QTableWidget()
        self.table.setColumnCount(len(_EXPENSE_HEADERS))
        self.table.setHorizontalHeaderLabels(_EXPENSE_HEADERS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)

        header = self.table.horizontalHeader()
        header.setHighlightSections(False)

        # Col 0: Expense # (Fixed width: 95px, hidden visually)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 95)
        self.table.setColumnHidden(0, True)

        # Col 1: Date (Fixed width: 155px)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 155)

        # Col 2: Category (Fixed width: 135px, centered)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 135)
        if self.table.horizontalHeaderItem(2):
            self.table.horizontalHeaderItem(2).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        # Col 3: Amount (Fixed width: 140px, right-aligned)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 140)
        if self.table.horizontalHeaderItem(3):
            self.table.horizontalHeaderItem(3).setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)

        # Col 4: Description (Stretch to fill remaining horizontal space)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        # Col 5: Recorded By (Fixed width: 160px)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 160)

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

    def _filter_values(self) -> dict:
        start = self.from_date.date().toPyDate().isoformat() if self.from_check.isChecked() else None
        end = self.to_date.date().toPyDate().isoformat() if self.to_check.isChecked() else None
        if end is not None:
            end = f"{end} 23:59:59"
        return {
            "category": self.selected_category or "",
            "start": start,
            "end": end,
        }

    def _selected_id(self) -> int | None:
        r = self.table.currentRow()
        if r < 0:
            return None
        try:
            text = self.table.item(r, 0).text().replace("#", "")
            return int(text)
        except (AttributeError, ValueError):
            return None

    def _create_category_pill(self, cat: str) -> QWidget:
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(container)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        cat_lower = (cat or "").strip().lower()
        if "labor" in cat_lower:
            bg_col, text_col, border_col = "#DBEAFE", "#1D4ED8", "#93C5FD"  # Blue
        elif "material" in cat_lower:
            bg_col, text_col, border_col = "#DCFCE7", "#15803D", "#86EFAC"  # Emerald / Green
        elif "misc" in cat_lower:
            bg_col, text_col, border_col = "#F3E8FF", "#6B21A8", "#D8B4FE"  # Purple
        elif "util" in cat_lower:
            bg_col, text_col, border_col = "#FFEDD5", "#C2410C", "#FDBA74"  # Amber / Orange
        else:
            bg_col, text_col, border_col = "#F1F5F9", "#475569", "#CBD5E1"  # Slate

        pill = QLabel(f" {cat} ")
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
    def _on_category_card_clicked(self, category: str) -> None:
        if self.selected_category == category:
            # Clicked active card again: toggle off, clear filter
            self.selected_category = None
            if category in self.category_cards:
                self.category_cards[category].set_active(False)
        else:
            # Activate clicked card, reset all others to default white
            self.selected_category = category
            for cat, card in self.category_cards.items():
                card.set_active(cat == category)

        self._load_table_data()

    def _load_category_counts(self) -> None:
        f = self._filter_values()
        conn = self._conn()
        try:
            counts = ExpenseManager(conn).count_expenses_by_category(
                start=f["start"], end=f["end"]
            )
            for cat, card in self.category_cards.items():
                card.set_value(counts.get(cat, 0))
        except Exception:  # noqa: BLE001
            pass
        finally:
            conn.close()

    def _load_table_data(self) -> None:
        f = self._filter_values()
        conn = self._conn()
        try:
            rows = ExpenseManager(conn).list_expenses(
                category=f["category"], start=f["start"], end=f["end"]
            )

            needle = self.search.text().strip().lower()
            if needle:
                rows = [
                    r for r in rows
                    if needle in str(r.get("description") or "").lower()
                    or needle in str(r.get("recorded_by") or "").lower()
                    or needle in str(r.get("category") or "").lower()
                    or needle in str(r.get("expense_id") or "").lower()
                ]

            self.table.setRowCount(len(rows))
            total = Decimal("0.00")

            for r, row in enumerate(rows):
                eid = row.get("expense_id")
                edate = _format_datetime(row.get("expense_date"))
                cat = str(row.get("category") or "Miscellaneous")
                amt = Decimal(str(row.get("amount") or 0))
                desc = str(row.get("description") or "—")
                rec_by = str(row.get("recorded_by") or "—").strip() or "—"

                total += amt

                # Col 0: Expense # (Centered)
                it_id = QTableWidgetItem(f"#{eid}")
                it_id.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, 0, it_id)

                # Col 1: Date (Centered)
                it_date = QTableWidgetItem(edate)
                it_date.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, 1, it_date)

                # Col 2: Category (Centered pill)
                self.table.setCellWidget(r, 2, self._create_category_pill(cat))

                # Col 3: Amount (Right-aligned)
                it_amt = QTableWidgetItem(f"P{amt:,.2f}")
                it_amt.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
                self.table.setItem(r, 3, it_amt)

                # Col 4: Description (Stretch to fill space, tooltip for full text)
                it_desc = QTableWidgetItem(desc)
                it_desc.setToolTip(desc)
                self.table.setItem(r, 4, it_desc)

                # Col 5: Recorded By (Left-aligned)
                it_rec = QTableWidgetItem(rec_by)
                it_rec.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.table.setItem(r, 5, it_rec)

            self.total_label.setText(f"P{total:,.2f}")
            self.count_label.setText(f"({len(rows)} {'transaction' if len(rows) == 1 else 'transactions'} displayed)")

        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to load expenses:\n{exc}")
        finally:
            conn.close()

    def refresh(self) -> None:
        self._populate_movements_dropdown()
        self._load_category_counts()
        self._load_table_data()

    def _populate_movements_dropdown(self) -> None:
        if not hasattr(self, "input_link_movement"):
            return
        current_data = self.input_link_movement.currentData()
        conn = self._conn()
        try:
            in_movs = _unlinked_in_movements(conn)
        except Exception:  # noqa: BLE001
            in_movs = []
        finally:
            conn.close()

        self.input_link_movement.blockSignals(True)
        self.input_link_movement.clear()
        self.input_link_movement.addItem("Link Inbound Stock Movement (Optional: Direct Overhead)", None)
        for m in in_movs:
            mid = m.get("movement_id")
            mname = m.get("material_name") or "Item"
            qty = m.get("quantity") or 0
            uom = m.get("unit_of_measure") or "pcs"
            self.input_link_movement.addItem(
                f"Movement #{mid} — {mname} (+{qty} {uom})",
                mid
            )

        if current_data is not None:
            idx = self.input_link_movement.findData(current_data)
            if idx >= 0:
                self.input_link_movement.setCurrentIndex(idx)
        self.input_link_movement.blockSignals(False)

    def clear_expense_form(self) -> None:
        if hasattr(self, "input_date"):
            self.input_date.setDate(QDate.currentDate())
        if hasattr(self, "input_category"):
            self.input_category.setCurrentText("Materials")
        if hasattr(self, "input_amount"):
            self.input_amount.setValue(0.00)
        if hasattr(self, "input_desc"):
            self.input_desc.clear()
        if hasattr(self, "input_link_movement"):
            self.input_link_movement.setCurrentIndex(0)

    def clear_filters(self) -> None:
        self.from_check.setChecked(False)
        self.to_check.setChecked(False)
        self.selected_category = None
        for card in self.category_cards.values():
            card.set_active(False)
        self.search.clear()
        self.refresh()

    def add_expense(self) -> None:
        amount = Decimal(str(self.input_amount.value()))
        if amount <= 0:
            QMessageBox.warning(self, "Record Expense", "Please enter a valid expense amount greater than zero.")
            self.input_amount.setFocus()
            return

        desc = self.input_desc.text().strip()
        if not desc:
            QMessageBox.warning(self, "Record Expense", "Please enter an expense description or purpose.")
            self.input_desc.setFocus()
            return

        category = self.input_category.currentText()
        if category not in EXPENSE_CATEGORIES:
            QMessageBox.warning(self, "Record Expense", f"Category must be one of {EXPENSE_CATEGORIES}")
            return

        edate = self.input_date.date().toPyDate().isoformat()
        movement_id = self.input_link_movement.currentData()

        conn = self._conn()
        try:
            mgr = ExpenseManager(conn)
            eid = mgr.create_expense(
                category, str(amount), desc,
                recorded_by_user_id=self._user_id(),
                expense_date=edate
            )
            if movement_id is not None:
                mgr.link_movement(eid, movement_id)

            QMessageBox.information(
                self, "Expense Recorded",
                f"Expense recorded successfully for P{amount:,.2f}."
            )
            self.clear_expense_form()
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            conn.close()

    def delete_expense(self) -> None:
        eid = self._selected_id()
        if eid is None:
            QMessageBox.warning(self, "Delete Expense", "Please select an expense from the table first.")
            return

        if QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete expense record #{eid}?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return

        conn = self._conn()
        try:
            ExpenseManager(conn).delete_expense(eid)
            QMessageBox.information(self, "Deleted", f"Expense #{eid} has been removed.")
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to delete expense:\n{exc}")
        finally:
            conn.close()

    # -- compatibility with legacy slots --
    def refresh_expenses(self) -> None:
        self.refresh()

    def add_expenses(self) -> None:
        self.add_expense()
