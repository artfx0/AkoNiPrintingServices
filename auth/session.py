"""Global session singleton storing the logged-in user.

Usage:
    from auth.session import Session
    Session.set_user(user_dict)
    Session.current_user() -> dict | None
    Session.clear()
"""
from __future__ import annotations


class Session:
    _user: dict | None = None

    @classmethod
    def set_user(cls, user: dict | None) -> None:
        cls._user = dict(user) if user else None

    @classmethod
    def clear(cls) -> None:
        cls._user = None

    @classmethod
    def current_user(cls) -> dict | None:
        return dict(cls._user) if cls._user else None

    @classmethod
    def user_id(cls) -> int | None:
        return cls._user.get("user_id") if cls._user else None

    @classmethod
    def username(cls) -> str:
        return cls._user.get("username", "") if cls._user else ""

    @classmethod
    def role(cls) -> str:
        return cls._user.get("role", "") if cls._user else ""

    @classmethod
    def is_admin(cls) -> bool:
        return cls.role() == "Admin"

    @classmethod
    def is_staff(cls) -> bool:
        return cls.role() == "Staff"

    @classmethod
    def is_authenticated(cls) -> bool:
        return cls._user is not None


# Backwards-compatible module-level alias
current_user: dict | None = None


def get_current_user() -> dict | None:
    return Session.current_user()
