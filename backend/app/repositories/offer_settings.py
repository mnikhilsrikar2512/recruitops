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


def find_requisition_budget_for_application(engine: Engine, application_id: int) -> tuple[Decimal | None, str | None]:
    """(budget_max, currency_code) of the application's requisition."""
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT r.budget_max, r.currency_code
                FROM dbo.candidate_applications AS ca
                INNER JOIN dbo.requisitions AS r ON r.id = ca.requisition_id
                WHERE ca.id = :application_id;
                """
            ),
            {"application_id": application_id},
        ).mappings().first()
    if row is None:
        return None, None
    budget = Decimal(str(row["budget_max"])) if row["budget_max"] is not None else None
    return budget, row["currency_code"]
