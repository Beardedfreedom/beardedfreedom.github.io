/* matrix-rain.js — Claude Code Internals
 * Themed digital rain (falling numbers / hex) behind all content.
 * Sits at z-index:-1, under the CRT scanline+vignette overlays.
 * CPU-friendly: capped FPS, pauses when tab hidden, respects reduced-motion.
 * Self-contained: just <script defer src="/assets/js/matrix-rain.js"></script>.
 */
(function () {
  "use strict";
  if (window.__cciMatrix) return;            // guard against double-injection
  window.__cciMatrix = true;

  var reduce = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Pull theme green from CSS so the rain always matches the design system.
  var root = getComputedStyle(document.documentElement);
  var GREEN = (root.getPropertyValue("--green") || "#3df58b").trim() || "#3df58b";
  var BG    = (root.getPropertyValue("--bg")    || "#0a0e0b").trim() || "#0a0e0b";
  var LEAD  = "#d7ffe9";                      // bright leading glyph
  var GLYPHS = "0123456789ABCDEF0123456789";  // mostly numbers, some hex flavor

  var canvas = document.createElement("canvas");
  canvas.setAttribute("aria-hidden", "true");
  var s = canvas.style;
  s.position = "fixed"; s.top = "0"; s.left = "0";
  s.width = "100%"; s.height = "100%";
  s.zIndex = "-1"; s.pointerEvents = "none";
  s.opacity = "0.42";                          // subtle — text stays readable
  (document.body || document.documentElement).appendChild(canvas);

  var ctx = canvas.getContext("2d", { alpha: true });
  var FONT = 15, cols = 0, drops = [], speeds = [], dpr = 1, W = 0, H = 0;

  function rint(n) { return Math.floor(Math.random() * n); }

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth; H = window.innerHeight;
    canvas.width = Math.floor(W * dpr);
    canvas.height = Math.floor(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    cols = Math.ceil(W / FONT);
    drops = new Array(cols);
    speeds = new Array(cols);
    for (var i = 0; i < cols; i++) {
      drops[i] = rint(Math.ceil(H / FONT));
      speeds[i] = 0.6 + Math.random() * 0.9;   // per-column speed variation
    }
    ctx.font = FONT + "px ui-monospace, 'JetBrains Mono', monospace";
    ctx.textBaseline = "top";
  }

  function drawFrame() {
    // translucent wash = fading trails
    ctx.fillStyle = "rgba(10,14,11,0.10)";
    ctx.fillRect(0, 0, W, H);
    for (var i = 0; i < cols; i++) {
      var x = i * FONT;
      var y = drops[i] * FONT;
      var ch = GLYPHS.charAt(rint(GLYPHS.length));
      // leading glyph bright, trail green
      ctx.fillStyle = Math.random() > 0.975 ? LEAD : GREEN;
      ctx.fillText(ch, x, y);
      if (y > H && Math.random() > 0.975) drops[i] = 0;
      else drops[i] += speeds[i];
    }
  }

  // Reduced motion: paint one calm static frame, no loop.
  if (reduce) {
    resize();
    ctx.fillStyle = BG; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = GREEN;
    for (var i = 0; i < cols; i++) {
      for (var j = 0; j < 3; j++) {
        if (Math.random() > 0.5) continue;
        ctx.fillText(GLYPHS.charAt(rint(GLYPHS.length)), i * FONT, rint(Math.ceil(H / FONT)) * FONT);
      }
    }
    window.addEventListener("resize", function () {
      clearTimeout(window.__cciMatrixRz);
      window.__cciMatrixRz = setTimeout(resize, 200);
    });
    return;
  }

  var FPS = 26, frameGap = 1000 / FPS, last = 0, running = true, rafId = 0;
  function loop(t) {
    rafId = requestAnimationFrame(loop);
    if (t - last < frameGap) return;
    last = t;
    drawFrame();
  }

  resize();
  rafId = requestAnimationFrame(loop);

  window.addEventListener("resize", function () {
    clearTimeout(window.__cciMatrixRz);
    window.__cciMatrixRz = setTimeout(resize, 200);
  });

  // Pause animation when the tab isn't visible — saves CPU on the laptop.
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      if (running) { cancelAnimationFrame(rafId); running = false; }
    } else if (!running) {
      running = true; last = 0; rafId = requestAnimationFrame(loop);
    }
  });
})();
