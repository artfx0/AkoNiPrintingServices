"""Two-Panel Login window (Professional SaaS / HCI format).

Features:
  - Two-panel split layout: Left Brand/Showcase panel + Right Authentication panel.
  - AkoNi brand identity with gold badge and feature value propositions.
  - Password visibility toggle (Show / Hide eye button) for accessible input verification.
  - Smooth focus states, accessible 42px touch targets, and Enter-key submission.
  - Inline error notifications for immediate, non-intrusive feedback.
  - Seamless integration with session manager and MySQL authentication.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QFrame, QGraphicsDropShadowEffect, QCheckBox,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QCursor

from auth.login import authenticate
from auth.session import Session
from database.database import get_connection
from ui.icons import get_icon, get_pixmap


class LoginWindow(QDialog):
    """Modern Two-Panel SaaS login dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AkoNi Printing Services — Sign In")
        self.setFixedSize(860, 540)
        self.user: dict | None = None

        # Clean off-screen / window background
        self.setStyleSheet("""
            QDialog {
                background-color: #F8FAFC;
            }
        """)

        # Root Layout: Center the elevated card
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(20, 20, 20, 20)
        root_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Elevated Two-Panel Card Container
        card = QFrame()
        card.setObjectName("TwoPanelCard")
        card.setStyleSheet("""
            QFrame#TwoPanelCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 16px;
            }
        """)

        # Drop Shadow for Elevation
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(15, 23, 42, 25))
        shadow.setOffset(0, 10)
        card.setGraphicsEffect(shadow)

        # Horizontal layout splitting Left and Right panels
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # 1. Left Panel (Brand & Feature Showcase)
        left_panel = self._build_left_panel()
        card_layout.addWidget(left_panel, 42)

        # 2. Right Panel (Interactive Login Form)
        right_panel = self._build_right_panel()
        card_layout.addWidget(right_panel, 58)

        root_lay.addWidget(card)

    # ------------------------------------------------------------------
    # Left Panel: Brand Identity & Value Propositions
    # ------------------------------------------------------------------
    def _build_left_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("BrandPanel")
        panel.setStyleSheet("""
            QFrame#BrandPanel {
                background-color: #0F172A;
                border-top-left-radius: 15px;
                border-bottom-left-radius: 15px;
                border-top-right-radius: 0px;
                border-bottom-right-radius: 0px;
            }
        """)

        lay = QVBoxLayout(panel)
        lay.setContentsMargins(36, 42, 36, 36)
        lay.setSpacing(20)

        # Brand Logo Badge
        brand_icon = QLabel()
        brand_icon.setFixedSize(54, 54)
        brand_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_icon.setStyleSheet("""
            background-color: #FEF3C7;
            border-radius: 14px;
        """)
        brand_icon.setPixmap(get_pixmap("printer", color="#B45309", size=28))
        lay.addWidget(brand_icon)

        # Brand Title & Tagline
        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        brand_title = QLabel("AkoNi Printing")
        brand_title.setStyleSheet("font-size: 22px; font-weight: bold; color: #FFFFFF;")

        brand_tagline = QLabel("POS & Management ERP System")
        brand_tagline.setStyleSheet("font-size: 13px; color: #D4AF37; font-weight: 600;")

        title_box.addWidget(brand_title)
        title_box.addWidget(brand_tagline)
        lay.addLayout(title_box)

        # Subtle Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("background-color: #334155; height: 1px; border: none;")
        lay.addWidget(div)

        # Feature List (HCI Value Propositions)
        features_lay = QVBoxLayout()
        features_lay.setSpacing(14)

        features = [
            ("zap", "#F59E0B", "Fast Order Processing", "Manage custom layout jobs, design fees, and rush print orders."),
            ("inventory", "#60A5FA", "Smart Stock Control", "Real-time raw material balances with automated reorder warnings."),
            ("trending-up", "#34D399", "Financial & P&L Insights", "Track settlements, operating overheads, and PDF invoices."),
        ]

        for icon_name, icon_col, feat_title, feat_desc in features:
            item_row = QHBoxLayout()
            item_row.setSpacing(12)
            item_row.setAlignment(Qt.AlignmentFlag.AlignTop)

            badge = QLabel()
            badge.setFixedSize(30, 30)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet("background: #1E293B; border-radius: 8px;")
            badge.setPixmap(get_pixmap(icon_name, color=icon_col, size=16))
            item_row.addWidget(badge)

            text_box = QVBoxLayout()
            text_box.setSpacing(2)
            h = QLabel(feat_title)
            h.setStyleSheet("color: #F8FAFC; font-weight: 600; font-size: 12px;")
            p = QLabel(feat_desc)
            p.setWordWrap(True)
            p.setStyleSheet("color: #94A3B8; font-size: 11px; line-height: 14px;")
            text_box.addWidget(h)
            text_box.addWidget(p)

            item_row.addLayout(text_box, 1)
            features_lay.addLayout(item_row)

        lay.addLayout(features_lay)
        lay.addStretch(1)

        # Footer system note
        footer = QLabel("v2.4 Enterprise • Local MySQL Engine")
        footer.setStyleSheet("color: #64748B; font-size: 10px;")
        lay.addWidget(footer)

        return panel

    # ------------------------------------------------------------------
    # Right Panel: Interactive Authentication Form
    # ------------------------------------------------------------------
    def _build_right_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("FormPanel")
        panel.setStyleSheet("""
            QFrame#FormPanel {
                background-color: #FFFFFF;
                border-top-right-radius: 15px;
                border-bottom-right-radius: 15px;
                border-top-left-radius: 0px;
                border-bottom-left-radius: 0px;
            }
        """)

        lay = QVBoxLayout(panel)
        lay.setContentsMargins(44, 40, 44, 36)
        lay.setSpacing(16)
        lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Header: Greeting
        header_box = QVBoxLayout()
        header_box.setSpacing(4)

        greet_title = QLabel("Welcome Back")
        greet_title.setStyleSheet("font-size: 22px; font-weight: bold; color: #0F172A;")

        greet_sub = QLabel("Sign in to access your operations dashboard.")
        greet_sub.setStyleSheet("font-size: 13px; color: #64748B;")

        header_box.addWidget(greet_title)
        header_box.addWidget(greet_sub)
        lay.addLayout(header_box)

        # Inline Error Banner (Hidden by default)
        self.error_banner = QFrame()
        self.error_banner.setObjectName("ErrorBanner")
        self.error_banner.setStyleSheet("""
            QFrame#ErrorBanner {
                background-color: #FEE2E2;
                border: 1px solid #FCA5A5;
                border-radius: 8px;
            }
        """)
        eb_lay = QHBoxLayout(self.error_banner)
        eb_lay.setContentsMargins(12, 8, 12, 8)
        eb_lay.setSpacing(10)
        eb_icon = QLabel()
        eb_icon.setPixmap(get_pixmap("alert-circle", color="#DC2626", size=16))
        self.error_msg_lbl = QLabel()
        self.error_msg_lbl.setStyleSheet("color: #DC2626; font-size: 12px; font-weight: 500;")
        self.error_msg_lbl.setWordWrap(True)
        eb_lay.addWidget(eb_icon)
        eb_lay.addWidget(self.error_msg_lbl, 1)
        self.error_banner.hide()
        lay.addWidget(self.error_banner)

        # Input Fields Container
        fields_lay = QVBoxLayout()
        fields_lay.setSpacing(14)

        # Username Field
        u_box = QVBoxLayout()
        u_box.setSpacing(4)
        u_lbl = QLabel("Username")
        u_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #334155;")
        self.username_edit = QLineEdit()
        self.username_edit.addAction(get_icon("user", color="#94A3B8", size=16), QLineEdit.ActionPosition.LeadingPosition)
        self.username_edit.setPlaceholderText("Enter your username")
        self.username_edit.setFixedHeight(42)
        self.username_edit.setStyleSheet("""
            QLineEdit {
                background-color: #F8FAFC;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1.5px solid #D4AF37;
                background-color: #FFFFFF;
            }
        """)
        u_box.addWidget(u_lbl)
        u_box.addWidget(self.username_edit)
        fields_lay.addLayout(u_box)

        # Password Field with Show/Hide toggle
        p_box = QVBoxLayout()
        p_box.setSpacing(4)
        p_lbl = QLabel("Password")
        p_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #334155;")

        p_row = QHBoxLayout()
        p_row.setSpacing(6)

        self.password_edit = QLineEdit()
        self.password_edit.addAction(get_icon("lock", color="#94A3B8", size=16), QLineEdit.ActionPosition.LeadingPosition)
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Enter your password")
        self.password_edit.setFixedHeight(42)
        self.password_edit.setStyleSheet("""
            QLineEdit {
                background-color: #F8FAFC;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1.5px solid #D4AF37;
                background-color: #FFFFFF;
            }
        """)

        # Password Reveal Eye Toggle
        self.eye_btn = QPushButton()
        self.eye_btn.setFixedSize(42, 42)
        self.eye_btn.setIcon(get_icon("eye", color="#64748B", size=18))
        self.eye_btn.setIconSize(QSize(18, 18))
        self.eye_btn.setToolTip("Show / Hide password")
        self.eye_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.eye_btn.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                color: #64748B;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
                color: #0F172A;
                border-color: #94A3B8;
            }
        """)
        self.eye_btn.clicked.connect(self._toggle_password_visibility)

        p_row.addWidget(self.password_edit, 1)
        p_row.addWidget(self.eye_btn)

        p_box.addWidget(p_lbl)
        p_box.addLayout(p_row)
        fields_lay.addLayout(p_box)

        lay.addLayout(fields_lay)

        # Keyboard Navigation Connections
        self.username_edit.returnPressed.connect(self.password_edit.setFocus)
        self.password_edit.returnPressed.connect(self.try_login)

        # Remember / Credentials row
        options_row = QHBoxLayout()
        self.remember_box = QCheckBox("Keep me signed in")
        self.remember_box.setChecked(True)
        self.remember_box.setStyleSheet("color: #64748B; font-size: 12px;")
        options_row.addWidget(self.remember_box)
        options_row.addStretch(1)

        role_hint = QLabel("Admin & Staff Access")
        role_hint.setStyleSheet("color: #94A3B8; font-size: 11px;")
        options_row.addWidget(role_hint)
        lay.addLayout(options_row)

        # Primary Sign In Button (HCI prominent call-to-action)
        self.login_btn = QPushButton("Sign In to Dashboard")
        self.login_btn.setIcon(get_icon("arrow-right", color="#0F172A", size=16))
        self.login_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.login_btn.setFixedHeight(44)
        self.login_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #D4AF37;
                color: #0F172A;
                font-weight: bold;
                font-size: 14px;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #C59B27;
            }
            QPushButton:pressed {
                background-color: #B58900;
            }
        """)
        self.login_btn.clicked.connect(self.try_login)
        lay.addWidget(self.login_btn)

        # Seed hint footnote
        hint = QLabel("Default login: <b>admin</b> / <b>admin123</b>")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #94A3B8; font-size: 11px; margin-top: 6px;")
        lay.addWidget(hint)

        return panel

    # ------------------------------------------------------------------
    # Actions & Validation
    # ------------------------------------------------------------------
    def _toggle_password_visibility(self) -> None:
        """Toggles between hidden password bullets and plain readable text."""
        if self.password_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.eye_btn.setIcon(get_icon("eye-off", color="#0F172A", size=18))
            self.eye_btn.setToolTip("Hide password")
        else:
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.eye_btn.setIcon(get_icon("eye", color="#64748B", size=18))
            self.eye_btn.setToolTip("Show password")

    def _show_error(self, message: str) -> None:
        self.error_msg_lbl.setText(message)
        self.error_banner.show()

    def _hide_error(self) -> None:
        self.error_banner.hide()

    def try_login(self) -> None:
        self._hide_error()
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        if not username or not password:
            self._show_error("Please enter both username and password.")
            if not username:
                self.username_edit.setFocus()
            else:
                self.password_edit.setFocus()
            return

        try:
            conn = get_connection()
        except Exception as exc:  # noqa: BLE001
            self._show_error(f"Cannot connect to MySQL server:\n{exc}")
            return

        try:
            user = authenticate(conn, username, password)
        finally:
            conn.close()

        if user is None:
            self._show_error("Invalid username/password or account is inactive.")
            self.password_edit.selectAll()
            self.password_edit.setFocus()
            return

        self.user = user
        Session.set_user(user)
        self.accept()
