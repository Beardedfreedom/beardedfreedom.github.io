# STYLE-CONTRACT.md — Claude Code Internals

> The single source of truth for visual consistency.
> **The changelog Anthropic doesn't publish.**
>
> Site: `beardedfreedom.online` · Author persona: **beardedfreedom**
> (HackerOne security researcher & USAF veteran).
> Audience: developers & power users of Claude Code (the CLI).

Every page on this site MUST be byte-identical in its shell (head / nav / footer).
If your page diverges from the snippets below, it is wrong — not the contract.
This file was authored alongside `games.html`, which is the reference
implementation. When in doubt, diff against `games.html`.

---

## 0. Non-negotiable rules

1. **Vanilla only.** HTML + CSS + JS. No frameworks, no build step, no bundler.
   Exactly **one** Google Fonts `<link>` block (the 3-line preconnect+stylesheet
   set below counts as the allowed block — do not add more font requests).
2. **Link the shared system, never inline a fork.** Every page links
   `/assets/css/theme.css` and loads `/assets/js/nav.js`. Do not copy CSS into
   a page `<style>` block except for trivial one-off layout nudges using the
   existing CSS custom properties (e.g. `style="margin-top: var(--sp-6);"`).
3. **Root-absolute asset paths.** Always `/assets/css/theme.css`,
   `/assets/js/nav.js`, `/index.html`, `/games.html`, etc. — leading slash.
   This is mandatory because game pages live one level deep (`/games/*.html`);
   relative paths would 404 the stylesheet there. Page-to-page links are also
   root-absolute (`/forum.html`), EXCEPT the three game cards on the hub, which
   link `games/flag-hunter.html` style (relative, same directory) — that is the
   only sanctioned relative exception and it only appears on `games.html`.
4. **Title token.** Only the page name varies in `<title>`. Format is exactly:
   `PAGE NAME — Claude Code Internals` (em dash `—`, U+2014). Replace the
   `__PAGE__` slot, change nothing else in the head.
5. **Semantic landmarks required.** `<header>` wraps the nav, `<main id="main">`
   wraps page content, `<footer>` is the footer. The skip-link targets `#main`.
6. **Accessibility is part of the brand.** Do not remove focus outlines without a
   replacement — `theme.css` already supplies a visible amber `:focus-visible`
   ring. Keep it. Maintain contrast; use the tokens, not ad-hoc colors.
7. **Tone of copy.** Sharp, technical, a little playful. Never corny, never
   generic-AI-startup. `[bracketed]` labels and `>` prompts are house style.
8. **No reference to Anthropic affiliation.** Footer states "unaffiliated with
   Anthropic." Keep it.

---

## 1. Page skeleton (assemble in this order)

```
<!DOCTYPE html>
<html lang="en">
<head> … HEAD BLOCK (§2) … </head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header"> … NAV BLOCK (§3) … </header>
  <main id="main">
    …YOUR PAGE CONTENT…
  </main>
  <footer class="site-footer"> … FOOTER BLOCK (§4) … </footer>
</body>
</html>
```

---

## 2. EXACT `<head>` block — copy/paste verbatim

Replace only `__PAGE__` (in `<title>`) and the `<meta name="description">`
content. Everything else is byte-frozen.

```html
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__PAGE__ — Claude Code Internals</title>
  <meta name="description" content="__ONE-LINE PAGE DESCRIPTION__">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,400;0,700;0,800;1,400&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/assets/css/theme.css">
  <script src="/assets/js/nav.js" defer></script>
</head>
```

---

## 3. EXACT `<nav>` block — copy/paste verbatim

Identical on every page (HOME, FORUM, GAMES, SUBSCRIBE, ABOUT — same order).
Do **not** add/remove/reorder items. `nav.js` sets `aria-current="page"`
automatically by matching `location.pathname`, so you do **not** hardcode the
active state. SUBSCRIBE always points at `/index.html#subscribe` so it works
identically from every page (including the index itself).

```html
    <nav class="nav" aria-label="Primary">
      <a class="nav__brand" href="/index.html">
        <span class="sigil">&gt;_</span> claude code <b>internals</b>
      </a>
      <button class="nav__toggle" aria-expanded="false" aria-controls="nav-menu">[ menu ]</button>
      <ul class="nav__list" id="nav-menu">
        <li><a class="nav__link" href="/index.html">HOME</a></li>
        <li><a class="nav__link" href="/forum.html">FORUM</a></li>
        <li><a class="nav__link" href="/games.html">GAMES</a></li>
        <li><a class="nav__link" href="/illuminate.html">HUNT</a></li>
        <li><a class="nav__link" href="/skills.html">SKILLS</a></li>
        <li><a class="nav__link" href="/index.html#subscribe">SUBSCRIBE</a></li>
        <li><a class="nav__link" href="/about.html">ABOUT</a></li>
      </ul>
    </nav>
```

