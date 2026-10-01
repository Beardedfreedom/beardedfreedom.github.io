#!/usr/bin/env python3
"""Fit an 18-hole course into the land the Florida Freedom World plan leaves free (EPSG:2236 ftUS, concept grade).

Steps
-----
1. Estate: an assumed set of 40-acre quarter-quarter sections (default SW, NW, SE of the PLSS breaks the
   lidar shows at E 427,050 and N 1,578,500). The parcel lines are NOT confirmed; see --parcels.
2. Free land: estate minus a setback from its edge, the master-plan programme areas (except the small
   Gator Greens pitch-and-putt, which the course replaces), the buildings with a safety buffer, the
   lakes and pond, and the main drives.
3. Routing: a depth-first search lays 18 straight holes one after another. Each hole is a corridor
   (tee, fairway, green) that must sit inside the free land and must not overlap an earlier hole; the
   next tee starts a short walk from the previous green; hole 1 starts and hole 18 should finish near
   the clubhouse. It first tries an executive course (par 3s and par 4s) and falls back to a par-3
   course if that does not fit.
4. Outputs (masterplan/golf/): plan image over the land-cover map, DXF, JSON and a summary.

Usage:  python3 scripts/golf_course.py [--parcels SW,NW,SE] [--time 240] [--seed 3]
Needs: numpy, shapely, ezdxf, Pillow.
"""
import argparse, gzip, json, math, os, random, time
import numpy as np
import ezdxf
from shapely.geometry import Point, LineString, Polygon, box, MultiPolygon
from shapely.ops import unary_union
from shapely.prepared import prep
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument('--base', default=os.path.join(os.path.dirname(__file__), '..'))
ap.add_argument('--parcels', default='SW,NW,SE', help='quarter-quarters assumed to be the estate (SW, NW, NE, SE)')
ap.add_argument('--time', type=float, default=240, help='search time budget per course type (s)')
ap.add_argument('--seed', type=int, default=3)
ap.add_argument('--setback', type=float, default=75, help='setback from the estate edge (ft)')
args = ap.parse_args()
B = os.path.abspath(args.base); OUT = os.path.join(B, 'masterplan', 'golf'); os.makedirs(OUT, exist_ok=True)
rng = random.Random(args.seed)

# ------------------------------------------------------------------ estate and constraints
E_BRK, N_BRK, QQ = 427050.0, 1578500.0, 1320.0
QQS = {'SW': box(E_BRK - QQ, N_BRK - QQ, E_BRK, N_BRK), 'NW': box(E_BRK - QQ, N_BRK, E_BRK, N_BRK + QQ),
       'NE': box(E_BRK, N_BRK, E_BRK + QQ, N_BRK + QQ), 'SE': box(E_BRK, N_BRK - QQ, E_BRK + QQ, N_BRK)}
parcels = [p.strip().upper() for p in args.parcels.split(',') if p.strip()]
estate = unary_union([QQS[p] for p in parcels])
inner = estate.buffer(-args.setback)

mp = ezdxf.readfile(f'{B}/masterplan/florida_freedom_world_masterplan_EPSG2236_ftUS.dxf').modelspace()
prog = {}
for e in mp.query('LWPOLYLINE'):
    if e.dxf.layer.startswith('L-PROG-'):
        prog[e.dxf.layer[7:].lower()] = Polygon([(p[0], p[1]) for p in e.get_points()]).buffer(0)
base = ezdxf.readfile(f'{B}/sausage_castle_base_EPSG2236_ftUS.dxf').modelspace()
bldgs = [Polygon([(p[0], p[1]) for p in e.get_points()]).buffer(0) for e in base.query('LWPOLYLINE[layer=="A-BLDG-FTPT"]')]
water = [Polygon([(p[0], p[1]) for p in e.get_points()]).buffer(0) for e in base.query('LWPOLYLINE[layer=="C-WATR-BNDY"]')]
roads = [LineString([(p[0], p[1]) for p in e.get_points()]) for e in base.query('LWPOLYLINE[layer=="C-ROAD-CNTR"]') if len(list(e.get_points())) > 1]
world = json.load(open(f'{B}/game/data/world.json'))
trees = np.array([[t[0], t[1], t[2], t[3]] for t in world['trees']])

