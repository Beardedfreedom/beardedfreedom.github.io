#!/usr/bin/env python3
"""Gator Greens in 3D: hazards, grading and a 3D CAD model of the routed course (EPSG:2236 ftUS, NAVD88 ft).

Reads the routing from masterplan/golf/golf_course.json (scripts/golf_course.py) and adds:
* a shaped green, a tee box and greenside bunkers on every hole;
* forced carries: ponds that span the hole between tee and green on WATER_HOLES, and cross bunkers on
  SAND_HOLES (chosen so they stay clear of the drives and buildings);
* grading on the 3 ft lidar ground: greens raised 1.5 ft with a 1.5% back-to-front fall, tees raised
  1.5 ft and flat, bunkers dug 2.5 ft, ponds dug to 5 ft below a water level 1 ft under the lowest bank;
  cut and fill are tallied.

Outputs in masterplan/golf/:
* golf_course_3d_EPSG2236_ftUS.dxf: per-hole 3D meshes on separate layers (fairway, green, tee, bunker,
  pond bed, water surface), flags, and 2D outlines with elevations. XREF the site base DXF underneath.
* golf_hazards_plan.jpg (whole course) and golf_yardage_book.jpg (all 18 holes, tee at the bottom).
* golf_course.json updated with each hole's hazards, carries and earthwork.
Usage: python3 scripts/golf_3d.py [--step 4]
"""
import argparse, gzip, json, math, os
import numpy as np
import ezdxf
from ezdxf.render import MeshBuilder
from scipy.ndimage import gaussian_filter
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union
from shapely.prepared import prep
from shapely import affinity
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser(); ap.add_argument('--base', default=os.path.join(os.path.dirname(__file__), '..')); ap.add_argument('--step', type=float, default=4.0)
args = ap.parse_args(); B = os.path.abspath(args.base); G = f'{B}/masterplan/golf'
course = json.load(open(f'{G}/golf_course.json')); holes = course['holes']; club = course['clubhouse']
HW, SURROUND = 48.0, 55.0                       # corridor half-width and green surround used by the router (par 3)
WATER_HOLES = [3, 6, 9, 13, 17]                 # preferred forced carries over water
SAND_HOLES = [2, 5, 8, 11, 15]                  # preferred cross bunkers
YD = 3.0

# ---------------------------------------------------------------- context: drives and buildings to keep hazards away from
base = ezdxf.readfile(f'{B}/sausage_castle_base_EPSG2236_ftUS.dxf').modelspace()
roads = unary_union([LineString([(p[0], p[1]) for p in e.get_points()]) for e in base.query('LWPOLYLINE[layer=="C-ROAD-CNTR"]') if len(list(e.get_points())) > 1])
bldgs = unary_union([Polygon([(p[0], p[1]) for p in e.get_points()]).buffer(0) for e in base.query('LWPOLYLINE[layer=="A-BLDG-FTPT"]')])
avoid = unary_union([roads.buffer(22), bldgs.buffer(60)])

with gzip.open(f'{B}/sausage_castle_dtm_3ft_EPSG2236.asc.gz', 'rt') as f:
    hdr = {}
    for _ in range(6):
        k, v = f.readline().split(); hdr[k.lower()] = float(v)
    dtm = np.loadtxt(f, dtype=np.float32)
dtm = np.where(dtm < -9000, np.nan, dtm); dtm = np.where(np.isnan(dtm), np.nanmedian(dtm), dtm)
smooth = gaussian_filter(dtm, 2.0)
CS, XL, YL, NR = hdr['cellsize'], hdr['xllcorner'], hdr['yllcorner'], int(hdr['nrows'])
def zs(x, y, arr=smooth):   # bilinear sample (state plane ft)
    fi = (x - XL) / CS - 0.5; fj = (NR - 1) - ((y - YL) / CS - 0.5)
    i0 = int(np.clip(np.floor(fi), 0, arr.shape[1] - 2)); j0 = int(np.clip(np.floor(fj), 0, arr.shape[0] - 2)); ti = float(np.clip(fi - i0, 0, 1)); tj = float(np.clip(fj - j0, 0, 1))
    return float(arr[j0, i0] * (1 - ti) * (1 - tj) + arr[j0, i0 + 1] * ti * (1 - tj) + arr[j0 + 1, i0] * (1 - ti) * tj + arr[j0 + 1, i0 + 1] * ti * tj)

