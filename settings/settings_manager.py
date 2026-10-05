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
