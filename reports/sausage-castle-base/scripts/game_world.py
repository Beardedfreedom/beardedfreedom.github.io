#!/usr/bin/env python3
"""Pack the property into one world file for the browser game (game/data/world.json).

Sources (all in this folder):
  viewer/data/meta.json + site_ground.png + site_surface.png + site_color.jpg   whole-site 6 ft grids
  sausage_castle_base_EPSG2236_ftUS.dxf        68 buildings (lidar-shaped 3D meshes + labels), 35 road centrelines, lake outlines
  masterplan/florida_freedom_world_masterplan_EPSG2236_ftUS.dxf  the 12 programme polygons and the trail loop
  masterplan/masterplan.json                   names, notes and acreage of the 12 programme areas
  viewer/data/units.json                       the four cabin meshes and the 22 placements
  focus/lakes/lake_zones_concept.json          pads (used to keep the pads clear of trees)
Trees come from the canopy height model (surface minus ground): every local maximum taller than 12 ft is a
tree, with its height; crown radius is estimated from height. Coordinates stay in EPSG:2236 US survey feet;
the game converts to its own axes.

Usage: python3 scripts/game_world.py [--base .] [--out game/data]
"""
import argparse, json, math, random, re, shutil
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, maximum_filter
import ezdxf
import shapely
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union

ap = argparse.ArgumentParser()
ap.add_argument('--base', type=Path, default=Path(__file__).resolve().parent.parent)
ap.add_argument('--out', type=Path, default=None)
ap.add_argument('--seed', type=int, default=3)
a = ap.parse_args()
BASE = a.base.resolve(); OUT = (a.out or BASE / 'game' / 'data').resolve(); OUT.mkdir(parents=True, exist_ok=True)
rng = random.Random(a.seed)

meta = json.load(open(BASE / 'viewer/data/meta.json'))['zones']['site']
x0, y0, cell = meta['x0'], meta['y0'], meta['cell_ft']


def decode(fn, spec):
    arr = np.asarray(Image.open(BASE / 'viewer/data' / fn).convert('RGB')).astype(np.float32)   # row 0 = north
    return (arr[..., 0] * 256 + arr[..., 1]) * spec['scale'] + spec['zmin']


S = decode(meta['surface']['file'], meta['surface']); G = decode(meta['ground']['file'], meta['ground']); ny, nx = G.shape


def ground_z(x, y):
    fi = (x - x0) / cell - 0.5; fj = (ny - 1) - ((y - y0) / cell - 0.5)
    i0 = int(np.clip(math.floor(fi), 0, nx - 2)); j0 = int(np.clip(math.floor(fj), 0, ny - 2)); ti = float(np.clip(fi - i0, 0, 1)); tj = float(np.clip(fj - j0, 0, 1))
    return float(G[j0, i0] * (1 - ti) * (1 - tj) + G[j0, i0 + 1] * ti * (1 - tj) + G[j0 + 1, i0] * (1 - ti) * tj + G[j0 + 1, i0 + 1] * ti * tj)


# ---- base DXF: buildings, roads, water
d = ezdxf.readfile(BASE / 'sausage_castle_base_EPSG2236_ftUS.dxf'); ms = d.modelspace()
labels = [(e.dxf.insert.x, e.dxf.insert.y, e.dxf.text) for e in ms.query('TEXT[layer=="A-BLDG-ANNO"]')]
buildings = []; footprints = []
meshes = list(ms.query('MESH[layer=="A-BLDG-3D"]')); fps = list(ms.query('LWPOLYLINE[layer=="A-BLDG-FTPT"]'))
for k, e in enumerate(meshes):
    md = e.get_data(); V = [(round(v[0], 2), round(v[1], 2), round(v[2], 2)) for v in md.vertices]
    F = []
    for face in md.faces:
        idx = list(face)
        for t in range(1, len(idx) - 1): F.append((idx[0], idx[t], idx[t + 1]))     # fan-triangulate
    cxm = sum(v[0] for v in V) / len(V); cym = sum(v[1] for v in V) / len(V)
    lab = min(labels, key=lambda L: (L[0] - cxm) ** 2 + (L[1] - cym) ** 2) if labels else None
    sf = h = None
    if lab:
        m1 = re.search(r'([\d,]+)\s*sf', lab[2]); m2 = re.search(r"h=(\d+(?:\.\d+)?)", lab[2])
        sf = int(m1.group(1).replace(',', '')) if m1 else None; h = float(m2.group(1)) if m2 else None
    fp = fps[k] if k < len(fps) else None
    fpts = [(p[0], p[1]) for p in fp.get_points()] if fp is not None else []
    if len(fpts) >= 3: footprints.append(Polygon(fpts).buffer(0))
    buildings.append({'sf': sf, 'h': h, 'v': [c for v in V for c in v], 'f': [i for f in F for i in f], 'fp': [round(c, 1) for p in fpts for c in p]})
