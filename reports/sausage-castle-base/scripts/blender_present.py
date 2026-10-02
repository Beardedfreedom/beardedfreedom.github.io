#!/usr/bin/env python3
"""Florida Freedom World, lake zones: the presentation model.

A clean 3D scene of the lake, the loop lane, the 22 cabins on their graded pads and the trees the
lidar found, drawn as stylised trees (heights and crown sizes from the lidar) on the smoothed bare
earth instead of the raw lidar canopy. Renders hero stills and a turntable, exports a .glb for the
web viewer (viewer3d/) and saves the .blend.

Run with the pip "bpy" module (Python 3.11):
    python3 scripts/blender_present.py --base . --out mockup/present --renders --samples 128 --turntable 48
    # zone close-ups (drone + visitor eye level, day and dusk) and a slow 240-frame orbit (10 s a lap at 24 fps):
    python3 scripts/blender_present.py --base . --out mockup/present --renders --no-glb \
        --views close_A,close_B,close_C,close_D,ground_A,ground_B,ground_C,ground_D,ground_C_dusk,ground_D_dusk,ground_A_dusk,ground_B_dusk \
        --turntable 240 --tt-res 1280x720 --tt-samples 40
or inside Blender:
    blender --background --python scripts/blender_present.py -- --base reports/sausage-castle-base --out ... --renders

Inputs: viewer/data/meta.json + lakes_cleared_ground.png (graded bare earth), viewer/data/units.json
(cabin meshes and placements), focus/lakes/clearing_grading.json (trees removed),
focus/lakes/lake_zones_concept.json (pads, lane rules, lake centroid),
focus/lakes/sausage_castle_lakes_focus_EPSG2236_ftUS.dxf (trees, lake outline, road centrelines).
Scene units: metres; origin at the lakes-zone centre; +Y north, +Z up. Feet in, metres out.
"""
import sys, os, json, math, argparse, re, random
try:
    import bpy, bmesh
except ImportError:
    sys.exit('This script needs Blender: run it with `blender --background --python ...` or install the bpy wheel.')
import numpy as np
from scipy.ndimage import gaussian_filter
import shapely
from shapely.geometry import Polygon, MultiLineString, LineString, Point, MultiPolygon
from shapely.ops import unary_union
import ezdxf

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
ap = argparse.ArgumentParser()
ap.add_argument('--base', default='.'); ap.add_argument('--out', default='mockup/present')
ap.add_argument('--renders', action='store_true'); ap.add_argument('--samples', type=int, default=128)
ap.add_argument('--res', default='1920x1080'); ap.add_argument('--step', type=int, default=2, help='ground grid subsampling (2 = 4 ft)')
ap.add_argument('--views', default='overall,A,B,C,D,lake,hero,hero_dusk')
ap.add_argument('--turntable', type=int, default=0, help='number of turntable frames (0 = none)')
ap.add_argument('--tt-res', default='960x540'); ap.add_argument('--tt-samples', type=int, default=48)
ap.add_argument('--tt-radius', type=float, default=900.0, help='turntable orbit radius (ft)'); ap.add_argument('--tt-height', type=float, default=380.0, help='turntable camera height above the water (ft)')
ap.add_argument('--tt-start', type=int, default=0, help='first turntable frame to render (resume)')
ap.add_argument('--no-trees', action='store_true'); ap.add_argument('--tree-density', type=float, default=1.0)
ap.add_argument('--no-glb', action='store_true'); ap.add_argument('--seed', type=int, default=7)
args = ap.parse_args(argv)
BASE = os.path.abspath(args.base); OUT = os.path.abspath(args.out); os.makedirs(OUT, exist_ok=True)
FT = 0.3048; rng = random.Random(args.seed); nrng = np.random.default_rng(args.seed)

VD = f'{BASE}/viewer/data'; meta = json.load(open(f'{VD}/meta.json')); z = meta['zones']['lakes']
c = z['cell_ft']; x0, y0 = z['x0'], z['y0']; W, Hh = z['width_ft'], z['height_ft']
cx, cy = x0 + W / 2, y0 + Hh / 2; zmin = z['z_range'][0]
lz = json.load(open(f'{BASE}/focus/lakes/lake_zones_concept.json')); rules = lz['rules']; pads = lz['pads']
units = json.load(open(f'{VD}/units.json'))
removed = set(t['id'] for t in json.load(open(f'{BASE}/focus/lakes/clearing_grading.json'))['trees_removed'])
dxf = ezdxf.readfile(f'{BASE}/focus/lakes/sausage_castle_lakes_focus_EPSG2236_ftUS.dxf'); ms = dxf.modelspace()


