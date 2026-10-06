import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import mysql.connector

for h in ["127.0.0.1", "localhost"]:
    print(f"\n--- Testing host: {h} ---", flush=True)
    try:
        server = mysql.connector.connect(
            host=h,
            port=3306,
            user="root",
            password="",
            connection_timeout=3,
        )
        print(f"Success with {h}!", flush=True)
        cursor = server.cursor()
        cursor.execute("SELECT VERSION()")
        print(f"Version: {cursor.fetchone()}", flush=True)
        cursor.close()
        server.close()
    except Exception as e:
        print(f"Failed with {h}: {e}", flush=True)
