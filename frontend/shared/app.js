

const WORKSPACE_INSIGHTS = {
  "user-management": {
    title: "User coverage snapshot",
    copy: "Review permission health, invite backlog, and ownership balance at a glance.",
    cards: [
      { icon: "mail", label: "Pending invites", value: "3 users", copy: "Two invites are older than 48 hours and should be nudged first." },
      { icon: "shield_person", label: "Permission drift", value: "5 roles", copy: "Five accounts have role-location combinations worth auditing before the next sync." },
      { icon: "hub", label: "Manager load", value: "2 hotspots", copy: "Two managers currently own the densest approval and onboarding coverage." },
    ],
  },
  "location-management": {
    title: "Location rollout snapshot",
    copy: "This panel keeps setup risk, unassigned leadership, and rollout readiness visible without needing a permanent right rail.",
    cards: [
      { icon: "location_on", label: "Pending setup", value: "4 locations", copy: "Four locations still need complete operating coverage before activation." },
      { icon: "person_search", label: "Unassigned leads", value: "1 location", copy: "Austin Tech Center is the only current location without a designated owner." },
      { icon: "schedule", label: "Recent change window", value: "2 active updates", copy: "Two location records were updated recently enough to watch for downstream user-scope drift." },
    ],
  },
};
const HEADINGLESS_WORKSPACE_ROUTES = new Set([
  "analytics-dashboard",
  "custom-report-builder",
  "pipeline-analytics",
  "sla-tracker",
  "source-effectiveness",
  "team-workload",
  "time-to-fill-report",
]);

const FORCED_WORKSPACE_HEADINGS = {
  "review-matches-workspace": {
    title: "Review Matches",
    subtitle: "Compare potential duplicates and resolve the incoming candidate record.",
  },
  reports: {
    title: "Reports",
    subtitle: "Browse saved reports or generate a focused recruiting view.",
  },
};

const SHORTCUT_CATALOG = [
  { keys: ["Esc"], label: "Close overlays" },
  { keys: ["Alt", "←"], label: "Go back" },
  { keys: ["Alt", "→"], label: "Go forward" },
  { keys: ["Ctrl", "Shift", "N"], label: "New candidate" },
  { keys: ["Shift", "G"], label: "Go to dashboard" },
  { keys: ["/"], label: "Focus search" },
  { keys: ["?"], label: "Show shortcuts" },
];

const SHORTCUT_HINT_ID = "shortcut-hint";

function isEditableElement(target) {
  if (!(target instanceof HTMLElement)) return false;
  return Boolean(target.closest("input, textarea, select, [contenteditable='true']"));
}

function closeOpenOverlays() {
  document.querySelectorAll("[data-overlay-surface='true']").forEach((surface) => {
    const close = surface.querySelector("[data-overlay-close]") || surface.querySelector("button[aria-label*='close'], button[aria-label*='Close']");
    if (close) close.click();
  });
  const mobileDialog = window._mobileDialog;
  if (mobileDialog?.open) {
    closeMobileNav(mobileDialog);
  }
}

function attachKeyboardShortcuts() {
  document.removeEventListener("keydown", handleKeyDown);
  document.addEventListener("keydown", handleKeyDown);
}

/* ═══════════════════════════════════════════════════════════════
   TABLE DENSITY TOGGLE
   Comfortable ↔ compact rows. One preference, persisted per user,
   applied before first paint on every app page (see applyDensity
   call at module top of DOMContentLoaded). Button lives in the
   topbar, injected so every page gets it without HTML edits.
   ═══════════════════════════════════════════════════════════════ */
const DENSITY_KEY = "recruitops.table_density";

function readDensityPreference() {
  try { return localStorage.getItem(DENSITY_KEY) === "compact" ? "compact" : "comfortable"; }
  catch { return "comfortable"; }
}

function applyDensityPreference(density) {
  document.documentElement.classList.toggle("density-compact", density === "compact");
  const btn = document.getElementById("density-toggle");
  if (btn) {
    const compact = density === "compact";
    btn.setAttribute("aria-pressed", String(compact));
    btn.title = compact ? "Table density: compact (click for comfortable)" : "Table density: comfortable (click for compact)";
    const icon = btn.querySelector(".material-symbols-outlined");
    if (icon) icon.textContent = compact ? "density_small" : "density_medium";
  }
}

function setDensityPreference(density) {
  try { localStorage.setItem(DENSITY_KEY, density); } catch { /* private mode */ }
  applyDensityPreference(density);
}

function injectDensityToggle() {
  if (document.getElementById("density-toggle")) return;
  const topbar = document.querySelector(".app-topbar");
  if (!topbar) return;
  const actions = topbar.querySelector(".flex.items-center.gap-2") || topbar;
  const btn = document.createElement("button");
  btn.id = "density-toggle";
  btn.type = "button";
  btn.className = "topbar-action rounded-full border border-border bg-surface p-2 text-on-surface";
  btn.setAttribute("aria-pressed", "false");
  btn.setAttribute("aria-label", "Toggle table density");
  btn.innerHTML = '<span class="material-symbols-outlined text-[18px]">density_medium</span>';
  btn.addEventListener("click", () => {
    setDensityPreference(readDensityPreference() === "compact" ? "comfortable" : "compact");
    showToast("Table density changed", readDensityPreference() === "compact" ? "Rows are compacted to fit more on screen." : "Rows are back to comfortable spacing.");
  });
  const search = topbar.querySelector(".topbar-search");
  if (search) { search.after(btn); } else { actions.appendChild(btn); }
  applyDensityPreference(readDensityPreference());
}

function handleKeyDown(event) {
  // Don't steal keys from inputs unless we explicitly allow it.
  const editing = isEditableElement(event.target);

  if (event.key === "Escape" && !editing) {
    const helpOverlay = document.getElementById("shortcut-help-overlay");
    if (helpOverlay) { helpOverlay.remove(); return; }
    if (paletteElements && !paletteElements.overlay.classList.contains("hidden")) { closeCommandPalette(); return; }
    closeOpenOverlays();
    return;
  }

  if (editing) {
    if (event.key === "Escape") {
      event.target.blur();
    }
    return;
  }

  const ctrl = event.ctrlKey || event.metaKey;
  if (ctrl && !event.shiftKey && event.key.toLowerCase() === "k") {
    event.preventDefault();
    toggleCommandPalette();
    return;
  }
  if (ctrl && event.shiftKey && event.key.toLowerCase() === "n") {
    event.preventDefault();
    const candidateRoute =
      window.location.pathname.includes("candidate-profiles")
        ? "candidate-review-drawer.html"
        : "candidate-review-drawer.html";
    navigateToRoute(candidateRoute);
    return;
  }

  if (event.altKey) {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      history.back();
      return;
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      history.forward();
      return;
    }
  }

  if (event.key.toLowerCase() === "g" && event.shiftKey) {
    event.preventDefault();
    navigateToRoute("role-dashboard.html");
    return;
  }

  if (event.key === "/" && !event.ctrlKey && !event.metaKey) {
    event.preventDefault();
    const searchInput = document.querySelector(".topbar-search input, #topbar-search");
    if (searchInput) { searchInput.focus(); }
    return;
  }

  if (event.key === "?" && !event.ctrlKey && !event.metaKey) {
    event.preventDefault();
    toggleShortcutHelp();
    return;
  }
}