# ---------------------------------------------------------------- shapes
def blob(cx, cy, rx, ry, ang, wob=0.12, seed=0, n=48):
    """organic closed shape: an ellipse with a soft wobble, rotated to ang (radians)"""
    rng = np.random.default_rng(seed); ph = rng.uniform(0, 2 * np.pi, 3); amp = wob * np.array([1.0, 0.6, 0.35])
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    r = 1 + amp[0] * np.sin(2 * t + ph[0]) + amp[1] * np.sin(3 * t + ph[1]) + amp[2] * np.sin(5 * t + ph[2])
    px, py = rx * r * np.cos(t), ry * r * np.sin(t); ca, sa = math.cos(ang), math.sin(ang)
    return Polygon(list(zip(cx + px * ca - py * sa, cy + px * sa + py * ca))).buffer(0)

def frame(h):
    tx, ty = h['tee']; gx, gy = h['green']; L = math.hypot(gx - tx, gy - ty); ux, uy = (gx - tx) / L, (gy - ty) / L
    return tx, ty, gx, gy, L, ux, uy, -uy, ux

plan = []
for h in holes:
    n = h['hole']; tx, ty, gx, gy, L, ux, uy, nx_, ny_ = frame(h); ang = math.atan2(uy, ux)
    corridor = unary_union([LineString([(tx, ty), (gx, gy)]).buffer(HW, cap_style=2), Point(gx, gy).buffer(SURROUND), Point(tx, ty).buffer(28)])
    green = blob(gx, gy, 36, 28, ang, 0.08, seed=n)                                  # about 3,200 sq ft
    tee = affinity.rotate(box(tx - 16, ty - 11, tx + 16, ty + 11), ang, origin=(tx, ty), use_radians=True)
    bunkers = []
    sides = [(150, 1), (215, 2)] if n % 2 else [(140, 1), (205, 2), (290, 3)]      # angles from the line of play (0 = behind the green)
    for a_deg, k in sides:
        a = ang + math.radians(a_deg); d = 36 + 15
        bx_, by_ = gx + d * math.cos(a), gy + d * math.sin(a)
        bunkers.append(blob(bx_, by_, 17, 8.5, a + math.pi / 2, 0.18, seed=n * 10 + k))
    hz = {'hole': n, 'corridor': corridor, 'green': green, 'tee': tee, 'bunkers': bunkers, 'pond': None, 'cross': None, 'L': L, 'ang': ang}
    plan.append(hz)

def carry_pond(hz, h, frac=0.45):
    tx, ty, gx, gy, L, ux, uy, nx_, ny_ = frame(h); along = min(max(L * 0.22, 40), 120) * 0.5 + 10
    for f in (frac, 0.40, 0.52, 0.35):
        cx, cy = tx + ux * L * f, ty + uy * L * f
        p = blob(cx, cy, along, HW - 6, hz['ang'], 0.08, seed=h['hole'] * 7)
        if p.intersects(avoid) or p.distance(hz['green']) < 45 or p.distance(hz['tee']) < 50: continue
        return p
    return None

def cross_bunker(hz, h, frac=0.55):
    tx, ty, gx, gy, L, ux, uy, nx_, ny_ = frame(h)
    for f in (frac, 0.48, 0.62):
        cx, cy = tx + ux * L * f, ty + uy * L * f
        p = blob(cx, cy, 12, HW * 0.82, hz['ang'], 0.16, seed=h['hole'] * 11)
        if p.intersects(avoid) or p.distance(hz['green']) < 40 or p.distance(hz['tee']) < 50: continue
        return p
    return None

