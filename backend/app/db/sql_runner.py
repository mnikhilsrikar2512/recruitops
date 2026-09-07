from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import pyodbc
except ModuleNotFoundError:  # pragma: no cover - allows pure stdlib test runs before dependency install
    pyodbc = None  # type: ignore[assignment]
from app.db.bootstrap_manifest import BootstrapScript


GO_PATTERN = re.compile(r"^\s*GO(?:\s+(\d+))?\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class SqlBatch:
    sql_text: str
    repeat_count: int


def split_sql_batches(sql_text: str) -> list[SqlBatch]:
    lines = sql_text.splitlines()
    batches: list[SqlBatch] = []
    current: list[str] = []

    for line in lines:
        match = GO_PATTERN.match(line)
        if match:
            batch_sql = "\n".join(current).strip()
            if batch_sql:
                repeat_count = int(match.group(1) or "1")
                batches.append(SqlBatch(sql_text=batch_sql, repeat_count=max(repeat_count, 1)))
            current = []
            continue
        current.append(line)

    final_sql = "\n".join(current).strip()
    if final_sql:
        batches.append(SqlBatch(sql_text=final_sql, repeat_count=1))

    return batches


def compute_sql_checksum(sql_text: str) -> str:
    return hashlib.sha256(sql_text.encode("utf-8")).hexdigest()


def _odbc_flags() -> tuple[str, str]:
    from app.core.config import settings

    encrypt_value = "yes" if settings.db_encrypt else "no"
    trust_value = "yes" if settings.db_trust_server_certificate else "no"
    return encrypt_value, trust_value


def build_pyodbc_connection_string(database: str | None = None) -> str:
    from app.core.config import settings

    encrypt_value, trust_value = _odbc_flags()
    return (
        f"DRIVER={{{settings.db_driver}}};"
        f"SERVER={settings.db_host},{settings.db_port};"
        f"DATABASE={database or settings.db_name};"
        f"UID={settings.db_user};"
        f"PWD={settings.db_password};"
        f"Encrypt={encrypt_value};"
        f"TrustServerCertificate={trust_value};"
    )


def ensure_database_exists() -> None:
    from app.core.config import settings

    database_name = settings.db_name
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", database_name):
        raise ValueError("DB_NAME must be a simple identifier")

    pyodbc_module = require_pyodbc()
    connection = pyodbc_module.connect(build_pyodbc_connection_string("master"), autocommit=True)
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            IF DB_ID(N'{database_name}') IS NULL
            BEGIN
              CREATE DATABASE [{database_name}];
            END;
            """
        )
    finally:
        connection.close()


def require_pyodbc() -> Any:
    if pyodbc is None:
        raise RuntimeError("pyodbc is required for live database bootstrap operations.")
    return pyodbc


def ensure_execution_table(connection: Any) -> None:
    cursor = connection.cursor()
    cursor.execute(
        """
        IF OBJECT_ID(N'dbo.backend_sql_executions', N'U') IS NULL
        BEGIN
          CREATE TABLE dbo.backend_sql_executions (
            id BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
            script_key NVARCHAR(200) NOT NULL,
            file_path NVARCHAR(500) NOT NULL,
            checksum_sha256 CHAR(64) NOT NULL,
            script_type NVARCHAR(50) NOT NULL,
            executed_at DATETIME2(0) NOT NULL CONSTRAINT DF_backend_sql_executions_executed_at DEFAULT SYSUTCDATETIME(),
            CONSTRAINT UQ_backend_sql_executions_script_key UNIQUE (script_key)
          );
        END;
        """
    )
    connection.commit()


def read_sql_file(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")


def get_execution_record(
    connection: Any, script_key: str
) -> tuple[str, str, str] | None:
    ensure_execution_table(connection)
    cursor = connection.cursor()
    row = cursor.execute(
        """
        SELECT script_key, checksum_sha256, script_type
        FROM dbo.backend_sql_executions
        WHERE script_key = ?;
        """,
        script_key,
    ).fetchone()
    if row is None:
        return None
    return row[0], row[1], row[2]


def should_execute_script(
    existing_checksum: str | None, new_checksum: str, force: bool = False
) -> bool:
    if force or existing_checksum is None:
        return True
    return existing_checksum != new_checksum


def run_sql_text(connection: Any, sql_text: str) -> None:
    cursor = connection.cursor()
    for batch in split_sql_batches(sql_text):
        for _ in range(batch.repeat_count):
            cursor.execute(batch.sql_text)
    connection.commit()


def track_execution(
    connection: Any,
    script: BootstrapScript,
    checksum_sha256: str,
) -> None:
    ensure_execution_table(connection)
    cursor = connection.cursor()
    cursor.execute(
        """
        MERGE dbo.backend_sql_executions AS target
        USING (
          SELECT
            ? AS script_key,
            ? AS file_path,
            ? AS checksum_sha256,
            ? AS script_type
        ) AS source
        ON target.script_key = source.script_key
        WHEN MATCHED THEN
          UPDATE SET
            target.file_path = source.file_path,
            target.checksum_sha256 = source.checksum_sha256,
            target.script_type = source.script_type,
            target.executed_at = SYSUTCDATETIME()
        WHEN NOT MATCHED THEN
          INSERT (script_key, file_path, checksum_sha256, script_type)
          VALUES (source.script_key, source.file_path, source.checksum_sha256, source.script_type);
        """,
        script.key,
        str(script.file_path),
        checksum_sha256,
        script.script_type,
    )
    connection.commit()