function toggleShortcutHelp() {
  const existing = document.getElementById("shortcut-help-overlay");
  if (existing) { existing.remove(); return; }
  const overlay = document.createElement("div");
  overlay.id = "shortcut-help-overlay";
  overlay.className = "fixed inset-0 z-[9998] flex items-center justify-center bg-black/40";
  overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
  overlay.innerHTML = `
    <div class="bg-surface rounded-xl border border-border shadow-xl w-full max-w-lg p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-headline-sm font-semibold text-on-surface">Keyboard Shortcuts</h3>
        <button onclick="this.closest('#shortcut-help-overlay').remove()" class="text-text-muted hover:text-on-surface p-1"><span class="material-symbols-outlined text-[20px]">close</span></button>
      </div>
      <div class="space-y-2 text-sm">
        <div class="flex justify-between py-1.5 border-b border-border"><span class="text-on-surface">Command palette</span><div><kbd class="px-2 py-0.5 rounded bg-surface-alt border border-border font-mono text-[12px]">Ctrl</kbd> <kbd class="px-2 py-0.5 rounded bg-surface-alt border border-border font-mono text-[12px]">K</kbd></div></div>
        <div class="flex justify-between py-1.5 border-b border-border"><span class="text-on-surface">Close overlays / dialogs</span><kbd class="px-2 py-0.5 rounded bg-surface-alt border border-border font-mono text-[12px]">Esc</kbd></div>
        <div class="flex justify-between py-1.5 border-b border-border"><span class="text-on-surface">Go back</span><div><kbd class="px-2 py-0.5 rounded bg-surface-alt border border-border font-mono text-[12px]">Alt</kbd> <kbd class="px-2 py-0.5 rounded bg-surface-alt border border-border font-mono text-[12px]">←</kbd></div></div>
        <div class="flex justify-between py-1.5 border-b border-border"><span class="text-on-surface">Go forward</span><div><kbd class="px-2 py-0.5 rounded bg-surface-alt border border-border font-mono text-[12px]">Alt</kbd> <kbd class="px-2 py-0.5 rounded bg-surface-alt border border-border font-mono text-[12px]">→</kbd></div></div>
        <div class="flex justify-between py-1.5 border-b border-border"><span class="text-on-surface">New candidate</span><div><kbd class="px-2 py-0.5 rounded bg-surface-alt border border-border font-mono text-[12px]">Ctrl</kbd> <kbd class="px-2 py-0.5 rounded bg-surface-alt border border-border font-mono text-[12px]">Shift</kbd> <kbd class="px-2 py-0.5 rounded bg-surface-alt border border-border font-mono text-[12px]">N</kbd></div></div>
        <div class="flex justify-between py-1.5 border-b border-border"><span class="text-on-surface">Go to dashboard</span><div><kbd class="px-2 py-0.5 rounded bg-surface-alt border border-border font-mono text-[12px]">Shift</kbd> <kbd class="px-2 py-0.5 rounded bg-surface-alt border border-border font-mono text-[12px]">G</kbd></div></div>
        <div class="flex justify-between py-1.5 border-b border-border"><span class="text-on-surface">Focus search</span><kbd class="px-2 py-0.5 rounded bg-surface-alt border border-border font-mono text-[12px]">/</kbd></div>
        <div class="flex justify-between py-1.5"><span class="text-on-surface">Show this help</span><kbd class="px-2 py-0.5 rounded bg-surface-alt border border-border font-mono text-[12px]">?</kbd></div>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);
}

function attachShortcutHint() {
  /* App workspaces only — marketing, auth, and overlay pages don't need it */
  if (!document.querySelector(".app-shell")) return;
  const kind = document.body?.dataset.routeKind || "";
  if (["marketing", "auth", "overlay"].includes(kind)) return;
  if (document.getElementById(SHORTCUT_HINT_ID)) return;
  const hint = document.createElement("div");
  hint.id = SHORTCUT_HINT_ID;
  hint.className = "shortcut-hint";
  hint.setAttribute("role", "note");
  hint.setAttribute("aria-label", "Keyboard shortcuts");
  hint.innerHTML = `
    <div class="shortcut-hint-inner">
      <span class="shortcut-hint-label">Shortcuts</span>
      <kbd>Esc</kbd> close
      <kbd>Alt</kbd><kbd>←</kbd> back
      <kbd>Alt</kbd><kbd>→</kbd> forward
      <kbd>?</kbd> help
    </div>
  `;
  document.body.appendChild(hint);
}

const RO_LOGO_SVG = `<svg class="ro-logo" viewBox="0 0 48 48" fill="none" aria-hidden="true"><circle class="ro-logo-ring" cx="24" cy="24" r="17" stroke="currentColor" stroke-width="7" stroke-linecap="round" stroke-dasharray="55 14 17 14" stroke-dashoffset="10" pathLength="100"/><circle cx="24" cy="24" r="6.5" fill="currentColor"/></svg>`;

function upgradeBrandMarks() {
  document.querySelectorAll(".sidebar-mark").forEach((mark) => {
    if (mark.querySelector(".ro-logo")) return;
    mark.innerHTML = RO_LOGO_SVG;
  });
}

function setupToggleGroups(scope = document) {
  scope.querySelectorAll("[data-toggle-group='true'], div[class*='space-x-1']").forEach((group) => {
    if (group.dataset.toggleGroupInitialized === "true") return;
    const buttons = Array.from(group.children).filter((child) => child.tagName === "BUTTON");
    if (buttons.length < 2) return;
    group.dataset.toggleGroup = "true";
    group.dataset.toggleGroupInitialized = "true";
    const activeButton =
      buttons.find((button) => /bg-secondarycontainer|bg-secondary-container|bg-primary|border-primary|text-primary|shadow-sm/.test(button.className)) ||
      buttons[0];
    if (activeButton) {
      activeButton.classList.add("is-active");
      activeButton.setAttribute("aria-pressed", "true");
    }
    buttons.forEach((button) => {
      if (!button.getAttribute("type")) {
        button.setAttribute("type", "button");
      }
      if (button !== activeButton) {
        button.setAttribute("aria-pressed", "false");
      }
    });
  });
}

function setupWorkspaceInsights() {
  const routeId = document.body?.dataset.routeId || "";
  const config = WORKSPACE_INSIGHTS[routeId];
  if (!config) return;

  const trigger = Array.from(document.querySelectorAll("button"))
    .find((button) => /\binsights\b/i.test(getActionLabel(button)));
  const host = document.querySelector("[data-demo-validate]");
  if (!trigger || !host || host.querySelector("[data-workspace-insight-panel]")) return;

  const panel = document.createElement("section");
  const panelId = `workspace-insights-${routeId}`;
  panel.id = panelId;
  panel.hidden = true;
  panel.dataset.workspaceInsightPanel = "true";
  panel.className = "workspace-insight-panel";
  panel.tabIndex = -1;
  panel.innerHTML = `
    <div class="workspace-insight-panel-header">
      <div>
        <p class="workspace-insight-card-label">
          <span class="material-symbols-outlined text-[16px]">insights</span>
          Workspace insight
        </p>
        <h3>${config.title}</h3>
        <p>${config.copy}</p>
      </div>
      <button type="button" class="workspace-insight-panel-dismiss" data-workspace-insight-close aria-label="Close insights panel">
        <span class="material-symbols-outlined text-[18px]">close</span>
      </button>
    </div>
    <div class="workspace-insight-panel-body">
      ${config.cards.map((card) => `
        <article class="workspace-insight-card">
          <p class="workspace-insight-card-label">
            <span class="material-symbols-outlined text-[16px]">${card.icon}</span>
            ${card.label}
          </p>
          <p class="workspace-insight-card-value">${card.value}</p>
          <p class="workspace-insight-card-copy">${card.copy}</p>
        </article>
      `).join("")}
    </div>
  `;

  host.prepend(panel);
  trigger.type = "button";
  trigger.dataset.workspaceInsightTrigger = "true";
  trigger.setAttribute("aria-expanded", "false");
  trigger.setAttribute("aria-controls", panelId);
  const triggerIcon = trigger.querySelector(".material-symbols-outlined");
  if (triggerIcon && !trigger.dataset.workspaceInsightOriginalIcon) {
    trigger.dataset.workspaceInsightOriginalIcon = (triggerIcon.textContent || "").trim();
  }

  const dismiss = panel.querySelector("[data-workspace-insight-close]");

  const closePanel = ({ restoreFocus = true } = {}) => {
    panel.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
    trigger.classList.remove("is-active");
    const icon = trigger.querySelector(".material-symbols-outlined");
    if (icon) {
      icon.textContent = trigger.dataset.workspaceInsightOriginalIcon || "insights";
    }
    if (restoreFocus) {
      window.requestAnimationFrame(() => trigger.focus());
    }
  };

  const openPanel = () => {
    panel.hidden = false;
    trigger.setAttribute("aria-expanded", "true");
    trigger.classList.add("is-active");
    const icon = trigger.querySelector(".material-symbols-outlined");
    if (icon && /right_panel_open|insights/.test(icon.textContent || "")) {
      icon.textContent = "right_panel_close";
    }
    window.requestAnimationFrame(() => panel.focus());
  };

  trigger.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (panel.hidden) {
      openPanel();
        return;
    }
    closePanel({ restoreFocus: false });
  });

  dismiss?.addEventListener("click", () => closePanel());
  document.addEventListener("click", (event) => {
    if (panel.hidden) return;
    const target = event.target;
    if (!(target instanceof Node)) return;
    if (panel.contains(target) || trigger.contains(target)) return;
    closePanel({ restoreFocus: false });
  });
}

function setupRecordLinkPolish() {
  const routeId = document.body?.dataset.routeId || "";

  const activateSurfaceRoute = (surface) => {
    if (!surface?.dataset.route) return;
    window.location.href = surface.dataset.route;
  };

  const promoteSurfaceRoute = (surface, route, ariaLabel) => {
    if (!surface || surface.dataset.route) return;
    surface.dataset.route = route;
    surface.dataset.surfaceRoute = "true";
    surface.tabIndex = 0;
    surface.setAttribute("role", "button");
    surface.setAttribute("aria-label", ariaLabel);
    surface.classList.add("cursor-pointer", "focus-visible:outline-none", "focus-visible:ring-2", "focus-visible:ring-primary", "focus-visible:ring-offset-2", "focus-visible:ring-offset-background");

    surface.addEventListener("click", (event) => {
      if (event.target.closest("a, button, input, select, textarea, label")) return;
      activateSurfaceRoute(surface);
    });

    surface.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      activateSurfaceRoute(surface);
    });
  };

  if (routeId === "approvals-inbox") {
    document.querySelectorAll("tbody tr").forEach((row) => {
      const relatedRecordCell = row.querySelectorAll("td")[2];
      if (!relatedRecordCell || relatedRecordCell.querySelector("a, button")) return;
      const recordText = (relatedRecordCell.textContent || "").replace(/\s+/g, " ").trim();
      if (!recordText) return;
      const route = /^REQ-/i.test(recordText)
        ? "requisition-detail.html"
        : /^CAND-/i.test(recordText)
          ? "candidate-review-drawer.html"
          : "";
      if (!route) return;

      const trigger = document.createElement("button");
      trigger.type = "button";
      trigger.dataset.route = route;
      trigger.className = "text-primary hover:underline font-inherit";
      trigger.textContent = recordText;
      trigger.setAttribute("aria-label", `Open ${recordText}`);
      relatedRecordCell.textContent = "";
      relatedRecordCell.appendChild(trigger);
    });
  }

  if (routeId === "role-dashboard") {
    const metricRoutes = [
      { match: /open requisitions/i, route: "requisition-list.html", label: "Open Requisitions" },
      { match: /active candidates/i, route: "candidate-profiles.html", label: "Active Candidates" },
      { match: /active applications/i, route: "candidate-screening.html", label: "Active Applications" },
      { match: /pending updates/i, route: "daily-updates-workspace.html", label: "Pending Updates" },
    ];

    document.querySelectorAll('[data-layout="metric-card"], [data-role-kpi-strip] > div').forEach((card) => {
      const label = (card.textContent || "").replace(/\s+/g, " ").trim();
      const config = metricRoutes.find((entry) => entry.match.test(label));
      if (!config) return;
      promoteSurfaceRoute(card, config.route, config.label);
    });

    document.querySelectorAll("p").forEach((copy) => {
      const text = (copy.textContent || "").replace(/\s+/g, " ").trim();
      if (!/^REQ-\d+/i.test(text)) return;
      const requisitionRow = copy.closest("div.flex.justify-between.items-start");
      if (!requisitionRow) return;
      promoteSurfaceRoute(requisitionRow, "requisition-detail.html", `Open ${text}`);
    });
  }

  if (routeId === "client-detail") {
    document.querySelectorAll("td").forEach((cell) => {
      const label = (cell.textContent || "").replace(/\s+/g, " ").trim();
      if (!/^(Senior Frontend Engineer|Product Manager|Backend Developer|DevOps Engineer)$/i.test(label)) return;
      promoteSurfaceRoute(cell, "requisition-detail.html", `Open ${label}`);
    });
  }

  if (routeId === "location-management") {
    document.querySelectorAll("span, div").forEach((node) => {
      const label = (node.textContent || "").replace(/\s+/g, " ").trim();
      if (/^(HQ - San Francisco|London Hub|Austin Tech Center|LOC-001|LOC-042|LOC-088)$/i.test(label)) {
        promoteSurfaceRoute(node, "location-management.html", `Open ${label}`);
      }
    });
  }

  if (routeId === "delivery-work-queue") {
    const metricRoutes = [
      { match: /overdue actions/i, route: "requisition-detail.html", label: "Open Overdue Actions" },
      { match: /approaching sla/i, route: "candidate-screening.html", label: "Open Approaching SLA Queue" },
      { match: /stale movements/i, route: "pipeline-board.html", label: "Open Stale Movements" },
      { match: /new matches/i, route: "candidate-profiles.html", label: "Open New Matches" },
    ];

    document.querySelectorAll('[data-layout="metric-card"]').forEach((card) => {
      const label = (card.textContent || "").replace(/\s+/g, " ").trim();
      const config = metricRoutes.find((entry) => entry.match.test(label));
      if (!config) return;
      promoteSurfaceRoute(card, config.route, config.label);
    });

    document.querySelectorAll("span").forEach((copy) => {
      const label = (copy.textContent || "").replace(/\s+/g, " ").trim();
      if (!/^(Alex Rodriguez|Emily Chen|David R\.)$/i.test(label)) return;
      promoteSurfaceRoute(copy, "candidate-review-drawer.html", `Open ${label}`);
    });
  }

  if (routeId === "my-work-dashboard") {
    document.querySelectorAll("td, div, button").forEach((node) => {
      const label = (node.textContent || "").replace(/\s+/g, " ").trim();
      if (/^REQ-(923|924|930|942)$/i.test(label)) {
        promoteSurfaceRoute(node, "requisition-detail.html", `Open ${label}`);
        return;
      }
      if (/^3 Pipeline Exceptions$/i.test(label)) {
        promoteSurfaceRoute(node, "exception-request-dialog.html", "Open Pipeline Exceptions");
        return;
      }
      if (/^Missing Budget Approval$/i.test(label)) {
        promoteSurfaceRoute(node, "requisition-detail.html", "Open Missing Budget Approval");
        return;
      }
      if (/^14$/.test(label) && node.closest('[data-layout="workload-strip"]')) {
        promoteSurfaceRoute(node.closest('[data-layout="metric-card"]') || node, "candidate-profiles.html", "Open New Applicants");
      }
    });
  }

  if (routeId === "requisition-list") {
    document.querySelectorAll("td, span, button").forEach((node) => {
      const label = (node.textContent || "").replace(/\s+/g, " ").trim();
      if (/^REQ-(9012|9008|9022)$/i.test(label)) {
        promoteSurfaceRoute(node, "requisition-detail.html", `Open ${label}`);
        return;
      }
      if (/^(Senior Frontend Engineer|Product Manager|VP of Engineering)$/i.test(label)) {
        promoteSurfaceRoute(node, "requisition-detail.html", `Open ${label}`);
        return;
      }
    });
  }

  if (routeId === "notifications-center") {
    document.querySelectorAll("h4, span, div").forEach((node) => {
      const label = (node.textContent || "").replace(/\s+/g, " ").trim();
      if (/^(Total Unread|High Priority|Mentioned)$/i.test(label)) {
        promoteSurfaceRoute(node.closest("div.bg-surface, div.bg-danger-bg") || node, "notification-detail-panel.html", `Open ${label}`);
        return;
      }
      if (/^REQ-9102$/i.test(label) || /^Elena Rostova$/i.test(label) || /^Michael Chang$/i.test(label)) {
        promoteSurfaceRoute(node, "notification-detail-panel.html", `Open ${label}`);
      }
    });
  }

  if (routeId === "daily-updates-workspace") {
    document.querySelectorAll("h4, span, div").forEach((node) => {
      const label = (node.textContent || "").replace(/\s+/g, " ").trim();
      if (/^(Updates Submitted|Pending Review)$/i.test(label)) {
        promoteSurfaceRoute(node.closest("div.bg-surface") || node, "daily-update-detail-panel.html", `Open ${label}`);
        return;
      }
      if (/^(UX Designer \(REQ-9102\)|Backend Lead \(REQ-8771\)|Marketing Director \(REQ-9011\)|DevOps Engineer \(REQ-8920\))$/i.test(label)) {
        promoteSurfaceRoute(node, "daily-update-detail-panel.html", `Open ${label}`);
      }
    });
  }

  if (routeId === "pipeline-board") {
    document.querySelectorAll("p, button, div").forEach((node) => {
      const label = (node.textContent || "").replace(/\s+/g, " ").trim();
      if (/^(Alex Mercer|Sarah Chen|David Jones|Omar Farooq|Elena Rostova|Kunal Patel)$/i.test(label)) {
        promoteSurfaceRoute(node, "candidate-review-drawer.html", `Open ${label}`);
      }
    });

    document.querySelectorAll('div[class*="w-[300px]"]').forEach((column) => {
      const stageName = (column.querySelector("h3")?.textContent || "").replace(/\s+/g, " ").trim();
      if (!stageName) return;
      const addButton = column.querySelector(":scope > div button");
      if (!addButton) return;
      promoteSurfaceRoute(addButton, "candidate-review-drawer.html", `Open ${stageName} candidate workspace`);
    });
  }
}

function setupContextualActionToasts() {}

function setupWorkflowActionPolish() {
  const routeId = document.body?.dataset.routeId || "";

  if (routeId === "candidate-screening") {
    document.querySelectorAll("button").forEach((button) => {
      const label = getActionLabel(button);
      if (/save draft/.test(label)) {
        button.dataset.toastTitle = "Draft saved";
        button.dataset.toast = "Your screening notes are saved.";
      }
      if (/submit evaluation/.test(label)) {
        button.dataset.toastTitle = "Evaluation submitted";
        button.dataset.toast = "Your decision has been recorded.";
      }
    });
  }

  if (routeId === "candidate-duplicate-review") {
    document.querySelectorAll("button").forEach((button) => {
      const label = getActionLabel(button);
      if (/skip for now/.test(label)) {
        button.dataset.toastTitle = "Skipped";
        button.dataset.toast = "This case will stay in the review queue.";
      }
    });
  }
}

function setupOverlayInteractionPolish(scope = document) {
  scope.querySelectorAll("[data-overlay-surface='true']").forEach((surface) => {
    if (surface.dataset.overlayStructureNormalized !== "true") {
      surface.dataset.overlayStructureNormalized = "true";
      const markOverlaySections = (container) => {
        const directChildren = Array.from(container.children);
        if (!directChildren.length) return;
        directChildren.forEach((child, index) => {
          const className = child.className || "";
          const isFirst = index === 0;
          const isLast = index === directChildren.length - 1;
          const hasHeading = Boolean(child.querySelector("h1, h2, h3"));
          const hasClose = Boolean(child.querySelector("[data-overlay-close], [aria-label*='Close'], .material-symbols-outlined"));
          const hasPrimaryAction = Boolean(child.querySelector("button, a[href]"));
          const looksLikeHeader = isFirst && (
            /border-b|rounded-t|items-start|items-center|justify-between/.test(className) ||
            (hasHeading && hasClose)
          );
          const looksLikeFooter = isLast && (
            /border-t|mt-auto|justify-end|rounded-b/.test(className) ||
            (hasPrimaryAction && !hasHeading && directChildren.length > 2)
          );
          const looksLikeBody = /flex-1|overflow-y-auto|overflow-auto|custom-scrollbar/.test(className);

          if (looksLikeHeader) {
            child.dataset.overlaySection = "header";
          } else if (looksLikeFooter) {
            child.dataset.overlaySection = "footer";
          } else if (looksLikeBody) {
            child.dataset.overlaySection = "body";
          }
        });

        const header = container.querySelector(":scope > [data-overlay-section='header']");
        const footer = container.querySelector(":scope > [data-overlay-section='footer']");
        const body = container.querySelector(":scope > [data-overlay-section='body']");
        if (!body) {
          directChildren
            .filter((child) => child !== header && child !== footer)
            .forEach((child) => {
              if (!child.dataset.overlaySection) child.dataset.overlaySection = "body";
            });
        }
      };

      const structuralRoot = surface.children.length === 1 && surface.firstElementChild?.children.length > 1
        ? surface.firstElementChild
        : surface;
      if (structuralRoot !== surface) {
        structuralRoot.dataset.overlayFrame = "true";
      }
      markOverlaySections(structuralRoot);

      const bodySection = structuralRoot.querySelector(":scope > [data-overlay-section='body']");
      const footerSection = structuralRoot.querySelector(":scope > [data-overlay-section='footer']");
      const nestedFooter = bodySection && !footerSection
        ? Array.from(bodySection.children).reverse().find((child) => {
          const className = child.className || "";
          return /border-t|justify-end|rounded-b/.test(className) && child.querySelector("button, a[href]");
        })
        : null;
      if (nestedFooter) {
        nestedFooter.dataset.overlaySection = "footer";
        structuralRoot.appendChild(nestedFooter);
      }
    }

    surface.querySelectorAll("button").forEach((button) => {
      if (!button.getAttribute("type")) {
        button.setAttribute("type", "button");
      }
      const icon = button.querySelector(".material-symbols-outlined")?.textContent?.trim().toLowerCase() || "";
      if (icon === "close") {
        if (!button.getAttribute("aria-label")) {
          button.setAttribute("aria-label", "Close overlay");
        }
        if (!button.getAttribute("title")) {
          button.setAttribute("title", "Close overlay");
        }
        button.dataset.overlayClose = "true";
      }
      const label = getActionLabel(button);
      if (/^(cancel|back|cancel and go back)$/i.test(label)) {
        button.dataset.overlayClose = "true";
        if (!button.getAttribute("title")) {
          button.setAttribute("title", "Close overlay");
        }
      }
    });
  });
}

function setupOverlayContextPolish() {
  if (document.body?.dataset.overlayPage !== "true") return;
  const surface = document.querySelector("[data-overlay-surface='true']");
  if (!surface) return;

  const routeId = document.body?.dataset.routeId || "";
  const routeTitle = (document.body.dataset.routeTitle || "").replace(/\s+/g, " ").trim();
  const parentTitle = (document.body.dataset.parentTitle || "").replace(/\s+/g, " ").trim();
  const titleNodes = Array.from(document.querySelectorAll("[data-shell-page-title], [data-shell-focus-title]"));
  const shellFocusCopyNode = document.querySelector("[data-shell-focus-copy]");
  const normalize = (value) => value.replace(/\s+/g, " ").trim().toLowerCase();
  const authoredShellCopy = (shellFocusCopyNode?.textContent || "").replace(/\s+/g, " ").trim();
  const preserveShellMountCopy = Boolean(
    authoredShellCopy
      && /stays mounted on/i.test(authoredShellCopy)
      && (!parentTitle || normalize(authoredShellCopy).includes(normalize(parentTitle))),
  );
  const headerSection = surface.querySelector("[data-overlay-section='header']");
  const headerNode = headerSection?.querySelector("h1, h2, h3");
  const headerHeading = (headerNode?.textContent || "").replace(/\s+/g, " ").trim();
  const headerCopyNode = headerSection?.querySelector("p");
  const headerCopy = (headerCopyNode?.textContent || "").replace(/\s+/g, " ").trim();
  const headerMetaCandidates = Array.from(headerSection?.querySelectorAll("span, div") || [])
    .map((node) => (node.textContent || "").replace(/\s+/g, " ").trim())
    .filter(Boolean)
    .filter((text) => normalize(text) !== normalize(routeTitle))
    .filter((text) => normalize(text) !== normalize(parentTitle))
    .filter((text) => normalize(text) !== normalize(headerHeading))
    .filter((text) => text.length <= 96)
    .filter((text) => !/^close(?:\s+(?:overlay|dialog|drawer|panel))?$/i.test(text));
  const headerMeta = headerMetaCandidates[0] || "";
  const usableHeaderCopy = headerCopy
    && normalize(headerCopy) !== normalize(routeTitle)
    && normalize(headerCopy) !== normalize(parentTitle)
    && normalize(headerCopy) !== normalize(headerHeading)
    && headerCopy.length <= 96
      ? headerCopy
      : headerMeta;

  const headingCandidates = [headerHeading, ...Array.from(surface.querySelectorAll("h1, h2, h3"))
    .map((node) => (node.textContent || "").replace(/\s+/g, " ").trim())
  ]
    .filter(Boolean)
    .filter((text) => normalize(text) !== normalize(routeTitle))
    .filter((text) => normalize(text) !== normalize(parentTitle))
    .filter((text) => text.length <= 72);

  const primaryHeading = headingCandidates[0];
  if (!primaryHeading) return;

  const actionLikeHeading = /\b(add|create|edit|move|review|reassign|request|configure|history|detail|notification|contact|location|role|user|client|candidate|pipeline|exception)\b/i.test(primaryHeading);
  const genericRouteTitle = /\b(workspace|detail|panel)\b/i.test(routeTitle);
  const routeContainsHeading = normalize(routeTitle).includes(normalize(primaryHeading));
  const headingContainsRoute = normalize(primaryHeading).includes(normalize(routeTitle));
  const meaningfullyDifferentTitle = !routeContainsHeading && !headingContainsRoute;
  const explicitActionTitleRoutes = new Set();
  const shouldPromoteTitle = !explicitActionTitleRoutes.has(routeId) && meaningfullyDifferentTitle && (actionLikeHeading || genericRouteTitle);

  if (shouldPromoteTitle) {
    titleNodes.forEach((node) => {
      node.textContent = primaryHeading;
    });
    document.body.dataset.routeTitle = primaryHeading;
    document.title = `${primaryHeading} - RecruitOps`;
    if (!preserveShellMountCopy && shellFocusCopyNode) {
      shellFocusCopyNode.textContent = actionLikeHeading
        ? `This action stays mounted on ${parentTitle || "the parent workspace"} while preserving the shared blurred overlay model.`
        : `Focused on ${primaryHeading} while keeping ${parentTitle || "the parent workspace"} in context.`;
    }
    return;
  }

  if (!preserveShellMountCopy && shellFocusCopyNode) {
    shellFocusCopyNode.textContent = usableHeaderCopy || `Focused on ${primaryHeading} while keeping ${parentTitle || "the parent workspace"} in context.`;
  }
}

function setupGenericActionAnnotations(scope = document) {
  const routeId = document.body?.dataset.routeId || "";

  scope.querySelectorAll("button, a[href='javascript:void(0)']").forEach((control) => {
    if (control.closest("form, [data-layout='pagination-controls'], [data-toggle-group]")) return;
    if (
      control.matches("[data-route], [data-toast], [data-overlay-close], [data-reset-toolbar-filters], [data-clear-search-preview], [data-mobile-nav-open], [data-mobile-nav-close], [data-notification-read], [data-duplicate-resolution-confirm], [data-flow-reset], [data-validate-scope], [aria-haspopup='menu']")
    ) return;
    const type = (control.getAttribute("type") || "").toLowerCase();
    if (type === "submit") return;

    const label = getActionLabel(control);
    const icon = control.querySelector(".material-symbols-outlined")?.textContent?.trim().toLowerCase() || "";
    const normalized = (label || icon).replace(/\s+/g, " ").trim().toLowerCase();
    const insideOverlay = control.closest("[data-overlay-surface]");

    if (routeId === "requisition-intake" && normalized === "cancel") {
      control.dataset.route = "requisition-list.html";
      return;
    }
    if (routeId === "requisition-intake" && /create requisition/.test(normalized)) {
      control.dataset.validateScope = "#requisition-form";
      control.dataset.successTitle = "Looks good";
      control.dataset.successText = "All required fields are complete.";
      return;
    }

    if (insideOverlay && !control.closest("form") && !control.id && /save|submit|confirm|approve|review|move|request|create|add|link/.test(normalized)) {
      control.dataset.overlayAction = "validate";
    }
  });
}

function setupWorkspaceChrome(scope = document) {
  const routeId = document.body?.dataset.routeId || "";

  scope.querySelectorAll("button").forEach((button) => {
    if (button.dataset.chromeBound === "true") return;
    if (button.dataset.route || button.dataset.toast) return;
    if (button.closest("form, table, [data-layout='pagination-controls'], [role='menu'], .ro-row-menu")) return;
    if (button.getAttribute("aria-haspopup") === "menu") return;
    const label = getActionLabel(button);
    const icon = button.querySelector(".material-symbols-outlined")?.textContent?.trim().toLowerCase() || "";
    const isExport = /export/.test(label) || (icon === "download" && /export|list/.test(label));
    const isRefresh = /^(refresh|reload)/.test(label.replace(icon, "").trim()) || (icon === "refresh" && /refresh|reload/.test(label));
    const isFilter = /^(filter|filters)$/.test(label.replace(/filter_list/g, "").trim());
    const isSaveView = /save view/.test(label);
    if (!isExport && !isRefresh && !isFilter && !isSaveView) return;
    button.dataset.chromeBound = "true";
    if (!button.getAttribute("type")) button.setAttribute("type", "button");
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (isExport) {
        exportWorkspaceAsCsv();
        return;
      }
      if (isRefresh) {
        showToast("Refreshing", "Reloading this view.");
        window.location.reload();
        return;
      }
      if (isFilter) {
        if (routeId === "role-dashboard") {
          const rows = Array.from(document.querySelectorAll("[data-live-workflow-row]"));
          if (!rows.length) {
            button.hidden = true;
            showToast("Queue is clear", "There is nothing to filter.");
            return;
          }
          const modes = ["all", "high", "overdue"];
          const next = modes[(modes.indexOf(button.dataset.filterMode || "all") + 1) % modes.length];
          button.dataset.filterMode = next;
          rows.forEach((row) => {
            const text = (row.textContent || "").toLowerCase();
            row.hidden = next === "high"
              ? !/high|urgent|critical/.test(text)
              : next === "overdue"
                ? !/overdue|past due/.test(text)
                : false;
          });
          showToast("Queue filtered", next === "all" ? "Showing all signals." : `Showing ${next} items.`);
          return;
        }
        const surface = document.querySelector("[data-layout='table-surface']") || document.querySelector(".workspace-surface");
        const toolbar = document.querySelector("[data-layout='filter-toolbar']")
          || (typeof findFilterToolbar === "function" ? findFilterToolbar(surface) : null);
        const firstControl = toolbar?.querySelector("select, input[type='text'], input:not([type])");
        if (firstControl) {
          firstControl.focus();
          showToast("Filters", "Use the fields above the list to narrow results.");
          return;
        }
        const dateChip = button.parentElement?.querySelector(".rounded-lg, span");
        const periods = ["Last 7 days", "Last 30 days", "Last 90 days"];
        const chipText = (dateChip?.textContent || "").replace(/\s+/g, " ").trim();
        const currentMatch = chipText.match(/Last \d+ days/i);
        const current = currentMatch ? currentMatch[0] : "";
        const currentIndex = periods.findIndex((period) => period.toLowerCase() === current.toLowerCase());
        const nextPeriod = periods[(currentIndex + 1) % periods.length];
        if (dateChip && current) {
          const labelNode = Array.from(dateChip.querySelectorAll("span")).find((span) => /last \d+ days/i.test(span.textContent || ""));
          if (labelNode) labelNode.textContent = nextPeriod;
          else dateChip.innerHTML = dateChip.innerHTML.replace(/Last \d+ days/i, nextPeriod);
          showToast("Range updated", nextPeriod);
          return;
        }
        showToast("No extra filters", "This view is already using its default range.");
        return;
      }
      if (isSaveView) {
        const key = `recruitops:saved-view:${routeId || "page"}`;
        try {
          localStorage.setItem(key, JSON.stringify({ url: window.location.href, savedAt: new Date().toISOString() }));
          showToast("View saved", "This layout is remembered in this browser.");
        } catch (error) {
          showToast("Could not save view", "Browser storage is unavailable.");
        }
      }
    });
  });

  scope.querySelectorAll("label").forEach((label) => {
    if (!/compare locations/i.test(label.textContent || "")) return;
    const checkbox = label.querySelector("input[type='checkbox']");
    if (!checkbox || checkbox.dataset.chromeBound === "true") return;
    checkbox.dataset.chromeBound = "true";
    checkbox.addEventListener("change", () => {
      document.querySelector(".workspace-surface")?.classList.toggle("is-comparing-locations", checkbox.checked);
      showToast(checkbox.checked ? "Comparing locations" : "Single view", checkbox.checked
        ? "Location series are shown together."
        : "Location comparison is off.");
    });
  });

  const viewToggle = Array.from(scope.querySelectorAll("button")).filter((button) => /^(calendar|list)$/.test(getActionLabel(button).replace(/calendar_view_week|view_list/g, "").trim()));
  if (viewToggle.length >= 2) {
    viewToggle.forEach((button) => {
      if (button.dataset.viewToggleBound === "true") return;
      button.dataset.viewToggleBound = "true";
      button.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        const mode = /calendar/.test(getActionLabel(button)) ? "calendar" : "list";
        viewToggle.forEach((item) => {
          const active = item === button;
          item.classList.toggle("bg-primary-container", active);
          item.classList.toggle("text-on-primary", active);
          item.classList.toggle("text-on-surface-variant", !active);
        });
        const surface = document.querySelector(".workspace-surface");
        surface?.setAttribute("data-view-mode", mode);
        showToast(mode === "calendar" ? "Calendar view" : "List view", "The schedule layout updated.");
      });
    });
  }

  scope.querySelectorAll("button").forEach((button) => {
    const icon = button.querySelector(".material-symbols-outlined")?.textContent?.trim().toLowerCase() || "";
    if (icon !== "more_vert" || button.dataset.rowMenuBound === "true" || button.closest("table")) return;
    if (button.dataset.standaloneMenuBound === "true") return;
    if (button.closest(".ro-row-menu-host")?.querySelector(":scope > .ro-row-menu, .ro-row-menu")) return;
    button.dataset.standaloneMenuBound = "true";
    button.setAttribute("type", "button");
    button.setAttribute("aria-haspopup", "menu");
    const host = button.parentElement;
    if (!host) return;
    host.classList.add("relative", "ro-row-menu-host");
    const menu = document.createElement("div");
    menu.className = "ro-row-menu";
    menu.hidden = true;
    menu.setAttribute("role", "menu");
    const fallback = routeId === "meetings" ? "meeting-form-dialog.html" : routeId === "follow-ups" ? "follow-up-form-dialog.html" : "";
    menu.innerHTML = `<button type="button" role="menuitem" data-route="${fallback}">Open</button>`;
    host.appendChild(menu);
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const willOpen = menu.hidden;
      closeRowActionMenus(host);
      menu.hidden = !willOpen;
      host.classList.toggle("ro-row-menu-open", willOpen);
    });
  });
  if (typeof wireHoverKebabMenus === "function") wireHoverKebabMenus(scope);
}

function setupHoverMenus(scope = document) {
  scope.querySelectorAll(".group").forEach((group) => {
    const menu = group.querySelector(".group-hover\\:block");
    const trigger = group.querySelector("button");
    if (!menu || !trigger || group.dataset.menuInitialized === "true") return;
    group.dataset.menuInitialized = "true";
    trigger.setAttribute("aria-haspopup", "menu");
    trigger.setAttribute("aria-expanded", "false");
    if (!trigger.getAttribute("type")) {
      trigger.setAttribute("type", "button");
    }
    menu.setAttribute("role", "menu");
    const menuItems = Array.from(menu.querySelectorAll("a, button"));
    menuItems.forEach((item) => {
      item.setAttribute("role", "menuitem");
      if (item.tabIndex < 0) {
        item.tabIndex = -1;
      }
    });

    const openMenu = ({ focusFirst = false, focusLast = false } = {}) => {
      document.querySelectorAll(".menu-open").forEach((openGroup) => {
        openGroup.classList.remove("menu-open");
        const openTrigger = openGroup.querySelector("button[aria-haspopup='menu']");
        if (openTrigger) openTrigger.setAttribute("aria-expanded", "false");
      });
      group.classList.add("menu-open");
      trigger.setAttribute("aria-expanded", "true");
      if (focusFirst && menuItems[0]) {
        window.requestAnimationFrame(() => menuItems[0].focus());
      }
      if (focusLast && menuItems.length > 0) {
        window.requestAnimationFrame(() => menuItems[menuItems.length - 1].focus());
      }
    };

    const closeMenu = ({ restoreFocus = false } = {}) => {
      group.classList.remove("menu-open");
      trigger.setAttribute("aria-expanded", "false");
      if (restoreFocus) {
        window.requestAnimationFrame(() => trigger.focus());
      }
    };

    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      const nextOpen = !group.classList.contains("menu-open");
      if (nextOpen) {
        openMenu();
        return;
      }
      closeMenu();
    });

    trigger.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        openMenu({ focusFirst: true });
        return;
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        openMenu({ focusLast: true });
        return;
      }
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        if (group.classList.contains("menu-open")) {
          closeMenu();
          return;
        }
        openMenu({ focusFirst: true });
      }
    });

    menu.addEventListener("keydown", (event) => {
      const activeIndex = menuItems.findIndex((item) => item === document.activeElement);
      if (event.key === "Escape") {
        event.preventDefault();
        closeMenu({ restoreFocus: true });
        return;
      }
      if (event.key === "ArrowDown") {
        event.preventDefault();
        const nextIndex = activeIndex >= 0 ? (activeIndex + 1) % menuItems.length : 0;
        menuItems[nextIndex]?.focus();
        return;
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        const nextIndex = activeIndex >= 0 ? (activeIndex - 1 + menuItems.length) % menuItems.length : menuItems.length - 1;
        menuItems[nextIndex]?.focus();
        return;
      }
      if (event.key === "Home") {
        event.preventDefault();
        menuItems[0]?.focus();
        return;
      }
      if (event.key === "End") {
        event.preventDefault();
        menuItems[menuItems.length - 1]?.focus();
      }
    });

    menuItems.forEach((item) => {
      item.addEventListener("click", () => closeMenu());
    });
  });
}

function closeOpenMenus() {
  document.querySelectorAll(".menu-open").forEach((group) => {
    group.classList.remove("menu-open");
    const trigger = group.querySelector("button[aria-haspopup='menu']");
    if (trigger) {
      trigger.setAttribute("aria-expanded", "false");
    }
  });
}

function markNotificationRead(button) {
  if (button.disabled) return;
  if (window.RecruitOpsLive?.markNotificationRead) {
    window.RecruitOpsLive.markNotificationRead(button);
    return;
  }
  const item = button.closest(".group, .relative, .flex");
  if (!item) return;
  item.classList.add("notification-read");
  button.setAttribute("disabled", "disabled");
  showToast("Got it", "This event is in Seen. Open What happened if you want the details again.");
}

document.addEventListener("click", (event) => {
  if (!(event.target instanceof Element)) return;
  const button = event.target.closest("[data-notification-read]");
  if (!button || button.disabled) return;
  event.preventDefault();
  markNotificationRead(button);
}, true);

function setupResumeUploadWorkspace() {
  if (document.body?.dataset.routeId !== "resume-upload-and-review") return;
  const queueItems = Array.from(document.querySelectorAll(".h-table-row")).filter((row) => row.textContent.includes(".pdf") || row.textContent.includes(".docx"));
  const headerTitle = Array.from(document.querySelectorAll("h2")).find((node) => node.textContent.includes("Chen_Wei_Senior_Dev"));
  const confidenceText = Array.from(document.querySelectorAll("p")).find((node) => node.textContent.includes("94% match rate"));

  queueItems.forEach((item) => {
    item.addEventListener("click", () => {
      queueItems.forEach((row) => row.classList.remove("is-active-record"));
      item.classList.add("is-active-record");
      const fileLabel = item.querySelector(".font-data-tabular")?.textContent?.trim() || "Selected resume";
      const statusLabel = item.querySelector(".font-label-caps")?.textContent?.trim() || "READY FOR REVIEW";
      if (headerTitle) {
        headerTitle.textContent = fileLabel.replace(/\.[^.]+$/, "").slice(0, 22) || fileLabel;
      }
      if (confidenceText) {
        confidenceText.textContent = `Current queue selection: ${statusLabel.toLowerCase()}. Review extracted details before moving forward.`;
      }
    });
  });

  if (queueItems[0]) {
    queueItems[0].classList.add("is-active-record");
  }
}

function setupDailyUpdatesWorkspace() {
  if (document.body?.dataset.routeId !== "daily-updates-workspace") return;
  const priorityToggle = document.getElementById("priority-toggle");
  if (priorityToggle) {
    priorityToggle.addEventListener("change", () => {
      showToast(
        priorityToggle.checked ? "Priority flag enabled" : "Priority flag cleared",
        priorityToggle.checked
          ? "This update will stand out in the review queue."
          : "This update will return to the standard review path.",
      );
    });
  }
}

function setupMyWorkWorkspace() {
  if (document.body?.dataset.routeId !== "my-work-dashboard") return;
  const items = Array.from(document.querySelectorAll("li"))
    .filter((item) => item.querySelector('input[type="checkbox"]'));
  if (items.length === 0) return;

  items.forEach((item) => {
    const checkbox = item.querySelector('input[type="checkbox"]');
    const labelNode = item.querySelector(".font-data-tabular");
    if (!checkbox) return;
    item.classList.add("task-checklist-item");

    const sync = ({ notify = false } = {}) => {
      item.classList.toggle("is-task-complete", checkbox.checked);
      item.setAttribute("aria-checked", checkbox.checked ? "true" : "false");
      if (notify) {
        const label = (labelNode?.textContent || "Follow-up").replace(/\s+/g, " ").trim();
        showToast(
          checkbox.checked ? "Follow-up completed" : "Follow-up reopened",
          checkbox.checked
            ? `${label} is done.`
            : `${label} is back on your list.`,
        );
      }
    };

    item.addEventListener("click", (event) => {
      if (event.target.closest("a, button, label")) return;
      if (event.target === checkbox) return;
      checkbox.checked = !checkbox.checked;
      checkbox.dispatchEvent(new Event("change", { bubbles: true }));
    });

    checkbox.addEventListener("change", () => sync({ notify: true }));
    sync();
  });
}

function setupRecoveryUtilities() {
  const routeId = document.body?.dataset.routeId || "";

  if (routeId === "access-denied") {
    const copyButton = Array.from(document.querySelectorAll("button")).find((button) =>
      /copy request id/i.test(button.getAttribute("aria-label") || ""),
    );
    const requestId = Array.from(document.querySelectorAll("span"))
      .find((node) => /REQ-\d{8}/.test(node.textContent || ""))
      ?.textContent?.trim();

    if (copyButton && requestId) {
      copyButton.addEventListener("click", async () => {
        try {
          await navigator.clipboard?.writeText(requestId);
        } catch {
          // File-based previews can block clipboard access; the toast still preserves the workflow.
        }
        showToast("Request ID copied", `${requestId} is ready to share with support or an administrator.`);
      });
    }
  }

  if (routeId === "support-workspace") {
    const blockerButtons = Array.from(document.querySelectorAll("button"));
    blockerButtons.forEach((button) => {
      const label = getActionLabel(button);
      if (/access issues/.test(label)) {
        button.dataset.toastTitle = "Access recovery";
        button.dataset.toast = "Check your assigned role, location scope, and any recent permission changes before escalating.";
      }
      if (/data discrepancy/.test(label)) {
        button.dataset.toastTitle = "Data recovery";
        button.dataset.toast = "Capture the affected record IDs and last known good state so support can triage faster.";
      }
    });

    document.querySelectorAll("a[href='javascript:void(0)']").forEach((link) => {
      const label = getActionLabel(link);
      if (/internal documentation/.test(label)) {
      }
      if (/system health status/.test(label)) {
      }
    });
  }

  if (routeId === "not-found") {
    document.querySelectorAll("a[href='javascript:void(0)']").forEach((link) => {
      const label = getActionLabel(link);
      if (/documentation registry/.test(label)) {
      }
      if (/platform status dashboard/.test(label)) {
      }
    });
  }
}

function setupApprovalsWorkspace() {
  if (document.body?.dataset.routeId !== "approvals-inbox") return;
  const rows = Array.from(document.querySelectorAll("tbody tr")).filter(
    (row) => !row.classList.contains("table-empty-state-row") && !row.querySelector(".ro-empty"),
  );
  if (!rows.length) return;
  rows.forEach((row) => {
    row.addEventListener("click", (event) => {
      if (event.target.closest("button, a, select, input")) return;
      rows.forEach((item) => item.classList.remove("is-active-record"));
      row.classList.add("is-active-record");
    });
  });
}


function setupDuplicateResolutionWorkspace() {
  if (document.body?.dataset.routeId !== "candidate-duplicate-review") return;
  if (document.querySelector("[data-duplicate-summary]")) return;
  const host = document.querySelector("[data-demo-validate]");
  const radios = Array.from(document.querySelectorAll('input[name="resolution"]'));
  const confirmButton = Array.from(document.querySelectorAll("button")).find((button) =>
    /confirm resolution/i.test(button.textContent || ""),
  );
  if (!host || radios.length === 0 || !confirmButton) return;

  confirmButton.dataset.duplicateResolutionConfirm = "true";
  confirmButton.disabled = true;
  confirmButton.classList.add("opacity-60", "cursor-not-allowed");

  const summary = document.createElement("section");
  summary.className = "decision-summary";
  summary.setAttribute("data-duplicate-summary", "true");
  summary.innerHTML = `
    <div class="decision-summary-header">
      <div>
        <div class="decision-summary-title">Resolution status</div>
        <p class="decision-summary-copy" data-duplicate-summary-copy>No resolution selected yet. Choose how this incoming record should be handled.</p>
      </div>
    </div>
    <div class="decision-summary-meta" data-duplicate-summary-meta>
      <span class="decision-summary-pill"><span class="material-symbols-outlined text-[14px]">rule</span>Confidence 94%</span>
      <span class="decision-summary-pill"><span class="material-symbols-outlined text-[14px]">warning</span>Action required</span>
    </div>
  `;
  placeAfterLeadHeading(host, summary);

  const copyNode = summary.querySelector("[data-duplicate-summary-copy]");
  const metaNode = summary.querySelector("[data-duplicate-summary-meta]");

  const syncSelection = () => {
    const selected = radios.find((radio) => radio.checked);
    if (!selected) {
      confirmButton.disabled = true;
      confirmButton.classList.add("opacity-60", "cursor-not-allowed");
      if (copyNode) {
        copyNode.textContent = "No resolution selected yet. Choose how this incoming record should be handled.";
      }
      return;
    }

    confirmButton.disabled = false;
    confirmButton.classList.remove("opacity-60", "cursor-not-allowed");
    const label = selected.closest("label")?.textContent?.replace(/\s+/g, " ").trim() || "Resolution selected";
    confirmButton.dataset.duplicateResolutionLabel = label;
    if (copyNode) {
      copyNode.textContent = `${label} is selected. Confirm when you're comfortable with the duplicate reasoning and downstream impact.`;
    }
    if (metaNode) {
      metaNode.innerHTML = `
        <span class="decision-summary-pill"><span class="material-symbols-outlined text-[14px]">rule</span>Confidence 94%</span>
        <span class="decision-summary-pill"><span class="material-symbols-outlined text-[14px]">check_circle</span>${label}</span>
      `;
    }
  };

  radios.forEach((radio) => {
    radio.addEventListener("change", syncSelection);
  });
  syncSelection();
}

