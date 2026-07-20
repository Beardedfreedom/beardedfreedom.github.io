---
name: pixel-claude-avatar
description: Use when building, animating, or rendering the Pixel-Claude character in Blender — voxel-style pixel-art mascot with optional cape, top hat, mouth, lip-sync to audio, family of color variants (orange/pink/yellow/cyan), or multi-scene narrative videos. Codifies framing rules, character anatomy, environment sizing for zoom flexibility, and the headless render-to-MP4 pipeline. Triggers on "Pixel Claude", "voxel claude character", "pixel claude scene", "pixel claude video", "claude avatar", "claude lip sync", "speaking pixel claude", "pixel claude family", "claude music video", or any Blender request involving the established Pixel-Claude character.
license: MIT
metadata:
  author: Steven Sanders + Claude
  version: "1.0"
---

# Pixel-Claude Avatar — Blender Character & Scene Skill

A complete pipeline for building, animating, and rendering Steven's Pixel-Claude character in Blender. Built from a multi-night collaboration covering: 14-scene Kryptonite music video, day-in-the-life narrative video, AUTO_DREAM sequence, speaking avatar with lip-sync.

## Character Anatomy (Critical — do not deviate)

Pixel-Claude is a voxel character built from a **6-row × 8-column × 3-layer (depth) bitmap**:

```python
BITMAP = [
    ". X X X X X X .",   # z=5 head top
    ". X . X X . X .",   # z=4 eye row (gaps = eye sockets)
    "X X X X X X X X",   # z=3 arm row (full 8U width)
    "X X X X X X X X",   # z=2 torso
    ". X . X X . X .",   # z=1 leg notches
    "X . X . . X . X",   # z=0 feet (4 separate legs)
]
W, DEPTH, H = 8, 3, 6
```

**Default orientation:**
- Faces -Y (face/eyes/mouth on the negative Y side)
- Stands upright, head at +Z, feet at -Z (z=0 to z=6)
- Width along X, depth along Y

**Body parts (split for bone control):**
- `head` — z>=4 (rows 4 and 5)
- `torso` — z=2 + middle of z=3
- `left_arm` — z=3, x=0 (the protruding voxel on the -X side)
- `right_arm` — z=3, x=7 (the protruding voxel on the +X side)
- `leg_left` — x<4, z<=1
- `leg_right` — x>=4, z<=1

**Eye sockets** are dark recessed cubes at (x=±2.5, y=0, z=4.5) with cream emissive pupils at the front face (y=-1.5).

**Brows** are small dark bars above each eye at (x=±2.5, y=-1.30, z=5.05).

**Antennae** are 1U×1U×3U bars on top of the head at (x=±2.5, z=6.5).

## The Framing Rules (NEVER VIOLATE)

Steven gave explicit feedback on this; embed it into every render decision:

1. **Always full-frame Pixel-Claude.** Default character scale = 1.0. Camera positioned so character fills 50–80% of vertical frame.
2. **No close-ups.** Close-ups (face only) are PERMITTED but RARE — max one per project, only when meaningful.
3. **Stage environments must be big enough for any zoom.** When building a stage/room/environment, size it so the camera can zoom out to a wider shot WITHOUT cutting off the character or revealing the edges of the set. Floors should extend ≥40 units, walls ≥20 units beyond the character.
4. **Characters move only in the direction they face.** If walking +Y, character must have `yaw_deg=180` (rotated 180° around Z so face direction points +Y). Never animate motion opposite to facing direction.
5. **Bed/lying scenes lie on the BACK** (face up to ceiling). Use `rotation_euler = (math.radians(-85), 0, 0)` — negative X rotation so face direction (-Y) rotates toward +Z (up).
6. **9:16 vertical for social media.** Default resolution `RES_X=540, RES_Y=960` for TikTok/Reels/Shorts.

## Color Palette (Family Variants)

```python
CLAUDE_DAD    = col(217, 119, 87)   # signature orange — the main hero
CLAUDE_MOM    = col(220, 100, 150)  # pink
CLAUDE_KID1   = col(245, 200, 80)   # yellow
CLAUDE_KID2   = col(120, 200, 230)  # cyan
RED_CAPE      = col(180, 30, 40)    # superhero cape
HAT_BLACK     = col(18, 12, 14)     # top hat
HAT_BAND      = same as body color  # orange band on hat
```

`col(r,g,b)` is sRGB→linear conversion. Always use it for Principled BSDF base color.

## Mouth + Lip Sync

