"""Company settings repository — reads/writes the primary company_entities row."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, text


@dataclass
class CompanyProfileRecord:
    id: int
    display_name: str
    legal_name: str
    company_code: str
    company_type_code: str | None
    hq_city: str | None
    hq_state: str | None
    country_name: str | None
    support_email: str | None
    support_phone: str | None
    website_url: str | None
    registered_address: str | None
    has_logo: bool


_PROFILE_COLUMNS = """
    id, display_name, legal_name, company_code, company_type_code,
    hq_city, hq_state, country_name, support_email, support_phone,
    website_url, registered_address,
    CASE WHEN logo_data IS NULL THEN 0 ELSE 1 END AS has_logo
"""


def _map_profile(row) -> CompanyProfileRecord:
    return CompanyProfileRecord(
        id=row["id"],
        display_name=row["display_name"],
        legal_name=row["legal_name"],
        company_code=row["company_code"],
        company_type_code=row["company_type_code"],
        hq_city=row["hq_city"],
        hq_state=row["hq_state"],
        country_name=row["country_name"],
        support_email=row["support_email"],
        support_phone=row["support_phone"],
        website_url=row["website_url"],
        registered_address=row["registered_address"],
        has_logo=bool(row["has_logo"]),
    )


def get_primary_company_profile(engine: Engine) -> CompanyProfileRecord | None:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                f"""
                SELECT {_PROFILE_COLUMNS}
                FROM dbo.company_entities
                WHERE is_primary = 1 AND status = N'active'
                """
            )
        ).mappings().first()
    return _map_profile(row) if row else None


def update_company_profile(
    engine: Engine, company_id: int, fields: dict[str, str | None]
) -> CompanyProfileRecord | None:
    if not fields:
        return get_primary_company_profile(engine)

    assignments = ", ".join(f"{column} = :{column}" for column in fields)
    params = {"company_id": company_id, **fields}
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                UPDATE dbo.company_entities
                SET {assignments}, updated_at = SYSUTCDATETIME()
                WHERE id = :company_id
                """
            ),
            params,
        )
    return get_primary_company_profile(engine)


def set_company_logo(engine: Engine, company_id: int, data_url: str | None) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE dbo.company_entities
                SET logo_data = :logo_data, updated_at = SYSUTCDATETIME()
                WHERE id = :company_id
                """
            ),
            {"company_id": company_id, "logo_data": data_url},
        )


def get_primary_company_id(engine: Engine) -> int | None:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT TOP (1) id FROM dbo.company_entities
                WHERE is_primary = 1 AND status = N'active'
                ORDER BY id
                """
            )
        ).first()
    return row[0] if row else None


def get_company_logo(engine: Engine, company_id: int) -> str | None:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT logo_data FROM dbo.company_entities WHERE id = :company_id"
            ),
            {"company_id": company_id},
        ).first()
    return row[0] if row and row[0] else None
