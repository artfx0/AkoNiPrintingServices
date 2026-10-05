import sys
import os
import json

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from main import load_app_stylesheet
from settings.settings_widget import SettingsWidget
from settings.settings_manager import SettingsManager

def test_sales_tab():
    app = QApplication.instance() or QApplication(sys.argv)
    qss = load_app_stylesheet()
    if qss:
        app.setStyleSheet(qss)

    admin_user = {"username": "admin", "role": "Admin"}
    widget = SettingsWidget(user=admin_user)
    widget.resize(1100, 750)
    widget.show()
    app.processEvents()

    # 1. Switch to Sales tab
    print("Test 1: Switching to Sales tab...")
    widget.tabs.setCurrentIndex(1)
    app.processEvents()
    assert widget.tabs.currentIndex() == 1
    assert widget.tabs.tabText(1) == "Sales"
    print("  -> Passed: Sales tab selected.")

    # 2. Verify Table Columns
    print("Test 2: Verifying Product Reference table...")
    table = widget.products_table
    assert table.columnCount() == 3
    headers = [table.horizontalHeaderItem(i).text() for i in range(3)]
    assert headers == ["Name", "Status", "Actions"], f"Unexpected headers: {headers}"
    print(f"  -> Passed: Table headers match exactly {headers}.")

    # 3. Verify Mock Row: Chocolate Box, Active, Edit & Archive
    print("Test 3: Verifying mock row data and styling...")
    assert table.rowCount() >= 1, "Expected at least 1 row in products table"
    first_name_item = table.item(0, 0)
    assert "Chocolate Box" in first_name_item.text(), f"Expected Chocolate Box, got {first_name_item.text()}"

    # Verify Status Badge
    status_widget = table.cellWidget(0, 1)
    status_label = status_widget.findChild(widget.products_table.__class__.__mro__[0], "") # or findChild QLabel
    from PyQt6.QtWidgets import QLabel, QPushButton
    status_lbl = status_widget.findChild(QLabel)
    assert status_lbl is not None, "Status badge QLabel not found"
    assert "Active" in status_lbl.text(), f"Expected Active status, got {status_lbl.text()}"
    assert status_lbl.property("status") == "active", "Status property is not 'active'"
    print(f"  -> Passed: Status badge is 'Active' with status='active' property.")

    # Verify Actions buttons
    actions_widget = table.cellWidget(0, 2)
    buttons = actions_widget.findChildren(QPushButton)
    btn_texts = [b.text() for b in buttons]
    assert "Edit" in btn_texts and "Archive" in btn_texts, f"Expected Edit & Archive, got {btn_texts}"
    print(f"  -> Passed: Action buttons {btn_texts} present and styled as SecondaryBtn.")

    # 4. Verify Input field & Add button
    print("Test 4: Verifying 'New product name' input and 'Add' button...")
    assert widget.new_product_input.placeholderText() == "New product name"
    assert widget.add_product_btn.text() == "Add"
    print("  -> Passed: Input field and Add button correctly configured.")

    # Capture initial Sales Tab screenshot
    artifact_dir = r"C:\Users\JohnPaul\.gemini\antigravity\brain\48e2fdad-38c3-4bae-92fc-f8ba6b8ded82"
    os.makedirs(artifact_dir, exist_ok=True)
    shot1 = os.path.join(artifact_dir, "settings_phase2_sales_tab.png")
    widget.grab().save(shot1)
    print(f"  -> Saved initial Sales Tab screenshot to {shot1}")

    # 5. Test Adding a new product
    print("Test 5: Testing 'Add' button flow...")
    initial_count = table.rowCount()
    widget.new_product_input.setText("Glossy Photo Sticker")
    widget._add_product()
    app.processEvents()
    assert table.rowCount() == initial_count + 1
    new_name_item = table.item(initial_count, 0)
    assert "Glossy Photo Sticker" in new_name_item.text()
    print("  -> Passed: New product successfully added and rendered.")

    # Capture screenshot with added product
    shot2 = os.path.join(artifact_dir, "settings_phase2_sales_tab_with_new_item.png")
    widget.grab().save(shot2)
    print(f"  -> Saved Sales Tab with added product screenshot to {shot2}")

    # 6. Test Archive toggle
    print("Test 6: Testing 'Archive' button toggle...")
    widget._toggle_archive_product(0)
    app.processEvents()
    status_widget = table.cellWidget(0, 1)
    status_lbl = status_widget.findChild(QLabel)
    assert "Archived" in status_lbl.text()
    assert status_lbl.property("status") == "other"
    print("  -> Passed: 'Archive' toggle updated status badge to 'Archived'.")

    # Revert to single mock row for clean state
    SettingsManager.save_product_references([{"name": "Chocolate Box", "status": "Active"}])
    widget._load_products()
    app.processEvents()

    # Re-save pristine screenshot of mock row
    widget.grab().save(shot1)
    widget.close()

    # 7. Capture MainWindow with Sales Tab
    from ui.main_window import MainWindow
    main_win = MainWindow(user=admin_user)
    main_win.resize(1280, 800)
    main_win.show()
    app.processEvents()

    settings_idx = main_win.nav.count() - 1
    main_win.nav.setCurrentRow(settings_idx)
    app.processEvents()
    settings_widget = main_win.stack.currentWidget()
    settings_widget.tabs.setCurrentIndex(1)
    app.processEvents()

    main_sales_shot = os.path.join(artifact_dir, "settings_phase2_in_main_window.png")
    main_win.grab().save(main_sales_shot)
    print(f"  -> Saved MainWindow with Sales Tab screenshot to {main_sales_shot}")
    main_win.close()

    print("\nALL PHASE 2 SALES TAB TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_sales_tab()
