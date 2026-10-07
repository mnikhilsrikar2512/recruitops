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
