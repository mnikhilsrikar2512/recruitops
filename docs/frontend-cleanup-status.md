# Frontend cleanup — status

Goal: no prototype leftovers in the product. Every screen a customer sees shows
their real data or an honest empty state, and every button does what it says.

## F.1 — done (this commit)

**Onboarding**
- The 12-step prototype wizard is gone (9 pages). It showed integrations as
  "Connected" that were never connected, and every new user's first login was
  sent into it.
- Replaced by a **setup checklist on Home**, shown to admins (`settings.update`)
  until they hide it. Items are worked out from the company's data, never ticked
  by hand: offices (optional), team, hiring stages, first client (optional),
  first requisition. API `GET /settings/setup-checklist`,
  `PUT /settings/setup-checklist/dismissed`; migration `029_setup_checklist.sql`
  (existing companies start dismissed).
- "Start free trial" / "Sign up" everywhere → `signup.html`. Marketing footer
  links → `legal.html`; dead `javascript:void(0)` nav links removed.
- The company's own stage list can now be edited (Admin → **Hiring Stages**,
  formerly "Stage Bucket Map"). Before, only per-client lists had an editor.

**Fake data removed** from ~45 pages (names, IDs, 2023 dates, US phone numbers,
fake select options, fake timelines). A browser check over all 93 app pages
finds no prototype text left.

**Screens that only pretended to work, now on the real API**
| Screen | Before | Now |
|---|---|---|
| Approval review drawer | Approve/Reject only showed a toast | Loads `/approvals/{id}`, decides via `/approvals/{id}/decide` |
| Deactivate user | Fake form, nothing called | `POST /users/{id}/deactivate` with hand-over owner, reason, confirmation |
| Reassignment review drawer | Fake counts and lists | Removed (deactivation hands work over itself) |
| User detail | Mostly fake profile | Real fields; Edit and Deactivate wired |
| Edit requisition | Form had no field ids; saving did nothing | Same form as New Requisition, pre-filled, PATCHes |
| Resume upload | "Uploaded" toast, no upload | Multipart `POST /candidates/{id}/upload` per file |
| Interviews | Fake calendar; no way to schedule | List from `/interviews/` + schedule form (`POST /interviews/`) |
| Interview detail | Fake page under the live card | Live card only |
| Meeting form | Fake attendees/requisitions; no client picker | Client, type, date/time, follow-up date, agenda |
| New follow-up | Never saved | Saved as a follow-up meeting |
| Assignment history, pipeline/stage history | Loader hooks missing → never showed data | Hooks added; live timeline |
| Daily update detail, daily updates review | Fake content; wrong field name | Real fields, counts and blockers |
| Delivery work queue | Fake rows | Open requisitions ranked overdue → priority → due date |
| Requisition detail | Fake KPIs, skills, activity | Real fields, skills, candidates, actions |
| Candidate screening | Fake match score | Real candidate + requirements; links to stage move, interview, AI screener |
| Offer form | US fields (401k, equity, USD) | CTC in INR first; only fields the API takes |
| Access denied / Not found | Fake request IDs, dead support links | Short honest pages |

**Small defects**
- Duplicate Logout in the sidebar; hard-coded "BN" initials.
- "Completion progress" bar on every form (filters, delete forms…): now opt-in,
  used only on New Requisition and Add Candidate.
- `pageHref()` added ".html" after a query string (`x.html?id=1.html`); this also
  broke the `next=` link from the legal-acceptance gate.
- Overlay layout code lifted a form's button row out of the `<form>`, so its
  submit button stopped submitting. It no longer does that.
- No inline `onclick`: a delegated `[data-history-back]` handler instead.

## F.2 — done
- The Tailwind Play CDN (a development tool that compiled CSS in every
  visitor's browser) is replaced by a compiled `shared/tailwind.css`, built
  from the same theme (`shared/tailwind.config.js`) by `npm run build`.
- Inter, Manrope and Material Symbols are self-hosted in `shared/fonts/`;
  pages no longer call Google Fonts (privacy, and a strict CSP in Phase 6).
- One asset version for every page: a hash of `shared/`, written by
  `scripts/stamp_assets.py` (part of `npm run build`).
- CI rebuilds and fails if the committed CSS/fonts/versions are stale.
- `server.js` serves `.woff2` (cached immutably in production).

**After changing any page or shared file:** `cd frontend && npm run build`, then commit.

## Backlog found during F.1 (not done)
- Money and dates are still formatted `en-US`/USD in a few renderers
  (`formatOfferMoney`, `formatOfferDate`); should follow the company's currency
  and `en-IN`.
- `routing.js` still guesses routes from button labels (prototype heuristic);
  `tables.js` "polishes" filter bars by rewriting them. Both are fragile.
- `api-client.js` is ~370 KB in one file; split by module.
- `npm audit` reports 7 issues in build-time dev dependencies only (Tailwind 3's
  toolchain); nothing ships to the browser. Review when moving to Tailwind 4.
- "Total users" and similar header counts were fake; a sweep for hard-coded
  counts is worth doing alongside the analytics pages.
- Home tiles are built from the permissions stored at sign-in and are not
  rebuilt after the background permission refresh.
