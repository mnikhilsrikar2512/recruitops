# Universal Recruitment Product Architecture

This document defines the product architecture that should guide execution from August 13, 2026 onward.

It replaces the assumption that every customer will follow one fixed role hierarchy.

## Why This Change Is Needed

The earlier prototype and planning documents assumed this operating chain:

`Admin -> Manager -> HR -> Recruiter`

That model is too narrow for a product intended to be used by many kinds of companies.

Real-world recruitment platforms support multiple operating models, including:

- staffing and recruitment agencies
- in-house talent acquisition teams
- RPO and delivery partners
- executive search firms
- multi-location recruiting operations

The system must therefore be built around configurable titles, permissions, visibility, and workflow ownership instead of a single hard-coded hierarchy.

## Product Design Principles

- fixed admin governance, configurable business roles
- configurable reporting hierarchy
- configurable record visibility and ownership
- support both agency and in-house recruiting models
- support both sales-side and delivery-side workflows
- keep workflow roles separate from permanent user roles
- treat candidates and profiles as records, not system roles

## Core Modeling Rule

The system must separate these concepts:

### 1. Permission Role

Controls what a user can do in the software.

Important rule:

- `Admin` is the only product-defined default role
- all other operational roles should be configurable by Admin
- examples below are illustrative business mappings, not mandatory product roles

### 2. Business Title

Controls how the customer describes the person in their organization.

Examples:

- Director
- BDM
- Account Manager
- Lead Recruiter
- Assistant Recruiter
- Recruiter
- Talent Acquisition Manager
- Talent Partner
- Delivery Manager
- Sourcer
- Coordinator

### 3. Reporting Relationship

Controls who reports to whom inside the customer organization.

Examples:

- a Recruiter reports to a Lead Recruiter
- a Lead Recruiter reports to a Delivery Manager
- a BDM reports to a Director

### 4. Visibility Scope

Controls what records a user can see.

Examples:

- own records only
- assigned team records
- location records
- business unit records
- global records

### 5. Workflow Assignment

Controls who is responsible inside a specific process.

Examples:

- requisition owner
- client owner
- delivery owner
- candidate owner
- approver
- collaborator

## Role Framework

The product should not depend on a fixed universal operational hierarchy.

The product should instead provide:

- one fixed `Admin` role
- configurable operational roles created by Admin
- configurable module access
- configurable feature access
- configurable page access
- configurable action permissions
- configurable visibility scopes

Example customer-created roles may include business, account, delivery, recruiting, support, or review roles.

These examples should guide capability design, but they should not be hard-coded as mandatory system roles.

### 1. Platform Admin

Purpose:

Own tenant-wide configuration, security, and governance.

Typical permissions:

- manage users, teams, locations, and settings
- manage role templates and access rules
- view all records
- manage integrations, automation, and audits
- view executive reports

### 2. Operations Admin

Purpose:

Run operational setup without necessarily owning executive commercial work.

Typical permissions:

- create and maintain master data
- manage users within approved scope
- support workflow configuration
- review system-wide operational dashboards

### 3. Business Lead

Purpose:

Own business development, prospecting, client growth, and high-level account performance.

Typical customer title examples:

- Director
- VP Sales
- BDM Head
- Business Head

Typical permissions:

- manage prospects and strategic accounts
- review meetings, mandates, and conversion metrics
- approve commercial or high-level client actions
- review team-level business performance

### 4. Client Manager

Purpose:

Own client accounts, active relationships, and requirement intake from clients.

Typical customer title examples:

- Account Manager
- Client Partner
- Account Lead
- Business Development Manager

Typical permissions:

- manage clients and contacts
- schedule meetings and follow-ups
- create or confirm client-driven requisitions
- track SLA commitments and client feedback
- view owned account performance

### 5. Delivery Lead

Purpose:

Own recruiting execution quality, team allocation, and delivery outcomes.

Typical customer title examples:

- Lead Recruiter
- Delivery Manager
- Team Lead
- Recruitment Lead

Typical permissions:

- assign requisitions to recruiters
- review candidate quality before submission
- monitor recruiter productivity and pipeline health
- manage escalations, blockers, and workload balance
- approve shortlist or delivery actions where needed

### 6. Recruiter

Purpose:

Run the core candidate delivery workflow.

Typical permissions:

