# Recruitment System MVP

This project is a recruitment operations system for a multi-location company that handles:

- Internal hiring for the company's own roles
- External hiring for client companies
- Optional client-to-client hiring chains where a client can share requirements from its own client
- Location-wise recruitment teams
- Role-based access control for `Admin`, `Manager`, and `HR`
- Meeting tracking for external business conversations
- Optional portal account scheduling for sourcing tools like `Naukri` and `LinkedIn`
- Daily operational updates with weekly and monthly reporting
- Priority guidance for HR based on urgency, due date, and hiring importance
- Admin review of process quality, productivity, and risks

## Project Structure

- `backend/`
  Active FastAPI backend foundation for the recruitment system
- `frontend/`
  Live prototype pages, shared CSS/JS, and the current routed frontend
- `docs/`
  Product, API, database, roadmap, and reporting documentation
- `scripts/`
  Seed scripts and supporting utilities

## Implementation Status

- Live routed frontend exists in `frontend/` with shared shell, overlay, and validation behavior
- Frontend is wired to the FastAPI backend for login, dashboard, requisitions, candidates, pipeline, and daily updates
- The historical frontend audit is archived in `docs/system/INTEGRATED_FRONTEND_READINESS_AUDIT.md`
- SQL planning and seed scripts exist
- FastAPI backend now exists in `backend/` as the active API implementation
- The old non-FastAPI backend has been removed
- Core FastAPI modules are implemented for auth, permissions, locations, roles, users, clients, requisitions, candidates, pipeline, daily updates, dashboards, and notifications

## Updated Operating Model

Each company location has a recruitment team.

- `Manager`
  - Owns the location recruitment team
  - Talks to external companies for hiring partnerships
  - Conducts or oversees client meetings
  - Converts meetings into external hiring opportunities
  - Tracks whether the requirement came from the direct client or, when applicable, the client's own client
  - Reviews HR performance and update quality for the location

- `HR`
  - Works on internal and external hiring requirements
  - Uses either full-access recruiting accounts or shared recruiting portals based on assigned account availability
  - Follows system-recommended work priority based on target close date, SLA pressure, and requirement criticality
  - Manages requisitions, candidates, interviews, and closures
  - Submits daily operational updates
  - Contributes to weekly and monthly reporting through those updates

- `Admin`
  - Oversees all locations
  - Reviews manager and HR performance
  - Compares location output
  - Audits meeting effectiveness, hiring conversion, SLA performance, and bottlenecks
  - Decides whether process changes are needed

## Core Business Modules

### 1. Location Management

- Location profile
- Manager assignment
- HR team roster
- Location targets
- Location-level internal vs external hiring split

### 2. Client Company Management

- Client company profile
- Optional parent client and end-client relationship support
- Industry
- Primary contact persons
- Meeting history
- Proposal status
- Requirement acceptance status
- Active mandates
- End-client requirement visibility

### 3. Portal Account Management

- Portal account profile
- Platform (`Naukri`, `LinkedIn`, others)
- Location or central ownership
- Optional usage slot allocation for shared accounts
- Next available slot
- Account status
- Daily usage notes

### 4. Requirement Intake And JD Structuring

- Structured JD capture
- Must-have skills
- Good-to-have skills
- Experience range
- Allowed employment gap range
- Required documents such as payslips and relieving letters
- Budget and compensation expectations
- Important notes and exceptions
- Client-round requirement flag

### 5. Meeting Management

- Meeting title
- Location
- Direct client
- End client when applicable
- Meeting type
- Attendance status
- Outcome status
- Notes and minutes
- Follow-up owner
- Follow-up due date

### 6. Requisition Management

- Requisition type (`internal`, `external`)
- Location
- Owner HR
- Requesting department, direct client, or optional end client
- Open positions
- Priority
- SLA
- Required skills
- Budget or fee details
- Due date
- Status
- Priority score for work recommendation

### 7. Candidate Pipeline

- `new`
- `screening`
- `shortlisted`
- `interview`
- `client-review`
- `offered`
- `hired`
- `rejected`
- `on-hold`

### 8. Candidate Evaluation And Rejection Control

- Manager or HR can screen against requirement rules before client round
- Client round can be optional
- Internal-side rejection reasons before client round
- Client-side rejection reasons after client review
- Clear rejection ownership and rejection stage history

### 9. Updates and Reporting

HRs submit:

- Daily operational update
- Weekly performance report
- Monthly performance report

Managers review:

- Location activity report
- External client meeting outcomes
- HR goal achievement
- Open requirement aging
- Portal usage effectiveness

Admins review:

- Company-wide weekly report
- Company-wide monthly report
- Location comparison
- Internal vs external performance
- Manager and HR effectiveness
- Process improvement recommendations

## Suggested Update And Report Structure

### Daily HR Update

- Requisitions worked on
- Candidates sourced
- Candidates screened
- Interviews scheduled
- Interviews completed
- Offers in progress
- Joins completed
- Blockers
- Plan for next day
- Portal used, and when applicable, slot used and next slot needed
- High-priority roles pending

### Weekly HR Report

- Aggregated from daily updates
- Weekly target vs actual
- Stage-wise movement
- Roles closed
- Pending interviews
- Delayed requisitions
- Client dependencies
- Support needed from manager
- Top priority roles still open

### Monthly HR Report

- Aggregated from daily updates and weekly reporting
- Monthly target vs actual
- Conversion ratios
- Time-to-fill
- Offer acceptance
- Join ratio
- High-risk requisitions
- Improvement notes

## Important Process Rules

### Requirement screening rules

Before a candidate reaches client round, the system should allow HR or Manager to validate:

- Required skills match
- Experience match
- Allowed employment gap match
- Required document availability
- Compensation fit
- Joining or notice-period fit

### Client round rules

- Client round may exist or may be skipped
- Internal screening can reject a profile before any client review
- External hiring can move to client review only when the client round is required

### Rejection classification rules

- `internal-side rejection`: rejected by HR or Manager before client round
- `client-side rejection`: rejected by client during or after client review
- Every rejection should store stage, reason, owner, and date

## Current Status

This repo currently includes:

- A refined system design
- RBAC structure
- Location and client meeting workflow model
- Portal account scheduling concept
- Daily-update plus weekly/monthly reporting framework
- Priority-based HR workflow guidance
- Database, roadmap, and screen planning documents
