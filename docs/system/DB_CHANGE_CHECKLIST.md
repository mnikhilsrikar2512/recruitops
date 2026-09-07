# DB Change Checklist

## Purpose

This document maps the gap between the current MVP schema draft and the finalized product decisions.

It should be used to:

- update the schema draft
- revise SQL DDL files
- plan migrations
- confirm MVP data model scope

This is a checklist, not the final schema itself.

## Source Of Truth

This checklist is aligned to:

- `docs/system/FINAL_REQUIREMENTS_DECISIONS.md`
- `docs/system/SYSTEM_RULES_AND_VALIDATIONS.md`
- `docs/system/PERMISSION_CODE_LIST.md`
- `docs/system/MVP_SCHEMA_DRAFT.md`

## Overall Status

The current schema draft is directionally strong, but it still reflects older assumptions in a few important places:

- it assumes more fixed role thinking than the new Admin-configured model
- it keeps candidates location-bound instead of globally stored
- it still centers some ownership around older role mappings
- it does not yet fully model duplicate review control
- it does not yet fully model pipeline template assignment
- it does not yet fully model explicit permission configuration at the level now required

## Priority 1: Keep

These structures should remain in MVP with refinement rather than replacement.

### Keep `locations`

Reason:

- location is now the primary operating boundary

### Keep `users`

Reason:

- user identity, location assignment, and reporting relationships remain core

### Keep `clients`

Reason:

- client registry remains required

### Keep `client_contacts`

Reason:

- requisition and communication workflows need them

### Keep `requisitions`

Reason:

- requisition workflow remains central

### Keep `requisition_assignments`

Reason:

- one requisition can have one primary owner plus additional contributors

### Keep `candidate_requisition_links`

Reason:

- one candidate can be linked to multiple requisitions
- pipeline is requisition-specific

### Keep `candidate_stage_history`

Reason:

- stage changes must remain auditable

### Keep `daily_updates`

Reason:

- daily updates are mandatory in MVP

## Priority 2: Change Existing Structures

## 2.1 `users`

### Change Needed

- shift from hard-coded role assumptions to configurable role assignment

### Checklist

- keep `location_id` for operational users
- keep `reporting_manager_user_id`
- replace simple `permission_role_code` usage with a configurable assigned-role reference model
- preserve support for one primary role plus extra permissions
- ensure Admin/setup/global records can exist without operational location dependency if needed

### Recommended additions

- `primary_role_id`
- `extra_permissions_json` only if using interim MVP shortcut
  or
- use dedicated relational mapping tables for extra permissions

## 2.2 `user_location_roles`

### Change Needed

- reshape this table toward user-role-location assignment, not older static role assumptions

### Checklist

- keep for location-scoped role assignment history
- rename in implementation if needed to something more explicit such as:
  - `user_role_assignments`
  or
  - `user_location_role_assignments`
- include effective dates and status
- support one primary active role per user in MVP

## 2.3 `clients`

### Change Needed

- remove assumptions that imply broad shared ownership

### Checklist

- keep `location_id`
- keep `created_by_user_id`
- keep business source ownership field
- ensure client belongs to one location only
- remove or avoid any schema logic implying default multi-location client sharing

### Recommended ownership fields

- `created_by_user_id`
- `client_owner_user_id`

### Candidate note

- if legacy `account_manager_user_id` exists, replace it with `client_owner_user_id` or `primary_owner_user_id` based on actual ownership meaning

## 2.4 `requisitions`

### Change Needed

- align with final rule that delivery owner is optional

### Checklist

- keep `location_id`
- keep `client_id`
- keep `created_by_user_id`
- keep one clear primary owner
- make `delivery_owner_user_id` nullable
- add explicit secondary contact if not already present
- add required skills structure
- add acceptable career gap field
- add preferred update time or update window field

### Recommended fields to add or confirm

- `primary_owner_user_id`
- `secondary_contact_user_id` nullable
- `delivery_owner_user_id` nullable
- `required_skills_json` or normalized skills tables
- `acceptable_career_gap_months` nullable
- `preferred_update_time_text` or structured update preference fields

## 2.5 `candidates`

### Change Needed

- this table needs the biggest conceptual change

### Current issue

- current draft says candidates are stored within one location

### Final rule

- candidates must be global at company level
- access stays controlled

### Checklist

- remove mandatory operational `location_id` from the candidate identity table
  or
- make it an owning-location concept instead of a hard partitioning key
- preserve `sourced_by_user_id`
- preserve `primary_owner_user_id`
- add social profile fields or related table
- keep resume reference
- keep duplicate-detection-related fields

### Recommended fields to add or confirm

- `owning_location_id`
- `linkedin_url` nullable
- `github_url` nullable where relevant
- `portfolio_url` nullable
- `social_profiles_json` if using flexible MVP model

## 2.6 `candidate_requisition_links`

### Change Needed

- align with global candidate model and requisition-based access

### Checklist

- keep `requisition_id`
- keep `candidate_id`
- keep `submitted_by_user_id`
- keep `owner_user_id` only for requisition-specific workflow ownership
- keep `sourced_by_user_id`
- keep current stage
- ensure location is derived from requisition when possible
- avoid forcing duplicate location boundaries on globally stored candidates

### Recommended additions

- `pipeline_template_id` if per-link template assignment is needed
- `last_activity_at`
- `stale_after_days` nullable if stage-level override needed

## 2.7 `daily_updates`

### Change Needed

- support one main daily summary plus optional extra updates

### Checklist

- keep `user_id`
- keep `update_date`
- keep `summary_text`
- add a field distinguishing main vs extra update

### Recommended field

- `update_type` with values like:
  - `main`
  - `extra`

## Priority 3: Add New Tables

