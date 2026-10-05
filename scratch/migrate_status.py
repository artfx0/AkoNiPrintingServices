import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database.database import get_connection

def migrate():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE customer_orders SET status = 'Processing' WHERE status = 'In Progress'")
    conn.commit()
    print("Rows updated:", cur.rowcount)
    cur.execute("SELECT status, COUNT(*) FROM customer_orders GROUP BY status")
    print("Current order counts:", cur.fetchall())
    conn.close()

if __name__ == "__main__":
    migrate()