castle = max(range(len(buildings)), key=lambda i: buildings[i]['sf'] or 0); buildings[castle]['castle'] = True
roads = [[(round(p[0], 1), round(p[1], 1)) for p in e.get_points()] for e in ms.query('LWPOLYLINE[layer=="C-ROAD-CNTR"]')]
road_names = [(e.dxf.insert.x, e.dxf.insert.y, e.dxf.text) for e in ms.query('TEXT[layer=="C-ROAD-ANNO"]')]
water = []
for e in ms.query('LWPOLYLINE[layer=="C-WATR-BNDY"]'):
    pts = [(p[0], p[1]) for p in e.get_points()]
    if len(pts) < 3: continue
    poly = Polygon(pts).buffer(0).buffer(4, join_style='round').buffer(-4, join_style='round').simplify(1.0)
    if poly.geom_type == 'MultiPolygon': poly = max(poly.geoms, key=lambda g: g.area)
    wse = e.dxf.elevation
    if not wse:   # match by acreage to the water table in the metadata
        ac = poly.area / 43560; wse = min(meta['water'], key=lambda w: abs(w['acres'] - ac))['wse']
    water.append({'wse': round(float(wse), 2), 'pts': [round(c, 1) for p in list(poly.exterior.coords)[:-1] for c in p]})
water_union = unary_union([Polygon(list(zip(w['pts'][::2], w['pts'][1::2]))) for w in water]) if water else Polygon()

# ---- master plan: programme polygons, trail loop
mp = json.load(open(BASE / 'masterplan/masterplan.json')); prog = {p['key']: p for p in mp['programme']}
dm = ezdxf.readfile(BASE / 'masterplan/florida_freedom_world_masterplan_EPSG2236_ftUS.dxf'); mms = dm.modelspace()
attractions = []; attr_polys = {}
for e in mms.query('LWPOLYLINE'):
    if not e.dxf.layer.startswith('L-PROG-'): continue
    key = e.dxf.layer[7:].lower(); pts = [(round(p[0], 1), round(p[1], 1)) for p in e.get_points()]
    p = prog.get(key) or next((v for v in prog.values() if v['key'].startswith(key[:4])), None)
    if p is None or len(pts) < 3: continue
    attr_polys[key] = Polygon(pts).buffer(0)
    attractions.append({'key': key, 'name': p['name'], 'acres': p['acres'], 'note': p['note'], 'poster': p['poster'], 'centroid': [round(c, 1) for c in p['centroid']], 'pts': [c for q in pts for c in q]})
trail = [[(round(p[0], 1), round(p[1], 1)) for p in e.get_points()] for e in mms.query('LWPOLYLINE[layer=="C-TRAIL-LOOP"]')]

# ---- cabins
units = json.load(open(BASE / 'viewer/data/units.json'))
cabins = [{'pad': pl['pad'], 'zone': pl['zone'], 'unit': pl['unit'], 'x': pl['x'], 'y': pl['y'], 'z': pl.get('z_graded', pl['z']), 'rot': pl['rot_deg']} for pl in units['placements']]
lz = json.load(open(BASE / 'focus/lakes/lake_zones_concept.json')); pads_union = unary_union([Polygon(p['corners']) for p in lz['pads']])

# ---- trees from the canopy height model
C = gaussian_filter(np.clip(S - G, 0, None), 1.0); peaks = (C == maximum_filter(C, size=5)) & (C > 12)
jj, ii = np.nonzero(peaks)
keep_out = unary_union([pads_union.buffer(12), unary_union(footprints).buffer(6), water_union.buffer(4),
                        unary_union([LineString(r) for r in roads if len(r) > 1]).buffer(9)] +
                       [attr_polys[k] for k in ('gate', 'arena', 'rv', 'ufo', 'lagoon') if k in attr_polys])
trees = []
for j, i in zip(jj, ii):
    x = x0 + (i + 0.5) * cell + rng.uniform(-2, 2); y = y0 + (ny - 1 - j + 0.5) * cell + rng.uniform(-2, 2); h = float(C[j, i])
    if keep_out.contains(Point(x, y)): continue
    r = min(max(h * 0.22, 6.0), 20.0) * rng.uniform(0.8, 1.2); kind = 1 if (h > 50 and rng.random() < 0.7) else 0   # 1 pine, 0 oak
    if water_union.distance(Point(x, y)) < 60 and h > 30 and rng.random() < 0.5: kind = 2                          # cypress near water
    trees.append([round(x, 1), round(y, 1), round(h, 1), round(r, 1), kind])

