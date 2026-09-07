# Business Analysis Document

## Project Name

Configurable Recruitment Management System

## Document Purpose

This business analysis document explains the business need, product direction, functional scope, constraints, and MVP priorities for the recruitment system.

For detailed MVP business flows, also use:

- `docs/system/MVP_USE_CASE_OVERVIEW.md`
- `docs/system/USE_CASES_AND_EXCEPTIONS_MASTER.md`
- `docs/system/MVP_USE_CASE_CATALOG.md`
- `docs/system/MODULE_WISE_USE_CASES_AND_EXCEPTIONS.md`

It reflects the updated product decision made on August 17, 2026:

- the system will not define fixed operational roles except `Admin`
- `Admin` will define roles, modules, features, pages, actions, and access scope
- the product team will focus on stable modules and workflows
- operational users and operational records must belong to a location
- candidates should be global at company level, but access remains controlled

## Executive Summary

Recruitment companies and talent teams do not all operate with the same hierarchy.

Some use:

- BDM
- Account Manager
- Lead Recruiter
- Recruiter

Others use:

- Sales Head
- Client Partner
- Delivery Manager
- Talent Specialist

Others use completely different structures.

Because of this, a role-predefined product will always become restrictive, expensive to customize, and difficult to scale across companies.

The better business approach is:

- define one fixed governance role: `Admin`
- let Admin create all other roles
- keep modules stable
- keep workflows stable
- keep permissions configurable
- keep location control strict for operations
- keep reporting stable even when workflow templates vary by client

## Business Problem

Traditional recruitment systems often fail in one or more of these ways:

- they assume one fixed organization hierarchy
- they combine business title and software permissions
- they do not isolate location data well
- they do not support configurable role visibility
- they require code changes when a company wants a different process structure
- they give too much access to some roles and too little to others

This creates:

- slow onboarding
- poor fit for different companies
- unnecessary customization cost
- permission confusion
- reporting inconsistency
- location-level data leakage risk

## Business Goal

Build a recruitment system that:

- works for many kinds of companies
- does not depend on fixed non-admin roles
- lets Admin configure the system structure
- supports stable recruitment workflows
- keeps location data controlled
- supports one client belonging to one operating location by default
- supports global duplicate-aware candidate intelligence
- supports reporting without hard-coding organization structure

## Business Objectives

- reduce dependency on custom development for role structure changes
- make onboarding easier for different companies
- keep access control manageable and auditable
- support end-to-end recruitment operations
- enable role-specific experience without hard-coded role assumptions
- allow growth from MVP to larger enterprise models

## Why Use Cases Matter

The module list alone is not enough to build the product correctly.

We also need use cases because they define:

- who is trying to do the work
- what business result they expect
- what page or workflow they use
- what API and DB support is required
- what validations, exceptions, and audit rules must apply

In this product, use cases must remain stable even when company hierarchies differ.

That means:

- one company may configure `BDM`
- another may configure `Client Partner`
- another may configure `Delivery Manager`

But the underlying use cases stay the same:

- create client
- create requisition
- assign delivery work
- create and review candidate
- move pipeline
- submit updates
- review reports

This is how the system stays usable by many companies without hard-coding a single hierarchy.

## Detailed Use Case Groups

At the business level, the MVP use cases follow one operating chain:

1. access and setup
2. client and requisition intake
3. delivery assignment
4. candidate creation and duplicate control
5. pipeline execution
6. daily tracking and reporting

The most important MVP use cases are:

- login and access loading
- create location
- create custom role
- create user
- create client
- add client contact
- create requisition
- assign delivery ownership
- create candidate
- upload resume
- detect duplicate candidate
- resolve duplicate candidate when needed
- link candidate to requisition
- screen candidate
- view and move pipeline
- submit daily update
- review daily updates
- view location reporting
- view company reporting

Detailed actor, page, API, and database mapping for these use cases is maintained in:

- `docs/system/MVP_USE_CASE_OVERVIEW.md`
- `docs/system/MVP_USE_CASE_EXECUTION_MATRIX.md`
- `docs/system/MVP_USE_CASE_API_CONTRACTS.md`
- `docs/system/MVP_USE_CASE_DB_CONTRACTS.md`

## Core MVP Use Cases

This section answers the business question:

- what will users actually do in the system from day to day

The product is not just a set of modules.

It is a sequence of use cases that must work together end to end.

### Stage 1. Access And Setup

- user logs in and the system loads the correct access context
- Admin creates locations
- Admin creates custom roles
- Admin creates users and assigns access
- user sees only the pages, actions, and data scope allowed to them

Business meaning:

- the platform becomes configurable without code changes
- each company can model its own operating structure
- operational access starts with controlled setup

