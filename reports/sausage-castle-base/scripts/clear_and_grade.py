#!/usr/bin/env python3
"""Clearing and grading for the 22 lake-zone pads, a cleared/graded 3D surface for the viewer, CAD outputs and renders."""
import json, math, datetime, os, re
import numpy as np, ezdxf, shapely, contourpy
from ezdxf.render import MeshBuilder
from PIL import Image
from shapely.geometry import Polygon, Point, box, shape
from shapely.ops import unary_union, transform as shp_transform
from scipy import ndimage
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, Circle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
BASE = '/home/user/beardedfreedom.github.io/reports/sausage-castle-base'; LK = f'{BASE}/focus/lakes'; VD = f'{BASE}/viewer/data'; MO = f'{BASE}/mockup'; os.makedirs(MO, exist_ok=True)
meta_all = json.load(open(f'{VD}/meta.json')); z = meta_all['zones']['lakes']; c = z['cell_ft']; x0, y0 = z['x0'], z['y0']
def dec(which):
    im = np.asarray(Image.open(f"{VD}/{z[which]['file']}").convert('RGB')).astype(float)
    return ((im[..., 0] * 256 + im[..., 1]) * z[which]['scale'] + z[which]['zmin'])[::-1]   # row 0 = south
dsm, dtm = dec('surface'), dec('ground'); ny, nx = dtm.shape
CLEAR_BUF, BLEND = 8.0, 10.0
# ---- trees with heights from the focus DXF
doc0 = ezdxf.readfile(f'{LK}/sausage_castle_lakes_focus_EPSG2236_ftUS.dxf'); msp0 = doc0.modelspace()
circles = [(e.dxf.center.x, e.dxf.center.y, e.dxf.radius, e.dxf.center.z) for e in msp0.query('CIRCLE[layer=="L-PLNT-TREE"]')]
texts = [(e.dxf.insert.x, e.dxf.insert.y, e.dxf.text) for e in msp0.query('TEXT[layer=="L-PLNT-ANNO"]')]
tmap = {(round(tx - 1), round(ty - 1)): t for tx, ty, t in texts}
trees = []
for i, (tx, ty, r, tz) in enumerate(circles):
    t = tmap.get((round(tx), round(ty)), ''); h = float(re.sub(r"[^0-9.]", "", t) or 0)
    trees.append(dict(id=i + 1, x=tx, y=ty, r=r, h=h, z=tz, crown=Point(tx, ty).buffer(r)))
lz = json.load(open(f'{LK}/lake_zones_concept.json')); units = json.load(open(f'{VD}/units.json'))
pads = {p['id']: dict(p, poly=Polygon(p['corners'])) for p in lz['pads']}
place = {pl['pad']: pl for pl in units['placements']}
jj, ii = np.mgrid[0:ny, 0:nx]; cx = x0 + (ii + 0.5) * c; cy = y0 + (jj + 0.5) * c
graded = dtm.copy(); cleared_mask = np.zeros((ny, nx), bool); pad_mask = np.zeros((ny, nx), bool); fringe_mask = np.zeros((ny, nx), bool)
rows = []; removed_ids = set()
for pid, p in pads.items():
    poly = p['poly']; clr = poly.buffer(CLEAR_BUF, join_style=2)
    inpad = shapely.contains_xy(poly, cx.ravel(), cy.ravel()).reshape(ny, nx)
    zz = dtm[inpad]; design = round(float(np.median(zz)), 1)
    cut = float(np.clip(zz - design, 0, None).sum() * c * c / 27); fill = float(np.clip(design - zz, 0, None).sum() * c * c / 27)
    near = shapely.contains_xy(poly.buffer(BLEND + 1), cx.ravel(), cy.ravel()).reshape(ny, nx) & ~inpad
    pts = [Point(a, b) for a, b in zip(cx[near], cy[near])]; d = np.array([poly.exterior.distance(pt) for pt in pts]) if pts else np.array([])
    t = np.clip(d / BLEND, 0, 1); t = t * t * (3 - 2 * t)
    graded[near] = design + (dtm[near] - design) * t; graded[inpad] = design
    pad_mask |= inpad; fringe_mask |= near
    cmask = shapely.contains_xy(clr, cx.ravel(), cy.ravel()).reshape(ny, nx); cleared_mask |= cmask
    rem = [tr for tr in trees if tr['crown'].intersects(poly) or clr.contains(Point(tr['x'], tr['y']))]
    for tr in rem: removed_ids.add(tr['id'])
    keep_near = [tr for tr in trees if tr['id'] not in {r['id'] for r in rem} and tr['crown'].intersects(clr.buffer(15))]
    rows.append(dict(pad=pid, zone=p['zone'], unit=place[pid]['unit'], center=[round(p['center'][0], 1), round(p['center'][1], 1)], existing_min=round(float(zz.min()), 1), existing_max=round(float(zz.max()), 1), existing_median=round(float(np.median(zz)), 1),
                     design_elev=design, cut_cy=round(cut, 1), fill_cy=round(fill, 1), net_cy=round(fill - cut, 1), clearing_sf=round(clr.area), trees_removed=len(rem), trees_removed_ids=[r['id'] for r in rem], tallest_removed_ft=max([r['h'] for r in rem], default=0), trees_kept_nearby=len(keep_near)))
    place[pid]['z_graded'] = design
