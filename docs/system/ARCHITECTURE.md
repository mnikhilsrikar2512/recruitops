# Recruitment System Architecture

## Important Note

This architecture document is aligned to the universal product model introduced on August 13, 2026.

Use `docs/system/UNIVERSAL_PRODUCT_ARCHITECTURE.md` as the primary source of truth for:

- universal roles
- configurable hierarchy
- module boundaries
- execution priorities

## System Summary

This system is a configurable recruitment operating platform designed to work for multiple business models, including:

- staffing and recruitment agencies
- in-house talent acquisition teams
- RPO and delivery partners
- multi-location recruiting businesses

The platform should support both:

1. internal hiring workflows
2. external client-driven hiring workflows

## Core Architecture Principle

The system must not hard-code one company-specific hierarchy.

Instead, it must model:

- permission roles
- business titles
- reporting relationships
- visibility scopes
- workflow ownership

## Core Actor Types

The product should be built around universal capability groups:

- `platform_admin`
- `operations_admin`
- `business_lead`
- `client_manager`
- `delivery_lead`
- `recruiter`
- `sourcing_support`
- `reviewer`
- `external_user`

Customer-facing titles such as `Director`, `BDM`, `Account Manager`, `Lead Recruiter`, `Assistant Recruiter`, `Recruiter`, `Talent Partner`, or `Hiring Manager` should be configuration, not product logic.

## Core Business Flows

### Internal Hiring Flow

1. a hiring need is raised
2. the requisition is created and assigned
3. a delivery owner allocates work
4. sourcing and candidate intake begin
5. candidates are screened and progressed
6. interviews, offers, and joins are tracked
7. dashboards and reports use the operational data

### External Hiring Flow

1. a prospect or client interaction is logged
2. meeting and follow-up activity is recorded
3. a client requirement is converted into a requisition
4. a delivery owner allocates the requisition
5. recruiters and sourcing support work the role
6. candidate submissions and feedback are tracked
7. interviews, offers, and placements are tracked
8. account and delivery reporting use the operational data

## Functional Domains

### Identity And Access

- authentication
- permission roles
- business titles
- visibility scopes
- audit logs

### Organization And Ownership

- locations
- teams
- departments
- reporting relationships
- record ownership
- workflow assignments

### CRM And Delivery

- prospects and clients
- meetings and follow-ups
- requisitions
- candidates
- submissions
- interviews
- placements and joins

### Analytics And Governance

- executive dashboards
- delivery dashboards
- account and client performance
- approvals
- audit and exception reporting

## Recommended Backend Boundaries

- `auth`
- `permissions`
- `org`
- `users`
- `clients`
- `activities`
- `requisitions`
- `candidates`
- `delivery`
- `reports`
- `analytics`
- `audit`

## Recommended Foundational Tables

- `permission_roles`
- `permissions`
- `permission_role_permissions`
- `business_titles`
- `users`
- `user_sessions`
- `password_reset_tokens`
- `user_reporting_relationships`
- `teams`
- `team_memberships`
- `locations`
- `business_units`
- `user_scope_assignments`
- `clients`
- `client_contacts`
- `meetings`
- `activities`
- `requisitions`
- `requisition_assignments`
- `candidates`
- `candidate_documents`
- `candidate_duplicate_checks`
- `candidate_stage_history`
- `interview_rounds`
- `approval_requests`
- `notifications`
- `audit_logs`

## Reporting Dimensions

Every important report should be filterable by:

- date range
- location
- business unit
- team
- permission role
- business title
- owner
- hiring type
- client company
- requisition status

## Suggested Priority Rules

- show overdue follow-ups before general activity
- show aging requisitions before fresh requisitions
- show SLA-risk work before low-risk work
- show account-level blockers before healthy accounts
- show delivery bottlenecks before summary metrics
- for external hiring, emphasize submissions, interviews, and client responsiveness
- for internal hiring, emphasize velocity, quality, and close-rate
