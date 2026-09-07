from fastapi import APIRouter, Depends, Path
from fastapi.responses import FileResponse

from app.api.deps import get_current_auth_context
from app.core.storage import get_file_path
from app.services.auth import AuthContext

router = APIRouter()


@router.get("/{file_path:path}")
def serve_file(
    file_path: str = Path(...),
    _auth: AuthContext = Depends(get_current_auth_context),
) -> FileResponse:
    resolved = get_file_path(file_path)
    return FileResponse(path=str(resolved), filename=resolved.name)