removed = [tr for tr in trees if tr['id'] in removed_ids]
crown_union = unary_union([tr['crown'] for tr in removed]) if removed else Polygon()
crown_mask = shapely.contains_xy(crown_union, cx.ravel(), cy.ravel()).reshape(ny, nx) if removed else np.zeros((ny, nx), bool)
cleared_dsm = np.where(cleared_mask | crown_mask, graded, dsm); cleared_dsm = np.maximum(cleared_dsm, graded - 0.5)
tot = dict(pads=len(rows), trees_removed=len(removed), cut_cy=round(sum(r['cut_cy'] for r in rows), 1), fill_cy=round(sum(r['fill_cy'] for r in rows), 1), clearing_ac=round(float((cleared_mask | crown_mask).sum() * c * c / 43560), 2))
print(tot); print('by zone:', {zn: dict(pads=sum(1 for r in rows if r['zone'] == zn), trees=sum(r['trees_removed'] for r in rows if r['zone'] == zn)) for zn in 'ABCD'})
# ---- viewer data: cleared variant
def enc(arr, path):
    zmin = float(np.floor(arr.min())); q = np.clip(np.round((arr - zmin) / 0.01), 0, 65535).astype(np.uint16)
    rgb = np.zeros(arr.shape + (3,), np.uint8); rgb[..., 0] = q >> 8; rgb[..., 1] = q & 255; Image.fromarray(rgb[::-1], 'RGB').save(path, optimize=True); return zmin
def hillshade(a, cell):
    dy, dx = np.gradient(a, cell); sl = np.arctan(np.hypot(dx, dy)); asp = np.arctan2(-dx, dy); az, al = math.radians(315), math.radians(45)
    return np.clip(np.sin(al) * np.cos(sl) + np.cos(al) * np.sin(sl) * np.cos(az - asp), 0, 1)
chm = np.clip(cleared_dsm - graded, 0, None)
col = np.zeros((ny, nx, 3), np.float32); col[:] = np.array([0.66, 0.68, 0.42])
t = np.clip(chm / 60, 0, 1)[..., None]
col = np.where((chm > 1.5)[..., None], np.array([0.45, 0.60, 0.33]), col); col = np.where((chm > 8)[..., None], np.array([0.24, 0.45, 0.22]) * (1 - t) + np.array([0.12, 0.30, 0.13]) * t, col)
col = np.where((chm < 0.3)[..., None], np.array([0.72, 0.70, 0.50]), col)
segs = None
try:
    ll_to_sp_ = __import__('pyproj').Transformer.from_crs('EPSG:4326', 'EPSG:2236', always_xy=True)
    segs = unary_union([shp_transform(lambda a, b, zz=None: ll_to_sp_.transform(a, b), shape(f['geometry'])) for f in json.load(open('astatula_segment.geojson'))['features']])
    rmask = shapely.contains_xy(segs.buffer(9), cx.ravel(), cy.ravel()).reshape(ny, nx); col = np.where(rmask[..., None], np.array([0.42, 0.40, 0.38]), col)
