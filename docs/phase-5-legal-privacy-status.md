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

## 5.3 Privacy requests — built, awaiting verify
- **Migration `027_privacy.sql`:**
  - `privacy_requests` keeps the record of every request. User ids are plain numbers, not links to user rows, so the record survives a purge.
  - `privacy_audit_hold` keeps a purged company's audit and legal-acceptance rows as JSON until their hold date.
  - New columns `tenants.purged_at`, `tenants.audit_hold_days` (default 90) and `candidates.erased_at`.
- **API (`privacy_request.write`, company admins):**
  - `GET /privacy/requests` lists requests; `GET /privacy/requests/{id}` shows one.
  - `POST /privacy/export-request` exports the whole company (202) and builds the zip in the background. Each table becomes one JSON file, with secrets dropped and AI run logs included, plus the stored files. The download works for 7 days.
  - `POST /privacy/delete-request` asks for a whole-company delete. It needs a reason and the word "DELETE" typed to confirm. It creates a "privacy-delete" item in the Approvals inbox.
  - The **second admin** approves in that inbox. The requester's own approval is refused (403), and the decider is always the signed-in user, never an id sent by the browser.
  - When there is no other admin, the requester uses `POST /privacy/requests/{id}/confirm` with a two-step verification code.
  - Once approved, the delete is **scheduled for 7 days later**. Until then, `POST /privacy/requests/{id}/cancel` stops it.
  - `POST /privacy/requests/{id}/download` gives a 15-minute link to an export zip, and each download is audited.
  - `POST /privacy/candidates/{id}/export` exports one candidate at once.
  - `POST /privacy/candidates/{id}/erase` erases one candidate. The admin types the candidate's ID to confirm.
- **Company purge (`app/services/tenant_purge.py`):** one database transaction, driven by the tenancy map and the database's own foreign keys.
  1. Candidates that another company also works with are handed over to that company.
  2. Every row the company owns is marked. Rows that must point to a marked row are marked too, and optional links to marked rows are cleared.
  3. A safety net stops the purge if any marked row belongs to another company, or if a shared table would be touched.
  4. Audit and legal rows are copied to the 90-day hold.
  5. Rows are deleted children-first, then the company's files.
  6. The company row stays as an "archived" tombstone.
- **Candidate erasure (`app/services/candidate_erasure.py`):**
  - **Removed:** name, contacts, pay and location; the resume and every document, including the stored files; parsed resume text; skills; duplicate-check snapshots; and the notes on that company's applications, interviews and stage history.
  - **Kept:** the stages and dates, so reports still count correctly.
  - A candidate another company also works with returns 409. That company must handle its own request, and this company can archive the candidate.
- **Job runner:** `backend/scripts/run_privacy_jobs.py`, run hourly. It runs deletes that are past their 7 days, releases expired holds, and removes expired export zips.
- **UI:**
  - Admin → **Data Export/Delete Requests** (`data-export-delete-request.html`): export, delete, confirm, cancel and download.
  - The candidate page has "Export their data" and "Erase candidate…" buttons.
- **Test (`test_privacy_db.py`):**
  - Two throw-away companies are built, exported and purged. Afterwards nothing owned by the purged company is left, the other company is unchanged, the shared candidate has been handed over, and the hold rows exist and are released after their date.
  - The delete request needs a second admin and can be cancelled.
  - A candidate is exported, downloaded and erased; a shared candidate is refused.
