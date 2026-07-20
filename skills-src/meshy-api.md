---
name: meshy-api
description: Use when generating 3D assets through Meshy AI's REST API (api.meshy.ai) — text-to-3D, image-to-3D, retexture, remesh, auto-rigging, library animations, balance/webhooks. Covers v1/v2 endpoint mix, Bearer-token auth (msy-...), credit costs per task, polling/SSE/webhook patterns, output formats (GLB/FBX/OBJ/USDZ/STL/3MF/.blend), and 2025-2026 breaking changes (free API ended Mar 2025; Meshy-4 retired Mar 2026). Triggers on "Meshy API", "generate 3D from text/image", "auto-rig", "Meshy webhook", "Meshy credits".
---

# Meshy AI REST API

Drive Meshy programmatically: generate 3D meshes from text or images, retexture, remesh, auto-rig humanoid characters, apply library animations. Output formats land in `~/Downloads` ready for Blender import (see the companion skill `meshy-blender-pipeline`).

## Auth & Setup

- **Base URL**: `https://api.meshy.ai`. Most endpoints under `/openapi/v1/...`. **Text-to-3D is on v2** (`/openapi/v2/text-to-3d`). Mixed versions are normal — don't "normalize."
- **Get a key**: log in at https://www.meshy.ai/settings/api → "Create API Key". Format: `msy-<random>`.
- **Tier requirement**: Pro or higher. **Free-tier API task creation ended 2025-03-20.** You can hold a free account but you cannot POST tasks.
- **Header**: `Authorization: Bearer msy-...` + `Content-Type: application/json`.
- **Test key (no credit consumption)**: `msy_dummy_api_key_for_test_mode_12345678` — returns a fixed sample response. Use it to validate request shape before burning real credits.
- **Version pin**: read response header `x-api-version` (added Oct 2025). If it changes between two of your calls, Meshy shipped a breaking change — re-read the changelog.
- **Balance check first**: `GET /openapi/v1/balance` → `{"balance": 1000}`. Always gate on this before launching a task.

## Endpoint Map (Quick Reference)

| Task | Method + Path | API | Credits | Output |
|---|---|---|---|---|
| Balance | `GET /openapi/v1/balance` | v1 | 0 | int |
| Text-to-3D preview | `POST /openapi/v2/text-to-3d` (mode=preview) | **v2** | ~5 | GLB/FBX/OBJ/USDZ/STL/3MF |
| Text-to-3D refine | `POST /openapi/v2/text-to-3d` (mode=refine) | v2 | ~10 (15 total preview+refine on Meshy-6) | + texture URLs |
| Poll | `GET /openapi/v2/text-to-3d/:id` (also v1 for others) | both | 0 | task object |
| SSE stream | `GET .../<task_id>/stream` | both | 0 | event stream |
| Image-to-3D | `POST /openapi/v1/image-to-3d` | v1 | 30 | same formats |
| Multi-Image-to-3D | `POST /openapi/v1/multi-image-to-3d` | v1 | 30+ | same formats |
| Retexture | `POST /openapi/v1/retexture` | v1 | 10 | GLB/FBX |
| Remesh | `POST /openapi/v1/remesh` | v1 | 5 | + **.blend** (only endpoint with native Blender output) |
| Auto-Rig | `POST /openapi/v1/rigging` | v1 | 5 | rigged FBX + GLB |
| Animation | `POST /openapi/v1/animations` | v1 | 3 | GLB/FBX/USDZ |
| List | `GET /openapi/{v1\|v2}/<resource>` | both | 0 | paginated tasks |
| Cancel | `DELETE /openapi/{v1\|v2}/<resource>/:id` | both | 0 | — |

See `references/api_endpoints.md` for full request/response schemas.

## Two-Stage Text-to-3D (Most Common)

Stage 1 — geometry preview:
```bash
curl https://api.meshy.ai/openapi/v2/text-to-3d \
  -H "Authorization: Bearer $MESHY_KEY" -H "Content-Type: application/json" \
  -d '{"mode":"preview","prompt":"cyberpunk samurai bust","ai_model":"latest",
       "topology":"quad","target_polycount":30000,"pose_mode":"a-pose"}'
```
Stage 2 — texturing (run after preview SUCCEEDED):
```bash
curl https://api.meshy.ai/openapi/v2/text-to-3d \
  -H "Authorization: Bearer $MESHY_KEY" -H "Content-Type: application/json" \
  -d '{"mode":"refine","preview_task_id":"<from stage 1>",
       "enable_pbr":true,"hd_texture":true,
       "texture_prompt":"weathered iron, neon-magenta highlights",
       "target_formats":["glb","fbx"]}'
```

**Always pass `target_formats:["glb",...]`** — GLB embeds PBR maps and is the cleanest Blender import path. FBX preserves rig+anim cleanest for downstream Animation/Rigging endpoints. Native `.blend` only emits from Remesh.

**Model choice**: `ai_model: "latest"` resolves to `meshy-6` (current). `meshy-4` retired 2026-03 — don't pin it. Older docs reference an `art_style` field — it's deprecated and ignored on Meshy-6.

## Polling Pattern (Preferred over webhooks for short jobs)

