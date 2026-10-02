#!/usr/bin/env python3
"""Assemble the Gator Greens drone flyover: mockup/flyover/f*.png -> mockup/golf_flyover.mp4 (+ poster).

The frames are rendered at a low frame rate (scripts/golf_mockup.py --flyover N --fps 8) and smoothed to
24 fps here with ffmpeg's motion-compensated interpolation, which suits a slow, steady drone glide.
Usage: python3 scripts/golf_flyover_video.py [--fps-in 8] [--fps-out 24] [--crf 18]
Needs imageio-ffmpeg (pip install imageio-ffmpeg) for the ffmpeg binary.
"""
import argparse, glob, os, shutil, subprocess, sys
from PIL import Image

ap = argparse.ArgumentParser(); ap.add_argument('--base', default=os.path.join(os.path.dirname(__file__), '..'))
ap.add_argument('--fps-in', type=int, default=8); ap.add_argument('--fps-out', type=int, default=24); ap.add_argument('--crf', type=int, default=18)
a = ap.parse_args(); MO = os.path.join(os.path.abspath(a.base), 'masterplan', 'golf', 'mockup'); FR = os.path.join(MO, 'flyover')
frames = sorted(glob.glob(os.path.join(FR, 'f*.png')))
if not frames: sys.exit('no frames in ' + FR)
try:
    import imageio_ffmpeg; ff = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    ff = shutil.which('ffmpeg') or sys.exit('ffmpeg not found (pip install imageio-ffmpeg)')
first = int(os.path.basename(frames[0])[1:5]); out = os.path.join(MO, 'golf_flyover.mp4')
vf = f"minterpolate=fps={a.fps_out}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,format=yuv420p"
cmd = [ff, '-y', '-v', 'error', '-framerate', str(a.fps_in), '-start_number', str(first), '-i', os.path.join(FR, 'f%04d.png'),
       '-vf', vf, '-c:v', 'libx264', '-preset', 'slow', '-crf', str(a.crf), '-movflags', '+faststart', out]
subprocess.run(cmd, check=True)
Image.open(frames[len(frames) // 2]).convert('RGB').save(os.path.join(MO, 'golf_flyover_poster.jpg'), quality=88)
print(f'{os.path.basename(out)}: {len(frames)} frames at {a.fps_in} fps -> {a.fps_out} fps, {os.path.getsize(out) // 1024} KB')
