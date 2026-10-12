/* RecruitOps marketing pages: shared header, footer, mobile menu and
   scroll reveals. Pages work without it (content is plain HTML). */
(function () {
  "use strict";
  var inPages = /\/pages\//.test(window.location.pathname);
  var p = inPages ? "" : "pages/";
  var home = inPages ? "../index.html" : "index.html";
  var page = (window.location.pathname.split("/").pop() || "index.html").replace(".html", "") || "index";
  var section = page.indexOf("product-tour") === 0 ? "product-tour" : page;
  var cur = function (name) { return section === name ? ' aria-current="page"' : ""; };
  var LOGO = '<svg viewBox="0 0 48 48" fill="none" aria-hidden="true"><circle cx="24" cy="24" r="17" stroke="currentColor" stroke-width="7" stroke-linecap="round" stroke-dasharray="55 14 17 14" stroke-dashoffset="10" pathLength="100"/><circle cx="24" cy="24" r="6.5" fill="currentColor"/></svg>';

  document.documentElement.classList.add("mk-js");

  var header = document.createElement("header");
  header.className = "mk-nav";
  header.innerHTML =
    '<div class="mk-nav-inner">' +
      '<div class="mk-nav-left">' +
        '<a class="mk-brand" href="' + home + '">' + LOGO + 'RecruitOps</a>' +
        '<nav class="mk-nav-links" aria-label="Main">' +
          '<a href="' + p + 'product-tour.html"' + cur("product-tour") + '>Product tour</a>' +
          '<a href="' + p + 'use-cases.html"' + cur("use-cases") + '>Use cases</a>' +
        '</nav>' +
      '</div>' +
      '<div class="mk-nav-right">' +
        '<a class="mk-signin" href="' + p + 'login.html">Sign in</a>' +
        '<a class="mk-btn mk-btn-primary" href="' + p + 'signup.html">Create your account</a>' +
        '<button type="button" class="mk-burger" aria-label="Open menu" aria-expanded="false" aria-controls="mk-mobile">' +
          '<span class="material-symbols-outlined" aria-hidden="true">menu</span></button>' +
      '</div>' +
    '</div>' +
    '<div class="mk-mobile" id="mk-mobile">' +
      '<a href="' + p + 'product-tour.html">Product tour</a>' +
      '<a href="' + p + 'use-cases.html">Use cases</a>' +
      '<a href="' + p + 'login.html">Sign in</a>' +
      '<a class="mk-btn mk-btn-primary" href="' + p + 'signup.html">Create your account</a>' +
    '</div>';
  document.body.insertBefore(header, document.body.firstChild);
  var skip = document.createElement("a");
  skip.className = "mk-skip"; skip.href = "#main"; skip.textContent = "Skip to content";
  document.body.insertBefore(skip, header);

  var burger = header.querySelector(".mk-burger");
  burger.addEventListener("click", function () {
    var open = header.classList.toggle("open");
    burger.setAttribute("aria-expanded", open ? "true" : "false");
    burger.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    burger.firstChild.textContent = open ? "close" : "menu";
  });
  var onScroll = function () { header.classList.toggle("scrolled", window.scrollY > 4); };
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  var footer = document.createElement("footer");
  footer.className = "mk-footer";
  footer.innerHTML =
    '<div class="mk-wrap">' +
      '<div class="mk-footer-grid">' +
        '<div><a class="mk-brand" href="' + home + '">' + LOGO + 'RecruitOps</a>' +
          '<p>Recruitment operations for agencies and in-house teams. Your stages, your clients, your rules.</p></div>' +
        '<div><h4>Product</h4><ul>' +
          '<li><a href="' + p + 'product-tour.html">Product tour</a></li>' +
          '<li><a href="' + p + 'use-cases.html">Use cases</a></li></ul></div>' +
        '<div><h4>Account</h4><ul>' +
          '<li><a href="' + p + 'signup.html">Create your account</a></li>' +
          '<li><a href="' + p + 'login.html">Sign in</a></li>' +
          '<li><a href="' + p + 'forgot-password.html">Reset your password</a></li></ul></div>' +
        '<div><h4>Legal</h4><ul>' +
          '<li><a href="' + p + 'legal.html?doc=tos">Terms of Service</a></li>' +
          '<li><a href="' + p + 'legal.html?doc=privacy">Privacy Policy</a></li>' +
          '<li><a href="' + p + 'legal.html?doc=dpa">Data Processing Agreement</a></li></ul></div>' +
      '</div>' +
      '<div class="mk-footer-bottom"><span>&copy; ' + new Date().getFullYear() + ' RecruitOps</span><span>Built for teams that take hiring seriously.</span></div>' +
    '</div>';
  document.body.appendChild(footer);

  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var items = document.querySelectorAll(".mk-reveal");
  if (reduce || !("IntersectionObserver" in window)) {
    items.forEach(function (el) { el.classList.add("in"); });
    return;
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) { entry.target.classList.add("in"); io.unobserve(entry.target); }
    });
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });
  items.forEach(function (el) { io.observe(el); });
})();
