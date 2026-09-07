# Recruitment System Modules And Features

This document is the detailed product-facing module and feature inventory for the recruitment platform.

It is aligned to the universal architecture introduced on August 13, 2026 and should be used as the feature reference for planning, backend implementation, API design, and future frontend work.

## Product Direction

The product must be usable by multiple kinds of recruiting organizations, including:

- staffing and recruitment agencies
- in-house talent acquisition teams
- RPO and delivery partners
- executive search firms
- multi-location recruiting businesses

The product must therefore be built around:

- permission roles
- business titles
- reporting relationships
- visibility scopes
- workflow ownership

It must not assume one hard-coded customer hierarchy.

## Design Principles

- configurable business hierarchy with stable permission logic
- structured data capture over free-text dependence
- role-safe and scope-safe visibility across UI and API
- operational workflows first, analytics and automation second
- both sales-side and delivery-side recruiting support
- clear ownership for every important record
- low-friction data entry for recruiters and coordinators
- better governance for leads, managers, and administrators
- auditability for sensitive actions
- extensibility for different customer operating models

## Universal Role Model

The system should support these core permission-role templates:

- `platform_admin`
- `operations_admin`
- `business_lead`
- `client_manager`
- `delivery_lead`
- `recruiter`
- `sourcing_support`
- `reviewer`
- `external_user`

The system should also support configurable business titles such as:

- Director
- BDM
- Account Manager
- Lead Recruiter
- Delivery Manager
- Recruiter
- Assistant Recruiter
- Resourcer
- Talent Acquisition Manager
- Talent Partner
- Hiring Manager
- Interview Coordinator

## Feature Classification

For execution clarity, features in this document fall into three buckets:

- MVP
  features that belong in the first working backend release
- Phase 2
  features that should come after the core operating loop is stable
- Later
  features that are valuable but should not block the first release

## Module 1: Identity, Authentication, And Session Control

### Purpose

Provide secure access to the platform and establish the authenticated operating context for every user.

### Core Features

- login using email and password
- logout and session invalidation
- password reset flow
- first-login password setup flow
- credential reset by admin
- force password change on first login
- session expiry and refresh handling
- device and session tracking
- failed login protection
- authentication audit trail

### MVP

- login
- logout
- password reset
- first-login setup
- session handling

### Phase 2

- multi-session management view
- suspicious login detection
- login alert notifications

### Later

- SSO
- MFA
- enterprise identity provider integration

## Module 2: Permission Roles, Business Titles, And Access Control

### Purpose

Separate product access logic from customer-specific job titles and org charts.

### Core Features

- permission-role templates
- custom business titles
- role-to-permission mapping
- feature-level permission flags
- action-level authorization
- role-safe route access
- route and API denial handling
- admin access review tools
- permission inheritance rules where needed

### Detailed Features

- create, update, activate, and deactivate business titles
- assign default permission role to each user
- allow customers to rename titles without changing system behavior
- show product role and customer title together in user records
- support read-only reviewer-style roles
- support scoped admins without full tenant-wide access

### MVP

- permission-role templates
- business title creation and assignment
- permission checks in backend and frontend

### Phase 2

- custom permission bundles
- tenant-specific role cloning

### Later

- fully dynamic permission builder UI

## Module 3: Organization Structure, Locations, Teams, And Reporting Lines

### Purpose

Model the customer’s internal structure without forcing a single hierarchy pattern.

### Core Features

- company profile
- locations and offices
- business units
- departments
- teams
- reporting manager relationships
- team lead relationships
- location ownership
- cross-team assignments

### Detailed Features

- create and manage locations
- assign location-level administrators or coordinators
- create delivery teams under locations
- create business-development or account teams
- map users to locations and teams
- mark primary vs secondary location assignment
- mark primary vs secondary team membership
- capture reporting manager for each user
- support agency, in-house, and RPO starter templates

### MVP

- locations
- teams
- reporting manager
- primary location and team assignment

### Phase 2

- business units
- cross-team assignments
- reporting-line visualization

### Later

- historical org structure changes
- matrix reporting rules

## Module 4: User Administration And Workforce Management

### Purpose

Manage user lifecycle, onboarding, status, and responsibility mapping.

### Core Features

- create user
- invite user
- activate and deactivate user
- assign permission role
- assign business title
- assign reporting manager
- assign locations and teams
- reset credentials
- status and access review

