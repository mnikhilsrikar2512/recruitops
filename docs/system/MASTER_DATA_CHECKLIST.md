# Master Data Checklist

This file defines the reference data we should confirm before seeding the `recruitment_system` MSSQL database.

The goal is to:
- keep reports clean and structured
- reduce invalid free-text entries
- avoid rework after API development starts
- ensure frontend dropdowns and filters match backend master data

## How To Use This File

For each section:
- `Predefine Now` means we can safely seed it early
- `Confirm With Business` means we should collect final values before seeding
- `Optional Later` means we can add it after the first release without breaking the core system

---

## 1. Organization Masters

### 1.1 Role Hierarchy
Status: `Predefine Now`

Confirmed hierarchy:
- `Admin`
- `Manager`
- `HR`
- `Recruiter`

Notes:
- This hierarchy should drive RBAC, sidebar visibility, approvals, report visibility, and workflow ownership.

### 1.2 Locations
Status: `Confirmed For Initial Seed`

Need:
- location code
- location name
- city
- state
- country
- location status: `Active`, `Inactive`
- default manager

Confirmed cities for day one:
- `Hyderabad`
- `Vijayawada`
- `Vizag`

Confirmed initial location names:
- `Hyderabad Location`
- `Vijayawada Location`
- `Vizag Location`

Confirmed initial location codes:
- `HYD01`
- `VJW01`
- `VZG01`

Confirmed structure notes:
- one city can optionally have multiple locations
- the system should support both `Legal Entity` and `Operational Team` mapping options at location level

Recommended structure:
- `location_code`
- `location_name`
- `city`
- `state`
- `country`
- `is_active`

### 1.3 Departments / Business Units
Status: `Confirmed`

Useful mainly for internal hiring.

Confirmed values:
- `Engineering`
- `Sales`
- `HR`
- `Finance`
- `Operations`

Questions to confirm:
- Do internal requisitions belong to departments, business units, or both?

### 1.4 Work Locations
Status: `Confirmed For Initial Seed`

Confirmed work modes:
- `Onsite`
- `Hybrid`
- `Remote`

Confirmed countries in initial rollout:
- `India`
- `USA`

Confirmed city/location values so far:
- `Hyderabad`
- `Vijayawada`
- `Vizag`

Confirmed scope:
- only India cities will be seeded initially
- USA remains an available country for future company/entity expansion, but no USA city master data will be seeded now

Recommendation:
- store `city/location`
- store `work_mode` separately as `Onsite`, `Hybrid`, `Remote`

### 1.5 Location Mapping Type
Status: `Confirmed`

Values:
- `Legal Entity`
- `Operational Team`
- `Both`

Notes:
- This should be stored as a location classification option so locations can represent either structure cleanly.

---

## 2. Hiring Process Masters

### 2.1 Hiring Type
Status: `Predefine Now`

Values:
- `Internal`
- `External`

Notes:
- Internal and external reporting logic is different.
- External reports should prioritize profile escalations to client.
- Internal reports should include call counts and profile escalations.

### 2.2 Employment Type
Status: `Predefine Now`

Values:
- `Permanent`
- `Contract`
- `Contract to Hire`

### 2.3 Requisition Priority
Status: `Predefine Now`

Values:
- `Low`
- `Medium`
- `High`
- `Critical`

Notes:
- JS can suggest this from end date, openings, and client round requirements.

### 2.4 Requisition Status
Status: `Predefine Now`

Recommended values:
- `Draft`
- `Pending Approval`
- `Approved`
- `Active`
- `On Hold`
- `Partially Closed`
- `Closed`
- `Cancelled`

### 2.5 Requisition Source
Status: `Predefine Now`

Values:
- `Internal Business Team`
- `Direct Client`
- `Client via End Client`

Notes:
- This aligns with your rule that a direct client can optionally have multiple end clients.

### 2.6 Client Round Requirement
Status: `Predefine Now`

Values:
- `Required`
- `Optional`
- `Not Required`

### 2.7 Approval Status
Status: `Predefine Now`

