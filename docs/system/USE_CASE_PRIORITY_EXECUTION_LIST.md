# Use Case Priority Execution List

## Purpose

This document converts the master use-case model into a practical build order.

It helps the team answer:

- what must be built first
- what is required for a usable MVP
- what can be delayed without breaking the MVP
- what should be treated as hardening or future extension

This document should be used together with:

- `docs/system/USE_CASES_AND_EXCEPTIONS_MASTER.md`
- `docs/system/MVP_USE_CASE_API_CONTRACTS.md`
- `docs/system/MVP_USE_CASE_DB_CONTRACTS.md`
- `docs/system/BUILD_PACK_PHASED_IMPLEMENTATION_BACKLOG.md`

## Priority Levels

- `P0 - MVP Core`
  Must exist for the first usable end-to-end product.
- `P1 - MVP Hardening`
  Strongly recommended before production rollout, but the system can still run without full depth here.
- `P2 - Future Extension`
  Valuable capability that should come after the first working MVP.

## Build Logic

A use case belongs in `P0` when all of these are true:

- the module is needed for daily business operations
- removing it breaks the core recruitment workflow
- other modules depend on it

A use case belongs in `P1` when:

- it improves control, safety, reporting, or admin usability
- the MVP still works without the full version of it

A use case belongs in `P2` when:

- it is useful but not required for first release
- it mainly adds flexibility, scale, or governance depth

## P0 - MVP Core Use Cases

### Module 1. Authentication And Session Control

- User login with valid credentials and correct access context
- User logout
- Session validation for authenticated use
- View current access context
- Admin credential reset for user recovery

Why P0:

- the product cannot be used without secure access and permission loading

### Module 2. Roles, Permissions, And Access Configuration

- Admin creates custom role
- Admin assigns modules, pages, actions, and scope to role
- Admin assigns role to user
- User sees only allowed modules and actions

Why P0:

- the system is built around configurable roles, not fixed operational hierarchy

### Module 3. Location And User Administration

- Admin creates location
- Admin activates or deactivates location
- Admin creates user
- Admin edits user profile and assignment context
- Admin views user list
- Admin deactivates user with active-work review

Why P0:

- operational structure cannot function without users and locations

### Module 4. Client Directory

- Create client under one location
- Add primary and secondary client contacts
- Edit client profile and status
- Search and list clients
- View client detail with linked contacts and requisitions

Why P0:

- requisitions depend on active clients and contacts

### Module 5. Requisition Management

- Create requisition
- Capture required requisition fields
- Assign operational ownership
- Update requisition status
- View requisition list and detail

Why P0:

- requisition intake is the starting point of delivery execution

### Module 6. Work Allocation And Assignment

- Assign recruiter or contributor to requisition
- View assignment ownership
- Reassign work with tracked review

Why P0:

- recruitment work cannot start without clear allocation

### Module 7. Candidate Management

- Create candidate profile
- Edit candidate profile before final submission
- Search candidate records
- View candidate detail
- Run duplicate detection
- Finalize candidate into requisition pipeline

Why P0:

- candidate creation and duplicate-safe submission are central to the platform

### Module 8. Pipeline Tracking

- View pipeline board or pipeline list
- View application detail and stage history
- Move candidate through valid stages
- Track pipeline progress by requisition

Why P0:

- the platform must support live recruitment progress after submission

### Module 9. Daily Updates And Execution Tracking

- Post daily update
- View updates linked to active work
- Review team execution summary

Why P0:

- daily execution visibility is part of the agreed MVP operating model

### Module 10. Dashboards, Reports, And Governance

- Admin views company-wide summary
- Permitted user views location summary
- View core requisition, candidate, and pipeline metrics

Why P0:

- leadership and oversight need summary visibility from the first release

## P1 - MVP Hardening Use Cases

### Module 1. Authentication And Session Control

- First-login password setup flow
- Suspicious access tracking depth
- Revocation behavior for active sessions after credential reset

### Module 2. Roles, Permissions, And Access Configuration

