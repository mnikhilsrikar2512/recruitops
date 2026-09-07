# Final Requirements Decisions

## Purpose

This document converts the filled Q&A into final MVP-friendly product decisions.

It keeps the original intent but tightens unclear, conflicting, or overly broad answers so the system can be planned and built cleanly.

Date locked:

- August 17, 2026

## 1. Business Model

### Decision

The product should support a mixed model.

That means it should be usable by:

- recruitment agencies
- internal hiring teams
- staffing and RPO partners
- companies with blended recruitment structures

### Why

This keeps the system commercially flexible and aligns with the decision to avoid fixed non-admin operational roles.

## 2. Location Model

### Decision

The system must support:

- single-location companies
- multi-location companies
- future location expansion

Location must be mandatory for:

- all operational users
- all operational records

Exceptions:

- Admin
- setup records
- global configuration records

### Why

Some customers will operate from one location, while others will need multiple locations and growth support.

## 3. Location Visibility Rule

### Decision

Users from one location should be blocked from seeing another location’s data by default.

Exception:

- special access can be granted through configured scope rules

### Why

This protects data separation while still allowing controlled exceptions.

## 4. Combined Visibility

### Decision

All-location combined visibility should be available to:

- Admin
- selected custom roles with explicitly configured global access

### Why

Not every leadership or reporting role should automatically get global visibility.

## 5. Fixed Role Model

### Decision

The only fixed product role is:

- `Admin`

All other operational roles must be created by Admin.

### Why

This keeps the product configurable for many organization structures.

## 6. Role Creation Model

### Decision

Admin should create custom roles manually, with starter templates.

### Why

This balances flexibility with setup speed.

## 7. Role Template Model

### Decision

The MVP should support:

- basic starter templates only

Future improvement:

- improve templates based on real admin usage patterns

### Why

This avoids overbuilding template logic too early.

## 8. Role Access Configuration Model

### Decision

For MVP, Admin should configure:

- modules
- actions
- scope

Page-level precision can be expanded later if needed.

### Why

This gives enough control for MVP without making setup too complex.

## 9. Scope Types

### Decision

MVP scope types should be:

- `own`
- `team`
- `location`
- `global`

`custom` scope should be postponed to a later phase.

### Why

`custom` scope adds complexity too early and is not necessary to prove the model.

## 10. Multi-Role Model

### Decision

Each user should have:

- one primary role
- optional extra permissions

### Why

This is simpler than true multi-role composition and still flexible enough for MVP.

## 11. Client Record Creation

### Decision

Any configured role with client-create permission can create client records.

Client ownership rule:

- one client belongs to one location
- only that location should work on that client by default

### Why

This supports different customer operating models.

## 12. Requisition Creation

### Decision

Any configured role with requisition-create permission can create requisitions.

### Why

This keeps the workflow role-configurable.

## 13. Requisition Ownership

### Decision

Every requisition must have:

- one clear primary owner

Optional:

- one secondary contact

### Why

This preserves accountability while allowing fallback contact coverage.

## 14. Delivery Ownership

### Decision

A requisition may optionally have a separate delivery owner.

### Why

Some companies use one owner for everything, while others separate business-side ownership from delivery execution.

## 15. Multi-User Assignment

### Decision

One requisition can be assigned to multiple users.

Rule:

- one primary owner
- additional contributors or support users allowed

### Why

This matches real recruiting execution better than one-user-only assignment.

## 16. Reassignment

### Decision

Reassignment should be allowed after work starts, but with confirmation or approval.

### Why

Operational flexibility is needed, but reassignment should not happen casually.

## 17. Candidate Creation

### Decision

Any configured role with candidate-create permission can create candidate records.

### Why

This supports flexible sourcing and delivery models.

## 18. Duplicate Prevention

### Decision

If a duplicate candidate is detected:

- the user must first compare the new record with the existing record
- the user can then take a controlled action such as:
  - request override
  - discard the new draft
  - keep the existing record and link to it where allowed

Final override or duplicate-change authority should belong only to:

- Admin
- configured senior roles if explicitly permitted

### Why

This reduces duplicate records without blocking legitimate edge cases and forces review before change.

## 19. Duplicate Matching Rules

### Decision

Candidate duplicate checks should use:

- email
- phone
- name
- resume similarity

### Why

This is strong enough to catch most operational duplicates.

## 20. Multi-Requisition Candidate Linking

### Decision

One candidate can be linked to multiple requisitions if permitted by system policy and scope.

### Why

This is necessary for realistic recruiting workflows.

## 21. Source Ownership Preservation

### Decision

The original source owner of a candidate must always be preserved.

Candidate model:

- candidates should be global at company level
- candidate access should still be controlled by configured role, scope, location ownership, and requisition linkage

### Why

This is important for tracking sourcing contribution and accountability.

## 21A. Candidate Transfer Between Locations

### Decision

Candidate transfer between locations should be allowed only for:

- selected configured roles

And only with:

- approval

### Why

This keeps ownership changes controlled without making the system too rigid.

## 22. Pipeline Stage Movement

### Decision

Only configured roles with stage-move permission can move candidate pipeline stages.

### Why

This keeps execution control intentional.

## 22A. Pipeline Template Model

### Decision

Pipeline stages should be configurable based on client or requisition requirement, but in a controlled way.

The system should support:

- a master stage library
- Admin-managed pipeline templates
- selection of a pipeline template for a client or requisition

Users should not freely invent new execution stages during live workflow.

### Why

