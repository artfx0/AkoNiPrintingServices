import sys
import os
import json

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QSizePolicy
from PyQt6.QtCore import Qt

from main import load_app_stylesheet
from settings.settings_widget import SettingsWidget
from settings.settings_manager import SettingsManager


def test_user_access_tab():
    app = QApplication.instance() or QApplication(sys.argv)
    qss = load_app_stylesheet()
    if qss:
        app.setStyleSheet(qss)

    admin_user = {"username": "admin", "role": "Admin"}
    widget = SettingsWidget(user=admin_user)
    widget.resize(1100, 750)
    widget.show()
    app.processEvents()

    # 1. Select User Access Tab (index 5)
    print("Test 1: Selecting User Access Tab...")
    widget.tabs.setCurrentIndex(5)
    app.processEvents()
    assert widget.tabs.currentIndex() == 5
    assert widget.tabs.tabText(5) == "User Access"
    print("  -> Passed: User Access tab selected at index 5.")

    # 2. Verify Admin Account Section
    print("Test 2: Verifying Admin Account section details and buttons...")
    assert "Earth Justin Anne Lim" in widget.admin_name_lbl.text()
    assert "@earth" in widget.admin_handle_lbl.text()
    admin_pill = widget.admin_status_widget.findChild(QLabel, "StatusPill")
    assert admin_pill is not None
    assert "Active" in admin_pill.text()
    assert admin_pill.property("status") == "active"

    assert widget.edit_admin_btn.text() == "Edit Account"
    assert widget.edit_admin_btn.objectName() == "SecondaryBtn"
    assert widget.change_admin_pw_btn.text() == "Change Password"
    assert widget.change_admin_pw_btn.objectName() == "SecondaryBtn"
    print("  -> Passed: Admin details and action buttons verified.")

    # 3. Verify Staff Accounts Table & Mock Row
    print("Test 3: Verifying Staff Accounts table and mock row...")
    table = widget.staff_table
    assert table.columnCount() == 4
    headers = [table.horizontalHeaderItem(i).text() for i in range(4)]
    assert headers == ["Name", "Username", "Status", "Action"], f"Unexpected headers: {headers}"
    assert table.rowCount() == 1, f"Expected 1 mock row, got {table.rowCount()}"

    row_name = table.item(0, 0).text().strip()
    row_user = table.item(0, 1).text().strip()
    assert row_name == "Carlo Reyes", f"Expected 'Carlo Reyes', got '{row_name}'"
    assert row_user == "dev_staff", f"Expected 'dev_staff', got '{row_user}'"

    status_cell = table.cellWidget(0, 2)
    staff_pill = status_cell.findChild(QLabel, "StatusPill")
    assert staff_pill is not None
    assert "Active" in staff_pill.text()
    assert staff_pill.property("status") == "active"

    actions_cell = table.cellWidget(0, 3)
    btns = actions_cell.findChildren(QPushButton)
    assert len(btns) == 3, f"Expected 3 action buttons, got {len(btns)}"
    assert btns[0].text() == "Edit"
    assert btns[1].text() == "Reset Password"
    assert btns[2].text() == "Deactivate"
    for b in btns:
        assert b.objectName() == "SecondaryBtn"
    print("  -> Passed: Staff table mock row and action buttons verified.")

    # 4. Verify Full-width 'Add Staff' Button
    print("Test 4: Verifying full-width outlined 'Add Staff' button...")
    assert widget.add_staff_btn.text() == "Add Staff"
    assert widget.add_staff_btn.objectName() == "SecondaryBtn"
    assert widget.add_staff_btn.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding
    print("  -> Passed: Full-width outlined 'Add Staff' button verified.")

    # Save initial tab screenshot
    artifact_dir = r"C:\Users\JohnPaul\.gemini\antigravity\brain\48e2fdad-38c3-4bae-92fc-f8ba6b8ded82"
    tab_shot = os.path.join(artifact_dir, "settings_phase6_user_access_tab.png")
    widget.grab().save(tab_shot)
    print(f"  -> Saved initial User Access Tab screenshot to {tab_shot}")

    # 5. Test Staff Deactivation Toggle
    print("Test 5: Testing staff deactivation toggle on row 0...")
    widget._toggle_deactivate_staff(0)
    app.processEvents()
    status_cell = table.cellWidget(0, 2)
    staff_pill = status_cell.findChild(QLabel, "StatusPill")
    assert "Deactivated" in staff_pill.text()
    actions_cell = table.cellWidget(0, 3)
    btns = actions_cell.findChildren(QPushButton)
    assert btns[2].text() == "Activate"
    print("  -> Passed: Staff toggled to Deactivated and button changed to Activate.")

    # Reset mock data to clean state
    print("Resetting mock data to clean state...")
    clean_staff = [
        {"name": "Carlo Reyes", "username": "dev_staff", "status": "Active"}
    ]
    SettingsManager.save_staff_accounts(clean_staff)
    widget._load_user_access_data()
    app.processEvents()
    assert table.rowCount() == 1
    widget.grab().save(tab_shot)

    # 6. Capture full MainWindow with User Access Tab
    print("Test 6: Capturing full MainWindow with User Access Tab...")
    from ui.main_window import MainWindow
    main_win = MainWindow(user=admin_user)
    main_win.resize(1280, 800)
    main_win.show()
    app.processEvents()

    settings_idx = main_win.nav.count() - 1
    main_win.nav.setCurrentRow(settings_idx)
    app.processEvents()
    settings_widget = main_win.stack.currentWidget()
    settings_widget.tabs.setCurrentIndex(5)
    app.processEvents()

    main_shot = os.path.join(artifact_dir, "settings_phase6_in_main_window.png")
    main_win.grab().save(main_shot)
    print(f"  -> Saved MainWindow with User Access Tab screenshot to {main_shot}")

    print("\nALL PHASE 6 USER ACCESS TAB TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_user_access_tab()
