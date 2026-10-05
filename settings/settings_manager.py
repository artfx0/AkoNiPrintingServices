"""Settings persistence manager for AkoNi Printing Services."""
from __future__ import annotations

import json
from pathlib import Path

_SETTINGS_FILE = Path(__file__).resolve().parent / "business_info.json"

_DEFAULT_BUSINESS_INFO = {
    "business_name": "AkoNi Printing Services",
    "business_address": "124 Rizal St., Brgy. Poblacion, Makati City, Metro Manila",
    "contact_number": "0917-123-4567",
    "email_address": "info@akoniprinting.com",
    "social_contact": "facebook.com/AkoNiPrintingServices",
    "payment_instructions": (
        "GCash: 0917-123-4567 (Juan D.)\n"
        "BDO Unibank Account: 0012-3456-7890 (AkoNi Printing Services)\n"
        "Please send your screenshot proof of payment along with your Order #."
    ),
    "invoice_reminder": (
        "Production commences upon settlement of the 50% assurance deposit.\n"
        "Standard order lead time is 3 to 5 business days following final layout approval."
    ),
}


_DEFAULT_PRODUCTS = [
    {"name": "Chocolate Box", "status": "Active"},
]

_DEFAULT_PAYMENT_METHODS = [
    {"name": "GCash", "status": "Active"},
    {"name": "Bank Transfer", "status": "Active"},
]

_DEFAULT_PAYMENT_ACCOUNTS: list[dict[str, str]] = []

_DEFAULT_EXPENSE_ACCOUNTS = [
    {"code": "401", "name": "Labor Expense", "status": "Active"},
    {"code": "", "name": "Materials Expense", "status": "Active"},
    {"code": "", "name": "Transportation Expense", "status": "Active"},
    {"code": "", "name": "Utilities Expense", "status": "Active"},
]

_DEFAULT_COURIERS = [
    {"name": "Grab", "status": "Active"},
    {"name": "J&T", "status": "Active"},
    {"name": "LBC", "status": "Active"},
]

_DEFAULT_ADMIN_ACCOUNT = {
    "name": "Earth Justin Anne Lim",
    "username": "earth",
    "status": "Active",
}

_DEFAULT_STAFF_ACCOUNTS = [
    {
        "name": "Carlo Reyes",
        "username": "dev_staff",
        "status": "Active",
    }
]


class SettingsManager:
    """Handles reading and writing business configuration."""

    @classmethod
    def load_business_info(cls) -> dict[str, str]:
        if _SETTINGS_FILE.exists():
            try:
                with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Merge with defaults in case of missing keys
                    merged = dict(_DEFAULT_BUSINESS_INFO)
                    merged.update(data)
                    return merged
            except Exception:
                pass
        return dict(_DEFAULT_BUSINESS_INFO)

    @classmethod
    def save_business_info(cls, info: dict[str, str]) -> None:
        merged = cls.load_business_info()
        merged.update(info)
        with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=4)

    @classmethod
    def load_product_references(cls) -> list[dict[str, str]]:
        if _SETTINGS_FILE.exists():
            try:
                with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "product_references" in data and isinstance(data["product_references"], list):
                        return list(data["product_references"])
            except Exception:
                pass
        return list(_DEFAULT_PRODUCTS)

    @classmethod
    def save_product_references(cls, products: list[dict[str, str]]) -> None:
        if _SETTINGS_FILE.exists():
            try:
                with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = dict(_DEFAULT_BUSINESS_INFO)
        else:
            data = dict(_DEFAULT_BUSINESS_INFO)

        data["product_references"] = products
        with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @classmethod
    def load_payment_methods(cls) -> list[dict[str, str]]:
        if _SETTINGS_FILE.exists():
            try:
                with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "payment_methods" in data and isinstance(data["payment_methods"], list):
                        return list(data["payment_methods"])
            except Exception:
                pass
        return list(_DEFAULT_PAYMENT_METHODS)

    @classmethod
    def save_payment_methods(cls, methods: list[dict[str, str]]) -> None:
        if _SETTINGS_FILE.exists():
            try:
                with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = dict(_DEFAULT_BUSINESS_INFO)
        else:
            data = dict(_DEFAULT_BUSINESS_INFO)

        data["payment_methods"] = methods
        with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @classmethod
    def load_payment_accounts(cls) -> list[dict[str, str]]:
        if _SETTINGS_FILE.exists():
            try:
                with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "payment_accounts" in data and isinstance(data["payment_accounts"], list):
                        return list(data["payment_accounts"])
            except Exception:
                pass
        return list(_DEFAULT_PAYMENT_ACCOUNTS)

    @classmethod
    def save_payment_accounts(cls, accounts: list[dict[str, str]]) -> None:
        if _SETTINGS_FILE.exists():
            try:
                with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = dict(_DEFAULT_BUSINESS_INFO)
        else:
            data = dict(_DEFAULT_BUSINESS_INFO)

        data["payment_accounts"] = accounts
        with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @classmethod
    def load_expense_accounts(cls) -> list[dict[str, str]]:
        if _SETTINGS_FILE.exists():
            try:
                with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "expense_accounts" in data and isinstance(data["expense_accounts"], list):
                        return list(data["expense_accounts"])
            except Exception:
                pass
        return list(_DEFAULT_EXPENSE_ACCOUNTS)

    @classmethod
    def save_expense_accounts(cls, accounts: list[dict[str, str]]) -> None:
        if _SETTINGS_FILE.exists():
            try:
                with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = dict(_DEFAULT_BUSINESS_INFO)
        else:
            data = dict(_DEFAULT_BUSINESS_INFO)

        data["expense_accounts"] = accounts
        with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @classmethod
    def load_courier_options(cls) -> list[dict[str, str]]:
        if _SETTINGS_FILE.exists():
            try:
                with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "courier_options" in data and isinstance(data["courier_options"], list):
                        return list(data["courier_options"])
            except Exception:
                pass
        return list(_DEFAULT_COURIERS)

    @classmethod
    def save_courier_options(cls, couriers: list[dict[str, str]]) -> None:
        if _SETTINGS_FILE.exists():
            try:
                with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = dict(_DEFAULT_BUSINESS_INFO)
        else:
            data = dict(_DEFAULT_BUSINESS_INFO)

        data["courier_options"] = couriers
        with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @classmethod
    def load_admin_account(cls) -> dict[str, str]:
        if _SETTINGS_FILE.exists():
            try:
                with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "admin_account" in data and isinstance(data["admin_account"], dict):
                        return dict(data["admin_account"])
            except Exception:
                pass
        return dict(_DEFAULT_ADMIN_ACCOUNT)

    @classmethod
    def save_admin_account(cls, admin: dict[str, str]) -> None:
        if _SETTINGS_FILE.exists():
            try:
                with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = dict(_DEFAULT_BUSINESS_INFO)
        else:
            data = dict(_DEFAULT_BUSINESS_INFO)

        data["admin_account"] = admin
        with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @classmethod
    def load_staff_accounts(cls) -> list[dict[str, str]]:
        if _SETTINGS_FILE.exists():
            try:
                with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "staff_accounts" in data and isinstance(data["staff_accounts"], list):
                        return list(data["staff_accounts"])
            except Exception:
                pass
        return [dict(s) for s in _DEFAULT_STAFF_ACCOUNTS]

    @classmethod
    def save_staff_accounts(cls, staff: list[dict[str, str]]) -> None:
        if _SETTINGS_FILE.exists():
            try:
                with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = dict(_DEFAULT_BUSINESS_INFO)
        else:
            data = dict(_DEFAULT_BUSINESS_INFO)

        data["staff_accounts"] = staff
        with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)


