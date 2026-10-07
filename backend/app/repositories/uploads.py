"""Upload bookkeeping (Phase 4.1/4.2, scripts/021_file_pipeline.sql)."""
from __future__ import annotations

from sqlalchemy import Engine, text


def record_quarantine(engine: Engine, *, tenant_id: int | None, user_id: int | None, entity_type: str,
                      entity_id: int, file_name: str, storage_key: str, sha256: str,
                      signature: str | None, scanner: str) -> int:
    with engine.begin() as connection:
        return int(connection.execute(
            text(
                """
                INSERT INTO dbo.upload_quarantine
                  (tenant_id, uploaded_by_user_id, entity_type, entity_id, file_name, storage_key, sha256, signature, scanner)
                OUTPUT INSERTED.id
                VALUES (:tenant_id, :user_id, :entity_type, :entity_id, :file_name, :storage_key, :sha256, :signature, :scanner);
                """
            ),
            {"tenant_id": tenant_id, "user_id": user_id, "entity_type": entity_type, "entity_id": entity_id,
             "file_name": file_name[:255], "storage_key": storage_key, "sha256": sha256,
             "signature": (signature or "")[:200] or None, "scanner": scanner},
        ).scalar_one())


def find_idempotent_document(engine: Engine, user_id: int, idem_key: str, entity_type: str, entity_id: int) -> int | None:
    with engine.connect() as connection:
        return connection.execute(
            text(
                "SELECT document_id FROM dbo.upload_idempotency WHERE user_id = :u AND idem_key = :k "
                "AND entity_type = :t AND entity_id = :e;"
            ),
            {"u": user_id, "k": idem_key, "t": entity_type, "e": entity_id},
        ).scalar_one_or_none()


def remember_idempotent_document(engine: Engine, user_id: int, idem_key: str, entity_type: str,
                                 entity_id: int, document_id: int) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                IF NOT EXISTS (SELECT 1 FROM dbo.upload_idempotency WHERE user_id = :u AND idem_key = :k)
                  INSERT INTO dbo.upload_idempotency (user_id, idem_key, entity_type, entity_id, document_id)
                  VALUES (:u, :k, :t, :e, :d);
                """
            ),
            {"u": user_id, "k": idem_key, "t": entity_type, "e": entity_id, "d": document_id},
        )