def M(x, y, zz):
    """feet (state plane) -> scene metres"""
    return ((x - cx) * FT, (y - cy) * FT, (zz - zmin) * FT)


def lin(hexcol):
    rgb = tuple(int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in rgb)


# ------------------------------------------------------------------ scene setup
bpy.ops.wm.read_factory_settings(use_empty=True); scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'; scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'
scene.cycles.samples = args.samples; scene.cycles.use_adaptive_sampling = True; scene.cycles.adaptive_threshold = 0.02
scene.cycles.use_denoising = True; scene.cycles.max_bounces = 6; scene.cycles.diffuse_bounces = 3; scene.cycles.glossy_bounces = 3
scene.render.resolution_x, scene.render.resolution_y = map(int, args.res.split('x')); scene.render.image_settings.file_format = 'PNG'
try:
    scene.view_settings.view_transform = 'AgX'; scene.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    try: scene.view_settings.view_transform = 'Filmic'
    except Exception: pass
scene.view_settings.exposure = 0.15


def collection(name):
    col = bpy.data.collections.new(name); scene.collection.children.link(col); return col


def principled(m):
    return m.node_tree.nodes['Principled BSDF']


def mat(name, color, rough=0.8, metal=0.0, emit=0.0, alpha=1.0, spec=None):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = principled(m)
    b.inputs['Base Color'].default_value = (*lin(color), 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if emit:
        if 'Emission Color' in b.inputs: b.inputs['Emission Color'].default_value = (*lin(color), 1)
        b.inputs['Emission Strength'].default_value = emit
    if spec is not None:
        key = 'Specular IOR Level' if 'Specular IOR Level' in b.inputs else 'Specular'; b.inputs[key].default_value = spec
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
        try: m.blend_method = 'BLEND'
        except Exception: pass
    return m


def mesh_obj(name, verts, faces, material=None, coll=None, smooth=False):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.validate(); me.update()
    if smooth:
        for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(name, me); (coll or scene.collection).objects.link(ob)
    if material: me.materials.append(material)
    return ob


def join(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]; bpy.ops.object.join(); ob = bpy.context.active_object; ob.name = name; return ob


# ------------------------------------------------------------------ site geometry from the DXF
water_polys = []
for e in ms.query('LWPOLYLINE[layer=="C-WATR-LIDAR"]'):
    pts = [(p[0], p[1]) for p in e.get_points()]
    if len(pts) >= 3:
        poly = Polygon(pts).buffer(0).buffer(5, join_style='round').buffer(-5, join_style='round').simplify(1.5)   # rounded shoreline
        if poly.geom_type == 'MultiPolygon': poly = max(poly.geoms, key=lambda g: g.area)
        if not poly.is_empty: water_polys.append((poly, e.dxf.elevation or 70.0))
water_polys.sort(key=lambda t: -t[0].area)
water_union = unary_union([p for p, _ in water_polys]) if water_polys else Polygon()
roads = [LineString([(p[0], p[1]) for p in e.get_points()]) for e in ms.query('LWPOLYLINE[layer=="C-ROAD-CNTR"]') if len(list(e.get_points())) >= 2]
roads_ml = MultiLineString(roads) if roads else MultiLineString([])
lane_w = rules.get('lane_width_ft', 20)
pad_polys = [Polygon(p['corners']) for p in pads]; pads_union = unary_union(pad_polys)
lake_c = lz['lake']['centroid']; wse = water_polys[0][1] if water_polys else 70.0
print(f'water bodies {len(water_polys)} (wse {wse:.1f} ft), roads {len(roads)}, pads {len(pads)}')

# ------------------------------------------------------------------ ground: smoothed graded bare earth with painted land cover
im = bpy.data.images.load(f"{VD}/{z['cleared']['ground']['file']}", check_existing=True); iw, ih = im.size
px = np.array(im.pixels[:], dtype=np.float32).reshape(ih, iw, 4)   # row 0 = south
G = (np.round(px[..., 0] * 255) * 256 + np.round(px[..., 1] * 255)) * z['cleared']['ground']['scale'] + z['cleared']['ground']['zmin']
ny, nx = G.shape
Gs = gaussian_filter(G, sigma=1.2)
st = args.step; Gs = Gs[::st, ::st]; hy, hx = Gs.shape
xs = x0 + (np.arange(hx) * st + 0.5) * c; ys = y0 + (np.arange(hy) * st + 0.5) * c
XX, YY = np.meshgrid(xs, ys); P = shapely.points(XX.ravel(), YY.ravel())
d_water = shapely.distance(P, water_union).reshape(hy, hx) if not water_union.is_empty else np.full((hy, hx), 1e9)
in_water = shapely.contains(water_union, P).reshape(hy, hx) if not water_union.is_empty else np.zeros((hy, hx), bool)
d_road = shapely.distance(P, roads_ml).reshape(hy, hx) if roads else np.full((hy, hx), 1e9)
d_pad = shapely.distance(P, pads_union).reshape(hy, hx)
# lake bed: keep the bed below the water plane so nothing pokes through
d_edge = shapely.distance(P, water_union.boundary).reshape(hy, hx) if not water_union.is_empty else np.zeros((hy, hx))
bed_z = wse + 0.6 - 3.5 * np.clip(d_edge / 14.0, 0, 1)     # gentle bed: shoreline at the water plane, 3 ft deep 14 ft out
Gs = np.where(in_water, np.minimum(Gs, bed_z), Gs)
# painted cover: grass with slow variation, sand ring at the shore, packed sand on tracks and pads
noise = gaussian_filter(nrng.random((hy, hx)), 6.0); noise = (noise - noise.min()) / max(noise.ptp(), 1e-6)
g1, g2 = np.array(lin('#5f9033')), np.array(lin('#88ad45')); sand = np.array(lin('#d9c89c')); bed = np.array(lin('#a89b78'))
track = np.array(lin('#c8b58f')); padc = np.array(lin('#cfc3a6'))
col = g1[None, None, :] * (1 - noise[..., None]) + g2[None, None, :] * noise[..., None]
shore = np.clip(1 - (d_water - 6) / 24, 0, 1)[..., None]; col = col * (1 - shore) + sand[None, None, :] * shore
col = np.where(in_water[..., None], bed[None, None, :], col)
tr = np.clip(1 - (d_road - lane_w / 2 + 2) / 4, 0, 1)[..., None]; col = col * (1 - tr) + track[None, None, :] * tr
pd = np.clip(1 - (d_pad - 1) / 3, 0, 1)[..., None]; col = col * (1 - pd) + padc[None, None, :] * pd
verts = [M(xs[i], ys[j], Gs[j, i]) for j in range(hy) for i in range(hx)]
faces = [(j * hx + i, j * hx + i + 1, (j + 1) * hx + i + 1, (j + 1) * hx + i) for j in range(hy - 1) for i in range(hx - 1)]
gcol = collection('Ground')
gmat = bpy.data.materials.new('Ground'); gmat.use_nodes = True; nt = gmat.node_tree
vc = nt.nodes.new('ShaderNodeVertexColor'); vc.layer_name = 'Cover'; nt.links.new(vc.outputs['Color'], principled(gmat).inputs['Base Color'])
principled(gmat).inputs['Roughness'].default_value = 0.95


def enrich_ground_material():
    """render-only: break up the painted cover with a fine procedural mottle (added after the glTF export, which needs the plain vertex-colour link)"""
    try:
        nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.4; nz.inputs['Detail'].default_value = 5.0; nz.inputs['Roughness'].default_value = 0.6
        mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.3; mr.inputs['From Max'].default_value = 0.7; mr.inputs['To Min'].default_value = 0.8; mr.inputs['To Max'].default_value = 1.16
        nt.links.new(nz.outputs['Fac'], mr.inputs['Value'])
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs[0].default_value = 1.0
        nt.links.new(vc.outputs['Color'], mix.inputs[6]); nt.links.new(mr.outputs['Result'], mix.inputs[7]); nt.links.new(mix.outputs[2], principled(gmat).inputs['Base Color'])
    except Exception as ex:
        print('ground mottle skipped:', ex)


ground = mesh_obj('Ground', verts, faces, gmat, gcol, smooth=True)
attr = ground.data.color_attributes.new(name='Cover', type='FLOAT_COLOR', domain='POINT')
flat = np.concatenate([col.reshape(-1, 3), np.ones((hy * hx, 1))], axis=1).astype(np.float32).ravel(); attr.data.foreach_set('color', flat)
print('ground', hx, 'x', hy, 'verts')


def ground_z(x, y):
    """bilinear ground elevation (ft) at state-plane x, y"""
    fi = (x - xs[0]) / (st * c); fj = (y - ys[0]) / (st * c)
    i0 = int(np.clip(np.floor(fi), 0, hx - 2)); j0 = int(np.clip(np.floor(fj), 0, hy - 2)); ti = float(np.clip(fi - i0, 0, 1)); tj = float(np.clip(fj - j0, 0, 1))
    return float(Gs[j0, i0] * (1 - ti) * (1 - tj) + Gs[j0, i0 + 1] * ti * (1 - tj) + Gs[j0 + 1, i0] * (1 - ti) * tj + Gs[j0 + 1, i0 + 1] * ti * tj)


# ------------------------------------------------------------------ water
wcol = collection('Water'); wmat = mat('Water', '#256a82', rough=0.06, spec=0.7)
nt = wmat.node_tree; b = principled(wmat)
try:
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 40.0; nz.inputs['Detail'].default_value = 4.0
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.04; nt.links.new(nz.outputs['Fac'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
except Exception: pass
for k, (poly, elev) in enumerate(water_polys):
    ring = list(poly.exterior.coords)[:-1]
    bm = bmesh.new(); vs = [bm.verts.new(M(x, y, elev + 0.3)) for x, y in ring]
    try: bm.faces.new(vs)
    except Exception: pass
    me = bpy.data.meshes.new(f'Water_{k}'); bm.to_mesh(me); bm.free(); ob = bpy.data.objects.new(f'Water_{k}', me); wcol.objects.link(ob); me.materials.append(wmat)


# ------------------------------------------------------------------ lane, pads, paths
def ribbon(name, line, width, lift, material, coll, step_ft=8.0):
    """a strip draped on the ground along a LineString"""
    L = line.length
    if L < 1: return None
    n = max(2, int(L / step_ft) + 1); ts = np.linspace(0, L, n); pts = [line.interpolate(t) for t in ts]
    verts, faces = [], []
    for k, p in enumerate(pts):
        q = pts[min(k + 1, n - 1)]; r = pts[max(k - 1, 0)]; dx, dy = q.x - r.x, q.y - r.y; d = math.hypot(dx, dy) or 1; nx_, ny_ = -dy / d, dx / d
        for s in (-1, 1):
            x, y = p.x + s * nx_ * width / 2, p.y + s * ny_ * width / 2; verts.append(M(x, y, ground_z(x, y) + lift))
    for k in range(n - 1): faces.append((2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2))
    return mesh_obj(name, verts, faces, material, coll, smooth=True)


scol = collection('Site'); lane_mat = mat('Lane', '#c4ad82', rough=0.95); pad_mat = mat('Pad', '#d3c7a8', rough=0.9); path_mat = mat('Path', '#c9b58c', rough=0.95)
for k, rd in enumerate(roads): ribbon(f'Lane_{k}', rd, lane_w, 0.25, lane_mat, scol)
for p in pads:
    zz = next((pl.get('z_graded', pl['z']) for pl in units['placements'] if pl['pad'] == p['id']), ground_z(*p['center']))
    cs = p['corners']; verts = [M(x, y, zz + 0.35) for x, y in cs]; mesh_obj(f"PadSlab_{p['id']}", verts, [(0, 1, 2, 3)], pad_mat, scol)
    if roads:
        near = shapely.ops.nearest_points(Point(p['center']), roads_ml)[1]; ribbon(f"Path_{p['id']}", LineString([p['center'], (near.x, near.y)]), 5.0, 0.3, path_mat, scol, step_ft=6)

# ------------------------------------------------------------------ trees: stylised, lidar-sized
tree_objs = []
if not args.no_trees:
    tcol = collection('Trees'); trunk_m = mat('Trunk', '#5a4632', rough=0.9)
    crown_ms = {'oak': [mat('Oak1', '#3f7d36', 0.85), mat('Oak2', '#4d8c3d', 0.85), mat('Oak3', '#35702f', 0.85)],
                'pine': [mat('Pine1', '#2f6b48', 0.85), mat('Pine2', '#3a7a52', 0.85)],
                'cypress': [mat('Cyp1', '#7a9c3a', 0.85), mat('Cyp2', '#6b8f36', 0.85)]}
    protos = {}

    def bake(ob):
        """freeze the object's transform into its mesh so shared copies read in world units"""
        bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        for p in ob.data.polygons: p.use_smooth = True
        scene.collection.objects.unlink(ob); return ob

    def make_crown(kind, v):
        """unit crown centred on the origin: radius 1 in plan, about 1.2 to 1.9 tall, scaled per tree"""
        parts = []
        if kind == 'oak':
            for k in range(6):
                a = rng.uniform(0, 2 * math.pi); rr = rng.uniform(0.0, 0.45); rad = rng.uniform(0.5, 0.68); zc = rng.uniform(-0.25, 0.3)
                bpy.ops.mesh.primitive_uv_sphere_add(segments=14, ring_count=9, radius=rad, location=(rr * math.cos(a), rr * math.sin(a), zc)); s = bpy.context.active_object
                s.scale = (1, 1, rng.uniform(0.75, 0.95)); s.data.materials.append(crown_ms['oak'][v % 3]); parts.append(s)
        elif kind == 'pine':
            for rad, zc, dep in ((1.0, -0.25, 0.6), (0.72, 0.12, 0.55), (0.42, 0.45, 0.45)):
                bpy.ops.mesh.primitive_cone_add(vertices=14, radius1=rad, radius2=0.0, depth=dep, location=(0, 0, zc)); s = bpy.context.active_object; s.data.materials.append(crown_ms['pine'][v % 2]); parts.append(s)
        else:  # cypress: one tall spire
            bpy.ops.mesh.primitive_cone_add(vertices=14, radius1=1.0, radius2=0.06, depth=1.0, location=(0, 0, 0)); s = bpy.context.active_object; s.data.materials.append(crown_ms['cypress'][v % 2]); parts.append(s)
        ob = join(parts, f'CrownProto_{kind}{v}'); ob.location = (0, 0, 0); return bake(ob)
    for kind, nv in (('oak', 3), ('pine', 2), ('cypress', 2)):
        protos[kind] = [make_crown(kind, v) for v in range(nv)]
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=1.0, depth=1.0, location=(0, 0, 0.5)); trunk_proto = bpy.context.active_object; trunk_proto.name = 'TrunkProto'
    trunk_proto.data.materials.append(trunk_m); bake(trunk_proto)   # mesh now spans z 0..1

    circles = list(ms.query('CIRCLE[layer=="L-PLNT-TREE"]')); labels = list(ms.query('TEXT[layer=="L-PLNT-ANNO"]'))
    heights = {}
    for lab in labels:
        m = re.search(r"(\d+(?:\.\d+)?)", lab.dxf.text or '')
        if m: heights[(round(lab.dxf.insert.x - 1), round(lab.dxf.insert.y - 1))] = float(m.group(1))
    keep_clear = unary_union([pads_union.buffer(rules.get('building_clearance_ft', 20) * 0.5), roads_ml.buffer(lane_w / 2 + 3)])
    placed = 0
    for i, e in enumerate(circles, start=1):
        if i in removed: continue
        if rng.random() > args.tree_density: continue
        x, y, r = e.dxf.center.x, e.dxf.center.y, max(e.dxf.radius, 3.0)
        pt = Point(x, y)
        if keep_clear.contains(pt) or water_union.contains(pt): continue
        h = heights.get((round(x), round(y)), max(12.0, r * 2.4)); h = max(h, r * 1.6, 10.0)
        dw = water_union.distance(pt) if not water_union.is_empty else 1e9
        if dw < 45 and h > 25: kind = 'cypress'
        elif h / (2 * r) > 1.9: kind = 'pine'
        else: kind = 'oak'
        proto = rng.choice(protos[kind]); gz = ground_z(x, y)
        if kind == 'oak':      # round crown about 1.7 r tall sitting at the top of the tree
            cr, ch = r, r * 0.85; cz = gz + h - ch * 0.75; th = max(h - ch, 0.3 * h); tr = 0.08 * r
        elif kind == 'pine':   # crown is the top 62% of the height
            cr, ch = r, 0.62 * h; cz = gz + h - ch / 2; th = h - ch + 0.15 * ch; tr = 0.06 * r
        else:                  # cypress spire, top 80%
            cr, ch = r * 0.9, 0.8 * h; cz = gz + h - ch / 2; th = 0.3 * h; tr = 0.07 * r
        cr *= rng.uniform(0.92, 1.08)
        crown = bpy.data.objects.new(f'Tree_{i}_{kind}', proto.data); crown.location = M(x, y, cz); crown.rotation_euler = (0, 0, rng.uniform(0, 2 * math.pi)); crown.scale = (cr * FT, cr * FT, ch * FT)
        trunk = bpy.data.objects.new(f'Trunk_{i}', trunk_proto.data); trunk.location = M(x, y, gz - 0.5); trunk.scale = (max(tr, 0.5) * FT, max(tr, 0.5) * FT, (th + 0.5) * FT)
        tcol.objects.link(crown); tcol.objects.link(trunk); tree_objs.append(((crown, trunk), x, y, h)); placed += 1
    print('trees placed', placed, 'of', len(circles), '| removed by clearing', len(removed))

# ------------------------------------------------------------------ cabins
ucol = collection('Cabins'); uprotos = {}
EMIT = {'portholes': 5.0, 'led ring': 6.0, 'windows': 1.2, 'skylight': 0.8}
ROUGH = {'ufo': 0.3}
for key, u in units['units'].items():
    parts = []
    for part in u['parts']:
        V = np.array(part['positions']).reshape(-1, 3) * FT; F = np.array(part['indices']).reshape(-1, 3)
        metal = 0.75 if (key == 'ufo' and part['name'] in ('hull', 'legs', 'ramp', 'feet', 'antenna')) else 0.0
        rough = 0.45 if part['name'] in ('cap', 'pod cap') else (0.25 if part['name'] in ('windows', 'skylight', 'dome', 'portholes') else ROUGH.get(key, 0.75))
        m = mat(f"{key}_{part['name']}", part['color'], rough=rough, metal=metal, emit=EMIT.get(part['name'], 0.0), alpha=0.5 if part['name'] == 'dome' else 1.0)
        parts.append(mesh_obj(f'{key}_{part["name"]}', [tuple(v) for v in V], [tuple(f) for f in F], m, ucol))
    proto = join(parts, f'UNIT_{key}')
    for p in proto.data.polygons: p.use_smooth = key in ('mushroom', 'ufo')
    if key in ('mushroom', 'ufo'):
        try:
            bpy.ops.object.select_all(action='DESELECT'); proto.select_set(True); bpy.context.view_layer.objects.active = proto
            bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40)) if hasattr(bpy.ops.object, 'shade_smooth_by_angle') else None
        except Exception: pass
    proto.hide_render = True; proto.hide_viewport = True; uprotos[key] = proto