### Detailed Features

- direct user creation with immediate credentials
- setup-link onboarding
- temporary password onboarding
- employee code support
- user directory filters by location, team, title, and status
- user performance summary entry point
- user ownership summary
- recruiter capacity summary
- delivery lead team roster

### MVP

- create, update, deactivate users
- invite flow
- location and team assignment
- reporting manager assignment

### Phase 2

- user workload summary
- capacity planning indicators
- user access review workflows

### Later

- approval for sensitive user changes
- historical access timeline

## Module 5: Visibility Scopes And Record Ownership

### Purpose

Make access control practical by combining role permissions with ownership and scope rules.

### Core Features

- scope assignment
- record ownership
- team-based visibility
- location-based visibility
- own-record visibility
- reviewer-only contextual visibility
- delegated access rules

### Detailed Features

- support `global`, `location`, `team`, and `own` scope types in MVP
- attach ownership fields to clients, requisitions, candidates, meetings, and tasks
- support delivery owner for execution-side records
- support client owner for account-side records
- show ownership in lists and detail pages
- enforce access on API queries and actions

### MVP

- location, team, and own scope enforcement
- owner-based filtering

### Phase 2

- delegated temporary access
- account-level scope

### Later

- exception-based record sharing rules

## Module 6: CRM, Accounts, Prospects, And Client Relationships

### Purpose

Support business development, active client management, and hiring-demand generation.

### Core Features

- prospect records
- client records
- account ownership
- client contacts
- account status
- relationship stage
- direct client and end-client structure
- mandate history

### Detailed Features

- create prospect or client record
- convert prospect to active client
- track relationship stage such as prospect, active, dormant, blocked
- manage multiple contacts per client
- capture industry and account notes
- track direct client vs end-client context
- track duplicate-profile complaints from clients
- track active mandates and closed mandates
- assign account owner and backup owner

### MVP

- client companies
- client contacts
- account owner
- direct and optional end-client mapping

### Phase 2

- prospect pipeline
- account health indicators
- client service notes timeline

### Later

- commercial agreements
- billing and invoice linkage

## Module 7: Meetings, Calls, Activities, And Follow-Ups

### Purpose

Track communication activity across sales-side and delivery-side workflows.

### Core Features

- meeting scheduling
- call logging
- note logging
- follow-up creation
- activity timeline
- attendance tracking
- outcome tracking
- next-step tracking

### Detailed Features

- create meeting with client, candidate, or internal stakeholder
- capture attendees and attendance outcome
- record meeting result such as accepted, follow-up needed, no-show, rejected
- assign follow-up owner
- set due dates and reminders
- capture meeting-to-requisition conversion
- record activity notes against clients and requisitions

### MVP

- meeting records
- outcome capture
- follow-up owner and due date

### Phase 2

- generalized activity timeline
- reminders and follow-up queues

### Later

- calendar integration
- email sync
- call logging integrations

## Module 8: Requisition Intake And Structured JD Design

### Purpose

Capture hiring demand in a way that is structured, reusable, and operationally clear.

### Core Features

- internal requisition intake
- external requisition intake
- structured JD fields
- skills and experience capture
- compensation capture
- SLA capture
- client round capture
- document expectation capture

### Detailed Features

- title, openings, location, experience range
- must-have skills
- good-to-have skills
- skill importance
- notice period expectations
- compensation and budget range
- mandatory documents such as payslips or relieving letters
- employment gap tolerance
- domain or industry preference
- target close date
- criticality and urgency
- recruiter-facing structured JD summary
- direct client and end-client association

### MVP

- structured requisition form
- structured JD JSON
- SLA and target close date
- client round required flag

### Phase 2

- reusable requisition templates
- intake approval hooks
- JD versioning

### Later

- AI JD normalization
- market benchmarking

## Module 9: Requisition Management And Work Allocation

### Purpose

Control the operational lifecycle of requisitions once they enter the system.

### Core Features

- requisition creation
- requisition ownership
- assignment to delivery team
- status tracking
- aging visibility
- open vs filled tracking
- allocation tracking

### Detailed Features

- assign delivery owner
- assign recruiter or sourcing support users
- move requisition between open, on-hold, paused, filled, cancelled
- track fulfillment against openings
- track location and team ownership
- track internal vs external hiring type
- show requisition summary cards and queue ordering
- expose requisition candidate list