function ensureDecisionSummary(host, key, title, copy) {
  if (!host) return null;
  const existing = host.querySelector(`[data-shared-summary="${key}"]`);
  if (existing) return existing;
  const summary = document.createElement("section");
  summary.className = "decision-summary";
  summary.setAttribute("data-shared-summary", key);
  summary.innerHTML = `
    <div class="decision-summary-header">
      <div>
        <div class="decision-summary-title">${title}</div>
        <p class="decision-summary-copy">${copy}</p>
      </div>
    </div>
    <div class="decision-summary-meta"></div>
  `;
  /* Kept detached: the summary object still drives confirm-button state,
     but the coaching panel itself is no longer rendered inside overlays. */
  return summary;
}

function updateDecisionSummaryMeta(summary, pills) {
  const meta = summary?.querySelector(".decision-summary-meta");
  if (!meta) return;
  meta.innerHTML = pills
    .map(
      (pill) => `
        <span class="decision-summary-pill">
          <span class="material-symbols-outlined text-[14px]">${pill.icon || "check_circle"}</span>
          ${pill.text}
        </span>
      `,
    )
    .join("");
}

function setActionEnabled(button, enabled) {
  if (!button) return;
  button.disabled = !enabled;
  button.classList.toggle("opacity-60", !enabled);
  button.classList.toggle("cursor-not-allowed", !enabled);
}

