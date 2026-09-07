# Final Permission And Action Matrix

Date locked:

- Tuesday, August 18, 2026

## Purpose

This document defines the backend permission primitives for the MVP.

The product is role-configurable, so the backend must enforce actions through stable permission codes rather than fixed role names.

## Permission Model

Each role should be assigned:

- module access
- action permissions
- scope permissions

## Scope Types

- `own`
- `team`
- `location`
- `global`

## Module Codes

- `auth_access`
- `location_admin`
- `user_admin`
- `role_admin`
- `client_management`
- `requisition_management`
- `assignment_management`
- `candidate_management`
- `pipeline_management`
- `daily_updates`
- `dashboard_reporting`
- `notification_center`
- `audit_access`

## Action Permission Codes

### Authentication And Session

- `auth.login`
- `auth.logout`
- `auth.view_self`
- `auth.view_permission_summary`

### Location Administration

- `location.create`
- `location.read`
- `location.update`
- `location.activate`
- `location.deactivate`

### User Administration

- `user.create`
- `user.read`
- `user.update`
- `user.activate`
- `user.deactivate`
- `user.reset_credentials`
- `user.assign_role`
- `user.assign_location`
- `user.assign_reporting_manager`

### Role Administration

- `role.create`
- `role.read`
- `role.update`
- `role.activate`
- `role.deactivate`
- `role.assign_modules`
- `role.assign_actions`
- `role.assign_scopes`

### Client Management

- `client.create`
- `client.read`
- `client.update`
- `client.change_status`
- `client.create_contact`
- `client.read_contact`
- `client.update_contact`

### Requisition Management

- `requisition.create`
- `requisition.read`
- `requisition.update`
- `requisition.change_status`
- `requisition.assign_primary_owner`
- `requisition.assign_delivery_owner`
- `requisition.assign_support_user`
- `requisition.reassign_after_start`

### Candidate Management

- `candidate.create`
- `candidate.read`
- `candidate.update`
- `candidate.upload_resume`
- `candidate.attach_to_requisition`
- `candidate.finalize`
- `candidate.request_duplicate_override`
- `candidate.approve_duplicate_override`

### Pipeline Management

- `pipeline.read`
- `pipeline.move_stage`
- `pipeline.reject`
- `pipeline.drop`
- `pipeline.join`
- `pipeline.view_history`
- `pipeline.comment`

### Daily Updates

- `daily_update.create`
- `daily_update.read`
- `daily_update.review`

### Dashboards And Reports

- `dashboard.read_role`
- `dashboard.read_my_work`
- `dashboard.read_location`
- `dashboard.read_global`
- `report.read_basic`

### Notifications And Audit

- `notification.read`
- `notification.mark_read`
- `audit.read`

## Scope Application Rules

### `own`

The record is visible only if the user is directly connected through:

- created by
- sourced by
- submitted by
- primary owner
- delivery owner
- assigned support user

### `team`

The record is visible if:

- the record belongs to the user’s team
- or the owner belongs to the user’s team

### `location`

The record is visible if:

- the record belongs to the user’s active location

### `global`

The record is visible across all locations only if explicit global scope is granted.

## Required Backend Enforcement Rules

- permissions are checked before scope
- scope is checked before record access
- visibility does not automatically grant edit rights
- edit rights do not automatically grant reassignment rights
- duplicate override is never allowed without explicit permission

## MVP Starter Role Templates

These are starter templates only. They are not fixed product roles.

### `Admin`

- all module permissions
- all action permissions
- `global` scope

### `Business Role Template`

Suggested permissions:

- `client.read`
- `client.create`
- `client.update`
- `client.create_contact`
- `requisition.read`
- `requisition.create`
- `requisition.update`
- `dashboard.read_role`
- `dashboard.read_my_work`

Suggested scope:

- `location`

### `Delivery Lead Template`

Suggested permissions:

- `requisition.read`
- `requisition.update`
- `requisition.assign_delivery_owner`
- `requisition.assign_support_user`
- `candidate.read`
- `pipeline.read`
- `pipeline.move_stage`
- `daily_update.read`
- `dashboard.read_role`
- `dashboard.read_my_work`

Suggested scope:

- `location`

### `Recruiter Template`

Suggested permissions:

- `candidate.create`
- `candidate.read`
- `candidate.update`
- `candidate.upload_resume`
- `candidate.attach_to_requisition`
- `pipeline.read`
- `pipeline.move_stage`
- `daily_update.create`
- `dashboard.read_my_work`

Suggested scope:

- `own`
- `location`

## Critical Action Controls

The following actions require special confirmation or approval flow:

- `requisition.reassign_after_start`
- `candidate.approve_duplicate_override`
- global scope grants
- role permission escalation

## QA Rules

Every protected API route must map to:

- one action permission
- one scope rule
- one record-access rule

No route should rely on frontend hiding alone.