cabin_pos = {}
for pl in units['placements']:
    inst = bpy.data.objects.new(f"{pl['pad']}_{pl['unit']}", uprotos[pl['unit']].data); zz = pl.get('z_graded', pl['z'])
    inst.location = M(pl['x'], pl['y'], zz); inst.rotation_euler = (0, 0, math.radians(pl['rot_deg'])); ucol.objects.link(inst); cabin_pos[pl['pad']] = (pl['x'], pl['y'], zz, pl['zone'])
print('cabins placed', len(units['placements']))

# ------------------------------------------------------------------ sky, sun, cameras
sun = bpy.data.lights.new('Sun', 'SUN'); sun.energy = 3.5; sun.angle = math.radians(1.2); so = bpy.data.objects.new('Sun', sun); scene.collection.objects.link(so)
PHYS_SKY = False; HAZE = None; _haze = {}
world = bpy.data.worlds.new('Sky'); scene.world = world; world.use_nodes = True; wn = world.node_tree; sky = None
try:
    sky = wn.nodes.new('ShaderNodeTexSky')
    sky_types = [i.identifier for i in sky.bl_rna.properties['sky_type'].enum_items]   # Blender 5 renamed NISHITA to MULTIPLE_SCATTERING
    sky.sky_type = next(t for t in ('NISHITA', 'MULTIPLE_SCATTERING', 'SINGLE_SCATTERING', 'HOSEK_WILKIE') if t in sky_types)
    sky.sun_intensity = 0.35; sky.altitude = 30
    for k, v in (('air_density', 1.0), ('dust_density', 2.2), ('aerosol_density', 2.2), ('ozone_density', 1.6)):
        if hasattr(sky, k): setattr(sky, k, v)
    print('sky', sky.sky_type); PHYS_SKY = True
    # below the horizon the physical sky is black and shows past the edge of the ground model. Blend those
    # directions to a haze background whose colour is measured from the sky just above the horizon (lighting()).
    bg1 = wn.nodes['Background']; HAZE = wn.nodes.new('ShaderNodeBackground'); mixs = wn.nodes.new('ShaderNodeMixShader')
    tc = wn.nodes.new('ShaderNodeTexCoord'); sep = wn.nodes.new('ShaderNodeSeparateXYZ'); mr = wn.nodes.new('ShaderNodeMapRange'); mr.clamp = True
    mr.inputs['From Min'].default_value = 0.0; mr.inputs['From Max'].default_value = -0.03; mr.inputs['To Min'].default_value = 0.0; mr.inputs['To Max'].default_value = 1.0
    wn.links.new(tc.outputs['Generated'], sep.inputs[0]); wn.links.new(sep.outputs['Z'], mr.inputs['Value']); lp = wn.nodes.new('ShaderNodeLightPath'); camonly = wn.nodes.new('ShaderNodeMath'); camonly.operation = 'MULTIPLY'   # haze only where the camera looks, so the lighting is unchanged
    wn.links.new(mr.outputs['Result'], camonly.inputs[0]); wn.links.new(lp.outputs['Is Camera Ray'], camonly.inputs[1]); wn.links.new(camonly.outputs[0], mixs.inputs[0])
    wn.links.new(bg1.outputs[0], mixs.inputs[1]); wn.links.new(HAZE.outputs[0], mixs.inputs[2]); wn.links.new(mixs.outputs[0], wn.nodes['World Output'].inputs['Surface'])
    wn.links.new(sky.outputs['Color'], wn.nodes['Background'].inputs['Color']); wn.nodes['Background'].inputs['Strength'].default_value = 0.55
