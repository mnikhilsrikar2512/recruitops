#!/usr/bin/env node
/*
 * Contract mock API + static server for frontend tests.
 *
 * Serves frontend/ exactly like server.js, but answers /api/v1/* from the
 * backend's OpenAPI document instead of a live FastAPI + SQL Server:
 *   - unknown path            → 404 and a contract violation
 *   - wrong method            → 405 and a contract violation
 *   - body fails the schema   → 422 and a contract violation
 *   - otherwise               → a deterministic, schema-shaped response
 *
 * Every call is logged; GET /__mock/log returns { calls, violations } and
 * POST /__mock/reset clears it. The page sweep (tests/page_sweep.py) reads it.
 *
 * Usage:
 *   node tests/mock-api-server.js --openapi path/to/openapi.json [--port 4180]
 *   MOCK_PERSONA=recruiter …   (admin | recruiter; drives /permissions/me)
 *
 * Generate openapi.json from the real backend with:
 *   cd backend && python scripts/export_openapi.py ../frontend/tests/openapi.json
 */
"use strict";

const http = require("http");
const fs = require("fs");
const path = require("path");

const args = process.argv.slice(2);
const argValue = (name, fallback) => {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
};
const PORT = Number(argValue("--port", process.env.PORT || 4180));
const FRONTEND = path.resolve(__dirname, "..");
const REPO = path.resolve(FRONTEND, "..");
const OPENAPI_PATH = path.resolve(argValue("--openapi", path.join(__dirname, "openapi.json")));
const spec = JSON.parse(fs.readFileSync(OPENAPI_PATH, "utf8"));
const schemas = (spec.components && spec.components.schemas) || {};

/* ── Route table ─────────────────────────────────────────────── */
const routes = Object.entries(spec.paths).map(([template, ops]) => {
  const names = [];
  const source = template
    .replace(/[.*+?^$()|[\]\\]/g, "\\$&")
    .replace(/\\?\{([^}]+)\\?\}/g, (_m, name) => {
      names.push(name);
      return name === "file_path" ? "(.+)" : "([^/]+)";
    });
  return { template, ops, names, regex: new RegExp(`^${source.replace(/\/$/, "")}/?$`) };
});
/* Literal segments beat parameters (FastAPI matches in declaration order,
   and e.g. /portal-accounts/availability is declared before /{id}). */
routes.sort((a, b) => a.names.length - b.names.length);

function matchRoute(pathname) {
  const hits = [];
  for (const route of routes) {
    const m = route.regex.exec(pathname);
    if (m) hits.push({ route, params: Object.fromEntries(route.names.map((n, i) => [n, m[i + 1]])) });
  }
  return hits;
}

/* ── Schema helpers ──────────────────────────────────────────── */
function deref(schema) {
  let s = schema || {};
  for (let i = 0; i < 20 && s.$ref; i += 1) s = schemas[s.$ref.split("/").pop()] || {};
  return s;
}
function nonNull(schema) {
  const s = deref(schema);
  const options = s.anyOf || s.oneOf;
  if (options) {
    const pick = options.map(deref).find((o) => o.type !== "null");
    return pick || {};
  }
  return s;
}

const FIRST_NAMES = ["Asha Rao", "Vikram Shah", "Meera Iyer", "Rohan Gupta", "Neha Kapoor"];
/* Field-name-aware fallbacks for the generic schema sampler below. Without
   these, any string field the patterns don't recognize falls through to a
   "field name + seed" placeholder ("current company 1", "work mode 2") and
   a few actively mislead ("resume_file_name" matched the generic *_name
   pattern and returned a person's name instead of a filename, and any
   "number"-typed field — experience years, days-to-fill, hours — reused
   the budget/CTC formula and came out as a six-figure number). These lists
   keep screenshots and manual QA readable without claiming to be real data. */
