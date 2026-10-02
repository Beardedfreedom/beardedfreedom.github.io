#!/usr/bin/env python3
"""Gator Greens, polished for mock-up photos and video (EPSG:2236 ftUS, NAVD88 ft).

From the routing and hazards in masterplan/golf/golf_course.json this builds the finished-course design
and the surfaces a renderer needs:

* design: organic fairways (approach fairways on the par 3s, the cross bunkers sit in them), maintained
  rough with an irregular tree line, 5 ft collars around the greens, two tee boxes per hole (back and
  forward), an 8 ft cart path network (clubhouse to 1, green to next tee, 9 and 18 back to the Castle,
  10 out again), pond banks;
* grading on a 2 ft grid over the course and its surroundings: turf smoothed, greens raised 1.5 ft with a
  1.5% back-to-front fall, tee boxes flat and raised, bunkers dug 2.5 ft with a raised lip, ponds dug 5 ft
  below their water level with soft banks;
* a painted surface map at 0.5 ft per pixel: mown stripes on fairways, cross-hatched greens, collars,
  tees, rough, raked sand, wet banks, concrete paths, and natural ground (pine straw and native grass)
  outside the turf, over the lidar land-cover map for roads and clearings.

Outputs (masterplan/golf/polish/):
  terrain.npz             graded heights (2 ft grid) + extent      (render input, git-ignored)
  surface_0p5ft.jpg       surface map at 0.5 ft/px                 (render input, git-ignored)
  golf_course_map.jpg     the same map at 1 ft/px                  (committed)
  design.json             every design polygon and the cart paths  (committed)
  golf_course_design_EPSG2236_ftUS.dxf   2D design layers at their elevations (committed)
Usage: python3 scripts/golf_polish.py [--res 0.5] [--seed 7]
       python3 scripts/golf_polish.py --extent estate   # the whole estate for the estate views: writes
           polish_estate/ (terrain and surface, git-ignored) and estate_map.jpg; the course files are untouched
"""
import argparse, gzip, json, math, os
import numpy as np
from scipy.ndimage import gaussian_filter, distance_transform_edt, zoom
from shapely.geometry import Point, Polygon, LineString, MultiPolygon, box
from shapely.ops import unary_union
from shapely import affinity
from PIL import Image, ImageDraw
import ezdxf

ap = argparse.ArgumentParser(); ap.add_argument('--base', default=os.path.join(os.path.dirname(__file__), '..'))
ap.add_argument('--res', type=float, default=0.5, help='surface map resolution (ft/px)'); ap.add_argument('--grid', type=float, default=2.0, help='terrain grid (ft)')
ap.add_argument('--margin', type=float, default=320.0); ap.add_argument('--seed', type=int, default=7)
ap.add_argument('--extent', choices=('course', 'estate'), default='course', help='course: the course and its margin; estate: the whole assumed estate, with the lakes')
args = ap.parse_args(); ESTATE = args.extent == 'estate'
B = os.path.abspath(args.base); G = f'{B}/masterplan/golf'; OUT = f'{G}/polish_estate' if ESTATE else f'{G}/polish'; os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(args.seed)
course = json.load(open(f'{G}/golf_course.json')); H = course['holes']; club = tuple(course['clubhouse'])

def P(pts): return Polygon(pts).buffer(0)
def frame(h):
    tx, ty = h['tee']; gx, gy = h['green']; L = math.hypot(gx - tx, gy - ty); ux, uy = (gx - tx) / L, (gy - ty) / L
    return tx, ty, gx, gy, L, ux, uy, -uy, ux
def smooth(g, r=6): return g.buffer(r, join_style='round').buffer(-2 * r, join_style='round').buffer(r, join_style='round')

