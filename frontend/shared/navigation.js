/* navigation.js — category-driven navigation & home rendering.
   Consumes window.NAV_CONFIG (navigation.config.js) and the existing
   session helpers from api-client.js (readSession, userPermissions,
   isAdmin). Renders: sidebar + mobile nav (default-deny), home grid,
   global live search, and role metrics. Pure DOM + events; no fetch
   logic beyond metric loaders via RecruitOpsLive helpers. */

function navPermissionSet() {
  /* Default-deny is evaluated against the user's RESOLVED permission
     codes (session.permissions from /permissions/me). The admin bypass
     (isAdmin) is intentionally NOT used here: PRD §3.1 — admins see the
     control plane they are seeded with, not the full catalog. Deep-link
     page gating (NAV_PAGE_PERMISSIONS via api-client) is unchanged. */
  const session = (typeof readSession === "function" && readSession()) || {};
  const codes = new Set((session.permissions || []).map((code) => String(code)));
  if (session.role_code) codes.add(`role:${session.role_code}`);
  return codes;
}

function navHasPermission(codes, entry) {
  const required = entry.permissions || [];
  if (!required.length) return true; /* account chrome */
  return required.some((code) => codes.has(code));
}

function navEntriesFor(codes, { sidebar = true, home = true } = {}) {
  const config = window.NAV_CONFIG;
  const seen = new Set();
  /* Per-branch feature flags: branches with offer tracking disabled
     (sourcing-only tenants) never see offer surfaces in nav, home, or
     search — the deep-link gate below still protects the pages. */
  const offersOn = typeof branchOffersEnabled === "function" ? branchOffersEnabled() : true;
  const offerPageIds = new Set(["offer-management", "offer-create-dialog", "join-tracker"]);
  return config.entries.filter((entry) => {
    if (sidebar && entry.showInSidebar === false) return false;
    if (home && entry.showInHome === false) return false;
    if (seen.has(entry.id)) return false;
    seen.add(entry.id);
    if (!offersOn && offerPageIds.has(entry.id)) return false;
    return navHasPermission(codes, entry);
  });
}

function navCategory(key) {
  return window.NAV_CONFIG.categories.find((category) => category.key === key);
}

/* ── Sidebar & mobile nav ──────────────────────────────────────── */

/* PRD §3.1: default Admin navigation = control plane + oversight only.
   The sidebar never dumps the full catalog — even when the admin role
   holds extra execution grants (seeded or explicit), only My Work is
   added. Deep links remain permission-gated as before. */
const ADMIN_SIDEBAR_BASE = new Set([
  "role-dashboard", "company-dashboard", "location-dashboard",
  "notifications-center", "approvals-inbox",
  "user-management", "location-management", "role-management", "role-permissions-editor",
  "business-titles", "visibility-rules", "work-assignment", "portal-accounts",
  "analytics-dashboard", "reports", "custom-report-builder", "pipeline-analytics",
  "time-to-fill-report", "source-effectiveness", "sla-tracker",
  "user-performance-reports", "team-workload",
  "my-profile", "support-workspace",
]);
const ADMIN_EXECUTION_GRANT_CODES = ["client.read", "requisition.read", "candidate.read", "daily_update.read"];

function navShapeEntriesForSidebar(entries, codes) {
  const session = (typeof readSession === "function" && readSession()) || {};
  if (session.role_code !== "admin") return entries;
  const allowed = new Set(ADMIN_SIDEBAR_BASE);
  if (ADMIN_EXECUTION_GRANT_CODES.some((code) => codes.has(code))) {
    allowed.add("my-work-dashboard"); /* PRD §3.1: My Work only with an execution grant */
  }
  return entries.filter((entry) => allowed.has(entry.id));
}

function navSidebarHtml(codes, { activeFile = "", compact = false } = {}) {
  const config = window.NAV_CONFIG;
  const entries = navShapeEntriesForSidebar(navEntriesFor(codes, { sidebar: true, home: false }), codes);
  const groups = config.categories
    .map((category) => ({
      category,
      items: entries.filter((entry) => entry.category === category.key),
    }))
    .filter((group) => group.items.length > 0);

  const link = (entry) => {
    const active = activeFile && entry.file === activeFile;
    return `<a href="${entry.file}" class="nav-link${active ? " is-active" : ""}" title="${entry.label}"${active ? ' aria-current="page"' : ""}><span class="material-symbols-outlined shrink-0"${active ? ' style="font-variation-settings:\'FILL\' 1;"' : ""}>${entry.icon}</span><span class="sidebar-label">${entry.label}</span></a>`;
  };

  const body = groups
    .map(
      ({ category, items }) => `
      <details class="nav-group"${compact ? "" : " open"} data-nav-group="${category.key}">
        <summary class="nav-group-toggle">
          <span class="material-symbols-outlined nav-group-icon">${category.icon}</span>
          <span class="nav-group-label">${category.label}</span>
          <span class="material-symbols-outlined nav-group-chevron">expand_more</span>
        </summary>
        <div class="nav-sub">${items.map(link).join("\n")}</div>
      </details>`,
    )
    .join("\n");

  return `${body}
  <a href="login.html?loggedOut=true" class="sidebar-logout" title="Log out of RecruitOps" data-logout-link="true"><span class="material-symbols-outlined">logout</span><span class="sidebar-label">Logout</span></a>`;
}