except Exception:
    wn.nodes['Background'].inputs['Color'].default_value = (0.55, 0.7, 0.9, 1)


def horizon_haze(preset):
    """linear colour of the sky 1-3 degrees above the horizon, from a tiny probe render (cached per preset)"""
    if preset in _haze: return _haze[preset]
    r = scene.render; keep = (r.resolution_x, r.resolution_y, r.resolution_percentage, r.filepath, r.image_settings.file_format, scene.camera, scene.cycles.samples)
    pc = bpy.data.cameras.new('probe'); pc.lens = 200; pc.clip_start = 0.01; pc.clip_end = 0.1; po = bpy.data.objects.new('probe', pc); scene.collection.objects.link(po)
    pc.lens = 50; r.resolution_x, r.resolution_y, r.resolution_percentage = 16, 2, 100; scene.cycles.samples = 16; scene.camera = po
    r.image_settings.file_format = 'OPEN_EXR'; acc = []
    for k in range(4):   # four compass directions, rays 1.5 to 6.5 degrees above the horizon
        po.location = (0, 0, 500); po.rotation_euler = (math.radians(94), 0, math.radians(90 * k))
        r.filepath = os.path.join(OUT, f'_probe_{preset}_{k}.exr'); bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(r.filepath); acc.append(np.array(img.pixels[:], dtype=np.float32).reshape(-1, 4)[:, :3].mean(axis=0)); bpy.data.images.remove(img); os.remove(r.filepath)
    rgb = tuple(float(v) for v in np.mean(acc, axis=0)); bpy.data.objects.remove(po); bpy.data.cameras.remove(pc)
    r.resolution_x, r.resolution_y, r.resolution_percentage, r.filepath, r.image_settings.file_format, scene.camera, scene.cycles.samples = keep
    print('haze', preset, [round(v, 4) for v in rgb]); _haze[preset] = rgb; return rgb