KEEP_GOLF = 'golf'   # the 3.3 ac pitch-and-putt area is absorbed by the course
excl = [g.buffer(40) for k, g in prog.items() if k != KEEP_GOLF]
excl += [b.buffer(100) for b in bldgs]            # safety buffer around buildings
excl += [w.buffer(30) for w in water]
road_u = unary_union([r for r in roads]) if roads else None   # internal drives: holes may cross them (cart crossings are counted)
free = inner.difference(unary_union(excl)).buffer(-1).buffer(1)
free = unary_union([g for g in getattr(free, 'geoms', [free]) if g.area > 20000])   # drop slivers under ~0.5 ac
AC = 43560.0
print(f'estate {estate.area / AC:.1f} ac ({",".join(parcels)}), inside setback {inner.area / AC:.1f} ac, free {free.area / AC:.1f} ac')

# terrain (3 ft DTM) for tee and green elevations
with gzip.open(f'{B}/sausage_castle_dtm_3ft_EPSG2236.asc.gz', 'rt') as f:
    hdr = {}
    for _ in range(6):
        k, v = f.readline().split(); hdr[k.lower()] = float(v)
    dtm = np.loadtxt(f, dtype=np.float32)
def zat(x, y):
    i = int((x - hdr['xllcorner']) / hdr['cellsize']); j = int(hdr['nrows'] - 1 - (y - hdr['yllcorner']) / hdr['cellsize'])
    i = min(max(i, 0), dtm.shape[1] - 1); j = min(max(j, 0), dtm.shape[0] - 1); v = float(dtm[j, i]); return v if v > -9000 else float('nan')

# clubhouse: the Castle (existing house) doubles as clubhouse and pro shop; the first tee is the nearest free ground
castle = prog.get('castle', Point(426828, 1577904).buffer(90))
club_pt = Point(*castle.centroid.coords[0])

# ------------------------------------------------------------------ hole geometry
YD = 3.0
SPEC = {3: dict(lens=[100, 120, 140, 160, 180, 200], hw=48, green=55, tee=28),
        4: dict(lens=[260, 290, 320, 350], hw=70, green=65, tee=32)}
def corridor(tee, ang, length_ft, par):
    s = SPEC[par]; gx, gy = tee.x + length_ft * math.cos(ang), tee.y + length_ft * math.sin(ang)
    line = LineString([(tee.x, tee.y), (gx, gy)])
    poly = unary_union([line.buffer(s['hw'], cap_style=2), Point(gx, gy).buffer(s['green']), tee.buffer(s['tee'])])
    return poly, Point(gx, gy)

