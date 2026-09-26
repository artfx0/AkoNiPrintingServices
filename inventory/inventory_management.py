"""Inventory management — shared Admin/Owner + Staff use case.

Materials + StockMovement (IN / OUT / ADJUSTMENT).
Stock updates are transactional: movement row + materials.current_stock_qty.
Optional links: order_item_id (consumption), expense_id (purchase).
"""
from __future__ import annotations

MOVEMENT_TYPES = ("IN", "OUT", "ADJUSTMENT")


class MaterialManager:
    def __init__(self, conn):
        self.conn = conn

    def create_material(self, material_name, unit_of_measure="pcs",
                        current_stock_qty=0, low_stock_threshold=10,
                        cost_per_unit=0) -> int:
        if not material_name:
            raise ValueError("material_name is required")
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO materials (material_name, unit_of_measure, current_stock_qty,"
                " low_stock_threshold, cost_per_unit)"
                " VALUES (%s, %s, %s, %s, %s)",
                (material_name.strip(), unit_of_measure.strip() or "pcs",
                 int(current_stock_qty), int(low_stock_threshold), str(cost_per_unit)),
            )
            self.conn.commit()
            return cursor.lastrowid
        finally:
            cursor.close()

    def list_materials(self, low_stock_only: bool = False, search: str = "") -> list[dict]:
        cursor = self.conn.cursor(dictionary=True)
        try:
            sql = "SELECT * FROM materials WHERE 1=1"
            params: list = []
            if search.strip():
                sql += " AND material_name LIKE %s"
                params.append(f"%{search.strip()}%")
            if low_stock_only:
                sql += " AND current_stock_qty <= low_stock_threshold"
            sql += " ORDER BY material_name"
            cursor.execute(sql, params)
            return list(cursor.fetchall())
        finally:
            cursor.close()

    def get_material(self, material_id: int) -> dict | None:
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM materials WHERE material_id = %s", (material_id,))
            return cursor.fetchone()
        finally:
            cursor.close()

    def update_material(self, material_id: int, **fields) -> None:
        allowed = {"material_name", "unit_of_measure", "low_stock_threshold", "cost_per_unit"}
        sets, params = [], []
        for key, value in fields.items():
            if key in allowed and value is not None:
                sets.append(f"{key} = %s")
                params.append(value)
        if not sets:
            return
        params.append(material_id)
        cursor = self.conn.cursor()
        try:
            cursor.execute(f"UPDATE materials SET {', '.join(sets)} WHERE material_id = %s",
                           params)
            self.conn.commit()
        finally:
            cursor.close()

    def delete_material(self, material_id: int) -> None:
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM stock_movements WHERE material_id = %s",
                           (material_id,))
            (n,) = cursor.fetchone()
            if n:
                raise ValueError("Cannot delete material with stock movements.")
            cursor.execute("DELETE FROM materials WHERE material_id = %s", (material_id,))
            self.conn.commit()
        finally:
            cursor.close()


class StockMovementManager:
    def __init__(self, conn):
        self.conn = conn

    def record_movement(self, material_id: int, recorded_by_user_id: int,
                        movement_type: str, quantity: int, reason: str = "",
                        order_item_id: int | None = None,
                        expense_id: int | None = None) -> int:
        if movement_type not in MOVEMENT_TYPES:
            raise ValueError(f"movement_type must be one of {MOVEMENT_TYPES}")
        quantity = int(quantity)
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT current_stock_qty FROM materials WHERE material_id = %s",
                           (material_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Material not found.")
            current = int(row["current_stock_qty"])
            if movement_type == "IN":
                new_qty = current + quantity
            elif movement_type == "OUT":
                if quantity > current:
                    raise ValueError(
                        f"Insufficient stock ({current} available, {quantity} requested).")
                new_qty = current - quantity
            else:  # ADJUSTMENT: quantity is the corrected on-hand value
                new_qty = quantity
            cursor.execute(
                "INSERT INTO stock_movements (material_id, recorded_by_user_id, movement_type,"
                " quantity, reason, order_item_id, expense_id)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (material_id, recorded_by_user_id, movement_type, quantity,
                 reason.strip() or None, order_item_id, expense_id),
            )
            movement_id = cursor.lastrowid
            cursor.execute("UPDATE materials SET current_stock_qty = %s WHERE material_id = %s",
                           (new_qty, material_id))
            self.conn.commit()
            return movement_id
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    def list_movements(self, material_id: int | None = None, limit: int = 200) -> list[dict]:
        cursor = self.conn.cursor(dictionary=True)
        try:
            sql = (
                "SELECT m.*, mat.material_name,"
                " CONCAT(u.first_name, ' ', u.last_name) AS recorded_by"
                " FROM stock_movements m"
                " JOIN materials mat ON mat.material_id = m.material_id"
                " JOIN users u ON u.user_id = m.recorded_by_user_id"
                " WHERE 1=1"
            )
            params: list = []
            if material_id is not None:
                sql += " AND m.material_id = %s"
                params.append(material_id)
            sql += " ORDER BY m.movement_date DESC LIMIT %s"
            params.append(int(limit))
            cursor.execute(sql, params)
            return list(cursor.fetchall())
        finally:
            cursor.close()
