#!/usr/bin/env python3
"""Build an AutoCAD/Civil 3D base model for the Sausage Castle site from USGS 3DEP lidar + Overture Maps.
Inputs: sausage_site.laz (EPSG:3857, Z metres), astatula_{building,segment,water,address}.geojson (WGS84)
Outputs (EPSG:2236 NAD83 / Florida East ftUS, NAVD88 ft): DXF base, ground grid CSV, DTM ASCII grid, preview PNG, metadata JSON
"""
import json, math, gzip, os, sys, time, datetime
import numpy as np, laspy, ezdxf, contourpy
from ezdxf.render import MeshBuilder
from pyproj import Transformer
from shapely.geometry import shape, box, LineString, Polygon, MultiPolygon, MultiLineString
from shapely.ops import transform as shp_transform
import shapely
from scipy import ndimage

t0 = time.time()
def log(*a): print(f"[{time.time()-t0:6.0f}s]", *a, flush=True)

SRC = 'sausage_site.laz'
OUT = '/home/user/beardedfreedom.github.io/reports/sausage-castle-base'
AOI_LL = (-81.7205, 28.6700, -81.7095, 28.6810)          # lon/lat bbox used for the lidar clip
TARGET_LL = (-81.715188, 28.672523)                        # footprint centroid on the 22501 Robbins Rd address point
CELL = 3.0                                                 # ft
M2FT = 1 / 0.30480060960121924                             # metres -> US survey feet
CRS_OUT = 'EPSG:2236'
to_sp = Transformer.from_crs('EPSG:3857', CRS_OUT, always_xy=True)
ll_to_sp = Transformer.from_crs('EPSG:4326', CRS_OUT, always_xy=True)
def ll2sp(geom): return shp_transform(lambda x, y, z=None: ll_to_sp.transform(x, y), geom)

# ---------- 1. read + reproject lidar ----------
las = laspy.read(SRC)
n = len(las); log('points', n)
cls = np.asarray(las.classification)
keep = ~np.isin(cls, [7, 18])                              # drop low/high noise
xm, ym, zm = np.asarray(las.x)[keep], np.asarray(las.y)[keep], np.asarray(las.z)[keep]
cls = cls[keep]; rn = np.asarray(las.return_number)[keep]
del las
X = np.empty(len(xm)); Y = np.empty(len(ym))
for i in range(0, len(xm), 4_000_000):
    X[i:i+4_000_000], Y[i:i+4_000_000] = to_sp.transform(xm[i:i+4_000_000], ym[i:i+4_000_000])
Z = (zm * M2FT).astype(np.float32)
del xm, ym, zm
log('reprojected to', CRS_OUT, 'X', X.min().round(1), X.max().round(1), 'Y', Y.min().round(1), Y.max().round(1), 'Z', Z.min().round(1), Z.max().round(1))

# ---------- 2. grids ----------
x0, y0 = math.floor(X.min()), math.floor(Y.min())
nx = int(math.ceil((X.max() - x0) / CELL)) + 1; ny = int(math.ceil((Y.max() - y0) / CELL)) + 1
ci = ((X - x0) / CELL).astype(np.int64); cj = ((Y - y0) / CELL).astype(np.int64)
idx = cj * nx + ci
def grid_max(mask):
    g = np.full(nx * ny, np.nan, dtype=np.float32)
    ii, zz = idx[mask], Z[mask]
    order = np.argsort(ii, kind='stable'); ii, zz = ii[order], zz[order]
    starts = np.flatnonzero(np.r_[True, ii[1:] != ii[:-1]])
    g[ii[starts]] = np.maximum.reduceat(zz, starts)
    return g.reshape(ny, nx)
def grid_mean(mask):
    s = np.bincount(idx[mask], weights=Z[mask], minlength=nx * ny); c = np.bincount(idx[mask], minlength=nx * ny)
    g = np.full(nx * ny, np.nan, dtype=np.float32); ok = c > 0; g[ok] = s[ok] / c[ok]
    return g.reshape(ny, nx), c.reshape(ny, nx)