function setupExceptionRequestOverlay() {
  if (document.body?.dataset.routeId !== "exception-request-dialog") return;
  const surface = document.querySelector("[data-overlay-surface='true']");
  const typeSelect = surface?.querySelector("select");
  const textarea = surface?.querySelector("textarea");
  const approverInput = surface?.querySelector('input[readonly][value*="VP"]');
  const submitButton = Array.from(surface?.querySelectorAll("button") || []).find((button) => /submit request/i.test(getActionLabel(button)));
  const changeButton = Array.from(surface?.querySelectorAll("button") || []).find((button) => /change/i.test(getActionLabel(button)));
  const counterNode = Array.from(surface?.querySelectorAll("span") || []).find((node) => /0\s*\/\s*500/.test(node.textContent || ""));
  const summary = ensureDecisionSummary(
    surface?.querySelector(".p-gutter.overflow-y-auto") || surface,
    "exception-request",
    "Exception readiness",
    "Complete the exception type and business justification before submitting this escalation.",
  );
  if (!surface || !typeSelect || !textarea || !submitButton || !summary) return;

  const sync = () => {
    const typeLabel = typeSelect.options[typeSelect.selectedIndex]?.text?.trim() || "Choose exception type";
    const justificationLength = (textarea.value || "").trim().length;
    const canSubmit = isFieldComplete(typeSelect) && justificationLength >= 24;
    setActionEnabled(submitButton, canSubmit);
    updateDecisionSummaryMeta(summary, [
      { icon: "policy", text: typeLabel },
      { icon: "description", text: justificationLength > 0 ? `${justificationLength} characters captured` : "Business justification needed" },
      { icon: "route", text: approverInput?.value?.trim() || "Approver path ready" },
    ]);
    if (counterNode) {
      counterNode.textContent = `${Math.min(justificationLength, 500)} / 500`;
    }
  };

  if (changeButton) {
    changeButton.type = "button";
  }

  textarea.addEventListener("input", sync);
  typeSelect.addEventListener("change", sync);
  sync();
}

/* The Offer stage exists only on branches with offer tracking enabled
   (branches.offers_enabled) — sourcing-only tenants get a streamlined
   flow that ends at client hand-off. */
const DEFAULT_PIPELINE_FLOW = (typeof branchOffersEnabled === "function" && !branchOffersEnabled())
  ? ["Sourced", "Screening", "Technical Interview", "Executive Review"]
  : ["Sourced", "Screening", "Technical Interview", "Executive Review", "Offer"];

function setupOverlayWorkflows() {
  setupExceptionRequestOverlay();
  setupStageMoveOverlay();
  setupReassignOwnerOverlay();
  setupApprovalReviewOverlay();
  setupPipelineHistoryOverlay();
}

function resolveWorkspaceSurface(host) {
  return host?.querySelector(".workspace-surface") || host || null;
}

