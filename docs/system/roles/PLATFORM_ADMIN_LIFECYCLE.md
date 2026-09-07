# Platform Admin Lifecycle

## Purpose

The `platform_admin` role owns tenant-wide governance, security, configuration, and high-level operational control.

This role is responsible for making sure the system is correctly configured, users have the right access, and sensitive actions remain auditable.

## Typical Customer Title Mappings

- Platform Admin
- System Administrator
- Tenant Owner
- Super Admin
- Enterprise Admin

## Main Responsibilities

- configure the tenant
- manage users and access
- define locations, teams, and role setup
- review sensitive changes and exceptions
- monitor executive dashboards
- maintain policy and governance controls

## Primary Records Owned Or Controlled

- users
- permission roles
- business titles
- locations
- teams
- visibility scopes
- sensitive approvals
- audit logs

## Daily Lifecycle

### Step 1. Review the executive control view

- open executive dashboard
- check active users, open requisitions, blocked work, and exceptions
- review critical operational warnings

### Step 2. Review access and user changes

- approve or execute user creation and deactivation
- review role, title, location, or scope changes
- verify that privileged access remains correct

### Step 3. Maintain org and master data

- create or update locations
- create or update teams
- maintain business titles and system role templates
- confirm reporting structures are valid

### Step 4. Review sensitive actions

- inspect credential resets
- inspect deactivations and reassignments
- inspect unusual exports or overrides once audit tooling exists

### Step 5. Review operational risk summary

- identify overloaded teams
- identify locations with low output or overdue work
- identify workflows that need process intervention

## Weekly Lifecycle

- review tenant-wide user and access integrity
- review location performance and delivery bottlenecks
- review open exception items
- review system adoption and data quality gaps
- validate whether any configuration changes are needed

## Monthly Lifecycle

- review executive productivity trends
- review location and team comparisons
- review audit and governance posture
- refine access policy where needed
- lock reporting or compliance periods if required later

## Key Screens And Views

- executive dashboard
- user administration
- location and team management
- role and permission management
- audit and exception views
- access review views

## Important Handoffs

- hands operational ownership to `operations_admin` for day-to-day setup tasks where allowed
- hands client-side work to `business_lead` and `client_manager`
- hands recruiting execution to `delivery_lead`

## Success Metrics

- correct access assignment rate
- low access-error incidents
- low unresolved exception count
- location and team configuration completeness
- auditability of sensitive changes

## MVP Expectations

For MVP, this role must be able to:

- create users
- assign permission roles and titles
- assign locations and teams
- reset credentials
- see executive dashboards
- enforce visibility and ownership rules