except Exception as e: print('roads skipped', e)
wat = [w for w in [Polygon([(pp[0], pp[1]) for pp in e.get_points()]) for e in msp0.query('LWPOLYLINE[layer=="C-WATR-LIDAR"]')]]
wmask = shapely.contains_xy(unary_union(wat), cx.ravel(), cy.ravel()).reshape(ny, nx); col = np.where(wmask[..., None], np.array([0.20, 0.42, 0.62]), col)
col = np.where((fringe_mask | (crown_mask & ~pad_mask))[..., None], np.array([0.62, 0.71, 0.40]), col)   # mowed grass
col = np.where(pad_mask[..., None], np.array([0.80, 0.76, 0.64]), col)                                     # gravel pad
col = np.clip(col * (0.55 + 0.6 * hillshade(cleared_dsm, c)[..., None]), 0, 1)
Image.fromarray((col[::-1] * 255).astype(np.uint8), 'RGB').save(f'{VD}/lakes_cleared_color.jpg', quality=88, optimize=True)
zs = enc(cleared_dsm, f'{VD}/lakes_cleared_surface.png'); zg = enc(graded, f'{VD}/lakes_cleared_ground.png')
z['cleared'] = dict(surface=dict(file='lakes_cleared_surface.png', zmin=zs, scale=0.01), ground=dict(file='lakes_cleared_ground.png', zmin=zg, scale=0.01), color='lakes_cleared_color.jpg', label='Cleared and graded')
meta_all['zones']['lakes'] = z; json.dump(meta_all, open(f'{VD}/meta.json', 'w'), indent=1)
units['placements'] = [dict(pl, z_graded=place[pl['pad']]['z_graded']) for pl in units['placements']]; json.dump(units, open(f'{VD}/units.json', 'w'))
# ---- plan image
fig, ax = plt.subplots(figsize=(14, 12.5), dpi=150); ext = [x0, x0 + nx * c, y0, y0 + ny * c]
ax.imshow(hillshade(cleared_dsm, c), cmap='gray', extent=ext, origin='lower', vmin=-0.2, vmax=1.15)
for w in wat: ax.add_patch(MPoly(list(w.exterior.coords), closed=True, fc='#4aa3df', ec='#1f5f8b', alpha=0.6))
for tr in trees:
    rem = tr['id'] in removed_ids
    ax.add_patch(Circle((tr['x'], tr['y']), tr['r'], fc='none', ec='#d33' if rem else '#2f7a3a', lw=1.2 if rem else 0.4, alpha=0.95 if rem else 0.6))
    if rem: ax.plot([tr['x'] - tr['r'] * .6, tr['x'] + tr['r'] * .6], [tr['y'] - tr['r'] * .6, tr['y'] + tr['r'] * .6], color='#d33', lw=0.9); ax.plot([tr['x'] - tr['r'] * .6, tr['x'] + tr['r'] * .6], [tr['y'] + tr['r'] * .6, tr['y'] - tr['r'] * .6], color='#d33', lw=0.9)
