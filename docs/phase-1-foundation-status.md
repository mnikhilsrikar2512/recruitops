# Phase 1 — Foundation: status

**Date:** 2026-10-05 · **Plan:** `recruitops-production-readiness-execution-plan.md` §4 Phase 1
**Branch:** `phase-1-foundation` (based on `main` @ `0b2aeaa` + the uncommitted working tree it found)

## 1. Root cause, corrected

The decision log (Q1) and the execution plan (§1) state that `apiRequest` "is defined
nowhere" and that items 5 and 6 fail because no data loader exists. That was true of the
**uncommitted working tree**, not of the code base:

| | `frontend/shared/api-client.js` | `apiRequest` | page loaders |
|---|---|---|---|
| Committed (`0b2aeaa`) | 5,978 lines | defined (line 96) | ~70 route loaders + 203 call sites |
| Working tree before this branch | 805 lines | re-added | **none** (all deleted) |

The working tree replaced the committed client with an RBAC-gate-only file. That deleted
every page loader, form submitter and the notification badge poller, so pages rendered
their hidden prototype templates only. The working tree then began re-implementing
loaders piecemeal in `app.js` (`loadApprovalsInbox`, `loadRoleDashboard`), which would
have shadowed the originals.

**Fix:** the committed data layer was restored and the working tree's useful changes were
merged into it (see §2). Nothing in the backend needed to change for the pages to load data.

## 2. What changed

### Frontend data layer (plan 1.2–1.5)
- `apiRequest()` now throws a structured `ApiError { status, detail, errors }` parsed from
  the backend's error envelope (`main.py`), JSON-encodes plain-object bodies, and has a
  pluggable 401 handler (the Phase 3 refresh-and-retry hook). A 401 on `login.html` no
  longer wipes the page; bad credentials show "Authentication Failed".
- `syncUserPermissions()` refreshes `/auth/me` + `/permissions/me` on every page boot
  (reusing a sync younger than 60 s), on tab focus/visibility, and every 5 minutes, and
  re-renders the sidebar when grants change (RBAC spec §4.1).
- Logout is one delegated listener, so the sidebar link that `navigation.js` re-renders
  still calls `POST /auth/logout` (before: it navigated away and the server session
  stayed alive).
- `bootRBACGate` kept for `login.html`'s inline hook; duplicate loaders removed from `app.js`.

### Bugs found by the new gates and fixed
| Found by | Bug | Fix |
|---|---|---|
| contract check | `POST /users/{id}/reset-credentials` (route is `/credentials/reset`) | path |
| contract check | `POST /notifications/{id}/read` (route is `PATCH`) | method + body |
| contract check | `POST /candidates/duplicates/{id}/decide` (no such route) | `/candidates/{id}/duplicate-check/decision` with the schema's decision values |
| undefined-identifier check | `renderInterviewDetail`, `workloadStatus` called but never defined (interview detail and team workload pages threw) | implemented in `renderers.js` |
| undefined-identifier check | `badgePollTimerDelay/ScheduledAt` undeclared | declared |
| browser sweep | report viewer requested `GET /reports/` — the filter hydrator rebuilt the report-type `<select>` | `data-no-filter` opt-out |
| browser sweep | stage-move dialog threw `reading 'badges'` with no remembered candidate | guard |
| UI flow | stage-move "Confirm Transition" only showed a toast — never called the API | calls `PATCH /pipeline/applications/{id}/stage` (rejection uses the canonical `rejected` code + reason) |
| UI flow | requisition intake could not create: client/location were free-text inputs (no ids), default priority `standard` is not a valid `RequisitionPriority` | real client/location selects, `standard` → `medium`, redirect to the new requisition |
| review | `currentUserId()` / `currentLocationId()` silently fell back to id **1** | return `null` |
| review | error handling matched `"403"`/`"409"` inside message strings | uses `error.status` |
| review | `frontend/server.js` resolved request paths without a root check | confined to `frontend/`; `nosniff`/frame/referrer headers |

### Config (plan 1.6)
- `CORS_ORIGINS` defaults to the dev origins (4174/3000) instead of `*`; CORS methods and
  headers are explicit.
- `validate_settings()`: `APP_ENV=staging|production` refuses to boot with wildcard or
  `http://` origins, an empty `DB_PASSWORD`, or `AI_ENABLED=true`.
- AI flag (D-10): agents API answers 404 in staging/production. Tests:
  `backend/tests/test_config_safety.py`.
- Scaffolding settings for S3, Redis and JWT (not yet consumed); `.env.example` documents all.
- `requirements.txt` / `requirements-dev.txt` added (the READMEs referenced a missing file).
- `start.sh` / `serve.sh` / `serve.py` now start the Node server with the `/api` proxy on
  :4174 (they used `python -m http.server`, which has no proxy); `start_backend.sh` no
  longer hard-codes one machine's path; API binds to 127.0.0.1.

