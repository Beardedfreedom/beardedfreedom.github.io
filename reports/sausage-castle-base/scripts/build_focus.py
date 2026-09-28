#!/usr/bin/env python3
"""High-detail focus models (house compound, lakes) from the Sausage Castle lidar clip.
Outputs per zone under reports/sausage-castle-base/focus/<zone>/ : DXF (0.5/1/5 ft contours, lidar-shaped roof meshes,
walls, 5 ft terrain mesh, trees, lidar-derived water outlines, notes), DSM 1 ft + DTM 2 ft ASCII grids, ground PNEZD 2 ft,
preview PNG, metadata JSON. CRS EPSG:2236 ftUS, NAVD88 ft."""
import json, math, gzip, os, time, datetime
import numpy as np, laspy, ezdxf, contourpy, shapely
from ezdxf.render import MeshBuilder
from pyproj import Transformer
from shapely.geometry import shape, box, LineString, Polygon, MultiPolygon
from shapely.ops import transform as shp_transform
from scipy import ndimage
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, Circle

t0 = time.time()
def log(*a): print(f"[{time.time()-t0:6.0f}s]", *a, flush=True)
OUT = '/home/user/beardedfreedom.github.io/reports/sausage-castle-base/focus'
M2FT = 1 / 0.30480060960121924
to_sp = Transformer.from_crs('EPSG:3857', 'EPSG:2236', always_xy=True)
ll_to_sp = Transformer.from_crs('EPSG:4326', 'EPSG:2236', always_xy=True)
def ll2sp(g): return shp_transform(lambda x, y, z=None: ll_to_sp.transform(x, y), g)
ZONES = {
    'house': dict(title='Main house and compound (22500/22501 Robbins Rd)', bbox=(426050, 1577150, 427050, 1578150)),
    'lakes': dict(title='Lakes and loop track', bbox=(425750, 1578350, 427050, 1579550)),
}
TARGET = ll_to_sp.transform(-81.715188, 28.672523)

las = laspy.read('sausage_site.laz'); cls = np.asarray(las.classification); keep = ~np.isin(cls, [7, 18])
xm, ym, zm = np.asarray(las.x)[keep], np.asarray(las.y)[keep], np.asarray(las.z)[keep]
cls = cls[keep]; rn = np.asarray(las.return_number)[keep]; del las
X = np.empty(len(xm)); Y = np.empty(len(ym))
for i in range(0, len(xm), 4_000_000): X[i:i+4_000_000], Y[i:i+4_000_000] = to_sp.transform(xm[i:i+4_000_000], ym[i:i+4_000_000])
Z = (zm * M2FT).astype(np.float32); del xm, ym, zm
log('points ready', len(Z))
bld_all = [(f['properties'], ll2sp(shape(f['geometry']))) for f in json.load(open('astatula_building.geojson'))['features']]
wat_all = [(f['properties'], ll2sp(shape(f['geometry']))) for f in json.load(open('astatula_water.geojson'))['features']]
seg_all = [(f['properties'], ll2sp(shape(f['geometry']))) for f in json.load(open('astatula_segment.geojson'))['features']]

def grid_reduce(ii, zz, n, how):
    g = np.full(n, np.nan, np.float32)
    if len(ii) == 0: return g
    order = np.argsort(ii, kind='stable'); ii, zz = ii[order], zz[order]
    starts = np.flatnonzero(np.r_[True, ii[1:] != ii[:-1]])
    g[ii[starts]] = (np.maximum.reduceat(zz, starts) if how == 'max' else np.add.reduceat(zz, starts) / np.diff(np.r_[starts, len(zz)]))
    return g
def fill_nearest(g):
    m = np.isnan(g)
    if not m.any(): return g
    idx = ndimage.distance_transform_edt(m, return_distances=False, return_indices=True)
    return g[tuple(idx)]
def hillshade(dsm, cell):
    dy, dx = np.gradient(dsm, cell); slope = np.arctan(np.hypot(dx, dy)); aspect = np.arctan2(-dx, dy)
    az, alt = math.radians(315), math.radians(45)
    return np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)

