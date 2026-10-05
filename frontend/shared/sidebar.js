/* ═══════════════════════════════════════════════════════════════
   SIDEBAR — Auto-extracted from app.js
   ═══════════════════════════════════════════════════════════════ */

const SIDEBAR_COLLAPSED_KEY = "recruitops-sidebar-collapsed";

function readSidebarCollapsed() {
  try {
    return window.localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "true";
  } catch {
    return false;
  }
}

function writeSidebarCollapsed(collapsed) {
  try {
    window.localStorage.setItem(SIDEBAR_COLLAPSED_KEY, collapsed ? "true" : "false");
  } catch {
    /* ignore quota / private-mode failures */
  }
}

function syncSidebarToggleButtons(collapsed) {
  document.querySelectorAll("[data-sidebar-toggle]").forEach((button) => {
    button.setAttribute("aria-expanded", collapsed ? "false" : "true");
    button.setAttribute("aria-label", collapsed ? "Expand sidebar" : "Collapse sidebar");
    button.title = collapsed ? "Expand sidebar" : "Collapse sidebar";
    const icon = button.querySelector(".material-symbols-outlined");
    if (icon) icon.textContent = collapsed ? "chevron_right" : "menu_open";
  });
}

function isSidebarCollapsed() {
  return document.querySelector(".app-shell")?.dataset.sidebarCollapsed === "true";
}

function applySidebarCollapsed(collapsed) {
  document.querySelectorAll(".app-shell").forEach((shell) => {
    shell.dataset.sidebarCollapsed = collapsed ? "true" : "false";
  });
  document.body.classList.toggle("sidebar-collapsed", collapsed);
  if (!collapsed) closeSidebarGenie(true);
  syncSidebarToggleButtons(collapsed);
  writeSidebarCollapsed(collapsed);
}

function toggleSidebarCollapsed() {
  const collapsed = document.querySelector(".app-shell")?.dataset.sidebarCollapsed === "true";
  applySidebarCollapsed(!collapsed);
}

function ensureSidebarToggle() {
  document.querySelectorAll(".app-sidebar [data-sidebar-toggle], .sidebar-collapse-toggle").forEach((button) => {
    button.remove();
  });

  const topbarLead = document.querySelector(".app-topbar .flex.min-w-0.flex-1, .app-topbar > div:first-child");
  if (topbarLead && !topbarLead.querySelector("[data-sidebar-toggle]")) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.sidebarToggle = "true";
    button.className = "topbar-sidebar-toggle topbar-action hidden rounded-full border border-border bg-surface p-2 text-on-surface lg:inline-flex";
    button.innerHTML = '<span class="material-symbols-outlined text-[18px]">menu_open</span>';
    const mobileOpen = topbarLead.querySelector("[data-mobile-nav-open]");
    if (mobileOpen) mobileOpen.insertAdjacentElement("afterend", button);
    else topbarLead.prepend(button);
  }

  document.querySelectorAll(".topbar-sidebar-toggle, .app-topbar [data-sidebar-toggle]").forEach((button) => {
    if (button.dataset.sidebarToggleBound === "true") return;
    button.dataset.sidebarToggleBound = "true";
    button.addEventListener("click", (event) => {
      event.preventDefault();
      toggleSidebarCollapsed();
    });
  });
}