# ------------------------------------------------------------------ design per hole
holes = []
for h in H:
    n = h['hole']; tx, ty, gx, gy, L, ux, uy, nx, ny = frame(h); ang = math.atan2(uy, ux)
    green = P(h['green_poly']); collar = green.buffer(5).difference(green)
    bunkers = [P(b) for b in h['bunker_polys']]; pond = P(h['pond_poly']) if h.get('pond_poly') else None
    corridor = unary_union([LineString([(tx, ty), (gx, gy)]).buffer(48, cap_style=2), Point(gx, gy).buffer(55), Point(tx, ty).buffer(28)])
    back = P(h['tee_poly']).buffer(-3).buffer(3)
    fwd_d = 40.0 if L > 400 else 30.0
    fx, fy = tx + ux * fwd_d, ty + uy * fwd_d
    fwd = affinity.rotate(box(fx - 11, fy - 8, fx + 11, fy + 8), ang, origin=(fx, fy), use_radians=True).buffer(-3).buffer(3)
    if pond is not None and fwd.buffer(10).intersects(pond): fwd = None
    tees = [t for t in (back, fwd) if t is not None]
    # approach fairway: from past the hazard (or ~1/3 of the way) to the front of the green, organic width
    if pond is not None:
        far = max(((x - tx) * ux + (y - ty) * uy) for x, y in pond.exterior.coords) + 14
        s0 = min(far, L - 70)
    else:
        s0 = L * (0.30 if L > 400 else 0.40)
    s1 = L - 18; pts = []
    for k, s in enumerate(np.arange(s0, s1 + 1, 8.0)):
        t = (s - s0) / max(s1 - s0, 1)
        w = (26 + 12 * t) * (1 + 0.10 * math.sin(n * 1.7 + s / 37.0) + 0.06 * math.sin(n * 0.9 + s / 13.0))
        off = 6 * math.sin(n * 2.3 + s / 61.0)
        pts.append(Point(tx + ux * s + nx * off, ty + uy * s + ny * off).buffer(w))
    fairway = smooth(unary_union(pts), 5).difference(green.buffer(5)) if pts else Polygon()
    if pond is not None: fairway = fairway.difference(pond.buffer(8))
    # maintained rough: the cleared corridor with an irregular tree line and a few tree islands
    edge = []
    for k in range(18):
        s = rng.uniform(0, L); side = rng.choice([-1, 1]); r = rng.uniform(8, 18)
        edge.append(Point(tx + ux * s + nx * side * (48 + rng.uniform(-4, 6)), ty + uy * s + ny * side * (48 + rng.uniform(-4, 6))).buffer(r))
    rough = smooth(unary_union([corridor.buffer(-2)] + edge[:9]).difference(unary_union(edge[9:13])), 4)
    rough = unary_union([rough, fairway.buffer(14), green.buffer(24)] + [t.buffer(12) for t in tees])
    bank = pond.buffer(4).difference(pond) if pond is not None else None
    holes.append({'n': n, 'h': h, 'frame': (tx, ty, gx, gy, L, ux, uy, nx, ny), 'green': green, 'collar': collar, 'bunkers': bunkers, 'pond': pond, 'bank': bank,
                  'tees': tees, 'fairway': fairway, 'rough': rough, 'corridor': corridor})

# ------------------------------------------------------------------ cart paths
def bezier(a, b, bow, n=24):
    ax, ay = a; bx, by = b; mx, my = (ax + bx) / 2, (ay + by) / 2; L = math.hypot(bx - ax, by - ay) or 1
    cx, cy = mx + (-(by - ay) / L) * bow, my + ((bx - ax) / L) * bow
    return [((1 - t) ** 2 * ax + 2 * (1 - t) * t * cx + t * t * bx, (1 - t) ** 2 * ay + 2 * (1 - t) * t * cy + t * t * by) for t in np.linspace(0, 1, n)]
keep_off = unary_union([x['green'].buffer(14) for x in holes] + [b.buffer(6) for x in holes for b in x['bunkers']] +
                       [x['pond'].buffer(10) for x in holes if x['pond'] is not None] + [t.buffer(4) for x in holes for t in x['tees']])
fw_soft = unary_union([x['fairway'].buffer(4) for x in holes])
def path_between(a, b):
    best = None
    for bow in (0, 30, -30, 60, -60, 100, -100, 150, -150, 210, -210):
        ln = LineString(bezier(a, b, bow)); cost = ln.intersection(keep_off).length * 5 + ln.intersection(fw_soft).length + ln.length * 0.02
        if best is None or cost < best[0] - 1e-6: best = (cost, ln)
    return best[1]
