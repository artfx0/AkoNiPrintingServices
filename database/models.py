"""MySQL DDL matching the approved ERD.

Table mapping (ERD entity -> physical table):
  Customer      -> customers
  User          -> users          ('user' is reserved-adjacent, so pluralized)
  CustomerOrder -> customer_orders
  OrderItem     -> order_items
  Payment       -> payments
  Material      -> materials
  StockMovement -> stock_movements
  Expense       -> expenses

Includes recommended additions:
  customer_orders.is_design_fee_deducted
  stock_movements.order_item_id / expense_id (both nullable)
  payments.order_id nullable, expenses.recorded_by_user_id nullable
"""
from __future__ import annotations

CREATE_TABLES_SQL = [
    # --- User ---
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        first_name VARCHAR(50) NOT NULL,
        last_name VARCHAR(50) NOT NULL,
        role ENUM('Admin', 'Staff') NOT NULL DEFAULT 'Staff',
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB
    """,
    # --- Customer ---
    """
    CREATE TABLE IF NOT EXISTS customers (
        customer_id INT AUTO_INCREMENT PRIMARY KEY,
        first_name VARCHAR(50) NOT NULL,
        last_name VARCHAR(50) NOT NULL,
        contact_number VARCHAR(20) NULL,
        email_address VARCHAR(100) NULL,
        address VARCHAR(255) NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_customer_name (last_name, first_name)
    ) ENGINE=InnoDB
    """,
    # --- Material ---
    """
    CREATE TABLE IF NOT EXISTS materials (
        material_id INT AUTO_INCREMENT PRIMARY KEY,
        material_name VARCHAR(100) NOT NULL,
        unit_of_measure VARCHAR(20) NOT NULL DEFAULT 'pcs',
        current_stock_qty INT NOT NULL DEFAULT 0,
        low_stock_threshold INT NOT NULL DEFAULT 10,
        cost_per_unit DECIMAL(10,2) NOT NULL DEFAULT 0.00
    ) ENGINE=InnoDB
    """,
    # --- Expense (before stock_movements so FK can reference it) ---
    """
    CREATE TABLE IF NOT EXISTS expenses (
        expense_id INT AUTO_INCREMENT PRIMARY KEY,
        recorded_by_user_id INT NULL,
        category ENUM('Labor', 'Materials', 'Miscellaneous', 'Utility', 'Other') NOT NULL,
        amount DECIMAL(10,2) NOT NULL,
        expense_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        description VARCHAR(255) NULL,
        CONSTRAINT fk_expense_user FOREIGN KEY (recorded_by_user_id)
            REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE SET NULL,
        INDEX idx_expense_date (expense_date),
        INDEX idx_expense_category (category)
    ) ENGINE=InnoDB
    """,
    # --- CustomerOrder ---
    """
    CREATE TABLE IF NOT EXISTS customer_orders (
        order_id INT AUTO_INCREMENT PRIMARY KEY,
        customer_id INT NOT NULL,
        recorded_by_user_id INT NOT NULL,
        order_type ENUM('LayoutOnly', 'ProductOrder') NOT NULL DEFAULT 'ProductOrder',
        order_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        expected_delivery_date DATETIME NULL,
        actual_delivery_date DATETIME NULL,
        status VARCHAR(30) NOT NULL DEFAULT 'Pending',
        rush_charge DECIMAL(10,2) NOT NULL DEFAULT 0.00,
        total_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
        delivery_address VARCHAR(255) NULL,
        is_design_fee_deducted BOOLEAN NOT NULL DEFAULT FALSE,
        CONSTRAINT fk_order_customer FOREIGN KEY (customer_id)
            REFERENCES customers(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT,
        CONSTRAINT fk_order_user FOREIGN KEY (recorded_by_user_id)
            REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
        INDEX idx_order_customer (customer_id),
        INDEX idx_order_status (status),
        INDEX idx_order_date (order_date)
    ) ENGINE=InnoDB
    """,
    # --- OrderItem ---
    """
    CREATE TABLE IF NOT EXISTS order_items (
        order_item_id INT AUTO_INCREMENT PRIMARY KEY,
        order_id INT NOT NULL,
        packaging_type VARCHAR(50) NULL,
        finish_type VARCHAR(50) NULL,
        size VARCHAR(50) NULL,
        quantity INT NOT NULL DEFAULT 1,
        unit_price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
        discount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
        design_file_path VARCHAR(255) NULL,
        CONSTRAINT fk_item_order FOREIGN KEY (order_id)
            REFERENCES customer_orders(order_id) ON UPDATE CASCADE ON DELETE CASCADE,
        INDEX idx_item_order (order_id)
    ) ENGINE=InnoDB
    """,
    # --- Payment (order_id nullable for Layout-Only payments) ---
    """
    CREATE TABLE IF NOT EXISTS payments (
        payment_id INT AUTO_INCREMENT PRIMARY KEY,
        order_id INT NULL,
        processed_by_user_id INT NOT NULL,
        payment_type ENUM('DesignFee', 'Assurance', 'ProductOrder', 'RushFee') NOT NULL,
        payment_method VARCHAR(30) NULL,
        amount_paid DECIMAL(10,2) NOT NULL,
        payment_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(30) NOT NULL DEFAULT 'Completed',
        CONSTRAINT fk_payment_order FOREIGN KEY (order_id)
            REFERENCES customer_orders(order_id) ON UPDATE CASCADE ON DELETE SET NULL,
        CONSTRAINT fk_payment_user FOREIGN KEY (processed_by_user_id)
            REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
        INDEX idx_payment_order (order_id),
        INDEX idx_payment_date (payment_date)
    ) ENGINE=InnoDB
    """,
    # --- StockMovement ---
    """
    CREATE TABLE IF NOT EXISTS stock_movements (
        movement_id INT AUTO_INCREMENT PRIMARY KEY,
        material_id INT NOT NULL,
        recorded_by_user_id INT NOT NULL,
        movement_type ENUM('IN', 'OUT', 'ADJUSTMENT') NOT NULL,
        quantity INT NOT NULL,
        reason VARCHAR(255) NULL,
        movement_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        order_item_id INT NULL,
        expense_id INT NULL,
        CONSTRAINT fk_movement_material FOREIGN KEY (material_id)
            REFERENCES materials(material_id) ON UPDATE CASCADE ON DELETE RESTRICT,
        CONSTRAINT fk_movement_user FOREIGN KEY (recorded_by_user_id)
            REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
        CONSTRAINT fk_movement_item FOREIGN KEY (order_item_id)
            REFERENCES order_items(order_item_id) ON UPDATE CASCADE ON DELETE SET NULL,
        CONSTRAINT fk_movement_expense FOREIGN KEY (expense_id)
            REFERENCES expenses(expense_id) ON UPDATE CASCADE ON DELETE SET NULL,
        INDEX idx_movement_material (material_id),
        INDEX idx_movement_date (movement_date)
    ) ENGINE=InnoDB
    """,
    # --- SystemLog (Phase 10: audit every backup / restore with date-time) ---
    """
    CREATE TABLE IF NOT EXISTS system_logs (
        log_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NULL,
        username VARCHAR(50) NULL,
        action ENUM('BACKUP', 'RESTORE') NOT NULL,
        details VARCHAR(500) NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_log_user FOREIGN KEY (user_id)
            REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE SET NULL,
        INDEX idx_log_date (created_at),
        INDEX idx_log_action (action)
    ) ENGINE=InnoDB
    """,
]

DROP_TABLES_SQL = [
    "DROP TABLE IF EXISTS system_logs",
    "DROP TABLE IF EXISTS stock_movements",
    "DROP TABLE IF EXISTS payments",
    "DROP TABLE IF EXISTS order_items",
    "DROP TABLE IF EXISTS customer_orders",
    "DROP TABLE IF EXISTS expenses",
    "DROP TABLE IF EXISTS materials",
    "DROP TABLE IF EXISTS customers",
    "DROP TABLE IF EXISTS users",
]


def create_tables(conn) -> None:
    cursor = conn.cursor()
    try:
        for sql in CREATE_TABLES_SQL:
            cursor.execute(sql)
    finally:
        cursor.close()


def migrate_enum_columns(conn) -> None:
    """Remap legacy VARCHAR values then enforce Phase-1 ENUM definitions.

    Safe to run on fresh installs (no-op) and on existing XAMPP databases
    that still use the old VARCHAR columns or old category/type names.

    Mapping:
      customer_orders.order_type: 'Layout-Only' -> 'LayoutOnly',
        'Print'/'Package'/'Custom'/anything else -> 'ProductOrder'
      expenses.category: 'Utilities' -> 'Utility',
        'Rent'/'Maintenance'/'Transport'/'Marketing'/anything else -> 'Other'
    """
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE customer_orders SET order_type = 'LayoutOnly' "
            "WHERE order_type = 'Layout-Only'"
        )
        cursor.execute(
            "UPDATE customer_orders SET order_type = 'ProductOrder' "
            "WHERE order_type NOT IN ('LayoutOnly', 'ProductOrder')"
        )
        cursor.execute(
            "ALTER TABLE customer_orders MODIFY COLUMN order_type "
            "ENUM('LayoutOnly', 'ProductOrder') NOT NULL DEFAULT 'ProductOrder'"
        )
    except Exception:
        # Table may not exist yet on very first init; create_tables covers it.
        pass
    try:
        cursor.execute(
            "UPDATE expenses SET category = 'Utility' WHERE category = 'Utilities'"
        )
        cursor.execute(
            "UPDATE expenses SET category = 'Other' "
            "WHERE category NOT IN "
            "('Labor', 'Materials', 'Miscellaneous', 'Utility', 'Other')"
        )
        cursor.execute(
            "ALTER TABLE expenses MODIFY COLUMN category "
            "ENUM('Labor', 'Materials', 'Miscellaneous', 'Utility', 'Other') NOT NULL"
        )
    except Exception:
        pass
    finally:
        cursor.close()


def drop_tables(conn) -> None:
    cursor = conn.cursor()
    try:
        cursor.execute("SET FOREIGN_KEY_CHECKS=0")
        for sql in DROP_TABLES_SQL:
            cursor.execute(sql)
        cursor.execute("SET FOREIGN_KEY_CHECKS=1")
    finally:
        cursor.close()
