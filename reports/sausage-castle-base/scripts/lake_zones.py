#!/usr/bin/env python3
"""Concept: four equal-area zones around the round lake, spacing rules, and tiny-home pad capacity."""
import json, math, datetime, os
import numpy as np, ezdxf, shapely
from shapely.geometry import Polygon, Point, LineString, shape, box
from shapely.ops import transform as shp_transform, unary_union
from shapely.affinity import rotate, translate
from pyproj import Transformer
from PIL import Image
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, Circle, Rectangle

BASE = '/home/user/beardedfreedom.github.io/reports/sausage-castle-base'
OUT = f'{BASE}/focus/lakes'
# ---- design rules (assumptions, stated in outputs)
WATER_BUFFER = 50      # ft, no-build strip from the lidar water edge
ZONE_LIMIT = int(os.environ.get('ZONE_LIMIT', 250))       # ft, outer limit of the lake zones from the water edge
LANE_W = 20            # ft, loop track lane width (existing service road)
LANE_SETBACK = 20      # ft, pad front from the lane edge
PAD_W, PAD_D = 35, 50  # ft, pad footprint along lane x depth (unit + porch + 2 cars)
SIDE_GAP = 15          # ft, between neighbouring pads
BLDG_CLEAR = 20        # ft, from existing buildings
ROAD_CLEAR = 25        # ft, from other existing roads
ll_to_sp = Transformer.from_crs('EPSG:4326', 'EPSG:2236', always_xy=True)
def ll2sp(g): return shp_transform(lambda x, y, z=None: ll_to_sp.transform(x, y), g)

# ---- inputs from the focus model
doc0 = ezdxf.readfile(f'{OUT}/sausage_castle_lakes_focus_EPSG2236_ftUS.dxf'); msp0 = doc0.modelspace()
waters = [Polygon([(p[0], p[1]) for p in e.get_points()]) for e in msp0.query('LWPOLYLINE[layer=="C-WATR-LIDAR"]')]
lake = max(waters, key=lambda l: l.centroid.x).simplify(1.5).buffer(0); elong = min(waters, key=lambda l: l.centroid.x).buffer(0)
trees = [Point(e.dxf.center.x, e.dxf.center.y).buffer(e.dxf.radius) for e in msp0.query('CIRCLE[layer=="L-PLNT-TREE"]')]
tree_pts = [(e.dxf.center.x, e.dxf.center.y, e.dxf.radius) for e in msp0.query('CIRCLE[layer=="L-PLNT-TREE"]')]
bldgs = [Polygon([(p[0], p[1]) for p in e.get_points()]) for e in msp0.query('LWPOLYLINE[layer=="A-BLDG-FTPT"]')]
segs = [(f['properties'], ll2sp(shape(f['geometry']))) for f in json.load(open('astatula_segment.geojson'))['features']]
c = lake.centroid
loop = max((g for p, g in segs if g.distance(lake) < 120 and g.length > 1000), key=lambda g: g.length)
other_roads = unary_union([g for p, g in segs if g is not loop and g.distance(c) < 600])
print('lake', round(lake.area / 43560, 2), 'ac; loop', round(loop.length), 'ft; loop-to-shore min/mean', round(loop.distance(lake)), round(np.mean([lake.exterior.distance(loop.interpolate(s)) for s in np.arange(0, loop.length, 10)])))

# ---- zone ring and equal-area split
buf = lake.buffer(WATER_BUFFER); outer = lake.buffer(ZONE_LIMIT)
ring = outer.difference(buf).difference(elong.buffer(WATER_BUFFER))
def wedge(a0, a1, R=1500):
    pts = [(c.x, c.y)]
    n = max(4, int((a1 - a0) / 2))
    for k in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * k / n); pts.append((c.x + R * math.sin(a), c.y + R * math.cos(a)))
    return Polygon(pts)
T = ring.area; theta0 = 0.0; cuts = [theta0]
for q in (1, 2, 3):
    lo, hi = cuts[-1] + 1, theta0 + 359.9
    for _ in range(60):
        mid = (lo + hi) / 2
        if ring.intersection(wedge(theta0, mid)).area < T * q / 4: lo = mid
        else: hi = mid
    cuts.append((lo + hi) / 2)
