# MVP Frontend Selection Matrix

## Purpose

This document is the working selection sheet for the real MVP frontend.

Use it after the new foundation and MVP frontend pages are uploaded.

It should help us:

- compare legacy reference pages against new uploads
- choose the best features for each target MVP page
- record final selection decisions clearly
- move from comparison into real frontend build

Use this together with:

- `docs/system/CURRENT_FRONTEND_ARTIFACT_BASELINE.md`
- `docs/system/MVP_FRONTEND_COMPARISON_AND_SELECTION_FRAMEWORK.md`
- `docs/system/MVP_FRONTEND_IMPLEMENTATION_MATRIX.md`
- `docs/system/MVP_COMPONENT_AND_STATE_CONTRACT.md`

## Selection Rule

For each target MVP page:

- compare the current legacy reference
- compare the new uploaded version
- choose only the features that best fit the product
- record the final selected direction

Do not select a page only because it looks more polished.

Select it only if it is better for:

- MVP relevance
- configurable-role model
- clarity
- reusability
- buildability

## Decision Values

Use one of these:

- `Adopt New`
- `Adopt New With Legacy Ideas`
- `Adopt Mixed`
- `Legacy Idea Only`
- `Reject`

## Page Comparison Matrix

| Target MVP Page | Legacy Reference Files | New Upload Files | Best Legacy Ideas | Best New Ideas | Final Decision | Selected Features To Carry Forward | Features To Reject | Build Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Login` |  |  |  |  |  |  |  |  |
| `Access Denied` |  |  |  |  |  |  |  |  |
| `Role Dashboard` |  |  |  |  |  |  |  |  |
| `My Work Dashboard` |  |  |  |  |  |  |  |  |
| `Location Management` |  |  |  |  |  |  |  |  |
| `User Management` |  |  |  |  |  |  |  |  |
| `User Detail` |  |  |  |  |  |  |  |  |
| `Role Management` |  |  |  |  |  |  |  |  |
| `Client Directory` |  |  |  |  |  |  |  |  |
| `Client Detail` |  |  |  |  |  |  |  |  |
| `Requisition List` |  |  |  |  |  |  |  |  |
| `Requisition Intake` |  |  |  |  |  |  |  |  |
| `Requisition Detail` |  |  |  |  |  |  |  |  |
| `Candidate Profiles` |  |  |  |  |  |  |  |  |
| `Resume Upload And Review` |  |  |  |  |  |  |  |  |
| `Candidate Duplicate Review` |  |  |  |  |  |  |  |  |
| `Pipeline Board` |  |  |  |  |  |  |  |  |
| `Daily Updates Submission` |  |  |  |  |  |  |  |  |
| `Daily Updates Review` |  |  |  |  |  |  |  |  |
| `Notifications Center` |  |  |  |  |  |  |  |  |
| `Location Dashboard` |  |  |  |  |  |  |  |  |
| `Company Dashboard` |  |  |  |  |  |  |  |  |

## Foundation Comparison Matrix

| Foundation Area | Legacy Reference Files | New Upload Files | Best Legacy Ideas | Best New Ideas | Final Decision | Selected Direction | Build Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Auth Layout` |  |  |  |  |  |  |  |
| `App Shell Layout` |  |  |  |  |  |  |  |
| `Dashboard Layout` |  |  |  |  |  |  |  |
| `Management Layout` |  |  |  |  |  |  |  |
| `Detail Layout` |  |  |  |  |  |  |  |
| `Filter Bar` |  |  |  |  |  |  |  |
| `Table Shell` |  |  |  |  |  |  |  |
| `Dialog Shell` |  |  |  |  |  |  |  |
| `Drawer Shell` |  |  |  |  |  |  |  |
| `Status Chip System` |  |  |  |  |  |  |  |
| `KPI Card System` |  |  |  |  |  |  |  |
| `Empty/Error/Loading States` |  |  |  |  |  |  |  |
| `Action Bar Pattern` |  |  |  |  |  |  |  |

## Section-Level Comparison Checklist

For each compared page, review these sections:

- page header
- page summary area
- filters
- table or board structure
- form section grouping
- action placement
- drawers or dialogs
- empty state
- error state
- restricted state
- success state

## Feature Decision Checklist

Before finalizing any page, confirm:

- the selected version supports the MVP workflow
- the selected version does not hard-code the wrong hierarchy
- the selected version is easier to componentize
- the selected version fits the route and state contracts
- rejected ideas are noted so they do not return later by mistake

## Final Build Handoff Rule

The frontend build should start from this matrix only after:

- the new uploads are fully mapped
- each target page has a decision
- each foundation area has a decision

If those decisions are missing, the team is still in comparison mode, not build mode.