### Stage 2. Client And Requisition Intake

- permitted user creates a client under one location
- permitted user adds one or more client contacts
- permitted user creates a requisition from a client requirement
- permitted user updates requisition status as intake progresses

Business meaning:

- demand enters the system in a structured and location-safe way
- requisition ownership starts from a real client and real contact
- intake can adapt to different company hierarchies without changing the product model

### Stage 3. Delivery Assignment

- permitted senior user assigns the requisition to delivery users
- senior user reviews current work allocation
- senior user reassigns ownership when needed

Business meaning:

- requisitions move from business intake into actual execution
- ownership becomes visible and accountable
- work continuity is protected when people move, leave, or become unavailable

### Stage 4. Candidate Creation And Quality Control

- recruiter or sourcing user creates a candidate profile
- recruiter uploads and reviews resume details
- system checks for duplicate candidates globally
- Admin or allowed senior user resolves duplicate conflicts safely
- recruiter links the candidate to a requisition
- recruiter completes candidate screening

Business meaning:

- candidate data becomes reusable across the company
- duplicate records are controlled before they damage pipeline quality
- the same platform supports both talent creation and requisition-specific submission

### Stage 5. Pipeline Execution

- recruiter views the candidate pipeline for linked requisitions
- recruiter sees progress for candidates they sourced or submitted
- permitted senior users review wider pipeline progress
- allowed users move candidates from one stage to another based on workflow rules

Business meaning:

- execution is visible from recruiter level upward
- visibility can move upward without automatically expanding edit rights
- client-specific pipeline stages can still fit inside one stable product flow

### Stage 6. Execution Monitoring And Reporting

- recruiter submits daily updates
- senior users review updates, blockers, and team progress
- users review operational notifications
- reporting users review location performance
- Admin or allowed reporting users review combined company performance

Business meaning:

- execution quality is tracked continuously
- management gets visibility without depending on informal follow-up
- Admin can monitor location-level and company-wide performance safely

## Use Case Design Rules

Every future feature should pass these use-case checks:

1. which business outcome does it support
2. which actor performs it
3. which page or workflow handles it
4. which API contract supports it
5. which database records and history support it
6. which exception, warning, or approval path is required

If a feature does not clearly fit a real use case, it should not be treated as MVP-ready.

## Most Important End-To-End Journey

For the MVP to be truly buildable as a usable product, this full chain must work:

1. Admin creates location, role, and user.
2. Permitted user creates client and contact.
3. Permitted user creates requisition.
4. Permitted senior user assigns delivery ownership.
5. Recruiter creates candidate and uploads resume.
6. System runs duplicate review.
7. Authorized user resolves duplicate if needed.
8. Recruiter links candidate to requisition.
9. Recruiter and senior users track pipeline progress.
10. Recruiter submits updates.
11. Senior users and reporting users review execution and reports.

If any one of these steps is missing:

- page support
- permission support
- API support
- DB support
- exception handling

then the product is not yet end-to-end ready.

## Stakeholders

### Primary Stakeholders

- product owner
- business owner
- admin users
- recruitment operations users
- delivery users
- reporting users

### Secondary Stakeholders

- implementation team
- support team
- compliance reviewers
- client-facing coordinators

## Scope Decision

## In Scope For MVP

- admin configuration
- locations
- users
- configurable roles
- configurable module access
- configurable page access
- configurable feature access
- configurable scope access
- client directory
- requisitions
- work allocation
- candidates
- pipeline tracking
- daily updates
- dashboards and reports

## Out Of Scope For MVP

- advanced approval engine
- complex workflow designer
- billing and invoicing
- external client portals
- AI parser orchestration
- advanced automation engine
- enterprise SSO and MFA
- multi-tenant shared client logic across locations

## Key Business Decision

The product will separate:

- business title
- system role
- page access
- feature access
- action permission
- visibility scope

This is the most important architecture and business decision in the project.

## Business Model Assumptions

- every company has at least one Admin
- Admin is trusted to configure the working structure
- operational users work within location-safe access
- location-level data isolation is required by default
- client ownership should stay location-bound by default
- candidate records should be global, but candidate access should still be controlled
- combined reporting must always be available to Admin

## Functional Model

The product should be built around stable modules, not fixed job hierarchies.

### Module 1. Authentication And Access

Business value:

- secure entry into the system
- correct loading of configured permissions and scope

### Module 2. Role And Permission Configuration

Business value:

- gives each company flexibility without code changes
- reduces future customization cost

### Module 3. Location And User Administration

Business value:

- lets each company mirror its operating structure
- enables location control and reporting

### Module 4. Client Directory

Business value:

- maintains client and contact data as the commercial base for recruitment work
- keeps client ownership clearly tied to one location in MVP

