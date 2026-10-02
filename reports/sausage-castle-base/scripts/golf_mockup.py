#!/usr/bin/env python3
"""Gator Greens mock-up renders: stills and a drone flyover of the polished course (Blender 5, Cycles).

Inputs from scripts/golf_polish.py (masterplan/golf/polish/): terrain.npz (graded 2 ft grid) and
surface_0p5ft.jpg (painted surface map), design.json (ponds, tees, pins). Also the lidar trees
(game/data/world.json), the lidar buildings (base DXF) and the 3 ft DTM for the land around.

Scene: graded terrain with the surface map, coarser lidar ground to the horizon, water on the ponds with
reeds and lily pads, live oaks, slash pines, cypress and cabbage palms (lidar positions and heights; the
course corridors are cleared), the Castle and the other buildings, flags, tee markers and benches, a
physical sky with procedural clouds. Lighting presets: day and golden hour.

Usage (pip bpy 5.x):
  python3 scripts/golf_mockup.py --views aerial,drone_day,drone_golden,hole13,tee17,green2,finish18
  python3 scripts/golf_mockup.py --flyover 288 --fps 12 --res 1280x720 --samples 16   # frames to mockup/flyover/
  python3 scripts/golf_mockup.py --polish polish_estate --views estate,estate_golden,estate_top --res 2560x1440
      # the whole estate (needs golf_polish.py --extent estate first): the Castle, all 18 holes and the lakes,
      # each also saved with labels (holes, the Castle, the lakes, the assumed estate edge)
Options: --samples, --res, --preview (quarter size, 8 samples), --start (resume a flyover), --polish (ground folder).
Outputs: masterplan/golf/mockup/*.jpg and mockup/flyover/f*.png.
"""
import argparse, json, math, os, sys
import numpy as np
import bpy
import ezdxf
from PIL import Image

ap = argparse.ArgumentParser(); ap.add_argument('--base', default=os.path.join(os.path.dirname(__file__), '..'))
ap.add_argument('--views', default=''); ap.add_argument('--samples', type=int, default=128); ap.add_argument('--res', default='1920x1080')
ap.add_argument('--preview', action='store_true'); ap.add_argument('--flyover', type=int, default=0); ap.add_argument('--fps', type=int, default=12)
ap.add_argument('--start', type=int, default=0); ap.add_argument('--end', type=int, default=0); ap.add_argument('--out', default=None); ap.add_argument('--seed', type=int, default=11)
ap.add_argument('--polish', default='polish', help='ground folder under masterplan/golf: polish (the course) or polish_estate (the whole estate)')
args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
B = os.path.abspath(args.base); G = f'{B}/masterplan/golf'; PO = f'{G}/{args.polish}'; OUT = os.path.abspath(args.out) if args.out else f'{G}/mockup'; os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(args.seed); FT = 0.3048
T = np.load(f'{PO}/terrain.npz'); Z = T['Z'].astype(np.float64); X0, Y0, X1, Y1, g = float(T['X0']), float(T['Y0']), float(T['X1']), float(T['Y1']), float(T['grid'])
D = json.load(open(f'{G}/polish/design.json')); world = json.load(open(f'{B}/game/data/world.json'))
CX, CY, ZB = (X0 + X1) / 2, (Y0 + Y1) / 2, 64.0
def M(x, y, z): return ((x - CX) * FT, (y - CY) * FT, (z - ZB) * FT)
nyg, nxg = Z.shape
def zg(x, y):   # graded height (bilinear on the 2 ft grid), lidar outside
    fi, fj = (x - X0) / g, (y - Y0) / g
    if 0 <= fi < nxg - 1 and 0 <= fj < nyg - 1:
        i0, j0 = int(fi), int(fj); ti, tj = fi - i0, fj - j0
        return float(Z[j0, i0] * (1 - ti) * (1 - tj) + Z[j0, i0 + 1] * ti * (1 - tj) + Z[j0 + 1, i0] * (1 - ti) * tj + Z[j0 + 1, i0 + 1] * ti * tj)
    return zd(x, y)
import gzip
with gzip.open(f'{B}/sausage_castle_dtm_3ft_EPSG2236.asc.gz', 'rt') as fh:
    hdr = {}
    for _ in range(6):
        k, v = fh.readline().split(); hdr[k.lower()] = float(v)
    dtm = np.loadtxt(fh, dtype=np.float32)
dtm = np.where(dtm < -9000, np.nanmedian(np.where(dtm < -9000, np.nan, dtm)), dtm)
def zd_arr(X, Y):
    fi = (X - hdr['xllcorner']) / hdr['cellsize'] - 0.5; fj = (hdr['nrows'] - 1) - ((Y - hdr['yllcorner']) / hdr['cellsize'] - 0.5)
    i0 = np.clip(np.floor(fi), 0, dtm.shape[1] - 2).astype(int); j0 = np.clip(np.floor(fj), 0, dtm.shape[0] - 2).astype(int); ti = np.clip(fi - i0, 0, 1); tj = np.clip(fj - j0, 0, 1)
    return dtm[j0, i0] * (1 - ti) * (1 - tj) + dtm[j0, i0 + 1] * ti * (1 - tj) + dtm[j0 + 1, i0] * (1 - ti) * tj + dtm[j0 + 1, i0 + 1] * ti * tj
def zd(x, y): return float(zd_arr(np.array([x]), np.array([y]))[0])

# ------------------------------------------------------------------ scene
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.02
sc.cycles.use_denoising = True; sc.cycles.max_bounces = 5; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transparent_max_bounces = 4
try: sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception: pass
def srgb(h): return tuple(((int(h[i:i + 2], 16) / 255 + 0.055) / 1.055) ** 2.4 if int(h[i:i + 2], 16) / 255 > 0.04045 else int(h[i:i + 2], 16) / 255 / 12.92 for i in (1, 3, 5))
def mat(name, hexc, rough=0.8, metal=0.0, spec=None, emit=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*srgb(hexc), 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if spec is not None: b.inputs['Specular IOR Level'].default_value = spec
    if emit: b.inputs['Emission Color'].default_value = (*srgb(hexc), 1); b.inputs['Emission Strength'].default_value = emit
    return m
def mesh_from(name, V, F, material=None, smooth=True):
    me = bpy.data.meshes.new(name); me.from_pydata(V, [], F); me.update()
    if material: me.materials.append(material)
    if smooth: me.shade_smooth()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob); return ob

