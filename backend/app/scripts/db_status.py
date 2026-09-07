from __future__ import annotations

import pyodbc

from app.db.bootstrap_manifest import BOOTSTRAP_SCRIPTS
from app.db.sql_runner import build_pyodbc_connection_string, ensure_execution_table


def main() -> None:
    with pyodbc.connect(build_pyodbc_connection_string(), autocommit=False) as connection:
        ensure_execution_table(connection)
        cursor = connection.cursor()
        rows = {
            row[0]: row[1]
            for row in cursor.execute(
                """
                SELECT script_key, executed_at
                FROM dbo.backend_sql_executions
                ORDER BY script_key;
                """
            ).fetchall()
        }

        for script in BOOTSTRAP_SCRIPTS:
            executed_at = rows.get(script.key)
            if executed_at is None:
                print(f"PENDING  {script.key}  {script.file_path}")
                continue
            print(f"APPLIED  {script.key}  {executed_at}  {script.file_path}")


if __name__ == "__main__":
    main()

