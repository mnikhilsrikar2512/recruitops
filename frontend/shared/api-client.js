/* ── Session, permission gate and shared API client ── */
/* Session + /permissions/me sync gate so admin-control-plane pages are
 * denied to non-admins at the right moment, consistent with the backend
 * per-route require_permissions checks. No local role catalog: the live
 * permission codes from /permissions/me are the single source of truth.
 * apiRequest() below is the one way pages call the API. */

/* ==========================================================================
   Constants
   ========================================================================== */

/** Frontend mirror of the backend PERMISSION_ALIASES (deps.py).
 * The live backend codes stay authoritative for gating; aliases only let the
 * freedom to map legacy prototype codes onto the canonical names. */
const PERMISSION_ALIASES = {
  dashboard_view_recruiter: ["dashboard.view_execution"],
  dashboard_view_manager: ["dashboard.view_execution"],
  dashboard_view_hr: ["dashboard.view_execution"],
  pipeline_read_summary: ["pipeline.board.read"],
  pipeline_read_detail: ["pipeline.board.read"],
  role_permissions_assign: ["role.write"],
  candidate_create: ["candidate.write"],
  daily_update_create_main: ["daily_update.write"],
  assignment_read: ["work_assignment.write"],
  portal_read: ["portal_accounts.write"],
  settings_read: ["location.read"],
};

/** Canonical permission codes consumed by /permissions/me. */
const ADMIN_CONTROL_PLANE = new Set([
  "access-denied.html",
  "approval-review-drawer.html",
  "analytics-dashboard.html",
  "agents-workbench.html",
  "application-detail-drawer.html",
  "application-history.html",
  "approval-review-drawer.html",
  "approval-review-drawer.html",
  "business-titles.html",
  "client-directory.html",
  "client-detail.html",
  "custom-report-builder.html",
  "daily-updates-review.html",
  "daily-updates-workspace.html",
  "login.html",
  "location-dashboard.html",
  "location-management.html",
  "meeting-form-dialog.html",
  "meetings.html",
  "notification-detail-panel.html",
  "notifications-center.html",
  "offer-management.html",
  "pipeline-analytics.html",
  "pipeline-board.html",
  "portal-accounts.html",
  "report-viewer.html",
  "reports.html",
  "role-management.html",
  "role-permissions-editor.html",
  "sla-tracker.html",
  "source-effectiveness.html",
  "stage-history-audit-log.html",
  "team-workload.html",
  "time-to-fill-report.html",
  "user-detail.html",
  "user-management.html",
  "user-performance-reports.html",
  "visibility-rules.html",
  "work-assignment.html",
]);

/** Canonical admin-role permission codes that unlock the control plane. */
const ADMIN_ROLE_PERMISSIONS = new Set([
  "role.read",
  "user.read",
  "location.read",
  "settings.read",
  "report.read",
  "dashboard.view_admin",
  "pipeline.read.summary",
  "approval.read",
  "offer.read",
  "meeting.read",
  "notification.read",
  "daily_update.read",
  "candidate.read",
  "client.read",
  "requisition.read",
  "work_assignment.write",
]);

/* ==========================================================================
   Session + permissions sync
   ========================================================================== */

const SESSION_STORAGE_KEY = "recruitops:session";
const TOKEN_STORAGE_KEY = "recruitops:token";
/* Backend prefix — see backend/app/core/config.py api_prefix (API_PREFIX). */
const API_PREFIX = "/api/v1";

/** Read the bearer token issued by POST {API_PREFIX}/auth/login. */
function readAuthToken() {
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY) || "";
  } catch (err) {
    return "";
  }
}

