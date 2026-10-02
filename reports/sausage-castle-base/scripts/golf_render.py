#!/usr/bin/env python3
"""Render the Gator Greens 3D CAD (masterplan/golf/golf_course_3d_EPSG2236_ftUS.dxf) with Blender's Cycles.

Builds a scene from the DXF meshes (one material per layer), the lidar ground around the course
(6 ft grid, coloured from the land-cover map), the lidar trees outside the holes as simple crowns,
and flags; renders an overview and eye-level views of a water carry and a sand carry.
Usage (pip bpy 5.x):  python3 scripts/golf_render.py [--samples 64] [--res 1600x900]
"""
import argparse, json, math, os, sys
import numpy as np
import bpy
import ezdxf
from PIL import Image

ap = argparse.ArgumentParser(); ap.add_argument('--base', default=os.path.join(os.path.dirname(__file__), '..'))
ap.add_argument('--samples', type=int, default=64); ap.add_argument('--res', default='1600x900'); ap.add_argument('--views', default='overview,water,sand,home')
args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
B = os.path.abspath(args.base); G = f'{B}/masterplan/golf'; FT = 0.3048
course = json.load(open(f'{G}/golf_course.json')); world = json.load(open(f'{B}/game/data/world.json'))
holes = course['holes']; allx = [c for h in holes for c in (h['tee'][0], h['green'][0])]; ally = [c for h in holes for c in (h['tee'][1], h['green'][1])]
CX, CY = (min(allx) + max(allx)) / 2, (min(ally) + max(ally)) / 2; ZB = 64.0
def M(x, y, z): return ((x - CX) * FT, (y - CY) * FT, (z - ZB) * FT)

bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = args.samples; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = map(int, args.res.split('x'))
try: sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception: pass