# near terrain: graded grid + painted surface map
xs = X0 + np.arange(nxg) * g; ys = Y0 + np.arange(nyg) * g; GX, GY = np.meshgrid(xs, ys)
V = np.stack([(GX - CX) * FT, (GY - CY) * FT, (Z - ZB) * FT], -1).reshape(-1, 3)
ii = np.arange(nyg - 1)[:, None] * nxg + np.arange(nxg - 1)[None, :]; F = np.stack([ii, ii + 1, ii + nxg + 1, ii + nxg], -1).reshape(-1, 4)
me = bpy.data.meshes.new('terrain'); me.vertices.add(len(V)); me.vertices.foreach_set('co', V.astype(np.float32).ravel())
me.loops.add(F.size); me.loops.foreach_set('vertex_index', F.astype(np.int32).ravel()); me.polygons.add(len(F)); me.polygons.foreach_set('loop_start', (np.arange(len(F)) * 4).astype(np.int32))
me.update(calc_edges=True)
uvv = np.stack([(GX - X0) / (X1 - X0), (GY - Y0) / (Y1 - Y0)], -1).reshape(-1, 2); uv = me.uv_layers.new(name='UVMap'); uv.data.foreach_set('uv', uvv[F.ravel()].astype(np.float32).ravel())
me.shade_smooth()
tm = bpy.data.materials.new('surface'); tm.use_nodes = True; nt = tm.node_tree; bs = nt.nodes['Principled BSDF']
im = nt.nodes.new('ShaderNodeTexImage'); im.image = bpy.data.images.load(f'{PO}/surface_0p5ft.jpg'); im.interpolation = 'Cubic'; im.extension = 'EXTEND'
nt.links.new(im.outputs['Color'], bs.inputs['Base Color']); bs.inputs['Roughness'].default_value = 0.86; bs.inputs['Specular IOR Level'].default_value = 0.3
nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 900.0; nz.inputs['Detail'].default_value = 6.0
bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.25; bump.inputs['Distance'].default_value = 0.01
nt.links.new(nz.outputs['Fac'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], bs.inputs['Normal'])
me.materials.append(tm); terrain = bpy.data.objects.new('terrain', me); sc.collection.objects.link(terrain)
print('terrain', len(V), 'verts', flush=True)

# far ground to the horizon, lidar coloured from the land-cover map
s_ = world['site']; lc = np.asarray(Image.open(f'{B}/viewer/data/site_color.jpg').convert('RGB'), np.float32) / 255.0
fs = 12.0; pad = 3200; fx = np.arange(X0 - pad, X1 + pad + fs, fs); fy = np.arange(Y0 - pad, Y1 + pad + fs, fs); FX, FY = np.meshgrid(fx, fy); FZ = zd_arr(FX, FY) - 0.4
inside = (FX > X0 + 2) & (FX < X1 - 2) & (FY > Y0 + 2) & (FY < Y1 - 2)
FZ = np.where(inside, FZ - 3.0, FZ)                                                       # tuck under the near terrain
Vf = np.stack([(FX - CX) * FT, (FY - CY) * FT, (FZ - ZB) * FT], -1).reshape(-1, 3); nfx = len(fx)
jj = np.arange(len(fy) - 1)[:, None] * nfx + np.arange(nfx - 1)[None, :]; Ff = np.stack([jj, jj + 1, jj + nfx + 1, jj + nfx], -1).reshape(-1, 4)
far = bpy.data.meshes.new('far'); far.vertices.add(len(Vf)); far.vertices.foreach_set('co', Vf.astype(np.float32).ravel()); far.loops.add(Ff.size); far.loops.foreach_set('vertex_index', Ff.astype(np.int32).ravel())
far.polygons.add(len(Ff)); far.polygons.foreach_set('loop_start', (np.arange(len(Ff)) * 4).astype(np.int32)); far.update(calc_edges=True)
ci = ((FX - s_['x0']) / s_['w'] * lc.shape[1]).astype(int).clip(0, lc.shape[1] - 1); cj = ((s_['y0'] + s_['h'] - FY) / s_['h'] * lc.shape[0]).astype(int).clip(0, lc.shape[0] - 1)
cols = lc[cj, ci].reshape(-1, 3); offsite = ((FX < s_['x0']) | (FX > s_['x0'] + s_['w']) | (FY < s_['y0']) | (FY > s_['y0'] + s_['h'])).ravel()
from scipy.ndimage import gaussian_filter as _gf, map_coordinates as _mc
_wr = np.random.default_rng(args.seed + 101); _wg = 80.0; _wx0, _wy0 = fx[0], fy[0]                # woods and fields beyond the lidar site (a smooth noise field)
_wn = _gf(_wr.random((int((fy[-1] - fy[0]) / _wg) + 3, int((fx[-1] - fx[0]) / _wg) + 3)), 3.0) * 0.7 + _gf(_wr.random((int((fy[-1] - fy[0]) / _wg) + 3, int((fx[-1] - fx[0]) / _wg) + 3)), 1.2) * 0.3
_wn = (_wn - _wn.mean()) / (_wn.std() + 1e-9)
def woods(X, Y): return np.clip((_mc(_wn, [(np.asarray(Y) - _wy0) / _wg, (np.asarray(X) - _wx0) / _wg], order=1, mode='nearest') + 0.15) / 0.7, 0, 1)
_wv = woods(FX.ravel(), FY.ravel())[:, None]; _tex = np.clip(0.5 + 0.25 * _gf(_wr.standard_normal(FX.shape), 1.0).ravel(), 0, 1)[:, None]
_off = np.array([0.62, 0.62, 0.40]) * (1 - _tex) + np.array([0.52, 0.56, 0.34]) * _tex                     # Bahia pasture
_off = _off * (1 - _wv) + (np.array([0.36, 0.32, 0.22]) * (1 - _tex) + np.array([0.30, 0.34, 0.21]) * _tex) * _wv   # woodland floor
cols[offsite] = _off[offsite]
ca = far.color_attributes.new('Cover', 'FLOAT_COLOR', 'POINT'); ca.data.foreach_set('color', np.concatenate([cols ** 2.2, np.ones((len(cols), 1))], 1).astype(np.float32).ravel())
fm = bpy.data.materials.new('far'); fm.use_nodes = True; fa = fm.node_tree.nodes.new('ShaderNodeAttribute'); fa.attribute_name = 'Cover'
fm.node_tree.links.new(fa.outputs['Color'], fm.node_tree.nodes['Principled BSDF'].inputs['Base Color']); fm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.92
far.materials.append(fm); far.shade_smooth(); farob = bpy.data.objects.new('far', far); sc.collection.objects.link(farob)
bpy.ops.mesh.primitive_plane_add(size=40000, location=M(CX, CY, float(np.percentile(dtm, 5)) - 2.0)); bpy.context.active_object.data.materials.append(mat('horizon', '#5a6e40', 0.95))

# ------------------------------------------------------------------ water, reeds, lily pads
water = bpy.data.materials.new('water'); water.use_nodes = True; wn = water.node_tree; wb = wn.nodes['Principled BSDF']
wb.inputs['Base Color'].default_value = (0.035, 0.075, 0.068, 1); wb.inputs['Roughness'].default_value = 0.05; wb.inputs['IOR'].default_value = 1.33; wb.inputs['Specular IOR Level'].default_value = 0.6
wnz = wn.nodes.new('ShaderNodeTexNoise'); wnz.inputs['Scale'].default_value = 3.0; wnz.inputs['Detail'].default_value = 4.0; wbump = wn.nodes.new('ShaderNodeBump'); wbump.inputs['Strength'].default_value = 0.06
wn.links.new(wnz.outputs['Fac'], wbump.inputs['Height']); wn.links.new(wbump.outputs['Normal'], wb.inputs['Normal'])
reed_m = mat('reed', '#7d8a45', 0.7); pad_m = mat('lilypad', '#3f6b2a', 0.5); flower_m = mat('lily', '#f4eef0', 0.4)
def reed_clump():
    V, F = [], []
    for k in range(28):
        a = rng.uniform(0, 2 * np.pi); r = rng.uniform(0, 0.25); x, y = r * math.cos(a), r * math.sin(a); h = rng.uniform(0.8, 1.6); lean = rng.uniform(-0.25, 0.25); w = 0.012
        b = len(V); V += [(x - w, y, 0), (x + w, y, 0), (x + lean * math.cos(a), y + lean * math.sin(a), h)]; F.append((b, b + 1, b + 2))
    return V, F
