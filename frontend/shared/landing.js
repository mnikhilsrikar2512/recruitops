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

  /* ── Active nav link helper ── */
  function isActive(page) {
    return currentPage === page ? ' class="active"' : "";
  }

  /* ═══ INJECT NAV ═══ */
  const navHTML = `
  <nav class="landing-nav" id="landingNav">
    <div class="landing-nav-inner">
      <div style="display:flex;align-items:center;gap:32px;">
        <a class="landing-nav-brand" href="${home}">
          <span class="material-symbols-outlined" style="font-size:24px;color:#24483C;font-variation-settings:'FILL'1">widgets</span>
          RecruitOps
        </a>
        <div class="landing-nav-links">
          <a href="${prefix}product-tour.html"${isActive("product-tour")}>Product</a>
          <a href="${prefix}use-cases.html"${isActive("use-cases")}>Use Cases</a>
        </div>
      </div>
      <div class="landing-nav-actions">
        <a class="btn-nav btn-nav-ghost" href="${prefix}login.html">Sign In</a>
        <a class="btn-nav btn-nav-primary" href="${prefix}login.html">Start Free Trial</a>
        <button class="nav-burger" id="navBurger" aria-label="Menu" aria-expanded="false" aria-controls="mobileMenu">
          <span class="material-symbols-outlined" style="font-size:22px">menu</span>
        </button>
      </div>
    </div>
    <ul class="mobile-menu" id="mobileMenu">
      <li class="mobile-menu-clip">
        <ul class="mobile-menu-list">
          <li><a href="${prefix}product-tour.html"${isActive("product-tour")}>Product</a></li>
          <li><a href="${prefix}use-cases.html"${isActive("use-cases")}>Use Cases</a></li>
          <li><a href="${prefix}login.html">Sign In</a></li>
          <li><a href="${prefix}login.html" class="mobile-menu-cta">Start Free Trial</a></li>
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
            <span class="material-symbols-outlined" style="font-size:22px;color:#24483C;font-variation-settings:'FILL'1">widgets</span>
            RecruitOps
          </a>
          <p>The customizable recruitment operating system. Build your own designations, pipelines, and approval workflows.</p>
          <a class="btn-primary" href="${prefix}login.html" style="font-size:12px;padding:10px 20px">
            Start Free Trial
            <span class="material-symbols-outlined" style="font-size:16px">arrow_forward</span>
          </a>
        </div>
        <div class="landing-footer-col">
          <h4>Product</h4>
          <a href="${prefix}product-tour.html">Product Tour</a>
          <a href="${prefix}use-cases.html">Use Cases</a>
          <a href="${prefix}product-tour.html#features">Features</a>
        </div>
        <div class="landing-footer-col">
          <h4>Company</h4>
          <a href="${prefix}login.html">Sign In</a>
          <a href="${prefix}login.html">Get Started</a>
          <a href="${prefix}login.html">Support</a>
        </div>
        <div class="landing-footer-col">
          <h4>Legal</h4>
          <span>Privacy Policy</span>
          <span>Terms of Service</span>
          <span>Cookie Policy</span>
        </div>
      </div>
      <div class="landing-footer-bottom">
        <div class="copy">&copy; 2026 RecruitOps. All rights reserved.</div>
        <div class="status"><span class="status-dot"></span> All systems operational</div>
      </div>
    </div>
  </footer>`;

  /* ═══ INSERT NAV + FOOTER ═══ */
  document.body.insertAdjacentHTML("afterbegin", navHTML);
  document.body.insertAdjacentHTML("beforeend", footerHTML);

  /* ═══ SCROLL REVEAL ═══ */
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
  document.querySelectorAll(".reveal, .reveal-scale, .reveal-left, .reveal-right, .reveal-pop").forEach((el) => revealObserver.observe(el));

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
    window.matchMedia("(min-width: 769px)").addEventListener("change", (e) => { if (e.matches) setMenu(false); });
  }

  /* ═══ SKIP LINK TARGET ═══ */
  const main = document.getElementById("main-content");
  if (main) main.style.paddingTop = "64px";
})();
