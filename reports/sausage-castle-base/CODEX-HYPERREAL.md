# Codex task: make the presentation model hyper-realistic

Paste this whole file into Codex as the task, or point Codex at it. Read `AGENTS.md` first for where the
build lives and the ground rules (privacy, branches, no secrets).

**Repository:** `Beardedfreedom/beardedfreedom.github.io`  
**Start from branch:** `claude/sharp-lamport-adogq3`  
**Work on branch:** `codex/hyperreal` and open a pull request back into `claude/sharp-lamport-adogq3`  
**Folder:** `reports/sausage-castle-base/`  
**Main file:** `scripts/blender_present.py` (Blender 5.0.1 as the pip `bpy` module, Cycles on CPU)

## Goal

Today the lake-zone renders look like a clean architectural diorama: smooth painted ground, lollipop
trees (icosphere and cone crowns), flat-coloured cabins, a simple water material. Turn them into
photoreal renders that read like drone photos and eye-level photos of a finished resort in central
Florida, while keeping every position exactly where the survey and plan put it: the ground heights,
the lake outline and water level, the loop lane, the 22 pads and cabins, and every tree's position,
height and crown size from the lidar.

Keep the current look available: add a flag `--realism {stylised,photo}` (default `photo`) so the old
pipeline still runs with `--realism stylised`.

## What to change, in order of payoff

1. **Trees (biggest win).** Replace the procedural crowns in the "trees: stylised, lidar-sized" section
   (`make_crown`, `protos`, `trunk_proto`) with realistic Florida species: live oak with Spanish moss,
   slash or longleaf pine, bald cypress near the water, cabbage palm, a few laurel oaks. Use CC0 assets
   (Poly Haven, ambientCG, Quaternius, or Blender's Sapling Tree Gen add-on) and keep the instancing:
   one prototype per species and size class, linked duplicates scaled to each lidar tree. Keep
   `foreground_cull()` working.
2. **Ground.** Replace the vertex-colour land cover (`enrich_ground_material()`) with PBR materials:
   St. Augustine or Bahia grass with real texture and displacement, packed sand and shell for the lane
   and pads, wet dark sand at the shore, leaf litter under oaks. Add a Geometry Nodes grass and weed
   scatter that is dense only near the low cameras (distance mask) and off the lane, pads and water.
3. **Water.** Central Florida lakes are tea-coloured and mirror-like. Water at IOR 1.33, tannin-brown
   volume absorption, a gentle wave normal, a soft wet edge at the shoreline, a few lily pads and reeds
   along the banks.
4. **Cabins.** Give the four cabin types (mushroom, haunted house, swamp stilt cabin, UFO saucer pod)
   real materials: wood siding and shake shingles, weathered paint, corrugated metal, glass with
   interior lights at dusk, bevelled edges. The AI-made detail models listed in `MODELS` in
   `game/index.html` (Meshy GLBs on Higgsfield's CDN) can replace the massing models if your
   environment can download them; otherwise upgrade the materials on the existing meshes. Add small
   props per pad: porch lights, an Adirondack chair, a fire ring, a kayak at the waterfront cabins.
5. **Light and sky.** Swap the physical sky for CC0 HDRIs (Poly Haven): a partly cloudy Florida-style
   day and a warm sunset for dusk. Keep a sun lamp aligned to the HDRI sun for crisp shadows. Keep the
   horizon haze idea (`horizon_haze()`) or replace it with real distant terrain and aerial perspective
   (a volume or mist pass), so the edge of the model never shows.
6. **Camera and film.** Physical camera settings: depth of field on the eye-level `ground_*` views
   (focus on the cabin, about f/5.6), slight motion blur on the turntable, AgX with a gentle grade,
   subtle glare and vignette in the compositor. Do not move the cameras: `add_cam()` and the camera
   list must keep their framing.
7. **Render settings.** Stills at 1920 x 1080 (or 3840 x 2160 if time allows), 256 to 512 samples
   with OpenImageDenoise. The turntable is 240 frames at 1280 x 720; keep it under about 40 seconds a
   frame on a 4-core CPU, or document what hardware you used.

## Assets and licences

Use CC0 assets only. Put downloaded files under `mockup/present/assets/` (HDRIs at 2K or 4K, textures
at 2K) and list every asset with its source URL and licence in `mockup/present/assets/CREDITS.md`.
Keep the total under about 60 MB; do not commit raw 8K textures.

## Outputs to produce

- Regenerated stills in `mockup/present/` with the same file names: `render_{overall,A,B,C,D,lake,hero,hero_dusk}.jpg`,
  `render_close_{A,B,C,D}.jpg`, `render_ground_{A,B,C,D}.jpg`, `render_ground_{A,B,C,D}_dusk.jpg`.
- `mockup/present/turntable.mp4` (240 frames, 24 fps) and `turntable_poster.jpg`, via
  `scripts/make_turntable.py mockup/present --fps 24`.
- The `.blend` saved by the script.
- A before-and-after contact sheet `mockup/present/realism_compare.jpg` (stylised on the left, photo
  on the right) for at least `hero`, `ground_C` and `close_D`.
- README section "Presentation model" updated with the new flag, assets and timings.

Commands:

    cd reports/sausage-castle-base
    pip install bpy==5.0.1 numpy scipy shapely ezdxf pillow imageio imageio-ffmpeg
    python3 scripts/blender_present.py --base . --out mockup/present --renders --no-glb --samples 256 \
        --views overall,A,B,C,D,lake,hero,hero_dusk,close_A,close_B,close_C,close_D,ground_A,ground_B,ground_C,ground_D,ground_A_dusk,ground_B_dusk,ground_C_dusk,ground_D_dusk \
        --turntable 240 --tt-res 1280x720 --tt-samples 64
    python3 scripts/make_turntable.py mockup/present --fps 24

For quick iteration, render a few views at `--res 640x360 --samples 16` first.

## Do not

- Do not move or resize anything that comes from the survey or the plan (terrain, lake, lane, pads,
  cabin positions, tree positions and sizes).
- Do not touch `review/` or rebuild it: that needs the owner's password, which is not in the repository.
- Do not add analytics, trackers or public uploads of any file from this folder.
- Do not push to `main` or rewrite history on `claude/sharp-lamport-adogq3`.

## Done means

The photo renders and turntable are committed on `codex/hyperreal`, the contact sheet shows the
improvement, `--realism stylised` still reproduces the old look, and the pull request description lists
the assets used, render times and anything left undone.