rv, rf = reed_clump(); reed_proto = bpy.data.meshes.new('reed'); reed_proto.from_pydata(rv, [], rf); reed_proto.materials.append(reed_m)
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
from shapely.prepared import prep
n_reeds = 0
for h in D['holes']:
    if not h['pond']: continue
    poly = Polygon(h['pond']); wl = h['water_level_ft']; ring = list(poly.exterior.coords)
    ob = mesh_from(f'pond{h["n"]}', [M(x, y, wl) for x, y in ring[:-1]], [tuple(range(len(ring) - 1))], water, smooth=False)
    per = poly.exterior.length; start = rng.uniform(0, per)
    for d_ in np.arange(0, per * 0.45, 4.5):                       # reeds along about half of the shore
        p = poly.exterior.interpolate((start + d_) % per); c = poly.centroid; vx, vy = c.x - p.x, c.y - p.y; L = math.hypot(vx, vy) or 1
        x, y = p.x + vx / L * rng.uniform(0.5, 2.5), p.y + vy / L * rng.uniform(0.5, 2.5)
        r_ = bpy.data.objects.new('reed', reed_proto); sc.collection.objects.link(r_); r_.location = M(x, y, wl - 0.3); r_.rotation_euler = (0, 0, rng.uniform(0, 6.3)); s = rng.uniform(0.8, 1.3); r_.scale = (s, s, s); n_reeds += 1
    for k in range(14):                                             # lily pads near the edge
        p = poly.exterior.interpolate(rng.uniform(0, per)); c = poly.centroid; vx, vy = c.x - p.x, c.y - p.y; L = math.hypot(vx, vy) or 1; t = rng.uniform(3, 9)
        x, y = p.x + vx / L * t, p.y + vy / L * t
        bpy.ops.mesh.primitive_cylinder_add(vertices=14, radius=rng.uniform(0.18, 0.35), depth=0.01, location=M(x, y, wl + 0.03)); bpy.context.active_object.data.materials.append(pad_m)
        if rng.random() < 0.3:
            bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=4, radius=0.06, location=M(x, y, wl + 0.15)); bpy.context.active_object.data.materials.append(flower_m)
print('reeds', n_reeds, flush=True)

# ------------------------------------------------------------------ trees
def leaf_mat(name, cols):
    m = bpy.data.materials.new(name); m.use_nodes = True; t = m.node_tree; b = t.nodes['Principled BSDF']; oi = t.nodes.new('ShaderNodeObjectInfo'); cr = t.nodes.new('ShaderNodeValToRGB')
    cr.color_ramp.elements[0].color = (*srgb(cols[0]), 1); cr.color_ramp.elements[1].color = (*srgb(cols[2]), 1); e = cr.color_ramp.elements.new(0.5); e.color = (*srgb(cols[1]), 1)
    t.links.new(oi.outputs['Random'], cr.inputs['Fac']); t.links.new(cr.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.82
    vo = t.nodes.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 9.0; bp = t.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.9; bp.inputs['Distance'].default_value = 0.3
    t.links.new(vo.outputs['Distance'], bp.inputs['Height']); t.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    dk = t.nodes.new('ShaderNodeMix'); dk.data_type = 'RGBA'; dk.blend_type = 'MULTIPLY'; dk.inputs['Factor'].default_value = 0.35   # darker gaps between leaf clumps
    t.links.new(cr.outputs['Color'], dk.inputs['A']); t.links.new(vo.outputs['Distance'], dk.inputs['B']); t.links.new(dk.outputs['Result'], b.inputs['Base Color']); return m
oak_m = leaf_mat('oakleaf', ('#3d5e2a', '#4f7232', '#5f7d3a')); pine_m = leaf_mat('pineleaf', ('#35502b', '#425f30', '#536b36'))
cyp_m = leaf_mat('cypleaf', ('#4f6a33', '#5d7a3a', '#71884a')); palm_m = leaf_mat('palmleaf', ('#5b7a32', '#6c8a3a', '#7f9746'))
bark = mat('bark', '#5b4a3a', 0.9); palmbark = mat('palmbark', '#8b7a62', 0.9)
tex = bpy.data.textures.new('lumps', 'CLOUDS'); tex.noise_scale = 0.06; tex.noise_depth = 3
def blob_parts(centers, radii, mat_):
    parts = []
    for (x, y, z), r in zip(centers, radii):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r, location=(x, y, z)); o = bpy.context.active_object
        dm = o.modifiers.new('d', 'DISPLACE'); dm.texture = tex; dm.strength = r * 0.55; dm.mid_level = 0.5; bpy.ops.object.modifier_apply(modifier='d'); o.data.materials.append(mat_); parts.append(o)
    return parts