const COMPANY_NAMES = ["Acme Corp", "Globex Technologies", "Initech Solutions", "Stark Industries", "Umbrella Group", "Northwind Traders"];
const LOCATION_NAMES = ["Bengaluru", "Pune", "Hyderabad", "Mumbai", "Chennai", "Austin Tech Center"];
const JOB_TITLES = ["Senior Backend Engineer", "Data Analyst", "Product Designer", "Engineering Manager", "QA Lead", "DevOps Engineer"];
const INDUSTRIES = ["Technology", "Financial Services", "Healthcare", "E-commerce", "Manufacturing", "Telecom"];
const SOURCE_TYPES = ["LinkedIn", "Referral", "Naukri", "Indeed", "Agency", "Career Site"];
const WORK_MODES = ["Remote", "Hybrid", "On-site"];
const EMPLOYMENT_TYPES = ["Full-time", "Part-time", "Contract", "Internship"];
const ENTITY_TYPES = ["Requisition", "Candidate", "Application", "Offer"];
const SKILLS = ["SQL", "Python", "Stakeholder management", "React", "Node.js", "Communication", "Excel", "Negotiation", "Figma", "Project management", "AWS", "Data analysis"];
const MATCH_REASONS = ["Email matches", "Phone number matches", "Same employer and role", "Matching resume fingerprint"];
const STREET_ADDRESSES = ["221 Residency Road", "48 MG Road", "12 Park Street", "77 Brigade Road"];
const SUMMARIES = [
  "Steady progress today; pipeline health looks good.",
  "Made headway on outstanding screenings, one blocker flagged.",
  "Caught up on interviews; offers pending client sign-off.",
];
function sampleString(name, s, seed) {
  if (s.enum) return s.enum[seed % s.enum.length];
  if (s.const) return s.const;
  if (s.format === "date-time") return new Date(Date.UTC(2026, 8, 1 + (seed % 25), 9, 30)).toISOString();
  if (s.format === "date") return `2026-09-${String(1 + (seed % 25)).padStart(2, "0")}`;
  if (s.format === "email" || /email/.test(name)) return `user${seed}@example.test`;
  // "candidate" ends in the letters "date", so it used to fall through to the
  // date/timestamp branch below and render as an ISO timestamp instead of a
  // name (seen on the placements report). Catch the exact field names that
  // collide with that suffix before the generic date-suffix check runs.
  if (/^candidate$/.test(name)) return FIRST_NAMES[seed % FIRST_NAMES.length];
  if (/^consultant$/.test(name)) return FIRST_NAMES[seed % FIRST_NAMES.length];
  if (/^requisition$/.test(name)) return JOB_TITLES[seed % JOB_TITLES.length];
  if (/^department$/.test(name)) return ["Engineering", "Sales", "Finance", "Operations", "Marketing"][seed % 5];
  if (/^assignment_type$/.test(name)) return ["primary_owner", "contributor", "recruiter", "sourcer"][seed % 4];
  if (/^platform_name$/.test(name)) return ["Naukri — Premium", "LinkedIn Recruiter", "Indeed Employer", "Monster Jobs", "Shine Pro"][seed % 5];
  if (/^company_type_code$/.test(name)) return ["recruitment-agency", "staffing", "consulting", "other"][seed % 4];
  if (/^login_identifier$/.test(name)) return `recruiting${1 + (seed % 4)}@${["naukri", "linkedin", "indeed", "monster", "shine"][seed % 5]}.recruitops.in`;
  // Interview fields: round_type/round_name/decision/feedback_* had no
  // dedicated pattern and fell to the generic "<field name> <seed>"
  // fallback (literally "round type 1", "decision 1", "feedback notes 1"
  // on screen). interviewer_name and created_by_name, meanwhile, matched
  // the same generic "_name$" person-name pattern as candidate_name with
  // the same seed, so an interview showed the same person as candidate,
  // interviewer, and "scheduled by". Dedicated patterns + offset seeds fix
  // both ahead of the generic rules below.
  if (/^round_type$/.test(name)) return ["Technical", "Managerial", "HR", "Screening", "Culture Fit"][seed % 5];
  if (/^round_name$/.test(name)) return ["Technical Round 1", "Technical Round 2", "Managerial Round", "HR Round", "Screening Call", "Culture Fit Round"][seed % 6];
  if (/^decision$/.test(name)) return ["strong_yes", "yes", "no", "strong_no"][seed % 4];
  if (/^feedback_status$/.test(name)) return ["pending", "submitted"][seed % 2];
  if (/^feedback_notes$/.test(name)) return ["Strong technical fundamentals, communicated clearly, recommend moving forward.", "Good problem-solving approach but light on system design depth.", "Confident communicator, needs a second technical round to confirm depth.", "Solid culture fit, references the team's working style well."][seed % 4];
  if (/^interviewer_name$/.test(name)) return FIRST_NAMES[(seed + 4) % FIRST_NAMES.length];
  if (/^created_by_name$/.test(name)) return FIRST_NAMES[(seed + 9) % FIRST_NAMES.length];
  if (/^approval_type$/.test(name)) return ["requisition_approval", "offer_approval", "signing_bonus_exception", "budget_exception", "hold_extension"][seed % 5];
  if (/^primary_action_label$/.test(name)) return ["Review submission", "Nudge candidate", "Resolve conflict", "Schedule interview", "Submit for approval"][seed % 5];
  if (/^blockers$/.test(name)) return ["Waiting on client interview feedback.", "Candidate requested a 1-week delay before next round.", "Budget approval pending from finance.", "Offer letter stuck in legal review."][seed % 4];
  if (/^next_actions$/.test(name)) return ["Follow up with the hiring manager tomorrow.", "Schedule the next round by end of week.", "Send updated compensation details to the client.", "Chase panel feedback from yesterday's interview."][seed % 4];
  if (/_at$|_date$|deadline|date$/.test(name)) return new Date(Date.UTC(2026, 8, 1 + (seed % 25), 9, 30)).toISOString();
  if (/status$/.test(name)) return ["open", "active", "pending"][seed % 3];
  if (/stage$/.test(name)) return ["Sourced", "Screening", "Interview", "Offer"][seed % 4];
  if (/priority$/.test(name)) return ["high", "standard", "critical"][seed % 3];
  if (/currency/.test(name)) return "INR";
  if (/phone/.test(name)) return `+91 98000 0000${seed % 10}`;
  if (/(^|_)code$/.test(name)) return `CODE-${100 + seed}`;
  if (/file_?name/.test(name)) return `${FIRST_NAMES[seed % FIRST_NAMES.length].toLowerCase().replace(/\s+/g, "_")}_resume.pdf`;
  if (/^skills$|_skills$/.test(name)) return SKILLS[seed % SKILLS.length];
  if (/source_type/.test(name)) return SOURCE_TYPES[seed % SOURCE_TYPES.length];
  if (/source_detail/.test(name)) return ["Referred by a current employee", "Inbound application", "Sourced from job board post", "Agency submission", "Event / career fair"][seed % 5];
  if (/work_mode/.test(name)) return WORK_MODES[seed % WORK_MODES.length];
  if (/employment_type/.test(name)) return EMPLOYMENT_TYPES[seed % EMPLOYMENT_TYPES.length];
  if (/industry/.test(name)) return INDUSTRIES[seed % INDUSTRIES.length];
  if (/designation/.test(name)) return JOB_TITLES[seed % JOB_TITLES.length];
  if (/company|client_name|legal_name|account_name|^client$|^display_name$/.test(name)) return COMPANY_NAMES[seed % COMPANY_NAMES.length];
  if (/branch_name|location_name|^hq_city$/.test(name)) return LOCATION_NAMES[seed % LOCATION_NAMES.length];
  if (/^hq_state$/.test(name)) return ["Karnataka", "Maharashtra", "Delhi", "Telangana", "Tamil Nadu"][seed % 5];
  if (/^registered_address$/.test(name)) return STREET_ADDRESSES[seed % STREET_ADDRESSES.length];
  if (/^website_url$/.test(name)) return `https://www.${COMPANY_NAMES[seed % COMPANY_NAMES.length].toLowerCase().replace(/[^a-z]+/g, "")}.com`;
  if (/^country_name$/.test(name)) return "India";
  if (/entity_type/.test(name)) return ENTITY_TYPES[seed % ENTITY_TYPES.length];
  if (/age_label/.test(name)) return `${2 + ((seed * 3) % 58)}d`;
  if (/match_reasons/.test(name)) return MATCH_REASONS[seed % MATCH_REASONS.length];
  if (/change_reason/.test(name)) return ["Panel feedback pending", "Candidate requested reschedule", "Budget approval needed", "Moved per client request", "Scheduling conflict resolved"][seed % 5];
  if (/^address$/.test(name)) return STREET_ADDRESSES[seed % STREET_ADDRESSES.length];
  if (/^summary$/.test(name)) return SUMMARIES[seed % SUMMARIES.length];
  if (/full_name|_name$|^name$/.test(name)) return FIRST_NAMES[seed % FIRST_NAMES.length];
  if (/url|path/.test(name)) return `/files/sample-${seed}.pdf`;
  if (/token/.test(name)) return `mock-token-${seed}`;
  if (/title/.test(name)) return JOB_TITLES[seed % JOB_TITLES.length];
  return `${name.replace(/_/g, " ")} ${seed}`.trim();
}

