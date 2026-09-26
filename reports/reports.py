"""Reports (Admin/Owner use case): sales, payments, expenses, inventory."""
from __future__ import annotations

import csv
from decimal import Decimal


class ReportManager:
    def __init__(self, conn):
        self.conn = conn

    def sales_summary(self, start=None, end=None) -> dict:
        cur = self.conn.cursor(dictionary=True)
        try:
            filt, params = "WHERE 1=1", []
            if start:
                filt += " AND order_date >= %s"
                params.append(start)
            if end:
                filt += " AND order_date <= %s"
                params.append(end)
            cur.execute(f"SELECT COUNT(*) AS orders, COALESCE(SUM(total_amount),0) AS revenue,"
                        f" COALESCE(SUM(rush_charge),0) AS rush FROM customer_orders {filt}",
                        params)
            totals = cur.fetchone()
            cur.execute(f"SELECT status, COUNT(*) AS n, COALESCE(SUM(total_amount),0) AS revenue"
                        f" FROM customer_orders {filt} GROUP BY status", params)
            by_status = list(cur.fetchall())
            cur.execute(
                f"SELECT DATE(order_date) AS day, COUNT(*) AS orders,"
                f" COALESCE(SUM(total_amount),0) AS revenue FROM customer_orders {filt}"
                f" GROUP BY DATE(order_date) ORDER BY day", params)
            daily = list(cur.fetchall())
            return {"totals": totals, "by_status": by_status, "daily": daily}
        finally:
            cur.close()

    def payments_summary(self, start=None, end=None) -> dict:
        cur = self.conn.cursor(dictionary=True)
        try:
            filt, params = "WHERE status = 'Completed'", []
            if start:
                filt += " AND payment_date >= %s"
                params.append(start)
            if end:
                filt += " AND payment_date <= %s"
                params.append(end)
            cur.execute(f"SELECT COUNT(*) AS n, COALESCE(SUM(amount_paid),0) AS collected"
                        f" FROM payments {filt}", params)
            totals = cur.fetchone()
            cur.execute(f"SELECT payment_type, COUNT(*) AS n, COALESCE(SUM(amount_paid),0) AS total"
                        f" FROM payments {filt} GROUP BY payment_type", params)
            by_type = list(cur.fetchall())
            cur.execute(f"SELECT payment_method, COUNT(*) AS n, COALESCE(SUM(amount_paid),0) AS total"
                        f" FROM payments {filt} GROUP BY payment_method", params)
            by_method = list(cur.fetchall())
            return {"totals": totals, "by_type": by_type, "by_method": by_method}
        finally:
            cur.close()

    def expenses_summary(self, start=None, end=None) -> dict:
        cur = self.conn.cursor(dictionary=True)
        try:
            filt, params = "WHERE 1=1", []
            if start:
                filt += " AND expense_date >= %s"
                params.append(start)
            if end:
                filt += " AND expense_date <= %s"
                params.append(end)
            cur.execute(f"SELECT COUNT(*) AS n, COALESCE(SUM(amount),0) AS total"
                        f" FROM expenses {filt}", params)
            totals = cur.fetchone()
            cur.execute(f"SELECT category, COUNT(*) AS n, COALESCE(SUM(amount),0) AS total"
                        f" FROM expenses {filt} GROUP BY category ORDER BY total DESC", params)
            return {"totals": totals, "by_category": list(cur.fetchall())}
        finally:
            cur.close()

    def profit_loss(self, start=None, end=None) -> dict:
        sales = self.sales_summary(start, end)["totals"]
        pay = self.payments_summary(start, end)["totals"]
        exp = self.expenses_summary(start, end)["totals"]
        revenue = Decimal(str(pay.get("collected", 0)))
        expenses = Decimal(str(exp.get("total", 0)))
        return {"revenue_collected": revenue, "expenses": expenses,
                "profit": revenue - expenses,
                "orders": sales.get("orders", 0),
                "order_revenue": Decimal(str(sales.get("revenue", 0)))}

    def inventory_status(self) -> list[dict]:
        cur = self.conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT *, (current_stock_qty <= low_stock_threshold) AS is_low"
                        " FROM materials ORDER BY material_name")
            return list(cur.fetchall())
        finally:
            cur.close()

    def unpaid_orders(self) -> list[dict]:
        cur = self.conn.cursor(dictionary=True)
        try:
            cur.execute(
                "SELECT o.order_id, CONCAT(c.first_name,' ',c.last_name) AS customer,"
                " o.total_amount, COALESCE(SUM(CASE WHEN p.status='Completed'"
                " THEN p.amount_paid ELSE 0 END),0) AS paid,"
                " (o.total_amount - COALESCE(SUM(CASE WHEN p.status='Completed'"
                " THEN p.amount_paid ELSE 0 END),0)) AS balance, o.status"
                " FROM customer_orders o JOIN customers c ON c.customer_id=o.customer_id"
                " LEFT JOIN payments p ON p.order_id=o.order_id"
                " GROUP BY o.order_id HAVING balance > 0 ORDER BY o.order_date DESC")
            return list(cur.fetchall())
        finally:
            cur.close()

    @staticmethod
    def export_to_csv(rows: list[dict], headers: list[str], path: str) -> str:
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        return path