PROTO_R = {'oak': 0.62, 'pine': 0.2, 'cypress': 0.13, 'palm': 0.3}     # crown radius / height of each model as built
def make_tree(kind, k):
    """models in real proportions, height 1 (scaled uniformly by the lidar height, spread nudged to the lidar crown)"""
    r = np.random.default_rng(100 + k * 7 + len(kind) * 13); parts = []
    if kind == 'oak':                                   # live oak: short trunk, broad spreading crown of rounded masses
        bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.05, radius2=0.03, depth=0.45, location=(0, 0, 0.225)); parts.append(bpy.context.active_object); parts[-1].data.materials.append(bark)
        cs = []
        for _ in range(22):                              # a domed shell of leaf masses, wider than tall
            a_ = r.uniform(0, 2 * np.pi); rr = 0.5 * math.sqrt(r.uniform(0.15, 1.0)); cs.append((rr * math.cos(a_), rr * math.sin(a_), 0.5 + 0.28 * math.sqrt(max(0.0, 1 - (rr / 0.55) ** 2)) + r.uniform(-0.05, 0.04)))
        parts += blob_parts(cs, [r.uniform(0.11, 0.17) for _ in cs], oak_m)
    elif kind == 'pine':                                # slash pine: tall bare trunk, small high irregular crown
        bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.022, radius2=0.01, depth=0.86, location=(0, 0, 0.43)); parts.append(bpy.context.active_object); parts[-1].data.materials.append(bark)
        cs = [(r.uniform(-0.13, 0.13), r.uniform(-0.13, 0.13), r.uniform(0.72, 0.95)) for _ in range(11)]
        parts += blob_parts(cs, [r.uniform(0.045, 0.075) for _ in cs], pine_m)
    elif kind == 'cypress':                             # bald cypress: narrow spire
        bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.04, radius2=0.015, depth=0.4, location=(0, 0, 0.2)); parts.append(bpy.context.active_object); parts[-1].data.materials.append(bark)
        cs = [(r.uniform(-0.03, 0.03), r.uniform(-0.03, 0.03), z) for z in np.linspace(0.32, 0.9, 7)]
        parts += blob_parts(cs, [0.11 - 0.07 * (z - 0.32) for (_, _, z) in cs], cyp_m)
    else:                                               # cabbage palm: trunk and a fan of drooping fronds
        bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.025, depth=0.86, location=(0, 0, 0.43)); parts.append(bpy.context.active_object); parts[-1].data.materials.append(palmbark)
        V, F = [], []
        for j in range(16):
            a = j / 16 * 2 * np.pi + r.uniform(-0.1, 0.1); up = r.uniform(-0.15, 0.45); Lf = r.uniform(0.26, 0.34); ca_, sa = math.cos(a), math.sin(a)
            pts = [(0.0, 0.0), (Lf * 0.5, 0.05 + up * 0.15), (Lf, up * 0.3 - 0.1)]
            b0 = len(V)
            for t_, (d, zz) in enumerate(pts):
                w = 0.05 * (1 - t_ / 2.2) + 0.008
                V += [(d * ca_ - w * sa, d * sa + w * ca_, 0.88 + zz), (d * ca_ + w * sa, d * sa - w * ca_, 0.88 + zz)]
            F += [(b0, b0 + 1, b0 + 3, b0 + 2), (b0 + 2, b0 + 3, b0 + 5, b0 + 4)]
        me_ = bpy.data.meshes.new('fronds'); me_.from_pydata(V, [], F); me_.materials.append(palm_m); o = bpy.data.objects.new('fronds', me_); sc.collection.objects.link(o); parts.append(o)
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts: p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]; bpy.ops.object.join(); o = bpy.context.active_object; o.name = f'proto_{kind}{k}'; o.hide_render = True; o.hide_viewport = True
    for pl in o.data.polygons: pl.use_smooth = True
    co_ = np.zeros(len(o.data.vertices) * 3, np.float32); o.data.vertices.foreach_get('co', co_); co_ = co_.reshape(-1, 3)
    zs_ = co_[:, 2].max() - co_[:, 2].min(); co_[:, 2] -= co_[:, 2].min(); co_ /= zs_          # uniform: height 1, proportions kept
    o.data.vertices.foreach_set('co', co_.ravel()); o.data.update()
    return o.data
protos = {k: [make_tree(k, i) for i in range(3)] for k in ('oak', 'pine', 'cypress', 'palm')}
turf = prep(unary_union([Polygon(r_) for h in D['holes'] for r_ in h['rough']]).buffer(4))
paths = prep(unary_union([LineString(p).buffer(7) for p in D['cart_paths']]))
ponds = unary_union([Polygon(h['pond']) for h in D['holes'] if h['pond']])
if 'lakes' in T.files and int(T['lakes']) > 0:                                             # existing lakes (their beds are dug by golf_polish.py --extent estate)
    for w_ in world['water']:
        lp = Polygon(list(zip(w_['pts'][0::2], w_['pts'][1::2]))).buffer(0)
        if lp.intersects(ponds): continue
        ring = list(lp.exterior.coords)[:-1]; mesh_from('lake', [M(x, y, float(w_['wse']) + 0.1) for x, y in ring], [tuple(range(len(ring)))], water, smooth=False)
bx0, by0, bx1, by1 = X0 - 900, Y0 - 900, X1 + 900, Y1 + 900; ntree = 0
lakes_u = unary_union([Polygon(list(zip(w_['pts'][0::2], w_['pts'][1::2]))).buffer(0) for w_ in world['water']])
TREES = []
def place(kind, x, y, h, r):
    global ntree
    o = bpy.data.objects.new(kind, protos[kind][int(rng.integers(0, 3))]); sc.collection.objects.link(o); z = zg(x, y)
    f = float(np.clip(r / (PROTO_R[kind] * h), 0.8, 1.3)); o.location = M(x, y, z - 0.3); o.rotation_euler = (0, 0, rng.uniform(0, 2 * np.pi))
    o.scale = (h * f * FT, h * f * FT, h * FT); ntree += 1; TREES.append((o, x, y, PROTO_R[kind] * h * f, h))
for t in world['trees']:
    x, y, h, r, kind = t
    if not (bx0 < x < bx1 and by0 < y < by1) or turf.contains(Point(x, y)) or paths.contains(Point(x, y)) or lakes_u.contains(Point(x, y)): continue
    k = {0: 'oak', 1: 'pine', 2: 'cypress'}[kind]
    if k == 'cypress' and ponds.distance(Point(x, y)) > 80: k = 'oak'
    spread = {'oak': float(np.clip(max(r * 1.3, 0.42 * h), 8, 42)), 'pine': float(np.clip(0.2 * h, 5, 13)), 'cypress': float(np.clip(0.16 * h, 4, 10))}[k]
    place(k, x, y, h, spread)
for h in D['holes']:                                    # cabbage palms on the pond banks and by the tees
    if h['pond']:
        P_ = Polygon(h['pond'])
        for k in range(3):
            p = P_.exterior.interpolate(rng.uniform(0, P_.exterior.length)); c = P_.centroid; vx, vy = p.x - c.x, p.y - c.y; L = math.hypot(vx, vy) or 1
            place('palm', p.x + vx / L * rng.uniform(10, 16), p.y + vy / L * rng.uniform(10, 16), rng.uniform(22, 32), rng.uniform(9, 11))
for k in range(9):
    a = rng.uniform(0, 2 * np.pi); d_ = rng.uniform(60, 120); place('palm', D['clubhouse'][0] + d_ * math.cos(a), D['clubhouse'][1] + d_ * math.sin(a), rng.uniform(24, 34), 10)
_tr = np.random.default_rng(args.seed + 202); n_off = 0; sx0, sy0, sx1, sy1 = s_['x0'], s_['y0'], s_['x0'] + s_['w'], s_['y0'] + s_['h']
for yy in np.arange(sy0 - 2200, sy1 + 2200, 42.0):                                        # trees in those woods, beyond the lidar trees
    for xx in np.arange(sx0 - 2200, sx1 + 2200, 42.0):
        x, y = xx + _tr.uniform(-16, 16), yy + _tr.uniform(-16, 16)
        if sx0 - 30 < x < sx1 + 30 and sy0 - 30 < y < sy1 + 30: continue
        if _tr.random() > 0.92 * float(woods(np.array([x]), np.array([y]))[0]): continue
        k = 'pine' if _tr.random() < 0.3 else 'oak'; h = float(_tr.uniform(32, 64))
        o = bpy.data.objects.new(k, protos[k][int(_tr.integers(0, 3))]); sc.collection.objects.link(o); spread = float(np.clip(0.42 * h, 8, 30)) if k == 'oak' else float(np.clip(0.2 * h, 5, 13))
        f = float(np.clip(spread / (PROTO_R[k] * h), 0.8, 1.3)); o.location = M(x, y, zg(x, y) - 0.3); o.rotation_euler = (0, 0, _tr.uniform(0, 2 * np.pi)); o.scale = (h * f * FT, h * f * FT, h * FT)
        TREES.append((o, x, y, PROTO_R[k] * h * f, h)); n_off += 1
print('trees', ntree, '+', n_off, 'beyond the site', flush=True)

