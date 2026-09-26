"""Authentication: password hashing + credential verification."""
from __future__ import annotations

import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def authenticate(conn, username: str, password: str) -> dict | None:
    """Return active user row (dict) if credentials valid, else None."""
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username.strip(),))
        user = cursor.fetchone()
    finally:
        cursor.close()
    if not user:
        return None
    if not user.get("is_active"):
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def is_admin(user: dict | None) -> bool:
    return bool(user) and user.get("role") == "Admin"


def is_staff(user: dict | None) -> bool:
    return bool(user) and user.get("role") == "Staff"