function sample(schema, name = "", seed = 1, depth = 0) {
  const s = nonNull(schema);
  if (depth > 6) return null;
  if (s.allOf) return Object.assign({}, ...s.allOf.map((p) => sample(p, name, seed, depth + 1)));
  const type = Array.isArray(s.type) ? s.type.find((t) => t !== "null") : s.type;
  if (type === "object" || s.properties) {
    const out = {};
    for (const [key, prop] of Object.entries(s.properties || {})) {
      out[key] = key === "id" || key.endsWith("_id") ? seed : sample(prop, key, seed, depth + 1);
    }
    return out;
  }
  if (type === "array") {
    const count = depth === 0 || name === "items" ? 3 : 2;
    return Array.from({ length: count }, (_v, i) => sample(s.items || {}, name, seed + i, depth + 1));
  }
  if (type === "integer") {
    if (name === "total") return 3;
    if (name === "page") return 1;
    if (name === "page_size") return 50;
    // field-name-aware range so e.g. notice_period_days stays in a plausible band
    if (/days$/.test(name)) return 1 + (seed % 30);
    // match_score (integer, e.g. duplicate-candidate matching) used to return
    // the raw seed (1, 2, 3…), so a match found on email+phone+employer showed
    // as "1% confidence" instead of a high score — the opposite of what the
    // match reasons next to it implied.
    if (/score$/.test(name)) return 72 + ((seed * 7) % 27);
    return seed;
  }
  if (type === "number") {
    // Every float-typed field used to share one "big currency number" formula
    // (100000 + seed*2500), so non-money fields like total_experience_years
    // or avg_days_to_fill rendered as "102500 years"/"102500 days". Route by
    // field-name semantics first and keep the original formula only for
    // genuinely money-like fields (budget, CTC, revenue, bonus).
    if (/years/.test(name)) return Math.round((1 + ((seed * 3) % 14)) * 10) / 10;
    if (/days/.test(name)) return 5 + ((seed * 4) % 55);
    if (/hours/.test(name)) return 1 + ((seed * 3) % 180);
    if (/pct|percent|rate|conversion|score/.test(name)) return Math.round((10 + ((seed * 7) % 85)) * 10) / 10;
    if (/threshold/.test(name)) return 50 + ((seed * 5) % 50);
    return 100000 + seed * 2500;
  }
  if (type === "boolean") return /enabled|active|is_/.test(name) ? true : seed % 2 === 0;
  if (type === "string" || s.format) return sampleString(name, s, seed);
  return null;
}