# ------------------------------------------------------------------ buildings (lidar meshes)
wall = mat('wall', '#c8b99a', 0.8); roof = mat('roof', '#3d3b38', 0.6)
base = ezdxf.readfile(f'{B}/sausage_castle_base_EPSG2236_ftUS.dxf').modelspace(); nb = 0
for e in base.query('MESH[layer=="A-BLDG-3D"]'):
    vv = [tuple(v) for v in e.vertices]; cx_, cy_ = np.mean([v[0] for v in vv]), np.mean([v[1] for v in vv])
    if not (bx0 < cx_ < bx1 and by0 < cy_ < by1): continue
    ob = mesh_from('bldg', [M(*v) for v in vv], [tuple(f) for f in e.faces], wall, smooth=False); ob.data.materials.append(roof)
    for p in ob.data.polygons: p.material_index = 1 if p.normal.z > 0.6 else 0
    nb += 1
print('buildings', nb, flush=True)

# ------------------------------------------------------------------ flags, tee markers, benches
pole_m = mat('pole', '#f4f1ea', 0.35); flag_m = mat('flag', '#ffc61a', 0.6); cup_m = mat('cup', '#111111', 0.5)
blue = mat('teeblue', '#2f6fd6', 0.4); red = mat('teered', '#d9342b', 0.4); wood = mat('wood', '#8a6a48', 0.8)
for h in D['holes']:
    px_, py_ = h['pin']; pz = zg(px_, py_); tx, ty = h['tee']; ux, uy = px_ - tx, py_ - ty; L = math.hypot(ux, uy); ux, uy = ux / L, uy / L
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.012, depth=2.13, location=M(px_, py_, pz + 3.5)); bpy.context.active_object.data.materials.append(pole_m)
    fv = [M(px_, py_, pz + 7.0), M(px_ + ux * 1.6, py_ + uy * 1.6, pz + 6.75), M(px_ + ux * 1.6, py_ + uy * 1.6, pz + 5.85), M(px_, py_, pz + 6.0)]
    mesh_from('flag', fv, [(0, 1, 2, 3)], flag_m, smooth=False)
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.054, depth=0.01, location=M(px_, py_, pz + 0.02)); bpy.context.active_object.data.materials.append(cup_m)
    for j, tp in enumerate(h['tees']):
        tpol = Polygon(tp); c = tpol.centroid; zt = zg(c.x, c.y); nx, ny = -uy, ux
        for s_ in (-1, 1):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=0.08, location=M(c.x + nx * 7 * s_ + ux * 4, c.y + ny * 7 * s_ + uy * 4, zt + 0.25)); bpy.context.active_object.data.materials.append(blue if j == 0 else red)
        if j == 0:
            bx, by = c.x - nx * 18 - ux * 4, c.y - ny * 18 - uy * 4; bz = zg(bx, by); ang = math.atan2(uy, ux)
            bpy.ops.mesh.primitive_cube_add(size=1, location=M(bx, by, bz + 1.5)); o = bpy.context.active_object; o.scale = (1.6, 0.4, 0.05); o.rotation_euler = (0, 0, ang); o.data.materials.append(wood)
            for s_ in (-0.6, 0.6):
                bpy.ops.mesh.primitive_cube_add(size=1, location=M(bx + ux * s_ / FT * 1.0, by + uy * s_ / FT * 1.0, bz + 0.75)); o = bpy.context.active_object; o.scale = (0.06, 0.35, 0.45); o.rotation_euler = (0, 0, ang); o.data.materials.append(wood)

# ------------------------------------------------------------------ sky, clouds, sun
sun = bpy.data.lights.new('sun', 'SUN'); sun.angle = math.radians(1.2); so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so)
w = bpy.data.worlds.new('sky'); sc.world = w; w.use_nodes = True; wn = w.node_tree; out_ = wn.nodes['World Output']; bg = wn.nodes['Background']
sky = wn.nodes.new('ShaderNodeTexSky'); types = [i.identifier for i in sky.bl_rna.properties['sky_type'].enum_items]
sky.sky_type = next(t for t in ('NISHITA', 'MULTIPLE_SCATTERING', 'HOSEK_WILKIE') if t in types); wn.links.new(sky.outputs['Color'], bg.inputs['Color'])
tc = wn.nodes.new('ShaderNodeTexCoord'); sep = wn.nodes.new('ShaderNodeSeparateXYZ'); wn.links.new(tc.outputs['Generated'], sep.inputs[0])
zc = wn.nodes.new('ShaderNodeMath'); zc.operation = 'MAXIMUM'; zc.inputs[1].default_value = 0.025; wn.links.new(sep.outputs['Z'], zc.inputs[0])
du = wn.nodes.new('ShaderNodeMath'); du.operation = 'DIVIDE'; wn.links.new(sep.outputs['X'], du.inputs[0]); wn.links.new(zc.outputs[0], du.inputs[1])
dv = wn.nodes.new('ShaderNodeMath'); dv.operation = 'DIVIDE'; wn.links.new(sep.outputs['Y'], dv.inputs[0]); wn.links.new(zc.outputs[0], dv.inputs[1])
cb = wn.nodes.new('ShaderNodeCombineXYZ'); wn.links.new(du.outputs[0], cb.inputs['X']); wn.links.new(dv.outputs[0], cb.inputs['Y'])
cn = wn.nodes.new('ShaderNodeTexNoise'); cn.inputs['Scale'].default_value = 0.9; cn.inputs['Detail'].default_value = 8.0; cn.inputs['Roughness'].default_value = 0.58; wn.links.new(cb.outputs[0], cn.inputs['Vector'])
cr = wn.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].position = 0.56; cr.color_ramp.elements[1].position = 0.70; wn.links.new(cn.outputs['Fac'], cr.inputs['Fac'])
fade = wn.nodes.new('ShaderNodeMapRange'); fade.inputs['From Min'].default_value = 0.02; fade.inputs['From Max'].default_value = 0.22; fade.clamp = True; wn.links.new(sep.outputs['Z'], fade.inputs['Value'])
cm = wn.nodes.new('ShaderNodeMath'); cm.operation = 'MULTIPLY'; wn.links.new(cr.outputs['Color'], cm.inputs[0]); wn.links.new(fade.outputs['Result'], cm.inputs[1])
lp = wn.nodes.new('ShaderNodeLightPath'); cam_only = wn.nodes.new('ShaderNodeMath'); cam_only.operation = 'MULTIPLY'; wn.links.new(cm.outputs[0], cam_only.inputs[0]); wn.links.new(lp.outputs['Is Camera Ray'], cam_only.inputs[1])
sh = wn.nodes.new('ShaderNodeTexNoise'); sh.inputs['Scale'].default_value = 2.2; sh.inputs['Detail'].default_value = 4.0; wn.links.new(cb.outputs[0], sh.inputs['Vector'])
shr = wn.nodes.new('ShaderNodeMapRange'); shr.inputs['To Min'].default_value = 0.62; shr.inputs['To Max'].default_value = 1.0; wn.links.new(sh.outputs['Fac'], shr.inputs['Value'])
cloud = wn.nodes.new('ShaderNodeBackground'); wn.links.new(shr.outputs['Result'], cloud.inputs['Strength'])
mix = wn.nodes.new('ShaderNodeMixShader'); wn.links.new(cam_only.outputs[0], mix.inputs[0]); wn.links.new(bg.outputs[0], mix.inputs[1]); wn.links.new(cloud.outputs[0], mix.inputs[2])
wn.links.new(mix.outputs[0], out_.inputs['Surface'])
FOG = []; _haze = {}
def fogify(m):
    t = m.node_tree; on = [n for n in t.nodes if n.type == 'OUTPUT_MATERIAL']
    if not on or not on[0].inputs['Surface'].links: return
    on = on[0]; src = on.inputs['Surface'].links[0].from_socket
    lpn = t.nodes.new('ShaderNodeLightPath'); k_ = t.nodes.new('ShaderNodeMath'); k_.operation = 'MULTIPLY'; k_.inputs[1].default_value = -1 / 2500.0
    t.links.new(lpn.outputs['Ray Length'], k_.inputs[0]); ex = t.nodes.new('ShaderNodeMath'); ex.operation = 'EXPONENT'; t.links.new(k_.outputs[0], ex.inputs[0])
    one = t.nodes.new('ShaderNodeMath'); one.operation = 'SUBTRACT'; one.inputs[0].default_value = 1.0; t.links.new(ex.outputs[0], one.inputs[1])
    cm_ = t.nodes.new('ShaderNodeMath'); cm_.operation = 'MULTIPLY'; t.links.new(one.outputs[0], cm_.inputs[0]); t.links.new(lpn.outputs['Is Camera Ray'], cm_.inputs[1])
    em = t.nodes.new('ShaderNodeEmission'); mx_ = t.nodes.new('ShaderNodeMixShader'); t.links.new(cm_.outputs[0], mx_.inputs[0]); t.links.new(src, mx_.inputs[1]); t.links.new(em.outputs[0], mx_.inputs[2])
    t.links.new(mx_.outputs[0], on.inputs['Surface']); FOG.append((k_, em))
