"""Legal documents and acceptances (Phase 5.1, scripts/026_legal.sql)."""
from __future__ import annotations

from sqlalchemy import Engine, text

DOC_TYPES = ("tos", "privacy", "dpa")
# Who accepts: every user for Terms and Privacy; the company (an admin, on
# the company's behalf) for the DPA.
PER_USER = ("tos", "privacy")
PER_COMPANY = ("dpa",)


def list_active_documents(engine: Engine) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT id, doc_type, version, title, body, is_placeholder, effective_at
                FROM dbo.legal_documents WHERE status = N'active'
                ORDER BY CASE doc_type WHEN N'tos' THEN 1 WHEN N'privacy' THEN 2 ELSE 3 END;
                """
            )
        ).mappings().all()
    return [{**dict(row), "is_placeholder": bool(row["is_placeholder"])} for row in rows]


def find_active_document(engine: Engine, doc_type: str) -> dict | None:
    return next((d for d in list_active_documents(engine) if d["doc_type"] == doc_type), None)


def active_placeholders(engine: Engine) -> list[str]:
    with engine.connect() as connection:
        return list(connection.execute(
            text("SELECT doc_type FROM dbo.legal_documents WHERE status = N'active' AND is_placeholder = 1 ORDER BY doc_type;")
        ).scalars().all())


def accepted_versions(engine: Engine, user_id: int, tenant_id: int | None) -> dict[str, dict]:
    """Latest acceptance per type that counts for this user: their own for
    Terms/Privacy, the company's for the DPA."""
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT a.doc_type, MAX(a.version) AS version, MAX(a.accepted_at) AS accepted_at
                FROM dbo.legal_acceptances AS a
                WHERE (a.doc_type IN (N'tos', N'privacy') AND a.user_id = :u)
                   OR (a.doc_type = N'dpa' AND a.tenant_id = :t)
                GROUP BY a.doc_type;
                """
            ),
            {"u": user_id, "t": tenant_id if tenant_id is not None else -1},
        ).mappings().all()
    return {row["doc_type"]: {"version": int(row["version"]), "accepted_at": row["accepted_at"]} for row in rows}


def record_acceptance(
    engine: Engine,
    *,
    tenant_id: int,
    user_id: int,
    document: dict,
    on_behalf_of_company: bool,
    ip_address: str | None,
    user_agent: str | None,
) -> int:
    with engine.begin() as connection:
        return int(connection.execute(
            text(
                """
                INSERT INTO dbo.legal_acceptances
                  (tenant_id, user_id, document_id, doc_type, version, on_behalf_of_company, ip_address, user_agent)
                OUTPUT INSERTED.id
                VALUES (:t, :u, :d, :type, :v, :company, :ip, :ua);
                """
            ),
            {"t": tenant_id, "u": user_id, "d": document["id"], "type": document["doc_type"],
             "v": document["version"], "company": 1 if on_behalf_of_company else 0,
             "ip": (ip_address or "")[:64] or None, "ua": (user_agent or "")[:400] or None},
        ).scalar_one())


def list_company_acceptances(engine: Engine, tenant_id: int) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT a.id, a.doc_type, a.version, a.accepted_at, a.on_behalf_of_company,
                       a.user_id, u.full_name AS user_name, u.email AS user_email
                FROM dbo.legal_acceptances AS a
                LEFT JOIN dbo.users AS u ON u.id = a.user_id
                WHERE a.tenant_id = :t
                ORDER BY a.accepted_at DESC, a.id DESC;
                """
            ),
            {"t": tenant_id},
        ).mappings().all()
    return [{**dict(row), "on_behalf_of_company": bool(row["on_behalf_of_company"])} for row in rows]


def publish_document(engine: Engine, *, doc_type: str, title: str, body: str, is_placeholder: bool, published_by: str) -> int:
    """Ops: the new version becomes active; the old one is superseded.
    Everyone must accept the new version (re-acceptance)."""
    if doc_type not in DOC_TYPES:
        raise ValueError(f"doc_type must be one of {DOC_TYPES}")
    with engine.begin() as connection:
        current = connection.execute(
            text("SELECT ISNULL(MAX(version), 0) FROM dbo.legal_documents WITH (UPDLOCK, HOLDLOCK) WHERE doc_type = :t;"),
            {"t": doc_type},
        ).scalar_one()
        connection.execute(
            text("UPDATE dbo.legal_documents SET status = N'superseded' WHERE doc_type = :t AND status = N'active';"),
            {"t": doc_type},
        )
        return int(connection.execute(
            text(
                """
                INSERT INTO dbo.legal_documents (doc_type, version, title, body, is_placeholder, published_by)
                OUTPUT INSERTED.id VALUES (:t, :v, :title, :body, :ph, :by);
                """
            ),
            {"t": doc_type, "v": int(current) + 1, "title": title, "body": body,
             "ph": 1 if is_placeholder else 0, "by": published_by},
        ).scalar_one())


def seed_accept_current_for_all_users(engine: Engine) -> int:
    """CI / staging seeding only: record acceptance of the documents in force
    for every active user (Terms, Privacy) and company (DPA, by its earliest
    user), so seeded personas aren't stopped by the acceptance page. Never
    called by the app. Returns the number of rows written."""
    with engine.begin() as connection:
        if connection.execute(text("SELECT OBJECT_ID(N'dbo.legal_documents')")).scalar() is None:
            return 0
        users = connection.execute(
            text(
                """
                INSERT INTO dbo.legal_acceptances (tenant_id, user_id, document_id, doc_type, version, on_behalf_of_company, user_agent)
                SELECT u.tenant_id, u.id, d.id, d.doc_type, d.version, 0, N'seed'
                FROM dbo.users AS u
                CROSS JOIN dbo.legal_documents AS d
                WHERE u.tenant_id IS NOT NULL AND u.status = N'active'
                  AND d.status = N'active' AND d.doc_type IN (N'tos', N'privacy')
                  AND NOT EXISTS (SELECT 1 FROM dbo.legal_acceptances a
                                  WHERE a.user_id = u.id AND a.doc_type = d.doc_type AND a.version = d.version);
                """
            )
        ).rowcount
        companies = connection.execute(
            text(
                """
                INSERT INTO dbo.legal_acceptances (tenant_id, user_id, document_id, doc_type, version, on_behalf_of_company, user_agent)
                SELECT t.id, (SELECT MIN(u.id) FROM dbo.users u WHERE u.tenant_id = t.id), d.id, d.doc_type, d.version, 1, N'seed'
                FROM dbo.tenants AS t
                CROSS JOIN dbo.legal_documents AS d
                WHERE d.status = N'active' AND d.doc_type = N'dpa'
                  AND EXISTS (SELECT 1 FROM dbo.users u WHERE u.tenant_id = t.id)
                  AND NOT EXISTS (SELECT 1 FROM dbo.legal_acceptances a
                                  WHERE a.tenant_id = t.id AND a.doc_type = d.doc_type AND a.version = d.version);
                """
            )
        ).rowcount
    return int(users or 0) + int(companies or 0)