/* Minimal JSON-schema validation: required keys, primitive types, enums,
   string length and integer minimum — the rules the pydantic models use. */
function validate(schema, value, at = "body", errors = []) {
  const raw = deref(schema);
  const options = raw.anyOf || raw.oneOf;
  if (options) {
    const ok = options.some((o) => validate(o, value, at, []).length === 0);
    if (!ok) errors.push(`${at}: does not match any allowed shape`);
    return errors;
  }
  const s = raw;
  const type = s.type;
  if (value === null || value === undefined) {
    if (type === "null") return errors;
    errors.push(`${at}: must not be null`);
    return errors;
  }
  const actual = Array.isArray(value) ? "array" : Number.isInteger(value) ? "integer" : typeof value;
  const ok = !type
    || type === actual
    || (type === "number" && (actual === "integer" || actual === "number"))
    || (type === "object" && actual === "object")
    || (type === "string" && actual === "string");
  if (!ok) {
    errors.push(`${at}: expected ${type}, got ${actual}`);
    return errors;
  }
  if (s.enum && !s.enum.includes(value)) errors.push(`${at}: must be one of ${s.enum.join(", ")}`);
  if (type === "string" && s.minLength && value.length < s.minLength) errors.push(`${at}: too short`);
  if (type === "string" && s.maxLength && value.length > s.maxLength) errors.push(`${at}: too long`);
  if (type === "integer" && s.minimum !== undefined && value < s.minimum) errors.push(`${at}: below minimum ${s.minimum}`);
  if (type === "object" || s.properties) {
    for (const key of s.required || []) {
      if (!(key in value)) errors.push(`${at}.${key}: field required`);
    }
    for (const [key, prop] of Object.entries(s.properties || {})) {
      if (key in value) validate(prop, value[key], `${at}.${key}`, errors);
    }
  }
  if (type === "array" && s.items) value.forEach((item, i) => validate(s.items, item, `${at}[${i}]`, errors));
  return errors;
}