def horizon_haze(preset):
    if preset in _haze: return _haze[preset]
    r = sc.render; keep = (r.resolution_x, r.resolution_y, r.filepath, r.image_settings.file_format, sc.camera, sc.cycles.samples, sc.view_settings.exposure)
    pc = bpy.data.cameras.new('probe'); pc.lens = 50; pc.clip_start = 0.01; pc.clip_end = 0.05; po = bpy.data.objects.new('probe', pc); sc.collection.objects.link(po)
    r.resolution_x, r.resolution_y = 16, 2; sc.cycles.samples = 16; sc.camera = po; r.image_settings.file_format = 'OPEN_EXR'; sc.view_settings.exposure = 0; acc = []
    for k in range(4):
        po.location = (0, 0, 800); po.rotation_euler = (math.radians(94), 0, math.radians(90 * k)); r.filepath = f'{OUT}/_probe_{k}.exr'; bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(r.filepath); acc.append(np.array(img.pixels[:], dtype=np.float32).reshape(-1, 4)[:, :3].mean(axis=0)); bpy.data.images.remove(img); os.remove(r.filepath)
    bpy.data.objects.remove(po); bpy.data.cameras.remove(pc)
    r.resolution_x, r.resolution_y, r.filepath, r.image_settings.file_format, sc.camera, sc.cycles.samples, sc.view_settings.exposure = keep
    _haze[preset] = tuple(float(v) for v in np.mean(acc, axis=0)); print('haze', preset, [round(v, 3) for v in _haze[preset]], flush=True); return _haze[preset]
def set_fog(dist_ft, preset):
    hz = horizon_haze(preset); m_ = max(max(hz), 1e-6)
    for k_, em in FOG:
        k_.inputs[1].default_value = -1 / max(dist_ft * FT, 1.0); em.inputs['Color'].default_value = (hz[0] / m_, hz[1] / m_, hz[2] / m_, 1); em.inputs['Strength'].default_value = m_
def lighting(preset):
    if preset == 'golden':
        elev, rot, energy, col, exp_, ccol, cstr = 11, 245, 2.4, (1.0, 0.78, 0.58), 0.55, (1.0, 0.72, 0.52), 0.55
    else:
        elev, rot, energy, col, exp_, ccol, cstr = 52, 210, 3.4, (1.0, 0.97, 0.92), 0.25, (0.97, 0.97, 1.0), 0.9
    so.rotation_euler = (math.radians(90 - elev), 0, math.radians(rot + 90)); sun.energy = energy; sun.color = col
    sky.sun_elevation = math.radians(elev); sky.sun_rotation = math.radians(rot); bg.inputs['Strength'].default_value = 0.03 if sky.sky_type != 'HOSEK_WILKIE' else 0.3
    cloud.inputs['Color'].default_value = (*ccol, 1); shr.inputs['To Max'].default_value = cstr; shr.inputs['To Min'].default_value = cstr * 0.62; sc.view_settings.exposure = exp_

for m in list(bpy.data.materials): fogify(m)

# ------------------------------------------------------------------ cameras
def look(cam, tgt):
    d = (tgt[0] - cam.location[0], tgt[1] - cam.location[1], tgt[2] - cam.location[2])
    cam.rotation_euler = (math.pi / 2 + math.atan2(d[2], math.hypot(d[0], d[1])), 0, math.atan2(d[1], d[0]) - math.pi / 2)
def cam(name, pos, tgt, lens, ortho=None):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_start = 0.1; cd.clip_end = 20000
    if ortho: cd.type = 'ORTHO'; cd.ortho_scale = ortho
    co = bpy.data.objects.new(name, cd); sc.collection.objects.link(co); co.location = M(*pos); look(co, M(*tgt)); return co
H = {h['n']: h for h in D['holes']}
def behind(n, back, up, lens, frac=0.8, side=0.0):
    h = H[n]; tx, ty = h['tee']; px_, py_ = h['pin']; L = math.hypot(px_ - tx, py_ - ty); ux, uy = (px_ - tx) / L, (py_ - ty) / L; nx, ny = -uy, ux
    x, y = tx - ux * back + nx * side, ty - uy * back + ny * side
    return (x, y, zg(x, y) + up), (tx + ux * L * frac, ty + uy * L * frac, zg(px_, py_) - 2), lens
