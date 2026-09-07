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
      </div>
    </div>
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
  document.querySelectorAll(".reveal, .reveal-scale").forEach((el) => revealObserver.observe(el));

  /* ═══ NAV SCROLL SHADOW ═══ */
  window.addEventListener("scroll", () => {
    const nav = document.getElementById("landingNav");
    if (nav) nav.classList.toggle("scrolled", window.scrollY > 20);
  });

  /* ═══ SKIP LINK TARGET ═══ */
  const main = document.getElementById("main-content");
  if (main) main.style.paddingTop = "64px";
})();
