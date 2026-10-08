# Phase 4 — Files, data integrity, lifecycle: status

Branch: `phase-4-data-integrity` (from `phase-3-security`).

Order of work: the parts that need nothing from outside first (4.5 → 4.6 → 4.3 → 4.4 → 4.8 → 4.7 → 4.9); file storage and scanning (4.1, 4.2) last, since they need the cloud choice (I-2).

## 4.5 Metric buckets (P0) — built

**What changed**

- Migration `scripts/016_metric_buckets.sql`:
  - `dbo.metric_buckets`: the fixed, ordered bucket list.
  - `dbo.stage_bucket_map`: maps stage labels to buckets. Rows with no company are the platform defaults; a company's own row overrides the default for that company.
  - `pipeline_template_stages` gains `metric_bucket` and `is_terminal`.
  - `candidate_stage_history` gains `from_bucket` and `to_bucket`. Existing rows are backfilled.
  - Two functions do all the label matching: `dbo.fn_metric_bucket` and `dbo.fn_application_stage_bucket`.
  - The view `dbo.vw_application_metric_state` gives each application's current bucket.
  - Two triggers: `trg_stage_history_fill_buckets` records the buckets on every new history row, whoever writes it; `trg_stage_history_append_only` blocks edits and deletes of history rows.
- A label is resolved in this order:
  1. The application's pipeline template stage.
  2. The company's own mapping.
  3. The platform default mapping.
  4. A guess from the stage name.
  5. `interview` if nothing else matches.
- History rows keep the bucket they had when they were written, so changing a mapping later does not rewrite past reports.
- `reports.py`: all 11 literal stage checks now use buckets (7 on history `to_bucket = 'joined'`, 4 on the current bucket through the view). Affected reports: Time to Fill, SLA, Source Effectiveness, Placements and Client Summary.
- `dashboards.py`: "submitted profiles" counts the `submitted` bucket. It used to match a list of 3 labels.
- Stage moves set `application_status` from the target stage's bucket (joined, rejected or withdrawn). Before, only 4 hard-coded labels did this.
- **Stage Bucket Map** admin page (`stage-bucket-map.html`) and API:
  - `GET /settings/stage-buckets` needs `settings.read`.
  - `PUT /settings/stage-buckets/{stage}` and `DELETE /settings/stage-buckets/{stage}` need `settings.update`.
  - Every change is audited (`stage_bucket.set` / `stage_bucket.reset`).
- Governed maintenance path: `app/db/maintenance.py history_maintenance()` sets SESSION_CONTEXT `recruitops.history_maintenance`. It is the only way to delete history rows (for the Phase 5 privacy purge and test cleanup). The flag is cleared before the connection goes back to the pool.

**Decision D-4.5a — 8 buckets, not 7.** The spec has 7 buckets: sourced, screened, interview, offer, joined, rejected, withdrawn. We added `submitted`, ordered between screened and interview. Without it, the dashboard's "profiles with the client" count would have needed raw stage labels again.

**Where the 5 live non-baseline labels now land:**

| Label | Bucket |
|---|---|
| Executive Review | interview |
| Technical Interview | interview |
| shortlisted | screened |
| internal-screening | screened |
| some-untemplated-stage | interview |

**Tests:** `tests/test_metric_buckets_db.py` covers the exit gate:
- The live labels resolve to the right buckets.
- History buckets are snapshotted, edits and deletes are refused, and the maintenance path works.
- A custom "Onboarding" label and a company-mapped "Start Date Confirmed" label both appear in Placements.
- Mapping changes are audited.

**Expected effect:** report and dashboard numbers can go up after migration 016, because applications in custom stages are now counted instead of dropped.

**Left for later:**
- Overlay inheritance, materialised `requisition_pipeline_stages`, and scorecards (spec P2).
- Scalar-function cost in the view, to be revisited in the Phase 6 load test.