function getElementChildren(node) {
  return Array.from(node?.children || []).filter((child) => child.nodeType === 1);
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function findLeadHeadingBlock(surface) {
  return getElementChildren(surface).find((child) => child.querySelector?.("h1, h2")) || null;
}

function placeAfterLeadHeading(host, node, { fallback = "surface" } = {}) {
  if (!host || !node) return false;
  const surface = resolveWorkspaceSurface(host);
  const headingBlock = findLeadHeadingBlock(surface);
  if (headingBlock) {
    headingBlock.insertAdjacentElement("afterend", node);
    return true;
  }
  if (surface && fallback === "surface") {
    surface.prepend(node);
    return true;
  }
  host.prepend(node);
  return true;
}

function ensureWorkspacePageHeading(host, options = {}) {
  const surface = resolveWorkspaceSurface(host);
  if (!surface || surface.querySelector("[data-generated-page-heading='true']")) return null;
  const hasVisibleHeading = Array.from(surface.querySelectorAll("h1, h2")).some((heading) => {
    const rect = heading.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  });
  if (hasVisibleHeading && !options.force) return null;

  const title = options.title || document.body?.dataset.routeTitle || document.querySelector("[data-shell-page-title]")?.textContent?.trim();
  if (!title) return null;
  const subtitle = options.subtitle || "";
  const header = document.createElement("div");
  header.dataset.layout = "workspace-header";
  header.dataset.generatedPageHeading = "true";
  header.innerHTML = `<div><h1 class="font-headline-lg text-headline-lg text-on-background">${escapeHtml(title)}</h1>${subtitle ? `<p class="font-body-md text-body-md text-text-muted mt-1">${escapeHtml(subtitle)}</p>` : ""}</div>`;
  surface.prepend(header);
  return header;
}

function resolveListPageLayout(host) {
  const surface = resolveWorkspaceSurface(host);
  if (!surface) return {};
  const topLevel = Array.from(surface.children).filter((el) => el.nodeType === 1);
  const root = topLevel.length === 1 && topLevel[0].matches("div") && topLevel[0].children.length >= 2
    ? topLevel[0]
    : surface;
  const sections = Array.from(root.children).filter((el) => el.nodeType === 1);
  const header = sections.find((el) => el.querySelector("h1, h2") && !el.querySelector("table")) || null;
  const following = header ? sections.slice(sections.indexOf(header) + 1) : sections.slice(1);
  const tableSurface = following.find((el) => el.querySelector("table")) || null;
  const filterToolbar = following.find((el) => el !== tableSurface && el.querySelector("input, select, button"))
    || tableSurface?.querySelector(":scope > div:first-of-type")
    || null;
  const headerActions = header
    ? Array.from(header.children).find((el) => el.querySelector("button, a") && !el.querySelector("h1, h2"))
      || header.querySelector(":scope > div:last-of-type, :scope > button:last-of-type")
    : null;
  const footer = tableSurface
    ? Array.from(tableSurface.children).find((el) => /showing [0-9]/i.test(el.textContent || ""))
      || tableSurface.querySelector(":scope > div:last-of-type")
    : null;
  return { surface, root, header, headerActions, filterToolbar, tableSurface, footer };
}

function markIf(node, layout) {
  if (!node) return;
  if (node.classList?.contains("workspace-surface")) return;
  if (layout === "workspace-header" && node.querySelector("table, #right-rail")) return;
  if (layout === "workspace-header-actions" && node.querySelector("table")) return;
  node.dataset.layout = layout;
}

function markIfUnset(node, layout) {
  if (!node || node.dataset?.layout) return;
  markIf(node, layout);
}

function markFilterToolbar(toolbar) {
  if (!toolbar || toolbar.dataset.layout) return;
  if (toolbar.closest("[data-overlay-surface='true'], .overlay-host")) return;
  if (toolbar.querySelector("table, form, textarea, h1, h2, h3, p.font-semibold")) return;
  const hasSearch = toolbar.querySelector("input[placeholder*='Search'], input[placeholder*='Filter'], input[type='search']");
  const selectCount = toolbar.querySelectorAll("select").length;
  const hasFilterControl = hasSearch || selectCount >= 2;
  if (!hasFilterControl) return;
  const controls = toolbar.querySelectorAll("input:not([type='hidden']), select, button, a[href]");
  if (controls.length < 2 && !hasSearch) return;
  markIf(toolbar, "filter-toolbar");
  const directGroups = Array.from(toolbar.children).filter((child) => child.querySelector?.("input:not([type='hidden']), select, button, a[href]"));
  if (directGroups.length > 1) {
    directGroups[0].dataset.layout = "filter-toolbar-primary";
    directGroups.slice(1).forEach((group) => {
      if (!group.dataset.layout) group.dataset.layout = "filter-toolbar-secondary";
    });
  }
}

function setupDenseWorkspaceLayouts() {
  const routeId = document.body?.dataset.routeId || "";
  const host = document.querySelector("[data-demo-validate]");
  const surface = resolveWorkspaceSurface(host);
  if (!surface) return;

  if (routeId === "candidate-duplicate-review") {
    const header = surface.querySelector(":scope > div:first-of-type");
    const grid = header?.nextElementSibling;
    const main = grid?.children?.[0];
    const side = grid?.children?.[1];
    markIf(header, "duplicate-review-header");
    markIf(grid, "duplicate-review-grid");
    markIf(main, "duplicate-review-main");
    markIf(side, "duplicate-review-side");
  }

  if (routeId === "resume-upload-and-review") {
    const grid = surface.querySelector(":scope > div.grid");
    const left = grid?.children?.[0];
    const right = grid?.children?.[1];
    markIf(grid, "resume-workspace-grid");
    markIf(left, "resume-workspace-left");
    markIf(right, "resume-workspace-right");
  }

  if (routeId === "pipeline-board") {
    const topSection = surface.querySelector(":scope > div:first-of-type");
    const headerRow = topSection?.querySelector(":scope > div.flex.items-center, :scope > div.flex.justify-between");
    const toolbarActions = headerRow?.querySelector(":scope > div.flex.gap-2") || topSection?.querySelector(":scope div.flex.gap-2");
    const filterBar = topSection?.querySelector(":scope > div.flex.gap-3");
    const boardScroll = topSection?.nextElementSibling;
    const title = topSection?.querySelector("h2");
    if (title && !topSection.querySelector(".pipeline-toolbar-subtitle")) {
      const subtitle = document.createElement("p");
      subtitle.className = "pipeline-toolbar-subtitle";
      subtitle.textContent = "Track candidates across active stages and keep movement actions close to the board.";
      (headerRow || title).insertAdjacentElement("afterend", subtitle);
    }
    markIf(topSection, "pipeline-toolbar");
    markIf(toolbarActions, "pipeline-toolbar-actions");
    markIf(filterBar, "pipeline-filter-bar");
    markIf(boardScroll, "pipeline-board-scroll");
  }

  if (routeId === "candidate-screening") {
    const header = surface.querySelector(":scope > div:first-of-type");
    const grid = header?.nextElementSibling;
    const main = grid?.children?.[0];
    const side = grid?.children?.[1];
    markIf(header, "screening-header");
    markIf(grid, "screening-grid");
    markIf(main, "screening-main");
    markIf(side, "screening-side");
  }
}

function setupWorkspaceVisualPolish() {
  const routeId = document.body?.dataset.routeId || "";
  const host = document.querySelector("[data-demo-validate]");
  if (!host) return;

  if (HEADINGLESS_WORKSPACE_ROUTES.has(routeId)) {
    ensureWorkspacePageHeading(host);
  }
  if (FORCED_WORKSPACE_HEADINGS[routeId]) {
    ensureWorkspacePageHeading(host, {
      force: true,
      ...FORCED_WORKSPACE_HEADINGS[routeId],
    });
  }

  const markMetricCards = (container) => {
    Array.from(container?.children || []).forEach((card) => {
      card.dataset.layout = "metric-card";
    });
  };

  if (routeId === "role-dashboard") {
    const surface = resolveWorkspaceSurface(host);
    const mainSection = surface?.querySelector(":scope > section");
    const dashboardHeader = mainSection?.querySelector(":scope > header");
    const metricStrip = dashboardHeader?.nextElementSibling;
    if (dashboardHeader) dashboardHeader.dataset.layout = "dashboard-header";
    if (metricStrip) {
      metricStrip.dataset.layout = "metric-strip";
      markMetricCards(metricStrip);
    }
    surface?.querySelectorAll("#right-rail a[href], #right-rail > div").forEach((node) => {
      const card = node.closest("div.bg-surface");
      if (card) card.dataset.layout = "dashboard-alert-card";
    });
  }

  if (routeId === "company-dashboard") {
    const surface = resolveWorkspaceSurface(host);
    const root = surface?.querySelector(":scope > div:first-of-type");
    const header = root?.querySelector(":scope > div:first-of-type");
    const headerActions = header?.querySelector(":scope > div:last-of-type");
    const filterBar = header?.nextElementSibling;
    const metricStrip = filterBar?.nextElementSibling;
    markIf(root, "report-dashboard-root");
    markIf(header, "report-command-header");
    markIf(headerActions, "report-command-actions");
    markIf(filterBar, "report-filter-bar");
    if (metricStrip) {
      metricStrip.dataset.layout = "report-metric-strip";
      markMetricCards(metricStrip);
    }
  }

  if (routeId === "daily-updates-submission") {
    const surface = resolveWorkspaceSurface(host);
    const root = surface?.querySelector(":scope > div:first-of-type");
    const rootChildren = getElementChildren(root);
    const banner = rootChildren.find((child) => /draft .* restored/i.test(child.textContent || ""));
    const header = rootChildren.find((child) => child.querySelector?.("h1, h2"));
    if (root) root.dataset.layout = "daily-submission-root";
    if (banner) banner.dataset.layout = "daily-submission-banner";
    if (header) {
      header.dataset.layout = "daily-submission-header";
      if (banner && banner.previousElementSibling !== header) {
        header.insertAdjacentElement("afterend", banner);
      }
    }
  }

  if (routeId === "requisition-detail") {
    const surface = resolveWorkspaceSurface(host);
    const breadcrumb = surface?.querySelector(":scope > nav");
    const header = breadcrumb?.nextElementSibling;
    const headerActions = header?.querySelector(":scope > div:last-of-type");
    const metrics = header?.nextElementSibling;
    const detailGrid = metrics?.nextElementSibling;
    const detailSide = detailGrid?.children?.[0];
    const detailMain = detailGrid?.children?.[1];
    markIf(header, "operational-header");
    markIf(headerActions, "operational-header-actions");
    if (metrics) {
      metrics.dataset.layout = "operational-metric-strip";
      markMetricCards(metrics);
    }
    markIf(detailGrid, "operational-detail-grid");
    markIf(detailSide, "operational-detail-side");
    markIf(detailMain, "operational-detail-main");
    detailMain?.querySelectorAll(":scope > div").forEach((section) => {
      section.dataset.layout = "timeline-surface";
    });
  }

  if (routeId === "requisition-intake") {
    const surface = resolveWorkspaceSurface(host);
    const toolbar = surface?.querySelector(":scope > div:first-of-type");
    const toolbarActions = toolbar?.querySelector(":scope > div:last-of-type");
    const content = toolbar?.nextElementSibling;
    const formStack = content?.querySelector(":scope > div");
    markIf(toolbar, "intake-toolbar");
    markIf(toolbarActions, "intake-toolbar-actions");
    markIf(formStack, "intake-form-stack");
  }

  if (routeId === "client-detail") {
    const surface = resolveWorkspaceSurface(host);
    const detailRoot = surface?.querySelector("[data-client-detail='true']") || surface;
    const header = detailRoot?.querySelector(":scope > section:first-of-type");
    const metricStrip = header?.querySelector(":scope > div:last-of-type");
    const detailGrid = header?.nextElementSibling;
    const detailSide = detailGrid?.children?.[0];
    const detailMain = detailGrid?.children?.[1];
    markIf(header, "client-detail-header");
    if (metricStrip) {
      metricStrip.dataset.layout = "operational-metric-strip";
      markMetricCards(metricStrip);
    }
    markIf(detailGrid, "client-detail-grid");
    markIf(detailSide, "client-detail-side");
    markIf(detailMain, "client-detail-main");
    detailMain?.querySelectorAll(":scope > div").forEach((section) => {
      section.dataset.layout = "timeline-surface";
    });
  }

  if (routeId === "my-work-dashboard") {
    const surface = resolveWorkspaceSurface(host);
    const header = surface?.querySelector(":scope > div:first-of-type");
    const mainGrid = header?.nextElementSibling;
    const main = mainGrid?.children?.[0];
    const side = mainGrid?.children?.[1];
    const alertStrip = main?.querySelector(":scope > div:first-of-type");
    const tableSurface = alertStrip?.nextElementSibling;
    const sideCards = side?.querySelectorAll(":scope > div");
    const workload = mainGrid?.nextElementSibling;
    const workloadStrip = workload?.querySelector(":scope > div:last-of-type");
    markIf(header, "operational-header");
    markIf(mainGrid, "my-work-grid");
    markIf(main, "my-work-main");
    markIf(side, "my-work-side");
    markIf(alertStrip, "alert-strip");
    markIf(tableSurface, "table-surface");
    sideCards?.forEach((card) => {
      card.dataset.layout = "timeline-surface";
    });
    markIf(workload, "timeline-surface");
    if (workloadStrip) {
      workloadStrip.dataset.layout = "workload-strip";
      markMetricCards(workloadStrip);
    }
  }

  if (routeId === "delivery-work-queue") {
    const surface = resolveWorkspaceSurface(host);
    const header = surface?.querySelector(":scope > div:first-of-type");
    const metrics = header?.nextElementSibling;
    const toggleBar = metrics?.nextElementSibling;
    const queueSurface = toggleBar?.nextElementSibling;
    markIf(header, "operational-header");
    if (metrics) {
      metrics.dataset.layout = "queue-metric-strip";
      markMetricCards(metrics);
    }
    if (toggleBar) {
      toggleBar.dataset.layout = "queue-toggle-bar";
      toggleBar.dataset.toggleGroup = "true";
    }
    markIf(queueSurface, "queue-surface");
  }

  if (routeId === "notifications-center") {
    const surface = resolveWorkspaceSurface(host);
    const header = surface?.querySelector(":scope > div:first-of-type");
    const triageBar = header?.nextElementSibling;
    const triageTabs = triageBar?.querySelector(":scope > div:first-of-type");
    if (triageTabs) triageTabs.dataset.toggleGroup = "true";
  }

  if (routeId === "requisition-list") {
    const surface = resolveWorkspaceSurface(host);
    const hostCard = surface?.querySelector(":scope > div:last-of-type");
    const filterBar = hostCard?.querySelector(":scope > div:first-of-type");
    const quickTabs = filterBar?.querySelector(":scope > div:first-of-type");
    if (quickTabs) quickTabs.dataset.toggleGroup = "true";
  }

  if (routeId === "client-directory") {
    const surface = resolveWorkspaceSurface(host);
    const hostCard = surface?.querySelector(":scope > div:last-of-type");
    const toolbar = hostCard?.querySelector(":scope > div:first-of-type");
    const tabs = toolbar?.querySelector(":scope > div:first-of-type");
    if (tabs) tabs.dataset.toggleGroup = "true";
  }

  if (routeId === "location-management") {
    const surface = resolveWorkspaceSurface(host);
    const filterShell = Array.from(surface?.querySelectorAll("div") || []).find((el) =>
      /All Locations/.test(el.textContent || "") && el.querySelector("input[placeholder*='Search locations']")
    );
    markFilterToolbar(filterShell);
    filterShell?.querySelector(":scope > div:first-child > div:first-child")?.setAttribute("data-toggle-group", "true");
    const searchWrap = filterShell?.querySelector("input[placeholder*='Search locations']")?.closest("div");
    const actionGroup = searchWrap?.nextElementSibling;
    if (actionGroup) {
      actionGroup.dataset.layout = "location-filter-actions";
      actionGroup.classList.remove("sm:w-auto");
      actionGroup.style.width = "100%";
      actionGroup.style.maxWidth = "100%";
      actionGroup.style.marginInlineStart = "0";
      actionGroup.style.transform = "none";
      actionGroup.querySelectorAll("button").forEach((button) => {
        button.classList.remove("whitespace-nowrap");
      });
    }
  }

  const surface = resolveWorkspaceSurface(host);
  surface?.querySelectorAll('[role="tablist"], .flex:has(> [role="tab"])').forEach((el) => {
    el.dataset.toggleGroup = "true";
  });

  const topSections = Array.from(surface?.children || []).filter((el) => el.nodeType === 1);
  const titlebar = topSections.find((el) => {
    if (el.dataset.layout || el.querySelector("table, form, #right-rail")) return false;
    const heading = el.querySelector(":scope h1, :scope h2");
    if (!heading) return false;
    const rect = el.getBoundingClientRect();
    return rect.height > 0 && rect.height < 220;
  });
  if (titlebar) {
    markIfUnset(titlebar, "page-titlebar");
    const actionGroup = Array.from(titlebar.children).find((el) => {
      if (el.querySelector("h1, h2, table, form")) return false;
      return el.querySelector("button, a, select");
    });
    markIfUnset(actionGroup, "page-titlebar-actions");
  }

  surface?.querySelectorAll("div").forEach((candidate) => {
    if (candidate === titlebar || candidate.closest("[data-overlay-surface='true'], .overlay-host, table, form, [data-layout='page-titlebar'], [data-layout='pipeline-toolbar'], [data-layout='pipeline-filter-bar'], [data-layout='pipeline-toolbar-actions']")) return;
    if (candidate.dataset.layout) return;
    if (candidate.parentElement?.closest("[data-layout='filter-toolbar']")) return;
    if (candidate.querySelector("h1, h2, h3")) return;
    const rect = candidate.getBoundingClientRect();
    if (rect.height <= 0 || rect.height > 180) return;
    const hasFilterControl = candidate.querySelector("input[placeholder*='Search'], input[placeholder*='Filter'], input[type='search'], select");
    if (!hasFilterControl) return;
    markFilterToolbar(candidate);
  });

  const sidebarCta = document.querySelector(".sidebar-cta-link");
  const normalizeCta = (text) => (text || "").replace(/\s+/g, " ").trim().toLowerCase().replace(/^[a-z0-9_]+ /, "");
  const sideLabel = normalizeCta(sidebarCta?.textContent);
  if (sideLabel) {
    const surface = resolveWorkspaceSurface(host);
    surface?.querySelectorAll("a").forEach((el) => {
      if (el.closest("#right-rail, table, tbody, .pipeline-card, nav, aside")) return;
      if (el.matches("[data-validate-scope], [form]")) return;
      if (el.parentElement?.querySelector(".group-hover\\:block, [role='menu']")) return;
      const label = normalizeCta(el.textContent);
      if (!label) return;
      const same = label === sideLabel || label.includes(sideLabel) || sideLabel.includes(label);
      if (!same) return;
      const nearTitle = el.closest("header, [data-layout='workspace-header'], [data-layout='workspace-header-actions'], [data-layout='pipeline-toolbar-actions']")
        || el.parentElement?.querySelector("h1, h2, .font-headline-lg, .text-headline-lg");
      if (nearTitle || /bg-primary/.test(el.className || "")) {
        el.classList.add("ro-duplicate-cta");
      }
    });
  }
}

function setupMarketingInteractions() {
  if (document.body?.dataset.routeKind !== "marketing") return;
  const routeId = document.body?.dataset.routeId || "";
  const routePrefix = window.location.pathname.endsWith("/index.html") || window.location.pathname.endsWith("/frontend/")
    ? "pages/"
    : "";
  const onboardingWelcomeHref = `${routePrefix}onboarding-welcome.html`;
  const routeMap = [
    { pattern: /step\s*1|define|strategy|plan/i, href: "product-tour-plan-strategy.html" },
    { pattern: /step\s*2|ownership|accountability|assign/i, href: "product-tour-assign-ownership.html" },
    { pattern: /step\s*3|candidate movement|move candidates|pipeline/i, href: "product-tour-move-candidates.html" },
    { pattern: /step\s*4|exception|governance|resolve/i, href: "product-tour-resolve-exceptions.html" },
    { pattern: /step\s*5|report|progress|data/i, href: "product-tour-report-progress.html" },
  ];

  document.querySelectorAll(".landing-canvas :is(section, header, main, footer, article), .landing-canvas > :is(div, nav)").forEach((node, index) => {
    node.style.setProperty("--reveal-index", String(index));
  });

  document.querySelectorAll("a").forEach((link) => {
    const label = getActionLabel(link);
    const href = link.getAttribute("href") || "";
    if (/product tour|^product$|tour/i.test(label) && href === "javascript:void(0)") {
      link.setAttribute("href", "product-tour.html");
    }
    if (/start free trial|get started|sign up/i.test(label)) {
      link.setAttribute("href", onboardingWelcomeHref);
    }
    const step = routeMap.find((entry) => entry.pattern.test(label));
    if (step) {
      link.setAttribute("href", step.href);
      link.dataset.tourStepLink = "true";
      if (step.href.replace(".html", "") === routeId) {
        link.classList.add("is-active");
        link.setAttribute("aria-current", "page");
      }
    }
  });

  document.querySelectorAll("button:not([data-route])").forEach((button) => {
    const label = getActionLabel(button);
    if (/start free trial|get started|sign up/i.test(label)) {
      button.dataset.route = onboardingWelcomeHref;
    }
  });

  document.querySelectorAll(".landing-canvas :is(article, section, div)").forEach((node) => {
    if (node.querySelector("a, button") || node.closest("a, button")) return;
    const text = (node.textContent || "").replace(/\s+/g, " ").trim();
    const step = routeMap.find((entry) => entry.pattern.test(text));
    const rect = node.getBoundingClientRect();
    if (!step || rect.width < 120 || rect.height < 60 || rect.height > 360) return;
    node.setAttribute("role", "link");
    node.setAttribute("tabindex", "0");
    node.dataset.route = step.href;
    node.dataset.tourStepLink = "true";
    node.style.cursor = "pointer";
  });

  Array.from(document.querySelectorAll(".landing-canvas :is(div, span, p)"))
    .filter((node) => /96%|100%|clarity score|workflow clarity/i.test(node.textContent || ""))
    .slice(0, 3)
    .forEach((node) => node.classList.add("marketing-score-pulse"));
}

function setupOnboardingInteractions() {
  const routeId = document.body?.dataset.routeId || "";
  if (!routeId.startsWith("onboarding-")) return;

  document.querySelectorAll("button[disabled][data-route]").forEach((button) => {
    button.dataset.pendingRoute = button.dataset.route;
    button.removeAttribute("data-route");
  });

  const enablePendingRoutes = () => {
    document.querySelectorAll("button[data-pending-route]").forEach((button) => {
      button.disabled = false;
      button.dataset.route = button.dataset.pendingRoute || "";
      delete button.dataset.pendingRoute;
      button.setAttribute("aria-disabled", "false");
    });
  };

  if (routeId === "onboarding-hiring-teams") {
    const addTeamButton = Array.from(document.querySelectorAll("button")).find((button) => /add team/i.test(getActionLabel(button)));
    addTeamButton?.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const heading = Array.from(document.querySelectorAll("h3")).find((node) => /configured teams/i.test(node.textContent || ""));
      if (heading) heading.textContent = "Configured Teams (1)";
      const emptyState = Array.from(document.querySelectorAll("p")).find((node) => /no teams mapped yet/i.test(node.textContent || ""))?.closest("div");
      if (emptyState) {
        emptyState.classList.remove("border-dashed");
        emptyState.innerHTML = `
          <div class="w-12 h-12 rounded-full bg-success-bg flex items-center justify-center mb-2">
            <span class="material-symbols-outlined text-success-text text-xl">groups</span>
          </div>
          <p class="font-body-md text-body-md text-on-surface-variant font-medium">Engineering team mapped</p>
          <p class="font-body-sm text-body-sm text-text-muted">Default recruiter and hiring manager are ready.</p>
        `;
      }
      document.querySelectorAll(".grayscale").forEach((node) => node.classList.remove("grayscale", "opacity-50"));
      Array.from(document.querySelectorAll("span")).filter((node) => /pending/i.test(node.textContent || "")).forEach((node) => {
        node.textContent = "UNLOCKED";
      });
      enablePendingRoutes();
      showToast("Team added", "The onboarding team map is complete enough to continue.");
    });
  }

  if (routeId === "onboarding-locations") {
    Array.from(document.querySelectorAll("button")).forEach((button) => {
      const label = getActionLabel(button);
      if (/add location/i.test(label)) {
        button.addEventListener("click", () => showToast("Location added", "It will be included in your workspace."));
      }
      if (/import locations/i.test(label)) {
        button.addEventListener("click", () => showToast("Import started", "Choose a file to import your locations."));
      }
      if (/edit/.test(label)) {
        button.dataset.toastTitle = "Location updated";
        button.dataset.toast = "Your changes have been recorded.";
      }
      if (/delete/.test(label)) {
        button.dataset.toastTitle = "Location removed";
        button.dataset.toast = "It is no longer part of your setup.";
      }
    });
  }

  if (routeId === "onboarding-pipeline-stage-builder") {
    Array.from(document.querySelectorAll("button")).forEach((button) => {
      const label = getActionLabel(button);
      if (/save pipeline/i.test(label)) {
        button.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          const inputs = Array.from(document.querySelectorAll("#stage-list input[type='text'], #stage-list input:not([type])"));
          const stages = inputs.map((input) => input.value.trim()).filter(Boolean);
          if (stages.length >= 2) {
            if (typeof savePipelineFlow === "function") savePipelineFlow(stages);
            const session = RecruitOpsLive.session || (typeof readSession === "function" ? readSession() : {});
            session.onboarding = session.onboarding || {};
            session.onboarding.stages = stages;
            if (typeof writeSession === "function") writeSession(session);
            RecruitOpsLive.session = session;
            showToast("Pipeline saved", stages.length + " stages saved to your pipeline.");
          } else {
            showToast("Need more stages", "Add at least two stages to define your pipeline.");
          }
        });
      }
    });
  }

  if (routeId === "onboarding-add-custom-stage-overlay") {
    Array.from(document.querySelectorAll("button")).forEach((button) => {
      const label = getActionLabel(button);
      if (/add to pipeline/i.test(label)) {
        button.dataset.route = "onboarding-pipeline-stage-builder.html";
      }
      if (/close/i.test(label)) {
        button.dataset.route = "onboarding-pipeline-stage-builder.html";
        button.setAttribute("aria-label", "Close custom stage");
        button.setAttribute("title", "Close custom stage");
      }
    });
  }

  if (routeId === "onboarding-integrations") {
    Array.from(document.querySelectorAll("button")).forEach((button) => {
      const label = getActionLabel(button);
      if (/connect|configure|reconnect|manage/i.test(label)) {
        button.addEventListener("click", (event) => {
          event.preventDefault();
          const card = button.closest("[class*='border']") || button.parentElement;
          const name = card?.querySelector("h3, h4, strong, .font-headline-sm")?.textContent?.trim() || "integration";
          button.disabled = true;
          button.innerHTML = '<span class="material-symbols-outlined text-sm">check</span> Connected';
          button.classList.remove("bg-primary", "hover:bg-primary-hover");
          button.classList.add("bg-success-bg", "text-success-text");
          const session = RecruitOpsLive.session || (typeof readSession === "function" ? readSession() : {});
          session.onboarding = session.onboarding || {};
          session.onboarding.integrations = session.onboarding.integrations || [];
          session.onboarding.integrations.push(name);
          if (typeof writeSession === "function") writeSession(session);
          RecruitOpsLive.session = session;
          showToast("Integration connected", name + " is now linked to your workspace.");
        });
      }
    });
  }
}

