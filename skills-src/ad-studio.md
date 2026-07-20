---
name: ad-studio
description: >
  Build a polished AI product commercial / promo / pitch video from 3D renders or product
  photos. Use this WHENEVER Steven wants a commercial, ad, promo video, hype reel, pitch
  video, "make a 30 second video", marketing clip, or product-in-use footage — especially
  when starting from Blender renders, product stills, or a concept image. Codifies the proven
  pipeline: renders → Higgsfield photoreal stills → real image-to-video (Kling/Seedance) →
  ffmpeg assembly → ElevenLabs voiceover. ALWAYS prefer this over hand-rolling, and ALWAYS
  generate REAL motion video (image-to-video) rather than retreating to Ken Burns pans on
  stills — the motion tools work, you just have to pick the right model per shot.
---

# Ad-Studio — AI Product Commercial Pipeline

Turn renders/photos into a finished commercial. Five stages: **stills → motion → voiceover →
assemble → deliver.** Each stage has a tool that works; the lessons below are paid for in
real failures, so honor them.

## The Prime Directive (read first)
**Generate real motion video. Do NOT fall back to Ken Burns zoom-on-stills unless every video
model genuinely refuses the shot.** Earlier, one Seedance refusal was wrongly treated as "video
is impossible," and a whole commercial got built from still-pans — a waste. The fix was one line:
use the right model per shot (below). Always exhaust the real i2v path first.

## Prereqs (verify once)
- `higgsfield` CLI authed: `higgsfield account status` (ultra plan). Models: `higgsfield model list --json`.
- `ELEVENLABS_API_KEY` env var set (`[ -n "$ELEVENLABS_API_KEY" ]`).
- `ffmpeg` + `ffprobe`. **This ffmpeg has NO `drawtext`** (`ffmpeg -filters | grep drawtext` → empty),
  so on-screen text is done as transparent PNG overlays via PIL, never drawtext.
- `python3` with PIL/Pillow (for text overlays / end cards).

---

## Stage 1 — Photoreal stills (Higgsfield, image-to-image)
Use **Nano Banana Pro** (`nano_banana_2`) with `--image <render-or-photo>` to turn a Blender
render / concept image into a photoreal still while preserving the design. This is the
`higgsfield-generate` skill under the hood; for full options read that skill.