ground = cls == 2
dtm_raw, gcount = grid_mean(ground)
has_ground = gcount > 0
dsm = grid_max(rn == 1)
dsm_all = grid_max(np.ones(len(Z), bool))
dsm = np.where(np.isnan(dsm), dsm_all, dsm)
log(f'grid {nx}x{ny} @ {CELL} ft; ground cells {has_ground.mean()*100:.1f}% filled; ground pts {ground.sum():,}')
# fill ground holes (lakes, under buildings) with nearest ground cell, then light smoothing for contours
fill_idx = ndimage.distance_transform_edt(~has_ground, return_distances=False, return_indices=True)
dtm = dtm_raw[tuple(fill_idx)]
dtm_smooth = ndimage.gaussian_filter(dtm, sigma=1.5)
dsm = np.where(np.isnan(dsm), dtm, dsm)
ndsm = np.clip(dsm - dtm, 0, None)
log('DTM ft min/med/max', np.nanmin(dtm).round(1), np.nanmedian(dtm).round(1), np.nanmax(dtm).round(1))

# ---------- 3. vector context (Overture) ----------
aoi = ll2sp(box(*AOI_LL))
def load(fn):
    feats = json.load(open(fn))['features']
    out = []
    for f in feats:
        g = ll2sp(shape(f['geometry']))
        if g.intersects(aoi):
            out.append((f['properties'], g))
    return out
bld = load('astatula_building.geojson'); seg = load('astatula_segment.geojson'); wat = load('astatula_water.geojson'); addr = load('astatula_addr.geojson')
log('overture in AOI: buildings', len(bld), 'segments', len(seg), 'water', len(wat), 'addresses', len(addr))

def cells_in(poly):
    minx, miny, maxx, maxy = poly.bounds
    i0, i1 = max(int((minx - x0) / CELL), 0), min(int((maxx - x0) / CELL) + 1, nx - 1)
    j0, j1 = max(int((miny - y0) / CELL), 0), min(int((maxy - y0) / CELL) + 1, ny - 1)
    if i1 <= i0 or j1 <= j0: return None, None
    jj, ii = np.mgrid[j0:j1 + 1, i0:i1 + 1]
    cx, cy = x0 + (ii + 0.5) * CELL, y0 + (jj + 0.5) * CELL
    m = shapely.contains_xy(poly, cx.ravel(), cy.ravel()).reshape(cx.shape)
    return (jj[m], ii[m]), m.sum()

buildings = []
for p, g in bld:
    polys = list(g.geoms) if isinstance(g, MultiPolygon) else [g]
    for poly in polys:
        if poly.area < 60: continue                        # < 60 sq ft: skip sheds/noise
        cells, cnt = cells_in(poly)
        base = float(np.median(dtm[cells])) if cnt else float(dtm[min(int((poly.centroid.y - y0)/CELL), ny-1), min(int((poly.centroid.x - x0)/CELL), nx-1)])
        h_lidar = float(np.percentile(ndsm[cells], 95)) if cnt and cnt >= 4 else None
        h_ovt = p.get('height'); h_ovt = float(h_ovt) * M2FT if h_ovt else None
        h = h_lidar if h_lidar and h_lidar > 6 else (h_ovt or 12.0)
        buildings.append(dict(poly=poly, base=base, height=h, h_lidar=h_lidar, h_overture=h_ovt, area=poly.area, src=p.get('sources', '')))
log('buildings modelled', len(buildings))

# ---------- 4. DXF ----------
doc = ezdxf.new('R2018', setup=True)
doc.header['$INSUNITS'] = 21                               # US survey feet (AutoCAD 2017+); fall back to 2 if a reader complains
doc.header['$MEASUREMENT'] = 0
doc.header['$EXTMIN'] = (x0, y0, 0); doc.header['$EXTMAX'] = (x0 + nx * CELL, y0 + ny * CELL, 200)
L = {'C-TOPO-MINR': 8, 'C-TOPO-MAJR': 3, 'A-BLDG-FTPT': 1, 'A-BLDG-3D': 30, 'A-BLDG-ANNO': 1, 'C-ROAD-CNTR': 7, 'C-ROAD-ANNO': 7,
     'C-WATR-BNDY': 5, 'C-WATR-ANNO': 5, 'G-ANNO-ADDR': 2, 'G-ANNO-AOI': 6, 'G-ANNO-TRGT': 6, 'G-ANNO-NOTE': 7, 'C-TOPO-GRND-PTS': 252}
