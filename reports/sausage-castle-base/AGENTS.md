# Working on Florida Freedom World (for Codex, Gemini and other coding agents)

This folder is the whole build for the Sausage Castle estate (22500 Robbins Road, Astatula, FL,
about 120 acres) and the Florida Freedom World theme-park concept drawn on it. Read `README.md`
in this folder for the full story of every file; this page is the short version for picking up work.

## Where it lives

- Repository: `Beardedfreedom/beardedfreedom.github.io`
- Branch: `claude/sharp-lamport-adogq3` (draft pull request #2 into `main`)
- Folder: `reports/sausage-castle-base/` (everything below is relative to it)
- The encrypted review copy is in `review/` at the repository root (built from this folder).

Start each agent on its own branch made from `claude/sharp-lamport-adogq3`, for example
`codex/<task>` or `gemini/<task>`, and open a pull request back into `claude/sharp-lamport-adogq3`.
Do not push to `main`, and do not rewrite history on the shared branch.

## Ground rules

- **Keep it private.** The project is confidential. Never post files from `reports/` anywhere public,
  never add analytics, trackers or third-party embeds, and keep `reports/` excluded from the GitHub
  Pages build (`_config.yml` at the repository root).
- **The review password is not in the repository and must never be committed.** Rebuilding `review/`
  needs it from the owner (`REVIEW_PASSWORD=... python3 scripts/build_review.py`).
- Coordinates: NAD83 Florida East, US survey feet (EPSG:2236). The game and viewers use feet with the
  origin at the site centre; Blender uses metres.
- Large binaries (the `.blend`, videos, DXF) are committed on purpose; avoid adding new ones over
  about 15 MB without asking.

## Map of the build

| Path | What it is |
|---|---|
| `index.html` | The demo page (sections 01 to 06), with a print stylesheet used for the review PDF |
| `game/index.html` | Freedom World Walkabout: three.js r128 first-person game on the lidar replica |
| `game/data/` | `world.json` (buildings, trees, roads, water, cabins, attractions), ground heightmap, colour map |
| `scripts/game_world.py` | Builds `game/data/` from the site data |
| `scripts/blender_present.py` | Blender 5 (pip `bpy`) presentation model: stills, zone close-ups, turntable, `.glb` |
| `scripts/make_turntable.py` | PNG stills to JPEG, turntable frames to MP4 |
| `mockup/present/` | Presentation renders, turntable video, `.blend` |
| `viewer/`, `viewer3d/` | Terrain viewer and the interactive presentation model page |
| `focus/lakes/` | Lake zones concept, clearing and grading plan, full-resolution lidar products |
| `units/` | The four cabin types (mushroom, haunted, swamp stilt cabin, UFO saucer pod) with CAD sets |
| `masterplan/`, `brand/` | Twelve attraction areas mapped on the lidar base; the owner's poster |
| `scripts/build_review.py`, `scripts/export_pdf.js`, `scripts/encrypt_pdf.py` | Encrypted review site and PDF |

## Running things

    # the game and the demo page (any static server works)
    cd reports/sausage-castle-base && python3 -m http.server 8000
    # then open http://localhost:8000/game/index.html and http://localhost:8000/index.html

    # the presentation model (needs: pip install bpy==5.0.1 numpy scipy shapely ezdxf pillow imageio imageio-ffmpeg)
    python3 scripts/blender_present.py --base . --out mockup/present --renders --samples 128
    python3 scripts/make_turntable.py mockup/present --fps 24

The game has a director API for scripted, frame-stepped capture: `window.__director.on()`, `.pose({x,z,yaw,pitch})`,
`.frame(dt)`, `.route(ax,az,bx,bz)`, `.free(x,z)`. `window.__game.teleport('gate')` jumps to an attraction.

## AI-made 3D models

The detail models (cabins, the gator mascot and the gator statue) were made with Meshy through
Higgsfield and load at runtime from Higgsfield's CDN; see `MODELS` near the top of the main script in
`game/index.html`. They are not in the repository. If your environment can reach
`d2ol7oe51mr4n9.cloudfront.net` and `d8j0ntlcm91z4.cloudfront.net`, download them into `game/models/`,
compress with `npx @gltf-transform/cli@3 resize --width 1024 --height 1024`, then `webp`, then `meshopt`,
and point `MODELS` at the local copies.

## Good hand-off tasks

Pick one, keep the pull request small, and say in it what you changed and how you checked it.

1. **Bring the AI models into the repository** (task above) so the game works offline and loads faster.
2. **Phone performance for the game**: frame rate on a mid-range phone, fewer draw calls for the 3,080
   trees, a lower-detail terrain on touch devices, texture sizes.
3. **Game feel**: ambient sound (birds, cicadas, water), footstep and golf-cart sounds, a waving
   animation trigger when the player walks up to the gator at the gate.
4. **Presentation renders with the AI models**: swap the procedural cabins in `scripts/blender_present.py`
   for the Meshy models and re-render the zone close-ups.
5. **Photoreal artist's impressions**: image-to-image passes over `mockup/present/render_close_*.jpg`
   that keep the composition and the cabin designs exactly (a good fit for Gemini's image models).
6. **Planning depth**: parking counts, utilities (septic, well, power), a phased cost model and an
   entitlements checklist for Lake County, written as new sections of the demo page.
7. **Parcel boundary**: the Lake County parcel polygon (the county GIS was unreachable from the
   environment that built this); add it to the base DXF and the game minimap.

## Checks before you open a pull request

- The game page loads with no console errors and reaches "Ready", and every inline script parses
  (`node --check` on each one).
- Python scripts still run with `--help`.
- Nothing secret or personal is added, and `review/` is only rebuilt by someone who has the password.
