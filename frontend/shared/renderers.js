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

function queryInt(...names) {
  const params = new URLSearchParams(window.location.search);
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
    low: "bg-surface-dim text-text-muted",
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
function renderTableEmptyCell(opts) {
  const { icon = "inventory_2", title, hint, hintClass = "text-[11px]", columnCount = 1 } = opts || {};
  const heading = title || (() => {
    const surface = document.querySelector(".workspace-surface");
    return surface?.querySelector("h2, h3")?.textContent?.trim() || "records";
  })();
  const titleText = /no /i.test(heading) ? heading : `No ${heading.toLowerCase()} found.`;
  const hintCopy = hint || "Try adjusting your filters or create a new record.";
  return `<td colspan="${columnCount}">
    <div class="table-empty-state-card">
      <div class="flex flex-col items-center gap-2">
        <span class="material-symbols-outlined text-3xl text-border">${icon}</span>
        <strong>${titleText}</strong>
        <p class="font-body-sm text-body-sm text-text-muted ${hintClass}">${hintCopy}</p>
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
function fillExistingTable(items, paintRow) {
  const tbody = document.querySelector(".workspace-surface tbody");
  if (!tbody) return;
  const template = tbody.querySelector("tr");
  if (!template) return;
  tbody.innerHTML = "";
  if (!items.length) {
    const cols = template.children.length || 1;
    tbody.innerHTML = renderTableEmptyState({ columnCount: cols });
    return;
  }
  items.forEach((item, index) => {
    const row = template.cloneNode(true);
    row.classList.toggle("bg-surface-alt", index % 2 === 1);
    row.dataset.recordId = item.id || item.application_id || "";
    paintRow(row, item, index);
    tbody.appendChild(row);
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
    if (!card) return;
    const headline = card.querySelector(".font-headline-md, .text-headline-md");
    if (headline) headline.textContent = String(pair.value ?? "—");
    const hint = card.querySelector(".font-body-sm, .text-body-sm, .text-text-muted");
    if (hint && pair.hint) hint.textContent = pair.hint;
  });
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
  const heading = Array.from(document.querySelectorAll(".workspace-surface h2, .workspace-surface h3")).find((node) =>
    readableText(node).toLowerCase() === needle,
  );
  return heading?.closest(".bg-surface, section, .rounded-2xl, .rounded-lg") || null;
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
    : `<div class="px-inset-card py-6 text-center text-text-muted">No open workflow actions from the API.</div>`;
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
          <button class="inline-flex items-center justify-center rounded-lg border border-primary/20 bg-surface px-3 py-2 font-data-tabular text-data-tabular font-semibold text-primary hover:bg-highlight-soft" type="button" data-live-workflow-action="${action}" data-action-item-id="${item.id}">${escapeLiveHtml(actionLabel)}</button>
        </article>`;
      }).join("")
    : `<div class="p-6 text-center text-text-muted">No open workflow actions from the API.</div>`;
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
}function renderDailyReviewQuickStats(myWork, pipelineItems) {
  const surface = document.querySelector(".workspace-surface");
  if (!surface) return;
  const statCards = surface.querySelectorAll(".grid-cols-2 .bg-surface.border");
  const stats = [
    { value: myWork?.pending_actions ?? 0, hint: "Pending Actions" },
    { value: myWork?.submitted_updates ?? 0, hint: "Updates Submitted" },
    { value: pipelineItems?.length ?? 0, hint: "Pipeline Items" },
  ];
  stats.forEach((stat, index) => {
    const card = statCards[index];
    if (!card) return;
    const headline = card.querySelector(".font-headline-md, .text-headline-md");
    if (headline) headline.textContent = String(stat.value);
  });
}

function renderDailyReviewPipelineActivity(items) {
  const host = panelRowsHost("Pipeline Activity");
  if (!host) return;
  host.innerHTML = items.length
    ? items.map((item) => `<div class="flex items-center gap-3 rounded-lg p-2 transition-colors hover:bg-highlight-soft">
        <span class="material-symbols-outlined text-[20px] text-primary">swap_horiz</span>
        <div class="min-w-0 flex-1">
          <p class="truncate text-body-sm font-medium text-on-surface">${escapeLiveHtml(item.candidate_name || "Candidate")}</p>
          <p class="truncate text-body-sm text-text-muted">${escapeLiveHtml(item.current_stage || "Pipeline")}</p>
        </div>
        <span class="text-[11px] text-text-muted">${escapeLiveHtml(relativeTime(item.stage_updated_at))}</span>
      </div>`).join("")
    : `<div class="p-4 text-body-sm text-text-muted">No recent pipeline activity.</div>`;
}function notificationAccentClass(item) {
  const status = String(item?.status || "").toLowerCase();
  if (status === "unread") return "bg-danger-bg text-danger-text border-[#e4b6b0]";
  return "bg-info-bg text-info-text border-outline-variant";
}