course_c = (sum(h['pin'][0] + h['tee'][0] for h in D['holes']) / 36, sum(h['pin'][1] + h['tee'][1] for h in D['holes']) / 36)
front = [h for h in D['holes'] if h['n'] <= 9]; fc = (sum(h['pin'][0] for h in front) / 9, sum(h['pin'][1] for h in front) / 9)
VIEWS = {
    'aerial': (dict(pos=((X0 + X1) / 2, (Y0 + Y1) / 2, 3000), tgt=((X0 + X1) / 2, (Y0 + Y1) / 2 + 0.01, 0), lens=50, ortho=(X1 - X0) * FT), 'day', (3840, int(3840 * (Y1 - Y0) / (X1 - X0)))),
    'drone_day': (dict(pos=(fc[0] + 520, fc[1] - 980, 560), tgt=(fc[0] - 120, fc[1] + 140, 72), lens=28), 'day', None),
    'drone_golden': (dict(pos=(fc[0] + 900, fc[1] - 760, 420), tgt=(fc[0] - 260, fc[1] + 120, 72), lens=26), 'golden', None),
    'hole13': (dict(zip(('pos', 'tgt', 'lens'), behind(13, 140, 48, 30, 0.85))), 'day', None),
    'tee17': (dict(zip(('pos', 'tgt', 'lens'), behind(17, 6, 5.6, 32, 0.95, side=-4))), 'day', None),
    'green2': None, 'finish18': None,
}
h2 = H[2]; gx, gy = h2['pin']; tx, ty = h2['tee']; L = math.hypot(gx - tx, gy - ty); ux, uy = (gx - tx) / L, (gy - ty) / L; nx, ny = -uy, ux
VIEWS['green2'] = (dict(pos=(gx - ux * 120 + nx * 45, gy - uy * 120 + ny * 45, zg(gx, gy) + 7.0), tgt=(gx, gy, zg(gx, gy) + 1.5), lens=60), 'day', None)
h18 = H[18]; cxh, cyh = D['clubhouse']; gx, gy = h18['pin']
dxh, dyh = cxh - gx, cyh - gy; Lh = math.hypot(dxh, dyh); ex_, ey_ = dxh / Lh, dyh / Lh
VIEWS['finish18'] = (dict(pos=(gx - ex_ * 230 - ey_ * 40, gy - ey_ * 230 + ex_ * 40, zg(gx, gy) + 70), tgt=(gx + ex_ * Lh * 0.55, gy + ey_ * Lh * 0.55, zg(cxh, cyh) + 10), lens=32), 'golden', None)

E_BRK, N_BRK, QQ = 427050.0, 1578500.0, 1320.0                                              # the estate scripts/golf_course.py assumes
_qq = {'SW': (E_BRK - QQ, N_BRK - QQ), 'NW': (E_BRK - QQ, N_BRK), 'NE': (E_BRK, N_BRK), 'SE': (E_BRK, N_BRK - QQ)}
ESTATE = unary_union([Polygon([(a, b), (a + QQ, b), (a + QQ, b + QQ), (a, b + QQ)]) for a, b in (_qq[k] for k in json.load(open(f'{G}/golf_course.json')).get('parcels_assumed', ['SW', 'NW', 'SE']))])
ec = (ESTATE.centroid.x, ESTATE.centroid.y); ez = zg(*ec)
VIEWS['estate'] = (dict(pos=(ec[0] + 2150, ec[1] - 2400, ez + 2400), tgt=(ec[0] + 150, ec[1] - 150, ez), lens=34), 'day', None)
VIEWS['estate_golden'] = (dict(pos=(ec[0] + 2150, ec[1] - 2400, ez + 2400), tgt=(ec[0] + 150, ec[1] - 150, ez), lens=34), 'golden', None)
VIEWS['estate_top'] = (dict(pos=((X0 + X1) / 2, (Y0 + Y1) / 2, 4000), tgt=((X0 + X1) / 2, (Y0 + Y1) / 2 + 0.01, 0), lens=50, ortho=max(X1 - X0, Y1 - Y0) * FT), 'day', (int(X1 - X0), int(Y1 - Y0)))

def annotate(name, co, w_, h_, src):
    """a labelled copy: hole numbers on the greens, the Castle, the lakes and the assumed estate edge"""
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    from PIL import ImageDraw, ImageFont
    def px(x, y, z):
        v = world_to_camera_view(sc, co, Vector(M(x, y, z))); return (v.x * w_, (1 - v.y) * h_, v.z)
    im = Image.open(src).convert('RGBA'); ov = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov); u = w_ / 100.0
    try: fb = ImageFont.truetype('DejaVuSans-Bold.ttf', int(u * 1.15)); fs_ = ImageFont.truetype('DejaVuSans-Bold.ttf', int(u * 0.95)); fn = ImageFont.truetype('DejaVuSans-Bold.ttf', int(u * 0.9))
    except OSError: fb = fs_ = fn = ImageFont.load_default()
    ring = list(ESTATE.exterior.coords); pts = []                                            # the estate edge, dashed
    for (ax, ay), (bx, by) in zip(ring[:-1], ring[1:]):
        n = max(2, int(math.hypot(bx - ax, by - ay) / 15))
        pts += [px(ax + (bx - ax) * t, ay + (by - ay) * t, zg(ax + (bx - ax) * t, ay + (by - ay) * t) + 3) for t in np.linspace(0, 1, n)]
    for k in range(0, len(pts) - 1, 2):
        if pts[k][2] > 0 and pts[k + 1][2] > 0: d.line([pts[k][:2], pts[k + 1][:2]], fill=(255, 255, 255, 215), width=max(2, int(u * 0.22)))
    def tag(x, y, z, text, font, fill=(16, 22, 18, 200), fg=(255, 255, 255, 255)):
        X, Y, Zc = px(x, y, z)
        if Zc <= 0 or not (0 <= X < w_ and 0 <= Y < h_): return
        tb = d.textbbox((0, 0), text, font=font); tw, th = tb[2] - tb[0], tb[3] - tb[1]; pad = u * 0.35
        bx_, by_ = X - tw / 2 - pad, Y - th - 2 * pad - u * 0.9
        d.line([(X, Y), (X, by_ + th + 2 * pad)], fill=(255, 255, 255, 230), width=max(1, int(u * 0.12))); d.ellipse([X - u * 0.22, Y - u * 0.22, X + u * 0.22, Y + u * 0.22], fill=(255, 255, 255, 240))
        d.rounded_rectangle([bx_, by_, bx_ + tw + 2 * pad, by_ + th + 2 * pad], radius=u * 0.3, fill=fill); d.text((bx_ + pad - tb[0], by_ + pad - tb[1]), text, font=font, fill=fg)
    for h in D['holes']:
        x, y = h['pin']; X, Y, Zc = px(x, y, zg(x, y) + 4)
        if Zc <= 0 or not (0 <= X < w_ and 0 <= Y < h_): continue
        r = u * 0.75; d.ellipse([X - r, Y - r, X + r, Y + r], fill=(255, 198, 26, 240), outline=(20, 20, 20, 255), width=max(1, int(u * 0.1)))
        t = str(h['n']); tb = d.textbbox((0, 0), t, font=fn); d.text((X - (tb[2] + tb[0]) / 2, Y - (tb[3] + tb[1]) / 2), t, font=fn, fill=(20, 20, 20, 255))
    cxh, cyh = D['clubhouse']; tag(cxh, cyh, zg(cxh, cyh) + 45, 'THE CASTLE · clubhouse', fb, fill=(120, 24, 24, 220))
    for w_l in world['water']:
        lp = Polygon(list(zip(w_l['pts'][0::2], w_l['pts'][1::2])))
        if lp.intersects(ponds) or lp.area < 20000: continue
        rr = list(lp.minimum_rotated_rectangle.exterior.coords); a_, b_ = math.dist(rr[0], rr[1]), math.dist(rr[1], rr[2])
        c = lp.centroid; tag(c.x, c.y, float(w_l['wse']), 'LONG LAKE' if max(a_, b_) > 2.2 * min(a_, b_) else 'ROUND LAKE', fs_, fill=(18, 60, 80, 210))
    sw = min(ESTATE.exterior.coords, key=lambda p: p[0] + p[1])
    tag(sw[0] + 420, sw[1] + 25, zg(sw[0] + 420, sw[1] + 25) + 3, 'ESTATE EDGE (ASSUMED, ABOUT 120 AC)', fs_, fill=(40, 40, 40, 190))
    C = json.load(open(f'{G}/golf_course.json'))                                            # title box, top left
    lines = [(f"SAUSAGE CASTLE ESTATE · ABOUT {C.get('estate_acres', 120):.0f} AC", fb), (f"Gator Greens: {len(D['holes'])} holes, par {C['par']}, {C['yards']:,} yd · the Castle is the clubhouse · yellow = greens", fs_)]
    y0_ = u * 1.2; bw = max(d.textbbox((0, 0), t, font=f)[2] for t, f in lines) + u * 1.6; bh = sum(d.textbbox((0, 0), t, font=f)[3] for t, f in lines) + u * 1.9
    d.rounded_rectangle([u * 1.2, y0_, u * 1.2 + bw, y0_ + bh], radius=u * 0.4, fill=(16, 22, 18, 205)); yy = y0_ + u * 0.7
    for t, f in lines: d.text((u * 2.0, yy), t, font=f, fill=(255, 255, 255, 255)); yy += d.textbbox((0, 0), t, font=f)[3] + u * 0.5
    out = Image.alpha_composite(im, ov).convert('RGB'); out.save(src.replace('.jpg', '_labeled.jpg'), quality=90); print('labelled', name, flush=True)

