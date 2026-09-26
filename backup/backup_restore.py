"""Backup and restore (Admin/Owner use case).

Uses mysqldump/mysql when available; otherwise falls back to a pure-Python
SQL dump (SHOW CREATE TABLE + INSERT statements) executed via mysql.connector.
"""
from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from database.database import load_config


class BackupManager:
    def __init__(self):
        self.cfg = load_config()
        self.mysqldump = shutil.which("mysqldump") or self._xampp_tool("mysqldump")
        self.mysql = shutil.which("mysql") or self._xampp_tool("mysql")

    @staticmethod
    def _xampp_tool(name: str) -> str | None:
        """Probe default XAMPP install locations (Windows) when not on PATH."""
        candidates = [
            Path(r"C:\xampp\mysql\bin") / f"{name}.exe",
            Path("/opt/lampp/bin") / name,
        ]
        for path in candidates:
            if path.is_file():
                return str(path)
        return None

    def default_filename(self, prefix: str = "akoni_backup") -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{stamp}.sql"

    # -- backup --
    def backup(self, dest_path: str) -> str:
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if self.mysqldump:
            self._backup_native(str(dest))
        else:
            self._backup_python(str(dest))
        return str(dest)

    def _backup_native(self, dest: str) -> None:
        cmd = [self.mysqldump, f"--host={self.cfg['host']}",
               f"--port={self.cfg['port']}", f"--user={self.cfg['user']}",
               f"--databases", self.cfg["database"], "--routines", "--events"]
        env_pw = {"MYSQL_PWD": self.cfg["password"]} if self.cfg["password"] else {}
        import os
        env = {**os.environ, **env_pw}
        with open(dest, "w", encoding="utf-8") as fh:
            subprocess.run(cmd, stdout=fh, env=env, check=True, timeout=300)

    def _backup_python(self, dest: str) -> None:
        import mysql.connector
        conn = mysql.connector.connect(
            host=self.cfg["host"], port=self.cfg["port"], user=self.cfg["user"],
            password=self.cfg["password"], database=self.cfg["database"])
        try:
            cur = conn.cursor()
            lines = [f"-- AkoNi backup {datetime.now().isoformat()}",
                     f"CREATE DATABASE IF NOT EXISTS `{self.cfg['database']}`;",
                     f"USE `{self.cfg['database']}`;",
                     "SET FOREIGN_KEY_CHECKS=0;"]
            cur.execute("SHOW TABLES")
            tables = [r[0] for r in cur.fetchall()]
            for table in tables:
                cur.execute(f"SHOW CREATE TABLE `{table}`")
                create_sql = cur.fetchone()[1]
                lines.append(f"DROP TABLE IF EXISTS `{table}`;")
                lines.append(create_sql + ";")
                cur2 = conn.cursor()
                try:
                    cur2.execute(f"SELECT * FROM `{table}`")
                    cols = [d[0] for d in cur2.description] if cur2.description else []
                    for row in cur2.fetchall():
                        vals = ", ".join(self._sql_literal(v) for v in row)
                        lines.append(f"INSERT INTO `{table}` (`{'`, `'.join(cols)}`)"
                                     f" VALUES ({vals});")
                finally:
                    cur2.close()
            lines.append("SET FOREIGN_KEY_CHECKS=1;")
            Path(dest).write_text("\n".join(lines), encoding="utf-8")
        finally:
            conn.close()

    @staticmethod
    def _sql_literal(value) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, (int, float)):
            return str(value)
        import decimal, datetime as dt
        if isinstance(value, decimal.Decimal):
            return str(value)
        if isinstance(value, (dt.datetime, dt.date)):
            return f"'{value.strftime('%Y-%m-%d %H:%M:%S') if isinstance(value, dt.datetime) else str(value)}'"
        escaped = str(value).replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"

    # -- restore --
    def restore(self, sql_path: str) -> None:
        if self.mysql:
            self._restore_native(sql_path)
        else:
            self._restore_python(sql_path)

    def _restore_native(self, sql_path: str) -> None:
        import os
        cmd = [self.mysql, f"--host={self.cfg['host']}", f"--port={self.cfg['port']}",
               f"--user={self.cfg['user']}", self.cfg["database"]]
        env = {**os.environ, **({"MYSQL_PWD": self.cfg["password"]} if self.cfg["password"] else {})}
        with open(sql_path, "r", encoding="utf-8") as fh:
            subprocess.run(cmd, stdin=fh, env=env, check=True, timeout=300)

    def _restore_python(self, sql_path: str) -> None:
        import mysql.connector
        sql = Path(sql_path).read_text(encoding="utf-8")
        conn = mysql.connector.connect(
            host=self.cfg["host"], port=self.cfg["port"], user=self.cfg["user"],
            password=self.cfg["password"], database=self.cfg["database"],
            allow_local_infile=True)
        try:
            cur = conn.cursor()
            # naive split on ";\n" — sufficient for our generated dumps
            for stmt in sql.split(";\n"):
                stmt = stmt.strip()
                if not stmt or stmt.startswith("--"):
                    continue
                # strip inline comment lines
                lines = [ln for ln in stmt.splitlines() if not ln.strip().startswith("--")]
                stmt = "\n".join(lines).strip()
                if stmt:
                    cur.execute(stmt)
            conn.commit()
        finally:
            conn.close()