function notificationIcon(item) {
  const module = String(item?.module_name || "").toLowerCase();
  if (/meeting/.test(module)) return "event";
  if (/approval/.test(module)) return "gavel";
  if (/candidate/.test(module)) return "person";
  if (/requisition/.test(module)) return "work";
  return "notifications";
}

function notificationCategory(item) {
  const source = `${item?.module_name || ""} ${item?.event_type || ""} ${item?.source_type || ""}`.toLowerCase();
  if (/approval/.test(source)) return "Approvals";
  if (/pipeline|stage/.test(source)) return "Pipeline";
  if (/requisition/.test(source)) return "Requisition";
  if (/candidate/.test(source)) return "Candidate";
  if (/daily.update/.test(source)) return "Daily Update";
  if (/meeting/.test(source)) return "Meeting";
  return "System";
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

  const pill = Array.from(surface.querySelectorAll("span")).find((span) => /priority alert/i.test(span.textContent || ""));
  if (pill) pill.textContent = `${highCount} priority alert${highCount === 1 ? "" : "s"}`;

  const liveBadge = Array.from(surface.querySelectorAll("span")).find((span) => /mock state/i.test(span.textContent || ""));
  if (liveBadge) {
    liveBadge.textContent = "Live API data";
    liveBadge.className = liveBadge.className.replace("bg-warning-bg", "bg-success-bg").replace("text-warning-text", "text-success-text");
  }

  const queueHeading = Array.from(surface.querySelectorAll("h2")).find((heading) => /action queue/i.test(heading.textContent || ""));
  const list = queueHeading?.closest("section")?.querySelector(".divide-y");
  if (!list) return false;

  list.innerHTML = items.length
    ? items.map((item) => {
        const unread = String(item.status || "").toLowerCase() === "unread";
        const accent = notificationAccentClass(item);
        return `<article class="group relative grid gap-3 p-4 transition-colors hover:bg-highlight-soft md:grid-cols-[auto_minmax(0,1fr)_auto] md:items-center${unread ? " border-l-4 border-error bg-danger-bg/20" : ""}" data-notification-id="${item.id}" data-notification-status="${escapeLiveHtml(item.status || "read")}">
          <div class="flex h-10 w-10 items-center justify-center rounded-xl ${unread ? "bg-error-container text-error" : "bg-surface-alt text-primary"}">
            <span class="material-symbols-outlined">${notificationIcon(item)}</span>
          </div>
          <div class="min-w-0">
            <div class="mb-1 flex flex-wrap items-center gap-2">
              <span class="rounded border px-1.5 py-0.5 font-label-caps text-label-caps uppercase tracking-wider ${unread ? "border-danger-text/20 bg-white text-danger-text" : "border-border bg-surface-alt text-secondary"}">${escapeLiveHtml(notificationCategory(item))}</span>
              <span class="font-data-tabular text-[11px] text-text-muted">${escapeLiveHtml(relativeTime(item.created_at))}</span>
              ${unread ? '<span data-notification-unread-indicator class="h-2 w-2 rounded-full bg-error"></span>' : ""}
            </div>
            <h3 class="font-headline-sm text-headline-sm text-on-surface">${escapeLiveHtml(item.title || "Notification")}</h3>
            <p class="mt-1 font-body-sm text-body-sm text-text-muted">${escapeLiveHtml(item.message || "")}</p>
          </div>
          <div class="flex flex-wrap items-center gap-2 md:justify-end">
            <span class="inline-flex items-center rounded border px-2 py-0.5 text-[10px] font-semibold ${accent}" data-notification-status-badge>${escapeLiveHtml(item.status || "read")}</span>
            ${unread ? `<button class="inline-flex min-h-9 items-center justify-center rounded-lg border border-border bg-surface px-2.5 text-secondary hover:bg-highlight-soft" title="Mark as Read" type="button" data-notification-read="true" aria-label="Mark as read"><span class="material-symbols-outlined text-[20px]">done</span></button>` : ""}
          </div>
        </article>`;
      }).join("")
    : `<div class="p-6 text-center text-body-sm text-text-muted">No ${escapeLiveHtml(notificationFilterLabel())} notifications. Try the "All" filter.</div>`;
  return true;
}


