# System Rules And Validations

## Purpose

This document converts the finalized business and product decisions into implementation-ready system rules.

It defines:

- validation rules
- warning rules
- approval rules
- visibility rules
- ownership rules
- report lock rules
- access change rules

This document should be used for:

- backend validation logic
- API behavior
- permission middleware
- workflow control
- frontend warnings and confirmations

## Source Of Truth

This document is aligned to:

- `docs/system/FINAL_REQUIREMENTS_DECISIONS.md`
- `docs/system/BUSINESS_ANALYSIS_DOCUMENT.md`
- `docs/system/MVP_SCHEMA_DRAFT.md`
- `docs/system/API_ENDPOINTS.md`

## 1. Core System Rules

### Rule 1. Admin Is The Only Fixed Role

- `Admin` is the only system-defined role
- all other roles are configurable
- Admin can create roles, assign permissions, and define access scope

### Rule 2. Location Is Mandatory For Operations

- every operational user must belong to a location
- every operational record must belong to a location unless it is:
  - an Admin record
  - a setup record
  - a global configuration record

### Rule 3. Clients Are Location-Bound

- one client belongs to one location
- only that location may work on that client by default
- another location may request access only through approval

### Rule 4. Candidates Are Global But Access-Controlled

- candidate records are global at company level
- candidate access is not automatically global
- candidate visibility must still depend on:
  - role permission
  - scope
  - requisition linkage
  - explicit access rules

### Rule 5. Visibility And Edit Rights Are Separate

- visibility may move upward by configured role
- edit rights must remain limited to explicitly permitted roles
- comment rights may exist without stage-edit rights

## 2. Validation Rules

## 2.1 User Creation Validation

The following fields are mandatory when creating a user:

- full name
- email
- phone number
- employee id
- location
- primary role
- reporting manager

Validation rules:

- email must be unique
- employee id must be unique where used
- location must be valid and active
- assigned role must exist and be active

## 2.2 Client Creation Validation

The following fields are mandatory when creating a client:

- client name
- location
- primary contact
- secondary contact
- status

Validation rules:

- client location must be valid and active
- primary and secondary contacts must be distinguishable records

## 2.3 Requisition Creation Validation

The following fields are mandatory when creating a requisition:

- title
- client
- location
- primary owner
- openings
- due date
- required skills
- acceptable career gap if applicable
- available time to receive updates on submitted profiles

Optional field:

- delivery owner

Validation rules:

- client must belong to the same location as the requisition
- openings must be greater than zero
- due date must be valid
- primary owner must have access to the requisition location
- delivery owner, if present, must have access to the requisition location

## 2.4 Candidate Creation Validation

The following fields are mandatory when creating a candidate:

- full name
- phone
- email
- source
- current company
- resume
- social profiles

Validation rules:

- at least one usable contact method must exist
- resume upload must complete before candidate final submission
- social profile values must be stored in a structured way if provided

## 2.5 Pipeline Stage Validation

The following stage changes require mandatory fields:

- `submitted`
  - resume
  - screening notes
- `interview`
  - scheduled date
- `joined`
  - joining date
- `rejected`
  - rejection reason

Current MVP exception:

- offer details are not mandatory yet

## 3. Duplicate Candidate Rules

### Rule 3.1 Duplicate Matching Inputs

Duplicate candidate checks must use:

- email
- phone
- name
- resume similarity

### Rule 3.2 Duplicate Review Flow

If a duplicate is detected:

1. the user must compare the new record with the existing candidate
2. the user may then choose one of these actions:
   - request override
   - discard the new draft
   - keep the existing record and link to it where allowed

### Rule 3.3 Duplicate Override Authority

Final duplicate override or duplicate-change authority may be granted only to:

- Admin
- selected senior roles

### Rule 3.4 Duplicate Override Approval

Duplicate override approval flow must be:

- configurable by company

## 4. Warning Rules

The system should show warnings for:

- low data completeness
- missing secondary contact
- no recent update
- stale requisition activity
- stale candidate activity

Duplicate detection is not just a normal warning:

- it must go through the duplicate review flow

### Rule 4.1 Requisition Stale Warning

- stale threshold should be configurable by company

### Rule 4.2 Candidate Stale Warning

- stale threshold should be configurable by stage

### Rule 4.3 Workload Warning

- the system does not need workload warnings in MVP

