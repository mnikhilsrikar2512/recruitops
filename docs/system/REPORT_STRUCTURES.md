# Recruitment System Report Structures

This document defines the improved report structures for the recruitment system.

The goal is to move away from a single flat tracker and instead create:

- executive-friendly summaries
- operational team review reports
- structured candidate movement details
- decision-oriented reports for `Admin`, `Manager`, `HR`, and `Recruiter`

## 1. Why The Existing Weekly Table Is Not Enough

The current weekly report format is useful as a raw tracker, but it is not strong enough as a management report because:

- summary and detailed rows are mixed together
- recruiter performance is not separated clearly
- internal and external hiring logic are not separated
- no pipeline aging or bottleneck section exists
- rejection trends are not easy to review
- action items for next week are not visible
- leadership must read every row to understand performance

Because of this, the system should generate reports in multiple layers.

## 2. Reporting Design Principles

- show summary first, detail later
- separate KPI view from transaction-level rows
- separate internal hiring logic from external hiring logic
- show recruiter, HR, manager, location, and client performance clearly
- always include blocker and action sections
- keep candidate detail tables available, but never use them as the only report view

## 3. Weekly Report Structure

The weekly report should be generated in 5 sections.

## Section A. Weekly Executive Summary

Purpose:

- give `Admin` and `Manager` a fast overview of the week

Recommended fields:

- Reporting week
- Location
- Hiring type split: `Internal`, `External`
- Total active requisitions
- New requisitions opened this week
- Requisitions closed this week
- Total candidate profiles added
- Total profiles screened
- Total profiles escalated to HR
- Total profiles escalated to client
- Total internal-side rejects
- Total client-side rejects
- Total interviews scheduled
- Total offers released
- Total joinings
- Total overdue requisitions
- Total overdue follow-ups
- Total blocked requisitions

Recommended display:

- KPI cards
- location comparison strip
- trend arrows vs previous week

## Section B. Weekly Recruiter Performance

Purpose:

- show how each recruiter performed during the week

Recommended columns:

- Recruiter name
- Location
- Assigned HR
- Active requisitions worked
- Profiles sourced
- Profiles escalated to HR
- Profiles escalated to client
- Internal hiring call count
- Internal-side rejects
- Client-side rejects
- Interviews generated
- Offers influenced
- Joinings influenced
- Pending active profiles
- Update submission compliance
- Major blocker
- Manager or HR remark

Important rule:

- For `External` hiring, focus on profiles escalated to clients rather than recruiter call count
- For `Internal` hiring, include recruiter call count and escalations

Recommended display:

- structured table with totals row
- color-coded performance bands

## Section C. Weekly Candidate Movement Report

Purpose:

- preserve transaction-level candidate tracking in a cleaner format

Recommended columns:

- Movement date
- Recruiter name
- HR owner
- Candidate name
- Client name
- End client name if applicable
- Role or position
- Hiring type: `Internal` / `External`
- Employment type: `Contract` / `Permanent`
- Current stage
- Stage update type
- Internal screening result
- Client feedback result
- Interview round
- Interview mode
- Offer status
- Date of joining
- Profile age
- Duplicate acknowledged by client: `Yes` / `No`
- Remarks

Better replacements for the current table:

- replace `Status` with `Current stage`
- replace `Internal screen Reject` with `Internal screening result`
- replace `Client reject` with `Client feedback result`
- replace `L1`, `L2` with `Interview round`
- add `Hiring type`
- add `HR owner`
- add `Profile age`
- add `Duplicate acknowledged by client`

## Section D. Weekly Rejection And Bottleneck Analysis

Purpose:

- help management understand where conversions are breaking

Recommended blocks:

- Top internal rejection reasons
- Top client rejection reasons
- Requisitions with highest profile drop-off
- Candidates stuck in stage beyond SLA
- Pending feedback items
- Duplicate profile acknowledgements by client
- Low-conversion roles

Recommended metrics:

- Submission to screening ratio
- Screening to client escalation ratio
- Client escalation to interview ratio
- Interview to offer ratio
- Offer to join ratio

## Section E. Weekly Action Plan

Purpose:

- convert report findings into next-step execution

Recommended fields:

- Issue
- Owner
- Priority
- Action required
- Target completion date
- Escalation required: `Yes` / `No`
- Admin or Manager remark

## 4. Monthly Report Structure

Monthly reports should be more strategic than weekly reports.

The monthly report should be generated in 6 sections.

## Section A. Monthly Leadership Summary

Purpose:

- give `Admin` leadership-level monthly visibility

Recommended fields:

- Reporting month
- Total locations active
- Total internal requisitions
- Total external requisitions
- Total closures
- Total offers
- Total joinings
- Total lost mandates
- Total active clients
- Total new clients added
- Total blocked requisitions
- Total SLA breaches
- Overall closure trend vs previous month

Recommended display:

- executive scorecard
- month-over-month trend view

## Section B. Monthly Location Performance

Purpose:

- compare location performance cleanly

Recommended columns:

- Location
- Manager
- Total requisitions
- Total closures
- Total joinings
- Active recruiters
- Active HR users
- Profiles added
- Profiles escalated to client
- Internal reject count
- Client reject count
- SLA breach count
- Weekly report compliance
- Monthly performance rating

