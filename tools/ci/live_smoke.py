#!/usr/bin/env python3
"""Live smoke test against a running RecruitOps stack (plan 1.8, §6.3).

Automates the API half of docs/staging-smoke-test.md against a real backend +
database seeded with backend/scripts/seed_staging.py. Standard library only.

    python tools/ci/live_smoke.py --base http://127.0.0.1:4174
    python tools/ci/live_smoke.py --base https://staging.example.com --password "$STAGING_PASSWORD"

--base is the frontend origin (its /api proxy) or the API origin itself.
Exit code 1 if any check fails. Creates a small amount of data (one client,
requisition, candidate, application) under tenant A — run on staging, not prod.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

ADMIN = ("ci.admin@recruitops-test.com", "admin123")
TENANT_A = ("manager@northwind-staging.example.com", "recruiter@northwind-staging.example.com")
TENANT_B = ("manager@contoso-staging.example.com", "recruiter@contoso-staging.example.com")
COMPANY_ADMINS = ("admin@northwind-staging.example.com", "admin@contoso-staging.example.com")

results: list[tuple[str, bool, str]] = []


def check(step: str, ok: bool, detail: str = "") -> bool:
    results.append((step, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {step}{'  — ' + detail if detail and not ok else ''}")
    return bool(ok)


class Api:
    def __init__(self, base: str):
        self.base = base.rstrip("/")
        self.token: str | None = None

    def call(self, method: str, path: str, body=None, headers=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"{self.base}/api/v1{path}", data=data, method=method)
        req.add_header("Accept", "application/json")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        for key, value in (headers or {}).items():
            req.add_header(key, value)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                return resp.status, (json.loads(raw) if raw else {}), dict(resp.headers)
        except urllib.error.HTTPError as err:
            raw = err.read()
            try:
                payload = json.loads(raw) if raw else {}
            except ValueError:
                payload = {"raw": raw.decode(errors="replace")[:300]}
            return err.code, payload, dict(err.headers)

    def login(self, email: str, password: str) -> bool:
        status, payload, _ = self.call("POST", "/auth/login", {"email": email, "password": password})
        self.token = payload.get("token") if status == 200 else None
        return status == 200


def leaks(payload) -> bool:
    text = json.dumps(payload)
    return "Traceback" in text or "SELECT " in text or "pyodbc" in text


def items(payload) -> list:
    return payload.get("items", []) if isinstance(payload, dict) else payload or []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:4174")
    ap.add_argument("--password", default="Staging#2026-Recruit", help="seed_staging.py persona password")
    ap.add_argument("--admin-password", default=ADMIN[1])
    opts = ap.parse_args()
    base = opts.base

    print("── Stage 0: pre-flight")
    anon = Api(base)
    status, health, _ = anon.call("GET", "/health")
    check("0.1 GET /health", status == 200, f"{status} {health}")

    print("── Stage 1: auth & session")
    admin = Api(base)
    check("1.1 admin login", admin.login(ADMIN[0], opts.admin_password))
    rec_a, mgr_a, rec_b = Api(base), Api(base), Api(base)
    check("1.2 tenant A recruiter login", rec_a.login(TENANT_A[1], opts.password))
    check("1.2 tenant A manager login", mgr_a.login(TENANT_A[0], opts.password))
    check("1.2 tenant B recruiter login", rec_b.login(TENANT_B[1], opts.password))
    bad = Api(base)
    status, payload, _ = bad.call("POST", "/auth/login", {"email": TENANT_A[1], "password": "wrong-password"})
    check("1.3 wrong password → 401, clean body", status == 401 and not leaks(payload), f"{status} {payload}")
    throwaway = Api(base)
    throwaway.login(TENANT_A[1], opts.password)
    old_token = throwaway.token
    throwaway.call("POST", "/auth/logout")
    throwaway.token = old_token
    status, _, _ = throwaway.call("GET", "/auth/me")
    check("1.4 token replay after logout → 401", status == 401, str(status))
    if not all(api.token for api in (admin, rec_a, mgr_a, rec_b)):
        print("\nPersona logins failed — is the database seeded (backend/scripts/seed_staging.py) "
              "and is --base pointing at the stack that uses it? Stopping early.")
        print(f"\n{sum(r[1] for r in results)}/{len(results)} smoke checks passed")
        return 1
    status, perms, _ = rec_a.call("GET", "/permissions/me")
    check("1.5 /permissions/me returns grants", status == 200 and perms.get("permissions"), str(status))

    print("── Stage 2: tenant isolation")
    status, reqs_a, _ = rec_a.call("GET", "/requisitions/?page_size=100")
    status_b, reqs_b, _ = rec_b.call("GET", "/requisitions/?page_size=100")
    titles_a = {r.get("title") for r in items(reqs_a)}
    titles_b = {r.get("title") for r in items(reqs_b)}
    check("2.1 recruiter A sees own requisitions", status == 200 and "Senior Backend Engineer" in titles_a, str(titles_a))
    check("2.1 recruiter A sees none of tenant B's", not ({"Supply Chain Planner", "Store Operations Lead"} & titles_a), str(titles_a))
    check("2.1 recruiter B sees none of tenant A's", status_b == 200 and not ({"Senior Backend Engineer", "Clinical Data Analyst"} & titles_b), str(titles_b))
    b_ids = [r["id"] for r in items(reqs_b)]
    if b_ids:
        status, payload, _ = rec_a.call("GET", f"/requisitions/{b_ids[0]}")
        check("2.2 A reading B's requisition by id → 403/404", status in (403, 404) and not leaks(payload), str(status))
    status, clients_a, _ = mgr_a.call("GET", "/clients/?page_size=100")
    client_names = {c.get("client_name") for c in items(clients_a)}
    check("2.1 manager A's clients exclude tenant B", status == 200 and not any("(STGB)" in (n or "") for n in client_names), str(client_names))
    status, approvals_a, _ = mgr_a.call("GET", "/approvals/?page_size=100")
    check("2.1 manager A's approvals exclude tenant B",
          status == 200 and not any("Supply Chain Planner" in (a.get("title") or "") for a in items(approvals_a)),
          str([a.get("title") for a in items(approvals_a)]))
    status, board_a, _ = rec_a.call("GET", "/pipeline/board")
    names_a = {r.get("candidate_name") for r in items(board_a)}
    check("2.2 pipeline board isolated", status == 200 and not ({"Farhan Qureshi", "Sneha Reddy", "Vivek Sharma"} & names_a), str(names_a))

    print("── Stage 2b: company isolation (company admins, Phase 2)")
    adm_a, adm_b = Api(base), Api(base)
    check("2.3 company A admin login", adm_a.login(COMPANY_ADMINS[0], opts.password))
    check("2.3 company B admin login", adm_b.login(COMPANY_ADMINS[1], opts.password))
    if adm_a.token and adm_b.token:
        status, appr, _ = adm_a.call("GET", "/approvals/?page_size=100")
        titles = {a.get("title") or "" for a in items(appr)}
        check("2.3 company admin A sees company A's approvals", status == 200 and any("Senior Backend Engineer" in t for t in titles), str(titles))
        check("2.3 company admin A sees none of company B's approvals",
              not any("Supply Chain Planner" in t or "Store Operations Lead" in t for t in titles), str(titles))
        status, appr_b, _ = adm_b.call("GET", "/approvals/?page_size=100")
        b_approval = next(iter(items(appr_b)), {}).get("id")
        if b_approval:
            status, payload, _ = adm_a.call("GET", f"/approvals/{b_approval}")
            check("2.3 company admin A reading B's approval by id → 404", status == 404 and not leaks(payload), str(status))
        status, locs, _ = adm_a.call("GET", "/locations/?page_size=100")
        codes = {loc.get("location_code") for loc in items(locs)}
        check("2.3 company admin A's offices are company A's only", status == 200 and "STGA" in codes and "STGB" not in codes, str(codes))
        status, users, _ = adm_a.call("GET", "/users/?page_size=100")
        emails = {u.get("email") for u in items(users)}
        check("2.3 company admin A's users exclude company B",
              status == 200 and not any("contoso-staging" in (e or "") for e in emails), str(sorted(emails))[:200])
        a_office = next((loc.get("id") for loc in items(locs) if loc.get("location_code") == "STGA"), None)
        status, roles, _ = adm_b.call("GET", "/roles/?page_size=100")
        b_role = next((r.get("id") for r in items(roles) if r.get("code") == "recruiter-stgb"), None)
        if a_office and b_role:
            status, payload, _ = adm_b.call("POST", "/users/", {
                "full_name": "Cross Company", "email": f"cross.{int(time.time())}@contoso-staging.example.com",
                "employee_code": f"X{int(time.time())}", "primary_location_id": a_office, "primary_role_id": b_role})
            check("2.3 company admin B cannot place a user in company A's office → 404", status == 404, f"{status} {payload}")
    if adm_a.token:
        print("── Stage 2c: Admin is the control plane, by grant (D-03, plan 2.5)")
        status, perms, _ = adm_a.call("GET", "/permissions/me")
        check("2.4 company admin holds scope.company", status == 200 and "scope.company" in perms.get("permissions", []), str(status))
        for path in ("/users/", "/roles/", "/locations/", "/approvals/", "/reports/time-to-fill"):
            status, _, _ = adm_a.call("GET", path)
            check(f"2.4 company admin passes control-plane {path} → 200", status == 200, str(status))
        for path in ("/candidates/", "/requisitions/", "/clients/", "/pipeline/board"):
            status, _, _ = adm_a.call("GET", path)
            check(f"2.4 company admin denied execution {path} → 403", status == 403, str(status))
    status, reqs, _ = admin.call("GET", "/requisitions/?page_size=100")
    titles = {r.get("title") for r in items(reqs)}
    check("2.3 CI company admin sees neither staging company",
          status == 200 and not ({"Senior Backend Engineer", "Supply Chain Planner"} & titles), str(titles))

    print("── Stage 3: RBAC")
    status, _, _ = rec_a.call("GET", "/users/")
    check("3.4 recruiter denied user admin API → 403", status == 403, str(status))
    status, _, _ = rec_a.call("POST", "/roles/", {"name": "x", "code": "xx"})
    check("3.4 recruiter denied role creation → 403", status == 403, str(status))
    status, _, _ = admin.call("GET", "/users/?page_size=5")
    check("3.1 admin reaches control-plane API", status == 200, str(status))

    print("── Stage 4: core happy path (tenant A manager)")
    me = mgr_a.call("GET", "/auth/me")[1]
    loc_id, mgr_id = me["primary_location"]["id"], me["user"]["id"]
    rec_id = rec_a.call("GET", "/auth/me")[1]["user"]["id"]
    stamp = time.strftime("%H%M%S")
    status, client, _ = mgr_a.call("POST", "/clients/", {
        "client_name": f"Smoke Client {stamp}", "location_id": loc_id,
        "client_owner_user_id": mgr_id, "business_source_owner_user_id": mgr_id})
    check("4.1 create client", status == 201, f"{status} {client}")
    status, req, _ = mgr_a.call("POST", "/requisitions/", {
        "client_id": client.get("id"), "location_id": loc_id, "title": f"Smoke Requisition {stamp}",
        "primary_owner_user_id": rec_id, "openings_count": 1, "priority": "medium",
        "target_closure_date": "2026-12-31", "job_description": "Live smoke test requisition."})
    check("4.1 create requisition", status == 201, f"{status} {req}")
    status, cand, _ = rec_a.call("POST", "/candidates/", {
        "full_name": f"Smoke Candidate {stamp}", "email": f"smoke.{stamp}@northwind-staging.example.com",
        "source_type": "Referral", "primary_owner_user_id": rec_id, "save_mode": "final"})
    check("4.1 create candidate", status == 201, f"{status} {cand}")
    rec_a.call("GET", f"/candidates/{cand.get('id')}/duplicate-check")
    status, link, _ = rec_a.call("POST", f"/candidates/{cand.get('id')}/applications", {
        "requisition_id": req.get("id"), "initial_stage": "sourced", "owner_user_id": rec_id})
    app_id = link.get("application_id") or link.get("id")
    check("4.1 link candidate → application", status == 201 and app_id, f"{status} {link}")
    status, move, _ = rec_a.call("PATCH", f"/pipeline/applications/{app_id}/stage", {
        "to_stage": "screening", "notes": "Smoke test stage move"})
    check("4.2 move stage", status == 200, f"{status} {move}")
    status, approvals, _ = mgr_a.call("GET", "/approvals/?status=pending&page_size=20")
    pending = items(approvals)
    check("4.2 manager sees pending approval", status == 200 and pending, f"{status} {approvals}")
    if pending:
        status, decided, _ = mgr_a.call("PATCH", f"/approvals/{pending[0]['id']}/decide", {
            "decision": "approved", "decision_notes": "Smoke test approval", "decision_user_id": mgr_id})
        check("4.2 decide approval", status == 200, f"{status} {decided}")
    status, notes, _ = rec_a.call("GET", "/notifications/?page_size=5")
    check("4.3 notifications list loads", status == 200, str(status))

    print("── Stage 5: guardrails")
    status, payload, _ = mgr_a.call("POST", "/requisitions/", {"title": ""})
    check("7.1 invalid payload → 422 envelope, no traceback",
          status == 422 and isinstance(payload.get("detail"), str) and not leaks(payload), f"{status} {payload}")
    status, payload, headers = anon.call("OPTIONS", "/health", headers={
        "Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    allowed = {k.lower(): v for k, v in headers.items()}.get("access-control-allow-origin")
    check("7.3 CORS: disallowed origin not echoed", allowed not in ("*", "https://evil.example"), str(allowed))
    status, payload, _ = rec_a.call("GET", "/requisitions/?page_size=2")
    meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
    check("7.2 list pagination meta", status == 200 and {"page", "page_size", "total"} <= set(meta), str(meta))

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} smoke checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