```bash
higgsfield generate create nano_banana_2 \
  --image /path/to/render.png \
  --prompt "Hyper-realistic <shot>. Preserve the exact design from the reference. <materials/lighting/lens>, photoreal." \
  --aspect_ratio 16:9 --wait --wait-timeout 12m | tail -2     # prints the result URL
```
Then `curl -s -o still.png "<url>"`. Prompt rules that matter:
- Always say **"Preserve the exact design/geometry from the reference"** — keeps the product on-model.
- **Proportions are a first-class requirement.** If a person holds the product, state the real
  scale explicitly ("handheld paddle, sign about as wide as the guard's head, gripped in one
  hand, normal human scale, NOT oversized"). Getting this wrong is the #1 reshoot cause.
- For a cut, generate a **shot list** of distinct stills (open / detail / hero / payoff / heroic)
  so the edit isn't repetitive. 16:9 for commercials; verify with the still before committing.
- **Transient `failed` / 502 / 504 are normal** — just retry the same call. A shorter prompt
  sometimes clears a stubborn `failed`.

## Stage 2 — Real motion (image-to-video) — PICK THE MODEL BY SUBJECT
| Shot subject | Model | Flag | Why |
|---|---|---|---|
| **People / faces** (guard, crowd, hands) | **`kling3_0`** | `--start-image` | Passes the content filter that Seedance trips |
| **Device / object / no face** | `seedance_2_0` | `--start-image` (16:9, `--resolution 720p`, `--genre epic`) | Great object motion |
| Generic / fallback | `veo3_1` | `--image` | Different filter, try if others refuse |

```bash
higgsfield generate create kling3_0 \
  --start-image still.png \
  --prompt "<motion>: LEDs flash, rain falls, the guard holds steady, slow cinematic push-in. Photoreal." \
  --wait --wait-timeout 20m | tail -1            # prints the .mp4 URL → curl it down
```
**The IP-filter lesson:** Seedance returns status **`ip_detected`** on realistic *people* (esp. at
1080p) and **`failed`** on unsupported param combos (e.g. 3:4 @ 1080p). That is NOT "video is off
the table" — it's "wrong model/params for this shot." Kling 3.0 animates people fine. Route by
subject and you'll get real footage every time. Clips come out ~5s, ~24fps, sometimes portrait
if the source was portrait — Stage 4 normalizes that.

## Stage 3 — Voiceover (ElevenLabs) — fill the whole duration
A 30s spot needs ~26–28s of narration, not a 10s blurb with 20s of silence. Write a real **pitch
script** (what it is, who it's for, the benefit, a closing tagline) sized to the runtime.
Default voice: **Brian** `nPczCjzI2devNBz1zQrb` (deep, reassuring); list others with
`curl -s -H "xi-api-key: $ELEVENLABS_API_KEY" https://api.elevenlabs.io/v1/voices`.
Spell out acronyms phonetically ("L E Ds") so they read naturally.

```bash
curl -s -X POST "https://api.elevenlabs.io/v1/text-to-speech/nPczCjzI2devNBz1zQrb?output_format=mp3_44100_128" \
  -H "xi-api-key: $ELEVENLABS_API_KEY" -H "Content-Type: application/json" \
  -d '{"text":"<pitch script>","model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.5,"similarity_boost":0.8,"style":0.3}}' \
  -o vo.mp3
ffmpeg -y -i vo.mp3 -ar 48000 -ac 2 vo.wav     # then ffprobe its duration; aim ~26–28s for a :30
```
Rough pacing for Brian: ~60–68 words ≈ 26s. Generate, measure, trim words if it overruns.
**Do NOT use macOS `say` in a voice-detection loop** — `say -v "?"` piped in a `for` loop has hung
the build. If you must use `say`, call it without the lookup loop.

## Stage 4 — Assemble (ffmpeg) — use the bundled script
`scripts/assemble_commercial.sh` does the whole cut: normalizes mixed clips, adds slow-mo,
crossfades, optional text overlays, and muxes the VO to an exact runtime. Read its header for args.

```bash
bash ~/.claude/skills/ad-studio/scripts/assemble_commercial.sh \
  --out /path/out.mp4 --vo vo.wav --vo-start 1.5 --total 30 \
  --clips "clipA.mp4 clipB.mp4 clipC.mp4 clipD.mp4 clipE.mp4" \
  --endcard endcard.png            # optional; omit for no end card
  # --overlays "0:6.4:11.5:t1.png 2:17.5:22.8:t2.png"  optional: idx:start:end:png
```
Why the script's choices matter:
- **Normalize with force-cover** (`scale=W:H:force_original_aspect_ratio=increase,crop=W:H`) so a
  stray **portrait clip never crashes the 16:9 crop** (a real failure: a 3:4 clip killed a build).
- **1.2× slow-mo** (`setpts=1.2*PTS`) gives the cinematic feel and helps clips reach :30.
- **xfade** chain for crossfades; `fadeblack` into the end card.
- **Captions are OPTIONAL** — Steven often prefers clean footage with VO carrying the message.
  Only add overlays if asked. Text overlays are PNGs (no drawtext); make them with
  `scripts/make_overlay.py`.

## Stage 5 — Deliver
Send the .mp4 with `SendUserFile`. Save a frame check first (`ffmpeg -ss <t> -i out.mp4 -vframes 1
chk.png`) and look at it to confirm proportions/text/composition before delivering.

---

## Hard-won lessons (the difference between a pro result and a waste of tokens)
1. **Real motion, not still-pans.** Route shots: Kling=people, Seedance=objects, Veo=fallback.
2. **Proportions first.** Wrong product scale relative to a person = guaranteed reshoot. State the
   real handheld/standing scale in the still prompt.
3. **VO fills the runtime.** A pitch script, sized to the cut, beats a short blurb + dead air.
4. **Regenerate the VO mix per cut.** A shared `vomix.wav` gets overwritten by the next build —
   build each cut's audio fresh (the script does this; if hand-rolling, don't reuse the file).
5. **Force-cover normalize** every clip; never assume uniform dimensions/orientation.
6. **`-map "[label]"` is required** when a filter_complex output is labeled, or ffmpeg errors with
   "output unconnected."
7. **Retry transient Higgsfield errors** (502/504/`failed`) — they're flaky, not fatal.
8. **Music is the last 10%.** These spots ship with VO only; offer to mux a music bed (ducked under
   the VO) when the user provides/approves a track. Don't add copyrighted music unprompted.
9. **Frame-check before delivering.** One extracted frame catches bad proportions, missing text,
   or a botched crop before the user sees it.

## Typical 6-beat :30 structure (adapt freely)
open (hook / hero of the product) → detail/feature → hero feature macro → human/benefit payoff →
heroic reprise → end card (logo + tagline). ~5–6s each, slowed to ~6s, xfaded, VO over the top.
