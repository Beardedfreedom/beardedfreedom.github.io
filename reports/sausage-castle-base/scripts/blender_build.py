#!/usr/bin/env python3
"""Florida Freedom World, lake zones: build the cleared and graded site with all 22 cabins in Blender, render stills, save .blend and .glb.

Run inside Blender (3.6 or newer, 4.x recommended):
    blender --background --python scripts/blender_build.py -- --base reports/sausage-castle-base --out reports/sausage-castle-base/mockup/blender --renders --samples 64
or with the pip "bpy" module (Python 3.11):
    python3 scripts/blender_build.py --base ... --out ... --renders

Inputs (all produced by the other scripts in this folder):
    viewer/data/meta.json                 zone extents, heightmap encodings, cleared variant for the lakes zone
    viewer/data/lakes_cleared_surface.png cleared surface heightmap (RGB-encoded: z = (R*256+G)*0.01 + zmin, row 0 = north)
    viewer/data/lakes_cleared_ground.png  graded bare earth
    viewer/data/lakes_cleared_color.jpg   land-cover colour texture
    viewer/data/units.json                cabin meshes (parts with colours) and placements with z_graded
    focus/lakes/clearing_grading.json     ids of trees removed
    focus/lakes/sausage_castle_lakes_focus_EPSG2236_ftUS.dxf   kept trees and lake outlines (optional, needs ezdxf)
Coordinates: the scene origin is the lakes-zone centre; feet are converted to metres; +Y is north, +Z is up.
"""
import sys, os, json, math, argparse
try:
    import bpy, bmesh
except ImportError:
    sys.exit('This script needs Blender: run it with `blender --background --python scripts/blender_build.py -- ...` or install the bpy wheel.')
import numpy as np
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
ap = argparse.ArgumentParser(); ap.add_argument('--base', default='.'); ap.add_argument('--out', default='mockup/blender'); ap.add_argument('--renders', action='store_true'); ap.add_argument('--samples', type=int, default=64)
ap.add_argument('--res', default='1600x900'); ap.add_argument('--step', type=int, default=1, help='heightmap subsampling (1 = full 2 ft grid)'); ap.add_argument('--no-trees', action='store_true'); ap.add_argument('--views', default='overall,A,B,C,D')
args = ap.parse_args(argv); BASE = os.path.abspath(args.base); OUT = os.path.abspath(args.out); os.makedirs(OUT, exist_ok=True); FT = 0.3048
VD = f'{BASE}/viewer/data'; meta = json.load(open(f'{VD}/meta.json')); z = meta['zones']['lakes']; c = z['cell_ft']; x0, y0 = z['x0'], z['y0']
cx, cy = x0 + z['width_ft'] / 2, y0 + z['height_ft'] / 2; zmin = z['z_range'][0]
def load_img(path):
    im = bpy.data.images.load(path, check_existing=True); w, h = im.size; px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4); return im, px   # row 0 = bottom (south)
def decode(spec):
    _, px = load_img(f"{VD}/{spec['file']}"); r = np.round(px[..., 0] * 255); g = np.round(px[..., 1] * 255); return (r * 256 + g) * spec['scale'] + spec['zmin']    # row 0 = south
def M(x, y, zz): return ((x - cx) * FT, (y - cy) * FT, (zz - zmin) * FT)