Values:
- `Pending`
- `Approved`
- `Rejected`
- `Returned For Changes`

---

## 3. Client And Relationship Masters

### 3.1 Client Type
Status: `Predefine Now`

Values:
- `Direct Client`
- `End Client`

### 3.2 Client Status
Status: `Predefine Now`

Values:
- `Active`
- `Inactive`
- `Prospect`
- `Blocked`

### 3.3 Client Relationship Model
Status: `Predefine Now`

Rules already agreed:
- A direct client may have zero, one, or many end clients.
- End clients are optional.

### 3.4 Contact Designation Types
Status: `Optional Later`

Examples:
- `HR`
- `Hiring Manager`
- `Delivery Manager`
- `Talent Acquisition`
- `Vendor Manager`
- `Operations Lead`

---

## 4. Candidate Masters

### 4.1 Candidate Status
Status: `Predefine Now`

Recommended values:
- `New`
- `Under Screening`
- `Submitted`
- `Shortlisted`
- `Interview In Progress`
- `Rejected`
- `Offered`
- `Joined`
- `Dropped`
- `Expired`

### 4.2 Candidate Lifecycle Rule
Status: `Predefine Now`

Confirmed business rule:
- candidate profile life = `30 days`

Recommendation:
- store `profile_expiry_date`
- calculate visibility and warnings in JS

### 4.3 Candidate Source
Status: `Predefine Now`

Values:
- `Naukri`
- `LinkedIn`
- `Referral`
- `Internal Database`
- `Career Portal`
- `Consultant Walk-in`
- `Job Board Other`
- `Manual Entry`

### 4.4 Duplicate Status
Status: `Predefine Now`

Values:
- `No Duplicate Found`
- `Potential Duplicate`
- `Confirmed Duplicate`
- `Client Marked Duplicate`

Notes:
- This supports the case where a client says the same profile already came from another location or vendor.

### 4.5 Resume Parse Status
Status: `Predefine Now`

Values:
- `Pending`
- `Parsed`
- `Needs Review`
- `Failed`

### 4.6 Candidate Document Types
Status: `Predefine Now`

Core values:
- `Resume`
- `Payslip`
- `Relieving Letter`
- `Offer Letter`
- `Experience Letter`
- `Government ID`
- `Education Certificate`
- `Bank Statement`
- `Other`

### 4.7 Notice Period
Status: `Confirmed`

Confirmed values:
- `Immediate`
- `15 Days`
- `30 Days`
- `45 Days`
- `60 Days`
- `90 Days`
- `Negotiable`

### 4.8 Employment Gap Brackets
Status: `Predefine Now`

Recommended values:
- `No Gap`
- `Up to 2 Months`
- `2 to 6 Months`
- `6 to 12 Months`
- `Above 12 Months`

Notes:
- This supports client requirements such as allowing only a certain gap range.

---

## 5. Screening, Rejection, And Interview Masters

### 5.1 Screening Outcome
Status: `Predefine Now`

Values:
- `Passed`
- `Rejected`
- `On Hold`
- `Needs Clarification`

### 5.2 Rejection Category
Status: `Predefine Now`

Values:
- `Internal Side Rejection`
- `Client Side Rejection`
- `Candidate Dropped`
- `Duplicate`
- `Position Closed`

### 5.3 Internal Rejection Reasons
Status: `Confirmed`

Confirmed values:
- `Skill Mismatch`
- `Communication Gap`
- `Experience Mismatch`
- `Notice Period Too Long`
- `Compensation Mismatch`
- `Missing Mandatory Document`
- `Employment Gap Not Acceptable`
- `Location Constraint`
- `Stability Concern`
- `Incomplete Profile`

### 5.4 Client Rejection Reasons
Status: `Confirmed`

Confirmed values:
- `Skill Mismatch`
- `Budget Mismatch`
- `Duplicate`
- `Overqualified`
- `Underqualified`
- `Notice Period Too Long`
- `Domain Mismatch`
- `Communication Gap`
- `Position On Hold`
- `Role Closed`

