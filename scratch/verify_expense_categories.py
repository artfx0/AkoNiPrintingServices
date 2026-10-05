import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from expenses.expense_management import EXPENSE_CATEGORIES, ExpenseManager
from expenses.expense_widget import ExpenseWidget, ExpenseDialog
from database.database import get_connection

def test_expenses_categories():
    print("--- 1. Testing EXPENSE_CATEGORIES ---")
    assert "Other" not in EXPENSE_CATEGORIES, "'Other' must NOT be in EXPENSE_CATEGORIES"
    assert EXPENSE_CATEGORIES == ("Labor", "Materials", "Miscellaneous", "Utility")
    print("EXPENSE_CATEGORIES:", EXPENSE_CATEGORIES)

    os.environ["QT_QPA_PLATFORM"] = "windows"
    app = QApplication.instance() or QApplication(sys.argv)

    if os.path.exists("ui/styles.qss"):
        with open("ui/styles.qss", "r") as f:
            app.setStyleSheet(f.read())

    print("\n--- 2. Testing ExpenseDialog Category Dropdown ---")
    dlg = ExpenseDialog()
    dlg.resize(480, 420)
    dlg.show()
    app.processEvents()

    items = [dlg.category_box.itemText(i) for i in range(dlg.category_box.count())]
    print("Category dropdown items in ExpenseDialog:", items)
    assert "Other" not in items, "'Other' must NOT be in the category dropdown!"
    assert items == ["Labor", "Materials", "Miscellaneous", "Utility"], f"Unexpected items: {items}"

    out_dir = r"C:\Users\JohnPaul\.gemini\antigravity\brain\48e2fdad-38c3-4bae-92fc-f8ba6b8ded82"
    pix_dlg = dlg.grab()
    dlg_img_path = os.path.join(out_dir, "updated_expenses_record_dialog_preview.png")
    pix_dlg.save(dlg_img_path)
    print("Saved dialog screenshot to:", dlg_img_path)
    dlg.close()

    print("\n--- 3. Testing ExpenseWidget Module UI & KPI Cards ---")
    widget = ExpenseWidget()
    widget.resize(1200, 780)
    widget.show()
    app.processEvents()

    card_keys = list(widget.category_cards.keys())
    print("Category KPI card keys:", card_keys)
    assert "Other" not in card_keys, "'Other' KPI card must NOT exist!"
    assert card_keys == ["Labor", "Materials", "Miscellaneous", "Utility"]

    pix_widget = widget.grab()
    widget_img_path = os.path.join(out_dir, "updated_expenses_module_preview.png")
    pix_widget.save(widget_img_path)
    print("Saved module screenshot to:", widget_img_path)

    widget.close()
    print("\nALL EXPENSE VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_expenses_categories()
