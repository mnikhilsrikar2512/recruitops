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
