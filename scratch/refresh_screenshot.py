import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

from main import load_app_stylesheet

app = QApplication.instance() or QApplication(sys.argv)
qss = load_app_stylesheet()
if qss:
    app.setStyleSheet(qss)

admin_user = {"username": "admin", "role": "Admin"}
win = MainWindow(user=admin_user)
win.resize(1280, 800)
win.show()
app.processEvents()

settings_idx = win.nav.count() - 1
win.nav.setCurrentRow(settings_idx)
app.processEvents()
win.stack.currentWidget().tabs.setCurrentIndex(3)
app.processEvents()

win.grab().save(r"C:\Users\JohnPaul\.gemini\antigravity\brain\48e2fdad-38c3-4bae-92fc-f8ba6b8ded82\settings_phase4_in_main_window.png")
win.settings_page.grab().save(r"C:\Users\JohnPaul\.gemini\antigravity\brain\48e2fdad-38c3-4bae-92fc-f8ba6b8ded82\settings_phase4_expenses_tab.png")
print("Screenshots refreshed!")