for r in rows:
    p = pads[r['pad']]; clr = p['poly'].buffer(CLEAR_BUF, join_style=2)
    ax.add_patch(MPoly(list(clr.exterior.coords), closed=True, fc='#c8e08a', ec='#6a8a2a', alpha=0.45, lw=0.8, ls='--'))
    ax.add_patch(MPoly(list(p['poly'].exterior.coords), closed=True, fc='#f1e6c8', ec='#8a6d1a', lw=1.2))
    ax.text(p['center'][0], p['center'][1], f"{r['pad']}\nFG {r['design_elev']:.1f}\n-{r['cut_cy']:.0f}/+{r['fill_cy']:.0f} cy", ha='center', va='center', fontsize=5.2, color='#3b2f0a')
bx = unary_union([p['poly'] for p in pads.values()]).bounds
ax.set_xlim(bx[0] - 120, bx[2] + 120); ax.set_ylim(bx[1] - 120, bx[3] + 120); ax.set_aspect('equal'); ax.tick_params(labelsize=7)
ax.set_title(f"Clearing and grading plan, lake-zone pads: {tot['trees_removed']} trees out (red X), {tot['clearing_ac']} ac cleared, pads graded flat (FG = finished grade, NAVD88 ft), cut {tot['cut_cy']} cy / fill {tot['fill_cy']} cy\nclearing limit 8 ft beyond each pad (dashed), 10 ft blend to existing ground · EPSG:2236 ftUS · concept grade", fontsize=9)
fig.savefig(f'{LK}/clearing_grading_plan.jpg', dpi=150, bbox_inches='tight', pil_kwargs={'quality': 90}); plt.close(fig)
# ---- DXF
doc = ezdxf.new('R2018', setup=True); doc.header['$INSUNITS'] = 21; msp = doc.modelspace()
for n, colr in {'C-GRAD-PAD': 30, 'C-GRAD-LIMIT': 3, 'C-GRAD-ANNO': 2, 'C-TOPO-GRAD-MINR': 8, 'C-TOPO-GRAD-MAJR': 3, 'L-PLNT-REMV': 1, 'L-PLNT-KEEP': 92, 'L-PLNT-ANNO': 1, 'C-WATR-LAKE': 5, 'G-ANNO-NOTE': 7}.items(): doc.layers.add(n, color=colr)
for r in rows:
    p = pads[r['pad']]; msp.add_lwpolyline(list(p['poly'].exterior.coords), close=True, dxfattribs={'layer': 'C-GRAD-PAD', 'elevation': r['design_elev']})
    msp.add_lwpolyline(list(p['poly'].buffer(CLEAR_BUF, join_style=2).exterior.coords), close=True, dxfattribs={'layer': 'C-GRAD-LIMIT'})
    msp.add_text(f"{r['pad']} FG {r['design_elev']:.1f}  CUT {r['cut_cy']:.0f} CY  FILL {r['fill_cy']:.0f} CY  TREES OUT {r['trees_removed']}", height=2.2, dxfattribs={'layer': 'C-GRAD-ANNO'}).set_placement((p['center'][0], p['center'][1] - 2), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
for tr in trees:
    rem = tr['id'] in removed_ids; msp.add_circle((tr['x'], tr['y']), tr['r'], dxfattribs={'layer': 'L-PLNT-REMV' if rem else 'L-PLNT-KEEP', 'elevation': tr['z']})
    if rem:
        msp.add_line((tr['x'] - tr['r'] * .7, tr['y'] - tr['r'] * .7), (tr['x'] + tr['r'] * .7, tr['y'] + tr['r'] * .7), dxfattribs={'layer': 'L-PLNT-REMV'}); msp.add_line((tr['x'] - tr['r'] * .7, tr['y'] + tr['r'] * .7), (tr['x'] + tr['r'] * .7, tr['y'] - tr['r'] * .7), dxfattribs={'layer': 'L-PLNT-REMV'})
        msp.add_text(f"T{tr['id']} {tr['h']:.0f}'", height=1.8, dxfattribs={'layer': 'L-PLNT-ANNO'}).set_placement((tr['x'] + 1, tr['y'] + 1))
for w in wat: msp.add_lwpolyline(list(w.exterior.coords), close=True, dxfattribs={'layer': 'C-WATR-LAKE'})
xs = x0 + (np.arange(nx) + 0.5) * c; ys = y0 + (np.arange(ny) + 0.5) * c
gs = ndimage.gaussian_filter(graded, 1.0); gs[pad_mask] = graded[pad_mask]
cg = contourpy.contour_generator(x=xs, y=ys, z=gs, line_type=contourpy.LineType.Separate)
ring = unary_union([p['poly'].buffer(60) for p in pads.values()])
for lvl in range(int(math.floor(gs.min())), int(math.ceil(gs.max())) + 1):
    for arr in cg.lines(float(lvl)):
        if len(arr) < 3: continue
        ls = shapely.LineString(arr).simplify(0.4).intersection(ring)
        for part in (list(ls.geoms) if hasattr(ls, 'geoms') else [ls]):
            if part.geom_type == 'LineString' and part.length > 10: msp.add_lwpolyline(list(part.coords), dxfattribs={'layer': 'C-TOPO-GRAD-MAJR' if lvl % 5 == 0 else 'C-TOPO-GRAD-MINR', 'elevation': float(lvl)})
msp.add_mtext(f"CLEARING AND GRADING - LAKE-ZONE PADS ({datetime.date.today()})\\PPADS GRADED FLAT AT THE MEDIAN EXISTING GRADE (BALANCED CUT/FILL), {BLEND:.0f} FT BLEND TO EXISTING; CLEARING LIMIT {CLEAR_BUF:.0f} FT BEYOND EACH PAD\\P"
              f"TREES OUT: {tot['trees_removed']} (L-PLNT-REMV, 2018 CANOPY); CLEARED AREA {tot['clearing_ac']} AC; TOTAL CUT {tot['cut_cy']} CY, FILL {tot['fill_cy']} CY\\PGRADED 1 FT CONTOURS ON C-TOPO-GRAD-*; EPSG:2236 ftUS, NAVD88 FT; CONCEPT GRADE, NOT FOR CONSTRUCTION",
              dxfattribs={'layer': 'G-ANNO-NOTE', 'char_height': 4, 'width': 520}).set_location((bx[0] - 100, bx[3] + 140))
doc.saveas(f'{LK}/clearing_grading_EPSG2236_ftUS.dxf')
json.dump(dict(generated=str(datetime.date.today()), rules=dict(clearing_limit_ft=CLEAR_BUF, blend_ft=BLEND, pad_grade='median existing'), totals=tot, pads=rows, trees_removed=[dict(id=t['id'], x=round(t['x'], 1), y=round(t['y'], 1), crown_r=round(t['r'], 1), height_ft=t['h']) for t in removed]), open(f'{LK}/clearing_grading.json', 'w'), indent=1)
md = f"# Clearing and grading, lake-zone pads\n\nGenerated {datetime.date.today()}. Concept grade.\n\nRules: each 35 × 50 ft pad is graded flat at the median existing grade inside it (balanced cut and fill), blended to existing ground over 10 ft; the clearing limit is 8 ft beyond the pad; any 2018 tree whose crown touches the pad or whose trunk stands inside the clearing limit comes out.\n\n| Total | Value |\n|---|---|\n| Pads | {tot['pads']} |\n| Trees removed | {tot['trees_removed']} |\n| Cleared area | {tot['clearing_ac']} ac |\n| Cut / fill | {tot['cut_cy']} / {tot['fill_cy']} cu yd |\n\n| Pad | Zone | Unit | Existing (min / median / max) | Finished grade | Cut cy | Fill cy | Trees out | Tallest out |\n|---|---|---|---|---|---|---|---|---|\n" + '\n'.join(f"| {r['pad']} | {r['zone']} | {r['unit']} | {r['existing_min']} / {r['existing_median']} / {r['existing_max']} | {r['design_elev']} | {r['cut_cy']} | {r['fill_cy']} | {r['trees_removed']} | {r['tallest_removed_ft']:.0f} ft |" for r in rows) + "\n\nFiles: `clearing_grading_EPSG2236_ftUS.dxf` (pads at finished grade, clearing limits, trees to remove with X marks and IDs, kept trees, graded 1 ft contours), `clearing_grading_plan.jpg`, `clearing_grading.json`. The 3D viewer's Lakes zone has a \"Cleared and graded\" toggle showing the surface with those trees gone and the pads flat.\n"
open(f'{LK}/CLEARING-GRADING.md', 'w').write(md)
# ---- 3D mock-up renders and DXF
def unit_tris(key):
    tris = []; cols = []
    for part in units['units'][key]['parts']:
        V = np.array(part['positions']).reshape(-1, 3); F = np.array(part['indices']).reshape(-1, 3); cc = np.array([int(part['color'][i:i + 2], 16) / 255 for i in (1, 3, 5)])
        tris.append(V[F]); cols.append(np.repeat(cc[None], len(F), 0))
    return np.vstack(tris), np.vstack(cols)
UT = {k: unit_tris(k) for k in units['units']}
def placed_tris(pl):
    T, C = UT[pl['unit']]; a = math.radians(pl['rot_deg']); R = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
    return T @ R.T + np.array([pl['x'], pl['y'], pl['z_graded']]), C
def shade_cols(T, C, light=np.array([0.4, -0.6, 0.7])):
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); L = np.linalg.norm(n, axis=1, keepdims=True); n = n / np.where(L == 0, 1, L)
    s = 0.5 + 0.5 * np.clip(n @ (light / np.linalg.norm(light)), 0, 1); return np.clip(C * s[:, None], 0, 1)