def lighting(preset):
    """day: high warm sun from the south-west; dusk: low sun, glowing windows"""
    elev, rot, energy, strength = (38, 215, 3.5, 0.55) if preset == 'day' else (7, 250, 1.6, 0.35)
    if PHYS_SKY: strength = 0.03 if preset == 'day' else 0.05      # the physical sky is radiometric: far brighter than the flat fallback colour
    so.rotation_euler = (math.radians(90 - elev), 0, math.radians(rot + 90))
    sun.energy = energy
    if sky is not None:
        sky.sun_elevation = math.radians(elev); sky.sun_rotation = math.radians(rot); wn.nodes['Background'].inputs['Strength'].default_value = strength
    if PHYS_SKY and HAZE is not None:
        rgb = horizon_haze(preset); m = max(max(rgb), 1e-6)
        HAZE.inputs['Color'].default_value = (rgb[0] / m, rgb[1] / m, rgb[2] / m, 1); HAZE.inputs['Strength'].default_value = m
    scene.view_settings.exposure = 0.15 if preset == 'day' else 0.6


def look_at(cam, target):
    d = (target[0] - cam.location[0], target[1] - cam.location[1], target[2] - cam.location[2]); yaw = math.atan2(d[1], d[0]); pitch = math.atan2(d[2], math.hypot(d[0], d[1]))
    cam.rotation_euler = (math.pi / 2 + pitch, 0, yaw - math.pi / 2)