/* ── Personas ────────────────────────────────────────────────── */
function permissionCatalog() {
  const codes = new Set();
  const apiDir = path.join(REPO, "backend", "app", "api");
  const walk = (dir) => fs.readdirSync(dir, { withFileTypes: true }).forEach((d) => {
    const p = path.join(dir, d.name);
    if (d.isDirectory()) walk(p);
    else if (p.endsWith(".py")) {
      const text = fs.readFileSync(p, "utf8");
      for (const m of text.matchAll(/require_(?:any_)?permissions?\(([^)]*)\)/g)) {
        for (const c of m[1].matchAll(/"([a-z_.]+)"/g)) codes.add(c[1]);
      }
    }
  });
  if (fs.existsSync(apiDir)) walk(apiDir);
  return [...codes].sort();
}
/* Codes the page gates use (navigation.config.js), which may be PRD names
   with no route of their own (dashboard.view_admin, …). */
function navCodes() {
  const file = path.join(REPO, "frontend", "shared", "navigation.config.js");
  if (!fs.existsSync(file)) return [];
  return [...new Set([...fs.readFileSync(file, "utf8").matchAll(/"([a-z_]+\.[a-z_.]+)"/g)].map((m) => m[1]))]
    .filter((c) => !c.endsWith(".html"));
}
/* The Admin template (D-03) straight from backend/app/core/rbac.py. */
function adminCodes() {
  const file = path.join(REPO, "backend", "app", "core", "rbac.py");
  if (!fs.existsSync(file)) return [];
  const text = fs.readFileSync(file, "utf8");
  const block = (text.split("ADMIN_PERMISSION_CODES: tuple")[1] || "").split("\n)\n")[0];
  const codes = [...block.matchAll(/"([a-z_]+\.[a-z_.]+)"/g)].map((m) => m[1]);
  return [...new Set([...codes, "scope.company"])];
}
const ALL_CODES = [...new Set([...permissionCatalog(), ...navCodes()])].sort();
const PERSONAS = {
  /* control plane only — denied execution pages by design */
  admin: { role_code: "admin", role_name: "Admin", permissions: adminCodes() },
  /* every code: sweeps every page with data, drives the UI flows */
  full: { role_code: "manager", role_name: "Full Access", permissions: ALL_CODES },
  recruiter: {
    role_code: "recruiter",
    role_name: "Recruiter",
    permissions: ALL_CODES.filter((c) => /^(candidate|pipeline|requisition\.read|interview|notification|daily_update|dashboard\.read_my_work|client\.read|offer\.read|meeting)/.test(c)),
  },
};
let persona = process.env.MOCK_PERSONA || "admin";

/* ── Call log ────────────────────────────────────────────────── */
let calls = [];
let violations = [];
function violation(kind, method, url, detail, page) {
  violations.push({ kind, method, url, detail, page });
}

