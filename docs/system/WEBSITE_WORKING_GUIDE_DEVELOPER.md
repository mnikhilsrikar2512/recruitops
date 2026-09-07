# Recruitment System Website Guide For Developers

This document is the technical developer-facing version of how the recruitment system website works.

It is intended for:

- backend developers
- frontend developers
- full-stack engineers
- architects
- QA engineers
- implementation teammates

## 1. Development Goal

The website should be built as a configurable recruitment operating platform.

It must support multiple business models while keeping a stable internal architecture.

The key implementation rule is:

do not hard-code one company hierarchy into product logic.

Instead, model:

- permission roles
- business titles
- reporting relationships
- visibility scopes
- record ownership
- workflow assignments

## 2. Core Product Model

The website is not only a UI layer.

It is the operational surface of a role-aware system where:

- authenticated users are routed to a role-appropriate landing page
- navigation is filtered by permission role
- data access is filtered by scope and ownership
- workflow state changes update reporting outputs

## 3. Internal Concepts That Must Stay Separate

### Permission role

Permission roles control access behavior.

Examples:

- `platform_admin`
- `operations_admin`
- `business_lead`
- `client_manager`
- `delivery_lead`
- `recruiter`
- `sourcing_support`
- `reviewer`

These should be stable product-level codes.

### Business title

Business titles are customer-defined labels.

Examples:

- Director
- BDM
- Account Manager
- Lead Recruiter
- Talent Partner

These should not drive authorization by themselves.

### Scope

Scopes control visibility.

MVP scopes:

- `global`
- `location`
- `team`
- `own`

### Ownership

Every important record should have ownership fields.

Common fields:

- `created_by_user_id`
- `primary_owner_user_id`
- `delivery_owner_user_id`
- `client_owner_user_id`
- `assigned_team_id`

### Workflow assignment

This allows contextual access.

Examples:

- reviewer assigned to candidate
- approver assigned to requisition
- sourcer assigned to requisition

## 4. How The Website Works End To End

At runtime the website should behave like this:

1. user lands on login page
2. authentication succeeds
3. backend returns user profile with permission role, title, location, team, scope, and permissions
4. frontend routes user to correct landing page
5. sidebar is built from permission-aware configuration
6. page-level API requests are filtered by scope and ownership
7. user performs workflow actions
8. those actions update records, stage history, and dashboard inputs

## 5. Main Functional Domains

## A. Identity And Access

Responsibilities:

- login
- logout
- password reset
- session management
- permission evaluation
- route protection

Implementation implications:

- backend must enforce permission checks
- frontend route gating is helpful but not sufficient
- `auth/me` response should include permission role, title, scope, and dashboard context

## B. Organization Structure

Responsibilities:

- company profile
- locations
- teams
- reporting-manager relationships
- title setup

Implementation implications:

- organization data should be its own domain
- location and team membership should not be hidden inside one overloaded user field

## C. CRM And Client Work

Responsibilities:

- client records
- contacts
- meetings
- follow-ups
- account ownership

Implementation implications:

- client-side records should support owner and status fields
- activity timelines should eventually connect to clients and requisitions

## D. Requisition And Delivery Work

Responsibilities:

- requisition creation
- structured JD storage
- delivery assignment
- candidate linking
- stage movement

Implementation implications:

- requisition domain is central to the product
- ownership and team assignment must be explicit
- structured JD should be stored in a queryable way even if MVP uses JSON for some sections

## E. Candidate And Pipeline Work

Responsibilities:

- candidate create and update
- document upload
- duplicate checks
- screening
- stage transitions
- outcome tracking

Implementation implications:

- candidate domain should support multiple requisition links over time
- stage history should be append-oriented, not overwrite-only
- duplicate checks should produce decision state, not just warnings

## F. Reporting And Governance

Responsibilities:

- dashboards
- role-based summaries
- approvals later
- audit later

Implementation implications:

- dashboards should derive from transactional data
- reporting should not depend on manual side-entry

## 6. Primary User Flows

## Internal Hiring Flow

Implementation path:

1. requisition created
2. delivery owner assigned
3. recruiter or sourcer assigned
4. candidate records created
5. screening recorded
6. stage transitions stored
7. final outcome stored
8. dashboard aggregates updated

## External Client Hiring Flow

Implementation path:

