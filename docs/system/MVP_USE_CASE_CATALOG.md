# MVP Use Case Catalog

## Purpose

This document converts the recruitment system plan into clear MVP use cases.

It should be used for:

- backend API design
- database design
- frontend page planning
- permission modeling
- QA scenario creation
- exception and approval design

This is not a role-locked document.

The system has only one fixed product role:

- `Admin`

All other actors below are working-role examples created and assigned by Admin.

## How To Read This Document

Each use case includes:

- business objective
- primary actor
- trigger
- core flow
- result
- important rules
- linked modules

## MVP Use Case Groups

- access and configuration
- organization setup
- client and requisition operations
- candidate and pipeline operations
- execution tracking
- reporting and governance

## Group 1. Access And Configuration Use Cases

### UC-01 User Login

- Business objective:
  Allow a valid user to enter the platform with the correct permission and location context.
- Primary actor:
  Any active user
- Trigger:
  User submits email and password
- Core flow:
  System validates credentials, checks active status, loads assigned role and permission scope, and creates a valid session.
- Result:
  User lands in the correct starting experience with allowed modules only.
- Important rules:
  Inactive users must be blocked. First-login password setup may be required. Session activity must be auditable.
- Linked modules:
  Authentication, Roles and Permissions, User Administration

### UC-02 View Current Access Context

- Business objective:
  Help the user understand what they can access.
- Primary actor:
  Any authenticated user
- Trigger:
  User opens profile or permission summary
- Core flow:
  System returns current user, role, title, location, and effective permission summary.
- Result:
  User understands available modules, pages, and actions.
- Important rules:
  Effective permissions should reflect both role and allowed exceptions if the company enables them.
- Linked modules:
  Authentication, Roles and Permissions

### UC-03 Create Custom Role

- Business objective:
  Allow each company to define its own operating structure without code changes.
- Primary actor:
  Admin
- Trigger:
  Admin creates a new role
- Core flow:
  Admin enters role name, description, allowed modules, pages, actions, and visibility scope.
- Result:
  A reusable custom operational role becomes available for assignment.
- Important rules:
  Admin is the only fixed product role. New roles must be auditable and editable later without breaking historical records.
- Linked modules:
  Roles and Permissions, User Administration

### UC-04 Assign Role To User

- Business objective:
  Put a user into the operating model with correct access.
- Primary actor:
  Admin
- Trigger:
  Admin creates or updates a user
- Core flow:
  Admin selects the user, assigns title, role, location, manager, and status.
- Result:
  User becomes operationally ready with controlled access.
- Important rules:
  A user should not receive operational access without a valid active location.
- Linked modules:
  User Administration, Roles and Permissions, Location Setup

## Group 2. Organization And Governance Use Cases

### UC-05 Create Location

- Business objective:
  Model the company operating structure.
- Primary actor:
  Admin
- Trigger:
  Admin creates a new location
- Core flow:
  Admin enters location name, code, status, and basic metadata.
- Result:
  Location becomes available for user and client assignment.
- Important rules:
  Operational ownership should remain location-bound by default.
- Linked modules:
  Location Setup, User Administration

### UC-06 Create User

- Business objective:
  Add an employee or team member into the system.
- Primary actor:
  Admin
- Trigger:
  Admin opens user creation flow
- Core flow:
  Admin enters identity details, contact fields, employee ID, manager, location, title, role, and activation settings.
- Result:
  User record is created and can proceed to first login setup.
- Important rules:
  Duplicate email, phone, or employee ID must be checked according to company policy.
- Linked modules:
  User Administration, Roles and Permissions, Location Setup

### UC-07 Deactivate User With Active Work

- Business objective:
  Safely remove access without losing operational continuity.
- Primary actor:
  Admin or permitted senior operator
- Trigger:
  User is to be deactivated while still linked to live requisitions, candidates, or updates
- Core flow:
  System shows active ownership and requires reassignment review before completion.
- Result:
  User is deactivated in a controlled way and active work is either reassigned or flagged.
- Important rules:
  Deactivation should not silently orphan live records.
