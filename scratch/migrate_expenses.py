import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database.database import get_connection

def migrate_expenses():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE expenses SET category = 'Miscellaneous' WHERE category = 'Other'")
    conn.commit()
    print("Updated rows:", cur.rowcount)
    cur.execute("SELECT category, COUNT(*) FROM expenses GROUP BY category")
    print("Categories now in DB:", cur.fetchall())
    conn.close()

if __name__ == "__main__":
    migrate_expenses()