used_w, used_s = [], []
for pref, kind in ((WATER_HOLES, 'pond'), (SAND_HOLES, 'cross')):
    order = pref + [h['hole'] for h in holes if h['hole'] not in WATER_HOLES + SAND_HOLES]
    want = len(pref)
    for n in order:
        if len(used_w if kind == 'pond' else used_s) >= want: break
        hz = plan[n - 1]; h = holes[n - 1]
        if hz['pond'] is not None or hz['cross'] is not None: continue
        p = carry_pond(hz, h) if kind == 'pond' else cross_bunker(hz, h)
        if p is None: continue
        hz[kind] = p; (used_w if kind == 'pond' else used_s).append(n)
print('water carries on holes', used_w, '| sand carries on holes', used_s)

# ---------------------------------------------------------------- grading
step = args.step
def graded_z(x, y, hz, ctx):
    z0 = zs(x, y); z = z0; p = Point(x, y)
    g = hz['green']; gc = ctx['gz']
    dg = g.exterior.distance(p) if not g.contains(p) else 0.0
    w = 1.0 if g.contains(p) else max(0.0, 1 - dg / 18.0)
    if w > 0:
        tx, ty = ctx['tee_xy']; gx, gy = ctx['green_xy']; L = ctx['L']
        along = ((x - gx) * (gx - tx) + (y - gy) * (gy - ty)) / L        # >0 behind the green centre
        zg = gc + 1.5 + 0.015 * along                                      # back-to-front fall
        z = z * (1 - w) + zg * w * 1.0 if w < 1 else zg
    t = hz['tee']; dt = t.exterior.distance(p) if not t.contains(p) else 0.0
    wt = 1.0 if t.contains(p) else max(0.0, 1 - dt / 14.0)
    if wt > 0: z = z * (1 - wt) + (ctx['tz'] + 1.5) * wt
    for b in hz['bunkers'] + ([hz['cross']] if hz['cross'] is not None else []):
        if b.contains(p):
            d = b.exterior.distance(p); z -= 2.5 * min(1.0, d / 5.0)
    if hz['pond'] is not None and hz['pond'].contains(p):
        d = hz['pond'].exterior.distance(p); z = min(z, ctx['wl'] + 0.5 - d / 4.0) ; z = max(z, ctx['wl'] - 5.0)
    edge = hz['corridor'].exterior.distance(p) if hz['corridor'].contains(p) else 0.0     # tie into the existing ground at the edge
    wb = min(1.0, edge / 12.0); zr = zs(x, y, dtm)
    return zr + (z - zr) * wb

LAYERS = {'FWY': ('L-GOLF-FWY-3D', 0x5f9a3c), 'GRN': ('L-GOLF-GRN-3D', 0x36b84a), 'TEE': ('L-GOLF-TEE-3D', 0x8fd16a),
          'BNKR': ('L-GOLF-BNKR-3D', 0xe8d49c), 'BED': ('L-GOLF-POND-BED-3D', 0x6b5a3a), 'WATR': ('L-GOLF-WATR-3D', 0x2b6f9a)}
doc = ezdxf.new('R2018', setup=True); doc.header['$INSUNITS'] = 21; msp = doc.modelspace()
for ln, col in list(LAYERS.values()) + [('L-GOLF-FLAG', 0xe0262b), ('L-GOLF-GRN', 0x36b84a), ('L-GOLF-TEE', 0x8fd16a), ('L-GOLF-BNKR', 0xd8c088),
                                       ('L-GOLF-WATR', 0x2b6f9a), ('L-GOLF-CL', 0xffffff), ('L-GOLF-ANNO', 0xffd23c)]:
    doc.layers.add(ln, true_color=col)
