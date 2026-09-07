

const WORKSPACE_INSIGHTS = {
  "user-management": {
    title: "User coverage snapshot",
    copy: "Use this staged panel to review permission health, invite backlog, and ownership balance before the live admin APIs are connected.",
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
const WORKFLOW_BRIEFS = {
  "candidate-screening": {
    badge: "Decision Desk",
    title: "Move from evidence to decision without losing context.",
    copy: "Keep the candidate summary, requisition rules, and your evaluation actions aligned before you advance or reject the profile.",
    bullets: [
      "Validate the requisition hard requirements before scoring soft-fit criteria.",
      "Capture the screening outcome while context is still fresh.",
      "Escalate exceptional cases instead of forcing them through a standard path.",
    ],
  },
  "resume-upload-and-review": {
    badge: "Intake Flow",
    title: "Turn uploads into clean candidate records with less back-and-forth.",
    copy: "Work from the queue, verify the extracted identity details, then hand off to duplicate review before the record enters the main pipeline.",
    bullets: [
      "Start with files marked ready for intake to keep throughput predictable.",
      "Use the review pane to confirm contact details before pipeline entry.",
      "Route uncertain records into duplicate review instead of guessing.",
    ],
  },
  "daily-updates-workspace": {
    badge: "Reporting Rhythm",
    title: "Keep daily updates concise, measurable, and easy to action.",
    copy: "A good update captures what changed, what is blocked, and what needs attention in the next 24 hours.",
    bullets: [
      "Use the counts to anchor the summary in measurable progress.",
      "Flag high-priority blockers so reviewers know where to intervene first.",
      "Open recent updates when you need continuity before posting a new one.",
    ],
  },
  "candidate-duplicate-review": {
    badge: "Conflict Resolution",
    title: "Resolve duplicates by protecting record quality, not just clearing the queue.",
    copy: "Use the confidence reasoning and record history to choose whether this profile should merge into the system of record or remain separate.",
    bullets: [
      "Prefer merge when primary identity fields and ownership context line up cleanly.",
      "Keep both only when the incoming record clearly represents a distinct candidate path.",
      "Escalate edge cases instead of forcing a decision with low confidence.",
    ],
  },
  "approvals-inbox": {
    badge: "Decision Queue",
    title: "Surface the riskiest approval first, then move decisively.",
    copy: "The queue is most useful when the current focus is explicit: pick an item, confirm the risk, and move straight into review.",
    bullets: [
      "Start with overdue or critical items before standard approvals.",
      "Use request type and related record together to avoid shallow reviews.",
      "Open the review drawer once the priority and business context are clear.",
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

const OVERLAY_BRIEFS = {
  "exception-request-dialog": {
    title: "Capture the exception clearly before you escalate it.",
    copy: "A good exception request explains the policy variance, the business impact, and the next approver path without leaving hidden assumptions behind.",
    pills: ["Policy variance", "Audit trail", "Executive routing"],
  },
  "stage-move-dialog": {
    title: "Make the stage decision explicit before you move the candidate.",
    copy: "Keep the target stage, rationale, and notes aligned so the next teammate can understand why this transition happened.",
    pills: ["Pipeline decision", "Hiring-team context", "Candidate lifecycle"],
  },
  "reassign-owner-dialog": {
    title: "Hand ownership over without dropping active work.",
    copy: "Use reassignment only when the new owner and the audit reason are clear enough to preserve continuity across outreach, approvals, and interviews.",
    pills: ["Ownership continuity", "Audit reason", "Task carryover"],
  },
  "approval-review-drawer": {
    title: "Review the risk and choose the next action deliberately.",
    copy: "This drawer should make it obvious whether the request is approvable now, needs more information, or should be rejected with a clear reason.",
    pills: ["Decision record", "SLA pressure", "Business impact"],
  },
  "pipeline-history-drawer": {
    title: "Use the timeline to explain the candidate path, not just view it.",
    copy: "The strongest audit trails show who moved the candidate, why the move happened, and which steps were manual versus automated.",
    pills: ["Audit trail", "Manual vs automation", "Stage continuity"],
  },
};

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
    .find((button) => /\\binsights\\b/i.test(getActionLabel(button)));
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
      showToast("Insights opened", "Contextual workspace signals are now visible in the integrated shell.");
      return;
    }
    closePanel({ restoreFocus: false });
    showToast("Insights hidden", "The workspace is back to its compact operating view.");
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
      const recordText = (relatedRecordCell.textContent || "").replace(/\\s+/g, " ").trim();
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
      { match: /overdue reviews/i, route: "approvals-inbox.html", label: "Open Overdue Reviews" },
      { match: /stale reqs/i, route: "requisition-detail.html", label: "Open Stale Requisitions" },
      { match: /high priority/i, route: "candidate-screening.html", label: "Open High Priority Roles" },
      { match: /offers sent/i, route: "approval-review-drawer.html", label: "Open Offers Sent" },
    ];

    document.querySelectorAll('[data-layout="metric-card"]').forEach((card) => {
      const label = (card.textContent || "").replace(/\\s+/g, " ").trim();
      const config = metricRoutes.find((entry) => entry.match.test(label));
      if (!config) return;
      promoteSurfaceRoute(card, config.route, config.label);
    });

    document.querySelectorAll("p").forEach((copy) => {
      const text = (copy.textContent || "").replace(/\\s+/g, " ").trim();
      if (!/^REQ-\\d+/i.test(text)) return;
      const requisitionRow = copy.closest("div.flex.justify-between.items-start");
      if (!requisitionRow) return;
      promoteSurfaceRoute(requisitionRow, "requisition-detail.html", `Open ${text}`);
    });
  }

  if (routeId === "client-detail") {
    document.querySelectorAll("td").forEach((cell) => {
      const label = (cell.textContent || "").replace(/\\s+/g, " ").trim();
      if (!/^(Senior Frontend Engineer|Product Manager|Backend Developer|DevOps Engineer)$/i.test(label)) return;
      promoteSurfaceRoute(cell, "requisition-detail.html", `Open ${label}`);
    });
  }

  if (routeId === "location-management" || routeId === "location-form-drawer") {
    document.querySelectorAll("span, div").forEach((node) => {
      const label = (node.textContent || "").replace(/\\s+/g, " ").trim();
      if (/^(HQ - San Francisco|London Hub|Austin Tech Center|LOC-001|LOC-042|LOC-088)$/i.test(label)) {
        promoteSurfaceRoute(node, "location-form-drawer.html", `Open ${label}`);
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
      const label = (card.textContent || "").replace(/\\s+/g, " ").trim();
      const config = metricRoutes.find((entry) => entry.match.test(label));
      if (!config) return;
      promoteSurfaceRoute(card, config.route, config.label);
    });

    document.querySelectorAll("span").forEach((copy) => {
      const label = (copy.textContent || "").replace(/\\s+/g, " ").trim();
      if (!/^(Alex Rodriguez|Emily Chen|David R\\.)$/i.test(label)) return;
      promoteSurfaceRoute(copy, "candidate-review-drawer.html", `Open ${label}`);
    });
  }

  if (routeId === "my-work-dashboard") {
    document.querySelectorAll("td, div, button").forEach((node) => {
      const label = (node.textContent || "").replace(/\\s+/g, " ").trim();
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
      const label = (node.textContent || "").replace(/\\s+/g, " ").trim();
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
      const label = (node.textContent || "").replace(/\\s+/g, " ").trim();
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
      const label = (node.textContent || "").replace(/\\s+/g, " ").trim();
      if (/^(Updates Submitted|Pending Review)$/i.test(label)) {
        promoteSurfaceRoute(node.closest("div.bg-surface") || node, "daily-update-detail-panel.html", `Open ${label}`);
        return;
      }
      if (/^(UX Designer \\(REQ-9102\\)|Backend Lead \\(REQ-8771\\)|Marketing Director \\(REQ-9011\\)|DevOps Engineer \\(REQ-8920\\))$/i.test(label)) {
        promoteSurfaceRoute(node, "daily-update-detail-panel.html", `Open ${label}`);
      }
    });
  }

  if (routeId === "pipeline-board") {
    document.querySelectorAll("p, button, div").forEach((node) => {
      const label = (node.textContent || "").replace(/\\s+/g, " ").trim();
      if (/^(Alex Mercer|Sarah Chen|David Jones|Omar Farooq|Elena Rostova|Kunal Patel)$/i.test(label)) {
        promoteSurfaceRoute(node, "candidate-review-drawer.html", `Open ${label}`);
      }
    });

    document.querySelectorAll('div[class*="w-[300px]"]').forEach((column) => {
      const stageName = (column.querySelector("h3")?.textContent || "").replace(/\\s+/g, " ").trim();
      if (!stageName) return;
      const addButton = column.querySelector(":scope > div button");
      if (!addButton) return;
      promoteSurfaceRoute(addButton, "candidate-review-drawer.html", `Open ${stageName} candidate workspace`);
    });
  }
}

function setupContextualActionToasts(scope = document) {
  const actionMatchers = [
    { pattern: /export/i, title: "Export prepared", body: "This export action is staged cleanly and ready for backend delivery." },
    { pattern: /insights/i, title: "Insights panel", body: "This analytics action can now be wired without reworking the page chrome." },
    { pattern: /manage stages/i, title: "Stage controls", body: "Stage configuration is preserved and ready for workflow settings APIs." },
    { pattern: /^role$|^location$|^owner$|^stage$|^readiness$|stale status/i, title: "Filter staged", body: "This filter control is now behaving like a live entry point for future API-backed filtering." },
  ];

  scope.querySelectorAll("button").forEach((button) => {
    if (button.dataset.toast || button.dataset.route || button.closest("form")) return;
    const label = (button.textContent || button.getAttribute("aria-label") || "").trim();
    const match = actionMatchers.find((entry) => entry.pattern.test(label));
    if (!match) return;
    button.dataset.toastTitle = match.title;
    button.dataset.toast = match.body;
  });
}

function setupWorkflowActionPolish() {
  const routeId = document.body?.dataset.routeId || "";

  if (routeId === "candidate-screening") {
    document.querySelectorAll("button").forEach((button) => {
      const label = getActionLabel(button);
      if (/save draft/.test(label)) {
        button.dataset.toastTitle = "Evaluation draft saved";
        button.dataset.toast = "Your screening notes are staged locally and ready for workflow persistence once APIs are connected.";
      }
      if (/submit evaluation/.test(label)) {
        button.dataset.toastTitle = "Evaluation staged";
        button.dataset.toast = "This screening decision is ready to move into reviewer and stage-transition workflows.";
      }
    });
  }

  if (routeId === "daily-updates-workspace") {
    document.querySelectorAll("button").forEach((button) => {
      const label = getActionLabel(button);
      if (/save draft/.test(label)) {
        button.dataset.toastTitle = "Draft saved";
        button.dataset.toast = "Your update draft is staged cleanly and ready for persistence once the reporting APIs are wired.";
      }
      if (/submit update/.test(label)) {
        button.dataset.toastTitle = "Update staged";
        button.dataset.toast = "This daily update is ready to enter the reviewer queue and downstream reporting workflows.";
      }
    });
  }

  if (routeId === "candidate-duplicate-review") {
    document.querySelectorAll("button").forEach((button) => {
      const label = getActionLabel(button);
      if (/skip for now/.test(label)) {
        button.dataset.toastTitle = "Review deferred";
        button.dataset.toast = "This duplicate case is intentionally deferred and can be re-queued without losing review context.";
      }
    });
  }

  if (routeId === "location-management" || routeId === "location-form-drawer") {
    document.querySelectorAll("button").forEach((button) => {
      const label = getActionLabel(button);
      if (/archive/.test(label)) {
        button.dataset.toastTitle = "Archive staged";
        button.dataset.toast = "This location archive action is preserved with a safe confirmation point before live admin APIs are connected.";
      }
    });
  }

  if (routeId === "user-management") {
    document.querySelectorAll("button").forEach((button) => {
      const label = getActionLabel(button);
      if (/suspend|reset password|resend invite/.test(label)) {
        button.dataset.toastTitle = "Account action staged";
        button.dataset.toast = "This user lifecycle action is ready to connect to account management APIs without changing the admin flow.";
      }
      if (/more actions/.test(label)) {
        button.dataset.toastTitle = "Action menu staged";
        button.dataset.toast = "This user action menu is ready for lifecycle controls like reset password, resend invite, and suspension.";
      }
      if (/more filters/.test(label)) {
        button.dataset.toastTitle = "Advanced filters staged";
        button.dataset.toast = "These user filters are ready to connect to role, location, and status-based directory queries.";
      }
    });
  }

  if (routeId === "role-management" || routeId === "role-form-drawer") {
    document.querySelectorAll("button").forEach((button) => {
      const label = getActionLabel(button);
      if (/duplicate/.test(label)) {
        button.dataset.toastTitle = "Role template staged";
        button.dataset.toast = "This duplicate action is ready to spin up a new role template without changing the permissions workflow.";
      }
      if (/audit log/.test(label)) {
        button.dataset.toastTitle = "Audit history staged";
        button.dataset.toast = "This audit entry point is ready for permission history and governance trail APIs.";
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
  const routeTitle = (document.body.dataset.routeTitle || "").replace(/\\s+/g, " ").trim();
  const parentTitle = (document.body.dataset.parentTitle || "").replace(/\\s+/g, " ").trim();
  const titleNodes = Array.from(document.querySelectorAll("[data-shell-page-title], [data-shell-focus-title]"));
  const shellFocusCopyNode = document.querySelector("[data-shell-focus-copy]");
  const normalize = (value) => value.replace(/\\s+/g, " ").trim().toLowerCase();
  const authoredShellCopy = (shellFocusCopyNode?.textContent || "").replace(/\\s+/g, " ").trim();
  const preserveShellMountCopy = Boolean(
    authoredShellCopy
      && /stays mounted on/i.test(authoredShellCopy)
      && (!parentTitle || normalize(authoredShellCopy).includes(normalize(parentTitle))),
  );
  const headerSection = surface.querySelector("[data-overlay-section='header']");
  const headerNode = headerSection?.querySelector("h1, h2, h3");
  const headerHeading = (headerNode?.textContent || "").replace(/\\s+/g, " ").trim();
  const headerCopyNode = headerSection?.querySelector("p");
  const headerCopy = (headerCopyNode?.textContent || "").replace(/\\s+/g, " ").trim();
  const headerMetaCandidates = Array.from(headerSection?.querySelectorAll("span, div") || [])
    .map((node) => (node.textContent || "").replace(/\\s+/g, " ").trim())
    .filter(Boolean)
    .filter((text) => normalize(text) !== normalize(routeTitle))
    .filter((text) => normalize(text) !== normalize(parentTitle))
    .filter((text) => normalize(text) !== normalize(headerHeading))
    .filter((text) => text.length <= 96)
    .filter((text) => !/^close(?:\\s+(?:overlay|dialog|drawer|panel))?$/i.test(text));
  const headerMeta = headerMetaCandidates[0] || "";
  const usableHeaderCopy = headerCopy
    && normalize(headerCopy) !== normalize(routeTitle)
    && normalize(headerCopy) !== normalize(parentTitle)
    && normalize(headerCopy) !== normalize(headerHeading)
    && headerCopy.length <= 96
      ? headerCopy
      : headerMeta;

  const headingCandidates = [headerHeading, ...Array.from(surface.querySelectorAll("h1, h2, h3"))
    .map((node) => (node.textContent || "").replace(/\\s+/g, " ").trim())
  ]
    .filter(Boolean)
    .filter((text) => normalize(text) !== normalize(routeTitle))
    .filter((text) => normalize(text) !== normalize(parentTitle))
    .filter((text) => text.length <= 72);

  const primaryHeading = headingCandidates[0];
  if (!primaryHeading) return;

  const actionLikeHeading = /\\b(add|create|edit|move|review|reassign|request|configure|history|detail|notification|contact|location|role|user|client|candidate|pipeline|exception)\\b/i.test(primaryHeading);
  const genericRouteTitle = /\\b(workspace|detail|panel)\\b/i.test(routeTitle);
  const routeContainsHeading = normalize(routeTitle).includes(normalize(primaryHeading));
  const headingContainsRoute = normalize(primaryHeading).includes(normalize(routeTitle));
  const meaningfullyDifferentTitle = !routeContainsHeading && !headingContainsRoute;
  const explicitActionTitleRoutes = new Set(["location-form-drawer"]);
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
  const annotate = (control, title, body) => {
    if (!control || control.dataset.route || control.dataset.toast || control.dataset.overlayClose || control.dataset.validateScope) return;
    control.dataset.toastTitle = title;
    control.dataset.toast = body;
  };

  scope.querySelectorAll("button, a[href='javascript:void(0)']").forEach((control) => {
    if (control.closest("form, [data-layout='pagination-controls'], [data-toggle-group]")) return;
    if (
      control.matches("[data-route], [data-toast], [data-overlay-close], [data-reset-toolbar-filters], [data-clear-search-preview], [data-mobile-nav-open], [data-mobile-nav-close], [data-notification-read], [data-duplicate-resolution-confirm], [data-flow-reset], [data-validate-scope], [aria-haspopup='menu']")
    ) return;
    const type = (control.getAttribute("type") || "").toLowerCase();
    if (type === "submit") return;

    const label = getActionLabel(control);
    const icon = control.querySelector(".material-symbols-outlined")?.textContent?.trim().toLowerCase() || "";
    const normalized = (label || icon).replace(/\\s+/g, " ").trim().toLowerCase();
    const insideOverlay = control.closest("[data-overlay-surface]");

    if (routeId === "requisition-intake" && normalized === "cancel") {
      control.dataset.route = "requisition-list.html";
      return;
    }
    if (routeId === "requisition-intake" && /create requisition/.test(normalized)) {
      control.dataset.validateScope = "#requisition-form";
      control.dataset.successTitle = "Form state is valid";
      control.dataset.successText = "This screen now has a consistent client-side guardrail.";
      return;
    }

    if (!normalized && /\\bh-2\\b|rounded-full/.test(String(control.className || ""))) {
      annotate(control, "Rating updated", "This scoring control is staged for live evaluation data.");
      return;
    }
    if (icon === "more_vert" || /more actions?/.test(normalized)) {
      annotate(control, "Action menu staged", "This row action menu is ready for live workflow options.");
      return;
    }
    if (icon === "filter_list" || /^filter$|filters?|more filters/.test(normalized)) {
      annotate(control, "Filter staged", "This filter control is ready for API-backed table slicing.");
      return;
    }
    if (insideOverlay && /save|submit|confirm|approve|review|move|request|create|add|link/.test(normalized)) {
      control.dataset.overlayAction = "validate";
      return;
    }
    if (/info|help/.test(normalized)) {
      annotate(control, "Help context staged", "This contextual helper is ready for inline guidance content.");
      return;
    }
    if (/active only/.test(normalized) || /^(all|owner changes|contributor changes|strong yes|yes|no|strong no)$/.test(normalized)) {
      annotate(control, "Selection updated", `${label || "This option"} is now staged as the active choice.`);
      return;
    }
    if (/^(client|location|owner|role|status|priority|region|type)\\b/.test(normalized)) {
      annotate(control, "Filter staged", `${label || "This filter"} is ready for live filtering.`);
      return;
    }
    if (/retry|select all|view \\d+ more|add note|manage|cancel|invite|continue|save|submit|confirm|create|add|send|schedule|update|link|move|request|approve|review|draft/.test(normalized)) {
      annotate(control, "Interaction staged", `${label || "This action"} is ready for backend workflow wiring.`);
    }
  });
}

function injectWorkflowBrief() {
  const routeId = document.body?.dataset.routeId || "";
  const config = WORKFLOW_BRIEFS[routeId];
  const host = document.querySelector("[data-demo-validate]");
  if (!config || !host || host.querySelector(".workflow-brief")) return;

  const brief = document.createElement("section");
  brief.className = "workflow-brief";
  brief.innerHTML = `
    <div class="workflow-brief-header">
      <div>
        <div class="workflow-brief-title">${escapeHtml(config.title)}</div>
        <p class="workflow-brief-copy">${escapeHtml(config.copy)}</p>
      </div>
      <div class="workflow-brief-badge">
        <span class="material-symbols-outlined text-[16px]">insights</span>
        ${escapeHtml(config.badge)}
      </div>
    </div>
    <ul class="workflow-brief-list">
      ${config.bullets
        .map(
          (item) => `
            <li>
              <span class="material-symbols-outlined">arrow_forward</span>
              <span>${escapeHtml(item)}</span>
            </li>
          `,
        )
        .join("")}
    </ul>
  `;
  placeAfterLeadHeading(host, brief);
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
  const item = button.closest(".group, .relative, .flex");
  if (!item) return;
  item.classList.add("notification-read");
  button.setAttribute("disabled", "disabled");
  showToast("Notification updated", "This alert is now marked as read in the frontend workflow.");
}

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
        headerTitle.textContent = fileLabel.replace(/\\.[^.]+$/, "").slice(0, 22) || fileLabel;
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
        const label = (labelNode?.textContent || "Follow-up").replace(/\\s+/g, " ").trim();
        showToast(
          checkbox.checked ? "Follow-up completed" : "Follow-up reopened",
          checkbox.checked
            ? `${label} is marked done for this workspace session.`
            : `${label} is back in your active follow-up list.`,
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
      .find((node) => /REQ-\\d{8}/.test(node.textContent || ""))
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
        link.dataset.toastTitle = "Documentation handoff";
        link.dataset.toast = "This knowledge entry point is ready to connect to internal runbooks or a searchable help center.";
      }
      if (/system health status/.test(label)) {
        link.dataset.toastTitle = "Health status";
        link.dataset.toast = "This status surface is staged for live operational telemetry, incident messaging, and escalation updates.";
      }
    });
  }

  if (routeId === "not-found") {
    document.querySelectorAll("a[href='javascript:void(0)']").forEach((link) => {
      const label = getActionLabel(link);
      if (/documentation registry/.test(label)) {
        link.dataset.toastTitle = "Documentation registry";
        link.dataset.toast = "This recovery link is ready for internal docs, release notes, and route ownership guidance.";
      }
      if (/platform status dashboard/.test(label)) {
        link.dataset.toastTitle = "Platform status";
        link.dataset.toast = "This recovery link is staged for live incident status, maintenance notices, and service health telemetry.";
      }
    });
  }
}

function setupApprovalsWorkspace() {
  if (document.body?.dataset.routeId !== "approvals-inbox") return;
  const table = document.querySelector("table");
  const rows = Array.from(document.querySelectorAll("tbody tr")).filter(
    (row) => !row.classList.contains("table-empty-state-row") && !row.querySelector(".ro-empty"),
  );
  if (!table || rows.length === 0 || document.querySelector("[data-approval-summary]")) return;

  const summary = document.createElement("section");
  summary.className = "decision-summary";
  summary.setAttribute("data-approval-summary", "true");
  summary.innerHTML = `
    <div class="decision-summary-header">
      <div>
        <div class="decision-summary-title">Current review focus</div>
        <p class="decision-summary-copy" data-approval-summary-copy>Pick an approval row to keep the decision context visible before you open the drawer.</p>
      </div>
      <div class="decision-summary-actions">
        <button type="button" data-route="approval-review-drawer.html">Open review drawer</button>
      </div>
    </div>
    <div class="decision-summary-meta" data-approval-summary-meta></div>
  `;

  table.parentElement.parentElement.insertBefore(summary, table.parentElement);
  const copyNode = summary.querySelector("[data-approval-summary-copy]");
  const metaNode = summary.querySelector("[data-approval-summary-meta]");

  const activateRow = (row) => {
    rows.forEach((item) => item.classList.remove("is-active-record"));
    row.classList.add("is-active-record");
    const cells = row.querySelectorAll("td");
    const sla = cells[0]?.textContent?.replace(/\\s+/g, " ").trim() || "Standard";
    const requestType = cells[1]?.textContent?.replace(/\\s+/g, " ").trim() || "Approval";
    const relatedRecord = cells[2]?.textContent?.replace(/\\s+/g, " ").trim() || "Record unavailable";
    const requester = cells[3]?.textContent?.replace(/\\s+/g, " ").trim() || "Requester unavailable";
    if (copyNode) {
      copyNode.textContent = `${requestType} is active. Review ${relatedRecord} and ${requester} together before you decide.`;
    }
    if (metaNode) {
      metaNode.innerHTML = `
        <span class="decision-summary-pill"><span class="material-symbols-outlined text-[14px]">priority_high</span>${sla}</span>
        <span class="decision-summary-pill"><span class="material-symbols-outlined text-[14px]">fact_check</span>${requestType}</span>
        <span class="decision-summary-pill"><span class="material-symbols-outlined text-[14px]">link</span>${relatedRecord}</span>
      `;
    }
  };

  rows.forEach((row) => {
    row.addEventListener("click", (event) => {
      if (event.target.closest("button, a, select, input")) return;
      activateRow(row);
    });
  });

  activateRow(rows[0]);
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
    const label = selected.closest("label")?.textContent?.replace(/\\s+/g, " ").trim() || "Resolution selected";
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
  if (host.matches?.("[data-overlay-surface='true']")) {
    host.prepend(summary);
  } else {
    placeAfterLeadHeading(host, summary);
  }
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

function injectOverlayBrief() {
  const routeId = document.body?.dataset.routeId || "";
  const config = OVERLAY_BRIEFS[routeId];
  const host = document.querySelector("[data-overlay-surface='true']");
  if (!config || !host || host.querySelector("[data-overlay-brief='true']")) return;

  const brief = document.createElement("section");
  brief.className = "decision-summary";
  brief.setAttribute("data-overlay-brief", "true");
  brief.innerHTML = `
    <div class="decision-summary-header">
      <div>
        <div class="decision-summary-title">${config.title}</div>
        <p class="decision-summary-copy">${config.copy}</p>
      </div>
    </div>
    <div class="decision-summary-meta">
      ${config.pills
        .map(
          (pill) => `
            <span class="decision-summary-pill">
              <span class="material-symbols-outlined text-[14px]">insights</span>
              ${pill}
            </span>
          `,
        )
        .join("")}
    </div>
  `;

  const contentHost =
    host.querySelector(".flex-1.overflow-y-auto") ||
    host.querySelector(".p-gutter.overflow-y-auto") ||
    host.querySelector(".p-inset-card.flex.flex-col") ||
    host.querySelector(".p-gutter.flex.flex-col") ||
    host;
  contentHost.prepend(brief);
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
    changeButton.dataset.toastTitle = "Approver routing preserved";
    changeButton.dataset.toast = "The approver picker can be wired here without changing the dialog structure.";
  }

  textarea.addEventListener("input", sync);
  typeSelect.addEventListener("change", sync);
  sync();
}

const DEFAULT_PIPELINE_FLOW = ["Sourced", "Screening", "Technical Interview", "Executive Review", "Offer"];

function setupOverlayWorkflows() {
  injectOverlayBrief();
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
  if (toolbar.querySelector("table, form, textarea")) return;
  const controls = toolbar.querySelectorAll("input:not([type='hidden']), select, button, a[href]");
  if (controls.length < 2 && !toolbar.querySelector("input[placeholder*='Search'], select")) return;
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
    const toolbarActions = topSection?.querySelector(":scope > div.flex.gap-2");
    const filterBar = topSection?.querySelector(":scope > div.flex.gap-3");
    const boardScroll = topSection?.nextElementSibling;
    const title = topSection?.querySelector("h2");
    if (title && !topSection.querySelector(".pipeline-toolbar-subtitle")) {
      const subtitle = document.createElement("p");
      subtitle.className = "pipeline-toolbar-subtitle";
      subtitle.textContent = "Track candidates across active stages and keep movement actions close to the board.";
      title.insertAdjacentElement("afterend", subtitle);
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
    if (candidate === titlebar || candidate.closest("[data-overlay-surface='true'], .overlay-host, table, form, [data-layout='page-titlebar']")) return;
    if (candidate.parentElement?.closest("[data-layout='filter-toolbar']")) return;
    if (candidate.querySelector("h1, h2, h3")) return;
    const rect = candidate.getBoundingClientRect();
    if (rect.height <= 0 || rect.height > 180) return;
    const hasFilterControl = candidate.querySelector("input[placeholder*='Search'], select");
    const directButtons = Array.from(candidate.children).filter((child) => child.matches?.("button, a") || child.querySelector?.(":scope > button, :scope > a"));
    if (!hasFilterControl && candidate.parentElement?.querySelector(":scope > div h1, :scope > div h2, :scope > div h3")) return;
    if (hasFilterControl || directButtons.length >= 2) {
      markFilterToolbar(candidate);
    }
  });

  const sidebarCta = document.querySelector(".sidebar-cta-link");
  const normalizeCta = (text) => (text || "").replace(/\\s+/g, " ").trim().toLowerCase().replace(/^[a-z0-9_]+ /, "");
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
    { pattern: /step\\s*1|define|strategy|plan/i, href: "product-tour-plan-strategy.html" },
    { pattern: /step\\s*2|ownership|accountability|assign/i, href: "product-tour-assign-ownership.html" },
    { pattern: /step\\s*3|candidate movement|move candidates|pipeline/i, href: "product-tour-move-candidates.html" },
    { pattern: /step\\s*4|exception|governance|resolve/i, href: "product-tour-resolve-exceptions.html" },
    { pattern: /step\\s*5|report|progress|data/i, href: "product-tour-report-progress.html" },
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
    if (/book demo/i.test(label)) {
      link.setAttribute("href", "javascript:void(0)");
      link.dataset.toastTitle = "Demo request staged";
      link.dataset.toast = "This public CTA is ready for CRM or calendar scheduling integration.";
    }
    if (/start free trial|get started/i.test(label)) {
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
    if (/start free trial|get started/i.test(label)) {
      button.dataset.route = onboardingWelcomeHref;
    } else if (/book demo/i.test(label)) {
      button.dataset.toastTitle = "Demo request staged";
      button.dataset.toast = "This public CTA is ready for CRM or calendar scheduling integration.";
    }
  });

  document.querySelectorAll(".landing-canvas :is(article, section, div)").forEach((node) => {
    if (node.querySelector("a, button") || node.closest("a, button")) return;
    const text = (node.textContent || "").replace(/\\s+/g, " ").trim();
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
        button.addEventListener("click", () => showToast("Location staged", "This location is ready for onboarding setup persistence."));
      }
      if (/import locations/i.test(label)) {
        button.addEventListener("click", () => showToast("Import staged", "Bulk location import is ready for file upload wiring."));
      }
      if (/edit/.test(label)) {
        button.dataset.toastTitle = "Location edit staged";
        button.dataset.toast = "The selected onboarding location is ready for edit-mode wiring.";
      }
      if (/delete/.test(label)) {
        button.dataset.toastTitle = "Location removal staged";
        button.dataset.toast = "The selected onboarding location can be removed once persistence is connected.";
      }
    });
  }

  if (routeId === "onboarding-pipeline-stage-builder") {
    Array.from(document.querySelectorAll("button")).forEach((button) => {
      const label = getActionLabel(button);
      if (/save pipeline/i.test(label)) {
        button.dataset.toastTitle = "Pipeline saved";
        button.dataset.toast = "The onboarding pipeline draft is staged and ready to continue.";
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
        button.dataset.toastTitle = "Integration staged";
        button.dataset.toast = "This integration action is ready for OAuth or API-key setup.";
      }
    });
  }
}

