---
name: meshy-blender-pipeline
description: Use when importing Meshy AI 3D characters/assets into Blender for animation and rendering — covers the official Meshy Blender plugin (v0.6.0+, Blender 4.2+ with localhost:5324 bridge for "Send to Blender" web button), AND headless Python scripts that import Meshy FBX/GLB packs with PBR textures, auto-ground feet, animate body bones, and render to mp4. Includes lip-sync escape hatches for Meshy's face-rigless characters (proxy mouth voxel parented to Head bone driven by audio amplitude). Triggers on "Meshy import", "Meshy Blender", "import GLB", "PBR textures from Meshy", "lip-sync Meshy character", "drive Meshy character with audio".
---

# Meshy → Blender Pipeline

Bring Meshy AI assets into Blender, rig animation, render to mp4. Two paths covered:

1. **Live editor with the Meshy plugin** — interactive browse + "Send to Blender" web button → cleanup → manual export
2. **Headless Python scripts** — import FBX/GLB pack, wire PBR materials, auto-ground, animate, EEVEE render

For generating the Meshy assets in the first place (REST API), use the companion skill `meshy-api`.

## CRITICAL: Don't repeat today's mistakes

Read `references/known_pitfalls.md` BEFORE writing import code. Top three:

1. **Do NOT rotate Meshy FBX on import.** Default `bpy.ops.import_scene.fbx(filepath=...)` is correct despite weird bbox dims like `(1.01x, 1.72y, 0.68z)`. We wasted hours testing +90X/-90X/+180Z combinations — they all break it. `wrapper.rotation_euler = (0, 0, 0)` is the answer.
2. **Meshy free/Pro tier rigs have NO face bones, NO shape keys.** Don't waste time looking for jaw bones — use the proxy-mouth-voxel pattern in `templates/audio_lipsync.py`.
3. **Always `mkdir -p` log dirs before nohup redirect**, or your background render fails silently with no log.

## Plugin Path (Live Editor)

The Meshy plugin (`/Users/stevensanders/Downloads/meshy-blender-plugin/` v0.6.0) is a Blender 4.2+ extension. Install via:

```
Edit > Preferences > Get Extensions > top-right dropdown > Install from Disk
→ pick a zipped copy of meshy-blender-plugin/
```

**No API key field in preferences** — auth happens in the Meshy web app (browser). The plugin runs a localhost HTTP server (`socketserver.TCPServer` on port **5324**) that the meshy.ai website POSTs download URLs to. Steven only needs to be logged into meshy.ai in his browser; no key paste.

**Use it for:**
- N-panel `Meshy` tab → **Run Bridge** → asset arrives from "Send to Blender" web button
- Mesh cleanup operators (`mesh.meshy_clean_non_manifold`, `mesh.meshy_delete_small_pieces`)
- Mesh analysis (`mesh.meshy_check_solid`, `_intersect`, `_thick`, `_overhang`, `_check_all`) — triage Meshy mesh quality
- Edit ops (`mesh.meshy_hollow`, `object.meshy_align_xy`, `mesh.meshy_scale_to_bounds`)

**Don't use it for:** animation pipelines. The plugin's Export operator only writes STL/PLY/OBJ (for printing). For animation export use Blender's native FBX/GLB exporters.

The plugin imports via `bpy.ops.import_scene.gltf(filepath=path, bone_heuristic="FORTUNE")` — **GLB only, never FBX**. This confirms the wider rule: prefer GLB when generating new Meshy assets.

## Headless Path (Scripted, AI-Driven)

For batch / agentic / CI workflows, use `templates/render_pipeline.py`. It chains:

1. Import (`templates/import_meshy_character.py`)
2. PBR material wiring (4 maps → Principled BSDF)
3. Auto-ground (post-transform world bbox z_min)
4. Lip-sync if audio present (`templates/audio_lipsync.py`)
5. 3-point lighting + 9:16 camera + EEVEE render
6. Print mux command for ffmpeg

