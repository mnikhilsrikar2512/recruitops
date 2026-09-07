from datetime import datetime, timezone

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    name: str
    status: str
    database_status: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