# ---- golf course (masterplan/golf, from scripts/golf_course.py + golf_3d.py): ponds become water, the holes are cleared
golf = None; gfile = BASE / 'masterplan/golf/golf_course.json'
if gfile.exists():
    gc = json.load(open(gfile))
    if 'hazards' in gc:
        corr = [unary_union([LineString([tuple(h['tee']), tuple(h['green'])]).buffer(48, cap_style=2), Point(*h['green']).buffer(55), Point(*h['tee']).buffer(28)]) for h in gc['holes']]
        course_u = unary_union(corr); n0 = len(trees)
        trees = [t for t in trees if not course_u.contains(Point(t[0], t[1]))]
        for h in gc['holes']:
            if h.get('pond_poly'): water.append({'wse': h['water_level_ft'], 'pts': [c for q in h['pond_poly'] for c in q]})
        golf = {'clubhouse': gc['clubhouse'], 'par': gc['par'], 'yards': gc['yards'],
                'holes': [{'n': h['hole'], 'par': h['par'], 'yards': h['yards'], 'tee': h['tee'], 'green': h['green'], 'carry': h.get('carry_yd'),
                           'hazard': 'water' if h.get('water_carry') else ('sand' if h.get('sand_carry') else '')} for h in gc['holes']]}
        print(f'golf: {len(gc["holes"])} holes, {n0 - len(trees)} trees cleared, {sum(1 for h in gc["holes"] if h.get("pond_poly"))} ponds')

# ---- spawn: on the house drive at the gate area, looking toward the Castle
cb = buildings[castle]; cxb = np.mean(cb['v'][0::3]); cyb = np.mean(cb['v'][1::3])
gate = prog['gate']['centroid']; spawn = {'x': gate[0], 'y': gate[1] - 80, 'look': [round(float(cxb), 1), round(float(cyb), 1)]}

world = {
    'generated': mp.get('generated'), 'crs': 'EPSG:2236 ftUS, NAVD88 ft',
    'site': {'x0': x0, 'y0': y0, 'cell': cell, 'nx': nx, 'ny': ny, 'w': meta['width_ft'], 'h': meta['height_ft'], 'zmin': meta['ground']['zmin'], 'scale': meta['ground']['scale'],
             'heightmap': 'site_ground.png', 'color': 'site_color.jpg', 'z_range': meta['z_range']},
    'water': water, 'roads': [[c for p in r for c in p] for r in roads], 'trail': [[c for p in r for c in p] for r in trail],
    'road_names': [{'x': round(x, 1), 'y': round(y, 1), 'name': t} for x, y, t in road_names],
    'buildings': buildings, 'castle': castle, 'trees': trees, 'units': units['units'], 'cabins': cabins, 'attractions': attractions, 'spawn': spawn,
    **({'golf': golf} if golf else {}),
}
(OUT / 'world.json').write_text(json.dumps(world, separators=(',', ':')))
for fn in ('site_ground.png', 'site_color.jpg'):
    shutil.copyfile(BASE / 'viewer/data' / fn, OUT / fn)
if golf:   # paint the course onto the game's ground colours and dig the ponds and bunkers into its heightmap
    from PIL import ImageDraw
    SC = 4; col = Image.open(OUT / 'site_color.jpg').convert('RGB'); ov = Image.new('RGBA', (col.width * SC, col.height * SC), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    def PX(x, y): return ((x - x0) / cell * SC, (ny - (y - y0) / cell) * SC)
    def fillp(pts, rgba): dr.polygon([PX(*q) for q in pts], fill=rgba)
    for g_ in corr: fillp(list(g_.exterior.coords), (104, 168, 72, 235))
    for h in gc['holes']:
        if h.get('pond_poly'): fillp(h['pond_poly'], (36, 92, 118, 255))
        for b in h.get('bunker_polys', []): fillp(b, (232, 214, 160, 255))
        fillp(h['green_poly'], (70, 196, 82, 255)); fillp(h['tee_poly'], (150, 214, 110, 255))
    col = Image.alpha_composite(col.convert('RGBA'), ov.resize(col.size, Image.LANCZOS)).convert('RGB'); col.save(OUT / 'site_color.jpg', quality=92)
    spec = meta['ground']; hm = np.asarray(Image.open(OUT / 'site_ground.png').convert('RGB')).astype(np.int64).copy(); Z = (hm[..., 0] * 256 + hm[..., 1]) * spec['scale'] + spec['zmin']
    for h in gc['holes']:
        for pts, kind in ([(h['pond_poly'], 'pond')] if h.get('pond_poly') else []) + [(b, 'bunker') for b in h.get('bunker_polys', [])]:
            mk = Image.new('L', (nx, ny), 0); ImageDraw.Draw(mk).polygon([((x - x0) / cell, ny - (y - y0) / cell) for x, y in pts], fill=255); m_ = np.asarray(mk) > 0
            Z[m_] = np.minimum(Z[m_], h['water_level_ft'] - 3.0) if kind == 'pond' else Z[m_] - 1.5
    v = np.clip(np.round((Z - spec['zmin']) / spec['scale']), 0, 65535).astype(np.int64); hm[..., 0] = v // 256; hm[..., 1] = v % 256
    Image.fromarray(hm.astype(np.uint8), 'RGB').save(OUT / 'site_ground.png')
print(f"world.json: {(OUT / 'world.json').stat().st_size // 1024} KB | buildings {len(buildings)} (castle #{castle}, {cb['sf']} sf, h {cb['h']} ft) | roads {len(roads)} | trail {len(trail)} | water {len(water)} | trees {len(trees)} | cabins {len(cabins)} | attractions {len(attractions)}")