def search(max4, budget, n_holes=18):
    """depth-first search with ordered candidates and restarts; par 4s are used where they fit (up to max4).
    Two loops of nine: holes 9 and 18 finish near the clubhouse."""
    t0 = time.time(); best = {'holes': []}
    def better(a, b):
        ka = (len(a), sum(h['par'] for h in a), -sum(h['walk'] for h in a)); kb = (len(b), sum(h['par'] for h in b), -sum(h['walk'] for h in b)); return ka > kb
    def candidates(i, used_u, prev_green, n4):
        avail = free.difference(used_u.buffer(25)) if used_u is not None else free
        if avail.is_empty: return []
        pa = prep(avail); edge = avail.boundary; out = []
        origin = club_pt if prev_green is None else prev_green
        k = i % 9; home_w = max(0, k - 5) / 3.0                       # pull the last holes of each nine back home
        pars = (4, 3) if n4 < max4 else (3,)
        for rings in ((90, 150, 220), (320, 460, 620)):                 # short walk first; a cart transfer only if nothing fits
            r_list = (160, 260, 360, 460) if prev_green is None else rings
            tees = [Point(origin.x + r * math.cos(a), origin.y + r * math.sin(a)) for r in r_list for a in np.radians(np.arange(0, 360, 20))]
            for tee in tees:
                for par in pars:
                    sp = SPEC[par]
                    if not pa.contains(tee.buffer(sp['tee'])): continue
                    walk = tee.distance(origin) if prev_green is not None else 0.0
                    for ang in np.radians(np.arange(0, 360, 12)):
                        for L in sp['lens']:
                            gx, gy = tee.x + L * YD * math.cos(ang), tee.y + L * YD * math.sin(ang)
                            if not pa.contains(Point(gx, gy)): continue
                            poly, green = corridor(tee, ang, L * YD, par)
                            if not pa.contains(poly): continue
                            dhome = green.distance(club_pt)
                            if k == 8 and dhome > 900: continue           # holes 9 and 18 must come back to the Castle
                            packed = abs(poly.distance(used_u) - 25) if used_u is not None else 0.0
                            hug = poly.distance(edge)
                            score = (3.0 if par == 4 else 0.0) + L / 45.0 - min(packed, 200) / 35.0 - min(hug, 200) / 45.0 - walk / 160.0 - home_w * dhome / 120.0 + rng.random() * 0.8
                            out.append((score, tee, green, poly, L, par, walk))
            if out: break
        out.sort(key=lambda c: -c[0])
        return out[:6] + (rng.sample(out[6:50], min(2, len(out[6:50]))) if len(out) > 6 else [])
    def dfs(i, holes, used_u, prev_green, n4):
        nonlocal best
        if better(holes, best['holes']): best = {'holes': list(holes)}
        if i == n_holes: return True
        if time.time() - t0 > budget: return False
        for score, tee, green, poly, L, par, walk in candidates(i, used_u, prev_green, n4):
            holes.append({'par': par, 'yards': L, 'tee': tee, 'green': green, 'poly': poly, 'walk': walk})
            if dfs(i + 1, holes, poly if used_u is None else used_u.union(poly), green, n4 + (par == 4)): return True
            holes.pop()
            if time.time() - t0 > budget: break
        return False
    while time.time() - t0 < budget:
        if dfs(0, [], None, None, 0): break
    return best['holes']

result = None
for max4 in (8, 6, 4, 2, 0):
    holes = search(max4, args.time)
    n4 = sum(1 for h in holes if h['par'] == 4)
    print(f'max par 4s {max4}: fitted {len(holes)} of 18 holes, {n4} par 4s, par {sum(h["par"] for h in holes)}')
    if result is None or (len(holes), sum(h['par'] for h in holes)) > (len(result), sum(h['par'] for h in result)): result = holes
    if len(holes) == 18: break
holes = result
n4 = sum(1 for h in holes if h['par'] == 4); kind = 'par-3' if n4 == 0 else 'executive'

# ------------------------------------------------------------------ measure and export
course_u = unary_union([h['poly'] for h in holes])
tree_xy = [Point(t[0], t[1]) for t in trees]
pc = prep(course_u); cleared = [i for i, p in enumerate(tree_xy) if pc.contains(p)]
rows = []
for n, h in enumerate(holes, 1):
    zt, zg = zat(h['tee'].x, h['tee'].y), zat(h['green'].x, h['green'].y); ph = prep(h['poly'])
    nt = sum(1 for i in cleared if ph.contains(tree_xy[i]))
    walk = 0.0 if n == 1 else holes[n - 2]['green'].distance(h['tee'])
    rows.append({'hole': n, 'par': h['par'], 'yards': h['yards'], 'tee': [round(h['tee'].x, 1), round(h['tee'].y, 1)], 'green': [round(h['green'].x, 1), round(h['green'].y, 1)],
                 'tee_z_ft': round(zt, 1), 'green_z_ft': round(zg, 1), 'drop_ft': round(zt - zg, 1), 'trees_to_clear': nt, 'walk_from_prev_ft': round(walk),
                 'acres': round(h['poly'].area / AC, 2), 'drive_crossings': int(sum(1 for r in roads if r.intersects(LineString([(h['tee'].x, h['tee'].y), (h['green'].x, h['green'].y)]))))})