def green_exit(x, toward):
    tx, ty, gx, gy, L, ux, uy, nx, ny = x['frame']; dx, dy = toward[0] - gx, toward[1] - gy; side = 1 if dx * nx + dy * ny > 0 else -1
    return (gx + nx * side * 52 + ux * 10, gy + ny * side * 52 + uy * 10)
def tee_entry(x, frm):
    tx, ty, gx, gy, L, ux, uy, nx, ny = x['frame']; dx, dy = frm[0] - tx, frm[1] - ty; side = 1 if dx * nx + dy * ny > 0 else -1
    return (tx - ux * 22 + nx * side * 26, ty - uy * 22 + ny * side * 26)
paths = []
club_door = (club[0] + 60, club[1] - 70)
for k, x in enumerate(holes):                       # clubhouse to 1, green to next tee (9 to 10 direct: halfway hut at the turn), 18 back home
    if x['n'] == 1: paths.append(path_between(club_door, tee_entry(x, club_door)))
    if k + 1 < len(holes):
        nxt = holes[k + 1]; a = green_exit(x, nxt['h']['tee']); paths.append(path_between(a, tee_entry(nxt, a)))
    if x['n'] == 18: paths.append(path_between(green_exit(x, club_door), club_door))
path_poly = unary_union([p.buffer(4, cap_style=1) for p in paths])
print(f'cart paths: {len(paths)} runs, {sum(p.length for p in paths):,.0f} ft')

turf = unary_union([x['rough'] for x in holes])
fairways = unary_union([x['fairway'] for x in holes]); greens = unary_union([x['green'] for x in holes]); collars = unary_union([x['collar'] for x in holes])
tees_u = unary_union([t for x in holes for t in x['tees']]); bunkers_u = unary_union([b for x in holes for b in x['bunkers']])
ponds_u = unary_union([x['pond'] for x in holes if x['pond'] is not None]); banks_u = unary_union([x['bank'] for x in holes if x['bank'] is not None])

# ------------------------------------------------------------------ extent, lidar ground
mx0, my0, mx1, my1 = unary_union([turf, path_poly]).bounds; M_ = args.margin
_w = json.load(open(f'{B}/game/data/world.json')); _s = _w['site']
E_BRK, N_BRK, QQ = 427050.0, 1578500.0, 1320.0                                              # the quarter-quarters scripts/golf_course.py assumes
QQS = {'SW': box(E_BRK - QQ, N_BRK - QQ, E_BRK, N_BRK), 'NW': box(E_BRK - QQ, N_BRK, E_BRK, N_BRK + QQ), 'NE': box(E_BRK, N_BRK, E_BRK + QQ, N_BRK + QQ), 'SE': box(E_BRK, N_BRK - QQ, E_BRK + QQ, N_BRK)}
estate = unary_union([QQS[k] for k in course.get('parcels_assumed', ['SW', 'NW', 'SE'])])
lakes = []
if ESTATE:
    ex0, ey0, ex1, ey1 = estate.buffer(200).bounds; mx0, my0, mx1, my1 = min(mx0, ex0 + M_), min(my0, ey0 + M_), max(mx1, ex1 - M_), max(my1, ey1 - M_)
    for w_ in _w['water']:                                                                  # existing lakes (the course ponds are drawn per hole)
        lp = Polygon(list(zip(w_['pts'][0::2], w_['pts'][1::2]))).buffer(0)
        if not lp.intersects(unary_union([x['pond'] for x in holes if x['pond'] is not None])): lakes.append((lp, float(w_['wse'])))
X0, Y0 = max(math.floor((mx0 - M_) / 10) * 10, _s['x0'] + 40), max(math.floor((my0 - M_) / 10) * 10, _s['y0'] + 40)
X1, Y1 = min(math.ceil((mx1 + M_) / 10) * 10, _s['x0'] + _s['w'] - 40), min(math.ceil((my1 + M_) / 10) * 10, _s['y0'] + _s['h'] - 40)
with gzip.open(f'{B}/sausage_castle_dtm_3ft_EPSG2236.asc.gz', 'rt') as f:
    hdr = {}
    for _ in range(6):
        k, v = f.readline().split(); hdr[k.lower()] = float(v)
    dtm = np.loadtxt(f, dtype=np.float32)