cams = {}


def add_cam(name, pos_ft, target_ft, lens=35):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_end = 5000; co = bpy.data.objects.new(name, cd); scene.collection.objects.link(co)
    co.location = M(*pos_ft); look_at(co, M(*target_ft)); cams[name] = (co, pos_ft, target_ft, lens); return co


zone_c = {}
for zn in 'ABCD':
    zp = [v for v in cabin_pos.values() if v[3] == zn]; zone_c[zn] = (float(np.mean([v[0] for v in zp])), float(np.mean([v[1] for v in zp])), float(np.mean([v[2] for v in zp])))
L = (lake_c[0], lake_c[1], wse)
add_cam('overall', (L[0] - 820, L[1] - 760, wse + 470), (L[0] + 20, L[1] + 30, wse + 5), 30)
for zn in 'ABCD':
    mx, my, mz = zone_c[zn]; ax = math.atan2(my - L[1], mx - L[0])   # camera outside the zone looking back over the cabins toward the lake
    a = ax + math.radians(28); add_cam(zn, (mx + 235 * math.cos(a), my + 235 * math.sin(a), mz + 95), (mx - 20 * math.cos(ax), my - 20 * math.sin(ax), mz + 8), 45)
cxC, cyC, czC = zone_c['C']; ax = math.atan2(cyC - L[1], cxC - L[0])
add_cam('lake', (L[0] - 118 * math.cos(ax), L[1] - 118 * math.sin(ax), wse + 5.5), (cxC, cyC, czC + 10), 38)
hero_pos = (L[0] - 0.12 * (cxC - L[0]), L[1] - 0.12 * (cyC - L[1]), wse + 46)   # low over the water, looking at the mushroom row
add_cam('hero', hero_pos, (cxC, cyC, czC + 6), 30)
add_cam('hero_dusk', hero_pos, (cxC, cyC, czC + 6), 30)
# zone close-ups: the two cabins nearest each zone centre, seen from the lake side (fronts face the lane)
ZONE_NAME = {'A': 'haunted', 'B': 'swamp', 'C': 'mushroom', 'D': 'saucer'}
for zn in 'ABCD':
    zp = sorted([v for v in cabin_pos.values() if v[3] == zn], key=lambda v: (v[0] - zone_c[zn][0]) ** 2 + (v[1] - zone_c[zn][1]) ** 2)
    k0 = zp[0]; k1 = zp[1] if len(zp) > 1 else zp[0]
    tx, ty, tz = (k0[0] + k1[0]) / 2, (k0[1] + k1[1]) / 2, max(k0[2], k1[2])
    dl = math.hypot(L[0] - tx, L[1] - ty) or 1.0; ux, uy = (L[0] - tx) / dl, (L[1] - ty) / dl   # unit vector toward the lake
    a = math.atan2(uy, ux) + math.radians(24)                                                  # low drone, three-quarter angle
    px, py = tx + 120 * math.cos(a), ty + 120 * math.sin(a)
    add_cam(f'close_{zn}', (px, py, max(ground_z(px, py), wse + 2) + 36), (tx, ty, tz + 9), 42)
    gx, gy = k0[0] + 60 * ux - 20 * uy, k0[1] + 60 * uy + 20 * ux                             # visitor on the lane, a step to the side
    for nm in (f'ground_{zn}', f'ground_{zn}_dusk'):
        add_cam(nm, (gx, gy, max(ground_z(gx, gy), wse + 1) + 5.5), (k0[0], k0[1], k0[2] + 10), 26)