function runLoginDemo(form) {
  if (window.RecruitOpsLive && typeof window.RecruitOpsLive.handleLogin === "function") {
    window.RecruitOpsLive.handleLogin(form);
    return;
  }
  if (!validateForm(form)) {
    return;
  }

  const overlay = document.getElementById("loading-overlay");
  const submitBtn = document.getElementById("submit-btn");
  const passwordInput = document.getElementById("password");
  const states = ["invalid", "inactive", "success"];
  const stateIndex = Number(form.dataset.loginStateIndex || "0");
  const nextState = states[stateIndex % states.length];
  form.dataset.loginStateIndex = String(stateIndex + 1);
  resetAlertBanner(document.getElementById("alert-banner"));

  if (overlay) {
    overlay.classList.remove("hidden");
  }

  if (submitBtn) {
    submitBtn.disabled = true;
  }

  window.setTimeout(() => {
    if (overlay) {
      overlay.classList.add("hidden");
    }

    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<span>Authenticate</span><span class="material-symbols-outlined text-[20px]">arrow_forward</span>';
    }

    if (nextState === "invalid") {
      showAlertState({
        bgClass: "bg-danger-bg",
        textClass: "text-danger-text",
        borderClass: "border-[#e4b6b0]",
        icon: "error",
        title: "Authentication Failed",
        message: "Invalid corporate email or password. Please try again.",
      });
      if (passwordInput) {
        passwordInput.value = "";
        passwordInput.focus();
      }
      return;
    }

    if (nextState === "inactive") {
      showAlertState({
        bgClass: "bg-warning-bg",
        textClass: "text-warning-text",
        borderClass: "border-[#dbc1a3]",
        icon: "warning",
        title: "Account Inactive",
        message: "Your enterprise account is temporarily suspended. Contact IT support to regain access.",
      });
      return;
    }

    showAlertState({
      bgClass: "bg-success-bg",
      textClass: "text-success-text",
      borderClass: "border-[#c5dac9]",
      icon: "check_circle",
      title: "Authenticated",
      message: "Secure workspace verified. Redirecting to the operational dashboard.",
    });

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="material-symbols-outlined animate-spin-slow text-[20px]">sync</span><span>Connecting...</span>';
    }

    showToast("Authentication succeeded", "The frontend lifecycle is ready for real auth wiring.");
    window.setTimeout(() => {
      window.location.href = "role-dashboard.html";
    }, 900);
  }, 900);
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
  setupLogoutLinks();
  setupMarketingInteractions();
  setupOnboardingInteractions();
  injectWorkflowBrief();
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
  setupAdvancedFilterPanels(document);
  setupSortableTables(document);
  setupRecordLinkPolish();
  setupGenericActionAnnotations(document);
  setupSidebarNav();
  setupRoutePrefetcher();
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

  document.querySelectorAll("[data-toggle-group]").forEach((group) => {
    group.addEventListener("click", (event) => {
      const button = event.target.closest("button");
      if (!button || !group.contains(button)) return;
      toggleActiveWithin(group, button);
      const label = (button.textContent || "").trim();
      const lensResult = applyTableLens(group, button);
      if (label) {
        const suffix = lensResult
          ? ` Showing ${lensResult.visibleCount} of ${lensResult.totalCount} records.`
          : "";
        showToast("View updated", `${label} is now the active lens for this workspace.${suffix}`);
      }
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
      if (validateForm(form)) {
        if (window.RecruitOpsLive && window.RecruitOpsLive.handleFormSubmit && window.RecruitOpsLive.handleFormSubmit(form)) {
          return;
        }
        showToast("Form state is valid", "This screen now has a consistent client-side guardrail.");
      }
    });
  });

  document.addEventListener("click", (event) => {
    const dismissTarget = event.target.closest("[data-overlay-close]");
    if (dismissTarget && closeHref && document.body.dataset.overlayPage === "true") {
      event.preventDefault();
      window.location.href = closeHref;
      return;
    }

    const button = event.target.closest("button, a");
    if (!button) {
      closeOpenMenus();
      return;
    }
    if (!button.closest(".menu-open")) {
      closeOpenMenus();
    }

    if (mobileDialog?.open && button.closest("#mobile-nav a[href]")) {
      closeMobileNav(mobileDialog);
    }

    if (button.dataset.route) {
      event.preventDefault();
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
        showToast("Reference action captured", "This placeholder action has been preserved safely and is ready for API or workflow wiring.");
        return;
      }
      const internalRoute = normalizeInternalRoute(href);
      if (internalRoute) {
        event.preventDefault();
        navigateToRoute(href);
        return;
      }
    }

    const contextualRoute = resolveContextualRoute(button);
    if (contextualRoute) {
      event.preventDefault();
      navigateToRoute(contextualRoute);
      return;
    }

    if (button.matches("[data-toast]")) {
      event.preventDefault();
          showToast(button.dataset.toastTitle || "Saved for later", button.dataset.toast || "");
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
      showToast("Preview cleared", "The table is back to its default state and ready for another search scenario.");
      return;
    }

    if (button.matches("[data-validate-scope]")) {
      event.preventDefault();
      const scope = document.querySelector(button.dataset.validateScope);
      if (!scope) return;
      if (validateScope(scope)) {
        showToast(button.dataset.successTitle || "Looks good", button.dataset.successText || "This UI flow is ready for API wiring.");
      }
      return;
    }

    const insideOverlay = button.closest("[data-overlay-surface]");
    if (insideOverlay) {
      const label = getActionLabel(button);
      if (button.matches("[data-overlay-close]") || /close|cancel|back/.test(label)) {
        if (closeHref) {
          event.preventDefault();
          window.location.href = closeHref;
          return;
        }
      }
      if (/save|submit|confirm|approve|review|move|request|create|add|link/.test(label)) {
        event.preventDefault();
        if (validateScope(insideOverlay)) {
          showToast("Interaction validated", "The surface is ready to be connected to live API actions.");
        }
        return;
      }
    }

    if (button.closest("[data-demo-validate]") && button.tagName === "BUTTON") {
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
        showToast("Resolution staged", `${button.dataset.duplicateResolutionLabel || "The selected resolution"} is ready for API-backed confirmation.`);
        return;
      }
      if (button.closest("form")) {
        return;
      }
      const label = getActionLabel(button);
      if (/open record actions|edit record|open details|preview record/.test(label)) {
        event.preventDefault();
        showToast("Action menu staged", `${button.closest("tr")?.dataset.rowSummary || "This record"} is ready for detailed workflow actions.`);
        return;
      }
      if (!/save|submit|create|add|authenticate|request|approve|move|continue|review/.test(label)) {
        return;
      }
      event.preventDefault();
      const scope = button.closest("[data-demo-validate]");
      if (validateScope(scope)) {
            showToast("Form state is valid", "This screen now has a consistent client-side guardrail.");
          }
          return;
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
          closeHref &&
          document.body.dataset.overlayPage === "true" &&
          !isEditableTarget(event.target)
        ) {
          window.location.href = closeHref;
          return;
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
        if (event.key === "Tab" && overlaySurface && document.body.dataset.overlayPage === "true") {
          trapFocusWithin(event, overlaySurface);
        }
      });

      const searchInputs = document.querySelectorAll(".topbar-search input, input[placeholder*='Search']");
      searchInputs.forEach((input) => {
        if (!supportsSharedSearchPreview(input)) return;
        input.addEventListener("keydown", (event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            const term = input.value.trim();
            if (!term) {
              const tableSurface = getLinkedTableSurface(input);
              clearTableSearchPreview(tableSurface?.querySelector("table"));
              showToast("Search is empty", "Add a term to test the routed search state.");
              return;
            }
            if (term.length < 2) {
              showToast("Search needs more detail", "Use at least 2 characters so the preview behaves like a realistic API-backed query.");
              return;
            }
            const preview = setTableSearchPreview(getLinkedTableSurface(input)?.querySelector("table"), term);
            showToast(preview.title, preview.body);
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
    