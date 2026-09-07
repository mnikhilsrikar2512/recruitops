# Working Model Features And Access Lifecycle

## Purpose

This document explains the MVP working model using:

- features
- modules
- admin configuration flow
- user access lifecycle

This document no longer defines fixed non-admin operational roles.

Only `Admin` is fixed by the product.

All other roles must be created and configured by Admin.

## Product Direction

The system should be role-configurable, not role-predefined.

That means the product team should build:

- stable modules
- stable features
- stable permission framework
- stable visibility rules

And allow Admin to decide:

- what roles exist
- what those roles are called
- what those roles can access
- what those roles can do

## Admin Configuration Lifecycle

### Step 1. Company Setup

Admin creates:

- company setup values
- locations
- basic operating structure

### Step 2. User Setup

Admin creates:

- users
- primary location mapping
- reporting structure

### Step 3. Role Setup

Admin creates:

- custom roles
- role names
- role descriptions

Examples:

- one company may create `BDM`
- another may create `Business Head`
- another may create `Delivery Manager`

These are customer decisions, not fixed product roles.

### Step 4. Access Setup

Admin assigns to each role:

- modules
- features
- pages
- actions
- visibility scope

### Step 5. Operational Flow

Configured users then work through:

- client flow
- requisition flow
- candidate flow
- pipeline flow
- daily update flow
- dashboard flow

## Module And Feature List

## Module 1. Authentication And Access

Features:

- login
- logout
- password setup
- password reset
- session control
- role-based access
- scope-based access

## Module 2. Role And Permission Configuration

Features:

- create role
- edit role
- activate and deactivate role
- assign modules to role
- assign pages to role
- assign features to role
- assign actions to role
- assign visibility scope

## Module 3. Location And User Administration

Features:

- create location
- edit location
- activate and deactivate location
- create user
- edit user
- activate and deactivate user
- map user to location
- map user to reporting manager
- assign role to user

## Module 4. Client Directory

Features:

- client create
- client edit
- client list
- client detail
- client contact create
- client contact edit
- client contact list
- client status tracking

## Module 5. Requisition Management

Features:

- requisition create
- requisition edit
- requisition list
- requisition detail
- requirement ownership fields
- JD capture
- status tracking
- requisition metrics

## Module 6. Work Allocation

Features:

- assign work owner
- assign support users
- reassign work
- assignment history
- workload visibility

## Module 7. Candidate Management

Features:

- candidate create
- candidate edit
- candidate list
- candidate detail
- resume upload
- source tracking
- duplicate check
- ownership tracking

## Module 8. Pipeline Management

Features:

- candidate pipeline
- stage movement
- stage history
- shortlist tracking
- rejection tracking
- joined tracking
- aging and stalled visibility
- summary views

## Module 9. Daily Updates

Features:

- submit daily update
- requisition-linked update
- blockers
- next actions
- progress counters
- review view

## Module 10. Dashboards And Reports

Features:

- my work dashboard
- pipeline summary
- requisition summary
- location summary
- role-wise dashboards
- admin combined reports

## User Access Lifecycle

This is the lifecycle every non-admin user should follow in the system.

### 1. User Creation

- Admin creates user
- Admin assigns location
- Admin assigns reporting manager
- Admin assigns configured role

### 2. First Access

- user logs in
- system loads assigned role permissions
- system loads page access
- system loads visibility scope

### 3. Operational Access

- user sees only allowed modules
- user sees only allowed pages
- user sees only allowed records
- user performs only allowed actions

### 4. Role Change

- Admin changes role assignment when needed
- page access and action access update accordingly

### 5. Access Removal

- Admin deactivates user or removes role access
- system blocks access immediately

## Clarification On Role Assignment

### 1. Only Admin Is Fixed

The product should not ship with fixed operational role definitions.

Only `Admin` should be predefined.

### 2. All Other Roles Are Configurable

Admin should be able to create roles such as:

- sales roles
- account roles
- delivery roles
- sourcing roles
- reviewer roles

But these should remain customer-defined.

### 3. Module Assignment Is Configurable

Admin should be able to decide:

- which role can access clients
- which role can access requisitions
- which role can access candidates
- which role can access pipeline
- which role can access dashboards

### 4. Feature Assignment Is Configurable

Admin should be able to decide:

- which role can create
- which role can edit
- which role can assign
- which role can move pipeline stages
- which role can only view

### 5. Scope Assignment Is Configurable

Admin should be able to define if a role can access:

- own records
- team records
- location records
- global records

## Recommended MVP Build Focus

The first build should prioritize:

1. Admin configuration capability
2. Authentication and access
3. Location and user administration
4. Client registry
5. Requisition management
6. Work allocation
7. Candidate management
8. Pipeline management
9. Daily updates
10. Dashboards and reports

## Success Definition

The MVP is successful if:

- Admin can create roles
- Admin can assign modules and features
- Admin can control page and action visibility
- different companies can use different role structures
- operational workflows still run without changing the product architecture
