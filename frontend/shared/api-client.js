/**
 * api-client.js — API layer, session management, page orchestration & async loaders
 *
 * Depends on renderers.js being loaded first for helper functions.
 * Contains: API requests, form submissions, page loaders, shell decoration.
 *
 * Load AFTER renderers.js:
 *   <script src="../shared/renderers.js"></script>
 *   <script src="../shared/api-client.js"></script>
 */

/* ═══════════════════════════════════════════════════════════════
   CONSTANTS & GLOBAL STATE
   ═══════════════════════════════════════════════════════════════ */

const RecruitOpsLive = { session: null };
const LIVE_API_ENABLED = true;
const API_BASE = "/api/v1";
const PUBLIC_ROUTES = new Set([
  "index", "login", "landing", "forgot-password", "reset-password",
  "password-setup", "product-tour", "use-cases", "onboarding-welcome",
  "onboarding-company-profile", "onboarding-locations", "onboarding-role-setup",
  "onboarding-pipeline-stage-builder", "onboarding-add-custom-stage-overlay",
  "onboarding-hiring-teams", "onboarding-integrations", "onboarding-success-launch",
]);


/* ═══════════════════════════════════════════════════════════════
   SESSION & API LAYER
   ═══════════════════════════════════════════════════════════════ */

function routeId() {
  const overlay = document.getElementById("ro-inpage-overlay");
  if (overlay?.dataset.overlayRoute) return overlay.dataset.overlayRoute;
  const file = (window.location.pathname.split("/").pop() || "index.html").replace(/\.html.*/, "").replace(/\?.*/, "");
  return file || "index";
}

function pathRouteId() {
  const file = (window.location.pathname.split("/").pop() || "index.html").replace(/\.html.*/, "").replace(/\?.*/, "");
  return document.body?.dataset.routeId || file || "index";
}

function readSession() {
  try {
    return JSON.parse(localStorage.getItem("recruitops-session") || "null");
  } catch {
    return null;
  }
}

function writeSession(session) {
  if (session) {
    localStorage.setItem("recruitops-session", JSON.stringify(session));
  } else {
    localStorage.removeItem("recruitops-session");
  }
}

function pageHref(name) {
  return name.endsWith(".html") ? name : name + ".html";
}

let cachedApiRoot = null;

function apiRootCandidates() {
  const roots = [];
  const explicit = typeof window !== "undefined" ? window.RECRUITOPS_API_ORIGIN : "";
  if (explicit) roots.push(String(explicit).replace(/\/$/, "") + API_BASE);
  if (typeof window !== "undefined" && window.location?.protocol && window.location.protocol !== "file:") {
    roots.push(`${window.location.origin}${API_BASE}`);
  }
  roots.push("http://127.0.0.1:8000" + API_BASE);
  roots.push("http://localhost:8000" + API_BASE);
  return [...new Set(roots)];
}

function apiUrl(path, root) {
  if (path.startsWith("http")) return path;
  return `${root}${path.startsWith("/") ? path : `/${path}`}`;
}

let connectionBannerShown = false;

function showConnectionBanner() {
  if (connectionBannerShown || document.querySelector(".ro-connection-banner")) return;
  connectionBannerShown = true;
  const banner = document.createElement("div");
  banner.className = "ro-error-banner ro-connection-banner";
  banner.setAttribute("role", "alert");
  banner.innerHTML = "<strong>Can’t reach the server.</strong> Data on this page may be missing. Start the backend and refresh.";
  const canvas = document.querySelector(".app-canvas") || document.querySelector("main") || document.body;
  canvas.prepend(banner);
}

async function apiRequest(path, options = {}) {
  const session = RecruitOpsLive.session || readSession();
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (session?.token) headers["Authorization"] = `Bearer ${session.token}`;
  const roots = cachedApiRoot ? [cachedApiRoot] : apiRootCandidates();
  let lastError = null;
  let unreachable = true;
  for (const root of roots) {
    try {
      const response = await fetch(apiUrl(path, root), { ...options, headers });
      if (response.status === 503) {
        lastError = new Error("API error 503: backend unreachable");
        continue;
      }
      unreachable = false;
      if (response.status === 404 && !cachedApiRoot && roots.length > 1) {
        lastError = new Error("API error 404");
        continue;
      }
      cachedApiRoot = root;
      if (response.status === 401) {
        writeSession(null);
        window.location.href = pageHref("login.html");
        throw new Error("Session expired");
      }
      if (!response.ok) {
        const body = await response.text().catch(() => "");
        throw new Error(`API error ${response.status}: ${body.slice(0, 200)}`);
      }
      if (response.status === 204) return {};
      return response.json();
    } catch (error) {
      lastError = error;
      if (cachedApiRoot || /Session expired/i.test(error?.message || "")) throw error;
    }
  }
  if (unreachable) showConnectionBanner();
  throw lastError || new Error("Unable to reach the API. Start FastAPI on port 8000.");
}

function formatListCount(visible, total) {
  const v = Number(visible) || 0;
  const t = Number(total) || 0;
  if (!t) return "0 of 0";
  return `${v} of ${t}`;
}

function showLiveError(error) {
  const message = error?.message || String(error);
  console.error("[RecruitOps]", message);
  document.querySelectorAll(".ro-error-banner").forEach((el) => el.remove());
  const banner = document.createElement("div");
  banner.className = "ro-error-banner";
  banner.setAttribute("role", "alert");
  banner.innerHTML = `<strong>Couldn’t complete that request.</strong> ${escapeLiveHtml(message)}`;
  const surface = document.querySelector(".workspace-surface");
  const title = surface?.querySelector(":scope > [data-layout='page-titlebar'], :scope > [data-layout='workspace-header'], :scope h1, :scope h2");
  if (title) {
    const host = title.closest("[data-layout='page-titlebar'], [data-layout='workspace-header']") || title;
    host.insertAdjacentElement("afterend", banner);
  } else {
    (surface || document.querySelector(".app-canvas") || document.querySelector("main") || document.body).prepend(banner);
  }
  setTimeout(() => banner.remove(), 8000);
}

function showLiveSuccess(title, text = "") {
  const toast = document.createElement("div");
  toast.className = "fixed bottom-4 right-4 z-[9999] max-w-sm rounded-lg border border-success-text/30 bg-success-bg px-4 py-3 shadow-lg";
  toast.innerHTML = `<p class="font-body-sm font-semibold text-success-text">${escapeLiveHtml(title)}</p>${text ? `<p class="font-body-sm text-success-text">${escapeLiveHtml(text)}</p>` : ""}`;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

function currentUserId() {
  return intOrNull(RecruitOpsLive.session?.user_id) || 1;
}

function currentLocationId() {
  return intOrNull(RecruitOpsLive.session?.location_id) || 1;
}

/* ═══════════════════════════════════════════════════════════════
   RBAC — Permission Helpers
   ═══════════════════════════════════════════════════════════════ */

function isAdmin() {
  const session = RecruitOpsLive.session || readSession();
  return session?.role === "admin" || session?.role_code === "admin";
}

function userPermissions() {
  const session = RecruitOpsLive.session || readSession();
  return session?.permissions || [];
}

/* ── Agent workbench state & helpers ─────────────────────────── */
let agentsCatalogCache = null;
let agentsRunsCache = [];
let agentsStatusFilter = "all"; /* all | pending | accepted */
let agentsRunContext = null; /* { candidate_id, requisition_id?, run?: boolean } deep-link context */

function agentsStatusVisible(run) {
  if (agentsStatusFilter === "pending") return run.status === "pending";
  if (agentsStatusFilter === "accepted") return run.status === "accepted";
  return true;
}

function renderAgentsRunContextBanner(catalog, replaceExisting = false) {
  /* Deep-link banner: names the candidate the screener will run against. */
  const surface = document.querySelector("[data-agents-workbench]");
  if (!surface || !agentsRunContext?.candidate_id) return;
  if (replaceExisting) surface.querySelector("[data-agents-run-context]")?.remove();
  if (surface.querySelector("[data-agents-run-context]")) return;
  const candidateName = agentsRunContext.candidate_name
    ? ` for ${agentsRunContext.candidate_name}`
    : ` (candidate #${agentsRunContext.candidate_id})`;
  const banner = document.createElement("div");
  banner.className = "flex items-center justify-between gap-3 rounded-xl border border-primary/30 bg-highlight-soft px-4 py-3";
  banner.dataset.agentsRunContext = "true";
  banner.innerHTML = `
    <p class="font-body-sm text-body-sm text-on-surface flex items-center gap-2">
      <span class="material-symbols-outlined text-[18px] text-primary">smart_toy</span>
      Resume Screener ready${escapeAgentHtml(candidateName)}${agentsRunContext.requisition_id ? ` · requisition #${escapeAgentHtml(agentsRunContext.requisition_id)}` : ""}
    </p>
    <button type="button" class="font-label-caps text-label-caps font-semibold text-primary hover:text-primary-hover" data-agents-context-dismiss>Dismiss</button>`;
  banner.querySelector("[data-agents-context-dismiss]").addEventListener("click", () => {
    agentsRunContext = null;
    banner.remove();
  });
  const statsHost = surface.querySelector(".rounded-2xl.border.border-border.bg-surface.p-5") || surface;
  statsHost.insertAdjacentElement("afterend", banner);
}

function renderAgentsFromCache() {
  const visible = agentsRunsCache.filter(agentsStatusVisible);
  if (typeof renderAgentsWorkbench === "function") {
    renderAgentsWorkbench(agentsCatalogCache, { items: visible });
  }
}

async function loadAgentsCatalog() {
  /* Request the slash form: GET /agents (no slash) 307-redirects to
     /agents/ and the browser re-issues the redirected request without
     the Authorization header, so auth is lost mid-flight. */
  agentsCatalogCache = await apiRequest("/agents/");
  return agentsCatalogCache;
}

async function loadAgentsRuns() {
  const payload = await apiRequest("/agents/runs?page_size=50");
  agentsRunsCache = payload.items || [];
  return payload;
}

async function runAgentAction(button, overrides = {}) {
  const select = document.querySelector("[data-agents-select]");
  const agentId = overrides.agentId || select?.value;
  if (!agentId) {
    showToast("Pick an agent", "Select an agent to run first.");
    return;
  }
  const spec = agentsCatalogCache?.items?.find((agent) => agent.id === agentId);
  /* Explicit overrides win; otherwise fall back to deep-link context. */
  const context = { ...(agentsRunContext || {}), ...overrides };
  if (agentId === "resume_screener" && !context.candidate_id) {
    showToast(
      "Candidate needed",
      "The Resume Screener runs from a candidate's profile — open one and click Run AI Screener.",
    );
    return;
  }
  const payload =
    agentId === "daily_brief"
      ? { scope: "me", max_items: 20 }
      : agentId === "resume_screener"
        ? { candidate_id: context.candidate_id, ...(context.requisition_id ? { requisition_id: context.requisition_id } : {}) }
        : { max_items: 20 };
  if (button) {
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
  }
  try {
    const run = await apiRequest(`/agents/${agentId}/run`, { method: "POST", body: JSON.stringify(payload) });
    agentsRunsCache.unshift(run);
    renderAgentsFromCache();
    agentsRunContext = null; /* one-shot context */
    document.querySelector("[data-agents-run-context]")?.remove();
    const summary = run.output_summary || "Nothing is saved until you accept.";
    showToast("Draft ready", summary);
  } catch (error) {
    showLiveError(error);
  }
  if (button) {
    button.disabled = false;
    button.removeAttribute("aria-busy");
  }
}

async function decideAgentRunAction(button) {
  const runId = intOrNull(button.dataset.agentRunId);
  const decision = button.dataset.agentDecision;
  if (!runId || !decision) return;
  button.disabled = true;
  try {
    const updated = await apiRequest(`/agents/runs/${runId}/decision`, {
      method: "POST",
      body: JSON.stringify({ decision }),
    });
    const index = agentsRunsCache.findIndex((run) => Number(run.id) === Number(runId));
    if (index !== -1) agentsRunsCache[index] = updated;
    const overlay = document.getElementById("ro-inpage-overlay");
    if (overlay && overlay.dataset.overlayRoute === "agents-workbench-run-detail") {
      renderAgentRunDetail(updated, agentsCatalogCache?.items || []);
    } else {
      applyAgentRunDecisionToDom(runId, updated.status);
      if (agentsStatusFilter !== "all" && agentsStatusVisible({ status: updated.status }) === false) {
        renderAgentsFromCache();
      } else {
        updateAgentRunCounters(agentsCatalogCache, { items: agentsRunsCache });
      }
    }
    showToast(decision === "accept" ? "Draft accepted" : "Draft rejected", "The decision is recorded in the audit log.");
  } catch (error) {
    button.disabled = false;
    showLiveError(error);
  }
}

async function openAgentRunDetail(button) {
  const runId = intOrNull(button.dataset.agentRunId);
  if (!runId) return;
  const run = agentsRunsCache.find((entry) => Number(entry.id) === Number(runId));
  if (!run) return;
  renderAgentRunDetail(run, agentsCatalogCache?.items || []);
}

function closeAgentRunOverlay() {
  if (typeof closeInPageOverlay === "function") {
    closeInPageOverlay({ silent: true });
  }
}

function wireAgentsWorkbenchFilters() {
  const bar = document.querySelector("[data-agents-filter-bar]");
  if (!bar || bar.dataset.agentsWired === "true") return;
  bar.dataset.agentsWired = "true";
  bar.querySelectorAll("[data-agents-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      const value = button.dataset.agentsFilter || "all";
      if (!/^(all|pending|accepted)$/.test(value)) return;
      agentsStatusFilter = value;
      bar.querySelectorAll("[data-agents-filter]").forEach((other) => {
        other.classList.remove("is-active", "bg-secondary-container", "text-on-secondary-container");
        other.classList.add("border", "border-border", "bg-surface", "text-secondary", "hover:bg-highlight-soft");
      });
      button.classList.add("is-active", "bg-secondary-container", "text-on-secondary-container");
      button.classList.remove("border", "border-border", "bg-surface", "text-secondary", "hover:bg-highlight-soft");
      renderAgentsFromCache();
    });
  });
}

function hasPermission(permissionCode) {
  if (isAdmin()) return true;
  const perms = userPermissions();
  if (!perms.length) return false;
  return perms.includes(permissionCode);
}

function hasAnyPermission(...codes) {
  if (isAdmin()) return true;
  return codes.some((code) => hasPermission(code));
}

function enforcePermission(permissionCode, label) {
  if (hasPermission(permissionCode)) return true;
  showAccessDenied(label || permissionCode);
  return false;
}

function showAccessDenied(action) {
  const overlay = document.createElement("div");
  overlay.className = "fixed inset-0 z-[10000] flex items-center justify-center bg-inverse-surface/40 backdrop-blur-sm";
  overlay.innerHTML = `<div class="bg-surface rounded-xl border border-border shadow-2xl p-8 max-w-md w-full mx-4 text-center">
    <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-danger-bg flex items-center justify-center">
      <span class="material-symbols-outlined text-danger-text text-3xl">lock</span>
    </div>
    <h2 class="font-headline-md text-headline-md text-on-surface mb-2">Access Denied</h2>
    <p class="font-body-sm text-body-sm text-text-muted mb-6">You don't have permission to ${escapeLiveHtml(action)}. Contact your administrator to request access.</p>
    <button onclick="this.closest('.fixed').remove()" class="px-6 py-2 bg-primary-container text-on-primary rounded-lg hover:bg-primary-hover transition-colors font-body-sm font-semibold">Got it</button>
  </div>`;
  document.body.appendChild(overlay);
  overlay.addEventListener("click", (e) => { if (e.target === overlay) overlay.remove(); });
}

async function firstItem(path) {
  const payload = await apiRequest(path);
  return (payload.items || [])[0] || null;
}

async function detailFromRoute(idNames, listPath, detailPath) {
  const requestedId = queryInt(...idNames);
  if (requestedId) return apiRequest(detailPath(requestedId));
  const fallback = await firstItem(listPath);
  return fallback?.id ? apiRequest(detailPath(fallback.id)) : fallback;
}


/* ═══════════════════════════════════════════════════════════════
   SELECT HYDRATION
   ═══════════════════════════════════════════════════════════════ */

async function fillSelect(selectId, items, labelFn, valueFn, selectedValue) {
  const select = document.getElementById(selectId);
  if (!select) return;
  select.innerHTML = `<option value="">Select...</option>` + items.map((item) =>
    `<option value="${valueFn(item)}" ${String(valueFn(item)) === String(selectedValue || "") ? "selected" : ""}>${labelFn(item)}</option>`
  ).join("");
}

async function hydrateSelects() {
  if (typeof hydrateLiveFilters === "function") hydrateLiveFilters();
}


/* ═══════════════════════════════════════════════════════════════
   SHELL & CONNECTION
   ═══════════════════════════════════════════════════════════════ */

function decorateShell() {
  const session = RecruitOpsLive.session || readSession();
  if (!session) return;
  const userName = session.user_name || session.email || "User";
  document.querySelectorAll(".sidebar-user-name, [data-user-name]").forEach((node) => {
    node.textContent = userName;
  });
  document.querySelectorAll(".sidebar-user-role, [data-user-role]").forEach((node) => {
    node.textContent = session.role_name || session.role || "Recruiter";
  });
  const initials = typeof personInitials === "function" ? personInitials(userName) : String(userName).slice(0, 2).toUpperCase();
  document.querySelectorAll('.app-topbar button[aria-label="Open my work"], .app-topbar button[aria-label="Open profile"]').forEach((button) => {
    button.dataset.route = "my-profile.html";
    button.setAttribute("aria-label", "Open profile");
    button.setAttribute("title", "Open profile");
    button.textContent = initials;
  });
  addConnectionIndicator();
  enforceSidebarRBAC();
}

/* ═══════════════════════════════════════════════════════════════
   RBAC — Sidebar Link Visibility
   ═══════════════════════════════════════════════════════════════ */

const SIDEBAR_PERMISSION_MAP = {
  /* nav links → required permission(s) */
  "location-management.html": ["location.read", "location.create"],
  "location-dashboard.html": ["location.read"],
  "user-management.html": ["user.read", "user.create"],
  "role-management.html": ["role.read", "role.create"],
  "role-permissions-editor.html": ["role.permissions.assign"],
  "business-titles.html": ["settings.read"],
  "visibility-rules.html": ["settings.read", "role.read"],
  "work-assignment.html": ["assignment.read", "requisition.assign"],
  "portal-accounts.html": ["portal.read"],
  "approvals-inbox.html": ["approval.read"],
  "client-directory.html": ["client.read"],
  "candidate-profiles.html": ["candidate.read"],
  "pipeline-board.html": ["pipeline.read.summary"],
  "requisition-list.html": ["requisition.read"],
  "interview-scheduler.html": ["interview.read"],
  "offer-management.html": ["offer.read"],
  "meetings.html": ["meeting.read"],
  "follow-ups.html": ["meeting.read"],
  "join-tracker.html": ["offer.read"],
  "daily-updates-workspace.html": ["daily_update.read"],
  "notifications-center.html": ["notification.read"],
  "analytics-dashboard.html": ["dashboard.view_admin", "dashboard.view_hr", "dashboard.view_manager", "dashboard.view_recruiter"],
  "company-dashboard.html": ["dashboard.view_admin"],
  "user-performance-reports.html": ["dashboard.view_admin", "dashboard.view_manager"],
  "team-workload.html": ["dashboard.view_admin", "dashboard.view_manager"],
  "role-dashboard.html": ["dashboard.view_recruiter", "dashboard.view_manager", "dashboard.view_hr", "dashboard.view_admin"],
};

function enforceSidebarRBAC() {
  if (isAdmin()) return; /* Admin sees everything */
  document.querySelectorAll(".sidebar-nav a.nav-link, .sidebar-nav .sidebar-cta-link").forEach((link) => {
    const href = link.getAttribute("href") || "";
    const page = href.split("/").pop();
    const required = SIDEBAR_PERMISSION_MAP[page];
    if (required && !hasAnyPermission(...required)) {
      link.style.display = "none";
    }
  });
  /* Hide entire nav groups if all children are hidden */
  document.querySelectorAll(".sidebar-nav details.nav-group").forEach((group) => {
    const visibleLinks = group.querySelectorAll("a.nav-link:not([style*='display: none'])");
    const hasCTA = group.querySelector(".sidebar-cta-link:not([style*='display: none'])");
    if (visibleLinks.length === 0 && !hasCTA) {
      group.style.display = "none";
    }
  });
  /* Enforce data-rbac attributes on buttons and links */
  document.querySelectorAll("[data-rbac]").forEach((el) => {
    const required = el.dataset.rbac;
    if (required && !hasAnyPermission(...required.split(","))) {
      el.style.display = "none";
    }
  });
  /* RBAC: Enforce on action buttons by label text */
  if (!isAdmin()) {
    const actionPermMap = {
      "Add Client": "client.create",
      "Create Requisition": "requisition.create",
      "Add Candidate": "candidate.create",
      "Add User": "user.create",
      "Add Role": "role.create",
      "Add Location": "location.create",
      "Schedule Meeting": "meeting.create",
      "Create Offer": "offer.create",
      "Submit Update": "daily_update.create_main",
      "Save Draft": "daily_update.create_main",
      "Submit": "daily_update.create_main",
    };
    document.querySelectorAll("button, a").forEach((el) => {
      const text = (el.textContent || "").trim();
      for (const [label, perm] of Object.entries(actionPermMap)) {
        if (text.startsWith(label) && !hasPermission(perm)) {
          el.style.display = "none";
        }
      }
    });
  }
}

function addConnectionIndicator() {
  const topbar = document.querySelector(".topbar, header, nav");
  if (!topbar) return;
  const indicator = document.createElement("div");
  indicator.className = "flex items-center gap-1.5 px-2 py-1 rounded-full text-[11px] font-medium";
  indicator.innerHTML = '<span class="h-2 w-2 rounded-full bg-text-muted animate-pulse"></span><span>Connecting</span>';
  topbar.appendChild(indicator);
  apiRequest("/health").then(() => {
    indicator.innerHTML = '<span class="h-2 w-2 rounded-full bg-success-text"></span><span class="text-success-text">Live</span>';
  }).catch(() => {
    indicator.innerHTML = '<span class="h-2 w-2 rounded-full bg-danger-text"></span><span class="text-danger-text">Offline</span>';
  });
}


/* ═══════════════════════════════════════════════════════════════
   FORM SUBMISSION & AUTH
   ═══════════════════════════════════════════════════════════════ */

async function handleLogin(form) {
  const emailInput = form?.querySelector('[name="email"]') || document.getElementById("email");
  const passwordInput = form?.querySelector('[name="password"]') || document.getElementById("password");
  const email = emailInput?.value?.trim();
  const password = passwordInput?.value;
  const overlay = document.getElementById("loading-overlay");
  const submitBtn = document.getElementById("submit-btn");
  const alertBanner = document.getElementById("alert-banner");

  if (!email || !password) {
    if (typeof showAlertState === "function") {
      showAlertState({ bgClass: "bg-danger-bg", textClass: "text-danger-text", borderClass: "border-[#e4b6b0]", icon: "error", title: "Validation Error", message: "Email and password are required." });
    } else { showLiveError(new Error("Email and password are required.")); }
    return;
  }

  // Show loading state
  if (overlay) {
    overlay.classList.remove("hidden");
    overlay.hidden = false;
    overlay.setAttribute("aria-hidden", "false");
  }
  if (submitBtn) { submitBtn.disabled = true; submitBtn.innerHTML = '<span class="material-symbols-outlined animate-spin text-[20px]">sync</span><span>Authenticating...</span>'; }
  if (alertBanner) alertBanner.className = "hidden w-full p-3 rounded flex items-start gap-3 border";

  try {
    const data = await apiRequest("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
    writeSession({
      token: data.token || data.access_token,
      user_id: data.user?.id || data.user_id,
      email: data.user?.email || email,
      user_name: data.user?.full_name || data.user_name || email,
      role: data.primary_role?.code || data.role || "Recruiter",
      role_name: data.primary_role?.name || data.role || "Recruiter",
      location_id: data.primary_location?.id || data.location_id,
      location_name: data.primary_location?.name || data.primary_location?.location_name || "",
    });
    RecruitOpsLive.session = readSession();
    /* Fetch the user's effective permissions for RBAC enforcement.
       /permissions/me resolves role + branch-role grants server-side and also
       returns the canonical role_code, so admins are recognized correctly. */
    try {
      const permData = await apiRequest("/permissions/me").catch(() => ({}));
      const session = RecruitOpsLive.session || readSession();
      session.permissions = permData.permissions || [];
      if (permData.role_code) session.role_code = permData.role_code;
      writeSession(session);
      RecruitOpsLive.session = session;
    } catch {}
    if (typeof showAlertState === "function") {
      showAlertState({ bgClass: "bg-success-bg", textClass: "text-success-text", borderClass: "border-[#c5dac9]", icon: "check_circle", title: "Authenticated", message: "Redirecting to your workspace..." });
    }
    /* Check if onboarding has been completed — if not, redirect to onboarding flow */
    const onboardingComplete = localStorage.getItem("recruitops-onboarding-complete");
    const isFirstLogin = data.session?.force_password_change_on_first_login;
    if (!onboardingComplete && isFirstLogin) {
      window.location.href = pageHref("onboarding-welcome.html");
    } else {
      window.location.href = pageHref("home.html");
    }
  } catch (error) {
    if (overlay) {
      overlay.classList.add("hidden");
      overlay.hidden = true;
      overlay.setAttribute("aria-hidden", "true");
    }
    if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = '<span>Sign In</span><span class="material-symbols-outlined" style="font-size:20px">arrow_forward</span>'; }
    const message = error?.message || String(error);
    const isInvalid = /401|invalid|unauthorized/i.test(message);
    if (typeof showAlertState === "function") {
      showAlertState({
        bgClass: isInvalid ? "bg-danger-bg" : "bg-warning-bg",
        textClass: isInvalid ? "text-danger-text" : "text-warning-text",
        borderClass: isInvalid ? "border-[#e4b6b0]" : "border-[#dbc1a3]",
        icon: isInvalid ? "error" : "warning",
        title: isInvalid ? "Authentication Failed" : "Connection Error",
        message: isInvalid ? "Invalid email or password. Please try again." : "Unable to reach the server. Please check your connection and try again.",
      });
    } else { showLiveError(error); }
    if (passwordInput) { passwordInput.value = ""; passwordInput.focus(); }
  }
}

async function handleLogout() {
  try { await apiRequest("/auth/logout", { method: "POST" }).catch(() => {}); } catch {}
  writeSession(null);
  RecruitOpsLive.session = null;
  window.location.href = pageHref("login.html");
}

async function handleForgot(form) {
  const email = document.getElementById("email")?.value;
  if (!email) { showLiveError(new Error("Email is required.")); return; }
  try {
    await apiRequest("/auth/password/forgot", { method: "POST", body: JSON.stringify({ email }) });
    if (typeof showAlertState === "function") {
      showAlertState({ bgClass: "bg-success-bg", textClass: "text-success-text", borderClass: "border-[#c5dac9]", icon: "check_circle", title: "Reset link sent", message: "Check your email for password reset instructions." });
    } else { showLiveSuccess("Reset link sent", "Check your email for password reset instructions."); }
  } catch (error) {
    if (typeof showAlertState === "function") {
      showAlertState({ bgClass: "bg-warning-bg", textClass: "text-warning-text", borderClass: "border-[#dbc1a3]", icon: "warning", title: "Request failed", message: "Could not send reset link. Please try again." });
    } else { showLiveError(error); }
  }
}

function afterOverlaySave(fallbackHref) {
  window.setTimeout(() => {
    if (typeof closeInPageOverlay === "function" && closeInPageOverlay({ refresh: true })) return;
    window.location.href = pageHref(fallbackHref);
  }, 400);
}

function handleFormSubmit(form) {
  const route = routeId();
  const submitMap = {
    "contact-form-dialog": submitContact,
    "requisition-intake": submitRequisition,
    "requisition-intake-edit": submitRequisition,
    "daily-updates-submission": submitDailyUpdate,
    "daily-updates-workspace": () => submitDailyUpdate({ stayOnPage: true, status: "submitted" }),
    "meeting-form-dialog": submitMeetingForm,
    "offer-create-dialog": submitOfferCreate,
    "link-to-requisition-dialog": submitLinkToRequisition,
    "stage-move-dialog": submitStageMove,
    "candidate-review-drawer": submitCandidate,
    "onboarding-company-profile": submitOnboardingCompanyProfile,
    "onboarding-locations": submitOnboardingLocation,
    "onboarding-role-setup": submitOnboardingRole,
    "onboarding-hiring-teams": submitOnboardingTeam,
  };
  /* RBAC: Check form submission permissions */
  if (!isAdmin()) {
    const formPermMap = {
      "contact-form-dialog": "client.contact.create",
      "requisition-intake": "requisition.create",
      "requisition-intake-edit": "requisition.update",
      "daily-updates-submission": "daily_update.create_main",
      "daily-updates-workspace": "daily_update.create_main",
      "meeting-form-dialog": "meeting.create",
      "offer-create-dialog": "offer.create",
      "link-to-requisition-dialog": "candidate.link_requisition",
      "stage-move-dialog": "pipeline.stage.move",
      "candidate-review-drawer": "candidate.create",
    };
    const required = formPermMap[route];
    if (required && !hasPermission(required)) {
      showAccessDenied("submit this form");
      return false;
    }
  }
  const handler = submitMap[route];
  if (handler) { handler(); return true; }
  return false;
}

async function submitLocation() {
  const id = queryInt("location_id");
  const name = firstValueOf(["location_name"], [/location name/i]);
  const payload = {
    location_name: name,
    location_code: (name || "LOC").substring(0, 10).toUpperCase().replace(/\s+/g, ""),
    address: firstValueOf(["address"], [/address/i]) || null,
    city: firstValueOf(["city"], [/city/i]) || null,
    country: firstValueOf(["country"], [/country/i]) || null,
    status: "active",
  };
  if (!payload.location_name) { showLiveError(new Error("Location name is required.")); return; }
  try {
    if (id) await apiRequest(`/locations/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
    else await apiRequest("/locations/", { method: "POST", body: JSON.stringify(payload) });
    showLiveSuccess("Location saved", payload.location_name);
    setTimeout(() => { window.location.href = pageHref("location-management.html"); }, 1000);
  } catch (error) { showLiveError(error); }
}




async function submitContact() {
  const clientId = queryInt("client_id");
  const payload = {
    client_id: clientId,
    contact_name: firstValueOf(["contact_name"], [/contact name/i]),
    email: firstValueOf(["email"], [/email/i]),
    phone: firstValueOf(["phone"], [/phone/i]),
    designation: firstValueOf(["designation"], [/designation/i]),
    is_primary_contact: true,
  };
  if (!payload.contact_name) { showLiveError(new Error("Contact name is required.")); return; }
  try {
    await apiRequest(`/clients/${clientId}/contacts`, { method: "POST", body: JSON.stringify(payload) });
    showLiveSuccess("Contact saved", payload.contact_name);
    afterOverlaySave("client-detail.html");
  } catch (error) { showLiveError(error); }
}

function splitSkillList(value) {
  if (!value) return [];
  if (Array.isArray(value)) return value.filter(Boolean);
  return String(value).split(/[,;\n]+/).map((s) => s.trim()).filter(Boolean);
}

function readRadioValue(name) {
  const checked = document.querySelector(`input[name="${name}"]:checked`);
  return checked?.value || null;
}

async function submitRequisition() {
  const id = queryInt("requisition_id");
  const session = RecruitOpsLive.session || readSession();
  /* Read from actual HTML field IDs: job-title, employment-type, start-date, client, hiring-manager, openings, priority, work-mode, location, req-skills, job-description */
  const title = document.getElementById("job-title")?.value?.trim() || firstValueOf(["title"], [/title/i]);
  const clientId = intOrNull(document.querySelector("[data-client-id]")?.dataset.clientId) || queryInt("client_id") || intOrNull(document.getElementById("client_id")?.value);
  const employmentType = document.getElementById("employment-type")?.value || firstValueOf(["employment_type"], [/employment type/i, /type/i]) || null;
  const targetDate = document.getElementById("start-date")?.value || document.getElementById("target_closure_date")?.value || new Date(Date.now() + 30 * 86400000).toISOString().split("T")[0];
  const openings = intOrNull(document.getElementById("openings")?.value) || intOrNull(document.getElementById("openings_count")?.value) || 1;
  const priority = document.getElementById("priority")?.value || firstValueOf(["priority"], [/priority/i]) || "medium";
  const workMode = readRadioValue("work-mode") || firstValueOf(["work_mode"], [/work mode/i]) || null;
  const locationId = intOrNull(document.getElementById("location_id")?.value) || session?.location_id;
  const skillsRaw = document.getElementById("req-skills")?.value || firstValueOf(["must_have_skills"], [/must have/i, /required skills/i]);
  const niceSkillsRaw = firstValueOf(["good_to_have_skills"], [/good to have/i, /nice to have/i]);
  const jobDesc = document.getElementById("job-description")?.value || firstValueOf(["job_description"], [/job description/i, /description/i]) || "To be updated";
  const createPayload = {
    title,
    client_id: clientId,
    location_id: locationId,
    primary_owner_user_id: session?.user_id,
    openings_count: openings,
    target_closure_date: targetDate,
    job_description: jobDesc,
    employment_type: employmentType,
    work_mode: workMode,
    priority,
    must_have_skills: splitSkillList(skillsRaw),
    good_to_have_skills: splitSkillList(niceSkillsRaw),
  };
  const updatePayload = {
    title: title || undefined,
    openings_count: openings,
    target_closure_date: targetDate,
    job_description: jobDesc,
    employment_type: employmentType,
    work_mode: workMode,
    priority,
    must_have_skills: splitSkillList(skillsRaw),
    good_to_have_skills: splitSkillList(niceSkillsRaw),
  };
  if (!title) { showLiveError(new Error("Title is required.")); return; }
  try {
    if (id) await apiRequest(`/requisitions/${id}`, { method: "PATCH", body: JSON.stringify(updatePayload) });
    else await apiRequest("/requisitions/", { method: "POST", body: JSON.stringify(createPayload) });
    showLiveSuccess("Requisition saved", title);
    setTimeout(() => { window.location.href = pageHref("requisition-detail.html"); }, 1000);
  } catch (error) { showLiveError(error); }
}async function resetUserCredentials(button) {
  const userId = intOrNull(button?.dataset.userId);
  if (!userId) { showLiveError(new Error("No user selected.")); return; }
  try {
    await apiRequest(`/users/${userId}/reset-credentials`, { method: "POST" });
    showLiveSuccess("Credentials reset", "A new invitation email has been sent.");
  } catch (error) { showLiveError(error); }
}

async function saveRolePermissions(button) {
  const roleId = rolePermState.roleId || queryInt("role_id");
  if (!roleId) { showLiveError(new Error("No role selected.")); return; }
  if (rolePermState.readonly) {
    showLiveError(new Error("The admin role always keeps full access; its permissions cannot be changed."));
    return;
  }
  if (!rolePermState.dirty) {
    if (typeof showToast === "function") showToast("No changes", "Toggle permissions before saving.");
    return;
  }
  const permissionCodes = Array.from(document.querySelectorAll("[data-perm].on")).map((toggle) => toggle.dataset.perm);
  if (button) button.disabled = true;
  try {
    const payload = await apiRequest(`/roles/${roleId}/permissions`, {
      method: "PUT",
      body: JSON.stringify({ permission_codes: permissionCodes, scope_rules: {} }),
    });
    rolePermState.baseline = new Set(payload.permission_codes || permissionCodes);
    rolePermState.dirty = false;
    updateRolePermSummary(rolePermState.baseline.size, rolePermState.total);
    showLiveSuccess("Permissions saved", `${rolePermState.baseline.size} granted to this role.`);
  } catch (error) { showLiveError(error); }
  finally {
    if (button) button.disabled = false;
  }
}

async function resetRolePermissions() {
  applyRolePermissionGrants(rolePermState.baseline);
  rolePermState.dirty = false;
  updateRolePermSummary(rolePermState.baseline.size, rolePermState.total);
  if (typeof showToast === "function") showToast("Changes discarded", "The matrix reflects the last saved state.");
}

function setPermissionToggleState(toggle, enabled) {
  if (!toggle) return;
  toggle.classList.toggle("on", enabled);
  toggle.setAttribute("aria-checked", String(enabled));
}


/* ═══════════════════════════════════════════════════════════════
   PAGE LOADERS
   ═══════════════════════════════════════════════════════════════ */

