"""Staging/demo seed: a fresh database with TWO isolated tenants (plan 1.7, D-12).

Runs on top of scripts/seed_ci.py (permission catalog, admin, Head Office) and
then builds, per tenant, through the real HTTP API in-process (so every row
goes through the same validation and branch attribution as production):

    branch → Manager + Recruiter roles → 2 users with passwords →
    2 clients → 2 requisitions → 3 candidates → applications at 3 stages →
    1 pending approval

Until Phase 2 adds a physical `tenants` table, a tenant is a branch and
everything scoped to it (the current isolation model). Re-running is safe:
a tenant whose manager account already exists is left untouched.

Usage (fresh staging DB, never a copy of dev — decision D-12):
    cd backend && .venv/bin/python scripts/seed_staging.py
    STAGING_PASSWORD='…' .venv/bin/python scripts/seed_staging.py   # custom password
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

import seed_ci  # noqa: E402
from app.db.session import create_db_engine  # noqa: E402
from app.main import create_application  # noqa: E402

PASSWORD = os.environ.get("STAGING_PASSWORD", "Staging#2026-Recruit")
ADMIN = ("ci.admin@recruitops-test.com", seed_ci.ADMIN_PASSWORD)

RECRUITER_CODES = [
    "candidate.read", "candidate.create", "candidate.update", "candidate.link_requisition",
    "candidate.duplicate.check", "candidate.resume.upload",
    "pipeline.read.summary", "pipeline.read.detail", "pipeline.stage.move", "pipeline.stage.history.read",
    "requisition.read", "client.read", "client.contact.read",
    "interview.read", "interview.create", "interview.feedback.submit",
    "offer.read", "meeting.read", "meeting.create",
    "daily_update.read", "daily_update.create_main", "dashboard.read_my_work",
    "notification.read", "notification.mark_read",
]
MANAGER_CODES = RECRUITER_CODES + [
    "requisition.create", "requisition.update", "requisition.assign", "requisition.status.update",
    "client.create", "client.update", "client.contact.create", "client.contact.update",
    "offer.create", "offer.decide", "approval.read", "approval.decide", "approval.create",
    "report.read", "dashboard.read_pipeline_summary", "user.read",
]

TENANTS = [
    {
        "key": "A", "branch": "Northwind Staffing — Bengaluru", "code": "STGA", "city": "Bengaluru",
        "domain": "northwind-staging.test",
        "clients": [("Acumen Fintech", "Financial Services"), ("Helios Health", "Healthcare")],
        "requisitions": ["Senior Backend Engineer", "Clinical Data Analyst"],
        "candidates": ["Ananya Rao", "Karthik Menon", "Divya Pillai"],
    },
    {
        "key": "B", "branch": "Contoso Talent — Hyderabad", "code": "STGB", "city": "Hyderabad",
        "domain": "contoso-staging.test",
        "clients": [("Orbit Logistics", "Logistics"), ("Lumen Retail", "Retail")],
        "requisitions": ["Supply Chain Planner", "Store Operations Lead"],
        "candidates": ["Farhan Qureshi", "Sneha Reddy", "Vivek Sharma"],
    },
]
STAGES = ["sourced", "screening", "interview"]


class Api:
    def __init__(self, client: TestClient, token: str | None = None):
        self.client = client
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}

    def call(self, method: str, path: str, payload: dict | None = None, ok=(200, 201)):
        response = self.client.request(method, f"/api/v1{path}", json=payload, headers=self.headers)
        if response.status_code not in ok:
            raise SystemExit(f"{method} {path} failed ({response.status_code}): {response.text[:400]}")
        return response.json() if response.content else {}


def login(client: TestClient, email: str, password: str) -> Api:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    if response.status_code != 200:
        raise SystemExit(f"login failed for {email} ({response.status_code}): {response.text[:200]}")
    return Api(client, response.json()["token"])


def ensure_branch(engine, tenant: dict) -> int:
    with engine.begin() as connection:
        return int(connection.execute(
            text(
                """
                IF NOT EXISTS (SELECT 1 FROM dbo.branches WHERE code = :code)
                    INSERT INTO dbo.branches (name, code, location, status, offers_enabled)
                    VALUES (:name, :code, :city, N'active', 1);
                SELECT id FROM dbo.branches WHERE code = :code;
                """
            ),
            {"code": tenant["code"], "name": tenant["branch"], "city": tenant["city"]},
        ).scalar_one())


def user_exists(engine, email: str) -> bool:
    with engine.connect() as connection:
        return connection.execute(text("SELECT 1 FROM dbo.users WHERE email = :e"), {"e": email}).first() is not None


def create_role(admin: Api, tenant: dict, label: str, codes: list[str]) -> int:
    role = admin.call("POST", "/roles/", {
        "name": f"{label} ({tenant['code']})",
        "code": f"{label.lower()}-{tenant['code'].lower()}",
        "description": f"Staging {label.lower()} role for {tenant['branch']}",
    })
    admin.call("PUT", f"/roles/{role['id']}/permissions", {"permission_codes": sorted(set(codes)), "scope_rules": {}})
    return role["id"]


def create_user(client: TestClient, admin: Api, name: str, email: str, branch_id: int, role_id: int,
                title: str, manager_id: int | None = None) -> int:
    payload = {
        "full_name": name, "email": email, "employee_code": email.split("@")[0].upper()[:40],
        "primary_location_id": branch_id, "primary_role_id": role_id, "business_title": title,
    }
    if manager_id:
        payload["reporting_manager_user_id"] = manager_id
    user = admin.call("POST", "/users/", payload)
    reset = admin.call("POST", f"/users/{user['id']}/credentials/reset", {"mode": "setup-link", "issued_by_user_id": 1})
    Api(client).call("POST", "/auth/password/setup", {"token": reset["setup_token"], "new_password": PASSWORD})
    return user["id"]


def seed_tenant(client: TestClient, engine, admin: Api, tenant: dict) -> dict:
    manager_email = f"manager@{tenant['domain']}"
    recruiter_email = f"recruiter@{tenant['domain']}"
    if user_exists(engine, manager_email):
        print(f"• tenant {tenant['key']} already seeded — skipping")
        return {"manager": manager_email, "recruiter": recruiter_email}

    branch_id = ensure_branch(engine, tenant)
    manager_role = create_role(admin, tenant, "Manager", MANAGER_CODES)
    recruiter_role = create_role(admin, tenant, "Recruiter", RECRUITER_CODES)
    manager_id = create_user(client, admin, f"{tenant['city']} Delivery Manager", manager_email,
                             branch_id, manager_role, "Delivery Manager")
    recruiter_id = create_user(client, admin, f"{tenant['city']} Recruiter", recruiter_email,
                               branch_id, recruiter_role, "Recruiter", manager_id)

    clients = [
        admin.call("POST", "/clients/", {
            "client_name": f"{name} ({tenant['code']})", "industry": industry, "location_id": branch_id,
            "client_owner_user_id": manager_id, "business_source_owner_user_id": manager_id,
            "placement_fee_pct": 8.33,
        })["id"]
        for name, industry in tenant["clients"]
    ]
    requisitions = [
        admin.call("POST", "/requisitions/", {
            "client_id": clients[i % len(clients)], "location_id": branch_id, "title": title,
            "primary_owner_user_id": recruiter_id, "openings_count": 2, "priority": "high" if i == 0 else "medium",
            "target_closure_date": "2026-12-31", "employment_type": "full-time", "work_mode": "hybrid",
            "must_have_skills": ["communication"], "job_description": f"{title} for {tenant['branch']} (staging seed).",
        })["id"]
        for i, title in enumerate(tenant["requisitions"])
    ]
    applications = []
    for i, name in enumerate(tenant["candidates"]):
        slug = name.lower().replace(" ", ".")
        candidate = admin.call("POST", "/candidates/", {
            "full_name": name, "email": f"{slug}@{tenant['domain']}", "phone": f"+91 9{len(tenant['key']) + ord(tenant['key']) % 10}000 {i:05d}",
            "source_type": "LinkedIn", "current_company": "Example Corp", "current_designation": "Engineer",
            "total_experience_years": 3 + i, "primary_owner_user_id": recruiter_id, "save_mode": "final",
        })
        admin.call("GET", f"/candidates/{candidate['id']}/duplicate-check")
        link = admin.call("POST", f"/candidates/{candidate['id']}/applications", {
            "requisition_id": requisitions[i % len(requisitions)], "initial_stage": STAGES[i % len(STAGES)],
            "owner_user_id": recruiter_id,
        })
        applications.append(link.get("application_id") or link.get("id"))

    admin.call("POST", "/approvals/", {
        "location_id": branch_id, "approval_type": "requisition", "related_entity_type": "requisition",
        "related_entity_id": requisitions[0], "title": f"Approve {tenant['requisitions'][0]} headcount",
        "description": "Staging seed: pending headcount approval.", "priority": "high",
        "requester_user_id": recruiter_id, "assigned_reviewer_user_id": manager_id,
    })
    print(f"✓ tenant {tenant['key']} ({tenant['branch']}): 2 users, {len(clients)} clients, "
          f"{len(requisitions)} requisitions, {len(applications)} applications, 1 approval")
    return {"manager": manager_email, "recruiter": recruiter_email}


def main() -> None:
    seed_ci.main()  # permission catalog, admin, Head Office (idempotent)
    engine = create_db_engine()
    with TestClient(create_application(), raise_server_exceptions=True) as client:
        admin = login(client, *ADMIN)
        accounts = [seed_tenant(client, engine, admin, tenant) for tenant in TENANTS]
        # Prove each persona can sign in with the seeded password.
        for account in accounts:
            for email in account.values():
                login(client, email, PASSWORD)

    print("\nStaging personas (password: $STAGING_PASSWORD, default shown in seed_staging.py):")
    print(f"  Admin (control plane)  {ADMIN[0]}")
    for tenant, account in zip(TENANTS, accounts):
        print(f"  Tenant {tenant['key']} manager     {account['manager']}")
        print(f"  Tenant {tenant['key']} recruiter   {account['recruiter']}")


if __name__ == "__main__":
    main()
