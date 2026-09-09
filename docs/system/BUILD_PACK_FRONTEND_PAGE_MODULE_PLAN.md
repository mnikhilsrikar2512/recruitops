# Frontend Page Module Plan

Date locked:

- Tuesday, August 18, 2026

## Purpose

This document defines the frontend page inventory for the MVP.

It is the source of truth for:

- what pages must be built
- how pages are grouped by module
- which pages are MVP
- which pages can wait

The goal is to build the frontend module by module without missing any required pages.

## Page Planning Rules

- page names must use the shared product vocabulary
- one business page may contain list, detail, form, and drawer states
- modal-only interactions should not become separate full pages unless the workflow needs it
- pages are listed in build order, not just alphabetical order
- every redirect, route change, or workflow jump must land in one of these three UI containers only:
  - dedicated page
  - named dialog
  - named side panel or drawer
- no hidden redirect should exist without being documented in this plan

## Shared Page Vocabulary

- `Login`
- `Role Dashboard`
- `My Work Dashboard`
- `Location Management`
- `User Management`
- `Role Management`
- `Client Directory`
- `Client Detail`
- `Requisition List`
- `Requisition Intake`
- `Requisition Detail`
- `Delivery Work Queue`
- `Candidate Profiles`
- `Candidate Screening`
- `Pipeline Board`
- `Daily Updates Submission`
- `Daily Updates Review`
- `Notifications Center`

## Navigation Coverage Rule

Before frontend build starts, every action that changes user context must be classified as one of:

- full-page navigation
- in-page dialog flow
- side panel or drawer flow

Examples:

- `Create Client`
  may open as a dedicated page or as a structured drawer, but the choice must be fixed in implementation
- `Edit Requisition`
  may open as a dedicated page or reuse `Requisition Intake`
- `Duplicate Review`
  must open as a dedicated page because it is a controlled workflow step
- `Pipeline History`
  may open as a drawer or side panel

If a page includes a button such as:

- view
- edit
- create
- assign
- continue
- review
- open details

then the destination must already exist in this document as:

- a page
- a dialog
- or a panel

## Navigation And Redirect Map

This section ensures that no redirect behavior is left undefined.

### Auth Flows

- `Login` submit success
  destination: `Role Dashboard`
  type: full-page navigation
- `Forgot Password`
  destination: `First Login Password Setup`
  type: full-page navigation
- access denied from protected route
  destination: `Access Denied`
  type: full-page navigation

### Dashboard Flows

- `Role Dashboard` open personal task view
  destination: `My Work Dashboard`
  type: full-page navigation
- `Role Dashboard` open urgent requisition
  destination: `Requisition Detail`
  type: full-page navigation
- `Role Dashboard` open pending duplicate review
  destination: `Candidate Duplicate Review`
  type: full-page navigation
- `Role Dashboard` open updates pending
  destination: `Daily Updates Review` or `Daily Updates Submission`
  type: full-page navigation

### Admin Setup Flows

- `Location Management` create location
  destination: in-page create form
  type: dialog or drawer flow
- `Location Management` edit location
  destination: in-page edit form
  type: drawer flow
- `User Management` create user
  destination: in-page create form
  type: drawer or dedicated page flow
- `User Management` edit user
  destination: in-page edit form
  type: drawer flow
- `Role Management` create role
  destination: in-page create form
  type: drawer or dedicated page flow
- `Role Management` edit role
  destination: in-page edit form
  type: drawer flow

### Client Flows

- `Client Directory` open client
  destination: `Client Detail`
  type: full-page navigation
- `Client Directory` create client
  destination: in-page form or dedicated create route
  type: drawer or full-page navigation
- `Client Detail` add contact
  destination: `Contact Form Dialog`
  type: dialog flow
- `Client Detail` edit contact
  destination: `Contact Form Dialog`
  type: dialog flow
- `Client Detail` open linked requisition
  destination: `Requisition Detail`
  type: full-page navigation

### Requisition Flows

- `Requisition List` create requisition
  destination: `Requisition Intake`
  type: full-page navigation
