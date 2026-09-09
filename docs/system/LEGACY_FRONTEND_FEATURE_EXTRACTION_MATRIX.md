# Legacy Frontend Feature Extraction Matrix

> **Archived:** the legacy prototype pages referenced throughout this document (the
> `*_executive_heritage*` files and similar one-off mockups under `frontend/pages/`) were
> removed once the live routed frontend replaced them. The idea categories and cautions
> below remain valid as design guidance; the file references are historical.

## Purpose

This document extracts the most useful ideas from the earlier legacy frontend artifacts and maps them to the target MVP pages.

It is not a final selection document.

Its purpose is to:

- reduce comparison time after new uploads arrive
- identify which legacy screens have reusable ideas
- identify which legacy ideas should be dropped early
- help the team compare old and new assets page by page

Use this together with:

- `docs/system/CURRENT_FRONTEND_ARTIFACT_BASELINE.md`
- `docs/system/MVP_FRONTEND_COMPARISON_AND_SELECTION_FRAMEWORK.md`
- `docs/system/MVP_FRONTEND_SELECTION_MATRIX.md`

## Important Rule

This document does not promote legacy pages into the real frontend.

It only captures:

- potentially reusable layout ideas
- potentially reusable section ideas
- potentially reusable interaction ideas

Everything here still needs comparison against the new uploads and the real MVP requirements.

## Extraction Legend

- `High Reference Value`
  likely useful as a comparison input
- `Medium Reference Value`
  some useful ideas, but not a strong full-page direction
- `Low Reference Value`
  limited MVP value
- `Drop By Default`
  likely outside current MVP scope or mismatched to product direction

## Page-Level Legacy Extraction