for name, color in L.items(): doc.layers.add(name, color=color)
msp = doc.modelspace()

# contours (1 ft minor / 5 ft major) from smoothed DTM
xs = x0 + (np.arange(nx) + 0.5) * CELL; ys = y0 + (np.arange(ny) + 0.5) * CELL
cg = contourpy.contour_generator(x=xs, y=ys, z=dtm_smooth, name='serial', line_type=contourpy.LineType.Separate)
lo, hi = int(math.floor(np.nanmin(dtm_smooth))), int(math.ceil(np.nanmax(dtm_smooth)))
n_ctr = 0; n_vtx = 0
aoi_prep = shapely.prepared.prep(aoi)
for lvl in range(lo, hi + 1):
    layer = 'C-TOPO-MAJR' if lvl % 5 == 0 else 'C-TOPO-MINR'
    for arr in cg.lines(float(lvl)):
        if len(arr) < 3: continue
        ls = LineString(arr).simplify(0.6, preserve_topology=False)
        if ls.length < 30: continue
        pts = list(ls.coords)
        pl = msp.add_lwpolyline(pts, dxfattribs={'layer': layer, 'elevation': float(lvl)})
        if pts[0] == pts[-1]: pl.close(True)
        n_ctr += 1; n_vtx += len(pts)
log('contours', n_ctr, 'vertices', n_vtx, 'levels', lo, '-', hi)

