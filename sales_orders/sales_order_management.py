"""Sales and orders management (Admin/Owner use case).

Business rules:
  total_amount = SUM(quantity * unit_price - discount) + rush_charge
                 - P500 assurance deduction (when is_design_fee_deducted=True)
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

DESIGN_ASSURANCE_DEDUCTION = Decimal("500.00")

ORDER_TYPES = ("LayoutOnly", "ProductOrder")
ORDER_STATUSES = ("Pending", "Processing", "Paid", "In Progress", "Ready", "Delivered", "Cancelled")


def _to_decimal(value) -> Decimal:
    if value is None or value == "":
        return Decimal("0.00")
    return Decimal(str(value))


def compute_totals(items: list[dict], rush_charge=0, is_design_fee_deducted: bool = False) -> Decimal:
    subtotal = Decimal("0.00")
    for item in items:
        qty = _to_decimal(item.get("quantity", 1))
        price = _to_decimal(item.get("unit_price", 0))
        discount = _to_decimal(item.get("discount", 0))
        subtotal += qty * price - discount
    total = subtotal + _to_decimal(rush_charge)
    if is_design_fee_deducted:
        total -= DESIGN_ASSURANCE_DEDUCTION
    return max(total, Decimal("0.00"))


class OrderManager:
    def __init__(self, conn):
        self.conn = conn

    # -- create (order + items atomically) --
    def create_order(self, customer_id: int, recorded_by_user_id: int,
                     order_type: str = "ProductOrder",
                     expected_delivery_date=None,
                     delivery_address: str = "",
                     rush_charge=0,
                     is_design_fee_deducted: bool = False,
                     items: list[dict] | None = None) -> int:
        if not items:
            raise ValueError("An order must contain at least one item.")
        if order_type not in ORDER_TYPES:
            raise ValueError(f"order_type must be one of {ORDER_TYPES}")
        total = compute_totals(items, rush_charge, is_design_fee_deducted)
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO customer_orders (customer_id, recorded_by_user_id, order_type,"
                " expected_delivery_date, status, rush_charge, total_amount,"
                " delivery_address, is_design_fee_deducted)"
                " VALUES (%s, %s, %s, %s, 'Pending', %s, %s, %s, %s)",
                (customer_id, recorded_by_user_id, order_type, expected_delivery_date,
                 str(_to_decimal(rush_charge)), str(total),
                 (delivery_address or "").strip() or None, bool(is_design_fee_deducted)),
            )
            order_id = cursor.lastrowid
            for item in items:
                cursor.execute(
                    "INSERT INTO order_items (order_id, packaging_type, finish_type, size,"
                    " quantity, unit_price, discount, design_file_path)"
                    " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (order_id, item.get("packaging_type"), item.get("finish_type"),
                     item.get("size"), int(item.get("quantity", 1)),
                     str(_to_decimal(item.get("unit_price", 0))),
                     str(_to_decimal(item.get("discount", 0))),
                     item.get("design_file_path")),
                )
            self.conn.commit()
            return order_id
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    # -- read --
    def list_orders(self, status: str = "", customer_search: str = "") -> list[dict]:
        cursor = self.conn.cursor(dictionary=True)
        try:
            sql = (
                "SELECT o.*, CONCAT(c.first_name, ' ', c.last_name) AS customer_name"
                " FROM customer_orders o JOIN customers c ON c.customer_id = o.customer_id"
                " WHERE 1=1"
            )
            params: list = []
            if status:
                sql += " AND o.status = %s"
                params.append(status)
            if customer_search.strip():
                sql += " AND (c.first_name LIKE %s OR c.last_name LIKE %s)"
                like = f"%{customer_search.strip()}%"
                params.extend([like, like])
            sql += " ORDER BY o.order_date DESC"
            cursor.execute(sql, params)
            return list(cursor.fetchall())
        finally:
            cursor.close()

    def get_order(self, order_id: int) -> dict | None:
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM customer_orders WHERE order_id = %s", (order_id,))
            order = cursor.fetchone()
            if not order:
                return None
            cursor.execute("SELECT * FROM order_items WHERE order_id = %s", (order_id,))
            order["items"] = list(cursor.fetchall())
            cursor.execute("SELECT * FROM payments WHERE order_id = %s ORDER BY payment_date",
                           (order_id,))
            order["payments"] = list(cursor.fetchall())
            paid = sum((_to_decimal(p["amount_paid"]) for p in order["payments"]),
                       Decimal("0.00"))
            order["amount_paid"] = paid
            order["balance"] = _to_decimal(order["total_amount"]) - paid
            return order
        finally:
            cursor.close()

    # -- update --
    def recalc_total(self, order_id: int) -> Decimal:
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM customer_orders WHERE order_id = %s", (order_id,))
            order = cursor.fetchone()
            cursor.execute("SELECT * FROM order_items WHERE order_id = %s", (order_id,))
            items = list(cursor.fetchall())
            total = compute_totals(items, order["rush_charge"],
                                   bool(order["is_design_fee_deducted"]))
            cursor2 = self.conn.cursor()
            try:
                cursor2.execute("UPDATE customer_orders SET total_amount = %s WHERE order_id = %s",
                                (str(total), order_id))
            finally:
                cursor2.close()
            self.conn.commit()
            return total
        finally:
            cursor.close()

    def update_status(self, order_id: int, status: str) -> None:
        if status not in ORDER_STATUSES:
            raise ValueError(f"status must be one of {ORDER_STATUSES}")
        cursor = self.conn.cursor()
        try:
            if status == "Delivered":
                cursor.execute(
                    "UPDATE customer_orders SET status=%s, actual_delivery_date=%s WHERE order_id=%s",
                    (status, datetime.now(), order_id),
                )
            else:
                cursor.execute("UPDATE customer_orders SET status=%s WHERE order_id=%s",
                               (status, order_id))
            self.conn.commit()
        finally:
            cursor.close()

    def update_order(self, order_id: int, rush_charge=None, is_design_fee_deducted=None,
                     expected_delivery_date=None, delivery_address=None,
                     order_type: str | None = None) -> Decimal:
        cursor = self.conn.cursor()
        try:
            sets, params = [], []
            if rush_charge is not None:
                sets.append("rush_charge = %s")
                params.append(str(_to_decimal(rush_charge)))
            if is_design_fee_deducted is not None:
                sets.append("is_design_fee_deducted = %s")
                params.append(bool(is_design_fee_deducted))
            if expected_delivery_date is not None:
                sets.append("expected_delivery_date = %s")
                params.append(expected_delivery_date)
            if delivery_address is not None:
                sets.append("delivery_address = %s")
                params.append(delivery_address)
            if order_type is not None:
                if order_type not in ORDER_TYPES:
                    raise ValueError(f"order_type must be one of {ORDER_TYPES}")
                sets.append("order_type = %s")
                params.append(order_type)
            if sets:
                params.append(order_id)
                cursor.execute(f"UPDATE customer_orders SET {', '.join(sets)} WHERE order_id = %s",
                               params)
            self.conn.commit()
        finally:
            cursor.close()
        return self.recalc_total(order_id)

    def add_item(self, order_id: int, item: dict) -> Decimal:
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO order_items (order_id, packaging_type, finish_type, size,"
                " quantity, unit_price, discount, design_file_path)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (order_id, item.get("packaging_type"), item.get("finish_type"),
                 item.get("size"), int(item.get("quantity", 1)),
                 str(_to_decimal(item.get("unit_price", 0))),
                 str(_to_decimal(item.get("discount", 0))),
                 item.get("design_file_path")),
            )
            self.conn.commit()
        finally:
            cursor.close()
        return self.recalc_total(order_id)

    def remove_item(self, order_item_id: int) -> Decimal:
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT order_id FROM order_items WHERE order_item_id = %s",
                           (order_item_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Order item not found.")
            order_id = row["order_id"]
            cursor.execute("SELECT COUNT(*) AS n FROM order_items WHERE order_id = %s",
                           (order_id,))
            if cursor.fetchone()["n"] <= 1:
                raise ValueError("An order must keep at least one item.")
        finally:
            cursor.close()
        cursor = self.conn.cursor()
        try:
            cursor.execute("DELETE FROM order_items WHERE order_item_id = %s", (order_item_id,))
            self.conn.commit()
        finally:
            cursor.close()
        return self.recalc_total(order_id)