1. client interaction logged
2. external requisition created
3. delivery owner assigned
4. candidate sourcing begins
5. candidate screening and submission occurs
6. feedback and stage transitions recorded
7. offer or placement tracked
8. account and delivery reporting updated

## 7. Role-Specific Development View

## Platform Admin

System responsibilities:

- user and access control
- location and team setup
- executive dashboards
- audit and sensitive configuration

Must be able to:

- create and manage users
- assign permission roles and titles
- manage locations and teams
- access executive and governance views

## Operations Admin

System responsibilities:

- maintain setup quality
- support onboarding
- fix master-data issues

Must be able to:

- manage selected org records
- maintain user assignment integrity
- support operational setup within scope

## Business Lead

System responsibilities:

- review account pipeline and strategic performance

Must be able to:

- access business dashboard
- review account health and mandate conversion

## Client Manager

System responsibilities:

- own clients
- manage contacts
- log meetings
- create external requisitions

Must be able to:

- manage client records in scope
- manage follow-ups
- create requisitions tied to client demand

## Delivery Lead

System responsibilities:

- own requisition execution
- allocate work
- review candidate readiness

Must be able to:

- manage requisitions in scope
- assign recruiters and sourcers
- access delivery dashboards

## Recruiter

System responsibilities:

- create and progress candidate work

Must be able to:

- view assigned requisitions
- create and update candidates
- upload documents
- run duplicate checks
- transition stages

## Sourcing Support

System responsibilities:

- prepare candidate drafts
- support sourcing throughput

Must be able to:

- create limited candidate drafts
- upload resumes
- enrich sourcing data

## Reviewer

System responsibilities:

- provide contextual feedback and limited decisions

Must be able to:

- see assigned review items only
- submit feedback or decision

## 8. Frontend Behavior Expectations

The frontend should:

- resolve a current role context after login
- show a scoped sidebar
- show role-appropriate landing pages
- gracefully handle unauthorized routes
- support shared pages that render slightly differently by role

Examples:

- same dashboard shell may be shared between HR and recruiter in prototype mode
- profile/settings page may be shared across roles
- notifications can be role-specific even when structurally similar

## 9. Backend Behavior Expectations

The backend should:

- enforce access rules at API level
- filter list responses by scope and ownership
- reject unauthorized mutation requests
- return enough identity context to let frontend render correctly
- keep ownership and stage state auditable

The backend must never trust the frontend to enforce access.

## 10. Data Model Expectations

At minimum, the data model should support:

- users
- permission roles
- business titles
- user sessions
- locations
- teams
- team memberships
- user scope assignments
- clients
- client contacts
- requisitions
- requisition assignments
- candidates
- candidate documents
- duplicate checks
- stage history

## 11. API Expectations

The API should prefer stable, product-level concepts.

Good patterns:

- `permission_role`
- `business_title`
- `visibility_scope`
- `primary_owner_user_id`
- `delivery_owner_user_id`
- `assigned_team_id`

Avoid:

- building all access logic around only `Admin`, `Manager`, `HR`, `Recruiter`
- assuming one fixed hierarchy in every endpoint response

## 12. Dashboard Expectations

Dashboards should be capability-based.

Examples:

- executive dashboard
- business dashboard
- delivery dashboard
- recruiter dashboard
- my-work dashboard

Dashboards should not be implemented only as hard-coded role pages without reusable data services underneath.

## 13. Frontend Prototype Versus Future Product

The current prototype still reflects old role naming in places.

That is acceptable for the prototype, but future implementation should follow the universal architecture:

- keep current role mapping where needed for compatibility
- move backend contracts to universal roles
- treat current pages as transitional UI assets

## 14. MVP Build Priorities

The MVP should focus on:

- auth
- roles and titles
- location and team assignment
- user management
- client management
- requisition creation and assignment
- candidate creation
- duplicate checks
- stage transitions
- delivery and role-aware dashboards

Defer:

- advanced approvals
- deep audit center
- AI-heavy workflows
- full external user portal

## 15. QA Expectations

QA should validate:

- correct route access by role
- correct API denial for unauthorized actions
- correct location/team/own visibility filtering
- candidate stage integrity
- duplicate-check behavior
- dashboard data consistency

## 16. Final Summary

For developers, the website should be understood as a role-aware operational system with configurable business titles and fixed product permissions.

The most important engineering rule is:

keep access logic stable, keep titles flexible, and make scope plus ownership first-class parts of the implementation.
