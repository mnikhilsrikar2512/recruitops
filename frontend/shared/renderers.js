/**
 * renderers.js — Pure rendering, data formatting & DOM helper functions
 *
 * All functions here are pure: they take data as input and return
 * HTML strings, computed values, or perform simple DOM queries.
 * No API calls, no async operations, no complex state mutations.
 *
 * Load BEFORE api-client.js:
 *   <script src="../shared/renderers.js"></script>
 *   <script src="../shared/api-client.js"></script>
 */

/* ═══════════════════════════════════════════════════════════════
   TEXT FORMATTING & DATA HELPERS
   ═══════════════════════════════════════════════════════════════ */

function escapeLiveHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatWhen(value) {
  if (!value) return "";
  const text = String(value);
  return text.replace("T", " ").slice(0, 16);
}function setText(node, value) {
  if (node) node.textContent = String(value ?? "");
}

function htmlList(items, renderItem, emptyHtml = "") {
  return items.length ? items.map(renderItem).join("") : emptyHtml;
}

function readableText(node) {
  if (!node) return "";
  const clone = node.cloneNode(true);
  clone.querySelectorAll(".material-symbols-outlined").forEach((icon) => icon.remove());
  return (clone.textContent || "").replace(/\s+/g, " ").trim();
}

function relativeTime(value) {
  if (!value) return "";
  const then = new Date(value);
  if (Number.isNaN(then.getTime())) return formatWhen(value);
  const delta = Date.now() - then.getTime();
  const minutes = Math.round(delta / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

function reqCode(item) {
  return item?.requisition_code || (item?.requisition_id ? `REQ-${item.requisition_id}` : item?.id ? `REQ-${item.id}` : "—");
}

/* ── Badge-Based Visual ID (PRD §2.6) ─────────────────────────────────
   Bold monospace display ID plus a soft-tinted branch pill. The pill
   tone is a stable hash of the branch code so HYD always renders the
   same color on every surface; unknown codes fall back to neutral. */
const BRANCH_TONES = ["sky", "violet", "amber", "rose", "teal"];

function branchTone(code) {
  const raw = String(code || "").trim();
  if (!raw) return "neutral";
  const base = raw.replace(/[0-9]+$/, "").toUpperCase() || raw.toUpperCase();
  let hash = 0;
  for (let i = 0; i < base.length; i += 1) hash = (hash * 31 + base.charCodeAt(i)) % 997;
  return BRANCH_TONES[hash % BRANCH_TONES.length];
}

function branchCodeLabel(code) {
  const raw = String(code || "").trim();
  if (!raw) return "";
  // Strip a trailing numeric suffix ("BLR01" -> "BLR"); also strip any
  // separator that suffix leaves dangling ("CODE-101" -> "CODE-" -> "CODE")
  // so a branch code that happens to look like a display id never renders
  // as a bare hyphen with nothing after it.
  const stripped = raw.replace(/[0-9]+$/, "").replace(/[-_\s]+$/, "");
  return (stripped || raw).toUpperCase();
}

function entityBadgeHtml(displayId, branchCode) {
  const id = String(displayId || "").trim();
  const pill = branchCodeLabel(branchCode);
  if (!id && !pill) return "";
  const tone = branchTone(branchCode);
  return `<span class="entity-badge">${
    id ? `<span class="entity-badge-id">${escapeLiveHtml(id)}</span>` : ""
  }${
    pill ? `<span class="branch-pill" data-branch-tone="${tone}" title="${escapeLiveHtml(String(branchCode).trim())}">${escapeLiveHtml(pill)}</span>` : ""
  }</span>`;
}

function personInitials(name) {
  return String(name || "?")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase() || "?";
}

function titleFromCode(value) {
  return String(value || "")
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function activeSearchParams() {
  const overlay = document.getElementById("ro-inpage-overlay");
  if (overlay?.dataset.overlaySearch) return new URLSearchParams(overlay.dataset.overlaySearch);
  return new URLSearchParams(window.location.search);
}

function queryInt(...names) {
  const params = activeSearchParams();
  for (const name of names) {
    const value = intOrNull(params.get(name));
    if (value) return value;
  }
  return null;
}


/* ═══════════════════════════════════════════════════════════════
   DOM & FORM UTILITIES
   ═══════════════════════════════════════════════════════════════ */function controlNearLabel(labelPattern, root = document) {
  const labels = Array.from(root.querySelectorAll("label"));
  const label = labels.find((node) => new RegExp(labelPattern, "i").test(node.textContent || ""));
  return label?.querySelector("input, select, textarea") || label?.nextElementSibling;
}

function valueNearLabel(labelPattern, root = document) {
  return controlNearLabel(labelPattern, root)?.value ?? "";
}

function firstValueOf(ids = [], labelPatterns = [], root = document) {
  for (const id of ids) {
    const node = document.getElementById(id);
    if (node && node.value) return node.value;
  }
  for (const pattern of labelPatterns) {
    const value = valueNearLabel(pattern, root);
    if (value) return value;
  }
  return "";
}function intOrNull(value) {
  if (value === null || value === undefined || value === "") return null;
  const num = Number(value);
  return Number.isNaN(num) ? null : Math.trunc(num);
}

function setFirstText(selector, value) {
  if (value === undefined || value === null) return;
  const node = document.querySelector(selector);
  if (node) node.textContent = String(value);
}

function setApiField(name, value) {
  setFirstText(`[data-api-field="${name}"]`, value ?? "—");
}

/* Fields gated by Visibility Rules (scripts/031_visibility_rules.sql) are
   OMITTED entirely from the API response for a role without access, not
   nulled — so "the key isn't on the object" means "hidden from you" and
   must stay hidden, while "the key is present but null" means "visible to
   you, just not set yet" and should render as "—" like any other field.
   `entity` is the API response object; `fieldFormatters` maps each gated
   field name to a `(rawValue) => displayString|null` formatter. Each row
   (marked `data-commercial-field="<name>"`) and the enclosing section
   (marked `data-commercial-terms`) start `hidden` in the page markup and
   are only unhidden here, per field, when that key actually exists. */
function revealGatedFields(entity, fieldFormatters) {
  let anyVisible = false;
  for (const [fieldName, formatter] of Object.entries(fieldFormatters)) {
    const row = document.querySelector(`[data-commercial-field="${fieldName}"]`);
    const present = entity != null && Object.prototype.hasOwnProperty.call(entity, fieldName);
    if (row) row.hidden = !present;
    if (present) {
      anyVisible = true;
      setApiField(fieldName, formatter(entity[fieldName]));
    }
  }
  const section = document.querySelector("[data-commercial-terms]");
  if (section) section.hidden = !anyVisible;
}function setStackedCell(td, title, subtitle) {
  if (!td) return;
  const titleNode = td.querySelector(".font-headline-sm, .font-semibold, p.font-headline-sm, span.font-medium, .truncate");
  if (titleNode) titleNode.textContent = title || "—";
  const extra = td.querySelector(".font-label-caps, .text-xs, .font-body-sm, p.font-body-sm, .text-text-muted");
  if (extra && subtitle !== undefined) extra.textContent = subtitle || "";
}function mapLocationStatus(value) {
  const normalized = String(value || "").toLowerCase();
  if (/active|open/.test(normalized)) return "Active";
  if (/inactive|closed/.test(normalized)) return "Inactive";
  return value || "—";
}/* ═══════════════════════════════════════════════════════════════
   TABLE RENDERING
   ═══════════════════════════════════════════════════════════════ */

function tableHeaders() {
  return Array.from(document.querySelectorAll(".workspace-surface thead th")).map((th) =>
    (th.textContent || "").replace(/\s+/g, " ").trim().toLowerCase(),
  );}function paintPersonCell(td, name) {
  if (!td) return;
  const label = String(name || "").trim();
  const initials = label.split(/\s+/).slice(0, 2).map((w) => w[0] || "").join("").toUpperCase();
  const avatar = td.querySelector("div");
  if (avatar) avatar.textContent = initials || "—";
  const nameSpan = td.querySelector("span");
  if (nameSpan) nameSpan.textContent = label || "—";
}function paintPriorityBadge(td, priority) {
  if (!td) return;
  const p = String(priority || "").toLowerCase();
  const tones = {
    critical: "bg-danger-bg text-danger-text",
    high: "bg-warning-bg text-warning-text",
    medium: "bg-info-bg text-info-text",
    low: "bg-surface-dim text-on-surface-variant",  // text-muted on surface-dim was 3.87:1, under WCAG AA (4.5:1) for this 12px badge text
  };
  const badge = td.querySelector("span") || td;
  badge.className = `inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${tones[p] || tones.low}`;
  badge.textContent = p ? p.charAt(0).toUpperCase() + p.slice(1) : "—";
}function ageDaysLabel(createdAt) {
  const then = new Date(createdAt);
  if (isNaN(then)) return "—";
  const days = Math.max(0, Math.floor((Date.now() - then.getTime()) / 86400000));
  return `${days}d`;
}function setCellValue(td, value) {
  if (!td || value === undefined) return;
  const titleNode = td.querySelector(".font-headline-sm, .font-semibold, p.font-headline-sm, span.font-medium, .truncate");
  if (titleNode) {
    titleNode.textContent = value || "—";
    const extra = td.querySelector(".font-label-caps, .text-xs, .font-body-sm, p.font-body-sm, .text-text-muted");
    if (extra && extra !== titleNode && extra.textContent && extra.textContent.length < 80) {
      extra.textContent = "";
    }
    return;
  }
  const status = td.querySelector("span");
  if (status && !status.classList.contains("material-symbols-outlined")) {
    status.textContent = value || "—";
    return;
  }
  td.textContent = value || "—";
}

/**
 * Render the inner content of a table empty-state cell.
 * Returns the <td> content only — callers wrap in <tr> as needed.
 *
 * @param {Object} opts
 * @param {string} [opts.icon='inventory_2'] - Material icon name
 * @param {string} [opts.title] - Bold heading (auto-derived from page surface if omitted)
 * @param {string} [opts.hint='Try adjusting your filters or create a new record.'] - Body copy
 * @param {string} [opts.hintClass='text-[11px]'] - Extra classes for the hint paragraph
 * @param {number} opts.columnCount - colspan for the td
 * @returns {string} HTML string for the empty-state cell content
 */
function emptyStateForRoute(filtered = false) {
  const route = document.body?.dataset.routeId || "";
  const map = {
    "candidate-profiles": { title: "No candidates yet", hint: "Add a candidate to start building your talent pool.", cta: "Add Candidate", href: "candidate-review-drawer.html" },
    "client-directory": { title: "No clients yet", hint: "Add a client to track accounts and requisitions.", cta: "Add Client", href: "" },
    "requisition-list": { title: "No requisitions yet", hint: "Create a requisition to start hiring.", cta: "Create Requisition", href: "requisition-intake.html" },
    "follow-ups": { title: "No follow-ups yet", hint: "Schedule a follow-up so nothing slips.", cta: "Add Follow-Up", href: "follow-up-form-dialog.html" },
    "meetings": { title: "No meetings yet", hint: "Schedule a meeting with your team or a client.", cta: "Schedule Meeting", href: "meeting-form-dialog.html" },
    "user-management": { title: "No users yet", hint: "Invite teammates so they can work in RecruitOps.", cta: "Add User", href: "" },
    "role-management": { title: "No roles yet", hint: "Create a role to control access.", cta: "Create Role", href: "" },
    "approvals-inbox": { title: "Nothing to approve", hint: "New requests will land here when they need a decision." },
    "offer-management": { title: "No offers yet", hint: "Create an offer when a candidate is ready.", cta: "Create Offer", href: "offer-create-dialog.html" },
    "interview-scheduler": { title: "No interviews yet", hint: "Interviews appear here once they are scheduled." },
  };
  if (filtered) {
    return { title: "No matching records", hint: "Nothing matches this search or filter. Clear it to see all records.", cta: "Clear filters", clear: true };
  }
  return map[route] || { title: "Nothing here yet", hint: "Try a different filter, or add a new record." };
}

function renderEmptyStateCta(meta) {
  if (!meta?.cta) return "";
  if (meta.clear) {
    return `<button type="button" data-clear-workspace-filters="true" class="mt-2 inline-flex items-center rounded-lg border border-border bg-surface px-3 py-1.5 text-[12px] font-semibold text-on-surface hover:bg-highlight-soft">Clear filters</button>`;
  }
  if (meta.href) {
    return `<button type="button" data-empty-cta-route="${meta.href}" class="mt-2 inline-flex items-center rounded-lg bg-primary-container px-3 py-1.5 text-[12px] font-semibold text-on-primary hover:bg-primary-hover">${meta.cta}</button>`;
  }
  return `<button type="button" data-empty-cta="primary" class="mt-2 inline-flex items-center rounded-lg bg-primary-container px-3 py-1.5 text-[12px] font-semibold text-on-primary hover:bg-primary-hover">${meta.cta}</button>`;
}

function renderTableEmptyCell(opts) {
  const { icon = "inventory_2", title, hint, hintClass = "text-[11px]", columnCount = 1, filtered = false } = opts || {};
  const fallback = emptyStateForRoute(filtered);
  const heading = title || fallback.title || (() => {
    const surface = document.querySelector(".workspace-surface");
    return surface?.querySelector("h2, h3")?.textContent?.trim() || "records";
  })();
  const titleText = /no /i.test(heading) ? heading : `No ${heading.toLowerCase()} found.`;
  const hintCopy = hint || fallback.hint || "Try adjusting your filters or create a new record.";
  const cta = renderEmptyStateCta({ ...fallback, cta: opts?.cta || fallback.cta, href: opts?.href || fallback.href, clear: opts?.clear || fallback.clear });
  return `<td colspan="${columnCount}">
    <div class="table-empty-state-card">
      <div class="flex flex-col items-center gap-2">
        <span class="material-symbols-outlined text-3xl text-border">${icon}</span>
        <strong>${titleText}</strong>
        <p class="font-body-sm text-body-sm text-text-muted ${hintClass}">${hintCopy}</p>
        ${cta}
      </div>
    </div>
  </td>`;
}

/**
 * Render a complete <tr> wrapping a reusable table empty-state.
 *
 * @param {Object} opts - Same as renderTableEmptyCell
 * @returns {string} Full <tr> HTML string with data-generated-empty-state attribute
 */
function renderTableEmptyState(opts) {
  return `<tr class="table-empty-state-row" data-generated-empty-state="true">${renderTableEmptyCell(opts)}</tr>`;
}

/**
 * Render a complete <tr> for a search / filter empty state.
 *
 * @param {Object} opts
 * @param {string} opts.searchTerm - The term the user searched for
 * @param {number} opts.columnCount - colspan for the td
 * @returns {string} Full <tr> HTML string
 */
function workspaceTbody() {
  const tbodies = document.querySelectorAll(".workspace-surface tbody, section.shell-card tbody");
  for (const tbody of tbodies) {
    if (tbody.closest(".overlay-underlay, [data-overlay-surface]")) continue;
    return tbody;
  }
  return null;
}

function fillExistingTable(items, paintRow) {
  const tbody = workspaceTbody();
  if (!tbody) return;
  if (!tbody._roTemplate) {
    const first = tbody.querySelector("tr[data-row-template], tr:not(.skeleton-row):not([data-generated-empty-state])");
    if (first) tbody._roTemplate = first.cloneNode(true);
  }
  const template = tbody._roTemplate || tbody.querySelector("tr");
  if (!template) return;
  template.removeAttribute("hidden");
  delete template.dataset.rowTemplate;
  tbody.innerHTML = "";
  if (!items.length) {
    const cols = template.children.length || 1;
    tbody.innerHTML = renderTableEmptyState({ columnCount: cols, ...emptyStateForRoute(false) });
    queueMicrotask(() => {
      const table = tbody.closest("table");
      if (table && typeof applyClientPagination === "function") applyClientPagination(table);
    });
    return;
  }
  items.forEach((item, index) => {
    const row = template.cloneNode(true);
    row.classList.remove("skeleton-row");
    row.hidden = false;
    row.classList.toggle("bg-surface-alt", index % 2 === 1);
    row.dataset.recordId = item.id || item.application_id || "";
    delete row.dataset.rowMenuWired;
    row.querySelectorAll("[data-hover-menu-wired]").forEach((node) => {
      delete node.dataset.hoverMenuWired;
    });
    paintRow(row, item, index);
    tbody.appendChild(row);
  });
  queueMicrotask(() => {
    const table = tbody.closest("table");
    if (table && typeof wireLiveTableInteractions === "function") {
      delete table.dataset.pageSize;
      table.dataset.page = "1";
      wireLiveTableInteractions(table);
    }
  });
}/* ═══════════════════════════════════════════════════════════════
   PAGE LOADING HELPERS
   ═══════════════════════════════════════════════════════════════ */function hidePageLoader() {
  const loader = document.getElementById("ro-page-loader");
  if (loader) loader.remove();
}

function fillDashboardMetrics(pairs) {
  const surface = document.querySelector(".workspace-surface");
  if (!surface) return;
  const cards = surface.querySelectorAll(".lg\\:items-end .min-w-\\[160px\\], .flex-wrap.lg\\:flex-nowrap .min-w-\\[160px\\]");
  pairs.forEach((pair, index) => {
    const card = cards[index];
    if (card) {
      const headline = card.querySelector(".font-headline-md, .text-headline-md");
      if (headline) headline.textContent = String(pair.value ?? "—");
      const hint = card.querySelector(".font-body-sm, .text-body-sm, .text-text-muted");
      if (hint && pair.hint) hint.textContent = pair.hint;
    }
    if (typeof setMetricCardValue === "function" && pair.label) {
      setMetricCardValue(pair.label, String(pair.value ?? "—"), pair.hint
        ? `<span class="text-body-sm text-text-muted">${escapeLiveHtml(pair.hint)}</span>`
        : "");
    }
  });
}

function hidePanelByHeading(text) {
  const panel = findPanelByHeading(text);
  if (!panel) return;
  panel.setAttribute("data-ro-hidden-panel", "true");
  panel.hidden = true;
}

function renderRankedMetricList(container, rows, options = {}) {
  if (!container) return;
  const format = options.format || ((value) => String(value));
  const items = (rows || []).filter((row) => row && (row.label || row.name));
  if (!items.length) {
    container.innerHTML = `<p class="text-body-sm text-text-muted py-4 text-center">${escapeLiveHtml(options.empty || "No data yet.")}</p>`;
    return;
  }
  const max = Math.max(...items.map((row) => Number(row.value) || 0), 1);
  container.innerHTML = items.map((row) => {
    const value = Number(row.value) || 0;
    const width = Math.max(6, Math.round((value / max) * 100));
    return `<div class="ro-ranked-row">
      <span title="${escapeLiveHtml(row.label || row.name)}">${escapeLiveHtml(row.label || row.name)}</span>
      <div class="ro-ranked-track"><div class="ro-ranked-fill" style="width:${width}%"></div></div>
      <span class="ro-ranked-value">${escapeLiveHtml(format(value))}</span>
    </div>`;
  }).join("") + (options.insight ? `<p class="ro-chart-insight">${escapeLiveHtml(options.insight)}</p>` : "");
}

function paintChartPlaceholder(heading, html) {
  const panel = findPanelByHeading(heading);
  const host = panel?.querySelector(".chart-placeholder") || panel?.querySelector("[data-live-chart]") || panel?.querySelector(".p-4:last-child");
  if (!host) return null;
  host.classList.remove("chart-placeholder", "h-64", "h-48");
  host.style.minHeight = "0";
  host.style.height = "auto";
  if (html) host.innerHTML = html;
  return host;
}

function renderCompanySlaRisks(requisitions) {
  const list = findPanelByHeading("Critical SLA Risks")?.querySelector("ul");
  if (!list) return;
  const now = Date.now();
  const risks = (requisitions || [])
    .filter((row) => String(row.status || "open") === "open")
    .map((row) => {
      const created = new Date(row.created_at).getTime();
      const days = Number.isNaN(created) ? 0 : Math.floor((now - created) / 86400000);
      const target = typeof slaTargetDays === "function" ? slaTargetDays(row) : 30;
      return { ...row, days, over: days - target };
    })
    .filter((row) => row.over > 0)
    .sort((a, b) => b.over - a.over)
    .slice(0, 4);
  list.innerHTML = risks.length
    ? risks.map((row) => `<li class="p-4 hover:bg-highlight-soft transition-colors flex items-start gap-3">
        <div class="w-8 h-8 rounded-DEFAULT ${row.over > 15 ? "bg-danger-bg text-danger-text" : "bg-warning-bg text-warning-text"} flex items-center justify-center shrink-0">
          <span class="font-data-tabular font-bold text-sm">${row.over}</span>
        </div>
        <div class="min-w-0">
          <h4 class="font-body-sm text-body-sm font-medium text-on-surface truncate">${escapeLiveHtml(row.title || "Requisition")}</h4>
          <p class="font-body-sm text-body-sm text-text-muted mt-0.5">${row.days}d open · ${escapeLiveHtml(row.client_name || "No client")}</p>
        </div>
      </li>`).join("")
    : `<li class="p-4 text-body-sm text-text-muted">No open requisitions past SLA.</li>`;
}

function renderCompanyLocations(locations) {
  const panel = findPanelByHeading("Top 5 Locations (Volume vs Compliance)");
  const thead = panel?.querySelector("thead tr");
  const tbody = panel?.querySelector("tbody");
  if (!tbody) return;
  if (thead) {
    thead.innerHTML = `<th class="pb-3 font-semibold">Location</th>
      <th class="pb-3 text-right font-semibold">Open Reqs</th>
      <th class="pb-3 text-right font-semibold">Pipeline</th>
      <th class="pb-3 text-right font-semibold">Submitted</th>
      <th class="pb-3 text-right font-semibold">Joined</th>`;
  }
  const rows = (locations || []).slice(0, 5);
  tbody.innerHTML = rows.length
    ? rows.map((loc) => `<tr class="hover:bg-highlight-soft/50 transition-colors">
        <td class="py-3 font-medium text-on-surface">${escapeLiveHtml(loc.location_name || "Location")}</td>
        <td class="py-3 text-right font-data-tabular">${loc.open_requisitions || 0}</td>
        <td class="py-3 text-right font-data-tabular">${loc.active_candidates || loc.active_applications || 0}</td>
        <td class="py-3 text-right font-data-tabular">${loc.submitted_profiles || 0}</td>
        <td class="py-3 text-right font-data-tabular">${loc.joined_applications || 0}</td>
      </tr>`).join("")
    : `<tr><td class="py-4 text-text-muted" colspan="5">No location volume yet.</td></tr>`;
}

function renderCompanyClientDemand(requisitions) {
  const panel = findPanelByHeading("Top Client Demand");
  const tbody = panel?.querySelector("tbody");
  if (!tbody) return;
  const grouped = {};
  (requisitions || []).filter((row) => String(row.status || "open") === "open").forEach((row) => {
    const name = row.client_name || "Unassigned";
    if (!grouped[name]) grouped[name] = { name, count: 0, days: 0 };
    grouped[name].count += 1;
    const created = new Date(row.created_at).getTime();
    grouped[name].days += Number.isNaN(created) ? 0 : Math.floor((Date.now() - created) / 86400000);
  });
  const rows = Object.values(grouped).sort((a, b) => b.count - a.count).slice(0, 5);
  tbody.innerHTML = rows.length
    ? rows.map((row) => {
        const avg = row.count ? Math.round(row.days / row.count) : 0;
        const priority = avg > 40 || row.count >= 4 ? "High" : avg > 20 ? "Med" : "Low";
        const badge = priority === "High" ? "bg-danger-bg text-danger-text" : priority === "Med" ? "bg-warning-bg text-warning-text" : "bg-info-bg text-info-text";
        return `<tr class="h-table-row border-b border-border hover:bg-highlight-soft transition-colors">
          <td class="px-5 py-2 font-medium text-on-surface">${escapeLiveHtml(row.name)}</td>
          <td class="px-5 py-2 text-right font-data-tabular">${row.count}</td>
          <td class="px-5 py-2"><span class="inline-flex items-center px-2 py-0.5 rounded-DEFAULT text-[11px] font-semibold ${badge}">${priority}</span></td>
          <td class="px-5 py-2 text-right font-data-tabular">${avg}d</td>
          <td class="px-5 py-2 text-center text-text-muted">—</td>
        </tr>`;
      }).join("")
    : `<tr><td class="px-5 py-6 text-text-muted" colspan="5">No open client demand yet.</td></tr>`;
}


/* ═══════════════════════════════════════════════════════════════
   WORKFLOW PURE HELPERS
   ═══════════════════════════════════════════════════════════════ */

function workflowEndpointForLabel(label) {
  const normalized = String(label || "").toLowerCase();
  if (normalized.includes("resolve")) return "resolve";
  if (normalized.includes("nudge")) return "nudge";
  return "run";
}

function workflowPriorityClass(priority) {
  const normalized = String(priority || "normal").toLowerCase();
  if (normalized === "critical") return "bg-error";
  if (normalized === "high") return "bg-warning-text";
  if (normalized === "low") return "bg-text-muted";
  return "bg-primary";
}

function workflowAccentClass(priority) {
  const normalized = String(priority || "normal").toLowerCase();
  if (normalized === "critical") return "border-error bg-danger-bg/20";
  if (normalized === "high") return "border-warning-text bg-warning-bg/20";
  return "border-primary bg-surface";
}

function workflowPriorityMeta(priority) {
  const normalized = String(priority || "normal").toLowerCase();
  if (normalized === "critical") return { dot: "bg-error", text: "text-danger-text", label: "Critical" };
  if (normalized === "high") return { dot: "bg-warning-text", text: "text-warning-text", label: "High" };
  if (normalized === "low") return { dot: "bg-text-muted", text: "text-text-muted", label: "Low" };
  return { dot: "bg-success-text", text: "text-success-text", label: "Standard" };
}

function findPanelByHeading(text) {
  const needle = String(text || "").toLowerCase();
  const headings = Array.from(document.querySelectorAll(".workspace-surface h2, .workspace-surface h3"));
  const heading = headings.find((node) => readableText(node).toLowerCase() === needle)
    || headings.find((node) => readableText(node).toLowerCase().endsWith(needle));
  return heading?.closest(".bg-surface, section, .rounded-2xl, .rounded-lg") || null;
}

function paintLabeledKpi(labelText, valueText, hintText) {
  const needle = String(labelText || "").toLowerCase();
  const heading = Array.from(document.querySelectorAll(".workspace-surface h3, .workspace-surface .text-label-caps")).find((node) =>
    readableText(node).toLowerCase() === needle,
  );
  if (!heading) {
    if (typeof setMetricCardValue === "function") {
      setMetricCardValue(labelText, String(valueText ?? "—"), hintText
        ? `<span class="text-body-sm text-text-muted">${escapeLiveHtml(hintText)}</span>`
        : "");
    }
    return;
  }
  const card = heading.closest(".bg-surface, .metric-card") || heading.parentElement;
  const valueNode = card?.querySelector(".font-headline-lg, .text-headline-lg, p[class*='headline']");
  if (valueNode) {
    const unit = valueNode.querySelector("span");
    if (unit && /days/i.test(unit.textContent || "") && String(valueText) !== "—" && !/%/.test(String(valueText))) {
      valueNode.innerHTML = `${escapeLiveHtml(String(valueText ?? "—"))} <span class="text-headline-md text-text-muted font-normal">days</span>`;
    } else {
      valueNode.textContent = String(valueText ?? "—");
    }
  }
  const hint = Array.from(card?.querySelectorAll("p.font-body-sm, p.text-body-sm") || []).pop();
  if (hint && hintText) hint.textContent = hintText;
  card?.querySelectorAll(".font-data-tabular").forEach((badge) => {
    if (/trending_|12%|4d|1\.1%|\+12%|\+0\.4x|\+5%|-3 days/i.test(badge.textContent || "")) badge.remove();
  });
}


/* ═══════════════════════════════════════════════════════════════
   WORKFLOW QUEUE RENDERERS
   ═══════════════════════════════════════════════════════════════ */

function renderRoleWorkflowQueue(items) {
  const rowsHost = document.querySelector("[data-role-workflow-rows]") || (() => {
    const panel = findPanelByHeading("Urgent Action Queue");
    return Array.from(panel?.children || []).find((child) =>
      child.classList?.contains("flex") && child.classList?.contains("flex-col") && !child.querySelector("h2, h3"),
    );
  })();
  if (!rowsHost) return;
  const header = rowsHost.previousElementSibling;
  if (header && header.classList.contains("grid")) {
    header.hidden = items.length === 0;
    header.style.display = items.length === 0 ? "none" : "";
  }
  const filterBtn = rowsHost.closest(".bg-surface")?.querySelector("h3")?.closest("div")?.parentElement?.querySelector("button");
  if (filterBtn) filterBtn.hidden = items.length === 0;
  const footer = rowsHost.parentElement?.querySelector("[data-role-queue-footer]");
  if (footer) footer.hidden = items.length === 0;
  rowsHost.innerHTML = items.length
    ? items.map((item) => {
        const actionLabel = item.primary_action_label || "Do Now";
        const action = workflowEndpointForLabel(actionLabel);
        return `<div class="grid grid-cols-12 gap-4 px-inset-card h-table-row items-center border-b border-border bg-surface hover:bg-highlight-soft transition-colors group" data-live-workflow-row="true" data-action-item-id="${item.id}">
          <div class="col-span-5 flex items-center gap-2 min-w-0">
            <span class="w-2 h-2 rounded-full ${workflowPriorityClass(item.priority)} shrink-0"></span>
            <span class="truncate">${escapeLiveHtml(item.title)}</span>
          </div>
          <div class="col-span-3 truncate text-text-muted">${escapeLiveHtml(item.entity_type || "Record")}${item.entity_id ? `-${item.entity_id}` : ""}</div>
          <div class="col-span-2 text-text-muted">${escapeLiveHtml(item.age_label || "")}</div>
          <div class="col-span-2 text-right">
            <button class="font-label-caps text-label-caps text-primary hover:text-primary-hover" type="button" data-live-workflow-action="${action}" data-action-item-id="${item.id}">${escapeLiveHtml(actionLabel)}</button>
          </div>
        </div>`;
      }).join("")
    : `<div class="px-inset-card py-2.5 flex items-center justify-center gap-2 bg-surface">
        <span class="material-symbols-outlined text-[18px] text-success-text">task_alt</span>
        <p class="font-body-sm text-body-sm text-text-muted">Nothing needs attention right now.</p>
      </div>`;
  if (typeof applyCollectionPagination === "function") {
    delete rowsHost.dataset.pageSize;
    rowsHost.dataset.page = "1";
    applyCollectionPagination(rowsHost);
  }
}

function renderNotificationWorkflowQueue(items) {
  const panel = findPanelByHeading("Action Queue");
  const rowsHost = panel?.querySelector(".divide-y");
  if (!rowsHost) return;
  rowsHost.innerHTML = items.length
    ? items.map((item) => {
        const actionLabel = item.primary_action_label || "Review";
        const action = workflowEndpointForLabel(actionLabel);
        return `<article class="group relative grid gap-3 border-l-4 p-4 transition-colors hover:bg-highlight-soft md:grid-cols-[auto_minmax(0,1fr)_auto] md:items-center ${workflowAccentClass(item.priority)}" data-live-workflow-row="true" data-action-item-id="${item.id}">
          <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-surface-alt text-primary">
            <span class="material-symbols-outlined">task_alt</span>
          </div>
          <div class="min-w-0">
            <div class="mb-1 flex flex-wrap items-center gap-2">
              <span class="rounded border border-border bg-white px-1.5 py-0.5 font-label-caps text-label-caps uppercase tracking-wider text-primary">${escapeLiveHtml(item.source)}</span>
              <span class="font-data-tabular text-[11px] text-text-muted">${escapeLiveHtml(item.age_label || "")}</span>
            </div>
            <h3 class="font-headline-sm text-headline-sm text-on-surface">${escapeLiveHtml(item.title)}</h3>
            <p class="mt-1 font-body-sm text-body-sm text-text-muted">${escapeLiveHtml(item.description || "")}</p>
          </div>
          ${cardKebabMenu(`<button type="button" role="menuitem" data-live-workflow-action="${action}" data-action-item-id="${item.id}">${escapeLiveHtml(actionLabel)}</button>`)}
        </article>`;
      }).join("")
    : `<div class="p-6 text-center text-text-muted">No open workflow actions from the API.</div>`;
  if (typeof wireHoverKebabMenus === "function") wireHoverKebabMenus(rowsHost);
}


/* ═══════════════════════════════════════════════════════════════
   DAILY REVIEW & NOTIFICATIONS
   ═══════════════════════════════════════════════════════════════ */

function dailyReviewAccent(item) {
  const priority = String(item?.priority || "").toLowerCase();
  if (priority === "critical") return { icon: "priority_high", bg: "bg-danger-bg", text: "text-danger-text" };
  if (priority === "high") return { icon: "warning", bg: "bg-warning-bg", text: "text-warning-text" };
  if (priority === "low") return { icon: "info", bg: "bg-info-bg", text: "text-info-text" };
  return { icon: "task_alt", bg: "bg-success-bg", text: "text-success-text" };
}

function panelRowsHost(title) {
  const panel = findPanelByHeading(title);
  return Array.from(panel?.children || []).find((child) =>
    child.classList?.contains("flex") && child.classList?.contains("flex-col") && !child.querySelector("h2, h3"),
  );
}function dailyReviewListHost(title) {
  const panel = findPanelByHeading(title);
  return panel?.querySelector(".divide-y") || panelRowsHost(title);
}

function renderDailyReviewQuickStats(myWork, pipelineItems, extra = {}) {
  const host = dailyReviewListHost("Quick Stats");
  const pipelineCount = pipelineItems?.length ?? 0;
  const interviews = extra.interviews ?? 0;
  const offers = extra.offers ?? 0;
  const ttf = extra.avgFillDays;
  if (host) {
    const rows = [
      ["Candidates in pipeline", pipelineCount],
      ["Interviews this week", interviews],
      ["Offers pending", offers],
      ["Time-to-hire (avg)", ttf != null ? `${ttf} days` : "—"],
    ];
    host.innerHTML = rows.map(([label, value]) => `<div class="px-inset-card py-3 flex items-center justify-between">
      <span class="font-body-sm text-on-surface-variant text-[13px]">${escapeLiveHtml(label)}</span>
      <span class="font-headline-sm font-bold text-on-surface">${escapeLiveHtml(String(value))}</span>
    </div>`).join("");
  }
  const dateNode = document.querySelector(".workspace-surface h2")?.nextElementSibling;
  if (dateNode && /daily recruitment operations digest/i.test(dateNode.textContent || "")) {
    dateNode.textContent = `What needs a decision today · ${new Date().toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}`;
  }
}

function renderDailyReviewActions(items) {
  const host = dailyReviewListHost("Action Items");
  const panel = findPanelByHeading("Action Items");
  const badge = panel?.querySelector("span.inline-flex, .rounded.bg-danger-bg, [class*='danger']");
  if (badge && /item/i.test(badge.textContent || "")) {
    badge.textContent = items.length ? `${items.length} open` : "Clear";
  }
  if (!host) return;
  host.innerHTML = items.length
    ? items.slice(0, 5).map((item) => `<div class="px-inset-card py-3 flex items-center gap-3 hover:bg-highlight-soft transition-colors">
        <span class="material-symbols-outlined text-[18px] text-primary shrink-0">${escapeLiveHtml(item.icon || "task_alt")}</span>
        <div class="flex-1 min-w-0">
          <p class="font-semibold text-on-surface text-[13px] truncate">${escapeLiveHtml(item.title)}</p>
        </div>
        <a href="${escapeLiveHtml(item.href || "#")}" class="text-primary font-body-sm text-[12px] font-semibold hover:underline shrink-0">${escapeLiveHtml(item.action || "Open")}</a>
      </div>`).join("")
    : `<div class="px-inset-card py-5 text-body-sm text-text-muted">Nothing waiting. Pipeline and inbox are clear.</div>`;
}

function renderDailyReviewPipelineActivity(items) {
  const host = dailyReviewListHost("Pipeline Activity");
  if (!host) return;
  host.innerHTML = items.length
    ? items.map((item) => `<div class="px-inset-card py-3 flex items-center gap-3 hover:bg-highlight-soft transition-colors">
        <div class="w-8 h-8 rounded-full bg-primary text-on-primary font-bold flex items-center justify-center shrink-0 text-[11px]">${escapeLiveHtml(personInitials(item.candidate_name || "C"))}</div>
        <p class="flex-1 min-w-0 truncate font-semibold text-on-surface text-[13px]">${escapeLiveHtml(item.candidate_name || "Candidate")}</p>
        ${typeof entityBadgeHtml === "function" ? entityBadgeHtml(item.candidate_code || item.requisition_code, "") : ""}
        <span class="text-[12px] text-text-muted shrink-0">${escapeLiveHtml(item.current_stage || "Pipeline")}</span>
      </div>`).join("")
    : `<div class="px-inset-card py-5 text-body-sm text-text-muted">No recent pipeline movement.</div>`;
}

function renderDailyReviewCompactList(title, items, emptyLabel) {
  const panel = findPanelByHeading(title);
  const badge = Array.from(panel?.querySelectorAll("span") || []).find((node) =>
    /\d+\s*(event|item|update|notification)/i.test(node.textContent || "") && !node.classList.contains("material-symbols-outlined"),
  );
  if (badge) badge.textContent = items.length ? String(items.length) : "0";
  const host = dailyReviewListHost(title);
  if (!host) return;
  host.innerHTML = items.length
    ? items.slice(0, 5).map((item) => `<div class="px-inset-card py-3 flex items-center gap-3 hover:bg-highlight-soft transition-colors">
        <span class="material-symbols-outlined text-[18px] text-primary shrink-0">${escapeLiveHtml(item.icon || "circle")}</span>
        <p class="flex-1 min-w-0 truncate font-semibold text-on-surface text-[13px]">${escapeLiveHtml(item.title)}</p>
        ${item.meta ? `<span class="text-[12px] text-text-muted shrink-0">${escapeLiveHtml(item.meta)}</span>` : ""}
      </div>`).join("")
    : `<div class="px-inset-card py-5 text-body-sm text-text-muted">${escapeLiveHtml(emptyLabel || "Nothing to show.")}</div>`;
}const NOTIFICATION_EVENTS = {
  pipeline_stage_changed: { label: "Stage moved", icon: "account_tree", category: "Pipeline", cta: "Open pipeline", next: "Check the candidate on the board" },
  candidate_assigned: { label: "Candidate assigned", icon: "person_add", category: "Candidate", cta: "Open candidate", next: "Review the profile and start screening" },
  duplicate_review_assigned: { label: "Duplicate to review", icon: "control_point_duplicate", category: "Candidate", cta: "Review duplicates", next: "Decide which profile to keep" },
  candidate_finalized: { label: "Candidate linked", icon: "how_to_reg", category: "Requisition", cta: "Open requisition", next: "Confirm the hire on the requisition" },
  candidate_owner_reassigned: { label: "Ownership changed", icon: "swap_horiz", category: "Candidate", cta: "Open candidate", next: "Pick up ownership of this candidate" },
  daily_update_submitted: { label: "Daily update in", icon: "assignment", category: "Daily update", cta: "Open update", next: "Read the update and follow up if needed" },
  requisition_created: { label: "New requisition", icon: "work", category: "Requisition", cta: "Open requisition", next: "Review intake and start sourcing" },
  requisition_status_changed: { label: "Requisition status changed", icon: "flag", category: "Requisition", cta: "Open requisition", next: "See the new status and adjust work" },
  requisition_assigned: { label: "Assigned to a requisition", icon: "group_add", category: "Requisition", cta: "Open requisition", next: "See what you now own" },
  requisition_owner_reassigned: { label: "You are now the owner", icon: "badge", category: "Requisition", cta: "Open requisition", next: "Take over as primary owner" },
  user_deactivated: { label: "Account deactivated", icon: "person_off", category: "Account", cta: "View account", next: "Your access was turned off" },
  user_moved: { label: "Role or location updated", icon: "transfer_within_a_station", category: "Account", cta: "View account", next: "Review your new assignment" },
  "workflow_action.nudge": { label: "Follow-up needed", icon: "task_alt", category: "Workflow", cta: "Open work item", next: "Finish the waiting action" },
};

function notificationEventMeta(item) {
  const key = String(item?.event_type || "").trim();
  return NOTIFICATION_EVENTS[key] || null;
}

function notificationRecordHref(item) {
  const url = String(item?.action_url || "");
  const source = String(item?.source_type || item?.entity_type || "").toLowerCase();
  const id = item?.entity_id || item?.source_id;
  let match = url.match(/\/candidates\/(\d+)\/duplicate-review/);
  if (match) return `candidate-duplicate-review.html?candidate_id=${match[1]}`;
  match = url.match(/\/pipeline\/applications\/(\d+)/);
  if (match) return `pipeline-board.html?application_id=${match[1]}`;
  match = url.match(/\/candidates\/(\d+)/);
  if (match) return `candidate-detail.html?candidate_id=${match[1]}`;
  match = url.match(/\/requisitions\/(\d+)/);
  if (match) return `requisition-detail.html?requisition_id=${match[1]}`;
  match = url.match(/\/daily-updates\/(\d+)/);
  if (match) return `daily-update-detail-panel.html?daily_update_id=${match[1]}`;
  match = url.match(/\/approvals\/(\d+)/);
  if (match) return `approval-review-drawer.html?approval_id=${match[1]}`;
  if (source === "candidate" && id) return `candidate-detail.html?candidate_id=${id}`;
  if (source === "requisition" && id) return `requisition-detail.html?requisition_id=${id}`;
  if (source === "pipeline" && id) return `pipeline-board.html?application_id=${id}`;
  if (source === "daily_update" && id) return `daily-update-detail-panel.html?daily_update_id=${id}`;
  if (source === "user" && id) return `user-detail.html?user_id=${id}`;
  return "";
}

function notificationStory(item) {
  const unread = String(item?.status || "").toLowerCase() === "unread";
  const meta = notificationEventMeta(item);
  const eventLabel = meta?.label || (item?.title && !/^notification$/i.test(item.title) ? item.title : titleFromCode(item?.event_type) || "Update");
  const headline = String(item?.message || "").trim() || eventLabel;
  const href = notificationRecordHref(item);
  const cta = meta?.cta || (href ? "Open record" : "View details");
  const next = meta?.next || (href ? "Open the related record to continue" : "Read the full event");
  return {
    unread,
    eventLabel,
    headline,
    category: meta?.category || notificationCategory(item),
    icon: meta?.icon || notificationIcon(item),
    href,
    cta,
    next,
    happened: relativeTime(item?.created_at) || "just now",
    seenAt: relativeTime(item?.read_at),
    waiting: unread ? "Waiting for you" : (item?.read_at ? `Seen ${relativeTime(item.read_at)}` : "Seen"),
    priority: String(item?.priority || "normal").toLowerCase(),
  };
}

function notificationAccentClass(item) {
  const story = notificationStory(item);
  if (story.unread) return "bg-highlight-soft text-on-surface border-border";
  return "bg-surface-alt text-text-muted border-border";
}

function notificationIcon(item) {
  const meta = notificationEventMeta(item);
  if (meta?.icon) return meta.icon;
  const module = `${item?.module_name || ""} ${item?.event_type || ""} ${item?.source_type || ""}`.toLowerCase();
  if (/meeting/.test(module)) return "event";
  if (/approval|workflow/.test(module)) return "gavel";
  if (/candidate/.test(module)) return "person";
  if (/requisition/.test(module)) return "work";
  if (/pipeline|stage/.test(module)) return "account_tree";
  return "notifications";
}

function notificationCategory(item) {
  const meta = notificationEventMeta(item);
  if (meta?.category) return meta.category;
  const source = `${item?.module_name || ""} ${item?.event_type || ""} ${item?.source_type || ""}`.toLowerCase();
  if (/approval/.test(source)) return "Approvals";
  if (/pipeline|stage/.test(source)) return "Pipeline";
  if (/requisition/.test(source)) return "Requisition";
  if (/candidate/.test(source)) return "Candidate";
  if (/daily.update/.test(source)) return "Daily update";
  if (/meeting/.test(source)) return "Meeting";
  if (/user|account/.test(source)) return "Account";
  return "Hiring";
}

function notificationFlowHtml(item, compact = false) {
  const story = notificationStory(item);
  if (compact) {
    return `<p class="mt-2 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-[12px] text-text-muted">
      <span class="font-semibold text-on-surface">${escapeLiveHtml(story.eventLabel)}</span>
      <span aria-hidden="true">→</span>
      <span>${escapeLiveHtml(story.waiting)}</span>
      <span aria-hidden="true">→</span>
      <span>${escapeLiveHtml(story.cta)}</span>
    </p>`;
  }
  return `<ol class="mt-4 grid gap-3">
    <li class="grid grid-cols-[18px_minmax(0,1fr)] gap-3">
      <span class="mt-0.5 flex h-[18px] w-[18px] items-center justify-center rounded-full bg-primary text-[11px] font-bold text-white">1</span>
      <div><p class="text-[11px] font-bold uppercase tracking-wider text-text-muted">What happened</p><p class="mt-0.5 font-semibold text-on-surface">${escapeLiveHtml(story.eventLabel)}</p><p class="mt-0.5 text-body-sm text-text-muted">${escapeLiveHtml(story.happened)}</p></div>
    </li>
    <li class="grid grid-cols-[18px_minmax(0,1fr)] gap-3">
      <span class="mt-0.5 flex h-[18px] w-[18px] items-center justify-center rounded-full ${story.unread ? "bg-primary text-white" : "bg-surface-alt text-text-muted"} text-[11px] font-bold">${story.unread ? "2" : "✓"}</span>
      <div><p class="text-[11px] font-bold uppercase tracking-wider text-text-muted">${story.unread ? "Needs you" : "You already saw this"}</p><p class="mt-0.5 text-body-sm text-on-surface">${escapeLiveHtml(story.unread ? "This is still new in your inbox." : story.waiting)}</p></div>
    </li>
    <li class="grid grid-cols-[18px_minmax(0,1fr)] gap-3">
      <span class="mt-0.5 flex h-[18px] w-[18px] items-center justify-center rounded-full border border-border text-[11px] font-bold text-text-muted">3</span>
      <div><p class="text-[11px] font-bold uppercase tracking-wider text-text-muted">Next step</p><p class="mt-0.5 text-body-sm text-on-surface">${escapeLiveHtml(story.next)}</p></div>
    </li>
  </ol>`;
}

function cardKebabMenu(itemsHtml) {
  return `<div class="ro-row-menu-host ro-card-kebab" data-layout="row-actions">
    <button type="button" class="ro-card-kebab-trigger" data-row-menu-bound="true" aria-haspopup="menu" aria-expanded="false" aria-label="Actions" title="Actions">
      <span class="material-symbols-outlined">more_vert</span>
    </button>
    <div class="ro-row-menu" hidden role="menu">${itemsHtml}</div>
  </div>`;
}

function notificationRowMenu(item) {
  const detailHref = `notification-detail-panel.html?notification_id=${item.id}`;
  const story = notificationStory(item);
  return cardKebabMenu(`
      <button type="button" role="menuitem" data-route="${escapeLiveHtml(detailHref)}">What happened</button>
      ${story.unread
        ? `<button type="button" role="menuitem" data-notification-read="true">Got it</button>`
        : `<button type="button" role="menuitem" disabled>Seen</button>`}`);
}

function renderNotificationDetailPanel(item) {
  const surface = document.querySelector("[data-overlay-surface='true']");
  if (!surface || !item) return false;
  const story = notificationStory(item);
  const urgent = story.priority === "high" || story.priority === "critical";
  surface.innerHTML = `<div class="flex h-full min-h-0 flex-col">
    <div class="flex items-center justify-between gap-3 border-b border-border px-5 py-4">
      <div class="flex min-w-0 items-center gap-3">
        <div class="flex h-10 w-10 items-center justify-center rounded-full ${story.unread ? "bg-primary text-white" : "bg-surface-alt text-primary"}">
          <span class="material-symbols-outlined">${escapeLiveHtml(story.icon)}</span>
        </div>
        <div class="min-w-0">
          <p class="text-[11px] font-bold uppercase tracking-wider text-text-muted">${escapeLiveHtml(story.category)}</p>
          <h2 class="truncate font-headline-md font-bold text-on-surface">${escapeLiveHtml(story.eventLabel)}</h2>
        </div>
      </div>
      <button class="rounded-lg p-2 text-text-muted hover:bg-highlight-soft hover:text-on-surface" type="button" data-overlay-close="true" aria-label="Close overlay" title="Close overlay">
        <span class="material-symbols-outlined">close</span>
      </button>
    </div>
    <div class="flex-1 space-y-5 overflow-y-auto px-5 py-5">
      <p class="text-body-md leading-relaxed text-on-surface">${escapeLiveHtml(story.headline)}</p>
      ${urgent ? `<p class="rounded-lg border border-warning-text/20 bg-warning-bg px-3 py-2 text-body-sm text-warning-text">This is marked ${escapeLiveHtml(story.priority)} priority.</p>` : ""}
      ${notificationFlowHtml(item, false)}
      <dl class="grid grid-cols-2 gap-4 border-t border-border pt-4 text-body-sm">
        <div><dt class="text-[11px] font-bold uppercase tracking-wider text-text-muted">When</dt><dd class="mt-1 text-on-surface">${escapeLiveHtml(story.happened)}</dd></div>
        <div><dt class="text-[11px] font-bold uppercase tracking-wider text-text-muted">Inbox</dt><dd class="mt-1 text-on-surface">${story.unread ? "New" : "Seen"}</dd></div>
      </dl>
    </div>
    <div class="flex items-center justify-end gap-2 border-t border-border px-5 py-3" data-notification-id="${item.id}">
      ${story.unread
        ? `<button class="h-8 rounded-lg bg-primary px-3 text-[13px] font-semibold text-white hover:bg-primary-hover" type="button" data-notification-read="true">Got it</button>`
        : `<span class="text-[12px] font-semibold text-text-muted">Seen</span>`}
    </div>
  </div>`;
  return true;
}

function renderNotificationsCommandCenter(items, meta) {
  const surface = document.querySelector("[data-notifications-command-center]");
  if (!surface) return false;

  const unreadTotal = Number(meta?.unread_total ?? 0);
  const highCount = items.filter((item) => item.status === "unread" && ["high", "critical"].includes(String(item.priority || "").toLowerCase())).length;
  const metrics = surface.querySelectorAll(".grid-cols-3 .font-headline-md");
  if (metrics[0]) metrics[0].textContent = String(unreadTotal);
  if (metrics[1]) metrics[1].textContent = String(highCount);
  if (metrics[2]) metrics[2].textContent = String(items.length);
  const metricLabels = surface.querySelectorAll(".grid-cols-3 .font-label-caps");
  if (metricLabels[2] && /mention/i.test(metricLabels[2].textContent || "")) metricLabels[2].textContent = "In view";

  const intro = surface.querySelector("h1 + p");
  if (intro) intro.textContent = "Each item is a hiring event: what changed, whether it still needs you, and the next step.";

  const pill = Array.from(surface.querySelectorAll("span")).find((span) => /priority alert|urgent event/i.test(span.textContent || ""));
  if (pill) pill.textContent = `${highCount} urgent event${highCount === 1 ? "" : "s"}`;

  const queueHeading = Array.from(surface.querySelectorAll("h2")).find((heading) => /action queue|what happened/i.test(heading.textContent || ""));
  if (queueHeading) {
    queueHeading.textContent = "What happened";
    const subtitle = queueHeading.nextElementSibling;
    if (subtitle) subtitle.textContent = "Newest events first. Stay here to see what happened; hover a row for actions.";
    const headerRow = queueHeading.closest("div.flex");
    let slot = headerRow?.querySelector("[data-mark-all-read-slot]");
    if (headerRow && !slot) {
      slot = document.createElement("div");
      slot.dataset.markAllReadSlot = "true";
      slot.className = "flex items-center gap-2 shrink-0";
      headerRow.appendChild(slot);
    }
    if (slot) {
      /* AI Triage applies to the unread backlog; show it alongside
         Mark-all-read whenever there is something unread. */
      const canTriage = typeof hasPermission === "function" && hasPermission("ai.agent.inbox_triage");
      slot.innerHTML = `${unreadTotal > 0 && canTriage
        ? `<button type="button" data-live-notifications-triage class="flex items-center gap-1.5 rounded-lg border border-primary/40 bg-highlight-soft px-3 py-1.5 font-data-tabular text-data-tabular font-semibold text-primary hover:bg-primary hover:text-on-primary transition-colors shrink-0" aria-label="Start AI triage review of ${unreadTotal} unread notifications"><span class="material-symbols-outlined text-[16px]" aria-hidden="true">smart_toy</span>AI Triage</button>`
        : ""}${unreadTotal > 0
        ? `<button type="button" data-live-notifications-mark-all-read class="flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 font-data-tabular text-data-tabular font-semibold text-secondary hover:bg-highlight-soft transition-colors shrink-0" aria-label="Mark all ${unreadTotal} unread notifications as read"><span class="material-symbols-outlined text-[16px]" aria-hidden="true">done_all</span><span data-mark-all-label>Mark all read</span></button>`
        : ""}`;
    }
  }
  const list = queueHeading?.closest("section")?.querySelector(".divide-y");
  if (!list) return false;

  list.innerHTML = items.length
    ? items.map((item) => {
        const story = notificationStory(item);
        const urgent = story.priority === "high" || story.priority === "critical";
        return `<article class="notification-event group relative grid gap-3 p-4 transition-colors hover:bg-highlight-soft md:grid-cols-[auto_minmax(0,1fr)_auto] md:items-start${story.unread ? " border-l-4 border-primary bg-highlight-soft/40" : ""}" data-notification-id="${item.id}" data-notification-status="${escapeLiveHtml(item.status || "read")}" data-filter-category="${escapeLiveHtml(story.category)}" data-filter-priority="${escapeLiveHtml(story.priority || "")}">
          <div class="flex h-10 w-10 items-center justify-center rounded-xl ${story.unread ? "bg-primary text-white" : "bg-surface-alt text-primary"}">
            <span class="material-symbols-outlined">${escapeLiveHtml(story.icon)}</span>
          </div>
          <div class="min-w-0">
            <div class="mb-1 flex flex-wrap items-center gap-2">
              <span class="rounded border border-border bg-surface px-1.5 py-0.5 font-label-caps text-label-caps uppercase tracking-wider text-secondary">${escapeLiveHtml(story.category)}</span>
              <span class="font-data-tabular text-[11px] text-text-muted">${escapeLiveHtml(story.happened)}</span>
              ${story.unread ? '<span data-notification-unread-indicator class="rounded-full bg-primary px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">New</span>' : ""}
              ${urgent ? `<span class="rounded-full bg-warning-bg px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-warning-text">${escapeLiveHtml(story.priority)}</span>` : ""}
            </div>
            <h3 class="font-headline-sm text-headline-sm text-on-surface">${escapeLiveHtml(story.eventLabel)}</h3>
            <p class="mt-1 font-body-sm text-body-sm text-on-surface">${escapeLiveHtml(story.headline)}</p>
            ${notificationFlowHtml(item, true)}
          </div>
          <div class="flex items-start justify-end">
            ${notificationRowMenu(item)}
          </div>
        </article>`;
      }).join("")
    : `<div class="p-6 text-center text-body-sm text-text-muted">No ${escapeLiveHtml(notificationFilterLabel())} events. Try the "All" filter to see what already happened.</div>`;

  const nextItem = items.find((item) => String(item.status).toLowerCase() === "unread") || items[0];
  const nextStory = nextItem ? notificationStory(nextItem) : null;
  const aside = queueHeading?.closest(".grid")?.querySelector("aside");
  if (aside) {
    aside.innerHTML = `<section class="rounded-2xl border border-border bg-surface p-4 shadow-sm">
        <h2 class="font-headline-sm text-headline-sm text-on-surface">Next up</h2>
        ${nextStory ? `<p class="mt-3 font-body-sm font-semibold text-on-surface">${escapeLiveHtml(nextStory.eventLabel)}</p>
        <p class="mt-1 font-body-sm text-body-sm text-text-muted">${escapeLiveHtml(nextStory.headline)}</p>
        <p class="mt-3 text-[12px] text-text-muted">${escapeLiveHtml(nextStory.waiting)} → ${escapeLiveHtml(nextStory.cta)}</p>` : `<p class="mt-3 font-body-sm text-body-sm text-text-muted">Nothing is waiting. New hiring events will land here.</p>`}
      </section>
      <section class="rounded-2xl border border-border bg-surface p-4 shadow-sm">
        <h2 class="font-headline-sm text-headline-sm text-on-surface">Suggested next step</h2>
        <p class="mt-3 font-body-sm text-body-sm text-on-surface">${escapeLiveHtml(nextStory ? nextStory.next : "You are caught up.")}</p>
      </section>
      <section class="rounded-2xl border border-border bg-surface p-4 shadow-sm">
        <h2 class="font-headline-sm text-headline-sm text-on-surface">Inbox</h2>
        <dl class="mt-3 grid gap-2 font-body-sm text-body-sm">
          <div class="flex justify-between gap-3"><dt class="text-text-muted">New</dt><dd class="font-semibold text-on-surface">${unreadTotal}</dd></div>
          <div class="flex justify-between gap-3"><dt class="text-text-muted">Urgent</dt><dd class="font-semibold text-on-surface">${highCount}</dd></div>
          <div class="flex justify-between gap-3"><dt class="text-text-muted">Showing</dt><dd class="font-semibold text-on-surface">${items.length}</dd></div>
        </dl>
      </section>`;
  }

  if (typeof applyCollectionPagination === "function") {
    delete list.dataset.pageSize;
    list.dataset.page = "1";
    applyCollectionPagination(list);
  }
  if (typeof wireHoverKebabMenus === "function") wireHoverKebabMenus(list);
  if (typeof wireNotificationListInteractions === "function") wireNotificationListInteractions(list);
  if (typeof hydrateLiveFilters === "function") hydrateLiveFilters(surface);
  surface.querySelectorAll("button").forEach((button) => {
    if (/load older notifications/i.test(button.textContent || "")) {
      button.closest(".flex.justify-center")?.setAttribute("hidden", "hidden");
    }
  });
  return true;
}


function businessTitleLevel(item) {
  const title = String(item.title || "").toLowerCase();
  if (/\b(vp|vice president|chief|head of)\b/.test(title)) return "VP";
  if (/\b(director)\b/.test(title)) return "Director";
  if (/\b(lead|principal|staff|manager)\b/.test(title)) return "Lead";
  if (/\b(senior|sr\.?)\b/.test(title)) return "Senior";
  if (String(item.priority || "").toLowerCase() === "critical") return "Senior";
  if (/\b(junior|jr\.?|associate|coordinator|analyst)\b/.test(title)) return "Junior";
  return "Mid";
}

function businessTitleCategory(item) {
  const text = `${item.title || ""} ${item.job_description || ""} ${(item.must_have_skills || []).join(" ")}`.toLowerCase();
  if (/design|ux|ui|product designer/.test(text)) return "Design";
  if (/product/.test(text)) return "Product";
  if (/market|brand|growth/.test(text)) return "Marketing";
  if (/sales|account executive|revenue/.test(text)) return "Sales";
  if (/operation|coordinator|delivery/.test(text)) return "Operations";
  return "Engineering";
}

function levelBadgeClass(level) {
  if (level === "VP" || level === "Director") return "bg-danger-bg text-danger-text border-tertiary-fixed-dim";
  if (level === "Lead") return "bg-warning-bg text-warning-text border-highlight-soft";
  if (level === "Senior") return "bg-primary-container text-on-primary border-primary-fixed-dim";
  if (level === "Junior") return "bg-info-bg text-info-text border-outline-variant";
  return "bg-success-bg text-success-text border-primary-fixed-dim";
}/* ═══════════════════════════════════════════════════════════════
   DELIVERY & ASSIGNMENT RENDERERS
   ═══════════════════════════════════════════════════════════════ */

function workQueueStatus(item) {
  const priority = String(item.priority || "").toLowerCase();
  if (priority === "critical" || /overdue/i.test(item.age_label || "")) {
    return { dot: "bg-danger-text", badge: "bg-danger-bg text-danger-text", label: item.age_label || "Overdue" };
  }
  if (priority === "high") return { dot: "bg-warning-text", badge: "bg-warning-bg text-warning-text", label: item.age_label || "High priority" };
  return { dot: "bg-primary", badge: "bg-info-bg text-info-text", label: item.age_label || "Open" };
}

function renderDeliveryWorkRow(item, index, pipelineByEntity) {
  const status = workQueueStatus(item);
  const pipeline = pipelineByEntity.get(`${item.entity_type}:${item.entity_id}`) || pipelineByEntity.get(`requisition:${item.entity_id}`) || {};
  const candidate = pipeline.candidate_name || item.title || "Work item";
  const requisition = pipeline.requisition_title || item.description || item.entity_type || "Recruiting work";
  const route = item.route_href || (pipeline.application_id ? `candidate-screening.html?application_id=${pipeline.application_id}` : "requisition-detail.html");
  const action = workflowEndpointForLabel(item.primary_action_label);
  return `<div class="group grid min-h-[44px] grid-cols-12 items-center gap-4 border-b border-border px-inset-card py-2 transition-colors hover:bg-highlight-soft" data-live-delivery-row="true" data-action-item-id="${item.id}">
    <div class="col-span-1 flex items-center gap-2">
      <span class="h-1.5 w-1.5 rounded-full ${status.dot}"></span>
      <span class="font-data-tabular text-data-tabular font-semibold text-on-surface">${index + 1}</span>
    </div>
    <div class="col-span-4 min-w-0">
      <p class="truncate font-data-tabular text-data-tabular font-semibold text-on-surface">${escapeLiveHtml(candidate)}</p>
      <p class="truncate text-body-sm text-text-muted">${escapeLiveHtml(requisition)}</p>
    </div>
    <div class="col-span-2 truncate font-data-tabular text-data-tabular text-on-surface">${escapeLiveHtml(pipeline.current_stage || titleFromCode(item.source || item.entity_type || "Queue"))}</div>
    <div class="col-span-2">
      <span class="inline-flex rounded px-2 py-0.5 text-label-caps font-bold ${status.badge}">${escapeLiveHtml(status.label)}</span>
    </div>
    <div class="col-span-3 flex justify-end">
      ${cardKebabMenu(`
        <button type="button" role="menuitem" data-route="${escapeLiveHtml(route)}">Open</button>
        <button type="button" role="menuitem" data-live-workflow-action="${action}" data-action-item-id="${item.id}">${escapeLiveHtml(item.primary_action_label || "Do Now")}</button>`)}
    </div>
  </div>`;
}function renderAvailableUserRow(user, requisitionId) {
  return `<div class="px-4 py-3 flex items-center justify-between hover:bg-highlight-soft transition-colors" data-live-available-user="true" data-user-id="${user.id}">
    <div class="flex min-w-0 items-center gap-3">
      <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-secondary-container text-sm font-bold text-on-secondary-container">${escapeLiveHtml(personInitials(user.full_name))}</div>
      <div class="min-w-0">
        <p class="truncate font-semibold text-on-surface">${escapeLiveHtml(user.full_name || "User")}</p>
        <p class="font-body-sm text-[11px] text-text-muted">${escapeLiveHtml(user.role || "")} · ${escapeLiveHtml(user.email || "")}</p>
      </div>
    </div>
    <button class="inline-flex min-h-8 items-center gap-1 rounded-lg bg-primary px-2.5 text-[12px] font-semibold text-on-primary transition-colors hover:bg-primary-hover" type="button" data-live-assign-user="true" data-user-id="${user.id}" data-requisition-id="${requisitionId || ""}">
      <span class="material-symbols-outlined text-[14px]">person_add</span>Assign
    </button>
  </div>`;
}


/* ═══════════════════════════════════════════════════════════════
   PIPELINE HISTORY
   ═══════════════════════════════════════════════════════════════ */

function pipelineHistoryIcon(item) {
  const action = String(item.action || (item.to_stage ? "stage" : "")).toLowerCase();
  if (/create|sourced|added/.test(action)) return "add_circle";
  if (/move|stage|advance/.test(action)) return "swap_horiz";
  if (/reject|decline|withdraw/.test(action)) return "cancel";
  if (/offer|extend/.test(action)) return "request_quote";
  if (/hire|join/.test(action)) return "check_circle";
  if (/comment|note|update/.test(action)) return "comment";
  return "radio_button_unchecked";
}

function renderPipelineHistoryItems(host, items) {
  if (!host) return;
  host.innerHTML = items.length
    ? items.map((item) => `<div class="flex items-start gap-3 py-3" data-live-pipeline-history-row="true">
        <span class="material-symbols-outlined text-[20px] text-primary mt-0.5">${pipelineHistoryIcon(item)}</span>
        <div class="min-w-0 flex-1">
          <p class="text-body-sm font-medium text-on-surface">${escapeLiveHtml(item.action || (item.to_stage ? (item.from_stage && item.from_stage !== item.to_stage ? `${item.from_stage} → ${item.to_stage}` : `Stage: ${item.to_stage}`) : "Stage change"))}</p>
          <p class="text-[11px] text-text-muted">${escapeLiveHtml(item.actor_name || item.changed_by_name || "System")} · ${escapeLiveHtml(relativeTime(item.created_at || item.changed_at))}</p>
          ${(item.notes || item.change_reason) ? `<p class="mt-1 text-[11px] text-text-muted">${escapeLiveHtml(item.notes || item.change_reason)}</p>` : ""}
        </div>
      </div>`).join("")
    : `<div class="p-4 text-body-sm text-text-muted">No history records returned by the API.</div>`;
}


/* ═══════════════════════════════════════════════════════════════
   DAILY UPDATE RENDERERS
   ═══════════════════════════════════════════════════════════════ */function renderDailyUpdateSubmissionCard(item) {
  return `<div class="p-4 border-b border-border bg-surface hover:bg-highlight-soft transition-colors group">
    <div class="flex justify-between items-start mb-2">
      <div>
        <h4 class="font-data-tabular font-semibold text-primary">${escapeLiveHtml(item.requisition_title || "Daily Update")}</h4>
        <span class="font-body-sm text-text-muted text-xs">${escapeLiveHtml(relativeTime(item.submitted_at || item.created_at))}</span>
      </div>
      <span class="px-2 py-0.5 rounded text-label-caps font-label-caps ${dailyUpdateStatusMeta(item).badge}">${escapeLiveHtml(dailyUpdateStatusMeta(item).label)}</span>
    </div>
    <p class="font-body-sm text-on-surface-variant line-clamp-2">${escapeLiveHtml(item.progress_summary || item.summary || "No summary provided.")}</p>
  </div>`;
}

function dailyUpdateStatusMeta(item) {
  const status = String(item?.submission_status || item?.review_status || item?.status || "").toLowerCase();
  if (/draft/.test(status)) return { label: "Draft", badge: "bg-surface-dim text-text-muted border-border" };
  if (/acknowledged|approved|reviewed/.test(status)) return { label: "Reviewed", badge: "bg-success-bg text-success-text border-[#C5DBC8]" };
  if (/pending|submitted/.test(status)) return { label: "Pending Review", badge: "bg-warning-bg text-warning-text border-[#E8D1B5]" };
  if (/feedback|rejected/.test(status)) return { label: "Feedback", badge: "bg-danger-bg text-danger-text border-[#E6C6C1]" };
  return { label: "Pending", badge: "bg-warning-bg text-warning-text border-[#E8D1B5]" };
}function renderDailyUpdateTableRow(item) {
  const status = dailyUpdateStatusMeta(item);
  return `<tr class="cursor-pointer hover:bg-highlight-soft transition-colors" data-daily-update-id="${item.id}" data-route="daily-update-detail-panel.html?daily_update_id=${item.id}">
    <td class="py-2 px-4 text-on-surface font-medium">${escapeLiveHtml(item.requisition_title || "Update")}</td>
    <td class="py-2 px-4 text-text-muted">${escapeLiveHtml(item.submitted_by_name || "Unknown")}</td>
    <td class="py-2 px-4"><span class="inline-flex items-center rounded border px-2 py-0.5 text-[10px] font-semibold ${status.badge}">${escapeLiveHtml(status.label)}</span></td>
    <td class="py-2 px-4 text-text-muted text-sm">${escapeLiveHtml(relativeTime(item.submitted_at || item.created_at))}</td>
  </tr>`;
}function renderDailyUpdatesReview(items, meta = {}) {
  const surface = document.querySelector(".workspace-surface");
  if (!surface) return;
  const tbody = surface.querySelector("tbody");
  if (tbody) {
    tbody.innerHTML = items.length
      ? items.map((item) => renderDailyUpdateTableRow(item)).join("")
      : `<tr><td class="px-4 py-6 text-text-muted" colspan="4">No daily updates returned by the API.</td></tr>`;
    const table = tbody.closest("table");
    if (table && typeof applyClientPagination === "function") {
      delete table.dataset.pageSize;
      table.dataset.page = "1";
      applyClientPagination(table);
    }
  }
  const count = (key, value) => { const node = surface.querySelector(`[data-review-count="${key}"]`); if (node) node.textContent = String(value); };
  const todayKey = new Date().toISOString().slice(0, 10);
  const blocked = items.filter((item) => String(item.blockers || "").trim());
  count("total", meta.total ?? items.length);
  count("today", items.filter((item) => String(item.update_date || item.submitted_at || "").slice(0, 10) === todayKey).length);
  count("blocked", blocked.length);
  count("drafts", items.filter((item) => /draft/i.test(String(item.submission_status || ""))).length);
  const rail = surface.querySelector("[data-review-blockers]");
  if (rail) {
    rail.innerHTML = blocked.length
      ? blocked.slice(0, 10).map((item) => `<li class="py-2"><a class="block hover:bg-highlight-soft" href="daily-update-detail-panel.html?daily_update_id=${item.id}">
          <p class="font-body-sm text-body-sm font-semibold text-on-surface">${escapeLiveHtml(item.submitted_by_name || "Unknown")} · <span class="font-normal text-text-muted">${escapeLiveHtml(item.requisition_title || "")}</span></p>
          <p class="font-body-sm text-body-sm text-on-surface-variant">${escapeLiveHtml(String(item.blockers).slice(0, 160))}</p></a></li>`).join("")
      : '<li class="py-2 font-body-sm text-body-sm text-text-muted">No blockers reported.</li>';
  }
}

function formatOfferMoney(amount, currency) {
  if (amount === null || amount === undefined || amount === "") return "—";
  const value = Number(amount);
  if (Number.isNaN(value)) return String(amount);
  const code = String(currency || "USD").toUpperCase();
  try {
    return `${new Intl.NumberFormat("en-IN", { style: "currency", currency: code, maximumFractionDigits: 0 }).format(value)}/yr`;
  } catch {
    return `${code} ${Math.round(value).toLocaleString("en-IN")}/yr`;
  }
}

function formatOfferDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function offerStatusMeta(status) {
  const key = String(status || "").toLowerCase();
  if (key === "accepted" || key === "joined") return { label: "ACCEPTED", badge: "bg-success-bg text-success-text border-primary-fixed-dim" };
  if (key === "sent") return { label: "SENT", badge: "bg-info-bg text-info-text border-outline-variant" };
  if (key === "pending-approval" || key === "pending_approval" || key === "pending") return { label: "PENDING APPROVAL", badge: "bg-warning-bg text-warning-text border-highlight-soft" };
  if (key === "declined" || key === "rejected") return { label: "DECLINED", badge: "bg-danger-bg text-danger-text border-tertiary-fixed-dim" };
  if (key === "approved") return { label: "APPROVED", badge: "bg-success-bg text-success-text border-primary-fixed-dim" };
  return { label: "DRAFT", badge: "bg-surface-alt text-text-muted border-border" };
}

function renderOffers(items = [], meta = {}) {
  const list = Array.isArray(items) ? items : [];
  fillExistingTable(list, (row, item) => {
    const cells = row.querySelectorAll("td");
    setStackedCell(cells[0], item.candidate_name || "—", item.candidate_email || "");
    const avatar = cells[0]?.querySelector(".rounded-full, .w-8.h-8");
    if (avatar) avatar.textContent = personInitials(item.candidate_name);
    setStackedCell(cells[1], item.requisition_title || "—", item.requisition_code || (item.requisition_id ? `REQ-${item.requisition_id}` : ""));
    const offerCodeNode = cells[1]?.querySelector(".font-label-caps, .text-xs, .font-body-sm, p.font-body-sm, .text-text-muted");
    if (offerCodeNode && typeof entityBadgeHtml === "function" && item.requisition_code && !offerCodeNode.querySelector(".entity-badge")) {
      offerCodeNode.insertAdjacentHTML("afterend", entityBadgeHtml(item.requisition_code, ""));
    }
    const bonus = item.signing_bonus ? `+ ${formatOfferMoney(item.signing_bonus, item.offer_currency).replace("/yr", "")}` : "";
    setStackedCell(cells[2], formatOfferMoney(item.offered_ctc, item.offer_currency), bonus);
    const status = offerStatusMeta(item.offer_status);
    const statusNode = cells[3]?.querySelector("span") || cells[3];
    if (statusNode) {
      statusNode.className = `inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border ${status.badge}`;
      statusNode.textContent = status.label;
    }
    const approval = String(item.approval_status || item.offer_status || "").toLowerCase();
    const approvalIcon = cells[4]?.querySelector(".material-symbols-outlined") || cells[4];
    if (approvalIcon) {
      if (/approved|accepted|joined|sent/.test(approval) && !/pending/.test(approval)) {
        approvalIcon.textContent = "check_circle";
        approvalIcon.className = "material-symbols-outlined text-success-text text-[20px]";
        approvalIcon.style.fontVariationSettings = "'FILL' 1";
      } else if (/pending/.test(approval)) {
        approvalIcon.textContent = "pending";
        approvalIcon.className = "material-symbols-outlined text-warning-text text-[20px]";
      } else {
        approvalIcon.textContent = "—";
        approvalIcon.className = "text-text-muted";
      }
    }
    setCellValue(cells[5], item.offer_sent_at ? formatOfferDate(item.offer_sent_at) : "—");
    setCellValue(cells[6], item.expected_joining_date ? formatOfferDate(item.expected_joining_date) : (item.offer_sent_at && /accepted|joined/.test(String(item.offer_status || "").toLowerCase()) ? formatOfferDate(item.updated_at) : "—"));
    row.dataset.recordId = item.id || item.application_id || "";
    const offerParams = new URLSearchParams();
    if (item.id) offerParams.set("offer_id", item.id);
    if (item.candidate_id) offerParams.set("candidate_id", item.candidate_id);
    if (item.requisition_id) offerParams.set("requisition_id", item.requisition_id);
    row.dataset.route = `offer-create-dialog.html?${offerParams.toString()}`;
    row.classList.add("cursor-pointer");
  });

  const counts = {
    draft: 0,
    pending: 0,
    sent: 0,
    accepted: 0,
    declined: 0,
  };
  list.forEach((item) => {
    const key = String(item.offer_status || "").toLowerCase();
    if (key === "accepted" || key === "joined") counts.accepted += 1;
    else if (key === "sent") counts.sent += 1;
    else if (key === "pending-approval" || key === "pending_approval" || key === "pending") counts.pending += 1;
    else if (key === "declined" || key === "rejected") counts.declined += 1;
    else counts.draft += 1;
  });
  const metricValues = document.querySelectorAll(".workspace-surface .grid .font-headline-lg, [data-layout='metric-strip'] .font-headline-lg, [data-layout='metric-card'] .font-headline-lg");
  const metricOrder = [counts.draft, counts.pending, counts.sent, counts.accepted, counts.declined];
  metricValues.forEach((node, index) => {
    if (metricOrder[index] !== undefined) node.textContent = String(metricOrder[index]);
  });
  const footerText = document.querySelector(".workspace-surface .border-t span");
  if (footerText) {
    const total = meta.total || list.length;
    footerText.textContent = `${list.length} of ${total}`;
  }
}


/* ═══════════════════════════════════════════════════════════════
   LOCATION RENDERERS
   ═══════════════════════════════════════════════════════════════ *//* ═══════════════════════════════════════════════════════════════
   TEAM WORKLOAD & USER PERFORMANCE
   ═══════════════════════════════════════════════════════════════ */

function buildWorkloadMembers(users, requisitions, candidates) {
  return (users || []).map((user) => {
    const activeReqs = (requisitions || []).filter((r) => r.primary_owner_user_id === user.id && ["open", "active", "sourcing"].includes(String(r.status || "").toLowerCase())).length;
    const activeCandidates = (candidates || []).filter((c) => c.owner_user_id === user.id && ["active", "sourced", "screened"].includes(String(c.profile_status || "").toLowerCase())).length;
    const utilization = Math.min(100, Math.round(activeReqs * 18 + activeCandidates * 12));
    return { ...user, activeReqs, activeCandidates, utilization };
  });
}

/* Utilization band for the team workload bars: >85% is overloaded,
   <40% has spare capacity. */
function workloadStatus(utilization) {
  const value = Number(utilization) || 0;
  if (value > 85) return { label: "Overloaded", barClass: "bg-error", textClass: "text-danger-text" };
  if (value >= 40) return { label: "Balanced", barClass: "bg-primary", textClass: "text-on-surface" };
  return { label: "Capacity", barClass: "bg-success-text", textClass: "text-success-text" };
}

function teamWorkloadStatusColor(utilization) {
  const value = Number(utilization) || 0;
  if (value > 85) return (window.RoCharts && window.RoCharts.STATUS.critical) || "#a63d33";
  if (value >= 40) return "#2a78d6";
  return (window.RoCharts && window.RoCharts.STATUS.good) || "#217a46";
}

function renderTeamWorkloadKpis(members) {
  const host = document.querySelector("[data-workload-kpis]");
  if (!host) return;
  const total = members.reduce((sum, m) => sum + m.activeReqs + m.activeCandidates, 0);
  const avgUtil = members.length ? Math.round(members.reduce((sum, m) => sum + m.utilization, 0) / members.length) : 0;
  const overloaded = members.filter((m) => m.utilization > 85).length;
  const available = members.filter((m) => m.utilization < 40).length;
  const tiles = [
    { label: "Total Active Assignments", value: String(total), icon: "assignment", hint: `${members.length} team member${members.length === 1 ? "" : "s"}`, hintClass: "text-text-muted" },
    { label: "Avg Utilization", value: `${avgUtil}%`, icon: "speed", hint: avgUtil > 85 ? "Team is stretched thin" : "Across the team", hintClass: avgUtil > 85 ? "text-danger-text" : "text-text-muted" },
    { label: "Overloaded Members", value: String(overloaded), icon: "warning", hint: overloaded ? "Over 85% utilization" : "None over capacity", hintClass: overloaded ? "text-danger-text" : "text-success-text" },
    { label: "Available Capacity", value: String(available), icon: "check_circle", hint: available ? `${available} team member${available === 1 ? "" : "s"} under 40%` : "No spare capacity", hintClass: "text-text-muted" },
  ];
  host.innerHTML = tiles
    .map(
      (t) => `<div class="metric-card bg-surface border border-outline-variant rounded-lg p-4">
        <div class="flex items-center justify-between mb-2">
          <span class="text-label-caps font-bold text-text-muted uppercase tracking-wider">${escapeLiveHtml(t.label)}</span>
          <span class="material-symbols-outlined text-[20px] text-primary">${t.icon}</span>
        </div>
        <p class="text-headline-lg font-bold text-on-surface">${escapeLiveHtml(t.value)}</p>
        <p class="text-body-sm ${t.hintClass} mt-1">${escapeLiveHtml(t.hint)}</p>
      </div>`
    )
    .join("");
}

function renderTeamWorkloadCapacityChart(members) {
  const host = document.querySelector("[data-workload-capacity-chart]");
  if (!host || !window.RoCharts) return;
  const sorted = [...members].sort((a, b) => b.utilization - a.utilization).slice(0, 10);
  window.RoCharts.bar(host, {
    items: sorted.map((m) => ({ label: m.full_name || "Team member", value: m.utilization, color: teamWorkloadStatusColor(m.utilization) })),
    format: "percent",
    empty: "No team members to show capacity for yet.",
    labelHeader: "Team member",
    valueHeader: "Utilization",
    ariaLabel: "Team member utilization",
  });
}

function renderTeamWorkloadByRole(members) {
  const host = document.querySelector("[data-workload-role-chart]");
  if (!host || !window.RoCharts) return;
  const byRole = new Map();
  members.forEach((m) => {
    const role = m.primary_role_name || "Unassigned role";
    byRole.set(role, (byRole.get(role) || 0) + m.activeReqs + m.activeCandidates);
  });
  const items = Array.from(byRole.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([label, value], i) => ({ label, value, color: window.RoCharts.CATEGORICAL[i % window.RoCharts.CATEGORICAL.length] }));
  window.RoCharts.bar(host, { items, empty: "No active assignments yet.", labelHeader: "Role", valueHeader: "Assignments", ariaLabel: "Active assignments by role" });
}

function renderTeamWorkloadRows(members) {
  return members.map((member) => {
    const status = workloadStatus(member.utilization);
    return `<tr class="hover:bg-highlight-soft transition-colors">
      <td class="py-2 px-4"><div class="flex items-center gap-3"><div class="flex h-8 w-8 items-center justify-center rounded-full bg-primary-container text-[11px] font-bold text-on-primary-container">${escapeLiveHtml(personInitials(member.full_name))}</div><span class="font-medium text-on-surface">${escapeLiveHtml(member.full_name || "Team member")}</span></div></td>
      <td class="py-2 px-4 text-data-tabular text-on-surface">${member.activeReqs}</td>
      <td class="py-2 px-4 text-data-tabular text-on-surface">${member.activeCandidates}</td>
      <td class="py-2 px-4"><div class="flex items-center gap-2"><div class="h-2 w-24 rounded-full bg-outline-variant"><div class="h-2 rounded-full ${status.barClass}" style="width:${member.utilization}%"></div></div><span class="text-[11px] ${status.textClass}">${member.utilization}%</span></div></td>
    </tr>`;
  }).join("");
}

function buildUserPerformanceMembers(users, requisitions, candidates, offers) {
  return (users || []).map((user) => {
    const submitted = (candidates || []).filter((c) => c.owner_user_id === user.id).length;
    const hired = (offers || []).filter((o) => o.owner_user_id === user.id && (o.application_status === "joined" || String(o.offer_status || "").toLowerCase() === "accepted")).length;
    const activeReqs = (requisitions || []).filter((r) => r.primary_owner_user_id === user.id && ["open", "active"].includes(String(r.status || "").toLowerCase())).length;
    return { ...user, submitted, hired, activeReqs };
  });
}

function userPerformanceConversion(member) {
  if (!member.submitted) return null;
  return Math.round((member.hired / member.submitted) * 100);
}

function renderUserPerformanceRows(members) {
  return members.map((member) => {
    const conversion = userPerformanceConversion(member);
    const badge = conversion == null ? "bg-surface-alt text-text-muted" : conversion >= 20 ? "bg-success-bg text-success-text" : conversion >= 8 ? "bg-warning-bg text-warning-text" : "bg-surface-alt text-on-surface";
    return `<tr class="hover:bg-highlight-soft transition-colors">
    <td class="py-2 px-4"><div class="flex items-center gap-3"><div class="flex h-8 w-8 items-center justify-center rounded-full bg-primary-container text-[11px] font-bold text-on-primary-container">${escapeLiveHtml(personInitials(member.full_name))}</div><span class="font-medium text-on-surface">${escapeLiveHtml(member.full_name || "User")}</span></div></td>
    <td class="py-2 px-4 text-data-tabular text-on-surface text-right">${member.submitted}</td>
    <td class="py-2 px-4 text-data-tabular text-success-text font-semibold text-right">${member.hired}</td>
    <td class="py-2 px-4 text-data-tabular text-on-surface text-right">${member.activeReqs}</td>
    <td class="py-2 px-4 text-right"><span class="px-2 py-0.5 rounded ${badge} text-label-caps font-semibold">${conversion == null ? "—" : `${conversion}%`}</span></td>
  </tr>`;
  }).join("");
}

function renderUserPerformanceTriage(members) {
  const host = findPanelByHeading("Performance Triage");
  if (!host) return;
  const sorted = [...members].sort((a, b) => b.hired - a.hired || b.submitted - a.submitted).slice(0, 4);
  const listHost = host.querySelector(".space-y-3") || host;
  listHost.innerHTML = sorted.length
    ? sorted.map((member) => `<div class="flex items-center justify-between rounded-lg p-2 transition-colors hover:bg-highlight-soft">
        <div class="flex min-w-0 items-center gap-3">
          <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-container text-[11px] font-bold text-on-primary-container">${escapeLiveHtml(personInitials(member.full_name))}</div>
          <span class="truncate text-body-sm text-on-surface">${escapeLiveHtml(member.full_name || "User")}</span>
        </div>
        <span class="shrink-0 text-data-tabular font-semibold text-success-text">${member.hired} hires</span>
      </div>`).join("")
    : `<div class="p-2 text-body-sm text-text-muted">No performance data available.</div>`;
}

function renderUserPerformanceWorkloadChart(members) {
  const host = document.querySelector("[data-perf-workload-chart]") || findPanelByHeading("Workload Balance")?.querySelector(".ro-chart-host");
  if (!host || !window.RoCharts) return;
  const sorted = [...members].sort((a, b) => (b.submitted + b.hired + b.activeReqs) - (a.submitted + a.hired + a.activeReqs)).slice(0, 8);
  window.RoCharts.bar(host, {
    items: sorted.map((m) => ({ label: m.full_name || "User", value: m.submitted + m.hired + m.activeReqs })),
    empty: "No workload data available.",
    labelHeader: "Recruiter",
    valueHeader: "Total load",
    ariaLabel: "Workload balance across recruiters",
  });
}

function renderUserPerformanceKpis(members, avgTimeToFill) {
  const host = document.querySelector("[data-perf-kpis]");
  if (!host) return;
  const totalSubmitted = members.reduce((sum, m) => sum + m.submitted, 0);
  const totalHired = members.reduce((sum, m) => sum + m.hired, 0);
  const avgReqs = members.length ? Math.round((members.reduce((sum, m) => sum + m.activeReqs, 0) / members.length) * 10) / 10 : 0;
  const top = [...members].sort((a, b) => b.hired - a.hired)[0];
  const tiles = [
    { label: "Team Avg Time to Fill", value: avgTimeToFill != null ? `${avgTimeToFill}` : "—", unit: avgTimeToFill != null ? "days" : "", icon: "hourglass_top" },
    { label: "Total Submissions", value: String(totalSubmitted), icon: "groups", hint: `${totalHired} hired (${totalSubmitted ? Math.round((totalHired / totalSubmitted) * 100) : 0}% conversion)` },
    { label: "Avg Active Reqs / User", value: String(avgReqs), icon: "assignment", hint: `${members.length} recruiter${members.length === 1 ? "" : "s"}` },
    { label: "Top Performer", value: top && top.hired ? escapeLiveHtml(top.full_name || "—") : "—", icon: "military_tech", hint: top && top.hired ? `${top.hired} hire${top.hired === 1 ? "" : "s"}` : "No hires recorded yet" },
  ];
  host.innerHTML = tiles
    .map(
      (t) => `<div class="bg-surface border border-border p-inset-card flex flex-col justify-between rounded-lg">
        <div class="flex justify-between items-start mb-2">
          <span class="font-label-caps text-label-caps text-text-muted uppercase tracking-wide">${escapeLiveHtml(t.label)}</span>
          <span class="material-symbols-outlined text-text-muted text-[20px]">${t.icon}</span>
        </div>
        <div class="flex items-end gap-2 mt-1">
          <span class="font-headline-lg text-headline-lg text-on-surface">${t.value}<span class="text-[14px] text-text-muted font-normal ml-1">${t.unit || ""}</span></span>
        </div>
        ${t.hint ? `<p class="text-body-sm text-text-muted mt-1">${t.hint}</p>` : ""}
      </div>`
    )
    .join("");
}


/* ═══════════════════════════════════════════════════════════════
   TIME-TO-FILL & SLA
   ═══════════════════════════════════════════════════════════════ */

function renderTimeToFillBars(panelTitle, rows) {
  const panel = findPanelByHeading(panelTitle);
  if (!panel) return;
  const host = panel.querySelector(".space-y-4") || panel.querySelector(".space-y-3") || panel;
  if (!host || !window.RoCharts) return;
  window.RoCharts.bar(host, {
    items: (rows || []).map((row, i) => ({
      label: row.label || row.title || "Role",
      value: row.days || 0,
      color: row.days > (row.slaTarget || 45) ? window.RoCharts.STATUS.critical : window.RoCharts.CATEGORICAL[i % window.RoCharts.CATEGORICAL.length],
    })),
    format: "days",
    empty: "No closed requisitions to report on yet.",
    labelHeader: "Group",
    valueHeader: "Avg days to fill",
    ariaLabel: panelTitle,
  });
}

function renderTimeToFillTrend(report) {
  const panel = findPanelByHeading("Time to Fill Summary");
  const host = panel?.querySelector(".chart-placeholder") || panel?.querySelector(".p-4:last-child");
  if (!host) return;
  host.classList.remove("chart-placeholder");
  const summary = report?.summary || report || {};
  const filled = summary.filled_count || 0;
  host.innerHTML = `<div class="ro-balance-note">
    <p class="m-0 text-[28px] font-semibold tracking-tight text-on-surface">${summary.avg_days != null ? summary.avg_days : "—"}<span class="ml-1 text-[13px] font-medium text-text-muted">days average</span></p>
    <p class="ro-chart-insight">${filled
      ? `${filled} filled role${filled === 1 ? "" : "s"}. Fastest ${summary.fastest_days ?? "—"}d · slowest ${summary.slowest_days ?? "—"}d. ${summary.within_sla_percent ?? "—"}% landed inside SLA.`
      : "Not enough closed requisitions yet — department bars above will fill as roles close."}</p>
  </div>`;
}/* ═══════════════════════════════════════════════════════════════
   SOURCE EFFECTIVENESS
   ═══════════════════════════════════════════════════════════════ */

function sourceQualityMeta(row) {
  const score = row.quality_score;
  if (score == null) return `<span class="text-body-sm text-text-muted">—</span>`;
  const color = score >= 7 ? "bg-success" : score >= 4 ? "bg-warning" : "bg-error";
  return `<div class="flex items-center gap-2">
    <div class="w-16 bg-outline-variant rounded-full h-2"><div class="${color} rounded-full" style="width:${Math.round((score / 10) * 100)}%"></div></div>
    <span class="text-data-tabular text-on-surface">${score}</span>
  </div>`;
}

function renderSourceEffectivenessTable(rows) {
  const tbody = document.querySelector(".workspace-surface tbody");
  if (!tbody) return;
  tbody.innerHTML = rows.length
    ? rows.map((row) => {
        const conversion = row.conversion_rate;
        const badgeClass = conversion == null ? "bg-surface-alt text-text-muted" : conversion >= 20 ? "bg-success-bg text-success" : conversion >= 10 ? "bg-warning-bg text-warning" : "bg-surface-alt text-on-surface";
        return `<tr class="hover:bg-highlight-soft transition-colors">
      <td class="px-4 py-3 font-medium text-on-surface">${escapeLiveHtml(row.source)}</td>
      <td class="px-4 py-3 text-data-tabular text-on-surface">${row.candidates}</td>
      <td class="px-4 py-3 text-data-tabular text-success">${row.hired}</td>
      <td class="px-4 py-3"><span class="px-2 py-0.5 rounded ${badgeClass} text-label-caps font-semibold">${conversion == null ? "—" : `${conversion}%`}</span></td>
      <td class="px-4 py-3 text-data-tabular text-on-surface">${row.cost_per_hire != null ? `$${Number(row.cost_per_hire).toLocaleString()}` : "—"}</td>
      <td class="px-4 py-3">${sourceQualityMeta(row)}</td>
    </tr>`;
      }).join("")
            : `<tr><td class="px-4 py-6 text-text-muted" colspan="6">No candidate source data available yet.</td></tr>`;
}

function slaRowStatus(row) {
  if (row.status === "closed" || row.status === "filled") {
    return row.current_days <= row.sla_target_days
      ? { label: "Met", badge: "bg-success-bg text-success" }
      : { label: `Breached (+${row.current_days - row.sla_target_days}d)`, badge: "bg-danger-bg text-danger" };
  }
  const over = row.current_days - row.sla_target_days;
  if (over > 0) return { label: `Overdue +${over}d`, badge: "bg-danger-bg text-danger" };
  if (over > -6) return { label: "At risk", badge: "bg-warning-bg text-warning" };
  return { label: "On track", badge: "bg-success-bg text-success" };
}

function renderSlaCompositionChart(rows) {
  const host = document.querySelector("[data-sla-composition-chart]");
  if (!host || !window.RoCharts) return;
  let onTrack = 0, atRisk = 0, breached = 0;
  rows.forEach((row) => {
    const status = slaRowStatus(row).label;
    if (status === "Met" || status === "On track") onTrack += 1;
    else if (status === "At risk") atRisk += 1;
    else breached += 1;
  });
  window.RoCharts.donut(host, {
    segments: [
      { label: "On track", value: onTrack, color: window.RoCharts.STATUS.good },
      { label: "At risk", value: atRisk, color: window.RoCharts.STATUS.warning },
      { label: "Breached / overdue", value: breached, color: window.RoCharts.STATUS.critical },
    ],
    centerLabel: "Mandates",
    empty: "No requisitions to track yet.",
    ariaLabel: "SLA composition",
  });
}

function renderSlaBreachedList(rows) {
  const host = document.querySelector("[data-sla-breached-list]");
  if (!host) return;
  const breached = rows
    .map((row) => ({ ...row, over: row.current_days - row.sla_target_days }))
    .filter((row) => row.over > 0)
    .sort((a, b) => b.over - a.over)
    .slice(0, 6);
  host.innerHTML = breached.length
    ? breached.map((row) => `<div class="flex items-center gap-3 p-2 rounded-lg hover:bg-highlight-soft">
        <span class="material-symbols-outlined text-[20px] text-danger-text">error</span>
        <div class="flex-1 min-w-0">
          <p class="text-body-sm text-on-surface font-medium m-0 truncate">${escapeLiveHtml(row.mandate)}</p>
          <p class="text-body-sm text-text-muted m-0">${escapeLiveHtml(row.client || "No client on file")} · ${escapeLiveHtml(row.owner || "Unassigned")}</p>
        </div>
        <span class="text-data-tabular font-semibold text-danger-text shrink-0">+${row.over}d</span>
      </div>`).join("")
    : `<div class="p-2 text-body-sm text-text-muted">Nothing is over its SLA target right now.</div>`;
}

function renderSlaTrackerTable(rows) {
  const tbody = document.querySelector(".workspace-surface tbody");
  if (!tbody) return;
  tbody.innerHTML = rows.length
    ? rows.slice(0, 50).map((row) => {
        const status = slaRowStatus(row);
        return `<tr class="hover:bg-highlight-soft transition-colors">
      <td class="px-4 py-3 font-medium text-on-surface">${escapeLiveHtml(row.mandate)}</td>
      <td class="px-4 py-3 text-body-sm text-on-surface">${escapeLiveHtml(row.client || "—")}</td>
      <td class="px-4 py-3 text-data-tabular text-on-surface">${row.sla_target_days}d</td>
      <td class="px-4 py-3 text-data-tabular text-on-surface">${row.current_days}d</td>
      <td class="px-4 py-3"><span class="px-2 py-0.5 rounded ${status.badge} text-label-caps font-semibold">${status.label}</span></td>
      <td class="px-4 py-3 text-body-sm text-on-surface">${escapeLiveHtml(row.owner || "—")}</td>
    </tr>`;
      }).join("")
    : `<tr><td class="px-4 py-6 text-text-muted" colspan="6">No requisitions to track yet.</td></tr>`;
}/* ═══════════════════════════════════════════════════════════════
   MEETING RENDERERS
   ═══════════════════════════════════════════════════════════════ */

function meetingTypeLabel(value) {
  const labels = {
    client_introduction: "Client Introduction",
    requirement_discussion: "Requirement Discussion",
    follow_up: "Follow Up",
    review_meeting: "Review Meeting",
    escalation_meeting: "Escalation",
    internal_review: "Internal Review",
  };
  const normalized = String(value || "").toLowerCase().replace(/[-\s]+/g, "_");
  return labels[normalized] || normalized.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase()) || "Meeting";
}

function meetingStatusMeta(item) {
  const outcome = String(item?.outcome_status || "").toLowerCase();
  const attendance = String(item?.attendance_status || "").toLowerCase();
  if (attendance === "cancelled" || outcome === "rescheduled") {
    return { label: attendance === "cancelled" ? "Cancelled" : "Rescheduled", badge: "bg-danger-bg text-danger-text border-[#e4b6b0]", rail: "bg-error" };
  }
  if (outcome === "follow-up-required") {
    return { label: "Follow-up Required", badge: "bg-warning-bg text-warning-text border-highlight-soft", rail: "bg-warning-text" };
  }
  if (outcome === "accepted" || outcome === "closed" || attendance === "attended") {
    return { label: outcome === "closed" ? "Closed" : "Completed", badge: "bg-success-bg text-success-text border-primary-fixed-dim", rail: "bg-success-text" };
  }
  return { label: "Pending", badge: "bg-info-bg text-info-text border-outline-variant", rail: "bg-primary-container" };
}

function formatMeetingDateTime(value) {
  if (!value) return "Time TBD";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return formatWhen(value);
  return date.toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}function renderMeetingAvatars(item) {
  const attendees = Array.isArray(item?.attendees) ? item.attendees : [];
  const names = attendees.map((attendee) => attendee.attendee_name).filter(Boolean);
  if (!names.length && item?.meeting_owner_name) names.push(item.meeting_owner_name);
  return names.slice(0, 4).map((name, index) => {
    const z = 40 - index * 10;
    const extra = index === 3 && names.length > 4 ? `+${names.length - 3}` : personInitials(name);
    return `<div class="flex h-7 w-7 items-center justify-center rounded-full border-2 border-surface bg-primary-container text-[10px] font-bold text-on-primary" style="z-index:${z}">${escapeLiveHtml(extra)}</div>`;
  }).join("");
}function normalizeMeetingTypeForApi(value) {
  const normalized = String(value || "").toLowerCase().replace(/[-\s]+/g, "_");
  const typeMap = {
    standup: "internal_review",
    debrief: "review_meeting",
    client_sync: "requirement_discussion",
    kickoff: "client_introduction",
    interview_panel: "internal_review",
    other: "follow_up",
  };
  return typeMap[normalized] || normalized || "internal_review";
}


/* ═══════════════════════════════════════════════════════════════
   FOLLOW-UP RENDERERS
   ═══════════════════════════════════════════════════════════════ */

function followUpTimingMeta(item) {
  const dueDate = item?.follow_up_due_date ? new Date(item.follow_up_due_date) : null;
  if (!dueDate || Number.isNaN(dueDate.getTime())) {
    return { label: "No due date", priority: "Medium", status: "Pending", dateClass: "text-text-muted", priorityClass: "bg-warning-bg text-warning-text border-highlight-soft" };
  }
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  dueDate.setHours(0, 0, 0, 0);
  const diffDays = Math.round((dueDate - today) / 86400000);
  if (diffDays < 0) {
    return { label: formatWhen(item.follow_up_due_date).slice(0, 10), priority: "High", status: "Overdue", dateClass: "text-danger-text font-semibold", priorityClass: "bg-danger-bg text-danger-text border-[#e4b6b0]" };
  }
  if (diffDays === 0) {
    return { label: "Today", priority: "High", status: "Due Today", dateClass: "text-warning-text font-semibold", priorityClass: "bg-danger-bg text-danger-text border-[#e4b6b0]" };
  }
  if (diffDays <= 7) {
    return { label: formatWhen(item.follow_up_due_date).slice(0, 10), priority: "Medium", status: "Upcoming", dateClass: "text-on-surface", priorityClass: "bg-warning-bg text-warning-text border-highlight-soft" };
  }
  return { label: formatWhen(item.follow_up_due_date).slice(0, 10), priority: "Low", status: "Upcoming", dateClass: "text-on-surface", priorityClass: "bg-info-bg text-info-text border-outline-variant" };
}

function startOfWeekMonday(date) {
  const d = new Date(date);
  const day = d.getDay();
  d.setDate(d.getDate() + (day === 0 ? -6 : 1 - day));
  d.setHours(0, 0, 0, 0);
  return d;
}

function renderMeetings(items = [], meta = {}) {
  const list = Array.isArray(items) ? items : [];
  const host = document.querySelector("[data-meetings-list]");
  if (host) {
    host.innerHTML = list.length
      ? list.map((item) => {
          const when = item.scheduled_at ? formatWhen(item.scheduled_at) : "Unscheduled";
          return `<div class="flex items-center gap-4 p-4 hover:bg-highlight-soft transition-colors" data-live-meeting-row="true" data-meeting-id="${item.id || ""}">
            <div class="w-1 h-12 rounded-full bg-primary-container shrink-0"></div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <h4 class="font-body-md font-semibold text-on-surface truncate">${escapeLiveHtml(item.title || "Meeting")}</h4>
                <span class="inline-flex items-center px-2 py-0.5 rounded bg-surface-alt text-[10px] font-semibold shrink-0">${escapeLiveHtml(titleFromCode(item.meeting_type || "meeting"))}</span>
              </div>
              <p class="font-body-sm text-text-muted">${escapeLiveHtml(when)}</p>
              <p class="font-body-sm text-text-muted mt-0.5">${escapeLiveHtml(item.client_name || item.location_name || item.notes || "")}</p>
            </div>
          </div>`;
        }).join("")
      : `<div class="p-6 text-center text-text-muted">No meetings returned by the API.</div>`;
  }
  const cal = document.querySelector("[data-meetings-calendar]");
  if (cal) {
    cal.textContent = list.length ? `${list.length} live meeting${list.length === 1 ? "" : "s"} this workspace.` : "No meetings scheduled.";
  }
  const start = startOfWeekMonday(new Date());
  const heading = document.querySelector(".workspace-surface h3.font-headline-md");
  if (heading) {
    const end = new Date(start);
    end.setDate(start.getDate() + 6);
    heading.textContent = `${start.toLocaleDateString(undefined, { month: "short", day: "numeric" })} – ${end.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}`;
  }
  document.querySelectorAll(".workspace-surface .grid-cols-7.border-b .font-headline-md").forEach((node, index) => {
    const d = new Date(start);
    d.setDate(start.getDate() + index);
    node.textContent = String(d.getDate());
  });
  const countChip = Array.from(document.querySelectorAll(".workspace-surface .font-label-caps")).find((el) => /LIVE|MEETING/i.test(el.textContent || ""));
  if (countChip) countChip.textContent = `${list.length} LIVE`;
}


/* ═══════════════════════════════════════════════════════════════
   INTERVIEW RENDERERS
   ═══════════════════════════════════════════════════════════════ */

function interviewStatusBadge(status) {
  const normalized = String(status || "").toLowerCase();
  if (/completed|done|passed/.test(normalized)) return "bg-success-bg text-success-text border-primary-fixed-dim";
  if (/scheduled|upcoming|pending/.test(normalized)) return "bg-info-bg text-info-text border-outline-variant";
  if (/cancelled|no.show/.test(normalized)) return "bg-danger-bg text-danger-text border-[#e4b6b0]";
  return "bg-warning-bg text-warning-text border-highlight-soft";
}

function renderInterviewCard(item, index) {
  const feedbackOpen = /pending/i.test(String(item.feedback_status || item.status || ""));
  return `<div class="flex items-center gap-4 p-4 ${index === 0 ? "" : "border-t border-border"} transition-colors hover:bg-highlight-soft" data-live-interview-row="true" data-interview-id="${item.id}">
    <div class="min-w-0 flex-1">
      <div class="mb-1 flex items-center gap-2">
        <h4 class="truncate font-body-md font-semibold text-on-surface">${escapeLiveHtml(item.candidate_name || "Candidate")}</h4>
        <span class="inline-flex shrink-0 items-center rounded border px-2 py-0.5 text-[10px] font-semibold ${interviewStatusBadge(item.feedback_status || item.status)}">${escapeLiveHtml(item.feedback_status || item.status || "Pending")}</span>
      </div>
      <p class="font-body-sm text-text-muted">${escapeLiveHtml(item.requisition_title || "Requisition")}</p>
      <p class="mt-0.5 text-[11px] text-text-muted">${escapeLiveHtml(item.round_type || item.interview_type || "Interview")} · ${escapeLiveHtml(formatWhen(item.scheduled_at))}</p>
    </div>
    <div class="flex shrink-0 items-center gap-1">
      ${feedbackOpen ? `<button class="rounded px-2 py-1 text-xs font-semibold text-primary transition-colors hover:bg-highlight-soft" type="button" data-route="interview-feedback-dialog.html?interview_id=${item.id}" aria-label="Submit feedback for ${escapeLiveHtml(item.candidate_name || "candidate")}">Feedback</button>` : ""}
      <button class="rounded p-1 text-text-muted transition-colors hover:bg-surface-variant hover:text-primary" type="button" data-route="interview-detail.html?interview_id=${item.id}" aria-label="View interview details">
        <span class="material-symbols-outlined text-[20px]">open_in_new</span>
      </button>
    </div>
  </div>`;
}


/* Summary card for interview-detail.html, painted from GET /interviews/{id}
   (InterviewResponse in backend/app/schemas/interview.py). */
function renderInterviewDetail(item) {
  const field = (label, value) => `<div>
      <p class="font-label-caps text-label-caps text-text-muted">${escapeLiveHtml(label)}</p>
      <p class="font-body-sm text-body-sm text-on-surface mt-0.5">${escapeLiveHtml(value || "—")}</p>
    </div>`;
  const status = item.feedback_status || item.status || "Pending";
  return `<section class="bg-surface border border-border rounded-lg p-4 mb-4" data-live-interview-detail="true">
    <div class="flex flex-wrap items-center justify-between gap-3 mb-3">
      <div class="min-w-0">
        <h2 class="font-headline-sm text-headline-sm text-on-surface truncate">${escapeLiveHtml(item.candidate_name || "Candidate")}</h2>
        <p class="font-body-sm text-body-sm text-text-muted">${escapeLiveHtml(item.requisition_title || "Requisition")}</p>
      </div>
      <span class="inline-flex items-center rounded border px-2 py-0.5 text-[11px] font-semibold ${interviewStatusBadge(status)}">${escapeLiveHtml(status)}</span>
    </div>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      ${field("Round", [item.round_type, item.round_name].filter(Boolean).join(" · "))}
      ${field("Scheduled", formatWhen(item.scheduled_at))}
      ${field("Interviewer", item.interviewer_name)}
      ${field("Location", item.location_name)}
      ${field("Decision", item.decision ? titleFromCode(item.decision) : "")}
      ${field("Scheduled by", item.created_by_name)}
    </div>
    ${item.feedback_notes ? `<p class="font-body-sm text-body-sm text-on-surface mt-4 whitespace-pre-line">${escapeLiveHtml(item.feedback_notes)}</p>` : ""}
    ${/pending/i.test(String(item.feedback_status || "")) ? `<div class="mt-4"><button type="button" class="px-4 py-2 rounded bg-primary-container text-on-primary font-body-sm font-semibold" data-route="interview-feedback-dialog.html?interview_id=${item.id}">Submit feedback</button></div>` : ""}
  </section>`;
}

/* ═══════════════════════════════════════════════════════════════
   OFFER RENDERERS
   ═══════════════════════════════════════════════════════════════ */

function normalizeOfferStatus(value) {
  const normalized = String(value || "").toLowerCase().replace(/[-\s]+/g, "_");
  if (/accept/.test(normalized)) return "accepted";
  if (/decline|reject/.test(normalized)) return "declined";
  if (/pending|sent|awaiting/.test(normalized)) return "pending";
  if (/draft|preparing/.test(normalized)) return "draft";
  return normalized || "draft";
}

function offerStatusBadge(status) {
  const normalized = normalizeOfferStatus(status);
  if (normalized === "accepted") return "bg-success-bg text-success-text border-primary-fixed-dim";
  if (normalized === "declined") return "bg-danger-bg text-danger-text border-[#e4b6b0]";
  if (normalized === "pending") return "bg-warning-bg text-warning-text border-highlight-soft";
  return "bg-info-bg text-info-text border-outline-variant";
}

function offerStatusLabel(status) {
  const normalized = normalizeOfferStatus(status);
  if (normalized === "accepted") return "Accepted";
  if (normalized === "declined") return "Declined";
  if (normalized === "pending") return "Pending";
  if (normalized === "draft") return "Draft";
  return titleFromCode(normalized);
}

function offerCompensationText(item) {
  if (item?.compensation_band) return item.compensation_band;
  if (item?.salary_range) return item.salary_range;
  if (item?.offered_ctc) return `$${Number(item.offered_ctc).toLocaleString()}`;
  if (item?.base_salary) return `$${Number(item.base_salary).toLocaleString()}`;
  return "Compensation TBD";
}/* ═══════════════════════════════════════════════════════════════
   PIPELINE ANALYTICS
   ═══════════════════════════════════════════════════════════════ */

function stageRank(stage) {
  const value = String(stage || "").toLowerCase();
  if (/hired|joined/.test(value)) return 4;
  if (/offer/.test(value)) return 3;
  if (/interview|technical|executive|manager|client/.test(value)) return 2;
  if (/screen|review/.test(value)) return 1;
  return 0;
}

function pipelineStageBuckets(pipelineItems, offerItems) {
  const buckets = [
    { label: "Sourced", matcher: (item) => stageRank(item.current_stage) === 0 },
    { label: "Screening", matcher: (item) => stageRank(item.current_stage) === 1 },
    { label: "Interview", matcher: (item) => stageRank(item.current_stage) === 2 },
    { label: "Offer", matcher: (item) => stageRank(item.current_stage) === 3 },
    { label: "Hired", matcher: (item) => stageRank(item.current_stage) >= 4 },
  ];
  const joinedOffers = offerItems.filter((item) => item.application_status === "joined" || normalizeOfferStatus(item.offer_status) === "accepted");
  return buckets.map((bucket) => {
    const pipelineCount = pipelineItems.filter(bucket.matcher).length;
    const offerCount = bucket.label === "Offer" ? offerItems.length : bucket.label === "Hired" ? joinedOffers.length : 0;
    return { ...bucket, count: pipelineCount + offerCount };
  });
}

function renderPipelineAnalyticsFunnel(stages) {
  const panel = findPanelByHeading("Pipeline Conversion Funnel");
  const host = panel?.querySelector(".space-y-4, .space-y-3");
  if (!host) return;
  const max = Math.max(...stages.map((stage) => stage.count), 1);
  host.innerHTML = stages
    .map((stage, index) => {
      const percent = Math.round((stage.count / max) * 100);
      return `<div class="flex items-center gap-4" data-live-pipeline-stage="${escapeLiveHtml(stage.label)}">
        <span class="w-28 text-body-sm font-medium text-on-surface">${escapeLiveHtml(stage.label)}</span>
        <div class="h-8 flex-1 overflow-hidden rounded-full bg-outline-variant">
          <div class="${index === stages.length - 1 ? "bg-success-text" : "bg-primary"} flex h-full items-center justify-end rounded-full pr-3" style="width: ${Math.max(6, percent)}%">
            <span class="text-body-sm font-semibold text-white">${stage.count}</span>
          </div>
        </div>
        <span class="w-12 text-right text-data-tabular font-semibold ${index === stages.length - 1 ? "text-success-text" : "text-on-surface"}">${percent}%</span>
      </div>`;
    })
    .join("");
}

function renderPipelineAnalyticsStageTable(stages, pipelineItems) {
  const panel = findPanelByHeading("Stage Duration Analysis");
  const tbody = panel?.querySelector("tbody");
  if (!tbody) return;
  const max = Math.max(...stages.map((stage) => stage.count), 1);
  tbody.innerHTML = htmlList(
    stages,
    (stage, index) => {
      const sample = pipelineItems.find((item) => {
        if (stage.label === "Offer") return stageRank(item.current_stage) === 3;
        if (stage.label === "Hired") return stageRank(item.current_stage) >= 4;
        return item.current_stage && stage.label.toLowerCase().includes(String(item.current_stage).toLowerCase().split(" ")[0]);
      });
      const days = Math.max(1, Math.round((Date.now() - new Date(sample?.stage_updated_at || sample?.last_activity_at || Date.now()).getTime()) / 86400000));
      const conversion = Math.round((stage.count / max) * 100);
      return `<tr class="border-b border-outline-variant transition-colors hover:bg-highlight-soft" data-live-pipeline-stage-row="true">
        <td class="px-4 py-3 text-body-sm font-medium text-on-surface">${escapeLiveHtml(stage.label)}</td>
        <td class="px-4 py-3 text-data-tabular text-on-surface">${days} days</td>
        <td class="px-4 py-3 text-data-tabular text-on-surface">${stage.count}</td>
        <td class="px-4 py-3 text-data-tabular text-on-surface">${conversion}%</td>
        <td class="px-4 py-3"><span class="material-symbols-outlined text-[18px] ${days > 5 ? "text-error" : "text-success-text"}">${days > 5 ? "trending_up" : "trending_down"}</span></td>
      </tr>`;
    },
    `<tr><td class="px-4 py-6 text-text-muted" colspan="5">No pipeline stage data from the API yet.</td></tr>`,
  );
}

function renderPipelineAnalyticsBottlenecks(stages, interviews, offers) {
  const panel = findPanelByHeading("Top Bottlenecks");
  const host = panel?.querySelector(".space-y-3");
  if (!host) return;
  const sorted = [...stages].sort((a, b) => b.count - a.count).slice(0, 4);
  const pendingInterviews = interviews.filter((item) => String(item.feedback_status || "").toLowerCase() === "pending").length;
  const pendingOffers = offers.filter((item) => /pending/.test(normalizeOfferStatus(item.offer_status))).length;
  const rows = [
    pendingInterviews ? { icon: "rate_review", label: "Interview Feedback", detail: `${pendingInterviews} interviews awaiting feedback` } : null,
    pendingOffers ? { icon: "approval", label: "Offer Approval", detail: `${pendingOffers} offers awaiting approval` } : null,
    ...sorted.map((stage) => ({
      icon: stage.count > 2 ? "warning" : "pending",
      label: stage.label,
      detail: `${stage.count} candidates currently in stage`,
    })),
  ].filter(Boolean).slice(0, 4);
  host.innerHTML = htmlList(
    rows,
    (row, index) => `<div class="flex items-center gap-3 rounded-lg p-2 transition-colors hover:bg-highlight-soft" data-live-pipeline-bottleneck="true">
      <span class="material-symbols-outlined text-[20px] ${index === 0 ? "text-error" : "text-warning-text"}">${escapeLiveHtml(row.icon)}</span>
      <div class="min-w-0 flex-1">
        <p class="truncate text-body-sm font-medium text-on-surface">${escapeLiveHtml(row.label)}</p>
        <p class="truncate text-body-sm text-text-muted">${escapeLiveHtml(row.detail)}</p>
      </div>
    </div>`,
    `<div class="p-2 text-body-sm text-text-muted">No pipeline bottlenecks from the API.</div>`,
  );
}


/* ═══════════════════════════════════════════════════════════════
   ANALYTICS HELPERS
   ═══════════════════════════════════════════════════════════════ */

function renderAnalyticsVisuals(pipelineItems, candidates, offers) {
  const stages = pipelineStageBuckets(pipelineItems, offers);
  const hires = (offers || []).filter((item) => item.application_status === "joined" || normalizeOfferStatus(item.offer_status) === "accepted").length;
  const hireHost = paintChartPlaceholder("Hiring Trend", "");
  if (hireHost) {
    hireHost.innerHTML = `<div class="ro-balance-note">
      <p class="m-0 text-[28px] font-semibold tracking-tight text-on-surface">${pipelineItems.length} <span class="text-[13px] font-medium text-text-muted">in pipeline</span></p>
      <p class="ro-chart-insight">${hires} hired · ${(offers || []).length} offers. Stage mix is in the funnel below.</p>
    </div>`;
  }
  const sourceCounts = {};
  (candidates || []).forEach((candidate) => {
    const source = candidate.source || candidate.source_type || candidate.channel || "Unspecified";
    sourceCounts[source] = (sourceCounts[source] || 0) + 1;
  });
  const sourceRows = Object.entries(sourceCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([label, value]) => ({ label, value }));
  const sourceHost = paintChartPlaceholder("Source Effectiveness", "");
  if (sourceHost) {
    renderRankedMetricList(sourceHost, sourceRows, {
      insight: sourceRows[0] ? `${sourceRows[0].label} is currently the busiest channel.` : "",
      empty: "Source mix will appear once candidates have a channel.",
    });
  }
  const funnelPanel = findPanelByHeading("Pipeline Funnel");
  const funnelHost = funnelPanel?.querySelector(".space-y-3");
  if (funnelHost && stages.length) {
    const max = Math.max(...stages.map((stage) => stage.count), 1);
    funnelHost.innerHTML = stages.map((stage) => {
      const pct = Math.round((stage.count / max) * 100);
      return `<div class="flex items-center gap-4">
        <span class="text-body-sm text-on-surface w-24">${escapeLiveHtml(stage.label)}</span>
        <div class="flex-1 bg-outline-variant rounded-full h-6 overflow-hidden">
          <div class="bg-primary h-full rounded-full" style="width:${Math.max(8, pct)}%"></div>
        </div>
        <span class="text-data-tabular font-semibold text-on-surface w-16 text-right">${stage.count}</span>
      </div>`;
    }).join("");
  }
}

function renderSourceRecommendations(rows) {
  const panel = findPanelByHeading("Recommendations");
  const host = panel?.querySelector(".space-y-3") || panel?.querySelector(".p-4");
  if (!host || !rows?.length) return;
  const ranked = [...rows].sort((a, b) => (b.conversion_rate || 0) - (a.conversion_rate || 0));
  const best = ranked[0];
  const weakest = ranked[ranked.length - 1];
  const notes = [
    best ? { icon: "trending_up", title: `Protect ${best.source}`, detail: `${best.conversion_rate ?? "—"}% conversion from ${best.candidates} candidates.` } : null,
    weakest && weakest !== best ? { icon: "tune", title: `Review ${weakest.source}`, detail: `${weakest.hired || 0} hires from ${weakest.candidates} candidates.` } : null,
  ].filter(Boolean);
  host.innerHTML = notes.map((note) => `<div class="flex items-start gap-3 p-2 rounded-lg">
    <span class="material-symbols-outlined text-[18px] text-primary mt-0.5">${note.icon}</span>
    <div class="min-w-0">
      <p class="text-body-sm text-on-surface font-medium m-0">${escapeLiveHtml(note.title)}</p>
      <p class="text-body-sm text-text-muted m-0">${escapeLiveHtml(note.detail)}</p>
    </div>
  </div>`).join("");
}

function renderSourceLeaderboard(rows) {
  const panel = findPanelByHeading("Top Performing Sources");
  const host = panel?.querySelector(".space-y-3") || panel?.querySelector(".p-4");
  if (!host) return;
  const ranked = [...(rows || [])]
    .sort((a, b) => (b.conversion_rate || 0) - (a.conversion_rate || 0) || (b.candidates || 0) - (a.candidates || 0))
    .slice(0, 5)
    .map((row) => ({ label: row.source, value: row.conversion_rate || 0 }));
  renderRankedMetricList(host, ranked, {
    format: (value) => `${value}%`,
    insight: ranked[0] ? `${ranked[0].label} currently converts best.` : "",
    empty: "Source ranking will appear once candidates have a channel.",
  });
}

function renderAnalyticsTeam(users, requisitions, candidates, offers) {
  const panel = findPanelByHeading("Team Performance");
  const host = panel?.querySelector(".space-y-3");
  if (!host) return;
  const members = buildWorkloadMembers(users, requisitions, candidates)
    .map((user) => ({
      ...user,
      placements: offers.filter((offer) => offer.owner_user_id === user.id && (offer.application_status === "joined" || normalizeOfferStatus(offer.offer_status) === "accepted")).length,
    }))
    .sort((a, b) => b.placements - a.placements || b.activeCandidates - a.activeCandidates)
    .slice(0, 4);
  host.innerHTML = htmlList(
    members,
    (member) => `<div class="flex items-center justify-between rounded-lg p-2 transition-colors hover:bg-highlight-soft" data-live-analytics-team-row="true">
      <div class="flex min-w-0 items-center gap-3">
        <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-container text-label-caps font-bold text-on-primary-container">${escapeLiveHtml(personInitials(member.full_name))}</div>
        <span class="truncate text-body-sm text-on-surface">${escapeLiveHtml(member.full_name || "Team member")}</span>
      </div>
      <span class="shrink-0 text-data-tabular font-semibold text-success-text">${member.placements} hires</span>
    </div>`,
    `<div class="p-2 text-body-sm text-text-muted">No team performance data from the API yet.</div>`,
  );
}

function renderAnalyticsSavedReports(company, dailyUpdates) {
  const cards = document.querySelectorAll(".workspace-surface .report-card");
  if (!cards.length) return;
  const definitions = [
    ["Pipeline Velocity Report", `${company.total_active_applications || 0} active applications across ${company.total_open_requisitions || 0} open requisitions.`, "analytics", "SCHEDULED"],
    ["Recruiter Performance", `${company.total_submitted_profiles || 0} submitted profiles and ${company.total_joined_applications || 0} joined candidates.`, "leaderboard", "ACTIVE"],
    ["Daily Update Rollup", `${dailyUpdates.length} submitted updates with ${dailyUpdates.filter((item) => item.blockers).length} blocker flags.`, "assignment", "LIVE"],
  ];
  cards.forEach((card, index) => {
    const [title, description, icon, status] = definitions[index] || definitions[0];
    setText(card.querySelector("h3"), title);
    setText(card.querySelector("p"), description);
    setText(card.querySelector(".material-symbols-outlined"), icon);
    const statusNode = card.querySelector("span.px-2, .text-label-caps:last-child");
    setText(statusNode, status);
    card.dataset.liveReportCard = "true";
  });
}


/* ═══════════════════════════════════════════════════════════════
   REPORTS LIBRARY
   ═══════════════════════════════════════════════════════════════ */

function reportLibraryDefinitions(company, pipelineItems, candidates, offers, dailyUpdates) {
  const joined = offers.filter((item) => item.application_status === "joined" || normalizeOfferStatus(item.offer_status) === "accepted").length;
  const pendingOffers = offers.filter((item) => /pending/.test(normalizeOfferStatus(item.offer_status))).length;
  const sources = new Set(candidates.map((item) => item.source_type).filter(Boolean));
  const blockers = dailyUpdates.filter((item) => item.blockers).length;
  return [
    { title: "Monthly Hiring Summary", description: `${company.total_open_requisitions || 0} open requisitions, ${company.total_active_candidates || 0} active candidates, ${joined} joined.`, icon: "analytics", status: "ACTIVE", category: "performance", href: "analytics-dashboard.html" },
    { title: "Pipeline Velocity Report", description: `${pipelineItems.length} active pipeline items across ${company.total_active_applications || pipelineItems.length} applications.`, icon: "timeline", status: "SCHEDULED", category: "pipeline", href: "pipeline-analytics.html" },
    { title: "Source Effectiveness", description: `${sources.size || 0} source channels contributing ${candidates.length} candidates.`, icon: "source", status: "LIVE", category: "candidates", href: "source-effectiveness.html" },
    { title: "Recruiter Performance", description: `${company.total_submitted_profiles || 0} profiles submitted with ${company.total_joined_applications || joined} placements.`, icon: "groups", status: "ACTIVE", category: "performance", href: "user-performance-reports.html" },
    { title: "Daily Update Risk Rollup", description: `${dailyUpdates.length} submitted daily updates with ${blockers} blocker flags.`, icon: "assignment_late", status: blockers ? "ACTION" : "CLEAR", category: "pipeline", href: "daily-updates-review.html" },
    { title: "Offer Approval Watch", description: `${pendingOffers} offers awaiting approval from ${offers.length} tracked offers.`, icon: "request_quote", status: pendingOffers ? "ACTION" : "CLEAR", category: "financial", href: "offer-management.html" },
  ];
}

function reportStatusClass(status) {
  const value = String(status || "").toLowerCase();
  if (value === "action") return "bg-warning-bg text-warning-text";
  if (value === "clear" || value === "active") return "bg-success-bg text-success-text";
  if (value === "live") return "bg-primary-container text-on-primary";
  return "bg-info-bg text-info-text";
}

function renderReportLibraryCards(reports, filter = "all") {
  const grid = Array.from(document.querySelectorAll(".workspace-surface .grid")).find((node) => node.querySelector(".report-card"));
  if (!grid) return;
  const filtered = reports.filter((report) => filter === "all" || report.category === filter);
  grid.innerHTML = htmlList(
    filtered,
    (report) => `<article class="report-card group flex min-h-[150px] cursor-pointer flex-col rounded-lg border border-outline-variant bg-surface p-4 transition hover:border-primary/40 hover:shadow-md" data-live-report-card="true" data-report-category="${escapeLiveHtml(report.category)}" data-route="${escapeLiveHtml(report.href)}">
      <div class="mb-3 flex items-start justify-between">
        <span class="material-symbols-outlined text-[24px] text-primary">${escapeLiveHtml(report.icon)}</span>
      </div>
      <h3 class="mb-1 text-headline-sm font-semibold text-on-surface">${escapeLiveHtml(report.title)}</h3>
      <p class="mb-3 line-clamp-2 text-body-sm text-text-muted">${escapeLiveHtml(report.description)}</p>
      <div class="mt-auto flex items-center justify-between gap-3">
        <span class="truncate text-label-caps text-text-muted">Last run: API snapshot</span>
        <span class="rounded px-2 py-0.5 text-label-caps font-semibold ${reportStatusClass(report.status)}">${escapeLiveHtml(report.status)}</span>
      </div>
    </article>`,
    `<div class="rounded-lg border border-outline-variant bg-surface p-6 text-text-muted">No reports match this category.</div>`,
  );
}

const CUSTOM_REPORT_DESTINATIONS = [
  { match: /time to fill/i, href: "time-to-fill-report.html" },
  { match: /conversion rate|pipeline/i, href: "pipeline-analytics.html" },
  { match: /source roi|source/i, href: "source-effectiveness.html" },
  { match: /sla/i, href: "sla-tracker.html" },
  { match: /team utilization|team/i, href: "team-workload.html" },
];

function customReportInputs(root = document) {
  const metrics = Array.from(root.querySelectorAll('input[type="checkbox"]'));
  const dates = Array.from(root.querySelectorAll('input[type="date"]'));
  const selects = Array.from(root.querySelectorAll("select"));
  const radios = Array.from(root.querySelectorAll('input[type="radio"]'));
  const labels = (items) => items.map((field) => readableText(field.closest("label")) || field.value).filter(Boolean);
  return {
    metrics,
    dates,
    selects,
    radios,
    selectedMetrics: labels(metrics.filter((field) => field.checked)),
    selectedViz: labels(radios.filter((field) => field.checked && field.name === "viz"))[0] || "Table",
    selectedSchedule: labels(radios.filter((field) => field.checked && field.name === "schedule"))[0] || "Run Once",
    selectedFormat: labels(radios.filter((field) => field.checked && field.name === "format"))[0] || "PDF",
  };
}

function customReportDestination(selectedMetrics) {
  const joined = selectedMetrics.join(" ");
  return CUSTOM_REPORT_DESTINATIONS.find((item) => item.match.test(joined))?.href || "analytics-dashboard.html";
}

function styleCustomReportChoices(root = document) {
  root.querySelectorAll('input[type="checkbox"], input[type="radio"]').forEach((field) => {
    const label = field.closest("label");
    if (!label) return;
    const active = field.checked;
    label.dataset.liveCustomReportControl = "true";
    label.classList.toggle("border-primary", active);
    label.classList.toggle("border-outline-variant", !active);
    label.classList.toggle("bg-primary-container", active);
    label.classList.toggle("bg-surface", !active);
    label.classList.toggle("hover:bg-highlight-soft", !active);
    label.querySelectorAll(".material-symbols-outlined, span, p").forEach((node) => {
      node.classList.toggle("text-on-primary-container", active);
      if (!active) node.classList.remove("text-on-primary-container");
    });
  });
}

function renderCustomReportPreview(context) {
  const root = document.querySelector(".workspace-surface");
  if (!root) return;
  const previewCard = Array.from(root.querySelectorAll(".bg-surface.border")).find((node) => /report preview/i.test(readableText(node.querySelector("h3"))));
  const chart = root.querySelector(".chart-placeholder");
  if (!previewCard) return;
  const inputs = customReportInputs(root);
  const selectedMetrics = inputs.selectedMetrics.length ? inputs.selectedMetrics : ["No metrics selected"];
  const openReqs = context.company.total_open_requisitions ?? context.requisitions.filter((item) => /open|active/i.test(item.status || "")).length;
  const activeCandidates = context.company.total_active_candidates ?? context.candidates.length;
  const blockers = context.dailyUpdates.filter((item) => item.blockers).length;
  const joined = context.offers.filter((item) => item.application_status === "joined" || normalizeOfferStatus(item.offer_status) === "accepted").length;
  const previewBody = previewCard.querySelector(".p-4:last-child") || previewCard;
  previewBody.innerHTML = `<div class="space-y-4" data-live-custom-report-preview="true">
    <div>
      <p class="mb-2 text-label-caps font-bold uppercase text-text-muted">Selected Metrics</p>
      <div class="flex flex-wrap gap-1.5">${htmlList(
        selectedMetrics,
        (metric) => `<span class="rounded bg-primary-container px-2 py-0.5 text-body-sm font-medium text-on-primary-container">${escapeLiveHtml(metric)}</span>`,
      )}</div>
    </div>
    <div class="grid grid-cols-2 gap-2">
      <div class="rounded-lg border border-border bg-surface-alt p-3">
        <p class="text-label-caps font-bold uppercase text-text-muted">Open Reqs</p>
        <p class="text-headline-md font-semibold text-on-surface">${openReqs}</p>
      </div>
      <div class="rounded-lg border border-border bg-surface-alt p-3">
        <p class="text-label-caps font-bold uppercase text-text-muted">Candidates</p>
        <p class="text-headline-md font-semibold text-on-surface">${activeCandidates}</p>
      </div>
      <div class="rounded-lg border border-border bg-surface-alt p-3">
        <p class="text-label-caps font-bold uppercase text-text-muted">Joined</p>
        <p class="text-headline-md font-semibold text-on-surface">${joined}</p>
      </div>
      <div class="rounded-lg border border-border bg-surface-alt p-3">
        <p class="text-label-caps font-bold uppercase text-text-muted">Blockers</p>
        <p class="text-headline-md font-semibold ${blockers ? "text-warning-text" : "text-success-text"}">${blockers}</p>
      </div>
    </div>
  </div>`;
  root.dataset.liveCustomReportDestination = customReportDestination(selectedMetrics);
}

function escapeAgentHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function agentMeta(agentId) {
  return {
    resume_screener: { icon: "plagiarism", accent: "bg-primary text-white" },
    daily_brief: { icon: "summarize", accent: "bg-secondary-container text-on-secondary-container" },
    inbox_triage: { icon: "inbox", accent: "bg-warning-bg text-warning-text" },
  }[agentId] || { icon: "smart_toy", accent: "bg-surface-alt text-primary" };
}

const TRIAGE_PRIORITY_CLASSES = {
  critical: "bg-danger-bg text-danger-text border-danger-text/20",
  high: "bg-warning-bg text-warning-text border-warning-text/20",
  normal: "bg-surface-alt text-text-muted border-border",
  low: "bg-surface-alt text-text-muted border-border",
};
TRIAGE_PRIORITY_CLASSES.low = "bg-surface-alt text-text-muted border-border";

function triagePriorityClass(priority) {
  return TRIAGE_PRIORITY_CLASSES[String(priority || "normal").toLowerCase()] || TRIAGE_PRIORITY_CLASSES.normal;
}

function renderNotificationsTriage() {
  /* AI Triage review mode for the notifications center: replaces the
     queue with the agent's prioritized draft. Informational until the
     user acts (Got it / Open); draft-only, audited server-side. */
  const state = window.notificationsTriageState;
  const surface = document.querySelector("[data-notifications-command-center]");
  if (!state || !surface) return false;
  const queue = state.queue || [];
  const cleared = state.done.size;
  const listHost = Array.from(surface.querySelectorAll(".divide-y")).find((el) => el.closest("section"));
  if (!listHost) return false;

  const banner = document.createElement("div");
  banner.className = "flex flex-wrap items-center justify-between gap-3 border-b border-border bg-highlight-soft px-4 py-3";
  banner.dataset.triageBanner = "true";
  banner.innerHTML = `
    <div class="flex items-center gap-2">
      <span class="material-symbols-outlined text-[18px] text-primary">smart_toy</span>
      <p class="font-body-sm text-body-sm text-on-surface"><strong>AI Triage</strong> · ${queue.length} unread sorted by priority</p>
      <span class="rounded-full border border-border bg-surface px-2 py-0.5 font-data-tabular text-[11px] text-text-muted" data-triage-progress>${cleared}/${queue.length} cleared</span>
    </div>
    <button type="button" class="inline-flex min-h-8 items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1 font-data-tabular text-[12px] font-semibold text-secondary hover:bg-highlight-soft transition" data-triage-exit aria-label="Exit triage review">
      <span class="material-symbols-outlined text-[16px]">close</span>Exit triage
    </button>`;
  surface.querySelector("[data-triage-banner]")?.remove();
  listHost.before(banner);

  listHost.innerHTML = queue.length
    ? queue.map((item, index) => {
        const id = escapeAgentHtml(item.id);
        const done = state.done.has(String(item.id));
        return `<article class="grid gap-3 p-4 transition-colors md:grid-cols-[auto_minmax(0,1fr)_auto] md:items-start ${done ? "opacity-50" : "hover:bg-highlight-soft"}" data-triage-row="${id}" data-notification-id="${id}" data-notification-status="${done ? "read" : "unread"}" data-filter-category="${escapeAgentHtml(item.module || "")}" data-filter-priority="${escapeAgentHtml(item.priority || "")}">
          <div class="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-surface font-data-tabular text-[12px] font-bold text-text-muted">${index + 1}</div>
          <div class="min-w-0">
            <div class="mb-1 flex flex-wrap items-center gap-2">
              <span class="rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${triagePriorityClass(item.priority)}">${escapeAgentHtml(item.priority || "normal")}</span>
              <span class="rounded border border-border bg-surface px-1.5 py-0.5 font-label-caps text-label-caps uppercase tracking-wider text-secondary">${escapeAgentHtml(item.module || "inbox")}</span>
              ${done ? '<span class="rounded-full bg-success-bg px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-success-text">Cleared</span>' : ""}
            </div>
            <h3 class="font-headline-sm text-headline-sm text-on-surface">${escapeAgentHtml(item.what || "(untitled notification)")}</h3>
            <p class="mt-1 font-body-sm text-body-sm text-on-surface">${escapeAgentHtml(item.why || "")}</p>
            <p class="mt-1.5 font-body-sm text-[12px] text-text-muted flex items-center gap-1"><span class="material-symbols-outlined text-[14px]">arrow_forward</span>${escapeAgentHtml(item.next || "Review this item")}</p>
          </div>
          <div class="flex items-center justify-end gap-2">
            ${done
              ? '<span class="font-body-sm text-[12px] font-semibold text-success-text">Seen</span>'
              : `<button type="button" class="inline-flex min-h-9 items-center gap-1.5 rounded-lg bg-success-bg px-3 py-1.5 font-data-tabular text-data-tabular font-semibold text-success-text hover:brightness-95 transition" data-triage-got-it data-notification-id="${id}" aria-label="Mark notification ${id} as read"><span class="material-symbols-outlined text-[16px]">check</span>Got it</button>
                 <button type="button" class="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 font-data-tabular text-data-tabular font-semibold text-secondary hover:bg-highlight-soft transition" data-triage-open data-notification-id="${id}" aria-label="Open notification ${id}">Open</button>`}
          </div>
        </article>`;
      }).join("")
    : '<div class="p-6 text-center font-body-sm text-body-sm text-text-muted">Nothing unread to triage. You are all caught up.</div>';
  return true;
}

function updateTriageProgress() {
  const state = window.notificationsTriageState;
  if (!state) return;
  const progress = document.querySelector("[data-triage-progress]");
  if (progress) progress.textContent = `${state.done.size}/${state.queue.length} cleared`;
  if (state.queue.length > 0 && state.done.size >= state.queue.length) {
    showToast("Inbox cleared", "Every triaged notification has been handled.");
  }
}

function applyTriageDoneToDom(notificationId) {
  const row = document.querySelector(`[data-triage-row="${CSS.escape(String(notificationId))}"]`);
  if (!row) return;
  row.classList.add("opacity-50");
  row.dataset.notificationStatus = "read";
  const actions = row.querySelector(".flex.items-center.justify-end.gap-2");
  if (actions) actions.innerHTML = '<span class="font-body-sm text-[12px] font-semibold text-success-text">Seen</span>';
  if (!row.querySelector("[data-triage-cleared-badge]")) {
    const cleared = document.createElement("span");
    cleared.className = "rounded-full bg-success-bg px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-success-text";
    cleared.dataset.triageClearedBadge = "true";
    cleared.textContent = "Cleared";
    row.querySelector(".mb-1")?.appendChild(cleared);
  }
}

function agentRunStatusMeta(status) {
  const s = String(status || "pending").toLowerCase();
  return {
    pending: { label: "Pending review", classes: "bg-warning-bg text-warning-text border-warning-text/20" },
    accepted: { label: "Accepted", classes: "bg-success-bg text-success-text border-success-text/20" },
    rejected: { label: "Rejected", classes: "bg-surface-alt text-text-muted border-border" },
    failed: { label: "Failed", classes: "bg-danger-bg text-danger-text border-danger-text/20" },
  }[s] || { label: s, classes: "bg-surface-alt text-text-muted border-border" };
}

function agentRelativeTime(iso) {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const minutes = Math.floor((Date.now() - then) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

function agentDraftHighlights(agentId, draft) {
  const highlights = [];
  if (agentId === "resume_screener") {
    const score = draft?.match_score;
    if (score != null) highlights.push(`Match ${Math.round(score * 100)}%`);
    const skills = draft?.extracted_skills || [];
    if (skills.length) highlights.push(`${skills.length} skill${skills.length === 1 ? "" : "s"}`);
    const note = (draft?.match_notes || [])[0];
    if (note) highlights.push(String(note));
  } else if (agentId === "daily_brief") {
    const stats = draft?.stats || {};
    const screened = stats.profiles_screened ?? 0;
    const focus = (draft?.focus_items || []).length;
    if (screened) highlights.push(`${screened} screened`);
    if (focus) highlights.push(`${focus} focus item${focus === 1 ? "" : "s"}`);
    const blockers = (draft?.blockers || []).filter(Boolean);
    if (blockers.length) highlights.push(`${blockers.length} blocker${blockers.length === 1 ? "" : "s"}`);
  } else if (agentId === "inbox_triage") {
    const queue = draft?.queue || [];
    if (queue.length) {
      highlights.push(`${queue.length} notification${queue.length === 1 ? "" : "s"}`);
      const urgent = queue.filter((entry) => ["high", "critical"].includes(String(entry.priority || "").toLowerCase())).length;
      if (urgent) highlights.push(`${urgent} urgent`);
    }
  }
  return highlights.slice(0, 3);
}

function updateAgentRunCounters(catalog, runs) {
  /* Refresh the header stats/pill after cache-only changes (e.g. a
     decision) without re-rendering the whole list. */
  const surface = document.querySelector("[data-agents-workbench]");
  if (!surface) return;
  const items = Array.isArray(catalog?.items) ? catalog.items : [];
  const runItems = Array.isArray(runs?.items) ? runs.items : [];
  const statTotal = surface.querySelector('[data-agents-stat="total"]');
  const statPending = surface.querySelector('[data-agents-stat="pending"]');
  const statAccepted = surface.querySelector('[data-agents-stat="accepted"]');
  if (statTotal) statTotal.textContent = String(items.length);
  if (statPending) statPending.textContent = String(runItems.filter((run) => run.status === "pending").length);
  if (statAccepted) statAccepted.textContent = String(runItems.filter((run) => run.status === "accepted").length);
  const countPill = surface.querySelector("[data-agents-count-pill]");
  if (countPill) countPill.textContent = `${items.length} agents · ${runItems.length} runs`;
}

function renderAgentsWorkbench(catalog, runs) {
  const surface = document.querySelector("[data-agents-workbench]");
  if (!surface) return false;
  const items = Array.isArray(catalog?.items) ? catalog.items : [];
  const runItems = Array.isArray(runs?.items) ? runs.items : [];
  const perms = typeof userPermissions === "function" ? userPermissions() : [];
  const canRun = (agentId) => perms.includes(`ai.agent.${agentId}`);

  updateAgentRunCounters(catalog, runs);

  const catalogHost = surface.querySelector("[data-agents-catalog]");
  if (catalogHost) {
    catalogHost.innerHTML = items.length
      ? items.map((agent) => {
          const meta = agentMeta(agent.id);
          const runnable = canRun(agent.id);
          return `<article class="rounded-xl border border-border bg-surface-alt p-3">
            <div class="flex items-center gap-2">
              <div class="flex h-8 w-8 items-center justify-center rounded-lg ${meta.accent}"><span class="material-symbols-outlined text-[16px]">${escapeAgentHtml(meta.icon)}</span></div>
              <div class="min-w-0 flex-1">
                <p class="font-data-tabular text-[13px] font-semibold text-on-surface">${escapeAgentHtml(agent.name)}</p>
                <p class="font-body-sm text-body-sm text-text-muted">${escapeAgentHtml(agent.where_used)}</p>
              </div>
            </div>
            <p class="mt-2 font-body-sm text-body-sm text-on-surface">${escapeAgentHtml(agent.job)}</p>
            <p class="mt-1.5 text-[11px] font-semibold uppercase tracking-wide ${runnable ? "text-success-text" : "text-text-muted"}">${runnable ? "Ready to run" : "Needs permission"}</p>
          </article>`;
        }).join("")
      : '<div class="p-4 font-body-sm text-body-sm text-text-muted">No agents available.</div>';
  }

  const select = surface.querySelector("[data-agents-select]");
  if (select) {
    const previous = select.value;
    select.innerHTML = items.length
      ? items.map((agent) => `<option value="${escapeAgentHtml(agent.id)}"${canRun(agent.id) ? "" : " disabled"}>${escapeAgentHtml(agent.name)}${canRun(agent.id) ? "" : " — permission required"}</option>`).join("")
      : '<option value="">No agents available</option>';
    if (previous && Array.from(select.options).some((option) => option.value === previous && !option.disabled)) select.value = previous;
  }

  const list = surface.querySelector("[data-agents-run-list]");
  if (list) {
    list.innerHTML = runItems.length
      ? runItems.map((run) => renderAgentRunRow(run, items)).join("")
      : '<div class="p-6 text-center font-body-sm text-body-sm text-text-muted">No runs yet. Pick an agent above and click Run agent.</div>';
  }
  return true;
}

function renderAgentRunRow(run, catalogItems) {
  const meta = agentMeta(run.agent_id);
  const statusMeta = agentRunStatusMeta(run.status);
  const agentName = (catalogItems || []).find((agent) => agent.id === run.agent_id)?.name || run.agent_id;
  const highlights = agentDraftHighlights(run.agent_id, run.output_draft);
  const runId = escapeAgentHtml(run.id);
  const pendingActions = `<button type="button" class="inline-flex min-h-9 items-center gap-1.5 rounded-lg bg-success-bg px-3 py-1.5 font-data-tabular text-data-tabular font-semibold text-success-text hover:brightness-95 transition" data-live-agents-decide data-agent-run-id="${runId}" data-agent-decision="accept" aria-label="Accept run ${runId}"><span class="material-symbols-outlined text-[16px]">check</span>Accept</button>
              <button type="button" class="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 font-data-tabular text-data-tabular font-semibold text-secondary hover:bg-highlight-soft transition" data-live-agents-decide data-agent-run-id="${runId}" data-agent-decision="reject" aria-label="Reject run ${runId}"><span class="material-symbols-outlined text-[16px]">close</span>Reject</button>`;
  const reviewAction = `<button type="button" class="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 font-data-tabular text-data-tabular font-semibold text-secondary hover:bg-highlight-soft transition" data-live-agents-open-run data-agent-run-id="${runId}" aria-label="Review run ${runId}">Review</button>`;
  return `<article class="agent-run-row group relative grid gap-3 p-4 transition-colors hover:bg-highlight-soft md:grid-cols-[auto_minmax(0,1fr)_auto] md:items-center" data-agent-run-id="${runId}" data-agent-run-status="${escapeAgentHtml(run.status)}">
            <div class="flex h-10 w-10 items-center justify-center rounded-xl ${meta.accent}"><span class="material-symbols-outlined">${escapeAgentHtml(meta.icon)}</span></div>
            <div class="min-w-0">
              <div class="mb-1 flex flex-wrap items-center gap-2">
                <span class="font-data-tabular text-[13px] font-semibold text-on-surface">${escapeAgentHtml(agentName)}</span>
                <span class="rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${statusMeta.classes}" data-agent-run-status-badge>${escapeAgentHtml(statusMeta.label)}</span>
                <span class="font-data-tabular text-[11px] text-text-muted" data-agent-run-time>${escapeAgentHtml(agentRelativeTime(run.created_at))}</span>
              </div>
              <p class="font-body-sm text-body-sm text-on-surface">${escapeAgentHtml(run.output_summary || "")}</p>
              ${highlights.length ? `<div class="mt-1.5 flex flex-wrap gap-1.5">${highlights.map((h) => `<span class="rounded bg-surface-alt px-1.5 py-0.5 font-data-tabular text-[11px] text-text-muted">${escapeAgentHtml(h)}</span>`).join("")}</div>` : ""}
            </div>
            <div class="flex items-center justify-end gap-2" data-agent-run-actions>${run.status === "pending" ? pendingActions : reviewAction}</div>
            <div class="hidden" data-agent-draft-host>${escapeAgentHtml(JSON.stringify(run.output_draft || {}))}</div>
          </article>`;
}

function applyAgentRunDecisionToDom(runId, status) {
  const row = document.querySelector(`[data-agent-run-id="${CSS.escape(String(runId))}"]`);
  if (!row) return;
  const statusMeta = agentRunStatusMeta(status);
  row.dataset.agentRunStatus = status;
  const badge = row.querySelector("[data-agent-run-status-badge]");
  if (badge) {
    badge.className = `rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${statusMeta.classes}`;
    badge.textContent = statusMeta.label;
  }
  const actions = row.querySelector("[data-agent-run-actions]");
  if (actions && status !== "pending") {
    const safeId = escapeAgentHtml(runId);
    actions.innerHTML = `<button type="button" class="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 font-data-tabular text-data-tabular font-semibold text-secondary hover:bg-highlight-soft transition" data-live-agents-open-run data-agent-run-id="${safeId}" aria-label="Review run ${safeId}">Review</button>`;
  }
}

function renderAgentRunDetail(run, catalogItems) {
  let overlay = document.getElementById("ro-inpage-overlay");
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.id = "ro-inpage-overlay";
    document.body.appendChild(overlay);
    document.body.classList.add("is-inpage-overlay");
  }
  const meta = agentMeta(run.agent_id);
  const agentName = (catalogItems || []).find((agent) => agent.id === run.agent_id)?.name || run.agent_id;
  const statusMeta = agentRunStatusMeta(run.status);
  const runId = escapeAgentHtml(run.id);
  const draftJson = JSON.stringify(run.output_draft || {}, null, 2);
  const inputEntries = Object.entries(run.input_refs || {}).map(([key, value]) => `<div class="flex justify-between gap-3"><dt class="text-text-muted">${escapeAgentHtml(key)}</dt><dd class="font-semibold text-on-surface">${escapeAgentHtml(String(value))}</dd></div>`).join("");
  overlay.dataset.overlayRoute = "agents-workbench-run-detail";
  overlay.innerHTML = `
    <div class="overlay-backdrop" data-overlay-close="true"></div>
    <div class="overlay-host dialog">
    <div class="w-full max-w-2xl rounded-2xl border border-border bg-surface shadow-2xl" role="dialog" aria-modal="true" aria-label="Agent run detail">
        <div class="flex items-start justify-between gap-3 border-b border-border px-5 py-4">
          <div class="flex items-center gap-3">
            <div class="flex h-10 w-10 items-center justify-center rounded-xl ${meta.accent}"><span class="material-symbols-outlined">${escapeAgentHtml(meta.icon)}</span></div>
            <div>
              <p class="font-headline-sm text-headline-sm text-on-surface">${escapeAgentHtml(agentName)} · run #${runId}</p>
              <p class="font-body-sm text-body-sm text-text-muted">${escapeAgentHtml(agentRelativeTime(run.created_at))} · ${escapeAgentHtml(run.output_summary || "")}</p>
            </div>
          </div>
          <button type="button" class="rounded-full border border-border p-2 text-on-surface" data-overlay-close aria-label="Close run detail"><span class="material-symbols-outlined">close</span></button>
        </div>
        <div class="max-h-[70vh] space-y-4 overflow-auto px-5 py-4">
          <div class="flex items-center gap-2">
            <span class="rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${statusMeta.classes}">${escapeAgentHtml(statusMeta.label)}</span>
            ${run.decided_at ? `<span class="font-data-tabular text-[11px] text-text-muted">Decided ${escapeAgentHtml(agentRelativeTime(run.decided_at))}${run.decision_notes ? ` · “${escapeAgentHtml(run.decision_notes)}”` : ""}</span>` : ""}
          </div>
          ${inputEntries ? `<section><h3 class="font-label-caps text-label-caps text-text-muted uppercase tracking-wider">Inputs</h3><dl class="mt-2 grid gap-1.5 font-body-sm text-body-sm">${inputEntries}</dl></section>` : ""}
          <section>
            <h3 class="font-label-caps text-label-caps text-text-muted uppercase tracking-wider">Draft output</h3>
            <pre class="mt-2 overflow-auto rounded-xl border border-border bg-surface-alt p-3 font-data-tabular text-[12px] text-on-surface" data-agent-draft-json>${escapeAgentHtml(draftJson)}</pre>
          </section>
        </div>
        <div class="flex items-center justify-end gap-2 border-t border-border px-5 py-4" data-agent-detail-actions>
          ${run.status === "pending" ? `<button type="button" class="inline-flex min-h-10 items-center gap-2 rounded-lg bg-success-bg px-4 font-data-tabular text-data-tabular font-semibold text-success-text hover:brightness-95 transition" data-live-agents-decide data-agent-run-id="${runId}" data-agent-decision="accept"><span class="material-symbols-outlined text-[18px]">check</span>Accept draft</button>
          <button type="button" class="inline-flex min-h-10 items-center gap-2 rounded-lg border border-border bg-surface px-4 font-data-tabular text-data-tabular font-semibold text-secondary hover:bg-highlight-soft transition" data-live-agents-decide data-agent-run-id="${runId}" data-agent-decision="reject"><span class="material-symbols-outlined text-[18px]">close</span>Reject</button>` : `<p class="font-body-sm text-body-sm text-text-muted">This run has been ${escapeAgentHtml(run.status)}.</p>`}
        </div>
      </div>
    </div>
    </div>`;
  if (typeof wireHoverKebabMenus === "function") { /* no-op: keeps call parity with other overlays */ }
}