function special(method, pathname, body) {
  const p = PERSONAS[persona] || PERSONAS.admin;
  if (method === "POST" && pathname === "/api/v1/auth/login") {
    if (!body || body.password === "wrong") return [401, { detail: "Invalid email or password" }];
    return [200, {
      token: `mock-${persona}-token`,
      user: { id: 1, full_name: "Asha Rao", email: body.email, status: "active", business_title: "Lead", phone: null, employee_code: "E1" },
      primary_role: { id: 1, code: p.role_code, name: p.role_name },
      primary_location: { id: 1, location_code: "BLR", location_name: "Bengaluru", offers_enabled: true },
      session: { id: 1, expires_at: "2026-12-31T00:00:00Z", force_password_change_on_first_login: false },
    }];
  }
  if (method === "GET" && pathname === "/api/v1/auth/me") {
    return [200, {
      user: { id: 1, full_name: "Asha Rao", email: "asha@example.test", status: "active", business_title: "Lead", phone: null, employee_code: "E1" },
      primary_role: { id: 1, code: p.role_code, name: p.role_name },
      primary_location: { id: 1, location_code: "BLR", location_name: "Bengaluru", offers_enabled: true },
    }];
  }
  /* Phase 5.1: the personas have accepted the current legal versions, so the
     acceptance gate lets every page through during the sweeps. */
  if (method === "GET" && pathname === "/api/v1/legal/acceptances") {
    return [200, { items: [], pending: [], company_pending: [] }];
  }
  if (method === "GET" && pathname === "/api/v1/permissions/me") {
    return [200, { user_id: 1, role_code: p.role_code, permissions: p.permissions }];
  }
  /* The generic /reports/datasets/{name} endpoint is used by SLA Tracker
     and the Custom Report Builder preview. Its response schema is too
     generic for the catch-all sampler below (it would produce "key 1" /
     "label 1" placeholder rows), so give each known dataset a realistic
     shape here instead. */
  const datasetMatch = /^\/api\/v1\/reports\/datasets\/(\w+)$/.exec(pathname);
  if (method === "GET" && datasetMatch) {
    return [200, reportDataset(datasetMatch[1])];
  }
  /* Hiring-stage list endpoints (stage-bucket-map, tenant-setup, client
     detail) have a `name`/`example_label` field that collides with the
     generic person-name sampler, and a `metric_bucket` field with no
     dedicated pattern — both fell through to literal placeholder text
     ("Vikram Shah" as a stage name, "metric bucket 1"). Give them a
     realistic hiring-stage shape instead. */
  const STAGE_NAMES = ["Sourced", "Screening", "Interview", "Offer", "Joined", "Rejected", "Withdrawn"];
  const STAGE_BUCKETS = ["sourced", "screened", "interview", "offer", "joined", "rejected", "withdrawn"];
  if (method === "GET" && /^\/api\/v1\/settings\/stage-lists\/(company|clients\/\d+)$/.test(pathname)) {
    return [200, {
      source: /clients\//.test(pathname) ? "company" : "platform",
      stages: STAGE_NAMES.map((name, i) => ({ name, bucket: STAGE_BUCKETS[i] })),
    }];
  }
  if (method === "GET" && pathname === "/api/v1/settings/stage-buckets") {
    return [200, {
      buckets: STAGE_BUCKET_CHOICES_MOCK,
      stages: STAGE_NAMES.map((name, i) => ({
        stage_key: name.toLowerCase(),
        example_label: name,
        applications: (i * 3 + 1) % 9,
        metric_bucket: STAGE_BUCKETS[i],
        source: i < 2 ? "platform" : i < 5 ? "company" : "inferred",
      })),
    }];
  }
  /* Notifications: "message" is a bare free-text field with no dedicated
     sampleString pattern, so it fell to the generic "message 1/2/3"
     fallback on notifications-center.html. A field named just "message"
     is too generic to give a dedicated pattern in sampleString() itself —
     several auth-flow schemas (logout, password reset) also have a plain
     "message" field, and those really are short confirmation strings, not
     hiring events. So this runs the normal schema sampler for the route
     and then overrides only the message text, scoped to this endpoint. */
  if (method === "GET" && pathname === "/api/v1/notifications/") {
    const hit = matchRoute(pathname).find((h) => h.route.ops.get);
    const op = hit && hit.route.ops.get;
    const firstResponse = op && op.responses && Object.entries(op.responses)[0];
    const resSchema = firstResponse && firstResponse[1].content && firstResponse[1].content["application/json"];
    if (resSchema) {
      const payload = sample(resSchema.schema);
      const NOTIFICATION_MESSAGES = ["Candidate moved to the next pipeline stage.", "Interview feedback is ready for review.", "Offer was sent and is awaiting a response.", "A new daily update was submitted with a blocker flagged.", "Requisition approval is pending your review."];
      (payload.items || []).forEach((item, i) => {
        item.message = NOTIFICATION_MESSAGES[i % NOTIFICATION_MESSAGES.length];
      });
      return [200, payload];
    }
  }
  return null;
}
const STAGE_BUCKET_CHOICES_MOCK = [
  { code: "sourced", label: "Sourced" }, { code: "screened", label: "Screened" },
  { code: "submitted", label: "Submitted" }, { code: "interview", label: "Interview" },
  { code: "offer", label: "Offer" }, { code: "joined", label: "Joined (closes)" },
  { code: "rejected", label: "Rejected (closes)" }, { code: "withdrawn", label: "Withdrawn (closes)" },
];