bpy.ops.wm.read_factory_settings(use_empty=True); scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'; scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'; scene.cycles.samples = args.samples; scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = map(int, args.res.split('x')); scene.render.film_transparent = False; scene.view_settings.view_transform = 'Filmic' if 'Filmic' in [v.identifier for v in scene.view_settings.bl_rna.properties['view_transform'].enum_items] else 'AgX'
def mat(name, color, rough=0.8, metal=0.0, emit=0.0, alpha=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']; rgb = tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if emit: b.inputs['Emission Color'].default_value = (*rgb, 1) if 'Emission Color' in b.inputs else None; b.inputs['Emission Strength'].default_value = emit
    if alpha < 1: b.inputs['Alpha'].default_value = alpha; m.blend_method = 'BLEND'
    return m
def mesh_obj(name, verts, faces, material=None, coll=None):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.validate(); me.update(); ob = bpy.data.objects.new(name, me)
    (coll or scene.collection).objects.link(ob)
    if material: me.materials.append(material)
    return ob
def collection(name): col = bpy.data.collections.new(name); scene.collection.children.link(col); return col

# ---- terrain (cleared surface with the land-cover texture)
H = decode(z['cleared']['surface']); ny, nx = H.shape; st = args.step; Hs = H[::st, ::st]; hy, hx = Hs.shape
verts = [M(x0 + (i * st + 0.5) * c, y0 + (j * st + 0.5) * c, Hs[j, i]) for j in range(hy) for i in range(hx)]
faces = [(j * hx + i, j * hx + i + 1, (j + 1) * hx + i + 1, (j + 1) * hx + i) for j in range(hy - 1) for i in range(hx - 1)]
tcol = collection('Terrain'); tmat = bpy.data.materials.new('Terrain'); tmat.use_nodes = True; nt = tmat.node_tree; tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = bpy.data.images.load(f"{VD}/{z['cleared']['color']}", check_existing=True)
nt.links.new(tex.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color']); nt.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.95
terrain = mesh_obj('Terrain_cleared', verts, faces, tmat, tcol)
uv = terrain.data.uv_layers.new(name='UVMap')
for poly in terrain.data.polygons:
    for li in poly.loop_indices:
        vi = terrain.data.loops[li].vertex_index; j, i = divmod(vi, hx); uv.data[li].uv = (i / max(hx - 1, 1), j / max(hy - 1, 1))
for p in terrain.data.polygons: p.use_smooth = True
print('terrain', hx, 'x', hy)

# ---- water and kept trees from the focus DXF (optional)
removed = set(t['id'] for t in json.load(open(f'{BASE}/focus/lakes/clearing_grading.json'))['trees_removed'])
try:
    import ezdxf
    d0 = ezdxf.readfile(f'{BASE}/focus/lakes/sausage_castle_lakes_focus_EPSG2236_ftUS.dxf'); ms = d0.modelspace()
    wcol = collection('Water'); wmat = mat('Water', '#2f6f9f', rough=0.05); wmat.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level' if 'Specular IOR Level' in wmat.node_tree.nodes['Principled BSDF'].inputs else 'Specular'].default_value = 0.8
    for e in ms.query('LWPOLYLINE[layer=="C-WATR-LIDAR"]'):
        pts = [(p[0], p[1]) for p in e.get_points()]; wse = e.dxf.elevation or 70.0
        bm = bmesh.new(); vs = [bm.verts.new(M(x, y, wse + 0.2)) for x, y in pts]; bm.faces.new(vs); me = bpy.data.meshes.new('Lake'); bm.to_mesh(me); ob = bpy.data.objects.new('Lake', me); wcol.objects.link(ob); me.materials.append(wmat)
    if not args.no_trees:
        trcol = collection('Trees'); crown = mat('Crown', '#2f7a3a', rough=0.9); trunk = mat('Trunk', '#4a3a2c')
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1.0); crown_ob = bpy.context.active_object; crown_ob.name = 'CrownProto'; crown_ob.data.materials.append(crown); scene.collection.objects.unlink(crown_ob)
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.18, depth=1.0); trunk_ob = bpy.context.active_object; trunk_ob.name = 'TrunkProto'; trunk_ob.data.materials.append(trunk); scene.collection.objects.unlink(trunk_ob)
        G = decode(z['cleared']['ground'])
        i = 0
        for e in ms.query('CIRCLE[layer=="L-PLNT-TREE"]'):
            i += 1
            if i in removed: continue
            x, y, r = e.dxf.center.x, e.dxf.center.y, e.dxf.radius; gi, gj = min(max(int((x - x0) / c), 0), nx - 1), min(max(int((y - y0) / c), 0), ny - 1); gz = G[gj, gi]; h = max(12.0, r * 2.2)
            t = bpy.data.objects.new(f'Trunk_{i}', trunk_ob.data); t.location = M(x, y, gz + h * 0.5 * 0.55 / 0.5); t.scale = (1, 1, h * 0.55 * FT); t.location = (t.location[0], t.location[1], (gz - zmin) * FT + h * 0.55 * FT / 2); trcol.objects.link(t)
            k = bpy.data.objects.new(f'Crown_{i}', crown_ob.data); k.location = ((x - cx) * FT, (y - cy) * FT, (gz - zmin + h * 0.7) * FT); k.scale = (r * FT, r * FT, h * 0.45 * FT); trcol.objects.link(k)
        print('trees placed', len(trcol.objects) // 2)
except Exception as ex:
    print('water/trees skipped:', ex)

# ---- cabins
units = json.load(open(f'{VD}/units.json')); ucol = collection('Cabins'); protos = {}
EMIT = {'portholes': 6.0, 'windows': 3.0, 'led ring': 8.0, 'skylight': 1.5, 'dome': 0.0}
for key, u in units['units'].items():
    parts = []
    for part in u['parts']:
        V = np.array(part['positions']).reshape(-1, 3) * FT; F = np.array(part['indices']).reshape(-1, 3)
        m = mat(f"{key}_{part['name']}", part['color'], rough=0.35 if key == 'ufo' else 0.75, metal=0.7 if (key == 'ufo' and part['name'] in ('hull', 'legs', 'ramp')) else 0.0, emit=EMIT.get(part['name'], 0.0), alpha=0.55 if part['name'] == 'dome' else 1.0)
        parts.append(mesh_obj(f'{key}_{part["name"]}', [tuple(v) for v in V], [tuple(f) for f in F], m, ucol))
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts: p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]; bpy.ops.object.join(); proto = bpy.context.active_object; proto.name = f'UNIT_{key}'
    for p in proto.data.polygons: p.use_smooth = key in ('mushroom', 'ufo')
    proto.hide_render = True; proto.hide_viewport = True; protos[key] = proto