function buildSidebarNav() {
  const root = document.querySelector("[data-nav-root]");
  if (!root || typeof navPermissionSet !== "function") return;
  const codes = navPermissionSet();
  const activeFile = (window.location.pathname.split("/").pop() || "").replace(/\?.*/, "");
  root.innerHTML = navSidebarHtml(codes, { activeFile });
  if (typeof setupSidebarNav === "function") setupSidebarNav();
  if (typeof hydrateNavGroups === "function") hydrateNavGroups(root);
}

function buildMobileNav() {
  const root = document.querySelector("[data-mobile-nav-root]");
  if (!root) return;
  const codes = navPermissionSet();
  const activeFile = (window.location.pathname.split("/").pop() || "").replace(/\?.*/, "");
  root.innerHTML = `<div class="space-y-4">${navSidebarHtml(codes, { activeFile, compact: true })}</div>`;
}

/* ── Home view: metrics + categorized feature grid ────────────── */

function navFeatureCardHtml(entry) {
  return `<a class="nav-feature-card group flex items-start gap-3 rounded-xl border border-border bg-surface p-4 transition-colors hover:bg-highlight-soft" href="${entry.file}" data-home-card data-entry-id="${entry.id}">
    <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-secondary-container text-on-secondary-container"><span class="material-symbols-outlined">${entry.icon}</span></span>
    <span class="min-w-0">
      <span class="block font-data-tabular text-[13px] font-semibold text-on-surface">${entry.label}</span>
      <span class="mt-0.5 block font-body-sm text-body-sm text-text-muted">${entry.description}</span>
    </span>
  </a>`;
}

function buildHomeGrid() {
  const root = document.querySelector("[data-home-grid]");
  if (!root) return false;
  const codes = navPermissionSet();
  const entries = navEntriesFor(codes, { sidebar: false, home: true }).filter((entry) => entry.category !== "account");
  const config = window.NAV_CONFIG;
  root.innerHTML = config.categories
    .map((category) => {
      const items = entries.filter((entry) => entry.category === category.key);
      if (!items.length) return "";
      return `<section class="rounded-2xl border border-border bg-surface shadow-sm" data-home-section="${category.key}">
        <div class="flex items-center gap-3 border-b border-border px-5 py-4">
          <span class="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-container text-on-primary-container"><span class="material-symbols-outlined text-[20px]">${category.icon}</span></span>
          <div>
            <h2 class="font-headline-sm text-headline-sm text-on-surface">${category.label}</h2>
            <p class="font-body-sm text-body-sm text-text-muted">${category.description}</p>
          </div>
        </div>
        <div class="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2 xl:grid-cols-3">${items.map(navFeatureCardHtml).join("")}</div>
      </section>`;
    })
    .join("");
  root.dataset.homeHasContent = entries.length > 0 ? "true" : "false";
  return true;
}

/* ── Global live search ───────────────────────────────────────── */

function navSearchableEntries() {
  const codes = navPermissionSet();
  return navEntriesFor(codes, { sidebar: false, home: false });
}

function ensureSearchDropdown() {
  let dropdown = document.getElementById("nav-search-dropdown");
  if (!dropdown) {
    dropdown = document.createElement("div");
    dropdown.id = "nav-search-dropdown";
    dropdown.className = "nav-search-dropdown";
    dropdown.setAttribute("role", "listbox");
    dropdown.setAttribute("aria-label", "Search results");
    document.body.appendChild(dropdown);
  }
  return dropdown;
}

