"""Expense management (Admin/Owner use case)."""
from __future__ import annotations

from decimal import Decimal

EXPENSE_CATEGORIES = (
    "Labor", "Materials", "Miscellaneous", "Utility",
)


class ExpenseManager:
    def __init__(self, conn):
        self.conn = conn

    def create_expense(self, category: str, amount, description: str = "",
                       recorded_by_user_id: int | None = None,
                       expense_date=None) -> int:
        if not category:
            raise ValueError("category is required")
        category = category.strip()
        if category not in EXPENSE_CATEGORIES:
            raise ValueError(f"category must be one of {EXPENSE_CATEGORIES}")
        value = Decimal(str(amount))
        if value <= 0:
            raise ValueError("amount must be greater than zero")
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO expenses (recorded_by_user_id, category, amount, expense_date, description)"
                " VALUES (%s, %s, %s, COALESCE(%s, NOW()), %s)",
                (recorded_by_user_id, category, str(value), expense_date,
                 description.strip() or None),
            )
            self.conn.commit()
            return cursor.lastrowid
        finally:
            cursor.close()

    def list_expenses(self, category: str = "", start=None, end=None) -> list[dict]:
        cursor = self.conn.cursor(dictionary=True)
        try:
            sql = ("SELECT e.*, CONCAT(COALESCE(u.first_name,''), ' ', COALESCE(u.last_name,''))"
                   " AS recorded_by FROM expenses e"
                   " LEFT JOIN users u ON u.user_id = e.recorded_by_user_id WHERE 1=1")
            params: list = []
            if category:
                sql += " AND e.category = %s"
                params.append(category)
            if start:
                sql += " AND e.expense_date >= %s"
                params.append(start)
            if end:
                sql += " AND e.expense_date <= %s"
                params.append(end)
            sql += " ORDER BY e.expense_date DESC"
            cursor.execute(sql, params)
            return list(cursor.fetchall())
        finally:
            cursor.close()

    def count_expenses_by_category(self, start=None, end=None) -> dict[str, int]:
        """Count total expenses for each category."""
        cursor = self.conn.cursor()
        try:
            sql = "SELECT category, COUNT(*) FROM expenses WHERE 1=1"
            params: list = []
            if start:
                sql += " AND expense_date >= %s"
                params.append(start)
            if end:
                sql += " AND expense_date <= %s"
                params.append(end)
            sql += " GROUP BY category"
            cursor.execute(sql, params)
            counts = {c: 0 for c in EXPENSE_CATEGORIES}
            for cat, count in cursor.fetchall():
                if cat in counts:
                    counts[cat] = int(count)
            return counts
        finally:
            cursor.close()

    def update_expense(self, expense_id: int, **fields) -> None:
        allowed = {"category", "amount", "description", "expense_date"}
        sets, params = [], []
        for key, value in fields.items():
            if key in allowed and value is not None:
                if key == "category":
                    value = str(value).strip()
                    if value not in EXPENSE_CATEGORIES:
                        raise ValueError(f"category must be one of {EXPENSE_CATEGORIES}")
                if key == "amount":
                    value = str(Decimal(str(value)))
                sets.append(f"{key} = %s")
                params.append(value)
        if not sets:
            return
        params.append(expense_id)
        cursor = self.conn.cursor()
        try:
            cursor.execute(f"UPDATE expenses SET {', '.join(sets)} WHERE expense_id = %s", params)
            self.conn.commit()
        finally:
            cursor.close()

    def link_movement(self, expense_id: int, movement_id: int) -> None:
        """Link a Stock IN movement to this expense (financial ↔ inventory sync)."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT movement_id FROM stock_movements WHERE movement_id = %s",
                           (movement_id,))
            if not cursor.fetchone():
                raise ValueError("Stock movement not found.")
            cursor.execute("UPDATE stock_movements SET expense_id = %s WHERE movement_id = %s",
                           (expense_id, movement_id))
            self.conn.commit()
        finally:
            cursor.close()

    def delete_expense(self, expense_id: int) -> None:
        cursor = self.conn.cursor()
        try:
            cursor.execute("UPDATE stock_movements SET expense_id = NULL WHERE expense_id = %s",
                           (expense_id,))
            cursor.execute("DELETE FROM expenses WHERE expense_id = %s", (expense_id,))
            self.conn.commit()
        finally:
            cursor.close()

    def total(self, start=None, end=None) -> Decimal:
        cursor = self.conn.cursor()
        try:
            sql = "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE 1=1"
            params: list = []
            if start:
                sql += " AND expense_date >= %s"
                params.append(start)
            if end:
                sql += " AND expense_date <= %s"
                params.append(end)
            cursor.execute(sql, params)
            (value,) = cursor.fetchone()
            return Decimal(str(value))
        finally:
            cursor.close()
