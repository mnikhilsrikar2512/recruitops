# System Improvements

This document strengthens the recruitment system beyond the base MVP and turns it into a more complete operations platform.

## 1. Stronger Operating Principles

The system should not only store recruitment data. It should actively improve execution quality.

### New principles

- Every important workflow should have an owner
- Every owner should have measurable targets
- Every delay should have a reason and escalation path
- Every meeting should create an outcome or a follow-up
- Every report should lead to a decision, not just data storage
- Every location should be compared on common metrics

## 2. Improved Role Model

The original RBAC is good, but we can make it more practical.

### Admin improvements

- Define company-wide targets by month and quarter
- Lock or reopen reporting periods
- Override location ownership in special cases
- Review audit logs for critical changes
- Approve location target revisions

### Manager improvements

- Approve external requisitions before HR starts work
- Review candidate submission quality for client-facing roles
- Escalate delayed client responses
- Approve weekly location report before it reaches Admin

### HR improvements

- Maintain sourcing activity discipline
- Record reason for every major stage change
- Request help from manager when requisition is blocked
- Submit exception reports for hard-to-fill roles

## 3. Approval Workflows

Approvals are missing in many MVP systems and become painful later.

### Add these approvals

- Internal requisition approval
- External requisition approval
- Target revision approval
- Offer approval
- Role closure approval
- Client mandate approval
- Report sign-off approval

### Approval states

- `draft`
- `pending-approval`
- `approved`
- `rejected`
- `sent-back-for-update`

## 4. Better External Hiring Lifecycle

External hiring should behave more like account management plus recruitment delivery.

### Add client lifecycle stages

- `lead`
- `contacted`
- `meeting-scheduled`
- `meeting-completed`
- `proposal-shared`
- `commercial-discussion`
- `mandate-received`
- `active-delivery`
- `on-hold`
- `closed-lost`
- `closed-won`

### Add external mandate fields

- Mandate type
- Service type
- Commercial terms
- Replacement window
- Client SLA
- Submission limit
- Interview turnaround expectation
- Billing trigger

## 5. Better Meeting Intelligence

Meetings should drive measurable business outcomes.

### Add meeting quality fields

- Meeting objective
- Prepared agenda
- Minutes of meeting
- Decision summary
- Confidence level
- Client urgency
- Commercial probability
- Requirement probability

### Add meeting performance analytics

- Meeting-to-proposal conversion
- Proposal-to-mandate conversion
- No-show trend by client
- Average follow-up turnaround
- Manager meeting productivity score

## 6. Better Requisition Controls

Not all requisitions are equal. The system should classify them better.

### Add requisition classifications

- Hiring type: `internal`, `external`
- Seniority: `entry`, `mid`, `senior`, `leadership`
- Criticality: `low`, `medium`, `high`, `critical`
- Difficulty: `easy`, `moderate`, `hard`
- Employment type: `full-time`, `contract`, `consultant`

### Add requisition guardrails

- Mandatory intake checklist
- Required salary or budget range
- Required must-have skills
- Required hiring manager or client point of contact
- Required SLA start date

## 7. Better Candidate Quality Management

Candidate tracking should include quality, not only movement.

### Add candidate quality features

- Candidate score
- Qualification checklist
- Duplicate detection rules
- Knockout criteria
- Notice period tracking
- Compensation expectation tracking
- Offer decline reasons
- Join drop-off reasons

### Add candidate risk flags

- Compensation mismatch
- Low response probability
- Competing offer
- Long notice period
- Skill mismatch
- Attendance concern

## 8. Better Reporting Discipline

Reports should be structured, reviewable, and actionable.

### Improve report system

- Draft and submit workflow
- Manager review comments
- Admin review comments
- Report version history
- Missed report escalation
- Locked month-end reporting
- Report quality score

### Add report sections

- Achievements
- Risks
- Blockers
- Escalations needed
- Planned actions
- Support required

## 9. Better KPI Framework

Current KPIs are useful, but we should make them sharper.

### Add operational KPIs

- Time in stage
- Submission-to-interview ratio
- Interview-to-offer ratio
- Offer-to-join ratio
- Requisition aging bucket
- Follow-up compliance rate
- Report submission compliance

### Add business KPIs

- Meeting-to-mandate conversion
- Mandate-to-closure conversion
- Client retention rate
- Repeat mandate rate
- Location revenue proxy for external hiring

### Add quality KPIs

- Candidate rejection due to mismatch
- Offer drop rate
- Join no-show rate
- Late feedback rate
- Data completeness rate

## 10. Better Alerts And Escalations

The system should push attention to issues early.

### Add escalation rules

- Escalate overdue follow-up after 48 hours
- Escalate requisition with no activity for 3 days
- Escalate client no-show after 2 consecutive meetings
- Escalate HR below 60 percent target attainment
- Escalate report not submitted by deadline
- Escalate candidate stuck in stage beyond SLA

## 11. Better Admin Control Center

Admin should not just see dashboards. Admin should be able to govern operations.

### Add Admin control features

- Company health score
- Location risk heatmap
- Manager effectiveness leaderboard
- HR workload balancing view
- Hard-to-fill role watchlist
- SLA breach center
- Audit event explorer
- Policy and template management

## 12. Templates And Playbooks

This is a big improvement area.

### Add standard templates

- Requisition intake template
- Meeting agenda template
- Meeting notes template
- Daily report template
- Weekly report template
- Monthly report template
- Interview scorecard template
- Offer approval template

### Add operating playbooks

- New client onboarding playbook
- Hard-to-fill role playbook
- Delayed client response playbook
- Offer follow-up playbook
- Join assurance playbook

## 13. Compliance And Auditability

Recruitment systems often become messy without traceability.

### Add compliance controls

- Record who changed what and when
- Track deletion and restoration events
- Retain report history
- Retain meeting history
- Retain candidate stage history
- Mask sensitive candidate data where needed

## 14. Data Quality And Master Data

Data quality directly affects reports.

### Add data quality rules

- Required fields by module
- Duplicate detection for candidates and clients
- Location ownership validation
- Invalid status transition prevention
- Closed requisition edit restriction
- Missing follow-up reminders

## 15. Future-Ready Additions

These are not needed for day one, but the architecture should allow them.

### Future enhancements

- Email integration
- Calendar integration
- Resume parsing
- AI-assisted report summaries
- AI-assisted meeting summaries
- Forecasting for location target achievement
- Client self-service portal
- Candidate self-service portal

## High-Impact Changes To Adopt Immediately

If we want the biggest improvement quickly, prioritize these:

1. Add approvals for requisitions, offers, and reports
2. Add external client lifecycle and mandate tracking
3. Add meeting quality and follow-up analytics
4. Add candidate quality and risk tracking
5. Add escalations for overdue actions and missed reports
6. Add templates and structured playbooks