### MVP

- create, list, update requisitions
- assign owner and delivery owner
- status tracking

### Phase 2

- requisition approval workflow
- allocation history
- requisition collaboration comments

### Later

- automated staffing suggestions
- commercial performance linkage

## Module 10: Candidate And Talent Records

### Purpose

Create and maintain the core candidate record as a long-lived recruiting asset.

### Core Features

- candidate profile creation
- resume upload
- candidate editing
- source tracking
- contact details
- ownership
- linked requisitions
- candidate notes
- candidate documents

### Detailed Features

- name, email, phone, location, experience
- source channel and source details
- current company and designation
- notice period
- compensation expectations
- skills and summary
- candidate owner
- linked requisitions and stage entries
- notes and attachments
- freshness tracking
- duplicate acknowledgement tracking

### MVP

- create and update candidate
- upload supporting documents
- link candidate to requisition
- track source and owner

### Phase 2

- reusable talent pool views
- archive and restore controls
- profile freshness alerts

### Later

- AI enrichment
- candidate persona tagging
- long-term talent relationship scoring

## Module 11: Resume Intake, Parsing, And Candidate Draft Preparation

### Purpose

Reduce candidate data-entry effort and improve candidate record quality at intake time.

### Core Features

- resume upload
- parse preview
- editable draft values
- missing-field prompts
- final save confirmation

### Detailed Features

- prefill name, email, phone, skills, experience, notice period
- allow recruiter or sourcer to edit parsed data before final save
- detect incomplete records before final confirmation
- show parse confidence or field-level reliability later

### MVP

- manual upload flow with editable candidate creation

### Phase 2

- structured parse preview
- parser confidence indicators

### Later

- multi-format parsing
- AI skill extraction and normalization

## Module 12: Duplicate Candidate Detection And Profile Governance

### Purpose

Prevent duplicate records and reduce client-side duplicate-profile issues.

### Core Features

- duplicate check on create
- duplicate review state
- merge or continue workflow
- duplicate acknowledgement history

### Detailed Features

- compare email and phone in MVP
- show duplicate warning before save
- allow reviewer decision on whether to continue or stop
- track when client reports duplicate ownership issues
- flag likely duplicate candidate applications across requisitions

### MVP

- duplicate check by email and phone
- warning and decision capture

### Phase 2

- resume-signal matching
- merge suggestions

### Later

- AI-assisted identity matching

## Module 13: Screening, Evaluation, And Qualification

### Purpose

Control candidate quality before the profile moves deeper into the workflow.

### Core Features

- screening checklist
- requirement match review
- qualification status
- mismatch capture
- rejection reason capture

### Detailed Features

- validate must-have skills
- validate experience fit
- validate notice period fit
- validate compensation fit
- validate document availability
- validate employment gap tolerance
- classify candidate as qualified, hold, reject, or escalate
- capture screening summary

### MVP

- structured screening decisions
- qualification and rejection fields

### Phase 2

- reusable screening templates
- weighted scorecards

### Later

- AI screening assist

## Module 14: Candidate Pipeline, Stage Movement, And Submission Flow

### Purpose

Track exactly where each candidate is in the recruiting workflow.

### Core Features

- candidate stage
- stage movement history
- submission readiness
- internal rejection
- client rejection
- hold and close states

### Detailed Features

- stages such as new, screening, shortlisted, submitted, interview, offered, hired, rejected, on-hold
- stage transition timestamps
- stage owner tracking
- client submission status
- stage comments
- rejection side classification
- lost, dropped, duplicate, hold, and withdrawn states

### MVP

- current stage
- stage history
- stage transition API
- rejection side and reason

### Phase 2

- pipeline board views
- submission approval hooks

### Later

- automated stage SLA alerts

## Module 15: Interview Scheduling, Feedback, And Decision Capture

### Purpose

Manage interview workflow in a structured and auditable way.

### Core Features

- interview scheduling
- round definition
- feedback submission
- outcome capture
- next-action capture

### Detailed Features

- define interview round type
- assign interviewer or reviewer
- capture scheduled time and status
- record completed, rescheduled, no-show, cancelled
- collect structured interview feedback
- decide pass, hold, reject, next round

### MVP

- can be represented through stage transitions and notes if needed

