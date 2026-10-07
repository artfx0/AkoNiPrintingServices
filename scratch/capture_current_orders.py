import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication
from main import load_app_stylesheet
from sales_orders.order_widget import OrderWidget

app = QApplication.instance() or QApplication(sys.argv)
qss = load_app_stylesheet()
if qss:
    app.setStyleSheet(qss)

admin_user = {"username": "admin", "role": "Admin", "user_id": 1}
widget = OrderWidget(user=admin_user)
widget.resize(1200, 750)
widget.show()
app.processEvents()

artifact_path = r"C:\Users\JohnPaul\.gemini\antigravity\brain\48e2fdad-38c3-4bae-92fc-f8ba6b8ded82\orders_table_current_state.png"
widget.grab().save(artifact_path)
print("Saved orders table screenshot to", artifact_path)