cuts.append(theta0 + 360)
names = ['A', 'B', 'C', 'D']; zones = []
for k in range(4):
    z = ring.intersection(wedge(cuts[k], cuts[k + 1])).buffer(0)
    if z.geom_type != 'Polygon': z = max(z.geoms, key=lambda g: g.area)
    zones.append(z)
print('cut azimuths', [round(a, 1) for a in cuts], 'zone acres', [round(z.area / 43560, 2) for z in zones])

# ---- pads along the loop, both sides
lane_half = LANE_W / 2; off = lane_half + LANE_SETBACK + PAD_D / 2
pitch = PAD_W + SIDE_GAP; keep_out = unary_union([buf, elong.buffer(WATER_BUFFER)] + [b.buffer(BLDG_CLEAR) for b in bldgs] + [other_roads.buffer(ROAD_CLEAR), loop.buffer(lane_half + LANE_SETBACK - 0.5)])
pads = []; placed = []
for side in (+1, -1):
    s = pitch / 2
    while s < loop.length:
        p = loop.interpolate(s); p0 = loop.interpolate(max(0, s - 2)); p1 = loop.interpolate(min(loop.length, s + 2))
        tx, ty = p1.x - p0.x, p1.y - p0.y; L = math.hypot(tx, ty) or 1; tx, ty = tx / L, ty / L; nx_, ny_ = -ty * side, tx * side
        cx, cy = p.x + nx_ * off, p.y + ny_ * off
        ang = math.degrees(math.atan2(ty, tx))
        pad = rotate(box(cx - PAD_W / 2, cy - PAD_D / 2, cx + PAD_W / 2, cy + PAD_D / 2), ang, origin=(cx, cy))
        ok = ring.contains(pad) and not pad.intersects(keep_out) and all(not pad.intersects(q.buffer(SIDE_GAP - 0.5)) for q in placed)
        zi = next((i for i, z in enumerate(zones) if z.contains(pad)), None)
        if ok and zi is not None:
            placed.append(pad); pads.append(dict(zone=names[zi], side='lake side' if side > 0 and loop.is_ring is False and Point(cx, cy).distance(lake) < p.distance(lake) else ('lake side' if Point(cx, cy).distance(lake) < p.distance(lake) else 'outer side'), poly=pad, center=(cx, cy), angle=ang, trees=sum(1 for t in trees if t.intersects(pad))))
        s += pitch
# renumber per zone
counter = {n: 0 for n in names}
for pd in sorted(pads, key=lambda d: (d['zone'], d['side'], d['center'])):
    counter[pd['zone']] += 1; pd['id'] = f"{pd['zone']}{counter[pd['zone']]:02d}"
# ---- per-zone metrics
rows = []
for n, z, a0, a1 in zip(names, zones, cuts[:-1], cuts[1:]):
    w = wedge(a0, a1); front = lake.exterior.intersection(w).length
    lp = loop.intersection(w); lane_len = lp.length
    dists = [lake.exterior.distance(lp.interpolate(s)) for s in np.arange(0, lp.length, 10)] if lp.length else [0]
    zp = [pd for pd in pads if pd['zone'] == n]
    ntree = sum(1 for t in trees if t.centroid.within(z)); bl = [b for b in bldgs if b.intersects(z)]
    rows.append(dict(zone=n, azimuth_from=round(a0), azimuth_to=round(a1), area_ac=round(z.area / 43560, 2), area_sf=round(z.area), frontage_ft=round(front), lane_ft=round(lane_len),
                     shore_to_lane_min=round(min(dists)), shore_to_lane_mean=round(float(np.mean(dists))), shore_to_lane_max=round(max(dists)),
                     pads_lake_side=sum(1 for p in zp if p['side'] == 'lake side'), pads_outer_side=sum(1 for p in zp if p['side'] == 'outer side'), pads_total=len(zp),
                     trees=ntree, trees_in_pads=sum(p['trees'] for p in zp), existing_buildings=len(bl), existing_bldg_sf=round(sum(b.area for b in bl)),
                     gross_capacity_est=int(z.area * 0.55 / ((PAD_W + SIDE_GAP) * (PAD_D + LANE_SETBACK + 10)))))
