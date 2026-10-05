import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from sales_orders.sales_order_management import (
    ORDER_STATUSES, CANCELLABLE_STATUSES, NON_CANCELLABLE_STATUSES, OrderManager
)
from sales_orders.order_widget import OrderWidget
from database.database import get_connection

def test_status_unification():
    print("--- Testing Constants & Business Rules ---")
    assert "In Progress" not in ORDER_STATUSES, "In Progress should not be in ORDER_STATUSES"
    assert ORDER_STATUSES == ("Pending", "Processing", "Paid", "Ready", "Delivered", "Cancelled")
    print(f"ORDER_STATUSES: {ORDER_STATUSES}")

    assert "In Progress" not in CANCELLABLE_STATUSES, "In Progress should not be in CANCELLABLE_STATUSES"
    assert CANCELLABLE_STATUSES == ("Pending", "Processing")
    print(f"CANCELLABLE_STATUSES: {CANCELLABLE_STATUSES}")

    conn = get_connection()
    mgr = OrderManager(conn)

    # Test cancellation logic
    mgr.validate_cancellation("Pending")
    mgr.validate_cancellation("Processing")
    print("Pending and Processing successfully validated as cancellable.")

    for blocked in ("Paid", "Ready", "Delivered", "Cancelled", "In Progress"):
        try:
            mgr.validate_cancellation(blocked)
            assert False, f"Expected validation error for status '{blocked}'"
        except ValueError as e:
            print(f"Correctly blocked cancellation for '{blocked}': {e.args[0].splitlines()[0]}")

    # Check database counts
    counts = mgr.count_orders_by_status()
    print(f"Orders count by status: {counts}")
    assert "In Progress" not in counts, "In Progress should not be in counts dictionary"
    conn.close()

    print("\n--- Testing Orders Widget UI ---")
    os.environ["QT_QPA_PLATFORM"] = "windows"
    app = QApplication.instance() or QApplication(sys.argv)

    if os.path.exists("ui/styles.qss"):
        with open("ui/styles.qss", "r") as f:
            app.setStyleSheet(f.read())

    widget = OrderWidget()
    widget.resize(1200, 780)
    widget.show()
    app.processEvents()

    # Verify KPI cards
    card_keys = list(widget.status_cards.keys())
    print(f"Status KPI card keys: {card_keys}")
    assert "In Progress" not in card_keys, "'In Progress' KPI card must be removed"
    assert card_keys == ["Pending", "Processing", "Paid", "Ready", "Delivered", "Cancelled"]

    # Verify cancel tooltip
    print(f"Cancel tooltip: {widget.cancel_btn.toolTip()}")
    assert "Pending or Processing only" in widget.cancel_btn.toolTip()

    # Capture default view screenshot
    out_dir = r"C:\Users\JohnPaul\.gemini\antigravity\brain\48e2fdad-38c3-4bae-92fc-f8ba6b8ded82"
    app.processEvents()
    pix = widget.grab()
    pix.save(os.path.join(out_dir, "updated_orders_module_preview.png"))
    print(f"Saved default preview screenshot to {out_dir}\\updated_orders_module_preview.png")

    # Click Processing card to test filter and active state
    proc_card = widget.status_cards["Processing"]
    proc_card.clicked.emit("Processing")
    app.processEvents()

    assert widget._active_status == "Processing"
    print(f"Active status after clicking Processing card: {widget._active_status}")
    print(f"Table row count for Processing: {widget.table.rowCount()}")

    # Capture filtered view screenshot
    app.processEvents()
    pix_proc = widget.grab()
    pix_proc.save(os.path.join(out_dir, "updated_orders_module_processing_filter_preview.png"))
    print(f"Saved processing filter preview screenshot to {out_dir}\\updated_orders_module_processing_filter_preview.png")

    # Toggle off
    proc_card.clicked.emit("Processing")
    app.processEvents()
    assert widget._active_status is None
    print(f"Active status after toggling off: {widget._active_status}")

    widget.close()
    print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_status_unification()
