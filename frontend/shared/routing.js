/* ═══════════════════════════════════════════════════════════════
   ROUTING — Auto-extracted from app.js
   ═══════════════════════════════════════════════════════════════ */

function getActionLabel(element) {
  if (!element) return "";
  const iconNodes = Array.from(element.querySelectorAll(".material-symbols-outlined"));
  let text = (element.textContent || "").replace(/\s+/g, " ").trim().toLowerCase();
  iconNodes.forEach((node) => {
    const icon = (node.textContent || "").replace(/\s+/g, " ").trim().toLowerCase();
    if (icon) text = text.replace(icon, " ");
  });
  text = text.replace(/\s+/g, " ").trim();
  const semanticLabel = (element.getAttribute("aria-label") || element.getAttribute("title") || "").trim().toLowerCase();
  return text || semanticLabel;
}


function normalizeInternalRoute(rawHref) {
  if (!rawHref) return "";
  try {
    const url = new URL(rawHref, window.location.href);
    const filename = url.pathname.split("/").pop() || "";
    return /\.html$/i.test(filename) ? filename : "";
  } catch (error) {
    const filename = String(rawHref).split(/[?#]/)[0].split("/").pop() || "";
    return /\.html$/i.test(filename) ? filename : "";
  }
}


function isRootIndexPath(pathname) {
  const path = String(pathname || "");
  if (path.includes("/pages/")) return false;
  return path === "/" || path.endsWith("/") || /\/index\.html$/i.test(path);
}


function getCurrentRouteFile() {
  const routeId = document.body?.dataset.routeId || "";
  if (routeId) {
    return `${routeId}.html`;
  }
  return normalizeInternalRoute(window.location.pathname);
}


function buildRouteHref(rawHref) {
  const routeFile = normalizeInternalRoute(rawHref);
  if (!routeFile) return rawHref;
  const target = new URL(rawHref, window.location.href);
  const currentPageIsRootIndex = isRootIndexPath(window.location.pathname);
  const targetIsRootIndex = routeFile.toLowerCase() === "index.html";
  if (OVERLAY_ROUTE_FILES.has(routeFile)) {
    const currentFile = getCurrentRouteFile();
    const currentKind = document.body?.dataset.routeKind || "";
    if (currentFile && currentKind !== "overlay") {
      target.searchParams.set("returnTo", currentFile);
    }
  }
  const routePath = targetIsRootIndex
    ? (currentPageIsRootIndex ? "index.html" : "../index.html")
    : (currentPageIsRootIndex ? `pages/${routeFile}` : routeFile);
  return `${routePath}${target.search}${target.hash}`;
}


function navigateToRoute(rawHref) {
  const routeFile = normalizeInternalRoute(rawHref);
  const currentKind = document.body?.dataset.routeKind || "";
  const alreadyOverlayPage = document.body?.dataset.overlayPage === "true" || currentKind === "overlay";
  if (routeFile && typeof OVERLAY_ROUTE_FILES !== "undefined" && OVERLAY_ROUTE_FILES.has(routeFile) && !alreadyOverlayPage) {
    openInPageOverlay(rawHref);
    return;
  }
  window.location.href = buildRouteHref(rawHref);
}


function inPageOverlayRoot() {
  return document.getElementById("ro-inpage-overlay");
}


function closeInPageOverlay(opts = {}) {
  const root = inPageOverlayRoot();
  if (!root) return false;
  const restoreSelector = root.dataset.restoreFocus;
  root.remove();
  document.body.classList.remove("is-inpage-overlay");
  if (opts.refresh && window.RecruitOpsLive?.reloadCurrentPage) {
    Promise.resolve(window.RecruitOpsLive.reloadCurrentPage()).catch(() => {});
  }
  if (!opts.silent && restoreSelector) {
    const restore = document.querySelector(restoreSelector);
    if (restore instanceof HTMLElement) restore.focus();
  }
  return true;
}


async function openInPageOverlay(rawHref) {
  const routeFile = normalizeInternalRoute(rawHref);
  if (!routeFile) {
    window.location.href = buildRouteHref(rawHref);
    return;
  }
  const target = new URL(rawHref, window.location.href);
  const overlayRoute = routeFile.replace(/\.html$/i, "");
  const fetchHref = buildRouteHref(rawHref);
  const active = document.activeElement;
  if (active instanceof HTMLElement) {
    if (!active.id) active.dataset.overlayReturnFocus = "true";
  }

  closeInPageOverlay({ silent: true });

  const root = document.createElement("div");
  root.id = "ro-inpage-overlay";
  root.dataset.overlayRoute = overlayRoute;
  root.dataset.overlaySearch = target.search.replace(/^\?/, "");
  if (active instanceof HTMLElement && active.id) root.dataset.restoreFocus = `#${CSS.escape(active.id)}`;
  else if (active instanceof HTMLElement) root.dataset.restoreFocus = "[data-overlay-return-focus='true']";
  root.innerHTML = `<div class="overlay-backdrop" data-overlay-close="true"></div><div class="overlay-host dialog" aria-busy="true"></div>`;
  document.body.appendChild(root);
  document.body.classList.add("is-inpage-overlay");

  try {
    const response = await fetch(fetchHref, { credentials: "same-origin", headers: { Accept: "text/html" } });
    if (!response.ok) throw new Error(`Overlay ${response.status}`);
    const html = await response.text();
    const doc = new DOMParser().parseFromString(html, "text/html");
    const sourceHost = doc.querySelector(".overlay-host");
    const sourceSurface = sourceHost?.querySelector("[data-overlay-surface='true']") || doc.querySelector("[data-overlay-surface='true']");
    const liveHost = root.querySelector(".overlay-host");
    if (sourceHost) {
      liveHost.className = sourceHost.className;
      liveHost.innerHTML = sourceHost.innerHTML;
    } else if (sourceSurface) {
      liveHost.innerHTML = "";
      liveHost.appendChild(document.importNode(sourceSurface, true));
    } else {
      throw new Error("Overlay markup missing");
    }
    liveHost.removeAttribute("aria-busy");

    if (typeof setupOverlayInteractionPolish === "function") setupOverlayInteractionPolish(root);
    if (typeof upgradeContextualRoutes === "function") upgradeContextualRoutes(root);

    root.querySelectorAll("form").forEach((form) => {
      form.setAttribute("novalidate", "novalidate");
      if (typeof setupFormProgress === "function") setupFormProgress(form);
      form.addEventListener("submit", (event) => {
        event.preventDefault();
        if (typeof validateForm === "function" && !validateForm(form)) return;
        if (window.RecruitOpsLive?.handleFormSubmit?.(form)) return;
        showToast("Looks good", "All required fields are complete.");
      });
    });

    if (window.RecruitOpsLive?.bootOverlay) {
      await window.RecruitOpsLive.bootOverlay(overlayRoute);
    }

    const focusTarget = root.querySelector("[data-overlay-surface] input:not([type='hidden']), [data-overlay-surface] select, [data-overlay-surface] textarea, [data-overlay-surface] button");
    window.requestAnimationFrame(() => {
      if (focusTarget instanceof HTMLElement) focusTarget.focus();
    });
  } catch (error) {
    root.remove();
    document.body.classList.remove("is-inpage-overlay");
    window.location.href = fetchHref;
  }
}


function resolveOverlayCloseHref() {
  const params = new URLSearchParams(window.location.search);
  const explicitReturn = normalizeInternalRoute(params.get("returnTo") || "");
  const fallbackReturn = normalizeInternalRoute(document.body?.dataset.overlayCloseHref || "");
  return explicitReturn || fallbackReturn || "";
}


function syncOverlayReturnLinks(closeHref) {
  if (document.body?.dataset.overlayPage !== "true" || !closeHref) return;
  document.querySelectorAll("[data-overlay-return-link]").forEach((link) => {
    link.setAttribute("href", closeHref);
  });
}


function shouldGuessRoute(element) {
  if (!element) return false;
  if (element.dataset.route || element.dataset.toast || element.dataset.chromeBound === "true") return false;
  if (element.getAttribute("aria-haspopup") === "menu") return false;
  if (element.closest("form, [data-layout='pagination-controls'], .ro-row-menu, .ro-row-menu-host, table")) return false;
  const icon = element.querySelector(".material-symbols-outlined")?.textContent?.trim().toLowerCase() || "";
  if (icon === "more_vert") return false;
  const label = getActionLabel(element);
  if (/export|refresh|reload|filter|save view|download/.test(label)) return false;
  return true;
}

function resolveContextualRoute(button) {
  if (!shouldGuessRoute(button)) return null;
  const routeId = document.body?.dataset.routeId || "";
  const label = getActionLabel(button);
  const icon = button.querySelector(".material-symbols-outlined")?.textContent?.trim().toLowerCase() || "";

  const onboardingNextRoutes = {
    "onboarding-welcome": "onboarding-company-profile.html",
    "onboarding-company-profile": "onboarding-hiring-teams.html",
    "onboarding-hiring-teams": "onboarding-locations.html",
    "onboarding-locations": "onboarding-role-setup.html",
    "onboarding-role-setup": "onboarding-pipeline-stage-builder.html",
    "onboarding-pipeline-stage-builder": "onboarding-integrations.html",
    "onboarding-integrations": "onboarding-success-launch.html",
  };
  if (routeId.startsWith("onboarding-")) {
    if (/continue|next|finish setup|launch workspace/.test(label)) {
      return onboardingNextRoutes[routeId] || "role-dashboard.html";
    }
    if (/invite/.test(label)) return routeId === "onboarding-hiring-teams" ? "onboarding-hiring-teams.html" : null;
  }

  if (routeId === "approvals-inbox") {
    if (/review/.test(label)) return "approval-review-drawer.html";
    if (/request exception/.test(label)) return "exception-request-dialog.html";
    if (/req-/.test(label)) return "requisition-detail.html";
  }

  if (routeId === "notifications-center") {
    if (/review|view details|view record/.test(label)) return "notification-detail-panel.html";
    if (/reply/.test(label)) return "candidate-review-drawer.html";
    if (/load older notifications/.test(label)) return "notifications-center.html";
  }

  if (routeId === "candidate-profiles") {
    if (/upload resume|bulk import/.test(label)) return "resume-upload-and-review.html";
    if (/manual entry/.test(label)) return "candidate-review-drawer.html";
  }

  if (routeId === "application-detail-drawer") {
    if (/full profile/.test(label)) return "candidate-profiles.html";
    if (/move stage/.test(label)) return "stage-move-dialog.html";
  }

  if (routeId === "candidate-review-drawer") {
    if (/upload resume|bulk import/.test(label)) return "resume-upload-and-review.html";
    if (/manual entry/.test(label)) return "candidate-review-drawer.html";
    if (/full profile|preview/.test(label)) return "candidate-profiles.html";
    if (/link to req/.test(label)) return "link-to-requisition-dialog.html";
    if (/move to pipeline stage|move stage/.test(label)) return "stage-move-dialog.html";
  }

  if (routeId === "client-directory") {
    if (/view detail/.test(label)) return "client-detail.html";
    if (/new requisition/.test(label)) return "requisition-intake.html";
    if (/add client|new client/.test(label)) return "contact-form-dialog.html";
  }

  if (routeId === "location-management") {
    if (/^admin$/.test(label)) return "role-dashboard.html";
    if (/^setup$/.test(label)) return "location-management.html";
  }

  if (routeId === "role-management") {
    if (/\b\d+\s+users?\b/.test(label)) return "user-management.html";
  }

  if (routeId === "user-management") {
  }

  if (routeId === "role-dashboard") {
    if (/create requisition/.test(label)) return "requisition-intake.html";
    if (/add candidate/.test(label)) return "candidate-review-drawer.html";
    if (/generate report|review daily updates/.test(label)) return "daily-updates-workspace.html";
    if (/reassign load/.test(label)) return "reassign-owner-dialog.html";
    if (/view all 24 items in queue/.test(label)) return "approvals-inbox.html";
    if (/^resolve$/.test(label)) return "candidate-duplicate-review.html";
    if (/^nudge$/.test(label)) return "requisition-detail.html";
    if (/^review$/.test(label)) return "candidate-screening.html";
    if (/^view$/.test(label)) return "approval-review-drawer.html";
  }

  if (routeId === "candidate-screening") {
    if (/view full profile/.test(label)) return "candidate-profiles.html";
    if (/elena rostova/.test(label)) return "candidate-review-drawer.html";
    if (/flag as exceptional case/.test(label)) return "exception-request-dialog.html";
    if (/request tech interview/.test(label)) return "stage-move-dialog.html";
    if (/reject with reason/.test(label)) return "stage-move-dialog.html";
  }

  if (routeId === "daily-updates-workspace") {
    if (/view detail/.test(label)) return "daily-update-detail-panel.html";
    if (/edit/.test(label)) return "daily-update-detail-panel.html";
    if (/reply/.test(label)) return "notification-detail-panel.html";
    if (/view all history/.test(label)) return "daily-updates-workspace.html";
  }

  if (routeId === "daily-update-detail-panel") {
    if (/req-\d+|staff engineer/.test(label)) return "requisition-detail.html";
  }

  if (routeId === "notification-detail-panel") {
    if (/go to record|review requisition/.test(label)) return "requisition-detail.html";
  }

  if (routeId === "requisition-detail") {
    if (/reassign/.test(label)) return "reassign-owner-dialog.html";
    if (/open pipeline/.test(label)) return "pipeline-board.html";
    if (/edit requisition/.test(label)) {
      const requisitionId = new URLSearchParams(window.location.search).get("requisition_id");
      return requisitionId ? `requisition-intake-edit.html?requisition_id=${requisitionId}` : "requisition-intake-edit.html";
    }
    if (/alex rodriguez|emily chen/.test(label)) return "candidate-review-drawer.html";
  }

  if (routeId === "follow-ups") {
    if (/add follow-up|new follow-up/.test(label)) return "follow-up-form-dialog.html";
  }

  if (routeId === "meetings") {
    if (/schedule meeting|add meeting|new meeting/.test(label)) return "meeting-form-dialog.html";
  }

  if (routeId === "reassign-owner-dialog") {
    if (/alex rodriguez|emily chen/.test(label)) return "candidate-review-drawer.html";
  }

  if (routeId === "client-detail") {
    if (/^add$/.test(label)) return "contact-form-dialog.html";
    if (/new req/.test(label)) return "requisition-intake.html";
    if (/senior frontend engineer|product manager|backend developer|devops engineer/.test(label)) return "requisition-detail.html";
  }

  if (routeId === "delivery-work-queue") {
    if (/ping hm|update notes/.test(label)) return "requisition-detail.html";
    if (/confirm schedule/.test(label)) return "candidate-screening.html";
  }

  if (routeId === "my-work-dashboard") {
    if (/view all/.test(label)) return "requisition-list.html";
    if (/^update$/.test(label)) return "daily-updates-workspace.html";
  }

  if (routeId === "requisition-list") {
    if (/create requisition/.test(label)) return "requisition-intake.html";
    if (/^client$|^status$|^priority$/.test(label)) return "requisition-list.html";
  }

  if (routeId === "pipeline-board") {
    if (/move stage/.test(label)) return "stage-move-dialog.html";
  }

  if (routeId === "stage-move-dialog") {
    if (/confirm transition|move stage/.test(label)) return "pipeline-board.html";
  }

  if (routeId === "login") {
    if (/forgot password|it support access/.test(label)) return "support-workspace.html";
  }

  return null;
}


function upgradeContextualRoutes(scope = document) {
  scope.querySelectorAll("a[href='javascript:void(0)']").forEach((link) => {
    const contextualRoute = resolveContextualRoute(link);
    if (!contextualRoute) return;
    link.setAttribute("href", contextualRoute);
    if (!link.getAttribute("title")) {
      link.setAttribute("title", getActionLabel(link));
    }
    if (!link.getAttribute("aria-label")) {
      link.setAttribute("aria-label", getActionLabel(link));
    }
    if (link.dataset.toastTitle === "Placeholder action") {
      delete link.dataset.toastTitle;
    }
    if ((link.dataset.toast || "").includes("ready for later API or workflow wiring")) {
      delete link.dataset.toast;
    }
  });

  scope.querySelectorAll("button:not([data-route])").forEach((button) => {
    if (button.closest("form")) return;
    const type = (button.getAttribute("type") || "").toLowerCase();
    if (type === "submit") return;
    const contextualRoute = resolveContextualRoute(button);
    if (!contextualRoute) return;
    button.dataset.route = contextualRoute;
  });
}


function setupRoutePrefetcher() {
  if (typeof document === "undefined") return;

  const currentFile = (window.location.pathname.split("/").pop() || "").replace(/\.html.*/, "");
  if (!currentFile || currentFile === "login" || currentFile === "landing" || currentFile === "index") return;

  // Collect all nav links grouped by section
  const groups = [];

  // First pass: collect all groups with ALL their links (including current page)
  document.querySelectorAll(".sidebar-nav details.nav-group").forEach((group) => {
    const label = group.dataset.navGroup || "";
    const allGroupLinks = [];
    group.querySelectorAll("a.nav-link").forEach((anchor) => {
      const href = anchor.getAttribute("href") || "";
      const file = href.replace(/\.html.*/, "");
      if (!file) return;
      allGroupLinks.push({ href, file, label });
    });
    if (allGroupLinks.length) groups.push({ label, links: allGroupLinks });
  });

  if (!groups.length) return;

  // Find which group the current page belongs to
  const currentFileLower = currentFile.toLowerCase();
  let currentGroupIndex = groups.findIndex((g) =>
    g.links.some((l) => l.file.toLowerCase() === currentFileLower),
  );

  // Build priority list: same group > adjacent groups > rest
  const priorities = [];

  // 1. Same-group siblings (highest priority — user is browsing within a section)
  if (currentGroupIndex >= 0) {
    groups[currentGroupIndex].links.forEach((link) => {
      if (link.file.toLowerCase() === currentFileLower) return; // skip current page
      priorities.push({ ...link, isCurrentGroup: true, priority: 1 });
    });
  }

  // 2. Adjacent group links (medium priority — likely next section)
  const adjacentIndices = [];
  if (currentGroupIndex > 0) adjacentIndices.push(currentGroupIndex - 1);
  if (currentGroupIndex < groups.length - 1) adjacentIndices.push(currentGroupIndex + 1);
  adjacentIndices.forEach((idx) => {
    groups[idx].links.forEach((link) => {
      priorities.push({ ...link, isCurrentGroup: false, priority: 2 });
    });
  });

  // 3. Also scan all in-page links (data-route) for related pages
  document.querySelectorAll("a[data-route], button[data-route]").forEach((el) => {
    const href = el.dataset.route || el.getAttribute("href") || "";
    const file = href.replace(/\.html.*/, "");
    if (!file || file === currentFile) return;
    const alreadyScheduled = priorities.some((p) => p.file === file);
    if (!alreadyScheduled) {
      priorities.push({ href, file, label: "", priority: 3 });
    }
  });

  // Deduplicate by file, keeping highest priority
  const seen = new Set();
  const unique = [];
  priorities.sort((a, b) => a.priority - b.priority);
  for (const item of priorities) {
    if (seen.has(item.file)) continue;
    seen.add(item.file);
    unique.push(item);
  }

  // Inject prefetch links after idle
  const injectPrefetches = () => {
    // Determine if we're on a root index page (needs pages/ prefix)
    const isRootIndex = isRootIndexPath(window.location.pathname);
    const prefix = isRootIndex ? "pages/" : "";

    unique.forEach((item, index) => {
      // Cap at 8 prefetches to avoid overwhelming the browser
      if (index >= 8) return;

      const fullHref = prefix + item.href;

      // Prefetch the HTML page
      const link = document.createElement("link");
      link.rel = "prefetch";
      link.href = fullHref;
      link.as = "document";
      document.head.appendChild(link);
    });
  };

  if (typeof requestIdleCallback === "function") {
    requestIdleCallback(injectPrefetches, { timeout: 3000 });
  } else {
    setTimeout(injectPrefetches, 200);
  }
}


