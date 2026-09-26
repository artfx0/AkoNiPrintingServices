"""Customer records management (Admin/Owner use case)."""
from __future__ import annotations


class CustomerManager:
    def __init__(self, conn):
        self.conn = conn

    def create_customer(self, first_name, last_name, contact_number="",
                        email_address="", address="") -> int:
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
        cursor = self.conn.cursor(dictionary=True)
        try:
            if search.strip():
                like = f"%{search.strip()}%"
                cursor.execute(
                    "SELECT * FROM customers WHERE first_name LIKE %s OR last_name LIKE %s"
                    " OR contact_number LIKE %s OR email_address LIKE %s"
                    " ORDER BY last_name, first_name",
                    (like, like, like, like),
                )
            else:
                cursor.execute("SELECT * FROM customers ORDER BY last_name, first_name")
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

    def delete_customer(self, customer_id: int) -> None:
        """Delete only if the customer has no orders (FK RESTRICT)."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM customer_orders WHERE customer_id = %s",
                           (customer_id,))
            (n,) = cursor.fetchone()
            if n:
                raise ValueError("Cannot delete customer with existing orders.")
            cursor.execute("DELETE FROM customers WHERE customer_id = %s", (customer_id,))
            self.conn.commit()
        finally:
            cursor.close()

    def order_history(self, customer_id: int) -> list[dict]:
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM customer_orders WHERE customer_id = %s ORDER BY order_date DESC",
                (customer_id,),
            )
            return list(cursor.fetchall())
        finally:
            cursor.close()
