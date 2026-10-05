# Docs

Product specification lives in one place:

- [PRODUCT_REQUIREMENTS_DOCUMENT.md](./PRODUCT_REQUIREMENTS_DOCUMENT.md)

Architecture and RBAC parity:

- [pipeline-rbac-architecture-spec.md](./pipeline-rbac-architecture-spec.md) — multi-client
  pipeline architecture, RBAC permission-parity rules (RB-1), and the frontend/backend
  enforcement deliverables. Its §0 "Exists today" audit rows and §2.2/§4.1 status callouts
  distinguish what is **shipped** from what is still **spec-only**, so the audit stays
  truthful against the code.

How to run the application is documented in the repository root `README.md` and `backend/README.md`.

Decision records:

- [readiness-qa-and-decisions.md](./readiness-qa-and-decisions.md) — verified answers to the
  open production-readiness questions (data-layer findings, RBAC site counts, PII probe,
  pipeline-scope evidence) plus the decisions still owed by the team.
- [production-readiness-assessment.md](./production-readiness-assessment.md) — Go/No-Go
  baseline. **Note:** its items 5/6 and the "17 `isAdmin()` sites" evidence are superseded by
  `readiness-qa-and-decisions.md` (Part 1).