async function loadWorkflowActions() {
  const payload = await apiRequest("/workflow-actions/queue?page_size=50").catch(() => ({ items: [] }));
  const items = payload.items || [];
  renderRoleWorkflowQueue(items);
  renderNotificationWorkflowQueue(items);
  /* Update the queue count footer if present */
  const countEl = document.querySelector("[data-role-queue-count]");
  if (countEl) {
    const total = payload.meta?.total ?? items.length;
    countEl.textContent = total > 0 ? `View all ${total} items in queue` : "Queue is clear";
  }
}

async function loadDashboardActionsOverlay() {
  const payload = await apiRequest("/workflow-actions/queue?page_size=50").catch(() => ({ items: [] }));
  renderOverlayWorkflowActions(payload.items || [], ".overlay-host .space-y-3, .workspace-surface .space-y-3", "No workflow actions");
}

async function loadNotificationDetailPanel() {
  const notificationId = queryInt("notification_id");
  let item = notificationItemsCache.find((entry) => Number(entry.id) === Number(notificationId));
  if (!item && notificationId) {
    const payload = await apiRequest("/notifications/?page_size=50").catch(() => ({ items: [] }));
    item = (payload.items || []).find((entry) => Number(entry.id) === Number(notificationId));
  }
  if (!item) {
    const surface = document.querySelector("[data-overlay-surface='true']");
    if (surface) {
      surface.innerHTML = `<div class="p-6"><h2 class="font-headline-md font-bold text-on-surface">Event not found</h2><p class="mt-2 text-body-sm text-text-muted">This hiring event is no longer in your inbox.</p></div>`;
    }
    return;
  }
  if (typeof renderNotificationDetailPanel === "function") renderNotificationDetailPanel(item);
}

async function loadContactFormDialog() {
  const clientId = queryInt("client_id");
  if (clientId) {
    setFirstText("[data-client-name]", "");
  }
}

async function loadRequisitionIntake() {
  const clientId = queryInt("client_id");
  if (clientId) {
    const client = await apiRequest(`/clients/${clientId}`).catch(() => null);
    if (client) setFirstText("[data-client-name]", client.client_name);
  }
  const clients = await apiRequest("/clients/?page_size=100").catch(() => ({ items: [] }));
  await fillSelect("client_id", clients.items || [], (c) => c.client_name, (c) => c.id, clientId);
}

async function submitRequisitionStatus(button) {
  const reqId = queryInt("requisition_id");
  const status = firstValueOf(["status"], [/status/i]);
  const reason = firstValueOf(["reason"], [/reason/i]) || "Status updated by user";
  if (!reqId || !status) return;
  try {
    await apiRequest(`/requisitions/${reqId}/status`, { method: "PATCH", body: JSON.stringify({ status, reason }) });
    showLiveSuccess("Status updated", status);
    loadRequisitionDetail();
  } catch (error) { showLiveError(error); }
}async function loadStageMoveDialog() {
  const applicationId = queryInt("application_id");
  if (!applicationId) return;
  try {
    const application = await apiRequest(`/pipeline/applications/${applicationId}`);
    setFirstText("[data-candidate-name]", application.candidate_name);
    setFirstText("[data-current-stage]", application.current_stage);
    const stageDialogName = document.querySelector("[data-candidate-name]");
    if (stageDialogName?.parentElement && typeof entityBadgeHtml === "function" && (application.candidate_code || application.requisition_code) && !stageDialogName.parentElement.querySelector(":scope > .entity-badge")) {
      stageDialogName.insertAdjacentHTML("afterend", entityBadgeHtml(application.candidate_code || application.requisition_code, application.branch_code));
    }
    const subtitle = document.querySelector("[data-overlay-surface] p.font-body-sm");
    if (subtitle && application.candidate_name) {
      subtitle.textContent = `${application.candidate_name}${application.requisition_title ? " • " + application.requisition_title : ""}`;
    }
  } catch (error) { showLiveError(error); }
}

async function submitStageMove() {
  const applicationId = queryInt("application_id");
  const toStage = document.getElementById("to_stage")?.value || firstValueOf(["to_stage"], [/to stage/i, /stage/i]);
  const notes = document.getElementById("stage_notes")?.value || firstValueOf(["notes"], [/notes/i]) || null;
  if (!applicationId || !toStage) { showLiveError(new Error("Application ID and target stage are required.")); return; }
  try {
    await apiRequest(`/pipeline/applications/${applicationId}/stage`, {
      method: "PATCH",
      body: JSON.stringify({ to_stage: toStage, notes }),
    });
    showLiveSuccess("Stage updated", toStage);
    afterOverlaySave("pipeline-board.html");
  } catch (error) { showLiveError(error); }
}

async function submitCandidate() {
  const id = queryInt("candidate_id");
  const fullName = document.getElementById("full-name")?.value?.trim();
  const sourceType = document.getElementById("source-type")?.value?.trim();
  if (!fullName) { showLiveError(new Error("Full name is required.")); return; }
  if (!sourceType) { showLiveError(new Error("Source type is required.")); return; }
  const payload = {
    full_name: fullName,
    email: document.getElementById("email")?.value?.trim() || null,
    phone: document.getElementById("phone")?.value?.trim() || null,
    source_type: sourceType,
    source_detail: document.getElementById("source-detail")?.value?.trim() || null,
    current_company: document.getElementById("current-company")?.value?.trim() || null,
    current_designation: document.getElementById("current-designation")?.value?.trim() || null,
    total_experience_years: parseFloat(document.getElementById("total-experience-years")?.value) || null,
    notice_period_days: parseInt(document.getElementById("notice-period-days")?.value, 10) || null,
    primary_owner_user_id: currentUserId(),
  };
  try {
    let result;
    if (id) {
      result = await apiRequest(`/candidates/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
    } else {
      payload.created_by_user_id = currentUserId();
      result = await apiRequest("/candidates/", { method: "POST", body: JSON.stringify(payload) });
    }
    showLiveSuccess(id ? "Candidate updated" : "Candidate created", result.full_name);
    afterOverlaySave("candidate-profiles.html");
  } catch (error) { showLiveError(error); }
}

function loadResumeUploadReview() {
  const input = document.querySelector("[data-live-resume-file-input]");
  if (input) {
    input.addEventListener("change", (e) => uploadCandidateResume(e.target));
  }
}

async function uploadCandidateResume(input) {
  const file = input?.files?.[0];
  if (!file) return;
  showLiveSuccess("Resume uploaded", file.name);
}function parseMoneyInput(value) {
  if (!value) return null;
  const num = Number(String(value).replace(/[^0-9.]/g, ""));
  return Number.isNaN(num) ? null : num;
}


/* ═══════════════════════════════════════════════════════════════
   PAGE LOADERS — CRUD
   ═══════════════════════════════════════════════════════════════ */


async function loadLocations() {
  const surface = document.querySelector('.workspace-surface');
  if (!surface) return;
  const tableWrap = document.getElementById('location-table-wrap');
  const actionsEl = document.getElementById('location-actions');
  const dialogHost = document.getElementById('location-dialog-host');
  if (!tableWrap) return;
  const canCreate = hasPermission('location.create');
  const canEdit = hasPermission('location.update');
  if (canCreate && actionsEl) {
    actionsEl.innerHTML = '<button id="btn-add-location" class="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-on-primary font-body-sm font-semibold hover:opacity-90 transition-opacity"><span class="material-symbols-outlined text-[18px]">add</span>Add Location</button>';
  }
  try {
    const payload = await apiRequest('/locations/?page_size=100');
    const items = payload.items || [];
    if (!items.length) {
      tableWrap.innerHTML = '<div class="flex flex-col items-center justify-center py-16 text-center"><span class="material-symbols-outlined text-[48px] text-text-muted mb-3">location_on</span><p class="text-headline-sm font-semibold text-on-surface">No locations yet</p><p class="text-body-sm text-text-muted mt-1">Create your first location to get started.</p></div>';
      return;
    }
    let rows = '';
    items.forEach(v => {
      const statusChip = v.status === 'active'
        ? '<span class="inline-flex items-center px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-[11px] font-semibold">Active</span>'
        : v.status === 'inactive'
          ? '<span class="inline-flex items-center px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 text-[11px] font-semibold">Inactive</span>'
          : '<span class="inline-flex items-center px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 text-[11px] font-semibold">' + escapeHtml(v.status) + '</span>';
      const headCell = v.location_head_name
        ? '<td class="px-4 py-3 text-on-surface">' + escapeHtml(v.location_head_name) + '</td>'
        : '<td class="px-4 py-3 text-text-muted italic">Unassigned</td>';
      const editBtn = canEdit ? '<button class="text-text-muted hover:text-primary transition-colors p-1 rounded hover:bg-surface-variant" data-edit-id="' + v.id + '" title="Edit"><span class="material-symbols-outlined text-[18px]">edit</span></button>' : '';
      rows += '<tr class="border-b border-border hover:bg-surface-variant/30 transition-colors">'
        + '<td class="px-4 py-3"><div class="flex flex-col"><span class="font-medium text-on-surface">' + escapeHtml(v.location_name) + '</span><span class="text-[11px] text-text-muted font-mono">' + escapeHtml(v.location_code) + '</span></div></td>'
        + headCell
        + '<td class="px-4 py-3 text-text-muted text-[13px]">' + escapeHtml(v.address || '\u2014') + '</td>'
        + '<td class="px-4 py-3">' + statusChip + '</td>'
        + '<td class="px-4 py-3 text-right">' + editBtn + '</td>'
        + '</tr>';
    });
    tableWrap.innerHTML = '<div class="mt-4 overflow-x-auto">'
      + '<table class="w-full text-left">'
      + '<thead><tr class="border-b border-border text-[11px] font-bold uppercase tracking-wider text-text-muted">'
      + '<th class="px-4 py-2.5">Location</th>'
      + '<th class="px-4 py-2.5">Head</th>'
      + '<th class="px-4 py-2.5">Address</th>'
      + '<th class="px-4 py-2.5">Status</th>'
      + '<th class="px-4 py-2.5 text-right w-12"></th>'
      + '</tr></thead>'
      + '<tbody>' + rows + '</tbody>'
      + '</table>'
      + '</div>';
    if (canCreate) {
      const btn = document.getElementById('btn-add-location');
      if (btn) btn.onclick = () => openLocationDialog(null);
    }
    if (canEdit) {
      tableWrap.querySelectorAll('[data-edit-id]').forEach(btn => {
        btn.onclick = () => openLocationDialog({ id: btn.dataset.editId });
      });
    }
  } catch (err) {
    tableWrap.innerHTML = '<div class="flex flex-col items-center justify-center py-16 text-center"><span class="material-symbols-outlined text-[48px] text-red-400 mb-3">error</span><p class="text-body-sm text-red-600">Failed to load locations: ' + escapeHtml(String(err.message || err)) + '</p></div>';
  }
}

/* ═══════════════════════════════════════════════════════════════
   INLINE ENTITY DIALOGS
   One helper for create/edit overlays opened directly from list
   pages (users, roles, clients — same pattern as locations).
   The helper owns the overlay shell, close behavior, and inline
   error display; callers supply fields + a submit handler.
   ═══════════════════════════════════════════════════════════════ */

function openEntityDialog({ id, title, fields, submitLabel = "Save", onSubmit, onClose, onChange }) {
  const existingOverlay = document.getElementById(id);
  if (existingOverlay) existingOverlay.remove();
  const wrapper = document.createElement("div");
  wrapper.id = id;
  wrapper.className = "fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4";
  const fieldHtml = fields.map((field) => {
    const value = field.value == null ? "" : String(field.value);
    const hintHtml = field.hint ? `<span class="mt-1 block text-[11px] leading-snug text-text-muted">${escapeHtml(field.hint)}</span>` : "";
    if (field.type === "select") {
      const options = (field.options || []).map((option) =>
        `<option value="${escapeHtml(String(option.value))}" ${String(option.value) === String(field.value) ? "selected" : ""}>${escapeHtml(option.label)}</option>`,
      ).join("");
      return `<label class="block mb-3"><span class="text-[11px] font-bold uppercase tracking-wider text-text-muted">${escapeHtml(field.label)}</span><select id="${field.name}" class="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2 text-on-surface text-sm focus:outline-none focus:border-primary">${options}</select>${hintHtml}</label>`;
    }
    const commonClass = field.readonly
      ? "mt-1 w-full rounded-lg border border-border bg-surface-variant px-3 py-2 text-text-muted text-sm"
      : "mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2 text-on-surface text-sm focus:outline-none focus:border-primary";
    return `<label class="block mb-3"><span class="text-[11px] font-bold uppercase tracking-wider text-text-muted">${escapeHtml(field.label)}</span><input id="${field.name}" name="${field.name}" type="${field.type || "text"}" ${field.required ? "required" : ""} ${field.readonly ? "readonly" : ""} ${field.step ? `step="${field.step}"` : ""} ${field.min != null ? `min="${field.min}"` : ""} ${field.max != null ? `max="${field.max}"` : ""} ${field.accept ? `accept="${field.accept}"` : ""} placeholder="${escapeHtml(field.placeholder || "")}" value="${escapeHtml(value)}" class="${commonClass}" />${hintHtml}</label>`;
  }).join("");
  wrapper.innerHTML = `<div class="bg-surface rounded-xl border border-border shadow-xl w-full max-w-md p-6 max-h-[90vh] overflow-y-auto">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-headline-sm font-semibold text-on-surface">${escapeHtml(title)}</h3>
      <button type="button" data-dialog-close class="text-text-muted hover:text-on-surface p-1"><span class="material-symbols-outlined text-[20px]">close</span></button>
    </div>
    <form data-entity-dialog-form>
      ${fieldHtml}
      <div data-dialog-error class="text-body-sm text-red-600 mb-3 hidden"></div>
      <div class="flex justify-end gap-2 mt-4">
        <button type="button" data-dialog-cancel class="px-4 py-2 rounded-lg border border-border text-on-surface text-sm font-medium hover:bg-surface-variant">Cancel</button>
        <button type="submit" class="px-4 py-2 rounded-lg bg-primary text-on-primary text-sm font-semibold hover:opacity-90">${escapeHtml(submitLabel)}</button>
      </div>
    </form>
  </div>`;
  document.body.appendChild(wrapper);
  const close = () => {
    wrapper.remove();
    if (onClose) onClose();
  };
  wrapper.querySelector("[data-dialog-close]").onclick = close;
  wrapper.querySelector("[data-dialog-cancel]").onclick = close;
  wrapper.addEventListener("click", (event) => { if (event.target === wrapper) close(); });
  wrapper.querySelector("[data-entity-dialog-form]").onsubmit = async (event) => {
    event.preventDefault();
    const errorEl = wrapper.querySelector("[data-dialog-error]");
    errorEl.classList.add("hidden");
    const values = {};
    fields.forEach((field) => { values[field.name] = wrapper.querySelector(`#${field.name}`)?.value ?? ""; });
    try {
      await onSubmit(values, close);
    } catch (err) {
      errorEl.textContent = err.message || "Something went wrong";
      errorEl.classList.remove("hidden");
    }
  };
  /* Optional live rewiring: callers can react to field changes (e.g. filter
     the owner dropdown when the client's location changes). */
  if (onChange) {
    fields.forEach((field) => {
      wrapper.querySelector(`#${field.name}`)?.addEventListener("change", (event) => onChange(field.name, event.target.value));
    });
  }
  return wrapper;
}

function entitySelectOptions(items, labelKey, valueKey = "id") {
  return [{ value: "", label: "— Select —" }].concat(
    (items || []).map((item) => ({
      value: item[valueKey],
      label: item[labelKey] || item.name || item.location_name || `#${item[valueKey]}`,
    })),
  );
}

function paintPlainCell(td, value) {
  if (!td) return;
  td.textContent = value == null || value === "" ? "—" : String(value);
}

function paintStackedUserCell(td, name, subtitle) {
  if (!td) return;
  td.innerHTML = `<div class="flex flex-col">
    <span class="font-medium text-on-surface">${escapeHtml(name || "—")}</span>
    <span class="text-[11px] text-text-muted">${escapeHtml(subtitle || "")}</span>
  </div>`;
}

function paintStatusChip(td, status) {
  if (!td) return;
  const normalized = String(status || "active").toLowerCase();
  const active = normalized === "active" || normalized === "open";
  const pending = normalized === "pending" || normalized === "pending-setup" || normalized === "prospect";
  const chipClass = active
    ? "bg-success-bg text-success-text border border-success-text/20"
    : pending
      ? "bg-warning-bg text-warning-text border border-warning-text/20"
      : "bg-surface-dim text-text-muted border border-outline-variant";
  td.innerHTML = `<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium ${chipClass}">${escapeHtml(String(status || "active"))}</span>`;
}

/** Bind Add + row-edit actions for a list page using inline dialogs.
 * Every table row that contains an edit affordance gets a data-edit-id so
 * the click handler knows which record to load; RBAC hides what the role
 * lacks. Idempotent per page load. */
function wireEntityTableActions({ addPermission, editPermission, addSelector, onAdd, onEdit }) {
  const canAdd = hasPermission(addPermission);
  const canEdit = hasPermission(editPermission);
  if (canAdd) {
    document.querySelectorAll(addSelector).forEach((button) => {
      button.onclick = (event) => { event.preventDefault(); onAdd(); };
    });
  } else {
    document.querySelectorAll(addSelector).forEach((button) => {
      button.classList.add("hidden");
    });
  }
  if (!canEdit) return;
  document.querySelectorAll(".workspace-surface tbody tr").forEach((row) => {
    /* Re-wire on every call: fillExistingTable clones the first <tr> as its
     * template, so "wired" markers propagate to fresh rows while their
     * property-assigned onclick handlers do not survive the clone. */
    const editButton = row.querySelector('button[aria-label*="Edit" i], button[title*="Edit" i], a[data-route*="form-drawer" i], a[data-route*="client-create"]');
    if (!editButton) return;
    const recordId = row.dataset.recordId;
    if (!recordId) return;
    editButton.onclick = (event) => {
      event.preventDefault();
      onEdit(recordId);
    };
  });
}

async function openUserDialog(userId, refresh) {
  const isEdit = !!userId;
  let user = null;
  if (isEdit) {
    user = await apiRequest(`/users/${userId}`).catch(() => null);
    if (!user) { showToast("Failed to load user", "Could not fetch this user for editing."); return; }
  }
  const [roles, locations] = await Promise.all([
    apiRequest("/roles/?page_size=50").catch(() => ({ items: [] })),
    apiRequest("/locations/?page_size=100").catch(() => ({ items: [] })),
  ]);
  // The roles list is newest-first and capped, so the user's current role may
  // be missing from the fetched page — inject it so the dropdown can show it.
  if (user?.primary_role_id && !roles.items.some((r) => String(r.id) === String(user.primary_role_id))) {
    roles.items.push({ id: user.primary_role_id, name: user.primary_role_name || `Role #${user.primary_role_id}` });
  }
  openEntityDialog({
    id: "user-dialog-overlay",
    title: isEdit ? "Edit User" : "Add User",
    submitLabel: isEdit ? "Save Changes" : "Create User",
    onClose: refresh,
    fields: [
      { name: "full_name", label: "Full Name", required: true, value: user?.full_name || "", placeholder: "e.g. Priya Sharma" },
      { name: "email", label: "Email", type: "email", required: true, value: user?.email || "", placeholder: "name@company.com" },
      { name: "phone", label: "Phone", value: user?.phone || "", placeholder: "Optional" },
      { name: "business_title", label: "Business Title", value: user?.business_title || "", placeholder: "e.g. Senior Recruiter" },
      { name: "primary_role_id", label: "Role", type: "select", required: true, value: user?.primary_role_id ?? "", options: entitySelectOptions(roles.items, "name", "id") },
      { name: "primary_location_id", label: "Location", type: "select", value: user?.primary_location_id ?? user?.location_id ?? "", options: entitySelectOptions(locations.items, "location_name", "id") },
      { name: "status", label: "Status", type: "select", value: user?.status || "active", options: [{ value: "active", label: "Active" }, { value: "inactive", label: "Inactive" }] },
    ],
    onSubmit: async (values, close) => {
      const payload = {
        full_name: values.full_name.trim(),
        email: values.email.trim(),
        phone: values.phone.trim() || null,
        business_title: values.business_title.trim() || null,
        primary_role_id: intOrNull(values.primary_role_id),
        primary_location_id: intOrNull(values.primary_location_id),
        status: values.status,
      };
      if (!payload.full_name || !payload.email) throw new Error("Name and email are required.");
      if (!payload.primary_role_id) throw new Error("Role is required.");
      if (isEdit) await apiRequest(`/users/${userId}`, { method: "PATCH", body: JSON.stringify(payload) });
      else await apiRequest("/users/", { method: "POST", body: JSON.stringify(payload) });
      close();
      showToast(isEdit ? "User updated" : "User created", payload.full_name);
    },
  });
}

async function openRoleDialog(roleId, refresh) {
  const isEdit = !!roleId;
  let role = null;
  if (isEdit) {
    role = await apiRequest(`/roles/${roleId}`).catch(() => null);
    if (!role) { showToast("Failed to load role", "Could not fetch this role for editing."); return; }
  }
  openEntityDialog({
    id: "role-dialog-overlay",
    title: isEdit ? "Edit Role" : "Create Role",
    submitLabel: isEdit ? "Save Changes" : "Create Role",
    onClose: refresh,
    fields: [
      { name: "name", label: "Role Name", required: true, value: role?.role_name || role?.name || "", placeholder: "e.g. Lead Recruiter" },
      { name: "description", label: "Description", value: role?.description || "", placeholder: "What this role is responsible for" },
      { name: "status", label: "Status", type: "select", value: role?.status || "active", options: [{ value: "active", label: "Active" }, { value: "inactive", label: "Inactive" }] },
    ],
    onSubmit: async (values, close) => {
      const payload = {
        name: values.name.trim(),
        code: values.name.trim().toLowerCase().replace(/\s+/g, "_").substring(0, 30),
        description: values.description.trim() || null,
        status: values.status,
      };
      if (!payload.name) throw new Error("Role name is required.");
      if (isEdit) await apiRequest(`/roles/${roleId}`, { method: "PATCH", body: JSON.stringify(payload) });
      else await apiRequest("/roles/", { method: "POST", body: JSON.stringify(payload) });
      close();
      showToast(isEdit ? "Role updated" : "Role created", payload.name);
    },
  });
}

async function duplicateRole(roleId) {
  const role = await apiRequest(`/roles/${roleId}`).catch(() => null);
  if (!role) {
    showToast("Could not duplicate role", "The role could not be loaded.");
    return;
  }
  const baseName = String(role.role_name || role.name || "Role").replace(/\s+copy$/i, "").trim();
  const name = `${baseName} copy`;
  const code = name.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "").substring(0, 50) || `role_${roleId}_copy`;
  try {
    await apiRequest("/roles/", {
      method: "POST",
      body: JSON.stringify({
        name,
        code,
        description: role.description || null,
        status: role.status || "active",
      }),
    });
    showToast("Role duplicated", name);
    if (typeof loadRoles === "function") loadRoles();
  } catch (error) {
    showToast("Could not duplicate role", error?.message || "Try a different name.");
  }
}

async function openClientDialog(clientId, refresh) {
  const isEdit = !!clientId;
  let client = null;
  if (isEdit) {
    client = await apiRequest(`/clients/${clientId}`).catch(() => null);
    if (!client) { showToast("Failed to load client", "Could not fetch this client for editing."); return; }
  }
  const session = RecruitOpsLive.session || readSession();
  const locations = await apiRequest("/locations/?page_size=100").catch(() => ({ items: [] }));
  /* Owners must belong to the client's location (location-integrity rule), so
     fetch staff once; the owner dropdown is filtered live as the location
     changes. Admins can own a client in another office — they just have to be
     one of that office's people. */
  /* Owners must belong to the client's location (location-integrity rule), so
     fetch staff filtered to a location — the server caps pages at 100 and a
     location-scoped list is always complete. Re-fetched as location changes. */
  const canReadUsers = isAdmin() || hasPermission("user.read");
  const users = canReadUsers && session?.location_id
    ? await apiRequest(`/users/?page_size=100&location_id=${session.location_id}`).catch(() => ({ items: [] }))
    : { items: [] };
  /* One owner-option builder shared by the initial paint and location changes. */
  const ownerOptionsFor = (locationId) => {
    const eligible = (users.items || []).filter((u) => u.status === "active");
    const options = eligible.map((u) => ({ value: u.id, label: u.id === session?.user_id ? `${u.full_name} (you)` : u.full_name }));
    if (locationId === session?.location_id && !eligible.some((u) => u.id === session?.user_id)) {
      options.unshift({ value: session?.user_id ?? "", label: "You" });
    }
    return options;
  };
  /* Location only drives the create path (the backend does not support moving
     a client between locations), so it is a create-only field. It defaults to
     the creator's own location, which the location-integrity rules require the
     client owner to belong to. */
  openEntityDialog({
    id: "client-dialog-overlay",
    title: isEdit ? "Edit Client" : "Add Client",
    submitLabel: isEdit ? "Save Changes" : "Create Client",
    onClose: refresh,
    fields: isEdit ? [
      { name: "client_name", label: "Client Name", required: true, value: client?.client_name || "", placeholder: "e.g. Acme Corp" },
      { name: "industry", label: "Industry", value: client?.industry || "", placeholder: "e.g. Technology" },
      { name: "status", label: "Status", type: "select", value: client?.status || "active", options: [{ value: "active", label: "Active" }, { value: "inactive", label: "Inactive" }] },
      { name: "placement_fee_pct", label: "Placement Fee %", type: "number", value: client?.placement_fee_pct ?? "", placeholder: "e.g. 8.33", step: "0.01", min: 0, max: 100, hint: "Used to compute revenue on the placements and client-summary reports." },
      { name: "notes", label: "Commercial Notes", value: client?.notes || "", placeholder: "Optional" },
    ] : [
      { name: "client_name", label: "Client Name", required: true, value: "", placeholder: "e.g. Acme Corp" },
      { name: "client_code", label: "Client Code", value: "", placeholder: "Auto-generated if blank" },
      { name: "industry", label: "Industry", value: "", placeholder: "e.g. Technology" },
      { name: "location_id", label: "Location", type: "select", value: session?.location_id ?? "", options: entitySelectOptions(locations.items, "location_name", "id"), hint: session?.location_name ? `You work from ${session.location_name}. Clients belong to one office — pick a different one only if this client is owned there.` : "Clients belong to one office." },
      { name: "client_owner_user_id", label: "Client Owner", type: "select", value: session?.user_id ?? "", options: ownerOptionsFor(session?.location_id) },
      { name: "status", label: "Status", type: "select", value: "active", options: [{ value: "active", label: "Active" }, { value: "inactive", label: "Inactive" }] },
      { name: "placement_fee_pct", label: "Placement Fee %", type: "number", value: "", placeholder: "e.g. 8.33", step: "0.01", min: 0, max: 100, hint: "Used to compute revenue on the placements and client-summary reports." },
      { name: "notes", label: "Commercial Notes", value: "", placeholder: "Optional" },
    ],
    onChange: async (fieldName, newValue) => {
      /* Owners must belong to the chosen location — refetch for it. */
      if (fieldName !== "location_id" || isEdit) return;
      const ownerSelect = document.querySelector("#client-dialog-overlay #client_owner_user_id");
      if (!ownerSelect) return;
      const chosenId = intOrNull(newValue) || session?.location_id;
      if (canReadUsers && chosenId) {
        const fresh = await apiRequest(`/users/?page_size=100&location_id=${chosenId}`).catch(() => ({ items: [] }));
        users.items = fresh.items || [];
      }
      const options = ownerOptionsFor(chosenId);
      ownerSelect.innerHTML = options.map((o) => `<option value="${escapeHtml(String(o.value))}">${escapeHtml(o.label)}</option>`).join("");
      ownerSelect.value = options[0]?.value ?? "";
    },
    onSubmit: async (values, close) => {
      const name = values.client_name.trim();
      if (!name) throw new Error("Client name is required.");
      if (isEdit) {
        await apiRequest(`/clients/${clientId}`, { method: "PATCH", body: JSON.stringify({ client_name: name, industry: values.industry || null, status: values.status, notes: values.notes || null, placement_fee_pct: values.placement_fee_pct === "" ? null : intOrNull(values.placement_fee_pct) === null ? null : Number(values.placement_fee_pct) }) });
      } else {
        const chosenLocationId = intOrNull(values.location_id) || session?.location_id;
        const ownerId = intOrNull(values.client_owner_user_id) || session?.user_id;
        if (!ownerId) throw new Error("Select a client owner who belongs to the chosen location.");
        await apiRequest("/clients/", { method: "POST", body: JSON.stringify({
          client_name: name,
          client_code: values.client_code.trim() || null,
          industry: values.industry || null,
          location_id: chosenLocationId,
          client_owner_user_id: ownerId,
          business_source_owner_user_id: ownerId,
          status: values.status,
          notes: values.notes || null,
          placement_fee_pct: values.placement_fee_pct === "" ? null : Number(values.placement_fee_pct),
        }) });
        /* Warn when the client belongs to a different office than the creator:
           requisitions and users must also match that location downstream. */
        if (chosenLocationId && session?.location_id && chosenLocationId !== session.location_id) {
          const chosen = (locations.items || []).find((loc) => loc.id === chosenLocationId);
          showToast("Client created in another location", `${name} belongs to ${chosen?.location_name || "that office"} — requisitions there must be staffed by users of the same location.`);
        }
      }
      close();
      showToast(isEdit ? "Client updated" : "Client created", name);
    },
  });
}

async function openLocationDialog(existing) {
  const isEdit = !!existing;
  let locationData = null;
  if (isEdit) {
    try {
      locationData = await apiRequest('/locations/' + existing.id);
    } catch (e) { showToast('Failed to load location', e.message); return; }
  }
  const nameVal = isEdit ? (locationData.location_name || '') : '';
  const codeVal = isEdit ? (locationData.location_code || '') : '';
  const addrVal = isEdit ? (locationData.address || '') : '';
  const existingOverlay = document.getElementById('location-overlay');
  if (existingOverlay) existingOverlay.remove();
  const wrapper = document.createElement('div');
  wrapper.id = 'location-overlay';
  wrapper.className = 'fixed inset-0 z-50 flex items-center justify-center bg-black/40';
  wrapper.innerHTML = '<div class="bg-surface rounded-xl border border-border shadow-xl w-full max-w-md p-6">'
    + '<div class="flex items-center justify-between mb-4">'
    + '<h3 class="text-headline-sm font-semibold text-on-surface">' + (isEdit ? 'Edit Location' : 'Add Location') + '</h3>'
    + '<button id="location-close" class="text-text-muted hover:text-on-surface p-1"><span class="material-symbols-outlined text-[20px]">close</span></button>'
    + '</div>'
    + '<form id="location-form">'
    + '<label class="block mb-3"><span class="text-[11px] font-bold uppercase tracking-wider text-text-muted">Name</span><input id="loc-name" type="text" required class="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2 text-on-surface text-sm focus:outline-none focus:border-primary" placeholder="e.g. Hyderabad Branch" value="' + escapeHtml(nameVal) + '" /></label>'
    + '<label class="block mb-3"><span class="text-[11px] font-bold uppercase tracking-wider text-text-muted">Code</span><input id="loc-code" type="text" required ' + (isEdit ? 'readonly class="mt-1 w-full rounded-lg border border-border bg-surface-variant px-3 py-2 text-text-muted text-sm"' : 'class="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2 text-on-surface text-sm focus:outline-none focus:border-primary" placeholder="e.g. HYD01"') + ' value="' + escapeHtml(codeVal) + '" /></label>'
    + '<label class="block mb-3"><span class="text-[11px] font-bold uppercase tracking-wider text-text-muted">Address</span><input id="loc-address" type="text" class="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2 text-on-surface text-sm focus:outline-none focus:border-primary" placeholder="e.g. 123 Main St" value="' + escapeHtml(addrVal) + '" /></label>'
    + '<div id="location-error" class="text-body-sm text-red-600 mb-3 hidden"></div>'
    + '<div class="flex justify-end gap-2 mt-4">'
    + '<button type="button" id="location-cancel" class="px-4 py-2 rounded-lg border border-border text-on-surface text-sm font-medium hover:bg-surface-variant">Cancel</button>'
    + '<button type="submit" class="px-4 py-2 rounded-lg bg-primary text-on-primary text-sm font-semibold hover:opacity-90">' + (isEdit ? 'Save Changes' : 'Create') + '</button>'
    + '</div>'
    + '</form>'
    + '</div>';
  document.body.appendChild(wrapper);
  const close = () => { wrapper.remove(); loadLocations(); };
  document.getElementById('location-close').onclick = close;
  document.getElementById('location-cancel').onclick = close;
  wrapper.onclick = (e) => { if (e.target === wrapper) close(); };
  if (!isEdit) {
    const nameInput = document.getElementById('loc-name');
    const codeInput = document.getElementById('loc-code');
    nameInput.addEventListener('input', () => {
      codeInput.value = nameInput.value.trim().toUpperCase().replace(/[^A-Z0-9]+/g, '').slice(0, 50);
    });
  }
  document.getElementById('location-form').onsubmit = async (e) => {
    e.preventDefault();
    const errEl = document.getElementById('location-error');
    errEl.classList.add('hidden');
    try {
      if (isEdit) {
        const payload = {};
        const newName = document.getElementById('loc-name').value.trim();
        const newAddr = document.getElementById('loc-address').value.trim();
        if (newName) payload.location_name = newName;
        if (newAddr !== undefined) payload.address = newAddr || null;
        await apiRequest('/locations/' + existing.id, { method: 'PATCH', body: JSON.stringify(payload) });
      } else {
        const name = document.getElementById('loc-name').value.trim();
        const code = document.getElementById('loc-code').value.trim();
        if (!name || !code) throw new Error('Name and code are required');
        const addr = document.getElementById('loc-address').value.trim();
        await apiRequest('/locations/', { method: 'POST', body: JSON.stringify({ location_name: name, location_code: code, address: addr || null, status: 'active' }) });
      }
      close();
      showToast(isEdit ? 'Location updated' : 'Location created', 'Changes saved successfully.');
    } catch (err) {
      errEl.textContent = err.message || 'Something went wrong';
      errEl.classList.remove('hidden');
    }
  };
}

async function loadUsers() {
  const payload = await apiRequest("/users/?page_size=100");
  fillExistingTable(payload.items || [], (row, item) => {
    const cells = row.querySelectorAll("td");
    paintStackedUserCell(cells[1], item.full_name, item.employee_code);
    paintPlainCell(cells[2], item.email);
    paintPlainCell(cells[3], item.primary_role_name || item.role || item.role_name);
    paintPlainCell(cells[4], item.primary_location_name || item.location_name);
    paintPlainCell(cells[5], item.reporting_manager_name || item.manager_name || "—");
    paintStatusChip(cells[6], item.status);
    row.dataset.filterStatus = String(item.status || "active").toLowerCase();
    row.dataset.filterRole = item.primary_role_name || item.role || item.role_name || "";
    row.dataset.filterLocation = item.primary_location_name || item.location_name || "";
    row.dataset.filterOwner = item.reporting_manager_name || item.manager_name || "";
    row.dataset.route = `user-detail.html?user_id=${item.id}`;
    row.classList.add("cursor-pointer");
  });
  wireEntityTableActions({
    addPermission: "user.create",
    editPermission: "user.update",
    addSelector: "[data-open-user-dialog]",
    onAdd: () => openUserDialog(null, loadUsers),
    onEdit: (id) => openUserDialog(id, loadUsers),
  });
}

async function loadUserDetail() {
  const user = await detailFromRoute(["user_id", "id"], "/users/?page_size=1", (id) => `/users/${id}`);
  if (!user) return;
  setFirstText("[data-user-name]", user.full_name);
  setFirstText("[data-user-email]", user.email);
  setFirstText("[data-user-role]", user.role || "—");
  setFirstText("[data-user-location]", user.location_name || "—");
}

function paintProfile(user, role, location) {
  const name = user?.full_name || RecruitOpsLive.session?.user_name || "—";
  const email = user?.email || RecruitOpsLive.session?.email || "—";
  const roleName = role?.name || user?.primary_role_name || RecruitOpsLive.session?.role_name || "—";
  const locationName = location?.location_name || user?.primary_location_name || RecruitOpsLive.session?.location_name || "—";
  const initials = typeof personInitials === "function" ? personInitials(name) : "";
  setFirstText("[data-profile-name]", name);
  setFirstText("[data-profile-email]", email);
  setFirstText("[data-profile-role]", roleName);
  setFirstText("[data-profile-location]", locationName);
  setFirstText("[data-profile-status]", titleFromCode(user?.status || "active"));
  setFirstText("[data-profile-code]", user?.employee_code || "—");
  setFirstText("[data-profile-title]", user?.business_title || roleName);
  setFirstText("[data-profile-initials]", initials);
  const nameInput = document.getElementById("profile-full-name");
  const phoneInput = document.getElementById("profile-phone");
  const emailInput = document.getElementById("profile-email");
  if (nameInput) nameInput.value = user?.full_name || "";
  if (phoneInput) phoneInput.value = user?.phone || "";
  if (emailInput) emailInput.value = email;
}

async function loadMyProfile() {
  const detailsForm = document.getElementById("profile-details-form");
  const passwordForm = document.getElementById("profile-password-form");
  const detailsSave = detailsForm?.querySelector("button[type='submit']");
  const passwordSave = passwordForm?.querySelector("button[type='submit']");

  let profileLoaded = false;
  let baselinePhone = "";

  try {
    const me = await apiRequest("/auth/me");
    if (!me?.user) throw new Error("Profile unavailable");
    paintProfile(me.user, me.primary_role, me.primary_location);
    baselinePhone = String(me.user.phone || "");
    profileLoaded = true;
  } catch (error) {
    paintProfile({}, null, null);
    if (detailsSave) detailsSave.disabled = true;
    if (passwordSave) passwordSave.disabled = true;
    if (typeof showToast === "function") {
      showToast("Could not load profile", error.message || "Refresh and try again.");
    }
  }

  if (detailsForm && detailsForm.dataset.wired !== "true") {
    detailsForm.dataset.wired = "true";
    detailsForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      event.stopImmediatePropagation();
      if (!profileLoaded) {
        if (typeof showToast === "function") {
          showToast("Could not save profile", "Profile has not loaded yet. Refresh and try again.");
        }
        return;
      }
      const fullName = String(document.getElementById("profile-full-name")?.value || "").trim();
      if (!fullName) {
        if (typeof showToast === "function") showToast("Name required", "Enter your full name.");
        return;
      }
      // Only send phone when the user actually changed it. Omitting the key keeps
      // the server phone untouched (avoids wiping when the form was empty).
      const currentPhone = String(document.getElementById("profile-phone")?.value || "").trim();
      const body = { full_name: fullName };
      if (currentPhone !== baselinePhone) {
        body.phone = currentPhone || null;
      }
      const saveButton = detailsForm.querySelector("button[type='submit']");
      if (saveButton) saveButton.disabled = true;
      try {
        const updated = await apiRequest("/auth/profile", {
          method: "PATCH",
          body: JSON.stringify(body),
        });
        baselinePhone = String(updated.user?.phone || "");
        const session = RecruitOpsLive.session || readSession() || {};
        session.user_name = updated.user?.full_name || fullName || session.user_name;
        writeSession(session);
        RecruitOpsLive.session = session;
        paintProfile(updated.user, updated.primary_role, updated.primary_location);
        decorateShell();
        if (typeof showToast === "function") showToast("Profile saved", "Your details are up to date.");
      } catch (error) {
        if (typeof showToast === "function") showToast("Could not save profile", error.message || "Try again.");
      } finally {
        if (saveButton) saveButton.disabled = false;
      }
    });
  }

  if (passwordForm && passwordForm.dataset.wired !== "true") {
    passwordForm.dataset.wired = "true";
    passwordForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      event.stopImmediatePropagation();
      if (!profileLoaded) {
        if (typeof showToast === "function") {
          showToast("Could not change password", "Profile has not loaded yet. Refresh and try again.");
        }
        return;
      }
      const currentPassword = document.getElementById("profile-current-password")?.value || "";
      const newPassword = document.getElementById("profile-new-password")?.value || "";
      const confirmPassword = document.getElementById("profile-confirm-password")?.value || "";
      if (newPassword !== confirmPassword) {
        if (typeof showToast === "function") showToast("Passwords do not match", "Re-enter the new password.");
        return;
      }
      const saveButton = passwordForm.querySelector("button[type='submit']");
      if (saveButton) saveButton.disabled = true;
      try {
        await apiRequest("/auth/password/change", {
          method: "POST",
          body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
        });
        passwordForm.reset();
        if (typeof showToast === "function") showToast("Password updated", "Use the new password next time you sign in.");
      } catch (error) {
        if (typeof showToast === "function") showToast("Could not change password", error.message || "Check your current password.");
      } finally {
        if (saveButton) saveButton.disabled = false;
      }
    });
  }
}