function setupSidebarNav() {
  ensureSidebarToggle();
  applySidebarCollapsed(readSidebarCollapsed());

  const roots = document.querySelectorAll(".app-sidebar nav, #mobile-nav .space-y-4, .mobile-nav-panel > .space-y-4");
  roots.forEach((root) => {
    upgradeLegacyNavGroups(root);
    hydrateNavGroups(root);
  });
  document.querySelectorAll(".app-sidebar .nav-group-toggle").forEach((summary) => {
    if (summary.title) return;
    const label = summary.querySelector(".nav-group-label")?.textContent?.trim();
    if (label) summary.title = label;
  });
  setupSidebarGenie();
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

let sidebarGenie = { group: null, closingTimer: 0, hoverOpenTimer: 0, hoverCloseTimer: 0 };

function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function sidebarGenieRoot() {
  let root = document.getElementById("ro-sidebar-genie");
  if (root) return root;
  root = document.createElement("div");
  root.id = "ro-sidebar-genie";
  root.className = "sidebar-genie";
  root.hidden = true;
  root.innerHTML = '<div class="sidebar-genie-card"><p class="sidebar-genie-title"></p><div class="sidebar-genie-links"></div></div>';
  document.body.appendChild(root);
  return root;
}

function clearSidebarGenieTimer() {
  if (sidebarGenie.closingTimer) {
    window.clearTimeout(sidebarGenie.closingTimer);
    sidebarGenie.closingTimer = 0;
  }
  if (sidebarGenie.hoverOpenTimer) {
    window.clearTimeout(sidebarGenie.hoverOpenTimer);
    sidebarGenie.hoverOpenTimer = 0;
  }
  if (sidebarGenie.hoverCloseTimer) {
    window.clearTimeout(sidebarGenie.hoverCloseTimer);
    sidebarGenie.hoverCloseTimer = 0;
  }
}

function isGenieHoverTarget(target) {
  if (!(target instanceof Element)) return false;
  return Boolean(target.closest("#ro-sidebar-genie, .app-sidebar details.nav-group"));
}

function scheduleOpenSidebarGenie(group) {
  if (!isSidebarCollapsed() || !group) return;
  if (sidebarGenie.hoverOpenTimer) {
    window.clearTimeout(sidebarGenie.hoverOpenTimer);
    sidebarGenie.hoverOpenTimer = 0;
  }
  if (sidebarGenie.hoverCloseTimer) {
    window.clearTimeout(sidebarGenie.hoverCloseTimer);
    sidebarGenie.hoverCloseTimer = 0;
  }
  if (sidebarGenie.group === group) return;
  const delay = sidebarGenie.group ? 0 : 70;
  sidebarGenie.hoverOpenTimer = window.setTimeout(() => {
    sidebarGenie.hoverOpenTimer = 0;
    openSidebarGenie(group);
  }, delay);
}

function scheduleCloseSidebarGenie() {
  if (sidebarGenie.hoverOpenTimer) {
    window.clearTimeout(sidebarGenie.hoverOpenTimer);
    sidebarGenie.hoverOpenTimer = 0;
  }
  if (sidebarGenie.hoverCloseTimer) {
    window.clearTimeout(sidebarGenie.hoverCloseTimer);
    sidebarGenie.hoverCloseTimer = 0;
  }
  sidebarGenie.hoverCloseTimer = window.setTimeout(() => {
    sidebarGenie.hoverCloseTimer = 0;
    closeSidebarGenie();
  }, 180);
}

function positionSidebarGenie(trigger) {
  const root = sidebarGenieRoot();
  const card = root.querySelector(".sidebar-genie-card");
  if (!trigger || !card) return;
  const rect = trigger.getBoundingClientRect();
  const sidebarRight = document.querySelector(".app-sidebar")?.getBoundingClientRect().right || rect.right;
  root.style.left = `${Math.round(sidebarRight + 8)}px`;
  root.style.top = "0px";
  const height = card.offsetHeight || 160;
  const pad = 12;
  let top = rect.top - 6;
  if (top + height > window.innerHeight - pad) top = window.innerHeight - height - pad;
  top = Math.max(pad, top);
  root.style.top = `${Math.round(top)}px`;
  const originY = ((rect.top + rect.height / 2) - top) / Math.max(height, 1) * 100;
  card.style.transformOrigin = `0% ${Math.max(8, Math.min(92, originY))}%`;
}

function closeSidebarGenie(immediate = false) {
  clearSidebarGenieTimer();
  const group = sidebarGenie.group;
  if (group) {
    group.classList.remove("is-genie-open");
    group.querySelector(".nav-group-toggle")?.setAttribute("aria-expanded", "false");
  }
  sidebarGenie.group = null;
  const root = document.getElementById("ro-sidebar-genie");
  if (!root || root.hidden) return;
  const hide = () => {
    root.hidden = true;
    root.classList.remove("is-open", "is-closing");
  };
  if (immediate || prefersReducedMotion()) {
    hide();
    return;
  }
  root.classList.remove("is-open");
  root.classList.add("is-closing");
  sidebarGenie.closingTimer = window.setTimeout(hide, 280);
}

function openSidebarGenie(group) {
  if (!isSidebarCollapsed() || !group) return;
  const trigger = group.querySelector(":scope > .nav-group-toggle");
  const source = group.querySelector(":scope > .nav-sub");
  if (!trigger || !source) return;
  if (sidebarGenie.group === group) {
    positionSidebarGenie(trigger);
    return;
  }
  closeSidebarGenie(true);
  const root = sidebarGenieRoot();
  const title = root.querySelector(".sidebar-genie-title");
  const links = root.querySelector(".sidebar-genie-links");
  const label = group.querySelector(".nav-group-label")?.textContent?.trim() || "Menu";
  title.textContent = label;
  links.replaceChildren(
    ...Array.from(source.querySelectorAll(":scope > a.nav-link")).map((link) => link.cloneNode(true))
  );
  sidebarGenie.group = group;
  group.classList.add("is-genie-open");
  trigger.setAttribute("aria-haspopup", "true");
  trigger.setAttribute("aria-expanded", "true");
  root.hidden = false;
  root.classList.remove("is-closing");
  root.setAttribute("aria-label", label);
  positionSidebarGenie(trigger);
  window.requestAnimationFrame(() => {
    if (sidebarGenie.group !== group) return;
    root.classList.add("is-open");
  });
}

function setupSidebarGenie() {
  const root = sidebarGenieRoot();
  document.querySelectorAll(".app-sidebar details.nav-group").forEach((group) => {
    if (group.dataset.genieBound === "true") return;
    group.dataset.genieBound = "true";
    const summary = group.querySelector(":scope > .nav-group-toggle");
    summary?.setAttribute("aria-haspopup", "true");
    group.addEventListener("mouseenter", () => {
      if (!isSidebarCollapsed()) return;
      scheduleOpenSidebarGenie(group);
    });
    group.addEventListener("mouseleave", (event) => {
      if (!isSidebarCollapsed()) return;
      if (isGenieHoverTarget(event.relatedTarget)) return;
      scheduleCloseSidebarGenie();
    });
    summary?.addEventListener("click", (event) => {
      if (!isSidebarCollapsed()) return;
      event.preventDefault();
    });
  });
  if (document.body.dataset.sidebarGenieBound === "true") return;
  document.body.dataset.sidebarGenieBound = "true";
  root.addEventListener("mouseenter", () => {
    if (sidebarGenie.hoverCloseTimer) {
      window.clearTimeout(sidebarGenie.hoverCloseTimer);
      sidebarGenie.hoverCloseTimer = 0;
    }
  });
  root.addEventListener("mouseleave", (event) => {
    if (isGenieHoverTarget(event.relatedTarget)) return;
    scheduleCloseSidebarGenie();
  });
  document.addEventListener("click", (event) => {
    if (!sidebarGenie.group) return;
    const target = event.target instanceof Element ? event.target : null;
    if (isGenieHoverTarget(target)) return;
    closeSidebarGenie();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeSidebarGenie(true);
  });
  window.addEventListener("resize", () => closeSidebarGenie(true));
  document.querySelector(".app-sidebar")?.addEventListener("scroll", () => {
    if (!sidebarGenie.group) return;
    const trigger = sidebarGenie.group.querySelector(":scope > .nav-group-toggle");
    if (trigger) positionSidebarGenie(trigger);
  }, { passive: true });
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


