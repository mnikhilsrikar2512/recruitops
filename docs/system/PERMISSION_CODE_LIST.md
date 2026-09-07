# Permission Code List

## Purpose

This document defines the backend permission vocabulary for the configurable recruitment system.

It is designed for a product where:

- `Admin` is the only fixed role
- all other roles are configurable
- Admin assigns modules, actions, and scope

This document should be used for:

- backend authorization
- role configuration UI
- permission seeding
- audit and approval checks
- API middleware

## Permission Design Principles

- permission codes must be stable even when business titles change
- permission codes should describe actions, not org hierarchy
- scopes must be applied separately from the permission code itself
- page access can be derived from permission groups in MVP
- approval and override permissions should be explicit, not implied

## Scope Model

Permissions work together with scope values:

- `own`
- `team`
- `location`
- `global`

Example:

- a user may have `candidate.read`
- but their scope may still be only `own` or `location`

## Permission Groups

The MVP permission model is organized into these groups:

1. Authentication
2. Role Configuration
3. Location Management
4. User Management
5. Client Management
6. Requisition Management
7. Work Allocation
8. Candidate Management
9. Duplicate Review
10. Pipeline Management
11. Daily Updates
12. Reporting And Dashboards
13. Audit
14. Approvals
15. Settings

## 1. Authentication

- `auth.session.manage_own`
- `auth.permissions.view_own`

## 2. Role Configuration

- `role.read`
- `role.create`
- `role.update`
- `role.activate`
- `role.deactivate`
- `role.template.read`
- `role.template.clone`
- `role.permissions.assign`
- `role.scope.assign`
- `role.preview`
- `role.over_access.review`

## 3. Location Management

- `location.read`
- `location.create`
- `location.update`
- `location.activate`
- `location.deactivate`
- `location.request_cross_access`
- `location.approve_cross_access`
- `location.report.read`

## 4. User Management

- `user.read`
- `user.create`
- `user.update`
- `user.activate`
- `user.deactivate`
- `user.delete.soft`
- `user.delete.hard`
- `user.role.assign`
- `user.permissions.assign_extra`
- `user.location.assign`
- `user.manager.assign`
- `user.credentials.manage`
- `user.access.notify`

## 5. Client Management

- `client.read`
- `client.create`
- `client.update`
- `client.delete.soft`
- `client.contact.read`
- `client.contact.create`
- `client.contact.update`
- `client.contact.delete.soft`
- `client.cross_location_access.request`
- `client.cross_location_access.approve`

## 6. Requisition Management

- `requisition.read`
- `requisition.create`
- `requisition.update`
- `requisition.close`
- `requisition.reopen`
- `requisition.owner.assign`
- `requisition.delivery_owner.assign`
- `requisition.secondary_contact.assign`
- `requisition.status.update`
- `requisition.skills.manage`
- `requisition.career_gap.manage`
- `requisition.update_time_window.manage`

## 7. Work Allocation

- `assignment.read`
- `assignment.create`
- `assignment.update`
- `assignment.reassign`
- `assignment.reassign.approve`
- `assignment.history.read`

## 8. Candidate Management

- `candidate.read`
- `candidate.create`
- `candidate.update`
- `candidate.delete.soft`
- `candidate.delete.hard`
- `candidate.resume.upload`
- `candidate.social_profile.manage`
- `candidate.source_owner.view`
- `candidate.source_owner.preserve`
- `candidate.current_owner.assign`
- `candidate.location_transfer.request`
- `candidate.location_transfer.approve`
- `candidate.link_requisition`
- `candidate.unlink_requisition`

## 9. Duplicate Review

- `candidate.duplicate.check`
- `candidate.duplicate.compare`
- `candidate.duplicate.request_override`
- `candidate.duplicate.approve_override`
- `candidate.duplicate.discard_draft`
- `candidate.duplicate.link_existing`

## 10. Pipeline Management

- `pipeline.read.summary`
- `pipeline.read.detail`
- `pipeline.stage.move`
- `pipeline.stage.comment`
- `pipeline.stage.reject`
- `pipeline.stage.mark_joined`
- `pipeline.stage.history.read`
- `pipeline.template.read`
- `pipeline.template.create`
- `pipeline.template.update`
- `pipeline.template.assign`

## 11. Daily Updates

- `daily_update.read`
- `daily_update.create_main`
- `daily_update.create_extra`
- `daily_update.update_own`
- `daily_update.review`
- `daily_update.reminder.manage`

## 12. Reporting And Dashboards

- `dashboard.read_my_work`
- `dashboard.read_location_summary`
- `dashboard.read_pipeline_summary`
- `dashboard.read_requisition_summary`
- `dashboard.read_admin_combined`
- `report.read_live`
- `report.read_locked`
- `report.generate_weekly`
- `report.generate_monthly`
- `report.lock_weekly`
- `report.lock_monthly`
- `report.unlock_weekly`
- `report.unlock_monthly`
- `report.export`
- `report.data_quality.view`

## 13. Audit

- `audit.read`
- `audit.read_global`
- `audit.scope_bypass`
- `audit.permission_changes.read`
- `audit.override_events.read`
- `audit.view_access_log.read`

## 14. Approvals

- `approval.read`
- `approval.request`
- `approval.decide`
- `approval.reassign`
- `approval.backup_act`

## 15. Settings

- `settings.read`
- `settings.update_own`
- `settings.update_system`

## Special Control Permissions

These should be treated as especially sensitive:

- `role.permissions.assign`
- `role.scope.assign`
- `role.over_access.review`
- `user.delete.hard`
- `candidate.delete.hard`
- `candidate.location_transfer.approve`
- `candidate.duplicate.approve_override`
- `pipeline.template.update`
- `report.unlock_weekly`
- `report.unlock_monthly`
- `audit.read_global`
- `audit.scope_bypass`
- `approval.decide`

## Suggested MVP Admin Baseline

Admin should normally receive:

- every permission code in this document

Non-admin roles should receive:

- only explicitly configured subsets

## Recommended Seeding Strategy

The product should seed:

- permission definitions
- optional starter role templates

The product should not seed:

- fixed permanent non-admin operational roles as mandatory

## Example Role Configuration Pattern

Example only:

- a sourcing-type role may receive:
  - `candidate.read`
  - `candidate.create`
  - `candidate.resume.upload`
  - `candidate.duplicate.check`
  - `candidate.duplicate.compare`
  - `pipeline.read.detail`
  - `daily_update.create_main`

- a reporting-only role may receive:
  - `dashboard.read_location_summary`
  - `dashboard.read_pipeline_summary`
  - `report.read_live`
  - `report.read_locked`
  - `report.data_quality.view`

## Implementation Notes

- backend must always combine permission code + scope
- UI should not assume permission based on business title
- approval flows should check explicit approve permissions
- duplicate override must check both compare-step completion and override authority
- audit access must still respect scope unless bypass permission is granted
