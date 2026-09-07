# Screen Field Specification

Date locked:

- Tuesday, August 18, 2026

## Purpose

This document defines the MVP screen set at field level.

It is the build reference for:

- frontend forms
- backend request validation
- QA test cases
- API-to-UI mapping

## Screen Naming Standard

- `Role Dashboard`
- `My Work Dashboard`
- `Client Directory`
- `Client Detail`
- `Requisition List`
- `Requisition Intake`
- `Requisition Detail`
- `Candidate Profiles`
- `Candidate Screening`
- `Pipeline Board`
- `Daily Updates Submission`
- `Daily Updates Review`
- `User Management`
- `Location Management`
- `Role Management`

## 1. Login

### Fields

- email
  required
  type: email
- password
  required
  type: password

### Actions

- sign in
- forgot password

### Validations

- email must exist
- password must match
- inactive users cannot log in

## 2. Location Management

### List Columns

- location code
- location name
- status
- location head
- created date

### Create Or Edit Fields

- location name
  required
- location code
  required
  unique
- address
  optional
- status
  required
  values: `active`, `inactive`
- location head user
  optional

### Actions

- create location
- edit location
- activate or deactivate location
- view location detail

## 3. User Management

### List Columns

- employee id
- full name
- email
- phone
- primary role
- location
- reporting manager
- status

### Create Or Edit Fields

- full name
  required
- email
  required
  unique
- phone
  required
- employee id
  required
  unique
- primary location
  required
- primary role
  required
- reporting manager
  required for non-admin users
- secondary contact
  optional
- status
  required

### Actions

- create user
- edit user
- activate or deactivate user
- reset credentials
- resend invite

## 4. Role Management

### List Columns

- role name
- status
- assigned users count
- scope model

### Create Or Edit Fields

- role name
  required
- role description
  optional
- status
  required
- module permissions
  required
- action permissions
  required
- scope permissions
  required

### Actions

- create role
- edit role
- activate or deactivate role
- assign role to users

## 5. Client Directory

### List Filters

- client name
- location
- status
- client owner
- business source owner

### List Columns

- client code
- client name
- location
- client owner
- business source owner
- status
- active requisitions count

### Create Or Edit Fields

- client name
  required
- client code
  required
  unique
- location
  required
- industry
  optional
- client owner
  required
- business source owner
  optional
- status
  required
- notes
  optional

### Contact Subform

- contact name
  required
- email
  optional
- phone
  optional
- designation
  optional
- primary contact flag
  optional
- secondary contact flag
  optional

### Validations

- client must belong to one location
- primary and secondary contacts must be distinguishable

## 6. Requisition Intake

### Fields

- requisition code
  system generated or configurable by company
- title
  required
- client
  required
- end client
  optional
- location
  required
- client contact
  optional
- primary owner
  required
- delivery owner
  optional
- openings
  required
  must be greater than zero
- priority
  required
- due date
  required
- employment type
  optional
- work mode
  optional
- experience minimum
  optional
- experience maximum
  optional
- job description
  required
- required skills
  required
- good to have skills
  optional
- acceptable career gap
  optional
- available update time for submitted profiles
  required
- client round required
  required
- stage template
  required

### Actions

- create requisition
- save draft
- submit requisition
- assign support users

### Validations

- client and requisition must belong to same location
- owners must have location access

## 7. Requisition Detail

### Summary Sections

- requisition header
- ownership
- client and contact info
- skill summary
- screening rules
- stage model
- assignment list
- pipeline counters
- activity history

### Key Read-Only Fields

- title
- code
- status
- priority
- due date
- primary owner
- delivery owner
- location
- client
- end client

### Actions

- edit requisition
- reassign primary owner
- reassign delivery owner
- add support assignment
- change status
- open pipeline board

## 8. Candidate Profiles

### List Filters

- full name
- email
- phone
- source
- requisition
- stage
- status
- duplicate review state

### List Columns

- candidate code
- full name
- contact summary
- source
- sourced by
- primary owner
- latest requisition
- latest stage
- duplicate state

### Create Or Edit Fields

- full name
  required
- email
  required unless company rule allows phone-only
- phone
  required
- source type
  required
- source detail
  optional
- current company
  required
- current designation
  optional
- total experience
  optional
- current location
  optional
- preferred location
  optional
- notice period
  optional
- current ctc
  optional
- expected ctc
  optional
- social profiles
  required when provided by company rules
- resume file
  required for final save
- profile summary
  optional
- sourced by
  required
- primary owner
  required
- linked requisition
  optional at draft stage

### Duplicate Review Section

- matched candidate
- match reason
- compare values
- override request notes
- discard draft
- link existing record

### Actions

- save draft
- finalize profile
- request duplicate override
- discard draft
- attach to requisition

## 9. Candidate Screening

### Data Shown

- requisition rules
- candidate profile summary
- required skills
- gap check
- document check
- notice period check
- compensation fit

### Input Fields

- screening decision
  required
- screening notes
  required
- missing document notes
  optional
- rejection reason
  required when rejected

### Actions

- pass screening
- fail screening
- move to submitted

## 10. Pipeline Board

### Board Filters

- client
- requisition
- stage
- owner
- recruiter
- location

### Card Summary

- candidate name
- requisition
- current stage
- sourced by
- submitted by
- current owner
- last stage update time
- flags

### Stage Actions

- move forward
- move backward if permitted
- mark rejected
- mark dropped
- mark joined
- add note

### Required Inputs By Stage

- `submitted`
  screening notes
  resume
- `interview`
  interview date
- `rejected`
  rejection reason
- `joined`
  joining date

## 11. Daily Updates Submission

### Fields

- update date
  required
- requisition
  optional
- summary
  required
- profiles sourced count
  required
- profiles screened count
  required
- profiles submitted count
  required
- interviews scheduled count
  required
- offers closed count
  required
- blockers
  optional
- next actions
  optional

### Actions

- save draft
- submit update

## 12. Daily Updates Review

### Filters

- date
- user
- location
- requisition
- submitted status

### Columns

- user
- location
- requisition
- update date
- sourced
- screened
- submitted
- interviews
- blockers
- submission time

### Actions

- view update
- comment if enabled
- export later phase only

## 13. Role Dashboard

### Core Widgets

- active requisitions
- overdue requisitions
- due today tasks
- stale pipelines
- pending duplicate reviews
- daily updates pending
- recent movements

### Visibility Rules

- data must follow role scope
- global visibility only by explicit permission

## 14. My Work Dashboard

### Core Widgets

- my assigned requisitions
- my candidates in progress
- my interviews today
- my pending follow-ups
- my daily update status
- my recent notifications

## QA Notes

Every required field in this document must map to:

- one UI control
- one API request property
- one backend validation rule
- one database persistence path