### Module 5. Requisition Management

Business value:

- captures demand in a structured way
- makes requisition ownership visible

### Module 6. Work Allocation

Business value:

- translates demand into operational execution
- makes work ownership clear

### Module 7. Candidate Management

Business value:

- centralizes candidate records
- improves sourcing, tracking, and duplicate control
- enables company-wide duplicate detection through a global candidate model

### Module 8. Pipeline Tracking

Business value:

- gives operational visibility into candidate progress
- supports different visibility levels by configured role
- supports client- or requisition-specific pipeline templates in a controlled way

### Module 9. Daily Updates

Business value:

- captures daily progress and blockers
- improves management visibility

### Module 10. Dashboards And Reports

Business value:

- gives decision-makers timely summary views
- supports location and combined reporting
- supports both live operational visibility and lockable weekly or monthly reporting

## MVP Use Case View

For MVP, the product should be designed around a small set of end-to-end business use cases.

These use cases are more important than titles because titles vary by company, but business actions do not.

### Use Case Group 1. Governance Setup

Main outcome:

- Admin prepares the company to use the system

Core use cases:

- create location
- create custom role
- assign modules, pages, and actions to role
- create user
- assign role, title, manager, and location to user
- deactivate or move user through controlled review

### Use Case Group 2. Client And Demand Intake

Main outcome:

- a location-owned client requirement becomes an executable requisition

Core use cases:

- create client under one location
- add primary and secondary client contacts
- create requisition from client requirement
- capture skills, acceptable career gap, target date, and update availability time
- assign business-side and operational ownership
- update requisition status through its working lifecycle

### Use Case Group 3. Delivery Allocation

Main outcome:

- live work is assigned to the right execution team without breaking location control

Core use cases:

- assign recruiter or contributor to requisition
- reassign ownership when capacity changes
- review assignment history and workload continuity

### Use Case Group 4. Candidate Intake And Quality Control

Main outcome:

- candidate records are created once, reviewed safely, and linked correctly to demand

Core use cases:

- create candidate profile
- upload or enter candidate details
- save draft or finalize candidate record
- detect duplicate candidate globally
- compare duplicate before override, discard, or use-existing decision
- link candidate to requisition

### Use Case Group 5. Pipeline Execution

Main outcome:

- recruiters and supervisors can track live delivery progress against requisitions

Core use cases:

- view candidate pipeline for linked requisitions
- allow recruiters to track candidates they sourced or submitted
- move candidate across configured pipeline stages
- capture stage-specific details when required
- review stage history and stalled profiles

### Use Case Group 6. Daily Execution Tracking

Main outcome:

- operational progress becomes visible every day

Core use cases:

- submit daily update linked to requisition
- review update counts, blockers, and missing submissions
- monitor team progress without taking over execution rights

### Use Case Group 7. Reporting And Governance

Main outcome:

- leadership gets visibility without unnecessary operational access

Core use cases:

- view personal dashboard
- view location performance dashboard
- view combined company dashboard
- review audit trail for sensitive changes
- review duplicate decisions, reassignments, and status changes

## MVP End-To-End Working Story

The MVP is only business-ready if this full chain works:

1. Admin creates location, role, permission scope, and users.
2. A permitted intake-side user creates a client and its contacts.
3. A permitted user creates a requisition under that client and location.
4. A permitted senior or delivery-side user assigns the requisition to recruiters.
5. A recruiter creates or uploads a candidate profile.
6. The system runs duplicate checks against the global candidate base.
7. The recruiter links the candidate to the requisition and starts live pipeline tracking.
8. The recruiter and allowed supervisors update or review stage progress.
9. The recruiter submits daily updates linked to requisition work.
10. Senior users, reporting users, or Admin review location and company performance.

If any one of these steps is missing in page design, API design, DB design, permissions, or exception handling, then the MVP is not fully usable end to end.

## Use Case Design Rules

Every use case in this product should follow these rules:

- operational records must respect location control unless the product explicitly allows otherwise
- candidate records remain global for duplicate detection
- visibility may move upward, but edit rights must remain intentionally limited
- duplicate handling must follow compare-first governance
- reassignment of active work must be reviewed and audited
- pipeline stages may be configurable by client or requisition requirement
- page access alone is not enough; action-level permissions must also be enforced
- all sensitive changes must be traceable

## Primary Use Case References

Use these documents during execution:

- `docs/system/MVP_USE_CASE_OVERVIEW.md`
- `docs/system/USE_CASES_AND_EXCEPTIONS_MASTER.md`
- `docs/system/MVP_USE_CASE_CATALOG.md`
- `docs/system/MVP_USE_CASE_ACTOR_MATRIX.md`
- `docs/system/USE_CASE_PRIORITY_EXECUTION_LIST.md`
- `docs/system/MVP_USE_CASE_API_CONTRACTS.md`
- `docs/system/MVP_USE_CASE_DB_CONTRACTS.md`