**First verify run (`17b97fa`):** 475 passed, 2 failed. Source Effectiveness returned 500 because SQL Server does not allow a subquery inside an aggregate. Fixed by joining `vw_application_metric_state` instead.

## 4.6 Terminal-state guard + reopen — built

- **Rules read buckets, not labels.** `move_pipeline_stage_service` resolves the current and target buckets: from the template stage's `metric_bucket` when it has one, otherwise from `dbo.fn_application_stage_bucket`. All rules below apply to companies' own stage names too.
- **Closed applications stay closed.** An application whose status or bucket is joined, rejected or withdrawn cannot move again. The move is refused with 409 and a "reopen it first" message.
- **Moving back needs a reason.** A backward move without `notes` is refused with 409. The order comes from the template stage order when there is one, otherwise from the bucket order. With a note, the move is allowed and the note is written to history. Closing moves (reject, withdraw, join) never count as backward.
- **Withdrawing needs a reason** (422 without one), as rejecting already did.
- The offer-tracking toggle check now uses the `offer` bucket instead of looking for "offer" in the stage name.
- **Reopen:** `POST /pipeline/applications/{id}/reopen` with `{to_stage, reason}` and permission `pipeline.stage.reopen`.
  - Only closed applications can be reopened, and only into an open stage.
  - The application status goes back to `active` and the rejection fields are cleared.
  - A new history row is added with `source_type = 'reopen'`; old history rows are never changed.
  - The action is audited as `pipeline.reopen`.
- **Migration `017_pipeline_reopen.sql`** adds the permission code and grants it once to every role holding both `pipeline.stage.move` and `requisition.update`, which are the manager-shaped roles. Recruiters and the Admin template do not get it. The PRD §3.2 row is updated.
- **Unit tests without a database** resolve buckets through the Python copy of the stage map (`app/core/stage_buckets.py`, via a conftest shim). `tests/test_stage_buckets_twin.py` fails if that copy drifts from the 016 seed.
- **Tests:** `tests/test_pipeline_lifecycle_db.py` covers backward moves needing a reason, withdraw as a closed state, the reopen rules, history rows and the audit entry.
- **Still to do in the UI:** a Reopen button on the application view. The API is ready; the button lands with the 4.3 conflict dialog work.

**Second verify run (`3745536`):** 483 passed, smoke 52/52, sweeps 105/105. 016 and 017 applied to dev.

## 4.3 Optimistic locking — built

Built on work that was already in the tree but not committed (migration 018, `versioning.py`, schema and repository changes). Reviewed and finished in this commit.

- **Migration `018_row_versions.sql`** adds `version INT NOT NULL DEFAULT 1` to `candidates`, `requisitions` and `candidate_applications`.
- **Every UPDATE of those tables bumps `version`.** This includes user-deactivation transfers, offers, duplicate state and assignments. `tests/test_row_versions_static.py` scans `app/` and fails on any UPDATE that forgets the bump.
- **Edits can carry the version the client loaded.** `CandidateUpdate`, `RequisitionUpdate`, `RequisitionStatusUpdate`, `PipelineStageMove`, `PipelineReopen` and `OfferDecisionUpdate` accept an optional `version`.
  - `check_version` reads the row under UPDLOCK/HOLDLOCK in the same transaction, so two writers serialise.
  - A stale version raises `StaleWriteConflict`. The API answers 409 with `{code: "stale_write", current_version, current: <fresh record>}`.
  - An edit without a version is not checked, so older clients and system writes keep working.
- **Detail responses include `version`:** candidate, requisition, pipeline application and stage-move responses. The candidate detail response was missing it and is now fixed.
- **Frontend (`api-client.js`):**
  - Detail reads remember each record's version.
  - Candidate edit, requisition edit and status change, stage move, and reopen send that version automatically.
  - A `stale_write` 409 opens a "This record changed" dialog with **Reload latest** and **Keep my screen**.