## 5. Approval Rules

All critical actions require approval or explicit controlled confirmation.

### Critical actions include:

- duplicate override
- candidate transfer between locations
- role permission escalation
- global visibility grant
- report unlock
- requisition reassignment after work starts
- other company-configured critical actions

### Rule 5.1 Candidate Transfer Between Locations

- candidate transfer is allowed
- selected roles may initiate or perform it
- approval is required
- approval path is configurable by company

### Rule 5.2 Report Unlock

Locked weekly or monthly reports may be unlocked by:

- Admin
- selected report roles

### Rule 5.3 Missing Approver Handling

If a required approver is unavailable:

- escalate to backup approver if available
- otherwise allow reassignment by configured senior role

## 6. Visibility Rules

## 6.1 Candidate Visibility

Global candidate records may be visible to:

- users linked through requisition
- roles with explicit permitted access
- users with approved higher visibility where configured

### Rule 6.1A Candidate Search

Users may search global candidates:

- with full detail if permitted

## 6.2 Audit Visibility

- audit logs must follow scope filtering for all roles except Admin
- Admin always has unrestricted audit visibility
- any non-admin audit visibility requires explicit audit permission

## 6.3 Combined Reporting Visibility

Combined all-location reporting must always be available to:

- Admin

It may also be available to:

- selected configured roles with explicit global reporting access

## 7. Ownership Rules

## 7.1 Client Ownership

Client records should store:

- created by
- business source owner

## 7.2 Requisition Ownership

Requisition records should store:

- primary owner
- secondary contact
- created by
- optional delivery owner

## 7.3 Candidate Ownership

Candidate records should store:

- sourced by
- current owner
- owning location
- duplicate review owner if used
- created by

## 7.4 Ownership History

- ownership history must always be preserved

## 8. Daily Update Rules

### Rule 8.1 Submission Pattern

Each user must submit:

- one main daily summary per day

The system may also allow:

- optional additional updates later the same day

### Rule 8.2 Review Pattern

Daily updates should be reviewed by:

- configured reporting managers
- Admin where needed

## 9. Report Rules

## 9.1 Live And Lockable Reports

The system must support:

- live dashboards
- live operational reports
- lockable weekly reports
- lockable monthly reports

## 9.2 Report Data Quality Warnings

Reports should show:

- incomplete data warning
- stale data warning

## 9.3 Locked Report Behavior

When a report is locked:

- reporting-related edits for that period should be blocked
- the system should preserve reporting integrity for the locked period
- operational edits outside the reporting-sensitive scope do not need to be fully blocked

## 10. Access Change Rules

### Rule 10.1 Permission Removal

If a role loses permission:

- access changes must take effect immediately
- the affected user should receive a notification

### Rule 10.2 User Location Change

If a user changes location:

- current open work must go through manual reassignment review

## 11. Confirmation Rules

All critical actions should require confirmation, even when separate approval is not required.

At minimum:

- delete
- reassign
- reject
- mark joined
- close requisition
- permission changes

## 12. Role Configuration Rules

### Rule 12.1 Role Templates

The system should support:

- protected original templates
- editable copied templates

### Rule 12.2 Access Configuration Model

For MVP, Admin should configure:

- modules
- actions
- scope

Page-level precision may be expanded later.

### Rule 12.3 Over-Access Warning

The MVP should include at least a basic warning for excessive access combinations.

Example:

- global access plus edit rights plus pipeline control

## 13. Pipeline Template Rules

### Rule 13.1 Controlled Pipeline Variants

Pipeline stages may vary based on client or requisition requirement.

But they must be managed through:

- a master stage library
- Admin-managed templates
- client- or requisition-level template assignment

### Rule 13.2 Free-Form Stage Creation

- users should not create free-form stages during live execution

## 14. MVP Enforcement Priorities

The first enforcement priorities should be:

1. location-safe access
2. duplicate review control
3. ownership clarity
4. stage validation
5. immediate permission enforcement
6. locked report integrity
7. audit logging and audit access control

## 15. Summary

The MVP should behave like a controlled, configurable recruitment operating system where:

- Admin governs structure
- locations control operations
- candidates are globally stored but carefully exposed
- duplicates are reviewed before override
- owners are always explicit
- reports can be trusted
- sensitive actions are controlled through confirmation, approval, and audit
