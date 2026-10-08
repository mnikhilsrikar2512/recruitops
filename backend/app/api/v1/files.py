"""Phase 4.1: file downloads only through short-lived signed links.

The old GET /files/{path} served any stored file to any signed-in user who
knew (or guessed) its path — no company or record check. It is gone. A link
now comes from an endpoint that first checks the caller may see the record
(e.g. GET /candidates/{id}/documents/{doc_id}/link); for the local backend
that link points here, for S3 it is a presigned URL to the private bucket.
"""
import jwt
from fastapi import APIRouter, Path
from fastapi.responses import Response

from app.core.errors import ApiError
from app.core.file_storage import decode_file_token, get_storage

router = APIRouter()


@router.get("/signed/{token}")
def serve_signed_file(token: str = Path(..., min_length=10, max_length=4096)) -> Response:
    try:
        claims = decode_file_token(token)
    except jwt.ExpiredSignatureError:
        raise ApiError(403, "LINK_EXPIRED", "This download link has expired; open the record again for a new one") from None
    except jwt.InvalidTokenError:
        raise ApiError(403, "LINK_INVALID", "This download link is not valid") from None
    storage = get_storage()
    if not storage.exists(claims["k"]):
        raise ApiError(404, "NOT_FOUND", "File not found")
    file_name = str(claims.get("fn") or "download").replace('"', "")
    return Response(
        content=storage.get(claims["k"]),
        media_type=str(claims.get("ct") or "application/octet-stream"),
        headers={
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