- **Exit gate:** `tests/test_row_versions_db.py` runs two edits against the same loaded version, for a candidate, a requisition and a stage move. The second edit gets 409 with the fresh row, and an edit without a version still succeeds.

**Third verify run (`e8ec25b`):** 487 passed, smoke 52/52, sweeps 105/105. 018 applied to dev.

## 4.4 Soft delete (D-07) — built

- **Migration `019_soft_delete.sql`:**
  - `dbo.candidate_archives`: candidates are shared identity records, so an archive belongs to **one company** and hides the candidate from that company only. Rows are kept after a restore as archive history.
  - `client_companies` gains `archived_at`, `archived_by_user_id` and `archive_reason`.
  - Adds the permission codes `candidate.delete.soft` and `client.delete.soft`. One code covers both archive and restore (readiness Q17). They are granted once to manager-shaped roles, the ones that edit the record and also hold `requisition.update`. PRD §3.2 rows added.
- **API:**
  - `POST /candidates/{id}/archive` (reason required) and `POST /candidates/{id}/restore`; the same pair for `/clients/{id}`.
  - Archiving is refused while the candidate still has open applications in the company, or the client still has open requisitions.
  - Every archive and restore is audited.
- **Hidden by default:**
  - The candidate and client lists leave archived records out. `?include_archived=true` needs the delete.soft grant (403 without it).
  - Direct-ID reads answer 404 for callers without the grant. Callers with the grant see the record marked `archived_at`.
  - Archived clients cannot be used for requisitions.
  - The filtering is done in the repository and service layers.
- **Hard delete is still not reachable from the app.**
- **Frontend:** the candidate and client detail pages show an archived banner and an Archive/Restore control (with a reason field) to holders of the grant.
- **Unit tests** see no archives on MagicMock engines (conftest shim); real engines always query `candidate_archives`.
- **Exit gate:** `tests/test_soft_delete_db.py` covers:
  - Archiving is blocked while records are still open.
  - Archived records are hidden from lists and shown with `include_archived`.
  - Direct reads answer 404 without the grant.
  - Restore brings records back.
  - Audit rows and archive history are written.
- **Not in scope:** a "show archived" toggle on the list pages (the API already supports it), and user and company soft delete. Users already have deactivation; company deletion belongs to Phase 5 privacy.

**Fourth verify run (`bd01926`):** 490 passed, smoke 52/52, sweeps 105/105. 019 applied to dev.

## 4.8 Offer approval threshold (D-06) — built

- **Migration `020_offer_threshold.sql`** adds `tenants.offer_approval_threshold DECIMAL(18,2) NOT NULL DEFAULT 0` with a CHECK that it is 0 or more.
- **The rule** (`offers.offer_requires_approval`):
  - Total = CTC + signing bonus.
  - Total above the threshold: the offer goes to `pending-approval` and an `offer-approval` request is created.
  - Total at or below the threshold: the offer goes straight to `approved` and no approval request is created.
  - An offer with no amount yet always goes to approval.
  - The default of 0 sends every paid offer to approval, which is today's behaviour, so nothing changes until a company sets an amount.
- **API:** `GET /settings/offer-approval` (`settings.read`) and `PUT /settings/offer-approval` (`settings.update`; audited as `settings.offer_threshold.set`). Company Settings has a new **Offer approvals** section to set it.
- **One amount, any currency:** the threshold is compared with the offer total whatever the offer's currency. Per-currency thresholds can come later if a company works in several currencies.
- **Tests:**
  - Unit tests in `test_offer_workflows.py::test_offer_threshold_rule` cover the boundaries.
  - The exit gate is `tests/test_offer_threshold_db.py`:
    - At the threshold, the offer is approved directly.
    - Above it, the offer goes to approval.
    - With the threshold at 0, every offer goes to approval.
    - A negative threshold is rejected.

### 4.8 revised — the requisition's pay range decides first (decision D-06a)

One company-wide limit is too blunt when roles pay differently, so the requisition's own budget now decides first. Chosen 2026-10-07.

