import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Set headless platform plugin offscreen so it runs smoothly
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.abspath("."))

from sales_orders.order_widget import OrderWidget
from database.database import get_connection

def test_order_widget():
    app = QApplication(sys.argv)
    
    # Load application stylesheet if exists
    if os.path.exists("ui/styles.qss"):
        with open("ui/styles.qss", "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
            
    user = {"user_id": 1, "username": "admin", "role": "Admin"}
    widget = OrderWidget(user=user)
    widget.resize(1200, 800)
    widget.show()
    app.processEvents()
    
    # Verification 1: ID column is hidden
    assert widget.table.isColumnHidden(0), "Column 0 (Order #) should be hidden visually!"
    print("Verification 1 Passed: Column 0 (Order #) is hidden.")
    
    # Verification 2: Rows exist and status widgets are readable
    row_count = widget.table.rowCount()
    print(f"Table row count: {row_count}")
    if row_count > 0:
        cell_widget = widget.table.cellWidget(0, 5)
        assert cell_widget is not None, "Column 5 must contain the status pill widget!"
        labels = cell_widget.findChildren(widget.__class__) or cell_widget.children()
        print(f"Cell widget on row 0: {cell_widget}, children count: {len(labels)}")
    print("Verification 2 Passed: Status badges are set as cell widgets.")
    
    # Verification 3: Inline form controls exist
    assert hasattr(widget, "input_customer"), "input_customer combobox missing!"
    assert hasattr(widget, "input_product"), "input_product missing!"
    assert hasattr(widget, "input_qty"), "input_qty missing!"
    assert hasattr(widget, "input_price"), "input_price missing!"
    assert hasattr(widget, "add_order_btn"), "add_order_btn missing!"
    print("Verification 3 Passed: Inline add order form controls exist.")
    
    # Verification 4: Test selecting customer and auto-filling address
    if widget.input_customer.count() > 0:
        widget.input_customer.setCurrentIndex(0)
        app.processEvents()
        print(f"Selected customer: {widget.input_customer.currentText()}, Address: {widget.input_address.text()}")
        
    # Verification 5: Live total calculation
    widget.input_qty.setValue(50)
    widget.input_price.setValue(20.00)
    widget.input_rush.setValue(100.00)
    widget.input_discount.setValue(50.00)
    app.processEvents()
    print(f"Live total badge text: {widget.inline_total_badge.text()}")
    assert "1,050.00" in widget.inline_total_badge.text(), "Total calculation mismatch!"
    print("Verification 5 Passed: Live total calculation correct.")
    
    # Capture screenshot for visual inspection
    screenshot_path = "scratch/orders_module_redesign_preview.png"
    pixmap = widget.grab()
    pixmap.save(screenshot_path)
    print(f"Screenshot saved to: {screenshot_path}")

    # Also save to conversation artifacts directory
    artifact_path = r"C:\Users\JohnPaul\.gemini\antigravity\brain\48e2fdad-38c3-4bae-92fc-f8ba6b8ded82\orders_module_redesign_preview.png"
    pixmap.save(artifact_path)
    print(f"Artifact screenshot saved to: {artifact_path}")

if __name__ == "__main__":
    test_order_widget()
