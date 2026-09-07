# Production Checklist

## Purpose

This checklist is the working readiness tracker for the recruitment system.

It covers:

- work already completed in planning and frontend prototyping
- work still required before production launch
- end-to-end test coverage needed before calling the system production-ready

Current status:

- frontend prototype and role-based journeys are substantially covered
- backend APIs, SQL implementation, auth, persistence, and production testing are still pending
- the system is not production-ready yet

## 1. Completed Work

- [x] System scope refined for `Admin -> Manager -> HR -> Recruiter`
- [x] Internal and external hiring workflows structured
- [x] Direct client with optional multiple end clients supported in system design
- [x] RBAC navigation behavior applied in frontend
- [x] Sidebar visibility aligned to accessible pages by role
- [x] Modules and features documentation created and updated
- [x] Implementation roadmap created and updated for SQL-based implementation
- [x] Database design document created and updated
- [x] API endpoint list created and updated
- [x] Report structure planning improved beyond a raw weekly tracking table
- [x] Stitch prompt set created for the major screens
- [x] Separate page prompts created from login through the operational workflows
- [x] Global design direction documented for Stitch
- [x] Frontend page set integrated into `frontend/`
- [x] Shared CSS and shared JS structure centralized
- [x] Loader integrated from Stitch and adapted for shared frontend usage
- [x] Notifications, success toasts, empty states, 404, and access denied screens added
- [x] Admin pages added, including audit-related pages
- [x] Manager pages added, including team performance and meetings/follow-ups
- [x] HR and Recruiter pages added for candidates, pipeline, reports, portal access, and daily updates
- [x] User lifecycle pages added for create, update, invite, delete, and deactivate flows
- [x] Resume upload flow pages added for parse review, duplicate check, save candidate, and success states
- [x] Approval modal and drawer flows added
- [x] Dead-link coverage improved across the frontend journeys
- [x] Repeated or oversized buttons and filters were cleaned up
- [x] Frontend typography scale reduced for neater layout
- [x] JS automation added for password generation
- [x] JS automation added for employee code suggestion
- [x] JS automation added for requisition priority recommendation
- [x] JS structured JD preview added
- [x] JS daily update draft narrative generation added
- [x] JS draft persistence added for key form flows
- [x] JS local notification generation added
- [x] JS notification page enhancement added for local automation events

## 2. JS Automation Scope

These are intentionally handled in frontend JS to reduce avoidable API calls:

- [x] Temporary password generation in create and reset flows
- [x] Employee code suggestion from user name
- [x] Requisition priority recommendation from end date, openings, and client-round pressure
- [x] Structured JD preview rendering
- [x] Daily update summary, next-priority, and follow-up draft generation
- [x] Local form draft persistence
- [x] Local frontend notification generation for non-authoritative reminders
- [x] Local notification count updates and live activity rendering on notifications screens

These must still be revalidated or persisted by backend services later:

- [ ] Final credential handling and password hashing
- [ ] Permanent notifications
- [ ] Official reports
- [ ] Candidate duplicate decisions
- [ ] Resume parsing
- [ ] Audit logs
- [ ] Cross-user and location-wide KPIs

## 3. Remaining Backend And SQL Work

- [ ] Build SQL schema and migration scripts
- [ ] Finalize SQL naming, constraints, indexes, and reference rules
- [ ] Build authentication and session management
- [ ] Build real RBAC enforcement on APIs
- [ ] Build user management APIs
- [ ] Build location management APIs
- [ ] Build client and end-client APIs
- [ ] Build requisition APIs
- [ ] Build candidate APIs
- [ ] Build resume upload and parsing integration
- [ ] Build duplicate candidate detection in backend
- [ ] Build screening, rejection, escalation, and client-round APIs
- [ ] Build meetings and meeting outcome APIs
- [ ] Build portal account and slot APIs
- [ ] Build daily, weekly, and monthly reporting APIs
- [ ] Build persistent notification APIs
- [ ] Build audit log APIs
- [ ] Build dashboard KPI APIs
- [ ] Build export APIs for PDF and Excel workflows
- [ ] Connect frontend to real APIs
- [ ] Replace local-only notification behavior with backend-backed notifications where needed
- [ ] Add server-side validation matching frontend logic
- [ ] Add candidate profile expiry handling for the 1-month life rule
- [ ] Add duplicate acknowledgement handling from clients
- [ ] Add client-feedback-driven escalation rules
- [ ] Add monitoring, logging, and security hardening
- [ ] Add deployment and release pipeline

## 4. Production Test Checklist

### Authentication And Access

- [ ] Login works for `Admin`, `Manager`, `HR`, and `Recruiter`
- [ ] Logout works correctly
- [ ] Password reset and setup-link flows work
- [ ] Each role sees only allowed pages in the sidebar
- [ ] Direct URL access to unauthorized pages is blocked
- [ ] Auth/session expiry is handled cleanly

### Navigation And Frontend Integrity

- [ ] All sidebar links resolve to valid pages
- [ ] All visible buttons have valid actions or are intentionally disabled
- [ ] Loaders appear only where needed and clear correctly
- [ ] Empty states render correctly
- [ ] `404` and `Access Denied` pages render correctly
- [ ] No blocking JS errors appear in the browser console

### User Management

- [ ] Create user flow works end to end
- [ ] Update user flow works end to end
- [ ] Invite user flow works end to end
- [ ] Delete user flow works end to end
- [ ] Deactivate user flow works end to end

### Requisitions And Candidates

- [ ] Requisition creation works for internal hiring
- [ ] Requisition creation works for external hiring
- [ ] Optional end clients work correctly
- [ ] Resume upload, parse review, duplicate check, and save candidate flow works end to end
- [ ] Candidate rejection before client round works with the correct classification
- [ ] Internal-side and client-side rejection are separated correctly
- [ ] Client-round-optional flow works correctly

### Meetings, Portal Access, And Updates

- [ ] Meeting logging flow works
- [ ] Portal slot assignment flow works
- [ ] Daily update submission works
- [ ] Weekly and monthly reports render correct table data and summaries
- [ ] Notification flows work correctly

### Data And Reporting

- [ ] SQL data saved matches UI behavior
- [ ] Official report totals match transactional data
- [ ] Candidate profile expiry works for the 1-month rule
- [ ] Client duplicate acknowledgements are tracked correctly
- [ ] Escalation logic follows client feedback state
- [ ] Audit logs capture critical actions

### Responsive And Visual QA

- [ ] Desktop layouts remain stable
- [ ] Tablet layouts remain stable
- [ ] Mobile layouts remain stable
- [ ] Typography, spacing, and action hierarchy feel consistent across pages

## 5. Final Go-Live Gate

The system can be called production-ready only when:

- all required SQL tables and APIs are implemented
- frontend is connected to real backend responses
- RBAC is enforced both in UI and API
- end-to-end tests pass for all role journeys
- audit and security checks pass
- reporting outputs are validated against real data
