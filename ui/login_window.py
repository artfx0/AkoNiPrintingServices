"""Login window (Professional SaaS / HCI format).

Features:
  - Modern card-centered design aligned with the Rhombus aesthetic.
  - AkoNi brand identity badge with gold accent.
  - Clean form inputs with focus states and Enter-key submission.
  - Informative validation and database connectivity error handling.
  - Returns authenticated user dict on accept.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QMessageBox, QFrame, QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from auth.login import authenticate
from auth.session import Session
from database.database import get_connection


class LoginWindow(QDialog):
    """Modern SaaS login dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AkoNi Printing Services — Sign In")
        self.setFixedSize(420, 520)
        self.user: dict | None = None

        self.setStyleSheet("""
            QDialog {
                background-color: #F8FAFC;
            }
        """)

        # Main Layout
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(28, 28, 28, 28)
        root_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Elevated White Card
        card = QFrame()
        card.setObjectName("LoginCard")
        card.setStyleSheet("""
            QFrame#LoginCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 16px;
            }
        """)

        # Drop Shadow for Card
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(15, 23, 42, 20))
        shadow.setOffset(0, 8)
        card.setGraphicsEffect(shadow)

        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(32, 36, 32, 32)
        card_lay.setSpacing(18)
        card_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Brand Icon Badge
        brand_icon = QLabel("🖨️")
        brand_icon.setFixedSize(54, 54)
        brand_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_icon.setStyleSheet("""
            background-color: #FEF3C7;
            border-radius: 27px;
            font-size: 26px;
        """)
        card_lay.addWidget(brand_icon, alignment=Qt.AlignmentFlag.AlignCenter)

        # Brand Titles
        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        brand_title = QLabel("AkoNi Printing")
        brand_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #0F172A;")

        brand_sub = QLabel("POS & Management ERP System")
        brand_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_sub.setStyleSheet("font-size: 12px; color: #64748B;")

        title_box.addWidget(brand_title)
        title_box.addWidget(brand_sub)
        card_lay.addLayout(title_box)

        card_lay.addSpacing(6)

        # Input Fields
        input_box = QVBoxLayout()
        input_box.setSpacing(12)

        # Username Input
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("👤  Username")
        self.username_edit.setStyleSheet("""
            QLineEdit {
                background-color: #F8FAFC;
                color: #0F172A;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1.5px solid #D4AF37;
                background-color: #FFFFFF;
            }
        """)
        input_box.addWidget(self.username_edit)

        # Password Input
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("🔒  Password")
        self.password_edit.setStyleSheet("""
            QLineEdit {
                background-color: #F8FAFC;
                color: #0F172A;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1.5px solid #D4AF37;
                background-color: #FFFFFF;
            }
        """)
        self.password_edit.returnPressed.connect(self.try_login)
        self.username_edit.returnPressed.connect(self.password_edit.setFocus)
        input_box.addWidget(self.password_edit)

        card_lay.addLayout(input_box)

        # Sign In Button
        self.login_btn = QPushButton("Sign In to Dashboard")
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #D4AF37;
                color: #0F172A;
                font-weight: bold;
                font-size: 14px;
                border: none;
                border-radius: 8px;
                padding: 11px 0px;
            }
            QPushButton:hover {
                background-color: #C59B27;
            }
            QPushButton:pressed {
                background-color: #B58900;
            }
        """)
        self.login_btn.clicked.connect(self.try_login)
        card_lay.addWidget(self.login_btn)

        # Seed hint
        hint = QLabel("Default login: admin / admin123")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #94A3B8; font-size: 11px; margin-top: 4px;")
        card_lay.addWidget(hint)

        root_lay.addWidget(card)

    def try_login(self) -> None:
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        if not username or not password:
            QMessageBox.warning(self, "Sign In Error", "Please enter both username and password.")
            return

        try:
            conn = get_connection()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self, "Database Error",
                f"Cannot connect to MySQL database.\nPlease check your local MySQL server is running.\n\n{exc}"
            )
            return

        try:
            user = authenticate(conn, username, password)
        finally:
            conn.close()

        if user is None:
            QMessageBox.warning(self, "Authentication Failed", "Invalid credentials or inactive user account.")
            return

        self.user = user
        Session.set_user(user)
        self.accept()
