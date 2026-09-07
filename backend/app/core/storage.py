from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


def _get_upload_root() -> Path:
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def _get_candidate_upload_dir(candidate_id: int) -> Path:
    candidate_dir = _get_upload_root() / "candidates" / str(candidate_id)
    candidate_dir.mkdir(parents=True, exist_ok=True)
    return candidate_dir


def _allowed_extension(filename: str) -> bool:
    allowed = {ext.strip().lower() for ext in settings.allowed_upload_extensions.split(",")}
    ext = Path(filename).suffix.lower()
    return ext in allowed


def _write_file(file_path: Path, content: bytes) -> None:
    with open(file_path, "wb") as f:
        f.write(content)


async def save_candidate_document(candidate_id: int, file: UploadFile) -> tuple[str, str]:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File name is required",
        )

    if not _allowed_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"File extension not allowed. Allowed: {settings.allowed_upload_extensions}",
        )

    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        max_mb = settings.max_upload_size_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {max_mb}MB",
        )

    candidate_dir = _get_candidate_upload_dir(candidate_id)
    ext = Path(file.filename).suffix.lower()
    safe_name = f"{uuid.uuid4().hex}{ext}"
    file_path = candidate_dir / safe_name

    await asyncio.to_thread(_write_file, file_path, content)

    relative_path = str(file_path.relative_to(_get_upload_root()))
    return file.filename, relative_path


def get_file_path(relative_path: str) -> Path:
    resolved = (_get_upload_root() / relative_path).resolve()
    upload_root = _get_upload_root().resolve()
    try:
        resolved.relative_to(upload_root)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this file is not allowed",
        ) from None
    if not resolved.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )
    return resolved