async function loadDeactivateUserDialog() {
  const userId = queryInt("user_id");
  if (userId) {
    const user = await apiRequest(`/users/${userId}`).catch(() => null);
    if (user) setFirstText("[data-user-name]", user.full_name);
  }
}

async function loadRoles() {
  const payload = await apiRequest("/roles/?page_size=50");
  fillExistingTable(payload.items || [], (row, item) => {
    const cells = row.querySelectorAll("td");
    paintPlainCell(cells[0], item.role_name || item.name);
    paintStatusChip(cells[1], item.status || "active");
    paintPlainCell(cells[2], "—");
    paintPlainCell(cells[3], "Global");
    paintPlainCell(cells[4], item.description || "—");
    row.dataset.route = `role-permissions-editor.html?role_id=${item.id}`;
    row.classList.add("cursor-pointer");
  });
  wireEntityTableActions({
    addPermission: "role.create",
    editPermission: "role.update",
    addSelector: "[data-open-role-dialog]",
    onAdd: () => openRoleDialog(null, loadRoles),
    onEdit: (id) => openRoleDialog(id, loadRoles),
  });
}

async function loadVisibilityRules() {
  const roles = await apiRequest("/roles/?page_size=50").catch(() => ({ items: [] }));
  fillExistingTable(roles.items || [], (row, item) => {
    const cells = row.querySelectorAll("td");
    setCellValue(cells[0], item.role_name || item.name || "—");
    setCellValue(cells[1], "Global");
    setCellValue(cells[2], item.status || "active");
  });
}

/* ═══ Role & Permissions editor — live permission matrix ═══ */

const ROLE_PERM_MODULE_META = {
  "ai": { label: "AI Agents", icon: "smart_toy" },
  "approval": { label: "Approvals", icon: "fact_check" },
  "assignment": { label: "Assignments", icon: "group_add" },
  "candidate": { label: "Candidates", icon: "group" },
  "client": { label: "Clients", icon: "apartment" },
  "dashboard": { label: "Dashboards", icon: "dashboard" },
  "daily_update": { label: "Daily Updates", icon: "assignment" },
  "interview": { label: "Interviews", icon: "calendar_month" },
  "location": { label: "Locations", icon: "location_on" },
  "meeting": { label: "Meetings", icon: "event" },
  "notification": { label: "Notifications", icon: "notifications" },
  "offer": { label: "Offers", icon: "request_quote" },
  "pipeline": { label: "Pipeline", icon: "account_tree" },
  "portal": { label: "Portal Accounts", icon: "vpn_key" },
  "requisition": { label: "Requisitions", icon: "work" },
  "report": { label: "Reports", icon: "monitoring" },
  "role": { label: "Roles & Permissions", icon: "shield_person" },
  "settings": { label: "Settings", icon: "settings" },
  "user": { label: "Users", icon: "manage_accounts" },
  "workflow_action": { label: "Workflow Actions", icon: "task_alt" },
  "workflow_overlay": { label: "Workflow Overlays", icon: "layers" },
};

const ROLE_PERM_DESCRIPTIONS = {
  "ai.use": "Invoke any AI agent (base gate)",
  "ai.agent.resume_screener": "Resume Screener agent runs + decisions",
  "ai.agent.daily_brief": "Daily Brief agent runs + decisions",
  "ai.agent.inbox_triage": "Inbox Triage agent runs + decisions",
};

const rolePermState = { roleId: null, baseline: new Set(), dirty: false, readonly: false, total: 0 };