for r in rows: print({k: r[k] for k in ('zone','area_ac','frontage_ft','pads_lake_side','pads_outer_side','pads_total','trees_in_pads')})
if os.environ.get('DRY'): print('TOTAL pads', sum(r['pads_total'] for r in rows), 'zone ac', rows[0]['area_ac']); raise SystemExit

# ---- DXF
doc = ezdxf.new('R2018', setup=True); doc.header['$INSUNITS'] = 21; msp = doc.modelspace()
for name, color in {'C-WATR-LAKE': 5, 'C-WATR-BUFR': 4, 'C-ZONE-LIMIT': 6, 'C-ZONE-BNDY': 1, 'C-ZONE-ANNO': 1, 'C-ROAD-LOOP': 7, 'C-ROAD-EDGE': 8, 'C-ROAD-EXST': 8,
                    'A-UNIT-PAD': 30, 'A-UNIT-ANNO': 30, 'A-BLDG-EXST': 9, 'L-PLNT-TREE-EXST': 92, 'G-ANNO-DIMS': 2, 'G-ANNO-NOTE': 7}.items(): doc.layers.add(name, color=color)
def poly(g, layer, elev=0, close=True):
    for pg in (list(g.geoms) if hasattr(g, 'geoms') else [g]):
        if pg.is_empty: continue
        if pg.geom_type == 'Polygon': msp.add_lwpolyline(list(pg.exterior.coords), close=True, dxfattribs={'layer': layer, 'elevation': elev})
        elif pg.geom_type == 'LineString': msp.add_lwpolyline(list(pg.coords), dxfattribs={'layer': layer})
poly(lake, 'C-WATR-LAKE'); poly(buf.exterior, 'C-WATR-BUFR'); poly(outer.exterior, 'C-ZONE-LIMIT'); poly(loop, 'C-ROAD-LOOP')
poly(loop.buffer(lane_half).exterior, 'C-ROAD-EDGE'); poly(loop.buffer(lane_half).interiors[0] if loop.buffer(lane_half).interiors else loop, 'C-ROAD-EDGE')
poly(other_roads.intersection(outer.buffer(100)), 'C-ROAD-EXST')
for b in bldgs:
    if b.intersects(outer.buffer(60)): poly(b, 'A-BLDG-EXST')
for x, y, r in tree_pts:
    if Point(x, y).within(outer.buffer(30)): msp.add_circle((x, y), r, dxfattribs={'layer': 'L-PLNT-TREE-EXST'})
