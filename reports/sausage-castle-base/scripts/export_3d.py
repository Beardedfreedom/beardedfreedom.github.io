#!/usr/bin/env python3
"""Export heightmaps (RGB-encoded 16-bit PNG) and land-cover color textures for a three.js viewer.
Zones: site (6 ft), house (1 ft), lakes (2 ft). Surface (DSM) and bare earth (DTM), hydro-flattened."""
import json, math, os, time
import numpy as np, laspy, shapely, contourpy
from pyproj import Transformer
from shapely.geometry import shape, box, Polygon, MultiPolygon
from shapely.ops import transform as shp_transform
from scipy import ndimage
from PIL import Image
t0 = time.time()
def log(*a): print(f"[{time.time()-t0:5.0f}s]", *a, flush=True)
OUT = '/home/user/beardedfreedom.github.io/reports/sausage-castle-base/viewer/data'
M2FT = 1 / 0.30480060960121924
to_sp = Transformer.from_crs('EPSG:3857', 'EPSG:2236', always_xy=True); ll_to_sp = Transformer.from_crs('EPSG:4326', 'EPSG:2236', always_xy=True)
def ll2sp(g): return shp_transform(lambda x, y, z=None: ll_to_sp.transform(x, y), g)
ZONES = {'site': dict(title='Whole site (328 ac)', bbox=(425120, 1576977, 428670, 1580997), cell=6),
         'house': dict(title='Main house and compound', bbox=(426050, 1577150, 427050, 1578150), cell=1),
         'lakes': dict(title='Lakes and loop track', bbox=(425750, 1578350, 427050, 1579550), cell=2)}
las = laspy.read('sausage_site.laz'); cls = np.asarray(las.classification); keep = ~np.isin(cls, [7, 18])
xm, ym, zm = np.asarray(las.x)[keep], np.asarray(las.y)[keep], np.asarray(las.z)[keep]; cls = cls[keep]; rn = np.asarray(las.return_number)[keep]; del las
X = np.empty(len(xm)); Y = np.empty(len(ym))
for i in range(0, len(xm), 4_000_000): X[i:i+4_000_000], Y[i:i+4_000_000] = to_sp.transform(xm[i:i+4_000_000], ym[i:i+4_000_000])
Z = (zm * M2FT).astype(np.float32); del xm, ym, zm; log('points', len(Z))
bld_all = [ll2sp(shape(f['geometry'])) for f in json.load(open('astatula_building.geojson'))['features']]
seg_all = [ll2sp(shape(f['geometry'])) for f in json.load(open('astatula_segment.geojson'))['features']]

def grid_reduce(ii, zz, n, how):
    g = np.full(n, np.nan, np.float32)
    if len(ii) == 0: return g
    o = np.argsort(ii, kind='stable'); ii, zz = ii[o], zz[o]; st = np.flatnonzero(np.r_[True, ii[1:] != ii[:-1]])
    g[ii[st]] = np.maximum.reduceat(zz, st) if how == 'max' else np.add.reduceat(zz, st) / np.diff(np.r_[st, len(zz)])
    return g
def fill_nearest(g):
    m = np.isnan(g)
    return g if not m.any() else g[tuple(ndimage.distance_transform_edt(m, return_distances=False, return_indices=True))]
def hillshade(dsm, cell, az=315, alt=45):
    dy, dx = np.gradient(dsm, cell); slope = np.arctan(np.hypot(dx, dy)); aspect = np.arctan2(-dx, dy)
    return np.clip(np.sin(math.radians(alt)) * np.cos(slope) + np.cos(math.radians(alt)) * np.sin(slope) * np.cos(math.radians(az) - aspect), 0, 1)
def enc_png(arr, path):
    """RGB PNG: value = (R*256+G) * 0.01 ft + zmin"""
    zmin = float(np.floor(arr.min())); q = np.clip(np.round((arr - zmin) / 0.01), 0, 65535).astype(np.uint16)
    rgb = np.zeros(arr.shape + (3,), np.uint8); rgb[..., 0] = q >> 8; rgb[..., 1] = q & 255
    Image.fromarray(rgb[::-1], 'RGB').save(path, optimize=True)      # row 0 = north (top)
    return zmin