- work assigned requisitions
- source, screen, and submit candidates
- move candidates through pipeline stages
- schedule interviews
- track offers, joins, and rejections
- submit operational updates

### 7. Sourcing Support

Purpose:

Support recruiters with sourcing, data enrichment, early candidate preparation, and admin-heavy candidate tasks.

Typical customer title examples:

- Assistant Recruiter
- Resourcer
- Sourcing Specialist
- Recruiting Coordinator

Typical permissions:

- search talent databases and portals
- upload resumes and create candidate drafts
- enrich candidate records
- prepare submission-ready candidate data
- work under assigned recruiter or delivery lead scope

### 8. Reviewer

Purpose:

Participate in approvals, interviews, or compliance checks without owning full recruiting execution.

Typical customer title examples:

- Hiring Manager
- Interviewer
- Compliance Reviewer
- Department Head

Typical permissions:

- review assigned jobs or candidates
- submit feedback
- approve or reject within limited workflow steps
- see only contextually assigned records

### 9. External User Roles

Purpose:

Allow controlled access for clients, vendors, or partners when needed.

Examples:

- client user
- vendor recruiter
- external interviewer

Typical permissions:

- access only approved shared records
- provide feedback or status updates
- no broad internal visibility

## Example Customer Hierarchies

These are customer templates, not system constraints.

### Agency Template

- Director
- BDM
- Account Manager
- Delivery Lead
- Recruiter
- Assistant Recruiter / Resourcer

### In-House Talent Acquisition Template

- Head of Talent
- Talent Acquisition Manager
- Recruiter
- Coordinator
- Hiring Manager
- Interviewer

### RPO Template

- Client Partner
- Delivery Manager
- Recruiter
- Sourcer
- Coordinator
- Client Reviewer

## Module Architecture

The product should be planned around the following module boundaries.

## Module 1: Identity, Roles, And Permissions

Purpose:

Provide secure access and support universal role modeling.

Core features:

- authentication and session management
- system permission roles
- custom business titles
- reporting-manager mapping
- visibility scopes
- custom role templates
- role-based feature gating
- protected API access
- audit logs for sensitive actions

## Module 2: Organization Structure

Purpose:

Model how each customer is organized.

Core features:

- locations, offices, and business units
- departments and teams
- reporting lines
- team membership
- cross-team assignments
- operating template selection during setup

## Module 3: User Administration

Purpose:

Create, activate, assign, and govern user accounts.

Core features:

- user creation and onboarding
- invitation and setup-link workflows
- title assignment
- role assignment
- location and team assignment
- activation and deactivation
- access review

## Module 4: CRM, Clients, And Accounts

Purpose:

Support customer-side business development and account ownership.

Core features:

- prospects and clients
- account ownership
- client contacts
- account status and stage
- parent and child client relationships
- mandate tracking
- service notes and relationship history

## Module 5: Meetings, Activities, And Follow-Ups

Purpose:

Track communication and next actions across sales and delivery workflows.

Core features:

- meeting scheduling
- call and interaction logging
- attendance and outcome tracking
- follow-up owner assignment
- reminders and due dates
- meeting-to-mandate conversion tracking

## Module 6: Requisitions And Job Intake

Purpose:

Capture internal and external hiring demand in a structured way.

Core features:

- internal and external requisitions
- client and end-client mapping
- structured JD capture
- skills, documents, compensation, and SLA fields
- assignment to delivery owner
- requisition approval hooks
- requisition aging and status tracking

## Module 7: Candidate And Talent Records

Purpose:

Manage profiles as records across the hiring lifecycle.

Core features:

- candidate creation and editing
- resume and document management
- source tracking
- duplicate detection
- candidate ownership
- profile freshness and activity history
- notes and attachments

Important note:

Profiles are candidate records, not user roles.

## Module 8: Screening, Submission, And Pipeline

Purpose:

Move candidates through a controlled delivery workflow.

Core features:

- screening checklists
- submission review
- internal rejection and client rejection classification
- stage movement history
- shortlist approval options
- interview progression
- offer and join tracking

## Module 9: Delivery Operations

Purpose:

Help delivery leads and recruiters manage workload and output.

Core features:

- recruiter and sourcer assignment
- work queues
- load balancing
- priority recommendation
- blocker tracking
- SLA risk visibility
- delivery dashboards