for n, z, r in zip(names, zones, rows):
    poly(z, 'C-ZONE-BNDY'); cz = z.representative_point()
    msp.add_text(f"ZONE {n}", height=14, dxfattribs={'layer': 'C-ZONE-ANNO'}).set_placement((cz.x, cz.y + 10), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    msp.add_text(f"{r['area_ac']:.2f} AC · {r['frontage_ft']} FT LAKE FRONTAGE · {r['pads_total']} PADS", height=5, dxfattribs={'layer': 'C-ZONE-ANNO'}).set_placement((cz.x, cz.y - 8), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
for pd in pads:
    poly(pd['poly'], 'A-UNIT-PAD'); msp.add_text(pd['id'], height=4, dxfattribs={'layer': 'A-UNIT-ANNO'}).set_placement(pd['center'], align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
# dimension callouts (aligned dims where possible, text fallback)
def dim(p1, p2, label, side=12):
    try:
        d = msp.add_aligned_dim(p1=p1, p2=p2, distance=side, dxfattribs={'layer': 'G-ANNO-DIMS'}, override={'dimtxt': 4, 'dimasz': 3}); d.render()
    except Exception: pass
    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    msp.add_text(label, height=4, dxfattribs={'layer': 'G-ANNO-DIMS'}).set_placement((mx, my + side + 4), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
# buffer dim: shore point due east -> 50 ft out; zone limit dim; lane dims on first pad of zone A
ex = lake.exterior.interpolate(lake.exterior.project(Point(c.x + 1000, c.y)))
dim((ex.x, ex.y), (ex.x + WATER_BUFFER, ex.y), f'{WATER_BUFFER} FT WATER BUFFER (NO BUILD)')
dim((ex.x + WATER_BUFFER, ex.y), (ex.x + ZONE_LIMIT, ex.y), f'{ZONE_LIMIT - WATER_BUFFER} FT ZONE DEPTH (LIMIT {ZONE_LIMIT} FT FROM WATER)', side=24)
pa = next((p for p in pads if p['zone'] == 'A'), pads[0]); cxp, cyp = pa['center']; a = math.radians(pa['angle']); ux, uy = math.cos(a), math.sin(a); vx, vy = -uy, ux
dim((cxp - ux * PAD_W / 2, cyp - uy * PAD_W / 2), (cxp + ux * PAD_W / 2, cyp + uy * PAD_W / 2), f'PAD {PAD_W} FT WIDE', side=PAD_D / 2 + 6)
dim((cxp - vx * PAD_D / 2, cyp - vy * PAD_D / 2), (cxp + vx * PAD_D / 2, cyp + vy * PAD_D / 2), f'PAD {PAD_D} FT DEEP', side=PAD_W / 2 + 6)
note = (f"LAKE ZONES CONCEPT - FOUR EQUAL-AREA ZONES AROUND THE ROUND LAKE\\PGENERATED {datetime.date.today()} ON THE LIDAR BASE (USGS 3DEP 2018); CONCEPT GRADE, NOT A SURVEY; NO PARCEL LINES; ZONING NOT YET VERIFIED\\P"
        f"RULES USED: {WATER_BUFFER} FT NO-BUILD BUFFER FROM THE 2018 WATER EDGE; ZONES EXTEND TO {ZONE_LIMIT} FT FROM THE WATER; ZONE LINES RADIATE FROM THE LAKE CENTROID AT AZIMUTHS "
        + ', '.join(f'{a:.0f}' for a in cuts[:-1]) + f" (EQUAL AREAS {rows[0]['area_ac']:.2f} AC EACH)\\P"
        f"EXISTING LOOP TRACK USED AS THE LANE ({LANE_W} FT); PADS {PAD_W} x {PAD_D} FT SET {LANE_SETBACK} FT BACK FROM THE LANE EDGE, {SIDE_GAP} FT BETWEEN PADS, {BLDG_CLEAR} FT FROM EXISTING BUILDINGS, {ROAD_CLEAR} FT FROM OTHER ROADS\\P"
        f"PADS PLACED: {len(pads)} ({', '.join(str(r['zone']) + '=' + str(r['pads_total']) for r in rows)}). TREE CIRCLES ARE 2018 CANOPY; PADS OVER TREES NEED CLEARING\\P"
        "CRS NAD83 / FLORIDA EAST ftUS (EPSG:2236); XREF THE LAKES FOCUS DXF FOR CONTOURS AND ROOFS")
msp.add_mtext(note, dxfattribs={'layer': 'G-ANNO-NOTE', 'char_height': 4, 'width': 520}).set_location((outer.bounds[0] - 40, outer.bounds[3] + 120))
dxf_path = f'{OUT}/lake_zones_concept_EPSG2236_ftUS.dxf'; doc.saveas(dxf_path); print('DXF', os.path.getsize(dxf_path) // 1024, 'KB')

# ---- plan drawing
meta = json.load(open(f'{BASE}/viewer/data/meta.json'))['zones']['lakes']
im = np.asarray(Image.open(f"{BASE}/viewer/data/{meta['surface']['file']}").convert('RGB')).astype(float)
dsm = (im[..., 0] * 256 + im[..., 1]) * meta['surface']['scale'] + meta['surface']['zmin']; dsm = dsm[::-1]   # row 0 = south now
cell = meta['cell_ft']; x0, y0 = meta['x0'], meta['y0']; ny, nx = dsm.shape
dy, dx = np.gradient(dsm, cell); sl = np.arctan(np.hypot(dx, dy)); asp = np.arctan2(-dx, dy); az, al = math.radians(315), math.radians(45)
hs = np.sin(al) * np.cos(sl) + np.cos(al) * np.sin(sl) * np.cos(az - asp)
zone_cols = ['#d94f3d', '#e8a33c', '#3f8f5a', '#4a7fc2']
fig, ax = plt.subplots(figsize=(14, 12), dpi=150)
ax.imshow(hs, cmap='gray', extent=[x0, x0 + nx * cell, y0, y0 + ny * cell], origin='lower', vmin=-0.2, vmax=1.15)
for zc, z, n, r in zip(zone_cols, zones, names, rows):
    ax.add_patch(MPoly(list(z.exterior.coords), closed=True, fc=zc, ec=zc, alpha=0.28, lw=1.5))
    ax.add_patch(MPoly(list(z.exterior.coords), closed=True, fc='none', ec=zc, lw=2))
    cz = z.representative_point(); ax.text(cz.x, cz.y + 12, f'ZONE {n}', ha='center', fontsize=15, weight='bold', color=zc)
    ax.text(cz.x, cz.y - 14, f"{r['area_ac']:.2f} ac · {r['frontage_ft']} ft frontage\n{r['pads_total']} pads ({r['pads_lake_side']} lake side, {r['pads_outer_side']} outer)", ha='center', fontsize=8.5, color='#111', bbox=dict(fc='white', ec='none', alpha=0.75, pad=2))
ax.add_patch(MPoly(list(lake.exterior.coords), closed=True, fc='#4aa3df', ec='#1f5f8b', alpha=0.85, lw=1))
ax.plot(*buf.exterior.xy, color='#1f5f8b', lw=1.2, ls='--'); ax.plot(*outer.exterior.xy, color='#7a2c8f', lw=1.4, ls='-.')
lb = loop.buffer(lane_half); ax.add_patch(MPoly(list(lb.exterior.coords), closed=True, fc='#555', ec='none', alpha=0.85))
if lb.interiors: ax.add_patch(MPoly(list(lb.interiors[0].coords), closed=True, fc='none', ec='none'))
for pg in (list(other_roads.geoms) if hasattr(other_roads, 'geoms') else [other_roads]):
    if pg.geom_type == 'LineString': ax.plot(*pg.xy, color='#555', lw=3, alpha=0.7)
for b in bldgs:
    if b.intersects(outer.buffer(60)): ax.add_patch(MPoly(list(b.exterior.coords), closed=True, fc='#b0433a', ec='#7a2020', lw=1))
for x, y, r in tree_pts:
    if Point(x, y).within(outer.buffer(30)): ax.add_patch(Circle((x, y), r, fc='#2f7a3a', ec='none', alpha=0.25))
for pd in pads:
    ax.add_patch(MPoly(list(pd['poly'].exterior.coords), closed=True, fc='#f5e6a8', ec='#8a6d1a', lw=1)); ax.text(pd['center'][0], pd['center'][1], pd['id'], ha='center', va='center', fontsize=5.5, color='#3b2f0a')
# dimension callouts
ax.annotate('', (ex.x, ex.y), (ex.x + WATER_BUFFER, ex.y), arrowprops=dict(arrowstyle='<->', color='#1f5f8b', lw=1.2)); ax.text(ex.x + WATER_BUFFER / 2, ex.y + 6, f'{WATER_BUFFER} ft no-build', ha='center', fontsize=8, color='#1f5f8b')
ax.annotate('', (ex.x + WATER_BUFFER, ex.y - 30), (ex.x + ZONE_LIMIT, ex.y - 30), arrowprops=dict(arrowstyle='<->', color='#7a2c8f', lw=1.2)); ax.text(ex.x + (WATER_BUFFER + ZONE_LIMIT) / 2, ex.y - 24, f'{ZONE_LIMIT - WATER_BUFFER} ft zone depth', ha='center', fontsize=8, color='#7a2c8f')
ax.text(cxp, cyp - PAD_D / 2 - 14, f'pad {PAD_W}×{PAD_D} ft · {SIDE_GAP} ft between · {LANE_SETBACK} ft off lane', ha='center', fontsize=7.5, color='#8a6d1a', bbox=dict(fc='white', ec='none', alpha=0.8, pad=1.5))
bx = outer.bounds; ax.set_xlim(bx[0] - 80, bx[2] + 80); ax.set_ylim(bx[1] - 80, bx[3] + 80); ax.set_aspect('equal')
ax.set_title('Lake zones concept: four equal-area zones around the round lake, with the existing loop track as the lane\n'
             f'{WATER_BUFFER} ft water buffer, zones to {ZONE_LIMIT} ft from shore, pads {PAD_W}×{PAD_D} ft · EPSG:2236 ftUS · concept grade, no parcel lines, zoning unverified', fontsize=10)
ax.set_xlabel('Easting (ftUS)'); ax.set_ylabel('Northing (ftUS)'); ax.tick_params(labelsize=7)
ax.plot([bx[2] - 20, bx[2] - 20], [bx[1] - 60, bx[1] + 40], color='k', lw=2); ax.text(bx[2] - 20, bx[1] + 48, 'N', ha='center', fontsize=10, weight='bold')
ax.plot([bx[0] - 60, bx[0] + 40], [bx[1] - 60, bx[1] - 60], color='k', lw=3); ax.text(bx[0] - 10, bx[1] - 52, '100 ft', ha='center', fontsize=8)
fig.savefig(f'{OUT}/lake_zones_plan.jpg', dpi=150, bbox_inches='tight', pil_kwargs={'quality': 90}); plt.close(fig)

# ---- viewer overlay texture (zones + pads drawn over the lakes colour map)
col = Image.open(f'{BASE}/viewer/data/lakes_color.jpg').convert('RGBA'); W, H = col.size   # row 0 = north
from PIL import ImageDraw
ov = Image.new('RGBA', col.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
def px(pt): return ((pt[0] - x0) / cell, (y0 + ny * cell - pt[1]) / cell)
for zc, z in zip(zone_cols, zones):
    rgb = tuple(int(zc[i:i + 2], 16) for i in (1, 3, 5)); dr.polygon([px(p) for p in z.exterior.coords], fill=rgb + (70,), outline=rgb + (255,), width=3)
for pd in pads: dr.polygon([px(p) for p in pd['poly'].exterior.coords], fill=(245, 230, 168, 230), outline=(138, 109, 26, 255), width=2)
dr.line([px(p) for p in buf.exterior.coords], fill=(31, 95, 139, 255), width=2); dr.line([px(p) for p in outer.exterior.coords], fill=(122, 44, 143, 255), width=3)
Image.alpha_composite(col, ov).convert('RGB').save(f'{BASE}/viewer/data/lakes_zones.jpg', quality=88, optimize=True)
mj = json.load(open(f'{BASE}/viewer/data/meta.json')); mj['zones']['lakes']['overlay'] = 'lakes_zones.jpg'; mj['zones']['lakes']['overlay_label'] = 'Lake zones concept'; json.dump(mj, open(f'{BASE}/viewer/data/meta.json', 'w'), indent=1)

# ---- data + markdown
json.dump(dict(rules=dict(water_buffer_ft=WATER_BUFFER, zone_limit_ft=ZONE_LIMIT, lane_width_ft=LANE_W, lane_setback_ft=LANE_SETBACK, pad_ft=[PAD_W, PAD_D], side_gap_ft=SIDE_GAP, building_clearance_ft=BLDG_CLEAR, road_clearance_ft=ROAD_CLEAR),
               lake=dict(area_ac=round(lake.area / 43560, 2), centroid=[round(c.x, 1), round(c.y, 1)], shoreline_ft=round(lake.exterior.length)), loop_ft=round(loop.length), cut_azimuths=[round(a, 1) for a in cuts[:-1]], zones=rows,
               pads=[dict(id=p['id'], zone=p['zone'], side=p['side'], center=[round(p['center'][0], 1), round(p['center'][1], 1)], angle_deg=round(p['angle'], 1), trees=p['trees'], corners=[[round(x, 1), round(y, 1)] for x, y in p['poly'].exterior.coords[:-1]]) for p in pads]),
          open(f'{OUT}/lake_zones_concept.json', 'w'), indent=1)
tot = sum(r['pads_total'] for r in rows)
md = f"""# Lake zones concept: four equal zones around the round lake

Drafted {datetime.date.today()} on the lidar base. Concept grade: no parcel lines, no survey, zoning not yet verified with Lake County.

## The lake and the loop

| Item | Value |
|---|---|
| Lake (2018 lidar water edge) | {lake.area/43560:.2f} acres, {round(lake.exterior.length)} ft of shoreline, water surface about 70.0 ft NAVD88 |
| Existing loop track | {round(loop.length)} ft long, {round(loop.distance(lake))} to {max(r['shore_to_lane_max'] for r in rows)} ft from the shore (mean {round(float(np.mean([r['shore_to_lane_mean'] for r in rows])))} ft), used as the {LANE_W} ft lane |
| Zone ring | {WATER_BUFFER} ft no-build buffer to {ZONE_LIMIT} ft from the water: {ring.area/43560:.2f} acres split four ways |

## Spacing rules used

| Rule | Distance |
|---|---|
| No-build buffer from the water edge | {WATER_BUFFER} ft |
| Zone depth beyond the buffer | {ZONE_LIMIT - WATER_BUFFER} ft (zones end {ZONE_LIMIT} ft from the water) |
| Lane width (existing loop track) | {LANE_W} ft |
| Pad front from the lane edge | {LANE_SETBACK} ft |
| Pad footprint (unit, porch, two cars) | {PAD_W} × {PAD_D} ft |
| Gap between pads | {SIDE_GAP} ft (pitch {PAD_W + SIDE_GAP} ft along the lane) |
| Clearance from existing buildings / other roads | {BLDG_CLEAR} ft / {ROAD_CLEAR} ft |

## The four zones

Zone lines radiate from the lake centroid at azimuths {', '.join(f'{a:.0f}°' for a in cuts[:-1])} so that each zone has the same area.

| Zone | Sector (azimuth) | Area | Lake frontage | Lane length | Shore to lane (min / mean / max) | Pads lake side | Pads outer side | Pads total | Trees in zone (2018) | Trees under pads | Existing buildings |
|---|---|---|---|---|---|---|---|---|---|---|---|
""" + '\n'.join(f"| {r['zone']} | {r['azimuth_from']}° to {r['azimuth_to']}° | {r['area_ac']:.2f} ac ({r['area_sf']:,} sf) | {r['frontage_ft']} ft | {r['lane_ft']} ft | {r['shore_to_lane_min']} / {r['shore_to_lane_mean']} / {r['shore_to_lane_max']} ft | {r['pads_lake_side']} | {r['pads_outer_side']} | {r['pads_total']} | {r['trees']} | {r['trees_in_pads']} | {r['existing_buildings']} ({r['existing_bldg_sf']:,} sf) |" for r in rows) + f"""

Total pads placed on one row each side of the loop: {tot}. A rough gross-capacity check (55 percent of zone area at one pad plus its share of lane and gaps) gives {', '.join(str(r['zone']) + ' ' + str(r['gross_capacity_est']) for r in rows)}, so a second outer row served by a rear lane would roughly double the count.

## Files

- `lake_zones_concept_EPSG2236_ftUS.dxf`: zones, buffer, limit, loop lane edges, pads with IDs, existing buildings and trees near the ring, dimension callouts and a notes block. Xref the lakes focus DXF underneath for contours and roofs.
- `lake_zones_plan.jpg`: the plan drawing over the lidar hillshade.
- `lake_zones_concept.json`: rules, per-zone metrics and every pad's corners in State Plane feet.
- The 3D viewer's Lakes zone has a "Lake zones concept" toggle that drapes this layout on the terrain.

## What to check before this becomes a plan

1. Lake County zoning for district A and whether tiny homes, park models or an RV-style community are permitted here, plus any Planned Unit Development route.
2. The county's waterbody and wetland setbacks (this concept assumes {WATER_BUFFER} ft) and St. Johns River Water Management District rules for the lake.
3. Parcel lines from the Property Appraiser, since the {ZONE_LIMIT} ft ring may cross the estate's lots.
4. Septic or sewer, well capacity and fire access: a {LANE_W} ft loop with pads on both sides needs turnouts or a wider lane for fire apparatus.
"""
open(f'{OUT}/LAKE-ZONES-CONCEPT.md', 'w').write(md); print('pads', tot, 'md written')