summary = {'generated': time.strftime('%Y-%m-%d'), 'crs': 'EPSG:2236 ftUS', 'parcels_assumed': parcels, 'estate_acres': round(estate.area / AC, 1),
           'free_acres': round(free.area / AC, 1), 'course_type': kind, 'holes_fitted': len(holes), 'par': sum(r['par'] for r in rows), 'yards': sum(r['yards'] for r in rows),
           'course_acres': round(course_u.area / AC, 1), 'trees_to_clear': len(cleared), 'clubhouse': [round(club_pt.x, 1), round(club_pt.y, 1)],
           'finish_to_clubhouse_ft': round(holes[-1]['green'].distance(club_pt)) if holes else None,
           'rules': {'edge_setback_ft': args.setback, 'building_buffer_ft': 100, 'water_buffer_ft': 30, 'drives': 'holes may cross internal drives (cart crossings counted)', 'programme_buffer_ft': 40,
                     'par3_corridor_ft': 2 * SPEC[3]['hw'], 'par4_corridor_ft': 2 * SPEC[4]['hw'], 'gap_between_holes_ft': 25},
           'holes': rows}
json.dump(summary, open(f'{OUT}/golf_course.json', 'w'), indent=1)

doc = ezdxf.new('R2018', setup=True); doc.units = 21; msp = doc.modelspace()   # units 21 = US survey feet
for name, col in (('L-GOLF-FWY', 3), ('L-GOLF-GRN', 82), ('L-GOLF-TEE', 1), ('L-GOLF-CL', 7), ('L-GOLF-ANNO', 2), ('L-GOLF-FREE', 8), ('G-ANNO-ESTATE', 6)):
    doc.layers.add(name, color=col)
def addpoly(g, layer):
    for p in getattr(g, 'geoms', [g]):
        if p.geom_type == 'Polygon': msp.add_lwpolyline(list(p.exterior.coords), close=True, dxfattribs={'layer': layer})
addpoly(estate, 'G-ANNO-ESTATE'); addpoly(free, 'L-GOLF-FREE')
for r, h in zip(rows, holes):
    addpoly(h['poly'], 'L-GOLF-FWY'); addpoly(h['green'].buffer(SPEC[h['par']]['green'] * 0.55), 'L-GOLF-GRN'); addpoly(h['tee'].buffer(14), 'L-GOLF-TEE')
    msp.add_line((h['tee'].x, h['tee'].y), (h['green'].x, h['green'].y), dxfattribs={'layer': 'L-GOLF-CL'})
    msp.add_text(f"{r['hole']}  PAR {r['par']}  {r['yards']} YD", dxfattribs={'layer': 'L-GOLF-ANNO', 'height': 14}).set_placement((h['tee'].x + 20, h['tee'].y + 20))
msp.add_mtext(f"FLORIDA FREEDOM WORLD - {kind.upper()} 18-HOLE COURSE CONCEPT ({summary['generated']})\\PPAR {summary['par']}, {summary['yards']} YD, {summary['course_acres']} AC OF PLAY CORRIDORS\\P"
              f"ESTATE ASSUMED = QUARTER-QUARTERS {'+'.join(parcels)} (PARCEL LINES NOT CONFIRMED). CONCEPT GRADE; NOT A SURVEY.",
              dxfattribs={'layer': 'L-GOLF-ANNO', 'char_height': 10, 'width': 900}).set_location((estate.bounds[0], estate.bounds[3] + 120))
doc.saveas(f'{OUT}/golf_course_EPSG2236_ftUS.dxf')

# plan image over the land-cover map
s = world['site']; img = Image.open(f'{B}/game/data/site_color.jpg').convert('RGB')
X0, Y0, X1, Y1 = s['x0'], s['y0'], s['x0'] + s['w'], s['y0'] + s['h']; SC = 3
img = img.resize((img.width * SC, img.height * SC), Image.LANCZOS); Wp, Hp = img.size
def P(x, y): return ((x - X0) / (X1 - X0) * Wp, (Y1 - y) / (Y1 - Y0) * Hp)
ov = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
def fill(g, rgba, outline=None, width=1):
    for p in getattr(g, 'geoms', [g]):
        if p.geom_type != 'Polygon': continue
        d.polygon([P(*c) for c in p.exterior.coords], fill=rgba, outline=outline, width=width)