/* ═══════════════════════════════════════════════════════════════
   BUSINESS TITLE HELPERS
   ═══════════════════════════════════════════════════════════════ */

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
  return `<div class="grid min-h-[44px] grid-cols-12 items-center gap-4 border-b border-border px-inset-card py-2 transition-colors hover:bg-highlight-soft" data-live-delivery-row="true" data-action-item-id="${item.id}">
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
    <div class="col-span-3 flex justify-end gap-2">
      <button class="inline-flex min-h-8 items-center rounded-lg border border-border bg-surface px-2.5 text-[12px] font-semibold text-secondary transition-colors hover:bg-highlight-soft hover:text-primary" type="button" data-route="${escapeLiveHtml(route)}">Open</button>
      <button class="inline-flex min-h-8 items-center rounded-lg bg-primary px-2.5 text-[12px] font-semibold text-on-primary transition-colors hover:bg-primary-hover disabled:opacity-60" type="button" data-live-workflow-action="${action}" data-action-item-id="${item.id}">${escapeLiveHtml(item.primary_action_label || "Do Now")}</button>
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
  const action = String(item.action || "").toLowerCase();
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
          <p class="text-body-sm font-medium text-on-surface">${escapeLiveHtml(item.action || "Stage change")}</p>
          <p class="text-[11px] text-text-muted">${escapeLiveHtml(item.actor_name || "System")} · ${escapeLiveHtml(relativeTime(item.created_at))}</p>
          ${item.notes ? `<p class="mt-1 text-[11px] text-text-muted">${escapeLiveHtml(item.notes)}</p>` : ""}
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
  const status = String(item?.review_status || item?.status || "").toLowerCase();
  if (/acknowledged|approved|reviewed/.test(status)) return { label: "Reviewed", badge: "bg-success-bg text-success-text border-[#C5DBC8]" };
  if (/pending|submitted/.test(status)) return { label: "Pending Review", badge: "bg-warning-bg text-warning-text border-[#E8D1B5]" };
  if (/feedback|rejected/.test(status)) return { label: "Feedback", badge: "bg-danger-bg text-danger-text border-[#E6C6C1]" };
  return { label: "Pending", badge: "bg-warning-bg text-warning-text border-[#E8D1B5]" };
}function renderDailyUpdateTableRow(item) {
  const status = dailyUpdateStatusMeta(item);
  return `<tr class="hover:bg-highlight-soft transition-colors" data-daily-update-id="${item.id}">
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

function renderUserPerformanceRows(members) {
  return members.map((member) => `<tr class="hover:bg-highlight-soft transition-colors">
    <td class="py-2 px-4"><div class="flex items-center gap-3"><div class="flex h-8 w-8 items-center justify-center rounded-full bg-primary-container text-[11px] font-bold text-on-primary-container">${escapeLiveHtml(personInitials(member.full_name))}</div><span class="font-medium text-on-surface">${escapeLiveHtml(member.full_name || "User")}</span></div></td>
    <td class="py-2 px-4 text-data-tabular text-on-surface">${member.submitted}</td>
    <td class="py-2 px-4 text-data-tabular text-success-text font-semibold">${member.hired}</td>
    <td class="py-2 px-4 text-data-tabular text-on-surface">${member.activeReqs}</td>
  </tr>`).join("");
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
  const panel = findPanelByHeading("Workload Distribution");
  if (!panel) return;
  const host = panel.querySelector(".space-y-3") || panel;
  const max = Math.max(...members.map((m) => m.submitted + m.hired + m.activeReqs), 1);
  host.innerHTML = members.slice(0, 6).map((member) => {
    const total = member.submitted + member.hired + member.activeReqs;
    const pct = Math.round((total / max) * 100);
    return `<div class="flex items-center gap-3">
      <span class="w-24 truncate text-body-sm text-on-surface">${escapeLiveHtml(member.full_name || "User")}</span>
      <div class="h-4 flex-1 overflow-hidden rounded bg-outline-variant">
        <div class="h-4 rounded bg-primary" style="width:${pct}%"></div>
      </div>
      <span class="w-8 text-right text-[11px] font-semibold text-on-surface">${total}</span>
    </div>`;
  }).join("") || `<div class="p-2 text-body-sm text-text-muted">No workload data available.</div>`;
}


