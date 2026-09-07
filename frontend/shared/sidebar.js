/* ═══════════════════════════════════════════════════════════════
   SIDEBAR — Auto-extracted from app.js
   ═══════════════════════════════════════════════════════════════ */

function setupSidebarNav() {
  document.querySelectorAll("[data-sidebar-toggle]").forEach((node) => node.remove());
  document.querySelectorAll(".app-shell").forEach((shell) => {
    delete shell.dataset.sidebarCollapsed;
  });
  window.localStorage.removeItem("recruitops-sidebar-collapsed");

  const roots = document.querySelectorAll(".app-sidebar nav, #mobile-nav .space-y-4, .mobile-nav-panel > .space-y-4");
  roots.forEach((root) => {
    upgradeLegacyNavGroups(root);
    hydrateNavGroups(root);
  });
}


function upgradeLegacyNavGroups(root) {
  if (!root || root.querySelector(":scope > .nav-group")) return;
  Array.from(root.querySelectorAll(":scope > .space-y-1")).forEach((group) => {
    const labelEl = group.querySelector(".sidebar-group-label");
    if (!labelEl) return;
    const label = (labelEl.textContent || "").trim();
    const details = document.createElement("details");
    details.className = "nav-group";
    details.dataset.navGroup = label.toLowerCase();
    const summary = document.createElement("summary");
    summary.className = "nav-group-toggle";
    summary.innerHTML = `<span class="material-symbols-outlined nav-group-icon">folder</span><span class="nav-group-label">${label}</span><span class="material-symbols-outlined nav-group-chevron">expand_more</span>`;
    const sub = document.createElement("div");
    sub.className = "nav-sub";
    Array.from(group.children).forEach((child) => {
      if (child !== labelEl) sub.appendChild(child);
    });
    details.append(summary, sub);
    if (sub.querySelector('[aria-current="page"]')) details.open = true;
    group.replaceWith(details);
  });
}


function persistNavGroups() {
  const openIds = Array.from(document.querySelectorAll(".app-sidebar details.nav-group"))
    .filter((group) => group.open)
    .map((group) => group.dataset.navGroup)
    .filter(Boolean);
  window.localStorage.setItem(NAV_GROUP_KEY, JSON.stringify(openIds));
}


function hydrateNavGroups(root) {
  let saved = [];
  try {
    saved = JSON.parse(window.localStorage.getItem(NAV_GROUP_KEY) || "[]");
  } catch (error) {
    saved = [];
  }
  if (!Array.isArray(saved)) saved = [];
  root.querySelectorAll("details.nav-group").forEach((group) => {
    const id = group.dataset.navGroup || "";
    const hasCurrent = Boolean(group.querySelector('[aria-current="page"]'));
    group.open = hasCurrent || saved.includes(id);
    group.addEventListener("toggle", persistNavGroups);
  });
}


function openMobileNav(mobileDialog) {
  if (!mobileDialog || mobileDialog.open) return;
  const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  if (trigger && trigger.matches("[data-mobile-nav-open]")) {
    mobileDialog.dataset.returnFocusSelector = "[data-mobile-nav-open]";
  }
  mobileDialog.showModal();
  document.body.classList.add("scroll-locked");
  focusFirstInteractive(mobileDialog.querySelector(".mobile-nav-panel"));
}


function closeMobileNav(mobileDialog) {
  if (!mobileDialog) return;
  if (mobileDialog.open) {
    mobileDialog.close();
  }
  document.body.classList.remove("scroll-locked");
  const returnFocusSelector = mobileDialog.dataset.returnFocusSelector;
  if (returnFocusSelector) {
    const returnTarget = document.querySelector(returnFocusSelector);
    if (returnTarget instanceof HTMLElement) {
      window.requestAnimationFrame(() => returnTarget.focus());
    }
  }
}


function setupLogoutLinks() {
  document.querySelectorAll("[data-logout-link]").forEach((link) => {
    link.addEventListener("click", () => {
      try {
        window.sessionStorage.clear();
        window.localStorage.removeItem("recruitops-selected-pipeline-candidate");
      } catch {
      }
      showToast("Logged out", "Returning to the sign-in screen.");
    });
  });
}