dtm = np.where(dtm < -9000, np.nan, dtm); dtm = np.where(np.isnan(dtm), np.nanmedian(dtm), dtm)
def sample(arr, X, Y):
    fi = (X - hdr['xllcorner']) / hdr['cellsize'] - 0.5; fj = (hdr['nrows'] - 1) - ((Y - hdr['yllcorner']) / hdr['cellsize'] - 0.5)
    i0 = np.clip(np.floor(fi), 0, arr.shape[1] - 2).astype(int); j0 = np.clip(np.floor(fj), 0, arr.shape[0] - 2).astype(int); ti = np.clip(fi - i0, 0, 1); tj = np.clip(fj - j0, 0, 1)
    return arr[j0, i0] * (1 - ti) * (1 - tj) + arr[j0, i0 + 1] * ti * (1 - tj) + arr[j0 + 1, i0] * (1 - ti) * tj + arr[j0 + 1, i0 + 1] * ti * tj

# ------------------------------------------------------------------ grading on the terrain grid (row 0 = south)
g = args.grid; gx_ = np.arange(X0, X1 + g / 2, g); gy_ = np.arange(Y0, Y1 + g / 2, g); GX, GY = np.meshgrid(gx_, gy_)
Z0 = sample(dtm, GX, GY).astype(np.float64); Zs = gaussian_filter(Z0, 3.0); nyg, nxg = Z0.shape
def gmask(geom, scale=1):
    """rasterise a polygon onto the terrain grid (True inside); row 0 = south"""
    im = Image.new('L', (nxg * scale, nyg * scale), 0); d = ImageDraw.Draw(im)
    for p in getattr(geom, 'geoms', [geom]):
        if p.is_empty or p.geom_type != 'Polygon': continue
        d.polygon([((x - X0) / g * scale + 0.5 * scale, (y - Y0) / g * scale + 0.5 * scale) for x, y in p.exterior.coords], fill=255)
        for r in p.interiors: d.polygon([((x - X0) / g * scale + 0.5 * scale, (y - Y0) / g * scale + 0.5 * scale) for x, y in r.coords], fill=0)
    a = np.asarray(im, dtype=np.float32) / 255.0
    return a if scale == 1 else a.reshape(nyg, scale, nxg, scale).mean(axis=(1, 3))
def ss(t): t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)
T = gmask(turf); Tsoft = ss(1 - distance_transform_edt(T < 0.5) * g / 14.0)            # 0 outside, 1 inside, 14 ft blend
Z = Z0 * (1 - Tsoft) + Zs * Tsoft                                                         # mown turf reads smooth; natural ground keeps its texture
for x in holes:
    h = x['h']; tx, ty, gx, gy, L, ux, uy, nx, ny = x['frame']
    m = gmask(x['green']); d_out = distance_transform_edt(m < 0.5) * g; w = ss(1 - d_out / 16.0)
    zc = float(np.mean(sample(dtm, np.array([c[0] for c in x['green'].exterior.coords]), np.array([c[1] for c in x['green'].exterior.coords]))))
    along = (GX - gx) * ux + (GY - gy) * uy; Zg = zc + 1.5 + 0.015 * along
    Z = Z * (1 - w) + Zg * w
    for t in x['tees']:
        m = gmask(t); d_out = distance_transform_edt(m < 0.5) * g; w = ss(1 - d_out / 9.0)
        zt = float(np.max(sample(dtm, np.array([c[0] for c in t.exterior.coords]), np.array([c[1] for c in t.exterior.coords])))) + 1.2
        Z = Z * (1 - w) + zt * w
    for b in x['bunkers']:
        m = gmask(b); d_in = distance_transform_edt(m > 0.5) * g; d_out = distance_transform_edt(m < 0.5) * g
        Z = Z - 2.5 * ss(d_in / 5.0) * (m > 0.5) + 0.6 * np.exp(-((d_out - 1.5) / 1.6) ** 2) * (m < 0.5) * (d_out < 5)
    if x['pond'] is not None:
        m = gmask(x['pond']); d_in = distance_transform_edt(m > 0.5) * g; d_out = distance_transform_edt(m < 0.5) * g; wl = h['water_level_ft']
        bed = np.maximum(wl + 0.4 - d_in / 4.0, wl - 5.0)
        Z = np.where(m > 0.5, np.minimum(Z, bed), Z)
        bankw = ss(1 - d_out / 12.0) * (m < 0.5); Z = Z * (1 - bankw) + np.minimum(Z, wl + 0.5 + d_out / 12.0 * 1.5) * bankw
