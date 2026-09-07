# Working Model Plan

## Purpose

This document defines the first usable working model for the recruitment system.

This working model is now based on one important rule:

- the product will not ship with fixed operational roles except `Admin`
- `Admin` is the only default system role
- `Admin` can create, configure, and assign all other roles
- `Admin` can decide which modules, features, pages, and actions belong to each role

The product planning should therefore focus first on:

- features
- modules
- workflows
- ownership logic
- access configuration capability

It should not depend on hard-coded business roles such as `BDM`, `Account Manager`, `Lead Recruiter`, or `Recruiter`.

## Product Position

The product must be usable by different recruitment companies with different internal structures.

That means:

- one company may use `BDM`, `Account Manager`, `Lead Recruiter`, and `Recruiter`
- another may use `Sales Head`, `Client Partner`, `Delivery Manager`, and `Talent Specialist`
- another may use a completely different structure

The system must support them without rewriting product logic.

## Core Working Model Rule

The product should have:

### 1. One Fixed Governance Role

- `Admin`

Admin is responsible for:

- company setup
- location setup
- user creation
- role creation
- module assignment
- feature assignment
- page access assignment
- action permission assignment
- visibility scope setup

### 2. Configurable Business Roles

All non-admin operational roles should be created by Admin.

Examples only:

- business development
- account manager
- delivery lead
- recruiter
- sourcing support
- reviewer

These are examples, not mandatory product roles.

### 3. Configurable Access Model

Admin should be able to define for every created role:

- which modules are visible
- which pages are visible
- which actions are allowed
- which records are visible
- whether access is `own`, `team`, `location`, or `global`

## Working Model Modules

The first release should focus on stable modules and features, not fixed role names.

## Module 1. Authentication And Access

Purpose:

- secure login
- establish user identity
- apply role-based and scope-based access

Features:

- login
- logout
- current user session
- password setup
- password reset
- role-based access control
- location-based access control
- action-level access control

## Module 2. Admin Configuration

Purpose:

- allow Admin to define the working structure of the system

Features:

- role creation
- role editing
- module assignment to role
- feature assignment to role
- page assignment to role
- action permission assignment to role
- visibility scope assignment
- user-to-role assignment

## Module 3. Location And User Setup

Purpose:

- allow Admin to create the operating structure

Features:

- location creation
- location status control
- user creation
- user activation and deactivation
- reporting-manager assignment
- primary location assignment

## Module 4. Client Directory

Purpose:

- store client data for recruitment operations

Features:

- client company create, edit, list, and detail
- client contact create, edit, list, and detail
- client status tracking
- client-to-location mapping

## Module 5. Requisition Management

Purpose:

- capture and track hiring requirements

Features:

- requisition create, edit, list, and detail
- client contact linkage
- job title, openings, priority, due date, and JD capture
- requisition ownership fields
- requisition status tracking
- requisition-wise pipeline counters

## Module 6. Team Assignment And Work Allocation

Purpose:

- allocate requisitions and operational work

Features:

- assign work owner
- assign support users
- reassign work
- view assignment list
- change assignment status
- workload visibility

## Module 7. Candidate And Profile Management

Purpose:

- manage candidate records used in recruitment

Features:

- candidate create, edit, list, and detail
- resume upload
- source tracking
- duplicate check by email and phone
- owner tracking
- attach candidate to requisition
- candidate status management

## Module 8. Pipeline And Stage Tracking

Purpose:

- run one shared candidate pipeline with configurable visibility

Features:

- candidate pipeline per requisition
- stage movement
- stage history
- shortlist tracking
- rejection reason tracking
- drop-off tracking
- joined tracking
- pipeline summary by requisition
- pipeline summary by user
- stalled and aging visibility

## Module 9. Daily Updates And Execution Tracking

Purpose:

- capture operational progress and blockers

Features:

- daily update submission
- requisition-linked updates
- sourced count
- screened count
- submitted count
- interview count
- blockers
- next action
- manager review view

## Module 10. Dashboards And Reports

Purpose:

- provide role-wise operational and summary visibility

Features:

- dashboard builder by role assignment
- my work dashboard
- location dashboard
- pipeline dashboard
- requisition dashboard
- recruiter productivity summary
- location-wise summary
- combined summary for Admin

## Core Workflow

The MVP workflow should be:

1. Admin creates locations and users.
2. Admin creates roles.
3. Admin assigns modules, features, pages, and actions to those roles.
4. Client records are created.
5. Requisitions are created.
6. Work is assigned.
7. Candidates are created and linked.
8. Pipeline stages are updated.
9. Daily updates are submitted.
10. Dashboards and reports show progress based on configured visibility.

## Access Model

Every non-admin role should be controlled by configurable access definitions.

Recommended visibility scopes:

- `own`
- `team`
- `location`
- `global`

Recommended access verbs:

- `full`
- `manage`
- `work`
- `view`
- `none`

## Important Clarification

The system should not assume:

- that one company uses `BDM`
- that another uses `Recruiter`
- that all companies have the same hierarchy
- that roles must be predefined by the product

Instead, the product should assume:

- only `Admin` is fixed
- every other role is configurable
- modules are stable
- features are stable
- access is configurable

## Success Definition

The working model is successful if:

- Admin can create locations and users
- Admin can create custom roles
- Admin can assign modules and features to each role
- Admin can control page and action visibility
- the system can run client, requisition, candidate, pipeline, and daily update workflows
- the system can support different company hierarchies without code changes