- `Requisition List` open requisition
  destination: `Requisition Detail`
  type: full-page navigation
- `Requisition Detail` edit requisition
  destination: `Requisition Intake`
  type: full-page navigation
- `Requisition Detail` reassign primary owner
  destination: `Reassign Owner Dialog`
  type: dialog flow
- `Requisition Detail` reassign delivery owner
  destination: `Reassign Owner Dialog`
  type: dialog flow
- `Requisition Detail` open pipeline
  destination: `Pipeline Board`
  type: full-page navigation
- `Delivery Work Queue` open requisition
  destination: `Requisition Detail`
  type: full-page navigation

### Candidate Flows

- `Candidate Profiles` create candidate
  destination: in-page candidate form or dedicated create state
  type: in-page flow
- `Candidate Profiles` upload resume
  destination: `Resume Upload And Review`
  type: full-page navigation
- `Candidate Profiles` open duplicate state
  destination: `Candidate Duplicate Review`
  type: full-page navigation
- `Resume Upload And Review` continue after upload
  destination: `Candidate Profiles`
  type: full-page navigation
- `Candidate Profiles` finalize candidate with duplicate issue
  destination: `Candidate Duplicate Review`
  type: full-page navigation

### Screening And Pipeline Flows

- `Candidate Screening` pass or fail action
  destination: `Stage Move Dialog` or pipeline update result state
  type: dialog flow
- `Pipeline Board` move candidate stage
  destination: `Stage Move Dialog`
  type: dialog flow
- `Pipeline Board` view stage history
  destination: `Pipeline History Drawer Or Panel`
  type: drawer flow
- `Pipeline Board` open candidate
  destination: `Candidate Profiles`
  type: full-page navigation

### Daily Update Flows

- `Daily Updates Submission` submit success
  destination: success state or `My Work Dashboard`
  type: in-page success state or full-page navigation
- `Daily Updates Review` open row detail
  destination: in-page detail panel
  type: panel flow

### Notification Flows

- `Notifications Center` open notification detail
  destination: `Notification Detail Panel`
  type: panel flow
- `Notification Detail Panel` open linked record
  destination: related page such as `Client Detail`, `Requisition Detail`, `Candidate Duplicate Review`, or `Daily Updates Review`
  type: full-page navigation

## MVP Frontend Modules

## Module 1. Authentication And Session

### Pages

#### 1. Login

Purpose:

- authenticate user
- load user context

Core sections:

- login form
- forgot password link
- session or access error messages

Dependencies:

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

MVP:

- yes

#### 2. First Login Password Setup

Purpose:

- allow invited or reset users to set first password

Core sections:

- new password
- confirm password
- password rule helper

Dependencies:

- auth reset or invite flow endpoint

MVP:

- yes

#### 3. Access Denied

Purpose:

- show user-friendly denial when route permission fails

Core sections:

- reason summary
- back to dashboard action

Dependencies:

- frontend route guard

MVP:

- yes

## Module 2. Shared User Workspace

### Pages

#### 4. Role Dashboard

Purpose:

- default landing page after login
- show role-scoped KPIs and alerts

Core sections:

- KPI cards
- due work summary
- stale requisition summary
- duplicate review summary
- daily updates reminder
- recent activity

Dependencies:

- `GET /api/v1/dashboards/role`

MVP:

- yes

#### 5. My Work Dashboard

Purpose:

- give each user a personal execution view

Core sections:

- my assigned requisitions
- my active candidates
- my interviews today
- my pending follow-ups
- my daily update status

Dependencies:

- `GET /api/v1/dashboards/my-work`

MVP:

- yes

#### 6. Notifications Center

Purpose:

- show workflow notifications and reminders

Core sections:

- unread list
- read list
- notification type filter
- mark read actions

Dependencies:

- `GET /api/v1/notifications`
- `PATCH /api/v1/notifications/{notification_id}/read`

MVP:

- yes

#### 7. My Profile

Purpose:

- show current user profile and operating context

Core sections:

- personal info
- primary role
- business title
- location
- reporting manager

Dependencies:

- `GET /api/v1/auth/me`

MVP:

- yes

## Module 3. Admin Setup

### Pages

#### 8. Location Management

Purpose:

- manage operational locations

Core sections:

- locations list
- create location form
- edit location drawer or page
- status control

Dependencies:

- `GET /api/v1/locations`
- `POST /api/v1/locations`
- `PATCH /api/v1/locations/{location_id}`

MVP:

- yes

#### 9. User Management

Purpose:

- manage users and operating assignments

Core sections:

- users list
- create user form
- edit user form
- activation controls
- credential reset controls

Dependencies:

- `GET /api/v1/users`
- `POST /api/v1/users`
- `PATCH /api/v1/users/{user_id}`
- `POST /api/v1/users/{user_id}/credentials/reset`

MVP:

- yes

#### 10. Role Management

Purpose:

- create and configure custom roles

Core sections:

- roles list
- create role form
- edit role form
- permission assignment
- scope assignment

Dependencies:

- `GET /api/v1/roles`
- `POST /api/v1/roles`
- `PATCH /api/v1/roles/{role_id}`
- `PUT /api/v1/roles/{role_id}/permissions`

MVP:

- yes

## Module 4. Client Management

### Pages

#### 11. Client Directory

Purpose:

- list and manage clients in permitted scope

Core sections:

- filter bar
- clients table
- quick status indicators
- create client action

Dependencies:

- `GET /api/v1/clients`
- `POST /api/v1/clients`

MVP:

- yes

#### 12. Client Detail

Purpose:

- show one client and its related operational context

Core sections:

- client summary
- contacts section
- linked requisitions
- ownership details
- notes and activity summary

Dependencies:

- `GET /api/v1/clients/{client_id}`
- `PATCH /api/v1/clients/{client_id}`
- `GET /api/v1/clients/{client_id}/contacts`
- `POST /api/v1/clients/{client_id}/contacts`

MVP:

- yes

## Module 5. Requisition Management

### Pages

#### 13. Requisition List

Purpose:

- list requisitions with operational filters

Core sections:

- filter bar
- requisition table
- status summary
- create requisition action

Dependencies:

- `GET /api/v1/requisitions`

MVP:

- yes

#### 14. Requisition Intake

Purpose:

- create or edit structured requisitions

Core sections:

- requisition basics
- client and owner assignment
- skill requirements
- screening rules
- stage template selection

Dependencies:

- `POST /api/v1/requisitions`
- `PATCH /api/v1/requisitions/{requisition_id}`

MVP:

- yes

#### 15. Requisition Detail

Purpose:

- monitor one requisition end to end

Core sections:

- requisition header
- ownership
- client details
- assignment list
- pipeline counters
- activity summary
- stage model

Dependencies:

- `GET /api/v1/requisitions/{requisition_id}`
- `PATCH /api/v1/requisitions/{requisition_id}/status`
- `POST /api/v1/requisitions/{requisition_id}/assignments`

MVP:

- yes

#### 16. Delivery Work Queue

Purpose:

- prioritize delivery-side requisition work

Core sections:

- urgency queue
- overdue flags
- due-date sorting
- action recommendations

Dependencies:

- requisitions list and dashboard summary APIs

MVP:

- yes

## Module 6. Candidate Management

### Pages

#### 17. Candidate Profiles

Purpose:

- list, create, review, and edit candidate profiles

Core sections:

- candidate list
- candidate form
- resume section
- source details
- requisition linkage
- duplicate state summary

Dependencies:

- `GET /api/v1/candidates`
- `POST /api/v1/candidates`
- `GET /api/v1/candidates/{candidate_id}`
- `PATCH /api/v1/candidates/{candidate_id}`

MVP:

- yes

#### 18. Candidate Duplicate Review

Purpose:

- review possible duplicates before final candidate save

Core sections:

- candidate draft summary
- matched records list
- compare values
- request override action
- discard draft action
- use existing candidate action

Dependencies:

- `GET /api/v1/candidates/{candidate_id}/duplicate-check`
- `POST /api/v1/candidates/{candidate_id}/duplicate-decision`