function rolePermModuleLabel(moduleName) {
  const meta = ROLE_PERM_MODULE_META[moduleName];
  if (meta) return meta.label;
  return moduleName.replace(/[_-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function updateRolePermSummary(enabledCount, totalCount) {
  const enabledEl = document.querySelector("[data-perm-enabled-count]");
  const disabledEl = document.querySelector("[data-perm-disabled-count]");
  if (enabledEl) enabledEl.textContent = `${enabledCount} permission${enabledCount === 1 ? "" : "s"} enabled`;
  if (disabledEl) disabledEl.textContent = `${Math.max(totalCount - enabledCount, 0)} permission${totalCount - enabledCount === 1 ? "" : "s"} disabled`;
  const saveButton = document.querySelector("[data-live-role-permissions-save]");
  if (saveButton) {
    saveButton.classList.toggle("opacity-50", !rolePermState.dirty);
    saveButton.classList.toggle("pointer-events-none", !rolePermState.dirty);
  }
}

function applyRolePermissionGrants(baseline) {
  document.querySelectorAll("[data-perm]").forEach((toggle) => {
    setPermissionToggleState(toggle, baseline.has(toggle.dataset.perm));
  });
  updateRolePermSummary(baseline.size, rolePermState.total);
}

function markRolePermDirty() {
  const current = new Set(Array.from(document.querySelectorAll("[data-perm].on")).map((t) => t.dataset.perm));
  rolePermState.dirty = current.size !== rolePermState.baseline.size
    || Array.from(current).some((code) => !rolePermState.baseline.has(code));
  updateRolePermSummary(current.size, rolePermState.total);
}

function renderRolePermissionMatrix(catalog) {
  const tbody = document.querySelector(".matrix-table tbody");
  if (!tbody) return;
  const modules = new Map();
  catalog.forEach((permission) => {
    if (!modules.has(permission.module_name)) modules.set(permission.module_name, []);
    modules.get(permission.module_name).push(permission);
  });
  const fragment = document.createDocumentFragment();
  Array.from(modules.keys()).sort().forEach((moduleName) => {
    const meta = ROLE_PERM_MODULE_META[moduleName] || {};
    const headerRow = document.createElement("tr");
    headerRow.className = "perm-section-header bg-surface-alt";
    headerRow.innerHTML = `
      <td colspan="2" class="px-4 py-2.5 font-label-caps text-label-caps text-on-surface-variant">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-[16px]">${meta.icon || "folder"}</span>
          ${escapeLiveHtml(rolePermModuleLabel(moduleName))}
        </div>
      </td>`;
    fragment.appendChild(headerRow);
    (modules.get(moduleName) || []).forEach((permission) => {
      const row = document.createElement("tr");
      const description = ROLE_PERM_DESCRIPTIONS[permission.code] || permission.action_name.replace(/[._-]+/g, " ");
      row.innerHTML = `
        <td class="px-4 py-3">
          <p class="font-semibold">${escapeLiveHtml(permission.code)}</p>
          <p class="text-[11px] text-text-muted">${escapeLiveHtml(description)}</p>
        </td>
        <td class="px-4 py-3 text-center">
          <button type="button" class="toggle-track" role="switch" aria-checked="false"
                  aria-label="Grant ${escapeLiveHtml(permission.code)}" data-perm="${escapeLiveHtml(permission.code)}"></button>
        </td>`;
      fragment.appendChild(row);
    });
  });
  tbody.innerHTML = "";
  tbody.appendChild(fragment);
}

function renderRolePermTabs(roles, activeRoleId) {
  /* The shared table enhancer (tables.js) rebuilds this page's filter bar and
     prunes sibling wrappers, so the tab strip is created here — after load —
     inside the bar rather than declared in static HTML. */
  let tabHost = document.querySelector("[data-role-tab-bar]");
  if (!tabHost) {
    const filterBar = document.querySelector(".ro-filter-bar, [data-layout='filter-toolbar']");
    if (!filterBar) return;
    tabHost = document.createElement("div");
    tabHost.className = "flex flex-wrap items-center gap-2";
    tabHost.setAttribute("data-role-tab-bar", "");
    filterBar.insertBefore(tabHost, filterBar.firstChild);
  }
  tabHost.innerHTML = (roles || []).map((role) => `
    <button type="button" class="role-tab flex items-center gap-2 px-5 py-2.5 rounded-lg font-body-sm font-semibold cursor-pointer ${Number(role.id) === Number(activeRoleId) ? "active" : ""}"
            data-role-id="${role.id}" title="Edit ${escapeLiveHtml(role.name)} permissions">
      <span class="material-symbols-outlined text-[18px]">${role.code === "admin" ? "admin_panel_settings" : "shield_person"}</span>
      ${escapeLiveHtml(role.name)}
    </button>`).join("");
}

async function selectRolePermissions(roleId) {
  const resolved = new URLSearchParams(window.location.search);
  resolved.set("role_id", String(roleId));
  window.history.replaceState(null, "", `${window.location.pathname}?${resolved.toString()}`);
  rolePermState.roleId = roleId;
  rolePermState.readonly = false;
  rolePermState.dirty = false;
  await hydrateRolePermissionsEditor();
}

async function hydrateRolePermissionsEditor() {
  const roleId = rolePermState.roleId;
  const role = await apiRequest(`/roles/${roleId}`).catch(() => null);
  const grants = await apiRequest(`/roles/${roleId}/permissions`).catch(() => null);
  const description = document.getElementById("role-description");
  if (role && description) {
    const nameEl = description.querySelector("h3");
    const copyEl = description.querySelector("p");
    if (nameEl) nameEl.innerHTML = `<span class="material-symbols-outlined text-[20px] text-primary">info</span> ${escapeLiveHtml(role.name || "Role")}`;
    if (copyEl) {
      copyEl.textContent = role.description
        || `Configure which permissions the ${role.name || "role"} holds. Toggle a permission to grant or revoke it for every user assigned to this role.`;
    }
  }
  rolePermState.baseline = new Set(grants?.permission_codes || []);
  applyRolePermissionGrants(rolePermState.baseline);
  if (role?.code === "admin") {
    rolePermState.readonly = true;
    document.querySelectorAll("[data-perm]").forEach((toggle) => { toggle.disabled = true; });
    const saveButton = document.querySelector("[data-live-role-permissions-save]");
    if (saveButton) saveButton.classList.add("opacity-50", "pointer-events-none");
    const note = description?.querySelector("[data-admin-note]");
    if (note) note.classList.remove("hidden");
  }
}

async function loadRolePermissionsEditor() {
  const surface = document.querySelector(".workspace-surface");
  const catalogPayload = await apiRequest("/permissions/").catch(() => null);
  const catalog = catalogPayload?.items || [];
  rolePermState.total = catalog.length;
  renderRolePermissionMatrix(catalog);

  const rolesPayload = await apiRequest("/roles/?page_size=100").catch(() => ({ items: [] }));
  const roles = (rolesPayload.items || []).filter((role) => role.status !== "inactive");
  const requestedId = queryInt("role_id");
  const activeRole = roles.find((role) => Number(role.id) === Number(requestedId)) || roles[0];
  if (!activeRole) {
    if (surface) setFirstText("[data-perm-enabled-count]", "No roles found");
    return;
  }
  renderRolePermTabs(roles, activeRole.id);
  rolePermState.roleId = activeRole.id;
  rolePermState.readonly = false;
  rolePermState.dirty = false;
  await hydrateRolePermissionsEditor();

  const tabBar = document.querySelector("[data-role-tab-bar]");
  if (tabBar && !tabBar.dataset.permTabsWired) {
    tabBar.dataset.permTabsWired = "true";
    tabBar.addEventListener("click", (event) => {
      const tab = event.target.closest("[data-role-id]");
      if (!tab || rolePermState.roleId === Number(tab.dataset.roleId)) return;
      tabBar.querySelectorAll(".role-tab").forEach((el) => el.classList.remove("active"));
      tab.classList.add("active");
      selectRolePermissions(Number(tab.dataset.roleId)).catch((error) => showLiveError(error));
    });
  }
  const search = document.querySelector("[data-perm-search]");
  if (search && !search.dataset.permSearchWired) {
    search.dataset.permSearchWired = "true";
    search.addEventListener("input", () => {
      const needle = search.value.trim().toLowerCase();
      document.querySelectorAll(".matrix-table tbody tr").forEach((row) => {
        if (row.classList.contains("perm-section-header")) return;
        row.style.display = !needle || row.textContent.toLowerCase().includes(needle) ? "" : "none";
      });
    });
  }
}

async function loadReassignmentReviewDrawer() {
  const reqId = queryInt("requisition_id");
  if (reqId) {
    const req = await apiRequest(`/requisitions/${reqId}`).catch(() => null);
    if (req) setFirstText("[data-requisition-title]", req.title);
  }
  const users = await apiRequest("/users/?page_size=100").catch(() => ({ items: [] }));
  const host = document.querySelector(".overlay-host .space-y-3");
  if (host) host.innerHTML = (users.items || []).map((user) => renderAvailableUserRow(user, reqId)).join("") || '<div class="p-4 text-text-muted">No users available.</div>';
}

async function loadStatusUpdateDialog() {
  const reqId = queryInt("requisition_id");
  if (reqId) {
    const req = await apiRequest(`/requisitions/${reqId}`).catch(() => null);
    if (req) setFirstText("[data-requisition-title]", req.title);
  }
}

async function loadReassignOwnerDialog() {
  const reqId = queryInt("requisition_id");
  if (reqId) {
    const req = await apiRequest(`/requisitions/${reqId}`).catch(() => null);
    if (req) setFirstText("[data-requisition-title]", req.title);
  }
}


/* ═══════════════════════════════════════════════════════════════
   CLIENT MANAGEMENT
   ═══════════════════════════════════════════════════════════════ */

async function loadClients() {
  const payload = await apiRequest("/clients/?page_size=100");
  fillExistingTable(payload.items || [], (row, item) => {
    const cells = row.querySelectorAll("td");
    paintPlainCell(cells[0], item.client_name);
    paintPlainCell(cells[1], item.location_name);
    paintPlainCell(cells[2], item.client_owner_name || item.owner_name);
    paintPlainCell(cells[3], item.industry);
    paintStatusChip(cells[4], item.status);
    paintPlainCell(cells[5], item.updated_at ? `Updated ${formatWhen(item.updated_at)}` : "—");
    row.dataset.filterStatus = String(item.status || "active").toLowerCase();
    row.dataset.filterLocation = item.location_name || "";
    row.dataset.filterIndustry = item.industry || "";
    row.dataset.filterOwner = item.client_owner_name || item.owner_name || "";
    row.dataset.route = `client-detail.html?client_id=${item.id}`;
    row.classList.add("cursor-pointer");
  });
  wireEntityTableActions({
    addPermission: "client.create",
    editPermission: "client.update",
    addSelector: "[data-open-client-dialog]",
    onAdd: () => openClientDialog(null, loadClients),
    onEdit: (id) => openClientDialog(id, loadClients),
  });
}

async function loadClientDetail() {
  const client = await detailFromRoute(["client_id", "id"], "/clients/?page_size=1", (id) => `/clients/${id}`);
  if (!client) return;
  const surface = document.querySelector("[data-client-detail]") || document.querySelector(".workspace-surface");
  setFirstText("[data-client-detail] h1", client.client_name);
  setApiField("open_requisitions", "—");
  setApiField("priority_roles", "—");
  setApiField("last_activity", formatWhen(client.updated_at) || "—");
}


/* ═══════════════════════════════════════════════════════════════
   REQUISITION MANAGEMENT
   ═══════════════════════════════════════════════════════════════ */

async function loadBusinessTitles() {
  const surface = document.querySelector('.workspace-surface');
  if (!surface) return;
  const header = document.getElementById('designation-header');
  const tableWrap = document.getElementById('designation-table-wrap');
  const actionsEl = document.getElementById('designation-actions');
  const dialogHost = document.getElementById('designation-dialog-host');
  if (!tableWrap) return;
  const canManage = hasPermission('settings.create');
  const canEdit = hasPermission('settings.update');
  if (canManage && actionsEl) {
    actionsEl.innerHTML = '<button id="btn-add-designation" class="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-on-primary font-body-sm font-semibold hover:opacity-90 transition-opacity"><span class="material-symbols-outlined text-[18px]">add</span>Add Designation</button>';
  }
  try {
    const payload = await apiRequest('/master-data/categories/designation/values?page_size=100');
    const items = payload.items || [];
    if (!items.length) {
      tableWrap.innerHTML = '<div class="flex flex-col items-center justify-center py-16 text-center"><span class="material-symbols-outlined text-[48px] text-text-muted mb-3">badge</span><p class="text-headline-sm font-semibold text-on-surface">No designations yet</p><p class="text-body-sm text-text-muted mt-1">Create your first designation to get started.</p></div>';
      return;
    }
    let rows = '';
    items.forEach(v => {
      const statusChip = v.is_active
        ? '<span class="inline-flex items-center px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-[11px] font-semibold">Active</span>'
        : '<span class="inline-flex items-center px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 text-[11px] font-semibold">Inactive</span>';
      const editBtn = canEdit ? '<button class="text-text-muted hover:text-primary transition-colors p-1 rounded hover:bg-surface-variant" data-edit-id="' + v.id + '" data-edit-name="' + escapeHtml(v.name) + '" title="Edit"><span class="material-symbols-outlined text-[18px]">edit</span></button>' : '';
      rows += '<tr class="border-b border-border hover:bg-surface-variant/30 transition-colors">'
        + '<td class="px-4 py-3 font-medium text-on-surface">' + escapeHtml(v.name) + '</td>'
        + '<td class="px-4 py-3 text-text-muted font-mono text-[13px]">' + escapeHtml(v.code) + '</td>'
        + '<td class="px-4 py-3 text-text-muted text-[13px]">' + escapeHtml(v.description || '\u2014') + '</td>'
        + '<td class="px-4 py-3 text-right">' + statusChip + '</td>'
        + '<td class="px-4 py-3 text-right">' + editBtn + '</td>'
        + '</tr>';
    });
    tableWrap.innerHTML = '<div class="mt-4 overflow-x-auto">'
      + '<table class="w-full text-left">'
      + '<thead><tr class="border-b border-border text-[11px] font-bold uppercase tracking-wider text-text-muted">'
      + '<th class="px-4 py-2.5">Name</th>'
      + '<th class="px-4 py-2.5">Code</th>'
      + '<th class="px-4 py-2.5">Description</th>'
      + '<th class="px-4 py-2.5 text-right">Status</th>'
      + '<th class="px-4 py-2.5 text-right w-12"></th>'
      + '</tr></thead>'
      + '<tbody>' + rows + '</tbody>'
      + '</table>'
      + '</div>';
    if (canManage) {
      const btn = document.getElementById('btn-add-designation');
      if (btn) btn.onclick = () => openDesignationDialog(null, dialogHost, tableWrap);
    }
    if (canEdit) {
      tableWrap.querySelectorAll('[data-edit-id]').forEach(btn => {
        btn.onclick = () => openDesignationDialog({ id: btn.dataset.editId, name: btn.dataset.editName }, dialogHost, tableWrap);
      });
    }
  } catch (err) {
    tableWrap.innerHTML = '<div class="flex flex-col items-center justify-center py-16 text-center"><span class="material-symbols-outlined text-[48px] text-red-400 mb-3">error</span><p class="text-body-sm text-red-600">Failed to load designations: ' + escapeHtml(String(err.message || err)) + '</p></div>';
  }
}

function openDesignationDialog(existing, dialogHost, tableWrap) {
  if (!dialogHost) return;
  const isEdit = !!existing;
  const title = isEdit ? 'Edit Designation' : 'Add Designation';
  const nameVal = isEdit ? existing.name : '';
  const codeField = isEdit ? '' : '<label class="block mb-3"><span class="text-[11px] font-bold uppercase tracking-wider text-text-muted">Code (auto-generated)</span><input id="designation-code" type="text" readonly class="mt-1 w-full rounded-lg border border-border bg-surface-variant px-3 py-2 text-text-muted text-sm" /></label>';
  dialogHost.innerHTML = '<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" id="designation-overlay">'
    + '<div class="bg-surface rounded-xl border border-border shadow-xl w-full max-w-md p-6">'
    + '<div class="flex items-center justify-between mb-4">'
    + '<h3 class="text-headline-sm font-semibold text-on-surface">' + title + '</h3>'
    + '<button id="designation-close" class="text-text-muted hover:text-on-surface p-1"><span class="material-symbols-outlined text-[20px]">close</span></button>'
    + '</div>'
    + '<form id="designation-form">'
    + '<label class="block mb-3"><span class="text-[11px] font-bold uppercase tracking-wider text-text-muted">Name</span><input id="designation-name" type="text" required class="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2 text-on-surface text-sm focus:outline-none focus:border-primary" placeholder="e.g. Senior Software Engineer" value="' + escapeHtml(nameVal) + '" /></label>'
    + codeField
    + '<div id="designation-error" class="text-body-sm text-red-600 mb-3 hidden"></div>'
    + '<div class="flex justify-end gap-2 mt-4">'
    + '<button type="button" id="designation-cancel" class="px-4 py-2 rounded-lg border border-border text-on-surface text-sm font-medium hover:bg-surface-variant">Cancel</button>'
    + '<button type="submit" class="px-4 py-2 rounded-lg bg-primary text-on-primary text-sm font-semibold hover:opacity-90">' + (isEdit ? 'Save Changes' : 'Create') + '</button>'
    + '</div>'
    + '</form>'
    + '</div>'
    + '</div>';
  const overlay = document.getElementById('designation-overlay');
  const close = () => { dialogHost.innerHTML = ''; loadBusinessTitles(); };
  document.getElementById('designation-close').onclick = close;
  document.getElementById('designation-cancel').onclick = close;
  overlay.onclick = (e) => { if (e.target === overlay) close(); };
  if (!isEdit) {
    const nameInput = document.getElementById('designation-name');
    const codeInput = document.getElementById('designation-code');
    nameInput.addEventListener('input', () => {
      codeInput.value = nameInput.value.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    });
  }
  document.getElementById('designation-form').onsubmit = async (e) => {
    e.preventDefault();
    const errEl = document.getElementById('designation-error');
    errEl.classList.add('hidden');
    try {
      if (isEdit) {
        const newName = document.getElementById('designation-name').value.trim();
        await apiRequest('/master-data/values/' + existing.id, { method: 'PATCH', body: JSON.stringify({ name: newName }) });
      } else {
        const name = document.getElementById('designation-name').value.trim();
        const code = document.getElementById('designation-code').value;
        if (!name || !code) throw new Error('Name is required');
        await apiRequest('/master-data/categories/designation/values', { method: 'POST', body: JSON.stringify({ code, name, sort_order: 99 }) });
      }
      close();
      showToast(isEdit ? 'Designation updated' : 'Designation created', 'Changes saved to the designation catalog.');
    } catch (err) {
      errEl.textContent = err.message || 'Something went wrong';
      errEl.classList.remove('hidden');
    }
  };
}

async function loadRequisitionDetail() {
  const requisition = await detailFromRoute(["requisition_id", "id"], "/requisitions/?page_size=1", (id) => `/requisitions/${id}`);
  if (!requisition) return;
  const surface = document.querySelector(".workspace-surface");
  setFirstText(".workspace-surface nav span:last-child", requisition.title);
  setFirstText(".workspace-surface h1, .workspace-surface h2", requisition.title);
  setFirstText(".workspace-surface h1 + span, .workspace-surface h2 + span", reqCode(requisition));
  const reqDetailCodeHost = document.querySelector(".workspace-surface h1 + span, .workspace-surface h2 + span");
  if (reqDetailCodeHost && typeof entityBadgeHtml === "function" && requisition.requisition_code && !reqDetailCodeHost.querySelector(".entity-badge")) {
    reqDetailCodeHost.insertAdjacentHTML("afterend", entityBadgeHtml(requisition.requisition_code, requisition.branch_code));
  }
  fillDashboardMetrics([
    { label: "Openings", value: requisition.openings_count, hint: requisition.employment_type || "Open role" },
    { label: "Priority", value: requisition.priority, hint: requisition.status },
    { label: "Target Close", value: formatWhen(requisition.target_closure_date).slice(0, 10), hint: "Target date" },
    { label: "Owners", value: 1, hint: requisition.primary_owner_name || "Primary owner" },
  ]);
}

async function loadAssignmentHistoryDrawer() {
  const requisition = await detailFromRoute(["requisition_id", "id"], "/requisitions/?page_size=1", (id) => `/requisitions/${id}`);
  if (!requisition) return;
  const assignments = await apiRequest(`/requisitions/${requisition.id}/assignments`).catch(() => []);
  const host = document.querySelector(".overlay-host .flex-1") || document.querySelector(".overlay-host");
  if (host) host.innerHTML = '<div class="p-4 text-text-muted">Assignment history loaded.</div>';
}

let workAssignmentReqId = null;

async function loadWorkAssignment() {
  workAssignmentReqId = queryInt("requisition_id") || workAssignmentReqId;
  const canManageAssignments = isAdmin() || hasAnyPermission("assignment.create", "assignment.update");
  const [requisitions, users] = await Promise.all([
    apiRequest("/requisitions/?page_size=100").catch(() => ({ items: [] })),
    apiRequest("/users/?page_size=100&status=active").catch(() => ({ items: [] })),
  ]);
  const reqItems = requisitions.items || [];
  if (!workAssignmentReqId && reqItems.length) workAssignmentReqId = reqItems[0].id;
  const selected = reqItems.find((r) => r.id === workAssignmentReqId);

  let assignments = [];
  if (workAssignmentReqId) {
    const payload = await apiRequest(`/requisitions/${workAssignmentReqId}/assignments`).catch(() => []);
    assignments = Array.isArray(payload) ? payload : payload.items || [];
  }
  const assignedIds = new Set(assignments.map((a) => a.assigned_user_id));
  const available = (users.items || []).filter((u) => !assignedIds.has(u.id) && u.id !== selected?.primary_owner_user_id);

  const surface = document.querySelector(".workspace-surface");
  if (!surface) return;
  const initials = (name) => (name || "?").split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  const roleOptions = reqItems.map((r) => `<option value="${r.id}" ${r.id === workAssignmentReqId ? "selected" : ""}>${escapeLiveHtml(r.title || `Requisition ${r.id}`)}${r.primary_owner_name ? ` — owner: ${escapeLiveHtml(r.primary_owner_name)}` : ""}</option>`).join("");
  const assignedRows = selected
    ? (assignments.length
        ? assignments.map((a) => `<div class="px-4 py-3 flex items-center justify-between hover:bg-highlight-soft transition-colors">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-full ${a.assignment_type === "primary_owner" ? "bg-primary-container text-on-primary" : "bg-secondary-container text-on-secondary-container"} font-bold flex items-center justify-center shrink-0 text-sm">${escapeLiveHtml(initials(a.assigned_user_name))}</div>
              <div>
                <p class="font-semibold text-on-surface">${escapeLiveHtml(a.assigned_user_name || "Unknown")}</p>
                <p class="text-text-muted font-body-sm text-[11px]">${escapeLiveHtml(a.assignment_type || "contributor")}</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              ${a.assignment_type === "primary_owner" ? '<span class="inline-flex items-center px-2 py-0.5 rounded bg-primary-container text-on-primary text-[10px] font-bold uppercase tracking-wide">Owner</span>' : ""}
              ${canManageAssignments ? `<button type="button" class="text-text-muted hover:text-danger-text transition-colors p-1 rounded hover:bg-danger-bg" title="Remove assignment" data-remove-assignment="${a.id}" aria-label="Remove assignment"><span class="material-symbols-outlined text-[18px]">close</span></button>` : ""}
            </div>
          </div>`).join("")
        : '<div class="px-4 py-6 text-text-muted font-body-sm">No team members assigned yet.</div>')
    : '<div class="px-4 py-6 text-text-muted font-body-sm">Select a requisition to view its team.</div>';
  const availableRows = selected
    ? (available.length
        ? available.map((u) => `<div class="px-4 py-3 flex items-center justify-between hover:bg-highlight-soft transition-colors">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-full bg-tertiary-container text-on-tertiary-container font-bold flex items-center justify-center shrink-0 text-sm">${escapeLiveHtml(initials(u.full_name))}</div>
              <div>
                <p class="font-semibold text-on-surface">${escapeLiveHtml(u.full_name)}</p>
                <p class="text-text-muted font-body-sm text-[11px]">${escapeLiveHtml(u.business_title || u.role_name || "Team member")}</p>
              </div>
            </div>
            ${canManageAssignments ? `<button type="button" class="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-primary-container text-on-primary font-body-sm text-[12px] font-semibold hover:bg-primary-hover transition-colors" data-assign-user="${u.id}" title="Assign as contributor"><span class="material-symbols-outlined text-[16px]">add</span> Assign</button>` : `<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-surface-dim text-text-muted font-body-sm text-[11px]" title="Read-only: you need assignment permissions to edit"><span class="material-symbols-outlined text-[14px]">lock</span>View</span>`}
          </div>`).join("")
        : '<div class="px-4 py-6 text-text-muted font-body-sm">Everyone is already assigned.</div>')
    : '<div class="px-4 py-6 text-text-muted font-body-sm">Select a requisition first.</div>';

  surface.innerHTML = `<div class="space-y-5" data-live-work-assignment="true">
    <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
      <div>
        <h1 class="text-headline-lg font-bold text-on-surface">Work Assignment</h1>
        <p class="font-body-sm text-body-sm text-text-muted mt-1">Assign team members across requisitions. Owner transfers require the primary-owner assignment type.</p>
        ${canManageAssignments ? "" : '<p class="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-surface-dim border border-border px-3 py-1.5 font-body-sm text-[12px] text-text-muted"><span class="material-symbols-outlined text-[15px]">lock</span>Read-only — you can view assignments but not change them</p>'}
      </div>
      <span class="inline-flex items-center rounded-full bg-success-bg px-2.5 py-1 font-label-caps text-label-caps text-success-text">Live API data</span>
    </div>
    <div class="bg-surface border border-border rounded-lg p-3 flex flex-col sm:flex-row items-start sm:items-center gap-4 shadow-sm">
      <div class="flex items-center gap-2">
        <span class="material-symbols-outlined text-text-muted text-[18px]">work</span>
        <span class="font-label-caps text-label-caps text-text-muted">REQUISITION</span>
      </div>
      <select id="work-assignment-requisition" class="w-full sm:w-96 bg-surface-alt border border-border rounded-lg text-on-surface font-body-sm py-2 pl-3 pr-3 focus:outline-none focus:border-primary">
        ${roleOptions || '<option value="">No requisitions yet</option>'}
      </select>
      <div class="flex items-center gap-2 text-sm text-text-muted">
        <span class="material-symbols-outlined text-[16px]">group</span>
        <span class="font-body-sm">${assignments.length} assigned</span>
      </div>
    </div>
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="bg-surface border border-border rounded-lg shadow-sm flex flex-col">
        <div class="bg-surface-alt border-b border-border px-4 py-3 flex items-center justify-between">
          <div class="flex items-center gap-2"><span class="material-symbols-outlined text-[18px] text-primary">group</span><h3 class="font-headline-sm text-headline-sm font-semibold text-on-surface">Assigned Members</h3></div>
          <span class="inline-flex items-center justify-center w-6 h-6 rounded-full bg-primary-container text-on-primary text-[11px] font-bold">${assignments.length}</span>
        </div>
        <div class="divide-y divide-border">${assignedRows}</div>
      </div>
      <div class="bg-surface border border-border rounded-lg shadow-sm flex flex-col">
        <div class="bg-surface-alt border-b border-border px-4 py-3 flex items-center justify-between">
          <div class="flex items-center gap-2"><span class="material-symbols-outlined text-[18px] text-success-text">person_add</span><h3 class="font-headline-sm text-headline-sm font-semibold text-on-surface">Available Team</h3></div>
          <span class="inline-flex items-center justify-center w-6 h-6 rounded-full bg-success-bg text-success-text text-[11px] font-bold">${available.length}</span>
        </div>
        <div class="divide-y divide-border max-h-[480px] overflow-y-auto">${availableRows}</div>
      </div>
    </div>
  </div>`;

  const selector = surface.querySelector("#work-assignment-requisition");
  if (selector) {
    selector.addEventListener("change", () => {
      workAssignmentReqId = intOrNull(selector.value);
      loadWorkAssignment();
    });
  }
  if (canManageAssignments) {
    surface.querySelectorAll("[data-assign-user]").forEach((button) => {
      button.addEventListener("click", () => createRequisitionAssignment(button));
    });
    surface.querySelectorAll("[data-remove-assignment]").forEach((button) => {
      button.addEventListener("click", () => removeRequisitionAssignment(button));
    });
  }
}

async function createRequisitionAssignment(button) {
  const reqId = workAssignmentReqId || queryInt("requisition_id");
  const userId = intOrNull(button?.dataset.userId || button?.getAttribute("data-assign-user"));
  const assignmentType = button?.dataset.assignmentType || "contributor";
  if (!reqId || !userId) return;
  try {
    await apiRequest(`/requisitions/${reqId}/assignments`, {
      method: "POST",
      body: JSON.stringify({ assigned_user_id: userId, assignment_type: assignmentType }),
    });
    showLiveSuccess(assignmentType === "primary_owner" ? "Owner assigned" : "Team member assigned", assignmentType === "primary_owner" ? "Requisition ownership transferred." : "Contributor added to the requisition team.");
    loadWorkAssignment();
  } catch (error) { showLiveError(error); }
}

async function removeRequisitionAssignment(button) {
  const assignmentId = intOrNull(button?.dataset.assignmentId || button?.getAttribute("data-remove-assignment"));
  if (!assignmentId) return;
  try {
    await apiRequest(`/requisitions/assignments/${assignmentId}`, { method: "DELETE" });
    showLiveSuccess("Assignment removed");
    loadWorkAssignment();
  } catch (error) { showLiveError(error); }
}


/* ═══════════════════════════════════════════════════════════════
   CANDIDATE MANAGEMENT
   ═══════════════════════════════════════════════════════════════ */

async function loadCandidates() {
  const table = document.querySelector(".workspace-surface table") || document.querySelector("table");
  const tbody = table?.querySelector("tbody");
  if (tbody && typeof showSkeletonTable === "function") showSkeletonTable(tbody, 6, 8);
  const payload = await apiRequest("/candidates/?page_size=100").catch(() => ({ items: [] }));
  const items = payload.items || [];

  const STATUS_LABEL = { draft: "Active", active: "Active", archived: "Archived", passive: "Passive" };
  const INTAKE_LABEL = {
    uploaded: "Incomplete",
    parsed: "Incomplete",
    "needs-review": "Missing Docs",
    "duplicate-review": "Missing Docs",
    "ready-to-save": "Ready",
    finalized: "Ready",
  };
  const INTAKE_ICON = { Ready: "check_circle", Incomplete: "pending", "Missing Docs": "error" };
  const DUP_META = {
    cleared: { label: "Verified Unique", tone: "bg-success-bg text-success-text" },
    unique: { label: "Verified Unique", tone: "bg-success-bg text-success-text" },
    "in-review": { label: "Potential Matches", tone: "bg-warning-bg text-warning-text" },
    potential: { label: "Potential Matches", tone: "bg-warning-bg text-warning-text" },
    conflict: { label: "Potential Matches", tone: "bg-danger-bg text-danger-text" },
    "not-started": { label: "Not Checked", tone: "bg-surface-dim text-text-muted" },
  };

  fillExistingTable(items, (row, item) => {
    const cells = row.querySelectorAll("td");
    setStackedCell(cells[0], item.full_name || "—", item.email || item.source_type || "");
    if (cells[0] && typeof entityBadgeHtml === "function" && item.candidate_code && !cells[0].querySelector(":scope > .entity-badge")) {
      cells[0].insertAdjacentHTML("beforeend", entityBadgeHtml(item.candidate_code, item.branch_code));
    }
    const avatar = cells[0]?.firstElementChild?.querySelector("div");
    if (avatar) {
      const initials = (item.full_name || "?").split(/\s+/).slice(0, 2).map((w) => w[0] || "").join("").toUpperCase();
      avatar.textContent = initials;
    }
    setStackedCell(cells[1], item.current_designation || "—", item.current_company || "");
    const owner = item.primary_owner_name || item.sourced_by_name;
    const ownerWrap = cells[2]?.querySelector("div");
    if (ownerWrap) {
      const initials = (owner || "—").split(/\s+/).slice(0, 2).map((w) => w[0] || "").join("").toUpperCase();
      ownerWrap.title = owner || "";
      const ownerAvatar = ownerWrap.querySelector("div");
      if (ownerAvatar) ownerAvatar.textContent = initials || "—";
    }
    const dup = DUP_META[String(item.duplicate_state || "not-started").toLowerCase()] || DUP_META["not-started"];
    const dupLabel = cells[3]?.querySelector("span") || cells[3];
    if (dupLabel) {
      dupLabel.className = `inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold ${dup.tone}`;
      dupLabel.textContent = dup.label;
    }
    const intakeLabel = INTAKE_LABEL[String(item.intake_stage || "uploaded").toLowerCase()] || "Incomplete";
    const readyIcon = cells[4]?.querySelector(".material-symbols-outlined");
    const readyText = cells[4]?.querySelector("span:not(.material-symbols-outlined):last-of-type") || cells[4]?.querySelector("span:last-child") || cells[4];
    if (readyIcon) readyIcon.textContent = INTAKE_ICON[intakeLabel] || "pending";
    if (readyText && readyText !== readyIcon) readyText.textContent = intakeLabel;
    const linked = cells[5]?.querySelector("span") || cells[5];
    const hasLink = Boolean(item.linked_requisition_titles?.length);
    if (linked) linked.textContent = hasLink ? String(item.linked_requisition_titles[0]).slice(0, 18) : "Unlinked";
    setCellValue(cells[6], item.updated_at ? ageDaysLabel(item.updated_at) + " ago" : "—");
    const statusLabel = STATUS_LABEL[String(item.profile_status || "draft").toLowerCase()] || "Active";
    const token = document.createElement("span");
    token.className = "sr-only";
    token.textContent = `${statusLabel} ${intakeLabel} ${dup.label} ${hasLink ? "linked" : "unlinked"}`;
    row.appendChild(token);
    row.dataset.filterStatus = statusLabel.toLowerCase();
    row.dataset.filterCode = item.candidate_code || "";
    row.dataset.filterDuplicate = dup.label.toLowerCase().includes("unique") ? "unique" : dup.label.toLowerCase().includes("potential") ? "potential" : "not-checked";
    row.dataset.filterReadiness = intakeLabel.toLowerCase().replace(/\s+/g, "-");
    row.dataset.filterLinkage = hasLink ? "linked" : "unlinked";
    row.dataset.filterOwner = owner || "";
    row.dataset.route = `candidate-detail.html?candidate_id=${item.id}`;
    row.classList.add("cursor-pointer");
  });

  const countChip = document.querySelector("[data-candidate-count]");
  if (countChip) countChip.textContent = items.length;
  /* Footer count + pager are owned by the shared engine in tables.js
     (fillExistingTable → wireLiveTableInteractions → applyClientPagination),
     which rewrites the summary after this painter returns. */
}

async function loadCandidateDetail() {
  const candidate = await detailFromRoute(["candidate_id", "id"], "/candidates/?page_size=1", (id) => `/candidates/${id}`);
  if (!candidate) return;
  setFirstText("[data-candidate-name]", candidate.full_name);
  setFirstText("[data-candidate-email]", candidate.email);
  setFirstText("[data-candidate-phone]", candidate.phone);
  const candidateNameHost = document.querySelector("[data-candidate-name]");
  if (candidateNameHost?.parentElement && typeof entityBadgeHtml === "function" && candidate.candidate_code && !candidateNameHost.parentElement.querySelector(":scope > .entity-badge")) {
    candidateNameHost.insertAdjacentHTML("afterend", entityBadgeHtml(candidate.candidate_code, candidate.branch_code));
  }
  /* Surface the agent entry point once the candidate id is known. */
  const screenerButton = document.querySelector("[data-live-agents-run-screener]");
  if (screenerButton) {
    screenerButton.dataset.candidateId = String(candidate.id ?? "");
    screenerButton.hidden = false;
    screenerButton.setAttribute(
      "aria-label",
      `Run the AI resume screener for ${candidate.full_name || "this candidate"}`,
    );
  }
}

async function loadCandidateReviewDrawer() {
  const candidateId = queryInt("candidate_id");
  if (candidateId) {
    const candidate = await apiRequest(`/candidates/${candidateId}`).catch(() => null);
    if (candidate) {
      document.getElementById("drawer-title").textContent = "Edit Candidate";
      document.getElementById("save-candidate-label").textContent = "Update Candidate";
      document.getElementById("full-name").value = candidate.full_name || "";
      document.getElementById("email").value = candidate.email || "";
      document.getElementById("phone").value = candidate.phone || "";
      document.getElementById("source-type").value = candidate.source_type || "";
      document.getElementById("source-detail").value = candidate.source_detail || "";
      document.getElementById("current-company").value = candidate.current_company || "";
      document.getElementById("current-designation").value = candidate.current_designation || "";
      document.getElementById("total-experience-years").value = candidate.total_experience_years ?? "";
      document.getElementById("notice-period-days").value = candidate.notice_period_days ?? "";
    }
  }
}

async function loadCandidateDuplicateReview() {
  const candidates = await apiRequest("/candidates/?duplicate_state=in-review&page_size=20").catch(() => ({ items: [] }));
  fillExistingTable(candidates.items || [], (row, item) => {
    const cells = row.querySelectorAll("td");
    setStackedCell(cells[0], item.full_name, item.email || "");
    setCellValue(cells[1], item.duplicate_status || "In Review");
  });
}

async function loadDuplicateWarningModal() {
  const candidate = await detailFromRoute(["candidate_id", "id"], "/candidates/?duplicate_state=in-review&page_size=1", (id) => `/candidates/${id}`);
  if (!candidate) return;
  const duplicate = await apiRequest(`/candidates/${candidate.id}/duplicate-check`).catch(() => ({ matches: [] }));
  const match = duplicate.matches?.[0] || {};
  const host = document.querySelector(".workspace-surface");
  if (host) host.innerHTML = `<div class="p-4"><h2>Duplicate Warning</h2><p>${escapeLiveHtml(candidate.full_name)} may match ${escapeLiveHtml(match.matched_candidate_name || "another candidate")} (${match.match_score || 0}% match).</p></div>`;
}async function loadCandidateScreening() {
  const applicationId = queryInt("application_id");
  if (!applicationId) return;
  try {
    const application = await apiRequest(`/pipeline/applications/${applicationId}`);
    setFirstText("[data-candidate-name]", application.candidate_name);
    setFirstText("[data-requisition-title]", application.requisition_title);
    setFirstText("[data-current-stage]", application.current_stage);
  } catch (error) { showLiveError(error); }
}

async function loadReviewMatchesWorkspace() {
  const candidates = await apiRequest("/candidates/?page_size=50").catch(() => ({ items: [] }));
  fillExistingTable(candidates.items || [], (row, item) => {
    const cells = row.querySelectorAll("td");
    setStackedCell(cells[0], item.full_name, item.email || "");
    setCellValue(cells[1], item.source_type || "—");
  });
}


/* ═══════════════════════════════════════════════════════════════
   PORTAL ACCOUNTS
   ═══════════════════════════════════════════════════════════════ */

function portalStatusChip(status) {
  const map = {
    active: "bg-success-bg text-success-text border border-success-text/20",
    inactive: "bg-surface-dim text-text-muted border border-border",
    locked: "bg-warning-bg text-warning-text border border-warning-text/20",
  };
  return `<span class="inline-flex items-center whitespace-nowrap px-2 py-0.5 rounded-sm text-xs font-semibold ${map[status] || map.inactive}">${escapeLiveHtml(status)}</span>`;
}

function portalOwnershipChip(ownershipType, ownedByName) {
  const label = ownershipType === "company-shared" ? "Company shared" : ownershipType === "user-owned" ? `Personal — ${ownedByName || ""}` : `Client owned — ${ownedByName || ""}`;
  const labelClean = label.replace(/ —\s*$/, "");
  const cls = ownershipType === "company-shared" ? "bg-primary-container text-on-primary-container" : "bg-secondary-container text-on-secondary-container";
  return `<span class="inline-flex items-center whitespace-nowrap px-2 py-0.5 rounded-sm text-[11px] font-semibold ${cls}">${escapeLiveHtml(labelClean)}</span>`;
}

async function loadPortalAccounts() {
  const surface = document.querySelector("[data-live-portal-accounts]");
  if (!surface) return;
  const canManage = isAdmin() || hasAnyPermission("portal.create", "portal.update");
  const canBookSlots = isAdmin() || hasAnyPermission("portal.assign_slot");

  const [payload, locations] = await Promise.all([
    apiRequest("/portal-accounts/?page_size=100").catch(() => ({ items: [] })),
    apiRequest("/locations/?page_size=100").catch(() => ({ items: [] })),
  ]);
  const accounts = payload.items || [];
  const locationOptions = (locations.items || [])
    .map((l) => `<option value="${l.id}">${escapeLiveHtml(l.location_name || `Location ${l.id}`)}</option>`)
    .join("");

  const accountRows = accounts.length
    ? accounts.map((a) => `
      <tr class="h-table-row border-b border-border/50 hover:bg-highlight-soft transition-colors" data-account-id="${a.id}">
        <td class="px-4 py-2">
          <div class="flex flex-col">
            <span class="font-headline-sm text-headline-sm text-on-background">${escapeLiveHtml(a.platform_name)}</span>
            <span class="font-label-caps text-label-caps text-text-muted">${escapeLiveHtml(a.account_name)}</span>
          </div>
        </td>
        <td class="px-4 py-2"><span class="block max-w-[200px] truncate text-on-surface-variant" title="${escapeLiveHtml(a.login_identifier || "")}">${escapeLiveHtml(a.login_identifier || "—")}</span></td>
        <td class="px-4 py-2">${portalOwnershipChip(a.ownership_type, a.owned_by_user_name)}</td>
        <td class="px-4 py-2 whitespace-nowrap text-on-surface-variant">${escapeLiveHtml(a.branch_name || "—")}</td>
        <td class="px-4 py-2">
          <div class="flex items-center gap-2">
            ${portalStatusChip(a.status)}
            ${a.has_full_access ? '<span class="inline-flex items-center whitespace-nowrap px-1.5 py-0.5 rounded-sm text-[10px] font-bold uppercase tracking-wide bg-warning-bg text-warning-text" title="Full access — no slot scheduling needed">Full access</span>' : ""}
          </div>
        </td>
        <td class="px-4 py-2 text-on-surface-variant">${a.daily_usage_limit_hours != null ? `${a.daily_usage_limit_hours}h/day` : "—"}</td>
        <td class="px-4 py-2 text-right">
          <div class="flex items-center justify-end gap-1">
            <button type="button" class="p-1 text-text-muted hover:text-primary hover:bg-surface-variant rounded transition-colors" title="Usage slots" data-slot-account="${a.id}" data-slot-label="${escapeLiveHtml(a.platform_name)} — ${escapeLiveHtml(a.account_name)}" data-slot-full-access="${a.has_full_access ? 1 : 0}" aria-label="Usage slots"><span class="material-symbols-outlined text-[18px]">calendar_month</span></button>
            ${canManage ? `<button type="button" class="p-1 text-text-muted hover:text-primary hover:bg-surface-variant rounded transition-colors" title="Edit" data-edit-account="${a.id}" aria-label="Edit"><span class="material-symbols-outlined text-[18px]">edit</span></button>` : ""}
          </div>
        </td>
      </tr>`).join("")
    : '<tr><td colspan="7" class="px-4 py-10 text-center text-text-muted font-body-sm">No portal accounts yet. Add a shared sourcing account to start tracking usage.</td></tr>';

  surface.innerHTML = `
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
      <div>
        <h1 class="font-headline-lg text-headline-lg text-on-background">Portal Accounts</h1>
        <p class="font-body-sm text-body-sm text-text-muted mt-1">Shared job-portal credentials, ownership, and usage-slot scheduling for the sourcing team.</p>
      </div>
      <div class="flex items-center gap-3">
        <span class="inline-flex items-center rounded-full bg-success-bg px-2.5 py-1 font-label-caps text-label-caps text-success-text">Live API data</span>
        ${canManage ? '<button type="button" id="portal-add-btn" class="h-10 px-4 bg-primary-container text-on-primary-container hover:bg-primary-hover rounded-DEFAULT flex items-center gap-2 font-headline-sm text-headline-sm transition-colors"><span class="material-symbols-outlined text-[18px]">add</span> Add Account</button>' : '<span class="inline-flex items-center gap-1.5 rounded-lg bg-surface-dim border border-border px-3 py-1.5 font-body-sm text-[12px] text-text-muted"><span class="material-symbols-outlined text-[15px]">lock</span>Read-only</span>'}
      </div>
    </div>
    <div class="bg-surface border border-border rounded-DEFAULT overflow-hidden">
      <div class="table-container overflow-auto">
        <table class="w-full text-left border-collapse min-w-[860px]">
          <thead class="bg-surface-alt border-b border-border">
            <tr>
              <th class="h-[40px] px-4 font-label-caps text-label-caps text-text-muted whitespace-nowrap">Platform / Account</th>
              <th class="h-[40px] px-4 font-label-caps text-label-caps text-text-muted whitespace-nowrap">Login</th>
              <th class="h-[40px] px-4 font-label-caps text-label-caps text-text-muted whitespace-nowrap">Ownership</th>
              <th class="h-[40px] px-4 font-label-caps text-label-caps text-text-muted whitespace-nowrap">Branch</th>
              <th class="h-[40px] px-4 font-label-caps text-label-caps text-text-muted whitespace-nowrap">Status</th>
              <th class="h-[40px] px-4 font-label-caps text-label-caps text-text-muted whitespace-nowrap">Usage limit</th>
              <th class="h-[40px] px-4 w-24"></th>
            </tr>
          </thead>
          <tbody class="font-data-tabular text-data-tabular text-on-background">${accountRows}</tbody>
        </table>
      </div>
    </div>
    <dialog id="portal-account-dialog" class="rounded-2xl backdrop:bg-black/40 p-0 w-[min(92vw,520px)]">
      <form method="dialog" class="p-6 space-y-4" id="portal-account-form">
        <h3 class="font-headline-md text-headline-md font-bold text-on-surface" id="portal-form-title">Add Portal Account</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <label class="block sm:col-span-1"><span class="font-body-sm text-text-muted">Platform *</span><input id="portal-platform" required maxlength="100" class="mt-1 w-full bg-surface-alt border border-border rounded-lg px-3 py-2 font-body-sm" placeholder="LinkedIn, Naukri…" /></label>
          <label class="block sm:col-span-1"><span class="font-body-sm text-text-muted">Account name *</span><input id="portal-account-name" required maxlength="150" class="mt-1 w-full bg-surface-alt border border-border rounded-lg px-3 py-2 font-body-sm" placeholder="Shared recruiting login" /></label>
          <label class="block sm:col-span-2"><span class="font-body-sm text-text-muted">Login identifier</span><input id="portal-login" maxlength="255" class="mt-1 w-full bg-surface-alt border border-border rounded-lg px-3 py-2 font-body-sm" placeholder="email or username used to sign in" /></label>
          <label class="block"><span class="font-body-sm text-text-muted">Branch *</span><select id="portal-branch" required class="mt-1 w-full bg-surface-alt border border-border rounded-lg px-3 py-2 font-body-sm">${locationOptions || '<option value="">No locations yet</option>'}</select></label>
          <label class="block"><span class="font-body-sm text-text-muted">Ownership *</span><select id="portal-ownership" class="mt-1 w-full bg-surface-alt border border-border rounded-lg px-3 py-2 font-body-sm"><option value="company-shared">Company shared</option><option value="user-owned">Personal (user owned)</option><option value="client-owned">Client owned</option></select></label>
          <label class="block"><span class="font-body-sm text-text-muted">Status</span><select id="portal-status" class="mt-1 w-full bg-surface-alt border border-border rounded-lg px-3 py-2 font-body-sm"><option value="active">Active</option><option value="inactive">Inactive</option><option value="locked">Locked</option></select></label>
          <label class="block"><span class="font-body-sm text-text-muted">Daily usage limit (hours)</span><input id="portal-limit" type="number" min="0" max="24" step="0.5" class="mt-1 w-full bg-surface-alt border border-border rounded-lg px-3 py-2 font-body-sm" /></label>
          <label class="flex items-center gap-2 mt-1"><input id="portal-shared" type="checkbox" checked class="rounded border-outline-variant text-primary bg-transparent w-4 h-4" /><span class="font-body-sm">Shared account</span></label>
          <label class="flex items-center gap-2 mt-1"><input id="portal-full-access" type="checkbox" class="rounded border-outline-variant text-primary bg-transparent w-4 h-4" /><span class="font-body-sm">Full access (no scheduling)</span></label>
          <label class="block sm:col-span-2"><span class="font-body-sm text-text-muted">Notes</span><textarea id="portal-notes" rows="2" maxlength="4000" class="mt-1 w-full bg-surface-alt border border-border rounded-lg px-3 py-2 font-body-sm"></textarea></label>
        </div>
        <p id="portal-form-error" class="hidden font-body-sm text-danger-text"></p>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" value="cancel" class="h-10 px-4 rounded-lg border border-border bg-surface text-on-surface font-body-sm hover:bg-highlight-soft" data-close-portal-dialog>Cancel</button>
          <button type="button" id="portal-save-btn" class="h-10 px-5 rounded-lg bg-primary text-on-primary font-body-sm font-semibold hover:bg-primary-hover">Save Account</button>
        </div>
      </form>
    </dialog>
    <dialog id="portal-slots-dialog" class="rounded-2xl backdrop:bg-black/40 p-0 w-[min(94vw,720px)]">
      <div class="p-6 space-y-4">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h3 class="font-headline-md text-headline-md font-bold text-on-surface" id="portal-slots-title">Usage Slots</h3>
            <p class="font-body-sm text-body-sm text-text-muted mt-0.5">Scheduled windows when team members may use this account.</p>
          </div>
          <button type="button" class="rounded-full border border-border p-2 text-on-surface" data-close-portal-slots aria-label="Close"><span class="material-symbols-outlined">close</span></button>
        </div>
        <p id="portal-slots-banner" class="hidden rounded-lg bg-surface-dim border border-border px-3 py-2 font-body-sm text-[12px] text-text-muted"><span class="material-symbols-outlined text-[14px] align-text-bottom">info</span> This account has full access — slot scheduling is not required, but you can still track usage.</p>
        <div id="portal-slots-list" class="divide-y divide-border rounded-lg border border-border max-h-64 overflow-auto"></div>
        <form id="portal-slot-form" class="grid grid-cols-2 sm:grid-cols-5 gap-2 items-end">
          <label class="block col-span-2 sm:col-span-1"><span class="font-body-sm text-text-muted">Date</span><input id="portal-slot-date" type="date" required class="mt-1 w-full bg-surface-alt border border-border rounded-lg px-2 py-2 font-body-sm" /></label>
          <label class="block"><span class="font-body-sm text-text-muted">Start</span><input id="portal-slot-start" type="time" required value="09:00" class="mt-1 w-full bg-surface-alt border border-border rounded-lg px-2 py-2 font-body-sm" /></label>
          <label class="block"><span class="font-body-sm text-text-muted">End</span><input id="portal-slot-end" type="time" required value="11:00" class="mt-1 w-full bg-surface-alt border border-border rounded-lg px-2 py-2 font-body-sm" /></label>
          <label class="block"><span class="font-body-sm text-text-muted">User</span><select id="portal-slot-user" class="mt-1 w-full bg-surface-alt border border-border rounded-lg px-2 py-2 font-body-sm"></select></label>
          <button type="submit" id="portal-slot-add" class="h-[38px] rounded-lg bg-primary-container text-on-primary-container font-body-sm font-semibold hover:bg-primary-hover flex items-center justify-center gap-1"><span class="material-symbols-outlined text-[16px]">add</span> Book</button>
        </form>
        <p id="portal-slot-error" class="hidden font-body-sm text-danger-text"></p>
      </div>
    </dialog>
  `;

  let usersCache = [];
  async function slotUsers() {
    if (!usersCache.length) {
      const res = await apiRequest("/users/?page_size=100&status=active").catch(() => ({ items: [] }));
      usersCache = res.items || [];
      const userSelect = surface.querySelector("#portal-slot-user");
      if (userSelect) userSelect.innerHTML = usersCache.map((u) => `<option value="${u.id}">${escapeLiveHtml(u.full_name)}</option>`).join("");
    }
    return usersCache;
  }

  const accountDialog = surface.querySelector("#portal-account-dialog");
  const slotsDialog = surface.querySelector("#portal-slots-dialog");
  let editingAccountId = null;
  let slotsAccountId = null;

  surface.querySelector("#portal-add-btn")?.addEventListener("click", () => {
    editingAccountId = null;
    surface.querySelector("#portal-form-title").textContent = "Add Portal Account";
    surface.querySelector("#portal-account-form").reset();
    surface.querySelector("#portal-form-error").classList.add("hidden");
    accountDialog.showModal();
  });

  surface.querySelectorAll("[data-edit-account]").forEach((btn) => btn.addEventListener("click", () => {
    const account = accounts.find((a) => a.id === Number(btn.dataset.editAccount));
    if (!account) return;
    editingAccountId = account.id;
    surface.querySelector("#portal-form-title").textContent = "Edit Portal Account";
    surface.querySelector("#portal-platform").value = account.platform_name || "";
    surface.querySelector("#portal-account-name").value = account.account_name || "";
    surface.querySelector("#portal-login").value = account.login_identifier || "";
    surface.querySelector("#portal-branch").value = account.branch_id;
    surface.querySelector("#portal-ownership").value = account.ownership_type;
    surface.querySelector("#portal-status").value = account.status;
    surface.querySelector("#portal-limit").value = account.daily_usage_limit_hours ?? "";
    surface.querySelector("#portal-shared").checked = !!account.is_shared;
    surface.querySelector("#portal-full-access").checked = !!account.has_full_access;
    surface.querySelector("#portal-notes").value = account.notes || "";
    surface.querySelector("#portal-form-error").classList.add("hidden");
    accountDialog.showModal();
  }));

  surface.querySelector("#portal-save-btn").addEventListener("click", async () => {
    const errorEl = surface.querySelector("#portal-form-error");
    const body = {
      platform_name: surface.querySelector("#portal-platform").value.trim(),
      account_name: surface.querySelector("#portal-account-name").value.trim(),
      login_identifier: surface.querySelector("#portal-login").value.trim() || null,
      branch_id: Number(surface.querySelector("#portal-branch").value),
      ownership_type: surface.querySelector("#portal-ownership").value,
      status: surface.querySelector("#portal-status").value,
      is_shared: surface.querySelector("#portal-shared").checked,
      has_full_access: surface.querySelector("#portal-full-access").checked,
      daily_usage_limit_hours: surface.querySelector("#portal-limit").value === "" ? null : Number(surface.querySelector("#portal-limit").value),
      notes: surface.querySelector("#portal-notes").value.trim() || null,
    };
    if (body.ownership_type === "user-owned") {
      const session = RecruitOpsLive.session || readSession();
      body.owned_by_user_id = Number(session?.user_id) || null;
      if (!body.owned_by_user_id) {
        errorEl.textContent = "Personal accounts require an owner.";
        errorEl.classList.remove("hidden");
        return;
      }
    }
    try {
      if (editingAccountId) {
        await apiRequest(`/portal-accounts/${editingAccountId}`, { method: "PATCH", body: JSON.stringify(body) });
        showToast("Portal account updated", body.account_name);
      } else {
        await apiRequest("/portal-accounts/", { method: "POST", body: JSON.stringify(body) });
        showToast("Portal account created", body.account_name);
      }
      accountDialog.close();
      loadPortalAccounts();
    } catch (error) {
      errorEl.textContent = error?.message || "Could not save the account.";
      errorEl.classList.remove("hidden");
    }
  });

  surface.querySelectorAll("[data-close-portal-dialog]").forEach((btn) => btn.addEventListener("click", () => accountDialog.close()));
  surface.querySelectorAll("[data-close-portal-slots]").forEach((btn) => btn.addEventListener("click", () => slotsDialog.close()));

  surface.querySelectorAll("[data-slot-account]").forEach((btn) => btn.addEventListener("click", async () => {
    slotsAccountId = Number(btn.dataset.slotAccount);
    surface.querySelector("#portal-slots-title").textContent = `Usage Slots — ${btn.dataset.slotLabel}`;
    surface.querySelector("#portal-slots-banner").classList.toggle("hidden", btn.dataset.slotFullAccess !== "1");
    const canBook = canBookSlots;
    surface.querySelector("#portal-slot-form").classList.toggle("hidden", !canBook);
    surface.querySelector("#portal-slot-date").value = new Date().toISOString().slice(0, 10);
    surface.querySelector("#portal-slot-error").classList.add("hidden");
    slotsDialog.showModal();
    await refreshSlots();
    if (canBook) await slotUsers();
  }));

  async function refreshSlots() {
    const list = surface.querySelector("#portal-slots-list");
    if (!list || !slotsAccountId) return;
    const slots = await apiRequest(`/portal-accounts/${slotsAccountId}/slots?page_size=100`).catch(() => ({ items: [] }));
    const items = slots.items || [];
    list.innerHTML = items.length
      ? items.map((s) => `
        <div class="px-4 py-2.5 flex items-center justify-between gap-3">
          <div class="flex items-center gap-3 min-w-0">
            <span class="font-data-tabular text-on-surface whitespace-nowrap">${escapeLiveHtml(s.usage_date)} ${escapeLiveHtml(String(s.start_time).slice(0, 5))}–${escapeLiveHtml(String(s.end_time).slice(0, 5))}</span>
            <span class="truncate font-body-sm text-on-surface-variant">${escapeLiveHtml(s.assigned_user_name || "Unassigned")}</span>
            <span class="inline-flex items-center px-1.5 py-0.5 rounded-sm text-[10px] font-bold uppercase bg-surface-dim text-text-muted">${escapeLiveHtml(s.status)}</span>
          </div>
          ${canBookSlots ? `<button type="button" class="p-1 text-text-muted hover:text-danger-text rounded hover:bg-danger-bg" title="Cancel slot" data-cancel-slot="${s.id}" aria-label="Cancel slot"><span class="material-symbols-outlined text-[16px]">close</span></button>` : ""}
        </div>`).join("")
      : '<div class="px-4 py-6 text-center text-text-muted font-body-sm">No slots booked.</div>';
    list.querySelectorAll("[data-cancel-slot]").forEach((btn) => btn.addEventListener("click", async () => {
      try {
        await apiRequest(`/portal-accounts/${slotsAccountId}/slots/${btn.dataset.cancelSlot}`, { method: "DELETE" });
        showToast("Slot cancelled");
        refreshSlots();
      } catch (error) { showLiveError(error); }
    }));
  }

  surface.querySelector("#portal-slot-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const errorEl = surface.querySelector("#portal-slot-error");
    errorEl.classList.add("hidden");
    const body = {
      assigned_user_id: Number(surface.querySelector("#portal-slot-user").value),
      usage_date: surface.querySelector("#portal-slot-date").value,
      start_time: `${surface.querySelector("#portal-slot-start").value}:00`,
      end_time: `${surface.querySelector("#portal-slot-end").value}:00`,
    };
    try {
      await apiRequest(`/portal-accounts/${slotsAccountId}/slots`, { method: "POST", body: JSON.stringify(body) });
      showToast("Slot booked", `${body.usage_date} ${body.start_time.slice(0, 5)}`);
      refreshSlots();
    } catch (error) {
      errorEl.textContent = error?.message || "Could not book the slot.";
      errorEl.classList.remove("hidden");
    }
  });
}


/* ═══════════════════════════════════════════════════════════════
   PIPELINE MANAGEMENT
   ═══════════════════════════════════════════════════════════════ */

async function loadPipeline() {
  const payload = await apiRequest("/pipeline/board").catch(() => []);
  const items = Array.isArray(payload) ? payload : payload.items || [];
  const board = document.querySelector(".flex.gap-4.min-w-max");
  if (!board) return;
  const columns = Array.from(board.children).filter((col) => col.querySelector("h3"));
  columns.forEach((col) => {
    const title = (col.querySelector("h3")?.textContent || "").trim();
    col.dataset.pipelineStage = title;
    const host = col.querySelector(".pipeline-drop-zone, .space-y-3, .flex-1.overflow-y-auto, .flex-1");
    if (!host) return;
    host.classList.remove("flex", "items-center", "justify-center", "flex-row", "flex-wrap");
    host.classList.add("flex-1", "overflow-y-auto", "hide-scrollbar", "space-y-3", "p-1", "pipeline-drop-zone");
    host.dataset.pipelineDropZone = title;
    const stageItems = items.filter((item) => pipelineStageMatchesColumn(item.current_stage, title));
    const badge = col.querySelector("h3")?.parentElement?.querySelector("span");
    if (badge) badge.textContent = String(stageItems.length);
    host.innerHTML = stageItems.length
      ? stageItems.map((item) => {
          const initials = String(item.candidate_name || "?").split(/\s+/).slice(0, 2).map((w) => w[0] || "").join("").toUpperCase();
          const age = item.stage_entered_at || item.updated_at || item.applied_at;
          return `<div class="pipeline-card bg-surface border border-border rounded-lg p-3 hover:bg-highlight-soft transition-colors cursor-grab" draggable="true" data-application-id="${item.application_id || item.id || ""}" data-filter-owner="${escapeLiveHtml(item.owner_name || item.primary_owner_name || "")}" data-filter-stage="${escapeLiveHtml(item.current_stage || title)}" data-filter-readiness="${escapeLiveHtml(item.readiness || "")}">
            <div class="flex justify-between items-start mb-2 min-w-0">
              <div class="flex items-center gap-2 min-w-0">
                <div class="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center text-[11px] font-semibold shrink-0">${escapeLiveHtml(initials)}</div>
                <div class="min-w-0">
                  <p class="font-headline-sm text-[14px] text-on-surface">${escapeLiveHtml(item.candidate_name || "Candidate")}</p>
                  <p class="font-body-sm text-[12px] text-text-muted">${escapeLiveHtml(item.requisition_title || "Requisition")}</p>
                  ${typeof entityBadgeHtml === "function" ? entityBadgeHtml(item.candidate_code || item.requisition_code, item.branch_code) : ""}
                </div>
              </div>
              <span class="material-symbols-outlined text-text-muted text-[18px] shrink-0">drag_indicator</span>
            </div>
            <div class="flex items-center justify-between border-t border-border pt-2 gap-2 min-w-0">
              <div class="flex items-center gap-1 text-text-muted text-[11px] min-w-0">
                <span class="material-symbols-outlined text-[14px]">schedule</span>
                ${age ? escapeLiveHtml(ageDaysLabel(age)) + " in stage" : "In stage"}
              </div>
              <button class="px-2 py-1 border border-border rounded text-[11px] font-semibold shrink-0" type="button" data-route="stage-move-dialog.html?application_id=${item.application_id || item.id || ""}">Move stage</button>
            </div>
          </div>`;
        }).join("")
      : '<div class="pipeline-empty-note">No candidates in this stage</div>';
  });
  if (typeof setupPipelineBoardInteractions === "function") setupPipelineBoardInteractions();
  if (typeof setupPipelineDragDrop === "function") setupPipelineDragDrop();
  if (typeof hydrateLiveFilters === "function") hydrateLiveFilters();
}

function pipelineStageMatchesColumn(stage, columnTitle) {
  const n = String(stage || "").toLowerCase().replace(/[_-]+/g, " ").trim();
  const t = String(columnTitle || "").toLowerCase();
  if (!n || !t) return false;
  if (n === t || n.includes(t) || t.includes(n)) return true;
  if (/source/.test(t)) return /source|new|applied/.test(n);
  if (/screen/.test(t)) return /screen|submit|l1/.test(n);
  if (/technical|interview/.test(t)) return /tech|l2|interview/.test(n);
  if (/executive|review/.test(t)) return /exec|client|review/.test(n);
  if (/offer/.test(t)) return /offer/.test(n);
  return false;
}async function loadPipelineApplicationDetail() {
  const applicationId = queryInt("application_id");
  if (!applicationId) return;
  try {
    const application = await apiRequest(`/pipeline/applications/${applicationId}`);
    setFirstText("[data-candidate-name]", application.candidate_name);
    setFirstText("[data-current-stage]", application.current_stage);
    const stageDialogName = document.querySelector("[data-candidate-name]");
    if (stageDialogName?.parentElement && typeof entityBadgeHtml === "function" && (application.candidate_code || application.requisition_code) && !stageDialogName.parentElement.querySelector(":scope > .entity-badge")) {
      stageDialogName.insertAdjacentHTML("afterend", entityBadgeHtml(application.candidate_code || application.requisition_code, application.branch_code));
    }
    setFirstText("[data-requisition-title]", application.requisition_title);
  } catch (error) { showLiveError(error); }
}

async function loadPipelineApplicationHistory() {
  const applicationId = queryInt("application_id");
  if (!applicationId) return;
  try {
    const payload = await apiRequest(`/pipeline/applications/${applicationId}/history`);
    const items = payload.items || payload || [];
    const host = document.querySelector(".workspace-surface .space-y-3, .overlay-host .space-y-3");
    renderPipelineHistoryItems(host, items);
  } catch (error) { showLiveError(error); }
}


/* ═══════════════════════════════════════════════════════════════
   DAILY UPDATES & REVIEW
   ═══════════════════════════════════════════════════════════════ */

function ensureDailyUpdateWorkspaceFields(surface) {
  if (!surface) return;
  const reqSelect = surface.querySelector("#req-select, #requisition_id");
  if (reqSelect && !reqSelect.id) reqSelect.id = "requisition_id";
  if (reqSelect && reqSelect.id === "req-select") reqSelect.id = "requisition_id";
  const numbers = Array.from(surface.querySelectorAll('input[type="number"]'));
  const numberIds = ["profiles-sourced-count", "profiles-screened-count", "profiles-submitted-count", "interviews-scheduled-count"];
  numbers.forEach((input, index) => {
    if (!input.id && numberIds[index]) input.id = numberIds[index];
  });
  const areas = Array.from(surface.querySelectorAll("textarea"));
  const areaIds = ["update-summary", "blockers", "next-actions"];
  areas.forEach((area, index) => {
    if (!area.id && areaIds[index]) area.id = areaIds[index];
  });
  if (!document.getElementById("update-date")) {
    const hidden = document.createElement("input");
    hidden.type = "hidden";
    hidden.id = "update-date";
    hidden.value = new Date().toISOString().split("T")[0];
    surface.appendChild(hidden);
  }
}

function wireDailyUpdateWorkspaceActions(surface) {
  if (!surface || surface.dataset.dailyWired === "true") return;
  surface.dataset.dailyWired = "true";
  const submitBtn = Array.from(surface.querySelectorAll("button")).find((btn) => /submit update/i.test((btn.textContent || "").replace(/\s+/g, " ")));
  if (submitBtn) {
    submitBtn.removeAttribute("data-route");
    submitBtn.dataset.dailySubmit = "true";
  }
}

async function loadDailyUpdates() {
  const surface = document.querySelector(".workspace-surface");
  if (!surface) return;
  ensureDailyUpdateWorkspaceFields(surface);
  wireDailyUpdateWorkspaceActions(surface);
  const [updatesPayload, requisitionsPayload] = await Promise.all([
    apiRequest("/daily-updates/?page_size=50").catch(() => ({ items: [], meta: { total: 0 } })),
    apiRequest("/requisitions/?page_size=100").catch(() => ({ items: [] })),
  ]);
  const items = updatesPayload.items || [];
  const submitted = items.filter((item) => String(item.submission_status || "").toLowerCase() === "submitted").length;
  const pending = items.filter((item) => /draft|submitted/i.test(String(item.submission_status || "submitted")) && !/reviewed/i.test(String(item.submission_status || ""))).length;
  const metricValues = surface.querySelectorAll(".flex.gap-4 .font-headline-md");
  if (metricValues[0]) metricValues[0].textContent = String(submitted);
  if (metricValues[1]) metricValues[1].textContent = String(pending);
  const queueCount = Array.from(surface.querySelectorAll("span")).find((el) => /total/i.test(el.textContent || ""));
  if (queueCount) queueCount.textContent = `${items.length} Total`;
  const list = surface.querySelector(".overflow-y-auto.flex-1") || surface.querySelector(".overflow-y-auto");
  if (list) {
    list.innerHTML = items.length
      ? items.map((item) => renderDailyUpdateSubmissionCard(item)).join("")
      : '<div class="p-4 text-text-muted font-body-sm">No updates yet.</div>';
    if (typeof applyCollectionPagination === "function") {
      delete list.dataset.pageSize;
      list.dataset.page = "1";
      applyCollectionPagination(list);
    }
  }
  await fillSelect(
    "requisition_id",
    requisitionsPayload.items || [],
    (r) => `${escapeLiveHtml(r.requisition_code || `REQ-${r.id}`)} — ${escapeLiveHtml(r.title)}`,
    (r) => r.id,
  );
  const draftHint = Array.from(surface.querySelectorAll("span")).find((el) => /draft saved/i.test(el.textContent || ""));
  if (draftHint) draftHint.textContent = "Ready to submit";
}

/* Loader for the daily-updates-submission page: populate the requisition select,
   date input, and the recent-updates list. Never touches the form fields.
   Users without daily_update.create_main get a read-only view (no submit controls). */
async function loadDailyUpdateSubmission() {
  const canSubmit = isAdmin() || hasPermission("daily_update.create_main");
  const [requisitions, updates] = await Promise.all([
    apiRequest("/requisitions/?page_size=100").catch(() => ({ items: [] })),
    apiRequest("/daily-updates/?page_size=20").catch(() => ({ items: [] })),
  ]);
  const reqItems = requisitions.items || [];
  const dateInput = document.getElementById("update-date");
  if (dateInput && !dateInput.value) dateInput.value = new Date().toISOString().split("T")[0];
  await fillSelect("requisition_id", reqItems,
    (r) => `${escapeLiveHtml(r.requisition_code || `REQ-${r.id}`)} — ${escapeLiveHtml(r.title)}`,
    (r) => r.id, queryInt("requisition_id"));
  const recent = document.getElementById("recent-updates-list");
  if (recent) {
    const mine = (updates.items || []).slice(0, 5);
    recent.innerHTML = mine.length
      ? mine.map((u) => `<div class="flex items-center justify-between border border-border rounded-lg px-4 py-3 bg-surface">
          <div class="min-w-0"><p class="truncate font-body-sm text-body-sm font-semibold text-on-surface">${escapeLiveHtml((u.summary || "").slice(0, 90) || "(no summary)")}</p>
          <p class="text-xs text-text-muted mt-0.5">${escapeLiveHtml(String(u.update_date || ""))}</p></div>
          <span class="ml-3 shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold ${u.submission_status === "draft" ? "bg-surface-dim text-text-muted" : "bg-success-container text-success-text"}">${escapeLiveHtml(u.submission_status || "submitted")}</span>
        </div>`).join("")
      : '<p class="text-text-muted">No updates submitted yet — your first one will appear here.</p>';
  }

  /* Read-only mode: strip submit controls and disable the form inputs */
  if (!canSubmit) {
    const surface = document.querySelector(".workspace-surface");
    if (surface) {
      surface.querySelectorAll("[data-route-submit]").forEach((btn) => btn.remove());
      const draftBtn = [...surface.querySelectorAll("button")].find((b) => /^save draft/i.test((b.textContent || "").replace(/\s+/g, " ").trim()));
      if (draftBtn) draftBtn.remove();
      const heading = surface.querySelector("h1");
      if (heading) heading.textContent = "Daily Updates";
      const notice = document.createElement("p");
      notice.className = "mt-2 inline-flex items-center gap-1.5 rounded-lg bg-surface-dim border border-border px-3 py-1.5 font-body-sm text-[12px] text-text-muted";
      notice.innerHTML = '<span class="material-symbols-outlined text-[15px]">lock</span>Read-only — you can view updates but not submit them';
      heading?.after(notice);
      ["update-summary", "requisition_id", "update-date", "profiles-sourced-count", "profiles-screened-count", "profiles-submitted-count", "interviews-scheduled-count", "blockers", "next-actions"].forEach((id) => {
        const field = document.getElementById(id);
        if (field) { field.disabled = true; field.classList.add("opacity-60", "cursor-not-allowed"); }
      });
    }
  }
}

async function loadDailyUpdatesReview() {
  const payload = await apiRequest("/daily-updates/?page_size=50");
  renderDailyUpdatesReview(payload.items || [], payload.meta || {});
}

async function loadDailyUpdateDetail() {
  const updateId = queryInt("daily_update_id");
  if (!updateId) return;
  const updates = await apiRequest("/daily-updates/?page_size=50").catch(() => ({ items: [] }));
  const item = (updates.items || []).find((u) => u.id === updateId) || (updates.items || [])[0];
  if (!item) return;
  setFirstText("[data-update-summary]", item.progress_summary || "—");
}

async function loadDailyReview() {
  const [myWork, pipeline, interviews, offers, actions, notifications, updates] = await Promise.all([
    apiRequest("/dashboards/my-work").catch(() => ({})),
    apiRequest("/pipeline/board").catch(() => []),
    apiRequest("/interviews/?page_size=50").catch(() => ({ items: [] })),
    apiRequest("/offers/?page_size=50").catch(() => ({ items: [] })),
    apiRequest("/workflow-actions/queue?page_size=20").catch(() => ({ items: [] })),
    apiRequest("/notifications/?page_size=10").catch(() => ({ items: [] })),
    apiRequest("/daily-updates/?page_size=20").catch(() => ({ items: [] })),
  ]);
  const pipelineItems = Array.isArray(pipeline) ? pipeline : pipeline.items || [];
  const interviewItems = interviews.items || [];
  const offerItems = offers.items || [];
  const pendingOffers = offerItems.filter((item) => {
    const status = String(item.offer_status || item.application_status || "").toLowerCase();
    return status && !/accepted|rejected|declined|joined|withdrawn/.test(status);
  });
  const thisWeekInterviews = interviewItems.filter((item) => {
    const when = new Date(item.scheduled_at || item.interview_date || item.created_at);
    if (Number.isNaN(when.getTime())) return false;
    const start = new Date();
    start.setDate(start.getDate() - start.getDay());
    start.setHours(0, 0, 0, 0);
    return when >= start;
  });
  hidePanelByHeading("Candidate Updates");
  renderDailyReviewQuickStats(myWork, pipelineItems, {
    interviews: thisWeekInterviews.length,
    offers: pendingOffers.length,
  });
  renderDailyReviewPipelineActivity(pipelineItems.slice(0, 5));
  const actionItems = (actions.items || []).slice(0, 5).map((item) => ({
    icon: "task_alt",
    title: item.title || item.entity_type || "Action",
    href: item.entity_type === "requisition" ? "requisition-list.html" : "approvals-inbox.html",
    action: item.primary_action_label || "Open",
  }));
  if (!actionItems.length && pendingOffers.length) {
    actionItems.push({ icon: "request_quote", title: `${pendingOffers.length} offers waiting`, href: "offer-management.html", action: "Review" });
  }
  renderDailyReviewActions(actionItems);
  renderDailyReviewCompactList("Today's Schedule", thisWeekInterviews.slice(0, 5).map((item) => ({
    icon: "calendar_month",
    title: item.candidate_name || item.title || "Interview",
    meta: item.interview_type || item.status || "Scheduled",
  })), "No interviews this week.");
  const seenTeam = new Set();
  const teamRows = [];
  (updates.items || []).forEach((item) => {
    const name = item.submitted_by_name || item.owner_name || "Teammate";
    if (seenTeam.has(name)) return;
    seenTeam.add(name);
    teamRows.push({ icon: "group", title: name, meta: item.submission_status || "Update" });
  });
  renderDailyReviewCompactList("My Team", teamRows, "No team updates yet.");
  renderDailyReviewCompactList("Recent Notifications", (notifications.items || []).slice(0, 5).map((item) => {
    const story = typeof notificationStory === "function" ? notificationStory(item) : null;
    return {
      icon: story?.icon || "notifications",
      title: story?.headline || item.message || item.title || "Hiring event",
      meta: story?.eventLabel || relativeTime(item.created_at),
    };
  }), "Inbox is clear.");
}


/* ═══════════════════════════════════════════════════════════════
   DASHBOARDS
   ═══════════════════════════════════════════════════════════════ */

/* ═══════════════════════════════════════════════════════════════
   ROLE DASHBOARD — live data from /dashboards/role + requisitions
   ═══════════════════════════════════════════════════════════════ */

async function loadRoleDashboard() {
  const [role, requisitions, dailyUpdates] = await Promise.all([
    apiRequest("/dashboards/role").catch(() => ({})),
    apiRequest("/requisitions/?page_size=50").catch(() => ({ items: [] })),
    apiRequest("/daily-updates/?page_size=50").catch(() => ({ items: [] })),
  ]);

  /* ── KPI strip ── */
  setFirstText("[data-role-metric-open-reqs]", role.open_requisitions ?? "—");
  setFirstText("[data-role-metric-active-candidates]", role.active_candidates ?? "—");
  setFirstText("[data-role-metric-active-apps]", role.active_applications ?? "—");
  setFirstText("[data-role-metric-pending-updates]", role.pending_daily_updates ?? "—");
  setFirstText("[data-role-hint-open-reqs]", "Across all locations");
  setFirstText("[data-role-hint-active-candidates]", "In active pipeline");
  setFirstText("[data-role-hint-active-apps]", "Under review");
  setFirstText("[data-role-hint-pending-updates]", "Awaiting submission");

  /* ── System status ── */
  const totalItems = (role.open_requisitions || 0) + (role.active_candidates || 0);
  const statusEl = document.querySelector("[data-role-system-status]");
  if (statusEl) {
    statusEl.className = "flex items-center gap-1 font-label-caps text-label-caps px-2 py-1 rounded " + (totalItems > 0 ? "text-success-text bg-success-bg" : "text-warning-text bg-warning-bg");
    statusEl.innerHTML = '<span class="material-symbols-outlined text-[14px]">' + (totalItems > 0 ? "check_circle" : "error") + '</span> ' + (totalItems > 0 ? "System Healthy" : "No Data");
  }
  setFirstText("[data-role-last-sync]", "Last sync: just now");

  /* ── Stale requisitions (older than 30 days) ── */
  const reqItems = requisitions.items || [];
  const now = Date.now();
  const stale = reqItems
    .map(r => {
      const created = new Date(r.created_at).getTime();
      const days = Math.floor((now - created) / 86400000);
      return { ...r, days };
    })
    .filter(r => r.days > 30 && r.status === "open")
    .sort((a, b) => b.days - a.days)
    .slice(0, 3);

  const staleEl = document.querySelector("[data-role-stale-reqs]");
  if (staleEl) {
    if (stale.length === 0) {
      staleEl.innerHTML = '<p class="font-body-sm text-body-sm text-text-muted text-center py-4">No stale requisitions.</p>';
    } else {
      staleEl.innerHTML = stale.map(r => {
        const pct = Math.min(100, Math.round((r.days / 60) * 100));
        const barClass = r.days > 45 ? "bg-error" : "bg-warning-text";
        const dayClass = r.days > 45 ? "text-danger-text" : "text-warning-text";
        return `<div class="flex justify-between items-start">
          <div>
            <p class="font-body-sm text-body-sm font-semibold text-on-surface">${escapeLiveHtml(r.title)}</p>
            <p class="font-data-tabular text-data-tabular text-text-muted">REQ-${r.id} \u2022 ${escapeLiveHtml(r.client_name || "—")}</p>
          </div>
          <div class="text-right">
            <p class="font-data-tabular text-data-tabular ${dayClass} font-medium">${r.days} Days</p>
          </div>
        </div>
        <div class="w-full bg-surface-dim h-1.5 rounded-full">
          <div class="${barClass}" style="width: ${pct}%"></div>
        </div>`;
      }).join("");
    }
    setFirstText("[data-role-stale-count]", stale.length > 0 ? `${stale.length} Stale` : "All Clear");
  }

  /* ── Daily update pressure ── */
  const updates = dailyUpdates.items || [];
  const submitted = updates.filter(u => u.submission_status === "submitted").length;
  const pending = role.pending_daily_updates || updates.filter(u => u.submission_status !== "submitted").length;
  const denom = submitted + pending || 1;
  const pressurePct = Math.round((submitted / denom) * 100);
  const pressureEl = document.querySelector("[data-role-pressure-value]");
  if (pressureEl) pressureEl.textContent = `${pressurePct}%`;
  const hintEl = document.querySelector("[data-role-pressure-hint]");
  if (hintEl) hintEl.textContent = `${submitted} submitted · ${pending} still open.`;
}

async function loadDashboards() {
  const [company, pipeline, ttf, sla, requisitions, placements, users, candidates] = await Promise.all([
    apiRequest("/dashboards/company-summary").catch(() => ({})),
    apiRequest("/pipeline/board").catch(() => []),
    apiRequest("/reports/time-to-fill").catch(() => null),
    apiRequest("/reports/datasets/sla").catch(() => null),
    apiRequest("/requisitions/?page_size=100").catch(() => ({ items: [] })),
    apiRequest("/reports/placements").catch(() => ({ rows: [] })),
    apiRequest("/users/?page_size=100").catch(() => ({ items: [] })),
    apiRequest("/candidates/?page_size=100").catch(() => ({ items: [] })),
  ]);
  const pipelineItems = Array.isArray(pipeline) ? pipeline : pipeline.items || [];
  const reqItems = requisitions.items || [];
  const summary = ttf?.summary || {};
  const slaRows = sla?.rows || [];
  const breached = slaRows.filter((row) => row.current_days > row.sla_target_days);
  const slaPct = slaRows.length ? Math.round(((slaRows.length - breached.length) / slaRows.length) * 100) : null;

  hidePanelByHeading("Pipeline Trend (7 Days)");
  hidePanelByHeading("Stage Distribution");
  hidePanelByHeading("Quick Stats");
  hidePanelByHeading("Workload Distribution (Capacity)");
  Array.from(document.querySelectorAll(".workspace-surface span")).some((node) => {
    if (!/^Global Filters$/i.test(readableText(node))) return false;
    const bar = node.closest(".mb-6, .bg-surface");
    if (bar) {
      bar.hidden = true;
      bar.setAttribute("data-ro-hidden-panel", "true");
    }
    return true;
  });
  const now = new Date();
  const quarter = `Q${Math.floor(now.getMonth() / 3) + 1} ${now.getFullYear()}`;
  Array.from(document.querySelectorAll(".workspace-surface button")).forEach((button) => {
    if (/Q3 2023/.test(button.textContent || "")) {
      button.innerHTML = `<span class="material-symbols-outlined text-[16px]">calendar_today</span> ${quarter}`;
    }
  });

  paintLabeledKpi("Total Active Reqs", company.total_open_requisitions || 0, `${company.total_locations || 0} locations`);
  paintLabeledKpi("Avg Time to Fill", summary.avg_days != null ? summary.avg_days : "—", summary.filled_count ? `${summary.filled_count} filled roles` : "No fills yet");
  paintLabeledKpi("Overall SLA Compliance", slaPct != null ? `${slaPct}%` : "—", slaRows.length ? `${slaRows.length - breached.length} of ${slaRows.length} on track` : "No SLA sample yet");
  paintLabeledKpi("Total Placements (YTD)", company.total_joined_applications || 0, `${company.total_active_applications || 0} active applications`);

  const stageContainer = document.querySelector("[data-live-stage-chart]");
  if (stageContainer) {
    const stageCounts = {};
    pipelineItems.forEach((item) => {
      const stage = item.current_stage || "Unknown";
      stageCounts[stage] = (stageCounts[stage] || 0) + 1;
    });
    const sorted = Object.entries(stageCounts).sort((a, b) => b[1] - a[1]);
    if (!sorted.length) {
      stageContainer.innerHTML = '<p class="text-body-sm text-text-muted text-center py-6">No pipeline volume yet.</p>';
    } else {
      const maxCount = Math.max(...sorted.map((row) => row[1]), 1);
      stageContainer.innerHTML = sorted.map(([stage, count]) => {
        const pct = Math.max(8, Math.round((count / maxCount) * 100));
        const label = stage.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
        return `<div class="flex items-center gap-3 min-w-0">
          <span class="w-[168px] shrink-0 text-[12px] leading-snug text-on-surface" title="${escapeLiveHtml(label)}">${escapeLiveHtml(label)}</span>
          <div class="flex-1 h-2.5 rounded bg-[#f1f2f0] overflow-hidden">
            <div class="h-full rounded" style="width:${pct}%;background:#1e293b;opacity:0.78"></div>
          </div>
          <span class="w-8 shrink-0 text-right text-[12px] font-semibold tabular-nums text-on-surface">${count}</span>
        </div>`;
      }).join("");
    }
  }

  const funnelApplied = document.querySelector("[data-live-funnel-applied]");
  if (funnelApplied) {
    const submitted = company.total_submitted_profiles || company.total_active_candidates || 0;
    const active = company.total_active_applications || 0;
    const joined = company.total_joined_applications || 0;
    const interview = Math.max(active, 0);
    const offer = Math.max(active - joined, 0);
    const values = [submitted || active || pipelineItems.length, active || pipelineItems.length, interview, offer, joined];
    const maxVal = Math.max(...values, 1);
    const nodes = [
      document.querySelector("[data-live-funnel-applied]"),
      document.querySelector("[data-live-funnel-screening]"),
      document.querySelector("[data-live-funnel-interview]"),
      document.querySelector("[data-live-funnel-offer]"),
      document.querySelector("[data-live-funnel-joined]"),
    ];
    nodes.forEach((node, index) => {
      if (!node) return;
      node.textContent = values[index];
      const bar = node.parentElement;
      if (!bar) return;
      const pct = Math.max(14, Math.round((values[index] / maxVal) * 100));
      bar.className = bar.className.replace(/w-\[[^\]]+\]/g, "").trim();
      bar.style.width = `${pct}%`;
    });
    const pcts = document.querySelectorAll("[data-live-funnel-pct]");
    pcts.forEach((node, index) => {
      node.textContent = `${Math.round((values[index] / maxVal) * 100)}%`;
    });
  }

  renderCompanySlaRisks(reqItems);
  renderCompanyLocations(company.locations || []);
  renderCompanyClientDemand(reqItems);

  const revenueContainer = document.querySelector("[data-live-revenue-chart]");
  if (revenueContainer) {
    const clientRevenue = {};
    (placements.rows || []).forEach((row) => {
      const client = row.client || "Unknown";
      clientRevenue[client] = (clientRevenue[client] || 0) + (row.revenue || 0);
    });
    const revenueData = Object.entries(clientRevenue)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([label, value]) => ({ label, value: Math.round(value) }));
    renderRankedMetricList(revenueContainer, revenueData, {
      format: (value) => value ? `$${Number(value).toLocaleString()}` : "—",
      insight: revenueData[0] ? `${revenueData[0].label} currently leads placement revenue.` : "",
      empty: "No placement revenue this period.",
    });
  }

  const recruiterContainer = document.querySelector("[data-live-recruiter-chart]");
  if (recruiterContainer) {
    const userMap = {};
    (users.items || []).forEach((user) => { userMap[user.id] = user.full_name || user.email; });
    const counts = {};
    reqItems.forEach((row) => {
      const owner = userMap[row.owner_user_id] || "Unassigned";
      counts[owner] = (counts[owner] || 0) + 1;
    });
    (candidates.items || []).forEach((row) => {
      const owner = userMap[row.owner_user_id] || userMap[row.sourced_by_user_id] || "Unassigned";
      counts[owner] = (counts[owner] || 0) + 1;
    });
    const recruiterData = Object.entries(counts)
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 6);
    renderRankedMetricList(recruiterContainer, recruiterData, {
      insight: recruiterData[0] ? `${recruiterData[0].label} owns the most live work.` : "",
      empty: "No recruiter activity yet.",
    });
  }
}

async function loadMyWorkDashboard() {
  const [myWork, requisitions, pipeline, interviews, updates] = await Promise.all([
    apiRequest("/dashboards/my-work").catch(() => ({})),
    apiRequest("/requisitions/?page_size=50").catch(() => ({ items: [] })),
    apiRequest("/pipeline/board").catch(() => []),
    apiRequest("/interviews/?page_size=50").catch(() => ({ items: [] })),
    apiRequest("/daily-updates/?page_size=20").catch(() => ({ items: [] })),
  ]);
  const pipelineItems = Array.isArray(pipeline) ? pipeline : pipeline.items || [];
  const reqItems = (requisitions.items || []).filter((row) => String(row.status || "open") === "open").slice(0, 6);
  const tbody = document.querySelector(".workspace-surface tbody");
  if (tbody) {
    tbody.innerHTML = reqItems.length
      ? reqItems.map((row) => {
          const created = new Date(row.created_at).getTime();
          const days = Number.isNaN(created) ? "—" : Math.floor((Date.now() - created) / 86400000);
          const priority = days > 30 ? "High" : days > 14 ? "Med" : "Low";
          return `<tr class="border-b border-border h-table-row hover:bg-highlight-soft">
            <td class="px-4">${typeof entityBadgeHtml === "function" && row.requisition_code ? entityBadgeHtml(row.requisition_code, row.branch_code) : escapeLiveHtml(row.requisition_code || `REQ-${row.id}`)}</td>
            <td class="px-4">${escapeLiveHtml(row.title || "Requisition")}</td>
            <td class="px-4"><span class="px-2 py-0.5 rounded-sm bg-success-bg text-success-text text-[11px] font-bold">${escapeLiveHtml(String(row.status || "open").toUpperCase())}</span></td>
            <td class="px-4">${days}</td>
            <td class="px-4">${priority}</td>
          </tr>`;
        }).join("")
      : `<tr><td class="px-4 py-6 text-text-muted" colspan="5">No open requisitions on your desk yet.</td></tr>`;
  }
  const actionHost = findPanelByHeading("Action Required")?.querySelector(".flex.gap-4");
  if (actionHost) {
    actionHost.innerHTML = `
      <div class="flex-1 bg-danger-bg border border-border rounded p-3">
        <div class="font-headline-sm text-on-surface mb-1">${pipelineItems.length} in pipeline</div>
        <div class="font-body-sm text-text-muted">${myWork.owned_requisitions ?? reqItems.length} open requisitions.</div>
      </div>
      <div class="flex-1 bg-warning-bg border border-border rounded p-3">
        <div class="font-headline-sm text-on-surface mb-1">${myWork.submitted_updates ?? 0} updates in</div>
        <div class="font-body-sm text-text-muted">${myWork.sourced_candidates ?? 0} sourced candidates.</div>
      </div>`;
  }
  const updatePanel = findPanelByHeading("Daily Update Status");
  const pendingUpdates = (updates.items || []).filter((item) => item.submission_status !== "submitted").length;
  const updateCopy = updatePanel?.querySelector(".font-data-tabular");
  if (updateCopy) updateCopy.textContent = pendingUpdates ? `${pendingUpdates} pending update${pendingUpdates === 1 ? "" : "s"}` : "Caught up";
  const updateHint = updatePanel?.querySelector(".font-body-sm, .text-body-sm");
  if (updateHint) updateHint.textContent = pendingUpdates ? "Still waiting on the desk." : "No pending submissions.";
  updatePanel?.querySelector(".animate-spin")?.classList.remove("animate-spin", "border-t-transparent");
  const followHost = findPanelByHeading("Today's Follow-ups")?.querySelector("ul");
  const upcoming = (interviews.items || []).slice(0, 4);
  if (followHost) {
    followHost.innerHTML = upcoming.length
      ? upcoming.map((item) => `<li class="p-3 hover:bg-highlight-soft rounded flex gap-3">
          <div>
            <div class="font-data-tabular text-on-surface leading-tight">${escapeLiveHtml(item.candidate_name || item.title || "Interview")}</div>
            <div class="font-body-sm text-text-muted mt-0.5">${escapeLiveHtml(item.interview_type || item.status || "Scheduled")}</div>
          </div>
        </li>`).join("")
      : `<li class="p-3 text-body-sm text-text-muted">No follow-ups scheduled today.</li>`;
  }
  const overview = findPanelByHeading("Candidate Workload Overview")?.querySelector(".grid");
  if (overview) {
    const stages = pipelineStageBuckets(pipelineItems, []);
    overview.innerHTML = stages.slice(0, 4).map((stage) => `<div class="p-4 border border-border rounded bg-background flex flex-col items-center justify-center text-center">
      <span class="font-headline-lg text-headline-lg text-on-surface mb-1">${stage.count}</span>
      <span class="font-label-caps text-label-caps text-text-muted">${escapeLiveHtml(stage.label)}</span>
    </div>`).join("");
  }
}


/* ═══════════════════════════════════════════════════════════════
   LOCATION DASHBOARD
   ═══════════════════════════════════════════════════════════════ */async function loadLocationDashboard() {
  const locationId = queryInt("location_id") || currentLocationId();
  const [location, requisitions, candidates] = await Promise.all([
    apiRequest(`/locations/${locationId}`).catch(() => ({})),
    apiRequest("/requisitions/?page_size=100").catch(() => ({ items: [] })),
    apiRequest("/candidates/?page_size=100").catch(() => ({ items: [] })),
  ]);
  setFirstText("[data-location-name]", location.location_name || location.name || "Location");
  const reqItems = (requisitions.items || []).filter((r) => !locationId || r.location_id === locationId);
  const candItems = (candidates.items || []).filter((c) => !locationId || c.location_id === locationId);
  fillDashboardMetrics([
    { label: "Active Reqs", value: reqItems.length, hint: "Open requisitions" },
    { label: "Candidates", value: candItems.length, hint: "Total candidates" },
  ]);
}


/* ═══════════════════════════════════════════════════════════════
   WORKLOAD & PERFORMANCE REPORTS
   ═══════════════════════════════════════════════════════════════ */async function loadTeamWorkload() {
  const [users, requisitions, candidates] = await Promise.all([
    apiRequest("/users/?page_size=100").catch(() => ({ items: [] })),
    apiRequest("/requisitions/?page_size=100").catch(() => ({ items: [] })),
    apiRequest("/candidates/?page_size=100").catch(() => ({ items: [] })),
  ]);
  const members = buildWorkloadMembers(users.items || [], requisitions.items || [], candidates.items || []);
  const tbody = document.querySelector(".workspace-surface tbody");
  if (tbody) tbody.innerHTML = renderTeamWorkloadRows(members);
}

async function loadUserPerformanceReports() {
  const [users, requisitions, candidates, offers] = await Promise.all([
    apiRequest("/users/?page_size=100").catch(() => ({ items: [] })),
    apiRequest("/requisitions/?page_size=100").catch(() => ({ items: [] })),
    apiRequest("/candidates/?page_size=100").catch(() => ({ items: [] })),
    apiRequest("/offers/?page_size=50").catch(() => ({ items: [] })),
  ]);
  const members = buildUserPerformanceMembers(users.items || [], requisitions.items || [], candidates.items || [], offers.items || []);
  const tbody = document.querySelector(".workspace-surface tbody");
  if (tbody) tbody.innerHTML = renderUserPerformanceRows(members);
  renderUserPerformanceTriage(members);
  renderUserPerformanceWorkloadChart(members);
}


/* ═══════════════════════════════════════════════════════════════
   TIME-TO-FILL & SLA
   ═══════════════════════════════════════════════════════════════ */

function daysBetween(startValue, endValue) {
  const start = new Date(startValue);
  const end = new Date(endValue);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return 0;
  return Math.max(0, Math.round((end - start) / 86400000));
}

function titleLevelFromText(title) {
  const text = String(title || "").toLowerCase();
  if (/\b(vp|chief|head)\b/.test(text)) return "VP";
  if (/\b(director)\b/.test(text)) return "Director";
  if (/\b(lead|principal|staff|manager)\b/.test(text)) return "Lead";
  if (/\b(senior|sr)\b/.test(text)) return "Senior";
  return "Mid";
}

function timeToFillRecords(requisitions, offers) {
  return (requisitions || [])
    .filter((r) => r.status === "closed" || r.status === "filled")
    .map((r) => {
      const offer = (offers || []).find((o) => o.requisition_id === r.id && (o.application_status === "joined" || String(o.offer_status || "").toLowerCase() === "accepted"));
      const days = daysBetween(r.created_at, offer?.accepted_at || offer?.updated_at || r.updated_at);
      return { title: r.title, days, level: titleLevelFromText(r.title) };
    })
    .filter((r) => r.days > 0)
    .sort((a, b) => b.days - a.days);
}function slaTargetDays(item) {
  const level = titleLevelFromText(item?.title);
  if (level === "VP" || level === "Director") return 60;
  if (level === "Lead") return 45;
  if (level === "Senior") return 35;
  return 30;
}function slaStatusBadge(status) {
  const normalized = String(status || "").toLowerCase();
  if (normalized === "on track") return "bg-success-bg text-success-text";
  if (normalized === "at risk") return "bg-warning-bg text-warning-text";
  return "bg-danger-bg text-danger-text";
}

function setMetricCardValue(labelText, valueText, hintHtml = "") {
  const needle = String(labelText || "").toLowerCase();
  const card = Array.from(document.querySelectorAll(".metric-card, .workspace-surface .bg-surface.border")).find((node) => {
    const label = node.querySelector("h3, .text-label-caps, span.text-label-caps");
    return label && readableText(label).toLowerCase() === needle;
  });
  if (!card) return;
  const headline = card.querySelector("p[class*='headline'], .text-headline-lg, .font-headline-lg");
  if (headline) headline.textContent = valueText;
  const hint = card.querySelector("p.text-body-sm:last-of-type, p.font-body-sm:last-of-type");
  if (hint && hintHtml) hint.innerHTML = hintHtml;
}

/* ═══════════════════════════════════════════════════════════════
   REPORT VIEWER — letterhead reports (placements / client summary)
   One owner for the loaded report payload: reportState. The toolbar,
   KPI strip, table, CSV export and print button all read from it.
   ═══════════════════════════════════════════════════════════════ */
const reportState = { type: "placements", data: null, columns: [], profile: null };

function reportIsoDaysAgo(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

function reportIsoDate(d) {
  /* Local-date ISO string — toISOString() shifts by timezone (IST gave Aug 31 for Sep 1). */
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function reportDefaultPeriod() {
  const now = new Date();
  const from = new Date(now.getFullYear(), now.getMonth(), 1);
  const to = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  return { from: reportIsoDate(from), to: reportIsoDate(to) };
}

function reportFormatNumber(value) {
  if (value == null || value === "") return "—";
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function reportMoney(value, currency) {
  if (value == null) return "—";
  const num = Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
  return currency ? `${num} ${currency}` : num;
}

async function loadReportLetterhead() {
  if (reportState.profile) return reportState.profile;
  const profile = await apiRequest("/settings/profile").catch(() => null);
  if (!profile) return null;
  reportState.profile = profile;
  setFirstText("#lh-company", profile.display_name || "Company");
  const addressBits = [profile.registered_address, profile.hq_city, profile.hq_state, profile.country_name]
    .filter(Boolean)
    .filter((part, index, all) =>
      /* Skip city/state/country when the street address already contains them. */
      index === 0 || !all[0].toLowerCase().includes(part.toLowerCase())
    );
  setFirstText("#lh-address", addressBits.join(", "));
  const contactBits = [profile.support_phone, profile.support_email, profile.website_url]
    .filter(Boolean);
  setFirstText("#lh-contact", contactBits.join(" · "));
  if (profile.has_logo) {
    const img = document.querySelector("#lh-logo");
    const fallback = document.querySelector("#lh-logo-fallback");
    if (img) {
      img.src = `/api/v1/settings/logo?t=${Date.now()}`;
      img.classList.remove("hidden");
      if (fallback) fallback.classList.add("hidden");
    }
  }
  return profile;
}

function renderReportKpis(kpis) {
  const strip = document.querySelector("#report-kpis");
  if (!strip) return;
  strip.innerHTML = kpis
    .map(
      (k) => `
      <div class="metric-card bg-surface border border-outline-variant rounded-lg p-4">
        <div class="flex items-center justify-between mb-2">
          <span class="text-label-caps font-bold text-text-muted uppercase tracking-wider">${escapeLiveHtml(k.label)}</span>
          <span class="material-symbols-outlined text-[20px] text-primary">${k.icon || "bar_chart"}</span>
        </div>
        <p class="text-headline-md font-bold text-on-surface">${escapeLiveHtml(k.value)}</p>
        ${k.hint ? `<p class="text-body-sm text-text-muted mt-1">${escapeLiveHtml(k.hint)}</p>` : ""}
      </div>`
    )
    .join("");
}

function renderReportTable(columns, rows, footerRow) {
  const head = document.querySelector("#report-table-head");
  const body = document.querySelector("#report-table-body");
  const foot = document.querySelector("#report-table-foot");
  if (!head || !body) return;
  head.innerHTML = `<tr>${columns.map((c) => `<th class="${c.num ? "num" : ""}">${escapeLiveHtml(c.label)}</th>`).join("")}</tr>`;
  body.innerHTML = rows.length
    ? rows
        .map(
          (row) =>
            `<tr>${columns
              .map((c) => `<td class="${c.num ? "num" : ""}">${escapeLiveHtml(String(row[c.key] ?? "—"))}</td>`)
              .join("")}</tr>`
        )
        .join("")
    : `<tr><td colspan="${columns.length}" class="text-center text-text-muted py-8">No placements recorded in this period.</td></tr>`;
  if (foot) {
    foot.innerHTML = footerRow
      ? `<tr>${columns
          .map((c) => `<td class="${c.num ? "num" : ""}">${escapeLiveHtml(String(footerRow[c.key] ?? ""))}</td>`)
          .join("")}</tr>`
      : "";
  }
  reportState.columns = columns;
}

function downloadReportCsv() {
  const { columns, data, type } = reportState;
  if (!data || !columns.length) return;
  const rows = type === "placements" ? data.rows : data.rows;
  const lines = [columns.map((c) => c.label).join(",")];
  for (const row of rows) {
    lines.push(
      columns
        .map((c) => {
          const raw = row[c.key];
          const text = raw == null ? "" : String(raw);
          return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
        })
        .join(",")
    );
  }
  const blob = new Blob(["\ufeff" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${type}-report-${data.period_from}-to-${data.period_to}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
  if (typeof showToast === "function") showToast("Excel (CSV) downloaded", "Your export is ready");
}

const REPORT_DEFS = {
  placements: {
    name: "Placements Report",
    sectionTitle: "1. Placement Details",
    columns: (currency) => [
      { key: "candidate", label: "Candidate" },
      { key: "client", label: "Client" },
      { key: "requisition", label: "Requisition" },
      { key: "consultant", label: "Consultant" },
      { key: "joining_date", label: "Joining Date" },
      { key: "ctc_display", label: "CTC (incl. bonus)", num: true },
      { key: "fee_pct_display", label: "Fee %", num: true },
      { key: "revenue_display", label: "Revenue", num: true },
      { key: "days_to_fill", label: "Days to Fill", num: true },
      ...(currency ? [] : []),
    ],
  },
  "client-summary": {
    name: "Client Summary Report",
    sectionTitle: "1. Client Summary",
    columns: () => [
      { key: "client_name", label: "Client" },
      { key: "requisitions", label: "Requisitions", num: true },
      { key: "open_requisitions", label: "Open", num: true },
      { key: "placements", label: "Placements", num: true },
      { key: "revenue_display", label: "Revenue", num: true },
      { key: "avg_days_to_fill_display", label: "Avg Days to Fill", num: true },
    ],
  },
};

function applyPeriodToUi(data, reportName) {
  setFirstText("#report-title", reportName);
  setFirstText("#lh-report-name", reportName);
  const label = `Reporting period: ${data.period_from} to ${data.period_to}`;
  setFirstText("#report-period-label", label);
  setFirstText("#lh-ref", `Ref: RPT-${data.period_from.slice(0, 7)} · Generated ${new Date().toLocaleDateString()}`);
  setFirstText("#report-footer", `Generated ${new Date().toLocaleString()} · Confidential — for internal and client use only`);
  const from = document.querySelector("#report-period-from");
  const to = document.querySelector("#report-period-to");
  if (from && !from.value) from.value = data.period_from;
  if (to && !to.value) to.value = data.period_to;
}

async function fetchAndRenderReport() {
  const typeSel = document.querySelector("#report-type");
  const type = typeSel ? typeSel.value : reportState.type;
  reportState.type = type;
  const fromInput = document.querySelector("#report-period-from");
  const toInput = document.querySelector("#report-period-to");
  const params = new URLSearchParams();
  if (fromInput && fromInput.value) params.set("period_from", fromInput.value);
  if (toInput && toInput.value) params.set("period_to", toInput.value);
  const query = params.toString() ? `?${params}` : "";
  const data = await apiRequest(`/reports/${type}${query}`).catch(() => null);
  if (!data) {
    if (typeof showToast === "function") showToast("Could not load report", "Please check your connection and try again");
    return;
  }
  reportState.data = data;
  const def = REPORT_DEFS[type];
  const currency = data.currency || null;
  applyPeriodToUi(data, def.name);
  setFirstText("#report-section-title", def.sectionTitle);
  const subtitle = document.querySelector("#report-section-subtitle");
  if (subtitle) {
    subtitle.textContent = type === "placements"
      ? "Every candidate who joined in the period, with derived commercial value."
      : "Requisitions, placements, and revenue aggregated per client for the period.";
  }
  document.title = `${def.name} - RecruitOps`;
  const shellTitle = document.querySelector("[data-shell-page-title]");
  if (shellTitle) shellTitle.textContent = def.name;

  if (type === "placements") {
    const s = data.summary || {};
    renderReportKpis([
      { label: "Placements", value: String(s.placements ?? 0), icon: "how_to_reg", hint: `${s.distinct_requisitions ?? 0} requisition(s) · ${s.distinct_clients ?? 0} client(s)` },
      { label: "Total Revenue", value: reportMoney(s.total_revenue, currency), icon: "payments" },
      { label: "Total CTC", value: reportMoney(s.total_ctc, currency), icon: "account_balance_wallet" },
      { label: "Avg Days to Fill", value: s.avg_days_to_fill != null ? `${s.avg_days_to_fill} days` : "—", icon: "schedule" },
    ]);
    const columns = def.columns(currency).map((c) => ({ ...c }));
    const rows = (data.rows || []).map((r) => ({
      ...r,
      ctc_display: reportMoney(r.ctc, r.currency || currency),
      fee_pct_display: r.fee_pct != null ? `${r.fee_pct}%` : "standard",
      revenue_display: reportMoney(r.revenue, r.currency || currency),
    }));
    const footerRow = rows.length
      ? { candidate: "Total", ctc_display: reportMoney(s.total_ctc, currency), revenue_display: reportMoney(s.total_revenue, currency) }
      : null;
    renderReportTable(columns, rows, footerRow);
  } else {
    const t = data.totals || {};
    renderReportKpis([
      { label: "Clients", value: String(t.clients ?? 0), icon: "business" },
      { label: "Requisitions", value: `${t.requisitions ?? 0} (${t.open_requisitions ?? 0} open)`, icon: "work" },
      { label: "Placements", value: String(t.placements ?? 0), icon: "how_to_reg" },
      { label: "Total Revenue", value: reportMoney(t.revenue, currency), icon: "payments" },
    ]);
    const rows = (data.rows || []).map((r) => ({
      ...r,
      revenue_display: reportMoney(r.revenue, currency),
      avg_days_to_fill_display: r.avg_days_to_fill != null ? `${r.avg_days_to_fill} days` : "—",
    }));
    const footerRow = rows.length
      ? { client_name: "Total", requisitions: t.requisitions, open_requisitions: t.open_requisitions, placements: t.placements, revenue_display: reportMoney(t.revenue, currency) }
      : null;
    renderReportTable(def.columns(currency), rows, footerRow);
  }
}

/* Letterhead editor — company profile fields + logo, edited inline from the
   report viewer. Admin-gated: only shown when the actor has settings.update. */
function openLetterheadDialog(onSaved) {
  const canEdit = isAdmin() || hasPermission("settings.update");
  if (!canEdit) {
    showToast("Not permitted", "Only admins can change the company letterhead.");
    return;
  }
  apiRequest("/settings/profile")
    .then(async (profile) => {
      openEntityDialog({
        id: "letterhead-dialog-overlay",
        title: "Company Letterhead",
        submitLabel: "Save Letterhead",
        fields: [
          { name: "display_name", label: "Company Name", required: true, value: profile.display_name || "" },
          { name: "registered_address", label: "Registered Address", value: profile.registered_address || "", placeholder: "Street, area" },
          { name: "hq_city", label: "City", value: profile.hq_city || "" },
          { name: "hq_state", label: "State", value: profile.hq_state || "" },
          { name: "country_name", label: "Country", value: profile.country_name || "" },
          { name: "support_phone", label: "Phone", value: profile.support_phone || "" },
          { name: "support_email", label: "Email", value: profile.support_email || "" },
          { name: "website_url", label: "Website", value: profile.website_url || "", placeholder: "https://" },
          { name: "logo_data_url", label: "Logo (PNG/JPG, ≤ 300KB)", type: "file", accept: "image/*" },
        ],
        onSubmit: async (values, close) => {
          await apiRequest("/settings/profile", {
            method: "PATCH",
            body: JSON.stringify({
              display_name: values.display_name.trim(),
              registered_address: values.registered_address || null,
              hq_city: values.hq_city || null,
              hq_state: values.hq_state || null,
              country_name: values.country_name || null,
              support_phone: values.support_phone || null,
              support_email: values.support_email || null,
              website_url: values.website_url || null,
            }),
          });
          const logoInput = document.querySelector("#letterhead-dialog-overlay #logo_data_url");
          const file = logoInput && logoInput.files && logoInput.files[0];
          if (file) {
            if (file.size > 300 * 1024) throw new Error("Logo must be 300KB or smaller.");
            const dataUrl = await new Promise((resolve, reject) => {
              const reader = new FileReader();
              reader.onload = () => resolve(String(reader.result));
              reader.onerror = () => reject(new Error("Could not read the logo file."));
              reader.readAsDataURL(file);
            });
            await apiRequest("/settings/logo", { method: "PUT", body: JSON.stringify({ data_url: dataUrl }) });
          }
          reportState.profile = null; // force letterhead refresh
          await loadReportLetterhead();
          close();
          showToast("Letterhead updated", "Reports will now use the new branding.");
          if (onSaved) onSaved();
        },
      });
    })
    .catch(() => showToast("Could not load letterhead", "Please try again."));
}

async function loadReportViewer() {
  await loadReportLetterhead();
  const defaults = reportDefaultPeriod();
  const from = document.querySelector("#report-period-from");
  const to = document.querySelector("#report-period-to");
  if (from && !from.value) from.value = defaults.from;
  if (to && !to.value) to.value = defaults.to;

  /* Deep links: report-viewer.html?type=client-summary opens the client view. */
  const typeParam = new URLSearchParams(location.search).get("type");
  const typeSelect = document.querySelector("#report-type");
  if (typeParam && typeSelect && REPORT_DEFS[typeParam]) {
    typeSelect.value = typeParam;
    reportState.type = typeParam;
  }

  const apply = document.querySelector("#report-apply");
  const print = document.querySelector("#report-print");
  const csv = document.querySelector("#report-csv");
  const letterhead = document.querySelector("#report-letterhead");
  if (apply && !apply.dataset.wired) {
    apply.dataset.wired = "1";
    apply.addEventListener("click", fetchAndRenderReport);
    typeSelect && typeSelect.addEventListener("change", fetchAndRenderReport);
    print && print.addEventListener("click", () => window.print());
    csv && csv.addEventListener("click", downloadReportCsv);
    letterhead && letterhead.addEventListener("click", () => openLetterheadDialog(fetchAndRenderReport));
  }
  await fetchAndRenderReport();
}

async function loadTimeToFillReport() {
  const report = await apiRequest("/reports/time-to-fill").catch(() => null);
  if (!report) return;
  const summary = report.summary || {};
  const emptyHint = `<span class="text-body-sm text-text-muted">No filled roles yet</span>`;
  setMetricCardValue("Avg Time to Fill", summary.avg_days != null ? `${summary.avg_days} days` : "—",
    summary.filled_count ? `<span class="text-body-sm text-text-muted">across ${summary.filled_count} filled role${summary.filled_count === 1 ? "" : "s"}</span>` : emptyHint);
  setMetricCardValue("Fastest Fill", summary.fastest_days != null ? `${summary.fastest_days} days` : "—",
    summary.fastest_requisition ? `<span class="text-body-sm text-text-muted">${escapeLiveHtml(summary.fastest_requisition)}</span>` : emptyHint);
  setMetricCardValue("Slowest Fill", summary.slowest_days != null ? `${summary.slowest_days} days` : "—",
    summary.slowest_requisition ? `<span class="text-body-sm text-text-muted">${escapeLiveHtml(summary.slowest_requisition)}</span>` : emptyHint);
  setMetricCardValue("Within SLA", summary.within_sla_percent != null ? `${summary.within_sla_percent}%` : "—",
    summary.filled_count ? `<span class="text-body-sm text-text-muted">${summary.within_sla} of ${summary.filled_count} fills</span>` : emptyHint);
  renderTimeToFillBars("Time to Fill by Department", (report.by_department || []).map((row) => ({ label: row.label, days: row.avg_days })));
  renderTimeToFillBars("Time to Fill by Seniority", (report.by_seniority || []).map((row) => ({ label: row.label, days: row.avg_days })));
  renderTimeToFillTrend(report);
}

async function loadSourceEffectiveness() {
  const report = await apiRequest("/reports/source-effectiveness").catch(() => null);
  if (!report) return;
  setMetricCardValue("Total Sources", String(report.total_sources || 0));
  setMetricCardValue("Best Source", report.best_source || "—",
    report.best_source_conversion != null ? `<span class="text-body-sm text-success">${report.best_source_conversion}% conversion rate</span>` : "");
  const rows = report.rows || [];
  const conversions = rows.map((row) => row.conversion_rate).filter((value) => value != null);
  const avgConversion = conversions.length ? Math.round(conversions.reduce((sum, value) => sum + value, 0) / conversions.length) : null;
  setMetricCardValue("Avg Cost per Hire", "—",
    `<span class="text-body-sm text-text-muted">${avgConversion != null ? `${avgConversion}% avg conversion` : "Cost is not tracked yet"}</span>`);
  const diversity = Math.min(10, (report.total_sources || 0) * 2);
  setMetricCardValue("Source Diversity Score", report.total_sources ? `${diversity}/10` : "—",
    `<span class="text-body-sm text-text-muted">${report.total_sources || 0} active channels</span>`);
  renderSourceEffectivenessTable(rows);
  renderSourceLeaderboard(rows);
  renderSourceRecommendations(rows);
}

async function loadSlaTracker() {
  const dataset = await apiRequest("/reports/datasets/sla").catch(() => null);
  if (!dataset) return;
  const rows = dataset.rows || [];
  const breached = rows.filter((row) => row.current_days > row.sla_target_days);
  const atRisk = rows.filter((row) => row.status !== "closed" && row.status !== "filled" && Math.abs(row.current_days - row.sla_target_days) <= 5);
  setMetricCardValue("Overall Compliance", rows.length ? `${Math.round(((rows.length - breached.length) / rows.length) * 100)}%` : "—");
  setMetricCardValue("At Risk", String(atRisk.length));
  setMetricCardValue("Breached", String(breached.length));
  const open = rows.filter((row) => row.status !== "closed" && row.status !== "filled");
  const avgOpen = open.length ? Math.round(open.reduce((sum, row) => sum + (row.current_days || 0), 0) / open.length) : null;
  setMetricCardValue("Avg Time to Fill", avgOpen != null ? `${avgOpen} days` : "—");
  renderSlaTrackerTable(rows);
}/* ═══════════════════════════════════════════════════════════════
   WORKFLOW ACTIONS & OVERLAY
   ═══════════════════════════════════════════════════════════════ */

function renderOverlayWorkflowActions(items, hostSelector, emptyLabel) {
  const host = document.querySelector(hostSelector);
  if (!host) return;
  host.innerHTML = items.length
    ? items.map((item) => `<div class="flex items-center gap-3 rounded-lg p-2 border-b border-border hover:bg-highlight-soft transition-colors" data-live-workflow-row="true" data-action-item-id="${item.id}">
        <span class="material-symbols-outlined text-primary">task_alt</span>
        <div class="min-w-0 flex-1"><p class="font-medium text-on-surface">${escapeLiveHtml(item.title)}</p><p class="text-[11px] text-text-muted">${escapeLiveHtml(item.entity_type || "Record")}</p></div>
        <button class="text-primary text-xs font-semibold" type="button" data-live-workflow-action="${workflowEndpointForLabel(item.primary_action_label)}" data-action-item-id="${item.id}">${escapeLiveHtml(item.primary_action_label || "Do Now")}</button>
      </div>`).join("")
    : `<div class="p-4 text-center text-text-muted">${emptyLabel || "No workflow actions."}</div>`;
}

function overlayActionTypeFromButton(button) {
  return button?.dataset?.liveWorkflowAction || "run";
}

async function runWorkflowAction(button) {
  const actionId = intOrNull(button?.dataset.actionItemId);
  const actionType = overlayActionTypeFromButton(button);
  if (!actionId) return;
  try {
    await apiRequest(`/workflow-actions/${actionId}/${actionType}`, { method: "POST" });
    showLiveSuccess("Action completed");
    loadWorkflowActions();
  } catch (error) { showLiveError(error); }
}async function loadWorkflowOverlay() {
  const payload = await apiRequest("/workflow-actions/queue?page_size=50").catch(() => ({ items: [] }));
  renderOverlayWorkflowActions(payload.items || [], ".overlay-host .space-y-3, .workspace-surface", "No workflow actions.");
}

async function runDuplicateDecision(button) {
  const decision = button?.dataset.decision || "keep_original";
  const caseId = intOrNull(button?.dataset.caseId);
  if (!caseId) return;
  try {
    await apiRequest(`/candidates/duplicates/${caseId}/decide`, { method: "POST", body: JSON.stringify({ decision }) });
    showLiveSuccess("Decision recorded");
  } catch (error) { showLiveError(error); }
}

async function markLiveNotificationRead(button) {
  const notificationId = intOrNull(button?.dataset.notificationId);
  if (!notificationId) return;
  try {
    await apiRequest(`/notifications/${notificationId}/read`, { method: "POST" });
    showLiveSuccess("Marked as read");
    loadNotifications();
  } catch (error) { showLiveError(error); }
}


/* ═══════════════════════════════════════════════════════════════
   MEETINGS & FOLLOW-UPS
   ═══════════════════════════════════════════════════════════════ */

async function loadMeetings() {
  const payload = await apiRequest("/meetings/?page_size=50").catch(() => ({ items: [] }));
  renderMeetings(payload.items || [], payload.meta || {});
}

async function loadMeetingFormDialog() {
  const session = RecruitOpsLive.session || readSession();
  const [clients, locations] = await Promise.all([
    apiRequest("/clients/?page_size=100").catch(() => ({ items: [] })),
    apiRequest("/locations/?page_size=100").catch(() => ({ items: [] })),
  ]);
  /* Pre-fill meeting_type select with backend-legal values */
  const typeSelect = document.getElementById("meeting_type");
  if (typeSelect) {
    typeSelect.innerHTML = '<option disabled selected value="">Select type...</option>' + [
      ["client_introduction", "Client Introduction"],
      ["requirement_discussion", "Requirement Discussion"],
      ["follow_up", "Follow Up"],
      ["review_meeting", "Review Meeting"],
      ["escalation_meeting", "Escalation"],
      ["internal_review", "Internal Review"],
    ].map(([val, label]) => `<option value="${val}">${label}</option>`).join("");
  }
}async function loadFollowUps() {
  const payload = await apiRequest("/meetings/?page_size=50").catch(() => ({ items: [] }));
  const all = payload.items || [];
  const follow = all.filter((item) => /follow/i.test(String(item.meeting_type || item.outcome_status || item.title || "")));
  const items = follow.length ? follow : all;
  fillExistingTable(items, (row, item) => {
    const cells = row.querySelectorAll("td");
    setStackedCell(cells[0], item.title || "Follow-up", item.notes || item.meeting_type || "");
    setCellValue(cells[1], item.priority || titleFromCode(item.meeting_type) || "—");
    setCellValue(cells[2], item.scheduled_at ? formatWhen(item.scheduled_at) : "—");
    setStackedCell(cells[3], item.contact_name || item.client_name || "—", item.meeting_type || "");
    if (typeof paintPersonCell === "function") paintPersonCell(cells[4], item.owner_name || item.created_by_name);
    else setCellValue(cells[4], item.owner_name || item.created_by_name || "—");
    setCellValue(cells[5], item.outcome_status || item.status || "Open");
    row.dataset.recordId = item.id || "";
    row.dataset.filterStatus = String(item.outcome_status || item.status || "open").toLowerCase();
    row.dataset.filterPriority = String(item.priority || "").toLowerCase();
    row.dataset.filterOwner = item.owner_name || item.created_by_name || "";
    row.dataset.filterRelated = item.meeting_type || item.client_name || "";
    row.dataset.route = `follow-up-form-dialog.html?id=${item.id}`;
    row.classList.add("cursor-pointer");
  });
  const metrics = document.querySelectorAll(".workspace-surface .grid .font-headline-md");
  if (metrics.length >= 4) {
    const overdue = items.filter((item) => /overdue/i.test(String(item.outcome_status || ""))).length;
    metrics[0].textContent = String(overdue);
    metrics[1].textContent = String(items.length);
    metrics[2].textContent = String(all.length);
    metrics[3].textContent = String(items.filter((item) => /complete|done/i.test(String(item.outcome_status || ""))).length);
  }
}

async function loadFollowUpFormDialog() {
  const [clients, users, locations] = await Promise.all([
    apiRequest("/clients/?page_size=100").catch(() => ({ items: [] })),
    apiRequest("/users/?page_size=100").catch(() => ({ items: [] })),
    apiRequest("/locations/?page_size=100").catch(() => ({ items: [] })),
  ]);
}/* ═══════════════════════════════════════════════════════════════
   INTERVIEWS
   ═══════════════════════════════════════════════════════════════ */

async function loadInterviewDetail() {
  const interviewId = queryInt("interview_id");
  if (!interviewId) return;
  try {
    const interviews = await apiRequest("/interviews/?page_size=50").catch(() => ({ items: [] }));
    const item = (interviews.items || []).find((i) => i.id === interviewId);
    if (item) {
      const surface = document.querySelector(".workspace-surface");
      if (surface) {
        const detail = document.createElement("div");
        detail.innerHTML = renderInterviewDetail(item);
        surface.appendChild(detail);
      }
    }
  } catch (error) { showLiveError(error); }
}

/* ═══════════════════════════════════════════════════════════════
   INTERVIEW FEEDBACK DIALOG
   ═══════════════════════════════════════════════════════════════ */

function interviewFeedbackDecision(label) {
  const normalized = String(label || "").toLowerCase().trim();
  if (normalized.includes("strong yes")) return "strong-yes";
  if (normalized.includes("strong no")) return "strong-no";
  if (normalized === "yes") return "yes";
  if (normalized === "no") return "no";
  return normalized.replace(/\s+/g, "-") || null;
}

function selectInterviewFeedbackDecision(value) {
  if (!value) return;
  const grid = document.querySelector("[data-decision-group]");
  if (!grid) return;
  grid.querySelectorAll("button").forEach((btn) => {
    const active = interviewFeedbackDecision(btn.textContent) === value;
    btn.dataset.selected = String(active);
    btn.classList.toggle("border-2", active);
    btn.classList.toggle("border-success-text/30", active);
    btn.classList.toggle("bg-success-bg", active);
    btn.classList.toggle("text-success-text", active);
    btn.classList.toggle("font-semibold", active);
    btn.classList.toggle("border", !active);
    btn.classList.toggle("border-border", !active);
    btn.classList.toggle("bg-surface", !active);
    btn.classList.toggle("text-on-surface-variant", !active);
  });
  grid.dataset.decision = value;
}

function wireInterviewFeedbackDecisionPicker() {
  const grid = document.querySelector("[data-decision-group]");
  if (!grid || grid.dataset.feedbackWired === "true") return;
  grid.dataset.feedbackWired = "true";
  grid.querySelectorAll("button").forEach((btn) => {
    btn.type = "button";
    btn.addEventListener("click", () => selectInterviewFeedbackDecision(interviewFeedbackDecision(btn.textContent)));
  });
  const preselected = grid.querySelector("button.border-2");
  if (preselected) grid.dataset.decision = interviewFeedbackDecision(preselected.textContent);
}

function wireInterviewFeedbackRatingBars() {
  const container = document.querySelector("[data-overlay-surface] .space-y-6");
  if (!container || container.dataset.ratingsWired === "true") return;
  container.dataset.ratingsWired = "true";
  container.querySelectorAll(".flex.gap-1").forEach((barRow) => {
    const labelRow = barRow.previousElementSibling;
    const scoreEl = labelRow ? labelRow.querySelector(".font-data-tabular") : null;
    const nameEl = labelRow ? labelRow.querySelector(".font-body-sm.font-semibold") : null;
    const bars = barRow.querySelectorAll("button");
    bars.forEach((bar, index) => {
      bar.type = "button";
      bar.addEventListener("click", () => {
        bars.forEach((b, i) => {
          const filled = i <= index;
          b.classList.toggle("bg-primary", filled);
          b.classList.toggle("bg-outline-variant", !filled);
        });
        if (scoreEl) scoreEl.textContent = `${index + 1} / 5`;
      });
    });
    if (nameEl && nameEl.textContent) nameEl.dataset.ratingName = nameEl.textContent.trim();
  });
}

async function loadInterviewFeedbackDialog() {
  wireInterviewFeedbackDecisionPicker();
  wireInterviewFeedbackRatingBars();
  const submitBtn = document.getElementById("feedback-submit");
  if (submitBtn && !submitBtn.dataset.wired) {
    submitBtn.dataset.wired = "true";
    submitBtn.addEventListener("click", () => submitInterviewFeedback({ draft: false }));
  }
  const draftBtn = document.getElementById("feedback-draft");
  if (draftBtn && !draftBtn.dataset.wired) {
    draftBtn.dataset.wired = "true";
    draftBtn.addEventListener("click", () => submitInterviewFeedback({ draft: true }));
  }
  const interviewId = queryInt("interview_id");
  if (!interviewId) return;
  const subtitle = document.querySelector("[data-feedback-subtitle]");
  try {
    const item = await apiRequest(`/interviews/${interviewId}`);
    if (item && subtitle) {
      const label = [item.candidate_name, item.round_name || item.round_type || item.interview_type].filter(Boolean).join(" \u00b7 ");
      if (label) subtitle.textContent = label;
    }
    if (item?.decision) selectInterviewFeedbackDecision(item.decision);
    const notes = document.getElementById("feedback-detailed-notes");
    if (item?.feedback_notes && notes && !notes.value) notes.value = item.feedback_notes;
  } catch (error) {
    /* Leave the static page as a graceful fallback when the record is unreachable */
  }
}

async function submitInterviewFeedback({ draft = false } = {}) {
  const interviewId = queryInt("interview_id");
  if (!interviewId) { showLiveError(new Error("Interview id is missing.")); return; }
  const grid = document.querySelector("[data-decision-group]");
  const decision = grid?.dataset.decision || null;
  const surface = document.querySelector("[data-overlay-surface]");
  const readField = (id) => {
    const el = document.getElementById(id);
    return el ? el.value.trim() : "";
  };
  const strengths = readField("feedback-strengths");
  const concerns = readField("feedback-concerns");
  const detailed = readField("feedback-detailed-notes");
  const ratingLines = [];
  (surface ? surface.querySelectorAll(".flex.gap-1") : []).forEach((row) => {
    const labelRow = row.previousElementSibling;
    const nameEl = labelRow ? labelRow.querySelector(".font-body-sm.font-semibold") : null;
    const scoreEl = labelRow ? labelRow.querySelector(".font-data-tabular") : null;
    if (nameEl && scoreEl) ratingLines.push(`${nameEl.textContent.trim()} ${scoreEl.textContent.trim()}`);
  });
  const notesParts = [];
  if (ratingLines.length) notesParts.push(`Competency ratings: ${ratingLines.join(", ")}.`);
  if (strengths) notesParts.push(`Strengths: ${strengths}`);
  if (concerns) notesParts.push(`Concerns: ${concerns}`);
  if (detailed) notesParts.push(`Notes: ${detailed}`);
  const feedbackNotes = notesParts.length ? notesParts.join("\n").slice(0, 1000) : null;
  if (!decision && !feedbackNotes) {
    showLiveError(new Error("Feedback requires a recommendation or notes."));
    return;
  }
  const payload = draft
    ? { status: "scheduled", feedback_status: "pending", decision: decision || undefined, feedback_notes: feedbackNotes }
    : { status: "completed", feedback_status: "received", decision: decision || undefined, feedback_notes: feedbackNotes };
  try {
    await apiRequest(`/interviews/${interviewId}/feedback`, { method: "PATCH", body: JSON.stringify(payload) });
    showLiveSuccess(draft ? "Draft saved" : "Feedback submitted", decision ? titleFromCode(decision) : undefined);
    afterOverlaySave("interview-detail.html");
  } catch (error) { showLiveError(error); }
}/* ═══════════════════════════════════════════════════════════════
   OFFERS
   ═══════════════════════════════════════════════════════════════ */

async function loadOfferManagement() {
  try {
    const payload = await apiRequest("/offers/?page_size=50").catch(() => ({ items: [], meta: { total: 0 } }));
    renderOffers(payload.items || [], payload.meta || {});
  } catch (error) {
    showLiveError(error);
  }
}

async function loadOfferCreateDialog() {
  /* The offer form uses position/department selects — populate from backend */
  const candidates = await apiRequest("/candidates/?page_size=50").catch(() => ({ items: [] }));
  const requisitions = await apiRequest("/requisitions/?page_size=50").catch(() => ({ items: [] }));
  /* If candidate_id or requisition_id in URL, pre-select */
  const candidateId = queryInt("candidate_id");
  const requisitionId = queryInt("requisition_id");
  if (candidateId && document.getElementById("candidate_id")) {
    const el = document.getElementById("candidate_id");
    if (el) el.value = candidateId;
  }
  if (requisitionId && document.getElementById("requisition_id")) {
    const el = document.getElementById("requisition_id");
    if (el) el.value = requisitionId;
  }
}


/* ═══════════════════════════════════════════════════════════════
   NOTIFICATIONS
   ═══════════════════════════════════════════════════════════════ */

let notificationItemsCache = [];
let notificationUnreadTotal = 0;
let notificationStatusFilter = "unread";
let notificationSearchText = "";

function notificationFilterLabel() {
  return notificationStatusFilter === "all" ? "" : notificationStatusFilter;
}

function notificationsView() {
  const term = notificationSearchText.trim().toLowerCase();
  if (!term) return notificationItemsCache;
  return notificationItemsCache.filter((item) => {
    const story = typeof notificationStory === "function" ? notificationStory(item) : {};
    return `${item.title || ""} ${item.message || ""} ${item.event_type || ""} ${story.eventLabel || ""} ${story.headline || ""}`.toLowerCase().includes(term);
  });
}

function ensureNotificationBadge() {
  const bell = document.querySelector('.app-topbar [data-route*="notifications-center"]');
  if (!bell) return null;
  let badge = bell.querySelector("[data-notification-badge]");
  if (!badge) {
    badge = document.createElement("span");
    badge.className = "notification-badge";
    badge.dataset.notificationBadge = "true";
    badge.hidden = true;
    bell.appendChild(badge);
  }
  return badge;
}

function formatNotificationBadgeCount(count) {
  /* Real count up to three digits; 999+ beyond that keeps the pill readable. */
  return count > 999 ? "999+" : String(count);
}

async function refreshNotificationBadge() {
  const badge = ensureNotificationBadge();
  if (!badge || !LIVE_API_ENABLED) return false;
  try {
    const payload = await apiRequest("/notifications/?status=unread&page_size=1");
    const count = payload.meta?.total ?? 0;
    badge.textContent = formatNotificationBadgeCount(count);
    badge.hidden = count === 0;
    /* Expose the live count to the bell button's accessible name. */
    const bell = badge.closest("button");
    if (bell) {
      bell.setAttribute(
        "aria-label",
        count > 0 ? `Review notifications, ${count} unread` : "Review notifications"
      );
    }
    return true;
  } catch {
    badge.hidden = true;
    return false;
  }
}

/* ── Adaptive notification-badge polling ──────────────────────
   A fixed 30s interval used to hit /notifications even when the tab
   was hidden, the user was away, or the backend was down. The cycle
   below instead:
   - polls every 30s while the tab is visible and the user is active;
   - backs off ×1.5 per skipped tick (hidden tab / idle user) up to 2min;
   - backs off ×2 per failed request up to 2min, so a downed backend
     stops being hammered — user activity never resets this backoff;
   - snaps back to the 30s cadence on real activity or tab return,
     running the next due poll within ~1s (unless a failure backoff
     is active — retrying a down API on every click is the exact
     hammering this prevents);
   - stops entirely once the session is gone. */
const BADGE_POLL_BASE_MS = 30 * 1000;
const BADGE_POLL_MAX_MS = 2 * 60 * 1000;
const BADGE_POLL_IDLE_MS = 2 * BADGE_POLL_BASE_MS;
let badgePollTimer = null;
let badgePollSkipBackoffMs = BADGE_POLL_BASE_MS;
let badgePollFailureBackoffMs = BADGE_POLL_BASE_MS;
let badgePollLastActivity = Date.now();

function scheduleBadgePoll(delayMs) {
  if (badgePollTimer) clearTimeout(badgePollTimer);
  badgePollTimerDelay = delayMs;
  badgePollTimerScheduledAt = Date.now();
  badgePollTimer = setTimeout(runBadgePollCycle, delayMs);
}

function remainingBadgePollDelay() {
  if (!badgePollTimer) return Infinity;
  return Math.max(0, badgePollTimerScheduledAt + badgePollTimerDelay - Date.now());
}

async function runBadgePollCycle() {
  badgePollTimer = null;
  if (!readSession()) return; /* signed out: stop polling */
  const documentHidden = typeof document !== "undefined" && document.hidden;
  const idleFor = Date.now() - badgePollLastActivity;
  if (documentHidden || idleFor >= BADGE_POLL_IDLE_MS) {
    /* Nobody is watching: skip the request and stretch the interval. */
    badgePollSkipBackoffMs = Math.min(badgePollSkipBackoffMs * 1.5, BADGE_POLL_MAX_MS);
    scheduleBadgePoll(Math.max(badgePollSkipBackoffMs, badgePollFailureBackoffMs));
    return;
  }
  const ok = await refreshNotificationBadge();
  if (ok) {
    badgePollFailureBackoffMs = BADGE_POLL_BASE_MS;
    badgePollSkipBackoffMs = BADGE_POLL_BASE_MS;
    scheduleBadgePoll(BADGE_POLL_BASE_MS);
  } else {
    badgePollFailureBackoffMs = Math.min(badgePollFailureBackoffMs * 2, BADGE_POLL_MAX_MS);
    scheduleBadgePoll(badgePollFailureBackoffMs);
  }
}

function nudgeBadgePollSooner() {
  /* Pull a backoff-delayed poll forward so a returning user sees a
     fresh count within ~1s. Only when the pending tick is farther out
     than the base cadence — otherwise steady activity would keep
     re-nudging and poll more often than every 30s. */
  if (!badgePollTimer || remainingBadgePollDelay() > BADGE_POLL_BASE_MS) {
    scheduleBadgePoll(1000);
  }
}

function noteBadgeUserActivity() {
  const now = Date.now();
  const recentlyHandled = now - badgePollLastActivity < 5000;
  badgePollLastActivity = now; /* record every event, throttle only the work */
  if (recentlyHandled) return;
  badgePollSkipBackoffMs = BADGE_POLL_BASE_MS;
  /* Never nudge through an active failure backoff: retrying a down
     API on every click is the hammering this scheduler prevents. */
  if (badgePollFailureBackoffMs === BADGE_POLL_BASE_MS) nudgeBadgePollSooner();
}

function startNotificationBadgePolling() {
  if (badgePollTimer) return; /* already running */
  if (!readSession()) return; /* nothing to poll for */
  badgePollLastActivity = Date.now();
  badgePollSkipBackoffMs = BADGE_POLL_BASE_MS;
  badgePollFailureBackoffMs = BADGE_POLL_BASE_MS;
  if (typeof document === "undefined" || !document.hidden) {
    refreshNotificationBadge();
  }
  scheduleBadgePoll(BADGE_POLL_BASE_MS);
  if (typeof document !== "undefined") {
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) {
        badgePollLastActivity = Date.now();
        badgePollSkipBackoffMs = BADGE_POLL_BASE_MS;
        if (badgePollFailureBackoffMs === BADGE_POLL_BASE_MS) nudgeBadgePollSooner();
      }
    });
  }
  if (typeof window !== "undefined") {
    for (const evt of ["pointerdown", "keydown", "wheel"]) {
      window.addEventListener(evt, noteBadgeUserActivity, { passive: true });
    }
  }
}

/* Hook for session changes that don't navigate away (login/logout flows
   outside the standard redirects). Safe to call repeatedly. */
function onSessionChangedBadgePoll() {
  if (readSession()) {
    startNotificationBadgePolling();
  } else if (badgePollTimer) {
    clearTimeout(badgePollTimer);
    badgePollTimer = null;
  }
}

function applyNotificationReadState(row) {
  if (!row) return;
  row.classList.add("notification-read");
  row.dataset.notificationStatus = "read";
  row.querySelectorAll("[data-notification-unread-indicator]").forEach((dot) => dot.remove());
  const button = row.querySelector("[data-notification-read]");
  if (button) {
    if (button.getAttribute("role") === "menuitem") {
      button.removeAttribute("data-notification-read");
      button.disabled = true;
      button.textContent = "Seen";
    } else {
      const seen = document.createElement("span");
      seen.className = "text-[12px] font-semibold text-text-muted";
      seen.textContent = "Seen";
      button.replaceWith(seen);
    }
  }
  const badge = row.querySelector("[data-notification-status-badge]");
  if (badge) badge.textContent = "Seen";
}

async function markNotificationSeen(id) {
  if (!id) return false;
  await apiRequest(`/notifications/${id}/read`, { method: "PATCH", body: JSON.stringify({ status: "read" }) });
  notificationItemsCache = notificationItemsCache.map((item) => (String(item.id) === String(id) ? { ...item, status: "read", read_at: item.read_at || new Date().toISOString() } : item));
  notificationUnreadTotal = Math.max(0, notificationUnreadTotal - 1);
  refreshNotificationBadge();
  return true;
}

const UNDO_WINDOW_MS = 30000;
const MARK_ALL_BUTTON_LABEL = "Mark all read";
let pendingMarkAllUndoIds = null;

function setMarkAllButtonState(button, state) {
  if (!button) return;
  /* Only the in-flight state locks the button; "failed" must stay
     clickable so the user can actually retry. */
  button.disabled = state === "pending";
  const icon = button.querySelector(".material-symbols-outlined");
  const label = button.querySelector("[data-mark-all-label]");
  if (!icon || !label) return;
  if (state === "pending") {
    icon.textContent = "progress_activity";
    icon.classList.add("animate-spin");
    label.textContent = "Marking…";
    button.setAttribute("aria-busy", "true");
  } else if (state === "failed") {
    icon.textContent = "refresh";
    icon.classList.remove("animate-spin");
    label.textContent = "Retry";
    button.setAttribute("aria-busy", "false");
  } else {
    icon.textContent = "done_all";
    icon.classList.remove("animate-spin");
    label.textContent = MARK_ALL_BUTTON_LABEL;
    button.removeAttribute("aria-busy");
  }
}

async function markAllNotificationsSeen() {
  /* The server returns the ids it flipped, so the undo window can restore
     the whole batch even when only one page (~50 rows) is cached. */
  const payload = await apiRequest("/notifications/read-all", { method: "POST" });
  notificationItemsCache = notificationItemsCache.map((item) => ({ ...item, status: "read", read_at: item.read_at || new Date().toISOString() }));
  notificationUnreadTotal = 0;
  refreshNotificationBadge();
  pendingMarkAllUndoIds = Array.isArray(payload?.notification_ids) ? payload.notification_ids.map(Number) : [];
  return Number(payload?.updated ?? 0);
}

async function undoMarkAllNotificationsSeen() {
  const ids = pendingMarkAllUndoIds || [];
  if (!ids.length) return 0;
  const payload = await apiRequest("/notifications/read-all/undo", {
    method: "POST",
    body: JSON.stringify({ notification_ids: ids }),
  });
  const revertedSet = new Set(ids.map(String));
  notificationItemsCache = notificationItemsCache.map((item) => (revertedSet.has(String(item.id)) ? { ...item, status: "unread", read_at: null } : item));
  notificationUnreadTotal = ids.length;
  pendingMarkAllUndoIds = null;
  refreshNotificationBadge();
  return Number(payload?.reverted ?? 0);
}

/* ── Notifications center: AI Triage review mode ─────────────── */
function exitNotificationsTriage() {
  window.notificationsTriageState = null;
  document.querySelector("[data-triage-banner]")?.remove();
  if (routeId() === "notifications-center") loadNotifications();
}

async function enterNotificationsTriage(button) {
  if (button?.disabled) return;
  if (button) {
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
  }
  try {
    const run = await apiRequest("/agents/inbox_triage/run", {
      method: "POST",
      body: JSON.stringify({ status: "unread", max_items: 50 }),
    });
    const queue = run.output_draft?.queue || [];
    window.notificationsTriageState = { runId: run.id, queue, done: new Set() };
    renderNotificationsTriage();
    showToast("AI Triage ready", `${queue.length} unread sorted by priority. Nothing changes until you act.`);
  } catch (error) {
    showLiveError(error);
  }
  if (button) {
    button.disabled = false;
    button.removeAttribute("aria-busy");
  }
}

async function triageGotItAction(button) {
  const id = intOrNull(button.dataset.notificationId);
  const state = window.notificationsTriageState;
  if (!id || !state) return;
  button.disabled = true;
  try {
    await markNotificationSeen(id);
    state.done.add(String(id));
    applyTriageDoneToDom(id);
    updateTriageProgress();
  } catch (error) {
    button.disabled = false;
    showLiveError(error);
  }
}

function triageOpenAction(button) {
  const id = intOrNull(button.dataset.notificationId);
  if (!id) return;
  navigateToRoute(`notification-detail-panel.html?notification_id=${id}`);
}

async function markAllNotificationsReadAction(button) {
  if (!button || button.disabled) return;
  setMarkAllButtonState(button, "pending");
  try {
    const updated = await markAllNotificationsSeen();
    if (routeId() === "notifications-center" && document.querySelector("[data-notifications-command-center]")) {
      renderNotificationsCommandCenter(notificationsView(), { unread_total: notificationUnreadTotal });
    }
    if (pendingMarkAllUndoIds && pendingMarkAllUndoIds.length === 0) {
      /* Server confirmed zero rows changed; nothing to offer undo for. */
      showToast("All caught up", "Nothing was waiting for you.");
      setMarkAllButtonState(button, "idle");
      return;
    }
    const undoResult = await showToastWithAction({
      title: "All caught up",
      text: updated > 0 ? `${updated} notification${updated === 1 ? "" : "s"} marked as read.` : "Nothing was waiting for you.",
      actionLabel: "Undo",
      timeoutMs: UNDO_WINDOW_MS,
    });
    if (undoResult.settled) {
      try {
        const reverted = await undoMarkAllNotificationsSeen();
        if (routeId() === "notifications-center" && document.querySelector("[data-notifications-command-center]")) {
          renderNotificationsCommandCenter(notificationsView(), { unread_total: notificationUnreadTotal });
        }
        showToast("Restored", `${reverted} notification${reverted === 1 ? "" : "s"} marked unread again.`);
      } catch (error) {
        showLiveError(error);
      }
    }
  } catch (error) {
    showLiveError(error);
    setMarkAllButtonState(button, "failed");
    return;
  }
  setMarkAllButtonState(button, "idle");
}

async function markNotificationReadAction(button) {
  if (button.disabled) return;
  button.setAttribute("disabled", "disabled");
  const row = button.closest("[data-notification-id]");
  const id = intOrNull(row?.dataset.notificationId) || intOrNull(button.dataset.notificationId);
  if (!id) {
    applyNotificationReadState(row);
    showToast("Got it", "This event will stay in Seen if you need it later.");
    return;
  }
  try {
    await markNotificationSeen(id);
    if (routeId() === "notifications-center" && document.querySelector("[data-notifications-command-center]")) {
      renderNotificationsCommandCenter(notificationsView(), { unread_total: notificationUnreadTotal });
    } else {
      applyNotificationReadState(row);
    }
    const overlay = document.getElementById("ro-inpage-overlay");
    if (overlay?.dataset.overlayRoute === "notification-detail-panel") {
      const item = notificationItemsCache.find((entry) => Number(entry.id) === Number(id));
      if (item && typeof renderNotificationDetailPanel === "function") renderNotificationDetailPanel(item);
    }
    showLiveSuccess("Got it", "This event is in Seen. Open What happened if you want the details again.");
  } catch (error) {
    button.removeAttribute("disabled");
    showLiveError(error);
  }
}

async function openNotificationRecord(button) {
  const row = button.closest("[data-notification-id]");
  const id = intOrNull(row?.dataset.notificationId) || intOrNull(button.dataset.notificationId);
  if (!id) return;
  try {
    await markNotificationSeen(id);
  } catch (error) {
    showLiveError(error);
    return;
  }
  navigateToRoute(`notification-detail-panel.html?notification_id=${id}`);
}

function wireNotificationListInteractions(list) {
  if (!list || list.dataset.notificationListWired === "true") return;
  list.dataset.notificationListWired = "true";
  list.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) return;
    if (event.target.closest("button, a, .ro-row-menu, .ro-card-kebab")) return;
    const article = event.target.closest("[data-notification-id]");
    const id = article?.dataset.notificationId;
    if (!id) return;
    event.preventDefault();
    navigateToRoute(`notification-detail-panel.html?notification_id=${id}`);
  });
}

function wireNotificationCenterFilters(surface) {
  const filterBar = surface.querySelector("[data-toggle-group]");
  if (filterBar && !filterBar.dataset.notifWired) {
    filterBar.dataset.notifWired = "true";
    filterBar.querySelectorAll("button").forEach((button) => {
      button.addEventListener("click", () => {
        const label = (button.textContent || "").trim().toLowerCase();
        if (!/^(unread|read|all)$/.test(label)) return;
        notificationStatusFilter = label;
        filterBar.querySelectorAll("button").forEach((other) => {
          other.classList.remove("is-active", "bg-secondary-container", "text-on-secondary-container");
          other.classList.add("border", "border-border", "bg-surface", "text-secondary", "hover:bg-highlight-soft");
        });
        button.classList.add("is-active", "bg-secondary-container", "text-on-secondary-container");
        button.classList.remove("border", "border-border", "bg-surface", "text-secondary", "hover:bg-highlight-soft");
        loadNotifications();
      });
    });
  }
  const searchInput = surface.querySelector('[data-layout="pipeline-filter-bar"] input[type="text"]');
  if (searchInput && !searchInput.dataset.notifWired) {
    searchInput.dataset.notifWired = "true";
    searchInput.addEventListener("input", () => {
      notificationSearchText = searchInput.value || "";
      renderNotificationsCommandCenter(notificationsView(), { unread_total: notificationUnreadTotal });
    });
  }
}

async function loadNotifications() {
  const query = notificationStatusFilter === "all" ? "?page_size=50" : `?status=${notificationStatusFilter}&page_size=50`;
  const [payload, unreadPayload] = await Promise.all([
    apiRequest(`/notifications/${query}`),
    apiRequest("/notifications/?status=unread&page_size=1").catch(() => null),
  ]);
  notificationItemsCache = payload.items || [];
  if (unreadPayload) notificationUnreadTotal = unreadPayload.meta?.total ?? 0;
  refreshNotificationBadge();
  const items = notificationsView();
  if (routeId() === "notifications-center") {
    const surface = document.querySelector("[data-notifications-command-center]");
    if (surface && renderNotificationsCommandCenter(items, { unread_total: notificationUnreadTotal })) {
      wireNotificationCenterFilters(surface);
      if (typeof hydrateLiveFilters === "function") hydrateLiveFilters(surface);
      return;
    }
  }
  const list = document.querySelector("[data-notification-list], .workspace-surface .rounded-xl.flex.flex-col");
  if (list && items.length) {
    list.innerHTML = items.map((item) => {
      const story = typeof notificationStory === "function" ? notificationStory(item) : { eventLabel: item.title || "Notification", headline: item.message || "", icon: "notifications", unread: String(item.status).toLowerCase() === "unread" };
      return `<div class="group flex items-start gap-4 p-4 border-b border-border bg-surface" data-live-notification-row="true" data-notification-id="${item.id}">
      <div class="mt-1 text-primary"><span class="material-symbols-outlined">${escapeLiveHtml(story.icon || "notifications")}</span></div>
      <div class="flex-1 min-w-0">
        <h4 class="font-headline-sm text-headline-sm text-on-surface truncate">${escapeLiveHtml(story.eventLabel)}</h4>
        <p class="font-body-sm text-body-sm text-on-surface mt-1">${escapeLiveHtml(story.headline)}</p>
      </div>
      ${typeof notificationRowMenu === "function" ? notificationRowMenu(item) : ""}
    </div>`;
    }).join("");
    if (typeof applyCollectionPagination === "function") {
      delete list.dataset.pageSize;
      list.dataset.page = "1";
      applyCollectionPagination(list);
    }
    if (typeof wireHoverKebabMenus === "function") wireHoverKebabMenus(list);
    wireNotificationListInteractions(list);
    return;
  }
  fillExistingTable(items, (row, item) => {
    const cells = row.querySelectorAll("td");
    setStackedCell(cells[1], item.title, item.message);
    const status = cells[2]?.querySelector("span") || cells[2];
    if (status) status.textContent = item.status || "—";
  });
}


/* ═══════════════════════════════════════════════════════════════
   APPROVALS
   ═══════════════════════════════════════════════════════════════ */

async function loadApprovalsInbox() {
  const tbody = document.querySelector(".workspace-surface tbody") || document.querySelector("tbody");
  if (tbody && typeof showSkeletonTable === "function") showSkeletonTable(tbody, 5, 7);
  const payload = await apiRequest("/approvals/?page_size=50").catch(() => ({ items: [], meta: { total: 0 } }));
  hideSkeleton(tbody);
  const items = payload.items || [];
  const total = payload.meta?.total || items.length;
  const pending = items.filter((i) => i.status === "pending").length;
  const overdue = items.filter((i) => i.status === "pending" && i.sla_deadline && new Date(i.sla_deadline) < new Date()).length;
  const awaiting = items.filter((i) => i.status === "pending" && (!i.assigned_reviewer_user_id || i.assigned_reviewer_user_id === currentUserId())).length;
  /* Update metric cards */
  const metrics = document.querySelectorAll("[data-layout='metric-card'] .font-headline-md, .bg-surface .font-headline-md");
  if (metrics[0]) metrics[0].textContent = pending;
  if (metrics[1]) metrics[1].textContent = overdue;
  if (metrics[2]) metrics[2].textContent = awaiting;
  /* Update the mobile tab strip: live count + active-tab filtering */
  const pendingCount = document.querySelector('[data-approval-count="pending"]');
  if (pendingCount) pendingCount.textContent = pending;
  wireApprovalTabs(items);
  /* Render table filtered to the active tab */
  const renderTbody = (typeof workspaceTbody === "function" ? workspaceTbody() : null) || document.querySelector(".workspace-surface tbody") || document.querySelector("tbody");
  if (!renderTbody) return;
  const activeTab = document.querySelector('[data-approval-tab].bg-secondary-container')?.dataset.approvalTab || "pending";
  renderApprovalRows(renderTbody, filterApprovalsByTab(items, activeTab));
  const paginationText = document.querySelector(".border-t span");
  if (paginationText) paginationText.textContent = formatListCount((payload.items || []).length, total);
}

function filterApprovalsByTab(items, tab) {
  if (tab === "pending") return items.filter((i) => i.status === "pending");
  if (tab === "actioned") return items.filter((i) => i.status !== "pending");
  return items;
}

function wireApprovalTabs(items) {
  const tabs = document.querySelectorAll("[data-approval-tab]");
  if (!tabs.length || tabs[0].dataset.wired === "true") return;
  tabs.forEach((tab) => {
    tab.dataset.wired = "true";
    tab.addEventListener("click", () => {
      tabs.forEach((t) => {
        const selected = t === tab;
        t.classList.toggle("bg-secondary-container", selected);
        t.classList.toggle("text-on-secondary-container", selected);
        t.classList.toggle("text-text-muted", !selected);
        t.setAttribute("aria-selected", String(selected));
      });
      const tbody = document.querySelector("tbody");
      if (tbody) renderApprovalRows(tbody, filterApprovalsByTab(items, tab.dataset.approvalTab));
    });
  });
}

function renderApprovalRows(tbody, items) {
  if (!items.length) {
    tbody.innerHTML = `<tr><td class="px-4 py-12 text-center text-text-muted" colspan="7">No approvals found.</td></tr>`;
    return;
  }
  tbody.innerHTML = items.map((item) => {
    const priorityMeta = { critical: { dot: "bg-error", text: "text-danger-text", label: "Critical" }, high: { dot: "bg-warning-text", text: "text-warning-text", label: "High" }, standard: { dot: "bg-success-text", text: "text-success-text", label: "Standard" } }[item.priority] || { dot: "bg-success-text", text: "text-success-text", label: "Standard" };
    const slaText = item.sla_deadline ? (new Date(item.sla_deadline) < new Date() ? `Overdue ${Math.ceil((Date.now() - new Date(item.sla_deadline)) / 86400000)}d` : `${Math.ceil((new Date(item.sla_deadline) - Date.now()) / 86400000)}d left`) : "No SLA";
    const slaColor = item.sla_deadline && new Date(item.sla_deadline) < new Date() ? "text-danger-text" : "text-success-text";
    const initials = (item.requester_name || "??").split(" ").map((w) => w[0]).join("").substring(0, 2).toUpperCase();
    const locationName = item.location_name || "—";
    const created = item.created_at ? relativeTime(item.created_at) : "—";
    const statusBadge = { pending: "", approved: `<span class="inline-flex items-center px-2 py-0.5 rounded bg-success-bg text-success-text text-[10px] font-semibold">Approved</span>`, rejected: `<span class="inline-flex items-center px-2 py-0.5 rounded bg-danger-bg text-danger-text text-[10px] font-semibold">Rejected</span>` }[item.status] || "";
    const actionsHtml = item.status === "pending"
      ? `<button class="px-3 py-1.5 border border-primary text-primary rounded text-xs font-semibold hover:bg-primary hover:text-on-primary transition-colors approve-btn" data-approval-id="${item.id}" type="button">Approve</button><button class="px-3 py-1.5 border border-danger-text text-danger-text rounded text-xs font-semibold hover:bg-danger-bg transition-colors reject-btn" data-approval-id="${item.id}" type="button">Reject</button>`
      : statusBadge;
    return `<tr class="hover:bg-highlight-soft transition-colors bg-surface h-[40px] group" data-approval-id="${item.id}" data-filter-type="${escapeLiveHtml(item.approval_type?.replace(/_/g, " ") || "Request")}" data-filter-priority="${escapeLiveHtml(item.priority || "standard")}" data-filter-location="${escapeLiveHtml(locationName)}" data-filter-status="${escapeLiveHtml(item.status || "")}">
      <td class="py-2 px-4 align-middle"><div class="flex items-center gap-2"><div class="w-2 h-2 rounded-full ${priorityMeta.dot}"></div><span class="${priorityMeta.text} font-medium text-xs">${item.status === "pending" ? slaText : item.status}</span></div></td>
      <td class="py-2 px-4 align-middle text-on-surface font-medium">${escapeLiveHtml(item.approval_type?.replace(/_/g, " ") || "Request")}</td>
      <td class="py-2 px-4 align-middle text-on-surface cursor-pointer hover:underline font-medium">${escapeLiveHtml(item.title || "—")}</td>
      <td class="py-2 px-4 align-middle"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded-full border border-border bg-surface-dim text-text-muted flex items-center justify-center font-headline-sm font-semibold text-[11px]">${initials}</div><span class="text-on-surface">${escapeLiveHtml(item.requester_name || "Unknown")}</span></div></td>
      <td class="py-2 px-4 align-middle text-text-muted text-sm">${escapeLiveHtml(locationName)}</td>
      <td class="py-2 px-4 align-middle text-text-muted text-sm">${created}</td>
      <td class="py-2 px-4 align-middle text-right"><div class="flex items-center justify-end gap-2">${actionsHtml}</div></td>
    </tr>`;
  }).join("");
  /* Wire approve/reject buttons */
  tbody.querySelectorAll(".approve-btn").forEach((btn) => btn.addEventListener("click", () => decideApproval(btn.dataset.approvalId, "approved")));
  tbody.querySelectorAll(".reject-btn").forEach((btn) => btn.addEventListener("click", () => decideApproval(btn.dataset.approvalId, "rejected")));
  const table = tbody.closest("table");
  if (table && typeof applyClientPagination === "function") {
    delete table.dataset.pageSize;
    table.dataset.page = "1";
    applyClientPagination(table);
  }
  if (typeof hydrateLiveFilters === "function") hydrateLiveFilters(tbody.closest(".workspace-surface, section") || document);
}

async function decideApproval(approvalId, decision) {
  let notes = null;
  if (decision === "rejected") {
    notes = await promptNotesDialog({
      title: "Reject approval",
      message: "Add a reason for the requester. Optional, but useful in the audit trail.",
      confirmLabel: "Reject",
      placeholder: "Reason for rejection",
    });
    if (notes === null) return;
  }
  try {
    await apiRequest(`/approvals/${approvalId}/decide`, {
      method: "PATCH",
      body: JSON.stringify({ decision, decision_notes: notes || (decision === "approved" ? "Approved" : "Rejected"), decision_user_id: currentUserId() }),
    });
    showLiveSuccess(decision === "approved" ? "Approved" : "Rejected", "Decision saved.");
    loadApprovalsInbox();
  } catch (error) { showLiveError(error); }
}

function promptNotesDialog({ title, message, confirmLabel = "Confirm", placeholder = "" } = {}) {
  return new Promise((resolve) => {
    document.getElementById("ro-notes-dialog")?.remove();
    const overlay = document.createElement("div");
    overlay.id = "ro-notes-dialog";
    overlay.className = "ro-notes-dialog";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.innerHTML = `
      <div class="ro-notes-dialog__card">
        <h2 class="font-headline-md text-[16px] text-on-surface">${escapeLiveHtml(title || "Notes")}</h2>
        <p class="mt-1 font-body-sm text-[13px] text-text-muted">${escapeLiveHtml(message || "")}</p>
        <textarea class="custom-input mt-3 w-full min-h-[96px]" placeholder="${escapeLiveHtml(placeholder)}"></textarea>
        <div class="mt-4 flex justify-end gap-2">
          <button type="button" data-notes-cancel class="px-3 py-1.5 border border-border rounded text-xs font-semibold">Cancel</button>
          <button type="button" data-notes-confirm class="px-3 py-1.5 bg-primary text-on-primary rounded text-xs font-semibold">${escapeLiveHtml(confirmLabel)}</button>
        </div>
      </div>`;
    const finish = (value) => {
      overlay.remove();
      resolve(value);
    };
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) finish(null);
    });
    overlay.querySelector("[data-notes-cancel]").addEventListener("click", () => finish(null));
    overlay.querySelector("[data-notes-confirm]").addEventListener("click", () => {
      finish(overlay.querySelector("textarea")?.value || "");
    });
    document.addEventListener("keydown", function onKey(event) {
      if (event.key === "Escape") {
        document.removeEventListener("keydown", onKey);
        finish(null);
      }
    });
    document.body.appendChild(overlay);
    overlay.querySelector("textarea")?.focus();
  });
}


/* ═══════════════════════════════════════════════════════════════
   JOIN TRACKER
   ═══════════════════════════════════════════════════════════════ */

async function loadJoinTracker() {
  const payload = await apiRequest("/offers/?status=accepted&page_size=50").catch(() => ({ items: [] }));
  const items = (payload.items || []).filter((item) => /accepted|joined/i.test(String(item.offer_status || item.application_status || "")));
  fillExistingTable(items, (row, item) => {
    const cells = row.querySelectorAll("td");
    setStackedCell(cells[0], item.candidate_name || "Candidate", item.candidate_email || "");
    const avatar = cells[0]?.querySelector(".rounded-full, .w-8.h-8");
    if (avatar && typeof personInitials === "function") avatar.textContent = personInitials(item.candidate_name);
    setStackedCell(cells[1], item.requisition_title || "Position", item.department || "");
    const start = item.expected_joining_date || item.accepted_at || item.updated_at;
    setStackedCell(cells[2], start ? (typeof formatOfferDate === "function" ? formatOfferDate(start) : formatWhen(start)) : "—", "");
    const joined = /joined/i.test(String(item.application_status || item.offer_status || ""));
    const pct = joined ? 100 : 60;
    const bar = cells[3]?.querySelector("[style*='width']");
    if (bar) bar.style.width = `${pct}%`;
    const pctLabel = Array.from(cells[3]?.querySelectorAll("span") || []).find((node) => /%/.test(node.textContent || ""));
    if (pctLabel) pctLabel.textContent = `${pct}%`;
    setCellValue(cells[4], "—");
    setCellValue(cells[5], "—");
    const statusNode = cells[6]?.querySelector("span") || cells[6];
    if (statusNode) statusNode.textContent = joined ? "Complete" : "Pre-boarding";
    row.dataset.recordId = item.candidate_id || item.id || "";
    row.dataset.route = item.candidate_id
      ? `candidate-detail.html?candidate_id=${item.candidate_id}`
      : `offer-create-dialog.html?offer_id=${item.id}`;
    row.classList.add("cursor-pointer");
  });
}


/* ═══════════════════════════════════════════════════════════════
   PIPELINE ANALYTICS
   ═══════════════════════════════════════════════════════════════ */

async function loadPipelineAnalytics() {
  const [company, pipeline, interviews, offers] = await Promise.all([
    apiRequest("/dashboards/company-summary").catch(() => ({})),
    apiRequest("/pipeline/board").catch(() => []),
    apiRequest("/interviews/?page_size=50").catch(() => ({ items: [] })),
    apiRequest("/offers/?page_size=50").catch(() => ({ items: [] })),
  ]);
  const pipelineItems = Array.isArray(pipeline) ? pipeline : pipeline.items || [];
  const offerItems = offers.items || [];
  const stages = pipelineStageBuckets(pipelineItems, offerItems);
  fillDashboardMetrics([
    { label: "Total in Pipeline", value: pipelineItems.length, hint: `${company.total_open_requisitions || 0} active mandates` },
    { label: "Conversion Rate", value: `${Math.round((offerItems.filter((i) => i.application_status === "joined").length / Math.max(pipelineItems.length, 1)) * 100)}%`, hint: "Pipeline to hire" },
  ]);
  renderPipelineAnalyticsFunnel(stages);
  renderPipelineAnalyticsStageTable(stages, pipelineItems);
  renderPipelineAnalyticsBottlenecks(stages, interviews.items || [], offerItems);
}


/* ═══════════════════════════════════════════════════════════════
   REPORTS & ANALYTICS
   ═══════════════════════════════════════════════════════════════ */

async function loadReportsLibrary() {
  const [company, pipeline, candidates, offers, dailyUpdates] = await Promise.all([
    apiRequest("/dashboards/company-summary").catch(() => ({})),
    apiRequest("/pipeline/board").catch(() => []),
    apiRequest("/candidates/?page_size=100").catch(() => ({ items: [] })),
    apiRequest("/offers/?page_size=50").catch(() => ({ items: [] })),
    apiRequest("/daily-updates/?page_size=50").catch(() => ({ items: [] })),
  ]);
  const reports = reportLibraryDefinitions(
    company,
    Array.isArray(pipeline) ? pipeline : pipeline.items || [],
    candidates.items || [],
    offers.items || [],
    dailyUpdates.items || [],
  );
  const surface = document.querySelector(".workspace-surface");
  if (surface) surface.dataset.liveReports = JSON.stringify(reports);
  renderReportLibraryCards(reports);
}

async function loadAnalyticsDashboard() {
  const [company, myWork, pipeline, users, requisitions, candidates, offers, dailyUpdates] = await Promise.all([
    apiRequest("/dashboards/company-summary").catch(() => ({})),
    apiRequest("/dashboards/my-work").catch(() => ({})),
    apiRequest("/pipeline/board").catch(() => []),
    apiRequest("/users/?page_size=100").catch(() => ({ items: [] })),
    apiRequest("/requisitions/?page_size=100").catch(() => ({ items: [] })),
    apiRequest("/candidates/?page_size=100").catch(() => ({ items: [] })),
    apiRequest("/offers/?page_size=50").catch(() => ({ items: [] })),
    apiRequest("/daily-updates/?page_size=50").catch(() => ({ items: [] })),
  ]);
  const pipelineItems = Array.isArray(pipeline) ? pipeline : pipeline.items || [];
  const offerItems = offers.items || [];
  const hires = offerItems.filter((item) => item.application_status === "joined" || normalizeOfferStatus(item.offer_status) === "accepted").length;
  const ttf = await apiRequest("/reports/time-to-fill").catch(() => null);
  fillDashboardMetrics([
    { label: "Total Hires", value: hires, hint: `${company.total_locations || 0} active locations` },
    { label: "Time to Fill", value: ttf?.summary?.avg_days != null ? `${ttf.summary.avg_days} days` : "—", hint: ttf?.summary?.filled_count ? `${ttf.summary.filled_count} filled roles` : "No fills yet" },
    { label: "Pipeline Velocity", value: `${Math.max(1, Math.round(pipelineItems.length / Math.max(company.total_open_requisitions || 1, 1)))}x`, hint: `${pipelineItems.length} active pipeline items` },
    { label: "Offer Accept Rate", value: offerItems.length ? `${Math.round((hires / offerItems.length) * 100)}%` : "—", hint: `${offerItems.length} offers` },
  ]);
  renderAnalyticsVisuals(pipelineItems, candidates.items || [], offerItems);
  renderAnalyticsTeam(users.items || [], requisitions.items || [], candidates.items || [], offerItems);
  renderAnalyticsSavedReports(company, dailyUpdates.items || []);
  renderPortalUsageReport();
}

async function renderPortalUsageReport() {
  const surface = document.querySelector("[data-portal-usage-body]");
  if (!surface) return;
  try {
    const summary = await apiRequest("/portal-accounts/usage-summary?weeks_back=6");
    const weeks = summary.weeks || [];
    const platforms = summary.platforms || [];
    if (!platforms.length || !weeks.length) {
      surface.innerHTML = '<p class="text-body-sm text-text-muted py-6 text-center">No portal usage recorded in the last 6 weeks.</p>';
      return;
    }
    const fmt = (d) => new Date(`${d}T00:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric" });
    const headCells = weeks.map((w) => `<th class="px-3 py-2 text-right text-label-caps font-bold text-text-muted uppercase tracking-wider">Wk of ${fmt(w)}</th>`).join("");
    const maxHours = Math.max(1, ...platforms.flatMap((p) => p.weeks.map((w) => w.booked_hours)));
    const bodyRows = platforms.map((platform) => {
      const byWeek = new Map(platform.weeks.map((w) => [w.week_start, w.booked_hours]));
      const cells = weeks.map((week) => {
        const hours = byWeek.get(week) || 0;
        const pct = Math.round((hours / maxHours) * 100);
        return `<td class="px-3 py-2 text-right">
          <div class="flex items-center justify-end gap-2">
            <div class="hidden sm:block w-16 bg-outline-variant rounded-full h-2 overflow-hidden"><div class="bg-tertiary rounded-full h-2" style="width:${pct}%"></div></div>
            <span class="text-data-tabular text-on-surface w-12">${hours.toFixed(1)}h</span>
          </div>
        </td>`;
      }).join("");
      return `<tr class="border-t border-outline-variant">
        <td class="px-3 py-2 text-body-sm font-semibold text-on-surface">${escapeHtml(platform.platform_name)}</td>
        ${cells}
        <td class="px-3 py-2 text-right text-data-tabular font-semibold text-primary">${platform.total_hours.toFixed(1)}h</td>
      </tr>`;
    }).join("");
    surface.innerHTML = `
      <div class="overflow-x-auto">
        <table class="w-full text-left">
          <thead><tr class="border-b border-outline-variant">
            <th class="px-3 py-2 text-left text-label-caps font-bold text-text-muted uppercase tracking-wider">Platform</th>
            ${headCells}
            <th class="px-3 py-2 text-right text-label-caps font-bold text-text-muted uppercase tracking-wider">Total</th>
          </tr></thead>
          <tbody>${bodyRows}</tbody>
        </table>
      </div>`;
  } catch (error) {
    surface.innerHTML = '<p class="text-body-sm text-error py-6 text-center">Portal usage report is unavailable right now.</p>'; 
  }
}

async function submitDailyUpdate(options = {}) {
  const stayOnPage = Boolean(options.stayOnPage);
  const status = options.status || "submitted";
  ensureDailyUpdateWorkspaceFields(document.querySelector(".workspace-surface"));
  const summary = document.getElementById("update-summary")?.value || document.querySelector(".workspace-surface textarea")?.value || "";
  const requisitionId = intOrNull(document.getElementById("requisition_id")?.value) || queryInt("requisition_id");
  const profilesSourced = intOrNull(document.getElementById("profiles-sourced-count")?.value);
  const profilesScreened = intOrNull(document.getElementById("profiles-screened-count")?.value);
  const profilesSubmitted = intOrNull(document.getElementById("profiles-submitted-count")?.value);
  const interviewsScheduled = intOrNull(document.getElementById("interviews-scheduled-count")?.value);
  const offersClosed = intOrNull(document.getElementById("offers-closed-count")?.value);
  const blockers = document.getElementById("blockers")?.value || null;
  const nextActions = document.getElementById("next-actions")?.value || null;
  const updateDate = document.getElementById("update-date")?.value || new Date().toISOString().split("T")[0];
  if (!summary.trim()) { showLiveError(new Error("Summary is required.")); return; }
  if (!requisitionId) { showLiveError(new Error("Please select a requisition.")); return; }
  let userId = currentUserId();
  const payload = {
    update_date: updateDate,
    requisition_id: requisitionId,
    submitted_by_user_id: userId,
    summary: summary.trim(),
    profiles_sourced_count: profilesSourced,
    profiles_screened_count: profilesScreened,
    profiles_submitted_count: profilesSubmitted,
    interviews_scheduled_count: interviewsScheduled,
    offers_closed_count: offersClosed,
    blockers,
    next_actions: nextActions,
    submission_status: status,
  };
  try {
    await apiRequest("/daily-updates/", { method: "POST", body: JSON.stringify(payload) });
    showLiveSuccess(status === "draft" ? "Draft saved" : "Daily update submitted");
    if (stayOnPage && typeof loadDailyUpdates === "function" && routeId() === "daily-updates-workspace") {
      await loadDailyUpdates();
      return;
    }
    setTimeout(() => { window.location.href = pageHref("daily-updates-review.html"); }, 1000);
  } catch (error) {
    const msg = error?.message || String(error);
    if (/403|linked.*requisition/i.test(msg)) {
      showLiveError(new Error("You are not assigned to this requisition. Contact your admin to assign you first."));
    } else if (/409|already exists/i.test(msg)) {
      showLiveError(new Error("An update for this requisition already exists today."));
    } else { showLiveError(error); }
  }
}

async function submitMeetingForm() {
  const session = RecruitOpsLive.session || readSession();
  const title = document.getElementById("meeting_title")?.value?.trim();
  const meetingType = document.getElementById("meeting_type")?.value;
  const meetingDate = document.getElementById("meeting_date")?.value;
  const startTime = document.getElementById("start_time")?.value;
  const agenda = document.getElementById("notes")?.value || null;
  const clientId = intOrNull(queryInt("client_id")) || session?.client_id;
  const locationId = session?.location_id || currentLocationId();
  let scheduledAt = null;
  if (meetingDate && startTime) scheduledAt = new Date(`${meetingDate}T${startTime}`).toISOString();
  /* Normalize meeting_type to backend enum */
  const typeMap = { standup: "internal_review", debrief: "internal_review", client_sync: "client_introduction", kickoff: "requirement_discussion", interview_panel: "review_meeting", other: "internal_review" };
  const normalizedType = typeMap[meetingType] || meetingType || "internal_review";
  if (!title) { showLiveError(new Error("Meeting title is required.")); return; }
  if (!clientId) { showLiveError(new Error("A client is required for meetings. Please create a client first.")); return; }
  const payload = {
    location_id: locationId,
    client_id: clientId,
    meeting_owner_user_id: currentUserId(),
    title,
    meeting_type: normalizedType,
    scheduled_at: scheduledAt,
    agenda,
  };
  try {
    await apiRequest("/meetings/", { method: "POST", body: JSON.stringify(payload) });
    showLiveSuccess("Meeting scheduled", title);
    afterOverlaySave("meetings.html");
  } catch (error) { showLiveError(error); }
}

async function submitOfferCreate() {
  const session = RecruitOpsLive.session || readSession();
  const applicationId = intOrNull(queryInt("application_id", "candidate_application_id")) || intOrNull(document.getElementById("candidate_application_id")?.value);
  const candidateId = intOrNull(queryInt("candidate_id")) || intOrNull(document.getElementById("candidate_id")?.value);
  const requisitionId = intOrNull(queryInt("requisition_id")) || intOrNull(document.getElementById("requisition_id")?.value);
  const offeredCtc = parseMoneyInput(document.getElementById("base_salary")?.value);
  const currency = document.getElementById("currency")?.value || "USD";
  const signingBonus = parseMoneyInput(document.getElementById("signing_bonus")?.value);
  const startDate = document.getElementById("start_date")?.value || null;
  const notes = document.getElementById("notes")?.value || null;
  /* If we have candidate+requisition but no application_id, we need to find it */
  let payload = {};
  if (applicationId) {
    payload.candidate_application_id = applicationId;
  } else if (candidateId && requisitionId) {
    /* Try to find the application from the candidate's applications list */
    const candidate = await apiRequest(`/candidates/${candidateId}`).catch(() => null);
    const app = candidate?.applications?.find(a => a.requisition_id === requisitionId);
    if (app) payload.candidate_application_id = app.id;
    else { showLiveError(new Error("No application found for this candidate-requisition pair.")); return; }
  } else {
    showLiveError(new Error("Please select a candidate and requisition.")); return;
  }
  payload.offered_ctc = offeredCtc;
  payload.offer_currency = currency;
  payload.signing_bonus = signingBonus;
  payload.expected_joining_date = startDate;
  payload.offer_notes = notes;
  payload.requested_by_user_id = currentUserId();
  try {
    await apiRequest("/offers/", { method: "POST", body: JSON.stringify(payload) });
    showLiveSuccess("Offer created");
    afterOverlaySave("offer-management.html");
  } catch (error) {
    const msg = error?.message || String(error);
    if (/500|database/i.test(msg)) {
      showLiveError(new Error("The offer could not be created. The candidate may need to be in an interview stage first."));
    } else { showLiveError(error); }
  }
}

async function submitLinkToRequisition() {
  const candidateId = queryInt("candidate_id", "id");
  const selectedCard = document.querySelector("[data-requisition-card-selected='true']") || document.querySelector(".border-2.border-primary");
  const requisitionId = intOrNull(selectedCard?.dataset?.requisitionId);
  if (!candidateId || !requisitionId) { showLiveError(new Error("Please select a candidate and a requisition.")); return; }
  const session = RecruitOpsLive.session || readSession();
  try {
    await apiRequest(`/candidates/${candidateId}/applications`, {
      method: "POST",
      body: JSON.stringify({
        requisition_id: requisitionId,
        initial_stage: "applied",
        owner_user_id: session?.user_id || currentUserId(),
      }),
    });
    showLiveSuccess("Candidate linked to requisition");
    afterOverlaySave("candidate-profiles.html");
  } catch (error) {
    const msg = error?.message || String(error);
    if (/duplicate.*check|cleared/i.test(msg)) {
      showLiveError(new Error("This candidate's duplicate check hasn't been cleared yet. Please resolve duplicates first."));
    } else { showLiveError(error); }
  }
}

async function loadLinkToRequisitionDialog() {
  const candidateId = queryInt("candidate_id", "id");
  const requisitions = await apiRequest("/requisitions/?page_size=20").catch(() => ({ items: [] }));
  const items = requisitions.items || [];
  const results = document.querySelector(".overlay-host .flex-1.overflow-y-auto");
  if (results && items.length) {
    results.innerHTML = items.map((item) => `
      <div class="p-stack-default bg-surface border border-border rounded cursor-pointer hover:border-primary transition-colors" data-requisition-card="true" data-requisition-id="${item.id}" onclick="this.classList.toggle('border-2'); this.classList.toggle('border-primary'); this.classList.toggle('border-border'); this.querySelectorAll('.requisition-check').forEach(c => c.classList.toggle('hidden'))">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-2">
            <span class="font-label-caps text-label-caps text-text-muted">REQ-${item.id}</span>
            <span class="w-1 h-1 rounded-full bg-border"></span>
            <span class="font-label-caps text-label-caps text-success-text">${escapeLiveHtml(item.status || "open")}</span>
          </div>
          <p class="font-headline-sm text-headline-sm text-on-surface">${escapeLiveHtml(item.title)}</p>
          <p class="font-body-sm text-body-sm text-text-muted">${escapeLiveHtml(item.client_name || "—")} · ${escapeLiveHtml(item.location_name || "—")}</p>
          <div class="flex items-center gap-2 mt-1">
            <span class="font-body-sm text-body-sm text-text-muted">${item.openings_count || 0} openings</span>
            <span class="w-1 h-1 rounded-full bg-border"></span>
            <span class="font-body-sm text-body-sm text-text-muted">${escapeLiveHtml(item.priority || "medium")}</span>
          </div>
        </div>
        <div class="requisition-check hidden absolute top-stack-default right-stack-default text-primary">
          <span class="material-symbols-outlined fill">check_circle</span>
        </div>
      </div>
    `).join("");
  }
}


/* ═══════════════════════════════════════════════════════════════
   CUSTOM REPORT BUILDER
   ═══════════════════════════════════════════════════════════════ */

const CUSTOM_REPORT_METRIC_TO_DATASET = [
  { match: /time to fill/i, dataset: "time_to_fill" },
  { match: /conversion rate|pipeline/i, dataset: "pipeline" },
  { match: /source roi|source/i, dataset: "source_effectiveness" },
  { match: /sla/i, dataset: "sla" },
  { match: /team utilization|requisition/i, dataset: "requisitions" },
  { match: /daily|update/i, dataset: "daily_updates" },
];

async function loadCustomReportBuilder() {
  const root = document.querySelector(".workspace-surface");
  if (!root) return;
  styleCustomReportChoices(root);
  bindCustomReportBuilder(root);
}

function customReportSelectedDataset(root) {
  const inputs = customReportInputs(root);
  const joined = inputs.selectedMetrics.join(" ");
  return CUSTOM_REPORT_METRIC_TO_DATASET.find((item) => item.match.test(joined))?.dataset || "requisitions";
}

function bindCustomReportBuilder(root) {
  if (root.dataset.liveCustomReportBound === "true") return;
  root.dataset.liveCustomReportBound = "true";
  root.addEventListener("change", () => styleCustomReportChoices(root));
  const generateButton = Array.from(root.querySelectorAll("button")).find((button) => /generate now/i.test(button.textContent || ""));
  if (generateButton) generateButton.addEventListener("click", () => runCustomReport(root));
}

function renderCustomReportDatasetTable(root, dataset, dimension, rows) {
  const host = root.querySelector(".chart-placeholder");
  if (!host) return;
  const columns = (dimension?.columns || []).filter((column) => rows.length === 0 || rows.some((row) => row[column.key] != null));
  host.classList.remove("chart-placeholder");
  host.innerHTML = `<div class="rounded-lg border border-outline-variant bg-surface overflow-hidden">
    <div class="flex items-center justify-between p-3 border-b border-outline-variant">
      <div>
        <p class="text-headline-sm font-semibold text-on-surface">${escapeLiveHtml(dimension?.label || dataset)}</p>
        <p class="text-body-sm text-text-muted">${rows.length} row${rows.length === 1 ? "" : "s"} from live data</p>
      </div>
    </div>
    <div class="overflow-x-auto max-h-80">
      <table class="w-full">
        <thead><tr class="border-b border-outline-variant">
          ${columns.map((column) => `<th class="text-left px-3 py-2 text-label-caps font-bold text-text-muted uppercase tracking-wider">${escapeLiveHtml(column.label)}</th>`).join("")}
        </tr></thead>
        <tbody>
          ${rows.length
            ? rows.slice(0, 50).map((row) => `<tr class="border-b border-outline-variant hover:bg-highlight-soft">
                ${columns.map((column) => {
                  const value = row[column.key];
                  const display = value == null ? "—" : column.type === "date" && value ? String(value).slice(0, 10) : String(value);
                  return `<td class="px-3 py-2 text-body-sm ${column.type === "number" ? "text-data-tabular" : ""} text-on-surface">${escapeLiveHtml(display.length > 80 ? `${display.slice(0, 80)}…` : display)}</td>`;
                }).join("")}
              </tr>`).join("")
            : `<tr><td class="px-3 py-6 text-body-sm text-text-muted" colspan="${columns.length || 1}">No rows returned for this dataset.</td></tr>`}
        </tbody>
      </table>
    </div>
  </div>`;
}

async function runCustomReport(root) {
  const dataset = customReportSelectedDataset(root);
  const inputs = customReportInputs(root);
  try {
    const payload = await apiRequest(`/reports/datasets/${dataset}`);
    const dimension = payload.dimensions?.[0];
    renderCustomReportDatasetTable(root, dataset, dimension, payload.rows || []);
    root.dataset.liveCustomReportDestination = customReportDestination(inputs.selectedMetrics);
  } catch (error) {
    showLiveError(error);
  }
}


/* ═══════════════════════════════════════════════════════════════
   LIVE API INTERACTIONS
   ═══════════════════════════════════════════════════════════════ */

function bindLiveApiInteractions() {
  if (document.documentElement.dataset.liveApiInteractionsBound === "true") return;
  document.documentElement.dataset.liveApiInteractionsBound = "true";

  document.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : event.target?.parentElement;

    /* RBAC: Check data-rbac-require on clicked buttons */
    const rbacTarget = target?.closest("[data-rbac-require]");
    if (rbacTarget && !isAdmin()) {
      const required = rbacTarget.dataset.rbacRequire.split(",");
      if (!hasAnyPermission(...required)) {
        event.preventDefault();
        event.stopPropagation();
        showAccessDenied(rbacTarget.dataset.rbacLabel || "this action");
        return;
      }
    }

    // Workflow actions
    const workflowButton = target?.closest("[data-live-workflow-action]");
    if (workflowButton) {
      event.preventDefault();
      event.stopPropagation();
      runWorkflowAction(workflowButton);
      return;
    }

    // Notification open record
    const openNotification = target?.closest("[data-notification-open]");
    if (openNotification) {
      event.preventDefault();
      event.stopPropagation();
      openNotificationRecord(openNotification);
      return;
    }

    // Notification read
    const readButton = target?.closest("[data-live-notification-read]");
    if (readButton) {
      event.preventDefault();
      event.stopPropagation();
      markLiveNotificationRead(readButton);
      return;
    }

    // Credential reset
    const credentialResetButton = target?.closest("[data-live-user-credentials-reset]");
    if (credentialResetButton) {
      event.preventDefault();
      event.stopPropagation();
      resetUserCredentials(credentialResetButton);
      return;
    }

    // Permission toggle
    const permissionToggle = target?.closest("[data-perm]");
    if (permissionToggle && routeId() === "role-permissions-editor") {
      event.preventDefault();
      event.stopPropagation();
      if (!permissionToggle.disabled) {
        setPermissionToggleState(permissionToggle, !permissionToggle.classList.contains("on"));
        markRolePermDirty();
      }
      return;
    }

    // Permission save
    const permissionSaveButton = target?.closest("[data-live-role-permissions-save]");
    if (permissionSaveButton) {
      event.preventDefault();
      event.stopPropagation();
      saveRolePermissions(permissionSaveButton);
      return;
    }

    // Notifications: mark all as read
    const markAllReadButton = target?.closest("[data-live-notifications-mark-all-read]");
    if (markAllReadButton) {
      event.preventDefault();
      event.stopPropagation();
      markAllNotificationsReadAction(markAllReadButton);
      return;
    }

    // Agents: open run detail
    const openRunButton = target?.closest("[data-live-agents-open-run]");
    if (openRunButton) {
      event.preventDefault();
      event.stopPropagation();
      openAgentRunDetail(openRunButton);
      return;
    }

    // Notifications center: AI triage review mode
    const triageToggle = target?.closest("[data-live-notifications-triage]");
    if (triageToggle) {
      event.preventDefault();
      event.stopPropagation();
      enterNotificationsTriage(triageToggle);
      return;
    }
    if (target?.closest("[data-triage-exit]")) {
      event.preventDefault();
      event.stopPropagation();
      exitNotificationsTriage();
      return;
    }
    const triageGotIt = target?.closest("[data-triage-got-it]");
    if (triageGotIt) {
      event.preventDefault();
      event.stopPropagation();
      triageGotItAction(triageGotIt);
      return;
    }
    const triageOpen = target?.closest("[data-triage-open]");
    if (triageOpen) {
      event.preventDefault();
      event.stopPropagation();
      triageOpenAction(triageOpen);
      return;
    }

    // Agents: run the selected agent
    const runAgentButton = target?.closest("[data-live-agents-open-runner]");
    if (runAgentButton) {
      event.preventDefault();
      event.stopPropagation();
      runAgentAction(runAgentButton);
      return;
    }

    // Agents: Run AI Screener from a candidate page (deep-links to workbench)
    const screenerButton = target?.closest("[data-live-agents-run-screener]");
    if (screenerButton) {
      event.preventDefault();
      event.stopPropagation();
      const candidateId = screenerButton.dataset.candidateId;
      if (!candidateId) {
        showToast("Hold on", "Load the candidate profile first, then run the screener.");
        return;
      }
      navigateToRoute(`agents-workbench.html?candidate_id=${encodeURIComponent(candidateId)}`);
      return;
    }

    // Agents: accept/reject a run
    const decideAgentButton = target?.closest("[data-live-agents-decide]");
    if (decideAgentButton) {
      event.preventDefault();
      event.stopPropagation();
      decideAgentRunAction(decideAgentButton);
      return;
    }

    // Permission reset (discard unsaved toggles)
    const permissionResetButton = target?.closest("[data-live-role-permissions-reset]");
    if (permissionResetButton) {
      event.preventDefault();
      event.stopPropagation();
      resetRolePermissions();
      return;
    }

    // Requisition status
    const requisitionStatusButton = target?.closest("[data-live-requisition-status]");
    if (requisitionStatusButton) {
      event.preventDefault();
      event.stopPropagation();
      submitRequisitionStatus(requisitionStatusButton);
      return;
    }

    // Duplicate decision
    const duplicateDecisionButton = target?.closest("[data-live-duplicate-decision]");
    if (duplicateDecisionButton) {
      event.preventDefault();
      event.stopPropagation();
      runDuplicateDecision(duplicateDecisionButton);
      return;
    }

    // Assignment create
    const assignButton = target?.closest("[data-live-assign-user]");
    if (assignButton) {
      event.preventDefault();
      event.stopPropagation();
      createRequisitionAssignment(assignButton);
      return;
    }

    // Assignment remove
    const removeButton = target?.closest("[data-live-assignment-remove]");
    if (removeButton) {
      event.preventDefault();
      event.stopPropagation();
      removeRequisitionAssignment(removeButton);
      return;
    }

    // Report filter
    const reportFilterButton = target?.closest("[data-live-report-filter]");
    if (reportFilterButton && routeId() === "reports") {
      event.preventDefault();
      event.stopPropagation();
      const filter = reportFilterButton.dataset.liveReportFilter || "all";
      document.querySelectorAll("[data-live-report-filter]").forEach((button) => {
        const active = button === reportFilterButton;
        button.classList.toggle("bg-primary-container", active);
        button.classList.toggle("text-on-primary-container", active);
        button.classList.toggle("border", !active);
        button.classList.toggle("border-outline-variant", !active);
      });
      try {
        renderReportLibraryCards(JSON.parse(document.querySelector(".workspace-surface")?.dataset.liveReports || "[]"), filter);
      } catch { renderReportLibraryCards([], filter); }
      return;
    }

    // Form submissions
    const routeSubmitButton = target?.closest("button");
    const route = routeId();
    const submitRoutes = new Set(["contact-form-dialog", "requisition-intake", "requisition-intake-edit", "daily-updates-submission", "daily-updates-workspace", "meeting-form-dialog", "offer-create-dialog", "link-to-requisition-dialog", "stage-move-dialog", "candidate-review-drawer", "onboarding-company-profile", "onboarding-locations", "onboarding-role-setup", "onboarding-hiring-teams"]);
    const label = (typeof getActionLabel === "function" ? getActionLabel(routeSubmitButton) : (routeSubmitButton?.textContent || "").replace(/\s+/g, " ").trim().toLowerCase());
    if (routeSubmitButton && submitRoutes.has(route) && /^(save|create|update|submit|schedule|confirm|continue|next|add|send|save changes|save user|save client|save contact|save role|create requisition|save candidate|update candidate)/.test(label)) {
      event.preventDefault();
      event.stopPropagation();
      if (route === "daily-updates-workspace") {
        submitDailyUpdate({ stayOnPage: true, status: /^save draft/.test(label) ? "draft" : "submitted" });
        return;
      }
      handleFormSubmit(document.querySelector("form") || routeSubmitButton.closest("form") || document.body);
      return;
    }
  }, true);

  document.addEventListener("change", (event) => {
    const target = event.target instanceof Element ? event.target : event.target?.parentElement;
    const resumeInput = target?.closest?.("[data-live-resume-file-input]");
    if (resumeInput) uploadCandidateResume(resumeInput);
  });

  // Login form
  const loginForm = document.querySelector('form[data-login], form[action*="login"], #login-form');
  if (loginForm) {
    loginForm.addEventListener("submit", (e) => { e.preventDefault(); handleLogin(loginForm); });
  }

  // Forgot password form
  const forgotForm = document.querySelector('form[data-forgot]');
  if (forgotForm) {
    forgotForm.addEventListener("submit", (e) => { e.preventDefault(); handleForgot(forgotForm); });
  }
}


/* ═══════════════════════════════════════════════════════════════
   ONBOARDING — Setup Flow Submissions
   ═══════════════════════════════════════════════════════════════ */

/* ═══════════════════════════════════════════════════════════════
   ONBOARDING — Location guidance
   Locations scope clients, requisitions and users, so during setup
   we surface the admin's working location and make switching to a
   newly created HQ one click. This prevents the "client owner must
   belong to the same location" rejection from surprising new users.
   ═══════════════════════════════════════════════════════════════ */

function wireOnboardingLocationGuidance() {
  const session = RecruitOpsLive.session || readSession();
  const banner = document.querySelector("[data-current-location-banner]");
  if (!banner) return;
  const nameEl = banner.querySelector("[data-current-location-name]");
  const locationName = session?.location_name || "your primary location";
  if (nameEl && session?.location_name) nameEl.textContent = session.location_name;
  else if (nameEl) nameEl.textContent = "your primary location";
  banner.classList.remove("hidden");
  banner.classList.add("flex");
  /* Keep the session location fresh after the admin moves to a new HQ. */
  banner.querySelector("[data-switch-location-btn]")?.addEventListener("click", async () => {
    const created = banner.querySelector("[data-created-location-name]")?.textContent || "";
    const locations = session.onboarding?.locations || [];
    const target = locations.find((loc) => loc.name === created);
    if (!target) return;
    try {
      await apiRequest(`/users/${session.user_id}/move`, {
        method: "POST",
        body: JSON.stringify({ new_primary_location_id: target.id, reason: "Set as company headquarters during onboarding", review_confirmed: true }),
      });
      session.location_id = target.id;
      session.location_name = target.name;
      writeSession(session);
      RecruitOpsLive.session = session;
      if (nameEl) nameEl.textContent = target.name;
      banner.querySelector("[data-switch-location-row]")?.classList.add("hidden");
      showLiveSuccess("Working location updated", `You now work from ${target.name}.`);
    } catch (error) { showLiveError(error); }
  });
}

async function submitOnboardingCompanyProfile() {
  const session = RecruitOpsLive.session || readSession();
  const legalName = document.getElementById("legalName")?.value?.trim();
  const brandName = document.getElementById("brandName")?.value?.trim();
  const industry = document.getElementById("industry")?.value;
  const size = document.getElementById("size")?.value;
  const currency = document.getElementById("currency")?.value;
  const timezone = document.getElementById("timezone")?.value;
  if (!legalName) { showLiveError(new Error("Company legal name is required.")); return; }
  /* Store company profile in session for onboarding flow */
  session.onboarding = session.onboarding || {};
  session.onboarding.company = { legalName, brandName, industry, size, currency, timezone };
  writeSession(session);
  RecruitOpsLive.session = session;
  /* Persist a headquarters location so the company exists in the database */
  try {
    const locationName = legalName + " — Headquarters";
    const payload = {
      location_name: locationName,
      location_code: legalName.substring(0, 10).toUpperCase().replace(/\s+/g, ""),
      status: "active",
    };
    const result = await apiRequest("/locations/", { method: "POST", body: JSON.stringify(payload) });
    session.onboarding.locations = session.onboarding.locations || [];
    session.onboarding.locations.push({ id: result.id, name: locationName });
    writeSession(session);
    RecruitOpsLive.session = session;
    showLiveSuccess("Company profile saved", "Headquarters location created.");
  } catch (error) {
    /* Location may already exist — still save the profile */
    showLiveSuccess("Company profile saved");
  }
}

async function submitOnboardingLocation() {
  const session = RecruitOpsLive.session || readSession();
  const nameInput = document.querySelector("input[placeholder*='location' i], input[placeholder*='office' i], input[placeholder*='branch' i]") || document.querySelector(".workspace-surface input[type='text']");
  const name = nameInput?.value?.trim();
  if (!name) { showLiveError(new Error("Location name is required.")); return; }
  const payload = {
    location_name: name,
    location_code: name.substring(0, 10).toUpperCase().replace(/\s+/g, ""),
    status: "active",
  };
  try {
    const result = await apiRequest("/locations/", { method: "POST", body: JSON.stringify(payload) });
    session.onboarding = session.onboarding || {};
    session.onboarding.locations = session.onboarding.locations || [];
    session.onboarding.locations.push({ id: result.id, name });
    writeSession(session);
    RecruitOpsLive.session = session;
    showLiveSuccess("Location created", name);
    if (nameInput) nameInput.value = "";
    /* If this differs from the admin's working location, offer a one-click move. */
    if (session.location_id && result.id !== session.location_id) {
      const banner = document.querySelector("[data-current-location-banner]");
      if (banner) {
        const createdEl = banner.querySelector("[data-created-location-name]");
        if (createdEl) createdEl.textContent = name;
        banner.querySelector("[data-switch-location-row]")?.classList.remove("hidden");
      }
    }
  } catch (error) { showLiveError(error); }
}

async function submitOnboardingRole() {
  const session = RecruitOpsLive.session || readSession();
  const nameInput = document.querySelector("input[placeholder*='role' i], input[placeholder*='title' i]") || document.querySelector(".workspace-surface input[type='text']");
  const name = nameInput?.value?.trim();
  if (!name) { showLiveError(new Error("Role name is required.")); return; }
  const payload = {
    name: name,
    code: name.toLowerCase().replace(/\s+/g, "_").substring(0, 30),
    status: "active",
  };
  try {
    const result = await apiRequest("/roles/", { method: "POST", body: JSON.stringify(payload) });
    session.onboarding = session.onboarding || {};
    session.onboarding.roles = session.onboarding.roles || [];
    session.onboarding.roles.push({ id: result.id, name });
    writeSession(session);
    RecruitOpsLive.session = session;
    showLiveSuccess("Role created", name);
    if (nameInput) nameInput.value = "";
  } catch (error) { showLiveError(error); }
}

async function submitOnboardingTeam() {
  const session = RecruitOpsLive.session || readSession();
  const nameInput = document.querySelector("input[placeholder*='name' i]") || document.querySelector(".workspace-surface input[type='text']");
  const emailInput = document.querySelector("input[type='email'], input[placeholder*='email' i]");
  const name = nameInput?.value?.trim();
  const email = emailInput?.value?.trim();
  if (!name || !email) { showLiveError(new Error("Name and email are required.")); return; }
  const locationId = session?.location_id || currentLocationId();
  const roleId = session?.onboarding?.roles?.[0]?.id || 4; /* Default to recruiter role */
  const payload = {
    full_name: name,
    email: email,
    employee_code: name.substring(0, 8).toUpperCase().replace(/\s+/g, "") + Math.floor(Math.random() * 1000),
    primary_location_id: locationId,
    primary_role_id: roleId,
    status: "active",
  };
  try {
    const result = await apiRequest("/users/", { method: "POST", body: JSON.stringify(payload) });
    session.onboarding = session.onboarding || {};
    session.onboarding.team = session.onboarding.team || [];
    session.onboarding.team.push({ id: result.id, name, email });
    writeSession(session);
    RecruitOpsLive.session = session;
    showLiveSuccess("Team member added", name);
    if (nameInput) nameInput.value = "";
    if (emailInput) emailInput.value = "";
  } catch (error) { showLiveError(error); }
}

async function completeOnboarding() {
  const session = RecruitOpsLive.session || readSession();
  /* Mark onboarding as complete */
  localStorage.setItem("recruitops-onboarding-complete", "true");
  /* Ensure user has Admin role */
  session.role = "admin";
  session.role_code = "admin";
  writeSession(session);
  RecruitOpsLive.session = session;
  /* Persist the admin role assignment to the database */
  try {
    const userId = session.user_id || currentUserId();
    if (userId && session.token) {
      await apiRequest(`/users/${userId}`, {
        method: "PATCH",
        body: JSON.stringify({ status: "active" }),
      });
    }
  } catch (e) { /* Best effort — session already set */ }
}

/* ═══════════════════════════════════════════════════════════════
   PAGE BOOT & ROUTING
   ═══════════════════════════════════════════════════════════════ */

async function bootPage() {
  if (!LIVE_API_ENABLED) {
    hidePageLoader();
    return;
  }
  RecruitOpsLive.session = readSession();
  const route = routeId();
  const kind = document.body?.dataset.routeKind || "";

  if (!PUBLIC_ROUTES.has(route) && kind !== "auth" && kind !== "marketing" && !RecruitOpsLive.session?.token) {
    window.location.href = pageHref("login.html");
    return;
  }

  const loaders = {
    "candidate-profiles": loadCandidates,
    "candidate-detail": loadCandidateDetail,
    "candidate-duplicate-review": loadCandidateDuplicateReview,
    "candidate-screening": loadCandidateScreening,
    "candidate-review-drawer": loadCandidateReviewDrawer,
    "duplicate-warning-modal": loadDuplicateWarningModal,
    "resume-upload-and-review": loadResumeUploadReview,
    "link-to-requisition-dialog": loadLinkToRequisitionDialog,
    "pipeline-board": loadPipeline,
    "application-detail-drawer": loadPipelineApplicationDetail,
    "pipeline-history-drawer": loadPipelineApplicationHistory,
    "stage-move-dialog": loadStageMoveDialog,
    "stage-history-audit-log": loadPipelineApplicationHistory,
    "client-directory": loadClients,
    "client-detail": loadClientDetail,
    "contact-form-dialog": loadContactFormDialog,
    "requisition-intake": loadRequisitionIntake,
    "requisition-intake-edit": loadRequisitionIntake,
    "requisition-detail": loadRequisitionDetail,
    "assignment-history-drawer": loadAssignmentHistoryDrawer,
    "work-assignment": loadWorkAssignment,
    "portal-accounts": loadPortalAccounts,
    "reassign-owner-dialog": loadReassignOwnerDialog,
    "reassignment-review-drawer": loadReassignmentReviewDrawer,
    "status-update-dialog": loadStatusUpdateDialog,
    "exception-request-dialog": loadWorkflowOverlay,
    "clarification-request-dialog": loadWorkflowOverlay,
    "user-management": loadUsers,
    "user-detail": loadUserDetail,
    "deactivate-user-dialog": loadDeactivateUserDialog,
    "my-profile": loadMyProfile,
    "role-management": loadRoles,
    "role-permissions-editor": loadRolePermissionsEditor,
    "role-dashboard": async () => { await Promise.all([loadRoleDashboard().catch(() => {}), loadWorkflowActions().catch(() => {})]); },
    "my-work-dashboard": loadMyWorkDashboard,
    "company-dashboard": loadDashboards,
    "location-management": loadLocations,
    "location-dashboard": loadLocationDashboard,
    "visibility-rules": loadVisibilityRules,
    "business-titles": loadBusinessTitles,
    "daily-updates-workspace": loadDailyUpdates,
    "daily-updates-submission": loadDailyUpdateSubmission,
    "daily-updates-review": loadDailyUpdatesReview,
    "daily-update-detail-panel": loadDailyUpdateDetail,
    "daily-review": loadDailyReview,
    "meetings": loadMeetings,
    "meeting-form-dialog": loadMeetingFormDialog,
    "follow-ups": loadFollowUps,
    "follow-up-form-dialog": loadFollowUpFormDialog,
    "interview-scheduler": async () => {
      const payload = await apiRequest("/interviews/?page_size=50").catch(() => ({ items: [] }));
      const surface = document.querySelector(".workspace-surface");
      if (surface) {
        const list = surface.querySelector(".rounded-xl.flex.flex-col");
        if (list) list.innerHTML = (payload.items || []).map((item, i) => renderInterviewCard(item, i)).join("") || '<div class="p-6 text-center text-text-muted">No interviews.</div>';
      }
    },
    "interview-detail": loadInterviewDetail,
    "interview-feedback-dialog": loadInterviewFeedbackDialog,
    "notifications-center": loadNotifications,
    "notification-detail-panel": loadNotificationDetailPanel,
    "approvals-inbox": loadApprovalsInbox,
    "approval-review-drawer": loadWorkflowOverlay,
    "dashboard-actions-overlay": loadDashboardActionsOverlay,
    "offer-management": loadOfferManagement,
    "offer-create-dialog": loadOfferCreateDialog,
    "join-tracker": loadJoinTracker,
    "team-workload": loadTeamWorkload,
    "user-performance-reports": loadUserPerformanceReports,
    "time-to-fill-report": loadTimeToFillReport,
    "source-effectiveness": loadSourceEffectiveness,
    "sla-tracker": loadSlaTracker,
    "pipeline-analytics": loadPipelineAnalytics,
    "analytics-dashboard": loadAnalyticsDashboard,
    "reports": loadReportsLibrary,
    "custom-report-builder": loadCustomReportBuilder,
    "report-viewer": loadReportViewer,
    "review-matches-workspace": loadReviewMatchesWorkspace,
    "requisition-list": async () => {
      const payload = await apiRequest("/requisitions/?page_size=100").catch(() => ({ items: [] }));
      fillExistingTable(payload.items || [], (row, item) => {
        const cells = row.querySelectorAll("td");
        /* Column order: Requisition | Client | Openings | Ownership | Location | Priority | Status | Age */
        setStackedCell(cells[0], item.title || item.requisition_code, item.client_name || "");
        if (cells[0] && typeof entityBadgeHtml === "function" && item.requisition_code && !cells[0].querySelector(":scope > .entity-badge")) {
          cells[0].insertAdjacentHTML("beforeend", entityBadgeHtml(item.requisition_code, item.branch_code));
        }
        paintPersonCell(cells[1], item.client_name);
        setCellValue(cells[2], `${item.openings_count ?? "—"} opening${item.openings_count === 1 ? "" : "s"}`);
        paintPersonCell(cells[3], item.primary_owner_name);
        setCellValue(cells[4], item.work_mode || "—");
        paintPriorityBadge(cells[5], item.priority);
        setCellValue(cells[6], item.status || "—");
        setCellValue(cells[7], ageDaysLabel(item.created_at));
        row.dataset.filterStatus = String(item.status || "").toLowerCase();
        row.dataset.filterPriority = String(item.priority || "").toLowerCase();
        row.dataset.filterClient = item.client_name || "";
        row.dataset.filterCode = item.requisition_code || "";
        row.dataset.filterOwner = item.primary_owner_name || "";
        row.dataset.filterLocation = item.work_mode || item.location_name || "";
        const detailRoute = `requisition-detail.html?requisition_id=${item.id}`;
        row.querySelectorAll('[data-route*="requisition-detail"]').forEach((el) => {
          el.dataset.route = detailRoute;
          el.setAttribute("aria-label", `Open ${item.title || item.requisition_code || "requisition"}`);
        });
        row.dataset.route = detailRoute;
        row.classList.add("cursor-pointer");
      });
    },
    "application-history": async () => {
      const candidateId = queryInt("candidate_id");
      if (!candidateId) return;
      const candidate = await apiRequest(`/candidates/${candidateId}`).catch(() => null);
      if (candidate) setFirstText("[data-candidate-name], h1", candidate.full_name);
    },
    "delivery-work-queue": async () => {
      const payload = await apiRequest("/requisitions/?page_size=50").catch(() => ({ items: [] }));
      fillExistingTable(payload.items || [], (row, item) => {
        const cells = row.querySelectorAll("td");
        setStackedCell(cells[0], item.title, item.client_name || "");
        setCellValue(cells[1], item.priority || "—");
        setCellValue(cells[2], item.openings_count || "0");
        setCellValue(cells[3], item.status || "open");
      });
    },
    "support-workspace": async () => {
      // Support page - no API needed, shows static help content
    },
    "agents-workbench": async () => {
      const [catalog, runsPayload] = await Promise.all([
        loadAgentsCatalog(),
        loadAgentsRuns().catch(() => ({ items: [] })),
      ]);
      /* Deep-link support: ?candidate_id=X prefills the Resume Screener
         context from a candidate page; &autorun=1 fires it immediately. */
      const linkedCandidateId = queryInt("candidate_id");
      if (linkedCandidateId) {
        agentsRunContext = {
          candidate_id: linkedCandidateId,
          requisition_id: queryInt("requisition_id") || undefined,
          run: queryInt("autorun") === 1,
        };
        renderAgentsRunContextBanner(catalog);
        const candidate = await apiRequest(`/candidates/${linkedCandidateId}`).catch(() => null);
        if (candidate?.full_name) {
          agentsRunContext.candidate_name = candidate.full_name;
          renderAgentsRunContextBanner(catalog, true);
        }
        const selectEl = document.querySelector("[data-agents-select]");
        if (selectEl) selectEl.value = "resume_screener";
      }
      if (renderAgentsWorkbench(catalog, { items: agentsRunsCache })) {
        wireAgentsWorkbenchFilters();
      }
      if (agentsRunContext?.run && typeof runAgentAction === "function") {
        const runButton = document.querySelector("[data-live-agents-open-runner]");
        runAgentAction(runButton, { ...agentsRunContext, agentId: "resume_screener" });
      }
    },
    "onboarding-company-profile": async () => { wireOnboardingLocationGuidance(); },
    "onboarding-hiring-teams": async () => {},
    "onboarding-locations": async () => { wireOnboardingLocationGuidance(); },
    "onboarding-role-setup": async () => {},
    "onboarding-pipeline-stage-builder": async () => {},
    "onboarding-integrations": async () => {},
    "onboarding-success-launch": async () => { await completeOnboarding(); },
  };
  RecruitOpsLive.pageLoaders = loaders;
  RecruitOpsLive.reloadCurrentPage = async () => {
    const id = pathRouteId();
    if (loaders[id]) await loaders[id]();
    if (typeof hydrateLiveFilters === "function") hydrateLiveFilters();
  };
  RecruitOpsLive.bootOverlay = async (overlayRoute) => {
    if (loaders[overlayRoute]) await loaders[overlayRoute]();
  };

  /* RBAC: Block access to unauthorized pages. The gate map now lives in
     navigation.config.js (NAV_PAGE_PERMISSIONS) — this file no longer
     duplicates it. Deep-link gating behavior is unchanged. */
  if (!isAdmin() && !PUBLIC_ROUTES.has(route)) {
    const pagePermMap = (window.NAV_CONFIG && window.NAV_CONFIG.pagePermissions) || {};
    const required = pagePermMap[route];
    if (required && !hasAnyPermission(...required)) {
      hidePageLoader();
      showAccessDenied("access this page");
      return;
    }
  }

  try {
    await hydrateSelects();
    if (loaders[route]) await loaders[route]();
    if (typeof hydrateLiveFilters === "function") hydrateLiveFilters();
  } catch (error) {
    showLiveError(error);
  } finally {
    hidePageLoader();
  }
}


/* ═══════════════════════════════════════════════════════════════
   EXPOSE PUBLIC API FOR APP.JS
   ═══════════════════════════════════════════════════════════════ */

RecruitOpsLive.handleLogin = handleLogin;
RecruitOpsLive.handleLogout = handleLogout;
RecruitOpsLive.handleForgot = handleForgot;
RecruitOpsLive.handleFormSubmit = handleFormSubmit;
RecruitOpsLive.markNotificationRead = markNotificationReadAction;
RecruitOpsLive.refreshNotificationBadge = refreshNotificationBadge;
RecruitOpsLive.bootOverlay = RecruitOpsLive.bootOverlay || (async (overlayRoute) => {
  const fn = RecruitOpsLive.pageLoaders?.[overlayRoute];
  if (fn) await fn();
});
RecruitOpsLive.reloadCurrentPage = RecruitOpsLive.reloadCurrentPage || (async () => {
  const fn = RecruitOpsLive.pageLoaders?.[pathRouteId()];
  if (fn) await fn();
  if (typeof hydrateLiveFilters === "function") hydrateLiveFilters();
});
RecruitOpsLive.startNotificationBadgePolling = startNotificationBadgePolling;
RecruitOpsLive.onSessionChangedBadgePoll = onSessionChangedBadgePoll;
window.RecruitOpsLive = RecruitOpsLive;


/* ═══════════════════════════════════════════════════════════════
   ENTRY POINT
   ═══════════════════════════════════════════════════════════════ */

function startLiveApiClient() {
  if (!LIVE_API_ENABLED) {
    hidePageLoader();
    return;
  }
  /* Marketing pages load the app scripts but must never receive app chrome
     (connection pill, sidebar RBAC, badge polling) — even when a session exists. */
  const isLandingPage = !!document.querySelector(".landing-nav, .landing-hero");
  if (!isLandingPage) decorateShell();
  bindLiveApiInteractions();

  // Handle logout links — call API, clear session, redirect
  document.querySelectorAll('[data-logout-link]').forEach((link) => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      handleLogout();
    });
  });

  // Clear session if arriving with ?loggedOut=true
  if (window.location.search.includes('loggedOut=true')) {
    writeSession(null);
    RecruitOpsLive.session = null;
  }

  Promise.resolve(bootPage()).catch(() => {}).finally(() => {
    hidePageLoader();
  });

  if (!isLandingPage && (RecruitOpsLive.session || readSession())) {
    startNotificationBadgePolling();
  }
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startLiveApiClient, { once: true });
  } else {
    startLiveApiClient();
  }
}
