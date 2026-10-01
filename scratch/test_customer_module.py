import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer

from customers.customer_widget import CustomerWidget
from customers.customer_management import CustomerManager
from database.database import get_connection

def run_test():
    os.environ["QT_QPA_PLATFORM"] = "windows"
    app = QApplication.instance() or QApplication(sys.argv)

    # Load styles
    if os.path.exists("ui/styles.qss"):
        with open("ui/styles.qss", "r") as f:
            app.setStyleSheet(f.read())

    widget = CustomerWidget()
    widget.resize(1100, 750)
    widget.show()

    # 1. Verification of columns
    col_count = widget.table.columnCount()
    assert col_count == 8, f"Expected 8 columns, got {col_count}"
    assert widget.table.isColumnHidden(0), "Column 0 (ID) must be hidden!"
    assert not widget.table.isColumnHidden(1), "Column 1 (First Name) should be visible!"

    headers = [widget.table.horizontalHeaderItem(i).text() for i in range(col_count)]
    print(f"Headers: {headers}")
    print(f"Column 0 hidden: {widget.table.isColumnHidden(0)}")

    # 2. Check inline input fields
    assert widget.input_first_name is not None
    assert widget.input_last_name is not None
    assert widget.input_contact is not None
    assert widget.input_email is not None
    assert widget.input_address is not None
    assert widget.add_customer_btn is not None
    assert widget.clear_form_btn is not None
    print("Inline form fields verified.")

    # 3. Check status button in table and toggle row 1 to Inactive for visual verification
    row_count = widget.table.rowCount()
    print(f"Table row count: {row_count}")
    if row_count > 1:
        status_widget_0 = widget.table.cellWidget(0, 7)
        btn0 = status_widget_0.findChild(type(widget.add_customer_btn))
        print(f"Row 0 Status Button text: {btn0.text()}")

        status_widget_1 = widget.table.cellWidget(1, 7)
        btn1 = status_widget_1.findChild(type(widget.add_customer_btn))
        print(f"Row 1 Status Button text before click: {btn1.text()}")
        # Click row 1 button to toggle to Inactive
        btn1.click()
        app.processEvents()

        # Re-fetch after refresh
        status_widget_1_after = widget.table.cellWidget(1, 7)
        btn1_after = status_widget_1_after.findChild(type(widget.add_customer_btn))
        print(f"Row 1 Status Button text after click: {btn1_after.text()}")

    # 4. Take a screenshot
    app.processEvents()
    pix = widget.grab()
    out_path = r"C:\Users\JohnPaul\.gemini\antigravity\brain\48e2fdad-38c3-4bae-92fc-f8ba6b8ded82\updated_customer_module_preview.png"
    pix.save(out_path)
    print(f"Saved preview screenshot to: {out_path}")

    widget.close()
    print("ALL CHECKS PASSED.")

if __name__ == "__main__":
    run_test()