## Module 10: Reports, Dashboards, And Analytics

Purpose:

Support operational visibility for every customer type.

Core features:

- executive dashboards
- business/account performance
- delivery performance
- recruiter productivity
- source effectiveness
- stage conversion
- aging and bottleneck analysis
- location and team comparison

## Module 11: Approvals, Governance, And Audit

Purpose:

Add discipline without forcing every customer into the same workflow.

Core features:

- configurable approval chains
- approval requests by module
- sensitive action review
- audit log reporting
- exception tracking

## Module 12: Automation And AI Assist

Purpose:

Reduce manual work after the core operating model is stable.

Core features:

- resume parsing
- duplicate suggestions
- task reminders
- report drafting
- next-best-action suggestions
- smart queue ordering
- exception alerts

## Execution Priorities

These modules should not be built all at once.

## MVP Execution Scope

Build first:

1. Identity, Roles, And Permissions
2. Organization Structure
3. User Administration
4. CRM, Clients, And Accounts
5. Requisitions And Job Intake
6. Candidate And Talent Records
7. Screening, Submission, And Pipeline
8. Delivery Operations

This gives the product a usable agency-and-enterprise-compatible operating core.

## MVP Contract

The MVP should implement one universal operating contract that is flexible enough for most customers without introducing excessive configurability in the first release.

### MVP Permission Roles

The first release should ship with these permission-role templates:

- `platform_admin`
- `operations_admin`
- `client_manager`
- `delivery_lead`
- `recruiter`
- `sourcing_support`
- `reviewer`

Notes:

- `business_lead` can be mapped temporarily to `client_manager` plus broader scope if we need to keep MVP smaller
- `external_user` should stay out of MVP unless a customer-sharing workflow becomes mandatory

### MVP Business Title Rules

The first release should support configurable business titles, but with a simple administration model:

- create title
- activate or deactivate title
- assign title to user

The MVP does not need:

- title-specific permission overrides
- title-based workflow logic
- title history tracking

### MVP Visibility Model

The first release should support these scopes:

- `global`
- `location`
- `team`
- `own`

The MVP does not need:

- account-level scope rules
- record-by-record custom sharing outside assigned ownership and reviewer workflows
- matrix visibility rules across multiple unrelated teams

### MVP Ownership Model

The first release should support these ownership fields:

- `created_by_user_id`
- `primary_owner_user_id`
- `delivery_owner_user_id`
- `assigned_team_id`

Optional module-specific owner fields:

- `client_owner_user_id`
- `source_owner_user_id`

### MVP Supported Business Models

The MVP should directly support:

- agency delivery teams
- in-house recruiting teams

The MVP should partially support:

- RPO teams through configurable titles and scopes

The MVP should not optimize yet for:

- vendor marketplaces
- external client portals
- complex multi-tenant white-label structures

## Phase 2 Scope

Build next:

1. Meetings, Activities, And Follow-Ups
2. Reports, Dashboards, And Analytics
3. Approvals, Governance, And Audit

## Phase 3 Scope

Build after stable operational data exists:

1. Automation And AI Assist
2. advanced productivity intelligence
3. predictive analytics
4. complex external collaboration workflows

## Data Model Implications

The backend and database design should support:

- user role templates
- custom job titles
- user-to-team assignments
- manager relationships
- record ownership by module
- visibility scope rules
- workflow assignments by record
- approval routing by module and customer configuration

## API Planning Implications

The API should avoid hard-coding narrow role names wherever possible.

Prefer patterns like:

- `permission_role`
- `business_title`
- `reporting_manager_id`
- `visibility_scope`
- `primary_owner_user_id`
- `delivery_owner_user_id`
- `client_owner_user_id`
- `assigned_team_id`

Avoid planning APIs that assume only:

- Admin
- Manager
- HR
- Recruiter

## Product Positioning Advantage

If built this way, the system can serve:

- staffing firms
- executive search firms
- internal hiring teams
- RPO companies
- multi-location recruiting businesses

without rebuilding the core product for each one.

## Execution Rule Going Forward

For all future planning and implementation decisions:

- use universal product roles, not one company-specific hierarchy
- keep customer titles configurable
- treat hierarchy as configuration
- treat permissions as product logic
- treat ownership and visibility as first-class backend concepts