cut = fill = 0.0; rows = []
for hz, h in zip(plan, holes):
    n = h['hole']; tx, ty, gx, gy, L, ux, uy, nx_, ny_ = frame(h)
    gz = np.mean([zs(*c) for c in list(hz['green'].exterior.coords)[::4]]); tz = max(zs(*c) for c in hz['tee'].exterior.coords)
    wl = (min(zs(*c) for c in hz['pond'].exterior.coords) - 1.0) if hz['pond'] is not None else None
    ctx = {'gz': gz, 'tz': tz, 'wl': wl, 'tee_xy': (tx, ty), 'green_xy': (gx, gy), 'L': L}
    minx, miny, maxx, maxy = hz['corridor'].bounds
    xs = np.arange(math.floor(minx / step) * step, maxx + step, step); ys = np.arange(math.floor(miny / step) * step, maxy + step, step)
    pc = prep(hz['corridor']); pg = prep(hz['green']); pt = prep(hz['tee']); pp = prep(hz['pond']) if hz['pond'] is not None else None
    pb = [prep(b) for b in hz['bunkers'] + ([hz['cross']] if hz['cross'] is not None else [])]
    zcache = {}
    def vz(i, j):
        if (i, j) not in zcache: zcache[(i, j)] = graded_z(xs[i], ys[j], hz, ctx)
        return zcache[(i, j)]
    meshes = {k: (MeshBuilder(), {}) for k in LAYERS}
    hole_cut = hole_fill = 0.0
    for j in range(len(ys) - 1):
        for i in range(len(xs) - 1):
            cx, cy = xs[i] + step / 2, ys[j] + step / 2; P = Point(cx, cy)
            if not pc.contains(P): continue
            if pp is not None and pp.contains(P): kind = 'BED'
            elif any(b.contains(P) for b in pb): kind = 'BNKR'
            elif pg.contains(P): kind = 'GRN'
            elif pt.contains(P): kind = 'TEE'
            else: kind = 'FWY'
            mb, idx = meshes[kind]; face = []
            for (a, b_) in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)):
                if (a, b_) not in idx: idx[(a, b_)] = len(mb.vertices); mb.vertices.append((float(xs[a]), float(ys[b_]), round(vz(a, b_), 2)))
                face.append(idx[(a, b_)])
            mb.faces.append(tuple(face))
            dz = graded_z(cx, cy, hz, ctx) - zs(cx, cy)
            if dz < 0: hole_cut -= dz * step * step
            else: hole_fill += dz * step * step
            if kind == 'BED':   # water surface over the pond bed
                wm, widx = meshes['WATR']; wf = []
                for (a, b_) in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)):
                    if (a, b_) not in widx: widx[(a, b_)] = len(wm.vertices); wm.vertices.append((float(xs[a]), float(ys[b_]), round(wl, 2)))
                    wf.append(widx[(a, b_)])
                wm.faces.append(tuple(wf))
    for k, (mb, idx) in meshes.items():
        if mb.faces: mb.render_mesh(msp, dxfattribs={'layer': LAYERS[k][0]})
    cut += hole_cut; fill += hole_fill
    # flag, outlines, labels
    zg = graded_z(gx, gy, hz, ctx)
    msp.add_line((gx, gy, zg), (gx, gy, zg + 8.0), dxfattribs={'layer': 'L-GOLF-FLAG'})
    msp.add_3dface([(gx, gy, zg + 8.0), (gx + 3.2 * ux, gy + 3.2 * uy, zg + 7.0), (gx, gy, zg + 6.0)], dxfattribs={'layer': 'L-GOLF-FLAG'})
    for poly, ln, z in [(hz['green'], 'L-GOLF-GRN', gz + 1.5), (hz['tee'], 'L-GOLF-TEE', tz + 1.5)] + [(b, 'L-GOLF-BNKR', None) for b in hz['bunkers'] + ([hz['cross']] if hz['cross'] is not None else [])] + ([(hz['pond'], 'L-GOLF-WATR', wl)] if wl is not None else []):
        zz = z if z is not None else min(zs(*c) for c in poly.exterior.coords)
        msp.add_lwpolyline(list(poly.exterior.coords), close=True, dxfattribs={'layer': ln, 'elevation': round(zz, 2)})
    msp.add_line((tx, ty, tz + 1.5), (gx, gy, zg), dxfattribs={'layer': 'L-GOLF-CL'})
    msp.add_text(f"HOLE {n}  PAR 3  {h['yards']} YD", dxfattribs={'layer': 'L-GOLF-ANNO', 'height': 10}).set_placement((tx + 24, ty - 24, tz + 2))
    carry = None
    if hz['pond'] is not None or hz['cross'] is not None:
        hazard = hz['pond'] if hz['pond'] is not None else hz['cross']
        cl = LineString([(tx, ty), (gx, gy)]); seg = cl.intersection(hazard)
        far = max(Point(tx, ty).distance(Point(c)) for c in (seg.coords if seg.geom_type == 'LineString' else [q for g_ in seg.geoms for q in g_.coords]))
        carry = round(far / YD)
    rows.append({'hole': n, 'water_carry': hz['pond'] is not None, 'sand_carry': hz['cross'] is not None, 'carry_yd': carry,
                 'greenside_bunkers': len(hz['bunkers']), 'water_level_ft': round(wl, 1) if wl is not None else None,
                 'pond_acres': round(hz['pond'].area / 43560, 3) if hz['pond'] is not None else None, 'green_sf': round(hz['green'].area),
                 'bunker_sf': round(sum(b.area for b in hz['bunkers'] + ([hz['cross']] if hz['cross'] is not None else []))),
                 'cut_cy': round(hole_cut / 27), 'fill_cy': round(hole_fill / 27),
                 'green_poly': [[round(x, 1), round(y, 1)] for x, y in list(hz['green'].exterior.coords)[:-1]],
                 'tee_poly': [[round(x, 1), round(y, 1)] for x, y in list(hz['tee'].exterior.coords)[:-1]],
                 'bunker_polys': [[[round(x, 1), round(y, 1)] for x, y in list(b.exterior.coords)[:-1]] for b in hz['bunkers'] + ([hz['cross']] if hz['cross'] is not None else [])],
                 'pond_poly': [[round(x, 1), round(y, 1)] for x, y in list(hz['pond'].exterior.coords)[:-1]] if hz['pond'] is not None else None,
                 'green_z_ft': round(gz + 1.5, 2), 'tee_z_ft': round(tz + 1.5, 2)})
    print(f"hole {n:2d}: {'water' if hz['pond'] is not None else ('sand ' if hz['cross'] is not None else '     ')} carry {carry or '-':>4} yd | cut {hole_cut / 27:5.0f} cy fill {hole_fill / 27:5.0f} cy | {sum(len(m.faces) for m, _ in meshes.values())} faces")
