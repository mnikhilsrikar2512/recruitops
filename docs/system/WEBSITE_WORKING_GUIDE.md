# Recruitment System Website Working Guide

This document explains in detail how the recruitment system website works as a product, how users move through it, and how each role uses it in daily operations.

It is intended to act as the most readable system walkthrough for:

- product planning
- backend implementation
- frontend integration
- onboarding new teammates
- explaining the system to stakeholders

## 1. What This Website Is

This website is a recruitment operating platform.

It is not only a candidate database and it is not only a hiring tracker.

It is designed to run the full operational flow around:

- people who configure and govern the system
- people who bring client or hiring demand into the system
- people who deliver recruitment work
- people who review or approve selected steps
- the system itself, which turns structured activity into reports, dashboards, and operational visibility

## 2. What Problem The Website Solves

Most recruitment teams struggle with the same problems:

- hiring work is scattered across spreadsheets, chats, and email
- ownership is unclear
- recruiters work without a structured priority system
- client follow-ups get delayed
- candidate information is inconsistent
- reporting is manual and unreliable
- leaders can see outcomes but not the real bottlenecks

This website solves that by putting the work into one structured system where:

- each record has an owner
- each user sees only relevant pages and actions
- demand is captured in structured form
- candidate movement is visible
- follow-ups are tracked
- reports are generated from real operational activity

## 3. Who The Website Is For

The website is designed to be usable by many types of companies, including:

- staffing and recruitment agencies
- in-house talent acquisition teams
- RPO and delivery partners
- executive search firms
- multi-location recruiting companies

Because of that, the system does not hard-code one real-world company hierarchy.

Instead, it uses:

- permission roles
- configurable business titles
- configurable reporting relationships
- location and team assignment
- visibility scopes
- workflow ownership

## 4. Core Product Idea

The website works by separating these five things:

### 1. Permission role

This decides what a user can do in the system.

Examples:

- `platform_admin`
- `operations_admin`
- `business_lead`
- `client_manager`
- `delivery_lead`
- `recruiter`
- `sourcing_support`
- `reviewer`

### 2. Business title

This is the customer-facing label for the user.

Examples:

- Director
- BDM
- Account Manager
- Lead Recruiter
- Assistant Recruiter
- Recruiter
- Talent Partner
- Hiring Manager

### 3. Scope

This decides what records a user can see.

Examples:

- global
- location
- team
- own records only

### 4. Ownership

This decides who is responsible for a record.

Examples:

- client owner
- delivery owner
- candidate owner
- reviewer
- assigned team

### 5. Workflow role

This decides who is involved in a specific process step.

Examples:

- approver for a requisition
- reviewer for a candidate
- account owner for a client

## 5. Main Areas Of The Website

The website is organized into a few major working areas.

## A. Identity And Access

This area controls:

- login
- logout
- password setup
- password reset
- session control
- page access

This is the first thing every user interacts with.

## B. Organization Setup

This area defines:

- company profile
- locations
- teams
- business units later
- reporting relationships
- role and title assignment

This area is mostly used by administrative roles.

## C. CRM And Client Work

This area supports:

- prospects
- clients
- contacts
- meetings
- follow-ups
- mandate conversion

This is the business-side operating area.

## D. Requisition And Delivery Work

This area supports:

- requisition intake
- structured JD capture
- assignment of ownership
- candidate sourcing
- screening
- pipeline movement
- interviews
- offers
- joins

This is the delivery-side operating area.

## E. Reporting And Governance

This area supports:

- dashboards
- productivity reports
- location performance
- approval workflows later
- audit and exceptions

This is the visibility and control area.

## 6. How A User Experiences The Website

When a user opens the website, the experience should work in this order:

1. user reaches login page
2. user signs in
3. system identifies permission role, business title, location, team, and scope
4. system routes the user to the correct landing page
5. navigation shows only the pages that role should use
6. lists, dashboards, and actions are filtered to the user’s allowed scope
7. the user performs their role-specific workflow
8. their actions update records, ownership, status, and later reporting outputs

## 7. How Navigation Works

Navigation should be role-aware and scope-aware.

That means:

- users should not see pages outside their normal workflow
- direct page access should still be checked by the backend
- if a user somehow opens a forbidden route, they should get `Access Denied`
- shared pages may render slightly differently for different roles

Examples:

- a recruiter should not see admin audit pages
- a client manager should not see deep candidate screening pages unless explicitly allowed
- a platform admin may have visibility into all modules but should still land on an executive view

