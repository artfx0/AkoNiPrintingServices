import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("Starting debug step-by-step...", flush=True)

import mysql.connector
from database.database import load_config

cfg = load_config()
print(f"Config loaded: {cfg}", flush=True)

try:
    print("Connecting to MySQL server directly...", flush=True)
    server = mysql.connector.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        connection_timeout=5,
    )
    print("Direct connection established!", flush=True)
    cursor = server.cursor()
    cursor.execute("SELECT VERSION()")
    row = cursor.fetchone()
    print(f"MySQL Version: {row}", flush=True)
    cursor.close()
    server.close()
except Exception as e:
    import traceback
    print(f"Direct connection failed: {e}", flush=True)
    traceback.print_exc()

print("Debug finished.", flush=True)