def mat(name, rgb, rough=0.8, metal=0.0, spec=None, emit=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    lin = tuple(((v / 255 + 0.055) / 1.055) ** 2.4 if v / 255 > 0.04045 else v / 255 / 12.92 for v in rgb)
    b.inputs['Base Color'].default_value = (*lin, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if spec is not None: b.inputs['Specular IOR Level'].default_value = spec
    if emit: b.inputs['Emission Color'].default_value = (*lin, 1); b.inputs['Emission Strength'].default_value = emit
    return m
MATS = {'L-GOLF-FWY-3D': mat('fairway', (92, 150, 60), 0.85), 'L-GOLF-GRN-3D': mat('green', (60, 175, 70), 0.6), 'L-GOLF-TEE-3D': mat('tee', (120, 185, 85), 0.7),
        'L-GOLF-BNKR-3D': mat('sand', (232, 214, 160), 0.95), 'L-GOLF-POND-BED-3D': mat('bed', (90, 75, 50), 0.9),
        'L-GOLF-WATR-3D': mat('water', (30, 70, 80), 0.04, spec=0.8)}
nt = MATS['L-GOLF-WATR-3D'].node_tree; bsdf = nt.nodes['Principled BSDF']
nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 60; bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.05
nt.links.new(nz.outputs['Fac'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])

doc = ezdxf.readfile(f'{G}/golf_course_3d_EPSG2236_ftUS.dxf'); msp = doc.modelspace(); n_mesh = 0
for e in msp.query('MESH'):
    V = [M(*v) for v in e.vertices]; F = [tuple(f) for f in e.faces]
    me = bpy.data.meshes.new(e.dxf.layer); me.from_pydata(V, [], F); me.update()
    ob = bpy.data.objects.new(e.dxf.layer, me); sc.collection.objects.link(ob); me.materials.append(MATS[e.dxf.layer]); n_mesh += 1
    if e.dxf.layer != 'L-GOLF-WATR-3D':
        for p in me.polygons: p.use_smooth = True
print('meshes', n_mesh)
pole_m = mat('pole', (245, 245, 240), 0.4); flag_m = mat('flag', (224, 38, 43), 0.6)
for ln in msp.query('LINE[layer=="L-GOLF-FLAG"]'):
    a, b = ln.dxf.start, ln.dxf.end; bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.04, depth=(b[2] - a[2]) * FT, location=M(a[0], a[1], (a[2] + b[2]) / 2))
    bpy.context.active_object.data.materials.append(pole_m)
for f in msp.query('3DFACE[layer=="L-GOLF-FLAG"]'):
    V = [M(*f.dxf.vtx0), M(*f.dxf.vtx1), M(*f.dxf.vtx2)]; me = bpy.data.meshes.new('flag'); me.from_pydata(V, [], [(0, 1, 2)]); ob = bpy.data.objects.new('flag', me); sc.collection.objects.link(ob); me.materials.append(flag_m)

# lidar ground around the course, coloured from the land-cover map
s = world['site']; import gzip
with gzip.open(f'{B}/sausage_castle_dtm_3ft_EPSG2236.asc.gz', 'rt') as fh:
    hdr = {}
    for _ in range(6):
        k, v = fh.readline().split(); hdr[k.lower()] = float(v)
    dtm = np.loadtxt(fh, dtype=np.float32)
dtm = np.where(dtm < -9000, np.nanmedian(np.where(dtm < -9000, np.nan, dtm)), dtm)
col = np.asarray(Image.open(f'{B}/game/data/site_color.jpg').convert('RGB'), dtype=np.float32) / 255.0
pad = 900; x0, x1, y0, y1 = min(allx) - pad, max(allx) + pad, min(ally) - pad, max(ally) + pad
def zb(X, Y):   # bilinear on the 3 ft DTM, cell-centred: the same surface golf_3d.py ties the holes into
    fi = (X - hdr['xllcorner']) / hdr['cellsize'] - 0.5; fj = (hdr['nrows'] - 1) - ((Y - hdr['yllcorner']) / hdr['cellsize'] - 0.5)
    i0 = np.clip(np.floor(fi), 0, dtm.shape[1] - 2).astype(int); j0 = np.clip(np.floor(fj), 0, dtm.shape[0] - 2).astype(int); ti = np.clip(fi - i0, 0, 1); tj = np.clip(fj - j0, 0, 1)
    return dtm[j0, i0] * (1 - ti) * (1 - tj) + dtm[j0, i0 + 1] * ti * (1 - tj) + dtm[j0 + 1, i0] * (1 - ti) * tj + dtm[j0 + 1, i0 + 1] * ti * tj
from shapely.geometry import Point as _P, LineString as _LS
from shapely.ops import unary_union as _uu
from shapely.prepared import prep as _prep
cut_out = _prep(_uu([_uu([_LS([tuple(h['tee']), tuple(h['green'])]).buffer(48, cap_style=2), _P(*h['green']).buffer(55), _P(*h['tee']).buffer(28)]).buffer(-6) for h in holes]))   # the hole corridors, eroded so the ground tucks under their edges
inner = (min(allx) - 150, max(allx) + 150, min(ally) - 150, max(ally) + 150)
gm = bpy.data.materials.new('ground'); gm.use_nodes = True; gn = gm.node_tree; attr = gn.nodes.new('ShaderNodeAttribute'); attr.attribute_name = 'Cover'
gn.links.new(attr.outputs['Color'], gn.nodes['Principled BSDF'].inputs['Base Color']); gn.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.9
def ground_mesh(name, bx0, bx1, by0, by1, st, dz, keep):
    xs = np.arange(bx0, bx1 + st, st); ys = np.arange(by0, by1 + st, st); XX, YY = np.meshgrid(xs, ys); ZZ = zb(XX, YY) + dz
    cj = ((s['y0'] + s['h'] - YY) / s['h'] * col.shape[0]).astype(int).clip(0, col.shape[0] - 1); ci = ((XX - s['x0']) / s['w'] * col.shape[1]).astype(int).clip(0, col.shape[1] - 1); CC = col[cj, ci]
    V = [M(x, y, z) for x, y, z in zip(XX.ravel(), YY.ravel(), ZZ.ravel())]; W_ = len(xs)
    F = [(a * W_ + b, a * W_ + b + 1, (a + 1) * W_ + b + 1, (a + 1) * W_ + b) for a in range(len(ys) - 1) for b in range(W_ - 1) if keep(xs[b] + st / 2, ys[a] + st / 2)]
    me = bpy.data.meshes.new(name); me.from_pydata(V, [], F); me.update()
    ca = me.color_attributes.new('Cover', 'FLOAT_COLOR', 'POINT')
    for k, c in enumerate(CC.reshape(-1, 3)): ca.data[k].color = (float(c[0]) ** 2.2, float(c[1]) ** 2.2, float(c[2]) ** 2.2, 1)
    me.materials.append(gm); ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    for p in me.polygons: p.use_smooth = True
    return len(F)
na = ground_mesh('ground_near', *inner, 3.0, -0.08, lambda x, y: not cut_out.contains(_P(x, y)))
nb = ground_mesh('ground_far', x0, x1, y0, y1, 9.0, -0.35, lambda x, y: not (inner[0] + 9 < x < inner[1] - 9 and inner[2] + 9 < y < inner[3] - 9))
print('ground faces', na, nb)

# distant land so the camera never sees the black sky below the horizon
bpy.ops.mesh.primitive_plane_add(size=20000, location=M(CX, CY, float(np.percentile(dtm, 5)) - 1.0)); far = bpy.context.active_object
far.data.materials.append(mat('far', (78, 110, 62), 0.95))

# trees outside the holes (lidar crowns) as simple instanced crowns
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union
from shapely.prepared import prep
holes_u = prep(unary_union([LineString([tuple(h['tee']), tuple(h['green'])]).buffer(60) for h in holes]))
oak = mat('oak', (52, 95, 40), 0.85); pine = mat('pine', (40, 80, 45), 0.85); trunk = mat('trunk', (90, 70, 50), 0.9)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0); crown_o = bpy.context.active_object; crown_o.data.materials.append(oak); crown_o.hide_render = True
bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=1.0, depth=2.0); crown_p = bpy.context.active_object; crown_p.data.materials.append(pine); crown_p.hide_render = True
bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=1.0, depth=1.0); stem = bpy.context.active_object; stem.data.materials.append(trunk); stem.hide_render = True
nt_ = 0
for t in world['trees']:
    x, y, h, r, kind = t
    if not (x0 + 200 < x < x1 - 200 and y0 + 200 < y < y1 - 200) or holes_u.contains(Point(x, y)): continue
    j = int(hdr['nrows'] - 1 - (y - hdr['yllcorner']) / hdr['cellsize']); i = int((x - hdr['xllcorner']) / hdr['cellsize']); gz = float(dtm[min(max(j, 0), dtm.shape[0] - 1), min(max(i, 0), dtm.shape[1] - 1)])
    proto = crown_p if kind == 1 else crown_o; ob = bpy.data.objects.new('tree', proto.data); sc.collection.objects.link(ob)
    if kind == 1: ob.location = M(x, y, gz + h * 0.62); ob.scale = (r * 0.7 * FT, r * 0.7 * FT, h * 0.38 * FT)
    else: ob.location = M(x, y, gz + h * 0.62); ob.scale = (r * FT, r * FT, h * 0.36 * FT)
    st_ = bpy.data.objects.new('stem', stem.data); sc.collection.objects.link(st_); st_.location = M(x, y, gz + h * 0.15); st_.scale = (0.35 * FT * 2, 0.35 * FT * 2, h * 0.32 * FT)
    nt_ += 1