msp.add_mtext(f"GATOR GREENS 3D: 18-HOLE PAR-3 COURSE, GRADED ON THE 2018 LIDAR GROUND\\PWATER CARRIES ON HOLES {', '.join(map(str, used_w))}; SAND CARRIES ON HOLES {', '.join(map(str, used_s))}\\P"
              f"CUT {cut / 27:,.0f} CY, FILL {fill / 27:,.0f} CY (PONDS AND BUNKERS SUPPLY THE GREENS AND TEES). CONCEPT GRADE. XREF THE SITE BASE DXF UNDERNEATH.",
              dxfattribs={'layer': 'L-GOLF-ANNO', 'char_height': 10, 'width': 900}).set_location((min(p['corridor'].bounds[0] for p in plan), max(p['corridor'].bounds[3] for p in plan) + 120, 90))
doc.saveas(f'{G}/golf_course_3d_EPSG2236_ftUS.dxf'); print('DXF', os.path.getsize(f'{G}/golf_course_3d_EPSG2236_ftUS.dxf') // 1024, 'KB')
for r, h in zip(rows, holes): h.update({k: v for k, v in r.items() if k != 'hole'})
course['hazards'] = {'water_carry_holes': used_w, 'sand_carry_holes': used_s, 'greenside_bunkers': sum(len(p['bunkers']) for p in plan),
                     'ponds_acres': round(sum(p['pond'].area for p in plan if p['pond'] is not None) / 43560, 2), 'cut_cy': round(cut / 27), 'fill_cy': round(fill / 27)}
json.dump(course, open(f'{G}/golf_course.json', 'w'), indent=1)
print(json.dumps(course['hazards']))

# ---------------------------------------------------------------- hazards plan and yardage book
try:
    FB = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 24); FR = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
    FT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 40)