meta = dict(crs='EPSG:2236 NAD83 / Florida East (ftUS)', vertical='NAVD88 ft', source='USGS 3DEP FL_Peninsular_Lake_2018 + Overture Maps 2026-09-23.1', zones={})
for zn, zc in ZONES.items():
    x0, y0, x1, y1 = zc['bbox']; c = zc['cell']; nx, ny = int((x1 - x0) / c), int((y1 - y0) / c)
    m = (X >= x0) & (X < x0 + nx * c) & (Y >= y0) & (Y < y0 + ny * c)
    zx, zy, zz, zc_, zr = X[m], Y[m], Z[m], cls[m], rn[m]
    i = ((zx - x0) / c).astype(np.int64); j = ((zy - y0) / c).astype(np.int64); idx = j * nx + i
    dsm = grid_reduce(idx[zr == 1], zz[zr == 1], nx * ny, 'max').reshape(ny, nx); dsm_any = grid_reduce(idx, zz, nx * ny, 'max').reshape(ny, nx)
    dsm = np.where(np.isnan(dsm), dsm_any, dsm)
    g = zc_ == 2; dtm_raw = grid_reduce(idx[g], zz[g], nx * ny, 'mean').reshape(ny, nx); has_g = ~np.isnan(dtm_raw)
    cnt = np.bincount(idx, minlength=nx * ny).reshape(ny, nx)
    # water: no-return cells, cleaned, >= 3000 sq ft
    it = max(1, int(round(4 / c)))
    wm = ndimage.binary_closing(ndimage.binary_opening(cnt == 0, iterations=it), iterations=it + 1)
    lab, nl = ndimage.label(wm); water = np.zeros((ny, nx), bool); waters = []
    dtm = fill_nearest(dtm_raw)
    for k in range(1, nl + 1):
        cells = lab == k
        if cells.sum() * c * c < 3000: continue
        lvl = float('nan')
        for d in (2, 4, 8, 14):
            ring = ndimage.binary_dilation(cells, iterations=max(1, int(d / c))) & ~ndimage.binary_dilation(cells, iterations=1) & has_g
            if ring.sum() >= 30: lvl = float(np.percentile(dtm_raw[ring], 25)); break
        if math.isnan(lvl): lvl = float(np.median(dtm[ndimage.binary_dilation(cells, iterations=2) & ~cells]))
        dtm[cells] = lvl; water |= cells; waters.append((cells.sum() * c * c / 43560, lvl))
    dsm = fill_nearest(dsm); dsm = ndimage.median_filter(dsm, size=3) if c <= 2 else dsm; dsm[water] = dtm[water]
    dtm_s = ndimage.gaussian_filter(dtm, max(0.6, 2 / c)); dtm_s[water] = dtm[water]
    dsm = np.maximum(dsm, dtm_s - 0.5)
    chm = np.clip(dsm - dtm_s, 0, None)
    # masks
    jj, ii = np.mgrid[0:ny, 0:nx]; cx = (x0 + (ii + 0.5) * c).ravel(); cy = (y0 + (jj + 0.5) * c).ravel()
    zone = box(x0, y0, x0 + nx * c, y0 + ny * c)
    bmask = np.zeros(nx * ny, bool)
    for gb in bld_all:
        if not gb.intersects(zone): continue
        for p in (list(gb.geoms) if isinstance(gb, MultiPolygon) else [gb]): bmask |= shapely.contains_xy(p.buffer(0.5), cx, cy)
    rmask = np.zeros(nx * ny, bool)
    for gs in seg_all:
        if not gs.intersects(zone): continue
        rmask |= shapely.contains_xy(gs.buffer(9), cx, cy)
    bmask = bmask.reshape(ny, nx); rmask = rmask.reshape(ny, nx) & ~bmask
    # color: land cover from canopy height, buildings, roads, water; lightly shaded
    col = np.zeros((ny, nx, 3), np.float32)
    grass = np.array([0.66, 0.68, 0.42]); shrub = np.array([0.45, 0.60, 0.33]); tree_lo = np.array([0.24, 0.45, 0.22]); tree_hi = np.array([0.12, 0.30, 0.13])
    t = np.clip(chm / 60, 0, 1)[..., None]
    col[:] = grass
    col = np.where((chm > 1.5)[..., None], shrub, col); col = np.where((chm > 8)[..., None], tree_lo * (1 - t) + tree_hi * t, col)
    bare = (chm < 0.3) & (hillshade(dtm_s, c) > 0)  # flat mown/bare areas slightly sandier
    col = np.where(bare[..., None], np.array([0.72, 0.70, 0.50]), col)
    col = np.where(rmask[..., None], np.array([0.42, 0.40, 0.38]), col)
    col = np.where(bmask[..., None], np.array([0.62, 0.30, 0.26]), col)
    col = np.where(water[..., None], np.array([0.20, 0.42, 0.62]), col)
    hs = hillshade(dsm, c)[..., None]
    col = np.clip(col * (0.55 + 0.6 * hs), 0, 1)
    Image.fromarray((col[::-1] * 255).astype(np.uint8), 'RGB').save(f'{OUT}/{zn}_color.jpg', quality=88, optimize=True)
    zmin_s = enc_png(dsm, f'{OUT}/{zn}_surface.png'); zmin_g = enc_png(dtm_s, f'{OUT}/{zn}_ground.png')
    meta['zones'][zn] = dict(title=zc['title'], cell_ft=c, nx=nx, ny=ny, x0=x0, y0=y0, width_ft=nx * c, height_ft=ny * c,
                             surface=dict(file=f'{zn}_surface.png', zmin=zmin_s, scale=0.01), ground=dict(file=f'{zn}_ground.png', zmin=zmin_g, scale=0.01),
                             color=f'{zn}_color.jpg', z_range=[float(dtm_s.min()), float(dsm.max())], water=[dict(acres=round(a, 2), wse=round(l, 1)) for a, l in waters],
                             target=list(ll_to_sp.transform(-81.715188, 28.672523)) if zn != 'lakes' else None)
    log(zn, f'{nx}x{ny} @ {c} ft, pts {len(zz):,}, water {len(waters)}, z {dtm_s.min():.1f}-{dsm.max():.1f}', {k: os.path.getsize(f'{OUT}/{zn}_{k}') // 1024 for k in ('surface.png', 'ground.png', 'color.jpg')}, 'KB')
json.dump(meta, open(f'{OUT}/meta.json', 'w'), indent=1); log('done')