1. **The offer has no amount yet:** it goes to approval.
2. **The requisition has a `budget_max`:**
   - An offer total (CTC + bonus) at or under `budget_max` is approved directly.
   - An offer over it needs approval.
   - An offer in a different currency from the budget needs approval, because it can't be compared safely.
3. **The requisition has no budget:** the company threshold applies (default 0, so every paid offer needs approval).

**What else changed:**

- `requisitions.budget_min`, `budget_max` and `currency_code` already existed in the database but were never exposed. They are now part of requisition create, update and response (`budget_min <= budget_max` is enforced, and the currency is stored in upper case).
- The intake form has a **Pay range** section, which is filled in when editing an existing requisition.
- The Company Settings text now explains that the threshold is the fallback.
- **Tests:**
  - The unit table in `test_offer_threshold_rule` covers 9 cases.
  - `test_offer_threshold_db.py::test_requisition_budget_decides_when_set` shows the budget overriding a company threshold of 0.

**Fifth verify run (`ceca100`):** 492 passed, 2 failed, both in `test_offer_threshold_db.py`. 020 applied to dev.

- **Cause: an old bug, now fixed.** Every offer that needed approval returned 500 on a real database. `create_offer` inserted into `approval_requests.location_id`, but that table's column is `branch_id`. No earlier test created an offer against a real database, and the unit tests mock the repository, so the bug never showed up before. The direct-approve path (new in 4.8) passed; the approval path exposed it.
- Fix: the INSERT now writes `branch_id`.
- Database errors are now logged on the server with the request path and the real SQL error. Before, they were swallowed into a generic 500, which made this hard to find.

**Sixth verify run (`82a5d59`):** 494 passed, smoke 52/52, sweeps 105/105.

## 4.7 Duplicate matching — built

The repository's `find_duplicate_matches` now sorts matches into two tiers:

| Tier | Rule | Effect | Scope |
|---|---|---|---|
| **exact** | Same e-mail (ignoring case and spaces) or same phone (last 10 digits; spaces, dashes, brackets and `+` ignored) | Flags the candidate `in-review` | Every company, because candidates are shared identity records |
| **suggested** | Name similarity ≥ 0.85 (word order, case and punctuation ignored) **and** the same location (current or preferred city) | A hint only; never changes the duplicate state | The caller's company only |

**Other changes:**

- A match that is only the same name (with no shared city) is no longer reported. Before, an exact name match alone flagged the candidate.
- **Privacy fix:** an exact match that belongs to another company comes back with `in_your_company: false` and no e-mail, phone or employer. Before, the duplicate check showed other companies' contact details.
- The response gains `match_tier` and `in_your_company`. Scores: exact matches score 90–100; suggestions are capped at 79.
- Duplicate decisions were already audited (`duplicate_decision_created`).
- **Tests:**
  - Unit tests in `tests/test_duplicate_tiers.py` cover name normalisation, phone digits, cross-company redaction and the suggestion cut-off.
  - `tests/test_duplicate_tiers_db.py` runs the full set of cases against a real database.

**Seventh verify run (`7140859`):** 499 passed, smoke 52/52, sweeps 105/105.

## 4.9 API contract sweep — built

- **Error contract (PRD §9.0).** Every error is now `{"detail": msg, "error": {"code", "message", "field_errors"}}` (`app/core/errors.py`).
  - Handlers cover:
    - every `HTTPException`, including the router's own 404/405;
    - validation errors, with `field_errors` per field;
    - stale writes (`STALE_WRITE`, with the fresh row as before);
    - integrity errors (`DATA_CONFLICT`);
    - database errors (`DATABASE_ERROR`, logged) and `DATABASE_UNAVAILABLE`.
  - Codes default from the status (`NOT_FOUND`, `FORBIDDEN`, `VALIDATION_ERROR`, `RATE_LIMITED`, …). `ApiError` carries explicit codes.
  - `detail` is kept with the same message, so the frontend and existing tests are unaffected. `ApiError.code` is now available in the frontend.