for lp, wl in lakes:                                                                        # existing lakes: the lidar ground sits at the water, so give them a bed
    m = gmask(lp); d_in = distance_transform_edt(m > 0.5) * g
    Z = np.where(m > 0.5, np.minimum(Z, np.maximum(wl + 0.3 - d_in / 5.0, wl - 6.0)), Z)
cut = float(np.sum(np.clip(Z0 - Z, 0, None)) * g * g / 27); fill = float(np.sum(np.clip(Z - Z0, 0, None)) * g * g / 27)
np.savez_compressed(f'{OUT}/terrain.npz', Z=Z.astype(np.float32), X0=X0, Y0=Y0, X1=X1, Y1=Y1, grid=g, lakes=np.array(len(lakes)))
print(f'terrain {nxg} x {nyg} at {g} ft; cut {cut:,.0f} cy, fill {fill:,.0f} cy')

# ------------------------------------------------------------------ painted surface map (row 0 = north)
R = args.res; W_, H_ = int(round((X1 - X0) / R)), int(round((Y1 - Y0) / R))
px = X0 + (np.arange(W_) + 0.5) * R; py = Y1 - (np.arange(H_) + 0.5) * R; PX, PY = np.meshgrid(px, py)
def tmask(geom, feather=0.6):
    im = Image.new('L', (W_ * 2, H_ * 2), 0); d = ImageDraw.Draw(im)
    for p in getattr(geom, 'geoms', [geom]):
        if p.is_empty or p.geom_type != 'Polygon': continue
        d.polygon([((x - X0) / R * 2, (Y1 - y) / R * 2) for x, y in p.exterior.coords], fill=255)
        for r in p.interiors: d.polygon([((x - X0) / R * 2, (Y1 - y) / R * 2) for x, y in r.coords], fill=0)
    a = np.asarray(im.resize((W_, H_), Image.BOX), dtype=np.float32) / 255.0
    return gaussian_filter(a, feather) if feather else a
def noise(scale_ft, octaves=4, seed=0):
    r = np.random.default_rng(seed); out = np.zeros((H_, W_), np.float32); amp = 1.0; tot = 0.0; s = scale_ft
    for o in range(octaves):
        gh, gw = max(2, int(H_ * R / s) + 2), max(2, int(W_ * R / s) + 2); base = r.random((gh, gw)).astype(np.float32)
        up = zoom(base, (H_ / gh, W_ / gw), order=3)[:H_, :W_]
        if up.shape != (H_, W_): up = np.pad(up, ((0, H_ - up.shape[0]), (0, W_ - up.shape[1])), mode='edge')
        out += amp * up; tot += amp; amp *= 0.5; s /= 2.2
    out /= tot; return (out - out.mean()) / (out.std() + 1e-6)