except Exception:
    FB = FR = FT = ImageFont.load_default()
world = json.load(open(f'{B}/game/data/world.json')); s = world['site']
base_img = Image.open(f'{B}/game/data/site_color.jpg').convert('RGB'); X0, Y0, X1, Y1 = s['x0'], s['y0'], s['x0'] + s['w'], s['y0'] + s['h']
SC = 4; big = base_img.resize((base_img.width * SC, base_img.height * SC), Image.LANCZOS)
def P(x, y): return ((x - X0) / (X1 - X0) * big.width, (Y1 - y) / (Y1 - Y0) * big.height)
ov = Image.new('RGBA', big.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
def poly(g, fill_, out=None, w=1):
    d.polygon([P(*c) for c in g.exterior.coords], fill=fill_, outline=out, width=w)
for hz in plan:
    poly(hz['corridor'], (110, 190, 80, 190), (40, 90, 30, 255), 2)
for hz in plan:
    poly(hz['green'], (60, 205, 75, 255), (20, 80, 20, 255), 2); poly(hz['tee'], (190, 235, 160, 255), (40, 70, 30, 255), 2)
    for b in hz['bunkers'] + ([hz['cross']] if hz['cross'] is not None else []): poly(b, (238, 220, 165, 255), (150, 120, 70, 255), 2)
    if hz['pond'] is not None: poly(hz['pond'], (43, 111, 154, 255), (20, 60, 90, 255), 2)
img = Image.alpha_composite(big.convert('RGBA'), ov); d2 = ImageDraw.Draw(img)
for hz, h in zip(plan, holes):
    x, y = P(*h['tee']); d2.ellipse([x - 16, y - 16, x + 16, y + 16], fill=(20, 60, 25, 255), outline=(255, 255, 255, 255), width=2); d2.text((x, y), str(h['hole']), fill='white', font=FR, anchor='mm')
    gx_, gy_ = P(*h['green']); d2.line([gx_, gy_, gx_, gy_ - 26], fill=(255, 255, 255, 255), width=2); d2.polygon([(gx_, gy_ - 26), (gx_ + 14, gy_ - 21), (gx_, gy_ - 16)], fill=(224, 38, 43, 255))
cx, cy = P(*club); d2.rectangle([cx - 14, cy - 10, cx + 14, cy + 10], fill=(255, 200, 40, 255), outline=(30, 30, 30, 255), width=2); d2.text((cx + 20, cy), 'Clubhouse (the Castle)', fill='white', font=FR, anchor='lm')
allb = unary_union([p['corridor'] for p in plan]).bounds; pad = 160
crop = img.crop((int(P(allb[0] - pad, allb[3] + pad)[0]), int(P(allb[0] - pad, allb[3] + pad)[1]), int(P(allb[2] + pad, allb[1] - pad)[0]), int(P(allb[2] + pad, allb[1] - pad)[1]))).convert('RGB')
pw = 520; out = Image.new('RGB', (crop.width + pw, max(crop.height, 900)), (20, 26, 22)); out.paste(crop, (0, 0)); dd = ImageDraw.Draw(out); X = crop.width + 26
dd.text((X, 26), 'Gator Greens', fill=(255, 210, 60), font=FT); dd.text((X, 80), f"18 holes · par 54 · {course['yards']:,} yd", fill=(235, 235, 225), font=FB)
dd.text((X, 118), f"water carries: holes {', '.join(map(str, used_w))}", fill=(120, 190, 235), font=FR)
dd.text((X, 146), f"sand carries: holes {', '.join(map(str, used_s))}", fill=(238, 220, 165), font=FR)
dd.text((X, 174), f"{course['hazards']['greenside_bunkers']} greenside bunkers · {course['hazards']['ponds_acres']} ac of ponds", fill=(210, 210, 200), font=FR)
dd.text((X, 202), f"cut {course['hazards']['cut_cy']:,} cy · fill {course['hazards']['fill_cy']:,} cy", fill=(210, 210, 200), font=FR)
yy = 250; dd.text((X, yy), 'HOLE  YDS  HAZARD       CARRY', fill=(255, 210, 60), font=FR); yy += 30
for h in holes:
    hzd = 'water' if h['water_carry'] else ('sand' if h['sand_carry'] else 'bunkers')
    dd.text((X, yy), f"{h['hole']:>3}   {h['yards']:>4}  {hzd:<10}  {str(h['carry_yd']) + ' yd' if h['carry_yd'] else ''}", fill=(235, 235, 225), font=FR); yy += 27
out.save(f'{G}/golf_hazards_plan.jpg', quality=88); print('plan', out.size)

# yardage book: each hole rotated so the tee is at the bottom
cw, ch = 300, 520; book = Image.new('RGB', (cw * 6 + 40, ch * 3 + 120), (245, 241, 230)); db = ImageDraw.Draw(book)
db.text((20, 18), 'GATOR GREENS · YARDAGE BOOK', fill=(30, 60, 30), font=FT); db.text((20, 70), 'tee at the bottom, green at the top · distances in yards from the tee · concept grade', fill=(80, 80, 70), font=FR)
for k, (hz, h) in enumerate(zip(plan, holes)):
    ox, oy = 20 + (k % 6) * cw, 110 + (k // 6) * ch; tx, ty, gx, gy, L, ux, uy, nx_, ny_ = frame(h)
    scale = (ch - 110) / (L + 140)
    def Q(x, y):
        a = (x - tx) * ux + (y - ty) * uy; b = (x - tx) * nx_ + (y - ty) * ny_      # along, across
        return (ox + cw / 2 - b * scale, oy + ch - 50 - (a + 40) * scale)
    def qp(g, f_, o=None, w=1): db.polygon([Q(*c) for c in g.exterior.coords], fill=f_, outline=o, width=w)
    db.rounded_rectangle([ox + 6, oy + 6, ox + cw - 6, oy + ch - 6], 14, fill=(232, 238, 220), outline=(170, 180, 150), width=2)
    qp(hz['corridor'], (120, 185, 90), (60, 110, 40), 2)
    if hz['pond'] is not None: qp(hz['pond'], (50, 120, 165), (25, 70, 100), 2)
    for b in hz['bunkers'] + ([hz['cross']] if hz['cross'] is not None else []): qp(b, (238, 220, 165), (150, 120, 70), 2)
    qp(hz['green'], (70, 200, 80), (20, 80, 20), 2); qp(hz['tee'], (200, 235, 170), (40, 70, 30), 2)
    fx, fy = Q(gx, gy); db.line([fx, fy, fx, fy - 22], fill=(40, 40, 40), width=2); db.polygon([(fx, fy - 22), (fx + 12, fy - 18), (fx, fy - 14)], fill=(224, 38, 43))
    for yd in (50, 100, 150):
        if yd * YD < L - 30:
            a = yd * YD; lx, ly = Q(tx + ux * a + nx_ * (HW + 4), ty + uy * a + ny_ * (HW + 4)); db.text((lx + 4, ly), str(yd), fill=(60, 60, 50), font=FR, anchor='lm')
    db.text((ox + 18, oy + 16), f"{h['hole']}", fill=(30, 60, 30), font=FT)
    db.text((ox + cw - 18, oy + 22), f"PAR 3 · {h['yards']} yd", fill=(30, 30, 30), font=FB, anchor='ra')
    note = f"carry {h['carry_yd']} yd over {'water' if h['water_carry'] else 'sand'}" if h['carry_yd'] else f"{h['greenside_bunkers']} greenside bunkers"
    db.text((ox + cw / 2, oy + ch - 26), note, fill=(60, 60, 50), font=FR, anchor='mm')
book.save(f'{G}/golf_yardage_book.jpg', quality=88); print('book', book.size)
