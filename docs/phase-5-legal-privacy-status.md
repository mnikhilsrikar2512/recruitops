# Phase 5 — Legal, privacy, provisioning: status

Decisions for this phase (2026-10-08) are D-5a to D-5c below; see `decisions-2026-10-06.md`.

- **Order:** 5.1 legal and 5.4 audit viewer, then 5.3 privacy requests, then 5.2 self-serve signup and ops provisioning. Each step is verified before the next.
- **Privacy scope:** whole-company export and delete, plus single-candidate export and erasure.
- **Company delete:** requested by one admin and approved by a second admin of the same company. A sole admin re-confirms with two-step verification instead. The delete then waits 7 days, during which it can be cancelled. Audit rows are kept 90 days after the purge.

## 5.1 Legal versions and acceptance — built, awaiting verify
- **Migration `026_legal.sql`:**
  - `legal_documents` holds platform-wide texts, with one active version per type: `tos`, `privacy` and `dpa`.
  - `legal_acceptances` records the user, company, exact version, time, IP and browser for each acceptance.
  - Version 1 of each document is seeded as a placeholder marked **DRAFT — NOT LEGAL TEXT**. The Privacy placeholder lists the topics the final text must cover: the automated-scoring disclosure and the 90-day audit hold.
- **Who accepts what:**
  - Terms and Privacy: every user.
  - DPA: once per company, by someone with `settings.update`, on the company's behalf.
  - A newer version asks for acceptance again. A stale version number returns 409.
- **API:**
  - `GET /legal/documents` is public.
  - `GET /legal/acceptances` shows what the caller still owes.
  - `POST /legal/acceptances` records an acceptance and is audited as `legal.accepted`.
  - `GET /legal/acceptances/company` returns the company's record.
- **UI:**
  - `legal.html`: public reader, linked from the sign-in page.
  - `legal-acceptance.html`: every app page sends a signed-in user here while they owe an acceptance. The check runs once per 30 minutes per tab and resets at sign-in.
- **Publishing (ops):**
  - `backend/scripts/publish_legal.py --type tos --title "…" --file terms.md --by you` publishes a new version.
  - `--list` shows the documents in force.
- **Go-live gate:**
  - With `APP_ENV=production`, the API refuses to start while any document in force is a placeholder.
  - Staging keeps the placeholders on purpose.
- **Seeds:** CI and staging personas get acceptances recorded, so the browser sweeps aren't stopped by the acceptance page.

## 5.4 Audit log viewer — built, awaiting verify
- **API (`audit_log.read`):**
  - `GET /audit-logs/` filters by actor, record type and id, action and date range. Filters are strict, and results are paged 50 at a time (100 at most).
  - `GET /audit-logs/facets` lists the record types and actions for the filter menus.
  - `GET /audit-logs/{id}` returns the before and after values.
- **Company scope:** every query is limited to the caller's company. A row belongs to the company through its office or, when it has no office, through the person who acted.
- **New audit events:** `session.revoked` and `session.revoked_others`. Two-step verification changes and privacy requests are audited by their own flows.
- **UI:** `audit-log-viewer.html`, under Admin → Audit Log, with filters, paging and a details dialog. It is in the PRD admin sidebar test.
- **Test:** `test_legal_audit_db.py`.