- **Unsupported filters → 400 `UNSUPPORTED_FILTER`.** All 16 list endpoints refuse query parameters they don't declare (`reject_unknown_query_params`). The error lists the parameters that are supported.
  - A static test scans every list URL in the frontend and live smoke and fails if one sends a parameter the API doesn't accept.
- **Sorting.** `?sort=field` / `-field` (comma-separated) works on candidates, clients and requisitions. It is built from an allowlist (`sort_clause`), so column names never come from the client, and an unknown field returns 400 `UNSUPPORTED_SORT`. Other lists don't take `sort` yet; on those, `?sort=` is refused as an unsupported filter rather than silently ignored.
- **Pagination.** Every list already takes `page` and `page_size` (max 100) and returns `meta.total`. Defaults are 20 on most lists; the PRD says 25, and that change is left alone so pages don't shift under the current UI.
- **Foreign-tenant IDs in responses.** Already covered by the Phase 2 isolation suites (`test_tenant_isolation_db.py`, `test_company_isolation_db.py`). 4.7 closed the one known leak, contact details in duplicate matches.
- **Not done:** cursor pagination for notifications and audit logs (the audit log viewer is Phase 5.4), and `sort` on the other 13 lists.

**First 4.9 run (`f79dc35`):** 39 failed, 465 passed; live smoke 28/48; the sweeps showed failing pages. Every strict list endpoint returned 500.

- **Cause:** `reject_unknown_query_params` imported `fastapi.dependencies.utils.get_flat_dependant`. That function no longer exists in the installed FastAPI (0.141). The same version nests included routers (`_IncludedRouter`), so the test's walk over `app.routes` found nothing either.
- **Fix:** the allowed names now come from the endpoint's own signature (`scope["endpoint"]`, its `Query` parameters and plain scalar defaults). This doesn't depend on FastAPI's routing internals, so a version bump can't break it the same way. The contract test now finds strict lists from the source files.

**Eighth verify run (`4f966cc`):** 504 passed, smoke 52/52, sweeps 105/105. Pushed.

## Phase 4 status

| Exit gate | Status | Proof |
|---|---|---|
| A report over the 5 live custom stage labels counts them in the right buckets | ✅ | `test_metric_buckets_db.py` |
| Two concurrent edits: the second gets 409 with the fresh row | ✅ | `test_row_versions_db.py` |
| Archived candidates are hidden from lists and from direct reads by users without the grant; restore works for users with it | ✅ | `test_soft_delete_db.py` |
| An offer under the threshold is approved directly; over it creates an approval; threshold 0 sends every offer to approval (plus the requisition pay range, D-06a) | ✅ | `test_offer_threshold_db.py` |
| An `.exe` renamed `.pdf` is rejected; an EICAR file is quarantined and never linkable | ⏳ | Needs 4.1/4.2 (storage and malware scanner; cloud choice I-2) |

Built: 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9. Still to build: 4.1 (storage adapter) and 4.2 (upload pipeline).

## 4.1 Storage adapter + 4.2 upload pipeline — built (portable; cloud still undecided, I-2)

Decision D-4.1 (2026-10-08): files are stored through the S3 standard, so any S3-compatible store works. The cloud choice is only settings.

- **Storage (`app/core/file_storage.py`):**
  - `STORAGE_BACKEND=local` (development and CI only) or `s3`. S3 covers AWS S3, Cloudflare R2, Backblaze B2, DigitalOcean Spaces and MinIO through `S3_ENDPOINT_URL`. `boto3` is imported only when S3 is in use.
  - Object keys are always `tenant_<id>/<area>/<entity>/<uuid><ext>`. Path escapes are refused.
  - Links: the S3 backend issues presigned GETs to a private bucket (AWS: SSE-AES256). The local backend issues short-lived signed tokens served by `GET /files/signed/{token}`. Tokens carry their own audience, so they can never be used as an access token, and they never point into `quarantine/`. Lifetime is `FILE_LINK_TTL_SECONDS`, default 300.
  - Links are issued **only after authorisation**: `GET /candidates/{id}/documents/{doc_id}/link` runs the full candidate access check (company, office, archive) and requires a clean scanned file.