/* ═══════════════════════════════════════════════════════════════
   TIME-TO-FILL & SLA
   ═══════════════════════════════════════════════════════════════ */

function renderTimeToFillBars(panelTitle, rows) {
  const panel = findPanelByHeading(panelTitle);
  if (!panel) return;
  const host = panel.querySelector(".space-y-4") || panel.querySelector(".space-y-3") || panel;
  if (!host) return;
  if (!rows || !rows.length) {
    host.innerHTML = `<div class="p-2 text-body-sm text-text-muted">No closed requisitions to report on yet.</div>`;
    return;
  }
  const max = Math.max(...rows.map((row) => row.days || 0), 1);
  host.innerHTML = rows.map((row) => `<div class="flex items-center gap-3">
        <span class="w-28 truncate text-body-sm text-on-surface">${escapeLiveHtml(row.label || row.title || "Role")}</span>
        <div class="h-4 flex-1 overflow-hidden rounded bg-outline-variant">
          <div class="h-4 rounded bg-primary" style="width:${Math.round(((row.days || 0) / max) * 100)}%"></div>
        </div>
        <span class="w-14 text-right text-[11px] font-semibold text-on-surface">${row.days != null ? `${row.days} days` : "—"}</span>
      </div>`).join("");
}

function renderTimeToFillTrend(records) {
  const panel = findPanelByHeading("Time to Fill Trend");
  if (!panel) return;
  const host = panel.querySelector(".space-y-3") || panel;
  if (!host || !records || !records.length) return; // trend placeholder stays when no monthly data
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
      <td class="px-4 py-3">${sourceQualityMeta(row)}</td>
    </tr>`;
      }).join("")
    : `<tr><td class="px-4 py-6 text-text-muted" colspan="5">No candidate source data available yet.</td></tr>`;
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
}function renderFollowUpRow(item, index) {
  const timing = followUpTimingMeta(item);
  return `<div class="flex items-center gap-4 p-4 ${index === 0 ? "" : "border-t border-border"} transition-colors hover:bg-highlight-soft" data-live-follow-up-row="true" data-follow-up-id="${item.id}">
    <div class="min-w-0 flex-1">
      <div class="mb-1 flex items-center gap-2">
        <h4 class="truncate font-body-md font-semibold text-on-surface">${escapeLiveHtml(item.title || "Follow-up")}</h4>
        <span class="inline-flex shrink-0 items-center rounded border px-2 py-0.5 text-[10px] font-semibold ${timing.priorityClass}">${escapeLiveHtml(timing.status)}</span>
      </div>
      <p class="font-body-sm text-text-muted">${escapeLiveHtml(item.contact_name || item.client_name || "No contact")}</p>
      <p class="mt-0.5 truncate font-body-sm text-text-muted text-[11px]">${escapeLiveHtml(item.notes || "No notes")}</p>
    </div>
    <div class="flex shrink-0 items-center gap-3">
      <span class="${timing.dateClass} font-data-tabular text-[11px]">${escapeLiveHtml(timing.label)}</span>
    </div>
  </div>`;
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
  return `<div class="flex items-center gap-4 p-4 ${index === 0 ? "" : "border-t border-border"} transition-colors hover:bg-highlight-soft" data-live-interview-row="true" data-interview-id="${item.id}">
    <div class="min-w-0 flex-1">
      <div class="mb-1 flex items-center gap-2">
        <h4 class="truncate font-body-md font-semibold text-on-surface">${escapeLiveHtml(item.candidate_name || "Candidate")}</h4>
        <span class="inline-flex shrink-0 items-center rounded border px-2 py-0.5 text-[10px] font-semibold ${interviewStatusBadge(item.feedback_status || item.status)}">${escapeLiveHtml(item.feedback_status || item.status || "Pending")}</span>
      </div>
      <p class="font-body-sm text-text-muted">${escapeLiveHtml(item.requisition_title || "Requisition")}</p>
      <p class="mt-0.5 text-[11px] text-text-muted">${escapeLiveHtml(item.round_type || item.interview_type || "Interview")} · ${escapeLiveHtml(formatWhen(item.scheduled_at))}</p>
    </div>
    <button class="rounded p-1 text-text-muted transition-colors hover:bg-surface-variant hover:text-primary" type="button" data-route="interview-detail.html?interview_id=${item.id}" aria-label="View interview details">
      <span class="material-symbols-outlined text-[20px]">open_in_new</span>
    </button>
  </div>`;
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
