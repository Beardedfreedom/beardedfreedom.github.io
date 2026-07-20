/* =========================================================================
   nav.js — Claude Code Internals
   Two tiny, progressive-enhancement jobs:
     1. Mark the active top-nav link via aria-current="page" (pathname match).
     2. Wire the mobile nav toggle (hamburger) open/close.
   No dependencies. Safe to load with `defer`. Does nothing harmful if the
   nav markup is absent.
   ========================================================================= */
(function () {
  "use strict";

  /* Normalize a pathname to a canonical page key.
     "/" and "/index.html" both resolve to HOME. */
  function pageKey(pathname) {
    var file = pathname.replace(/\/+$/, "").split("/").pop();
    if (file === "" || file === undefined) return "index.html";
    return file;
  }

  function init() {
    var current = pageKey(window.location.pathname);

    /* 1. Active link ----------------------------------------------------- */
    var links = document.querySelectorAll(".nav__link");
    links.forEach(function (link) {
      var href = link.getAttribute("href") || "";
      // strip query/hash, keep the file segment
      var target = pageKey(href.split("#")[0].split("?")[0]);
      // a bare "#subscribe" style anchor has no file -> never "active"
      var isAnchorOnly = href.charAt(0) === "#";
      if (!isAnchorOnly && target === current) {
        link.setAttribute("aria-current", "page");
      } else {
        link.removeAttribute("aria-current");
      }
    });

    /* 2. Mobile toggle --------------------------------------------------- */
    var toggle = document.querySelector(".nav__toggle");
    var list = document.querySelector(".nav__list");
    if (toggle && list) {
      toggle.addEventListener("click", function () {
        var open = list.getAttribute("data-open") === "true";
        list.setAttribute("data-open", open ? "false" : "true");
        toggle.setAttribute("aria-expanded", open ? "false" : "true");
      });
      // collapse the menu after following a link on mobile
      list.addEventListener("click", function (e) {
        if (e.target.closest(".nav__link")) {
          list.setAttribute("data-open", "false");
          toggle.setAttribute("aria-expanded", "false");
        }
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
