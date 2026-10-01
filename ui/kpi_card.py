"""KpiCard — Modern SaaS KPI metric card (Rhombus reference style).

Layout inside the card:
  Top row    : Title on the left (small grey text) + small icon badge on the right
  Middle row : The Value (large, bold text, e.g., 'P1,100.00')
  Bottom row : A Subtitle showing a comparison (e.g., '+5% vs last month' in green)

Dynamic Alert:
  When set_alert(True) (e.g. Low Stock Items > 0), the card's border changes
  to red (#EF4444) and the subtitle text turns red.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QVBoxLayout, QGraphicsDropShadowEffect,
    QSizePolicy, QStyle, QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPixmap

TONE_POSITIVE = "positive"
TONE_NEGATIVE = "negative"
TONE_NEUTRAL = "neutral"


def _apply_card_shadow(widget: QFrame) -> None:
    """Apply a subtle drop shadow effect."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(14)
    effect.setXOffset(0)
    effect.setYOffset(2)
    effect.setColor(QColor(15, 23, 42, 16))  # Subtle slate shadow
    widget.setGraphicsEffect(effect)


def _repolish(widget) -> None:
    """Re-evaluate QSS dynamic property selectors after a property change."""
    style = widget.style()
    if style:
        style.unpolish(widget)
        style.polish(widget)


