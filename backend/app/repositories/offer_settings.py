"""Company offer-approval threshold (Phase 4.8, scripts/020_offer_threshold.sql)."""
from __future__ import annotations

from dataclasses import dataclass
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


# ---- Phase 4.13: signing-bonus policy (scripts/022_signing_bonus_policy.sql)
@dataclass(frozen=True)
class OfferPolicy:
    """What applies to one application's offer.

    source = "client" when the requisition is for a client (its switches,
    falling back to the company's when NULL); "company" for internal hiring.
    """
    signing_bonus_allowed: bool = True
    bonus_counts_against_budget: bool = True
    source: str = "company"
    client_company_id: int | None = None
    budget_max: Decimal | None = None
    currency_code: str | None = None
    threshold: Decimal = Decimal("0")


def get_offer_policy(engine: Engine, application_id: int) -> OfferPolicy | None:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT
                  r.client_company_id,
                  r.budget_max,
                  r.currency_code,
                  t.offer_approval_threshold,
                  t.offers_signing_bonus AS company_bonus,
                  t.bonus_counts_against_budget AS company_counts,
                  cc.offers_signing_bonus AS client_bonus,
                  cc.bonus_counts_against_budget AS client_counts
                FROM dbo.candidate_applications AS ca
                INNER JOIN dbo.requisitions AS r ON r.id = ca.requisition_id
                LEFT JOIN dbo.branches AS b ON b.id = r.branch_id
                LEFT JOIN dbo.tenants AS t ON t.id = b.tenant_id
                LEFT JOIN dbo.client_companies AS cc ON cc.id = r.client_company_id
                WHERE ca.id = :application_id;
                """
            ),
            {"application_id": application_id},
        ).mappings().first()
    if row is None:
        return None
    return resolve_offer_policy(dict(row))


def resolve_offer_policy(row: dict) -> OfferPolicy:
    """Pure: client switch when set, else the company's (else today's default)."""
    def pick(client_value, company_value, default: bool) -> bool:
        if client_value is not None:
            return bool(client_value)
        if company_value is not None:
            return bool(company_value)
        return default

    is_client = row.get("client_company_id") is not None
    budget = row.get("budget_max")
    threshold = row.get("offer_approval_threshold")
    return OfferPolicy(
        signing_bonus_allowed=pick(row.get("client_bonus") if is_client else None, row.get("company_bonus"), True),
        bonus_counts_against_budget=pick(row.get("client_counts") if is_client else None, row.get("company_counts"), True),
        source="client" if is_client else "company",
        client_company_id=int(row["client_company_id"]) if is_client else None,
        budget_max=Decimal(str(budget)) if budget is not None else None,
        currency_code=row.get("currency_code"),
        threshold=Decimal(str(threshold)) if threshold is not None else Decimal("0"),
    )


def get_company_bonus_switches(engine: Engine, tenant_id: int | None) -> tuple[bool, bool]:
    if tenant_id is None:
        return True, True
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT offers_signing_bonus, bonus_counts_against_budget FROM dbo.tenants WHERE id = :t;"),
            {"t": tenant_id},
        ).first()
    return (bool(row[0]), bool(row[1])) if row else (True, True)


def set_company_bonus_switches(engine: Engine, tenant_id: int, offers_bonus: bool, counts: bool) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE dbo.tenants SET offers_signing_bonus = :b, bonus_counts_against_budget = :c, "
                "updated_at = SYSUTCDATETIME() WHERE id = :t;"
            ),
            {"t": tenant_id, "b": 1 if offers_bonus else 0, "c": 1 if counts else 0},
        )