function reportDataset(name) {
  const n = (seed) => 1 + ((seed * 2654435761) % 2147483647);
  if (name === "sla") {
    const columns = [
      { key: "mandate", label: "Mandate", type: "string" },
      { key: "client", label: "Client", type: "string" },
      { key: "sla_target_days", label: "SLA Target (days)", type: "number" },
      { key: "current_days", label: "Current (days)", type: "number" },
      { key: "status", label: "Status", type: "string" },
      { key: "owner", label: "Owner", type: "string" },
    ];
    const rows = JOB_TITLES.map((title, i) => {
      const target = 30 + (i % 3) * 10;
      const current = Math.max(3, target - 12 + ((n(i) % 25)));
      return {
        mandate: title,
        client: COMPANY_NAMES[i % COMPANY_NAMES.length],
        sla_target_days: target,
        current_days: current,
        status: "open",
        owner: FIRST_NAMES[i % FIRST_NAMES.length],
      };
    });
    return { dimensions: [{ key: "sla", label: "SLA", columns, requires: [] }], rows };
  }
  if (name === "time_to_fill") {
    const columns = [
      { key: "requisition", label: "Requisition", type: "string" },
      { key: "department", label: "Department", type: "string" },
      { key: "days_to_fill", label: "Days to Fill", type: "number" },
    ];
    const rows = JOB_TITLES.map((title, i) => ({ requisition: title, department: ["Engineering", "Sales", "Marketing", "Operations"][i % 4], days_to_fill: 14 + (n(i) % 50) }));
    return { dimensions: [{ key: "time_to_fill", label: "Time to Fill", columns, requires: [] }], rows };
  }
  if (name === "source_effectiveness") {
    const columns = [
      { key: "source", label: "Source", type: "string" },
      { key: "candidates", label: "Candidates", type: "number" },
      { key: "hired", label: "Hired", type: "number" },
      { key: "conversion_rate", label: "Conversion %", type: "number" },
    ];
    const rows = SOURCE_TYPES.map((source, i) => {
      const candidates = 20 + (n(i) % 300);
      const hired = Math.max(1, Math.round(candidates * (0.05 + (n(i + 1) % 25) / 100)));
      return { source, candidates, hired, conversion_rate: Math.round((hired / candidates) * 100) };
    });
    return { dimensions: [{ key: "source_effectiveness", label: "Source Effectiveness", columns, requires: [] }], rows };
  }
  if (name === "pipeline") {
    const columns = [
      { key: "stage", label: "Stage", type: "string" },
      { key: "candidates", label: "Candidates", type: "number" },
      { key: "conversion_rate", label: "Conversion %", type: "number" },
    ];
    const stages = ["Applied", "Screened", "Interview", "Offer", "Joined"];
    const rows = stages.map((stage, i) => ({ stage, candidates: Math.max(1, 200 - i * 38), conversion_rate: Math.max(5, 100 - i * 18) }));
    return { dimensions: [{ key: "pipeline", label: "Pipeline", columns, requires: [] }], rows };
  }
  if (name === "daily_updates") {
    const columns = [
      { key: "user", label: "User", type: "string" },
      { key: "date", label: "Date", type: "date" },
      { key: "blockers", label: "Blockers", type: "string" },
    ];
    const rows = FIRST_NAMES.slice(0, 6).map((user, i) => ({ user, date: reportIsoDaysAgoForMock(i), blockers: i % 3 === 0 ? "Awaiting client feedback" : "" }));
    return { dimensions: [{ key: "daily_updates", label: "Daily Updates", columns, requires: [] }], rows };
  }
  /* requisitions (default) */
  const columns = [
    { key: "title", label: "Requisition", type: "string" },
    { key: "client", label: "Client", type: "string" },
    { key: "status", label: "Status", type: "string" },
    { key: "openings", label: "Openings", type: "number" },
  ];
  const rows = JOB_TITLES.map((title, i) => ({ title, client: COMPANY_NAMES[i % COMPANY_NAMES.length], status: i % 4 === 0 ? "closed" : "open", openings: 1 + (n(i) % 4) }));
  return { dimensions: [{ key: "requisitions", label: "Requisitions", columns, requires: [] }], rows };
}