/** Persist the bearer token so later page loads can re-sync permissions. */
function writeAuthToken(token) {
  try {
    if (token) window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
    else window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch (err) {
    /* storage unavailable (private mode) — sync becomes a no-op */
  }
}

/**
 * Synchronous session read. navigation.js and app.js both call readSession()
 * expecting a plain object, so this must stay synchronous — the network
 * refresh lives in syncUserPermissions().
 */
function readSession() {
  if (window.RecruitOpsLive && window.RecruitOpsLive.session) {
    return window.RecruitOpsLive.session;
  }
  return readSessionSync();
}

/** Persist the session so readSession()/navPermissionSet() see it synchronously. */
function writeSession(session) {
  try {
    if (session) {
      window.sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
    } else {
      window.sessionStorage.removeItem(SESSION_STORAGE_KEY);
    }
  } catch (err) {
    /* storage can be unavailable in private mode — the in-memory
     * RecruitOpsLive.session set by app.js still backs the gate. */
  }
}

/**
 * Synchronous snapshot used for default-deny rendering and page gating.
 * Returns the parsed session or null when nothing has synced yet.
 */
function readSessionSync() {
  try {
    const raw = window.sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (err) {
    return null;
  }
}

/**
 * Fetch /auth/me + /permissions/me and persist the merged session.
 *
 * This is "the right moment": RB-1 gating runs only once BOTH calls resolve,
 * mirroring the backend which evaluates require_permissions per route against
 * the same resolved permission catalog (list_resolved_permissions).
 *
 * Returns the merged session, or null when there is no token / the session
 * was rejected (401/403) — in which case any cached session is cleared.
 */
async function syncUserPermissions() {
  if (!readAuthToken()) return readSessionSync();

  try {
    /* Both calls go through apiRequest so auth, errors and the 401 hook
       live in exactly one place. */
    const [me, perms] = await Promise.all([
      apiRequest("/auth/me"),
      apiRequest("/permissions/me"),
    ]);
    if (!perms || !Array.isArray(perms.permissions)) return readSessionSync();

    /* /permissions/me is the RB-1 source of truth for role_code + permissions;
     * /auth/me contributes user/role/location display context. */
    const session = Object.assign({}, me || {}, perms);
    writeSession(session);
    if (window.RecruitOpsLive) window.RecruitOpsLive.session = session;
    return session;
  } catch (err) {
    if (err && (err.status === 401 || err.status === 403)) {
      /* Session revoked/expired or the user was deactivated. */
      clearSession();
      return null;
    }
    /* Network failure: keep whatever we already synced rather than deny. */
    return readSessionSync();
  }
}

/** Drop the cached session + token (logout, or rejected by the API). */
function clearSession() {
  writeSession(null);
  writeAuthToken("");
  if (window.RecruitOpsLive) window.RecruitOpsLive.session = null;
}

/** Deep-link page gating. Call after the session + /permissions/me sync. */
function enforcePagePermission(pageId) {
  const session = readSessionSync();

  /* Nothing synced yet (no token, or the API is unreachable): leave the page
     alone. RB-1 gates *sessions* — denying here would lock every page for
     anonymous/prototype visitors while the backend still protects the APIs. */
  if (!session || typeof session.role_code !== "string") return true;

  const roleCode = session.role_code;
  /* NB: local name must not shadow the global isAdmin() guard — referring to
     `isAdmin` inside its own initializer throws a TDZ ReferenceError. */
  const adminByRole = roleCode === "admin" ||
    (typeof isAdmin === "function" ? isAdmin() : false);

  if (adminByRole) return true;

  if (!pageId) return true;

  if (ADMIN_CONTROL_PLANE.has(pageId)) {
    /* Admin-control-plane pages are off-limits to non-admins. */
    showAccessDenied(pageId);
    return false;
  }

  const requiredCodes = pagePermissionCodes(pageId);
  if (!requiredCodes || requiredCodes.length === 0) return true;

  const sessionPermissions = sessionPermissionsSet(session);
  const required = requiredCodes.map((code) => permissionAliasTarget(code)).filter(Boolean);
  if (required.some((code) => sessionPermissions.has(code))) return true;

  showAccessDenied(pageId);
  return false;
}

/** Redirect to the shared Access Restricted page, preserving the deep link. */
function showAccessDenied(pageId) {
  const redirect = encodeURIComponent(location.href);
  const target = `access-denied.html?denied=1&page=${encodeURIComponent(pageId)}&redirect=${redirect}`;
  if (typeof navigateToRoute === "function") {
    navigateToRoute(target);
  } else {
    location.href = target;
  }
}

/* ==========================================================================
   Shared API client
   ========================================================================== */

/**
 * Normalized failure for every non-2xx response (and for network failures).
 * Parsed from the backend's actual error shapes (main.py):
 *   409 / 500 / 503 → {"detail": "…"}
 *   422             → {"detail": "…", "errors": ["field: message", …]}
 * `detail` is the human-readable message; `errors` carries the field list.
 * Status 0 means the request never reached the API (network failure).
 */
class ApiError extends Error {
  constructor(status, detail, errors) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.errors = Array.isArray(errors) ? errors : [];
  }
}

/** Build an ApiError from an HTTP status and the parsed error body. */
function apiErrorFromBody(status, body) {
  const detail = body && typeof body === "object" ? body.detail : null;
  const errors = body && Array.isArray(body.errors) ? body.errors : [];
  let message;
  if (typeof detail === "string" && detail) {
    message = detail;
  } else if (errors.length) {
    message = String(errors[0]);
  } else {
    message = `Request failed with status ${status}`;
  }
  return new ApiError(status, message, errors);
}

/* 401 handling is pluggable: Phase 3 swaps in refresh-and-retry here
 * (plan §5.A) without touching any call site. */
let unauthorizedHandler = defaultUnauthorizedHandler;

function defaultUnauthorizedHandler() {
  /* On the login page a 401 means the *submitted credentials* were rejected
     (POST /auth/login), not that the stored session was revoked — wiping a
     working session because someone mistyped their password is wrong. */
  if (location.pathname.endsWith("login.html")) return;
  clearSession();
  /* Pages are flat siblings of login.html. */
  location.href = "login.html";
}

/** Replace the 401 handler; any non-function restores the default. */
function setUnauthorizedHandler(handler) {
  unauthorizedHandler = typeof handler === "function" ? handler : defaultUnauthorizedHandler;
}

/**
 * The shared data client. Returns the parsed JSON body untouched (list
 * endpoints keep their { items, meta: { page, page_size, total } } shape).
 *
 *   apiRequest("/approvals/?status=pending")
 *   apiRequest("/pipeline/applications/7/stage", { method: "PATCH", body: {...} })
 *
 * - prefixes API_PREFIX and sends the stored Bearer token
 * - throws ApiError { status, detail, errors } on any non-2xx
 * - on 401 runs the pluggable handler (clear session → login) before throwing
 * - never widens access on failure: it reads credentials, it never grants any
 */
async function apiRequest(path, options = {}) {
  const url = path.startsWith(API_PREFIX) ? path : API_PREFIX + (path.startsWith("/") ? path : `/${path}`);
  const headers = Object.assign({ Accept: "application/json" }, options.headers);
  const token = readAuthToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let body = options.body;
  if (body !== undefined && body !== null) {
    if (typeof body !== "string") body = JSON.stringify(body);
    if (!headers["Content-Type"]) headers["Content-Type"] = "application/json";
  }

  let response;
  try {
    response = await fetch(url, {
      method: options.method || "GET",
      headers,
      body,
      signal: options.signal,
    });
  } catch (err) {
    throw new ApiError(0, (err && err.message) || "Network request failed");
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const error = apiErrorFromBody(response.status, payload);
    if (response.status === 401) unauthorizedHandler();
    throw error;
  }
  return payload;
}

/* ==========================================================================
   Login — wires the existing form to POST {API_PREFIX}/auth/login
   ========================================================================== */

/**
 * Submit the login form against the current backend contract:
 *   { email, password } → { token, user, primary_role, primary_location, session }
 *
 * On success it persists the token, runs the /auth/me + /permissions/me sync so
 * the RBAC gate has a resolved session, then hands off to the dashboard. On
 * failure it surfaces the backend's own `detail` in the form's alert banner —
 * no local auth copy, no demo state cycling.
 */
async function handleLogin(form) {
  if (!form || handleLogin.pending) return; /* rapid double-submit */
  handleLogin.pending = true;

  const emailInput = form.querySelector("#email");
  const passwordInput = form.querySelector("#password");
  const submitBtn = form.querySelector("#submit-btn");
  const overlay = document.getElementById("loading-overlay");
  const banner = document.getElementById("alert-banner");

  /* The button's click handler preventDefaults, so the browser's own
     constraint validation never runs on that path — run it explicitly. */
  if (!form.checkValidity()) {
    form.reportValidity();
    handleLogin.pending = false;
    return;
  }

  resetAlertBanner(banner);
  if (overlay) overlay.classList.remove("hidden");
  if (submitBtn) submitBtn.disabled = true;

  try {
    const data = await apiRequest("/auth/login", {
      method: "POST",
      body: {
        email: (emailInput ? emailInput.value : "").trim(),
        password: passwordInput ? passwordInput.value : "",
      },
    });
    if (!data || !data.token) {
      throw new ApiError(500, "Sign-in failed: the server returned no session token");
    }

    writeAuthToken(data.token);
    /* Resolve /auth/me + /permissions/me now: the dashboard's page gate and
       every data loader run against this session from the next page on. */
    await syncUserPermissions();

    window.location.href = "role-dashboard.html";
  } catch (err) {
    const status = (err && err.status) || 0;
    const detail = (err && err.detail) || (err && err.message) || "Sign in failed. Please try again.";
    showAlertState({
      role: "alert",
      bgClass: "bg-danger-bg",
      textClass: "text-danger-text",
      borderClass: "border-[#e4b6b0]",
      icon: "error",
      /* 0 = unreachable proxy/network, 401 = bad creds, 422 = input the
         backend rejected; anything else (503, 500) gets the generic title. */
      title: { 0: "Can't reach the server", 401: "Authentication Failed", 422: "Check your details" }[status] || "Sign in failed",
      message: detail, /* the backend's real error, not local copy */
    });
    if (passwordInput) {
      passwordInput.value = "";
      passwordInput.focus();
    }
  } finally {
    if (overlay) overlay.classList.add("hidden");
    if (submitBtn) submitBtn.disabled = false;
    handleLogin.pending = false;
  }
}

/* --------------------------------------------------------------------------
 * Logout — teardown has one owner, next to the login/session code above.
 * Ends the session everywhere: best-effort server-side revoke, then the
 * stored token/session regardless, then the sign-in screen.
 * -------------------------------------------------------------------------- */

async function logout() {
  if (logout.pending) return; /* rapid double-click */
  logout.pending = true;
  try {
    if (readAuthToken()) {
      try {
        await apiRequest("/auth/logout", { method: "POST" });
      } catch (err) {
        /* Best-effort: an already-dead token must not block the local logout. */
      }
    }
    clearSession();
    /* Tab-scoped prototype state (e.g. the selected pipeline candidate). */
    try {
      window.sessionStorage.clear();
    } catch (err) {
      /* storage unavailable */
    }
    window.location.href = "login.html?loggedOut=true";
  } finally {
    logout.pending = false;
  }
}

/* ==========================================================================
   Permission catalog helpers
   ========================================================================== */

/**
 * Resolve the permission codes a page requires, from the shared config when
 * present, falling back to the static pagePermMap (the single copy now).
 * Returns [] for account chrome (my-profile, support-workspace) which are
 * always visible.
 */
function pagePermissionCodes(pageId) {
  if (!pageId) return [];
  const config = window.NAV_CONFIG && window.NAV_CONFIG.pagePermissions;
  if (config && typeof config === "object") {
    const fromConfig = config[pageId];
    if (Array.isArray(fromConfig) && fromConfig.length > 0) {
      return fromConfig;
    }
  }
  const merged = window.NAV_PAGE_PERMISSIONS || {};
  const fromMerge = merged[pageId];
  if (Array.isArray(fromMerge) && fromMerge.length > 0) {
    return fromMerge;
  }
  return [];
}

/**
 * Resolve aliases (legacy → canonical) and return the *set* of permission
 * codes the current session holds, including the `role:<code>` shim used by
 * navigation.js.
 */
function sessionPermissionsSet(session) {
  const codes = new Set();
  const sessionPermissions = (session && Array.isArray(session.permissions))
    ? session.permissions : [];
  for (const code of sessionPermissions) {
    const canonical = permissionAliasTarget(code);
    if (canonical) codes.add(canonical);
  }
  if (session && typeof session.role_code === "string") {
    codes.add("role:" + session.role_code);
  }
  return codes;
}

/** Map a legacy/alias code to its canonical permission code. */
function permissionAliasTarget(code) {
  if (typeof code !== "string") return null;
  const trimmed = code.trim();
  if (!trimmed) return null;
  if (PERMISSION_ALIASES.hasOwnProperty(trimmed)) {
    return PERMISSION_ALIASES[trimmed][0];
  }
  return trimmed;
}

/* --------------------------------------------------------------------------
 * Capability checks. These resolve the references that previously pointed at
 * helpers defined nowhere (renderers.js, and this file's own admin guards):
 * everything derives from the synced session, never from a local catalog.
 * -------------------------------------------------------------------------- */

/** True when the synced session carries the admin role (PRD §3.1 control plane). */
function isAdmin() {
  const session = readSessionSync();
  return Boolean(session && session.role_code === "admin");
}

/** Live permission codes from /permissions/me, as held by the session. */
function userPermissions() {
  const session = readSessionSync();
  return session && Array.isArray(session.permissions) ? session.permissions.slice() : [];
}

/** Capability check: does the synced session hold this permission code? */
function hasPermission(code) {
  const session = readSessionSync();
  if (!session) return false;
  return sessionPermissionsSet(session).has(permissionAliasTarget(code) || code);
}

/* ==========================================================================
   Gate hooks (register + run)
   ========================================================================== */

const PERMISSION_GATE_REGISTRY = [];

/** Register a callback that runs after the session + /permissions/me sync. */
function registerPermissionGate(callback) {
  if (typeof callback === "function") {
    PERMISSION_GATE_REGISTRY.push(callback);
  }
}

/**
 * Run every registered gate in registration order and then enforce the
 * deep-link permission gate for the current page.
 */
async function runPermissionGates() {
  for (const callback of PERMISSION_GATE_REGISTRY) {
    try {
      await callback();
    } catch (err) {
      /* a failing gate must never block the session flow */
    }
  }
  enforcePagePermission(currentRouteId());
}

/* ==========================================================================
   Admin skeleton + portal chrome rendering
   ========================================================================== */

/**
 * Wrap the document shell with the admin-control-plane chrome (sidebar,
 * topbar, grounded skeleton) when the current user is an admin.
 */
function enforceAdminSkeleton() {
  const session = readSessionSync();
  const roleCode = session && typeof session.role_code === "string" ? session.role_code : "";
  const adminByRole = roleCode === "admin" ||
    (typeof isAdmin === "function" ? isAdmin() : false);

  if (!adminByRole) {
    removeAdminSkeleton();
    return;
  }

  const root = document.querySelector("body");
  if (!root) return;

  const wrapper = document.createElement("div");
  wrapper.className = "admin-control-plane";

  wrapper.innerHTML = _adminSkeletonHtml();

  /* Replace the page content with the skeleton. Keep the nav/menu anchors
   * the shell expects so decorators, metric loaders, and deep-link gates
   * keep working. */
  const anchor = document.querySelector("#main-content") || document.querySelector("main");
  if (anchor && anchor.parentElement) {
    anchor.parentElement.insertBefore(wrapper, anchor);
    anchor.remove();
  } else {
    root.insertBefore(wrapper, root.firstChild);
  }
}

function removeAdminSkeleton() {
  const existing = document.querySelector(".admin-control-plane");
  if (existing) {
    existing.remove();
  }
}

/* --- Admin-control-plane skeleton template --------------------------------------- */
/* Keep it as a plain string (not a template literal) so the file parses cleanly. */
function _adminSkeletonHtml() {
  return (
    '<div class="admin-skeleton-overlay">' +
      '<div class="admin-skeleton-sidebar">' +
        '<div class="admin-skeleton-brand">' +
          '<span class="material-symbols-outlined">admin_panel_settings</span>' +
          '<span>RecruitOps</span>' +
        '</div>' +
        '<nav class="admin-skeleton-nav" aria-label="Admin control plane">' +
          '<div class="admin-skeleton-group">' +
            '<div class="admin-skeleton-group-label">Control Plane</div>' +
            '<a class="admin-skeleton-nav-item" href="user-management.html">Users</a>' +
            '<a class="admin-skeleton-nav-item" href="location-management.html">Locations</a>' +
            '<a class="admin-skeleton-nav-item" href="role-management.html">Roles</a>' +
            '<a class="admin-skeleton-nav-item" href="role-permissions-editor.html">Permissions</a>' +
            '<a class="admin-skeleton-nav-item" href="business-titles.html">Titles</a>' +
            '<a class="admin-skeleton-nav-item" href="portal-accounts.html">Portal</a>' +
          '</div>' +
          '<div class="admin-skeleton-group">' +
            '<div class="admin-skeleton-group-label">Oversight</div>' +
            '<a class="admin-skeleton-nav-item" href="analytics-dashboard.html">Analytics</a>' +
            '<a class="admin-skeleton-nav-item" href="reports.html">Reports</a>' +
            '<a class="admin-skeleton-nav-item" href="pipeline-analytics.html">Pipeline</a>' +
            '<a class="admin-skeleton-nav-item" href="time-to-fill-report.html">Time to Fill</a>' +
            '<a class="admin-skeleton-nav-item" href="source-effectiveness.html">Sources</a>' +
            '<a class="admin-skeleton-nav-item" href="sla-tracker.html">SLA</a>' +
            '<a class="admin-skeleton-nav-item" href="user-performance-reports.html">Users</a>' +
            '<a class="admin-skeleton-nav-item" href="team-workload.html">Team</a>' +
          '</div>' +
          '<div class="admin-skeleton-group">' +
            '<div class="admin-skeleton-group-label">Operations</div>' +
            '<a class="admin-skeleton-nav-item" href="approvals-inbox.html">Approvals</a>' +
            '<a class="admin-skeleton-nav-item" href="meeting-form-dialog.html">Meetings</a>' +
            '<a class="admin-skeleton-nav-item" href="notifications-center.html">Notify</a>' +
          '</div>' +
        '</nav>' +
        '<div class="admin-skeleton-footer">' +
          '<a href="login.html?loggedOut=true">Log out</a>' +
        '</div>' +
      '</div>' +
      '<div class="admin-skeleton-topbar">' +
        '<button class="admin-skeleton-topbar-menu" type="button" aria-label="Open admin menu">' +
          '<span class="material-symbols-outlined">menu</span>' +
        '</button>' +
        '<div class="admin-skeleton-topbar-title">Control Plane</div>' +
        '<div class="admin-skeleton-topbar-spacer"></div>' +
        '<div class="admin-skeleton-topbar-user">' +
          '<span class="material-symbols-outlined">person</span>' +
          '<span class="admin-skeleton-topbar-user-name"></span>' +
        '</div>' +
      '</div>' +
      '<main id="main-content" class="admin-skeleton-canvas">' +
        '<div class="admin-skeleton-shell">' +
          '<div class="admin-skeleton-wheel"></div>' +
          '<p class="admin-skeleton-loading">Loading control plane…</p>' +
        '</div>' +
      '</main>' +
    '</div>'
  );
}

/* ==========================================================================
   Page boot entry
   ========================================================================== */

/** Current page's route id (e.g. "user-management"). */
function currentRouteId() {
  return (document && document.body && document.body.dataset && document.body.dataset.routeId) || "";
}

/**
 * Shared page-boot entry: sync /auth/me + /permissions/me FIRST, then
 * enforce the deep-link gate for this route. Call once per page (login.html
 * and every gated page) before the rest of the shell/app is wired.
 *
 * Async by design — RB-1 must evaluate the gate *after* the permission sync,
 * not against a stale or empty session.
 */
async function bootRBACGate() {
  /* Memoize: login.html's inline call and the shared DOMContentLoaded
     bootstrap can both land on the same page — one sync, one gate run. */
  if (bootRBACGate.pending) return bootRBACGate.pending;
  bootRBACGate.pending = (async () => {
    await syncUserPermissions();
    /* runPermissionGates() runs the registered hooks and then enforces the
       deep-link gate for this route — one enforcement point, no double gate. */
    return runPermissionGates();
  })();
  try {
    return await bootRBACGate.pending;
  } finally {
    bootRBACGate.pending = null;
  }
}

/* --------------------------------------------------------------------------
 * Shared page boot.
 *
 * api-client.js is included by every page, so bootstrapping here wires the
 * gate for all of them without editing each HTML file. It registers its
 * DOMContentLoaded listener first (api-client.js parses before app.js), so
 * RB-1 is evaluated before app wiring runs.
 *
 * Anonymous visitors (no token) are left alone: there is no *session* to gate
 * and the backend still enforces require_permissions on every API call.
 * -------------------------------------------------------------------------- */
const RBAC_REVEAL_TIMEOUT_MS = 4000;

function setGatePending(pending) {
  const surface = document.getElementById("main-content");
  if (!surface) return;
  if (pending) {
    surface.dataset.rbacPending = "true";
    surface.style.visibility = "hidden";
  } else {
    delete surface.dataset.rbacPending;
    surface.style.visibility = "";
  }
}

async function startPageGate() {
  if (!readAuthToken()) return; /* no session → nothing to enforce */

  setGatePending(true);
  /* Never leave the page blank if the sync hangs — reveal regardless. */
  const safety = window.setTimeout(() => setGatePending(false), RBAC_REVEAL_TIMEOUT_MS);

  try {
    await bootRBACGate();
  } finally {
    window.clearTimeout(safety);
    setGatePending(false);
  }
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startPageGate, { once: true });
  } else {
    startPageGate();
  }

  /* One delegated listener owns logout for every [data-logout-link],
     including links rendered later by navigation.js. */
  document.addEventListener("click", (event) => {
    const link = event.target.closest("a[data-logout-link]");
    if (!link) return;
    event.preventDefault();
    /* This link is fully owned by logout. app.js's router skips it via
       ANCHOR_ROUTER_EXCLUSIONS; stopImmediatePropagation keeps every other
       document-level listener from issuing a navigation that would abort
       the /auth/logout request still in flight. */
    event.stopImmediatePropagation();
    logout();
  });
}

