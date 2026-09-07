# Module-Wise Use Cases And Exceptions

## Purpose

This document lists:

- normal business use cases
- expected user outcomes
- common operational exceptions
- system handling expectations

It is written for the current MVP working model and should be used during:

- backend API planning
- DB rule planning
- permission design
- frontend screen planning
- QA test-case creation

Use case meaning:

- a normal business action the system should support

Exception meaning:

- a non-standard situation where the normal workflow needs validation, override, reassignment, escalation, or audit logging

## Writing Pattern

Each use case below follows this structure:

- actor
- action
- expected result
- linked exception examples

## Module 1. Authentication And Session Control

### Use Cases

- A user logs in with email and password and enters the system with the correct role, title, and location context.
- A user logs out and the active session is invalidated.
- A logged-in user opens the app again and the system validates whether the session is still active.
- A user checks their current profile context through the authenticated session payload.
- A user views their own effective permission payload to understand what pages and actions are available.
- An admin resets a user’s credentials and forces password change on first login.
- A newly onboarded user receives a first-login access flow and sets a usable password.

### Exceptions

- Invalid password entered:
  System rejects login and records failed access attempt.
- Inactive or suspended user attempts login:
  System blocks access and returns a restricted-status response.
- Session token is expired or revoked:
  System forces re-authentication.
- User has valid credentials but incomplete onboarding:
  System allows only setup flow if that model is enabled.
- Admin resets credentials while the user is currently active:
  Existing sessions may be revoked depending on policy.

## Module 2. Role, Permission, And Access Configuration

### Use Cases

- Admin creates a new custom role for a company-specific title.
- Admin assigns modules, pages, actions, and scopes to a role.
- Admin updates a role without changing historical audit records.
- Admin assigns a primary role to a user.
- A user loads the application and sees only the modules allowed by their effective permissions.
- A reviewer-style user gets read-only visibility without edit controls.

### Exceptions

- Admin creates a role with overly broad access:
  System should flag sensitive combinations for review.
- Role update removes access from users currently using a module:
  System should apply new access immediately and log the change.
- User receives extra permissions outside their base role:
  System should resolve final access from both role and direct grants.
- A user attempts an action outside their permission scope:
  System must deny the action and return a clear authorization error.

## Module 3. Location And User Administration

### Use Cases

- Admin creates a new location.
- Admin activates or deactivates a location.
- Admin creates a user and maps the user to a primary location.
- Admin assigns reporting manager and business title to a user.
- Admin edits a user’s phone, role, manager, or status.
- Admin resets a user’s access credentials.
- Admin lists users by location, status, or role for workforce management.

### Exceptions

- User is assigned to a deactivated location:
  System should block new operational assignments until corrected.
- User is assigned to report to themselves:
  System must reject the update.
- Duplicate email or employee code:
  System must reject creation or update.
- User is moved to another location while owning active work:
  System should require reassignment review or controlled transfer handling.

## Module 4. Client Directory

### Use Cases

- A permitted user creates a client under a location.
- A permitted user edits client name, industry, notes, or status.
- A permitted user adds primary and secondary client contacts.
- A user searches clients by code, owner, industry, or status.
- A user opens client detail to review contacts and linked requisitions.
- A business source owner is linked to a client for origination tracking.

### Exceptions

- Same client is attempted again in the same location:
  System should detect likely duplication and ask for review.
- Client is created under the wrong location:
  System should require correction before requisitions flow through the wrong team.
- Contact selected for a requisition does not belong to the client:
  System must reject the mapping.
- One location tries to work on a client owned by another location:
  System must block by default unless explicit exception policy exists.

## Module 5. Requisition Management

### Use Cases

- A permitted user creates a requisition from a client requirement.
- A user captures title, priority, openings, owners, contacts, skills, work mode, and target closure date.
- An account-facing owner tracks requisition intake progress.
- A delivery-side owner tracks execution progress through the recruitment team.
- A user updates requisition status from draft to open, on-hold, closed, or cancelled.
- A user views requisitions filtered by location, client, owner, status, or priority.
- A user opens requisition detail to review assignment, pipeline, and skill requirements.

### Exceptions

- Primary owner and delivery owner belong to the wrong location:
  System must reject owner assignment.
- Requisition is created against an inactive client:
  System should reject or require controlled override.
- Closed requisition needs reopening:
  System should require a tracked status change reason.
- Requisition owner becomes unavailable:
  System should trigger reassignment workflow.
- Client changes pipeline stages mid-process:
  System should allow template update without silently corrupting active applications.

## Module 6. Work Allocation And Assignment

### Use Cases

- A lead or admin assigns a requisition to a recruiter.
- A support user is added as contributor to a requisition.
- Assignment history is visible for audit and workload understanding.
- A user lists current assignments for a requisition.
- A manager reassigns work when capacity changes.

### Exceptions

- Assignee belongs to another location:
  System should block unless cross-location exception is explicitly approved.
- Reassignment happens while active candidate work exists:
  System should preserve history and require confirmation.
- A user is deactivated while still assigned:
  System should surface reassignment-required alerts.

## Module 7. Candidate Management

### Use Cases