This supports client-specific processes without breaking reporting and workflow consistency.

## 23. Critical Stage Controls

### Decision

Some stage changes must require mandatory fields or confirmation.

Rule:

- at minimum for critical stages

Examples:

- rejected
- offered
- joined
- dropped

### Why

This improves data quality and reduces accidental stage movement.

## 24. Full Candidate Pipeline Visibility

### Decision

Full candidate-level pipeline visibility should be available only to:

- configured roles with detailed pipeline access

### Why

Not every role should see all candidate-level detail.

## 25. Summary Pipeline Visibility

### Decision

Summary pipeline visibility should be available to:

- any configured summary-only role

### Why

This supports business, reporting, and oversight use cases.

## 26. Visibility Vs Edit Control

### Decision

Default system rule:

- visibility may move upward
- edit rights stay limited

Admin may override for selected roles if needed.

### Why

This is the safest and most practical operational model.

## 27. Comment Without Edit

### Decision

Selected roles should be allowed to comment without being able to edit pipeline stages.

### Why

This supports oversight and collaboration without giving away delivery control.

## 28. Daily Updates

### Decision

Daily updates should be mandatory in MVP.

### Why

This is important for operational discipline and reliable reporting.

## 29. Daily Update Review

### Decision

Daily updates should be reviewed by:

- configured reporting managers
- Admin where needed

### Why

Admin should have visibility, but should not become the default reviewer of every operational update.

## 29A. Daily Update Submission Pattern

### Decision

The system should require:

- one main daily summary per user per day

And allow:

- optional extra updates if something important changes later that day

### Why

This keeps daily reporting clean while still allowing same-day flexibility.

## 30. Stale Record Reminders

### Decision

The system should send stale or missing-update reminders for critical workflows.

### Why

This improves execution quality without over-notifying every workflow.

## 31. Stale Threshold

### Decision

MVP should use:

- a default stale threshold of 3 to 5 days

Future:

- make this configurable by company

### Why

A default is needed for MVP, even if future configurability is desirable.

## 32. MVP Dashboards

### Decision

MVP dashboards should be limited to:

- My Work
- Location Summary
- Pipeline Summary
- Requisition Summary
- Admin Combined Summary

### Why

This is enough for MVP without overbuilding dashboard variants.

## 33. Report Data Warnings

### Decision

Reports should show incomplete or stale data warnings.

### Why

This improves reporting trustworthiness.

## 33A. Live Vs Lockable Reports

### Decision

The product should support:

- live dashboards and live operational reports
- lockable weekly reports
- lockable monthly reports

### Why

This gives both real-time operational visibility and reliable period-based reporting.

## 34. Admin Combined Reporting

### Decision

Admin should always be able to view combined reporting across all locations.

### Why

Admin is the fixed governance role and needs this visibility by default.

## 35. Non-Admin Report Access

### Decision

Non-admin roles should get only configured report access.

### Why

This supports the configurable role model and prevents overexposure.

## 36. Delete Model

### Decision

MVP delete behavior should be:

- soft delete by default
- hard delete only for Admin and only in limited cleanup cases

### Why

This is safer for operational data and recovery.

## 37. Audit Logging

### Decision

Sensitive changes must be logged in audit history.

### Why

This is essential for accountability and governance.

## 37A. Audit Log Visibility

### Decision

Audit logs may be viewed by any role that has explicit audit permission.

Required safeguards:

- audit access must be explicitly granted by Admin
- audit visibility should still respect scope rules
- audit-log viewing itself should also be logged

### Why

This preserves flexibility while keeping sensitive audit access controlled.

## 38. Confirmation Rules

### Decision

All critical actions should require confirmation.

Examples:

- delete
- reassign
- reject
- mark joined
- close requisition
- permission changes

### Why

This reduces accidental high-impact actions.

## 39. Role Preview

### Decision

Admin should be able to preview a role’s access before saving it.

### Why

This reduces misconfiguration risk.

## 40. Over-Access Warning

### Decision

MVP should include at least a basic warning for excessive access.

Example:

- global access plus edit rights plus pipeline control

### Why

Even a simple warning is valuable and should not be postponed fully.

## 41. MVP Must-Haves

### Decision

The MVP must include:

- Admin role setup
- user and location setup
- configurable roles
- configurable module, action, and scope access
- client registry
- requisitions
- candidates
- pipeline
- daily updates
- core dashboards

### Why

These are the minimum elements needed to prove the product model.

## 42. Postpone To Later

### Decision

Postpone these to later phases:

- advanced approvals
- billing
- external portals
- AI parsing
- automation rules
- SSO and MFA

### Why

These are valuable but not required for MVP proof of value.

## 43. MVP Priority Order

### Decision

MVP priority should be:

1. strict control
2. flexibility
3. speed

### Why

This matches the product direction of controlled access, reliable structure, and safe execution.

## 44. Biggest Problem To Solve First

### Decision

Primary problem:

- permission confusion

Secondary problem:

- candidate pipeline visibility

### Why

If access logic is unclear, the whole configurable model becomes hard to trust.

## 45. Most Common User Mistake Today

### Decision

Top common mistakes:

- duplicate entries
- missing updates

### Why

These are the most likely to damage both operations and reporting quality.

## Final Product Direction Summary

The MVP should be built as:

- a configurable recruitment system
- with `Admin` as the only fixed role
- with stable modules and workflows
- with configurable access rules
- with location-safe data separation
- with explicit ownership fields
- with controlled execution rights
- with strong duplicate and stale-data controls