### CI (plan 1.1) — `.github/workflows/ci.yml` (shipped as `tools/ci/github-workflow-ci.yml` — move it there to enable)
- **backend:** ODBC 18 + deps → ruff (report-only until the baseline is clean) →
  config guardrail tests → `scripts/run_tests_ci.sh` (throwaway SQL Server, schema, seed, pytest).
- **frontend:** `tools/ci/run_frontend_checks.sh`:
  syntax → undefined identifiers → API contract → static assets → browser sweep of all
  101 pages as **admin** and **recruiter** → 7 end-to-end UI flows.
  The sweep and flows run against `frontend/tests/mock-api-server.js`, which is generated
  from the backend's OpenAPI document (`backend/scripts/export_openapi.py`): unknown
  paths, wrong methods, bad path/query params and request bodies that fail the pydantic
  schema are recorded as violations and fail the build.

## 3. Phase 1 exit gate

| Gate | Status | Evidence |
|---|---|---|
| A page-level test loads a list through the API for each core module | **Met (against the contract mock)** | sweep `LIVE_DATA_CHECKS`: clients, requisitions, candidates, pipeline, approvals, notifications, users render API rows |
| No `ReferenceError` in the browser console across all pages | **Met** | sweep: 101/101 pages clean as admin and as recruiter (denied pages show Access Denied, not errors) |
| CI green and required for merge | **Workflow added; not yet run on GitHub** | turn on branch protection → require `Backend tests` and `Frontend gates` |

UI flows passing: login (bad + good credentials), create client, create requisition,
approve, pipeline stage move, mark notification read, logout.

## 4. Completion of 1.7 and 1.8

| Item | Delivered |
|---|---|
| 1.7 fresh dual-tenant seed | `backend/scripts/seed_staging.py` — on top of `seed_ci.py`, builds two isolated tenants (Northwind Staffing — Bengaluru, Contoso Talent — Hyderabad), each with a Manager and Recruiter role + user, 2 clients, 2 requisitions, 3 candidates at 3 stages and a pending approval, all through the real API. Idempotent; verifies every persona can sign in. A tenant is a branch until Phase 2.1 adds `tenants`. |
| 1.8 re-baselined smoke test | `docs/staging-smoke-test.md` (v2, replaces assessment §3 with the §6.3 corrections and no waivers) + `tools/ci/live_smoke.py` (27 automated API checks: auth, token replay, isolation A↔B, RBAC 403s, happy path, 422 envelope, CORS, pagination) + `page_sweep.py --live` (signs in through `login.html`, then sweeps every page against the real backend). |

## 5. The one remaining step: run it on a machine with the stack

Everything above was built and exercised against the contract mock in a sandbox
that cannot install the backend's Python packages or reach SQL Server, so the
following has **not yet been run against the real backend**. On your Mac:

```bash
# 0. enable CI (this session could not write under .github/)
mkdir -p .github/workflows && git mv tools/ci/github-workflow-ci.yml .github/workflows/ci.yml

# 1. backend tests (throwaway SQL Server in Docker; or SKIP_DOCKER=1 for your local DB)
cd backend && .venv/bin/pip install -r requirements-dev.txt
DB_PORT=1434 ./scripts/run_tests_ci.sh

# 2. fresh staging DB + seed (D-12: never your dev DB)
#    create an empty DB, apply db/schema.sql + ../scripts/00X_*.sql, then:
DB_NAME=recruitops_staging .venv/bin/python scripts/seed_staging.py

# 3. run the stack against it and smoke-test
cd .. && DB_NAME=recruitops_staging ./start.sh        # second terminal for the rest
python3 tools/ci/live_smoke.py --base http://127.0.0.1:4174
pip install playwright && python3 -m playwright install chromium
python3 frontend/tests/page_sweep.py --base http://127.0.0.1:4174 --live
python3 frontend/tests/page_sweep.py --base http://127.0.0.1:4174 --live \
  --email recruiter@northwind-staging.test --password 'Staging#2026-Recruit' --persona recruiter
```

Phase 1 is closed when steps 1–3 pass (every `auto` row in the smoke test) and CI is
green and required on `main`.

## 6. Deferred out of Phase 1 (by design)

| Item | Why |
|---|---|
| Tailwind via CDN (`cdn.tailwindcss.com`) | Not for production use; compile the CSS at build time in Phase 6 (6.1). |
| Admin bypass (`role_code == "admin"`) | Removing it needs the D-03 seed migration in the same change (Phase 2.5 + 2.6, risk register row 1). |
| Smoke rows marked "FAIL until Phase N" | Owned by Phases 2–6; tracked in `staging-smoke-test.md`, not waived. |
