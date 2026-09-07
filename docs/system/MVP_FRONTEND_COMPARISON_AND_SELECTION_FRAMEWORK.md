# MVP Frontend Comparison And Selection Framework

## Purpose

This document defines how we will compare the incoming frontend uploads against the current artifact baseline and choose only the features that best fit this project.

It is the working decision framework for:

- foundation comparison
- page comparison
- feature selection
- flow selection
- keeping the new frontend aligned to the real MVP

Use this together with:

- `docs/system/CURRENT_FRONTEND_ARTIFACT_BASELINE.md`
- `docs/system/MVP_FRONTEND_BUILD_SEQUENCE_PACK.md`
- `docs/system/MVP_COMPONENT_AND_STATE_CONTRACT.md`
- `docs/system/MVP_ROUTE_AND_NAVIGATION_CONTRACT.md`

## Important Rule

We are not integrating the old frontend.

We are using:

- the current frontend artifacts as legacy reference
- the new uploaded foundation and MVP pages as the primary comparison input
- the planning pack as the source of product truth

The final frontend should be selected and built from:

- product fit
- workflow fit
- configurable-role fit
- MVP scope fit

not from whichever old page looks more complete.

## Comparison Inputs

Each comparison should use these three inputs:

### 1. Product Truth

This includes:

- working model
- modules and features
- use cases
- route and navigation contract
- component and state contract

### 2. Legacy Reference

This includes:

- current static frontend artifacts in `frontend/pages/`
- current shared CSS and JS reference assets

### 3. New Uploads

This includes:

- new foundation pages
- new MVP pages
- any new shared styling or layout files you upload

## Selection Priorities

When there is a conflict, choose in this order:

1. product truth and MVP working model
2. new upload that fits the working model best
3. legacy artifact idea only if it improves the chosen new version

## What “Best Fit” Means For This Project

A selected page or feature is a good fit only if it supports these rules:

- configurable roles instead of hard-coded operational roles
- location-safe operations
- client and requisition workflow clarity
- candidate duplicate-aware workflow
- recruiter-to-management pipeline visibility
- clean dashboard and reporting separation
- real MVP scope without future-extension clutter

## Comparison Criteria

Score each compared page or feature against these criteria:

### 1. MVP Relevance

Question:

- does this directly support a current MVP page or flow?

### 2. Working-Model Fit

Question:

- does this match the recruitment operating model we finalized?

### 3. Configurable-Role Fit

Question:

- does this avoid hard-coding specific business roles into the product behavior?

### 4. UI Clarity

Question:

- is the page easy to understand and navigate?

### 5. Action Clarity

Question:

- are the page actions obvious and correctly grouped?

### 6. Reusability

Question:

- can the layout or sections become reusable components in the real frontend architecture?

### 7. Scope Safety

Question:

- does it avoid bringing in non-MVP or future-extension clutter?

### 8. Buildability

Question:

- can this be implemented cleanly in the target frontend architecture we planned?

## Decision Outcomes

For each page or feature, choose one of these outcomes:

- `Adopt`
  Use the new uploaded version as the main direction
- `Adopt With Legacy Ideas`
  Use the new uploaded version, but borrow limited ideas from the legacy baseline
- `Keep Legacy Idea Only`
  The old version contains one useful idea, but not a full page direction
- `Reject`
  Does not fit the current product direction

## Comparison Sheet Structure

When the new uploads arrive, compare them using these columns:

- MVP page name
- legacy reference file
- new upload file
- compared feature or section
- what works better in the legacy version
- what works better in the new version
- final selected direction
- decision reason
- reusable component impact
- route or flow impact
- API or state impact

## Page-Level Comparison Order

Compare incoming uploads in this order:

1. foundation layouts
2. auth pages
3. admin setup pages
4. client pages
5. requisition pages
6. candidate pages
7. pipeline pages
8. daily update pages
9. dashboard and reporting pages
10. notifications and utility pages

## Feature Categories To Compare On Every Page

For each page, compare these feature categories:

- page layout
- header structure
- filter bar
- data table or board structure
- form section grouping
- primary actions
- secondary actions
- detail side panels or drawers
- empty state
- error state
- success state
- mobile or compact behavior if visible

## Features We Should Usually Prefer From Better Uploads

If the new uploads improve these areas, prefer them:

- clearer component structure
- cleaner information hierarchy
- less hard-coded role language
- better action grouping
- stronger form clarity
- better responsive behavior
- more reusable layout patterns

## Features We Should Usually Reject Even If They Look Good

Reject or de-prioritize features that:

- force a fixed hierarchy into the UI
- add approvals not in current MVP
- add portal-account complexity
- add settings extras outside MVP
- add role-specific dashboards that break configurable-role design
- make the page visually rich but operationally unclear

## Build Decision Rule

After comparison, the real frontend should be built from:

- selected layouts
- selected sections
- selected flow patterns
- selected component behavior

not by copying an uploaded page blindly.

## Immediate Next Step After Upload

Once you upload the new foundation and MVP pages, I should do this in order:

1. inventory the uploaded files
2. map each upload to the target MVP page
3. compare each against the legacy baseline
4. choose the winning features
5. produce a final selected frontend direction file
6. begin building the real frontend from the chosen direction

## Final Rule

The comparison is successful only if the chosen frontend direction is:

- clearer than the current legacy baseline
- aligned to the real MVP
- ready to be built into the target frontend architecture
