from __future__ import annotations

import argparse

import pyodbc

from app.db.bootstrap_manifest import select_bootstrap_scripts
from app.db.sql_runner import (
    build_pyodbc_connection_string,
    compute_sql_checksum,
    ensure_database_exists,
    get_execution_record,
    read_sql_file,
    run_sql_text,
    should_execute_script,
    track_execution,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap the recruitment system database.")
    parser.add_argument(
        "--include-sample-data",
        action="store_true",
        help="Also apply the sample operational data script.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reapply tracked scripts even if their checksum has not changed.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scripts = select_bootstrap_scripts(include_sample_data=args.include_sample_data)
    ensure_database_exists()

    with pyodbc.connect(build_pyodbc_connection_string(), autocommit=False) as connection:
        for script in scripts:
            sql_text = read_sql_file(script.file_path)
            checksum_sha256 = compute_sql_checksum(sql_text)
            existing_record = get_execution_record(connection, script.key)
            existing_checksum = existing_record[1] if existing_record else None

            if not should_execute_script(existing_checksum, checksum_sha256, force=args.force):
                print(f"Skipped unchanged SQL file: {script.file_path}")
                continue

            run_sql_text(connection, sql_text)
            track_execution(connection, script, checksum_sha256)
            print(f"Executed SQL file: {script.file_path}")

    print("Database bootstrap completed successfully")


if __name__ == "__main__":
    main()