### 5.5 Interview Round Type
Status: `Predefine Now`

Values:
- `Internal Screening`
- `Client Round`
- `L1`
- `L2`
- `L3`
- `Final HR`
- `Managerial`

### 5.6 Interview Mode
Status: `Predefine Now`

Values:
- `Virtual`
- `In Person`
- `Telephonic`
- `Panel`
- `Assignment`

### 5.7 Interview Outcome
Status: `Predefine Now`

Values:
- `Scheduled`
- `Completed`
- `Selected`
- `Rejected`
- `Rescheduled`
- `No Show`
- `Awaiting Feedback`

### 5.8 Feedback Owner
Status: `Predefine Now`

Confirmed business rule:
- Recruiters are not responsible for feedback handling.
- Feedback is handled by `HR` or `Manager`.

---

## 6. Meeting And Follow-Up Masters

### 6.1 Meeting Type
Status: `Predefine Now`

Values:
- `Client Introduction`
- `Requirement Discussion`
- `Follow-up`
- `Review Meeting`
- `Escalation Meeting`
- `Internal Review`

### 6.2 Meeting Attendance Status
Status: `Predefine Now`

Values:
- `Attended`
- `Did Not Attend`
- `Rescheduled`
- `Cancelled`

### 6.3 Meeting Outcome
Status: `Predefine Now`

Values:
- `Requirement Confirmed`
- `Pending Clarification`
- `Client Accepted`
- `Client Rejected`
- `No Decision`
- `Follow-up Required`
- `No Show`

### 6.4 Follow-Up Task Type
Status: `Predefine Now`

Values:
- `Send Profiles`
- `Clarify Requirement`
- `Schedule Next Meeting`
- `Collect Feedback`
- `Close Requirement`
- `Re-open Search`

---

## 7. Portal And Account Usage Masters

### 7.1 Portal Names
Status: `Confirmed`

Values:
- `Naukri`
- `LinkedIn`
- `Indeed`
- `Foundit`
- `Internal Database`

### 7.2 Portal Access Type
Status: `Predefine Now`

Values:
- `Full Access`
- `Scheduled Slot Access`

Notes:
- Scheduling remains optional as requested.

### 7.3 Portal Slot Status
Status: `Predefine Now`

Values:
- `Available`
- `Reserved`
- `In Use`
- `Completed`
- `Missed`
- `Cancelled`

---

## 8. Reporting Masters

### 8.1 Report Type
Status: `Predefine Now`

Values:
- `Daily Update`
- `Weekly Report`
- `Monthly Report`

Notes:
- System should capture daily updates and generate weekly/monthly rollups where possible.

### 8.2 Report Scope
Status: `Predefine Now`

Values:
- `Recruiter`
- `HR`
- `Manager`
- `Location`
- `Client`
- `Organization`

### 8.3 Report Status
Status: `Predefine Now`

Values:
- `Draft`
- `Generated`
- `Submitted`
- `Reviewed`
- `Locked`

### 8.4 Weekly Report Columns
Status: `Predefine Now`

Confirmed core attributes:
- `Date`
- `Recruiter Name`
- `Candidate Name`
- `Client Name`
- `Role`
- `Contract/Permanent`
- `Status`
- `Internal Screen Reject`
- `Client Reject`
- `L1`
- `L2`
- `Interview Mode`
- `Offer Letter`
- `Date Of Joining`
- `Remarks`

Recommendation:
- keep this tabular report
- also add summary blocks above it for:
  - total profiles submitted
  - total escalated to client
  - internal rejects
  - client rejects
  - offers
  - joins
  - active pipeline
  - overdue requisitions

---

## 9. Notification Masters

### 9.1 Notification Type
Status: `Predefine Now`

Values:
- `Approval Pending`
- `Requisition Assigned`
- `Interview Scheduled`
- `Feedback Pending`
- `Portal Slot Reminder`
- `Candidate Expiry Warning`
- `Report Submission Reminder`
- `Meeting Follow-up Reminder`
- `Duplicate Warning`
- `Profile Escalation Update`

