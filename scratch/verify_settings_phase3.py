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

def test_payments_tab():
    app = QApplication.instance() or QApplication(sys.argv)
    qss = load_app_stylesheet()
    if qss:
        app.setStyleSheet(qss)

    admin_user = {"username": "admin", "role": "Admin"}
    widget = SettingsWidget(user=admin_user)
    widget.resize(1100, 850)
    widget.show()
    app.processEvents()

    # 1. Select Payments Tab
    print("Test 1: Selecting Payments Tab...")
    widget.tabs.setCurrentIndex(2)
    app.processEvents()
    assert widget.tabs.currentIndex() == 2
    assert widget.tabs.tabText(2) == "Payments"
    print("  -> Passed: Payments tab selected at index 2.")

    # 2. Verify Payment Methods Table
    print("Test 2: Verifying Payment Methods Section...")
    m_table = widget.methods_table
    assert m_table.columnCount() == 3
    m_headers = [m_table.horizontalHeaderItem(i).text() for i in range(3)]
    assert m_headers == ["Name", "Status", "Actions"]
    assert m_table.rowCount() == 2, f"Expected 2 mock rows, got {m_table.rowCount()}"

    # Row 0: GCash
    assert "GCash" in m_table.item(0, 0).text()
    status_lbl_0 = m_table.cellWidget(0, 1).findChild(QLabel)
    assert "Active" in status_lbl_0.text()
    assert status_lbl_0.property("status") == "active"
    btns_0 = [b.text() for b in m_table.cellWidget(0, 2).findChildren(QPushButton)]
    assert "Edit" in btns_0 and "Archive" in btns_0

    # Row 1: Bank Transfer
    assert "Bank Transfer" in m_table.item(1, 0).text()
    status_lbl_1 = m_table.cellWidget(1, 1).findChild(QLabel)
    assert "Active" in status_lbl_1.text()
    assert status_lbl_1.property("status") == "active"
    btns_1 = [b.text() for b in m_table.cellWidget(1, 2).findChildren(QPushButton)]
    assert "Edit" in btns_1 and "Archive" in btns_1
    print("  -> Passed: Mock rows 'GCash' and 'Bank Transfer' verified with active badges and action buttons.")

    # Input and Add button
    assert widget.new_method_input.placeholderText() == "New payment method name"
    assert widget.add_method_btn.text() == "Add"
    print("  -> Passed: New payment method input and Add button present.")

    # 3. Verify Payment Accounts Section
    print("Test 3: Verifying Payment Accounts Section...")
    a_table = widget.accounts_table
    assert a_table.columnCount() == 8
    expected_a_headers = ["Method", "Label", "Account Name", "Number/Details", "Invoice", "Order", "Status", "Actions"]
    actual_a_headers = [a_table.horizontalHeaderItem(i).text() for i in range(8)]
    assert actual_a_headers == expected_a_headers, f"Expected {expected_a_headers}, got {actual_a_headers}"

    # Verify empty table state
    assert a_table.rowCount() == 0, f"Expected 0 rows in empty accounts table, got {a_table.rowCount()}"
    assert widget.no_accounts_label.isVisible() is True
    assert widget.no_accounts_label.text() == "No payment accounts yet"
    print("  -> Passed: Payment Accounts table is empty with 'No payment accounts yet' placeholder displayed.")

    # 4. Verify Form below empty table
    print("Test 4: Verifying Payment Account Form inputs...")
    assert widget.account_method_combo.count() >= 2
    assert "GCash" in [widget.account_method_combo.itemText(i) for i in range(widget.account_method_combo.count())]
    assert "Display Label" in widget.account_label_input.placeholderText() or "Label" in widget.account_label_input.placeholderText()
    assert "Account Name" in widget.account_name_input.placeholderText() or "Name" in widget.account_name_input.placeholderText()
    assert widget.add_account_btn is not None
    print("  -> Passed: Form inputs (Payment Method combo, Display Label, Account Name) verified.")

    # Capture initial Payments Tab screenshot (empty accounts table state)
    artifact_dir = r"C:\Users\JohnPaul\.gemini\antigravity\brain\48e2fdad-38c3-4bae-92fc-f8ba6b8ded82"
    os.makedirs(artifact_dir, exist_ok=True)
    shot1 = os.path.join(artifact_dir, "settings_phase3_payments_tab.png")
    widget.grab().save(shot1)
    print(f"  -> Saved initial Payments Tab screenshot to {shot1}")

    # 5. Test Adding a Payment Account
    print("Test 5: Adding a payment account through the form...")
    widget.account_method_combo.setCurrentText("GCash")
    widget.account_label_input.setText("Primary QR Account")
    widget.account_name_input.setText("AkoNi Printing Services")
    widget._add_payment_account()
    app.processEvents()

    assert a_table.rowCount() == 1
    assert widget.no_accounts_label.isVisible() is False
    assert "GCash" in a_table.item(0, 0).text()
    assert "Primary QR Account" in a_table.item(0, 1).text()
    assert "AkoNi Printing Services" in a_table.item(0, 2).text()
    print("  -> Passed: Payment account added and rendered in accounts table.")

    shot2 = os.path.join(artifact_dir, "settings_phase3_payments_tab_with_account.png")
    widget.grab().save(shot2)
    print(f"  -> Saved Payments Tab with added account screenshot to {shot2}")

    # Clean up added account for default pristine empty state
    SettingsManager.save_payment_accounts([])
    widget._load_payment_accounts()
    app.processEvents()
    assert a_table.rowCount() == 0
    assert widget.no_accounts_label.isVisible() is True
    widget.close()

    # 6. Test MainWindow Integration
    print("Test 6: Verifying MainWindow integration with Payments tab...")
    from ui.main_window import MainWindow
    main_win = MainWindow(user=admin_user)
    main_win.resize(1280, 800)
    main_win.show()
    app.processEvents()

    settings_idx = main_win.nav.count() - 1
    main_win.nav.setCurrentRow(settings_idx)
    app.processEvents()
    settings_widget = main_win.stack.currentWidget()
    settings_widget.tabs.setCurrentIndex(2)
    app.processEvents()

    main_shot = os.path.join(artifact_dir, "settings_phase3_in_main_window.png")
    main_win.grab().save(main_shot)
    print(f"  -> Saved MainWindow with Payments Tab screenshot to {main_shot}")
    main_win.close()

    print("\nALL PHASE 3 PAYMENTS TAB TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_payments_tab()