for pl in units['placements']:
    inst = bpy.data.objects.new(f"{pl['pad']}_{pl['unit']}", protos[pl['unit']].data); inst.location = M(pl['x'], pl['y'], pl.get('z_graded', pl['z'])); inst.rotation_euler = (0, 0, math.radians(pl['rot_deg'])); ucol.objects.link(inst)
print('cabins placed', len(units['placements']))

# ---- light, sky, cameras
sun = bpy.data.lights.new('Sun', 'SUN'); sun.energy = 4.0; sun.angle = math.radians(1.5); so = bpy.data.objects.new('Sun', sun); scene.collection.objects.link(so); so.rotation_euler = (math.radians(50), 0, math.radians(315 + 180))
world = bpy.data.worlds.new('Sky'); scene.world = world; world.use_nodes = True; wn = world.node_tree
try:
    sky = wn.nodes.new('ShaderNodeTexSky'); sky.sky_type = 'NISHITA'; sky.sun_elevation = math.radians(40); sky.sun_rotation = math.radians(135); sky.sun_intensity = 0.4; wn.links.new(sky.outputs['Color'], wn.nodes['Background'].inputs['Color']); wn.nodes['Background'].inputs['Strength'].default_value = 0.6
except Exception: wn.nodes['Background'].inputs['Color'].default_value = (0.55, 0.7, 0.9, 1)
lz = json.load(open(f'{BASE}/focus/lakes/lake_zones_concept.json')); pads = {p['id']: p for p in lz['pads']}
def look_at(cam, target):
    d = (target[0] - cam.location[0], target[1] - cam.location[1], target[2] - cam.location[2]); yaw = math.atan2(d[1], d[0]); pitch = math.atan2(d[2], math.hypot(d[0], d[1]))
    cam.rotation_euler = (math.pi / 2 + pitch, 0, yaw - math.pi / 2)
def add_cam(name, pos_ft, target_ft, lens=35):
    cd = bpy.data.cameras.new(name); cd.lens = lens; co = bpy.data.objects.new(name, cd); scene.collection.objects.link(co); co.location = M(*pos_ft); look_at(co, M(*target_ft)); return co
lake = lz['lake']['centroid']; cams = {}
cams['overall'] = add_cam('Cam_overall', (lake[0] - 900, lake[1] - 800, zmin + 520), (lake[0], lake[1] + 40, zmin + 5), 32)
for zn, az in (('A', 40), ('B', 150), ('C', 240), ('D', 320)):
    zp = [p for p in pads.values() if p['zone'] == zn]; mx, my = np.mean([p['center'][0] for p in zp]), np.mean([p['center'][1] for p in zp]); mz = np.mean([units['placements'][i].get('z_graded', 0) for i, pl in enumerate(units['placements']) if pl['zone'] == zn])
    a = math.radians(az); cams[zn] = add_cam(f'Cam_zone{zn}', (mx + 260 * math.cos(a), my + 260 * math.sin(a), mz + 110), (mx, my, mz + 8), 40)
scene.camera = cams['overall']
bpy.ops.wm.save_as_mainfile(filepath=f'{OUT}/florida_freedom_world_lakes.blend'); print('saved .blend')
try:
    for p in protos.values(): p.hide_viewport = False
    bpy.ops.export_scene.gltf(filepath=f'{OUT}/florida_freedom_world_lakes.glb', export_format='GLB', export_apply=True, use_visible=True); print('exported .glb')
    for p in protos.values(): p.hide_viewport = True
except Exception as ex: print('glb export skipped:', ex)
if args.renders:
    for name in args.views.split(','):
        scene.camera = cams[name]; scene.render.filepath = f'{OUT}/render_{name}.png'; bpy.ops.render.render(write_still=True); print('rendered', name)
print('done')
