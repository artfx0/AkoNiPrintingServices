import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication
from main import load_app_stylesheet
from ui.login_window import LoginWindow

app = QApplication.instance() or QApplication(sys.argv)
qss = load_app_stylesheet()
if qss:
    app.setStyleSheet(qss)

login = LoginWindow()
login.show()
app.processEvents()

artifact_path = r"C:\Users\JohnPaul\.gemini\antigravity\brain\48e2fdad-38c3-4bae-92fc-f8ba6b8ded82\system_startup_login_window.png"
login.grab().save(artifact_path)
print("Saved LoginWindow screenshot to", artifact_path)
