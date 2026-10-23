/* tour.js — guided product tour (module-wise, permission-gated by nature).
   Loaded only on pages that have a registered module tour (see TOUR_REGISTRY
   below) — add a new module by adding a registry entry and one
   <script src="../shared/tour.js"> tag to that page, nothing else.

   Why this needs no separate RBAC logic: the tour only ever runs on a page
   the signed-in user has already reached, and every app page is already
   gated by the real sidebar/route permission check (see api-client.js's
   SIDEBAR_PERMISSION_MAP and the server's own 403s). A role that can't open
   Role Management, say, never loads this registry's "role-management" entry
   in the first place, so there is nothing to show it and nothing to hide —
   the trigger is naturally scoped "per module, by the permissions given."

   Mechanic: spotlight ring + tooltip card over real on-page elements, with
   Back/Next/Skip and a short finish moment — same interaction approved in
   the mockup (https://claude.ai/artifact/3SY4m4ubYku6KrYkyCnuZT), rebuilt
   here against this app's real design tokens (global.css's --ro-* custom
   properties) instead of invented colors, and against real selectors on
   each page instead of placeholder markup. */
(function () {
  "use strict";

  /* Each entry: steps run in order. A step is either:
       { selector }                      - first element matching selector
       { selector, text }                - first element matching selector
                                            whose own text includes `text`
                                            (case-insensitive); selector
                                            defaults to 'button, a' when text
                                            is given and selector is omitted.
     A step whose element isn't found on the page right now is skipped
     silently (never blocks the rest of the tour) — pages change over time,
     and a missing one-off element shouldn't break the whole walkthrough. */
  var TOUR_REGISTRY = {
    "role-dashboard": {
      label: "Role Dashboard",
      steps: [
        { selector: "[data-role-kpi-strip]", title: "Your daily KPIs",
          body: "Open Requisitions, Active Candidates, Active Applications, and Pending Updates — the four numbers worth checking first thing." },
        { selector: "[data-role-stale-reqs]", title: "Stale Requisitions",
          body: "Roles that have sat open too long without movement get flagged here automatically, so nothing quietly goes cold." },
        { selector: "[data-role-pressure]", title: "Daily Update Pressure",
          body: "A quick read on how much of today's daily-update workload is still outstanding across your team." },
        { text: "View all items in queue", title: "Everything in one inbox",
          body: "This takes you to the full Approvals Inbox — every pending decision in one filterable list." }
      ]
    },
    "requisition-list": {
      label: "Requisitions",
      steps: [
        { selector: '[data-api-field="req_total_open"]', title: "Open requisitions at a glance",
          body: "Total open, critical-priority, and stale (60+ days) counts — computed live from your current list, not a cached number." },
        { text: "Create Requisition", title: "Raise a new requisition",
          body: "Opens the intake form: client, location, pay range, and who owns it." },
        { selector: "table", title: "Your requisition list",
          body: "Click any row to open its detail page. Use the filters above the table to narrow it down by status, priority, or owner." }
      ]
    },
    "candidate-profiles": {
      label: "Candidates",
      steps: [
        { text: "Add Candidate", title: "Add a candidate",
          body: "Manual entry, resume upload, or bulk import — all three land the new profile in this same list." },
        { text: "Export List", title: "Export what you're looking at",
          body: "Exports the candidates currently showing, respecting whatever filters are applied." },
        { selector: "table", title: "Readiness and linkage at a glance",
          body: "Duplicate warnings and requisition links show inline, so you catch them before they become a problem mid-pipeline." }
      ]
    },
    "pipeline-board": {
      label: "Pipeline Board",
      steps: [
        { selector: "table, .pipeline-board, [data-pipeline-board]", title: "Drag candidates across stages",
          body: "Each client can run its own stage names here — this board always reflects whichever list governs the requisition you're viewing." },
        { text: "Manage Stages", title: "Manage Stages",
          body: "Admins and anyone with client.update can edit a client's own hiring-stage list from here, or from the client's own page." },
        { text: "Export", title: "Export the board",
          body: "Pulls the board as it's currently filtered — handy for a status update outside RecruitOps." }
      ]
    },
    "approvals-inbox": {
      label: "Approvals Inbox",
      steps: [
        { selector: '[data-layout="metric-card"]', title: "What's waiting on you",
          body: "Total Pending, Overdue SLA, and Awaiting My Review — the three numbers that tell you whether you're behind." },
        { selector: "table, .workspace-surface", title: "One queue for every request type",
          body: "Offers above threshold, holds, exceptions, and more all land here — approve or decide without hunting across pages." }
      ]
    },
    "user-management": {
      label: "Users",
      steps: [
        { selector: "[data-open-user-dialog]", title: "Invite a teammate",
          body: "Add someone, then set their role and office — that's what actually decides what they can reach." },
        { selector: "[data-user-total]", title: "Everyone at your company",
          body: "Every user here belongs to your company only. Deactivating someone automatically transfers their open work." }
      ]
    },
    "role-management": {
      label: "Roles",
      steps: [
        { selector: "[data-open-role-dialog]", title: "Create a role",
          body: "Give it a name that describes the job — like \"Technical Interviewer\" — then open its Permissions Editor to decide what it can reach." }
      ]
    },
    "role-permissions-editor": {
      label: "Permissions Editor",
      steps: [
        { selector: "#role-description", title: "Which role you're editing",
          body: "The Admin role's toggles are always locked — it can't be edited. For a narrower slice of control-plane access, create a new role instead." },
        { selector: ".matrix-table", title: "Toggle what this role can do",
          body: "Every permission code, grouped by module. Nothing is saved until you click Save Changes." },
        { selector: "#perm-search", title: "Narrow it down",
          body: "Filter to one module at a time — handy once a role holds more than a handful of permissions." }
      ]
    },
    "visibility-rules": {
      label: "Visibility Rules",
      steps: [
        { selector: "[data-visibility-rules]", title: "Field-level access, not page-level",
          body: "This goes one level deeper than role permissions — hiding specific sensitive fields, like margin %, from roles that can still open the page." },
        { selector: "[data-vis-rule-count]", title: "Commercial & Financial Terms",
          body: "Margin %, bill rate, and markup % — check which roles may see each one. An unchecked role never receives the field at all, not even blanked out." }
      ]
    },
    "reports": {
      label: "Reports",
      steps: [
        { selector: '[data-live-report-filter="all"]', title: "Filter by report type",
          body: "Pipeline, Candidates, Performance, Financial — narrow the saved-reports list to what you need." },
        { selector: '[data-route="custom-report-builder.html"]', title: "Build your own",
          body: "Pick a dataset and the fields you want — saved reports here start from a template just like this one." }
      ]
    },
    "tenant-setup": {
      label: "Company Settings",
      steps: [
        { selector: "#company-display-name", title: "Company profile",
          body: "Your display name, legal name, and HQ address — shown across the app and on anything you export." },
        { selector: "[data-offer-approval-settings]", title: "Offer approval threshold",
          body: "Offers above this amount (or above a requisition's own pay range, if it has one) are routed for a second approval." },
        { selector: "#company-stage-list", title: "Your company's default hiring stages",
          body: "Used for internal hiring and any client that hasn't set its own list. Each client can override this from their own page." }
      ]
    },
    "client-directory": {
      label: "Clients",
      steps: [
        { text: "Add Client", title: "Add a client",
          body: "A short form for the company's name, location, and primary contact. New clients start out on your company's default hiring stages." },
        { selector: "table", title: "Every account in one place",
          body: "Owner, industry, and status at a glance. Open any row for that client's requisitions, contacts, and commercial terms." },
        { selector: "[title=\"New Requisition\"]", title: "Raise a req without leaving the list",
          body: "Hover any row to start a new requisition for that client directly from here." }
      ]
    },
    "offer-management": {
      label: "Offers",
      steps: [
        { text: "Create Offer", title: "Send a new offer",
          body: "Captures compensation and routes it for a second approval automatically when it's above your company's threshold." },
        { selector: "table", title: "Track every offer's status",
          body: "Draft, Pending Approval, Sent, Accepted, or Declined, with the date each one moved, so nothing sits unanswered." },
        { text: "Export List", title: "Export what you're viewing",
          body: "Pulls whichever offers are currently showing, respecting any filters you've applied." }
      ]
    },
    "interview-scheduler": {
      label: "Interviews",
      steps: [
        { selector: "h1", title: "Where every interview lives",
          body: "Every scheduled round for your requisitions appears here, updated the moment someone logs feedback." },
        { selector: "[data-interview-list]", title: "Status and feedback, inline",
          body: "Completed, upcoming, or awaiting feedback — each round shows its outcome without opening a separate page." }
      ]
    },
    "daily-review": {
      label: "Daily Review",
      steps: [
        { selector: "[data-route=\"daily-updates-submission.html\"]", title: "Submit today's update",
          body: "Opens the daily update form — what got done today, any blockers, and what's next." },
        { text: "View All", title: "Every follow-up, not just today's",
          body: "Jumps to the full Follow-Ups list, so nothing scheduled for later quietly slips past." }
      ]
    },
    "daily-updates-submission": {
      label: "Submit Update",
      steps: [
        { selector: "#update-summary", title: "Today's summary",
          body: "A short narrative of what happened today — accomplishments, pipeline health, and anything that needs context." },
        { selector: "[data-route-submit=\"true\"]", title: "Submit when ready",
          body: "Save Draft keeps it private until you're ready. Submit Update sends it straight to your manager's review queue." }
      ]
    },
    "follow-ups": {
      label: "Follow-Ups",
      steps: [
        { selector: "[data-route=\"follow-up-form-dialog.html\"]", title: "Log a follow-up",
          body: "Set a reminder — send an assessment, check in with a client, anything that can't be forgotten — with a due date and an owner." },
        { selector: "table", title: "Nothing falls through",
          body: "Overdue items are flagged automatically, so a forgotten follow-up never quietly disappears." }
      ]
    },
    "audit-log-viewer": {
      label: "Audit Log",
      steps: [
        { selector: "#audit-filters", title: "Narrow it down",
          body: "Filter by date, action type, or who did it — handy when you're tracing one specific change." },
        { selector: "table", title: "Every change, who made it, and when",
          body: "Click Details on any row for the full before-and-after of that action." }
      ]
    },
    "data-export-delete-request": {
      label: "Data Export & Delete Requests",
      steps: [
        { selector: "#privacy-export", title: "Export your data",
          body: "Requests a full export of your company's data. It's prepared in the background and you'll get a link once it's ready." },
        { text: "Request deletion", title: "Request deletion",
          body: "Starts the process to permanently delete your company's data. If other admins exist, they're notified before it goes any further." }
      ]
    },
    "portal-accounts": {
      label: "Portal Accounts",
      steps: [
        { selector: "table", title: "Shared sourcing logins, tracked",
          body: "Each shared job-board account shows who owns it, which branch it's tied to, and how much it's been used today." },
        { selector: "#portal-add-btn", title: "Add a shared account",
          body: "Only shown if you can manage portal accounts — set the platform, login, and who owns it." },
        { selector: "[data-slot-account]", title: "Book a usage slot",
          body: "Reserve a time window on a shared account, so two people don't log in and lock each other out." }
      ]
    },
    "stage-bucket-map": {
      label: "Hiring Stages",
      steps: [
        { selector: "#company-stage-list", title: "Your company's default stages",
          body: "Add, rename, or reorder stages here — any client without its own list uses this one." },
        { selector: "table", title: "Keep reports accurate",
          body: "Every stage counts toward one reporting bucket. A stage with no match is flagged here so it never throws off Time to Fill or Placements." }
      ]
    },
    "work-assignment": {
      label: "Work Assignment",
      steps: [
        { text: "Assign Member", title: "Add someone to a req",
          body: "Pick from your available team — their role here (Owner, Reviewer, Coordinator…) decides what they're responsible for on this requisition." },
        { selector: "select", title: "Switch requisitions",
          body: "Everything below reflects whichever requisition is selected here." }
      ]
    },
    "my-profile": {
      label: "My Profile",
      steps: [
        { selector: "#profile-details-form", title: "Your details",
          body: "Name, contact info, and how you appear to teammates across the app." },
        { selector: "#profile-password-form", title: "Change your password",
          body: "Update it any time — you'll need your current password to confirm." },
        { selector: "a[href=\"mfa-enroll.html\"]", title: "Turn on two-factor",
          body: "Adds a second step at login for extra protection on your account." }
      ]
    }
  };

  function currentRouteId() {
    return document.body ? document.body.dataset.routeId || "" : "";
  }

  function sessionKey() {
    try {
      var session = (window.RecruitOpsLive && window.RecruitOpsLive.session) ||
        JSON.parse(localStorage.getItem("recruitops-session") || "null");
      return (session && (session.email || session.user_name)) || "anon";
    } catch (e) {
      return "anon";
    }
  }

  function seenStorageKey(moduleKey) {
    return "ro-tour-seen:" + sessionKey() + ":" + moduleKey;
  }

  function hasSeen(moduleKey) {
    try { return localStorage.getItem(seenStorageKey(moduleKey)) === "1"; } catch (e) { return false; }
  }

  function markSeen(moduleKey) {
    try { localStorage.setItem(seenStorageKey(moduleKey), "1"); } catch (e) { /* ignore */ }
  }

  function findTarget(step) {
    if (step.text) {
      var nodes = document.querySelectorAll(step.selector || "button, a");
      var needle = step.text.toLowerCase();
      for (var i = 0; i < nodes.length; i++) {
        var text = (nodes[i].textContent || "").replace(/\s+/g, " ").trim().toLowerCase();
        if (text.indexOf(needle) !== -1) return nodes[i];
      }
      return null;
    }
    try { return document.querySelector(step.selector); } catch (e) { return null; }
  }


  function injectStyles() {
    if (document.getElementById("ro-tour-styles")) return;
    var style = document.createElement("style");
    style.id = "ro-tour-styles";
    style.textContent = [
      "#ro-tour-overlay{position:fixed;inset:0;z-index:9999;display:none;pointer-events:none;}",
      "#ro-tour-overlay.on{display:block;pointer-events:auto;background:rgba(20,18,14,0.45);}",
      "#ro-tour-ring{position:absolute;border-radius:10px;box-shadow:0 0 0 4px var(--ro-focus,rgba(63,93,67,.2)),0 0 0 2000px rgba(20,18,14,0.45);transition:top .25s ease,left .25s ease,width .25s ease,height .25s ease;pointer-events:none;}",
      "#ro-tour-card{position:absolute;width:300px;background:var(--ro-surface,#fff);border:1px solid var(--ro-border,#e2e0da);border-radius:12px;box-shadow:var(--ro-elevation-overlay,0 24px 48px rgba(0,0,0,.25));padding:16px;transition:top .25s ease,left .25s ease;}",
      "#ro-tour-skip{position:absolute;top:8px;right:10px;background:none;border:none;font-size:18px;line-height:1;color:var(--ro-muted,#726f66);cursor:pointer;}",
      ".ro-tour-tag{display:inline-block;font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--ro-primary,#3F5D43);background:var(--ro-focus,rgba(63,93,67,.12));border-radius:999px;padding:2px 8px;margin-bottom:8px;}",
      "#ro-tour-title{margin:0 0 6px;font-size:15px;font-weight:700;color:var(--ro-text,#2b2823);}",
      "#ro-tour-body{margin:0 0 14px;font-size:13px;line-height:1.5;color:var(--ro-muted,#726f66);}",
      ".ro-tour-foot{display:flex;align-items:center;justify-content:space-between;gap:10px;}",
      ".ro-tour-dots{display:flex;gap:5px;}",
      ".ro-tour-dots span{width:6px;height:6px;border-radius:50%;background:var(--ro-border,#e2e0da);}",
      ".ro-tour-dots span.cur{background:var(--ro-primary,#3F5D43);width:14px;border-radius:4px;}",
      ".ro-tour-dots span.done{background:var(--ro-primary-hover,#2E4530);}",
      ".ro-tour-actions{display:flex;gap:8px;}",
      ".ro-tour-btn{font-size:12px;font-weight:600;border-radius:8px;padding:6px 12px;cursor:pointer;border:1px solid transparent;}",
      ".ro-tour-btn-primary{background:var(--ro-primary,#3F5D43);color:#fff;}",
      ".ro-tour-btn-primary:hover{background:var(--ro-primary-hover,#2E4530);}",
      ".ro-tour-btn-ghost{background:transparent;color:var(--ro-muted,#726f66);border-color:var(--ro-border,#e2e0da);}",
      ".ro-tour-btn-ghost:disabled{opacity:.4;cursor:default;}",
      "#ro-tour-finale{position:fixed;inset:0;display:none;align-items:center;justify-content:center;background:rgba(20,18,14,0.45);z-index:10000;}",
      "#ro-tour-finale.on{display:flex;}",
      ".ro-tour-finale-card{background:var(--ro-surface,#fff);border-radius:14px;padding:28px;max-width:320px;text-align:center;box-shadow:var(--ro-elevation-overlay,0 24px 48px rgba(0,0,0,.25));}",
      ".ro-tour-finale-emoji{width:40px;height:40px;line-height:40px;border-radius:50%;background:var(--ro-primary,#3F5D43);color:#fff;font-size:18px;margin:0 auto 12px;}",
      ".ro-tour-finale-card h4{margin:0 0 8px;font-size:16px;color:var(--ro-text,#2b2823);}",
      ".ro-tour-finale-card p{margin:0 0 16px;font-size:13px;color:var(--ro-muted,#726f66);line-height:1.5;}"
    ].join("");
    document.head.appendChild(style);
  }

  var state = { moduleKey: null, steps: [], index: 0 };
  var dom = null;

  function buildDom() {
    if (dom) return dom;
    var overlay = document.createElement("div");
    overlay.id = "ro-tour-overlay";
    overlay.innerHTML =
      '<div id="ro-tour-ring"></div>' +
      '<div id="ro-tour-card" role="dialog" aria-live="polite">' +
        '<button type="button" id="ro-tour-skip" aria-label="Skip tour">&times;</button>' +
        '<div class="ro-tour-tag" id="ro-tour-tag"></div>' +
        '<h4 id="ro-tour-title"></h4>' +
        '<p id="ro-tour-body"></p>' +
        '<div class="ro-tour-foot">' +
          '<div class="ro-tour-dots" id="ro-tour-dots"></div>' +
          '<div class="ro-tour-actions">' +
            '<button type="button" class="ro-tour-btn ro-tour-btn-ghost" id="ro-tour-back">Back</button>' +
            '<button type="button" class="ro-tour-btn ro-tour-btn-primary" id="ro-tour-next">Next</button>' +
          '</div>' +
        '</div>' +
      '</div>' +
      '<div id="ro-tour-finale">' +
        '<div class="ro-tour-finale-card">' +
          '<div class="ro-tour-finale-emoji">&#10003;</div>' +
          '<h4>You\'re set up</h4>' +
          '<p id="ro-tour-finale-copy"></p>' +
          '<button type="button" class="ro-tour-btn ro-tour-btn-primary" id="ro-tour-finale-close">Done</button>' +
        '</div>' +
      '</div>';
        injectStyles();
    document.body.appendChild(overlay);
    dom = {
      overlay: overlay,
      ring: overlay.querySelector("#ro-tour-ring"),
      card: overlay.querySelector("#ro-tour-card"),
      tag: overlay.querySelector("#ro-tour-tag"),
      title: overlay.querySelector("#ro-tour-title"),
      body: overlay.querySelector("#ro-tour-body"),
      dots: overlay.querySelector("#ro-tour-dots"),
      back: overlay.querySelector("#ro-tour-back"),
      next: overlay.querySelector("#ro-tour-next"),
      skip: overlay.querySelector("#ro-tour-skip"),
      finale: overlay.querySelector("#ro-tour-finale"),
      finaleCopy: overlay.querySelector("#ro-tour-finale-copy"),
      finaleClose: overlay.querySelector("#ro-tour-finale-close")
    };
    dom.skip.addEventListener("click", function () { endTour(false); });
    dom.back.addEventListener("click", function () { if (state.index > 0) { state.index--; renderStep(); } });
    dom.next.addEventListener("click", function () {
      if (state.index < state.steps.length - 1) { state.index++; renderStep(); } else { endTour(true); }
    });
    dom.finaleClose.addEventListener("click", function () { dom.finale.classList.remove("on"); });
    window.addEventListener("resize", function () { if (state.steps.length) placeAt(state.steps[state.index]); });
    window.addEventListener("scroll", function () { if (state.steps.length) placeAt(state.steps[state.index]); }, true);
    return dom;
  }

  function placeAt(step) {
    var el = findTarget(step);
    if (!el) { nextOrSkip(); return; }
    el.scrollIntoView({ block: "center", behavior: "smooth" });
    var r = el.getBoundingClientRect();
    dom.ring.style.top = (window.scrollY + r.top - 5) + "px";
    dom.ring.style.left = (window.scrollX + r.left - 6) + "px";
    dom.ring.style.width = (r.width + 12) + "px";
    dom.ring.style.height = (r.height + 10) + "px";
    var cardTop = window.scrollY + r.bottom + 14;
    var cardLeft = window.scrollX + r.left;
    if (cardLeft + 300 > window.innerWidth - 20) cardLeft = Math.max(16, window.innerWidth - 320);
    if (cardTop + 180 > window.scrollY + window.innerHeight) cardTop = window.scrollY + r.top - 6;
    dom.card.style.top = cardTop + "px";
    dom.card.style.left = cardLeft + "px";
  }

  function nextOrSkip() {
    if (state.index < state.steps.length - 1) { state.index++; renderStep(); } else { endTour(true); }
  }

  function renderDots() {
    dom.dots.innerHTML = state.steps.map(function (_, i) {
      var cls = i < state.index ? "done" : (i === state.index ? "cur" : "");
      return '<span class="' + cls + '"></span>';
    }).join("");
  }

  function renderStep() {
    var step = state.steps[state.index];
    var entry = TOUR_REGISTRY[state.moduleKey];
    dom.tag.textContent = entry.label;
    dom.title.textContent = step.title;
    dom.body.textContent = step.body;
    dom.back.disabled = state.index === 0;
    dom.next.textContent = state.index === state.steps.length - 1 ? "Finish" : "Next";
    renderDots();
    placeAt(step);
  }

  function startTour(moduleKey) {
    var entry = TOUR_REGISTRY[moduleKey];
    if (!entry || !entry.steps.length) return;
    buildDom();
    state.moduleKey = moduleKey;
    state.steps = entry.steps.filter(function (s) { return !!findTarget(s); });
    if (!state.steps.length) return;
    state.index = 0;
    dom.overlay.classList.add("on");
    renderStep();
  }

  function endTour(showFinale) {
    if (!dom) return;
    dom.overlay.classList.remove("on");
    if (state.moduleKey) markSeen(state.moduleKey);
    if (showFinale) {
      dom.finaleCopy.textContent =
        "You've seen the highlights of " + (TOUR_REGISTRY[state.moduleKey] || {}).label + ". Replay it anytime from the tour button in the top bar.";
      dom.finale.classList.add("on");
    }
  }

  function injectReplayButton(moduleKey) {
    var actionGroup = document.querySelector(".app-topbar .flex.items-center.gap-2");
    if (!actionGroup || actionGroup.querySelector("[data-tour-replay]")) return;
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "topbar-action rounded-full border border-border bg-surface p-2 text-on-surface";
    btn.setAttribute("data-tour-replay", moduleKey);
    btn.setAttribute("aria-label", "Replay guided tour for this page");
    btn.setAttribute("title", "Replay guided tour");
    btn.innerHTML = '<span class="material-symbols-outlined text-[18px]">school</span>';
    btn.addEventListener("click", function () { startTour(moduleKey); });
    actionGroup.insertBefore(btn, actionGroup.firstChild);
  }

  function maybeAutoStart() {
    var moduleKey = currentRouteId();
    if (!TOUR_REGISTRY[moduleKey]) return;
    injectReplayButton(moduleKey);
    if (hasSeen(moduleKey)) return;
    window.requestAnimationFrame(function () {
      window.setTimeout(function () { startTour(moduleKey); }, 150);
    });
  }

  window.RoTour = {
    maybeAutoStart: maybeAutoStart,
    replay: function (moduleKey) { startTour(moduleKey || currentRouteId()); },
    registry: TOUR_REGISTRY
  };
})();
