# Decisions — 2026-10-06 (owner answers to the execution plan's open inputs)

Supersedes the "pending" and "adopted on recommendation" rows of
`recruitops-production-readiness-execution-plan.md` §2.2–2.3 where they differ.

| ID | Question | Decision | Effect on the plan |
|---|---|---|---|
| I-5 | How existing offices map to companies | **A company is the tenant; it owns a head office (HO) plus branches in different states/locations, all managed by that company's admin.** Every office in the current dev DB belongs to one company. | Phase 2.2 backfill: one tenant for all existing branches/locations — no mapping file needed for dev. |
| I-6 | Is the Executive Connection data real? | **Made-up demo data.** | No PII review needed for the dev DB; still never copied to staging (D-12). |
| I-2 | Cloud | **Not decided.** | Stay provider-neutral: S3-compatible storage, Redis, env/secret-manager adapters. Docker images in Phase 6. |
| D-03 | Admin scope | **Control plane only.** Admin manages users, offices, roles, settings, approvals, reports; recruiting work needs an execution role. | Admin seed = PRD §3.2 Admin column; admin bypass removed (Phase 2.5–2.6). |
| D-04 | Cross-company candidate footprint | **A company admin sees only their own company's offices' data — never another company's.** | Footprint limited to the admin's own tenant; no cross-tenant view for tenant admins (any cross-tenant view, if ever needed, is platform-ops only and audited). |
| D-07 | Delete behaviour | **Archive, restorable.** Candidates, clients, users, company archived (audited, restorable); requisitions close/reopen; applications keep rejected/withdrawn/joined; permanent delete only via platform ops or a privacy request. | Phase 4.4 as planned. |
| D-13 / I-1 | Phase order, launch date | **Order confirmed (tenancy before JWT). No launch date yet.** | Roadmap stays sequence-only. |
| I-1 | Team | **Solo owner + Claude.** | Phases sized for one person; owner is also on-call and backup-drill owner (I-4). |
| D-02 / 2.4 | Login with multiple companies | **Email only; company found from the email.** One email belongs to one company. | Replaces slug login: `(tenant_id, email)` stays unique *and* email is globally unique for login; wrong-slug guardrail becomes "unknown email → generic 401". |
| D-01 | Onboarding at launch | **Self-serve signup.** | Overrides D-01 (was ops-provisioned). Phase 5 adds public signup, email verification, ToS/Privacy/DPA acceptance gate, anti-abuse (rate limits, CAPTCHA-free throttling). §13 item 9 and 16 are launch blockers again. |
| — | When a self-serve company becomes active | **After the admin verifies their email** (then MFA enrolment), no manual approval. | Signup → verify → MFA → `active`. |
| D-09 | MFA | **Required for Admins** (TOTP); optional for others. | Phase 3.6 as planned. |
| D-06 | Offer approval threshold | **Per-company setting**, default 0 (every offer needs approval). | Phase 4.8 as planned. |
| I-4 | Peak concurrent users | **Unknown.** | Plan for 100 concurrent; load-test at 3× = 300. |
| I-7 | Legal text | **Lawyer, later.** | Engineering builds versioned acceptance with clearly marked placeholder text; launch blocked until final text. |
| I-3 | Domain | **None yet.** | Placeholders `app.<domain>` / `staging.<domain>`; CORS/TLS close when bought. |