- Linked modules:
  User Administration, Requisitions, Candidates, Pipeline

## Group 3. Client And Requisition Use Cases

### UC-08 Create Client Under A Location

- Business objective:
  Add a client to the commercial and delivery system.
- Primary actor:
  Permitted business-side or admin user
- Trigger:
  User creates a client
- Core flow:
  User enters client profile, contact data, industry, and assigns it to one operating location.
- Result:
  Client becomes available for requisitions inside that location.
- Important rules:
  In MVP, one client belongs to one location for operations. Other locations should not work on that client unless future exception support is added.
- Linked modules:
  Client Directory, Location Control

### UC-09 Add Client Contact

- Business objective:
  Maintain operationally useful contact information for requisitions and communication tracking.
- Primary actor:
  Permitted user
- Trigger:
  User opens client contact create flow
- Core flow:
  User adds primary or secondary contact details, title, contact method, and notes.
- Result:
  Contact becomes selectable inside requisitions for that client.
- Important rules:
  Contact must belong to the same client record.
- Linked modules:
  Client Directory, Requisition Management

### UC-10 Create Requisition

- Business objective:
  Capture a hiring requirement in a structured way.
- Primary actor:
  Permitted user
- Trigger:
  User creates a requisition from a client requirement
- Core flow:
  User selects client and contact, enters role title, openings, priority, skills, acceptable career gap, due date, and update availability window.
- Result:
  Requisition is created and becomes ready for assignment and delivery.
- Important rules:
  Pipeline stages may be configurable by client requirement. Requisition must inherit valid location ownership from the client.
- Linked modules:
  Requisition Management, Client Directory

### UC-11 Update Requisition Status

- Business objective:
  Keep demand tracking accurate through the recruitment lifecycle.
- Primary actor:
  Permitted owner or manager
- Trigger:
  Requisition status changes
- Core flow:
  User updates the requisition from draft, open, on-hold, closed, or cancelled with reason where required.
- Result:
  The requisition lifecycle stays operationally current.
- Important rules:
  Closed or cancelled changes should be auditable. Reopening may require explicit reason.
- Linked modules:
  Requisition Management, Reporting

### UC-12 Assign Requisition To Delivery Team

- Business objective:
  Turn a hiring requirement into actionable recruitment work.
- Primary actor:
  Permitted senior user
- Trigger:
  Requisition is ready for execution
- Core flow:
  System links the requisition to one or more working users through assignment records.
- Result:
  Delivery work ownership becomes visible and trackable.
- Important rules:
  Assignment should stay inside the location by default. Manual reassignment review is required when assignment changes affect live work.
- Linked modules:
  Work Allocation, Requisition Management

## Group 4. Candidate Use Cases

### UC-13 Create Candidate Profile

- Business objective:
  Add a candidate into the company talent pool.
- Primary actor:
  Recruiter or sourcing user
- Trigger:
  User creates a candidate manually or from sourced information
- Core flow:
  User enters identity fields, contact details, skills, source data, social profiles, and ownership details.
- Result:
  Candidate is saved as a global company candidate with controlled access.
- Important rules:
  Candidate is globally searchable for duplicate detection, but operational visibility must remain controlled by access rules.
- Linked modules:
  Candidate Management, Access Control

### UC-14 Upload Resume Or Candidate Document

- Business objective:
  Preserve supporting candidate documents in a structured way.
- Primary actor:
  Recruiter or permitted user
- Trigger:
  User adds resume or document
- Core flow:
  User uploads a file, classifies document type, and links it to the candidate.
- Result:
  Candidate document becomes visible in candidate detail and downstream workflow.
- Important rules:
  File metadata and uploader context should be auditable.
- Linked modules:
  Candidate Management

### UC-15 Detect Candidate Duplicate

- Business objective:
  Avoid duplicate candidate pollution and duplicate submissions for the same work.
- Primary actor:
  Recruiter or permitted user
- Trigger:
  User saves or finalizes a candidate
- Core flow:
  System checks global candidate data using configured fields such as phone, email, and other company rules.
- Result:
  User is warned about possible duplicates before the workflow continues.
