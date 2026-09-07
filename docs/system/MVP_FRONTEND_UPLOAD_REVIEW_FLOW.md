# MVP Frontend Upload Review Flow

## Purpose

This document defines the exact working flow to follow after the new foundation and MVP frontend uploads arrive.

It exists so the team can move directly from upload to comparison to selection to real frontend build without confusion.

Use this together with:

- `docs/system/CURRENT_FRONTEND_ARTIFACT_BASELINE.md`
- `docs/system/MVP_FRONTEND_COMPARISON_AND_SELECTION_FRAMEWORK.md`
- `docs/system/MVP_FRONTEND_SELECTION_MATRIX.md`
- `frontend-mvp/incoming/README.md`

## Important Rule

Do not build the real MVP frontend from the legacy prototype in `frontend/`.

Use the legacy prototype only as reference.

The real build must happen in `frontend-mvp/`.

## Working Flow

### Step 1. Upload Intake

Place all new uploads in:

- `frontend-mvp/incoming/`

Recommended grouping:

- foundation files
- MVP page files
- shared styling files
- component reference files

### Step 2. Upload Inventory

For every uploaded file:

- record filename
- identify whether it is foundation or page-specific
- map it to the target MVP page or foundation area

### Step 3. Legacy Comparison

Compare each uploaded item against:

- `docs/system/CURRENT_FRONTEND_ARTIFACT_BASELINE.md`

Check:

- what the legacy reference does better
- what the new upload does better
- what should not be carried forward

### Step 4. Product-Fit Check

Validate each compared item against:

- configurable-role model
- location-safe workflow
- client and requisition flow
- candidate and pipeline flow
- reporting and dashboard fit
- MVP scope only

### Step 5. Selection Decision

Use:

- `docs/system/MVP_FRONTEND_SELECTION_MATRIX.md`

Choose one:

- `Adopt New`
- `Adopt New With Legacy Ideas`
- `Adopt Mixed`
- `Legacy Idea Only`
- `Reject`

### Step 6. Selected Output Capture

Place the chosen direction notes or selected artifacts in:

- `frontend-mvp/selected/`

### Step 7. Real Frontend Build Start

Only after selection is complete:

- start building in `frontend-mvp/app/`

Use the existing frontend planning pack as the implementation contract.

## Review Questions For Every Uploaded Page

- does it match a current MVP page?
- does it fit configurable roles?
- does it avoid future-extension clutter?
- is the information hierarchy clearer?
- is the action placement better?
- is it easier to componentize?
- is it easier to route cleanly?

## Final Rule

The team is ready to build the real frontend only when:

- uploads are inventoried
- page decisions are recorded
- selected direction is clear

Until then, the team is still in review mode.