# buildings: footprint at base elevation + extruded MESH
for b in buildings:
    ring = list(b['poly'].exterior.coords)[:-1]
    if b['poly'].exterior.is_ccw is False: ring = ring[::-1]
    msp.add_lwpolyline(ring, close=True, dxfattribs={'layer': 'A-BLDG-FTPT', 'elevation': b['base']})
    mb = MeshBuilder(); k = len(ring); top = b['base'] + b['height']
    bot = [(x, y, b['base']) for x, y in ring]; up = [(x, y, top) for x, y in ring]
    mb.add_face(up); mb.add_face(bot[::-1])
    for i in range(k):
        mb.add_face([bot[i], bot[(i+1) % k], up[(i+1) % k], up[i]])
    mb.render_mesh(msp, dxfattribs={'layer': 'A-BLDG-3D'})
    c = b['poly'].centroid
    msp.add_text(f"{b['area']:.0f} sf  h={b['height']:.0f}'", height=4, dxfattribs={'layer': 'A-BLDG-ANNO'}).set_placement((c.x, c.y), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

# roads
for p, g in seg:
    names = p.get('names'); name = json.loads(names).get('primary') if names else None
    lines = list(g.geoms) if isinstance(g, MultiLineString) else [g]
    for ls in lines:
        ls = ls.intersection(aoi)
        parts = list(ls.geoms) if hasattr(ls, 'geoms') else [ls]
        for part in parts:
            if part.is_empty or part.geom_type != 'LineString': continue
            msp.add_lwpolyline(list(part.coords), dxfattribs={'layer': 'C-ROAD-CNTR'})
            if name and part.length > 200:
                m = part.interpolate(0.5, normalized=True)
                msp.add_text(f"{name} ({p.get('class')})", height=6, dxfattribs={'layer': 'C-ROAD-ANNO'}).set_placement((m.x, m.y))
# water
for p, g in wat:
    polys = list(g.geoms) if isinstance(g, MultiPolygon) else ([g] if g.geom_type == 'Polygon' else [])
    for poly in polys:
        poly = poly.intersection(aoi)
        for pp in (list(poly.geoms) if hasattr(poly, 'geoms') else [poly]):
            if pp.is_empty or pp.geom_type != 'Polygon': continue
            msp.add_lwpolyline(list(pp.exterior.coords), close=True, dxfattribs={'layer': 'C-WATR-BNDY'})
            c = pp.centroid
            msp.add_text(f"{p.get('subtype','water')} {pp.area/43560:.1f} ac", height=5, dxfattribs={'layer': 'C-WATR-ANNO'}).set_placement((c.x, c.y), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
# addresses
for p, g in addr:
    msp.add_circle((g.x, g.y), 3, dxfattribs={'layer': 'G-ANNO-ADDR'})
    msp.add_text(f"{p.get('number','')} {p.get('street','')}", height=4, dxfattribs={'layer': 'G-ANNO-ADDR'}).set_placement((g.x + 5, g.y + 5))
# AOI frame, target marker, notes
msp.add_lwpolyline(list(aoi.exterior.coords), close=True, dxfattribs={'layer': 'G-ANNO-AOI'})
tx, ty = ll_to_sp.transform(*TARGET_LL)
msp.add_circle((tx, ty), 60, dxfattribs={'layer': 'G-ANNO-TRGT'})
msp.add_text('22500/22501 ROBBINS RD - "SAUSAGE CASTLE" (LISTING/ADDRESS POINT) - VERIFY PARCEL', height=8, dxfattribs={'layer': 'G-ANNO-TRGT'}).set_placement((tx + 70, ty))
note = ("SAUSAGE CASTLE SITE BASE - EXISTING CONDITIONS (CONCEPT GRADE, NOT A SURVEY)\\P"
        f"GENERATED {datetime.date.today()} FROM PUBLIC DATA:\\P"
        "- TERRAIN: USGS 3DEP LIDAR, PROJECT FL_Peninsular_Lake_2018 (PUBLIC DOMAIN), GROUND-CLASSIFIED POINTS, 3 FT GRID, 1 FT CONTOURS (SMOOTHED)\\P"
        "- BUILDINGS/ROADS/WATER/ADDRESSES: OVERTURE MAPS 2026-09-23.1 (ODbL / CDLA), HEIGHTS FROM LIDAR 95TH PERCENTILE ABOVE GROUND\\P"
        "- COORDINATE SYSTEM: NAD83 / FLORIDA EAST, US SURVEY FEET (EPSG:2236 / CIVIL 3D 'FL83-EF'). ELEVATIONS NAVD88 FEET (LIDAR METRES x 3.28083333)\\P"
        "- LAKE SURFACES: NO LIDAR RETURNS; FILLED FROM NEAREST SHORE - DO NOT USE FOR BATHYMETRY\\P"
        "- NO PARCEL LINES INCLUDED: OBTAIN FROM LAKE COUNTY PROPERTY APPRAISER (PARCELS 09-21-26-000300004800/-4600/-4900) OR A BOUNDARY SURVEY\\P"
        "- ACCURACY: LIDAR QL2 ~10 CM RMSEz VERTICAL; HORIZONTAL DATUM WGS84->NAD83 SHIFT NOT APPLIED (~1 M)")
msp.add_mtext(note, dxfattribs={'layer': 'G-ANNO-NOTE', 'char_height': 6, 'width': 900}).set_location((x0 + 20, y0 + ny * CELL - 20))
dxf_path = f'{OUT}/sausage_castle_base_EPSG2236_ftUS.dxf'
doc.saveas(dxf_path); log('DXF written', os.path.getsize(dxf_path) // 1024, 'KB')

# ---------- 5. ground grid CSV (PNEZD, 6 ft, only cells with real ground returns) ----------
step = 2
csv_path = f'{OUT}/sausage_castle_ground_pts_6ft_PNEZD.csv.gz'
with gzip.open(csv_path, 'wt') as f:
    f.write('# P,N,E,Z,D  -- Civil 3D point file format PNEZD (comma delimited); N/E in ftUS EPSG:2236; Z NAVD88 ft; D=description\n')
    k = 0
    for j in range(0, ny, step):
        for i in range(0, nx, step):
            if has_ground[j, i]:
                k += 1; f.write(f"{k},{y0 + (j + 0.5) * CELL:.2f},{x0 + (i + 0.5) * CELL:.2f},{dtm_raw[j, i]:.2f},GRND\n")
log('ground points CSV', k, 'pts', os.path.getsize(csv_path) // 1024, 'KB')

# ---------- 6. DTM ESRI ASCII grid ----------
asc_path = f'{OUT}/sausage_castle_dtm_3ft_EPSG2236.asc.gz'
with gzip.open(asc_path, 'wt') as f:
    f.write(f"ncols {nx}\nnrows {ny}\nxllcorner {x0}\nyllcorner {y0}\ncellsize {CELL}\nNODATA_value -9999\n")
    for j in range(ny - 1, -1, -1):
        row = np.where(has_ground[j], dtm_raw[j], dtm[j])
        f.write(' '.join(f"{v:.2f}" for v in row) + '\n')
log('DTM asc', os.path.getsize(asc_path) // 1024, 'KB')

# ---------- 7. preview PNG ----------
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
dy, dx = np.gradient(dsm, CELL); slope = np.arctan(np.hypot(dx, dy)); aspect = np.arctan2(-dx, dy)
az, alt = math.radians(315), math.radians(45)
shade = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
fig, ax = plt.subplots(figsize=(12, 12 * ny / nx), dpi=200)
ext = [x0, x0 + nx * CELL, y0, y0 + ny * CELL]
ax.imshow(shade, cmap='gray', extent=ext, origin='lower', vmin=-0.2, vmax=1.1)
ax.imshow(np.ma.masked_less(ndsm, 8), cmap='YlGn', extent=ext, origin='lower', alpha=0.35, vmin=8, vmax=60)
for p, g in wat:
    for pp in (list(g.geoms) if hasattr(g, 'geoms') else [g]):
        if pp.geom_type == 'Polygon': ax.add_patch(MPoly(list(pp.exterior.coords), closed=True, fc='#4aa3df', ec='#1f5f8b', alpha=0.6, lw=0.6))
for b in buildings: ax.add_patch(MPoly(list(b['poly'].exterior.coords), closed=True, fc='none', ec='red', lw=0.8))
for p, g in seg:
    for ls in (list(g.geoms) if hasattr(g, 'geoms') else [g]):
        xx, yy = ls.xy; ax.plot(xx, yy, color='black', lw=1.2)
for p, g in addr:
    ax.plot(g.x, g.y, 'o', ms=2, color='orange'); ax.text(g.x + 8, g.y + 8, str(p.get('number', '')), fontsize=4, color='darkorange')
ax.add_patch(MPoly([(tx-60,ty-60),(tx+60,ty-60),(tx+60,ty+60),(tx-60,ty+60)], closed=True, fc='none', ec='magenta', lw=1.5))
ax.text(tx + 70, ty + 70, '22500/22501 Robbins Rd', fontsize=7, color='magenta', weight='bold')
ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3]); ax.set_aspect('equal')
ax.set_title('Sausage Castle site, Astatula FL: lidar hillshade (USGS 3DEP 2018) + Overture buildings/roads/water\nNAD83 Florida East ftUS (EPSG:2236); green = >8 ft above ground (trees/roofs); north up', fontsize=8)
ax.set_xlabel('Easting (ftUS)'); ax.set_ylabel('Northing (ftUS)'); ax.tick_params(labelsize=6)
png_path = f'{OUT}/sausage_castle_preview.png'  # converted to .jpg afterwards to keep the repo small; fig.savefig(png_path, bbox_inches='tight'); log('preview', os.path.getsize(png_path) // 1024, 'KB')

# ---------- 8. metadata ----------
meta = dict(generated=str(datetime.datetime.now()), crs=CRS_OUT, crs_name='NAD83 / Florida East (ftUS)', vertical='NAVD88 ft (lidar metres x 3.2808333)',
            lidar_project='FL_Peninsular_Lake_2018', lidar_source='s3://usgs-lidar-public (USGS 3DEP EPT)', points_used=int(len(Z)), ground_points=int(ground.sum()),
            aoi_lonlat=AOI_LL, extent_ftUS=dict(xmin=x0, ymin=y0, xmax=x0 + nx * CELL, ymax=y0 + ny * CELL), cell_ft=CELL, grid=[nx, ny],
            dtm_ft=dict(min=float(np.nanmin(dtm)), median=float(np.nanmedian(dtm)), max=float(np.nanmax(dtm))), contours=dict(count=n_ctr, interval_ft=1, levels=[lo, hi]),
            buildings=[dict(area_sf=round(b['area']), base_ft=round(b['base'], 1), height_ft=round(b['height'], 1), h_lidar=b['h_lidar'] and round(b['h_lidar'], 1), h_overture=b['h_overture'] and round(b['h_overture'], 1), centroid=[round(b['poly'].centroid.x, 1), round(b['poly'].centroid.y, 1)]) for b in buildings],
            overture_release='2026-09-23.1', target_ftUS=[tx, ty], target_lonlat=TARGET_LL)
json.dump(meta, open(f'{OUT}/sausage_castle_base_metadata.json', 'w'), indent=1)
log('done')
