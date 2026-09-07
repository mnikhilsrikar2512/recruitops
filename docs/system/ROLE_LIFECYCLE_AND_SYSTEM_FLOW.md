# Role Lifecycle And System Flow

## Important Note

This document is aligned to the universal product model introduced on August 13, 2026.

Do not treat one fixed chain such as `Admin -> Manager -> HR -> Recruiter` as the product lifecycle.

Use this document to understand configurable operating flows. Use `docs/system/UNIVERSAL_PRODUCT_ARCHITECTURE.md` for the canonical role model.

## 1. Overall System Flow

The system should support multiple customer operating models through the same platform.

The universal flow is:

1. tenant setup defines permission roles, business titles, teams, locations, and reporting relationships
2. business-side users manage prospects, clients, meetings, and hiring demand
3. delivery-side users manage requisitions, sourcing, screening, submissions, and pipeline movement
4. reviewer or approver roles participate where configured
5. the system turns operational data into dashboards, reports, alerts, and audit history

## 2. Setup Lifecycle

This is the first lifecycle before recruiting work begins.

### Step 1. Tenant setup

- create company profile
- define countries, locations, business units, and teams
- choose an operating template such as agency, in-house, or RPO
- define business titles
- define permission roles and scope rules
- define approval rules and reporting templates

### Step 2. User setup

- create users
- assign permission role
- assign business title
- assign location, team, and scope
- assign reporting manager where relevant
- use manual password, generated password, or setup-link onboarding

### Step 3. Access setup

- apply role permissions
- assign visibility scopes
- assign record-ownership defaults
- ensure each user sees only authorized data and actions

## 3. Universal Daily Lifecycles

These are capability-based lifecycles, not mandatory job titles.

## Platform Admin Lifecycle

Purpose:

Own system governance, security, and configuration.

Typical daily actions:

- review tenant-wide dashboard
- manage users, roles, scopes, and team setup
- review audit logs and exceptions
- review sensitive approvals when configured
- maintain integrations and automation settings

## Business Lead Lifecycle

Purpose:

Own sales-side and executive business performance.

Typical daily actions:

- review prospect and client pipeline
- review meeting outcomes and mandate conversion
- review account-level bottlenecks
- approve strategic or commercial actions where needed
- monitor team-level business performance

## Client Manager Lifecycle

Purpose:

Own active accounts, client communication, and requirement intake.

Typical daily actions:

- contact clients or prospects
- schedule and log meetings
- record follow-ups and commitment dates
- convert client demand into requisitions
- track SLA expectations and client-side blockers

## Delivery Lead Lifecycle

Purpose:

Own delivery quality, work allocation, and recruiting output.

Typical daily actions:

- review delivery dashboard and work queues
- assign requisitions to recruiters or sourcing support
- review candidate quality before submission when needed
- manage blockers, escalations, and workload balance
- review requisition progress and team productivity

## Recruiter Lifecycle

Purpose:

Own active candidate delivery and pipeline execution.

Typical daily actions:

- review assigned requisitions
- source and screen candidates
- update candidate records
- progress submissions, interviews, and offers
- record blockers and daily progress

## Sourcing Support Lifecycle

Purpose:

Support recruiters with sourcing and candidate preparation.

Typical daily actions:

- search portals and databases
- upload resumes and create candidate drafts
- enrich candidate profiles
- validate basic record completeness
- hand prepared profiles to the assigned recruiter or delivery lead

## Reviewer Lifecycle

Purpose:

Participate in context-specific review and approval steps.

Typical daily actions:

- review assigned jobs or candidates
- provide interview or workflow feedback
- approve or reject within assigned scope
- view only the records shared into the workflow

## 4. Universal Operational Flows

## External Client-Driven Hiring Flow

1. a client-facing user logs a meeting or client conversation
2. the system records outcome, follow-up, and commercial context
3. a requisition is created from client demand
4. a delivery lead becomes the delivery owner
5. recruiters and sourcing support are assigned
6. candidate intake, screening, and submission begin
7. client feedback, interviews, offers, and placements are tracked
8. dashboards reflect both account performance and delivery performance

## Internal Hiring Flow

1. an internal hiring need is raised
2. a requisition is created with structured fields
3. a delivery lead or recruiter is assigned
4. sourcing and screening begin
5. reviewers and interviewers provide feedback
6. offer and join steps are tracked
7. dashboards reflect velocity, quality, and close-rate

## 5. Reporting Flow

Operational data should be entered by the people doing the work and then rolled up according to role, team, location, and ownership.

The reporting flow should support:

- executive visibility by business unit or location
- account visibility by client owner
- delivery visibility by delivery lead
- recruiter productivity and stage movement
- SLA and bottleneck reporting

## 6. Execution Rule

For product planning and implementation:

- use capability-based system roles
- let customers define business titles
- let customers define reporting lines
- use ownership and visibility rules to control workflow access
- never treat profiles or candidates as user roles
