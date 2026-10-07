"""Company offer-approval threshold (Phase 4.8, scripts/020_offer_threshold.sql)."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Engine, text


def get_offer_approval_threshold(engine: Engine, tenant_id: int | None) -> Decimal:
    """0 when the company is unknown: every paid offer then needs approval."""
    if tenant_id is None:
        return Decimal("0")
    with engine.connect() as connection:
        value = connection.execute(
            text("SELECT offer_approval_threshold FROM dbo.tenants WHERE id = :tenant_id;"),
            {"tenant_id": tenant_id},
        ).scalar_one_or_none()
    return Decimal(str(value)) if value is not None else Decimal("0")


def set_offer_approval_threshold(engine: Engine, tenant_id: int, threshold: Decimal) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE dbo.tenants SET offer_approval_threshold = :threshold, updated_at = SYSUTCDATETIME() "
                "WHERE id = :tenant_id;"
            ),
            {"tenant_id": tenant_id, "threshold": threshold},
        )
