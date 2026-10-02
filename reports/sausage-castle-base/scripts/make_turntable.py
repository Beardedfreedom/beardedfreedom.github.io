#!/usr/bin/env python3
"""Finish a blender_present.py run: JPEG stills, turntable video and poster, and the .glb moved beside the web page.

Usage:  python3 scripts/make_turntable.py <present_dir> [--fps 24] [--quality 88] [--keep-png]

* render_*.png  -> render_*.jpg (PNG removed unless --keep-png)
* turntable/frame_*.png -> turntable.mp4 (H.264, yuv420p, loops cleanly) + turntable_poster.jpg
* florida_freedom_world_lakes_present.glb -> ../../viewer3d/ (next to viewer3d/index.html) when that folder exists
Needs Pillow; the video needs imageio + imageio-ffmpeg (pip install imageio imageio-ffmpeg).
"""
import argparse
import shutil
import sys
from pathlib import Path

from PIL import Image


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("present_dir", type=Path)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--quality", type=int, default=88)
    ap.add_argument("--keep-png", action="store_true")
    a = ap.parse_args()
    d = a.present_dir.resolve()

    for png in sorted(d.glob("render_*.png")):
        jpg = png.with_suffix(".jpg")
        Image.open(png).convert("RGB").save(jpg, quality=a.quality, optimize=True, progressive=True)
        print(f"{jpg.name}: {jpg.stat().st_size // 1024} KB")
        if not a.keep_png:
            png.unlink()

    frames = sorted((d / "turntable").glob("frame_*.png"))
    if frames:
        try:
            import imageio.v2 as imageio
            with imageio.get_writer(str(d / "turntable.mp4"), fps=a.fps, codec="libx264", quality=8, pixelformat="yuv420p", macro_block_size=8) as w:
                for f in frames:
                    im = Image.open(f).convert("RGB")
                    w.append_data(__import__("numpy").asarray(im))
            print(f"turntable.mp4: {len(frames)} frames, {(d / 'turntable.mp4').stat().st_size // 1024} KB")
        except Exception as ex:
            print("video skipped:", ex, file=sys.stderr)
        Image.open(frames[0]).convert("RGB").save(d / "turntable_poster.jpg", quality=a.quality, optimize=True)

    glb = d / "florida_freedom_world_lakes_present.glb"
    v3d = d.parent.parent / "viewer3d"
    if glb.exists() and v3d.is_dir():
        shutil.move(str(glb), str(v3d / glb.name)); print(f"moved {glb.name} -> viewer3d/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
