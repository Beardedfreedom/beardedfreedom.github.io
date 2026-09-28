#!/usr/bin/env python3
"""Florida Freedom World master plan: map the poster's programme onto the Sausage Castle estate (EPSG:2236 ftUS)."""
import json, math, datetime, os
import numpy as np, ezdxf
from PIL import Image
from shapely.geometry import Polygon, Point, LineString, box, shape
from shapely.ops import unary_union, transform as shp_transform
from pyproj import Transformer
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, Circle
BASE = '/home/user/beardedfreedom.github.io/reports/sausage-castle-base'; OUT = f'{BASE}/masterplan'
meta = json.load(open(f'{BASE}/viewer/data/meta.json'))['zones']['site']
im = np.asarray(Image.open(f"{BASE}/viewer/data/{meta['surface']['file']}").convert('RGB')).astype(float)
dsm = ((im[..., 0] * 256 + im[..., 1]) * meta['surface']['scale'] + meta['surface']['zmin'])[::-1]
c = meta['cell_ft']; x0, y0 = meta['x0'], meta['y0']; ny, nx = dsm.shape
dy, dx = np.gradient(dsm, c); sl = np.arctan(np.hypot(dx, dy)); asp = np.arctan2(-dx, dy); az, al = math.radians(315), math.radians(45)
hs = np.sin(al) * np.cos(sl) + np.cos(al) * np.sin(sl) * np.cos(az - asp)
lz = json.load(open(f'{BASE}/focus/lakes/lake_zones_concept.json'))
ll_to_sp = Transformer.from_crs('EPSG:4326', 'EPSG:2236', always_xy=True)
def ll2sp(g): return shp_transform(lambda x, y, z=None: ll_to_sp.transform(x, y), g)
water = [ll2sp(shape(f['geometry'])) for f in json.load(open('astatula_water.geojson'))['features']]
segs = [ll2sp(shape(f['geometry'])) for f in json.load(open('astatula_segment.geojson'))['features']]
bld = [ll2sp(shape(f['geometry'])) for f in json.load(open('astatula_building.geojson'))['features']]
site = box(x0, y0, x0 + nx * c, y0 + ny * c)
round_lake = Point(426595, 1579180).buffer(130); long_lake = Polygon([(425800, 1578620), (426000, 1578620), (426220, 1578900), (426220, 1579090), (426020, 1579090), (425790, 1578800)])
for w in water:
    if w.intersects(site):
        if w.distance(Point(426595, 1579180)) < 5: round_lake = w
        if w.distance(Point(426006, 1578844)) < 5: long_lake = w