for zname, zc in ZONES.items():
    x0, y0, x1, y1 = zc['bbox']; zdir = f'{OUT}/{zname}'; os.makedirs(zdir, exist_ok=True)
    m = (X >= x0) & (X < x1) & (Y >= y0) & (Y < y1)
    zx, zy, zz, zc_, zr = X[m], Y[m], Z[m], cls[m], rn[m]
    nx1, ny1 = int((x1 - x0)), int((y1 - y0))                       # 1 ft grid
    nx2, ny2 = nx1 // 2, ny1 // 2                                    # 2 ft grid
    i1 = (zx - x0).astype(np.int64); j1 = (zy - y0).astype(np.int64); idx1 = j1 * nx1 + i1
    i2 = i1 // 2; j2 = j1 // 2; idx2 = j2 * nx2 + i2
    # DSM 1 ft: max of first returns, then any return, then nearest fill
    dsm = grid_reduce(idx1[zr == 1], zz[zr == 1], nx1 * ny1, 'max').reshape(ny1, nx1)
    dsm_any = grid_reduce(idx1, zz, nx1 * ny1, 'max').reshape(ny1, nx1)
    dsm = np.where(np.isnan(dsm), dsm_any, dsm)
    returns_2ft = np.bincount(idx2, minlength=nx2 * ny2).reshape(ny2, nx2)
    dsm = ndimage.median_filter(fill_nearest(dsm), size=3)
    # DTM 2 ft: mean of ground returns, fill, smooth
    gm = zc_ == 2
    dtm_raw = grid_reduce(idx2[gm], zz[gm], nx2 * ny2, 'mean').reshape(ny2, nx2)
    has_ground = ~np.isnan(dtm_raw)
    dtm = fill_nearest(dtm_raw)
    log(zname, f'pts {len(zz):,} ground {gm.sum():,} ({gm.sum()/((x1-x0)*(y1-y0)):.2f}/sqft) grid1 {nx1}x{ny1} ground cells {has_ground.mean()*100:.0f}% DTM {np.nanmin(dtm_raw):.1f}-{np.nanmax(dtm_raw):.1f} ft')

    zone = box(x0, y0, x1, y1)
    # ---- water from lidar: 2 ft cells with zero returns, opened/closed, >= 3000 sq ft
    nowater = returns_2ft == 0
    wmask = ndimage.binary_opening(nowater, iterations=2); wmask = ndimage.binary_closing(wmask, iterations=3)
    lab, nlab = ndimage.label(wmask); waters = []
    xs2 = x0 + (np.arange(nx2) + 1) * 2 - 1; ys2 = y0 + (np.arange(ny2) + 1) * 2 - 1
    for k in range(1, nlab + 1):
        cells = lab == k; area = cells.sum() * 4
        if area < 3000: continue
        cg = contourpy.contour_generator(x=xs2, y=ys2, z=cells.astype(float), line_type=contourpy.LineType.Separate)
        rings = [r for r in cg.lines(0.5) if len(r) > 3]
        if not rings: continue
        ring = max(rings, key=len); poly = Polygon(ring).simplify(1.5)
        if not poly.is_valid or poly.area < 3000: continue
        lvl = float('nan')
        for it in (4, 8, 14):
            shore = ndimage.binary_dilation(cells, iterations=it) & ~ndimage.binary_dilation(cells, iterations=1) & has_ground
            if shore.sum() >= 30: lvl = float(np.percentile(dtm_raw[shore], 25)); break
        if math.isnan(lvl): lvl = float(np.median(dtm[ndimage.binary_dilation(cells, iterations=3) & ~cells]))
        waters.append(dict(poly=poly, area_sf=float(poly.area), level=lvl, cells=cells))
    log(zname, 'lidar water bodies', len(waters), [(round(w['area_sf']/43560, 2), round(w['level'], 1)) for w in waters])
    # hydro-flatten: water cells take the water surface elevation in DTM and DSM
    water2 = np.zeros((ny2, nx2), bool)
    for w in waters:
        dtm[w['cells']] = w['level']; water2 |= w['cells']
        w1 = np.repeat(np.repeat(w['cells'], 2, axis=0), 2, axis=1)[:ny1, :nx1]
        dsm[w1] = w['level']
    water1 = np.repeat(np.repeat(ndimage.binary_dilation(water2, iterations=2), 2, axis=0), 2, axis=1)[:ny1, :nx1]
    dtm_s = ndimage.gaussian_filter(dtm, 1.0)
    for w in waters: dtm_s[w['cells']] = w['level']
    dtm1 = ndimage.zoom(dtm_s, (ny1 / ny2, nx1 / nx2), order=1)
    if dtm1.shape != dsm.shape: dtm1 = dtm1[:ny1, :nx1]
    chm = np.clip(dsm - dtm1, 0, None); chm[water1] = 0

    # ---- buildings: lidar-shaped roofs
    bld = [(p, g) for p, g in bld_all if g.intersects(zone)]
    bmask_all = np.zeros((ny1, nx1), bool); buildings = []
    jj, ii = np.mgrid[0:ny1, 0:nx1]; cxg = x0 + ii + 0.5; cyg = y0 + jj + 0.5
    for p, g in bld:
        for poly in (list(g.geoms) if isinstance(g, MultiPolygon) else [g]):
            poly = poly.intersection(zone)
            if poly.is_empty or poly.geom_type != 'Polygon' or poly.area < 100: continue
            minx, miny, maxx, maxy = poly.bounds
            i0, i1_ = max(int(minx - x0) - 2, 0), min(int(maxx - x0) + 3, nx1); j0, j1_ = max(int(miny - y0) - 2, 0), min(int(maxy - y0) + 3, ny1)
            sub = shapely.contains_xy(poly.buffer(1.0), cxg[j0:j1_, i0:i1_].ravel(), cyg[j0:j1_, i0:i1_].ravel()).reshape(j1_ - j0, i1_ - i0)
            if sub.sum() < 20: continue
            bmask_all[j0:j1_, i0:i1_] |= sub
            roof = dsm[j0:j1_, i0:i1_]; grd = dtm1[j0:j1_, i0:i1_]
            base = float(np.percentile(grd[sub], 10)); ridge = float(np.percentile(roof[sub], 98))
            inner = shapely.contains_xy(poly.buffer(-2.5), cxg[j0:j1_, i0:i1_].ravel(), cyg[j0:j1_, i0:i1_].ravel()).reshape(sub.shape)
            eave = float(np.percentile(roof[inner], 25)) if inner.sum() >= 10 else float(np.percentile(roof[sub], 25))
            # vertex grid (corners) with Z = mean of adjacent in-mask cells
            H, W = sub.shape; vz = np.full((H + 1, W + 1), np.nan); cnt = np.zeros((H + 1, W + 1))
            for dj, di in ((0, 0), (0, 1), (1, 0), (1, 1)):
                acc = np.zeros((H + 1, W + 1)); acc[dj:dj + H, di:di + W] = np.where(sub, roof, 0); c = np.zeros((H + 1, W + 1)); c[dj:dj + H, di:di + W] = sub
                vz = np.where(np.isnan(vz), 0, vz) + acc; cnt += c
            vz = np.where(cnt > 0, vz / np.maximum(cnt, 1), np.nan)
            mb = MeshBuilder(); vx = x0 + i0 + np.arange(W + 1); vy = y0 + j0 + np.arange(H + 1)
            def V(j, i, z=None): return (float(vx[i]), float(vy[j]), float(vz[j, i] if z is None else z))
            for j in range(H):
                for i in range(W):
                    if not sub[j, i]: continue
                    mb.add_face([V(j, i), V(j, i + 1), V(j + 1, i + 1), V(j + 1, i)])
                    for (nj, ni, a, b) in ((j - 1, i, (j, i), (j, i + 1)), (j, i + 1, (j, i + 1), (j + 1, i + 1)), (j + 1, i, (j + 1, i + 1), (j + 1, i)), (j, i - 1, (j + 1, i), (j, i))):
                        if nj < 0 or ni < 0 or nj >= H or ni >= W or not sub[nj, ni]:
                            mb.add_face([V(*a), V(*b), V(*b, z=base), V(*a, z=base)])
            buildings.append(dict(poly=poly, base=base, ridge=ridge, eave=eave, mesh=mb, area=float(poly.area), faces=len(mb.faces)))
    log(zname, 'buildings', len(buildings), 'roof+wall faces', sum(b['faces'] for b in buildings))

    # ---- trees: CHM local maxima outside buildings
    chm_t = np.where(ndimage.binary_dilation(bmask_all, iterations=5), 0, chm)
    chm_t = ndimage.gaussian_filter(chm_t, 1.5)
    win = 17
    peaks = (chm_t == ndimage.maximum_filter(chm_t, size=win)) & (chm_t > 12)
    pj, pi = np.nonzero(peaks); trees = []
    for j, i in zip(pj, pi):
        h = float(chm_t[j, i]); rads = []
        for dj, di in ((0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)):
            r = 0
            for s in range(1, 31):
                jj_, ii_ = j + dj * s, i + di * s
                if jj_ < 0 or ii_ < 0 or jj_ >= ny1 or ii_ >= nx1 or chm_t[jj_, ii_] < 0.5 * h: break
                r = s
            rads.append(r * (1.414 if dj and di else 1))
        trees.append(dict(x=x0 + i + 0.5, y=y0 + j + 0.5, h=h, r=float(np.clip(np.mean(rads), 4, 30)), z=float(dtm1[j, i])))
    log(zname, 'trees (>12 ft, 17 ft window)', len(trees))

    # ---- DXF
    doc = ezdxf.new('R2018', setup=True); doc.header['$INSUNITS'] = 21; doc.header['$MEASUREMENT'] = 0
    for name, color in {'C-TOPO-HALF': 9, 'C-TOPO-MINR': 8, 'C-TOPO-MAJR': 3, 'C-TOPO-MESH-3D': 254, 'A-BLDG-FTPT': 1, 'A-BLDG-ROOF-3D': 30, 'A-BLDG-ANNO': 1,
                        'L-PLNT-TREE': 92, 'L-PLNT-ANNO': 92, 'C-WATR-LIDAR': 5, 'C-WATR-OVERTURE': 4, 'C-WATR-ANNO': 5, 'C-ROAD-CNTR': 7,
                        'G-ANNO-ZONE': 6, 'G-ANNO-TRGT': 6, 'G-ANNO-NOTE': 7}.items(): doc.layers.add(name, color=color)
    msp = doc.modelspace()
    cg = contourpy.contour_generator(x=xs2, y=ys2, z=dtm_s, line_type=contourpy.LineType.Separate)
    lo, hi = math.floor(np.nanmin(dtm_s) * 2) / 2, math.ceil(np.nanmax(dtm_s) * 2) / 2
    n_ctr = 0; lvl = lo
    while lvl <= hi + 1e-6:
        layer = 'C-TOPO-MAJR' if abs(lvl % 5) < 1e-6 else ('C-TOPO-MINR' if abs(lvl % 1) < 1e-6 else 'C-TOPO-HALF')
        for arr in cg.lines(lvl):
            if len(arr) < 3: continue
            ls = LineString(arr).simplify(0.4)
            if ls.length < 15: continue
            pts = list(ls.coords); pl = msp.add_lwpolyline(pts, dxfattribs={'layer': layer, 'elevation': float(lvl)})
            if pts[0] == pts[-1]: pl.close(True)
            n_ctr += 1
        lvl += 0.5
    # terrain mesh 5 ft
    step = 5; tm = MeshBuilder()
    gx = np.arange(x0, x1 + 1, step); gy = np.arange(y0, y1 + 1, step)
    gi = np.clip(((gx - x0) // 2).astype(int), 0, nx2 - 1); gj = np.clip(((gy - y0) // 2).astype(int), 0, ny2 - 1)
    tz = dtm_s[np.ix_(gj, gi)]
    W_ = len(gx)
    tm.add_vertices([(float(gx[b]), float(gy[a]), float(tz[a, b])) for a in range(len(gy)) for b in range(W_)])
    for a in range(len(gy) - 1):
        for b in range(W_ - 1): tm.faces.append((a * W_ + b, a * W_ + b + 1, (a + 1) * W_ + b + 1, (a + 1) * W_ + b))
    tm.render_mesh(msp, dxfattribs={'layer': 'C-TOPO-MESH-3D'})
    for b in buildings:
        msp.add_lwpolyline(list(b['poly'].exterior.coords), close=True, dxfattribs={'layer': 'A-BLDG-FTPT', 'elevation': b['base']})
        b['mesh'].render_mesh(msp, dxfattribs={'layer': 'A-BLDG-ROOF-3D'})
        c = b['poly'].centroid
        msp.add_text(f"{b['area']:.0f} sf  FFE~{b['base']+1:.1f}  EAVE {b['eave']-b['base']:.0f}'  RIDGE {b['ridge']-b['base']:.0f}'", height=2.5, dxfattribs={'layer': 'A-BLDG-ANNO'}).set_placement((c.x, c.y), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    for t in trees:
        msp.add_circle((t['x'], t['y']), t['r'], dxfattribs={'layer': 'L-PLNT-TREE', 'elevation': t['z']})
        msp.add_text(f"{t['h']:.0f}'", height=2, dxfattribs={'layer': 'L-PLNT-ANNO'}).set_placement((t['x'] + 1, t['y'] + 1))
    for w in waters:
        msp.add_lwpolyline(list(w['poly'].exterior.coords), close=True, dxfattribs={'layer': 'C-WATR-LIDAR', 'elevation': w['level'] if not math.isnan(w['level']) else 0})
        c = w['poly'].centroid
        msp.add_text(f"LIDAR NO-RETURN AREA {w['area_sf']/43560:.2f} AC  WSE(2018)~{w['level']:.1f} FT", height=4, dxfattribs={'layer': 'C-WATR-ANNO'}).set_placement((c.x, c.y), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    for p, g in wat_all:
        gg = g.intersection(zone)
        for pp in (list(gg.geoms) if hasattr(gg, 'geoms') else [gg]):
            if pp.geom_type == 'Polygon' and not pp.is_empty: msp.add_lwpolyline(list(pp.exterior.coords), close=True, dxfattribs={'layer': 'C-WATR-OVERTURE'})
    for p, g in seg_all:
        gg = g.intersection(zone)
        for ls in (list(gg.geoms) if hasattr(gg, 'geoms') else [gg]):
            if ls.geom_type == 'LineString' and not ls.is_empty: msp.add_lwpolyline(list(ls.coords), dxfattribs={'layer': 'C-ROAD-CNTR'})
    msp.add_lwpolyline(list(zone.exterior.coords), close=True, dxfattribs={'layer': 'G-ANNO-ZONE'})
    if zone.contains(shapely.Point(TARGET)):
        msp.add_circle(TARGET, 40, dxfattribs={'layer': 'G-ANNO-TRGT'})
    note = (f"FOCUS ZONE: {zc['title'].upper()}\\PGENERATED {datetime.date.today()} FROM USGS 3DEP LIDAR FL_Peninsular_Lake_2018 (PUBLIC DOMAIN) + OVERTURE MAPS 2026-09-23.1 (ODbL)\\P"
            "CRS NAD83 / FLORIDA EAST ftUS (EPSG:2236, CIVIL 3D FL83-EF); ELEVATIONS NAVD88 FT\\P"
            "CONTOURS 0.5 FT FROM 2 FT GROUND GRID (GAUSSIAN 1 CELL); LIDAR RMSEz ~0.33 FT SO 0.5 FT CONTOURS ARE INDICATIVE\\P"
            "ROOFS: 1 FT LIDAR SURFACE INSIDE EACH FOOTPRINT (MESH); WALLS DROP TO 10TH-PERCENTILE GROUND; TREES INSIDE FOOTPRINTS APPEAR AS ROOF\\P"
            "TREES: CANOPY-HEIGHT LOCAL MAXIMA >12 FT, CIRCLE RADIUS = CROWN AT HALF HEIGHT (APPROX)\\P"
            "WATER: LIDAR NO-RETURN AREAS (2018 WATER SURFACE); WSE = MEDIAN SHORE GROUND ELEVATION\\P"
            "CONCEPT GRADE - NOT A SURVEY. NO PARCEL LINES.")
    msp.add_mtext(note, dxfattribs={'layer': 'G-ANNO-NOTE', 'char_height': 4, 'width': 600}).set_location((x0 + 10, y1 - 10))
    dxf_path = f'{zdir}/sausage_castle_{zname}_focus_EPSG2236_ftUS.dxf'; doc.saveas(dxf_path)
    log(zname, 'DXF', os.path.getsize(dxf_path) // 1024, 'KB contours', n_ctr)

    # ---- grids + points
    with gzip.open(f'{zdir}/{zname}_dsm_1ft.asc.gz', 'wt') as f:
        f.write(f"ncols {nx1}\nnrows {ny1}\nxllcorner {x0}\nyllcorner {y0}\ncellsize 1\nNODATA_value -9999\n")
        for j in range(ny1 - 1, -1, -1): f.write(' '.join(f"{v:.2f}" for v in dsm[j]) + '\n')
    with gzip.open(f'{zdir}/{zname}_dtm_2ft.asc.gz', 'wt') as f:
        f.write(f"ncols {nx2}\nnrows {ny2}\nxllcorner {x0}\nyllcorner {y0}\ncellsize 2\nNODATA_value -9999\n")
        for j in range(ny2 - 1, -1, -1): f.write(' '.join(f"{v:.2f}" for v in np.where(has_ground[j], dtm_raw[j], dtm[j])) + '\n')
    with gzip.open(f'{zdir}/{zname}_ground_pts_2ft_PNEZD.csv.gz', 'wt') as f:
        f.write('# P,N,E,Z,D  PNEZD comma delimited; N/E ftUS EPSG:2236; Z NAVD88 ft\n'); k = 0
        for j in range(ny2):
            for i in range(nx2):
                if has_ground[j, i]: k += 1; f.write(f"{k},{y0 + j*2 + 1:.1f},{x0 + i*2 + 1:.1f},{dtm_raw[j, i]:.2f},GRND\n")
    # ---- preview
    fig, ax = plt.subplots(figsize=(13, 13 * ny1 / nx1), dpi=170); ext = [x0, x1, y0, y1]
    ax.imshow(hillshade(dsm, 1), cmap='gray', extent=ext, origin='lower', vmin=-0.2, vmax=1.1)
    ax.imshow(np.ma.masked_less(chm, 8), cmap='YlGn', extent=ext, origin='lower', alpha=0.3, vmin=8, vmax=60)
    cs = ax.contour(xs2, ys2, dtm_s, levels=np.arange(math.floor(lo), math.ceil(hi) + 1, 1), colors='#b5651d', linewidths=0.35, alpha=0.9)
    ax.clabel(cs, fmt='%d', fontsize=4, inline=True)
    for w in waters: ax.add_patch(MPoly(list(w['poly'].exterior.coords), closed=True, fc='#4aa3df', ec='#1f5f8b', alpha=0.55, lw=0.8)); c = w['poly'].centroid; ax.text(c.x, c.y, f"WSE {w['level']:.1f} ft", fontsize=6, ha='center', color='navy')
    for b in buildings: ax.add_patch(MPoly(list(b['poly'].exterior.coords), closed=True, fc='none', ec='red', lw=1.0)); c = b['poly'].centroid; ax.text(c.x, c.y - 12, f"{b['area']:.0f} sf, ridge {b['ridge']-b['base']:.0f} ft", fontsize=4.5, ha='center', color='darkred')
    for t in trees: ax.add_patch(Circle((t['x'], t['y']), t['r'], fc='none', ec='green', lw=0.3, alpha=0.7))
    for p, g in seg_all:
        gg = g.intersection(zone)
        for ls in (list(gg.geoms) if hasattr(gg, 'geoms') else [gg]):
            if ls.geom_type == 'LineString' and not ls.is_empty: xx, yy = ls.xy; ax.plot(xx, yy, color='black', lw=1.0)
    if zone.contains(shapely.Point(TARGET)): ax.add_patch(Circle(TARGET, 40, fc='none', ec='magenta', lw=1.5))
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.tick_params(labelsize=6)
    ax.set_title(f"{zc['title']}: 1 ft lidar surface hillshade, 1 ft contours, footprints (red), trees (green), lidar water (blue)\nEPSG:2236 ftUS, NAVD88 ft; USGS 3DEP 2018", fontsize=8)
    fig.savefig(f'{zdir}/{zname}_preview.png', bbox_inches='tight'); plt.close(fig)
    from PIL import Image; im = Image.open(f'{zdir}/{zname}_preview.png').convert('RGB'); im.save(f'{zdir}/{zname}_preview.jpg', quality=90, optimize=True); os.remove(f'{zdir}/{zname}_preview.png')
    meta = dict(zone=zname, title=zc['title'], bbox_ftUS=zc['bbox'], crs='EPSG:2236 ftUS', vertical='NAVD88 ft', points=int(len(zz)), ground_points=int(gm.sum()),
                dtm_ft=[float(np.nanmin(dtm_raw)), float(np.nanmax(dtm_raw))], contours=n_ctr, trees=len(trees),
                water=[dict(area_ac=round(w['area_sf']/43560, 2), wse_ft=round(w['level'], 1), note='hydro-flattened to WSE in DTM/DSM', centroid=[round(w['poly'].centroid.x), round(w['poly'].centroid.y)]) for w in waters],
                buildings=[dict(area_sf=round(b['area']), base_ft=round(b['base'], 1), eave_ft=round(b['eave'] - b['base'], 1), ridge_ft=round(b['ridge'] - b['base'], 1), centroid=[round(b['poly'].centroid.x), round(b['poly'].centroid.y)]) for b in sorted(buildings, key=lambda b: -b['area'])])
    json.dump(meta, open(f'{zdir}/{zname}_metadata.json', 'w'), indent=1)
    log(zname, 'done')
log('all done')