def cull(spec, on):
    (cx_, cy_, _), (tx_, ty_, _) = spec['pos'], spec['tgt']; L = math.hypot(tx_ - cx_, ty_ - cy_) or 1; ux, uy = (tx_ - cx_) / L, (ty_ - cy_) / L; n = 0
    for o, x, y, r, h in TREES:
        a = (x - cx_) * ux + (y - cy_) * uy; lat = abs(-(x - cx_) * uy + (y - cy_) * ux)
        hide = on and -r < a < min(L * 0.55, 420) and lat < r + 10 + a * 0.18
        o.hide_render = hide; n += hide
    return n
def render_still(name):
    spec, preset, size = VIEWS[name]; lighting(preset); co = cam(name, **spec); sc.camera = co; top = name in ('aerial', 'estate_top'); est = name.startswith('estate')
    set_fog(1e9 if top else (14000 if est else (5200 if preset == 'golden' else 3600)), preset)
    if not top and not est: print('  culled', cull(spec, True), 'trees', flush=True)
    w_, h_ = size if size else map(int, args.res.split('x'))
    if args.preview: w_, h_ = w_ // 4, h_ // 4
    sc.render.resolution_x, sc.render.resolution_y = w_, h_; sc.cycles.samples = 8 if args.preview else (48 if top else args.samples)
    fp = f'{OUT}/golf_mockup_{name}.png'; sc.render.filepath = fp; bpy.ops.render.render(write_still=True)
    Image.open(fp).convert('RGB').save(fp[:-4] + '.jpg', quality=90); os.remove(fp); cull(spec, False); print('rendered', name, flush=True)
    if est: annotate(name, co, w_, h_, fp[:-4] + '.jpg')
for v in [v for v in args.views.split(',') if v]: render_still(v)

# ------------------------------------------------------------------ flyover: a slow drone glide over the front nine to the Castle
if args.flyover:
    FO = f'{OUT}/flyover'; os.makedirs(FO, exist_ok=True); lighting('day'); set_fog(3600, 'day'); sc.render.use_persistent_data = True
    w_, h_ = map(int, args.res.split('x')); sc.render.resolution_x, sc.render.resolution_y = w_, h_; sc.cycles.samples = args.samples
    h6, h3, h13, h8 = H[6], H[3], H[13], H[8]
    way = [(h6['pin'][0] + 260, h6['pin'][1] - 260, 360), ((h3['pin'][0] + h6['tee'][0]) / 2, (h3['pin'][1] + h6['tee'][1]) / 2, 290),
           (h3['tee'][0] - 60, h3['tee'][1] - 140, 250), (h13['tee'][0], h13['tee'][1] - 40, 220), ((h13['pin'][0] + cxh) / 2 + 60, (h13['pin'][1] + cyh) / 2 - 80, 200),
           (cxh + 230, cyh - 210, 180)]
    def cr_(p0, p1, p2, p3, t):
        return tuple(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t ** 3) for a, b, c, d in zip(p0, p1, p2, p3))
    pts = [way[0]] + way + [way[-1]]; dense = []
    for i in range(1, len(pts) - 2):
        for t in np.linspace(0, 1, 60, endpoint=False): dense.append(cr_(pts[i - 1], pts[i], pts[i + 1], pts[i + 2], t))
    dense.append(way[-1]); seg = np.array(dense); dist = np.concatenate([[0], np.cumsum(np.hypot(np.diff(seg[:, 0]), np.diff(seg[:, 1])))])
    co = cam('fly', (seg[0][0], seg[0][1], seg[0][2] + 70), (seg[5][0], seg[5][1], 70), 26); sc.camera = co
    def along(d):                                                                       # point at arc length d, interpolated (no stepping)
        k = min(max(int(np.searchsorted(dist, d)), 1), len(seg) - 1); a = min(max((d - dist[k - 1]) / max(dist[k] - dist[k - 1], 1e-6), 0.0), 1.0)
        return seg[k - 1] + (seg[k] - seg[k - 1]) * a
    def gsmooth(v, s):                                                                  # Gaussian low-pass across frames, edges held
        r = int(3 * s); k = np.exp(-0.5 * (np.arange(-r, r + 1) / s) ** 2); k /= k.sum()
        return np.convolve(np.pad(v, r, mode='edge'), k, mode='valid')
    N = args.flyover; P, T = [], []
    for f in range(N):                                                                  # the whole camera path first, so it can be smoothed
        u = f / (N - 1); u_e = 0.5 - 0.5 * math.cos(math.pi * u)                       # ease in and out
        d = u_e * dist[-1]; P.append(along(d))
        tx_, ty_ = np.mean([along(min(d + o, dist[-1]))[:2] for o in (360, 420, 480)], axis=0)   # aim about 420 ft ahead
        bl = min(max((u - 0.68) / 0.22, 0.0), 1.0); bl = bl * bl * (3 - 2 * bl)      # then turn to the Castle and hold on it
        T.append((tx_ * (1 - bl) + cxh * bl, ty_ * (1 - bl) + cyh * bl))
    P, T = np.array(P), np.array(T)
    yaw = gsmooth(np.unwrap(np.arctan2(T[:, 1] - P[:, 1], T[:, 0] - P[:, 0])), 16)    # heading and look-down distance smoothed over
    hd = np.exp(gsmooth(np.log(np.maximum(np.hypot(*(T - P[:, :2]).T), 150)), 16))     # about 2 s, so pans stay under 2 degrees a frame
    for f in range(args.start, args.end or N):
        x, y, alt = P[f]; tx_, ty_ = x + hd[f] * math.cos(yaw[f]), y + hd[f] * math.sin(yaw[f])
        co.location = M(x, y, zg(x, y) + alt); look(co, M(tx_, ty_, zg(tx_, ty_) + 8))
        sc.render.filepath = f'{FO}/f{f:04d}.png'; bpy.ops.render.render(write_still=True); print('frame', f, flush=True)
    print('flyover done', flush=True)