/* --------------------------------------------------------------------------
 * Exports for other modules / shell wiring.
 * -------------------------------------------------------------------------- */
if (typeof window !== "undefined") {
  window.RecruitOpsLive = window.RecruitOpsLive || {};
  window.RecruitOpsLive.readSession = readSession;
  window.RecruitOpsLive.writeSession = writeSession;
  window.RecruitOpsLive.clearSession = clearSession;
  window.RecruitOpsLive.readAuthToken = readAuthToken;
  window.RecruitOpsLive.writeAuthToken = writeAuthToken;
  window.RecruitOpsLive.apiRequest = apiRequest;
  window.RecruitOpsLive.ApiError = ApiError;
  window.RecruitOpsLive.setUnauthorizedHandler = setUnauthorizedHandler;
  window.RecruitOpsLive.isAdmin = isAdmin;
  window.RecruitOpsLive.hasPermission = hasPermission;
  window.RecruitOpsLive.userPermissions = userPermissions;
  window.RecruitOpsLive.syncUserPermissions = syncUserPermissions;
  window.RecruitOpsLive.sessionPermissions = sessionPermissionsSet;
  window.RecruitOpsLive.enforcePagePermission = enforcePagePermission;
  window.RecruitOpsLive.runPermissionGates = runPermissionGates;
  window.RecruitOpsLive.registerPermissionGate = registerPermissionGate;
  window.RecruitOpsLive.enforceAdminSkeleton = enforceAdminSkeleton;
  window.RecruitOpsLive.removeAdminSkeleton = removeAdminSkeleton;
  window.RecruitOpsLive.bootRBACGate = bootRBACGate;
  window.RecruitOpsLive.handleLogin = handleLogin;
  window.RecruitOpsLive.logout = logout;
  window.RecruitOpsLive.startPageGate = startPageGate;
  window.RecruitOpsLive.showAccessDenied = showAccessDenied;
}
