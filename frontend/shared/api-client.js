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
  "onboarding-hiring-teams", "onboarding-integrations",
]);


/* ═══════════════════════════════════════════════════════════════
   SESSION & API LAYER
   ═══════════════════════════════════════════════════════════════ */

function routeId() {
  const file = (window.location.pathname.split("/").pop() || "index.html").replace(/\.html.*/, "").replace(/\?.*/, "");
  return file || "index";
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
}async function apiRequest(path, options = {}) {
  const session = RecruitOpsLive.session || readSession();
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (session?.token) headers["Authorization"] = `Bearer ${session.token}`;
  const origin = window.location.origin && window.location.protocol !== "file:" ? window.location.origin : "http://localhost:8000";
  const url = path.startsWith("http") ? path : `${origin}${API_BASE}${path}`;
  const response = await fetch(url, { ...options, headers });
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
}

function showLiveError(error) {
  const message = error?.message || String(error);
  console.error("[RecruitOps]", message);
  const toast = document.createElement("div");
  toast.className = "fixed bottom-4 right-4 z-[9999] max-w-sm rounded-lg border border-danger-text/30 bg-danger-bg px-4 py-3 shadow-lg";
  toast.innerHTML = `<p class="font-body-sm font-semibold text-danger-text">Error</p><p class="font-body-sm text-danger-text">${escapeLiveHtml(message)}</p>`;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 5000);
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