- A recruiter creates a candidate profile manually.
- A recruiter uploads candidate details and source information.
- A recruiter edits candidate profile before final submission.
- A recruiter views candidate list by source owner, owner, requisition, or duplicate state.
- A recruiter opens candidate detail and sees linked applications.
- A user adds document metadata for a candidate.
- A user runs duplicate check for a candidate before finalization.
- A user finalizes a candidate into a requisition pipeline.

### Exceptions

- Duplicate candidate is detected:
  System must force compare-first flow before override or discard decision.
- Duplicate override is requested:
  System should create a review case and preserve snapshot details.
- Candidate is linked to the wrong owner:
  System should support controlled owner correction with audit.
- Candidate is finalized into the wrong requisition:
  System should require restore or unlink workflow rather than silent edit.
- Candidate profile is incomplete but save is attempted as final:
  System should block or downgrade to draft.

## Module 8. Pipeline Management

### Use Cases

- A recruiter opens pipeline board to track active applications.
- A recruiter views candidates they sourced, submitted, or own in pipeline.
- A delivery lead reviews team pipeline for a location.
- A user opens a pipeline application detail page.
- A recruiter moves a candidate from one stage to another.
- A user reviews stage history for a candidate application.
- A user tracks stalled profiles and joining progress.

### Exceptions

- Candidate is moved to an invalid stage:
  System should reject if stage is not part of the requisition’s active pipeline template.
- Candidate is moved backward in stage:
  System should log reason and preserve stage history.
- Candidate is marked rejected after being joined:
  System should reject inconsistent state transition.
- Unauthorized user tries to update another location’s pipeline:
  System must deny access.
- Pipeline template changes after applications already started:
  System should protect existing histories and require controlled mapping.

## Module 9. Daily Updates

### Use Cases

- A recruiter submits a daily update for a requisition on a specific date.
- A user records sourcing, screening, submission, interview, and closure counts.
- A user records blockers and next actions.
- A lead or manager reviews location-level daily updates.
- A user filters daily updates by date, location, requisition, or submitting user.
- A user opens daily update detail for operational review.

### Exceptions

- User submits update for a requisition outside their location:
  System should reject.
- Same user attempts multiple final updates for the same requisition and date:
  System should either merge, block, or enforce one-record policy based on company configuration.
- Daily update missed due to leave or outage:
  System should support draft catch-up or approved delay handling.
- Counts entered do not align with pipeline evidence:
  System should flag review discrepancy, not silently overwrite.

## Module 10. Dashboards

### Use Cases

- A logged-in user opens role dashboard and sees summary metrics for their current access context.
- A logged-in user opens my-work dashboard and sees owned requisitions, sourced candidates, active pipeline items, and submitted updates.
- A senior user reviews location-level execution summary.
- An admin compares overall recruitment activity across locations.

### Exceptions

- Dashboard data includes records outside allowed scope:
  System must prevent overexposure through backend filtering.
- Metrics are stale because refresh jobs or update sources lag:
  System should show refresh timing if needed.
- User changes location or role and cached dashboard still reflects old access:
  System should refresh access-dependent metrics.

## Module 11. Notifications

### Use Cases

- A user opens the notification inbox and sees assigned notifications.
- A user filters notifications by status or priority.
- A user marks a notification as read.
- A user follows the action URL from a notification into the relevant workflow page.
- System raises notifications for reassignment needs, duplicate reviews, pending approvals, and due work.

### Exceptions

- User attempts to mark another user’s notification as read:
  System must reject.
- Notification points to an entity that was closed or removed:
  System should show graceful fallback rather than broken navigation.
- Notification was delivered but business event is already resolved:
  System should remain auditable but can be marked read or archived.

## Cross-Module Use Cases

### Requisition-To-Pipeline Operating Loop

- Client exists in the correct location.
- Requisition is created from the client requirement.
- Owners and delivery team are assigned.
- Recruiter sources candidate profiles.
- Candidate duplicate check is completed.
- Candidate is finalized into requisition pipeline.
- Pipeline stages are updated through screening and hiring flow.
- Daily updates capture operational progress.
- Dashboards summarize execution health.

### User Access Lifecycle

- Admin creates location.
- Admin creates role.
- Admin creates user.
- Admin assigns role, title, manager, and location.
- User receives credentials.
- User logs in and sees allowed modules.
- User performs only permitted actions inside permitted scope.

## Cross-Module Exceptions

- Cross-location access request for a restricted client or requisition.
- Duplicate candidate override request.
- Reassignment of active requisition due to owner unavailability.
- Stage skip or forced movement due to client-specific process deviation.
- Reopen closed requisition due to revived client demand.
- Restore mistakenly rejected candidate application.
- Locked or missed reporting period requiring controlled backfill.

## System Handling Expectations For Exceptions

- Exception events should never silently bypass rules.
- Sensitive exceptions should create audit records.
- Approval-based exceptions should capture:
  - requested by
  - approved by
  - reason
  - timestamp
  - before value
  - after value
- Temporary exceptions should expire automatically where possible.
- Exception handling should preserve location-separation rules unless an approved override exists.

## Recommended Next Step

Convert this document into:

- API rule checklist
- DB validation checklist
- QA scenario sheet
- role-wise test scenarios
