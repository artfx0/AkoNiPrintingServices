import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("1. Testing database imports and connection...")
try:
    from database.database import init_database, test_connection
    print("Testing init_database()...")
    init_database()
    print("init_database() SUCCESS")
    ok, msg = test_connection()
    print(f"test_connection(): ok={ok}, msg={msg}")
except Exception as e:
    import traceback
    print("Database error:", e)
    traceback.print_exc()

print("\n2. Testing Qt imports and components...")
try:
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    from ui.login_window import LoginWindow
    print("LoginWindow imported successfully")
    login = LoginWindow()
    print("LoginWindow instantiated successfully")
    from ui.main_window import MainWindow
    print("MainWindow imported successfully")
    admin_user = {"username": "admin", "role": "Admin", "first_name": "Admin", "last_name": "User"}
    win = MainWindow(admin_user)
    print("MainWindow instantiated successfully")
except Exception as e:
    import traceback
    print("Qt/UI error:", e)
    traceback.print_exc()
