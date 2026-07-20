/* skills.js — Claude Code Internals :: skills registry
 * Loads the public manifest, renders a searchable category list, and shows
 * source for the selected skill through CODE / ILLUMINATE / RAINBOW lenses
 * (reusing window.CCI from illuminate.js). XSS-safe: textContent only.
 */
(function () {
  "use strict";

  function el(tag, cls, txt) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (txt != null) n.textContent = txt;
    return n;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var listEl = document.getElementById("sk-list");
    var search = document.getElementById("sk-search");
    var titleEl = document.getElementById("sk-title");
    var metaEl = document.getElementById("sk-meta");
    var outEl = document.getElementById("sk-source");
    var lensWrap = document.getElementById("sk-lenses");
    var countEl = document.getElementById("sk-count");
    if (!listEl) return;

    var ALL = [], current = null, currentText = "", lens = 0;
    var LENSES = ["CODE", "ILLUMINATE", "RAINBOW"];

    function renderSource() {
      outEl.textContent = "";
      if (current == null) {
        outEl.appendChild(el("p", "text-muted", "Select a skill to view its source."));
        return;
      }
      if (lens === 2 && window.CCI) {
        window.CCI.renderRainbow(currentText, outEl);
      } else if (lens === 1 && window.CCI) {
        var p = el("pre", "ill-out"); p.textContent = window.CCI.illuminate(currentText); outEl.appendChild(p);
      } else {
        var c = el("pre", "ill-out"); c.textContent = currentText; outEl.appendChild(c);
      }
    }

    function select(skill, node) {
      var nodes = listEl.querySelectorAll(".sk-item");
      for (var i = 0; i < nodes.length; i++) nodes[i].classList.remove("on");
      if (node) node.classList.add("on");
      current = skill;
      titleEl.textContent = skill.title;
      metaEl.textContent = "";
      metaEl.appendChild(el("span", "badge", skill.category));
      metaEl.appendChild(el("span", "text-muted", " " + skill.lines + " lines · " + skill.id));
      outEl.textContent = "";
      outEl.appendChild(el("p", "text-muted", "loading source…"));
      lensWrap.hidden = false;
      fetch(skill.src).then(function (r) { return r.text(); }).then(function (t) {
        currentText = t; renderSource();
      }).catch(function () {
        outEl.textContent = ""; outEl.appendChild(el("p", "text-danger", "Could not load source."));
      });
    }

    function renderList(filter) {
      listEl.textContent = "";
      var f = (filter || "").toLowerCase();
      var byCat = {};
      ALL.forEach(function (s) {
        if (f && (s.title + " " + s.desc + " " + s.id + " " + s.category).toLowerCase().indexOf(f) === -1) return;
        (byCat[s.category] = byCat[s.category] || []).push(s);
      });
      var cats = Object.keys(byCat).sort();
      if (!cats.length) { listEl.appendChild(el("p", "text-muted", "No skills match.")); return; }
      cats.forEach(function (cat) {
        var h = el("div", "sk-cat", cat + " (" + byCat[cat].length + ")");
        listEl.appendChild(h);
        byCat[cat].forEach(function (s) {
          var item = el("button", "sk-item");
          item.type = "button";
          item.dataset.id = s.id;
          item.appendChild(el("span", "sk-item__title", s.title));
          item.appendChild(el("span", "sk-item__desc", s.desc));
          item.addEventListener("click", function () { select(s, item); });
          listEl.appendChild(item);
        });
      });
    }

    // lens buttons
    LENSES.forEach(function (name, i) {
      var b = el("button", "btn btn--ghost sk-lens", "> " + name);
      if (i === 0) b.classList.add("on");
      b.type = "button";
      b.addEventListener("click", function () {
        lens = i;
        var bs = lensWrap.querySelectorAll(".sk-lens");
        for (var k = 0; k < bs.length; k++) bs[k].classList.remove("on");
        b.classList.add("on");
        renderSource();
      });
      lensWrap.appendChild(b);
    });
    lensWrap.hidden = true;

    // deep-link: #<skill-id> or #<skill-id>/<lens>  (lens = code|illuminate|rainbow)
    function applyHash() {
      var raw = decodeURIComponent((location.hash || "").replace(/^#/, ""));
      if (!raw) return;
      var parts = raw.split("/"), id = parts[0], lensName = (parts[1] || "").toLowerCase();
      var skill = null;
      for (var i = 0; i < ALL.length; i++) if (ALL[i].id === id) { skill = ALL[i]; break; }
      if (!skill) return;
      var li = { code: 0, illuminate: 1, rainbow: 2 };
      if (lensName in li) {
        lens = li[lensName];
        var bs = lensWrap.querySelectorAll(".sk-lens");
        for (var k = 0; k < bs.length; k++) bs[k].classList.toggle("on", k === lens);
      }
      var node = listEl.querySelector('[data-id="' + id + '"]');
      select(skill, node);
      if (node && node.scrollIntoView) node.scrollIntoView({ block: "nearest" });
    }

    fetch("/skills.json").then(function (r) { return r.json(); }).then(function (d) {
      ALL = d.skills || [];
      countEl.textContent = d.public_count + " public skills · " + d.private_count + " held in the private arsenal";
      renderList("");
      applyHash();
      window.addEventListener("hashchange", applyHash);
    }).catch(function () {
      listEl.appendChild(el("p", "text-danger", "Could not load skills.json (serve the site over HTTP, not file://)."));
    });

    if (search) search.addEventListener("input", function () { renderList(search.value); });
    renderSource();
  });
})();
