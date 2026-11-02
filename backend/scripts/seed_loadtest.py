"""Build the load-test company and hand k6 its sign-ins (Phase 6.7).

Run it inside the API container of the environment you are about to load
(staging or the local compose stack), so the tokens are signed with that
environment's own JWT key and the data lands in that environment's database:

    docker compose exec api python scripts/seed_loadtest.py --out /tmp/loadtest.json
    docker compose cp api:/tmp/loadtest.json deploy/loadtest/fixture.json

What it does
------------
1. Creates (once) a separate company, "Loadtest Staffing", with one office and
   its own roles: managers and recruiters, using the same permission sets as the
   staging personas. Nothing touches other companies.
2. Creates (once) realistic volume through the real API, as those people:
   clients, requisitions, candidates and their applications spread over stages.
3. Every run: starts a fresh sign-in (session + JWT) for each load-test user
   and writes them to the fixture file k6 reads.

Why sign-ins are issued here instead of through /auth/login: sign-in is
rate-limited per IP (5/min) and per account on purpose, and a load generator
is one IP. The load test measures the app under recruiting traffic; it must
not need the rate limits loosened. Sessions are created by the same code the
login endpoint uses (app.services.auth._start_session), are real rows in
user_sessions, and can be revoked like any other.

The fixture holds live bearer tokens: it is written 0600 and is git-ignored.
Revoke them after the run with --revoke.

Refuses to run with APP_ENV=production.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.config import settings  # noqa: E402

COMPANY = {
    "key": "L", "company": "Loadtest Staffing", "slug": "loadtest",
    "branch": "Loadtest Staffing — Pune", "code": "LOAD", "city": "Pune",
    "domain": "loadtest.example.com",
}
STAGES = ["sourced", "screening", "interview"]
SOURCES = ["LinkedIn", "Naukri", "Referral", "Job Board", "Walk-in"]
CLIENTS = [("Acme Industries", "Manufacturing"), ("Bluefin Capital", "Financial Services"),
           ("Cedar Health", "Healthcare"), ("Delta Logistics", "Logistics"), ("Ember Retail", "Retail"),
           ("Fjord Software", "Technology"), ("Granite Infra", "Construction"), ("Harbor Foods", "FMCG"),
           ("Iris Telecom", "Telecom"), ("Juniper Energy", "Energy")]
TITLES = ["Backend Engineer", "Data Analyst", "Sales Manager", "Accountant", "HR Generalist", "Plant Supervisor",
          "Product Designer", "Support Lead", "Business Analyst", "QA Engineer", "Store Manager", "DevOps Engineer"]
FIRST = ["Aarav", "Diya", "Ishaan", "Meera", "Rohan", "Sara", "Kabir", "Anika", "Vihaan", "Tara",
         "Arjun", "Nisha", "Dev", "Kiara", "Reyansh", "Pooja", "Aditya", "Riya", "Yash", "Zoya"]
LAST = ["Sharma", "Iyer", "Khan", "Patel", "Reddy", "Das", "Nair", "Gupta", "Singh", "Joshi",
        "Menon", "Rao", "Bose", "Kulkarni", "Shah", "Pillai", "Verma", "Chopra", "Mehta", "Ghosh"]


def _email(kind: str, n: int) -> str:
    return f"{kind}{n:03d}@{COMPANY['domain']}"


def _users(engine) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT u.id, u.email FROM dbo.users u JOIN dbo.tenants t ON t.id = u.tenant_id "
            "WHERE t.slug = :slug AND u.status = N'active' AND (u.email LIKE N'manager%' OR u.email LIKE N'recruiter%') "
            "ORDER BY u.email"), {"slug": COMPANY["slug"]}).mappings().all()
    return [{"id": int(r["id"]), "email": r["email"], "role": "manager" if r["email"].startswith("manager") else "recruiter"}
            for r in rows]


def _build_people(client, engine, admin_api, branch_id: int, admin_id: int, managers: int, recruiters: int) -> None:
    from seed_staging import MANAGER_CODES, RECRUITER_CODES, create_role, user_exists  # noqa: PLC0415

    existing = {u["email"] for u in _users(engine)}
    if len(existing) >= managers + recruiters:
        return
    with engine.connect() as connection:
        roles = dict(connection.execute(text(
            "SELECT code, id FROM dbo.roles WHERE tenant_id = (SELECT id FROM dbo.tenants WHERE slug = :s)"),
            {"s": COMPANY["slug"]}).all())
    manager_role = roles.get("manager-load") or create_role(admin_api, COMPANY, "Manager", MANAGER_CODES)
    recruiter_role = roles.get("recruiter-load") or create_role(admin_api, COMPANY, "Recruiter", RECRUITER_CODES)
    for kind, count, role, title in (("manager", managers, manager_role, "Delivery Manager"),
                                     ("recruiter", recruiters, recruiter_role, "Recruiter")):
        for n in range(1, count + 1):
            email = _email(kind, n)
            if email in existing or user_exists(engine, email):
                continue
            admin_api.call("POST", "/users/", {
                "full_name": f"Load {kind.title()} {n:03d}", "email": email,
                "employee_code": f"LT-{kind[:3].upper()}-{n:03d}",
                "primary_location_id": branch_id, "primary_role_id": role, "business_title": title,
            })
    # People created through the API wait for a password; load-test people
    # never sign in with one, so mark them set up (sessions are issued below).
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE dbo.users SET password_setup_status = N'active', force_password_change_on_first_login = 0 "
            "WHERE tenant_id = (SELECT id FROM dbo.tenants WHERE slug = :s) AND id <> :admin"),
            {"s": COMPANY["slug"], "admin": admin_id})


def _has_data(engine) -> bool:
    with engine.connect() as connection:
        return bool(connection.execute(text(
            "SELECT COUNT(*) FROM dbo.requisitions r JOIN dbo.branches b ON b.id = r.branch_id "
            "JOIN dbo.tenants t ON t.id = b.tenant_id WHERE t.slug = :s"), {"s": COMPANY["slug"]}).scalar_one())


def _build_data(client, apis: dict[int, object], users: list[dict], branch_id: int, *, requisitions: int,
                candidates: int, rng: random.Random) -> None:
    managers = [u for u in users if u["role"] == "manager"]
    recruiters = [u for u in users if u["role"] == "recruiter"]
    lead = apis[managers[0]["id"]]
    client_ids = [
        lead.call("POST", "/clients/", {
            "client_name": f"{name} (LOAD)", "industry": industry, "location_id": branch_id,
            "client_owner_user_id": managers[0]["id"], "business_source_owner_user_id": managers[0]["id"],
            "placement_fee_pct": 8.33,
        })["id"]
        for name, industry in CLIENTS
    ]
    print(f"  {len(client_ids)} clients")
    reqs_by_owner: dict[int, list[int]] = {r["id"]: [] for r in recruiters}
    for i in range(requisitions):
        owner = recruiters[i % len(recruiters)]
        manager = managers[i % len(managers)]
        title = TITLES[i % len(TITLES)]
        rid = apis[manager["id"]].call("POST", "/requisitions/", {
            "client_id": client_ids[i % len(client_ids)], "location_id": branch_id, "title": f"{title} #{i + 1}",
            "primary_owner_user_id": owner["id"], "openings_count": rng.randint(1, 4),
            "priority": rng.choice(["high", "medium", "low"]), "target_closure_date": "2027-06-30",
            "employment_type": "full-time", "work_mode": rng.choice(["hybrid", "onsite", "remote"]),
            "must_have_skills": ["communication"], "job_description": f"{title} (load-test data).",
        })["id"]
        reqs_by_owner[owner["id"]].append(rid)
    print(f"  {requisitions} requisitions")
    for n in range(candidates):
        owner = recruiters[n % len(recruiters)]
        api = apis[owner["id"]]
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        candidate = api.call("POST", "/candidates/", {
            "full_name": name, "email": f"cand{n:05d}@cand.loadtest.example.com", "phone": f"+91 98{n:08d}",
            "source_type": rng.choice(SOURCES), "current_company": "Example Corp", "current_designation": "Associate",
            "total_experience_years": rng.randint(1, 15), "primary_owner_user_id": owner["id"], "save_mode": "final",
        })
        api.call("GET", f"/candidates/{candidate['id']}/duplicate-check")
        api.call("POST", f"/candidates/{candidate['id']}/applications", {
            "requisition_id": rng.choice(reqs_by_owner[owner["id"]]), "initial_stage": rng.choice(STAGES),
            "owner_user_id": owner["id"],
        })
        if (n + 1) % 250 == 0:
            print(f"  {n + 1}/{candidates} candidates")


def _fixture(engine, users: list[dict], tokens: dict[int, str], branch_id: int, expires_at: datetime) -> dict:
    with engine.connect() as connection:
        apps = connection.execute(text(
            "SELECT ca.id, ca.owner_user_id, ca.candidate_id FROM dbo.candidate_applications ca "
            "JOIN dbo.requisitions r ON r.id = ca.requisition_id "
            "WHERE r.branch_id = :b AND ca.application_status = N'active' AND r.status NOT IN (N'on-hold', N'closed')"),
            {"b": branch_id}).all()
        reqs = [int(r[0]) for r in connection.execute(text(
            "SELECT id FROM dbo.requisitions WHERE branch_id = :b"), {"b": branch_id}).all()]
    by_owner: dict[int, dict[str, list[int]]] = {}
    for app_id, owner, candidate in apps:
        slot = by_owner.setdefault(int(owner), {"applications": [], "candidates": []})
        slot["applications"].append(int(app_id))
        slot["candidates"].append(int(candidate))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tokens_expire_at": expires_at.isoformat(),
        "branch_id": branch_id,
        "requisitions": reqs,
        "users": [{**u, "token": tokens[u["id"]], **by_owner.get(u["id"], {"applications": [], "candidates": []})}
                  for u in users],
    }


def _issue_sessions(engine, emails: list[str], hours: float) -> tuple[dict[str, tuple[int, str]], datetime]:
    """One fresh sign-in per person, through the login code path's own helper."""
    from app.repositories.auth import find_user_for_login  # noqa: PLC0415
    from app.services.auth import _start_session  # noqa: PLC0415

    ttl = settings.jwt_access_ttl_minutes
    settings.jwt_access_ttl_minutes = int(hours * 60)  # only for tokens issued by this process
    try:
        out, expires_at = {}, datetime.now(timezone.utc)
        for email in emails:
            user = find_user_for_login(engine, email)
            _session, access, _refresh, expires_at = _start_session(engine, user, "loadtest-seed", "seed_loadtest.py")
            out[email] = (int(user.id), access)
        return out, expires_at
    finally:
        settings.jwt_access_ttl_minutes = ttl