MVP:

- yes

#### 19. Resume Upload And Review

Purpose:

- upload candidate resume and complete initial review

Core sections:

- upload area
- file status
- extracted candidate summary if available later
- continue to candidate form action

Dependencies:

- `POST /api/v1/candidates/{candidate_id}/resume`

MVP:

- yes

## Module 7. Screening And Pipeline

### Pages

#### 20. Candidate Screening

Purpose:

- complete structured screening against requisition rules

Core sections:

- candidate summary
- requisition rule summary
- skill check
- gap check
- document check
- compensation and notice check
- pass or fail decision

Dependencies:

- candidate detail data
- requisition detail data
- pipeline stage update endpoint

MVP:

- yes

#### 21. Pipeline Board

Purpose:

- move candidates across stages for each requisition

Core sections:

- stage columns
- candidate cards
- board filters
- move-stage actions
- rejection and join actions

Dependencies:

- `GET /api/v1/pipeline/board`
- `POST /api/v1/pipeline/{application_id}/move-stage`
- `GET /api/v1/pipeline/{application_id}/history`

MVP:

- yes

#### 22. Pipeline History Drawer Or Panel

Purpose:

- show auditable stage movement history

Core sections:

- timeline
- stage changes
- notes
- actor and timestamps

Dependencies:

- `GET /api/v1/pipeline/{application_id}/history`

MVP:

- yes

## Module 8. Daily Updates

### Pages

#### 23. Daily Updates Submission

Purpose:

- submit structured daily execution updates

Core sections:

- date selector
- requisition selector
- counts input
- blockers
- next actions

Dependencies:

- `POST /api/v1/daily-updates`

MVP:

- yes

#### 24. Daily Updates Review

Purpose:

- review updates submitted by permitted users

Core sections:

- filters
- update list
- update detail panel
- reminder and follow-up context

Dependencies:

- `GET /api/v1/daily-updates`
- `GET /api/v1/daily-updates/{daily_update_id}`

MVP:

- yes

## Module 9. Shared Workflow Components

These may be implemented as reusable drawers or modals instead of full routes.

### Shared Components

#### 25. Reassign Owner Dialog

Purpose:

- reassign primary or delivery ownership with controlled confirmation

MVP:

- yes

#### 26. Stage Move Dialog

Purpose:

- collect required fields during stage transitions

MVP:

- yes

#### 27. Contact Form Dialog

Purpose:

- add or edit client contacts from client pages

MVP:

- yes

#### 28. Notification Detail Panel

Purpose:

- show linked record and action context from a notification

MVP:

- yes

## Route And Container Decision Checklist

For every MVP page or workflow action, implementation must confirm:

- route path exists if it is a full-page flow
- dialog name exists if it is a popup flow
- panel or drawer name exists if it is a side-flow
- no button is left without a defined destination

## Deferred Frontend Pages

These should not block MVP build.

### Deferred Pages

- report export center
- advanced approvals inbox
- audit center explorer
- automation jobs monitor
- weekly report builder
- monthly report builder
- external client portal
- advanced access review center

## Recommended Frontend Build Order

### Wave 1

- Login
- Access Denied
- Role Dashboard
- My Work Dashboard

### Wave 2

- Location Management
- User Management
- Role Management

### Wave 3

- Client Directory
- Client Detail

### Wave 4

- Requisition List
- Requisition Intake
- Requisition Detail
- Delivery Work Queue

### Wave 5

- Candidate Profiles
- Resume Upload And Review
- Candidate Duplicate Review

### Wave 6

- Candidate Screening
- Pipeline Board
- Pipeline History Drawer Or Panel

### Wave 7

- Daily Updates Submission
- Daily Updates Review
- Notifications Center

## MVP Page Count

### Full Pages

- 24

### Shared Dialogs And Panels

- 4

### Total Planned MVP Frontend Units

- 28

## Build Completion Rule

The frontend module plan is complete only when every MVP page listed here has:

- route or page container decision
- API dependency mapping
- permission requirement
- empty state
- loading state
- validation state
- error state
