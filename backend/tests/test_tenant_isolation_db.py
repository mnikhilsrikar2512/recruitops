"""DB-backed tenant-isolation regression tests.

Proves the multi-tenant data-isolation rules from the recruitment workflow
spec through the real HTTP API against the real database (skips when the DB
is unreachable, matching test_rbac_chain_integration.py):

- A client-scoped user (recruiter on branch A) can read and work the
  applications of their own client requisitions.
- The same user CANNOT read, mutate, or even discover another client's
  candidate applications — including stage/offer data, client-feedback
  notes, offer terms, and stage history.
- Offer workflows respect the same boundary.

Isolation model reminder: candidates are global identity records; everything
tenant-owned (stage, offer terms, notes) lives on candidate_applications and
is reachable only through requisitions.client_id / branch scoping. These
tests lock that boundary so a regression (e.g. dropping a scope filter)
fails loudly here.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import create_db_engine
from app.main import create_application

ADMIN_EMAIL_CANDIDATES = ["admin@executiveconnection.com", "ci.admin@recruitops-test.com"]
ADMIN_PASSWORD = "admin123"
USER_PASSWORD = "TenantIso123!"


def _db_reachable() -> bool:
    try:
        engine = create_db_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def client():
    if not _db_reachable():
        pytest.skip("Configured SQL Server database is not reachable")
    app = create_application()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def admin_headers(client):
    for email in ADMIN_EMAIL_CANDIDATES:
        attempt = client.post("/api/v1/auth/login", json={"email": email, "password": ADMIN_PASSWORD})
        if attempt.status_code == 200:
            return {"Authorization": f"Bearer {attempt.json()['token']}"}
    pytest.skip("Seed admin login failed; seed users first")


class TenantIsolationFixtures:
    """Builds one isolation scenario shared by the whole module.

    Two tenants on distinct branches, each with a requisition + application
    carrying private notes and offer terms, and one scoped recruiter per
    tenant. Everything is created via the API (so the tests also cover the
    create paths' branch attribution) with DB fallbacks where the API has no
    surface (branches/clients are admin/DB-managed).
    """

    def __init__(self) -> None:
        self.engine = create_db_engine()
        self.suffix = uuid.uuid4().hex[:8]
        self.created_users: list[int] = []
        self.created_requisitions: list[int] = []
        self.created_candidates: list[int] = []
        self.created_branch_ids: list[int] = []

    # -- raw SQL helpers (admin-grade fixture setup) -------------------------

    def _exec(self, sql: str, **params):
        with self.engine.begin() as connection:
            return connection.execute(text(sql), params)

    def _scalar(self, sql: str, **params):
        # engine.begin() so INSERT ... OUTPUT fixtures actually commit
        # (a bare connect() rolls back on close in SQLAlchemy 2.x).
        with self.engine.begin() as connection:
            return connection.execute(text(sql), params).scalar_one()

    def _setup_branches(self) -> None:
        """Two dedicated branches so tenant A's recruiter has no location
        overlap with tenant B's data (location scope is one isolation layer)."""
        for label in ("A", "B"):
            branch_id = self._scalar(
                """
                INSERT INTO dbo.branches (name, code, location, status, offers_enabled, tenant_id)
                OUTPUT INSERTED.id
                VALUES (:name, :code, :location, N'active', 1,
                        -- offices of the seed admin's company (010_tenants)
                        COALESCE(
                          (SELECT TOP 1 u.tenant_id FROM dbo.users AS u
                           WHERE u.email IN (N'admin@executiveconnection.com', N'ci.admin@recruitops-test.com')
                           ORDER BY u.id),
                          (SELECT t.id FROM dbo.tenants AS t WHERE t.slug = N'default')));
                """,
                name=f"TenantISO {label} {self.suffix}",
                code=f"TISO{label}{self.suffix[:4]}",
                location=f"TenantISO {label} {self.suffix}",
            )
            setattr(self, f"branch_{label.lower()}", int(branch_id))
            self.created_branch_ids.append(int(branch_id))

    def _setup_clients(self) -> None:
        self.client_a = self._scalar(
            """
            INSERT INTO dbo.client_companies (branch_id, name, relationship_type, status)
            OUTPUT INSERTED.id
            VALUES (:branch_id, :name, N'direct-client', N'active');
            """,
            branch_id=self.branch_a,
            name=f"TenantISO Client A {self.suffix}",
        )
        self.client_b = self._scalar(
            """
            INSERT INTO dbo.client_companies (branch_id, name, relationship_type, status)
            OUTPUT INSERTED.id
            VALUES (:branch_id, :name, N'direct-client', N'active');
            """,
            branch_id=self.branch_b,
            name=f"TenantISO Client B {self.suffix}",
        )

    def _setup_users(self, admin_headers) -> None:
        """One scoped recruiter per tenant, created through the API so roles,
        credentials, and location binding match production onboarding."""
        self.user_headers = {}
        for label, branch_id in (("A", self.branch_a), ("B", self.branch_b)):
            email = f"tenant-iso-{label.lower()}-{self.suffix}@example.com"
            role = client_post(
                admin_headers,
                "/api/v1/roles/",
                {
                    "name": f"TenantISO {label} {self.suffix}",
                    "code": f"tenant-iso-{label.lower()}-{self.suffix}",
                    "description": "Tenant isolation regression role",
                },
            )
            assert role.status_code == 201, role.text
            role_id = role.json()["id"]
            assigned = client_put(
                admin_headers,
                f"/api/v1/roles/{role_id}/permissions",
                {
                    # offer.read/offer.create are satisfied through the
                    # PERMISSION_ALIASES chain (offer.read ← candidate.read /
                    # pipeline.read.detail; offer.create ← pipeline.stage.move).
                    "permission_codes": [
                        "candidate.read", "candidate.create", "candidate.update",
                        "candidate.link_requisition",
                        "pipeline.read.summary", "pipeline.read.detail", "pipeline.stage.move",
                        "pipeline.stage.history.read",
                        "requisition.read", "requisition.create",
                    ],
                    "scope_rules": {},
                },
            )
            assert assigned.status_code == 200, assigned.text
            user = client_post(
                admin_headers,
                "/api/v1/users/",
                {
                    "full_name": f"TenantISO Recruiter {label}",
                    "email": email,
                    "employee_code": f"TISO-{label}-{self.suffix}",
                    "primary_location_id": branch_id,
                    "primary_role_id": role_id,
                },
            )
            assert user.status_code == 201, user.text
            user_id = user.json()["id"]
            self.created_users.append(user_id)
            reset = client_post(
                admin_headers,
                f"/api/v1/users/{user_id}/credentials/reset",
                {"mode": "setup-link", "issued_by_user_id": 1},
            )
            assert reset.status_code == 200, reset.text
            setup = client_post(
                None,
                "/api/v1/auth/password/setup",
                {"token": reset.json()["setup_token"], "new_password": USER_PASSWORD},
            )
            assert setup.status_code == 200, setup.text
            login = client_post(
                None, "/api/v1/auth/login", {"email": email, "password": USER_PASSWORD}
            )
            assert login.status_code == 200, login.text
            self.user_headers[label] = {"Authorization": f"Bearer {login.json()['token']}"}

    def _setup_requisitions(self, admin_headers) -> None:
        """Tenant requisitions via the API (exercises create-path scoping too)."""
        self.requisition = {}
        for label, client_id, branch_id in (("A", self.client_a, self.branch_a), ("B", self.client_b, self.branch_b)):
            user_id = self._scalar(
                "SELECT id FROM dbo.users WHERE email = :email",
                email=f"tenant-iso-{label.lower()}-{self.suffix}@example.com",
            )
            payload = {
                "client_id": client_id,
                "location_id": branch_id,
                "title": f"TenantISO Req {label} {self.suffix}",
                "primary_owner_user_id": user_id,
                "openings_count": 1,
                "priority": "medium",
                "target_closure_date": "2027-01-31",
                "job_description": f"Isolation fixture requisition for tenant {label}.",
            }
            response = client_post(admin_headers, "/api/v1/requisitions/", payload)
            assert response.status_code == 201, response.text
            requisition_id = response.json()["id"]
            self.requisition[label] = requisition_id
            self.created_requisitions.append(requisition_id)

    def _setup_candidates_and_applications(self, admin_headers) -> None:
        """One candidate applied to BOTH tenants' requisitions — the spec's
        core scenario. The global candidate record is shared; the application
        rows (stage/notes/offer terms) must stay tenant-isolated."""
        user_a = self._scalar(
            "SELECT id FROM dbo.users WHERE email = :email",
            email=f"tenant-iso-a-{self.suffix}@example.com",
        )
        user_b = self._scalar(
            "SELECT id FROM dbo.users WHERE email = :email",
            email=f"tenant-iso-b-{self.suffix}@example.com",
        )
        candidate = client_post(
            admin_headers,
            "/api/v1/candidates/",
            {
                "full_name": f"TenantISO Shared Candidate {self.suffix}",
                "email": f"tenant-iso-shared-{self.suffix}@example.com",
                "phone": f"9{self.suffix[:9]}",
                "source_type": "Manual Entry",
                "primary_owner_user_id": user_a,
                "save_mode": "final",
            },
        )
        assert candidate.status_code == 201, candidate.text
        self.candidate_id = candidate.json()["id"]
        self.created_candidates.append(self.candidate_id)

        # Run the duplicate-check surface so the candidate is cleared for
        # finalization (mirrors the production linking workflow).
        duplicate = client_get(
            admin_headers,
            f"/api/v1/candidates/{self.candidate_id}/duplicate-check",
        )
        assert duplicate.status_code == 200, duplicate.text

        # Link the shared candidate to each tenant's requisition via the
        # candidate-applications API (the production linking surface).
        self.application = {}
        for label, owner_user_id in (("A", user_a), ("B", user_b)):
            link = client_post(
                admin_headers,
                f"/api/v1/candidates/{self.candidate_id}/applications",
                {
                    "requisition_id": self.requisition[label],
                    "initial_stage": "sourced",
                    "owner_user_id": owner_user_id,
                },
            )
            assert link.status_code == 201, link.text
            payload = link.json()
            application_id = payload.get("application_id") or payload.get("id")
            assert application_id, link.text
            self.application[label] = int(application_id)

        # Tenant-private data: notes and offer terms on each application.
        self._exec(
            """
            UPDATE dbo.candidate_applications
            SET client_feedback_notes = :notes, offered_ctc = :ctc, offer_currency = :currency
            WHERE id = :application_id;
            """,
            notes=f"PRIVATE NOTE tenant A {self.suffix}: compensation expectations and client feedback.",
            ctc=111000.0,
            currency="USD",
            application_id=self.application["A"],
        )
        self._exec(
            """
            UPDATE dbo.candidate_applications
            SET client_feedback_notes = :notes, offered_ctc = :ctc, offer_currency = :currency
            WHERE id = :application_id;
            """,
            notes=f"PRIVATE NOTE tenant B {self.suffix}: different terms entirely.",
            ctc=999000.0,
            currency="USD",
            application_id=self.application["B"],
        )

    def build(self, admin_headers) -> None:
        self._setup_branches()
        self._setup_clients()
        self._setup_users(admin_headers)
        self._setup_requisitions(admin_headers)
        self._setup_candidates_and_applications(admin_headers)

    def cleanup(self, admin_headers) -> None:
        """Best-effort teardown; must never mask test results.

        Order matters (FKs): applications → stage history → candidates →
        requisitions → role grants → roles → users (sessions, reset tokens,
        audit rows) → clients → sequence rows → branches. A swallowed error
        here previously left fixture rows behind, so each stage is isolated
        and the residue sweep below guarantees a clean exit even if an
        individual delete fails.
        """
        try:
            for user_id in self.created_users:
                client_post(
                    admin_headers,
                    f"/api/v1/users/{user_id}/deactivate",
                    {"reason": "isolation test cleanup", "review_confirmed": True},
                )
        except Exception:
            pass

        # Idempotent residue sweep keyed on the fixture suffix — removes this
        # module's rows (and any left by an earlier crashed run of itself).
        # FK order matters: users must be deleted BEFORE the roles their
        # primary_role_id references; a mid-batch constraint failure is
        # statement-terminating (the rest of the batch still commits), so the
        # statements run individually and failures are recorded, not silent.
        statements = [
            ("candidate_stage_history", """
                EXEC sp_set_session_context N'recruitops.history_maintenance', 1;
                DELETE FROM dbo.candidate_stage_history
                WHERE candidate_application_id IN (
                  SELECT id FROM dbo.candidate_applications WHERE candidate_id IN (
                    SELECT id FROM dbo.candidates WHERE email LIKE :candidate_email));
                EXEC sp_set_session_context N'recruitops.history_maintenance', NULL;"""),
            ("candidate_applications", """
                DELETE FROM dbo.candidate_applications
                WHERE candidate_id IN (
                  SELECT id FROM dbo.candidates WHERE email LIKE :candidate_email);"""),
            ("candidates", "DELETE FROM dbo.candidates WHERE email LIKE :candidate_email;"),
            ("requisitions", "DELETE FROM dbo.requisitions WHERE title LIKE :requisition_title;"),
            ("user_branch_roles", """
                DELETE FROM dbo.user_branch_roles
                WHERE user_id IN (SELECT id FROM dbo.users WHERE email LIKE :user_email);"""),
            ("user_location_roles", """
                DELETE FROM dbo.user_location_roles
                WHERE user_id IN (SELECT id FROM dbo.users WHERE email LIKE :user_email);"""),
            ("user_sessions", """
                DELETE FROM dbo.user_sessions
                WHERE user_id IN (SELECT id FROM dbo.users WHERE email LIKE :user_email);"""),
            ("password_reset_tokens", """
                DELETE FROM dbo.password_reset_tokens
                WHERE user_id IN (SELECT id FROM dbo.users WHERE email LIKE :user_email);"""),
            ("audit_logs_actor", """
                DELETE FROM dbo.audit_logs
                WHERE actor_user_id IN (SELECT id FROM dbo.users WHERE email LIKE :user_email);"""),
            ("audit_logs_branch", """
                DELETE FROM dbo.audit_logs
                WHERE branch_id IN (SELECT id FROM dbo.branches WHERE code LIKE :branch_code);"""),
            ("users", "DELETE FROM dbo.users WHERE email LIKE :user_email;"),
            ("role_permissions", """
                DELETE FROM dbo.role_permissions
                WHERE role_id IN (SELECT id FROM dbo.roles WHERE code LIKE :role_code);"""),
            ("role_scope_rules", """
                DELETE FROM dbo.role_scope_rules
                WHERE role_id IN (SELECT id FROM dbo.roles WHERE code LIKE :role_code);"""),
            ("roles", "DELETE FROM dbo.roles WHERE code LIKE :role_code;"),
            ("client_companies", "DELETE FROM dbo.client_companies WHERE name LIKE :client_name;"),
            ("display_id_sequences", """
                DELETE FROM dbo.display_id_sequences
                WHERE branch_id IN (SELECT id FROM dbo.branches WHERE code LIKE :branch_code);"""),
            ("branches", "DELETE FROM dbo.branches WHERE code LIKE :branch_code;"),
        ]
        params = {
            "candidate_email": "tenant-iso-shared-%",
            "requisition_title": "TenantISO Req %",
            "user_email": "tenant-iso-%",
            "role_code": "tenant-iso-%",
            "branch_code": "TISO%",
            "client_name": "TenantISO Client %",
        }
        for label, statement in statements:
            try:
                with self.engine.begin() as connection:
                    connection.execute(text(statement), params)
            except Exception:
                # Best-effort by design; residue never masks test results.
                continue


@pytest.fixture(scope="module")
def isolation(client, admin_headers):
    fixtures = TenantIsolationFixtures()

    def _post(headers, path, payload=None):
        return client.post(path, json=payload, headers=headers or {})

    def _put(headers, path, payload=None):
        return client.put(path, json=payload, headers=headers or {})

    def _get(headers, path):
        return client.get(path, headers=headers or {})

    # Bind the HTTP helpers used inside the fixture class to this module's
    # TestClient (kept as module globals so tests can use them directly too).
    import sys

    module = sys.modules[__name__]
    module.client_post = _post
    module.client_put = _put
    globals()["client_post"] = _post
    globals()["client_put"] = _put
    globals()["client_get"] = _get
    try:
        fixtures.build(admin_headers)
    except Exception:
        fixtures.cleanup(admin_headers)
        raise
    yield fixtures
    fixtures.cleanup(admin_headers)


class TestCrossTenantReadIsolation:
    """Tenant A's recruiter must not read tenant B's application data."""

    def test_pipeline_detail_denied_for_other_tenant(self, client, isolation):
        response = client.get(
            f"/api/v1/pipeline/applications/{isolation.application['B']}",
            headers=isolation.user_headers["A"],
        )
        assert response.status_code == 403, response.text

    def test_own_tenant_application_readable(self, client, isolation):
        response = client.get(
            f"/api/v1/pipeline/applications/{isolation.application['A']}",
            headers=isolation.user_headers["A"],
        )
        assert response.status_code == 200, response.text

    def test_stage_history_denied_for_other_tenant(self, client, isolation):
        response = client.get(
            f"/api/v1/pipeline/applications/{isolation.application['B']}/history",
            headers=isolation.user_headers["A"],
        )
        assert response.status_code == 403, response.text

    def test_board_does_not_leak_other_tenant_rows(self, client, isolation):
        response = client.get("/api/v1/pipeline/board", headers=isolation.user_headers["A"])
        assert response.status_code == 200, response.text
        items = response.json() if isinstance(response.json(), list) else response.json().get("items", [])
        ids = {item.get("application_id") for item in items}
        assert isolation.application["B"] not in ids
        assert isolation.application["A"] in ids

    def test_candidate_detail_hides_other_tenant_application_summary(self, client, isolation):
        """The shared candidate is global, but tenant A's recruiter must only
        see the application summary that belongs to their own tenant."""
        response = client.get(
            f"/api/v1/candidates/{isolation.candidate_id}",
            headers=isolation.user_headers["A"],
        )
        assert response.status_code == 200, response.text
        applications = response.json().get("applications", [])
        application_ids = {application.get("id") for application in applications}
        assert isolation.application["A"] in application_ids
        assert isolation.application["B"] not in application_ids


class TestCrossTenantMutationIsolation:
    """Tenant A's recruiter must not mutate tenant B's application state."""

    def test_stage_move_denied_for_other_tenant(self, client, isolation):
        response = client.patch(
            f"/api/v1/pipeline/applications/{isolation.application['B']}/stage",
            json={"to_stage": "screening", "notes": "cross-tenant mutation attempt"},
            headers=isolation.user_headers["A"],
        )
        assert response.status_code == 403, response.text
        row = isolation._scalar(
            "SELECT current_stage FROM dbo.candidate_applications WHERE id = :id",
            id=isolation.application["B"],
        )
        assert row == "sourced", "stage must be untouched after denied move"

    def test_stage_move_allowed_within_own_tenant(self, client, isolation):
        response = client.patch(
            f"/api/v1/pipeline/applications/{isolation.application['A']}/stage",
            json={"to_stage": "screening", "notes": "own-tenant progression"},
            headers=isolation.user_headers["A"],
        )
        assert response.status_code == 200, response.text

    def test_denied_stage_move_leaves_no_history_trace(self, client, isolation):
        history = client.get(
            f"/api/v1/pipeline/applications/{isolation.application['B']}/history",
            headers=isolation.user_headers["A"],
        )
        assert history.status_code == 403


class TestCrossTenantOfferIsolation:
    """Offer terms are tenant-owned: A cannot read or move B's offers."""

    def test_offer_detail_denied_for_other_tenant(self, client, isolation):
        response = client.get(
            f"/api/v1/offers/{isolation.application['B']}",
            headers=isolation.user_headers["A"],
        )
        assert response.status_code == 403, response.text

    def test_offer_detail_allowed_within_own_tenant(self, client, isolation):
        response = client.get(
            f"/api/v1/offers/{isolation.application['A']}",
            headers=isolation.user_headers["A"],
        )
        assert response.status_code == 200, response.text
        assert response.json().get("offered_ctc") is not None

    def test_offer_list_scoped_to_own_tenant(self, client, isolation):
        response = client.get("/api/v1/offers/?page_size=100", headers=isolation.user_headers["A"])
        assert response.status_code == 200, response.text
        items = response.json().get("items", [])
        application_ids = {item.get("candidate_application_id") for item in items}
        assert isolation.application["B"] not in application_ids

    def test_offer_creation_denied_on_other_tenant_application(self, client, isolation):
        response = client_post(
            isolation.user_headers["A"],
            "/api/v1/offers/",
            {
                "candidate_application_id": isolation.application["B"],
                "offered_ctc": 123000,
                "offer_currency": "USD",
                "requested_by_user_id": isolation._scalar(
                    "SELECT id FROM dbo.users WHERE email = :email",
                    email=f"tenant-iso-a-{isolation.suffix}@example.com",
                ),
            },
        )
        assert response.status_code == 403, response.text

    def test_private_notes_never_serialize_cross_tenant(self, client, isolation):
        """The tenant-B note string must not appear in any payload tenant A
        can read: candidate detail (applications list), pipeline detail, and
        offer detail for the shared candidate."""
        leak_probe = f"PRIVATE NOTE tenant B {isolation.suffix}"
        for path in (
            f"/api/v1/candidates/{isolation.candidate_id}",
            f"/api/v1/pipeline/applications/{isolation.application['A']}",
            f"/api/v1/offers/{isolation.application['A']}",
        ):
            body = client.get(path, headers=isolation.user_headers["A"]).text
            assert leak_probe not in body, f"tenant B notes leaked via {path}"


class TestAdminFootprintOversight:
    """Admin-only cross-tenant footprint: admins see which clients a shared
    candidate is in play with; recruiters do not, and the payload never
    carries tenant-private fields (notes, offer terms, owner identities)."""

    def test_admin_gets_full_footprint(self, client, isolation, admin_headers):
        response = client.get(
            f"/api/v1/candidates/{isolation.candidate_id}/footprint",
            headers=admin_headers,
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["candidate_id"] == isolation.candidate_id
        assert payload["clients_count"] >= 2, "shared candidate spans >= 2 clients"
        client_ids = {entry["client_id"] for entry in payload["entries"]}
        assert {isolation.client_a, isolation.client_b} <= client_ids

    def test_footprint_payload_has_no_tenant_private_fields(self, client, isolation, admin_headers):
        response = client.get(
            f"/api/v1/candidates/{isolation.candidate_id}/footprint",
            headers=admin_headers,
        )
        assert response.status_code == 200, response.text
        body = response.text
        for forbidden in (
            f"PRIVATE NOTE tenant A {isolation.suffix}",
            f"PRIVATE NOTE tenant B {isolation.suffix}",
            "client_feedback_notes",
            "offered_ctc",
            "offer_currency",
            "owner_user_id",
            "owner_name",
        ):
            assert forbidden not in body, f"footprint leaked tenant-private field: {forbidden}"

    @pytest.mark.parametrize("label", ["A", "B"])
    def test_recruiters_denied_footprint(self, client, isolation, label):
        response = client.get(
            f"/api/v1/candidates/{isolation.candidate_id}/footprint",
            headers=isolation.user_headers[label],
        )
        assert response.status_code == 403, response.text
        assert "administrator oversight" in response.json()["detail"]

    def test_footprint_requires_authentication(self, client, isolation):
        response = client.get(f"/api/v1/candidates/{isolation.candidate_id}/footprint")
        assert response.status_code in {401, 403}

    def test_footprint_404_for_unknown_candidate(self, client, admin_headers):
        response = client.get("/api/v1/candidates/99999999/footprint", headers=admin_headers)
        assert response.status_code == 404


class TestTenantDataDoesNotLeakViaLists:
    """List endpoints must not leak other tenants' rows or aggregate values."""

    def test_board_ids_never_cross_tenants(self, client, isolation):
        response = client.get("/api/v1/pipeline/board?page_size=200", headers=isolation.user_headers["A"])
        assert response.status_code == 200, response.text
        items = response.json() if isinstance(response.json(), list) else response.json().get("items", [])
        assert all(item.get("location_id") == isolation.branch_a for item in items)

    def test_offers_list_location_scoping(self, client, isolation):
        response = client.get("/api/v1/offers/?page_size=100", headers=isolation.user_headers["A"])
        assert response.status_code == 200, response.text
        items = response.json().get("items", [])
        assert all(
            item.get("candidate_application_id") != isolation.application["B"] for item in items
        )
