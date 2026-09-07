# MVP Freeze Document

Date locked:

- Tuesday, August 18, 2026

## Purpose

This document freezes the first buildable MVP scope for the recruitment system.

It defines:

- what must be built now
- what is explicitly deferred
- what is configurable
- what counts as MVP-complete

This document is the delivery boundary for the first end-to-end product build.

## Product Position

The MVP is a configurable recruitment operating system for:

- recruitment agencies
- staffing and RPO firms
- internal hiring teams
- mixed-model recruiting companies

The MVP must support:

- location-safe operations
- configurable non-admin roles
- client and requisition operations
- candidate pipeline tracking
- daily execution updates
- basic operational dashboards

## Fixed Product Rules

- `Admin` is the only fixed system role
- all other operational roles are created by Admin
- operational data is location-bound by default
- candidate records are global for duplicate detection, but access remains permission-controlled
- client ownership is location-bound in MVP
- one requisition has one primary owner
- one requisition may optionally have one delivery owner

## MVP In Scope

### 1. Authentication And Access

- login
- logout
- current session
- current permission payload
- password hashing
- active role loading
- location-safe access enforcement
- action-level permission checks

### 2. Admin Setup

- location creation and activation
- user creation and activation
- role creation
- role update
- module assignment to role
- action assignment to role
- scope assignment to role
- primary role assignment to user

### 3. Client Management

- client create
- client edit
- client list
- client detail
- client contacts
- one client mapped to one location

### 4. Requisition Management

- requisition create
- requisition edit
- requisition list
- requisition detail
- direct client linkage
- optional end-client linkage
- primary owner assignment
- optional delivery owner assignment
- support-user assignment
- status tracking
- configurable pipeline stages by client or company rules

### 5. Candidate Management

- candidate create
- candidate edit
- candidate list
- candidate detail
- resume upload
- source tracking
- social profile capture
- candidate-to-requisition linkage
- global duplicate detection using configured inputs
- duplicate review flow
- override request flow for selected senior roles

### 6. Pipeline Execution

- stage movement
- stage history
- recruiter visibility into sourced candidates
- primary owner visibility into requisition pipeline
- delivery owner visibility into assigned pipeline
- rejection capture
- joined capture
- configurable stage model by client requirement

### 7. Daily Updates

- daily updates submission
- requisition-linked updates
- blockers
- next actions
- activity counts
- review visibility for configured roles

### 8. Basic Dashboards

- role dashboard
- my work dashboard
- location-level dashboard
- requisition pipeline summary
- candidate pipeline summary
- daily update summary
- Admin combined reporting view

### 9. Core Audit And Notifications

- audit log for critical entity changes
- in-app notifications for workflow events
- duplicate review notifications
- reassignment review notifications
- update reminders

## MVP Explicitly Deferred

These items must not expand the first delivery slice unless separately approved.

### Deferred Workflow And Governance

- advanced approval engine
- visual workflow designer
- report lock lifecycle beyond simple unlock control
- true multi-role composition
- cross-location shared client operations

### Deferred Candidate Intelligence

- AI resume parsing
- parser-confidence workflows
- advanced duplicate intelligence beyond MVP rule set
- AI screening recommendations

### Deferred Reporting

- finalized weekly report engine
- finalized monthly report engine
- Excel exports
- PDF exports
- advanced productivity scoring
- forecasting and target prediction

### Deferred Platform Features

- external client portal
- billing and invoicing
- enterprise SSO
- MFA
- advanced automation engine
- full SLA rules engine

## MVP Role Model

### Fixed

- `Admin`

### Configurable By Admin

Examples only:

- business development
- account manager
- lead recruiter
- recruiter
- assistant recruiter
- reviewer

These are customer-defined, not product-defined.

## MVP Data Boundary

The following operational entities must be complete enough for live use:

- locations
- users
- roles
- role permissions
- clients
- client contacts
- requisitions
- requisition assignments
- candidates
- candidate applications or pipeline links
- candidate stage history
- daily updates
- notifications
- audit logs

## MVP Readiness Criteria

The MVP is build-complete only when all of the following are true:

### Functional Readiness

- Admin can create locations, users, roles, and access rules
- a permitted user can create a client
- a permitted user can create a requisition
- a permitted user can assign requisition ownership
- a permitted user can create a candidate
- duplicate review works before final save
- a permitted user can move candidate stages
- a permitted user can submit daily updates
- dashboards reflect live operational data

### Data Readiness

- all required operational records persist correctly
- audit records are captured for critical changes
- duplicate review decisions are stored
- stage history is stored

### Security Readiness

- unauthorized routes are blocked server-side
- location data isolation works by default
- global visibility requires explicit permission

### Usability Readiness

- all MVP pages use stable API-backed data
- no core workflow depends on spreadsheet fallback
- role dashboard and my work dashboard show actionable items

## Build Stop Rule

If a requested feature is not listed in this document as MVP in-scope, it must be treated as:

- deferred
- optional
- future-phase only

unless the MVP freeze is formally updated.