### 9.2 Notification Priority
Status: `Predefine Now`

Values:
- `Low`
- `Normal`
- `High`
- `Critical`

### 9.3 Delivery Channel
Status: `Optional Later`

Possible values:
- `In App`
- `Email`
- `SMS`
- `WhatsApp`

Notes:
- For now, JS/local notification behavior can cover the first frontend phase.

---

## 10. Skills And Requirement Masters

### 10.1 Skill Categories
Status: `Confirmed`

Confirmed categories:
- `Programming`
- `Frontend`
- `Backend`
- `Database`
- `Cloud`
- `DevOps`
- `Testing`
- `ERP`
- `Analytics`
- `Support`

### 10.2 Skill Priority
Status: `Predefine Now`

Values:
- `Mandatory`
- `Important`
- `Good To Have`

### 10.3 Requirement Constraint Types
Status: `Predefine Now`

Values:
- `Max Notice Period`
- `Allowed Employment Gap`
- `Mandatory Documents`
- `Minimum Experience`
- `Maximum Budget`
- `Location Constraint`
- `Certification Required`

---

## 11. Audit And Compliance Masters

### 11.1 Audit Event Type
Status: `Predefine Now`

Values:
- `User Created`
- `User Updated`
- `User Deleted`
- `Role Changed`
- `Requisition Approved`
- `Requisition Rejected`
- `Candidate Submitted`
- `Candidate Rejected`
- `Report Locked`
- `Portal Slot Assigned`

### 11.2 Audit Severity
Status: `Predefine Now`

Values:
- `Info`
- `Warning`
- `Critical`

---

## 12. Seeding Plan

### Seed First
- roles
- permissions
- role-permission mappings
- hiring types
- employment types
- requisition statuses
- candidate statuses
- duplicate statuses
- interview modes
- interview outcomes
- report types
- report statuses
- portal names
- notification types
- document types
- rejection categories

### Seed After Business Confirmation
- cities
- locations
- departments
- client designation types
- internal rejection reasons
- client rejection reasons
- work locations
- skill categories

### Seed Later As Transaction Data
- users
- clients
- end clients
- requisitions
- candidates
- interviews
- meetings
- reports

---

## 13. Decisions We Already Know

These are already confirmed from our discussions:
- role hierarchy is `Admin -> Manager -> HR -> Recruiter`
- end clients are optional
- one direct client can have multiple end clients
- portal scheduling is optional
- candidate profile life is `1 month`
- recruiters are not responsible for feedback handling
- feedback is handled by `HR` or `Manager`
- external hiring reports should focus on profiles escalated to clients
- internal hiring reports should include call counts and escalations
- daily updates should feed weekly and monthly reports
- not all fields should be mandatory
- location cities for day one are `Hyderabad`, `Vijayawada`, and `Vizag`
- initial location names are `Hyderabad Location`, `Vijayawada Location`, and `Vizag Location`
- initial location codes are `HYD01`, `VJW01`, and `VZG01`
- internal departments are `Engineering`, `Sales`, `HR`, `Finance`, and `Operations`
- work modes are `Onsite`, `Hybrid`, and `Remote`
- portal list includes `Naukri`, `LinkedIn`, `Indeed`, `Foundit`, and `Internal Database`
- notice period options are confirmed
- employment gap brackets are confirmed
- skill category reporting is enabled
- company types will use the recommended structure
- initial countries are `India` and `USA`
- only India city masters will be seeded initially
- one city can optionally support multiple locations
- location mapping should support `Legal Entity`, `Operational Team`, and `Both`

---

## 14. What I Recommend We Finalize Next

The remaining items can be refined later, but they do not block initial master data seeding:
- additional location records beyond the first 3
- USA city masters when USA locations/entities go live
- location-to-company mapping rules once multiple company entities are active

Once these are confirmed, we should create:
1. `002_seed_master_data.sql`
2. `003_seed_permissions_and_role_mappings.sql`
3. `004_seed_sample_business_data.sql`