scene.camera = cams['overall'][0]; lighting('day')


def foreground_cull(name, on):
    """hide trees standing between a low camera and its subject so the cabins read clearly"""
    if name in ('overall',) or not tree_objs: return
    co, pos, tgt, lens = cams[name]; hfov = 2 * math.atan(18.0 / lens)
    dx, dy = tgt[0] - pos[0], tgt[1] - pos[1]; dist = math.hypot(dx, dy); ux, uy = dx / dist, dy / dist
    for objs, x, y, h in tree_objs:
        vx, vy = x - pos[0], y - pos[1]; along = vx * ux + vy * uy; lat = abs(-vx * uy + vy * ux)
        near = 0 < along < dist * 0.8 and lat < along * math.tan(hfov / 2) + 25
        for ob in objs: ob.hide_render = bool(on and near)


# ------------------------------------------------------------------ save, export, render
bpy.ops.wm.save_as_mainfile(filepath=f'{OUT}/florida_freedom_world_lakes_present.blend'); print('saved .blend')
if not args.no_glb:
    try:
        bpy.ops.export_scene.gltf(filepath=f'{OUT}/florida_freedom_world_lakes_present.glb', export_format='GLB', export_apply=False, use_visible=True,
                                  export_cameras=False, export_lights=False, export_yup=True)
        print('exported .glb', os.path.getsize(f'{OUT}/florida_freedom_world_lakes_present.glb') // 1024, 'KB')
    except Exception as ex:
        print('glb export skipped:', ex)
enrich_ground_material()
if args.renders:
    for name in [v for v in args.views.split(',') if v]:
        lighting('dusk' if name.endswith('_dusk') else 'day'); scene.camera = cams[name][0]; foreground_cull(name, True)
        scene.render.filepath = f'{OUT}/render_{name}.png'; bpy.ops.render.render(write_still=True); foreground_cull(name, False); print('rendered', name, flush=True)
if args.turntable:
    lighting('day'); scene.render.resolution_x, scene.render.resolution_y = map(int, args.tt_res.split('x')); scene.cycles.samples = args.tt_samples
    R, Hc = args.tt_radius, args.tt_height
    cam = add_cam('turntable', (L[0] + R, L[1], wse + Hc), (L[0], L[1], wse + 10), 32); scene.camera = cam; os.makedirs(f'{OUT}/turntable', exist_ok=True)
    for f in range(args.tt_start, args.turntable):
        a = 2 * math.pi * f / args.turntable; cam.location = M(L[0] + R * math.cos(a), L[1] + R * math.sin(a), wse + Hc); look_at(cam, M(L[0], L[1], wse + 10))
        scene.render.filepath = f'{OUT}/turntable/frame_{f:03d}.png'; bpy.ops.render.render(write_still=True); print('turntable frame', f, flush=True)
print('done')
