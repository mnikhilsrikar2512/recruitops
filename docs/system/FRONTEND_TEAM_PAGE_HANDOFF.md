# Frontend Team Page Handoff

Date locked:

- Tuesday, August 18, 2026

## Purpose

This file is the direct handoff sheet for frontend contributors.

Each page section tells the builder:

- what page they are working on
- what APIs are required
- what can be handled in frontend JS only
- what must not be faked in JS

## Rule For All Pages

### JS Can Handle

- local UI state
- open and close of drawers, dialogs, and panels
- local form validation hints
- loading, empty, and success visuals
- local draft behavior before final submit
- animations, transitions, and interaction feedback

### API Must Handle

- persistent business data
- validation that affects saved data
- role and scope permissions
- cross-record checks
- dashboard truth
- notifications truth

## 1. Login

### Required APIs

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

### JS Only

- email format validation
- password visibility toggle
- loading spinner
- inline invalid-credential message rendering

### Do Not Fake In JS

- login success
- inactive user decision
- permission payload

## 2. Access Denied

### Required APIs

- no direct page API required

### JS Only

- read route-guard failure state
- render denial message
- navigate back or to dashboard

### Do Not Fake In JS

- permission decision itself

## 3. Role Dashboard

### Required APIs

- `GET /api/v1/dashboards/role`

### JS Only

- widget expand and collapse
- card hover states
- local refresh animation
- drill-down highlight state

### Do Not Fake In JS

- KPI counts
- stale counts
- pending duplicate review counts
- updates pending counts

## 4. My Work Dashboard

### Required APIs

- `GET /api/v1/dashboards/my-work`

### JS Only

- local task-card interactions
- highlight urgent cards
- expand and collapse small panels

### Do Not Fake In JS

- assigned requisitions
- interview today count
- update completion state

## 5. Notifications Center

### Required APIs

- `GET /api/v1/notifications`
- `PATCH /api/v1/notifications/{notification_id}/read`

### JS Only

- open detail panel
- optimistic mark-read UI
- unread badge animation

### Do Not Fake In JS

- persistent unread state
- source notification list

## 6. My Profile

### Required APIs

- `GET /api/v1/auth/me`

### JS Only

- profile section tabs if used
- copy-field interactions

### Do Not Fake In JS

- current role
- current location
- reporting manager

## 7. Location Management

### Required APIs

- `GET /api/v1/locations`
- `POST /api/v1/locations`
- `PATCH /api/v1/locations/{location_id}`

### JS Only

- create drawer state
- edit drawer state
- inline required-field hints
- success toast after response

### Do Not Fake In JS

- saved location list
- active and inactive state persistence

## 8. User Management

### Required APIs

- `GET /api/v1/users`
- `POST /api/v1/users`
- `PATCH /api/v1/users/{user_id}`
- `POST /api/v1/users/{user_id}/credentials/reset`

### JS Only

- create drawer
- edit drawer
- local password suggestion
- inline field validation
- unsaved-change warning

### Do Not Fake In JS

- user creation
- user update
- credential reset result

## 9. Role Management

### Required APIs

- `GET /api/v1/roles`
- `POST /api/v1/roles`
- `PATCH /api/v1/roles/{role_id}`
- `PUT /api/v1/roles/{role_id}/permissions`

### JS Only

- permission group expand and collapse
- action selection UI
- scope selection UI
- local review summary before save

### Do Not Fake In JS

- role persistence
- permission persistence

## 10. Client Directory

### Required APIs

- `GET /api/v1/clients`
- `POST /api/v1/clients`

### JS Only

- filter bar behavior
- local table sort on loaded rows if needed
- create drawer state if used

### Do Not Fake In JS

- saved client list
- real status data

## 11. Client Detail

### Required APIs

- `GET /api/v1/clients/{client_id}`
- `PATCH /api/v1/clients/{client_id}`
- `GET /api/v1/clients/{client_id}/contacts`
- `POST /api/v1/clients/{client_id}/contacts`

### JS Only

- add-contact dialog state
- edit-contact dialog state
- local section collapse

### Do Not Fake In JS

- linked requisitions
- contacts persistence
- ownership data

## 12. Requisition List

### Required APIs

- `GET /api/v1/requisitions`

### JS Only

- filter bar interactions
- urgency color emphasis
- local sort on loaded table if needed

### Do Not Fake In JS

- requisition list truth
- due-date and status truth

## 13. Requisition Intake

### Required APIs

- `POST /api/v1/requisitions`
- `PATCH /api/v1/requisitions/{requisition_id}`

### JS Only

- multi-section step behavior
- skill chip input
- local priority hint
- local due-date urgency preview
- draft-style unsaved state