- Important rules:
  The user must compare first. Only Admin and selected senior roles should be able to override or delete after review.
- Linked modules:
  Candidate Management, Governance, Audit

### UC-16 Compare And Resolve Duplicate

- Business objective:
  Support controlled cleanup when a probable duplicate is found.
- Primary actor:
  Admin or selected senior role
- Trigger:
  Duplicate warning requires decision
- Core flow:
  System shows both records side by side, highlights conflicts, and allows merge-direction or cleanup decision according to company policy.
- Result:
  Duplicate is resolved without losing audit visibility.
- Important rules:
  Resolution must preserve history and show who approved the action.
- Linked modules:
  Candidate Management, Governance

### UC-17 Link Candidate To Requisition

- Business objective:
  Move a candidate from talent record to active demand.
- Primary actor:
  Recruiter or permitted user
- Trigger:
  Candidate is considered relevant for a requisition
- Core flow:
  User selects a requisition and links the candidate into its active application pipeline.
- Result:
  A requisition-linked candidate application is created.
- Important rules:
  Same candidate-to-same-requisition duplication should be prevented or heavily warned.
- Linked modules:
  Candidate Management, Pipeline, Requisition Management

## Group 5. Pipeline And Delivery Use Cases

### UC-18 View Candidate Pipeline

- Business objective:
  Let operational users track progress on live candidates.
- Primary actor:
  Recruiter, lead, account-facing user, or manager with access
- Trigger:
  User opens the pipeline board or application list
- Core flow:
  System shows requisition-linked candidates grouped by stage, owner, aging, and status.
- Result:
  The user understands current progress and pending actions.
- Important rules:
  Pipeline visibility should move upward for business awareness, while edit rights remain limited to permitted users.
- Linked modules:
  Pipeline, Access Control, Requisition Management

### UC-19 Move Candidate To Next Stage

- Business objective:
  Keep the hiring workflow current.
- Primary actor:
  Permitted operational user
- Trigger:
  Candidate progresses or regresses in the workflow
- Core flow:
  User selects a new stage, enters mandatory note or reason if configured, and confirms the move.
- Result:
  Pipeline stage updates and history is preserved.
- Important rules:
  Stages are configurable by client requirement. Invalid stage moves must be blocked.
- Linked modules:
  Pipeline, Requisition Management

### UC-20 View Pipeline History

- Business objective:
  Maintain accountability and explain candidate movement over time.
- Primary actor:
  Permitted user
- Trigger:
  User opens pipeline history
- Core flow:
  System shows stage timeline, who moved the candidate, notes, and timestamps.
- Result:
  Stakeholders can understand the application journey clearly.
- Important rules:
  History should be append-only and auditable.
- Linked modules:
  Pipeline, Audit

### UC-21 Track Recruiter-Owned Progress

- Business objective:
  Ensure recruiters can continue tracking candidates they sourced or submitted.
- Primary actor:
  Recruiter
- Trigger:
  Recruiter opens their work queue or candidate detail
- Core flow:
  System shows candidates sourced by, owned by, or submitted by the user with live stage progress.
- Result:
  Recruiters stay informed even when higher-level stakeholders are also viewing the same pipeline.
- Important rules:
  Visibility should not require edit authority.
- Linked modules:
  Pipeline, Candidate Management, Dashboards

## Group 6. Daily Execution And Reporting Use Cases

### UC-22 Submit Daily Update

- Business objective:
  Record daily execution output and blockers.
- Primary actor:
  Recruiter or permitted user
- Trigger:
  User submits end-of-day or periodic progress
- Core flow:
  User enters counts, blockers, notes, and next steps for a requisition on a date.
- Result:
  Daily execution data becomes available to leads and reports.
- Important rules:
  Validation behavior for multiple same-day submissions should follow company configuration.
- Linked modules:
  Daily Updates, Requisition Management

### UC-23 Review Team Progress

- Business objective:
  Give seniors a delivery view without needing direct record editing.
- Primary actor:
  Permitted lead, account-facing user, or manager
- Trigger:
  User opens team summary or requisition progress
