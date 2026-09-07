# Working Model Role Configuration Matrix

## Purpose

This document defines how the MVP should support configurable roles, pages, modules, and actions.

It no longer assigns product pages to fixed non-admin roles.

Instead, it defines what `Admin` must be able to configure.

## Fixed Product Role

The only fixed role in the product is:

- `Admin`

Admin must be able to:

- create roles
- edit roles
- assign modules to roles
- assign pages to roles
- assign features to roles
- assign action permissions to roles
- assign visibility scopes to roles
- assign roles to users

## Page Configuration Model

For every created role, Admin should be able to control access to the following page groups.

### Shared Pages

- Login
- Access Denied
- My Profile
- My Work Dashboard

### Admin Configuration Pages

- Location Management
- User Management
- Role Management
- Module Assignment
- Feature Assignment
- Page Assignment
- Action Permission Assignment
- Visibility Scope Assignment

### Operational Pages

- Client Directory
- Client Detail
- Client Contacts
- Requisition List
- Create Requisition
- Requisition Detail
- Assignment Board
- Candidate List
- Candidate Detail
- Add Candidate
- Resume Upload
- Pipeline Board
- Pipeline Summary
- Daily Updates Submission
- Daily Updates Review
- Role Dashboard
- Reports

## Access Verbs

- `full`
  configure, create, read, update, delete, assign, and govern
- `manage`
  create, read, update, assign, and control workflow
- `work`
  perform operational actions on allowed records
- `view`
  read-only or summary-only visibility
- `none`
  no access

## Scope Types

- `own`
- `team`
- `location`
- `global`

## Admin Configuration Matrix

Admin should be able to define for each custom role:

### 1. Module Access

Admin can decide whether a role has:

- `full`
- `manage`
- `work`
- `view`
- `none`

Against each module:

- Authentication And Access
- Role And Permission Configuration
- Location And User Administration
- Client Directory
- Requisition Management
- Work Allocation
- Candidate Management
- Pipeline Management
- Daily Updates
- Dashboards And Reports

### 2. Page Access

Admin can decide whether a role can access:

- Client Directory
- Client Detail
- Client Contacts
- Requisition List
- Create Requisition
- Requisition Detail
- Assignment Board
- Candidate List
- Candidate Detail
- Add Candidate
- Resume Upload
- Pipeline Board
- Pipeline Summary
- Daily Updates Submission
- Daily Updates Review
- Role Dashboard
- Reports
- My Work Dashboard
- My Profile

### 3. Feature Access

Admin can decide whether a role can:

- create clients
- edit clients
- create contacts
- edit contacts
- create requisitions
- edit requisitions
- assign work
- reassign work
- create candidates
- edit candidates
- upload resumes
- move stages
- view pipeline
- view summaries
- submit daily updates
- review daily updates
- export reports

### 4. Scope Access

Admin can decide whether a role sees:

- own records
- team records
- location records
- global records

## Admin Default Page Access

Assigned pages:

- Location Management
- User Management
- Role Management
- Module Assignment
- Feature Assignment
- Page Assignment
- Action Permission Assignment
- Visibility Scope Assignment
- Client Directory
- Requisition List
- Candidate List
- Pipeline Summary
- Daily Updates Review
- Role Dashboard
- Reports
- My Profile

Admin access level:

- all configuration pages: `full`
- all operational pages: `full`
- all report pages: `full`

## Recommended Operational Page Buckets

These are the page buckets Admin should configure for custom roles.

### Bucket 1. Client Access

- Client Directory
- Client Detail
- Client Contacts

### Bucket 2. Requisition Access

- Requisition List
- Create Requisition
- Requisition Detail

### Bucket 3. Assignment Access

- Assignment Board

### Bucket 4. Candidate Access

- Candidate List
- Candidate Detail
- Add Candidate
- Resume Upload

### Bucket 5. Pipeline Access

- Pipeline Board
- Pipeline Summary

### Bucket 6. Daily Update Access

- Daily Updates Submission
- Daily Updates Review

### Bucket 7. Dashboard And Reporting Access

- Role Dashboard
- Reports
- My Work Dashboard
- My Profile

## Recommended Permission Design

The product should separate:

- page visibility
- feature visibility
- action permission
- record scope

Example:

- a role may see `Candidate List`
- but may not be allowed to edit candidates
- and may only see candidates in `own` scope

## Clarification

This document is intentionally not assigning:

- BDM pages
- Account Manager pages
- Delivery Lead pages
- Recruiter pages

Those should be configured by Admin after the company defines its operating structure.

## MVP Success Definition

The role configuration model is successful if:

- Admin can create any required business role
- Admin can map modules and pages without code changes
- Admin can control actions separately from page visibility
- Admin can control visibility scope separately from feature access
- different companies can create different role structures on the same product
