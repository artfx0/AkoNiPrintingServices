"""SystemLog audit trail (Phase 10): date-time of every backup/restore."""
from __future__ import annotations


class SystemLogManager:
    def __init__(self, conn):
        self.conn = conn

    def log_action(self, action: str, user: dict | None = None,
                   details: str = "") -> int:
        if action not in ("BACKUP", "RESTORE"):
            raise ValueError("action must be BACKUP or RESTORE")
        uid = (user or {}).get("user_id")
        username = (user or {}).get("username")
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO system_logs (user_id, username, action, details)"
                " VALUES (%s, %s, %s, %s)",
                (uid, username, action, (details or "")[:500] or None),
            )
            self.conn.commit()
            return cursor.lastrowid
        finally:
            cursor.close()

    def list_logs(self, limit: int = 200) -> list[dict]:
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM system_logs ORDER BY created_at DESC LIMIT %s",
                (int(limit),))
            return list(cursor.fetchall())
        finally:
            cursor.close()
