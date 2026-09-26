"""KpiCard — gold-theme KPI metric card (Phase 2).

A reusable QFrame showing, top to bottom:
  top row    : small gold icon + small grey title (#64748B)
  middle row : large bold value (#1A1A1A)
  bottom row : comparison subtitle — green (#2E7D32) when positive,
               red (#C62828) when negative, grey when neutral.

Chrome (white background, 8px radius, 1px #E0E0E0 border, red alert
border) comes from the global ui/styles.qss via objectName / dynamic
property selectors; the subtle drop shadow is applied in code because
QSS has no box-shadow support.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QVBoxLayout, QGraphicsDropShadowEffect,
    QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

TONE_POSITIVE = "positive"
TONE_NEGATIVE = "negative"
TONE_NEUTRAL = "neutral"


def _apply_card_shadow(widget) -> None:
    """Subtle drop shadow — QSS has no box-shadow, so this lives in code."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(18)
    effect.setXOffset(0)
    effect.setYOffset(2)
    effect.setColor(QColor(26, 26, 26, 35))
    widget.setGraphicsEffect(effect)


def _repolish(widget) -> None:
    """Re-evaluate QSS property selectors after a property change."""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)


class KpiCard(QFrame):
    """Top-level dashboard metric card (icon / title / value / subtitle)."""

    def __init__(self, title: str, icon: str = "●", value: str = "—",
                 subtitle: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("KpiCard")
        self.setMinimumHeight(120)
        self.setMinimumWidth(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Fixed)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(4)

        # Top row: gold icon chip + small grey title.
        top = QHBoxLayout()
        top.setSpacing(8)
        self.icon_label = QLabel(icon)
        self.icon_label.setObjectName("KpiIcon")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setFixedSize(24, 24)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("KpiTitle")
        top.addWidget(self.icon_label)
        top.addWidget(self.title_label, 1)
        lay.addLayout(top)

        # Middle row: the big number.
        self.value_label = QLabel(value)
        self.value_label.setObjectName("KpiValue")
        lay.addWidget(self.value_label)

        # Bottom row: comparison line (tone decides its color).
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("KpiSubtitle")
        lay.addWidget(self.subtitle_label)
        lay.addStretch(1)

        self.set_subtitle(subtitle)
        _apply_card_shadow(self)

    # -- updates -------------------------------------------------------
    def set_value(self, text: str) -> None:
        self.value_label.setText(text)

    def set_subtitle(self, text: str, tone: str = TONE_NEUTRAL) -> None:
        self.subtitle_label.setText(text)
        self.subtitle_label.setProperty("tone", tone)
        _repolish(self.subtitle_label)

    def set_alert(self, alert: bool) -> None:
        """Dynamic alert: red border (e.g. low-stock warning).

        Pair with set_subtitle(..., TONE_NEGATIVE) for red subtitle text.
        """
        self.setProperty("alert", bool(alert))
        _repolish(self)