function runLoginDemo(form) {
  /* Real sign-in lives in api-client.js (loaded before this file on every
     page). The demo state machine that used to live here — cycling
     invalid → inactive → success with canned copy — was unreachable. */
  window.RecruitOpsLive.handleLogin(form);
}

/* ═══════════════════════════════════════════════════════════════
   ROUTE PREFETCHER
   ═══════════════════════════════════════════════════════════════ */

  
/**
 * Prefetches likely-next pages so navigation feels instant.
 * Scans sidebar nav links, groups them by section, then injects
 * <link rel="prefetch"> for sibling pages in the current section
 * and adjacent sections. Uses requestIdleCallback to avoid blocking.
 */
document.addEventListener("DOMContentLoaded", () => {
  annotateRequiredFields(document);
  bindFieldValidation(document);
  setupToggleGroups(document);
  setupWorkspaceInsights();
  setupContextualActionToasts(document);
  setupWorkflowActionPolish();
  setupHoverMenus(document);
  setupOverlayInteractionPolish(document);
  setupOverlayContextPolish();
  upgradeContextualRoutes(document);
  setupMarketingInteractions();
  setupOnboardingInteractions();
  setupResumeUploadWorkspace();
  setupDailyUpdatesWorkspace();
  setupMyWorkWorkspace();
  setupRecoveryUtilities();
  setupApprovalsWorkspace();
  setupDuplicateResolutionWorkspace();
  setupPipelineBoardInteractions();
  setupOverlayWorkflows();
  setupDenseWorkspaceLayouts();
  setupWorkspaceVisualPolish();
  setupToggleGroups(document);
  setupTableControlPolish();
  if (typeof refreshWorkspacePagers === "function") refreshWorkspacePagers();
  setupAdvancedFilterPanels(document);
  setupSortableTables(document);
  setupRecordLinkPolish();
  setupGenericActionAnnotations(document);
  setupWorkspaceChrome(document);
  setupSidebarNav();
  setupVisualPassChrome();
  setupRoutePrefetcher();
  injectDensityToggle();
  applyDensityPreference(readDensityPreference());
  setupCommandPalette();
  const mobileDialog = document.getElementById("mobile-nav");
  const mobileOpen = document.querySelector("[data-mobile-nav-open]");
  const mobileClose = document.querySelector("[data-mobile-nav-close]");
  const closeHref = resolveOverlayCloseHref();
  const overlaySurface = document.querySelector("[data-overlay-surface='true']");
  syncOverlayReturnLinks(closeHref);

  if (mobileOpen && mobileDialog) {
    mobileOpen.addEventListener("click", () => openMobileNav(mobileDialog));
  }

  if (mobileClose && mobileDialog) {
    mobileClose.addEventListener("click", () => closeMobileNav(mobileDialog));
  }

  if (mobileDialog) {
    mobileDialog.addEventListener("close", () => {
      document.body.classList.remove("scroll-locked");
    });
    mobileDialog.addEventListener("cancel", () => {
      document.body.classList.remove("scroll-locked");
    });
    mobileDialog.addEventListener("click", (event) => {
      const panel = mobileDialog.querySelector(".mobile-nav-panel");
      if (panel && !panel.contains(event.target)) {
        closeMobileNav(mobileDialog);
      }
    });
  }

  if (overlaySurface) {
    window.requestAnimationFrame(() => focusFirstInteractive(overlaySurface));
  }
  attachKeyboardShortcuts();
  attachShortcutHint();
  upgradeBrandMarks();

  document.querySelectorAll("[data-toggle-group]").forEach((group) => {
    group.addEventListener("click", (event) => {
      const button = event.target.closest("button");
      if (!button || !group.contains(button)) return;
      toggleActiveWithin(group, button);
      applyTableLens(group, button);
    });
  });

  document.querySelectorAll("form").forEach((form) => {
    form.setAttribute("novalidate", "novalidate");
    setupFormProgress(form);
    if (form.id === "login-form") {
      const submitButton = form.querySelector('#submit-btn[type="submit"], #submit-btn');
      if (submitButton) {
        submitButton.addEventListener("click", (event) => {
          event.preventDefault();
          runLoginDemo(form);
        });
      }
    }
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      if (form.id === "login-form") {
        runLoginDemo(form);
        return;
      }
      if (form.id === "profile-details-form" || form.id === "profile-password-form") {
        return;
      }
      if (validateForm(form)) {
        if (window.RecruitOpsLive && window.RecruitOpsLive.handleFormSubmit && window.RecruitOpsLive.handleFormSubmit(form)) {
          return;
        }
        showToast("Looks good", "All required fields are complete.");
      }
    });
  });

  /* The shared anchor router never takes over links another owner has
     claimed — excluded anchors keep their native behavior and skip every
     routing branch below:
       a[data-logout-link] → api-client.js's logout listener owns it; its
         POST /auth/logout must survive without a navigateToRoute abort
         (this also makes the router safe regardless of listener order).
       a[download], a[target] → the browser owns those. */
  const ANCHOR_ROUTER_EXCLUSIONS = [
    "a[data-logout-link]",
    "a[download]",
    "a[target]",
  ].join(", ");

  document.addEventListener("click", (event) => {
    const dismissTarget = event.target.closest("[data-overlay-close]");
    if (dismissTarget) {
      event.preventDefault();
      if (typeof closeInPageOverlay === "function" && closeInPageOverlay()) return;
      if (closeHref && document.body.dataset.overlayPage === "true") {
        window.location.href = closeHref;
      }
      return;
    }

    const button = event.target.closest("button, a");
    if (!button) {
      closeOpenMenus();
      if (typeof closeRowActionMenus === "function") closeRowActionMenus();
      /* Rows/cells promoted to routes (role="button" surfaces) lose their
         listeners when live loaders clone them — handle them here. */
      if (!event.target.closest("input, select, textarea, label")) {
        const routedSurface = event.target.closest("[data-route]");
        if (routedSurface?.dataset.route) {
          event.preventDefault();
          navigateToRoute(routedSurface.dataset.route);
        }
      }
      return;
    }
    if (!button.closest(".menu-open") && !button.closest(".ro-row-menu-host")) {
      closeOpenMenus();
      if (typeof closeRowActionMenus === "function") closeRowActionMenus();
    }

    if (mobileDialog?.open && button.closest("#mobile-nav a[href]")) {
      closeMobileNav(mobileDialog);
    }

    if (button.matches(ANCHOR_ROUTER_EXCLUSIONS)) {
      return;
    }

    if (button.dataset.editRecord) {
      event.preventDefault();
      if (typeof closeRowActionMenus === "function") closeRowActionMenus();
      if (typeof invokeRowEdit === "function") invokeRowEdit(button.closest("tr"));
      return;
    }

    if (button.dataset.rowAction) {
      event.preventDefault();
      if (typeof closeRowActionMenus === "function") closeRowActionMenus();
      if (typeof invokeRowAction === "function") invokeRowAction(button.closest("tr"), button.dataset.rowAction);
      return;
    }

    if (button.dataset.route) {
      event.preventDefault();
      if (typeof closeRowActionMenus === "function") closeRowActionMenus();
      navigateToRoute(button.dataset.route);
      return;
    }

    if (button.tagName === "A") {
      const href = button.getAttribute("href") || "";
      if (href === "javascript:history.back()") {
        event.preventDefault();
        if (window.history.length > 1) {
          window.history.back();
          return;
        }
        window.location.href = closeHref || "role-dashboard.html";
        return;
      }
      if (href === "javascript:void(0)") {
        const fallbackRoute = resolveContextualRoute(button);
        if (fallbackRoute) {
          event.preventDefault();
          navigateToRoute(fallbackRoute);
          return;
        }
        if (button.matches("[data-toast]")) {
          event.preventDefault();
          showToast(button.dataset.toastTitle || "Saved for later", button.dataset.toast || "");
          return;
        }
        event.preventDefault();
        return;
      }
      const internalRoute = normalizeInternalRoute(href);
      if (internalRoute) {
        event.preventDefault();
        navigateToRoute(href);
        return;
      }
    }

    // Buttons with their own click handler own their behavior — never
    // hijack them with label-based contextual routing.
    if (typeof button.onclick === "function") {
      return;
    }

    // Do not guess routes from labels at click time. Known CTAs are stamped
    // with data-route on load; everything else must have an explicit handler.
    if (button.getAttribute("aria-haspopup") === "menu" || button.closest("[data-layout='pagination-controls']")) {
      return;
    }

    if (button.matches("[data-toast]")) {
      event.preventDefault();
          showToast(button.dataset.toastTitle || "Saved for later", button.dataset.toast || "");
          return;
        }

    if (button.matches("[data-clear-workspace-filters]")) {
      event.preventDefault();
      if (typeof resetWorkspaceFilters === "function") resetWorkspaceFilters(button);
      return;
    }

    if (button.dataset.emptyCtaRoute) {
      event.preventDefault();
      navigateToRoute(button.dataset.emptyCtaRoute);
      return;
    }

    if (button.dataset.emptyCta === "primary") {
      event.preventDefault();
      const addButton = document.querySelector("[data-open-client-dialog], [data-open-user-dialog], [data-open-role-dialog]");
      if (addButton) addButton.click();
      return;
    }

    if (button.matches("[data-clear-search-preview]")) {
      event.preventDefault();
      const table = button.closest("[data-layout='table-surface']")?.querySelector("table");
      clearTableSearchPreview(table);
      const searchInput = button.closest("[data-layout='table-surface']")?.querySelector("input[placeholder*='Search']");
      if (searchInput) {
        searchInput.value = "";
        searchInput.focus();
      }
      return;
    }

    if (button.matches("[data-validate-scope]")) {
      event.preventDefault();
      const scope = document.querySelector(button.dataset.validateScope);
      if (!scope) return;
      if (validateScope(scope)) {
        showToast(button.dataset.successTitle || "Looks good", button.dataset.successText || "All required fields are complete.");
      }
      return;
    }

    const insideOverlay = button.closest("[data-overlay-surface]");
    if (insideOverlay) {
      const label = getActionLabel(button);
      if (button.matches("[data-overlay-close]") || /close|cancel|back/.test(label)) {
        event.preventDefault();
        if (typeof closeInPageOverlay === "function" && closeInPageOverlay()) return;
        if (closeHref) {
          window.location.href = closeHref;
          return;
        }
      }
      if (button.closest("form")) {
        return;
      }
      if (button.dataset.overlayAction === "validate") {
        event.preventDefault();
        if (!validateScope(insideOverlay)) return;
        const liveForm = document.querySelector("[data-overlay-surface] form") || document.querySelector("form") || document.body;
        if (window.RecruitOpsLive?.handleFormSubmit?.(liveForm)) return;
        showToast("Saved", "Your changes have been recorded.");
      }
      return;
    }

    if (button.dataset.notificationRead === "true") {
      event.preventDefault();
      markNotificationRead(button);
      return;
    }
    if (button.dataset.duplicateResolutionConfirm === "true") {
      event.preventDefault();
      if (button.disabled) {
        showToast("Choose a resolution first", "Pick how this profile should be handled before confirming the duplicate review.");
        return;
      }
      showToast("Resolution recorded", `${button.dataset.duplicateResolutionLabel || "The selected resolution"} will be applied to this profile.`);
    }
      });

      const isEditableTarget = (target) => {
        if (!(target instanceof HTMLElement)) return false;
        return Boolean(target.closest("input, textarea, select, [contenteditable='true']"));
      };

      document.addEventListener("keydown", (event) => {
        const insightPanel = document.querySelector("[data-workspace-insight-panel]");
        const insightTrigger = document.querySelector("[data-workspace-insight-trigger='true']");
        if (
          event.key === "Escape" &&
          !isEditableTarget(event.target)
        ) {
          if (typeof closeInPageOverlay === "function" && closeInPageOverlay()) {
            event.preventDefault();
            return;
          }
          if (closeHref && document.body.dataset.overlayPage === "true") {
            window.location.href = closeHref;
            return;
          }
        }
        if (event.key === "Escape" && insightPanel && !insightPanel.hidden) {
          event.preventDefault();
          insightPanel.hidden = true;
          insightTrigger?.setAttribute("aria-expanded", "false");
          insightTrigger?.classList.remove("is-active");
          const icon = insightTrigger?.querySelector(".material-symbols-outlined");
          if (icon) {
            icon.textContent = insightTrigger?.dataset.workspaceInsightOriginalIcon || "insights";
          }
          if (insightTrigger instanceof HTMLElement) {
            window.requestAnimationFrame(() => insightTrigger.focus());
          }
          return;
        }
        if (event.key === "Escape" && mobileDialog?.open) {
          closeMobileNav(mobileDialog);
          return;
        }
        if (event.key === "Tab" && mobileDialog?.open) {
          trapFocusWithin(event, mobileDialog.querySelector(".mobile-nav-panel"));
          return;
        }
        const liveOverlaySurface = document.querySelector("#ro-inpage-overlay [data-overlay-surface='true']") || overlaySurface;
        if (event.key === "Tab" && liveOverlaySurface && (document.body.classList.contains("is-inpage-overlay") || document.body.dataset.overlayPage === "true")) {
          trapFocusWithin(event, liveOverlaySurface);
        }
      });

      const searchInputs = document.querySelectorAll(".topbar-search input, input[placeholder*='Search']");
      searchInputs.forEach((input) => {
        if (!supportsSharedSearchPreview(input)) return;
        /* Live topbar search: typed terms filter the page's table via the
           shared filter engine (term override), composing with the page's
           own toolbar filters. Debounced; clears restore all rows. */
        if (input.id === "topbar-search" && input.dataset.liveTopbarBound !== "true") {
          input.dataset.liveTopbarBound = "true";
          input.addEventListener("input", () => {
            if (input.dataset.topbarTimerId) {
              window.clearTimeout(Number(input.dataset.topbarTimerId));
            }
            input.dataset.topbarTimerId = String(window.setTimeout(() => {
              delete input.dataset.topbarTimerId;
              const table = getLinkedTableSurface(input)?.querySelector("table");
              if (!table) return;
              const toolbar = findFilterToolbar(table.closest("[data-layout='table-surface']"));
              const term = input.value.trim();
              if (term.length === 1) return;
              applyToolbarFilters(toolbar, { notify: false, searchTerm: term });
            }, 220));
          });
          input.addEventListener("keydown", (event) => {
            if (event.key !== "Escape") return;
            input.value = "";
            const table = getLinkedTableSurface(input)?.querySelector("table");
            if (table) applyToolbarFilters(findFilterToolbar(table.closest("[data-layout='table-surface']")), { notify: false, searchTerm: "" });
          });
        }
        input.addEventListener("keydown", (event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            const term = input.value.trim();
            if (!term) {
              const tableSurface = getLinkedTableSurface(input);
              clearTableSearchPreview(tableSurface?.querySelector("table"));
              showToast("Search is empty", "Type something to search for.");
              return;
            }
            if (term.length < 2) {
              showToast("Keep typing", "Use at least 2 characters to search.");
              return;
            }
            setTableSearchPreview(getLinkedTableSurface(input)?.querySelector("table"), term);
          }
          if (event.key === "Escape") {
            const tableSurface = getLinkedTableSurface(input);
            clearTableSearchPreview(tableSurface?.querySelector("table"));
            input.value = "";
          }
        });
      });

      setupTableInteractionPolish(document);
      document.querySelectorAll("table").forEach((table) => {
        setupTableSelection(table);
      });

    });
    

