"""User management (Admin use case)."""
from __future__ import annotations

from auth.login import hash_password

ALLOWED_ROLES = ("Admin", "Staff")


class UserManager:
    def __init__(self, conn):
        self.conn = conn

    # -- create --
    def create_user(self, username, password, first_name, last_name, role="Staff") -> int:
        if role not in ALLOWED_ROLES:
            raise ValueError(f"role must be one of {ALLOWED_ROLES}")
        if not username or not password:
            raise ValueError("username and password are required")
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password_hash, first_name, last_name, role, is_active)"
                " VALUES (%s, %s, %s, %s, %s, TRUE)",
                (username.strip(), hash_password(password), first_name.strip(),
                 last_name.strip(), role),
            )
            self.conn.commit()
            return cursor.lastrowid
        finally:
            cursor.close()

    # -- read --
    def list_users(self, include_inactive: bool = True) -> list[dict]:
        cursor = self.conn.cursor(dictionary=True)
        try:
            sql = ("SELECT user_id, username, first_name, last_name, role, is_active, created_at"
                   " FROM users")
            if not include_inactive:
                sql += " WHERE is_active = TRUE"
            sql += " ORDER BY username"
            cursor.execute(sql)
            return list(cursor.fetchall())
        finally:
            cursor.close()

    def get_user(self, user_id: int) -> dict | None:
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            return cursor.fetchone()
        finally:
            cursor.close()

    # -- update --
    def update_user(self, user_id, first_name=None, last_name=None, role=None) -> None:
        fields, params = [], []
        if first_name is not None:
            fields.append("first_name = %s")
            params.append(first_name.strip())
        if last_name is not None:
            fields.append("last_name = %s")
            params.append(last_name.strip())
        if role is not None:
            if role not in ALLOWED_ROLES:
                raise ValueError(f"role must be one of {ALLOWED_ROLES}")
            fields.append("role = %s")
            params.append(role)
        if not fields:
            return
        params.append(user_id)
        cursor = self.conn.cursor()
        try:
            cursor.execute(f"UPDATE users SET {', '.join(fields)} WHERE user_id = %s", params)
            self.conn.commit()
        finally:
            cursor.close()

    def set_active(self, user_id: int, active: bool) -> None:
        cursor = self.conn.cursor()
        try:
            cursor.execute("UPDATE users SET is_active = %s WHERE user_id = %s",
                           (bool(active), user_id))
            self.conn.commit()
        finally:
            cursor.close()

    def change_password(self, user_id: int, new_password: str) -> None:
        if not new_password:
            raise ValueError("new password required")
        cursor = self.conn.cursor()
        try:
            cursor.execute("UPDATE users SET password_hash = %s WHERE user_id = %s",
                           (hash_password(new_password), user_id))
            self.conn.commit()
        finally:
            cursor.close()
