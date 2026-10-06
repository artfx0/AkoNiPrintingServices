"""MySQL connection layer for AkoNi Printing Services.

Reads config from db_config.ini [mysql] (project root) with env-var fallback:
  AKONI_DB_HOST, AKONI_DB_PORT, AKONI_DB_USER, AKONI_DB_PASSWORD, AKONI_DB_NAME
"""
import configparser
import os
from pathlib import Path

import mysql.connector
from mysql.connector import pooling

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_FILE = _PROJECT_ROOT / "db_config.ini"

_DEFAULTS = {
    "host": "localhost",
    "port": "3306",
    "user": "root",
    "password": "",
    "database": "akoni_printing_db",
}


def load_config() -> dict:
    cfg = dict(_DEFAULTS)
    if _CONFIG_FILE.exists():
        parser = configparser.ConfigParser()
        parser.read(_CONFIG_FILE)
        if parser.has_section("mysql"):
            for key in cfg:
                if parser.has_option("mysql", key):
                    cfg[key] = parser.get("mysql", key)
    cfg["host"] = os.getenv("AKONI_DB_HOST", cfg["host"])
    cfg["port"] = os.getenv("AKONI_DB_PORT", str(cfg["port"]))
    cfg["user"] = os.getenv("AKONI_DB_USER", cfg["user"])
    cfg["password"] = os.getenv("AKONI_DB_PASSWORD", cfg["password"])
    cfg["database"] = os.getenv("AKONI_DB_NAME", cfg["database"])
    try:
        cfg["port"] = int(cfg["port"])
    except (TypeError, ValueError):
        cfg["port"] = 3306
    return cfg


_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        cfg = load_config()
        _pool = pooling.MySQLConnectionPool(
            pool_name="akoni_pool",
            pool_size=5,
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            database=cfg["database"],
            autocommit=False,
            connection_timeout=5,
        )
    return _pool


def get_connection():
    """Get a pooled connection to the app database."""
    return _get_pool().get_connection()


def get_server_connection():
    """Get a connection without selecting a database (for CREATE DATABASE)."""
    cfg = load_config()
    return mysql.connector.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        autocommit=True,
        connection_timeout=5,
    )


def test_connection() -> tuple[bool, str]:
    try:
        conn = get_connection()
        conn.ping(reconnect=True)
        conn.close()
        return True, "Connection OK"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def init_database() -> None:
    """Create database (if needed) then all tables per ERD."""
    from database.models import create_tables, migrate_enum_columns

    cfg = load_config()
    server = get_server_connection()
    try:
        cursor = server.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.close()
    finally:
        server.close()

    global _pool
    _pool = None  # force reconnect now that DB exists
    conn = get_connection()
    try:
        create_tables(conn)
        conn.commit()
        migrate_enum_columns(conn)
        conn.commit()
        _ensure_default_admin(conn)
        conn.commit()
    finally:
        conn.close()


def _ensure_default_admin(conn) -> None:
    """Seed a default Admin account (admin / admin123) if users table is empty."""
    import bcrypt

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    (count,) = cursor.fetchone()
    if count == 0:
        pw_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode("utf-8")
        cursor.execute(
            "INSERT INTO users (username, password_hash, first_name, last_name, role, is_active) "
            "VALUES (%s, %s, %s, %s, 'Admin', TRUE)",
            ("admin", pw_hash, "System", "Admin"),
        )
    cursor.close()
