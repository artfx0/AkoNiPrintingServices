"""Reports (Admin/Owner use case): sales, payments, expenses, inventory."""
from __future__ import annotations

import csv
from datetime import date, datetime
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

    def get_kpis(self, start: str | None = None, end: str | None = None) -> dict:
        cur = self.conn.cursor(dictionary=True)
        try:
            order_filt = "WHERE 1=1"
            order_params = []
            exp_filt = "WHERE 1=1"
            exp_params = []

            if start:
                order_filt += " AND order_date >= %s"
                order_params.append(start)
                exp_filt += " AND expense_date >= %s"
                exp_params.append(start)
            if end:
                end_str = f"{end} 23:59:59" if len(end) == 10 else end
                order_filt += " AND order_date <= %s"
                order_params.append(end_str)
                exp_filt += " AND expense_date <= %s"
                exp_params.append(end_str)

            cur.execute(
                f"SELECT COALESCE(SUM(total_amount), 0) AS total_sales FROM customer_orders {order_filt}",
                order_params
            )
            total_sales = Decimal(str(cur.fetchone()["total_sales"]))

            cur.execute(
                f"SELECT COALESCE(SUM(amount), 0) AS total_expenses FROM expenses {exp_filt}",
                exp_params
            )
            total_expenses = Decimal(str(cur.fetchone()["total_expenses"]))

            cur.execute("SELECT COUNT(*) AS pending_orders FROM customer_orders WHERE status = 'Pending'")
            pending_orders = cur.fetchone()["pending_orders"]

            net_income = total_sales - total_expenses

            return {
                "total_sales": total_sales,
                "total_expenses": total_expenses,
                "net_income": net_income,
                "pending_orders": pending_orders,
            }
        finally:
            cur.close()

    def get_monthly_sales_trend(self, num_months: int = 6) -> list[dict]:
        today = date.today()
        months = []
        y, m = today.year, today.month
        for _ in range(num_months):
            ym = f"{y:04d}-{m:02d}"
            label = date(y, m, 1).strftime("%b %Y")
            months.append({"ym": ym, "label": label, "amount": Decimal("0.00")})
            m -= 1
            if m == 0:
                m = 12
                y -= 1
        months = list(reversed(months))
        months_dict = {item["ym"]: item for item in months}

        cur = self.conn.cursor(dictionary=True)
        try:
            earliest_ym = months[0]["ym"] + "-01"
            cur.execute("""
                SELECT DATE_FORMAT(order_date, '%Y-%m') AS ym,
                       COALESCE(SUM(total_amount), 0) AS total_sales
                FROM customer_orders
                WHERE order_date >= %s
                GROUP BY ym
                ORDER BY ym ASC
            """, (earliest_ym,))
            for row in cur.fetchall():
                ym = row["ym"]
                if ym in months_dict:
                    months_dict[ym]["amount"] = Decimal(str(row["total_sales"]))
            return months
        finally:
            cur.close()

    def get_expenses_breakdown(self, start: str | None = None, end: str | None = None) -> list[dict]:
        cur = self.conn.cursor(dictionary=True)
        try:
            filt = "WHERE 1=1"
            params = []
            if start:
                filt += " AND expense_date >= %s"
                params.append(start)
            if end:
                end_str = f"{end} 23:59:59" if len(end) == 10 else end
                filt += " AND expense_date <= %s"
                params.append(end_str)
            cur.execute(f"""
                SELECT category, COALESCE(SUM(amount), 0) AS total
                FROM expenses
                {filt}
                GROUP BY category
                ORDER BY total DESC
            """, params)
            return [
                {"category": r["category"], "total": Decimal(str(r["total"]))}
                for r in cur.fetchall()
            ]
        finally:
            cur.close()

    def get_top_materials_valuation(self, limit: int = 5) -> list[dict]:
        cur = self.conn.cursor(dictionary=True)
        try:
            cur.execute("""
                SELECT material_name, current_stock_qty, cost_per_unit,
                       (current_stock_qty * cost_per_unit) AS total_val
                FROM materials
                ORDER BY total_val DESC
                LIMIT %s
            """, (limit,))
            return [
                {
                    "material_name": r["material_name"],
                    "current_stock_qty": r["current_stock_qty"],
                    "cost_per_unit": Decimal(str(r["cost_per_unit"])),
                    "total_val": Decimal(str(r["total_val"])),
                }
                for r in cur.fetchall()
            ]
        finally:
            cur.close()

    def get_accounts_receivable_monthly(self, num_months: int = 6) -> list[dict]:
        today = date.today()
        months = []
        y, m = today.year, today.month
        for _ in range(num_months):
            ym = f"{y:04d}-{m:02d}"
            label = date(y, m, 1).strftime("%b %Y")
            months.append({
                "ym": ym,
                "label": label,
                "paid": Decimal("0.00"),
                "unpaid": Decimal("0.00"),
            })
            m -= 1
            if m == 0:
                m = 12
                y -= 1
        months = list(reversed(months))
        months_dict = {item["ym"]: item for item in months}

        cur = self.conn.cursor(dictionary=True)
        try:
            earliest_ym = months[0]["ym"] + "-01"
            cur.execute("""
                SELECT DATE_FORMAT(o.order_date, '%Y-%m') AS ym,
                       COALESCE(SUM(LEAST(COALESCE(p.paid, 0), o.total_amount)), 0) AS paid_amount,
                       COALESCE(SUM(GREATEST(0, o.total_amount - COALESCE(p.paid, 0))), 0) AS unpaid_amount
                FROM customer_orders o
                LEFT JOIN (
                    SELECT order_id, SUM(amount_paid) AS paid
                    FROM payments
                    WHERE status = 'Completed'
                    GROUP BY order_id
                ) p ON p.order_id = o.order_id
                WHERE o.order_date >= %s
                GROUP BY ym
                ORDER BY ym ASC
            """, (earliest_ym,))
            for row in cur.fetchall():
                ym = row["ym"]
                if ym in months_dict:
                    months_dict[ym]["paid"] = Decimal(str(row["paid_amount"]))
                    months_dict[ym]["unpaid"] = Decimal(str(row["unpaid_amount"]))
            return months
        finally:
            cur.close()

    def get_detailed_transactions(self, start: str | None = None, end: str | None = None) -> list[dict]:
        cur = self.conn.cursor(dictionary=True)
        try:
            order_filt = "WHERE 1=1"
            order_params = []
            exp_filt = "WHERE 1=1"
            exp_params = []

            if start:
                order_filt += " AND o.order_date >= %s"
                order_params.append(start)
                exp_filt += " AND e.expense_date >= %s"
                exp_params.append(start)
            if end:
                end_str = f"{end} 23:59:59" if len(end) == 10 else end
                order_filt += " AND o.order_date <= %s"
                order_params.append(end_str)
                exp_filt += " AND e.expense_date <= %s"
                exp_params.append(end_str)

            query = f"""
                SELECT 
                    o.order_id AS raw_id,
                    o.order_date AS tx_date,
                    CONCAT('ORD-', LPAD(o.order_id, 4, '0')) AS reference_no,
                    CONCAT(c.first_name, ' ', c.last_name) AS entity_name,
                    CONCAT(o.order_type, ' (', o.status, ')') AS description,
                    'Sales' AS category,
                    o.total_amount AS amount,
                    'sales' AS record_type,
                    DATE_FORMAT(o.order_date, '%Y-%m') AS ym,
                    DATE_FORMAT(o.order_date, '%b %Y') AS month_label
                FROM customer_orders o
                JOIN customers c ON c.customer_id = o.customer_id
                {order_filt}

                UNION ALL

                SELECT 
                    e.expense_id AS raw_id,
                    e.expense_date AS tx_date,
                    CONCAT('EXP-', LPAD(e.expense_id, 4, '0')) AS reference_no,
                    COALESCE(CONCAT(u.first_name, ' ', u.last_name), 'System Admin') AS entity_name,
                    e.description AS description,
                    e.category AS category,
                    e.amount AS amount,
                    'expense' AS record_type,
                    DATE_FORMAT(e.expense_date, '%Y-%m') AS ym,
                    DATE_FORMAT(e.expense_date, '%b %Y') AS month_label
                FROM expenses e
                LEFT JOIN users u ON u.user_id = e.recorded_by_user_id
                {exp_filt}

                ORDER BY tx_date DESC
            """
            cur.execute(query, order_params + exp_params)
            rows = cur.fetchall()
            for r in rows:
                r["amount"] = Decimal(str(r["amount"]))
            return rows
        finally:
            cur.close()