### Do Not Fake In JS

- final requisition save
- ownership persistence
- stage template persistence

## 14. Requisition Detail

### Required APIs

- `GET /api/v1/requisitions/{requisition_id}`
- `PATCH /api/v1/requisitions/{requisition_id}/status`
- `POST /api/v1/requisitions/{requisition_id}/assignments`

### JS Only

- open reassign dialog
- section collapse
- optimistic UI after status change response

### Do Not Fake In JS

- assignment persistence
- status persistence
- pipeline counters

## 15. Delivery Work Queue

### Required APIs

- `GET /api/v1/requisitions`
- optionally `GET /api/v1/dashboards/role` if queue summary uses dashboard data

### JS Only

- ranked visual emphasis
- urgency badges
- sorting controls

### Do Not Fake In JS

- queue data truth
- stale and due status truth

## 16. Candidate Profiles

### Required APIs

- `GET /api/v1/candidates`
- `POST /api/v1/candidates`
- `GET /api/v1/candidates/{candidate_id}`
- `PATCH /api/v1/candidates/{candidate_id}`

### JS Only

- local draft state
- filter interactions
- list-detail switching
- social profile chip editing

### Do Not Fake In JS

- candidate save
- candidate updates
- linked requisition truth

## 17. Resume Upload And Review

### Required APIs

- `POST /api/v1/candidates/{candidate_id}/resume`

### JS Only

- upload progress display
- file preview state
- continue button state

### Do Not Fake In JS

- uploaded file persistence

## 18. Candidate Duplicate Review

### Required APIs

- `GET /api/v1/candidates/{candidate_id}/duplicate-check`
- `POST /api/v1/candidates/{candidate_id}/duplicate-decision`

### JS Only

- compare layout behavior
- decision confirmation dialog if used
- local highlight of differences

### Do Not Fake In JS

- duplicate matches
- duplicate decision persistence

## 19. Candidate Screening

### Required APIs

- candidate detail API
- requisition detail API
- pipeline move-stage API

### JS Only

- section collapse
- inline fit indicators
- notes field behavior
- stage-move dialog open state

### Do Not Fake In JS

- screening result persistence
- rule truth

## 20. Pipeline Board

### Required APIs

- `GET /api/v1/pipeline/board`
- `POST /api/v1/pipeline/{application_id}/move-stage`
- `GET /api/v1/pipeline/{application_id}/history`

### JS Only

- drag preview
- stage column collapse
- history drawer state
- card hover actions

### Do Not Fake In JS

- final stage movement
- stage history
- pipeline counts

## 21. Pipeline History Drawer Or Panel

### Required APIs

- `GET /api/v1/pipeline/{application_id}/history`

### JS Only

- drawer open and close
- timeline expand if needed

### Do Not Fake In JS

- audit history data

## 22. Daily Updates Submission

### Required APIs

- `POST /api/v1/daily-updates`

### JS Only

- local draft text
- count helper formatting
- success toast
- redirect after submit

### Do Not Fake In JS

- saved daily update

## 23. Daily Updates Review

### Required APIs

- `GET /api/v1/daily-updates`
- `GET /api/v1/daily-updates/{daily_update_id}`

### JS Only

- detail panel state
- filter UI
- row highlight state

### Do Not Fake In JS

- review list truth
- update detail truth

## 24. Reassign Owner Dialog

### Required APIs

- requisition detail API
- requisition assignment or update API

### JS Only

- dialog state
- warning display
- reason input behavior

### Do Not Fake In JS

- reassignment persistence

## 25. Stage Move Dialog

### Required APIs

- `POST /api/v1/pipeline/{application_id}/move-stage`

### JS Only

- dialog state
- conditional field switching
- pre-submit validation hints

### Do Not Fake In JS

- final stage move
- stage validation truth

## 26. Contact Form Dialog

### Required APIs

- `POST /api/v1/clients/{client_id}/contacts`

### JS Only

- dialog open and close
- inline validation hints

### Do Not Fake In JS

- contact persistence

## 27. Notification Detail Panel

### Required APIs

- `GET /api/v1/notifications`
- `PATCH /api/v1/notifications/{notification_id}/read`

### JS Only

- side panel state
- linked-record navigation action

### Do Not Fake In JS

- notification truth
- read-state persistence

## Parallel Work Rule

If multiple frontend people work at once:

- one person can own layout and shell work
- one person can own admin pages
- one person can own client and requisition pages
- one person can own candidate and pipeline pages
- one person can own daily updates and notifications

But everyone must use the same:

- layout system
- table shell
- form field system
- dialog, drawer, and side panel shells
