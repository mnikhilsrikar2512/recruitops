"""Setup checklist for a new company's admins (frontend cleanup F.1).

Replaces the prototype onboarding wizard. Nothing is ticked by hand: each
item is done when the company's own data says so, so the list stays true
however the admin got there (this page, a later visit, an import).
The only stored state is tenants.setup_checklist_dismissed_at.
"""
from __future__ import annotations

from sqlalchemy import Engine, text

from app.services.tenant_data import predicate

# key, title, why, page, optional, SQL that counts the rows that make it done, how many are needed
ITEMS: list[tuple[str, str, str, str, bool, str, int]] = [
    ("offices", "Add your offices",
     "Requisitions, clients and people belong to an office. Sign-up created a Head Office; add the rest.",
     "location-management.html", True,
     "SELECT COUNT(*) FROM dbo.branches AS x WHERE x.status = N'active' AND " + predicate("branches", "x"), 2),
    ("team", "Invite your team",
     "Add recruiters and managers so work can be assigned to them.",
     "user-management.html", False,
     "SELECT COUNT(*) FROM dbo.users AS x WHERE x.status = N'active' AND " + predicate("users", "x"), 2),
    ("stages", "Set your hiring stages",
     "The stages every candidate moves through. Clients can have their own list later.",
     "stage-bucket-map.html", False,
     "SELECT COUNT(*) FROM dbo.pipeline_templates AS x WHERE x.status = N'active' AND " + predicate("pipeline_templates", "x"), 1),
    ("client", "Add your first client",
     "Skip this if you only hire for your own company.",
     "client-directory.html", True,
     "SELECT COUNT(*) FROM dbo.client_companies AS x WHERE x.archived_at IS NULL AND " + predicate("client_companies", "x"), 1),
    ("requisition", "Open your first requisition",
     "A requisition is a role you are hiring for. Candidates are added against it.",
     "requisition-intake.html", False,
     "SELECT COUNT(*) FROM dbo.requisitions AS x WHERE " + predicate("requisitions", "x"), 1),
]


def checklist(engine: Engine, tenant_id: int) -> dict:
    with engine.connect() as connection:
        dismissed = connection.execute(
            text("SELECT setup_checklist_dismissed_at FROM dbo.tenants WHERE id = :tenant"), {"tenant": tenant_id}
        ).scalar()
        items = []
        for key, title, why, page, optional, sql, needed in ITEMS:
            count = int(connection.execute(text(sql), {"tenant": tenant_id}).scalar() or 0)
            items.append({"key": key, "title": title, "description": why, "page": page,
                          "optional": optional, "done": count >= needed})
    required = [i for i in items if not i["optional"]]
    return {
        "items": items,
        "done": sum(1 for i in items if i["done"]),
        "total": len(items),
        "complete": all(i["done"] for i in required),
        "dismissed": dismissed is not None,
    }


def set_dismissed(engine: Engine, tenant_id: int, dismissed: bool) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE dbo.tenants SET setup_checklist_dismissed_at = "
                 "CASE WHEN :d = 1 THEN SYSUTCDATETIME() ELSE NULL END WHERE id = :tenant"),
            {"d": 1 if dismissed else 0, "tenant": tenant_id},
        )