def render(view_bbox, step, elev, azim, path, title):
    bx0, by0, bx1, by1 = view_bbox; i0, i1 = max(0, int((bx0 - x0) / c)), min(nx, int((bx1 - x0) / c)); j0, j1 = max(0, int((by0 - y0) / c)), min(ny, int((by1 - y0) / c))
    H = cleared_dsm[j0:j1:step, i0:i1:step]; colc = col[j0:j1:step, i0:i1:step]
    xs_ = x0 + (np.arange(i0, i1, step) + 0.5) * c; ys_ = y0 + (np.arange(j0, j1, step) + 0.5) * c; X, Y = np.meshgrid(xs_, ys_)
    fig = plt.figure(figsize=(16, 11), dpi=120); ax = fig.add_subplot(111, projection='3d')
    ax.plot_surface(X, Y, H, facecolors=colc, rstride=1, cstride=1, linewidth=0, antialiased=False, shade=False)
    Ts, Cs = [], []
    for pl in units['placements']:
        if bx0 <= pl['x'] <= bx1 and by0 <= pl['y'] <= by1: T, C = placed_tris(pl); Ts.append(T); Cs.append(C)
    if Ts:
        T = np.vstack(Ts); C = np.vstack(Cs); ax.add_collection3d(Poly3DCollection(T, facecolors=shade_cols(T, C), edgecolors='none'))
    zr = H.max() - H.min() + 40; ax.set_box_aspect((bx1 - bx0, by1 - by0, zr)); ax.set_xlim(bx0, bx1); ax.set_ylim(by0, by1); ax.set_zlim(H.min(), H.min() + zr)
    ax.view_init(elev=elev, azim=azim); ax.set_axis_off(); fig.subplots_adjust(0, 0, 1, 1); fig.text(0.01, 0.01, title, fontsize=9, color='#333')
    fig.savefig(path, dpi=120, pil_kwargs={'quality': 88}); plt.close(fig); print('render', os.path.basename(path))