/* ═══════════════════════════════════════════════════════════════
   COMMAND PALETTE (Ctrl+K / ⌘K)
   Fuzzy-lite search over: app navigation (from the sidebar),
   primary pages, and quick actions. One owner: setupCommandPalette
   builds the DOM lazily; toggleCommandPalette opens/closes.
   ═══════════════════════════════════════════════════════════════ */
/* Command palette entries derive from navigation.config.js (DRY: one
   source for sidebar, home grid, and palette) plus in-place actions. */
const NAV_PALETTE_ITEMS = (window.NAV_CONFIG && window.NAV_CONFIG.entries
  ? window.NAV_CONFIG.entries
      .filter((entry) => entry.showInSidebar !== false)
      .map((entry) => ({
        label: entry.label,
        hint: (window.NAV_CONFIG.categories.find((c) => c.key === entry.category) || {}).label || "Page",
        icon: entry.icon,
        route: entry.file,
      }))
  : []);

const COMMAND_ITEMS = [
  ...NAV_PALETTE_ITEMS,
  { label: "Toggle table density", hint: "Action", icon: "density_medium", action: () => {
      setDensityPreference(readDensityPreference() === "compact" ? "comfortable" : "compact");
      showToast("Table density changed", readDensityPreference() === "compact" ? "Rows are compacted to fit more on screen." : "Rows are back to comfortable spacing.");
    } },
];

let paletteElements = null;

function collectSidebarCommands() {
  const seen = new Set(COMMAND_ITEMS.map((i) => i.route));
  document.querySelectorAll(".nav-link[href]").forEach((link) => {
    const href = link.getAttribute("href");
    if (!href || !href.endsWith(".html") || seen.has(href)) return;
    const label = link.querySelector(".sidebar-label")?.textContent.trim();
    if (!label) return;
    seen.add(href);
    COMMAND_ITEMS.push({ label, hint: "Menu", icon: link.querySelector(".material-symbols-outlined")?.textContent.trim() || "chevron_right", route: href });
  });
}