- Core flow:
  System aggregates assignments, pipeline counts, aging, and daily updates.
- Result:
  Management can identify stalled work and intervene early.
- Important rules:
  This is visibility-first. Edit authority should stay separate.
- Linked modules:
  Dashboards, Pipeline, Daily Updates, Requisitions

### UC-24 View Location Performance

- Business objective:
  Monitor output at operating-location level.
- Primary actor:
  Admin or permitted reporting user
- Trigger:
  User opens dashboard or report
- Core flow:
  System summarizes requisition volume, candidate flow, closures, joins, and daily update activity by location.
- Result:
  Performance can be tracked for each location.
- Important rules:
  Cross-location reporting should be controlled. Admin should always be able to see combined reporting.
- Linked modules:
  Dashboards, Reports, Access Control

### UC-25 View Combined Company Reporting

- Business objective:
  Give top-level governance a complete picture.
- Primary actor:
  Admin and selected reporting roles
- Trigger:
  User opens combined reporting views
- Core flow:
  System aggregates metrics across all locations.
- Result:
  Leadership can compare locations and monitor overall execution.
- Important rules:
  This should not automatically imply edit rights across all records.
- Linked modules:
  Dashboards, Reports, Governance

## Group 7. Governance And Exception Use Cases

### UC-26 Reassign Ownership On Active Work

- Business objective:
  Preserve business continuity when owners change.
- Primary actor:
  Admin or permitted senior user
- Trigger:
  User, candidate, or requisition ownership must change
- Core flow:
  System shows impacted live records, requires confirmation, and logs the reassignment.
- Result:
  Operational ownership changes safely.
- Important rules:
  Manual reassignment review is required where the change may disrupt accountability.
- Linked modules:
  Users, Requisitions, Candidates, Pipeline

### UC-27 Handle Access Denial

- Business objective:
  Protect data while keeping product behavior understandable.
- Primary actor:
  Any user
- Trigger:
  User attempts to open or modify restricted data
- Core flow:
  System denies the action, returns clear reason context, and logs the attempt where appropriate.
- Result:
  Unauthorized access is blocked without silent failure.
- Important rules:
  Upward visibility, location scope, and action permissions must all be respected.
- Linked modules:
  Authentication, Access Control, Audit

### UC-28 Audit Sensitive Changes

- Business objective:
  Preserve trust in the system.
- Primary actor:
  Admin, reviewer, or compliance user
- Trigger:
  Sensitive create, update, override, delete, or reassignment event occurs
- Core flow:
  System stores who changed what, when, why, and on which record.
- Result:
  The platform supports investigation and accountability.
- Important rules:
  Duplicate resolutions, permission changes, status changes, and ownership changes should always be auditable.
- Linked modules:
  Audit, Roles and Permissions, Candidates, Requisitions, Pipeline

## MVP Use Case Priorities

### Must Work End To End

- UC-01 User Login
- UC-03 Create Custom Role
- UC-04 Assign Role To User
- UC-05 Create Location
- UC-06 Create User
- UC-08 Create Client Under A Location
- UC-10 Create Requisition
- UC-12 Assign Requisition To Delivery Team
- UC-13 Create Candidate Profile
- UC-15 Detect Candidate Duplicate
- UC-17 Link Candidate To Requisition
- UC-18 View Candidate Pipeline
- UC-19 Move Candidate To Next Stage
- UC-22 Submit Daily Update
- UC-23 Review Team Progress
- UC-24 View Location Performance
- UC-25 View Combined Company Reporting

### Important But Can Be Hardened In Phase 2

- UC-07 Deactivate User With Active Work
- UC-14 Upload Resume Or Candidate Document
- UC-16 Compare And Resolve Duplicate
- UC-20 View Pipeline History
- UC-26 Reassign Ownership On Active Work
- UC-28 Audit Sensitive Changes

## Key Clarification

Use cases answer:

- what the user is trying to do
- why the product must support it
- what result the system must produce

Exceptions answer:

- what can go wrong
- what must be blocked
- what needs review, override, reassignment, or audit

Both are needed.

Use cases define the normal product.

Exceptions define the safe product.