render((bx[0] - 90, bx[1] - 90, bx[2] + 90, bx[3] + 90), 2, 38, -55, f'{MO}/lakes_cleared_mockup_overall.jpg', '3D mock-up: lake-zone pads cleared and graded, 22 themed cabins placed · lidar surface with removed trees gone · view from the south-west')
cz = [p['poly'].centroid for pid, p in pads.items() if p['zone'] == 'C']; cxm, cym = np.mean([q.x for q in cz]), np.mean([q.y for q in cz])
render((cxm - 220, cym - 170, cxm + 220, cym + 170), 1, 30, -35, f'{MO}/lakes_cleared_mockup_zoneC.jpg', '3D mock-up close-up: zone C mushroom cabins on cleared, graded pads along the loop lane')
cz = [p['poly'].centroid for pid, p in pads.items() if p['zone'] == 'A']; cxm, cym = np.mean([q.x for q in cz]), np.mean([q.y for q in cz])
render((cxm - 220, cym - 170, cxm + 220, cym + 170), 1, 30, 200, f'{MO}/lakes_cleared_mockup_zoneA.jpg', '3D mock-up close-up: zone A haunted-house cabins on cleared, graded pads')
# mock-up DXF: graded terrain mesh at 4 ft + blocks
doc = ezdxf.new('R2018', setup=True); doc.header['$INSUNITS'] = 21; msp = doc.modelspace()
doc.layers.add('C-TOPO-GRAD-MESH', color=254); doc.layers.add('C-GRAD-PAD', color=30); doc.layers.add('A-UNIT-INSERT', color=30); doc.layers.add('C-WATR-LAKE', color=5)
step = 2; bb = (max(0, int((bx[0] - 100 - x0) / c)), min(nx, int((bx[2] + 100 - x0) / c)), max(0, int((bx[1] - 100 - y0) / c)), min(ny, int((bx[3] + 100 - y0) / c)))
gx = np.arange(bb[0], bb[1], step); gy = np.arange(bb[2], bb[3], step); tz = graded[np.ix_(gy, gx)]; W_ = len(gx); tm = MeshBuilder()
tm.add_vertices([(float(x0 + (gx[b] + 0.5) * c), float(y0 + (gy[a] + 0.5) * c), float(tz[a, b])) for a in range(len(gy)) for b in range(W_)])
for a in range(len(gy) - 1):
    for b in range(W_ - 1): tm.faces.append((a * W_ + b, a * W_ + b + 1, (a + 1) * W_ + b + 1, (a + 1) * W_ + b))