function buildCommandPalette() {
  if (paletteElements) return paletteElements;
  collectSidebarCommands();
  const overlay = document.createElement("div");
  overlay.id = "command-palette";
  overlay.className = "fixed inset-0 z-[9999] hidden items-start justify-center bg-black/35 pt-[12vh]";
  overlay.innerHTML = `
    <div class="w-full max-w-xl mx-4 bg-surface rounded-xl border border-border shadow-2xl overflow-hidden" role="dialog" aria-label="Command palette">
      <div class="flex items-center gap-3 px-4 py-3 border-b border-border">
        <span class="material-symbols-outlined text-[20px] text-text-muted">search</span>
        <input id="palette-input" type="text" placeholder="Search pages and actions..." autocomplete="off"
          class="flex-1 bg-transparent text-sm text-on-surface outline-none placeholder:text-text-muted" aria-label="Search commands" />
        <kbd class="px-1.5 py-0.5 rounded bg-surface-alt border border-border font-mono text-[11px] text-text-muted">esc</kbd>
      </div>
      <div id="palette-results" class="max-h-[52vh] overflow-y-auto p-2" role="listbox"></div>
      <div class="px-4 py-2 border-t border-border flex items-center gap-4 text-[11px] text-text-muted">
        <span><kbd class="font-mono">↑↓</kbd> navigate</span><span><kbd class="font-mono">enter</kbd> open</span><span><kbd class="font-mono">esc</kbd> close</span>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  const input = overlay.querySelector("#palette-input");
  const results = overlay.querySelector("#palette-results");
  let matches = [];
  let activeIndex = 0;

  function score(item, q) {
    const hay = (item.label + " " + item.hint).toLowerCase();
    const idx = hay.indexOf(q);
    if (idx === -1) {
      // subsequence fallback: all query chars in order
      let pos = 0;
      for (const ch of q) { pos = hay.indexOf(ch, pos); if (pos === -1) return -1; pos += 1; }
      return 500 + pos;
    }
    // exact prefix ranks first (0), later substring matches rank by position
    return idx + (item.label.toLowerCase().startsWith(q) ? 0 : 1);
  }

  function render() {
    const q = input.value.trim().toLowerCase();
    matches = q ? COMMAND_ITEMS
      .map((item) => ({ item, s: score(item, q) }))
      .filter((m) => m.s >= 0)
      .sort((a, b) => a.s - b.s)
      .map((m) => m.item)
      .slice(0, 12)
      : COMMAND_ITEMS.slice(0, 12);
    activeIndex = 0;
    if (!matches.length) {
      results.innerHTML = '<div class="px-3 py-8 text-center text-sm text-text-muted">No matching pages or actions.</div>';
      return;
    }
    results.innerHTML = matches.map((item, i) => `
      <button type="button" role="option" aria-selected="${i === activeIndex}" data-palette-index="${i}"
        class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left ${i === activeIndex ? "bg-highlight-soft" : "hover:bg-highlight-soft"}">
        <span class="material-symbols-outlined text-[18px] text-text-muted">${item.icon}</span>
        <span class="flex-1 text-sm font-medium text-on-surface">${item.label}</span>
        <span class="text-[11px] uppercase tracking-wide text-text-muted">${item.hint}</span>
      </button>`).join("");
  }

  function run(item) {
    closeCommandPalette();
    if (item.action) { item.action(); return; }
    if (item.route) navigateToRoute(item.route);
  }

  input.addEventListener("input", render);
  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") { event.preventDefault(); activeIndex = Math.min(activeIndex + 1, matches.length - 1); render(); scrollActive(); }
    else if (event.key === "ArrowUp") { event.preventDefault(); activeIndex = Math.max(activeIndex - 1, 0); render(); scrollActive(); }
    else if (event.key === "Enter") { event.preventDefault(); if (matches[activeIndex]) run(matches[activeIndex]); }
  });
  function scrollActive() {
    const el = results.querySelector(`[data-palette-index="${activeIndex}"]`);
    if (el) el.scrollIntoView({ block: "nearest" });
  }
  results.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-palette-index]");
    if (btn) run(matches[Number(btn.dataset.paletteIndex)]);
  });
  overlay.addEventListener("mousedown", (event) => { if (event.target === overlay) closeCommandPalette(); });
  paletteElements = { overlay, input, render };
  return paletteElements;
}

function openCommandPalette() {
  const { overlay, input, render } = buildCommandPalette();
  overlay.classList.remove("hidden");
  overlay.classList.add("flex");
  input.value = "";
  render();
  input.focus();
}

function closeCommandPalette() {
  if (!paletteElements) return;
  paletteElements.overlay.classList.add("hidden");
  paletteElements.overlay.classList.remove("flex");
}

function toggleCommandPalette() {
  if (!paletteElements || paletteElements.overlay.classList.contains("hidden")) openCommandPalette();
  else closeCommandPalette();
}

function setupCommandPalette() {
  buildCommandPalette();
}


/* ═══════════════════════════════════════════════════════════════
   SKELETON LOADERS
   Helper functions to show/hide skeleton placeholders while
   API data loads. Call showSkeleton before fetch, hideSkeleton
   after data renders.
   ═══════════════════════════════════════════════════════════════ */
function showSkeletonTable(container, rows = 5, cols = 4) {
  const tbody = container?.tagName === "TBODY"
    ? container
    : container?.querySelector?.("tbody") || (container?.closest?.("table")?.querySelector("tbody"));
  if (tbody) {
    if (!tbody._roTemplate) {
      const first = tbody.querySelector("tr[data-row-template], tr:not(.skeleton-row):not([data-generated-empty-state])");
      if (first) tbody._roTemplate = first.cloneNode(true);
    }
    tbody.innerHTML = Array.from({ length: rows }, () => (
      `<tr class="skeleton-row" aria-hidden="true"><td colspan="${cols}"><div class="ro-skel"><span></span></div></td></tr>`
    )).join("");
    return;
  }
  if (!container) return;
  const existing = container.querySelector(":scope > .skeleton-rows");
  if (existing) return;
  const skeletonHtml = `
    <div class="skeleton-rows" aria-hidden="true">
      ${Array.from({length: rows}, () => `
        <div class="skeleton-row">
          ${Array.from({length: cols}, (_, i) => `<div class="skeleton skeleton-${i === 0 ? 'text' : 'text-sm'}" style="width:${60 + Math.random() * 30}%"></div>`).join("")}
        </div>
      `).join("")}
    </div>`;
  container.insertAdjacentHTML("afterbegin", skeletonHtml);
}

function showSkeletonCards(container, count = 3) {
  if (!container) return;
  const existing = container.querySelector(".skeleton-card");
  if (existing) return;
  const skeletonHtml = Array.from({length: count}, () => `
    <div class="skeleton-card">
      <div class="flex items-center gap-3">
        <div class="skeleton skeleton-avatar"></div>
        <div class="flex-1">
          <div class="skeleton skeleton-text"></div>
          <div class="skeleton skeleton-text-sm mt-2"></div>
        </div>
      </div>
      <div class="skeleton skeleton-text-lg"></div>
      <div class="flex gap-2">
        <div class="skeleton skeleton-badge"></div>
        <div class="skeleton skeleton-badge"></div>
      </div>
    </div>
  `).join("");
  container.insertAdjacentHTML("afterbegin", skeletonHtml);
}

function hideSkeleton(container) {
  if (!container) return;
  container.querySelectorAll(":scope > .skeleton-rows, .skeleton-table, .skeleton-card, tr.skeleton-row").forEach((el) => el.remove());
}

/* ═══════════════════════════════════════════════════════════════
   PAGE TRANSITIONS
   Smooth fade when navigating between pages.
   ═══════════════════════════════════════════════════════════════ */
function initPageTransition() {
  const main = document.querySelector(".app-main") || document.querySelector("main");
  if (!main) return;
  main.classList.add("page-transition-enter");
  main.addEventListener("animationend", () => main.classList.remove("page-transition-enter"), { once: true });
}
document.addEventListener("DOMContentLoaded", initPageTransition);


/* ═══════════════════════════════════════════════════════════════
   PIPELINE DRAG-AND-DROP
   Enables native HTML5 drag-and-drop on the pipeline board.
   Cards carry their application_id via data attribute; columns
   are the drop zones. On drop, PATCH /pipeline/applications/:id/stage
   ═══════════════════════════════════════════════════════════════ */
function setupPipelineDragDrop() {
  const board = document.querySelector(".flex.gap-4.min-w-max");
  if (!board) return;

  board.querySelectorAll("[data-application-id], .cursor-grab, [draggable='true']").forEach((card) => {
    if (card.dataset.dragWired === "true") return;
    card.dataset.dragWired = "true";
    card.setAttribute("draggable", "true");
    card.addEventListener("dragstart", (e) => {
      card.classList.add("opacity-50", "scale-95");
      e.dataTransfer.setData("text/plain", card.dataset.applicationId || "");
      e.dataTransfer.effectAllowed = "move";
    });
    card.addEventListener("dragend", () => {
      card.classList.remove("opacity-50", "scale-95");
      board.querySelectorAll(".border-primary").forEach(el => el.classList.remove("border-primary", "bg-primary/5"));
    });
  });

  // Set up drop zones on columns
  Array.from(board.children).filter((col) => col.querySelector("h3")).forEach((col) => {
    const stage = col.querySelector("h3")?.textContent.trim();
    if (!stage || col.dataset.dropWired === "true") return;
    col.dataset.dropWired = "true";

    col.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      col.classList.add("ring-2", "ring-primary/40", "ring-offset-1");
    });

    col.addEventListener("dragleave", () => {
      col.classList.remove("ring-2", "ring-primary/40", "ring-offset-1");
    });

    col.addEventListener("drop", async (e) => {
      e.preventDefault();
      col.classList.remove("ring-2", "ring-primary/40", "ring-offset-1");
      const applicationId = e.dataTransfer.getData("text/plain");
      if (!applicationId) return;

      // Find the card and move it
      const card = board.querySelector(`[data-application-id="${applicationId}"]`);
      if (!card) return;
      const dropZone = col.querySelector(".pipeline-drop-zone, .space-y-3, .flex-1");
      if (dropZone) {
        dropZone.classList.remove("flex", "items-center", "justify-center");
        dropZone.querySelectorAll(".pipeline-empty-note, .border-dashed").forEach((node) => {
          if (!node.closest(".cursor-grab, [data-pipeline-candidate-card], [data-application-id]")) node.remove();
        });
        dropZone.appendChild(card);
      }

      // Update the stage badge count
      Array.from(board.children).filter((c) => c.querySelector("h3")).forEach((c) => {
        const count = c.querySelector(".space-y-3, .flex-1")?.children.length || 0;
        const badge = c.querySelector("span.bg-surface");
        if (badge) badge.textContent = count;
      });

      // Call the API
      try {
        await apiRequest(`/pipeline/applications/${applicationId}/stage`, {
          method: "PATCH",
          body: JSON.stringify({ to_stage: stage }),
        });
        showToast("Stage updated", `Candidate moved to ${stage}`);
      } catch (err) {
        showToast("Move failed", err.message || "Could not update stage");
        // Revert on failure
        location.reload();
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", setupPipelineDragDrop);


/* ═══════════════════════════════════════════════════════════════
   BREADCRUMB NAVIGATION
   Auto-generates breadcrumbs from the sidebar hierarchy.
   Injects into .app-topbar on app pages.
   ═══════════════════════════════════════════════════════════════ */
function setupVisualPassChrome() {
  const kind = document.body?.dataset.routeKind;
  const routeId = document.body?.dataset.routeId || "";

  document.querySelectorAll("[data-password-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = document.getElementById("password");
      if (!input) return;
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      const icon = btn.querySelector(".material-symbols-outlined");
      if (icon) icon.textContent = show ? "visibility_off" : "visibility";
      btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
    });
  });

  if (kind !== "app" && kind !== "overlay") return;

  document.querySelectorAll("a.sidebar-brand").forEach((link) => {
    link.setAttribute("href", "role-dashboard.html");
    link.title = "Go to Role Dashboard";
  });

  document.querySelectorAll(".workspace-surface .rounded-full").forEach((el) => {
    const label = (el.textContent || "").trim();
    if (label.length < 1 || label.length > 3) return;
    let hash = 0;
    for (let i = 0; i < label.length; i += 1) hash = (hash * 31 + label.charCodeAt(i)) % 5;
    const fills = ["#1e293b", "#334155", "#475569", "#0f172a", "#1e3a4c"];
    el.style.background = fills[hash];
    el.style.color = "#ffffff";
    el.style.borderColor = "transparent";
  });

  document.querySelectorAll(".workspace-surface").forEach((surface) => {
    surface.querySelectorAll("p, span").forEach((node) => {
      if (node.dataset.pageSummary === "true") return;
      const text = (node.textContent || "").trim();
      const match = text.match(/^Showing\s+(\d+)\s+to\s+(\d+)\s+of\s+(\d+)\s+entries$/i);
      if (match) node.textContent = `${match[2]} of ${match[3]}`;
    });
  });

  if (routeId === "role-dashboard") {
    document.querySelectorAll(".workspace-surface header p, .workspace-surface .font-body-md").forEach((p) => {
      if (/command center/i.test(p.textContent || "")) p.textContent = "Your queue";
    });
  }

  document.querySelectorAll("[data-route-id='daily-updates-workspace'] .group .opacity-0, body[data-route-id='daily-updates-workspace'] .opacity-0").forEach((el) => {
    el.classList.remove("opacity-0", "group-hover:opacity-100");
  });
}

function injectBreadcrumbs() {}

document.addEventListener("DOMContentLoaded", injectBreadcrumbs);


/* ═══════════════════════════════════════════════════════════════
   BOTTOM NAVIGATION (Mobile)
   Injected into app pages on mobile viewports.
   ═══════════════════════════════════════════════════════════════ */
function injectBottomNav() {
  const existing = document.querySelector(".bottom-nav");
  const isApp = document.body?.dataset.routeKind === "app" && document.querySelector(".app-shell");
  const compactPortrait = window.innerWidth <= 768 && window.innerHeight > 500
    && window.matchMedia("(orientation: portrait)").matches;

  if (!isApp || !compactPortrait) {
    existing?.remove();
    return;
  }
  if (existing) return;

  const routeId = document.body?.dataset.routeId || "";
  const navItems = [
    { icon: "dashboard", label: "Home", route: "company-dashboard.html" },
    { icon: "work", label: "Reqs", route: "requisition-list.html" },
    { icon: "groups", label: "People", route: "candidate-profiles.html" },
    { icon: "view_kanban", label: "Pipeline", route: "pipeline-board.html" },
    { icon: "approval", label: "Approvals", route: "approvals-inbox.html" },
  ];

  const nav = document.createElement("nav");
  nav.className = "bottom-nav";
  nav.setAttribute("aria-label", "Mobile navigation");

  nav.innerHTML = navItems.map((item) => `
    <a href="${item.route}" class="bottom-nav-item ${routeId === item.route.replace('.html', '') ? 'active' : ''}">
      <span class="material-symbols-outlined">${item.icon}</span>
      <span>${item.label}</span>
    </a>
  `).join("");

  document.body.appendChild(nav);
}

document.addEventListener("DOMContentLoaded", injectBottomNav);
window.addEventListener("resize", () => {
  if (window.__roViewportRaf) cancelAnimationFrame(window.__roViewportRaf);
  window.__roViewportRaf = requestAnimationFrame(syncViewportLayout);
});
window.addEventListener("orientationchange", () => {
  setTimeout(syncViewportLayout, 50);
  setTimeout(syncViewportLayout, 300);
});
if (window.visualViewport) {
  window.visualViewport.addEventListener("resize", () => {
    if (window.__roViewportRaf) cancelAnimationFrame(window.__roViewportRaf);
    window.__roViewportRaf = requestAnimationFrame(syncViewportLayout);
  });
}

function syncViewportLayout() {
  const root = document.documentElement;
  const height = Math.round(window.visualViewport?.height || window.innerHeight);
  const width = Math.round(window.visualViewport?.width || window.innerWidth);
  const landscape = width > height;
  root.dataset.orientation = landscape ? "landscape" : "portrait";
  root.style.setProperty("--app-height", `${height}px`);
  root.style.setProperty("--app-width", `${width}px`);
  document.querySelectorAll(".reveal, .reveal-scale, .reveal-left, .reveal-right, .reveal-pop").forEach((el) => {
    const rect = el.getBoundingClientRect();
    if (rect.bottom > 24 && rect.top < height - 24) el.classList.add("visible");
  });
  injectBottomNav();
}

document.addEventListener("DOMContentLoaded", syncViewportLayout);
if (document.readyState !== "loading") syncViewportLayout();

function setupPagePanLock() {
  if (document.documentElement.dataset.panLock === "true") return;
  document.documentElement.dataset.panLock = "true";

  const pin = (el) => {
    if (el && el.scrollLeft) el.scrollLeft = 0;
  };

  const pinRoots = () => {
    pin(document.documentElement);
    pin(document.body);
    document.querySelectorAll(".app-canvas, .login-split, .login-right, .login-left, .landing-hero").forEach(pin);
  };

  document.addEventListener("scroll", (event) => {
    const target = event.target;
    if (target === document || target === document.documentElement || target === document.body) {
      pinRoots();
      return;
    }
    if (!(target instanceof Element)) return;
    if (
      target.classList.contains("app-canvas")
      || target.classList.contains("login-split")
      || target.classList.contains("login-right")
      || target.classList.contains("login-left")
      || target.classList.contains("landing-hero")
    ) {
      pin(target);
    }
  }, { capture: true, passive: true });

  pinRoots();
}

document.addEventListener("DOMContentLoaded", setupPagePanLock);
if (document.readyState !== "loading") setupPagePanLock();


/* ═══════════════════════════════════════════════════════════════
   SVG CHART UTILITIES
   Lightweight inline SVG charts for dashboards.
   ═══════════════════════════════════════════════════════════════ */
function renderLineChart(container, data, options = {}) {
  if (!container || !data.length) return;
  const { width = 400, height = 120, color = "#1E293B", label = "" } = options;
  const max = Math.max(...data.map(d => d.value), 1);
  const min = Math.min(...data.map(d => d.value), 0);
  const range = max - min || 1;
  const padding = 20;
  const chartW = width - padding * 2;
  const chartH = height - padding * 2;

  const points = data.map((d, i) => {
    const x = padding + (i / (data.length - 1)) * chartW;
    const y = padding + chartH - ((d.value - min) / range) * chartH;
    return { x, y, label: d.label, value: d.value };
  });

  const pathD = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
  const areaD = pathD + ` L ${points[points.length - 1].x} ${padding + chartH} L ${points[0].x} ${padding + chartH} Z`;

  const svg = `
    <svg width="100%" viewBox="0 0 ${width} ${height}" class="w-full">
      <defs>
        <linearGradient id="area-${label.replace(/\s/g, '')}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${color}" stop-opacity="0.15"/>
          <stop offset="100%" stop-color="${color}" stop-opacity="0.02"/>
        </linearGradient>
      </defs>
      <path d="${areaD}" fill="url(#area-${label.replace(/\s/g, '')})" />
      <path d="${pathD}" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      ${points.map(p => `<circle cx="${p.x}" cy="${p.y}" r="3" fill="${color}" />`).join("")}
      ${points.map(p => `<text x="${p.x}" y="${height - 2}" text-anchor="middle" font-size="9" fill="#6E7476">${p.label}</text>`).join("")}
    </svg>`;
  container.innerHTML = svg;
}

function renderBarChart(container, data, options = {}) {
  if (!container || !data.length) return;
  const { width = 420, height = 168, color = "#1E293B" } = options;
  const max = Math.max(...data.map(d => d.value), 1);
  const padX = 16;
  const padTop = 22;
  const padBottom = 44;
  const chartW = width - padX * 2;
  const chartH = height - padTop - padBottom;
  const barW = Math.min(chartW / data.length - 8, 48);

  const bars = data.map((d, i) => {
    const x = padX + (i / data.length) * chartW + (chartW / data.length - barW) / 2;
    const barH = Math.max(4, (d.value / max) * chartH);
    const y = padTop + chartH - barH;
    return { x, y, w: barW, h: barH, label: String(d.label || ""), value: d.value };
  });

  const svg = `
    <svg width="100%" viewBox="0 0 ${width} ${height}" class="w-full">
      ${bars.map((b) => {
        const cx = b.x + b.w / 2;
        const shown = b.label.length > 18 ? `${b.label.slice(0, 16)}…` : b.label;
        return `
        <rect x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}" fill="${color}" rx="3" opacity="0.82"/>
        <text x="${cx}" y="${b.y - 6}" text-anchor="middle" font-size="10" fill="#6E7476">${b.value}</text>
        <text x="${cx}" y="${height - 28}" text-anchor="end" font-size="10" fill="#4B5257" transform="rotate(-32 ${cx} ${height - 28})">${shown.replace(/</g, "")}</text>`;
      }).join("")}
    </svg>`;
  container.innerHTML = svg;
}

function renderDonutChart(container, data, options = {}) {
  if (!container || !data.length) return;
  const { size = 120, colors = ["#1E293B", "#4B5257", "#6E7476", "#A0A4A8", "#D4D8D6"] } = options;
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  const r = size / 2 - 10;
  const cx = size / 2;
  const cy = size / 2;

  let currentAngle = -90;
  const arcs = data.map((d, i) => {
    const angle = (d.value / total) * 360;
    const startAngle = currentAngle;
    currentAngle += angle;
    const endAngle = currentAngle;
    const startRad = (startAngle * Math.PI) / 180;
    const endRad = (endAngle * Math.PI) / 180;
    const x1 = cx + r * Math.cos(startRad);
    const y1 = cy + r * Math.sin(startRad);
    const x2 = cx + r * Math.cos(endRad);
    const y2 = cy + r * Math.sin(endRad);
    const largeArc = angle > 180 ? 1 : 0;
    const path = `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`;
    return { path, color: colors[i % colors.length], label: d.label, value: d.value, pct: Math.round((d.value / total) * 100) };
  });

  const svg = `
    <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
      ${arcs.map(a => `<path d="${a.path}" fill="${a.color}" />`).join("")}
      <circle cx="${cx}" cy="${cy}" r="${r * 0.55}" fill="#ffffff"/>
      <text x="${cx}" y="${cy - 4}" text-anchor="middle" font-size="14" font-weight="600" fill="#1E293B">${total}</text>
      <text x="${cx}" y="${cy + 10}" text-anchor="middle" font-size="9" fill="#6E7476">total</text>
    </svg>
    <div class="flex flex-wrap gap-2 mt-2">
      ${arcs.map(a => `<div class="flex items-center gap-1 text-[10px] text-on-surface"><span class="w-2 h-2 rounded-full" style="background:${a.color}"></span>${a.label} (${a.pct}%)</div>`).join("")}
    </div>`;
  container.innerHTML = svg;
}
