# MVP Use Case Overview

## Purpose

This document gives a simple business-facing view of the MVP use cases.

It should be used when the team wants to understand:

- what the product actually lets users do
- which actor usually performs each action
- which module owns the action
- which page supports the action
- which use cases are core for the first working MVP

Use this together with:

- `docs/system/MVP_USE_CASE_CATALOG.md`
- `docs/system/USE_CASES_AND_EXCEPTIONS_MASTER.md`
- `docs/system/MVP_USE_CASE_EXECUTION_MATRIX.md`
- `docs/system/MVP_USE_CASE_API_CONTRACTS.md`
- `docs/system/MVP_USE_CASE_DB_CONTRACTS.md`

## Why Use Cases Matter

Modules tell us what the product contains.

Use cases tell us how people actually use it.

Without use cases, the team may build:

- pages without business purpose
- APIs without a complete workflow
- database tables without lifecycle logic
- permissions without clear actor intent
- reports without operational meaning

That is why this product must be planned in this order:

1. business rule
2. use case
3. page or workflow
4. API contract
5. database contract
6. exception handling

## Product Rule For Actors

- `Admin` is the only fixed product role
- all other actors below are example operating actors
- each company may rename or split them differently
- the use cases remain stable even when titles change

Example:

- one company may use `BDM`
- another may use `Account Manager`
- another may use `Client Partner`

All of them may still perform the same use case:

- create client
- create requisition
- review progress

## MVP Core Actor Groups

- `Admin`
  Governance actor who configures locations, users, roles, access, and recovery actions.
- `Permitted Business User`
  Intake-side actor who usually handles clients, contacts, and requisitions.
- `Permitted Senior User`
  Control actor who usually assigns work, reviews team progress, and handles exceptions.
- `Recruiter Or Sourcing User`
  Execution actor who creates candidates, links them to requisitions, and updates the pipeline.
- `Permitted Reporting User`
  Read-focused actor who reviews dashboards and company or location performance.
- `Any Authenticated User`
  Any active user using the system within assigned access.

## MVP Use Case Summary

| Use Case | Business Goal | Primary Actor | Main Module | Main Page |
| --- | --- | --- | --- | --- |
| `UC-01 Login` | Enter the platform with the correct access context | `Any Authenticated User` | Authentication | `Login` |
| `UC-02 View Access Context` | Understand allowed modules and actions | `Any Authenticated User` | Access Control | `Role Dashboard` |
| `UC-03 Create Location` | Create an operating location | `Admin` | Location Administration | `Location Management` |
| `UC-04 Create Custom Role` | Define a configurable working role | `Admin` | Roles And Permissions | `Role Management` |
| `UC-05 Create User` | Onboard a user with valid access and location | `Admin` | User Administration | `User Management` |
| `UC-06 Create Client` | Register a client under one location | `Permitted Business User` | Client Directory | `Client Directory` |
| `UC-07 Add Client Contact` | Maintain requisition-ready client contacts | `Permitted Business User` | Client Directory | `Client Detail` |
| `UC-08 Create Requisition` | Capture a hiring requirement | `Permitted Business User` | Requisition Management | `Requisition Intake` |
| `UC-09 View Requisition Backlog` | Track and prioritize open demand | `Permitted Business User` | Requisition Management | `Requisition List` |
| `UC-10 Assign Delivery Ownership` | Assign a requisition to the working team | `Permitted Senior User` | Work Allocation | `Requisition Detail` |
| `UC-11 Review Work Queue` | See pending delivery work | `Permitted Senior User` | Work Allocation | `Delivery Work Queue` |
| `UC-12 Create Candidate` | Create a reusable candidate record | `Recruiter Or Sourcing User` | Candidate Management | `Candidate Profiles` |
| `UC-13 Upload Resume` | Add candidate data from documents | `Recruiter Or Sourcing User` | Candidate Management | `Resume Upload And Review` |
| `UC-14 Detect Duplicate Candidate` | Prevent accidental duplicate records | `Recruiter Or Sourcing User` | Candidate Governance | `Candidate Profiles` |
| `UC-15 Resolve Duplicate` | Compare duplicate candidates and decide safely | `Admin` or selected senior role | Candidate Governance | `Candidate Duplicate Review` |
| `UC-16 Link Candidate To Requisition` | Turn a candidate into an active application | `Recruiter Or Sourcing User` | Candidate And Pipeline | `Candidate Profiles` |
| `UC-17 Screen Candidate` | Validate fit before movement | `Recruiter Or Sourcing User` | Candidate Screening | `Candidate Screening` |
| `UC-18 View Pipeline` | Track active candidate progress | `Recruiter Or Sourcing User` plus senior visibility | Pipeline Tracking | `Pipeline Board` |
| `UC-19 Move Pipeline Stage` | Progress a candidate through the workflow | `Recruiter Or Sourcing User` or permitted senior | Pipeline Tracking | `Pipeline Board` |
| `UC-20 Track Recruiter-Owned Progress` | Let recruiters see progress on sourced candidates | `Recruiter Or Sourcing User` | Dashboard And Pipeline | `My Work Dashboard` |
| `UC-21 Submit Daily Update` | Record work progress and blockers | `Recruiter Or Sourcing User` | Daily Updates | `Daily Updates Submission` |
| `UC-22 Review Daily Updates` | Review team execution | `Permitted Senior User` | Daily Updates | `Daily Updates Review` |
| `UC-23 Review Notifications` | Respond to alerts and reminders | `Any Authenticated User` | Notifications | `Notifications Center` |
| `UC-24 View Location Reporting` | Review location-level performance | `Permitted Reporting User` | Reporting | `Location Dashboard` |
| `UC-25 View Company Reporting` | Review combined company performance | `Admin` or permitted reporting role | Reporting | `Company Dashboard` |
| `UC-26 Handle Access Denial` | Block unauthorized access clearly | `Any Authenticated User` | Access Control | `Access Denied` |

