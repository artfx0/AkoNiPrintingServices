"""Payment processing (Admin/Owner use case).

payment_type: DesignFee | Assurance | ProductOrder | RushFee
order_id is nullable to allow Layout-Only / walk-in design payments.
"""
from __future__ import annotations

from decimal import Decimal

PAYMENT_TYPES = ("DesignFee", "Assurance", "ProductOrder", "RushFee")
PAYMENT_METHODS = ("Cash", "GCash", "Bank Transfer", "Card", "Other")
PAYMENT_STATUSES = ("Pending", "Completed", "Refunded", "Cancelled")


def _to_decimal(value) -> Decimal:
    if value is None or value == "":
        return Decimal("0.00")
    return Decimal(str(value))


class PaymentManager:
    def __init__(self, conn):
        self.conn = conn

    def record_payment(self, processed_by_user_id: int, amount_paid,
                       payment_type: str = "ProductOrder",
                       payment_method: str = "Cash",
                       order_id: int | None = None,
                       status: str = "Completed") -> int:
        if payment_type not in PAYMENT_TYPES:
            raise ValueError(f"payment_type must be one of {PAYMENT_TYPES}")
        if payment_method not in PAYMENT_METHODS:
            raise ValueError(f"payment_method must be one of {PAYMENT_METHODS}")
        if status not in PAYMENT_STATUSES:
            raise ValueError(f"status must be one of {PAYMENT_STATUSES}")
        amount = _to_decimal(amount_paid)
        if amount <= 0:
            raise ValueError("amount_paid must be greater than zero")
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO payments (order_id, processed_by_user_id, payment_type,"
                " payment_method, amount_paid, status)"
                " VALUES (%s, %s, %s, %s, %s, %s)",
                (order_id, processed_by_user_id, payment_type, payment_method,
                 str(amount), status),
            )
            payment_id = cursor.lastrowid
            self.conn.commit()
        finally:
            cursor.close()
        if order_id is not None and status == "Completed":
            try:
                self.sync_order_status(order_id)
            except Exception:  # noqa: BLE001 — payment stands even if sync fails
                pass
        return payment_id

    def list_payments(self, order_id: int | None = None, payment_type: str = "") -> list[dict]:
        cursor = self.conn.cursor(dictionary=True)
        try:
            sql = ("SELECT p.*, CONCAT(u.first_name, ' ', u.last_name) AS processed_by"
                   " FROM payments p JOIN users u ON u.user_id = p.processed_by_user_id"
                   " WHERE 1=1")
            params: list = []
            if order_id is not None:
                sql += " AND p.order_id = %s"
                params.append(order_id)
            if payment_type:
                sql += " AND p.payment_type = %s"
                params.append(payment_type)
            sql += " ORDER BY p.payment_date DESC"
            cursor.execute(sql, params)
            return list(cursor.fetchall())
        finally:
            cursor.close()

    def list_layout_only(self) -> list[dict]:
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM payments WHERE order_id IS NULL ORDER BY payment_date DESC")
            return list(cursor.fetchall())
        finally:
            cursor.close()

    def order_balance(self, order_id: int) -> dict:
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT total_amount FROM customer_orders WHERE order_id = %s",
                           (order_id,))
            order = cursor.fetchone()
            if not order:
                raise ValueError("Order not found.")
            cursor.execute(
                "SELECT COALESCE(SUM(amount_paid), 0) AS paid FROM payments"
                " WHERE order_id = %s AND status = 'Completed'", (order_id,))
            paid = _to_decimal(cursor.fetchone()["paid"])
            total = _to_decimal(order["total_amount"])
            return {"total": total, "paid": paid, "balance": total - paid}
        finally:
            cursor.close()

    def void_payment(self, payment_id: int) -> None:
        cursor = self.conn.cursor()
        try:
            cursor.execute("UPDATE payments SET status = 'Cancelled' WHERE payment_id = %s",
                           (payment_id,))
            self.conn.commit()
        finally:
            cursor.close()

    def verify_payment(self, payment_id: int) -> dict | None:
        """Mark a Pending payment Completed; sync linked order status.

        Returns the updated payment row (dict) or None if not found.
        """
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM payments WHERE payment_id = %s", (payment_id,))
            pay = cursor.fetchone()
            if not pay:
                raise ValueError("Payment not found.")
            if pay.get("status") != "Pending":
                raise ValueError("Only Pending payments can be verified.")
            cursor.execute("UPDATE payments SET status = 'Completed' WHERE payment_id = %s",
                           (payment_id,))
            self.conn.commit()
            cursor.execute("SELECT * FROM payments WHERE payment_id = %s", (payment_id,))
            pay = cursor.fetchone()
        finally:
            cursor.close()
        if pay and pay.get("order_id") is not None:
            self.sync_order_status(pay["order_id"])
        return pay

    def get_payment(self, payment_id: int) -> dict | None:
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM payments WHERE payment_id = %s", (payment_id,))
            return cursor.fetchone()
        finally:
            cursor.close()

    def sync_order_status(self, order_id: int) -> str:
        """Set linked order to 'Paid' (balance <= 0) or 'Processing'.

        Only auto-moves orders still in an early status so manual
        Ready/Delivered/Cancelled states are never overwritten.
        Returns the resulting status.
        """
        balance = self.order_balance(order_id)
        target = "Paid" if balance["balance"] <= 0 else "Processing"
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT status FROM customer_orders WHERE order_id = %s",
                           (order_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Order not found.")
            if row.get("status") in ("Pending", "Processing", "Paid", "In Progress"):
                cursor.execute("UPDATE customer_orders SET status = %s WHERE order_id = %s",
                               (target, order_id))
                self.conn.commit()
                return target
            return row.get("status")
        finally:
            cursor.close()
