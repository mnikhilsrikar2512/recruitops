# Role Access Matrix

This document converts the universal role model into implementation-facing access rules.

It should be used for:

- backend authorization
- dashboard routing
- module-level access control
- API visibility rules
- record ownership and scope enforcement

## Source Of Truth

This matrix is aligned to:

- `docs/system/UNIVERSAL_PRODUCT_ARCHITECTURE.md`
- `docs/system/MODULES_AND_FEATURES.md`
- `docs/system/API_ENDPOINTS.md`
- the role lifecycle files in `docs/system/roles/`

## Core Access Rule

Access must always be determined by:

- permission role
- visibility scope
- location membership
- team membership
- record ownership
- workflow assignment

Business titles such as `Director`, `BDM`, `Lead Recruiter`, or `Assistant Recruiter` must never be the primary authorization rule.

## Supported MVP Scopes

- `global`
- `location`
- `team`
- `own`

## Access Verbs

The matrix below uses these access verbs:

- `full`
  create, read, update, delete, assign, and govern
- `manage`
  create, read, update, assign, and operationally control
- `work`
  read and execute workflow actions on scoped records
- `review`
  read assigned context and submit feedback or decisions
- `view`
  read-only access within scope
- `none`
  no direct access

## Dashboard Access Matrix

### Platform Admin

- executive dashboard: `full`
- business dashboard: `view`
- delivery dashboard: `view`
- recruiter dashboard: `view`
- my work dashboard: `view`

### Operations Admin

- executive dashboard: `view`
- business dashboard: `none`
- delivery dashboard: `view`
- recruiter dashboard: `none`
- my work dashboard: `view`

### Business Lead

- executive dashboard: `view`
- business dashboard: `full`
- delivery dashboard: `view`
- recruiter dashboard: `none`
- my work dashboard: `view`

### Client Manager

- executive dashboard: `none`
- business dashboard: `manage`
- delivery dashboard: `view`
- recruiter dashboard: `none`
- my work dashboard: `work`

### Delivery Lead

- executive dashboard: `none`
- business dashboard: `view`
- delivery dashboard: `manage`
- recruiter dashboard: `view`
- my work dashboard: `work`

### Recruiter

- executive dashboard: `none`
- business dashboard: `none`
- delivery dashboard: `none`
- recruiter dashboard: `manage`
- my work dashboard: `work`

### Sourcing Support

- executive dashboard: `none`
- business dashboard: `none`
- delivery dashboard: `view`
- recruiter dashboard: `view`
- my work dashboard: `work`

### Reviewer

- executive dashboard: `none`
- business dashboard: `none`
- delivery dashboard: `none`
- recruiter dashboard: `none`
- my work dashboard: `review`

### External User

- executive dashboard: `none`
- business dashboard: `none`
- delivery dashboard: `none`
- recruiter dashboard: `none`
- my work dashboard: `review`

## Module Access Matrix

### Module 1. Identity, Authentication, And Session Control

- `platform_admin`: `full`
- `operations_admin`: `manage`
- `business_lead`: `view`
- `client_manager`: `view`
- `delivery_lead`: `view`
- `recruiter`: `view`
- `sourcing_support`: `view`
- `reviewer`: `view`
- `external_user`: `view`

### Module 2. Permission Roles, Business Titles, And Access Control

- `platform_admin`: `full`
- `operations_admin`: `manage`
- `business_lead`: `view`
- `client_manager`: `none`
- `delivery_lead`: `none`
- `recruiter`: `none`
- `sourcing_support`: `none`
- `reviewer`: `none`
- `external_user`: `none`

### Module 3. Organization Structure, Locations, Teams, And Reporting Lines

- `platform_admin`: `full`
- `operations_admin`: `manage`
- `business_lead`: `view`
- `client_manager`: `view`
- `delivery_lead`: `view`
- `recruiter`: `none`
- `sourcing_support`: `none`
- `reviewer`: `none`
- `external_user`: `none`

### Module 4. User Administration And Workforce Management

- `platform_admin`: `full`
- `operations_admin`: `manage`
- `business_lead`: `view`
- `client_manager`: `none`
- `delivery_lead`: `view`
- `recruiter`: `none`
- `sourcing_support`: `none`
- `reviewer`: `none`
- `external_user`: `none`

### Module 5. Visibility Scopes And Record Ownership

- `platform_admin`: `full`
- `operations_admin`: `manage`
- all execution roles: `view`
- `reviewer`: `none`
- `external_user`: `none`

### Module 6. CRM, Accounts, Prospects, And Client Relationships

- `platform_admin`: `full`
- `operations_admin`: `manage`
- `business_lead`: `manage`
- `client_manager`: `manage`
- `delivery_lead`: `view`
- `recruiter`: `view`
- `sourcing_support`: `none`
- `reviewer`: `none`
- `external_user`: `review`

### Module 7. Meetings, Calls, Activities, And Follow-Ups

