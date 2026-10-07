import sys
import os

sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtCore import QSize
from main import load_app_stylesheet

def main():
    app = QApplication.instance() or QApplication(sys.argv)
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeuib.ttf")
    QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeuisl.ttf")
    qss = load_app_stylesheet()
    if qss:
        app.setStyleSheet(qss)
    app.setFont(QFont("Segoe UI", 10))

    # 1. Test PaymentWidget
    from payments.payment_widget import PaymentWidget
    pay_widget = PaymentWidget(user={"user_id": 1, "username": "admin", "role": "admin"})
    pay_widget.resize(1200, 800)
    pay_widget.show()
    app.processEvents()

    # Assertions for Payments Module
    assert hasattr(pay_widget, "input_order"), "input_order missing"
    assert hasattr(pay_widget, "input_type"), "input_type missing"
    assert hasattr(pay_widget, "input_method"), "input_method missing"
    assert hasattr(pay_widget, "input_date"), "input_date missing"
    assert hasattr(pay_widget, "input_amount"), "input_amount missing"
    assert hasattr(pay_widget, "input_status"), "input_status missing"
    assert hasattr(pay_widget, "record_payment_btn"), "record_payment_btn missing"
    assert hasattr(pay_widget, "clear_payment_btn"), "clear_payment_btn missing"
    assert pay_widget.table.isColumnHidden(0), "Table column 0 (Payment #) must be hidden"

    # Status Pill test
    pill_widget = pay_widget._create_pill_widget("Completed", "Completed")
    assert pill_widget is not None

    artifact_dir = r"C:\Users\JohnPaul\.gemini\antigravity\brain\48e2fdad-38c3-4bae-92fc-f8ba6b8ded82"
    pay_shot_path = os.path.join(artifact_dir, "payments_module_redesign_preview.png")
    pay_pix = pay_widget.grab()
    pay_pix.save(pay_shot_path)
    print(f"Payments screenshot saved to: {pay_shot_path}")
    pay_widget.close()

    # 2. Test ExpenseWidget
    from expenses.expense_widget import ExpenseWidget
    exp_widget = ExpenseWidget(user={"user_id": 1, "username": "admin", "role": "admin"})
    exp_widget.resize(1200, 800)
    exp_widget.show()
    app.processEvents()

    # Assertions for Expenses Module
    assert hasattr(exp_widget, "input_date"), "input_date missing"
    assert hasattr(exp_widget, "input_category"), "input_category missing"
    assert hasattr(exp_widget, "input_amount"), "input_amount missing"
    assert hasattr(exp_widget, "input_desc"), "input_desc missing"
    assert hasattr(exp_widget, "input_link_movement"), "input_link_movement missing"
    assert hasattr(exp_widget, "record_expense_btn"), "record_expense_btn missing"
    assert hasattr(exp_widget, "clear_expense_btn"), "clear_expense_btn missing"
    assert exp_widget.table.isColumnHidden(0), "Table column 0 (Expense #) must be hidden"

    # Category Pill test
    cat_pill = exp_widget._create_category_pill("Materials")
    assert cat_pill is not None

    exp_shot_path = os.path.join(artifact_dir, "expenses_module_redesign_preview.png")
    exp_pix = exp_widget.grab()
    exp_pix.save(exp_shot_path)
    print(f"Expenses screenshot saved to: {exp_shot_path}")
    exp_widget.close()

    print("ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
