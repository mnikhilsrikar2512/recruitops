"""Phase 4.2 upload pipeline: sniff -> allowlist -> size cap -> quarantine
-> malware scan -> available.

Nothing reaches its final storage key until the scan says clean. A file
that fails the scan stays under quarantine/, is logged in
dbo.upload_quarantine and is never linked; the caller gets 422
MALWARE_DETECTED. A scanner that cannot answer refuses the upload (503
SCANNER_UNAVAILABLE) — fail closed.
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import UploadFile
from sqlalchemy import Engine

from app.core.errors import ApiError
from app.core.file_storage import QUARANTINE_PREFIX, get_storage, tenant_key
from app.core.file_types import PURPOSES, FileRejected, check_file
from app.core.malware import ScanUnavailable, get_scanner
from app.repositories.audit import insert_audit_log
from app.repositories.uploads import record_quarantine

log = logging.getLogger("recruitops.uploads")


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    file_name: str
    content_type: str
    size_bytes: int
    sha256: str
    scan_status: str
    scanned_at: datetime


async def read_capped(file: UploadFile, purpose: str) -> bytes:
    """Read at most cap+1 bytes so an oversized upload never sits in memory whole."""
    _, cap = PURPOSES[purpose]
    return await file.read(cap + 1)


def ingest(engine: Engine, *, content: bytes, file_name: str, purpose: str, tenant_id: int | None,
           area: str, entity_type: str, entity_id: int, actor_user_id: int | None,
           actor_location_id: int | None) -> StoredFile:
    try:
        kind = check_file(file_name, content, purpose)
    except FileRejected as rejected:
        status_code = 413 if rejected.code == "FILE_TOO_LARGE" else 422
        raise ApiError(status_code, rejected.code, rejected.message) from None

    digest = hashlib.sha256(content).hexdigest()
    suffix = f"{uuid.uuid4().hex}{sorted(kind.extensions)[0]}"
    final_key = tenant_key(tenant_id, area, entity_id, suffix)
    quarantine_key = QUARANTINE_PREFIX + final_key
    storage = get_storage()
    storage.put(quarantine_key, content, kind.content_type)

    try:
        result = get_scanner().scan(content)
    except ScanUnavailable as exc:
        log.error("malware scanner unavailable: %s", exc)
        storage.delete(quarantine_key)
        raise ApiError(503, "SCANNER_UNAVAILABLE",
                       "Files can't be checked for viruses right now, so the upload was not accepted. Try again shortly.") from None

    if not result.clean:
        record_quarantine(engine, tenant_id=tenant_id, user_id=actor_user_id, entity_type=entity_type,
                          entity_id=entity_id, file_name=file_name, storage_key=quarantine_key, sha256=digest,
                          signature=result.signature, scanner=result.scanner)
        if actor_user_id is not None:
            insert_audit_log(engine, actor_user_id=actor_user_id, location_id=actor_location_id,
                             entity_type=entity_type, entity_id=entity_id, action_type="upload.malware_blocked",
                             new_values={"file_name": file_name, "sha256": digest, "signature": result.signature,
                                         "scanner": result.scanner})
        raise ApiError(422, "MALWARE_DETECTED",
                       "This file failed the virus check and was not accepted. It has been quarantined.")

    storage.put(final_key, content, kind.content_type)
    storage.delete(quarantine_key)
    return StoredFile(storage_key=final_key, file_name=file_name, content_type=kind.content_type,
                      size_bytes=len(content), sha256=digest, scan_status="clean",
                      scanned_at=datetime.now(timezone.utc))
