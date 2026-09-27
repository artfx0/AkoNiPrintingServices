"""Customer records management (Admin/Owner use case)."""
from __future__ import annotations

from decimal import Decimal


class CustomerManager:
    def __init__(self, conn):
        self.conn = conn

    def create_customer(self, first_name: str, last_name: str, contact_number: str = "",
                        email_address: str = "", address: str = "") -> int:
        if not first_name or not last_name:
            raise ValueError("first_name and last_name are required")
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO customers (first_name, last_name, contact_number, email_address, address)"
                " VALUES (%s, %s, %s, %s, %s)",
                (first_name.strip(), last_name.strip(),
                 (contact_number or "").strip() or None,
                 (email_address or "").strip() or None,
                 (address or "").strip() or None),
            )
            self.conn.commit()
            return cursor.lastrowid
        finally:
            cursor.close()

    def list_customers(self, search: str = "") -> list[dict]:
        """Fetch customer records sorted newest first (ORDER BY created_at DESC)."""
        cursor = self.conn.cursor(dictionary=True)
        try:
            if search.strip():
                like = f"%{search.strip()}%"
                cursor.execute(
                    "SELECT * FROM customers WHERE first_name LIKE %s OR last_name LIKE %s"
                    " OR contact_number LIKE %s OR email_address LIKE %s"
                    " ORDER BY created_at DESC",
                    (like, like, like, like),
                )
            else:
                cursor.execute("SELECT * FROM customers ORDER BY created_at DESC")
            return list(cursor.fetchall())
        finally:
            cursor.close()

    def get_customer(self, customer_id: int) -> dict | None:
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM customers WHERE customer_id = %s", (customer_id,))
            return cursor.fetchone()
        finally:
            cursor.close()

    def update_customer(self, customer_id: int, **fields) -> None:
        allowed = {"first_name", "last_name", "contact_number", "email_address", "address"}
        sets, params = [], []
        for key, value in fields.items():
            if key in allowed and value is not None:
                sets.append(f"{key} = %s")
                params.append(value.strip() if isinstance(value, str) else value)
        if not sets:
            return
        params.append(customer_id)
        cursor = self.conn.cursor()
        try:
            cursor.execute(f"UPDATE customers SET {', '.join(sets)} WHERE customer_id = %s", params)
            self.conn.commit()
        finally:
            cursor.close()

    def count_orders(self, customer_id: int) -> int:
        """Check order count for deletion validation."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM customer_orders WHERE customer_id = %s", (customer_id,))
            (count,) = cursor.fetchone()
            return int(count or 0)
        finally:
            cursor.close()

    def delete_customer(self, customer_id: int) -> None:
        """Delete only if the customer has no orders (FK RESTRICT check)."""
        n = self.count_orders(customer_id)
        if n > 0:
            raise ValueError("Cannot delete. Customer has existing orders.")
        cursor = self.conn.cursor()
        try:
            cursor.execute("DELETE FROM customers WHERE customer_id = %s", (customer_id,))
            self.conn.commit()
        finally:
            cursor.close()

    def order_history(self, customer_id: int) -> list[dict]:
        """Fetch customer orders with computed paid amounts and outstanding balance."""
        cursor = self.conn.cursor(dictionary=True)
        try:
            sql = """
                SELECT o.order_id, o.order_type, o.order_date, o.status, o.total_amount,
                       COALESCE(SUM(p.amount_paid), 0.00) AS paid_amount
                FROM customer_orders o
                LEFT JOIN payments p ON p.order_id = o.order_id
                WHERE o.customer_id = %s
                GROUP BY o.order_id, o.order_type, o.order_date, o.status, o.total_amount
                ORDER BY o.order_date DESC
            """
            cursor.execute(sql, (customer_id,))
            rows = list(cursor.fetchall())
            for r in rows:
                total = Decimal(str(r.get("total_amount") or "0.00"))
                paid = Decimal(str(r.get("paid_amount") or "0.00"))
                r["balance"] = max(Decimal("0.00"), total - paid)
            return rows
        finally:
            cursor.close()

    def customer_total_spent(self, customer_id: int) -> Decimal:
        """Aggregate total order spend for a customer."""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "SELECT COALESCE(SUM(total_amount), 0.00) FROM customer_orders WHERE customer_id = %s",
                (customer_id,),
            )
            (total,) = cursor.fetchone()
            return Decimal(str(total or "0.00"))
        finally:
            cursor.close()