| Target MVP Page | Legacy Files To Review First | Reference Value | Useful Ideas To Extract | Cautions |
| --- | --- | --- | --- | --- |
| `Login` | `frontend/pages/login_executive_heritage.html` | `High Reference Value` | auth layout, form spacing, brand placement, submit hierarchy | do not inherit visual style blindly if new upload is structurally clearer |
| `Access Denied` | `frontend/pages/access_denied_executive_heritage.html`, `frontend/pages/404_not_found_executive_heritage.html` | `Medium Reference Value` | denial wording, safe exit action placement, simple centered state | keep it minimal; do not over-design utility pages |
| `Role Dashboard` | `frontend/pages/admin_dashboard_executive_heritage_fixed.html`, `frontend/pages/manager_dashboard_executive_heritage_fixed.html`, `frontend/pages/hr_dashboard_executive_heritage.html` | `Medium Reference Value` | KPI grouping, alert cards, dashboard spacing ideas | hard-coded role dashboards conflict with configurable-role model |
| `My Work Dashboard` | `frontend/pages/manager_dashboard_executive_heritage_fixed.html`, `frontend/pages/hr_dashboard_executive_heritage.html`, `frontend/pages/team_performance_executive_heritage.html` | `Medium Reference Value` | personal work widgets, summary-card grouping, action priority zones | avoid manager or HR-specific assumptions in final UX |
| `Location Management` | `frontend/pages/location_management_executive_heritage.html` | `High Reference Value` | management table structure, page header, action layout, status handling | likely a useful comparison base for admin pages |
| `User Management` | `frontend/pages/user_management_executive_heritage.html`, `frontend/pages/create_user_executive_heritage.html`, `frontend/pages/update_user_executive_heritage.html` | `High Reference Value` | list and form split, user details grouping, multi-step invite patterns | current role assumptions may not match configurable access model |
| `User Detail` | `frontend/pages/deactivate_user_step_2_impact_timing.html`, `frontend/pages/deactivate_user_step_3_success_confirmation.html`, `frontend/pages/delete_user_step_1_summary_choice.html`, `frontend/pages/delete_user_step_2_impact_reassignment.html` | `High Reference Value` | review flow sequencing, impact summary presentation, confirmation hierarchy | delete-oriented language may need reinterpretation as deactivate-and-reassign |
| `Role Management` | no strong direct match; review `frontend/pages/create_user_executive_heritage.html` and admin dashboard patterns lightly | `Low Reference Value` | maybe matrix spacing or admin form treatment only | do not force a role UI from unrelated legacy screens |
| `Client Directory` | `frontend/pages/client_companies_executive_heritage.html`, `frontend/pages/client_portfolio_executive_heritage.html` | `High Reference Value` | client list structure, ownership display, list filters | ensure final model stays location-bound and configurable |
| `Client Detail` | `frontend/pages/company_details_executive_heritage.html` | `High Reference Value` | entity detail header, summary sections, related record grouping | may contain non-MVP company details that should be simplified |
| `Requisition List` | `frontend/pages/managed_requisitions_perfectly_balanced_layout.html` | `High Reference Value` | requisition table density, quick status visibility, action placement | verify that the balance of metrics vs list is still right for MVP |
| `Requisition Intake` | `frontend/pages/structured_requisition_intake_layout_fixes.html` | `High Reference Value` | form section grouping, sticky action strategy, intake flow structure | approval or extra controls may exceed MVP |
| `Requisition Detail` | `frontend/pages/managed_requisitions_perfectly_balanced_layout.html`, `frontend/pages/structured_requisition_approval_modal.html` | `Medium Reference Value` | detail summary arrangement, status/review treatment, assignment action framing | avoid approval-heavy patterns not in MVP |
| `Candidate Profiles` | `frontend/pages/candidate_profiles_refined_structure.html`, `frontend/pages/candidate_profile_arjun_mehta.html` | `High Reference Value` | candidate section grouping, profile density, activity sidebar ideas | some fields may be too profile-heavy versus action-heavy |
| `Resume Upload And Review` | `frontend/pages/upload_resume_parse_review_modal_executive_heritage.html`, `frontend/pages/resume_save_candidate_modal_executive_heritage.html` | `High Reference Value` | upload flow stages, parse review block layout, save decision flow | modal-only treatment may need conversion into page or structured flow |
| `Candidate Duplicate Review` | `frontend/pages/resume_duplicate_check_modal_executive_heritage.html` | `High Reference Value` | compare-first warning logic, duplicate action framing, review messaging | current version may be too modal-like for a controlled review page |
| `Pipeline Board` | `frontend/pages/pipeline_board_executive_heritage.html`, `frontend/pages/candidate_screening_arjun_mehta.html` | `High Reference Value` | lane organization, card density, stage grouping, move-action placement | screening page may contain steps that should remain inside dialogs or drawers |
| `Daily Updates Submission` | `frontend/pages/submit_daily_update_executive_heritage.html` | `High Reference Value` | form hierarchy, summary counts grouping, progress-note structure | verify it matches current update fields, not older reporting assumptions |
| `Daily Updates Review` | `frontend/pages/reports_center_executive_heritage.html`, `frontend/pages/team_performance_executive_heritage.html` | `Medium Reference Value` | summary-to-detail reporting pattern, review-table ideas | likely too report-heavy; keep only structural ideas |
| `Notifications Center` | `frontend/pages/admin_notifications_executive_heritage.html`, `frontend/pages/manager_notifications_executive_heritage.html`, `frontend/pages/hr_notifications_executive_heritage.html` | `Medium Reference Value` | notification list grouping, read-state cues, detail panel ideas | role-specific duplication should not carry forward |
| `Location Dashboard` | `frontend/pages/team_performance_executive_heritage.html`, `frontend/pages/manager_reports_executive_heritage.html`, `frontend/pages/hr_reports_executive_heritage.html` | `Medium Reference Value` | KPI grouping, chart layout ideas, location-level summary composition | avoid role-specific naming and non-MVP reporting sections |
| `Company Dashboard` | `frontend/pages/admin_dashboard_executive_heritage_fixed.html`, `frontend/pages/reports_center_executive_heritage.html` | `Medium Reference Value` | top-level KPI grouping, risk-summary arrangement, company-wide overview framing | make sure combined reporting does not imply operational control UI |

## Foundation-Level Legacy Extraction