print('trees', nt_)

# sky and sun
sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 3.2; sun.angle = math.radians(1.5); so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so)
so.rotation_euler = (math.radians(50), 0, math.radians(220))
w = bpy.data.worlds.new('sky'); sc.world = w; w.use_nodes = True; wn = w.node_tree; sky = wn.nodes.new('ShaderNodeTexSky')
types = [i.identifier for i in sky.bl_rna.properties['sky_type'].enum_items]; sky.sky_type = next(t for t in ('NISHITA', 'MULTIPLE_SCATTERING', 'HOSEK_WILKIE') if t in types)
sky.sun_elevation = math.radians(40); sky.sun_rotation = math.radians(130)
wn.links.new(sky.outputs['Color'], wn.nodes['Background'].inputs['Color']); wn.nodes['Background'].inputs['Strength'].default_value = 0.03 if sky.sky_type != 'HOSEK_WILKIE' else 0.3
sc.view_settings.exposure = 0.2

def look(cam, tgt):
    d = (tgt[0] - cam.location[0], tgt[1] - cam.location[1], tgt[2] - cam.location[2])
    cam.rotation_euler = (math.pi / 2 + math.atan2(d[2], math.hypot(d[0], d[1])), 0, math.atan2(d[1], d[0]) - math.pi / 2)
def cam(name, pos, tgt, lens):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_end = 5000; co = bpy.data.objects.new(name, cd); sc.collection.objects.link(co); co.location = M(*pos); look(co, M(*tgt)); return co
def hole(n): return next(h for h in holes if h['hole'] == n)
views = {}
ox, oy = (min(allx) + max(allx)) / 2, (min(ally) + max(ally)) / 2
views['overview'] = cam('overview', (ox + 700, oy - 1250, 1250), (ox - 40, oy + 60, 70), 30)
def behind_tee(n, back=150, up=32.0, lens=32):
    h = hole(n); tx, ty = h['tee']; gx, gy = h['green']; L = math.hypot(gx - tx, gy - ty); ux, uy = (gx - tx) / L, (gy - ty) / L
    return cam(f'h{n}', (tx - ux * back, ty - uy * back, h['tee_z_ft'] + up), (tx + ux * L * 0.75, ty + uy * L * 0.75, h['green_z_ft'] - 2), lens)
wh = course['hazards']['water_carry_holes']; sh = course['hazards']['sand_carry_holes']
views['water'] = behind_tee(wh[0]); views['sand'] = behind_tee(sh[0])
h18 = hole(18); views['home'] = cam('home', (h18['green'][0] + 160, h18['green'][1] - 220, h18['green_z_ft'] + 45), (h18['green'][0], h18['green'][1], h18['green_z_ft']), 35)
for name in [v for v in args.views.split(',') if v]:
    sc.camera = views[name]; sc.render.filepath = f'{G}/golf_3d_{name}.png'; bpy.ops.render.render(write_still=True)
    Image.open(sc.render.filepath).convert('RGB').save(f'{G}/golf_3d_{name}.jpg', quality=88); os.remove(sc.render.filepath); print('rendered', name, flush=True)
