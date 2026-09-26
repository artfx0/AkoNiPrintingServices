"""Settings / Backup & Restore widget (Admin access only — Professional SaaS / HCI format).

Features:
  - Visual hierarchy: Section title + descriptive subtitle.
  - Interactive Action Cards for 'Create Full Database Backup' and 'Restore Database Snapshot'.
  - Elevated card container wrapping the System Audit Log.
  - Live log search and action pill indicators.
  - Safe error handling and confirmation prompts before restore.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QMessageBox, QFileDialog,
    QHeaderView, QAbstractItemView, QFrame, QLineEdit,
)
from PyQt6.QtCore import Qt

from backup.backup_restore import BackupManager
from backup.system_log import SystemLogManager
from database.database import get_connection
from ui.icons import get_icon, get_action_icon, get_pixmap

_LOG_HEADERS = ["Log #", "Action", "User", "Details / File Path", "Timestamp"]


class SettingsWidget(QWidget):
    """Admin-only Database Settings, Backup & Restore, and Audit Log."""

    def __init__(self, user: dict | None = None, parent=None):
        super().__init__(parent)
        self.user = user or {}
        if (self.user.get("role") or "") != "Admin":
            raise PermissionError("Backup & Restore is Admin-only.")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(20)

        # 1. Page Header (Title + Subtitle)
        header_lay = QVBoxLayout()
        header_lay.setSpacing(4)
        title = QLabel("Database Backup & System Logs")
        title.setObjectName("ModuleHeaderTitle")
        sub = QLabel("Safeguard business records with full SQL backups, restore historical snapshots, and monitor the audit log.")
        sub.setObjectName("ModuleHeaderSub")
        header_lay.addWidget(title)
        header_lay.addWidget(sub)
        layout.addLayout(header_lay)

        # 2. Backup & Restore Action Cards (2 Columns)
        cards_grid = QGridLayout()
        cards_grid.setSpacing(16)

        # Backup Card
        backup_card = QFrame()
        backup_card.setObjectName("ModuleCardContainer")
        backup_card.setStyleSheet(
            "QFrame#ModuleCardContainer { background: #FFFFFF; border: 1px solid #E2E8F0; "
            "border-radius: 12px; padding: 18px; }"
        )
        b_lay = QVBoxLayout(backup_card)
        b_lay.setSpacing(10)

        b_top = QHBoxLayout()
        b_icon = QLabel()
        b_icon.setFixedSize(36, 36)
        b_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        b_icon.setStyleSheet("background: #FEF3C7; border-radius: 8px;")
        b_icon.setPixmap(get_pixmap("backup", color="#B45309", size=18))
        b_top.addWidget(b_icon)
        b_title = QLabel("Create Database Backup")
        b_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0F172A;")
        b_top.addWidget(b_title)
        b_top.addStretch(1)
        b_lay.addLayout(b_top)

        b_desc = QLabel(
            "Generates an immediate SQL dump of all orders, payments, customers, inventory, and expense tables. "
            "Automated fallback ensures backups complete even without native mysqldump."
        )
        b_desc.setWordWrap(True)
        b_desc.setStyleSheet("font-size: 12px; color: #64748B; line-height: 16px;")
        b_lay.addWidget(b_desc)

        b_btn_box = QHBoxLayout()
        b_btn_box.addStretch(1)
        self.backup_btn = QPushButton("Backup Database Now")
        self.backup_btn.setIcon(get_action_icon("download", "primary", 15))
        self.backup_btn.clicked.connect(self.backup_database)
        b_btn_box.addWidget(self.backup_btn)
        b_lay.addLayout(b_btn_box)

        cards_grid.addWidget(backup_card, 0, 0)

        # Restore Card
        restore_card = QFrame()
        restore_card.setObjectName("ModuleCardContainer")
        restore_card.setStyleSheet(
            "QFrame#ModuleCardContainer { background: #FFFFFF; border: 1px solid #E2E8F0; "
            "border-radius: 12px; padding: 18px; }"
        )
        r_lay = QVBoxLayout(restore_card)
        r_lay.setSpacing(10)

        r_top = QHBoxLayout()
        r_icon = QLabel()
        r_icon.setFixedSize(36, 36)
        r_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        r_icon.setStyleSheet("background: #FEE2E2; border-radius: 8px;")
        r_icon.setPixmap(get_pixmap("upload-cloud", color="#DC2626", size=18))
        r_top.addWidget(r_icon)
        r_title = QLabel("Restore from Backup")
        r_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0F172A;")
        r_top.addWidget(r_title)
        r_top.addStretch(1)
        r_lay.addLayout(r_top)

        r_desc = QLabel(
            "Select an existing SQL dump file to restore database tables. "
            "<b>Warning:</b> Restoring will overwrite existing operational data with the state in the backup file."
        )
        r_desc.setWordWrap(True)
        r_desc.setStyleSheet("font-size: 12px; color: #64748B; line-height: 16px;")
        r_lay.addWidget(r_desc)

        r_btn_box = QHBoxLayout()
        r_btn_box.addStretch(1)
        self.restore_btn = QPushButton("Select Backup File to Restore")
        self.restore_btn.setObjectName("SecondaryBtn")
        self.restore_btn.setStyleSheet("border-color: #FCA5A5; color: #DC2626;")
        self.restore_btn.setIcon(get_action_icon("upload-cloud", "danger", 15))
        self.restore_btn.clicked.connect(self.restore_database)
        r_btn_box.addWidget(self.restore_btn)
        r_lay.addLayout(r_btn_box)

        cards_grid.addWidget(restore_card, 0, 1)

        layout.addLayout(cards_grid)

        # 3. System Log Section (Toolbar + Table inside Card)
        log_header = QVBoxLayout()
        log_header.setSpacing(2)
        log_title = QLabel("System Audit Trail")
        log_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        log_sub = QLabel("Timestamped log entries for administrative maintenance and security operations.")
        log_sub.setStyleSheet("font-size: 12px; color: #64748B;")
        log_header.addWidget(log_title)
        log_header.addWidget(log_sub)
        layout.addLayout(log_header)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.search = QLineEdit()
        self.search.setObjectName("TableSearchInput")
        self.search.addAction(get_icon("search", color="#94A3B8", size=16), QLineEdit.ActionPosition.LeadingPosition)
        self.search.setPlaceholderText("Search audit log by action, user, or details...")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(240)
        self.search.textChanged.connect(self.refresh_log)
        toolbar.addWidget(self.search, 1)

        self.refresh_btn = QPushButton("Refresh Log")
        self.refresh_btn.setObjectName("SecondaryBtn")
        self.refresh_btn.setIcon(get_action_icon("refresh", "secondary", 15))
        self.refresh_btn.clicked.connect(self.refresh_log)
        toolbar.addWidget(self.refresh_btn)

        layout.addLayout(toolbar)

        # Card container wrapping log table
        card = QFrame()
        card.setObjectName("ModuleCardContainer")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        self.table = QTableWidget()
        self.table.setColumnCount(len(_LOG_HEADERS))
        self.table.setHorizontalHeaderLabels(_LOG_HEADERS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 110)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)

        card_lay.addWidget(self.table)
        layout.addWidget(card, 1)

        self.refresh_log()

    # -- helpers --
    def _conn(self):
        return get_connection()

    def _create_action_pill(self, action: str) -> QWidget:
        container = QWidget()
        lay = QHBoxLayout(container)
        lay.setContentsMargins(6, 4, 6, 4)
        pill = QLabel(action)
        pill.setObjectName("StatusPill")

        if action.upper() == "BACKUP":
            pill.setProperty("status", "paid")       # Green
        elif action.upper() == "RESTORE":
            pill.setProperty("status", "pending")    # Amber
        else:
            pill.setProperty("status", "processing") # Blue

        pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pill.style().unpolish(pill)
        pill.style().polish(pill)
        lay.addWidget(pill)
        return container

    # -- Backup & Restore logic --
    def backup_database(self) -> None:
        mgr = BackupManager()
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Database Backup", mgr.default_filename(), "SQL (*.sql)"
        )
        if not path:
            return

        try:
            mgr.backup(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Backup Error", f"Backup failed:\n{exc}")
            return

        conn = self._conn()
        try:
            SystemLogManager(conn).log_action(
                "BACKUP", self.user, f"Database backup saved to: {path}"
            )
        except Exception:  # noqa: BLE001
            pass
        finally:
            conn.close()

        QMessageBox.information(self, "Backup Successful", f"Full database backup successfully created:\n{path}")
        self.refresh_log()

    def restore_database(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select SQL Backup to Restore", "", "SQL (*.sql)"
        )
        if not path:
            return

        if QMessageBox.question(
            self, "Confirm Database Restore",
            f"Are you sure you want to restore from:\n{path}\n\n"
            "Warning: This action will overwrite existing operational records with data from the backup file!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return

        try:
            BackupManager().restore(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Restore Error", f"Database restore failed:\n{exc}")
            return

        conn = self._conn()
        try:
            SystemLogManager(conn).log_action(
                "RESTORE", self.user, f"Restored snapshot from: {path}"
            )
        except Exception:  # noqa: BLE001
            pass
        finally:
            conn.close()

        QMessageBox.information(
            self, "Restore Completed",
            "Database restore completed successfully. All tables have been refreshed."
        )
        self.refresh_log()

    def refresh_log(self) -> None:
        conn = self._conn()
        try:
            try:
                rows = SystemLogManager(conn).list_logs()
            except Exception:
                rows = []

            needle = self.search.text().strip().lower()
            if needle:
                rows = [
                    r for r in rows
                    if needle in str(r.get("action") or "").lower()
                    or needle in str(r.get("username") or "").lower()
                    or needle in str(r.get("details") or "").lower()
                ]

            self.table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                lid = row.get("log_id")
                action = str(row.get("action") or "LOG")
                user = str(row.get("username") or "system")
                details = str(row.get("details") or "—")
                created = str(row.get("created_at") or "")

                self.table.setItem(r, 0, QTableWidgetItem(f"#{lid}"))
                self.table.setCellWidget(r, 1, self._create_action_pill(action))
                self.table.setItem(r, 2, QTableWidgetItem(user))
                self.table.setItem(r, 3, QTableWidgetItem(details))
                self.table.setItem(r, 4, QTableWidgetItem(created))

        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to load system log:\n{exc}")
        finally:
            conn.close()