## 3.1 `roles`

### Why needed

- Admin creates custom roles
- roles are not hard-coded except Admin

### Suggested fields

- `id`
- `code`
- `name`
- `description`
- `is_system_role`
- `status`
- `created_by_user_id`
- `created_at`
- `updated_at`

## 3.2 `role_permissions`

### Why needed

- configurable role-to-permission mapping is core to the product

### Suggested fields

- `id`
- `role_id`
- `permission_id`
- `created_at`
- `updated_at`

## 3.3 `permissions`

### Why needed

- stable permission vocabulary must be stored from the permission code list

### Suggested fields

- `id`
- `code`
- `module_name`
- `action_name`
- `description`
- `is_sensitive`
- `created_at`
- `updated_at`

## 3.4 `role_templates`

### Why needed

- MVP uses basic starter templates
- originals must be protected and cloneable

### Suggested fields

- `id`
- `code`
- `name`
- `description`
- `is_protected`
- `created_at`
- `updated_at`

## 3.5 `role_template_permissions`

### Why needed

- starter templates need predefined permission bundles

## 3.6 `user_extra_permissions`

### Why needed

- users can have one primary role plus extra permissions

### Suggested fields

- `id`
- `user_id`
- `permission_id`
- `granted_by_user_id`
- `status`
- `created_at`
- `updated_at`

## 3.7 `pipeline_stage_library`

### Why needed

- controlled stage vocabulary is required

### Suggested fields

- `id`
- `code`
- `name`
- `sequence_order`
- `is_terminal`
- `created_at`
- `updated_at`

## 3.8 `pipeline_templates`

### Why needed

- stages vary by client or requisition requirement

### Suggested fields

- `id`
- `name`
- `description`
- `created_by_user_id`
- `status`
- `created_at`
- `updated_at`

## 3.9 `pipeline_template_stages`

### Why needed

- each template needs ordered stage membership

### Suggested fields

- `id`
- `pipeline_template_id`
- `stage_library_id`
- `display_name`
- `sequence_order`
- `is_required`

## 3.10 `duplicate_review_cases`

### Why needed

- duplicate handling is not a simple warning
- compare-first flow needs a persisted review object

### Suggested fields

- `id`
- `new_candidate_draft_id` nullable if drafts are stored separately
- `existing_candidate_id`
- `requested_by_user_id`
- `review_status`
- `decision`
- `decided_by_user_id` nullable
- `decision_notes`
- `created_at`
- `updated_at`

## 3.11 `candidate_location_transfer_requests`

### Why needed

- cross-location candidate transfer needs approval workflow

### Suggested fields

- `id`
- `candidate_id`
- `from_location_id`
- `to_location_id`
- `requested_by_user_id`
- `approval_status`
- `approved_by_user_id` nullable
- `approval_notes`
- `created_at`
- `updated_at`

## 3.12 `report_locks`

### Why needed

- weekly and monthly reports must be lockable

### Suggested fields

- `id`
- `report_type`
- `location_id` nullable
- `period_start`
- `period_end`
- `lock_status`
- `locked_by_user_id`
- `locked_at`
- `unlocked_by_user_id` nullable
- `unlocked_at` nullable

## 3.13 `audit_log_access_events`

### Why needed

- audit-log viewing itself should be logged

### Suggested fields

- `id`
- `viewer_user_id`
- `scope_used`
- `filters_json`
- `viewed_at`

## Priority 4: Add Or Confirm Approval Structures

The current system may already contain approval-like tables in older schema drafts, but MVP needs approval support specifically for:

- duplicate override
- candidate transfer between locations
- report unlock
- requisition reassignment after work starts
- global visibility grant

### Checklist

- confirm whether existing `approval_requests` can cover these cleanly
- if yes, standardize request types
- if no, add targeted approval tables or extend the generic approval table

## Priority 5: Remove Or De-Emphasize Old Assumptions

These older assumptions should be removed from schema thinking where still present:

- fixed permanent operational role hierarchy
- mandatory delivery owner on every requisition
- location-bound candidate identity
- unrestricted shared clients across locations
- duplicate handling as only a warning

## Priority 6: Index And Constraint Changes

## Candidate indexes

Because candidates are global:

- move duplicate indexes away from hard `location_id + email`
- use company-level duplicate search logic where needed
- keep supporting indexes for owner, source owner, and linked requisition workflow

Recommended candidate indexes:

- `candidates(email)`
- `candidates(phone)`
- `candidates(full_name)`
- `candidates(source_owner_user_id, primary_owner_user_id, status)`

## Requisition indexes

Recommended:

- `requisitions(location_id, status, target_closure_date)`
- `requisitions(client_id, status)`
- `requisitions(primary_owner_user_id, status)`

## Duplicate review indexes

Recommended:

- `duplicate_review_cases(existing_candidate_id, review_status)`
- `duplicate_review_cases(requested_by_user_id, review_status)`

## Report lock indexes

Recommended:

- `report_locks(location_id, report_type, period_start, period_end, lock_status)`

## Priority 7: Final Schema Decisions To Confirm In DDL

Before DDL is finalized, confirm these final modeling choices in SQL:

1. `roles` are configurable, with Admin as only fixed default
2. `permissions` are seeded from the permission code list
3. `role_permissions` define baseline access
4. `user_extra_permissions` handle exceptions
5. `clients` remain location-bound
6. `candidates` are global
7. `requisitions` have primary owner and optional delivery owner
8. duplicate review is persisted, not purely transient
9. pipeline templates are persisted
10. report locks are persisted
11. audit-log access events are persisted

## Recommended Next Step

After this checklist, the next document should be:

- a revised `MVP_SCHEMA_V2.md`

or directly:

- a revised SQL DDL file based on this checklist