```python
import time, requests

def poll(task_id, kind="text-to-3d", api="v2"):
    url = f"https://api.meshy.ai/openapi/{api}/{kind}/{task_id}"
    h = {"Authorization": f"Bearer {os.environ['MESHY_KEY']}"}
    while True:
        r = requests.get(url, headers=h, timeout=30).json()
        if r["status"] in ("SUCCEEDED", "FAILED", "CANCELED"):
            return r
        print(f"  [{r['status']}] {r.get('progress', 0)}%")
        time.sleep(8)
```
Typical end-to-end: 1–3 min preview + 1–2 min refine. SSE `/stream` is push-based but adds connection-management complexity — only use it for >5-min jobs.

## Webhooks (For Long-Running Pipelines)

- Configure in https://www.meshy.ai/settings/api (no REST endpoint to manage them).
- **HTTPS only**, **max 5 active per account**.
- Meshy POSTs JSON on every status change. Respond `<400` (200/202) — repeated 4xx/5xx auto-disables the hook.
- **Payload schema and HMAC signing are NOT publicly documented as of 2026-05.** Don't trust the payload origin without out-of-band verification — re-poll the task ID via GET to confirm.
- Local dev: use a smee.io URL → forward to localhost.

## Output Download (Time-Limited URLs)

`model_urls.<format>` and `texture_urls[].*` are signed CDN URLs with **3-day asset retention** (Pro/Studio); Enterprise = forever; Free tier = N/A (no API). **Mirror to your own storage immediately on `SUCCEEDED`.**

```python
import urllib.request
urllib.request.urlretrieve(task["model_urls"]["glb"], "/tmp/asset.glb")
```

## Auto-Rig + Animation (Character Pipeline)

```bash
# 1. Rig (body-only humanoid; fails on quadrupeds, mecha, multi-limb)
curl https://api.meshy.ai/openapi/v1/rigging \
  -H "Authorization: Bearer $MESHY_KEY" -d '{
    "model_url":"https://cdn.meshy.ai/.../character.glb",
    "height_meters":1.8,
    "texture_image_url":"https://.../basecolor.png"
  }'

# 2. Apply library animation (3 credits each, 600+ action_ids available)
curl https://api.meshy.ai/openapi/v1/animations \
  -H "Authorization: Bearer $MESHY_KEY" -d '{
    "rig_task_id":"<from step 1>",
    "action_id":1,
    "post_process":{"fps":30,"format":"fbx"}
  }'
```

**Fetch the live action_id table** before pinning IDs — Meshy adds new actions monthly. `GET /openapi/v1/animation-library` lists them. Highlights: `0` Idle, `1` Walking_Woman, `30` Casual_Walk, `14-16` Run variants, `22-24` FunnyDancing, `4` Attack, `460-472` jumps, `290-318` conversation gestures.

**Hard rigging limits:**
- ≤300k faces (run Remesh first if larger).
- Standard humanoid biped only.
- Character must face **+Z (glTF forward)**.
- **Body-only skeleton — no face bones, no fingers detail beyond standard hand chain, no shape keys.** For face animation, see `meshy-blender-pipeline` skill's lip-sync escape hatches.
- Mixamo bone naming is NOT guaranteed — manual remap required for Mixamo retargeting.

## Pricing (2026)

| Tier | Price | Monthly Credits | API | Rate Limit | Asset Retention |
|---|---|---|---|---|---|
| Free | $0 | 100 (UI only) | ❌ | — | — |
| **Pro** | from ~$20/mo (yearly) | 1,000 | ✅ | 20 req/s | 3 days |
| Studio | per-seat yearly | 4,000 | ✅ | 20 req/s | 3 days |
| Enterprise | custom | custom | ✅ | 100 req/s | Forever |

Costs are **identical across paid tiers**. Credits refresh monthly. Pro is the API floor.

## Common Failure Modes

1. **Prompt too abstract** → blob mesh with no anatomy. Be specific about pose, era, materials.
2. **Profile-only input image** → broken/missing back. Use front-facing or 3/4 view, plain neutral background.
3. **Transparent PNG bg** confuses subject detection. Use solid neutral.
4. **`should_remesh:true` on Meshy-6** sometimes destroys fine detail. Leave it `false` unless you specifically need topology cleanup.
5. **Symmetry forced "on"** can fuse asymmetrical features (eye patches, gauntlets). Use `"off"` for asymmetric characters.
6. **Mac FBX scale 100x bug**: Meshy rigged FBX sometimes imports at 100x in Blender. Fix: `bpy.ops.import_scene.fbx(filepath=..., global_scale=0.01)` or apply Scale 0.01 after import.
7. **"No native `.blend`"** — Text-to-3D and Image-to-3D do not emit `.blend`. Pipeline GLB → Blender importer. Only Remesh emits `.blend`.
8. **Quadrupeds / mecha** → rigging endpoint fails. Humanoid biped only.

## When to Use This Skill (vs. the Plugin)

- **API skill (here)**: programmatic batch generation, headless pipelines, AI-agent-driven workflows, integrating Meshy outputs into Blender headless renders, CI/CD that produces 3D assets.
- **Plugin** (`meshy-blender-pipeline` skill): interactive browse-and-import in the live Blender editor, "Send to Blender" web button workflow, mesh cleanup/analyze operators, one-off creative sessions.

The two are complementary, not competing. The plugin runs a localhost HTTP server (port 5324) that the Meshy *web app* talks to — it doesn't call the API directly.

## See Also

- `references/api_endpoints.md` — full request/response schemas for every endpoint
- `references/animation_library.md` — curated action_id reference
- `meshy-blender-pipeline` skill — Blender import/render side
- Meshy docs: https://docs.meshy.ai/en