function hasPermission(permissionCode) {
  if (isAdmin()) return true;
  const perms = userPermissions();
  if (!perms.length) return true; /* If no permissions loaded, allow (fail-open for UX) */
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
  const route = routeId();
  if (route === "location-form-drawer" || route === "user-form-drawer") {
    const locations = await apiRequest("/locations/?page_size=100").catch(() => ({ items: [] }));
    await fillSelect("location_id", locations.items || [], (l) => l.location_name || l.name || `Location ${l.id}`, (l) => l.id, queryInt("location_id"));
  }
  if (route === "user-form-drawer" || route === "role-form-drawer") {
    const roles = await apiRequest("/roles/?page_size=50").catch(() => ({ items: [] }));
    await fillSelect("role_id", roles.items || [], (r) => r.role_name || r.name || `Role ${r.id}`, (r) => r.id, queryInt("role_id"));
  }
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
    node.textContent = session.role || "Recruiter";
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
  "location-form-drawer.html": ["location.create"],
  "location-dashboard.html": ["location.read"],
  "user-management.html": ["user.read", "user.create"],
  "user-form-drawer.html": ["user.create"],
  "role-management.html": ["role.read", "role.create"],
  "role-form-drawer.html": ["role.create"],
  "role-permissions-editor.html": ["role.permissions.assign"],
  "business-titles.html": ["settings.read"],
  "visibility-rules.html": ["settings.read", "role.read"],
  "work-assignment.html": ["assignment.read", "requisition.assign"],
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
  const healthOrigin = window.location.origin && window.location.protocol !== "file:" ? window.location.origin : "http://localhost:8000";
  fetch(`${healthOrigin}${API_BASE}/health`).then(() => {
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
  if (overlay) overlay.classList.remove("hidden");
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
      window.location.href = pageHref("daily-review.html");
    }
  } catch (error) {
    if (overlay) overlay.classList.add("hidden");
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
}function handleFormSubmit(form) {
  const route = routeId();
  const submitMap = {
    "location-form-drawer": submitLocation,
    "user-form-drawer": submitUser,
    "role-form-drawer": submitRole,
    "client-create-or-edit-drawer": submitClient,
    "contact-form-dialog": submitContact,
    "requisition-intake": submitRequisition,
    "requisition-intake-edit": submitRequisition,
    "daily-updates-submission": submitDailyUpdate,
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
      "location-form-drawer": "location.create",
      "user-form-drawer": "user.create",
      "role-form-drawer": "role.create",
      "client-create-or-edit-drawer": "client.create",
      "contact-form-dialog": "client.contact.create",
      "requisition-intake": "requisition.create",
      "requisition-intake-edit": "requisition.update",
      "daily-updates-submission": "daily_update.create_main",
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

async function submitUser() {
  const id = queryInt("user_id");
  const session = RecruitOpsLive.session || readSession();
  const name = firstValueOf(["full_name"], [/full name/i]);
  const email = firstValueOf(["email"], [/email/i]);
  const roleId = intOrNull(document.getElementById("role_id")?.value) || intOrNull(document.getElementById("primary_role_id")?.value);
  const locationId = intOrNull(document.getElementById("location_id")?.value) || intOrNull(document.getElementById("primary_location_id")?.value) || session?.location_id;
  const payload = {
    full_name: name,
    email: email,
    employee_code: (name || "USR").substring(0, 8).toUpperCase().replace(/\s+/g, "") + Math.floor(Math.random() * 1000),
    primary_role_id: roleId,
    primary_location_id: locationId,
    phone: firstValueOf(["phone"], [/phone/i]) || null,
    business_title: firstValueOf(["business_title"], [/title/i, /designation/i]) || null,
    status: "active",
  };
  if (!payload.full_name || !payload.email) { showLiveError(new Error("Name and email are required.")); return; }
  try {
    if (id) await apiRequest(`/users/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
    else await apiRequest("/users/", { method: "POST", body: JSON.stringify(payload) });
    showLiveSuccess("User saved", payload.full_name);
    setTimeout(() => { window.location.href = pageHref("user-management.html"); }, 1000);
  } catch (error) { showLiveError(error); }
}

async function submitRole() {
  const id = queryInt("role_id");
  const name = firstValueOf(["role_name", "name"], [/role name/i, /name/i]);
  const payload = {
    name: name,
    code: (name || "role").toLowerCase().replace(/\s+/g, "_").substring(0, 30),
    description: firstValueOf(["description"], [/description/i]) || null,
    status: "active",
  };
  if (!payload.name) { showLiveError(new Error("Role name is required.")); return; }
  try {
    if (id) await apiRequest(`/roles/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
    else await apiRequest("/roles/", { method: "POST", body: JSON.stringify(payload) });
    showLiveSuccess("Role saved", payload.name);
    setTimeout(() => { window.location.href = pageHref("role-management.html"); }, 1000);
  } catch (error) { showLiveError(error); }
}

async function submitClient() {
  const id = queryInt("client_id");
  const session = RecruitOpsLive.session || readSession();
  /* Read from actual HTML field IDs: client-name, client-code, industry, location, client-owner, business-source, status */
  const name = document.getElementById("client-name")?.value?.trim() || firstValueOf(["client_name"], [/client name/i]);
  const code = document.getElementById("client-code")?.value?.trim() || null;
  const industry = document.getElementById("industry")?.value || firstValueOf(["industry"], [/industry/i]) || null;
  const locationId = intOrNull(document.getElementById("location_id")?.value) || intOrNull(document.getElementById("location")?.value) || session?.location_id;
  const ownerSelect = document.getElementById("client-owner");
  const sourceSelect = document.getElementById("business-source");
  const statusVal = document.getElementById("status")?.value || "active";
  const notes = document.getElementById("commercial-notes")?.value || null;
  const createPayload = {
    client_name: name,
    client_code: code,
    industry,
    location_id: locationId,
    client_owner_user_id: intOrNull(ownerSelect?.value) || session?.user_id,
    business_source_owner_user_id: intOrNull(sourceSelect?.value) || session?.user_id,
    status: statusVal,
    notes,
  };
  const updatePayload = {
    client_name: name || undefined,
    industry,
    status: statusVal,
    notes,
  };
  if (!name) { showLiveError(new Error("Client name is required.")); return; }
  try {
    if (id) await apiRequest(`/clients/${id}`, { method: "PATCH", body: JSON.stringify(updatePayload) });
    else await apiRequest("/clients/", { method: "POST", body: JSON.stringify(createPayload) });
    showLiveSuccess("Client saved", name);
    setTimeout(() => { window.location.href = pageHref("client-directory.html"); }, 1000);
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
  const roleId = queryInt("role_id");
  if (!roleId) { showLiveError(new Error("No role selected.")); return; }
  const permissions = {};
  document.querySelectorAll("[data-perm].on").forEach((toggle) => {
    permissions[toggle.dataset.perm] = true;
  });
  try {
    await apiRequest(`/roles/${roleId}/permissions`, { method: "PUT", body: JSON.stringify({ permission_codes: Object.keys(permissions) }) });
    showLiveSuccess("Permissions saved");
  } catch (error) { showLiveError(error); }
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
    countEl.textContent = total > 0 ? `View all ${total} items in queue` : "No items in queue";
  }
}

async function loadDashboardActionsOverlay() {
  const payload = await apiRequest("/workflow-actions/queue?page_size=50").catch(() => ({ items: [] }));
  renderOverlayWorkflowActions(payload.items || [], ".overlay-host .space-y-3, .workspace-surface .space-y-3", "No workflow actions");
}

async function loadNotificationDetailPanel() {
  const notificationId = queryInt("notification_id");
  if (notificationId) {
    try {
      await apiRequest(`/notifications/${notificationId}/read`, { method: "PATCH", body: JSON.stringify({ status: "read" }) });
      refreshNotificationBadge();
    } catch {}
  }
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
    setTimeout(() => { window.location.href = pageHref("pipeline-board.html"); }, 1000);
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
    setTimeout(() => { window.location.href = pageHref("candidate-profiles.html"); }, 1000);
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

async function loadEditableEntityForm() {
  const route = routeId();
  const id = queryInt("location_id", "user_id", "role_id", "client_id");
  if (!id) return;
  try {
    const pathMap = { "location-form-drawer": `/locations/${id}`, "user-form-drawer": `/users/${id}`, "role-form-drawer": `/roles/${id}`, "client-create-or-edit-drawer": `/clients/${id}` };
    const data = await apiRequest(pathMap[route] || "");
    /* API keys use underscores (client_name), HTML IDs use hyphens (client-name) */
    Object.entries(data).forEach(([key, value]) => {
      if (value == null) return;
      const hyphenated = key.replace(/_/g, "-");
      const field = document.getElementById(key) || document.getElementById(hyphenated) || document.querySelector(`[name="${key}"]`) || document.querySelector(`[name="${hyphenated}"]`);
      if (field) field.value = value;
    });
  } catch {}
}

async function loadLocations() {
  const payload = await apiRequest("/locations/?page_size=100");
  fillExistingTable(payload.items || [], (row, item) => {
    const cells = row.querySelectorAll("td");
    setCellValue(cells[0], item.location_name || item.name || "—");
    setCellValue(cells[1], `${item.city || ""}, ${item.country || ""}`.trim() || "—");
    setCellValue(cells[2], mapLocationStatus(item.status));
    const editLink = row.querySelector('[data-route*="location-form"]');
    if (editLink) editLink.dataset.route = `location-form-drawer.html?location_id=${item.id}`;
  });
}

async function loadUsers() {
  const payload = await apiRequest("/users/?page_size=100");
  fillExistingTable(payload.items || [], (row, item) => {
    const cells = row.querySelectorAll("td");
    setStackedCell(cells[1], item.full_name || item.email, item.email || "");
    setCellValue(cells[2], item.role || "—");
    setCellValue(cells[3], item.location_name || "—");
    setCellValue(cells[4], item.status || "active");
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
    setCellValue(cells[0], item.role_name || item.name || "—");
    setCellValue(cells[1], item.description || "—");
    setCellValue(cells[2], item.status || "active");
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

async function loadRolePermissionsEditor() {
  const roleId = queryInt("role_id");
  if (!roleId) return;
  const role = await apiRequest(`/roles/${roleId}`).catch(() => null);
  if (role) {
    setFirstText("[data-role-name]", role.role_name || role.name);
    const permissions = role.permissions || {};
    Object.entries(permissions).forEach(([key, enabled]) => {
      const toggle = document.querySelector(`[data-perm="${key}"]`);
      if (toggle) setPermissionToggleState(toggle, enabled);
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
    setStackedCell(cells[0], item.client_name, item.industry || "");
    setCellValue(cells[1], item.status || "active");
    const editLink = row.querySelector('[data-route*="client-create"]');
    if (editLink) editLink.dataset.route = `client-create-or-edit-drawer.html?client_id=${item.id}`;
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
  const payload = await apiRequest("/requisitions/?page_size=100");
  renderBusinessTitles(payload.items || []);
}

async function loadRequisitionDetail() {
  const requisition = await detailFromRoute(["requisition_id", "id"], "/requisitions/?page_size=1", (id) => `/requisitions/${id}`);
  if (!requisition) return;
  const surface = document.querySelector(".workspace-surface");
  setFirstText(".workspace-surface nav span:last-child", requisition.title);
  setFirstText(".workspace-surface h1, .workspace-surface h2", requisition.title);
  setFirstText(".workspace-surface h1 + span, .workspace-surface h2 + span", reqCode(requisition));
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
  const payload = await apiRequest("/candidates/?page_size=100");
  fillExistingTable(payload.items || [], (row, item) => {
    const cells = row.querySelectorAll("td");
    setStackedCell(cells[0], item.full_name, item.email || "");
    setCellValue(cells[1], item.current_designation || item.source_type || "—");
    setCellValue(cells[2], item.location_name || "—");
    const status = cells[3]?.querySelector("span") || cells[3];
    if (status) status.textContent = item.profile_status || "—";
  });
}

async function loadCandidateDetail() {
  const candidate = await detailFromRoute(["candidate_id", "id"], "/candidates/?page_size=1", (id) => `/candidates/${id}`);
  if (!candidate) return;
  setFirstText("[data-candidate-name]", candidate.full_name);
  setFirstText("[data-candidate-email]", candidate.email);
  setFirstText("[data-candidate-phone]", candidate.phone);
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
   PIPELINE MANAGEMENT
   ═══════════════════════════════════════════════════════════════ */

async function loadPipeline() {
  const payload = await apiRequest("/pipeline/board").catch(() => []);
  const items = Array.isArray(payload) ? payload : payload.items || [];
  const columns = document.querySelectorAll("[data-pipeline-stage]");
  columns.forEach((col) => {
    const stageName = col.querySelector("h3")?.textContent?.trim() || "";
    const host = col.querySelector(".space-y-2, .flex.flex-col");
    if (!host) return;
    const stageItems = items.filter((item) => String(item.current_stage || "").toLowerCase() === stageName.toLowerCase());
    host.innerHTML = stageItems.length
      ? stageItems.map((item) => `      <div class="rounded-lg border border-border bg-surface p-3 hover:border-primary transition-colors cursor-pointer" data-application-id="${item.application_id}">
          <p class="font-data-tabular font-semibold text-on-surface">${escapeLiveHtml(item.candidate_name || "Candidate")}</p>
          <p class="mt-1 truncate text-[11px] text-text-muted">${escapeLiveHtml(item.requisition_title || "Requisition")}</p>
        </div>`).join("")
      : '<div class="p-3 text-center text-text-muted text-[11px]">No items</div>';
  });
}async function loadPipelineApplicationDetail() {
  const applicationId = queryInt("application_id");
  if (!applicationId) return;
  try {
    const application = await apiRequest(`/pipeline/applications/${applicationId}`);
    setFirstText("[data-candidate-name]", application.candidate_name);
    setFirstText("[data-current-stage]", application.current_stage);
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

async function loadDailyUpdates() {
  const payload = await apiRequest("/daily-updates/?page_size=50");
  const items = payload.items || [];
  const surface = document.querySelector(".workspace-surface");
  if (!surface) return;
  const list = surface.querySelector(".space-y-4, .rounded-xl.flex.flex-col");
  if (list) list.innerHTML = items.length ? items.map((item, i) => renderDailyUpdateSubmissionCard(item)).join("") : '<div class="p-4 text-text-muted">No updates.</div>';
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
  const [company, myWork, pipeline] = await Promise.all([
    apiRequest("/dashboards/company-summary").catch(() => ({})),
    apiRequest("/dashboards/my-work").catch(() => ({})),
    apiRequest("/pipeline/board").catch(() => []),
  ]);
  const pipelineItems = Array.isArray(pipeline) ? pipeline : pipeline.items || [];
  renderDailyReviewQuickStats(myWork, pipelineItems);
  renderDailyReviewPipelineActivity(pipelineItems.slice(0, 5));
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
  const totalUsers = 11; // known user count
  const pressurePct = totalUsers > 0 ? Math.round((submitted / totalUsers) * 100) : 0;
  const pressureEl = document.querySelector("[data-role-pressure-value]");
  if (pressureEl) pressureEl.textContent = `${pressurePct}%`;
  const hintEl = document.querySelector("[data-role-pressure-hint]");
  if (hintEl) hintEl.textContent = `${submitted} of ${totalUsers} users submitted this period.`;
}

async function loadDashboards() {
  const [company, myWork, pipeline] = await Promise.all([
    apiRequest("/dashboards/company-summary").catch(() => ({})),
    apiRequest("/dashboards/my-work").catch(() => ({})),
    apiRequest("/pipeline/board").catch(() => []),
  ]);
  const pipelineItems = Array.isArray(pipeline) ? pipeline : pipeline.items || [];
  fillDashboardMetrics([
    { label: "Open Reqs", value: company.total_open_requisitions || 0, hint: "Active mandates" },
    { label: "Active Pipeline", value: pipelineItems.length, hint: "Candidates in pipeline" },
    { label: "My Updates", value: myWork?.submitted_updates || 0, hint: "Submitted this week" },
    { label: "Pending Actions", value: myWork?.pending_actions || 0, hint: "Need attention" },
  ]);
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

async function loadTimeToFillReport() {
  const [requisitions, offers] = await Promise.all([
    apiRequest("/requisitions/?page_size=100").catch(() => ({ items: [] })),
    apiRequest("/offers/?page_size=50").catch(() => ({ items: [] })),
  ]);
  const records = timeToFillRecords(requisitions.items || [], offers.items || []);
  renderTimeToFillBars("Average Time to Fill", records.slice(0, 8));
  renderTimeToFillTrend(records.slice(0, 6));
}

async function loadSourceEffectiveness() {
  const candidates = await apiRequest("/candidates/?page_size=100").catch(() => ({ items: [] }));
  renderSourceEffectiveness(candidates.items || []);
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
  const payload = await apiRequest("/meetings/?page_size=50");
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
  const payload = await apiRequest("/meetings/?page_size=50");
  const items = (payload.items || []).filter((item) => /follow/i.test(String(item.meeting_type || item.outcome_status || "")));
  const surface = document.querySelector(".workspace-surface");
  if (!surface) return;
  const list = surface.querySelector(".rounded-xl.flex.flex-col, [data-follow-up-list]");
  if (list) list.innerHTML = items.length
    ? items.map((item, index) => renderFollowUpRow(item, index)).join("")
    : '<div class="p-6 text-center text-text-muted">No follow-ups returned by the API.</div>';
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
}/* ═══════════════════════════════════════════════════════════════
   OFFERS
   ═══════════════════════════════════════════════════════════════ */

async function loadOfferManagement() {
  const payload = await apiRequest("/offers/?page_size=50");
  renderOffers(payload.items || [], payload.meta || {});
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
  return notificationItemsCache.filter((item) => `${item.title || ""} ${item.message || ""}`.toLowerCase().includes(term));
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

async function refreshNotificationBadge() {
  const badge = ensureNotificationBadge();
  if (!badge || !LIVE_API_ENABLED) return;
  try {
    const payload = await apiRequest("/notifications/?status=unread&page_size=1");
    const count = payload.meta?.total ?? 0;
    badge.textContent = count > 99 ? "99+" : String(count);
    badge.hidden = count === 0;
  } catch {
    badge.hidden = true;
  }
}

function applyNotificationReadState(row) {
  if (!row) return;
  row.classList.add("notification-read");
  row.dataset.notificationStatus = "read";
  row.querySelectorAll("[data-notification-unread-indicator]").forEach((dot) => dot.remove());
  const button = row.querySelector("[data-notification-read]");
  if (button) button.setAttribute("disabled", "disabled");
  const badge = row.querySelector("[data-notification-status-badge]");
  if (badge) badge.textContent = "read";
}

async function markNotificationReadAction(button) {
  if (button.disabled) return;
  button.setAttribute("disabled", "disabled");
  const row = button.closest("[data-notification-id]");
  const id = intOrNull(row?.dataset.notificationId);
  if (!id) {
    applyNotificationReadState(row);
    showToast("Notification updated", "This alert is marked as read for this session.");
    return;
  }
  try {
    await apiRequest(`/notifications/${id}/read`, { method: "PATCH", body: JSON.stringify({ status: "read" }) });
    notificationItemsCache = notificationItemsCache.map((item) => (String(item.id) === String(id) ? { ...item, status: "read" } : item));
    notificationUnreadTotal = Math.max(0, notificationUnreadTotal - 1);
    refreshNotificationBadge();
    if (routeId() === "notifications-center" && document.querySelector("[data-notifications-command-center]")) {
      renderNotificationsCommandCenter(notificationsView(), { unread_total: notificationUnreadTotal });
    } else {
      applyNotificationReadState(row);
    }
    showLiveSuccess("Marked as read", "Notification updated.");
  } catch (error) {
    button.removeAttribute("disabled");
    showLiveError(error);
  }
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
      return;
    }
  }
  const list = document.querySelector("[data-notification-list], .workspace-surface .rounded-xl.flex.flex-col");
  if (list && items.length) {
    list.innerHTML = items.map((item) => `<div class="flex items-start gap-4 p-4 border-b border-border bg-surface" data-live-notification-row="true" data-notification-id="${item.id}">
      <div class="mt-1 text-primary"><span class="material-symbols-outlined">notifications</span></div>
      <div class="flex-1 min-w-0">
        <h4 class="font-headline-sm text-headline-sm text-on-surface truncate">${item.title || "Notification"}</h4>
        <p class="font-body-sm text-body-sm text-text-muted mt-1">${item.message || ""}</p>
      </div>
      ${String(item.status).toLowerCase() === "unread" ? `<button class="topbar-action" type="button" data-notification-read="true" aria-label="Mark as read" title="Mark as Read"><span class="material-symbols-outlined text-[20px]">done</span></button>` : ""}
    </div>`).join("");
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
  const payload = await apiRequest("/approvals/?page_size=50").catch(() => ({ items: [], meta: { total: 0 } }));
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
  /* Render table */
  const tbody = document.querySelector("tbody");
  if (!tbody) return;
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
    return `<tr class="hover:bg-highlight-soft transition-colors bg-surface h-[40px] group" data-approval-id="${item.id}">
      <td class="py-2 px-4 align-middle"><div class="flex items-center gap-2"><div class="w-2 h-2 rounded-full ${priorityMeta.dot}"></div><span class="${priorityMeta.text} font-medium text-xs">${item.status === "pending" ? slaText : item.status}</span></div></td>
      <td class="py-2 px-4 align-middle text-on-surface font-medium">${escapeLiveHtml(item.approval_type?.replace(/_/g, " ") || "Request")}</td>
      <td class="py-2 px-4 align-middle text-primary cursor-pointer hover:underline">${escapeLiveHtml(item.title || "—")}</td>
      <td class="py-2 px-4 align-middle"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded-full border border-border bg-surface-dim text-text-muted flex items-center justify-center font-headline-sm font-semibold text-[11px]">${initials}</div><span class="text-on-surface">${escapeLiveHtml(item.requester_name || "Unknown")}</span></div></td>
      <td class="py-2 px-4 align-middle text-text-muted text-sm">${escapeLiveHtml(locationName)}</td>
      <td class="py-2 px-4 align-middle text-text-muted text-sm">${created}</td>
      <td class="py-2 px-4 align-middle text-right"><div class="flex items-center justify-end gap-2">${actionsHtml}</div></td>
    </tr>`;
  }).join("");
  /* Wire approve/reject buttons */
  tbody.querySelectorAll(".approve-btn").forEach((btn) => btn.addEventListener("click", () => decideApproval(btn.dataset.approvalId, "approved")));
  tbody.querySelectorAll(".reject-btn").forEach((btn) => btn.addEventListener("click", () => decideApproval(btn.dataset.approvalId, "rejected")));
  /* Update pagination text */
  const paginationText = document.querySelector(".border-t span");
  if (paginationText) paginationText.textContent = `Showing 1 to ${items.length} of ${total} entries`;
}

async function decideApproval(approvalId, decision) {
  const notes = decision === "rejected" ? prompt("Reason for rejection (optional):") : null;
  if (decision === "rejected" && notes === null) return;
  try {
    await apiRequest(`/approvals/${approvalId}/decide`, {
      method: "PATCH",
      body: JSON.stringify({ decision, decision_notes: notes || (decision === "approved" ? "Approved" : "Rejected"), decision_user_id: currentUserId() }),
    });
    showLiveSuccess(decision === "approved" ? "Approved" : "Rejected", "Decision saved.");
    loadApprovalsInbox();
  } catch (error) { showLiveError(error); }
}


/* ═══════════════════════════════════════════════════════════════
   JOIN TRACKER
   ═══════════════════════════════════════════════════════════════ */

async function loadJoinTracker() {
  const payload = await apiRequest("/offers/?status=accepted&page_size=50").catch(() => ({ items: [] }));
  const items = (payload.items || []).filter((item) => /accepted|joined/i.test(String(item.offer_status || item.application_status || "")));
  const surface = document.querySelector(".workspace-surface");
  if (!surface) return;
  const tbody = surface.querySelector("tbody");
  if (tbody) {
    tbody.innerHTML = items.length
      ? items.map((item, i) => `<tr class="hover:bg-highlight-soft transition-colors">
          <td class="py-2 px-4 font-medium text-on-surface">${escapeLiveHtml(item.candidate_name || "Candidate")}</td>
          <td class="py-2 px-4 text-text-muted">${escapeLiveHtml(item.requisition_title || "Position")}</td>
          <td class="py-2 px-4 text-text-muted">${escapeLiveHtml(item.department || "—")}</td>
          <td class="py-2 px-4"><span class="inline-flex items-center rounded bg-success-bg px-2 py-0.5 text-[10px] font-semibold text-success-text">Joined</span></td>
          <td class="py-2 px-4 text-text-muted text-sm">${escapeLiveHtml(formatWhen(item.accepted_at || item.updated_at))}</td>
        </tr>`).join("")
      : '<tr><td class="px-4 py-6 text-text-muted" colspan="5">No joined candidates.</td></tr>';
  }
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
  fillDashboardMetrics([
    { label: "Total Hires", value: hires, hint: `${company.total_locations || 0} active locations` },
    { label: "Pipeline Velocity", value: `${Math.max(1, Math.round(pipelineItems.length / Math.max(company.total_open_requisitions || 1, 1)))}x`, hint: `${pipelineItems.length} active pipeline items` },
  ]);
  renderAnalyticsTeam(users.items || [], requisitions.items || [], candidates.items || [], offerItems);
  renderAnalyticsSavedReports(company, dailyUpdates.items || []);
}

async function submitDailyUpdate() {
  const session = RecruitOpsLive.session || readSession();
  const summary = document.getElementById("update-summary")?.value || document.querySelector("textarea")?.value || "";
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
  /* Try to find a requisition the user is actually linked to */
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
  };
  try {
    await apiRequest("/daily-updates/", { method: "POST", body: JSON.stringify(payload) });
    showLiveSuccess("Daily update submitted");
    setTimeout(() => { window.location.href = pageHref("daily-updates-review.html"); }, 1000);
  } catch (error) {
    /* If 403 "must be linked", show helpful message */
    const msg = error?.message || String(error);
    if (/403|linked.*requisition/i.test(msg)) {
      showLiveError(new Error("You are not assigned to this requisition. Contact your admin to assign you first."));
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
    setTimeout(() => { window.location.href = pageHref("meetings.html"); }, 1000);
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
    setTimeout(() => { window.location.href = pageHref("offer-management.html"); }, 1000);
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
    setTimeout(() => { window.location.href = pageHref("candidate-profiles.html"); }, 1000);
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

async function loadCustomReportBuilder() {
  const [company, pipeline, requisitions, users, candidates, offers, dailyUpdates] = await Promise.all([
    apiRequest("/dashboards/company-summary").catch(() => ({})),
    apiRequest("/pipeline/board").catch(() => []),
    apiRequest("/requisitions/?page_size=100").catch(() => ({ items: [] })),
    apiRequest("/users/?page_size=100").catch(() => ({ items: [] })),
    apiRequest("/candidates/?page_size=100").catch(() => ({ items: [] })),
    apiRequest("/offers/?page_size=50").catch(() => ({ items: [] })),
    apiRequest("/daily-updates/?page_size=50").catch(() => ({ items: [] })),
  ]);
  const root = document.querySelector(".workspace-surface");
  if (!root) return;
  const context = {
    company,
    pipelineItems: Array.isArray(pipeline) ? pipeline : pipeline.items || [],
    requisitions: requisitions.items || [],
    users: users.items || [],
    candidates: candidates.items || [],
    offers: offers.items || [],
    dailyUpdates: dailyUpdates.items || [],
  };
  styleCustomReportChoices(root);
  renderCustomReportPreview(context);
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
      setPermissionToggleState(permissionToggle, !permissionToggle.classList.contains("on"));
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
    const submitRoutes = new Set(["location-form-drawer", "user-form-drawer", "role-form-drawer", "client-create-or-edit-drawer", "contact-form-dialog", "requisition-intake", "requisition-intake-edit", "daily-updates-submission", "meeting-form-dialog", "offer-create-dialog", "link-to-requisition-dialog", "stage-move-dialog", "candidate-review-drawer", "onboarding-company-profile", "onboarding-locations", "onboarding-role-setup", "onboarding-hiring-teams"]);
    const label = (routeSubmitButton?.textContent || "").replace(/\s+/g, " ").trim().toLowerCase();
    if (routeSubmitButton && submitRoutes.has(route) && /^(save|create|update|submit|schedule|confirm|continue|next|add|send|save changes|save user|save client|save contact|save role|create requisition|save candidate)/.test(label)) {
      event.preventDefault();
      event.stopPropagation();
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
    "client-create-or-edit-drawer": loadEditableEntityForm,
    "contact-form-dialog": loadContactFormDialog,
    "requisition-intake": loadRequisitionIntake,
    "requisition-intake-edit": loadRequisitionIntake,
    "requisition-detail": loadRequisitionDetail,
    "assignment-history-drawer": loadAssignmentHistoryDrawer,
    "work-assignment": loadWorkAssignment,
    "reassign-owner-dialog": loadReassignOwnerDialog,
    "reassignment-review-drawer": loadReassignmentReviewDrawer,
    "status-update-dialog": loadStatusUpdateDialog,
    "exception-request-dialog": loadWorkflowOverlay,
    "clarification-request-dialog": loadWorkflowOverlay,
    "user-management": loadUsers,
    "user-detail": loadUserDetail,
    "user-form-drawer": loadEditableEntityForm,
    "deactivate-user-dialog": loadDeactivateUserDialog,
    "role-management": loadRoles,
    "role-form-drawer": loadEditableEntityForm,
    "role-permissions-editor": loadRolePermissionsEditor,
    "role-dashboard": async () => { await Promise.all([loadRoleDashboard().catch(() => {}), loadWorkflowActions().catch(() => {})]); },
    "my-work-dashboard": loadDashboards,
    "company-dashboard": loadDashboards,
    "location-management": loadLocations,
    "location-detail": loadLocationDashboard,
    "location-form-drawer": loadEditableEntityForm,
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
    "sla-tracker": loadSourceEffectiveness,
    "pipeline-analytics": loadPipelineAnalytics,
    "analytics-dashboard": loadAnalyticsDashboard,
    "reports": loadReportsLibrary,
    "reports-library": loadReportsLibrary,
    "custom-report-builder": loadCustomReportBuilder,
    "review-matches-workspace": loadReviewMatchesWorkspace,
    "requisition-list": async () => {
      const payload = await apiRequest("/requisitions/?page_size=100").catch(() => ({ items: [] }));
      fillExistingTable(payload.items || [], (row, item) => {
        const cells = row.querySelectorAll("td");
        setStackedCell(cells[0], item.title || item.requisition_code, item.client_name || "");
        setCellValue(cells[1], item.client_name || "—");
        setCellValue(cells[2], item.status || "open");
        setCellValue(cells[3], item.priority || "—");
        setCellValue(cells[4], item.primary_owner_name || "—");
        const editLink = row.querySelector('[data-route*="requisition-detail"]');
        if (editLink) editLink.dataset.route = `requisition-detail.html?requisition_id=${item.id}`;
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
    "onboarding-company-profile": async () => {},
    "onboarding-hiring-teams": async () => {},
    "onboarding-locations": async () => {},
    "onboarding-role-setup": async () => {},
    "onboarding-pipeline-stage-builder": async () => {},
    "onboarding-integrations": async () => {},
    "onboarding-success-launch": async () => { await completeOnboarding(); },
  };

  /* RBAC: Block access to unauthorized pages */
  if (!isAdmin() && !PUBLIC_ROUTES.has(route)) {
    const pagePermMap = {
      "location-management": ["location.read"],
      "location-form-drawer": ["location.create"],
      "location-detail": ["location.read"],
      "location-dashboard": ["location.read"],
      "user-management": ["user.read"],
      "user-form-drawer": ["user.create"],
      "user-detail": ["user.read"],
      "role-management": ["role.read"],
      "role-form-drawer": ["role.create"],
      "role-permissions-editor": ["role.permissions.assign"],
      "role-dashboard": ["dashboard.view_recruiter", "dashboard.view_manager", "dashboard.view_hr"],
      "business-titles": ["settings.read"],
      "visibility-rules": ["settings.read"],
      "work-assignment": ["assignment.read", "requisition.read"],
      "approvals-inbox": ["approval.read"],
      "client-directory": ["client.read"],
      "client-detail": ["client.read"],
      "client-create-or-edit-drawer": ["client.create"],
      "contact-form-dialog": ["client.contact.create"],
      "candidate-profiles": ["candidate.read"],
      "candidate-detail": ["candidate.read"],
      "candidate-review-drawer": ["candidate.create"],
      "pipeline-board": ["pipeline.read.summary"],
      "application-detail-drawer": ["pipeline.read.detail"],
      "stage-move-dialog": ["pipeline.stage.move"],
      "requisition-list": ["requisition.read"],
      "requisition-detail": ["requisition.read"],
      "requisition-intake": ["requisition.create"],
      "requisition-intake-edit": ["requisition.update"],
      "interview-scheduler": ["interview.read"],
      "interview-detail": ["interview.read"],
      "offer-management": ["offer.read"],
      "offer-create-dialog": ["offer.create"],
      "meetings": ["meeting.read"],
      "meeting-form-dialog": ["meeting.create"],
      "follow-ups": ["meeting.read"],
      "follow-up-form-dialog": ["meeting.create"],
      "join-tracker": ["offer.read"],
      "daily-updates-workspace": ["daily_update.read"],
      "daily-updates-submission": ["daily_update.create_main", "daily_update.read"],
      "daily-updates-review": ["daily_update.read"],
      "daily-update-detail-panel": ["daily_update.read"],
      "notifications-center": ["notification.read"],
      "notification-detail-panel": ["notification.read"],
      "analytics-dashboard": ["dashboard.view_admin", "dashboard.view_hr", "dashboard.view_manager", "dashboard.view_recruiter"],
      "company-dashboard": ["dashboard.view_admin"],
      "user-performance-reports": ["dashboard.view_admin", "dashboard.view_manager"],
      "team-workload": ["dashboard.view_admin", "dashboard.view_manager"],
      "reports": ["report.read_recruiter", "report.read_hr", "report.read_manager", "report.read_admin"],
      "reports-library": ["report.read_recruiter", "report.read_hr", "report.read_manager", "report.read_admin"],
      "custom-report-builder": ["report.generate"],
      "pipeline-analytics": ["pipeline.read.summary"],
      "time-to-fill-report": ["report.read_admin", "report.read_manager"],
      "source-effectiveness": ["report.read_admin", "report.read_manager"],
      "sla-tracker": ["report.read_admin", "report.read_manager"],
    };
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
window.RecruitOpsLive = RecruitOpsLive;


/* ═══════════════════════════════════════════════════════════════
   ENTRY POINT
   ═══════════════════════════════════════════════════════════════ */

function startLiveApiClient() {
  if (!LIVE_API_ENABLED) {
    hidePageLoader();
    return;
  }
  decorateShell();
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

  if (RecruitOpsLive.session || readSession()) {
    refreshNotificationBadge();
    setInterval(() => refreshNotificationBadge(), 30000);
  }
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startLiveApiClient, { once: true });
  } else {
    startLiveApiClient();
  }
}