| Foundation Area | Legacy Files To Review First | Reference Value | Useful Ideas To Extract | Cautions |
| --- | --- | --- | --- | --- |
| `Auth Layout` | `frontend/pages/login_executive_heritage.html` | `High Reference Value` | centered auth card, brand placement, supporting text placement | keep structure, not necessarily full styling |
| `App Shell Layout` | `frontend/pages/admin_dashboard_executive_heritage_fixed.html`, `frontend/pages/manager_dashboard_executive_heritage_fixed.html` | `Medium Reference Value` | sidebar width, top-bar spacing, page-header rhythm | current shell may embed role-specific assumptions |
| `Dashboard Layout` | dashboard and reports pages listed above | `Medium Reference Value` | KPI strip spacing, widget grouping, card hierarchy | do not inherit role-specific widget sets |
| `Management Layout` | `frontend/pages/location_management_executive_heritage.html`, `frontend/pages/user_management_executive_heritage.html`, `frontend/pages/client_companies_executive_heritage.html` | `High Reference Value` | filter bar placement, table-header action balance, list rhythm | likely one of the best reusable legacy sources |
| `Detail Layout` | `frontend/pages/company_details_executive_heritage.html`, `frontend/pages/candidate_profile_arjun_mehta.html` | `High Reference Value` | summary-header plus detail-sections pattern, related-record grouping | keep it operational, not profile-heavy |
| `Filter Bar` | management and report list pages | `High Reference Value` | search placement, chip layout, quick-filter grouping | remove filters that only exist because of old hierarchy |
| `Table Shell` | location, user, client, requisition pages | `High Reference Value` | column density, sticky action placement, empty-area rhythm | confirm reusable behavior before copying visuals |
| `Dialog Shell` | requisition approval modal, meeting outcome modal, duplicate modal | `Medium Reference Value` | action footer hierarchy, close/confirm spacing | several examples come from non-MVP flows |
| `Drawer Shell` | approval decision drawer and related detail patterns | `Medium Reference Value` | right-side detail presentation and compact action handling | not many clean MVP-specific examples |
| `Status Chip System` | location, requisition, notifications, reports pages | `High Reference Value` | quick status readability, color cue ideas | must be normalized into one consistent system later |
| `KPI Card System` | dashboards and reports pages | `Medium Reference Value` | count emphasis, label hierarchy, comparison card ideas | role-specific content should not survive |
| `Empty/Error/Loading States` | 404, delete-empty-state, access denied | `Medium Reference Value` | simple empty messaging and fallback hierarchy | likely still needs better consistency in the real app |
| `Action Bar Pattern` | requisition intake, create/update user flows | `High Reference Value` | sticky action treatment, primary vs secondary action grouping | keep only the decision pattern, not legacy wording |

## Legacy Items To Drop By Default

These should normally be excluded unless a very specific idea is unusually strong:

- `frontend/pages/approvals_inbox_executive_heritage.html`
- `frontend/pages/structured_requisition_approval_modal.html`
- `frontend/pages/portal_accounts_executive_heritage.html`
- `frontend/pages/assign_portal_slot_modal_executive_heritage.html`
- `frontend/pages/portal_slot_success_toast_executive_heritage.html`
- `frontend/pages/interview_schedule_executive_heritage.html`
- `frontend/pages/meetings_follow_ups_executive_heritage.html`
- `frontend/pages/settings_executive_heritage.html`
- `frontend/pages/user_profile_account_settings_executive_heritage.html`

Reason:

- they are future-extension oriented
- they are outside current MVP scope
- or they reflect an older product direction

## Best Legacy Areas For Reuse

The legacy frontend appears most useful as reference in these areas:

- management list page structure
- detail page structure
- requisition intake section grouping
- candidate profile and resume review flow
- pipeline board lane layout
- daily update submission structure

## Weakest Legacy Areas For Reuse

The legacy frontend appears weakest or least aligned in these areas:

- configurable role management
- clean, role-agnostic dashboards
- company-wide reporting for the new product model
- notifications as one unified cross-role experience

## Recommended Use During Comparison

When new uploads arrive:

1. start by comparing against `High Reference Value` legacy items
2. borrow only structure, not assumptions
3. treat hard-coded role language as suspect
4. reject any legacy feature that pulls the product back toward the old model

## Final Rule

The legacy frontend should help us move faster, but it should never decide the final product direction by itself.
