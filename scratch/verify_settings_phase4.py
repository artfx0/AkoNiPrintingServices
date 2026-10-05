import sys
import os
import json

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication, QLabel, QPushButton
from PyQt6.QtCore import Qt

from main import load_app_stylesheet
from settings.settings_widget import SettingsWidget
from settings.settings_manager import SettingsManager

def test_expenses_tab():
    app = QApplication.instance() or QApplication(sys.argv)
    qss = load_app_stylesheet()
    if qss:
        app.setStyleSheet(qss)

    admin_user = {"username": "admin", "role": "Admin"}
    widget = SettingsWidget(user=admin_user)
    widget.resize(1100, 750)
    widget.show()
    app.processEvents()

    # 1. Select Expenses Tab
    print("Test 1: Selecting Expenses Tab...")
    widget.tabs.setCurrentIndex(3)
    app.processEvents()
    assert widget.tabs.currentIndex() == 3
    assert widget.tabs.tabText(3) == "Expenses"
    print("  -> Passed: Expenses tab selected at index 3.")

    # 2. Verify Section and Top-Right Button
    print("Test 2: Verifying section header and top-right Add button...")
    assert widget.add_expense_btn is not None
    assert widget.add_expense_btn.text() in ["Add Expense Account", "+ Add Expense Account"]
    assert widget.add_expense_btn.objectName() == "SecondaryBtn"
    print("  -> Passed: Top-right secondary outlined '+ Add Expense Account' button verified.")

    # 3. Verify Table Columns and Mock Rows
    print("Test 3: Verifying Expense Accounts table and mock rows...")
    table = widget.expenses_table
    assert table.columnCount() == 3
    headers = [table.horizontalHeaderItem(i).text() for i in range(3)]
    assert headers == ["Account Code", "Account Name", "Status"], f"Unexpected headers: {headers}"
    assert table.rowCount() == 4, f"Expected 4 mock rows, got {table.rowCount()}"

    expected_rows = [
        ("401", "Labor Expense"),
        ("—", "Materials Expense"),
        ("—", "Transportation Expense"),
        ("—", "Utilities Expense"),
    ]

    for r, (exp_code, exp_name) in enumerate(expected_rows):
        code_text = table.item(r, 0).text().strip()
        name_text = table.item(r, 1).text().strip()
        status_widget = table.cellWidget(r, 2)
        status_lbl = status_widget.findChild(QLabel)

        assert exp_code in code_text or (exp_code == "—" and (code_text == "—" or code_text == "")), \
            f"Row {r} code mismatch: expected {exp_code}, got {code_text}"
        assert exp_name == name_text, f"Row {r} name mismatch: expected {exp_name}, got {name_text}"
        assert status_lbl is not None
        assert "Active" in status_lbl.text()
        assert status_lbl.property("status") == "active"
        print(f"  -> Row {r}: {code_text} | {name_text} | Active (green badge verified)")

    # 4. Verify Bottom Buttons
    print("Test 4: Verifying bottom action buttons...")
    assert widget.edit_expense_btn is not None
    assert widget.edit_expense_btn.text() == "Edit Expense Account"
    assert widget.edit_expense_btn.objectName() == "SecondaryBtn"

    assert widget.archive_expense_btn is not None
    assert widget.archive_expense_btn.text() == "Archive Expense Account"
    assert widget.archive_expense_btn.objectName() == "SecondaryBtn"
    print("  -> Passed: Bottom outlined buttons 'Edit Expense Account' and 'Archive Expense Account' verified.")

    # Capture pristine Expenses tab screenshot
    artifact_dir = r"C:\Users\JohnPaul\.gemini\antigravity\brain\48e2fdad-38c3-4bae-92fc-f8ba6b8ded82"
    os.makedirs(artifact_dir, exist_ok=True)
    shot1 = os.path.join(artifact_dir, "settings_phase4_expenses_tab.png")
    widget.grab().save(shot1)
    print(f"  -> Saved initial Expenses Tab screenshot to {shot1}")

    # 5. Test Archive toggle operation
    print("Test 5: Testing archive operation on selected row...")
    table.selectRow(0)
    widget._toggle_archive_selected_expense_account()
    app.processEvents()

    status_lbl_0 = table.cellWidget(0, 2).findChild(QLabel)
    assert "Archived" in status_lbl_0.text()
    assert status_lbl_0.property("status") == "other"
    print("  -> Passed: Row 0 archived successfully.")

    # Revert to clean mock state
    clean_mock_accounts = [
        {"code": "401", "name": "Labor Expense", "status": "Active"},
        {"code": "", "name": "Materials Expense", "status": "Active"},
        {"code": "", "name": "Transportation Expense", "status": "Active"},
        {"code": "", "name": "Utilities Expense", "status": "Active"},
    ]
    SettingsManager.save_expense_accounts(clean_mock_accounts)
    widget._load_expense_accounts()
    app.processEvents()
    widget.close()

    # 6. Capture full MainWindow context
    print("Test 6: Capturing full MainWindow with Expenses Tab...")
    from ui.main_window import MainWindow
    main_win = MainWindow(user=admin_user)
    main_win.resize(1280, 800)
    main_win.show()
    app.processEvents()

    settings_idx = main_win.nav.count() - 1
    main_win.nav.setCurrentRow(settings_idx)
    app.processEvents()
    settings_widget = main_win.stack.currentWidget()
    settings_widget.tabs.setCurrentIndex(3)
    app.processEvents()

    main_shot = os.path.join(artifact_dir, "settings_phase4_in_main_window.png")
    main_win.grab().save(main_shot)
    print(f"  -> Saved MainWindow with Expenses Tab screenshot to {main_shot}")
    main_win.close()

    print("\nALL PHASE 4 EXPENSES TAB TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_expenses_tab()
