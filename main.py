"""AkoNi Printing Services — entry point (MySQL + PyQt6)."""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PyQt6.QtWidgets import QApplication, QMessageBox

_QSS_CACHE: str | None = None


def load_app_stylesheet() -> str:
    """Load the global Rich Gold QSS (ui/styles.qss), cached."""
    global _QSS_CACHE
    if _QSS_CACHE is None:
        qss_path = Path(__file__).resolve().parent / "ui" / "styles.qss"
        try:
            _QSS_CACHE = qss_path.read_text(encoding="utf-8")
        except OSError:
            _QSS_CACHE = ""
    return _QSS_CACHE


def main() -> int:
    from auth.session import Session
    from database.database import init_database, test_connection
    from ui.login_window import LoginWindow
    from ui.main_window import MainWindow

    app = QApplication(sys.argv)
    # Keep the app alive when a dashboard closes on logout so we can
    # show the login dialog again.
    app.setQuitOnLastWindowClosed(False)

    # Phase 1: Rich Gold theme — one global stylesheet for every window.
    qss = load_app_stylesheet()
    if qss:
        app.setStyleSheet(qss)

    try:
        init_database()
    except Exception as exc:  # noqa: BLE001
        QMessageBox.critical(
            None, "Database init failed",
            f"Could not initialise MySQL.\nCheck db_config.ini / env vars and that"
            f" MySQL server is running.\n\n{exc}\n\n{traceback.format_exc(limit=3)}")
        return 1

    ok, msg = test_connection()
    if not ok:
        QMessageBox.critical(None, "Database error", msg)
        return 1

    # Login -> dashboard -> logout loop (RBAC enforced here).
    while True:
        Session.clear()
        login = LoginWindow()
        if login.exec() != LoginWindow.DialogCode.Accepted or not login.user:
            return 0

        # Prefer the session copy; fall back to the dialog result.
        user = Session.current_user() or login.user
        Session.set_user(user)

        # Role-Based UI handled inside MainWindow (nav filtering).
        window = MainWindow(user)
        window.show()
        app.exec()

        # X-close exits; Logout returns to the login prompt.
        if not getattr(window, "logout_requested", False):
            Session.clear()
            return 0
        # else: loop back to LoginWindow

    # unreachable


if __name__ == "__main__":
    raise SystemExit(main())