- `platform_admin`: `full`
- `operations_admin`: `manage`
- `business_lead`: `manage`
- `client_manager`: `manage`
- `delivery_lead`: `view`
- `recruiter`: `work`
- `sourcing_support`: `none`
- `reviewer`: `review`
- `external_user`: `review`

### Module 8. Requisition Intake And Structured JD Design

- `platform_admin`: `full`
- `operations_admin`: `manage`
- `business_lead`: `view`
- `client_manager`: `manage`
- `delivery_lead`: `manage`
- `recruiter`: `view`
- `sourcing_support`: `none`
- `reviewer`: `review`
- `external_user`: `none`

### Module 9. Requisition Management And Work Allocation

- `platform_admin`: `full`
- `operations_admin`: `view`
- `business_lead`: `view`
- `client_manager`: `manage`
- `delivery_lead`: `manage`
- `recruiter`: `work`
- `sourcing_support`: `view`
- `reviewer`: `review`
- `external_user`: `none`

### Module 10. Candidate And Talent Records

- `platform_admin`: `full`
- `operations_admin`: `view`
- `business_lead`: `view`
- `client_manager`: `view`
- `delivery_lead`: `manage`
- `recruiter`: `manage`
- `sourcing_support`: `work`
- `reviewer`: `review`
- `external_user`: `review`

### Module 11. Resume Intake, Parsing, And Candidate Draft Preparation

- `platform_admin`: `view`
- `operations_admin`: `view`
- `business_lead`: `none`
- `client_manager`: `none`
- `delivery_lead`: `view`
- `recruiter`: `manage`
- `sourcing_support`: `manage`
- `reviewer`: `none`
- `external_user`: `none`

### Module 12. Duplicate Candidate Detection And Profile Governance

- `platform_admin`: `view`
- `operations_admin`: `view`
- `business_lead`: `none`
- `client_manager`: `view`
- `delivery_lead`: `manage`
- `recruiter`: `manage`
- `sourcing_support`: `work`
- `reviewer`: `none`
- `external_user`: `none`

### Module 13. Screening, Evaluation, And Qualification

- `platform_admin`: `view`
- `operations_admin`: `none`
- `business_lead`: `none`
- `client_manager`: `view`
- `delivery_lead`: `manage`
- `recruiter`: `manage`
- `sourcing_support`: `none`
- `reviewer`: `review`
- `external_user`: `none`

### Module 14. Candidate Pipeline, Stage Movement, And Submission Flow

- `platform_admin`: `view`
- `operations_admin`: `none`
- `business_lead`: `view`
- `client_manager`: `view`
- `delivery_lead`: `manage`
- `recruiter`: `manage`
- `sourcing_support`: `work`
- `reviewer`: `review`
- `external_user`: `review`

### Module 15. Interview Scheduling, Feedback, And Decision Capture

- `platform_admin`: `view`
- `operations_admin`: `none`
- `business_lead`: `none`
- `client_manager`: `view`
- `delivery_lead`: `manage`
- `recruiter`: `work`
- `sourcing_support`: `none`
- `reviewer`: `manage`
- `external_user`: `review`

### Module 16. Offer, Join, Closure, And Placement Tracking

- `platform_admin`: `view`
- `operations_admin`: `none`
- `business_lead`: `view`
- `client_manager`: `view`
- `delivery_lead`: `manage`
- `recruiter`: `work`
- `sourcing_support`: `none`
- `reviewer`: `review`
- `external_user`: `none`

### Module 17. Delivery Operations And Team Work Management

- `platform_admin`: `view`
- `operations_admin`: `view`
- `business_lead`: `view`
- `client_manager`: `view`
- `delivery_lead`: `manage`
- `recruiter`: `work`
- `sourcing_support`: `work`
- `reviewer`: `none`
- `external_user`: `none`

### Module 18. Portal Accounts, Sourcing Tools, And Resource Usage

- `platform_admin`: `full`
- `operations_admin`: `manage`
- `business_lead`: `view`
- `client_manager`: `view`
- `delivery_lead`: `manage`
- `recruiter`: `work`
- `sourcing_support`: `work`
- `reviewer`: `none`
- `external_user`: `none`

### Module 19. Tasks, Reminders, And Follow-Through

- `platform_admin`: `view`
- `operations_admin`: `view`
- `business_lead`: `manage`
- `client_manager`: `manage`
- `delivery_lead`: `manage`
- `recruiter`: `work`
- `sourcing_support`: `work`
- `reviewer`: `review`
- `external_user`: `review`

### Module 20. Notifications And Alerting

- all internal roles: `view`
- `external_user`: `review`

### Module 21. Dashboards, Operational Reporting, And Productivity Analytics

- `platform_admin`: `full`
- `operations_admin`: `view`
- `business_lead`: `manage`
- `client_manager`: `manage`
- `delivery_lead`: `manage`
- `recruiter`: `manage`
- `sourcing_support`: `view`
- `reviewer`: `none`
- `external_user`: `none`

