"""User Management module widget (Professional SaaS / HCI format).

Features:
  - Visual hierarchy: Section title + descriptive subtitle.
  - Action toolbar: Live search, Role filter, and Status filter.
  - Actions: Refresh, Reset Password, Toggle Active, Edit Profile, and '+ Add User'.
  - Elevated card container wrapping the users data table.
  - Status and Role pills (Admin, Staff, Active, Inactive).
  - Modern modal dialogs for creating/editing user accounts and resetting passwords.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QDialog, QFormLayout, QMessageBox, QLabel,
    QComboBox, QHeaderView, QAbstractItemView, QFrame,
)
from PyQt6.QtCore import Qt

from auth.user_management import UserManager, ALLOWED_ROLES
from database.database import get_connection
from ui.icons import get_icon, get_action_icon

_USER_HEADERS = [
    "User #", "Username", "Full Name", "System Role", "Status", "Date Registered"
]


class UserDialog(QDialog):
    """Add / Edit User dialog with clean form controls and validation."""

    def __init__(self, parent=None, user: dict | None = None):
        super().__init__(parent)
        self._is_edit = user is not None
        self.setWindowTitle("Edit User Profile" if self._is_edit else "Add New User Account")
        self.setMinimumWidth(440)
        data = user or {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Edit User Account" if self._is_edit else "Create System User Account")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        sub = QLabel("Configure login credentials and access role permissions.")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(title)
        layout.addWidget(sub)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.username_edit = QLineEdit(str(data.get("username") or ""))
        self.username_edit.setPlaceholderText("e.g. jdelacruz")
        self.username_edit.setEnabled(not self._is_edit)
        form.addRow("Username *:", self.username_edit)

        if not self._is_edit:
            self.pw_edit = QLineEdit()
            self.pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.pw_edit.setPlaceholderText("Enter secure password...")
            form.addRow("Password *:", self.pw_edit)
        else:
            self.pw_edit = None

        self.first_edit = QLineEdit(str(data.get("first_name") or ""))
        self.first_edit.setPlaceholderText("e.g. Juan")
        form.addRow("First Name *:", self.first_edit)

        self.last_edit = QLineEdit(str(data.get("last_name") or ""))
        self.last_edit.setPlaceholderText("e.g. Dela Cruz")
        form.addRow("Last Name *:", self.last_edit)

        self.role_box = QComboBox()
        self.role_box.addItems(list(ALLOWED_ROLES))
        if data.get("role") in ALLOWED_ROLES:
            self.role_box.setCurrentText(data["role"])
        form.addRow("System Role *:", self.role_box)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("SecondaryBtn")
        cancel.clicked.connect(self.reject)

        save = QPushButton("Save User Profile")
        save.setIcon(get_action_icon("check", "primary", 15))
        save.clicked.connect(self._on_save)

        btns.addWidget(cancel)
        btns.addWidget(save)
        layout.addLayout(btns)

    def _on_save(self) -> None:
        if not self.username_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Username is required.")
            return
        if not self._is_edit and not self.pw_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Password is required for new accounts.")
            return
        if not self.first_edit.text().strip() or not self.last_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "First and Last names are required.")
            return
        self.accept()

    def values(self) -> dict:
        vals = {
            "username": self.username_edit.text().strip(),
            "first_name": self.first_edit.text().strip(),
            "last_name": self.last_edit.text().strip(),
            "role": self.role_box.currentText(),
        }
        if self.pw_edit is not None:
            vals["password"] = self.pw_edit.text()
        return vals


class ResetPasswordDialog(QDialog):
    """Secure password reset dialog."""

    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reset Password")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel(f"Reset Password for '{username}'")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0F172A;")
        sub = QLabel("Enter and confirm the new account password.")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(title)
        layout.addWidget(sub)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.p1 = QLineEdit()
        self.p1.setEchoMode(QLineEdit.EchoMode.Password)
        self.p1.setPlaceholderText("New password...")
        form.addRow("New Password:", self.p1)

        self.p2 = QLineEdit()
        self.p2.setEchoMode(QLineEdit.EchoMode.Password)
        self.p2.setPlaceholderText("Confirm new password...")
        form.addRow("Confirm Password:", self.p2)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("SecondaryBtn")
        cancel.clicked.connect(self.reject)

        save = QPushButton("Update Password")
        save.setIcon(get_action_icon("key", "primary", 15))
        save.clicked.connect(self._on_save)

        btns.addWidget(cancel)
        btns.addWidget(save)
        layout.addLayout(btns)

    def _on_save(self) -> None:
        p1 = self.p1.text()
        p2 = self.p2.text()
        if not p1:
            QMessageBox.warning(self, "Validation Error", "Password cannot be empty.")
            return
        if p1 != p2:
            QMessageBox.warning(self, "Validation Error", "Passwords do not match.")
            return
        self.accept()

    def password(self) -> str:
        return self.p1.text()


class UserWidget(QWidget):
    """User Accounts & Security module with modern HCI layout."""

    def __init__(self, current_user: dict | None = None, parent=None):
        super().__init__(parent)
        self.current_user = current_user or {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(18)

        # 1. Page Header (Title + Subtitle)
        header_lay = QVBoxLayout()
        header_lay.setSpacing(4)
        title = QLabel("User Accounts & Access Control")
        title.setObjectName("ModuleHeaderTitle")
        sub = QLabel("Manage system staff credentials, administrator privileges, and active login access.")
        sub.setObjectName("ModuleHeaderSub")
        header_lay.addWidget(title)
        header_lay.addWidget(sub)
        layout.addLayout(header_lay)

        # 2. Action Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.search = QLineEdit()
        self.search.setObjectName("TableSearchInput")
        self.search.addAction(get_icon("search", color="#94A3B8", size=16), QLineEdit.ActionPosition.LeadingPosition)
        self.search.setPlaceholderText("Search users by username or full name...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refresh)
        toolbar.addWidget(self.search, 1)

        self.role_filter = QComboBox()
        self.role_filter.setObjectName("TableFilterCombo")
        self.role_filter.addItem("All Roles", "")
        for r in ALLOWED_ROLES:
            self.role_filter.addItem(r, r)
        self.role_filter.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.role_filter)

        self.status_filter = QComboBox()
        self.status_filter.setObjectName("TableFilterCombo")
        self.status_filter.addItem("All Statuses", "")
        self.status_filter.addItem("Active Only", "ACTIVE")
        self.status_filter.addItem("Inactive Only", "INACTIVE")
        self.status_filter.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.status_filter)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setIcon(get_action_icon("refresh", "secondary", 15))
        self.refresh_btn.setObjectName("SecondaryBtn")
        self.refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self.refresh_btn)

        self.pw_btn = QPushButton("Reset Password")
        self.pw_btn.setIcon(get_action_icon("key", "secondary", 15))
        self.pw_btn.setObjectName("SecondaryBtn")
        self.pw_btn.clicked.connect(self.reset_password)
        toolbar.addWidget(self.pw_btn)

        self.toggle_btn = QPushButton("Toggle Active")
        self.toggle_btn.setIcon(get_action_icon("shield-check", "secondary", 15))
        self.toggle_btn.setObjectName("SecondaryBtn")
        self.toggle_btn.clicked.connect(self.toggle_user)
        toolbar.addWidget(self.toggle_btn)

        self.edit_btn = QPushButton("Edit Profile")
        self.edit_btn.setIcon(get_action_icon("edit", "secondary", 15))
        self.edit_btn.setObjectName("SecondaryBtn")
        self.edit_btn.clicked.connect(self.edit_user)
        toolbar.addWidget(self.edit_btn)

        self.add_btn = QPushButton("Add User")
        self.add_btn.setIcon(get_action_icon("user-plus", "primary", 16))
        self.add_btn.clicked.connect(self.add_user)
        toolbar.addWidget(self.add_btn)

        layout.addLayout(toolbar)

        # 3. Card Container wrapping the Table
        card = QFrame()
        card.setObjectName("ModuleCardContainer")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        self.table = QTableWidget()
        self.table.setColumnCount(len(_USER_HEADERS))
        self.table.setHorizontalHeaderLabels(_USER_HEADERS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 115)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 115)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.doubleClicked.connect(self.edit_user)

        card_lay.addWidget(self.table)
        layout.addWidget(card, 1)

        self.refresh()

    # -- helpers --
    def _conn(self):
        return get_connection()

    def _selected_id(self) -> int | None:
        r = self.table.currentRow()
        if r < 0:
            return None
        try:
            text = self.table.item(r, 0).text().replace("#", "")
            return int(text)
        except (AttributeError, ValueError):
            return None

    def _create_role_pill(self, role: str) -> QWidget:
        container = QWidget()
        lay = QHBoxLayout(container)
        lay.setContentsMargins(6, 4, 6, 4)
        pill = QLabel(role)
        pill.setObjectName("StatusPill")

        if role == "Admin":
            pill.setProperty("status", "ready")     # Purple / Gold
        else:
            pill.setProperty("status", "processing") # Blue

        pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pill.style().unpolish(pill)
        pill.style().polish(pill)
        lay.addWidget(pill)
        return container

    def _create_status_pill(self, is_active: bool) -> QWidget:
        container = QWidget()
        lay = QHBoxLayout(container)
        lay.setContentsMargins(6, 4, 6, 4)
        pill = QLabel("● Active" if is_active else "● Inactive")
        pill.setObjectName("StatusPill")
        pill.setProperty("status", "paid" if is_active else "cancelled")
        pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pill.style().unpolish(pill)
        pill.style().polish(pill)
        lay.addWidget(pill)
        return container

    # -- Core logic --
    def refresh(self) -> None:
        conn = self._conn()
        try:
            rows = UserManager(conn).list_users(include_inactive=True)

            # Role filter
            rfilter = self.role_filter.currentData() or ""
            if rfilter:
                rows = [r for r in rows if r.get("role") == rfilter]

            # Status filter
            sfilter = self.status_filter.currentData() or ""
            if sfilter == "ACTIVE":
                rows = [r for r in rows if r.get("is_active")]
            elif sfilter == "INACTIVE":
                rows = [r for r in rows if not r.get("is_active")]

            # Needle search
            needle = self.search.text().strip().lower()
            if needle:
                rows = [
                    r for r in rows
                    if needle in str(r.get("username") or "").lower()
                    or needle in str(r.get("first_name") or "").lower()
                    or needle in str(r.get("last_name") or "").lower()
                ]

            self.table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                uid = row.get("user_id")
                uname = str(row.get("username") or "")
                first = str(row.get("first_name") or "")
                last = str(row.get("last_name") or "")
                full_name = f"{first} {last}".strip() or "—"
                role = str(row.get("role") or "Staff")
                active = bool(row.get("is_active"))
                created = str(row.get("created_at") or "")

                self.table.setItem(r, 0, QTableWidgetItem(f"#{uid}"))
                self.table.setItem(r, 1, QTableWidgetItem(uname))
                self.table.setItem(r, 2, QTableWidgetItem(full_name))
                self.table.setCellWidget(r, 3, self._create_role_pill(role))
                self.table.setCellWidget(r, 4, self._create_status_pill(active))
                self.table.setItem(r, 5, QTableWidgetItem(created))

        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to load user accounts:\n{exc}")
        finally:
            conn.close()

    def add_user(self) -> None:
        dlg = UserDialog(self)
        if not dlg.exec():
            return
        vals = dlg.values()
        conn = self._conn()
        try:
            UserManager(conn).create_user(
                vals["username"], vals["password"],
                vals["first_name"], vals["last_name"],
                vals["role"]
            )
            QMessageBox.information(self, "User Created", f"Account '{vals['username']}' created successfully.")
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to create user:\n{exc}")
        finally:
            conn.close()

    def edit_user(self) -> None:
        uid = self._selected_id()
        if uid is None:
            QMessageBox.warning(self, "Edit User", "Please select a user account from the table first.")
            return

        conn = self._conn()
        try:
            cur = UserManager(conn).get_user(uid)
        finally:
            conn.close()

        if not cur:
            QMessageBox.warning(self, "Error", "User record not found.")
            return

        dlg = UserDialog(self, user=cur)
        if not dlg.exec():
            return

        vals = dlg.values()
        conn = self._conn()
        try:
            UserManager(conn).update_user(
                uid,
                first_name=vals["first_name"],
                last_name=vals["last_name"],
                role=vals["role"],
            )
            QMessageBox.information(self, "User Updated", f"Profile for '{cur['username']}' updated successfully.")
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to update user:\n{exc}")
        finally:
            conn.close()

    def toggle_user(self) -> None:
        uid = self._selected_id()
        if uid is None:
            QMessageBox.warning(self, "Toggle Status", "Please select a user account from the table first.")
            return

        conn = self._conn()
        try:
            mgr = UserManager(conn)
            u = mgr.get_user(uid)
            if not u:
                return

            new_status = not u["is_active"]
            mgr.set_active(uid, new_status)
            status_word = "Activated" if new_status else "Deactivated"
            QMessageBox.information(self, "Status Updated", f"User '{u['username']}' has been {status_word}.")
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to update status:\n{exc}")
        finally:
            conn.close()

    def reset_password(self) -> None:
        uid = self._selected_id()
        if uid is None:
            QMessageBox.warning(self, "Reset Password", "Please select a user account from the table first.")
            return

        conn = self._conn()
        try:
            u = UserManager(conn).get_user(uid)
        finally:
            conn.close()

        if not u:
            return

        dlg = ResetPasswordDialog(u["username"], self)
        if not dlg.exec():
            return

        new_pw = dlg.password()
        conn = self._conn()
        try:
            UserManager(conn).change_password(uid, new_pw)
            QMessageBox.information(self, "Password Reset", f"Password for '{u['username']}' has been updated.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to reset password:\n{exc}")
        finally:
            conn.close()
