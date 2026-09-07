from fastapi import APIRouter

from app.db.health import get_database_health
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    database_status = get_database_health()
    return HealthResponse(
        name="Recruitment System API",
        status="ok" if database_status == "ok" else "degraded",
        database_status=database_status,
    )