zone_ring = Point(426595, 1579180).buffer(250).difference(round_lake.buffer(50))
# ---- programme (name, colour, geometry, poster element, capacity note)
P = []
def add(key, name, color, geom, poster, note): P.append(dict(key=key, name=name, color=color, geom=geom, poster=poster, note=note))
add('gate', 'Gator Gate and midway', '#ff6a1f', box(426620, 1577300, 427010, 1577760), 'the gator mascot, rides, snake-skin airboat photo op', 'entry plaza at the house drive; existing 200 ft ring becomes the carousel and putt-putt; food trucks along the drive')
add('castle', 'The Castle (existing house)', '#ffc93c', Point(426828, 1577904).buffer(90), 'headquarters', 'existing 7,423 sq ft house and 43 ft tower: office, VIP, first aid, radio room')
add('arena', 'Freedom Arena', '#ff2fa8', box(426190, 1577170, 426630, 1577630), 'the laser stage and crowd', 'the existing 400 x 400 ft cleared square; stage on the north edge facing south; about 4,000 people on the lawn at 40 sq ft each')
add('golf', 'Gator Greens pitch and putt', '#7dd35a', box(426180, 1577650, 426620, 1577980), 'the golfer', 'nine short holes around the pond (68.8 ft) with the 4,479 sq ft outbuilding as the clubhouse and cart barn')
add('cabins', 'Lakeside cabins (four lands)', '#2fb0ff', zone_ring, 'mushrooms, haunted hammock, swamp camp', '22 themed tiny homes on the loop track around the round lake; zone A haunted, B swamp, C mushroom, D mixed')
add('lagoon', 'Freedom Float lagoon', '#33c6c6', long_lake.buffer(60), 'the girl on the float, the turtle', 'the 1.6 ac long lake (water 69.3 ft) as a swim and float lagoon with a sand beach on the east bank; no motors')
add('grove', 'Butterfly Grove and mushroom garden', '#ffb6f2', box(426060, 1578440, 426470, 1579010).difference(long_lake.buffer(60)), 'butterflies, sunflowers, toadstools', 'the existing orchard rows kept as a walk-through pollinator garden and the mushroom-home showcase')
add('barn', 'Goat Barn petting farm', '#c9a06a', unary_union([box(426170, 1579140, 426370, 1579340), box(425850, 1579100, 426250, 1579450)]), 'the goat', 'the existing 1,869 sq ft barn plus the north-west orchard block as pasture')
add('lodge', 'Swamp Camp lodge', '#8b6b4a', Point(426876, 1578711).buffer(110), 'the tent and campfire', 'the existing 5,378 sq ft building as bathhouse, laundry and camp store for the cabins; fire circle behind')
add('rv', 'RV and tent camp', '#f5e08a', box(427080, 1578650, 427360, 1579550), 'the RV', 'about 35 RV sites at 45 x 60 ft on two lanes plus a tent loop; hookups from the north drive')
add('ufo', 'Landing Site observation tower', '#b48cff', Point(425850, 1578530).buffer(120), 'the UFO and the sky', 'a 40 ft steel tower on the knoll south-west of the lagoon for the night drone and laser show; the highest ground near the lakes')
add('barns', 'Event barns (ownership to confirm)', '#9aa3a8', box(426600, 1579560, 426990, 1579760), 'indoor stage and rain plan', 'four existing barns of 6,300 to 7,600 sq ft; may sit on the neighbouring parcel')
trail = unary_union([s for s in segs if s.intersects(site) and s.length > 300]).intersection(site)
# ---- metrics
rows = []
for p in P:
    g = p['geom'].intersection(site); p['geom'] = g
    rows.append(dict(key=p['key'], name=p['name'], acres=round(g.area / 43560, 2), poster=p['poster'], note=p['note'], centroid=[round(g.centroid.x), round(g.centroid.y)], trees_note=''))