### Phase 2

- dedicated interview rounds
- interview feedback forms

### Later

- calendar sync
- panel feedback consolidation

## Module 16: Offer, Join, Closure, And Placement Tracking

### Purpose

Track final outcome and closure value of recruiting work.

### Core Features

- offer stage tracking
- joining stage tracking
- closure reason capture
- placement summary

### Detailed Features

- offer released date
- offer accepted or declined
- expected join date
- actual join date
- backout tracking
- closed-without-fill reason
- fill count against requisition

### MVP

- offer and join stage support through pipeline states

### Phase 2

- structured offer outcome fields
- placement summary reporting

### Later

- commercial placement value tracking

## Module 17: Delivery Operations And Team Work Management

### Purpose

Help delivery leads and recruiters manage workload, output, and blockers.

### Core Features

- my work queue
- team work queue
- assignment load visibility
- blocker tracking
- next action visibility
- delivery dashboard

### Detailed Features

- show requisitions assigned to me
- show candidate actions due today
- show overdue follow-ups
- show blocked requisitions
- show recruiter and sourcer load balance
- show team open roles and aging
- show candidate movement today and this week

### MVP

- my work dashboard
- delivery dashboard
- ownership-based queues

### Phase 2

- workload balancing suggestions
- recruiter capacity indicators

### Later

- predictive delivery risk scoring

## Module 18: Portal Accounts, Sourcing Tools, And Resource Usage

### Purpose

Track access to sourcing systems and shared recruiting resources.

### Core Features

- portal account registry
- ownership mapping
- shared vs personal accounts
- slot scheduling
- usage notes
- utilization tracking

### Detailed Features

- platform type such as LinkedIn or Naukri
- assign location or central ownership
- assign account manager
- support shared-account time slots
- note usage outcome
- view account availability
- track who used what and when

### MVP

- portal account profile
- ownership and status

### Phase 2

- slot scheduling
- portal utilization reporting

### Later

- direct portal integrations

## Module 19: Tasks, Reminders, And Follow-Through

### Purpose

Reduce dropped actions and make operational follow-up more reliable.

### Core Features

- task creation
- due dates
- assignees
- reminders
- completion status
- linked records

### Detailed Features

- attach task to client, requisition, or candidate
- assign task to recruiter, client manager, or delivery lead
- mark task priority
- show overdue tasks in dashboards
- support quick-complete or snooze in later phases

### MVP

- may be handled through follow-up fields and queues

### Phase 2

- dedicated task entity and list views

### Later

- recurring task automation

## Module 20: Notifications And Alerting

### Purpose

Inform users about meaningful changes without overwhelming them.

### Core Features

- in-app notifications
- event-triggered alerts
- read and unread state
- action links
- priority levels

### Detailed Features

- notify on assignment
- notify on overdue actions
- notify on candidate movement needing review
- notify on meeting follow-up due
- notify on credential or access changes
- notify on SLA-risk requisitions

### MVP

- lightweight dashboard-level reminders or basic notification events

### Phase 2

- persistent notifications
- notification preferences

### Later

- email and messaging integrations

## Module 21: Dashboards, Operational Reporting, And Productivity Analytics

### Purpose

Turn transaction data into usable decision support for each operating level.

### Core Features

- executive dashboard
- business dashboard
- delivery dashboard
- recruiter dashboard
- my-work dashboard
- location and team comparison

### Detailed Features

- open requisitions
- stage movement
- overdue actions
- close-rate
- recruiter productivity
- source effectiveness
- account conversion
- location output
- SLA-risk items
- aging and bottlenecks

### MVP

- my-work
- delivery
- business
- executive summary dashboards

### Phase 2

- filterable reports
- scheduled summaries
- deeper productivity breakdowns

### Later

- forecasting
- trend analysis

## Module 22: Approvals, Governance, And Exception Handling

### Purpose

Support customers that need structured review and control points.

### Core Features

- approval requests
- approval inbox
- send-back flow
- escalation flow
- exception queue
- governance notes

### Detailed Features

- requisition approval
- submission approval
- sensitive user-change approval
- exception logging for policy breaks
- structured decision comments

### MVP

- defer full approval engine

### Phase 2

- approval requests by module
- lightweight exception tracking

### Later

- configurable approval chains

## Module 23: Audit Trail, Compliance, And Sensitive Action History