### Module 22. Approvals, Governance, And Exception Handling

- `platform_admin`: `full`
- `operations_admin`: `view`
- `business_lead`: `manage`
- `client_manager`: `review`
- `delivery_lead`: `review`
- `recruiter`: `none`
- `sourcing_support`: `none`
- `reviewer`: `review`
- `external_user`: `none`

### Module 23. Audit Trail, Compliance, And Sensitive Action History

- `platform_admin`: `full`
- `operations_admin`: `view`
- `business_lead`: `view`
- all other roles: `none`

### Module 24. Data Quality, Validation, And Operational Controls

- `platform_admin`: `manage`
- `operations_admin`: `manage`
- `business_lead`: `view`
- `client_manager`: `work`
- `delivery_lead`: `manage`
- `recruiter`: `work`
- `sourcing_support`: `work`
- `reviewer`: `none`
- `external_user`: `none`

### Module 25. Templates, Playbooks, And Standardization

- `platform_admin`: `full`
- `operations_admin`: `manage`
- `business_lead`: `view`
- `client_manager`: `view`
- `delivery_lead`: `manage`
- `recruiter`: `view`
- `sourcing_support`: `none`
- `reviewer`: `none`
- `external_user`: `none`

### Module 26. Import, Export, And Data Portability

- `platform_admin`: `full`
- `operations_admin`: `manage`
- `business_lead`: `view`
- `client_manager`: `view`
- `delivery_lead`: `view`
- `recruiter`: `none`
- `sourcing_support`: `none`
- `reviewer`: `none`
- `external_user`: `none`

### Module 27. Integrations And External Connectivity

- `platform_admin`: `full`
- `operations_admin`: `manage`
- all other roles: `view` or `none` depending on integration context

### Module 28. Automation And AI Assistance

- `platform_admin`: `manage`
- `operations_admin`: `view`
- `business_lead`: `view`
- `client_manager`: `view`
- `delivery_lead`: `manage`
- `recruiter`: `work`
- `sourcing_support`: `work`
- `reviewer`: `none`
- `external_user`: `none`

## API Resource Ownership Rules

### Users

- `platform_admin`: global access
- `operations_admin`: scoped manage access
- all other roles: self access only unless explicitly granted summary access

### Locations And Teams

- `platform_admin`: full
- `operations_admin`: manage within scope
- business and delivery roles: view within scope

### Clients

- `business_lead`: view and manage within scope
- `client_manager`: manage owned or scoped clients
- `delivery_lead`: view clients attached to owned requisitions
- `recruiter`: view client context only for assigned requisitions

### Requisitions

- `client_manager`: create and manage client-originating requisitions in scope
- `delivery_lead`: manage assigned requisitions
- `recruiter`: work assigned requisitions
- `sourcing_support`: view requisitions assigned for sourcing support
- `reviewer`: review only assigned requisitions

### Candidates

- `delivery_lead`: manage candidates in owned requisitions
- `recruiter`: manage candidates in assigned requisitions
- `sourcing_support`: create draft candidates and edit limited candidate fields
- `client_manager`: view candidates only where account visibility is needed
- `reviewer`: review assigned candidates only

## MVP Permission Codes

The first backend version should define permissions at least around these capabilities:

- `auth.manage_session`
- `user.read`
- `user.create`
- `user.update`
- `user.deactivate`
- `role.read`
- `title.read`
- `title.manage`
- `location.read`
- `location.manage`
- `team.read`
- `team.manage`
- `client.read`
- `client.create`
- `client.update`
- `meeting.read`
- `meeting.create`
- `meeting.update`
- `requisition.read`
- `requisition.create`
- `requisition.update`
- `requisition.assign`
- `candidate.read`
- `candidate.create`
- `candidate.update`
- `candidate.upload_document`
- `candidate.transition_stage`
- `candidate.run_duplicate_check`
- `dashboard.read_executive`
- `dashboard.read_business`
- `dashboard.read_delivery`
- `dashboard.read_recruiter`
- `dashboard.read_my_work`

## MVP Routing Guidance

### Platform Admin

- default landing: executive dashboard

### Operations Admin

- default landing: operations setup or delivery support dashboard

### Business Lead

- default landing: business dashboard

### Client Manager

- default landing: account dashboard or clients list

### Delivery Lead

- default landing: delivery dashboard

### Recruiter

- default landing: my work dashboard

### Sourcing Support

- default landing: sourcing queue or my work dashboard

### Reviewer

- default landing: assigned review inbox

### External User

- default landing: shared review inbox

## Implementation Notes

- backend authorization must be server-side and scope-aware
- frontend hiding is helpful but never sufficient
- customer titles should be rendered in UI, but permission checks must rely on stable product role codes
- every list endpoint should automatically filter records to the caller’s allowed scope