tm.render_mesh(msp, dxfattribs={'layer': 'C-TOPO-GRAD-MESH'})
for k, u in units['units'].items():
    blk = doc.blocks.new(name=k.upper())
    for part in u['parts']:
        ln = 'M-' + k.upper() + '-' + part['name'].upper().replace(' ', '-'); doc.layers.add(ln, true_color=int(part['color'][1:], 16))
        mb = MeshBuilder(); mb.add_vertices([tuple(part['positions'][i:i + 3]) for i in range(0, len(part['positions']), 3)])
        for i in range(0, len(part['indices']), 3): mb.faces.append(tuple(part['indices'][i:i + 3]))
        mb.render_mesh(blk, dxfattribs={'layer': ln})
for pl in units['placements']:
    msp.add_blockref(pl['unit'].upper(), (pl['x'], pl['y'], pl['z_graded']), dxfattribs={'rotation': pl['rot_deg'], 'layer': 'A-UNIT-INSERT'})
    p = pads[pl['pad']]; msp.add_lwpolyline(list(p['poly'].exterior.coords), close=True, dxfattribs={'layer': 'C-GRAD-PAD', 'elevation': pl['z_graded']})
for w in wat: msp.add_lwpolyline(list(w.exterior.coords), close=True, dxfattribs={'layer': 'C-WATR-LAKE'})
doc.saveas(f'{MO}/lakes_cleared_3d_mockup_EPSG2236_ftUS.dxf'); print('mockup DXF', os.path.getsize(f'{MO}/lakes_cleared_3d_mockup_EPSG2236_ftUS.dxf') // 1024, 'KB'); print('done')