Mouth is an **EXTERIOR** voxel mounted in front of the face plane:
- Position: `(0, -1.75, 3.55)` — 0.25U in front of face plane at y=-1.5
- Default closed scale: `(1.6, 0.30, 0.22)` (wide, thin)
- Animate `scale.z` per frame from RMS audio amplitude

```python
def sample_amplitudes(wav_path, fps=30):
    """Returns one normalized amplitude (0-1) per video frame."""
    import wave, struct
    with wave.open(wav_path, 'rb') as w:
        sr = w.getframerate()
        nframes = w.getnframes()
        spv = int(sr / fps)  # samples per video frame
        raw = w.readframes(nframes)
        samples = struct.unpack(f"{nframes * w.getnchannels()}h", raw)
        if w.getnchannels() == 2:
            samples = samples[::2]
        amps = []
        for i in range(0, len(samples), spv):
            chunk = samples[i:i+spv]
            if not chunk:
                amps.append(0)
                continue
            rms = (sum(s*s for s in chunk) / len(chunk)) ** 0.5
            amps.append(rms / 32768)
        # Smooth + normalize
        peak = max(amps) or 1
        return [a/peak for a in amps]
```

Then keyframe `mouth.scale = (1.6 * (1 - a*0.15), 0.30, 0.22 + a * 1.4)` per frame.

## Pipeline — Headless Render to MP4

**Always render headless** — `Blender --background --python script.py`. The MCP socket dies on long renders; CLI background is the only reliable path.

```bash
# Launch headless render
nohup /Applications/Blender.app/Contents/MacOS/Blender \
    --background --python /tmp/render.py > /tmp/render.log 2>&1 &

# When done, ffmpeg mux:
ffmpeg -y -framerate 30 -i /tmp/frames/frame_%04d.png \
       -i /path/to/audio.mp3 \
       -c:v libx264 -pix_fmt yuv420p -crf 20 -preset medium \
       -c:a aac -b:a 192k -shortest -movflags +faststart \
       ~/Downloads/output.mp4
```

**Render rate:** ~2.5–4 fps on EEVEE @ 540×960 with `taa_render_samples=16`. Plan for ~3.5 fps and ~30 sec scene-rebuild overhead per scene in multi-scene scripts.

**Blender 5.x gotchas:**
- FFmpeg output enum may not exist — render PNG sequence + ffmpeg-mux externally
- `BLENDER_EEVEE_NEXT` reverted to `BLENDER_EEVEE` in 5.x; check before setting
- Action F-curves moved to slot/layer/strip API — see `references/blender_5x_animation_api.md`
- VSE: use `seq.strips` and `seq.strips_all` (not `sequences`)

## Reusable Templates

- `references/character_builder.py` — the canonical `build_claude()` function
- `references/scene_template.py` — minimal scene with full-frame framing + 9:16 + 3-point lighting
- `references/lip_sync.py` — audio amplitude → mouth animation
- `references/multi_scene_master.py` — pattern for chaining 10+ scenes in one render
- `references/known_assets.md` — current MP4 outputs, rendered scripts, frame caches

## Outputs (current artifacts on disk)

| File | What it is |
|---|---|
| `~/Downloads/claude-kryptonite-MV.mp4` | 14-scene Kryptonite music video (3:54) |
| `~/Downloads/claude-day-in-the-life-9x16.mp4` | 15-scene narrative day video (3:35) |
| `~/Downloads/claude-AUTO_DREAM.mp4` | Dream sequence floating in starfield (20s) |
| `~/Downloads/claude-filler-turntable.mp4` | Loopable turntable filler (20s) |
| `~/Downloads/claude-avatar-greeting.mp4` | Speaking avatar with lip sync |
| `/tmp/kryptonite_mv.py` | Master 14-scene MV script |
| `/tmp/day_in_life_v2.py` | Master 15-scene narrative script |
| `/tmp/claude_avatar.py` | Speaking avatar pipeline |

## When to Use This Skill

- Any time Steven says "build Claude / pixel claude / pixel-claude / claude avatar"
- Any new music video, narrative scene, or animated short featuring the character
- Any speaking-avatar request with text or audio
- Adding new family members, costumes, or environments
- Tweaking framing/lighting/composition on existing scenes

## When NOT to Use

- Generic Blender questions (use `blender-syntax-*` skills instead)
- Non-character voxel art (cities, props, abstract scenes)
- Live MCP-driven Blender work — this skill is for headless render pipelines

## Memory Hooks

Cross-references to user memory:
- `feedback_blender_framing.md` — full-frame rule
- `project_blender_skills.md` — Blender MCP setup + 26 OpenAEC skills
- `reference_elevenlabs_voice.md` — premium voice option for avatar speech