fill(free, (255, 255, 255, 38), (255, 255, 255, 120), 2)
for k, g in prog.items():
    if k != KEEP_GOLF: fill(g, (230, 60, 200, 60), (230, 60, 200, 200), 2)
for h in holes:
    fill(h['poly'], (120, 220, 90, 150), (30, 90, 30, 255), 2); fill(h['green'].buffer(SPEC[h['par']]['green'] * 0.55), (60, 200, 60, 255), (20, 70, 20, 255), 2)
    fill(h['tee'].buffer(14), (250, 250, 240, 255), (40, 40, 40, 255), 2)
img = Image.alpha_composite(img.convert('RGBA'), ov); d = ImageDraw.Draw(img)
for p in getattr(estate, 'geoms', [estate]):
    d.line([P(*c) for c in p.exterior.coords], fill=(255, 220, 40, 255), width=4)
try: fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 26); fs = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 22)
except Exception: fnt = fs = ImageFont.load_default()
for n, h in enumerate(holes, 1):
    if n > 1:
        a, b = P(holes[n - 2]['green'].x, holes[n - 2]['green'].y), P(h['tee'].x, h['tee'].y); d.line([a, b], fill=(255, 255, 255, 220), width=2)
    x, y = P(h['tee'].x, h['tee'].y); d.ellipse([x - 17, y - 17, x + 17, y + 17], fill=(20, 60, 25, 255), outline=(255, 255, 255, 255), width=2)
    d.text((x, y), str(n), fill=(255, 255, 255, 255), font=fs, anchor='mm')
cx, cy = P(club_pt.x, club_pt.y); d.rectangle([cx - 16, cy - 12, cx + 16, cy + 12], fill=(255, 200, 40, 255), outline=(30, 30, 30, 255), width=2); d.text((cx + 22, cy), 'Clubhouse', fill=(255, 255, 255, 255), font=fs, anchor='lm')
bx0, by0 = P(estate.bounds[0] - 250, estate.bounds[3] + 250); bx1, by1 = P(estate.bounds[2] + 700, estate.bounds[1] - 250)
crop = img.crop((max(0, int(bx0)), max(0, int(by0)), min(Wp, int(bx1)), min(Hp, int(by1)))).convert('RGB')
pw = 560; panel = Image.new('RGB', (crop.width + pw, crop.height), (20, 26, 22)); panel.paste(crop, (0, 0)); dp = ImageDraw.Draw(panel); X = crop.width + 28
dp.text((X, 30), 'Gator Greens', fill=(255, 210, 60), font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 40) if fnt != ImageFont.load_default() else fnt)
dp.text((X, 86), f"{kind} 18 · par {summary['par']} · {summary['yards']:,} yd", fill=(235, 235, 225), font=fnt)
dp.text((X, 124), f"{summary['course_acres']} ac of holes in {summary['free_acres']} ac free", fill=(200, 205, 195), font=fs)
dp.text((X, 156), f"{summary['trees_to_clear']} lidar trees inside the holes", fill=(200, 205, 195), font=fs)
yy = 206; dp.text((X, yy), 'HOLE   PAR   YARDS   DROP ft', fill=(255, 210, 60), font=fs); yy += 34
for r in rows:
    dp.text((X, yy), f"{r['hole']:>3}     {r['par']}     {r['yards']:>4}     {r['drop_ft']:+5.1f}", fill=(235, 235, 225), font=fs); yy += 30
dp.text((X, yy + 10), f"TOTAL  {summary['par']}    {summary['yards']:,}", fill=(255, 210, 60), font=fnt)
dp.text((X, crop.height - 150), 'Yellow: estate assumed (3 quarter-quarters,\nparcel lines not confirmed). Pink: other\nplan areas. White wash: free land.\nConcept grade on the lidar base.', fill=(170, 175, 165), font=fs)
panel.save(f'{OUT}/golf_course_plan.jpg', quality=88)
print(json.dumps({k: v for k, v in summary.items() if k not in ('holes', 'rules')}, indent=1))