for r in rows: print(f"{r['key']:8s} {r['acres']:6.2f} ac  {r['name']}")
print('programme total', round(sum(r['acres'] for r in rows), 1), 'ac; trail', round(trail.length), 'ft')
# ---- DXF
doc = ezdxf.new('R2018', setup=True); doc.header['$INSUNITS'] = 21; msp = doc.modelspace()
doc.layers.add('L-PROG-ANNO', color=2); doc.layers.add('C-TRAIL-LOOP', color=7); doc.layers.add('G-ANNO-NOTE', color=7)
for p in P:
    ln = 'L-PROG-' + p['key'].upper(); doc.layers.add(ln, true_color=int(p['color'][1:], 16))
    for pg in (list(p['geom'].geoms) if hasattr(p['geom'], 'geoms') else [p['geom']]):
        if pg.geom_type == 'Polygon': msp.add_lwpolyline(list(pg.exterior.coords), close=True, dxfattribs={'layer': ln})
    cz = p['geom'].representative_point(); msp.add_text(f"{p['name'].upper()}  {p['geom'].area/43560:.1f} AC", height=10, dxfattribs={'layer': 'L-PROG-ANNO'}).set_placement((cz.x, cz.y), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
for ls in (list(trail.geoms) if hasattr(trail, 'geoms') else [trail]):
    if ls.geom_type == 'LineString': msp.add_lwpolyline(list(ls.coords), dxfattribs={'layer': 'C-TRAIL-LOOP'})
msp.add_mtext(f"FLORIDA FREEDOM WORLD - MASTER PLAN PROGRAMME ({datetime.date.today()})\\PPROGRAMME AREAS MAPPED ONTO THE LIDAR BASE; CONCEPT GRADE; NO PARCEL LINES; ZONING, ACCESS AND UTILITIES UNVERIFIED\\PEPSG:2236 ftUS. XREF THE SITE BASE DXF UNDERNEATH.", dxfattribs={'layer': 'G-ANNO-NOTE', 'char_height': 8, 'width': 900}).set_location((x0 + 40, y0 + ny * c - 40))
doc.saveas(f'{OUT}/florida_freedom_world_masterplan_EPSG2236_ftUS.dxf')
json.dump(dict(generated=str(datetime.date.today()), crs='EPSG:2236 ftUS', programme=rows, trail_ft=round(trail.length)), open(f'{OUT}/masterplan.json', 'w'), indent=1)
# ---- plan image (dark poster palette on the hillshade)
fig, ax = plt.subplots(figsize=(14, 15.6), dpi=140); fig.patch.set_facecolor('#0b0a14'); ax.set_facecolor('#0b0a14')
ax.imshow(hs, cmap='gray', extent=[x0, x0 + nx * c, y0, y0 + ny * c], origin='lower', vmin=-0.3, vmax=1.4, alpha=0.9)
for w in water:
    if w.intersects(site):
        for pg in (list(w.geoms) if hasattr(w, 'geoms') else [w]):
            if pg.geom_type == 'Polygon': ax.add_patch(MPoly(list(pg.exterior.coords), closed=True, fc='#2fb0ff', ec='#9fe0ff', alpha=0.75, lw=0.8))
for ls in (list(trail.geoms) if hasattr(trail, 'geoms') else [trail]):
    if ls.geom_type == 'LineString': xx, yy = ls.xy; ax.plot(xx, yy, color='#ffffff', lw=1.6, alpha=0.55)
for b in bld:
    if b.intersects(site):
        for pg in (list(b.geoms) if hasattr(b, 'geoms') else [b]):
            if pg.geom_type == 'Polygon' and pg.area > 400: ax.add_patch(MPoly(list(pg.exterior.coords), closed=True, fc='#ff6a1f', ec='#ffd0b0', lw=0.5, alpha=0.9))
for i, p in enumerate(P):
    for pg in (list(p['geom'].geoms) if hasattr(p['geom'], 'geoms') else [p['geom']]):
        if pg.geom_type != 'Polygon': continue
        ax.add_patch(MPoly(list(pg.exterior.coords), closed=True, fc=p['color'], ec=p['color'], alpha=0.28, lw=0))
        ax.add_patch(MPoly(list(pg.exterior.coords), closed=True, fc='none', ec=p['color'], lw=2.2))
    cz = p['geom'].representative_point()
    ax.text(cz.x, cz.y, f"{i+1}", ha='center', va='center', fontsize=13, weight='bold', color='#0b0a14', bbox=dict(boxstyle='circle,pad=0.35', fc=p['color'], ec='white', lw=1.2))
legend = '\n'.join(f"{i+1}  {p['name']}  ·  {p['geom'].area/43560:.1f} ac" for i, p in enumerate(P))
ax.text(x0 + 60, y0 + 60, legend, fontsize=10.5, color='#fff6e6', va='bottom', family='DejaVu Sans', bbox=dict(fc='#15132a', ec='#ff6a1f', lw=1.5, alpha=0.92, pad=10))
ax.text(x0 + nx * c - 60, y0 + ny * c - 60, 'FLORIDA FREEDOM WORLD\nmaster plan programme on the lidar base', ha='right', va='top', fontsize=20, weight='bold', color='#ffc93c', family='DejaVu Sans')
ax.text(x0 + nx * c - 60, y0 + ny * c - 300, 'Sausage Castle estate, Astatula FL · EPSG:2236 ftUS · concept grade\nwhite lines: existing roads and trail loop · orange: existing buildings · blue: lakes', ha='right', va='top', fontsize=9.5, color='#cfd6d0')
ax.plot([x0 + nx * c - 460, x0 + nx * c - 60], [y0 + 140, y0 + 140], color='white', lw=3); ax.text(x0 + nx * c - 260, y0 + 165, '400 ft', ha='center', fontsize=9, color='white')
ax.text(x0 + nx * c - 120, y0 + 330, 'N', ha='center', fontsize=12, weight='bold', color='white'); ax.annotate('', (x0 + nx * c - 120, y0 + 320), (x0 + nx * c - 120, y0 + 200), arrowprops=dict(arrowstyle='-|>', color='white', lw=2))
ax.set_xlim(x0, x0 + nx * c); ax.set_ylim(y0, y0 + ny * c); ax.set_aspect('equal'); ax.set_axis_off(); fig.subplots_adjust(0, 0, 1, 1)
fig.savefig(f'{OUT}/florida_freedom_world_masterplan.jpg', dpi=140, facecolor=fig.get_facecolor(), pil_kwargs={'quality': 88}); plt.close(fig); print('plan image written')