## Section C. Monthly Role-Wise Productivity

Purpose:

- compare Managers, HRs, and Recruiters at a monthly level

Recommended subsections:

### Manager monthly view

- Meetings completed
- Mandates received
- Active clients handled
- Team closure count
- Client follow-up compliance
- Lost mandate reasons

### HR monthly view

- Requisitions owned
- Profiles screened
- Profiles escalated to client
- Feedback closure rate
- Interview coordination count
- Offer closure count
- Requisition aging quality

### Recruiter monthly view

- Profiles sourced
- Profiles escalated to HR
- Profiles escalated to client
- Internal call count for internal hiring
- Portal usage contribution
- Update submission compliance
- Pipeline support contribution

## Section D. Monthly Funnel And Conversion Analysis

Purpose:

- show conversion quality from source to joining

Recommended stages:

- Requisition open
- Profiles sourced
- Profiles screened
- Profiles escalated to client
- Client shortlisted
- Interviews completed
- Offers released
- Joinings completed

Recommended cuts:

- location-wise
- role-wise
- client-wise
- internal vs external

## Section E. Monthly Exceptions, Risks, And Quality

Purpose:

- surface operational quality concerns

Recommended sections:

- Candidates expired after 1 month
- Requisitions breaching SLA
- Repeat rejection patterns
- Portal under-utilization
- Missed follow-ups
- Missing daily update trends
- Data completeness issues
- Duplicate candidate conflicts

## Section F. Monthly Recommendations

Purpose:

- help leadership decide on changes required

Recommended blocks:

- Process changes required
- Team support required
- Locations needing intervention
- Clients needing escalation
- Roles needing sourcing correction
- Hiring bottlenecks needing policy change

## 5. Role-Wise Report Structures

Each role should receive a different report view even if the system uses the same data.

## Admin Report

Purpose:

- executive oversight and decision-making

Admin report should include:

- company-wide KPI summary
- location comparison
- manager, HR, and recruiter performance summary
- SLA breaches
- bottleneck analysis
- blocked requisitions
- client mandate trends
- recommendations and action list

Admin report format:

- summary cards
- comparison tables
- conversion charts
- exception list
- action tracker

## Manager Report

Purpose:

- location delivery review and client oversight

Manager report should include:

- location KPI summary
- active client and mandate view
- recruiter and HR performance
- meeting outcomes
- escalated profiles count
- pending client feedback
- difficult or aging requisitions
- action list for next week

Manager report format:

- location dashboard summary
- team table
- client-wise delivery table
- pending decision queue

## HR Report

Purpose:

- operational control of owned requisitions and candidate flow

HR report should include:

- requisitions owned
- profiles screened
- profiles escalated to client
- screening pass and fail split
- pending feedback items
- interview pipeline
- overdue requisitions
- recruiter support summary
- blocker list

HR report format:

- operational KPI row
- requisition table
- candidate movement table
- recruiter support table
- blocker and next-step section

## Recruiter Report

Purpose:

- sourcing productivity and pending action control

Recruiter report should include:

- requisitions worked
- profiles sourced
- profiles escalated to HR
- profiles escalated to client
- internal call count where relevant
- portal usage summary
- duplicate flags found
- pending profiles requiring update
- overdue priorities
- blocker list

Recruiter report format:

- KPI strip
- requisition worklist
- profile movement table
- portal usage and compliance section

## 6. Better Weekly Table Design

If a tabular report is still needed for export, it should be redesigned.

## Improved weekly detail table

Recommended attributes:

- Date
- Recruiter Name
- HR Owner
- Candidate Name
- Client Name
- End Client
- Role
- Hiring Type
- Employment Type
- Current Stage
- Internal Screening Result
- Client Feedback Result
- Interview Round
- Interview Mode
- Offer Status
- Date of Joining
- Profile Age
- Duplicate Acknowledged
- Remarks

This is better than the current design because it:

- removes unclear stage-only columns
- keeps internal and external context visible
- adds ownership clarity
- supports duplicate and aging analysis
- makes reporting more usable for review

## 7. Recommended Visual Design

The reports should not look like plain spreadsheets inside the product.

Recommended structure:

### Page 1

- title and reporting period
- KPI summary cards
- trend comparison
- location or team snapshot

### Page 2

- role-wise productivity tables

### Page 3

- candidate movement detail table

### Page 4

- rejection, bottleneck, and risk analysis

### Page 5

- recommendations and next-step action list

Recommended visual elements:

- muted professional cards
- status chips
- stage color indicators
- recruiter and location comparison tables
- funnel visuals
- aging buckets

## 8. System Recommendation

The system should not use only one weekly or monthly table.

Instead, it should generate:

1. `Executive Weekly Report`
2. `Recruiter Performance Weekly Report`
3. `Candidate Movement Weekly Report`
4. `Rejection And Bottleneck Weekly Report`
5. `Executive Monthly Report`
6. `Location And Team Monthly Performance Report`
7. `Role-Wise Monthly Productivity Report`

## 9. Final Conclusion

Yes, the system can produce much better reports than the current weekly table format.

The better design is:

- summary first
- role-wise analysis second
- candidate movement detail third
- bottleneck and action sections last

This will make the reports more professional, more useful for leadership, and much easier for operations teams to act on.
