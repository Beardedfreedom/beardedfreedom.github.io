/* =========================================================================
   forum.js — Claude Code Internals
   A fully client-side community forum. No backend, no build step, no network.
   State lives in localStorage; the UI is a small re-render loop driven by a
   hash route (#/board/<id> · #/thread/<id>) so the browser back button works.

   Design rules honored:
     - All user-authored strings (titles, authors, post bodies) are rendered
       via textContent / escaped helpers. Never innerHTML-interpolated. A
       security-research forum that's XSS-able would be embarrassing.
     - Seed runs exactly once (gated on a version key). Reseeding never clobbers
       user posts — replies and new threads persist across reloads.
     - Works on file:// — no modules, no fetch, plain localStorage.
   ========================================================================= */
(function () {
  "use strict";

  var STORE_KEY = "cci_forum_v1";

  /* ----------------------------------------------------------------------- */
  /* Utilities                                                                */
  /* ----------------------------------------------------------------------- */

  function uid() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return window.crypto.randomUUID();
    }
    return "id-" + Date.now().toString(36) + "-" +
           Math.random().toString(36).slice(2, 8);
  }

  /* Build an element with text content set safely (never parsed as HTML). */
  function el(tag, opts) {
    opts = opts || {};
    var node = document.createElement(tag);
    if (opts.className) node.className = opts.className;
    if (opts.text != null) node.textContent = String(opts.text);
    /* No innerHTML path by design: every string rendered here is user-authored
       and goes through textContent, so the forum is XSS-proof end to end. */
    if (opts.attrs) {
      Object.keys(opts.attrs).forEach(function (k) {
        node.setAttribute(k, opts.attrs[k]);
      });
    }
    if (opts.children) {
      opts.children.forEach(function (c) { if (c) node.appendChild(c); });
    }
    return node;
  }

  /* Relative time, terminal-flavored. */
  function timeAgo(ts) {
    var s = Math.floor((Date.now() - ts) / 1000);
    if (s < 5) return "just now";
    if (s < 60) return s + "s ago";
    var m = Math.floor(s / 60);
    if (m < 60) return m + "m ago";
    var h = Math.floor(m / 60);
    if (h < 24) return h + "h ago";
    var d = Math.floor(h / 24);
    if (d < 30) return d + "d ago";
    var mo = Math.floor(d / 30);
    if (mo < 12) return mo + "mo ago";
    return Math.floor(mo / 12) + "y ago";
  }

  function plural(n, one, many) {
    return n + " " + (n === 1 ? one : (many || one + "s"));
  }

  /* ----------------------------------------------------------------------- */
  /* Seed data                                                                */
  /* ----------------------------------------------------------------------- */

  function seed() {
    var now = Date.now();
    var min = 60 * 1000, hr = 60 * min, day = 24 * hr;

    function post(author, body, ago) {
      return { id: uid(), author: author, body: body, created: now - ago };
    }
    function thread(boardId, title, ago, posts) {
      return {
        id: uid(),
        boardId: boardId,
        title: title,
        created: now - ago,
        posts: posts
      };
    }

    var boards = [
      {
        id: "flag-watch",
        name: "Flag Watch",
        blurb: "New TENGU_* flags, env vars, and undocumented config keys spotted in fresh CLI builds."
      },
      {
        id: "workflows-hooks",
        name: "Workflows & Hooks",
        blurb: "Settings.json sorcery — Stop hooks, PreToolUse gates, auto-format, and slash-command rigs."
      },
      {
        id: "ctf-bounty",
        name: "CTF / Bounty",
        blurb: "Capture-the-flag writeups, HackerOne war stories, and responsible-disclosure craft."
      }
    ];

    var threads = [
      thread("flag-watch",
        "New settings key after the last update?",
        2 * hr,
        [
          post("beardedfreedom",
            "Pulled the new build and diffed the flag table — there's a key that wasn't in the previous release. " +
            "Anyone else seeing CLAUDE_CODE_COLD_COMPACT show up in their env dump? Looks like a background-precompute toggle.\n\n" +
            "Going to wire a local listener and A/B it tonight. Post your env diffs below.",
            2 * hr),
          post("nullbyte",
            "Confirmed on my side. It's gated server-side though — flipping it locally is a no-op until the rollout reaches your account.",
            95 * min),
          post("ghostframe",
            "Same. Also noticed `heron_brook` in the strings near the system-prompt assembler. Smells like a remote-fillable slot. Treating it as CONTROL until proven otherwise.",
            40 * min)
        ]),

      thread("flag-watch",
        "TENGU flag count jumped — anyone have a clean diff?",
        9 * hr,
        [
          post("stracectl",
            "Count went up by ~9 vs the last tag. One looks like a REMOVAL (iron_gate is gone). " +
            "If anyone has the previous build cached, drop your before/after so we can confirm the delta.",
            9 * hr),
          post("beardedfreedom",
            "iron_gate didn't get removed so much as hardcoded fail-closed — the branch that read the flag is now an unconditional deny. That's a hardening change, not a feature cut. Net positive.",
            7 * hr)
        ]),

      thread("workflows-hooks",
        "Best hooks setup for auto-format on save?",
        1 * day,
        [
          post("tabsnotspaces",
            "I want my formatter to run after every Write/Edit without nagging me for permission each time. " +
            "Is a PostToolUse hook the right surface, or should I be shelling out from a Stop hook?\n\n" +
            "Current attempt fires twice on multi-file edits. What's your config?",
            1 * day),
          post("hookwitch",
            "PostToolUse matched to Write|Edit is correct. The double-fire is because you're not de-duping by file path. " +
            "Collect the paths, run the formatter once at the end of the batch. I gate on a 300ms debounce — works clean.",
            22 * hr),
          post("beardedfreedom",
            "+1 to PostToolUse. One gotcha: keep the hook idempotent and fast. If it blocks for >1s the whole loop feels laggy. " +
            "I pipe through a project-local script so it's portable across machines.",
            20 * hr)
        ]),

      thread("workflows-hooks",
        "Stop hook to speak the last response with local TTS",
        2 * day,
        [
          post("phosphor",
            "Wired Piper (LibriTTS voice) as a Stop hook so the terminal reads Claude's last message aloud. " +
            "Fully offline, no ElevenLabs char cap. Happy to share the hook JSON if there's interest — it's about 12 lines.",
            2 * day),
          post("nullbyte",
            "Yes please. Been wanting a free local voice. Does it handle code blocks gracefully or read every backtick?",
            1 * day + 4 * hr)
        ]),

      thread("ctf-bounty",
        "CTF writeup: terminal escape via crafted filename",
        3 * day,
        [
          post("beardedfreedom",
            "Short writeup. The challenge dropped attacker-controlled text into a TUI without sanitizing escape sequences. " +
            "A filename carrying a CSI sequence could move the cursor and overwrite the prompt line — classic terminal-injection.\n\n" +
            "Fix is the same as always: treat ALL external content as untrusted, strip C0/C1 control bytes before render. " +
            "Untrusted-content-in-a-trusted-costume is the whole class. Full notes + PoC on request.",
            3 * day),
          post("ghostframe",
            "Clean find. This is why I render every dynamic string through an escaper that whitelists printable + newline and nothing else. The moment you allow raw control bytes, the terminal is the attacker's canvas.",
            2 * day + 6 * hr),
          post("stracectl",
            "Did the program pay out or was it OOS as 'self-XSS in a terminal'? Curious how the triage went.",
            2 * day),
          post("beardedfreedom",
            "Triaged as Low — real but limited blast radius since it needed a local file. Still got a swag credit and, more importantly, the sanitizer shipped. Defender-first; the bounty's a bonus.",
            1 * day + 18 * hr)
        ])
    ];

    return { version: 1, boards: boards, threads: threads };
  }

  /* ----------------------------------------------------------------------- */
  /* Persistence                                                              */
  /* ----------------------------------------------------------------------- */

  var memoryFallback = null; // used only if localStorage is unavailable

  function load() {
    var raw = null;
    try { raw = window.localStorage.getItem(STORE_KEY); }
    catch (e) { /* localStorage blocked (rare under file://) */ }

    if (raw) {
      try {
        var parsed = JSON.parse(raw);
        if (parsed && parsed.boards && parsed.threads) return parsed;
      } catch (e) { /* corrupt — fall through to reseed */ }
    }

    if (memoryFallback) return memoryFallback;

    var fresh = seed();
    save(fresh);
    return fresh;
  }

  function save(state) {
    memoryFallback = state;
    try { window.localStorage.setItem(STORE_KEY, JSON.stringify(state)); }
    catch (e) { /* keep working from memoryFallback this session */ }
  }

  function resetToSeed() {
    try { window.localStorage.removeItem(STORE_KEY); } catch (e) {}
    memoryFallback = null;
    DB = load();
  }

  var DB = load();

  /* lookups */
  function getBoard(id) {
    return DB.boards.filter(function (b) { return b.id === id; })[0] || null;
  }
  function getThread(id) {
    return DB.threads.filter(function (t) { return t.id === id; })[0] || null;
  }
  function threadsForBoard(boardId) {
    return DB.threads
      .filter(function (t) { return t.boardId === boardId; })
      .sort(function (a, b) { return lastActivity(b) - lastActivity(a); });
  }
  function lastActivity(thread) {
    if (!thread.posts.length) return thread.created;
    return thread.posts[thread.posts.length - 1].created;
  }

  /* ----------------------------------------------------------------------- */
  /* Routing                                                                  */
  /* ----------------------------------------------------------------------- */

  function parseRoute() {
    var h = window.location.hash.replace(/^#\/?/, "");
    var parts = h.split("/").filter(Boolean);
    if (parts[0] === "board" && parts[1]) return { name: "board", id: parts[1] };
    if (parts[0] === "thread" && parts[1]) return { name: "thread", id: parts[1] };
    if (parts[0] === "new" && parts[1]) return { name: "new", id: parts[1] };
    return { name: "home" };
  }

  function go(hash) {
    if (window.location.hash === hash) { render(); }
    else { window.location.hash = hash; }
  }

  /* ----------------------------------------------------------------------- */
  /* View builders                                                            */
  /* ----------------------------------------------------------------------- */

  var root, crumbs;

  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

  function setCrumbs(trail) {
    clear(crumbs);
    trail.forEach(function (c, i) {
      if (i > 0) crumbs.appendChild(el("span", { className: "crumb-sep", text: "/" }));
      if (c.href) {
        crumbs.appendChild(el("a", { text: c.label, attrs: { href: c.href } }));
      } else {
        crumbs.appendChild(el("span", { className: "crumb-current", text: c.label }));
      }
    });
  }

  /* ---- HOME: board list ---- */
  function viewHome() {
    setCrumbs([{ label: "forum" }]);

    var grid = el("div", { className: "card-grid" });

    DB.boards.forEach(function (board, i) {
      var ts = threadsForBoard(board.id);
      var postCount = ts.reduce(function (n, t) { return n + t.posts.length; }, 0);
      var latest = ts.length ? lastActivity(ts[0]) : board.created;

      var card = el("article", { className: "card card--link", attrs: { tabindex: "0", role: "link" } });

      var idx = el("span", { className: "card__index", text: "[ " + String(i + 1).padStart(2, "0") + " ]" });

      var titleRow = el("div", { className: "card__title-row", children: [
        el("h2", { className: "card__title", text: board.name }),
        el("span", { className: "badge", text: plural(ts.length, "thread") })
      ]});

      var desc = el("p", { className: "card__desc", text: board.blurb });

      var meta = el("div", { className: "board-meta", children: [
        el("span", { text: plural(postCount, "post") }),
        el("span", { children: [
          document.createTextNode("last activity "),
          el("span", { className: "text-amber", text: ts.length ? timeAgo(latest) : "—" })
        ]})
      ]});

      card.appendChild(idx);
      card.appendChild(titleRow);
      card.appendChild(desc);
      card.appendChild(meta);

      function open() { go("#/board/" + board.id); }
      card.addEventListener("click", open);
      card.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); }
      });

      grid.appendChild(card);
    });

    root.appendChild(el("span", { className: "forum-section-label", text: "boards" }));
    root.appendChild(grid);
  }

  /* ---- BOARD: thread list ---- */
  function viewBoard(boardId) {
    var board = getBoard(boardId);
    if (!board) { go("#/"); return; }

    setCrumbs([
      { label: "forum", href: "#/" },
      { label: board.name }
    ]);

    // toolbar
    var toolbar = el("div", { className: "forum-toolbar" });
    toolbar.appendChild(headingBlock(board.name, board.blurb));
    var spacer = el("span", { className: "spacer" });
    var newBtn = el("a", { className: "btn btn--primary", text: "> NEW THREAD",
      attrs: { href: "#/new/" + board.id } });
    toolbar.appendChild(spacer);
    toolbar.appendChild(newBtn);
    root.appendChild(toolbar);

    var ts = threadsForBoard(boardId);

    if (!ts.length) {
      root.appendChild(emptyPanel("no threads on this board yet — be the first to post"));
      return;
    }

    var stack = el("div", { className: "forum-stack" });
    ts.forEach(function (t) {
      var op = t.posts[0];
      var row = el("article", {
        className: "panel card--link thread-row",
        attrs: { tabindex: "0", role: "link", "data-title": t.boardId === "ctf-bounty" ? "ctf" : "thread" }
      });

      row.appendChild(el("h3", { className: "thread-title", text: t.title }));
      if (op) {
        row.appendChild(el("p", { className: "thread-excerpt", text: op.body }));
      }
      row.appendChild(el("div", { className: "thread-meta", children: [
        el("span", { children: [
          document.createTextNode("by "),
          el("span", { className: "text-amber", text: op ? op.author : "anon" })
        ]}),
        el("span", { text: plural(t.posts.length, "post") }),
        el("span", { children: [
          document.createTextNode("last reply "),
          el("span", { className: "text-amber", text: timeAgo(lastActivity(t)) })
        ]})
      ]}));

      function open() { go("#/thread/" + t.id); }
      row.addEventListener("click", open);
      row.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); }
      });
      stack.appendChild(row);
    });
    root.appendChild(stack);
  }

  /* ---- THREAD: posts + reply form ---- */
  function viewThread(threadId) {
    var t = getThread(threadId);
    if (!t) { go("#/"); return; }
    var board = getBoard(t.boardId);

    setCrumbs([
      { label: "forum", href: "#/" },
      { label: board ? board.name : "board", href: "#/board/" + t.boardId },
      { label: t.title }
    ]);

    root.appendChild(headingBlock(t.title,
      "started " + timeAgo(t.created) + " · " + plural(t.posts.length, "post")));

    var stack = el("div", { className: "forum-stack", attrs: { style: "margin-top: var(--sp-5);" } });
    t.posts.forEach(function (p, i) {
      stack.appendChild(buildPost(p, i === 0));
    });
    root.appendChild(stack);

    /* reply form */
    root.appendChild(el("span", { className: "forum-section-label", text: "add a reply" }));
    root.appendChild(buildReplyForm(t));
  }

  function buildPost(p, isOp) {
    var head = el("div", { className: "post__head" });
    head.appendChild(el("span", { className: "post__author", text: p.author }));
    if (isOp) head.appendChild(el("span", { className: "post__op-tag", text: "[ OP ]" }));
    head.appendChild(el("span", { text: timeAgo(p.created) }));

    var body = el("p", { className: "post__body", text: p.body });

    return el("article", { className: "panel post", attrs: { "data-title": isOp ? "op" : "reply" },
      children: [head, body] });
  }

  function buildReplyForm(thread) {
    var form = el("form", { className: "panel", attrs: { novalidate: "novalidate" } });

    // author
    var authField = el("div", { className: "field" });
    authField.appendChild(el("label", { className: "field__label", text: "handle",
      attrs: { for: "reply-author" } }));
    var authInput = el("input", { className: "input", attrs: {
      id: "reply-author", type: "text", maxlength: "32",
      placeholder: "anon", autocomplete: "off" } });
    authField.appendChild(authInput);

    // body
    var bodyField = el("div", { className: "field" });
    bodyField.appendChild(el("label", { className: "field__label", text: "reply",
      attrs: { for: "reply-body" } }));
    var bodyInput = el("textarea", { className: "textarea", attrs: {
      id: "reply-body", maxlength: "4000",
      placeholder: "> drop your two cents…" } });
    bodyField.appendChild(bodyInput);
    bodyField.appendChild(el("p", { className: "field__hint",
      text: "Plain text only. Markup is escaped on render — this is a security forum." }));

    var errBox = el("p", { className: "form-error", attrs: { role: "alert" } });

    var submit = el("button", { className: "btn btn--primary", text: "> POST REPLY",
      attrs: { type: "submit" } });
    var actions = el("div", { className: "card__foot", children: [submit] });

    form.appendChild(authField);
    form.appendChild(bodyField);
    form.appendChild(errBox);
    form.appendChild(actions);

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      errBox.textContent = "";
      var body = bodyInput.value.trim();
      var author = authInput.value.trim() || "anon";
      if (!body) { errBox.textContent = "Reply body can't be empty."; bodyInput.focus(); return; }

      thread.posts.push({ id: uid(), author: author, body: body, created: Date.now() });
      save(DB);
      go("#/thread/" + thread.id);
      // after re-render, scroll the newest post into view
      window.requestAnimationFrame(function () {
        var posts = root.querySelectorAll(".post");
        if (posts.length) posts[posts.length - 1].scrollIntoView({ behavior: "smooth", block: "center" });
      });
    });

    return form;
  }

  /* ---- NEW THREAD form ---- */
  function viewNewThread(boardId) {
    var board = getBoard(boardId);
    if (!board) { go("#/"); return; }

    setCrumbs([
      { label: "forum", href: "#/" },
      { label: board.name, href: "#/board/" + boardId },
      { label: "new thread" }
    ]);

    root.appendChild(headingBlock("Start a thread in " + board.name,
      "Posts to this board stay on your device. Keep it sharp and on-topic."));

    var form = el("form", { className: "panel", attrs: { novalidate: "novalidate", style: "margin-top: var(--sp-5);" } });

    var titleField = el("div", { className: "field" });
    titleField.appendChild(el("label", { className: "field__label", text: "thread title",
      attrs: { for: "nt-title" } }));
    var titleInput = el("input", { className: "input", attrs: {
      id: "nt-title", type: "text", maxlength: "120", autocomplete: "off",
      placeholder: "e.g. New env var in the latest build?" } });
    titleField.appendChild(titleInput);

    var authField = el("div", { className: "field" });
    authField.appendChild(el("label", { className: "field__label", text: "handle",
      attrs: { for: "nt-author" } }));
    var authInput = el("input", { className: "input", attrs: {
      id: "nt-author", type: "text", maxlength: "32", autocomplete: "off",
      placeholder: "anon" } });
    authField.appendChild(authInput);

    var bodyField = el("div", { className: "field" });
    bodyField.appendChild(el("label", { className: "field__label", text: "opening post",
      attrs: { for: "nt-body" } }));
    var bodyInput = el("textarea", { className: "textarea", attrs: {
      id: "nt-body", maxlength: "4000",
      placeholder: "> lay it out — what did you find, what's the question…" } });
    bodyField.appendChild(bodyInput);
    bodyField.appendChild(el("p", { className: "field__hint",
      text: "Plain text only. Markup is escaped on render." }));

    var errBox = el("p", { className: "form-error", attrs: { role: "alert" } });

    var submit = el("button", { className: "btn btn--primary", text: "> CREATE THREAD",
      attrs: { type: "submit" } });
    var cancel = el("a", { className: "btn btn--ghost", text: "cancel",
      attrs: { href: "#/board/" + boardId } });
    var actions = el("div", { className: "card__foot", attrs: { style: "display:flex; gap: var(--sp-3);" },
      children: [submit, cancel] });

    form.appendChild(titleField);
    form.appendChild(authField);
    form.appendChild(bodyField);
    form.appendChild(errBox);
    form.appendChild(actions);

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      errBox.textContent = "";
      var title = titleInput.value.trim();
      var body = bodyInput.value.trim();
      var author = authInput.value.trim() || "anon";
      if (!title) { errBox.textContent = "A thread needs a title."; titleInput.focus(); return; }
      if (!body) { errBox.textContent = "The opening post can't be empty."; bodyInput.focus(); return; }

      var thread = {
        id: uid(),
        boardId: boardId,
        title: title,
        created: Date.now(),
        posts: [{ id: uid(), author: author, body: body, created: Date.now() }]
      };
      DB.threads.push(thread);
      save(DB);
      go("#/thread/" + thread.id);
    });

    root.appendChild(form);

    window.requestAnimationFrame(function () { titleInput.focus(); });
  }

  /* ---- shared small builders ---- */
  function headingBlock(title, sub) {
    var wrap = el("div");
    wrap.appendChild(el("h2", { className: "prompt", text: title }));
    if (sub) wrap.appendChild(el("p", { className: "text-muted", attrs: { style: "margin:0;" }, text: sub }));
    return wrap;
  }

  function emptyPanel(msg) {
    var panel = el("div", { className: "panel", attrs: { "data-title": "empty" } });
    panel.appendChild(el("p", { className: "empty-state", text: msg }));
    return panel;
  }

  /* ----------------------------------------------------------------------- */
  /* Render dispatch                                                          */
  /* ----------------------------------------------------------------------- */

  function render() {
    clear(root);
    var r = parseRoute();
    switch (r.name) {
      case "board":  viewBoard(r.id); break;
      case "thread": viewThread(r.id); break;
      case "new":    viewNewThread(r.id); break;
      default:       viewHome();
    }
    // keep the page anchored near the top of #main on navigation
    if (r.name !== "home") {
      var main = document.getElementById("main");
      if (main && main.scrollIntoView) {
        // only nudge if we're scrolled past the heading
        if (window.scrollY > 240) main.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
  }

  /* ----------------------------------------------------------------------- */
  /* Boot                                                                     */
  /* ----------------------------------------------------------------------- */

  function init() {
    root = document.getElementById("forum-root");
    crumbs = document.getElementById("forum-crumbs");
    if (!root) return;

    window.addEventListener("hashchange", render);

    var resetLink = document.getElementById("forum-reset");
    if (resetLink) {
      resetLink.addEventListener("click", function (e) {
        e.preventDefault();
        var ok = window.confirm(
          "Reset all boards to the seed dataset?\nThis wipes every thread and reply you've posted on this device.");
        if (ok) { resetToSeed(); go("#/"); render(); }
      });
    }

    render();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