- Sensitive permission-combination warnings
- Direct grant or access-exception support
- Read-only reviewer-style access refinement

### Module 3. Location And User Administration

- User detail page with complete access and ownership summary
- Controlled user move workflow with reassignment review
- More advanced duplicate checks for phone and employee ID by company policy

### Module 4. Client Directory

- Stronger duplicate detection for client creation
- Better correction flow for wrongly assigned location before operations begin

### Module 5. Requisition Management

- Controlled requisition reopening with mandatory reason
- Requisition history depth and audit visibility
- Better handling for inactive-client override scenarios

### Module 6. Work Allocation And Assignment

- Workload balancing view
- Contributor role refinement
- Stronger reassignment warnings when active candidate work exists

### Module 7. Candidate Management

- Duplicate compare-first review flow with richer side-by-side comparison
- Controlled owner correction workflows
- Better draft-versus-final validation states
- Document metadata depth and validation

### Module 8. Pipeline Tracking

- Stage backward movement reason capture
- Stale pipeline aging indicators
- Better invalid-transition guidance

### Module 9. Daily Updates And Execution Tracking

- Reminder behavior for missed updates
- Review locks for finalized update periods
- Better blocker escalation visibility

### Module 10. Dashboards, Reports, And Governance

- Governed export permissions
- Company-configurable reporting scope
- Optional locked reporting periods
- Sensitive-report access traceability

## P2 - Future Extension Use Cases

### Module 1. Authentication And Session Control

- Advanced enterprise authentication such as SSO or MFA
- More advanced session-risk policies

### Module 2. Roles, Permissions, And Access Configuration

- Complex access policy templates
- Rule-driven permission recommendations

### Module 3. Location And User Administration

- Multi-location user operating models
- More advanced org-chart management

### Module 4. Client Directory

- Shared client model across multiple locations
- More complex relationship hierarchies between parent and child clients

### Module 5. Requisition Management

- Fully dynamic requisition workflow designer
- Rich approval chains for intake and closure

### Module 6. Work Allocation And Assignment

- Automated assignment suggestion engine
- Skill-capacity based workload optimization

### Module 7. Candidate Management

- Resume parsing orchestration
- Bulk import pipelines
- Advanced candidate merge intelligence

### Module 8. Pipeline Tracking

- Deep client-specific workflow engine
- Advanced SLA tracking and automation

### Module 9. Daily Updates And Execution Tracking

- Automated follow-up engine
- Scheduled escalation chains

### Module 10. Dashboards, Reports, And Governance

- Snapshot-based governance reporting at scale
- Enterprise analytics packs
- Client-facing reporting portals

## Cross-Module Priority Rules

### P0 Cross-Module Rules

- one client belongs to one location for operations
- candidates are global for duplicate detection
- visibility can move upward while edit rights stay restricted
- duplicate handling must use compare-first logic
- active work must not be silently orphaned

### P1 Cross-Module Rules

- more approval depth for risky edits
- stronger audit visibility for sensitive actions
- more configurable reporting controls

### P2 Cross-Module Rules

- cross-location operating exceptions
- advanced automation
- enterprise-scale governance layers

## Suggested Execution Order

### Phase 1

- Authentication and session control
- Roles and permissions
- Locations and users

### Phase 2

- Clients and contacts
- Requisitions
- Work allocation

### Phase 3

- Candidates
- Duplicate handling
- Pipeline tracking

### Phase 4

- Daily updates
- Dashboards and reports
- P1 hardening gaps

### Phase 5

- P2 extension planning

## Minimum End-To-End MVP Flow

The product should not be called usable until this full flow works:

1. Admin creates location.
2. Admin creates role and permissions.
3. Admin creates users.
4. User logs in.
5. User creates client and contact.
6. User creates requisition.
7. User assigns delivery work.
8. Recruiter adds candidate.
9. System checks duplicates.
10. Candidate is finalized into pipeline.
11. Pipeline stages are updated.
12. Daily execution update is posted.
13. Reporting users view location or company summary.

If any of these steps is missing, the MVP is still incomplete.
