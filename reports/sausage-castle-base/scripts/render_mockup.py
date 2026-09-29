#!/usr/bin/env python3
"""Perspective renders of the cleared, graded lake zones with the cabins in place (from the viewer data)."""
import json, math, os, numpy as np
from PIL import Image
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
BASE = '/home/user/beardedfreedom.github.io/reports/sausage-castle-base'; VD = f'{BASE}/viewer/data'; MO = f'{BASE}/mockup'
z = json.load(open(f'{VD}/meta.json'))['zones']['lakes']; c = z['cell_ft']; x0, y0 = z['x0'], z['y0']
def dec(spec):
    im = np.asarray(Image.open(f"{VD}/{spec['file']}").convert('RGB')).astype(float); return ((im[..., 0] * 256 + im[..., 1]) * spec['scale'] + spec['zmin'])[::-1]
H = dec(z['cleared']['surface']); ny, nx = H.shape; col = np.asarray(Image.open(f"{VD}/{z['cleared']['color']}").convert('RGB')).astype(float)[::-1] / 255
units = json.load(open(f'{VD}/units.json')); lz = json.load(open(f'{BASE}/focus/lakes/lake_zones_concept.json'))
def unit_tris(key):
    T, C = [], []
    for part in units['units'][key]['parts']:
        V = np.array(part['positions']).reshape(-1, 3); F = np.array(part['indices']).reshape(-1, 3); cc = np.array([int(part['color'][i:i + 2], 16) / 255 for i in (1, 3, 5)])
        T.append(V[F]); C.append(np.repeat(cc[None], len(F), 0))
    return np.vstack(T), np.vstack(C)
UT = {k: unit_tris(k) for k in units['units']}
def placed(pl):
    T, C = UT[pl['unit']]; a = math.radians(pl['rot_deg']); R = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
    return T @ R.T + np.array([pl['x'], pl['y'], pl.get('z_graded', pl['z'])]), C
def shade(T, C, light=np.array([0.4, -0.6, 0.7])):
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); L = np.linalg.norm(n, axis=1, keepdims=True); n = n / np.where(L == 0, 1, L)
    return np.clip(C * (0.5 + 0.5 * np.clip(n @ (light / np.linalg.norm(light)), 0, 1))[:, None], 0, 1)
def render(bb, step, elev, azim, path, title, exag=1.0):
    bx0, by0, bx1, by1 = bb; i0, i1 = max(0, int((bx0 - x0) / c)), min(nx, int((bx1 - x0) / c)); j0, j1 = max(0, int((by0 - y0) / c)), min(ny, int((by1 - y0) / c))
    Hs = H[j0:j1:step, i0:i1:step] * exag; cs = col[j0:j1:step, i0:i1:step]
    xs = x0 + (np.arange(i0, i1, step)[:Hs.shape[1]] + 0.5) * c; ys = y0 + (np.arange(j0, j1, step)[:Hs.shape[0]] + 0.5) * c; X, Y = np.meshgrid(xs, ys)
    fig = plt.figure(figsize=(16, 11), dpi=120); ax = fig.add_subplot(111, projection='3d'); ax.computed_zorder = False
    ax.plot_surface(X, Y, Hs, facecolors=cs, rstride=1, cstride=1, linewidth=0, antialiased=False, shade=False, zorder=1)
    Ts, Cs = [], []
    for pl in units['placements']:
        if bx0 <= pl['x'] <= bx1 and by0 <= pl['y'] <= by1: T, C = placed(pl); T[:, :, 2] *= exag; Ts.append(T); Cs.append(C)
    if Ts: T = np.vstack(Ts); C = np.vstack(Cs); ax.add_collection3d(Poly3DCollection(T, facecolors=shade(T, C), edgecolors='none', zorder=5))
    zr = Hs.max() - Hs.min() + 45; ax.set_box_aspect((bx1 - bx0, by1 - by0, zr)); ax.set_xlim(bx0, bx1); ax.set_ylim(by0, by1); ax.set_zlim(Hs.min(), Hs.min() + zr)
    ax.view_init(elev=elev, azim=azim); ax.set_axis_off(); fig.subplots_adjust(0, 0, 1, 1); fig.text(0.01, 0.01, title, fontsize=9, color='#333')
    fig.savefig(path, dpi=120, pil_kwargs={'quality': 88}); plt.close(fig); print('render', os.path.basename(path))
pads = {p['id']: p for p in lz['pads']}; allx = [p['center'][0] for p in pads.values()]; ally = [p['center'][1] for p in pads.values()]
render((min(allx) - 100, min(ally) - 100, max(allx) + 100, max(ally) + 100), 2, 40, -55, f'{MO}/lakes_cleared_mockup_overall.jpg', '3D mock-up: lake-zone pads cleared and graded with the 22 themed cabins in place · removed trees gone, pads at finished grade · view from the south-west')
def zone_bb(zn, half=210):
    xs_ = [p['center'][0] for p in pads.values() if p['zone'] == zn]; ys_ = [p['center'][1] for p in pads.values() if p['zone'] == zn]
    cx, cy = np.mean(xs_), np.mean(ys_); return (cx - half, cy - half * 0.75, cx + half, cy + half * 0.75)
render(zone_bb('C'), 1, 28, -40, f'{MO}/lakes_cleared_mockup_zoneC.jpg', 'Zone C close-up: mushroom cabins on cleared, graded pads along the loop lane')
render(zone_bb('A'), 1, 28, 205, f'{MO}/lakes_cleared_mockup_zoneA.jpg', 'Zone A close-up: haunted-house cabins on cleared, graded pads')
render(zone_bb('B'), 1, 28, -120, f'{MO}/lakes_cleared_mockup_zoneB.jpg', 'Zone B close-up: swamp cabins on stilts on cleared, graded pads')