## End-To-End MVP Journey

The MVP becomes truly usable only when this full chain works:

1. `Admin` creates location, role, and user.
2. `Permitted Business User` creates client and contact.
3. `Permitted Business User` creates requisition.
4. `Permitted Senior User` assigns delivery ownership.
5. `Recruiter Or Sourcing User` creates candidate.
6. `Recruiter Or Sourcing User` uploads resume and reviews the profile.
7. System checks duplicates globally.
8. Authorized user resolves duplicate if required.
9. `Recruiter Or Sourcing User` links candidate to requisition.
10. `Recruiter Or Sourcing User` moves the candidate through pipeline stages.
11. `Recruiter Or Sourcing User` submits daily updates.
12. Senior or reporting users review location or company performance.

If any part of this chain is missing page support, API support, database support, permission support, or exception handling, the MVP is not fully ready.

## Use Cases By Business Stage

### Stage 1. Access And Setup

- `UC-01 Login`
- `UC-02 View Access Context`
- `UC-03 Create Location`
- `UC-04 Create Custom Role`
- `UC-05 Create User`

### Stage 2. Intake And Demand Creation

- `UC-06 Create Client`
- `UC-07 Add Client Contact`
- `UC-08 Create Requisition`
- `UC-09 View Requisition Backlog`

### Stage 3. Delivery Setup

- `UC-10 Assign Delivery Ownership`
- `UC-11 Review Work Queue`

### Stage 4. Candidate Creation And Quality Control

- `UC-12 Create Candidate`
- `UC-13 Upload Resume`
- `UC-14 Detect Duplicate Candidate`
- `UC-15 Resolve Duplicate`
- `UC-16 Link Candidate To Requisition`
- `UC-17 Screen Candidate`

### Stage 5. Live Pipeline Execution

- `UC-18 View Pipeline`
- `UC-19 Move Pipeline Stage`
- `UC-20 Track Recruiter-Owned Progress`

### Stage 6. Execution Monitoring And Governance

- `UC-21 Submit Daily Update`
- `UC-22 Review Daily Updates`
- `UC-23 Review Notifications`
- `UC-24 View Location Reporting`
- `UC-25 View Company Reporting`
- `UC-26 Handle Access Denial`

## MVP Priority View

### Must Work In First End-To-End Build

- login and access loading
- location, role, and user setup
- client and contact creation
- requisition creation and assignment
- candidate creation
- duplicate detection and controlled resolution
- candidate-to-requisition linking
- pipeline viewing and movement
- daily updates
- location and company reporting

### Can Be Deeper Later Without Blocking The MVP

- advanced approval chains
- richer workload balancing
- automation-heavy reminders
- highly detailed audit analytics
- complex client-specific workflow design tools

## Planning Rule Going Forward

For every new module or feature, we should now ask five questions:

1. Which use case does this support?
2. Who is the primary actor?
3. Which page or workflow handles it?
4. Which API and DB contracts are required?
5. Which exception path must be handled before we call it complete?

If a feature cannot answer those five questions clearly, it is not ready for build.