class KpiCard(QFrame):
    """Modern SaaS KPI metric card matching the reference design."""

    clicked = pyqtSignal()

    def __init__(self, title: str,
                 icon: str | QIcon | QPixmap | QStyle.StandardPixmap | None = None,
                 value: str = "—",
                 subtitle: str = "",
                 subtitle_tone: str = TONE_NEUTRAL,
                 icon_theme: str = "gold",
                 parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("KpiCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(130)
        self.setMinimumWidth(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        # Top row: Title on the left + Icon badge on the top-right
        top = QHBoxLayout()
        top.setSpacing(8)
        top.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("KpiTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        top.addWidget(self.title_label, 1)

        self._icon_theme = icon_theme
        self.icon_label = QLabel()
        self.icon_label.setObjectName("KpiIconBadge")
        self.icon_label.setProperty("theme", icon_theme)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setFixedSize(34, 34)
        self.icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        top.addWidget(self.icon_label)
        layout.addLayout(top)

        # Middle row: The Value (large, bold text)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("KpiValue")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.value_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.value_label)

        # Bottom row: Subtitle showing a comparison (green / red / grey text)
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("KpiSubtitle")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.subtitle_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.subtitle_label)
        layout.addStretch(1)

        # Initialize content & styling
        self.set_icon(icon)
        self.set_subtitle(subtitle, subtitle_tone)
        _apply_card_shadow(self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    # -- Content setters & getters -------------------------------------
    def set_icon(self, icon: str | QIcon | QPixmap | QStyle.StandardPixmap | None) -> None:
        """Set the top-row icon from a vector SVG, standard Qt icon, QPixmap, or file path."""
        if icon is None:
            self.icon_label.setText("")
            return

        if isinstance(icon, QStyle.StandardPixmap):
            style = QApplication.style()
            if style:
                self.icon_label.setPixmap(style.standardIcon(icon).pixmap(18, 18))
                return

        if isinstance(icon, QIcon):
            self.icon_label.setPixmap(icon.pixmap(18, 18))
            return

        if isinstance(icon, QPixmap):
            self.icon_label.setPixmap(
                icon.scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )
            return

        if isinstance(icon, str):
            from ui.icons import SVG_PATHS, get_pixmap
            if icon in SVG_PATHS:
                theme_colors = {
                    "gold": "#B45309",
                    "coral": "#DC2626",
                    "blue": "#2563EB",
                    "amber": "#D97706",
                    "emerald": "#16A34A",
                }
                theme = getattr(self, "_icon_theme", "gold")
                color = theme_colors.get(theme, "#B45309")
                self.icon_label.setPixmap(get_pixmap(icon, color=color, size=18))
                return
            p = Path(icon)
            if p.is_file():
                self.icon_label.setPixmap(
                    QPixmap(str(p)).scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                )
            else:
                self.icon_label.setText(icon)

    def set_title(self, title: str) -> None:
        self.title_label.setText(title)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)

    def set_subtitle(self, text: str, tone: str = TONE_NEUTRAL) -> None:
        """Set comparison subtitle text and tone ('positive' = green, 'negative' = red, 'neutral' = grey)."""
        self.subtitle_label.setText(text)
        self.subtitle_label.setProperty("tone", tone)
        _repolish(self.subtitle_label)

    def set_alert(self, alert: bool) -> None:
        """Dynamic alert: If True, change the card's border to red (#EF4444) and subtitle to red."""
        self.setProperty("alert", bool(alert))
        _repolish(self)

    def title(self) -> str:
        return self.title_label.text()

    def value(self) -> str:
        return self.value_label.text()

    def subtitle(self) -> str:
        return self.subtitle_label.text()

    def is_alert(self) -> bool:
        return bool(self.property("alert"))


class StatusKpiCard(QFrame):
    """Custom Status KPI Summary Card for Sales and Order Management.

    Features:
      - Default state: #FFFFFF background, 1px solid #E0E0E0 border, 8px radius,
        12px #64748B title, 24px bold #1A1A1A value, grey icon, 15px padding.
      - Pressed/Active state: Solid status color background and border (2px),
        white title text, white value text, white icon.
      - Cursor: Qt.PointingHandCursor.
      - Layout: [Icon] Title on top row, Value on bottom row.
    """

    clicked = pyqtSignal(str)

    STATUS_CONFIG: dict[str, dict[str, str]] = {
        "Pending": {"color": "#F57C00", "icon": "clock"},
        "Processing": {"color": "#3B82F6", "icon": "refresh"},
        "Paid": {"color": "#2E7D32", "icon": "check-circle"},
        "In Progress": {"color": "#8B5CF6", "icon": "trending-up"},
        "Ready": {"color": "#D4AF37", "icon": "package-check"},
        "Delivered": {"color": "#1A1A1A", "icon": "truck"},
        "Cancelled": {"color": "#C62828", "icon": "x-circle"},
        # Payments Statuses
        "Completed": {"color": "#2E7D32", "icon": "check-circle"},
        "Verified": {"color": "#3B82F6", "icon": "shield-check"},
        "Failed": {"color": "#C62828", "icon": "alert-circle"},
        "Refunded": {"color": "#8B5CF6", "icon": "adjust"},
        # Expense Categories
        "Labor": {"color": "#3B82F6", "icon": "users"},
        "Materials": {"color": "#2E7D32", "icon": "inventory"},
        "Miscellaneous": {"color": "#8B5CF6", "icon": "adjust"},
        "Utility": {"color": "#F57C00", "icon": "zap"},
        "Other": {"color": "#64748B", "icon": "info"},
    }

    def __init__(self, status: str, value: int | str = 0,
                 color: str | None = None, icon: str | None = None,
                 parent=None) -> None:
        super().__init__(parent)
        self.status = status
        self._value = value
        self._is_active = False

        cfg = self.STATUS_CONFIG.get(status, {"color": "#475569", "icon": "info"})
        self.color = color or cfg["color"]
        self.icon_name = icon or cfg["icon"]

        self.setObjectName("StatusKpiCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(76)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(6)

        # Top row: [Icon] Title
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)
        top_row.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        self.icon_label = QLabel()
        self.icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.icon_label.setFixedSize(16, 16)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(self.icon_label)

        self.title_label = QLabel(self.status)
        self.title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        top_row.addWidget(self.title_label)
        top_row.addStretch(1)

        layout.addLayout(top_row)

        # Bottom row: Value
        self.value_label = QLabel(str(self._value))
        self.value_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.value_label)

        self._update_appearance()

    def _update_appearance(self) -> None:
        from ui.icons import get_pixmap
        if self._is_active:
            self.setStyleSheet(f"""
                QFrame#StatusKpiCard {{
                    background-color: {self.color};
                    border: 2px solid {self.color};
                    border-radius: 8px;
                }}
            """)
            self.title_label.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 600; background: transparent; border: none;")
            self.value_label.setStyleSheet("color: #FFFFFF; font-size: 24px; font-weight: bold; background: transparent; border: none;")
            self.icon_label.setStyleSheet("background: transparent; border: none;")
            self.icon_label.setPixmap(get_pixmap(self.icon_name, color="#FFFFFF", size=16))
        else:
            self.setStyleSheet("""
                QFrame#StatusKpiCard {
                    background-color: #FFFFFF;
                    border: 1px solid #E0E0E0;
                    border-radius: 8px;
                }
                QFrame#StatusKpiCard:hover {
                    border: 1px solid #CBD5E1;
                    background-color: #F8FAFC;
                }
            """)
            self.title_label.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 500; background: transparent; border: none;")
            self.value_label.setStyleSheet("color: #1A1A1A; font-size: 24px; font-weight: bold; background: transparent; border: none;")
            self.icon_label.setStyleSheet("background: transparent; border: none;")
            self.icon_label.setPixmap(get_pixmap(self.icon_name, color="#64748B", size=16))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.status)
        super().mousePressEvent(event)

    def set_value(self, value: int | str) -> None:
        self._value = value
        self.value_label.setText(str(value))

    def value(self) -> int | str:
        return self._value

    def set_active(self, active: bool) -> None:
        if self._is_active != active:
            self._is_active = bool(active)
            self._update_appearance()

    def is_active(self) -> bool:
        return self._is_active


# -- Standalone Preview / Demo -----------------------------------------
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QMainWindow, QWidget, QPushButton

    app = QApplication(sys.argv)
    qss_file = Path(__file__).resolve().parent / "styles.qss"
    if qss_file.exists():
        app.setStyleSheet(qss_file.read_text(encoding="utf-8"))

    demo_win = QMainWindow()
    demo_win.setWindowTitle("AkoNi Printing — KPI Cards Preview")
    demo_win.resize(1000, 240)

    central = QWidget()
    main_layout = QVBoxLayout(central)
    cards_layout = QHBoxLayout()
    cards_layout.setSpacing(14)

    card1 = KpiCard("Total Sales", icon="trending-up", value="P1,100.00",
                    subtitle="+5% vs last month", subtitle_tone=TONE_POSITIVE, icon_theme="gold")
    card2 = KpiCard("Total Expenses", icon="expenses", value="P2,550.00",
                    subtitle="+15% vs last month", subtitle_tone=TONE_POSITIVE, icon_theme="coral")
    card3 = KpiCard("Pending Orders", icon="clock", value="0",
                    subtitle="All caught up!", subtitle_tone=TONE_NEUTRAL, icon_theme="blue")
    card4 = KpiCard("Low Stock Items", icon="inventory", value="0",
                    subtitle="Inventory healthy", subtitle_tone=TONE_NEUTRAL, icon_theme="amber")

    cards_layout.addWidget(card1)
    cards_layout.addWidget(card2)
    cards_layout.addWidget(card3)
    cards_layout.addWidget(card4)
    main_layout.addLayout(cards_layout)

    # Dynamic Alert Toggle Demonstration
    toggle_btn = QPushButton("Toggle 'Low Stock Items' Alert (Value > 0)")
    toggle_btn.setFixedWidth(320)

    def _toggle_alert():
        if not card4.is_alert():
            card4.set_value("3")
            card4.set_subtitle("3 items need restock", TONE_NEGATIVE)
            card4.set_alert(True)
        else:
            card4.set_value("0")
            card4.set_subtitle("Inventory healthy", TONE_NEUTRAL)
            card4.set_alert(False)

    toggle_btn.clicked.connect(_toggle_alert)
    main_layout.addWidget(toggle_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    demo_win.setCentralWidget(central)
    demo_win.show()
    sys.exit(app.exec())
