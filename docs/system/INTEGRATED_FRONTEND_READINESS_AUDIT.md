# Integrated Frontend Readiness Audit

Last generated: August 20, 2026

> **Archived:** The original design-tool export folders and the one-shot build scripts below
> (`build_integrated_frontend.py`, `verify_frontend_integrity.py`,
> `smoke_integrated_frontend.mjs`, `check_frontend_readiness.py`) were removed after the
> integrated frontend was wired to the live FastAPI backend. This document is kept as a
> historical snapshot of the pre-API integration gate; use the backend test suite
> (`backend/scripts/run_tests_ci.sh`) and the live pages under `frontend/pages/` for
> current verification.

## Scope

This audit covers the frontend that was generated from the original design exports into the live routed frontend under `frontend/`.

Current generated inventory:

- Primary routed pages: `23`
- Overlay routed pages: `13`
- Total routed pages: `36`

## What Is Verified

- Shared shell consistency:
  - unified sidebar and topbar on routed app pages
  - shared context strip on every routed page
  - shared toast root on every routed page
- Overlay behavior:
  - blur/backdrop structure exists on routed overlays
  - overlay close pill exists and matches body-level close routing metadata
  - backdrop close target exists
  - in-surface close affordance exists
- Navigation and naming:
  - internal routed links resolve successfully
  - blocked legacy naming like `Jobs`, `Pipelines`, and `ATS` is rejected by the verifier
  - simplified overlay naming is reflected in shared chrome
- Lifecycle and runtime behavior:
  - login invalid, inactive, and success states
  - requisition-intake validation and success path
  - overlay close and cancel return behavior
  - exception-request submit path
  - mobile nav open and close behavior
- Validation safety:
  - explicit required-selector metadata is validated
  - malformed required-selector metadata is rejected
- API handoff support:
  - `frontend/route-manifest.json` is generated with route titles, sections, links, and overlay parent mappings

## Commands Used As Evidence

The original one-shot build/verify/smoke scripts were removed once the frontend was integrated with the live API:

```bash
# removed: python3 scripts/build_integrated_frontend.py
# removed: python3 scripts/verify_frontend_integrity.py
# removed: node scripts/smoke_integrated_frontend.mjs
# removed: python3 scripts/check_frontend_readiness.py
```

Current verification is the backend test suite plus serving `frontend/` and exercising the routed pages directly.

## Generated Handoff Artifacts

- `frontend/route-manifest.json`
  - machine-readable map of routed pages and overlays
  - useful for later API-wiring, route ownership, and adapter planning
- `docs/system/INTEGRATED_FRONTEND_READINESS_AUDIT.md`
  - human-readable snapshot of what is currently verified

## Readiness Interpretation

The frontend was in a strong pre-API state for the integrated scope at the time of this audit:

- route structure is consistent
- shared shell behavior is unified
- overlays behave like integrated product surfaces instead of isolated mockups
- key user flows now have repeatable browser evidence

## Residual Caution

These are not frontend integration blockers, but they should remain visible:

- The pages still use `cdn.tailwindcss.com`, which raises a warning during browser runs. This has not been treated as a functional regression for the current prototype gate.
- This audit proves frontend readiness for later API wiring, not that live backend integration is already complete.
- A broader feature-level frontend test pass is still the right next step before beginning API integration work.