def lin(hexc): v = np.array([int(hexc[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255.0; return v
N1, N2, N3 = noise(40, 4, 1), noise(9, 3, 2), noise(2.2, 2, 3)
# natural ground from the lidar land-cover map, with forest floor where the canopy was
s = json.load(open(f'{B}/game/data/world.json'))['site']; lc = np.asarray(Image.open(f'{B}/viewer/data/site_color.jpg').convert('RGB'), np.float32) / 255.0
ci = ((PX - s['x0']) / s['w'] * lc.shape[1] - 0.5); cj = ((s['y0'] + s['h'] - PY) / s['h'] * lc.shape[0] - 0.5)
i0 = np.clip(np.floor(ci), 0, lc.shape[1] - 2).astype(int); j0 = np.clip(np.floor(cj), 0, lc.shape[0] - 2).astype(int); ti = np.clip(ci - i0, 0, 1)[..., None]; tj = np.clip(cj - j0, 0, 1)[..., None]
LC = lc[j0, i0] * (1 - ti) * (1 - tj) + lc[j0, i0 + 1] * ti * (1 - tj) + lc[j0 + 1, i0] * (1 - ti) * tj + lc[j0 + 1, i0 + 1] * ti * tj
del ci, cj, i0, j0, ti, tj
LC = np.stack([gaussian_filter(LC[..., k], 2.0) for k in range(3)], -1)
canopy = np.clip((0.42 - LC.mean(-1)) / 0.12, 0, 1) * np.clip((LC[..., 1] - LC[..., 0]) / 0.08, 0, 1)        # dark green = trees in the land-cover map
canopy = gaussian_filter(canopy, 4.0)
floor = lin('#6e5c3e') * (1 - np.clip(0.5 + 0.35 * N1, 0, 1))[..., None] + lin('#55603a') * np.clip(0.5 + 0.35 * N1, 0, 1)[..., None]
native = lin('#8f9a5a') * (1 - np.clip(0.5 + 0.4 * N1, 0, 1))[..., None] + lin('#b4ac78') * np.clip(0.5 + 0.4 * N1, 0, 1)[..., None]
grassy = np.clip((LC[..., 1] - LC[..., 2]) / 0.25, 0, 1)[..., None]
nat = LC * 0.55 + (native * grassy + LC * (1 - grassy)) * 0.45
# open tan ground in the land-cover map (dry grass and bare sand) reads as Bahia pasture; grey roads and red roofs stay
lum = LC.mean(-1); sat = LC.max(-1) - LC.min(-1); tan = np.clip((lum - 0.42) / 0.12, 0, 1) * np.clip((LC[..., 0] - LC[..., 2]) / 0.06, 0, 1) * np.clip((0.30 - sat) / 0.08, 0, 1) * np.clip((LC[..., 1] - LC[..., 0] + 0.14) / 0.06, 0, 1)
pasture = lin('#86924c') * (1 - np.clip(0.5 + 0.45 * N1, 0, 1))[..., None] + lin('#a6a467') * np.clip(0.5 + 0.45 * N1, 0, 1)[..., None]
tan = gaussian_filter(tan, 3.0)[..., None] * 0.95; nat = nat * (1 - tan) + pasture * tan
nat = nat * (1 - canopy[..., None]) + floor * canopy[..., None]
img = nat * (1 + 0.06 * N2[..., None] + 0.05 * N3[..., None])
def lay(mask, col):
    global img
    img = img * (1 - mask[..., None]) + col * mask[..., None]
# turf layers
mT = tmask(turf, 1.4); rough_c = lin('#4f7d2c')[None, None, :] * (1 + 0.07 * N1[..., None] + 0.05 * N2[..., None] + 0.04 * N3[..., None]); lay(mT, rough_c)
def stripes(geom_list, width, amp, cross=False):
    out = np.zeros((H_, W_), np.float32)
    for geom, (tx, ty, gx, gy, L, ux, uy, nx, ny) in geom_list:
        if geom.is_empty: continue
        bx0, by0, bx1, by1 = geom.buffer(4).bounds; c0, c1 = int(max(0, (bx0 - X0) / R)), int(min(W_, (bx1 - X0) / R) + 1); r0, r1 = int(max(0, (Y1 - by1) / R)), int(min(H_, (Y1 - by0) / R) + 1)
        sx, sy = PX[r0:r1, c0:c1], PY[r0:r1, c0:c1]
        a = (sx - tx) * nx + (sy - ty) * ny; v = np.tanh(3.0 * np.sin(np.pi * a / width))
        if cross:
            b_ = (sx - tx) * ux + (sy - ty) * uy; v = 0.5 * (v + np.tanh(3.0 * np.sin(np.pi * b_ / width)))
        out[r0:r1, c0:c1] = np.where(np.abs(v) > np.abs(out[r0:r1, c0:c1]), v, out[r0:r1, c0:c1])
    return gaussian_filter(out, 0.8) * amp
mF = tmask(fairways); stF = stripes([(x['fairway'], x['frame']) for x in holes], 15.0, 0.075)
lay(mF, lin('#6a9e35')[None, None, :] * (1 + stF[..., None] + 0.03 * N2[..., None] + 0.02 * N3[..., None]))
mTe = tmask(tees_u, 0.5); stT = stripes([(t, x['frame']) for x in holes for t in x['tees']], 5.0, 0.06, cross=False)
lay(mTe, lin('#6fa63a')[None, None, :] * (1 + stT[..., None] + 0.02 * N3[..., None]))
mC = tmask(collars, 0.5); lay(mC, lin('#5f9a33')[None, None, :] * (1 + 0.02 * N3[..., None]))
mG = tmask(greens, 0.5); stG = stripes([(x['green'], x['frame']) for x in holes], 7.0, 0.035, cross=True)
lay(mG, lin('#74b23e')[None, None, :] * (1 + stG[..., None] + 0.012 * N3[..., None]))
mBk = tmask(banks_u, 1.0); lay(mBk * 0.85, lin('#6b5a3c')[None, None, :] * (1 + 0.08 * N2[..., None]))
mP = tmask(unary_union([ponds_u] + [lp for lp, _ in lakes]), 0.8); lay(mP, lin('#3b3424')[None, None, :] * (1 + 0.05 * N2[..., None]))                    # pond bed (under the water plane)
mB = tmask(bunkers_u, 0.5); rake = 0.025 * np.sin(PX * 2.1 + PY * 0.7 + 3 * N2)
lay(mB, lin('#e9dcb5')[None, None, :] * (1 + 0.04 * N2[..., None] + 0.03 * N3[..., None] + rake[..., None]))
lip = np.clip(gaussian_filter(mB, 2.5) - mB, 0, 1) * 1.6; lay(np.clip(lip, 0, 0.55), lin('#4e7a2a')[None, None, :])
mPa = tmask(path_poly, 0.5); lay(mPa, lin('#cfcac0')[None, None, :] * (1 + 0.03 * N3[..., None]))
pedge = np.clip(gaussian_filter(mPa, 1.2) - mPa, 0, 1) * 1.2; lay(np.clip(pedge, 0, 0.35), lin('#8f8a7d')[None, None, :])
out = np.clip(img, 0, 1)
Image.fromarray((out * 255).astype(np.uint8)).save(f'{OUT}/surface_0p5ft.jpg', quality=92)
wcol = lin('#24505a')[None, None, :] * (1 + 0.05 * N1[..., None] + 0.03 * N2[..., None]); glint = np.clip(0.25 * gaussian_filter(np.clip(N3, 1.6, None) - 1.6, 1.0), 0, 0.3)
mp = mP[..., None]; outm = np.clip(out * (1 - mp) + (wcol + glint[..., None]) * mp, 0, 1)
small = Image.fromarray((outm * 255).astype(np.uint8)).resize((int(W_ * R), int(H_ * R)), Image.LANCZOS)
small.save(f'{G}/estate_map.jpg' if ESTATE else f'{G}/golf_course_map.jpg', quality=90)
print(f'surface map {W_} x {H_} at {R} ft/px; map at 1 ft/px {small.size}')
if ESTATE:
    json.dump({'extent': [X0, Y0, X1, Y1], 'estate': [[round(x, 1), round(y, 1)] for x, y in estate.exterior.coords], 'lakes': len(lakes)}, open(f'{OUT}/estate.json', 'w'))
    raise SystemExit(0)                                                                     # the course design files come from the course extent only

# ------------------------------------------------------------------ design data and CAD
def coords(gm): return [[[round(x, 1), round(y, 1)] for x, y in p.exterior.coords] for p in getattr(gm, 'geoms', [gm]) if p.geom_type == 'Polygon' and not p.is_empty]
design = {'generated': course['generated'], 'crs': 'EPSG:2236 ftUS, NAVD88 ft', 'extent': [X0, Y0, X1, Y1], 'terrain_grid_ft': g, 'surface_res_ft': R,
          'clubhouse': list(club), 'club_door': [round(c, 1) for c in club_door], 'cut_cy': round(cut), 'fill_cy': round(fill),
          'cart_paths': [[[round(x, 1), round(y, 1)] for x, y in p.coords] for p in paths], 'cart_path_ft': round(sum(p.length for p in paths)),
          'areas_ac': {k: round(v.area / 43560, 2) for k, v in (('turf', turf), ('fairways', fairways), ('greens', greens), ('collars', collars), ('tees', tees_u), ('bunkers', bunkers_u), ('ponds', ponds_u))},
          'holes': [{'n': x['n'], 'green': coords(x['green']), 'collar': coords(x['green'].buffer(5)), 'fairway': coords(x['fairway']), 'rough': coords(x['rough']),
                     'tees': [coords(t)[0] for t in x['tees']], 'bunkers': [coords(b)[0] for b in x['bunkers']], 'pond': coords(x['pond'])[0] if x['pond'] is not None else None,
                     'water_level_ft': x['h'].get('water_level_ft'), 'tee': x['h']['tee'], 'pin': x['h']['green']} for x in holes]}
json.dump(design, open(f'{G}/polish/design.json', 'w'))
print('areas (ac):', design['areas_ac'])
doc = ezdxf.new('R2018', setup=True); doc.header['$INSUNITS'] = 21; msp = doc.modelspace()
LAY = {'L-GOLF-ROUGH': 0x4f7d2c, 'L-GOLF-FWY': 0x6a9e35, 'L-GOLF-COLLAR': 0x5f9a33, 'L-GOLF-GRN': 0x74b23e, 'L-GOLF-TEE': 0x6fa63a,
       'L-GOLF-BNKR': 0xe9dcb5, 'L-GOLF-WATR': 0x2b6f9a, 'L-GOLF-CART': 0xcfcac0, 'L-GOLF-PIN': 0xe0262b, 'L-GOLF-ANNO': 0xffd23c}
for k, c in LAY.items(): doc.layers.add(k, true_color=c)
def zat(x, y): return float(Z[int(np.clip(round((y - Y0) / g), 0, nyg - 1)), int(np.clip(round((x - X0) / g), 0, nxg - 1))])
def add(gm, layer):
    for p in getattr(gm, 'geoms', [gm]):
        if p.geom_type == 'Polygon' and not p.is_empty:
            c = p.centroid; msp.add_lwpolyline(list(p.exterior.coords), close=True, dxfattribs={'layer': layer, 'elevation': round(zat(c.x, c.y), 2)})
for x in holes:
    add(x['rough'], 'L-GOLF-ROUGH'); add(x['fairway'], 'L-GOLF-FWY'); add(x['green'].buffer(5), 'L-GOLF-COLLAR'); add(x['green'], 'L-GOLF-GRN')
    for t in x['tees']: add(t, 'L-GOLF-TEE')
    for b in x['bunkers']: add(b, 'L-GOLF-BNKR')
    if x['pond'] is not None: msp.add_lwpolyline(list(x['pond'].exterior.coords), close=True, dxfattribs={'layer': 'L-GOLF-WATR', 'elevation': x['h']['water_level_ft']})
    gx, gy = x['h']['green']; msp.add_circle((gx, gy, zat(gx, gy)), 0.35, dxfattribs={'layer': 'L-GOLF-PIN'})
    tx, ty = x['h']['tee']; msp.add_text(f"{x['n']}", dxfattribs={'layer': 'L-GOLF-ANNO', 'height': 14}).set_placement((tx + 20, ty + 20))
for p in paths:
    msp.add_lwpolyline(list(p.coords), dxfattribs={'layer': 'L-GOLF-CART', 'const_width': 8.0})
msp.add_mtext('GATOR GREENS - FINISHED COURSE DESIGN (CONCEPT): ROUGH, FAIRWAYS, COLLARS, GREENS, BACK AND FORWARD TEES, BUNKERS, PONDS, 8 FT CART PATHS.\\P'
              'POLYLINE ELEVATIONS FROM THE GRADED SURFACE (NAVD88 FT). XREF THE SITE BASE AND golf_course_3d DXF UNDERNEATH.',
              dxfattribs={'layer': 'L-GOLF-ANNO', 'char_height': 10, 'width': 900}).set_location((X0 + 40, Y1 - 40))
doc.saveas(f'{G}/golf_course_design_EPSG2236_ftUS.dxf'); print('design DXF', os.path.getsize(f'{G}/golf_course_design_EPSG2236_ftUS.dxf') // 1024, 'KB')