## 8. The Main Operating Flow Of The Website

The website supports two major hiring flows:

## Flow 1. Internal Hiring

This is for hiring inside the company itself.

1. hiring need is created
2. requisition is entered with structured details
3. delivery owner is assigned
4. sourcing begins
5. candidates are created and screened
6. stages progress through interviews and offers
7. final join outcome is tracked
8. dashboards and reports update automatically from the work

## Flow 2. External Client Hiring

This is for hiring on behalf of clients.

1. a client conversation or meeting is logged
2. client need is captured
3. an external requisition is created
4. a delivery owner is assigned
5. recruiters and sourcers work the role
6. candidates are screened and progressed
7. submissions, interviews, offers, and placements are tracked
8. account-level and delivery-level dashboards are updated

## 9. How Records Move Through The Website

The system revolves around a few important record types:

### Users

Users represent people who can log in.

Each user has:

- permission role
- business title
- location assignment
- team assignment
- reporting manager
- active or inactive status

### Clients

Clients represent external business accounts.

Each client can have:

- account owner
- multiple contacts
- direct client or end-client relationships
- activity history
- requisitions attached

### Requisitions

Requisitions represent hiring demand.

Each requisition has:

- hiring type
- owner
- delivery owner
- location and team context
- JD structure
- status
- due date
- SLA context
- candidate pipeline

### Candidates

Candidates represent profiles being worked in the system.

Each candidate can have:

- source
- owner
- linked requisitions
- document uploads
- duplicate-check history
- stage history
- rejection reason
- offer or join outcome

## 10. Website Behavior By Role

Below is the practical working behavior for each role in the system.

## Platform Admin

### What this role is for

This role governs the system itself.

### What this role mainly sees

- executive dashboard
- user administration
- location and team setup
- company setup
- settings
- audit and exception views

### What this role mainly does

- create and maintain users
- assign roles and titles
- assign locations and teams
- reset credentials
- manage access rules
- monitor executive performance and system health

### What this role normally should not do

- day-to-day candidate sourcing
- routine recruiting execution
- account-level client follow-up as a primary workflow

## Operations Admin

### What this role is for

This role supports setup and data hygiene without being the main business or delivery owner.

### What this role mainly sees

- org setup views
- selected user administration views
- location and team data
- portal-account setup later
- operational support views

### What this role mainly does

- support onboarding
- maintain location and team records
- correct assignment errors
- maintain setup quality

### What this role normally should not do

- strategic client ownership
- recruiting execution ownership
- executive governance decisions unless delegated

## Business Lead

### What this role is for

This role owns strategic business-side performance.

### What this role mainly sees

- business dashboard
- high-level client and account summaries
- performance and conversion trends
- strategic requisition inflow visibility

### What this role mainly does

- review account pipeline health
- monitor business conversion
- guide strategic client decisions
- escalate commercial issues

### What this role normally should not do

- detailed candidate execution
- regular admin setup work

## Client Manager

### What this role is for

This role owns client communication and converts external demand into requisitions.

### What this role mainly sees

- client list and client detail
- contact records
- meetings and follow-up pages
- account dashboard
- requisition intake pages

### What this role mainly does

- manage clients and contacts
- run meetings
- record outcomes and follow-ups
- create external requisitions
- hand work to delivery

### What this role normally should not do

- deep screening and stage control
- user administration
- system governance

## Delivery Lead

### What this role is for

This role owns recruiting execution quality and team allocation.

### What this role mainly sees

- delivery dashboard
- requisition list and detail
- candidate readiness views
- team workload views
- stage movement summaries

### What this role mainly does

- assign work to recruiters and sourcers
- review candidate quality
- monitor blockers
- manage aging requisitions
- monitor fulfillment

### What this role normally should not do

- tenant-wide access setup
- strategic commercial account ownership

## Recruiter

### What this role is for

This role owns candidate execution work.

### What this role mainly sees

- my work dashboard
- candidate list and detail
- stage movement pages
- resume upload flow
- recruiter reports

### What this role mainly does

- source candidates
- create and update candidate records
- upload resumes and documents
- run duplicate checks
- move candidates through workflow stages
- record progress updates

### What this role normally should not do

- location governance
- user management
- tenant settings
- executive audit review

## Sourcing Support

### What this role is for

This role improves recruiter throughput by preparing candidate drafts and sourcing support.

### What this role mainly sees

- candidate intake views
- resume upload views
- sourcing queues
- portal access references

### What this role mainly does

