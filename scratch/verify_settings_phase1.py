import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import json

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from main import load_app_stylesheet
from settings.settings_widget import SettingsWidget
from settings.settings_manager import SettingsManager
from ui.main_window import MainWindow

def test_settings_module():
    app = QApplication.instance() or QApplication(sys.argv)
    qss = load_app_stylesheet()
    if qss:
        app.setStyleSheet(qss)

    # 1. Test Admin-only enforcement
    print("Test 1: Admin-only access enforcement...")
    try:
        SettingsWidget(user={"username": "staff1", "role": "Staff"})
        assert False, "Non-admin access did not raise PermissionError"
    except PermissionError:
        print("  -> Passed: Staff correctly rejected with PermissionError.")

    admin_user = {"username": "admin", "role": "Admin"}
    widget = SettingsWidget(user=admin_user)
    widget.resize(1100, 750)
    widget.show()
    app.processEvents()

    # 2. Test Tab structure
    print("Test 2: Tab structure and default selection...")
    assert widget.tabs.count() == 6, f"Expected 6 tabs, found {widget.tabs.count()}"
    expected_tabs = ["General", "Sales", "Payments", "Expenses", "Fulfillment", "User Access"]
    for i, expected_title in enumerate(expected_tabs):
        actual_title = widget.tabs.tabText(i)
        assert actual_title == expected_title, f"Tab {i} expected {expected_title}, got {actual_title}"
    assert widget.tabs.currentIndex() == 0, f"Expected default tab 0, got {widget.tabs.currentIndex()}"
    print(f"  -> Passed: All 6 tabs present in order, 'General' is active tab 0.")

    # 3. Test Form fields
    print("Test 3: Business Information Form fields...")
    assert widget.business_name_edit.isReadOnly() is True
    assert widget.business_address_edit.isReadOnly() is True
    assert widget.contact_number_edit.isReadOnly() is True
    assert widget.email_address_edit.isReadOnly() is True
    assert widget.social_contact_edit.isReadOnly() is True
    assert widget.payment_instructions_edit.isReadOnly() is True
    assert widget.invoice_reminder_edit.isReadOnly() is True
    assert widget.edit_btn.isVisible() is True
    assert widget.save_btn.isVisible() is False
    assert widget.cancel_btn.isVisible() is False
    print("  -> Passed: Form fields initialized in read-only view mode with 'Edit' button visible.")

    # Load and verify values
    b_name = widget.business_name_edit.text()
    assert len(b_name) > 0, "Business name is empty"
    print(f"  -> Business Name: {b_name}")

    # Capture View Mode Screenshot
    artifact_dir = r"C:\Users\JohnPaul\.gemini\antigravity\brain\48e2fdad-38c3-4bae-92fc-f8ba6b8ded82"
    os.makedirs(artifact_dir, exist_ok=True)
    view_shot_path = os.path.join(artifact_dir, "settings_phase1_view_mode.png")
    widget.grab().save(view_shot_path)
    print(f"  -> Saved view mode screenshot to {view_shot_path}")

    # 4. Test Edit mode toggle
    print("Test 4: Edit mode toggle and input enablement...")
    widget._enable_editing()
    app.processEvents()
    assert widget.business_name_edit.isReadOnly() is False
    assert widget.business_address_edit.isReadOnly() is False
    assert widget.contact_number_edit.isReadOnly() is False
    assert widget.payment_instructions_edit.isReadOnly() is False
    assert widget.edit_btn.isVisible() is False
    assert widget.save_btn.isVisible() is True
    assert widget.cancel_btn.isVisible() is True
    print("  -> Passed: Edit mode active, inputs editable, Save/Cancel visible.")

    # Capture Edit Mode Screenshot
    edit_shot_path = os.path.join(artifact_dir, "settings_phase1_edit_mode.png")
    widget.grab().save(edit_shot_path)
    print(f"  -> Saved edit mode screenshot to {edit_shot_path}")

    # Test Cancel reverts
    widget.business_name_edit.setText("Temporary Unsaved Business Name")
    widget._cancel_editing()
    app.processEvents()
    assert widget.business_name_edit.text() == b_name
    assert widget.business_name_edit.isReadOnly() is True
    assert widget.edit_btn.isVisible() is True
    print("  -> Passed: Cancel reverts dirty fields and returns to view mode.")

    # 5. Test Placeholder Tab view
    print("Test 5: Placeholder tabs rendering...")
    widget.tabs.setCurrentIndex(1)  # Sales
    app.processEvents()
    sales_shot_path = os.path.join(artifact_dir, "settings_phase1_sales_placeholder.png")
    widget.grab().save(sales_shot_path)
    print(f"  -> Saved sales placeholder screenshot to {sales_shot_path}")
    widget.tabs.setCurrentIndex(0)
    widget.close()

    # 6. Test MainWindow Integration
    print("Test 6: MainWindow integration and navigation...")
    main_win = MainWindow(user=admin_user)
    main_win.resize(1280, 800)
    main_win.show()
    app.processEvents()

    # Navigate to Settings tab
    settings_idx = main_win.nav.count() - 1
    main_win.nav.setCurrentRow(settings_idx)
    app.processEvents()
    current_page = main_win.stack.currentWidget()
    assert isinstance(current_page, SettingsWidget), f"Expected SettingsWidget, got {type(current_page)}"
    print(f"  -> Passed: Settings module opens smoothly inside MainWindow at nav row {settings_idx}.")

    main_shot_path = os.path.join(artifact_dir, "settings_phase1_in_main_window.png")
    main_win.grab().save(main_shot_path)
    print(f"  -> Saved full MainWindow screenshot to {main_shot_path}")
    main_win.close()

    print("\nALL PHASE 1 SETTINGS MODULE TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_settings_module()