The `<nav>` must sit inside `<header class="site-header"> … </header>`.

---

## 4. EXACT `<footer>` block — copy/paste verbatim

Identical on every page.

```html
  <footer class="site-footer">
    <div class="container">
      <span class="site-footer__brand"><span class="sigil">&gt;_</span> claude code internals</span>
      <span class="site-footer__tag">The changelog Anthropic doesn't publish.</span>
      <span class="site-footer__meta">
        by <a href="/about.html">beardedfreedom</a> · unaffiliated with Anthropic · &copy; 2026
      </span>
    </div>
  </footer>
```

---

## 5. Design tokens (from `theme.css` — use these, never raw hex)

| Token | Value | Use |
|---|---|---|
| `--bg` | `#0a0e0b` | page background (near-black) |
| `--panel` | `#11161a` | raised panels / cards |
| `--panel-2` | `#0d1215` | recessed fields |
| `--green` | `#3df58b` | primary terminal green |
| `--green-dim` | `#2bbf6a` | pressed / secondary green |
| `--amber` | `#ffb000` | accent / link-hover / focus ring |
| `--muted` | `#8aa39b` | secondary text |
| `--danger` | `#ff5c5c` | errors / destructive |
| `--ink` | `#e6f1ea` | primary near-white text |
| `--line` / `--line-strong` / `--line-faint` | rgba green | 1px borders |
| `--mono` | `"JetBrains Mono", ui-monospace, Menlo, …` | all type |

Type scale: `--fs-300` (12px) → `--fs-900` (~42px).
Spacing: `--sp-1` (4px) → `--sp-8` (64px). Radius: `--radius` (4px).
Content column: `--maxw` (1080px). Nav height: `--nav-h` (56px).

---

## 6. Component cheat-sheet (all defined in `theme.css`)

Use these classes; do not reinvent them.

- **Container / sections:** `.container`, `.section`, `.section--tight`
- **Eyebrow label:** `<span class="eyebrow">label</span>` → renders `[ LABEL ]`
- **Prompt prefix:** add `.prompt` to a heading → prepends green `> `
- **Blinking cursor:** `<span class="cursor" aria-hidden="true"></span>`
- **Panel (TUI box):** `<div class="panel" data-title="exec"> … </div>`
  (the `data-title` is optional and draws an inset `[exec]` tab)
- **Buttons:** `.btn` plus a variant — `.btn--primary` (green),
  `.btn--accent` (amber), `.btn--ghost` (muted), `.btn--block` (full width).
  Play/CTA buttons use the literal label `> PLAY`, `> SUBSCRIBE`, etc.
- **Card grid:** `<div class="card-grid">` of `<article class="card">` with
  `.card__index` (`[ 01 ]`), `.card__title`, `.card__desc`, `.card__foot`.
- **Forms:** `.field` › `.field__label` + `.input` / `.textarea` / `.select`,
  `.field__hint`, `.input-row` for inline email+button rows.
- **Badges:** `.badge`, `.badge--amber`, `.badge--danger`.
- **Text helpers:** `.lead`, `.text-muted`, `.text-amber`, `.text-danger`.
- **Spacing helpers:** `.stack` (16px rhythm), `.flow` (24px rhythm).
- **A11y:** `.skip-link`, `.sr-only`.

The scanline/CRT overlay and the blink/flicker keyframes are global and
automatic — you do not add markup for them.

---

## 7. Mobile behavior (handled for you)

Below 720px the nav collapses behind the `[ menu ]` toggle button.
`nav.js` toggles `data-open="true"` on `.nav__list`. Do not rebuild this — just
ship the exact nav markup from §3 and it works.

---

## 8. Conformance checklist (run before you ship a page)

- [ ] Head block is byte-identical to §2 except `__PAGE__` + description.
- [ ] `<title>` uses the em-dash form: `Name — Claude Code Internals`.
- [ ] Nav block is byte-identical to §3, inside `<header class="site-header">`.
- [ ] Footer block is byte-identical to §4.
- [ ] All asset/page links are root-absolute (leading `/`), except same-dir
      game-card links on the hub.
- [ ] `<main id="main">` wraps content; skip-link present.
- [ ] No second font request; no inlined copy of `theme.css`.
- [ ] Colors come from tokens, not raw hex.
- [ ] Focus ring intact (didn't kill `:focus-visible`).
- [ ] Copy is sharp/technical, uses `[brackets]` + `>` house style, not corny.
```
