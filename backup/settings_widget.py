"""Settings / Backup & Restore widget (Admin access only — Phase 10).

Backup Database button -> QFileDialog save location -> mysqldump
(via BackupManager: native mysqldump when on PATH, else pure-Python
dump through mysql.connector) -> SystemLog BACKUP row.
Restore Database button -> QFileDialog pick .sql -> mysql client
(or pure-Python replay) -> SystemLog RESTORE row.
Security: constructor refuses non-Admin users; MainWindow only
exposes this page on the Admin nav.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QMessageBox, QFileDialog, QHeaderView,
    QAbstractItemView,
)

from backup.backup_restore import BackupManager
from backup.system_log import SystemLogManager
from database.database import get_connection

_LOG_HEADERS = ["log_id", "username", "action", "details", "created_at"]
_LOG_LABELS = ["ID", "User", "Action", "Details", "Date/Time"]


class SettingsWidget(QWidget):
    """Standalone Admin-only page for QStackedWidget."""

    def __init__(self, user: dict | None = None, parent=None):
        super().__init__(parent)
        self.user = user or {}
        if (self.user.get("role") or "") != "Admin":
            raise PermissionError("Backup & Restore is Admin-only.")
        layout = QVBoxLayout(self)
        title = QLabel("Settings — Backup & Restore")
        title.setObjectName("DashboardTitle")
        layout.addWidget(title)
        layout.addWidget(QLabel(
            "Backups use mysqldump when available, otherwise an automatic "
            "pure-Python dump. Every action is logged with date and time."))

        row = QHBoxLayout()
        self.backup_btn = QPushButton("Backup Database")
        self.restore_btn = QPushButton("Restore Database")
        self.refresh_btn = QPushButton("Refresh Log")
        self.backup_btn.clicked.connect(self.backup_database)
        self.restore_btn.clicked.connect(self.restore_database)
        self.refresh_btn.clicked.connect(self.refresh_log)
        for b in (self.backup_btn, self.restore_btn, self.refresh_btn):
            row.addWidget(b)
        layout.addLayout(row)

        layout.addWidget(QLabel("System Log (backup / restore history)"))
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        self.refresh_log()

    # -- helpers --
    def _conn(self):
        return get_connection()

    # -- spec logic --
    def backup_database(self) -> None:
        mgr = BackupManager()
        path, _ = QFileDialog.getSaveFileName(
            self, "Save backup", mgr.default_filename(), "SQL (*.sql)")
        if not path:
            return
        try:
            mgr.backup(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Backup", f"Backup failed:\n{exc}")
            return
        conn = self._conn()
        try:
            SystemLogManager(conn).log_action(
                "BACKUP", self.user, f"Backup saved to {path}")
        except Exception:  # noqa: BLE001 — backup stands even if logging fails
            pass
        finally:
            conn.close()
        QMessageBox.information(self, "Backup", f"Backup saved to {path}")
        self.refresh_log()

    def restore_database(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select backup to restore", "", "SQL (*.sql)")
        if not path:
            return
        if QMessageBox.question(
                self, "Restore",
                "Restore will overwrite current data. Continue?"
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            BackupManager().restore(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Restore", f"Restore failed:\n{exc}")
            return
        conn = self._conn()
        try:
            SystemLogManager(conn).log_action(
                "RESTORE", self.user, f"Restored from {path}")
        except Exception:  # noqa: BLE001
            pass
        finally:
            conn.close()
        QMessageBox.information(self, "Restore", "Restore completed.")
        self.refresh_log()

    def refresh_log(self) -> None:
        conn = self._conn()
        try:
            try:
                rows = SystemLogManager(conn).list_logs()
            except Exception:
                rows = []  # table created on next init_database
            self.table.setRowCount(len(rows))
            self.table.setColumnCount(len(_LOG_HEADERS))
            self.table.setHorizontalHeaderLabels(_LOG_LABELS)
            for r, row in enumerate(rows):
                for c, h in enumerate(_LOG_HEADERS):
                    val = row.get(h, "")
                    self.table.setItem(r, c, QTableWidgetItem(
                        "" if val is None else str(val)))
            self.table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            conn.close()
