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
from PyQt6.QtCore import Qt
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
        top.addWidget(self.title_label, 1)

        self.icon_label = QLabel()
        self.icon_label.setObjectName("KpiIconBadge")
        self.icon_label.setProperty("theme", icon_theme)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setFixedSize(34, 34)
        top.addWidget(self.icon_label)
        layout.addLayout(top)

        # Middle row: The Value (large, bold text)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("KpiValue")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.value_label)

        # Bottom row: Subtitle showing a comparison (green / red / grey text)
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("KpiSubtitle")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.subtitle_label)
        layout.addStretch(1)

        # Initialize content & styling
        self.set_icon(icon)
        self.set_subtitle(subtitle, subtitle_tone)
        _apply_card_shadow(self)

    # -- Content setters & getters -------------------------------------
    def set_icon(self, icon: str | QIcon | QPixmap | QStyle.StandardPixmap | None) -> None:
        """Set the top-row icon from a standard Qt icon, QPixmap, file path, or text/emoji."""
        if icon is None:
            self.icon_label.setText("●")
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

    card1 = KpiCard("Total Sales", icon="💰", value="P1,100.00",
                    subtitle="+5% vs last month", subtitle_tone=TONE_POSITIVE, icon_theme="gold")
    card2 = KpiCard("Total Expenses", icon="💸", value="P2,550.00",
                    subtitle="+15% vs last month", subtitle_tone=TONE_POSITIVE, icon_theme="coral")
    card3 = KpiCard("Pending Orders", icon="📋", value="0",
                    subtitle="All caught up!", subtitle_tone=TONE_NEUTRAL, icon_theme="blue")
    card4 = KpiCard("Low Stock Items", icon="📦", value="0",
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