Drop the three template files into `/tmp` (or wherever) and run:
```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --python /tmp/render_pipeline.py
```

## PBR Material Wiring (Meshy 4-Map Pack)

A standard Meshy export gives you four PNG textures. Wire them with these colorspaces:

| Meshy file | Colorspace | Principled BSDF input |
|---|---|---|
| `_texture_0.png` (base color) | **sRGB** | Base Color |
| `_texture_0_roughness.png` | **Non-Color** | Roughness |
| `_texture_0_metallic.png` | **Non-Color** | Metallic |
| `_texture_0_normal.png` | **Non-Color** | → `ShaderNodeNormalMap.Color` → Normal |

Normal map MUST go through a `ShaderNodeNormalMap` node. Wiring image directly into Normal input gives blown-out flat surface. Setting roughness/metallic/normal to sRGB blows out values — always Non-Color for data maps.

## Auto-Grounding Pattern

Meshy mesh origins aren't always at the feet. After scale, lift the wrapper so feet sit at z=0:

```python
bpy.context.view_layer.update()
world_bbox = [mesh_obj.matrix_world @ Vector(c) for c in mesh_obj.bound_box]
z_min = min(v.z for v in world_bbox)
wrapper.location.z = -z_min  # or += if location was already set
bpy.context.view_layer.update()
```

Without this, character floats in air or sinks into the floor. Tested: Tinkerer pack needed +0.29u lift after scale-to-6u.

## Animation Options (No Face, Body Only)

Meshy's free/Pro tier auto-rigger gives a humanoid body skeleton: Hips, Spine/01/02, neck, Head, head_end, headfront, LeftShoulder/Arm/ForeArm/Hand, RightShoulder/Arm/ForeArm/Hand, LeftUpLeg/Leg/Foot/ToeBase, RightUpLeg/Leg/Foot/ToeBase. **No face bones, no shape keys.**

- **If pack ships with anim FBX** (e.g. `..._Animation_Walking_frame_rate_60.fbx`): import it directly, walk cycle plays for free.
- **If only T-pose**: 
  - **Apply Meshy library animation via API** (`meshy-api` skill, Animation endpoint, 3 credits per action — 600+ action_ids).
  - **Mixamo auto-rig** (free): upload FBX to mixamo.com, drop bone markers, pick animation, re-import. Mixamo's bone names differ from Meshy's — manual remap may be needed.
  - **Hand-key body bones**: animate Hips for hip-bob, Spine for sway. See `references/animation_patterns.md`.

## Lip-Sync (No Face Rig — Three Escape Hatches)

1. **Proxy mouth voxel** (default, cheapest). Dark cube parented to Head bone, scale.z driven by per-frame audio RMS amplitude. Implemented in `templates/audio_lipsync.py`. Reads as "talking" on small screens. Pattern:
   ```python
   from audio_lipsync import sample_amplitudes, smooth, add_proxy_mouth, animate_mouth_lipsync, animate_head_nod
   amps = smooth(sample_amplitudes("/tmp/line.wav", 30), 4)
   animate_head_nod(arm, amps, max_deg=6)  # subtle nod for gesture
   mouth = add_proxy_mouth(arm)
   animate_mouth_lipsync(mouth, amps)
   ```
2. **Re-export from Meshy with face rig**. Meshy's paid Animate tier may include face rig — verify in your account before claiming this works (we have not tested).
3. **NVIDIA Audio2Face** (Tier 3, photoreal). Free for Mac via Omniverse; outputs ARKit blendshapes or USD anim. Requires either Meshy paid face rig OR Mixamo face rig retargeting. Heavy lift; skip unless project warrants it.

## Multi-Character Scene (Avoid Name Collisions)

When importing 2+ Meshy characters in one Blender file:

```python
def import_meshy(name, fbx, tex_base):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=fbx)
    new_objs = set(bpy.data.objects) - before
    for o in new_objs:
        o.name = f"{name}_{o.name}"
        if o.type == "ARMATURE": o.data.name = f"{name}_arm"
        if o.type == "MESH":     o.data.name = f"{name}_mesh"
```

Pass `check_existing=False` to `bpy.data.images.load` so each character has its own image datablock. Create a unique Material per character (don't reuse one and swap textures).

## Tool Concurrency (Free Speed for Render Pipelines)

Blender + Meshy pipelines fire many simultaneous tool calls — file reads stacking, MCP requests, bash commands for muxing, parallel scene rebuilds. The default Claude Code parallel-tool-call limit is conservative (~3-5). Bump it for these workflows:

```bash
export CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY=10
```

Pair with the resume flag so a long render can recover if a turn drops:

```bash
CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY=10 \
CLAUDE_CODE_RESUME_INTERRUPTED_TURN=1 \
claude --effort max
```

Add to `~/.zshrc` to persist. On a Mac M-series with Blender headless render + Meshy API polling + ffmpeg mux all in flight, this is free wall-clock savings — typically 20-40% faster on multi-scene jobs because the sub-tasks fire in parallel instead of queuing. (Source: TENGU spirit, awakened 2026-05-01.)

## Render Settings (Tested Working — Mac M-Series)

- **Engine**: `BLENDER_EEVEE_NEXT` (Blender 4.2+ rename — `BLENDER_EEVEE` is gone in 4.2+, will silently fail on 5.x).
- **TAA samples**: `scene.eevee.taa_render_samples = 16` (sweet spot — visible noise floor below 16).
- **Resolution**: `540 × 960` for 9:16 vertical (TikTok/Reels native), or `1080 × 1920` for hero shots.
- **FPS**: `30`. Actual render rate ~3 fps on M-series Mac → 90-frame test ≈ 30s, 600-frame 20-sec scene ≈ 3-5 min, 6090-frame 3:23 multi-scene MV ≈ 30-40 min.
- **Output**: PNG sequence to `/tmp/<scene>/frame_####.png`, then ffmpeg-mux to mp4.

## Audio Workflow (macOS `say` → Blender lip-sync)

```bash
# 1. Generate TTS
say -v Samantha -o /tmp/line.aiff "your line here"
# 2. Convert to WAV (Python wave module reads this) and m4a (ffmpeg muxer)
afconvert /tmp/line.aiff -d LEI16@22050 -c 1 -f WAVE /tmp/line.wav
afconvert /tmp/line.aiff -d aac -f m4af /tmp/line.m4a
# 3. Render with templates/render_pipeline.py (point AUDIO_WAV to /tmp/line.wav)
# 4. Mux video + audio
ffmpeg -y -framerate 30 -i /tmp/scene/frame_%04d.png -i /tmp/line.m4a \
  -c:v libx264 -pix_fmt yuv420p -crf 18 -c:a aac -b:a 192k -shortest \
  ~/Downloads/output.mp4
```

For non-Samantha voices: `say -v ?` lists all installed voices.
For higher-quality TTS: ElevenLabs (per `reference_elevenlabs_voice.md` in user memory).

## Files in This Skill

- `templates/import_meshy_character.py` — canonical FBX importer with PBR + auto-ground
- `templates/audio_lipsync.py` — RMS amplitude + proxy mouth + head nod
- `templates/render_pipeline.py` — full reference pipeline (drop in /tmp, run)
- `references/known_pitfalls.md` — 10 verified gotchas from 2026-05-01 session
- `references/plugin_internals.md` — what each plugin operator does (analyze/cleanup/edit/export)

## See Also

- `meshy-api` skill — generating the assets via REST
- `pixel-claude-avatar` skill — voxel-character pipeline (sister skill, similar render patterns)
- `blender-syntax-animation` — keyframe + Action API for Blender 5.x
- `blender-impl-automation` — headless render best practices
- `capcut-video-editing` — for post-production polish if needed