function renderSearchResults(query) {
  const dropdown = ensureSearchDropdown();
  const input = document.querySelector("[data-global-search]");
  const q = String(query || "").trim().toLowerCase();
  if (!q || !input) {
    dropdown.hidden = true;
    dropdown.innerHTML = "";
    return;
  }
  const entries = navSearchableEntries().filter((entry) =>
    `${entry.label} ${entry.description}`.toLowerCase().includes(q),
  );
  dropdown.innerHTML = entries.length
    ? entries
        .slice(0, 8)
        .map(
          (entry) => `<a class="nav-search-item" role="option" href="${entry.file}" data-search-file="${entry.file}">
            <span class="material-symbols-outlined text-[18px]">${entry.icon}</span>
            <span class="min-w-0"><span class="block text-[13px] font-semibold text-on-surface">${entry.label}</span>
            <span class="block text-[12px] text-text-muted">${entry.description}</span></span></a>`,
        )
        .join("")
    : `<p class="nav-search-empty">No matches for “${q.replace(/</g, "&lt;")}”</p>`;
  dropdown.hidden = false;
  const rect = input.getBoundingClientRect();
  dropdown.style.top = `${rect.bottom + 6}px`;
  dropdown.style.left = `${rect.left}px`;
  dropdown.style.width = `${Math.max(rect.width, 320)}px`;
}

function wireGlobalSearch() {
  const input = document.querySelector("[data-global-search]");
  if (!input || input.dataset.navSearchWired === "true") return;
  input.dataset.navSearchWired = "true";
  input.addEventListener("input", () => renderSearchResults(input.value));
  input.addEventListener("focus", () => {
    if (input.value.trim()) renderSearchResults(input.value);
  });
  document.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) return;
    if (event.target.closest("[data-global-search], #nav-search-dropdown")) return;
    const dropdown = ensureSearchDropdown();
    dropdown.hidden = true;
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      input.value = "";
      renderSearchResults("");
      input.blur();
    }
  });
  /* On the home page, typing also filters the visible cards in real time. */
  input.addEventListener("input", () => {
    const grid = document.querySelector("[data-home-grid]");
    if (!grid) return;
    const q = input.value.trim().toLowerCase();
    grid.querySelectorAll("[data-home-card]").forEach((card) => {
      const text = (card.textContent || "").toLowerCase();
      card.hidden = Boolean(q) && !text.includes(q);
    });
    grid.querySelectorAll("[data-home-section]").forEach((section) => {
      const anyVisible = Array.from(section.querySelectorAll("[data-home-card]")).some((card) => !card.hidden);
      section.hidden = Boolean(q) && !anyVisible;
    });
  });
}

/* ── Metrics widget ───────────────────────────────────────────── */

function navCanSeeMetric(metric, codes) {
  const required = metric.permissions || [];
  return !required.length || required.some((code) => codes.has(code));
}

function buildHomeMetrics() {
  const host = document.querySelector("[data-home-metrics]");
  if (!host) return;
  const codes = navPermissionSet();
  const config = window.NAV_CONFIG;
  const visible = config.metrics.filter((metric) => navCanSeeMetric(metric, codes));
  host.innerHTML = visible
    .map(
      (metric) => `<div class="rounded-xl border border-border bg-surface p-3" data-metric-id="${metric.id}">
        <p class="font-label-caps text-label-caps text-text-muted uppercase">${metric.label}</p>
        <p class="mt-1 font-headline-md text-headline-md text-primary" data-metric-value>—</p>
      </div>`,
    )
    .join("");
  loadHomeMetrics();
}

async function loadHomeMetrics() {
  const setValue = (id, value) => {
    const host = document.querySelector(`[data-metric-id="${id}"] [data-metric-value]`);
    if (host) host.textContent = value;
  };
  const api = typeof apiRequest === "function" ? apiRequest : null;
  if (!api) return;
  const guard = (promise, fallback) => promise.catch(() => fallback);

  const requisitions = await guard(api("/requisitions/?page_size=1"), null);
  setValue("open-requisitions", requisitions?.meta?.total ?? "—");
  const notifications = await guard(api("/notifications/?status=unread&page_size=1"), null);
  setValue("unread-notifications", notifications?.meta?.total ?? "—");
  const approvals = await guard(api("/approvals/?page_size=1"), null);
  setValue("pending-approvals", approvals?.meta?.total ?? "—");
  const updates = await guard(api("/daily-updates/?page_size=1"), null);
  setValue("overdue-updates", updates?.meta?.total ?? "—");
}

/* ── Boot ─────────────────────────────────────────────────────── */

function bootNavigationChrome() {
  buildSidebarNav();
  buildMobileNav();
  if (document.querySelector("[data-home-grid]")) buildHomeGrid();
  if (document.querySelector("[data-home-metrics]")) buildHomeMetrics();
  wireGlobalSearch();
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootNavigationChrome, { once: true });
  } else {
    bootNavigationChrome();
  }
}