function reportIsoDaysAgoForMock(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

/* ── HTTP ────────────────────────────────────────────────────── */
const MIME = {
  ".html": "text/html", ".css": "text/css", ".js": "application/javascript", ".json": "application/json",
  ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml", ".ico": "image/x-icon", ".webp": "image/webp", ".woff2": "font/woff2",
};

function sendJson(res, status, payload) {
  res.writeHead(status, { "Content-Type": "application/json", "Cache-Control": "no-store" });
  res.end(status === 204 ? "" : JSON.stringify(payload));
}

function serveStatic(req, res) {
  const urlPath = decodeURIComponent(req.url.split("?")[0]);
  let filePath = path.resolve(FRONTEND, "." + (urlPath === "/" ? "/index.html" : urlPath));
  if (!fs.existsSync(filePath)) filePath = path.resolve(FRONTEND, "pages", "." + urlPath);
  if (!filePath.startsWith(FRONTEND + path.sep) || !fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    res.writeHead(404);
    res.end("Not found");
    return;
  }
  res.writeHead(200, { "Content-Type": MIME[path.extname(filePath)] || "application/octet-stream", "Cache-Control": "no-store" });
  fs.createReadStream(filePath).pipe(res);
}

function handleApi(req, res, rawBody) {
  const url = new URL(req.url, "http://mock");
  const method = req.method.toUpperCase();
  const page = req.headers.referer ? path.basename(new URL(req.headers.referer).pathname) : "";
  let body = null;
  if (rawBody) {
    try { body = JSON.parse(rawBody); } catch { body = rawBody; }
  }
  calls.push({ method, url: url.pathname + url.search, page, body: method === "GET" ? undefined : body });

  if (!req.headers.authorization && !/\/auth\/(login|password\/(forgot|reset|setup))$/.test(url.pathname) && url.pathname !== "/api/v1/health") {
    return sendJson(res, 401, { detail: "Missing bearer token" });
  }

  const hits = matchRoute(url.pathname);
  if (!hits.length) {
    violation("unknown-path", method, url.pathname, "no backend route", page);
    return sendJson(res, 404, { detail: "Not Found" });
  }
  const hit = hits.find((h) => h.route.ops[method.toLowerCase()]);
  if (!hit) {
    violation("wrong-method", method, url.pathname, `allowed: ${Object.keys(hits[0].route.ops).join(", ")}`, page);
    return sendJson(res, 405, { detail: "Method Not Allowed" });
  }
  const op = hit.route.ops[method.toLowerCase()];

  for (const param of op.parameters || []) {
    if (param.in === "path") {
      const value = hit.params[param.name];
      const ps = nonNull(param.schema);
      if (ps.type === "integer" && !/^\d+$/.test(value)) {
        violation("bad-path-param", method, url.pathname, `${param.name}=${value} is not an integer`, page);
        return sendJson(res, 422, { detail: `${param.name}: Input should be a valid integer` });
      }
    }
    if (param.in === "query" && url.searchParams.has(param.name)) {
      const ps = nonNull(param.schema);
      const value = url.searchParams.get(param.name);
      if (ps.type === "integer" && !/^-?\d+$/.test(value)) {
        violation("bad-query-param", method, url.pathname + url.search, `${param.name}=${value} is not an integer`, page);
        return sendJson(res, 422, { detail: `${param.name}: Input should be a valid integer` });
      }
      if (ps.type === "integer" && ps.maximum !== undefined && Number(value) > ps.maximum) {
        violation("bad-query-param", method, url.pathname + url.search, `${param.name}=${value} exceeds maximum ${ps.maximum}`, page);
        return sendJson(res, 422, { detail: `${param.name}: Input should be less than or equal to ${ps.maximum}` });
      }
      if (ps.enum && !ps.enum.includes(value)) {
        violation("bad-query-param", method, url.pathname + url.search, `${param.name}=${value} not in ${ps.enum.join("|")}`, page);
        return sendJson(res, 422, { detail: `${param.name}: invalid value` });
      }
    }
  }

  const reqSchema = op.requestBody && op.requestBody.content && op.requestBody.content["application/json"];
  if (reqSchema) {
    const errors = validate(reqSchema.schema, body ?? null);
    if (errors.length) {
      violation("invalid-body", method, url.pathname, errors.slice(0, 5).join("; "), page);
      return sendJson(res, 422, { detail: errors[0], errors });
    }
  }

  const fixed = special(method, url.pathname, body);
  if (fixed) return sendJson(res, fixed[0], fixed[1]);

  const [code, response] = Object.entries(op.responses || {})[0] || ["200", {}];
  const status = Number(code) || 200;
  const resSchema = response.content && response.content["application/json"];
  if (status === 204) return sendJson(res, 204, null);
  return sendJson(res, status, resSchema ? sample(resSchema.schema) : {});
}

http.createServer((req, res) => {
  if (req.url === "/__mock/log") return sendJson(res, 200, { calls, violations });
  if (req.url.startsWith("/__mock/reset")) {
    calls = [];
    violations = [];
    const m = /persona=(\w+)/.exec(req.url);
    if (m && PERSONAS[m[1]]) persona = m[1];
    return sendJson(res, 200, { ok: true, persona });
  }
  if (req.url.startsWith("/api/")) {
    let raw = "";
    req.on("data", (chunk) => { raw += chunk; });
    req.on("end", () => handleApi(req, res, raw));
    return undefined;
  }
  return serveStatic(req, res);
}).listen(PORT, "127.0.0.1", () => {
  console.log(`Mock API + frontend on http://127.0.0.1:${PORT} (${routes.length} routes, ${ALL_CODES.length} permission codes)`);
});