def revoke(engine) -> int:
    with engine.begin() as connection:
        return connection.execute(text(
            "UPDATE s SET s.revoked_at = SYSUTCDATETIME() FROM dbo.user_sessions s JOIN dbo.users u ON u.id = s.user_id "
            "JOIN dbo.tenants t ON t.id = u.tenant_id WHERE t.slug = :s AND s.revoked_at IS NULL"),
            {"s": COMPANY["slug"]}).rowcount


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default="loadtest-fixture.json", help="where to write the k6 fixture (tokens: keep private)")
    ap.add_argument("--managers", type=int, default=6)
    ap.add_argument("--recruiters", type=int, default=44)
    ap.add_argument("--requisitions", type=int, default=120)
    ap.add_argument("--candidates", type=int, default=3000)
    ap.add_argument("--token-hours", type=float, default=2.0, help="lifetime of the issued access tokens")
    ap.add_argument("--revoke", action="store_true", help="end every load-test sign-in and exit")
    args = ap.parse_args()

    if settings.is_production or os.environ.get("APP_ENV", "").lower() == "production":
        raise SystemExit("✗ refusing to seed load-test data into production (APP_ENV=production)")

    from app.db.session import create_db_engine  # noqa: PLC0415
    engine = create_db_engine()
    if args.revoke:
        print(f"✓ revoked {revoke(engine)} load-test sign-ins")
        return
    if args.managers < 1 or args.recruiters < 1:
        raise SystemExit("✗ need at least one manager and one recruiter")

    from app.main import create_application  # noqa: PLC0415
    from app.repositories.legal import seed_accept_current_for_all_users  # noqa: PLC0415
    from seed_staging import Api, ensure_company  # noqa: PLC0415

    branch_id, admin_email, admin_id = ensure_company(engine, COMPANY)
    rng = random.Random(6_7)
    with TestClient(create_application(), raise_server_exceptions=True) as client:
        admin_tokens, _ = _issue_sessions(engine, [admin_email], 0.5)
        admin_api = Api(client, admin_tokens[admin_email][1])
        _build_people(client, engine, admin_api, branch_id, admin_id, args.managers, args.recruiters)
        users = [u for u in _users(engine)
                 if (u["role"] == "manager" and int(u["email"][7:10]) <= args.managers)
                 or (u["role"] == "recruiter" and int(u["email"][9:12]) <= args.recruiters)]
        issued, expires_at = _issue_sessions(engine, [u["email"] for u in users], args.token_hours)
        tokens = {uid: token for uid, token in issued.values()}
        if not _has_data(engine):
            print(f"• building data for {COMPANY['company']} (first run only)")
            apis = {u["id"]: Api(client, tokens[u["id"]]) for u in users}
            _build_data(client, apis, users, branch_id, requisitions=args.requisitions,
                        candidates=args.candidates, rng=rng)
    seed_accept_current_for_all_users(engine)
    with engine.begin() as connection:  # the admin's sign-in was only for set-up
        connection.execute(text("UPDATE dbo.user_sessions SET revoked_at = SYSUTCDATETIME() "
                                "WHERE user_id = :u AND revoked_at IS NULL"), {"u": admin_id})

    fixture = _fixture(engine, users, tokens, branch_id, expires_at)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        json.dump(fixture, handle)
    apps = sum(len(u["applications"]) for u in fixture["users"])
    print(f"✓ {len(users)} sign-ins ({sum(u['role'] == 'manager' for u in users)} managers), "
          f"{len(fixture['requisitions'])} requisitions, {apps} open applications → {out} "
          f"(tokens valid until {expires_at:%H:%M} UTC; revoke with --revoke)")


if __name__ == "__main__":
    main()