- search databases and portals
- prepare candidate draft records
- upload resumes
- enrich candidate information
- hand profiles to recruiter workflow

### What this role normally should not do

- final delivery ownership
- high-level client ownership
- system governance

## Reviewer

### What this role is for

This role only enters the workflow when review or feedback is required.

### What this role mainly sees

- assigned review inbox
- requisition review context
- candidate review context
- feedback forms

### What this role mainly does

- review assigned context
- provide feedback
- approve or reject when allowed

### What this role normally should not do

- broader delivery execution
- user administration
- client management

## External User

### What this role is for

This role is for controlled external collaboration later.

### What this role mainly sees

- shared review or feedback items only

### What this role mainly does

- provide limited feedback
- respond to shared items

### What this role normally should not do

- view internal records broadly
- access internal dashboards

## 11. What The Main Screens Do

The website can be understood through its key screen groups.

## Dashboard Screens

These show:

- priority work
- alerts
- summary metrics
- overdue items
- role-specific tasks

Dashboards are the first place users should land after login.

## Client And Account Screens

These support:

- client creation and maintenance
- contact management
- client relationship tracking
- meeting follow-up
- account visibility

## Requisition Screens

These support:

- creating requisitions
- capturing structured JD data
- assigning owners
- tracking requisition status
- connecting candidates to the role

## Candidate Screens

These support:

- creating candidate records
- viewing candidate details
- uploading resumes
- duplicate checking
- managing stages
- capturing rejections

## Screening And Pipeline Screens

These support:

- checking candidate fit
- moving candidates from stage to stage
- deciding rejection or escalation
- tracking interviews, offers, and joins

## Reporting Screens

These support:

- executive views
- location performance
- delivery performance
- recruiter productivity
- operational updates

## Settings And Governance Screens

These support:

- user access control
- location and company setup
- rules and configuration
- audit and exception views

## 12. How Ownership Works In The Website

Ownership is one of the most important ideas in the system.

The website should always know who owns a record.

### Common ownership types

- creator
- owner
- delivery owner
- client owner
- assigned team
- reviewer

### Why ownership matters

Ownership drives:

- which records appear in lists
- which items show in dashboards
- who gets follow-up responsibility
- who can update the record
- who is accountable for delays

## 13. How Scope Works In The Website

The website must not show every record to every user.

Scope decides how wide a user’s visibility is.

### Common scopes

- global
- location
- team
- own

### Examples

- a global admin can see all records
- a location-scoped user can see records from their location
- a team-scoped delivery lead can see team-owned requisitions and candidates
- an own-scoped recruiter can see records assigned directly to them

## 14. How Reporting Works In The Website

Reporting in this website should not depend on manual spreadsheet building.

Instead, reports should be generated from:

- meeting records
- requisition records
- candidate records
- stage changes
- updates entered by users
- ownership fields
- due dates and SLA values

### The website should support reporting for:

- executive visibility
- account visibility
- delivery visibility
- recruiter productivity
- stage conversion
- aging and bottlenecks

## 15. How The Website Should Feel To The User

The user experience should feel:

- role-aware
- calm
- structured
- operational
- fast to scan
- hard to misuse

That means:

- users should not be overloaded with pages they do not need
- key actions should be obvious
- status and ownership should be visible
- forms should collect structured information without unnecessary friction
- the system should help users decide what to do next

## 16. What The MVP Version Of The Website Must Do

The MVP does not need every advanced feature.

The MVP must get the core operating system right.

### MVP essentials

- login and session handling
- role and title assignment
- location and team setup
- user creation and management
- client and contact management
- requisition creation and assignment
- candidate creation and updates
- duplicate checks
- candidate stage movement
- delivery and role-specific dashboards

### Not required for MVP

- full approvals engine
- full audit center
- advanced automation
- external client portal
- AI-heavy flows
- full forecasting

## 17. What Happens After MVP

After the MVP operating loop is stable, the website can expand into:

- approvals and governance workflows
- persistent notifications
- deep audit trails
- automation and AI assistance
- integrations with email, calendar, and sourcing tools
- advanced reporting and forecasting

## 18. Final Summary

The website works as a recruitment operating system.

It brings together:

- system setup
- user access
- client and account work
- requisition intake
- candidate execution
- delivery visibility
- role-specific dashboards
- future governance and automation

The most important design rule is this:

the website must always be role-aware, scope-aware, and ownership-aware.

That is what makes it usable by different companies while still remaining structured, clear, and operationally powerful.