### Purpose

Provide accountability for security-sensitive and business-sensitive actions.

### Core Features

- audit log
- record change trace
- access-change trace
- export and override logging
- admin action review

### Detailed Features

- login and password reset events
- user creation and deactivation events
- permission and scope changes
- stage overrides
- deletion or merge actions
- sensitive exports

### MVP

- basic auth and access event logging

### Phase 2

- module-level audit logs
- audit filtering and export

### Later

- compliance retention policies

## Module 24: Data Quality, Validation, And Operational Controls

### Purpose

Improve data consistency so analytics, reporting, and workflow decisions stay reliable.

### Core Features

- required field validation
- status transition validation
- duplicate prevention
- consistency checks
- incomplete-record warnings

### Detailed Features

- validate mandatory requisition fields before open status
- validate candidate identity fields before submission
- validate ownership presence on key records
- warn when records lack required next-step data
- prevent invalid stage transitions

### MVP

- server-side validation for core forms

### Phase 2

- data quality dashboards
- exception cleanup views

### Later

- auto-healing suggestions

## Module 25: Templates, Playbooks, And Standardization

### Purpose

Help customers run repeatable workflows with less variation.

### Core Features

- requisition templates
- screening templates
- update templates
- workflow playbooks
- location or team defaults

### MVP

- defer

### Phase 2

- basic templates for requisitions and screening

### Later

- customer-managed playbooks

## Module 26: Import, Export, And Data Portability

### Purpose

Support onboarding, migration, reporting, and controlled external sharing.

### Core Features

- CSV import
- CSV export
- filtered export
- template download
- error reporting for import failures

### MVP

- defer or keep minimal admin-only export

### Phase 2

- structured CSV import and export

### Later

- bulk migration tooling
- PDF and spreadsheet report generation

## Module 27: Integrations And External Connectivity

### Purpose

Connect the platform to external systems where needed.

### Core Features

- email integration
- calendar integration
- sourcing platform integration
- file storage integration
- HRIS or ATS interoperability

### MVP

- none required beyond local file handling assumptions

### Phase 2

- calendar and mail integration planning

### Later

- full integration marketplace

## Module 28: Automation And AI Assistance

### Purpose

Reduce repetitive work after the operational base is stable.

### Core Features

- resume parsing
- duplicate suggestions
- next-best-action suggestions
- report drafting
- smart reminders
- smart queue ordering
- data-quality suggestions

### MVP

- do not make AI a dependency for the first release

### Phase 2

- resume parsing
- basic smart reminders

### Later

- AI copilots
- predictive insights

## Cross-Module Reporting Dimensions

Every important operational report should be filterable, where relevant, by:

- date range
- location
- team
- business unit
- permission role
- business title
- owner
- client
- requisition status
- hiring type
- stage
- source

## Cross-Module Ownership Rules

Every important record should support clear ownership.

### Required Ownership Types

- creator
- owner
- delivery owner
- client owner
- assigned team
- reviewer where applicable

### Ownership Rules

- ownership must drive list visibility and dashboard grouping
- ownership must be available in APIs and database schema
- ownership changes must be auditable in later phases

## Core Data Capture Policy

The system should capture important information in structured fields wherever possible.

### Must Be Structured

- user access and assignments
- client status
- requisition details
- candidate stage
- rejection reasons
- follow-up dates
- owners and assignees
- due dates and SLA fields

### Can Remain Flexible

- free-text notes
- meeting summaries
- candidate comments
- account observations

## Execution Summary

The first working release should focus on the operational core:

- Identity, Authentication, And Session Control
- Permission Roles, Business Titles, And Access Control
- Organization Structure, Locations, Teams, And Reporting Lines
- User Administration And Workforce Management
- Visibility Scopes And Record Ownership
- CRM, Accounts, Prospects, And Client Relationships
- Requisition Intake And Structured JD Design
- Requisition Management And Work Allocation
- Candidate And Talent Records
- Duplicate Candidate Detection And Profile Governance
- Screening, Evaluation, And Qualification
- Candidate Pipeline, Stage Movement, And Submission Flow
- Delivery Operations And Team Work Management
- Dashboards, Operational Reporting, And Productivity Analytics

These modules create the first real operating system for recruiting work.

The remaining modules should expand governance, automation, integrations, and analytics after the backend core is stable.