- **Security fix: removed `GET /files/{path}`.** It served any stored file to any signed-in user who knew the path, with no company or record check.
- **Upload pipeline (`app/services/uploads.py`):** sniff → allowlist → size cap → `quarantine/` → malware scan → final key.
  - **Type sniffing** (`file_types.py`):
    - The file type comes from its first bytes: PDF, DOC (OLE), DOCX, PNG, JPEG.
    - The extension must agree with the content, so an `.exe` renamed `.pdf` gets 422 `UNSUPPORTED_FILE_TYPE`.
    - Allowed per purpose: resume = PDF/DOC/DOCX; document = those plus PNG/JPEG; logo = PNG/JPEG.
    - Size caps: resumes and documents 10 MB, logo 5 MB. The upload is read only to cap + 1 bytes.
  - **Scanning** (`malware.py`):
    - `MALWARE_SCANNER=clamav` talks to clamd INSTREAM over TCP; no new dependency.
    - `builtin` (development and CI) detects only the EICAR test signature.
    - A scanner that can't answer refuses the upload: 503 `SCANNER_UNAVAILABLE` (fail closed).
  - **Infected files:**
    - The bytes stay under `quarantine/` and a row goes into `upload_quarantine`.
    - The block is audited as `upload.malware_blocked`, and the caller gets 422 `MALWARE_DETECTED`.
    - No document row is created, so nothing can link to the file.
  - **Idempotency:** an `Idempotency-Key` header returns the first document on retry (`upload_idempotency`). `api-client.js` adds a key to every FormData POST.
  - **Company logo:** must really be PNG or JPEG (SVG could carry script on a public URL) and is scanned. The stored media type comes from the bytes.
- **Migration `021_file_pipeline.sql`:**
  - Adds to `candidate_documents`: `storage_key`, `content_type`, `size_bytes`, `sha256` and the scan fields.
  - New tables: `upload_quarantine` and `upload_idempotency`.
  - Rows from before this migration have no `storage_key` and are never linked.
- **Config guard:** staging and production refuse to start with `STORAGE_BACKEND != s3`, without an `S3_BUCKET`, or with `MALWARE_SCANNER != clamav`.
- **Tests:**
  - Unit tests in `test_file_pipeline.py` cover the sniff rules, the EICAR scanner, the ClamAV protocol against a fake clamd, fail-closed behaviour, path escapes, and signed-link tamper and expiry.
  - The exit gate is `test_upload_pipeline_db.py`:
    - A renamed `.exe` gets 422.
    - An EICAR file is quarantined, with no document and no link.
    - A clean upload lands under the company prefix and is idempotent.
    - The signed link downloads the file, the raw path returns 404, and a forged link returns 403.
- **Still needed for go-live:**
  - Pick the bucket provider and set the `S3_*` settings.
  - Run a ClamAV daemon next to the API (`clamav/clamav` image, port 3310).
  - Move existing local files into the bucket (none exist today; readiness Q15 counted 0 uploads).

**4.1/4.2 verify run (`0e15686`):** 516 passed, 1 failed; smoke 52/52; sweeps 105/105. 021 applied to dev.

- `test_file_serve_route_registered` still expected the removed `GET /files/{file_path}` route. It now checks that `/files/signed/{token}` exists and that the raw path route is gone.
- GitHub CI's frontend gates failed `flow_logout` with "Transition was aborted because of invalid state". That is Chromium's own cross-document View Transition promise being rejected when logout navigates mid-transition. The browser sweep already ignored this message; the UI-flow runner now ignores it the same way (`_BENIGN_ERRORS`). The navigation itself completes and the flow's assertions still run.
