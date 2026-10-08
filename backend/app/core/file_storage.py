"""Phase 4.1: where uploaded files live.

Backends (STORAGE_BACKEND):
  local  development/CI only: files under UPLOAD_DIR; links are short-lived
         signed tokens served by GET /api/v1/files/signed/{token}.
  s3     staging/production: any S3-compatible store (AWS S3, Cloudflare R2,
         Backblaze B2, DigitalOcean Spaces, MinIO) via S3_ENDPOINT_URL.
         The bucket is private; links are presigned GET URLs.

Keys are always prefixed by company: ``tenant_<id>/<area>/<entity>/<uuid><ext>``.
Uploads land under ``quarantine/`` first and move to their final key only
after a clean malware scan (app/services/uploads.py). A link is only ever
issued by a service that has already checked the caller may see the record.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

import jwt

from app.core.config import DEV_JWT_SIGNING_KEY, settings

QUARANTINE_PREFIX = "quarantine/"
_LINK_AUDIENCE = "recruitops-file-link"


class StorageBackend(Protocol):
    name: str

    def put(self, key: str, content: bytes, content_type: str) -> None: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
    def exists(self, key: str) -> bool: ...
    def link(self, key: str, file_name: str, content_type: str, ttl_seconds: int) -> str: ...


def _safe_key(key: str) -> str:
    parts = [p for p in key.replace("\\", "/").split("/") if p]
    if not parts or any(p in {".", ".."} for p in parts):
        raise ValueError(f"unsafe storage key: {key!r}")
    return "/".join(parts)


class LocalStorage:
    name = "local"

    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / _safe_key(key)).resolve()
        path.relative_to(self.root)  # raises if it escapes the root
        return path

    def put(self, key: str, content: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def link(self, key: str, file_name: str, content_type: str, ttl_seconds: int) -> str:
        token = issue_file_token(_safe_key(key), file_name, content_type, ttl_seconds)
        return f"{settings.api_prefix}/files/signed/{token}"


class S3Storage:
    name = "s3"

    def __init__(self) -> None:
        import boto3  # imported lazily: development never needs it
        from botocore.config import Config

        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            region_name=settings.s3_region or None,
            endpoint_url=settings.s3_endpoint_url or None,
            aws_access_key_id=settings.s3_access_key_id or None,
            aws_secret_access_key=settings.s3_secret_access_key or None,
            config=Config(signature_version="s3v4"),
        )

    def put(self, key: str, content: bytes, content_type: str) -> None:
        extra = {}
        if not settings.s3_endpoint_url:  # AWS itself: encrypt at rest with S3-managed keys
            extra["ServerSideEncryption"] = "AES256"
        self.client.put_object(Bucket=self.bucket, Key=_safe_key(key), Body=content, ContentType=content_type, **extra)

    def get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=_safe_key(key))["Body"].read()

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=_safe_key(key))

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=_safe_key(key))
            return True
        except Exception:
            return False

    def link(self, key: str, file_name: str, content_type: str, ttl_seconds: int) -> str:
        safe_name = file_name.replace('"', "")
        return self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": _safe_key(key),
                "ResponseContentDisposition": f'attachment; filename="{safe_name}"',
                "ResponseContentType": content_type,
            },
            ExpiresIn=ttl_seconds,
        )


_backend: StorageBackend | None = None


def get_storage() -> StorageBackend:
    global _backend
    wanted = settings.storage_backend.strip().lower()
    if _backend is None or _backend.name != wanted:
        _backend = S3Storage() if wanted == "s3" else LocalStorage(settings.upload_dir)
    return _backend


def tenant_key(tenant_id: int | None, area: str, entity_id: int, file_name_suffix: str) -> str:
    return f"tenant_{tenant_id or 0}/{area}/{entity_id}/{file_name_suffix}"


# ---- signed links for the local backend --------------------------------
def _key() -> str:
    return settings.jwt_signing_key or DEV_JWT_SIGNING_KEY


def issue_file_token(key: str, file_name: str, content_type: str, ttl_seconds: int) -> str:
    expires = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    claims = {"k": key, "fn": file_name, "ct": content_type, "exp": expires, "typ": "file", "aud": _LINK_AUDIENCE}
    return jwt.encode(claims, _key(), algorithm="HS256")


def decode_file_token(token: str) -> dict:
    """Raises jwt.InvalidTokenError when tampered with, expired or not a file link."""
    claims = jwt.decode(token, _key(), algorithms=["HS256"], audience=_LINK_AUDIENCE,
                        options={"require": ["exp", "k", "typ", "aud"]})
    if claims.get("typ") != "file" or str(claims["k"]).startswith(QUARANTINE_PREFIX):
        raise jwt.InvalidTokenError("not a file link")
    return claims
