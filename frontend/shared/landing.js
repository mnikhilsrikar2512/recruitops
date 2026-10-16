/* ═══════════════════════════════════════════════════════════════
   RecruitOps — Shared Landing Page Script
   Injects: nav, footer, scroll reveals, animated counters
   ═══════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  /* ── Detect current page ── */
  const path = window.location.pathname;
  const isRoot = !path.includes("/pages/");
  const prefix = isRoot ? "pages/" : "";
  const home = isRoot ? "index.html" : "../index.html";
  const currentPage = path.split("/").pop().replace(".html", "") || "index";
  const routeKind = document.body?.dataset.routeKind || "";
  const AUTH_PAGES = new Set(["login", "forgot-password", "reset-password", "password-setup", "mfa-challenge"]);
  if (routeKind === "auth" || AUTH_PAGES.has(currentPage)) {
    return;
  }

  /* ── Active nav link helper ── */
  function isActive(page) {
    return currentPage === page ? ' class="active"' : "";
  }

  /* ── Brand mark: segmented ring + core dot (spins as a loader) ── */
  const LOGO_SVG = `<svg class="ro-logo" viewBox="0 0 48 48" fill="none" aria-hidden="true"><circle class="ro-logo-ring" cx="24" cy="24" r="17" stroke="currentColor" stroke-width="7" stroke-linecap="round" stroke-dasharray="55 14 17 14" stroke-dashoffset="10" pathLength="100"/><circle cx="24" cy="24" r="6.5" fill="currentColor"/></svg>`;

  /* ═══ INJECT NAV ═══ */
  const navHTML = `
  <nav class="landing-nav" id="landingNav">
    <div class="landing-nav-inner">
      <div style="display:flex;align-items:center;gap:32px;">
        <a class="landing-nav-brand" href="${home}">
          ${LOGO_SVG}
          RecruitOps
        </a>
        <div class="landing-nav-links">
          <a href="${prefix}product-tour.html"${isActive("product-tour")}>Product tour</a>
          <a href="${prefix}use-cases.html"${isActive("use-cases")}>Use cases</a>
        </div>
      </div>
      <div class="landing-nav-actions">
        <a class="btn-nav btn-nav-ghost" href="${prefix}login.html">Sign in</a>
        <a class="btn-nav btn-nav-primary" href="${prefix}signup.html">Create account</a>
        <button class="nav-burger" id="navBurger" aria-label="Menu" aria-expanded="false" aria-controls="mobileMenu">
          <span class="material-symbols-outlined" style="font-size:22px">menu</span>
        </button>
      </div>
    </div>
    <ul class="mobile-menu" id="mobileMenu">
      <li class="mobile-menu-clip">
        <ul class="mobile-menu-list">
          <li><a href="${prefix}product-tour.html"${isActive("product-tour")}>Product tour</a></li>
          <li><a href="${prefix}use-cases.html"${isActive("use-cases")}>Use cases</a></li>
          <li><a href="${prefix}login.html">Sign in</a></li>
          <li><a href="${prefix}signup.html" class="mobile-menu-cta">Create your account</a></li>
        </ul>
      </li>
    </ul>
  </nav>`;

  /* ═══ INJECT FOOTER ═══ */
  const footerHTML = `
  <footer class="landing-footer">
    <div class="landing-footer-inner">
      <div class="landing-footer-main">
        <div class="landing-footer-brand">
          <a class="landing-nav-brand" href="${home}" style="margin-bottom:0">
            ${LOGO_SVG}
            RecruitOps
          </a>
          <p>Recruitment operations for agencies and in-house teams. Your stages, your clients, your rules.</p>
          <a class="btn-primary" href="${prefix}signup.html" style="font-size:12px;padding:10px 20px">
            Create your account
            <span class="material-symbols-outlined" style="font-size:16px">arrow_forward</span>
          </a>
        </div>
        <div class="landing-footer-col">
          <h4>Product</h4>
          <a href="${prefix}product-tour.html">Product tour</a>
          <a href="${prefix}use-cases.html">Use cases</a>
        </div>
        <div class="landing-footer-col">
          <h4>Account</h4>
          <a href="${prefix}signup.html">Create your account</a>
          <a href="${prefix}login.html">Sign in</a>
        </div>
        <div class="landing-footer-col">
          <h4>Legal</h4>
          <a href="${prefix}legal.html?doc=tos">Terms of Service</a>
          <a href="${prefix}legal.html?doc=privacy">Privacy Policy</a>
          <a href="${prefix}legal.html?doc=dpa">Data Processing Agreement</a>
        </div>
      </div>
      <div class="landing-footer-bottom">
        <div class="copy">&copy; ${new Date().getFullYear()} RecruitOps. All rights reserved.</div>
      </div>
    </div>
  </footer>`;

  /* ═══ INSERT NAV + FOOTER ═══ */
  document.body.insertAdjacentHTML("afterbegin", navHTML);
  document.body.insertAdjacentHTML("beforeend", footerHTML);

  /* ═══ SCROLL REVEAL ═══
     These elements start at opacity:0 in CSS and only reach opacity:1 once
     this observer marks them "visible" as the user scrolls them into view.
     There was no fallback: if IntersectionObserver isn't available, or this
     script throws before reaching this point, or simply never loads (ad
     blocker, strict CSP, flaky network, JS disabled), almost every section
     below the hero on every marketing/product-tour page stays permanently
     invisible — not broken-looking, just blank, which is worse. Wrapped in
     try/catch with an immediate "show everything" fallback on any failure,
     and feature-detect IntersectionObserver itself rather than assuming it
     exists. */
  const revealTargets = document.querySelectorAll(".reveal, .reveal-scale, .reveal-left, .reveal-right, .reveal-pop");
  function showAllReveals() {
    revealTargets.forEach((el) => el.classList.add("visible"));
  }
  try {
    if (!("IntersectionObserver" in window)) {
      showAllReveals();
    } else {
      const revealObserver = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.add("visible");
              /* Animate counters inside */
              entry.target.querySelectorAll("[data-count]").forEach((el) => {
                const target = parseInt(el.dataset.count, 10);
                const suffix = el.dataset.suffix || "";
                let current = 0;
                const step = Math.max(1, Math.floor(target / 20));
                if (el.textContent && el.textContent !== "0" && el.textContent !== "0" + suffix) {
                  return;
                }
                const timer = setInterval(() => {
                  current += step;
                  if (current >= target) { current = target; clearInterval(timer); }
                  el.textContent = current + suffix;
                }, 30);
              });
            }
          });
        },
        { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
      );
      revealTargets.forEach((el) => revealObserver.observe(el));
    }
  } catch (err) {
    showAllReveals();
  }

  /* ═══ NAV SCROLL SHADOW ═══ */
  window.addEventListener("scroll", () => {
    const nav = document.getElementById("landingNav");
    if (nav) nav.classList.toggle("scrolled", window.scrollY > 20);
  });

  /* ═══ REDUCED MOTION GUARD ═══ */
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ═══ PARALLAX DEPTH ON SECTION HEADINGS ═══
     Headings drift behind the scroll while entering the viewport and
     settle to rest by the time they reach the upper third — a subtle
     depth cue. Scroll-linked via rAF; skipped under reduced motion. */
  const parallaxHeadings = [];
  if (!reduceMotion) {
    document.querySelectorAll("main section h2").forEach((h) => {
      h.classList.add("parallax-heading");
      parallaxHeadings.push(h);
    });
  }
  if (parallaxHeadings.length) {
    const DEPTH = 28; // px of drift across the entry band
    let ticking = false;
    const updateHeadingParallax = () => {
      ticking = false;
      const vh = window.innerHeight;
      for (const h of parallaxHeadings) {
        const rect = h.getBoundingClientRect();
        if (rect.bottom < -80 || rect.top > vh + 80) continue;
        /* 0 entering at the bottom edge → 1 settled in the upper third */
        const progress = Math.min(1, Math.max(0, (vh - rect.top) / (vh * 0.85)));
        h.style.transform = `translateY(${((1 - progress) * DEPTH).toFixed(1)}px)`;
      }
    };
    window.addEventListener("scroll", () => {
      if (!ticking) { ticking = true; requestAnimationFrame(updateHeadingParallax); }
    }, { passive: true });
    updateHeadingParallax();
  }

  /* ═══ MOUSE PARALLAX ON HERO ORBS ═══ */
  const hero = document.querySelector(".landing-hero");
  if (hero && !reduceMotion) {
    const orbs = hero.querySelectorAll(".orb");
    orbs.forEach((orb) => orb.classList.add("parallax-orb"));
    hero.addEventListener("mousemove", (e) => {
      const rect = hero.getBoundingClientRect();
      const nx = (e.clientX - rect.left) / rect.width - 0.5;
      const ny = (e.clientY - rect.top) / rect.height - 0.5;
      orbs.forEach((orb, i) => {
        const depth = (i + 1) * 14;
        orb.style.transform = `translate(${(-nx * depth).toFixed(1)}px, ${(-ny * depth).toFixed(1)}px)`;
      });
    });
    hero.addEventListener("mouseleave", () => {
      orbs.forEach((orb) => (orb.style.transform = ""));
    });
  }

  /* ═══ 3D TILT ON PRODUCT PREVIEW ═══ */
  document.querySelectorAll(".tilt-wrap").forEach((wrap) => {
    const card = wrap.querySelector(".tilt-card");
    if (!card || reduceMotion) return;
    wrap.addEventListener("mousemove", (e) => {
      const rect = card.getBoundingClientRect();
      const nx = (e.clientX - rect.left) / rect.width;
      const ny = (e.clientY - rect.top) / rect.height;
      const rx = (0.5 - ny) * 8;
      const ry = (nx - 0.5) * 10;
      card.style.transform = `rotateX(${rx.toFixed(2)}deg) rotateY(${ry.toFixed(2)}deg)`;
      card.style.setProperty("--gx", `${(nx * 100).toFixed(1)}%`);
      card.style.setProperty("--gy", `${(ny * 100).toFixed(1)}%`);
    });
    wrap.addEventListener("mouseleave", () => {
      card.style.transform = "";
    });
  });

  /* ═══ MOBILE MENU ═══ */
  const burger = document.getElementById("navBurger");
  const mobileMenu = document.getElementById("mobileMenu");
  if (burger && mobileMenu) {
    const isOpen = () => mobileMenu.classList.contains("open");
    const setMenu = (open) => {
      mobileMenu.classList.toggle("open", open);
      burger.setAttribute("aria-expanded", String(open));
      burger.querySelector(".material-symbols-outlined").textContent = open ? "close" : "menu";
    };
    burger.addEventListener("click", () => setMenu(!isOpen()));
    /* Close on link tap, Escape, and resize back to desktop */
    mobileMenu.addEventListener("click", (e) => { if (e.target.closest("a")) setMenu(false); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && isOpen()) setMenu(false); });
    window.matchMedia("(min-width: 1024px)").addEventListener("change", (e) => { if (e.matches) setMenu(false); });
  }

  /* ═══ SKIP LINK TARGET ═══ */
  const main = document.getElementById("main-content");
  if (main && !main.querySelector(".landing-hero")) {
    main.style.paddingTop = "64px";
  }
})();
