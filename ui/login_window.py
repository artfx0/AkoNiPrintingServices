"""Login window (PyQt6). Returns the authenticated user dict on accept."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QLabel,
    QMessageBox, QDialogButtonBox,
)

from auth.login import authenticate
from auth.session import Session
from database.database import get_connection


class LoginWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AkoNi Printing Services — Login")
        self.setMinimumWidth(340)
        self.user: dict | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Sign in with your Admin / Staff account"))
        form = QFormLayout()
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("username")
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("password")
        form.addRow("Username:", self.username_edit)
        form.addRow("Password:", self.password_edit)
        layout.addLayout(form)

        self.hint = QLabel("Default seed: admin / admin123 (after first DB init)")
        self.hint.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.hint)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Login")
        buttons.accepted.connect(self.try_login)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.password_edit.returnPressed.connect(self.try_login)

    def try_login(self) -> None:
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        if not username or not password:
            QMessageBox.warning(self, "Login", "Enter username and password.")
            return
        try:
            conn = get_connection()
        except Exception as exc:  # noqa: BLE001 — show DB errors in UI
            QMessageBox.critical(
                self, "Database error",
                f"Cannot connect to MySQL.\nCheck db_config.ini / env vars.\n\n{exc}")
            return
        try:
            user = authenticate(conn, username, password)
        finally:
            conn.close()
        if user is None:
            QMessageBox.warning(self, "Login", "Invalid credentials or inactive account.")
            return
        self.user = user
        Session.set_user(user)
        self.accept()