## Non-Functional Business Requirements

- configurable without code changes for role structure
- location-safe data access
- auditable access configuration
- clear ownership on operational records
- scalable to support different company models
- understandable for admins during setup
- strong enough to prevent accidental duplicate pollution
- clear enough to support ownership transfers only through controlled approval

## Access And Governance Requirements

### Fixed Rule

- `Admin` is the only fixed product role

### Configurable Rules

Admin must be able to configure:

- role names
- role descriptions
- module access
- page access
- feature access
- action permissions
- visibility scope
- user-role assignment
- explicit audit permissions

### Visibility Scope Types

- `own`
- `team`
- `location`
- `global`

### Access Verbs

- `full`
- `manage`
- `work`
- `view`
- `none`

## Operational Workflow

The intended operational workflow is:

1. Admin sets up locations.
2. Admin creates users.
3. Admin creates roles.
4. Admin assigns modules, features, pages, actions, and scope.
5. Client records are created and tied to one operating location.
6. Requisitions are created with a clear primary owner and optional delivery owner.
7. Work is allocated with one main owner and optional contributors.
8. Candidates are created globally, checked for duplicates, and linked to requisitions.
9. If duplicates are detected, users compare first and only allowed senior roles can approve final override decisions.
10. Pipeline stages are applied through controlled templates tied to client or requisition needs.
11. Daily updates are submitted as one main daily summary with optional extra updates.
12. Dashboards stay live, while weekly and monthly reports can be locked.

## Risks

### Risk 1. Over-Configuration Complexity

If Admin configuration becomes too complex, onboarding may become slow.

Mitigation:

- keep module and feature structure simple
- provide basic role templates in MVP

### Risk 2. Permission Misconfiguration

If Admin incorrectly configures roles, users may get too much or too little access.

Mitigation:

- use clear access verbs
- separate module, action, and scope access clearly in MVP
- provide permission review screen

### Risk 3. Scope Leakage

If location filtering is weak, data may leak across locations.

Mitigation:

- make location scope a core backend rule
- do not trust frontend-only filtering

### Risk 4. Workflow Ambiguity

If ownership fields are unclear, teams may dispute responsibilities.

Mitigation:

- keep explicit ownership fields on requisitions and candidates
- preserve source owner separately from current owner
- support optional delivery-owner separation

### Risk 5. Duplicate Candidate Pollution

If duplicate control is weak, the company will end up with repeated candidate records, bad reporting, and poor recruiter trust.

Mitigation:

- use duplicate checks on email, phone, name, and resume similarity
- require compare-first behavior before override
- allow final override only to Admin or explicitly permitted senior roles

### Risk 6. Uncontrolled Pipeline Variation

If every user can freely invent stages, reporting and workflow consistency will break.

Mitigation:

- use master stage libraries
- use Admin-managed pipeline templates
- apply templates to client or requisition workflows instead of free-form stage creation

### Risk 7. Sensitive Audit Exposure

If audit data is too open, sensitive operational and permission history may leak.

Mitigation:

- require explicit audit permission
- enforce scope even for audit viewing
- log audit-log access itself

Mitigation:

- keep record ownership explicit
- store ownership on requisitions and candidates

## Benefits Of This Approach

- supports more companies without rebuilding the product
- lowers long-term customization cost
- makes the system more scalable
- reduces hierarchy lock-in
- keeps Admin in control of system structure
- keeps product engineering focused on modules and workflows
- improves duplicate prevention across the company
- supports both live operations and formal period reporting

## Recommended MVP Priorities

1. Authentication and access
2. Role and permission configuration
3. Location and user administration
4. Client registry
5. Requisition management
6. Work allocation
7. Candidate management
8. Pipeline tracking
9. Daily updates
10. Dashboards and reports

## Success Criteria

The product should be considered successful for MVP if:

- Admin can create custom roles
- Admin can configure modules and features without code changes
- Admin can assign role-based page and action access
- companies with different hierarchies can use the same system
- core recruitment workflows operate successfully
- location-safe reporting works correctly
- duplicate candidate handling stays controlled and reviewable
- weekly and monthly reports can be locked when needed

## Related Documents

- `docs/system/WORKING_MODEL.md`
- `docs/system/WORKING_MODEL_FEATURES_AND_ROLE_LIFECYCLE.md`
- `docs/system/WORKING_MODEL_ROLE_PAGE_ACTION_MATRIX.md`
- `docs/system/UNIVERSAL_PRODUCT_ARCHITECTURE.md`
