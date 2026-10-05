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


def test_fulfillment_tab():
    app = QApplication.instance() or QApplication(sys.argv)
    qss = load_app_stylesheet()
    if qss:
        app.setStyleSheet(qss)

    admin_user = {"username": "admin", "role": "Admin"}
    widget = SettingsWidget(user=admin_user)
    widget.resize(1100, 750)
    widget.show()
    app.processEvents()

    # 1. Select Fulfillment Tab (index 4)
    print("Test 1: Selecting Fulfillment Tab...")
    widget.tabs.setCurrentIndex(4)
    app.processEvents()
    assert widget.tabs.currentIndex() == 4
    assert widget.tabs.tabText(4) == "Fulfillment"
    print("  -> Passed: Fulfillment tab selected at index 4.")

    # 2. Verify Table Columns and Mock Rows
    print("Test 2: Verifying Courier Options table columns and mock rows...")
    table = widget.couriers_table
    assert table.columnCount() == 3
    headers = [table.horizontalHeaderItem(i).text() for i in range(3)]
    assert headers == ["Name", "Status", "Actions"], f"Unexpected headers: {headers}"
    assert table.rowCount() == 3, f"Expected 3 mock rows, got {table.rowCount()}"

    expected_couriers = ["Grab", "J&T", "LBC"]
    for r, exp_name in enumerate(expected_couriers):
        name_text = table.item(r, 0).text().strip()
        assert name_text == exp_name, f"Row {r} name mismatch: '{name_text}' != '{exp_name}'"

        status_cell = table.cellWidget(r, 1)
        status_pill = status_cell.findChild(QLabel, "StatusPill")
        assert status_pill is not None
        assert "Active" in status_pill.text()
        assert status_pill.property("status") == "active"

        actions_cell = table.cellWidget(r, 2)
        btns = actions_cell.findChildren(QPushButton)
        assert len(btns) == 2, f"Row {r} expected 2 action buttons, found {len(btns)}"
        assert btns[0].text() == "Edit"
        assert btns[1].text() == "Archive"
        print(f"  -> Row {r}: {exp_name} | Active | Edit & Archive verified.")

    # 3. Verify Bottom Input and Solid Gold Add Button
    print("Test 3: Verifying bottom input and Add button...")
    assert widget.new_courier_input.placeholderText() == "New courier name"
    assert widget.add_courier_btn.text() == "Add"
    print("  -> Passed: Input field and Add button verified.")

    # Save initial Fulfillment Tab screenshot
    artifact_dir = r"C:\Users\JohnPaul\.gemini\antigravity\brain\48e2fdad-38c3-4bae-92fc-f8ba6b8ded82"
    tab_shot = os.path.join(artifact_dir, "settings_phase5_fulfillment_tab.png")
    widget.grab().save(tab_shot)
    print(f"  -> Saved initial Fulfillment Tab screenshot to {tab_shot}")

    # 4. Test Add Courier functionality
    print("Test 4: Adding a new courier 'Ninja Van'...")
    widget.new_courier_input.setText("Ninja Van")
    widget._add_courier()
    app.processEvents()
    assert table.rowCount() == 4
    assert table.item(3, 0).text().strip() == "Ninja Van"
    print("  -> Passed: 'Ninja Van' added successfully. Table now has 4 rows.")

    # 5. Test Toggle Archive functionality
    print("Test 5: Testing archive operation on row 0 (Grab)...")
    widget._toggle_archive_courier(0)
    app.processEvents()
    status_cell = table.cellWidget(0, 1)
    status_pill = status_cell.findChild(QLabel, "StatusPill")
    assert "Archived" in status_pill.text()
    assert status_pill.property("status") == "other"
    actions_cell = table.cellWidget(0, 2)
    btns = actions_cell.findChildren(QPushButton)
    assert btns[1].text() == "Restore"
    print("  -> Passed: Row 0 archived successfully. Status is now Archived and button is Restore.")

    # Reset mock data to clean state for final screenshots
    print("Resetting mock data to pristine 3 rows...")
    clean_couriers = [
        {"name": "Grab", "status": "Active"},
        {"name": "J&T", "status": "Active"},
        {"name": "LBC", "status": "Active"},
    ]
    SettingsManager.save_courier_options(clean_couriers)
    widget._load_couriers()
    app.processEvents()
    assert table.rowCount() == 3
    widget.grab().save(tab_shot)

    # 6. Full MainWindow Verification
    print("Test 6: Capturing full MainWindow with Fulfillment Tab...")
    from ui.main_window import MainWindow
    main_win = MainWindow(user=admin_user)
    main_win.resize(1280, 800)
    main_win.show()
    app.processEvents()

    settings_idx = main_win.nav.count() - 1
    main_win.nav.setCurrentRow(settings_idx)
    app.processEvents()
    settings_widget = main_win.stack.currentWidget()
    settings_widget.tabs.setCurrentIndex(4)
    app.processEvents()

    main_shot = os.path.join(artifact_dir, "settings_phase5_in_main_window.png")
    main_win.grab().save(main_shot)
    print(f"  -> Saved MainWindow with Fulfillment Tab screenshot to {main_shot}")

    print("\nALL PHASE 5 FULFILLMENT TAB TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_fulfillment_tab()
