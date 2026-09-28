#!/usr/bin/env python3
"""Parametric tiny-home massing models for three themes (mushroom, haunted house, Florida swamp).
Local unit coordinates in feet: X along the pad width (parallel to the lane), Y = pad depth (front toward the lane is -Y), Z up.
Outputs per unit: DXF (3D mesh parts + 2D plan), JSON mesh for the viewer, sheet PNG (plan, elevations, axon).
Then: placement of units on the lake-zone pads (DXF with blocks + JSON for the viewer)."""
import json, math, os, datetime
import numpy as np, ezdxf
from ezdxf.render import MeshBuilder
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.patches import Rectangle, Circle, Polygon as MPoly, Arc
from shapely.geometry import LineString, Point, shape
from shapely.ops import transform as shp_transform
from pyproj import Transformer

BASE = '/home/user/beardedfreedom.github.io/reports/sausage-castle-base'; OUT = f'{BASE}/units'; os.makedirs(OUT, exist_ok=True)

# ---------------- mesh primitives ----------------
class Part:
    def __init__(self, name, color): self.name, self.color, self.v, self.f = name, color, [], []
    def add_face(self, pts):   # polygon (list of xyz), fan triangulated, outward order given by caller
        base = len(self.v); self.v += [tuple(map(float, p)) for p in pts]
        for i in range(1, len(pts) - 1): self.f.append((base, base + i, base + i + 1))
    def box(self, x0, x1, y0, y1, z0, z1):
        a = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)]; b = [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        self.add_face(a[::-1]); self.add_face(b)
        for i in range(4): j = (i + 1) % 4; self.add_face([a[i], a[j], b[j], b[i]])
    def prism(self, poly, z0, z1):   # vertical extrusion of a CCW 2D polygon
        n = len(poly); bot = [(x, y, z0) for x, y in poly]; top = [(x, y, z1) for x, y in poly]
        self.add_face(bot[::-1]); self.add_face(top)
        for i in range(n): j = (i + 1) % n; self.add_face([bot[i], bot[j], top[j], top[i]])
    def lathe(self, profile, cx=0, cy=0, seg=32, z_shift=0):   # profile [(r, z)] from top to bottom, closed by axis
        rings = [[(cx + r * math.cos(2 * math.pi * k / seg), cy + r * math.sin(2 * math.pi * k / seg), z + z_shift) for k in range(seg)] for r, z in profile]
        for i in range(len(profile) - 1):
            for k in range(seg):
                j = (k + 1) % seg; a, b, c, d = rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]
                if profile[i][0] < 1e-6: self.add_face([a, c, d])
                elif profile[i + 1][0] < 1e-6: self.add_face([a, b, c])
                else: self.add_face([a, b, c, d])
    def cylinder(self, cx, cy, r, z0, z1, seg=24): self.lathe([(0, z1), (r, z1), (r, z0), (0, z0)], cx, cy, seg)
    def cone(self, cx, cy, r, z0, z1, seg=16): self.lathe([(0, z1), (r, z0), (0, z0)], cx, cy, seg)
    def gable(self, x0, x1, y0, y1, ze, zr, along='y', oh=1.5, thick=0.6):   # ridge along axis; overhang oh
        if along == 'y':
            mx = (x0 + x1) / 2; sec = [(x0 - oh, ze - oh * (zr - ze) / ((x1 - x0) / 2)), (mx, zr), (x1 + oh, ze - oh * (zr - ze) / ((x1 - x0) / 2))]
            for s in (1, -1):
                pts = [(x, y0 - oh, z) for x, z in sec] if s == 1 else [(x, y1 + oh, z) for x, z in sec]
                self.add_face(pts if s == -1 else pts[::-1])   # gable ends (thin slab look via prism below)
            for i in range(2):
                (xa, za), (xb, zb) = sec[i], sec[i + 1]
                quad = [(xa, y0 - oh, za), (xb, y0 - oh, zb), (xb, y1 + oh, zb), (xa, y1 + oh, za)]
                self.add_face(quad if i == 0 else quad[::-1]); self.add_face([(x, y, z + thick) for x, y, z in (quad[::-1] if i == 0 else quad)])
        else:
            my = (y0 + y1) / 2; sec = [(y0 - oh, ze - oh * (zr - ze) / ((y1 - y0) / 2)), (my, zr), (y1 + oh, ze - oh * (zr - ze) / ((y1 - y0) / 2))]
            for s in (1, -1):
                pts = [(x0 - oh, y, z) for y, z in sec] if s == 1 else [(x1 + oh, y, z) for y, z in sec]
                self.add_face(pts if s == 1 else pts[::-1])
            for i in range(2):
                (ya, za), (yb, zb) = sec[i], sec[i + 1]
                quad = [(x0 - oh, ya, za), (x0 - oh, yb, zb), (x1 + oh, yb, zb), (x1 + oh, ya, za)]
                self.add_face(quad if i == 1 else quad[::-1]); self.add_face([(x, y, z + thick) for x, y, z in (quad[::-1] if i == 1 else quad)])
    def hip(self, x0, x1, y0, y1, ze, zr, oh=2.5, thick=0.5):   # hip roof, ridge along the longer axis
        x0, x1, y0, y1 = x0 - oh, x1 + oh, y0 - oh, y1 + oh; ze = ze - oh * (zr - ze) / (min(x1 - x0, y1 - y0) / 2 + oh)
        w, d = x1 - x0, y1 - y0; h = zr - ze
        if w >= d: rl = w - d; ra, rb = ((x0 + x1) / 2 - rl / 2, (y0 + y1) / 2, zr), ((x0 + x1) / 2 + rl / 2, (y0 + y1) / 2, zr)
        else: rl = d - w; ra, rb = ((x0 + x1) / 2, (y0 + y1) / 2 - rl / 2, zr), ((x0 + x1) / 2, (y0 + y1) / 2 + rl / 2, zr)
        c = [(x0, y0, ze), (x1, y0, ze), (x1, y1, ze), (x0, y1, ze)]
        faces = ([[c[0], c[1], rb, ra], [c[1], c[2], rb], [c[2], c[3], ra, rb], [c[3], c[0], ra]] if w >= d else [[c[0], c[1], ra], [c[1], c[2], rb, ra], [c[2], c[3], rb], [c[3], c[0], ra, rb]])
        for f in faces: self.add_face(f); self.add_face([(x, y, z + thick) for x, y, z in f[::-1]])
    def octagon(self, cx, cy, r, z0, z1):
        self.prism([(cx + r * math.cos(math.pi / 8 + k * math.pi / 4), cy + r * math.sin(math.pi / 8 + k * math.pi / 4)) for k in range(8)], z0, z1)
    def stairs(self, x0, x1, y_front, y_back, z0, z1, n):
        for i in range(n):
            t = i / n; self.box(x0, x1, y_front + (y_back - y_front) * t, y_back, z0, z0 + (z1 - z0) * (i + 1) / n)

class Unit:
    def __init__(self, key, name, theme): self.key, self.name, self.theme, self.parts, self.plan, self.spec = key, name, theme, [], {'walls': [], 'rooms': [], 'labels': [], 'doors': [], 'windows': [], 'deck': [], 'roof': []}, {}
    def part(self, name, color): p = Part(name, color); self.parts.append(p); return p
    def nfaces(self): return sum(len(p.f) for p in self.parts)

def circle(cx, cy, r, n=32): return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]

# ---------------- 1. mushroom ----------------
def mushroom():
    u = Unit('mushroom', 'Amanita cottage', 'mushroom')
    R, H = 9.0, 9.5                               # stem radius (18 ft dia), wall height
    stem = u.part('stem', '#efe4cc'); stem.cylinder(0, 4, R, 0.5, H, 40)
    plinth = u.part('plinth', '#c9bda0'); plinth.cylinder(0, 4, R + 0.6, 0, 0.5, 40)
    cap = u.part('cap', '#c0392b')
    prof = [(0, 23.5), (4, 23.2), (8, 22.0), (11, 20.0), (13, 17.5), (14.5, 14.0), (15, 11.8)]   # top skin
    cap.lathe(prof, 0, 4, 48)
    gills = u.part('gills', '#e8d9b5'); gills.lathe([(15, 11.8), (14.6, 10.8), (12, 9.8), (R + 0.1, 9.6), (R + 0.1, H), (0, H)], 0, 4, 48)
    spots = u.part('spots', '#fbf6ea')
    for k, (ang, rr, zz, sr) in enumerate([(20, 6, 22.5, 2.0), (95, 10, 20.4, 2.6), (160, 4, 23.0, 1.5), (210, 11.5, 19.2, 2.2), (275, 8, 21.7, 2.4), (330, 12.5, 18.2, 1.8)]):
        a = math.radians(ang); cx, cy = rr * math.cos(a), 4 + rr * math.sin(a)
        spots.lathe([(0, zz + 0.9), (sr * 0.7, zz + 0.7), (sr, zz + 0.1), (sr, zz - 0.8), (0, zz - 0.8)], cx, cy, 18)
    sky = u.part('skylight', '#5a8fa8'); sky.cylinder(0, 4, 2.2, 23.3, 23.9, 24)
    win = u.part('windows', '#3f7a8a')
    for ang in (35, 145, 215, 325):
        a = math.radians(ang); cx, cy = R * math.cos(a), 4 + R * math.sin(a)
        win.lathe([(0, 5.6), (1.6, 5.6), (1.6, 5.2), (0, 5.2)], cx, cy, 20)   # round porthole discs (rendered as flat pucks)
    door = u.part('door', '#7a4a2b'); door.box(-1.8, 1.8, 4 - R - 0.4, 4 - R + 0.2, 0.5, 7.5)
    deck = u.part('deck', '#a67c52'); deck.prism([(x, y) for x, y in circle(0, 4 - R + 1, 6.5, 24) if y < 4 - R + 0.5] + [(-6.5, 4 - R + 0.5), (6.5, 4 - R + 0.5)][::-1], 0, 0.5)
    deck.stairs(-2.5, 2.5, 4 - R - 9.5, 4 - R - 6.0, 0, 0.5, 2)
    pod_c = (-12.5, -6); pods = u.part('pod stem', '#efe4cc'); pods.cylinder(*pod_c, 3.6, 0, 7.5, 24)
    podc = u.part('pod cap', '#d35400'); podc.lathe([(0, 12.5), (2.5, 12.2), (4.8, 10.6), (6.0, 8.8), (6.2, 7.6), (5.4, 6.9), (3.7, 7.0), (3.7, 7.5), (0, 7.5)], *pod_c, 32)
    link = u.part('link', '#efe4cc'); link.box(-9.6, -6.2, -8.0, -4.0, 0.5, 7.2)
    # plan
    p = u.plan; p['walls'] = [circle(0, 4, R), circle(*pod_c, 3.6), [(-9.6, -8), (-6.2, -8), (-6.2, -4), (-9.6, -4)]]
    p['rooms'] = [('LIVING / KITCHEN', (0, 6.5), 254), ('SLEEP LOFT ABOVE (in cap)', (0, 2.5), 120), ('BATH POD', pod_c, 38), ('LINK', (-7.9, -6), 14), ('DECK', (0, -6.5), 55)]
    p['doors'] = [((-1.8, 4 - R), (1.8, 4 - R))]; p['windows'] = [(R * math.cos(math.radians(a)), 4 + R * math.sin(math.radians(a))) for a in (35, 145, 215, 325)]
    p['deck'] = [[(x, y) for x, y in circle(0, 4 - R + 1, 6.5, 24) if y < 4 - R + 0.5]]; p['roof'] = [circle(0, 4, 15), circle(*pod_c, 6.2)]
    p['furn'] = [('spiral stair', Circle((5.5, 7.5), 2.2)), ('kitchen', Rectangle((-8, 8), 6, 2)), ('sofa', Rectangle((-3, -1.5), 6, 2.2)), ('wc', Rectangle((-14.2, -4.5), 1.6, 2)), ('shower', Rectangle((-14.5, -8.6), 3, 3))]
    u.spec = dict(footprint='18 ft diameter stem, 30 ft diameter cap, plus 7 ft bath pod', floor_sf=254, loft_sf=120, pod_sf=38, gross_sf=412, height_ft=24, pad='fits 35 x 50 pad with 2.5 ft to spare each side',
                  materials='Stem: shotcrete or SIP panels with lime plaster; cap: sprayed foam roof over steel ribs, elastomeric coating in red with cream spots; gill soffit: tongue-and-groove cypress; porthole windows 3 ft round; oak plank deck',
                  concept='A single tall-stemmed amanita with the sleeping loft inside the cap, a round skylight at the crown, and a baby mushroom as the bathroom pod. The cap overhangs 6 ft all round so the stem stays in shade.',
                  florida='Round shell sheds hurricane wind well; foam roof needs Miami-Dade rated coating; raise finished floor 18 in on a slab plinth; mechanical closet in the link.')
    return u

# ---------------- 2. haunted house ----------------
def haunted():
    u = Unit('haunted', "Widow's Peak", 'haunted house')
    W, D, F, WALL = 14.0, 24.0, 3.0, 10.0              # width, depth, raised floor, wall height
    x0, x1, y0, y1 = -W / 2, W / 2, -6, -6 + D
    base = u.part('foundation', '#4a4a4a'); base.box(x0 + 0.5, x1 - 0.5, y0 + 0.5, y1 - 0.5, 0, F)
    lattice = u.part('lattice', '#2f2f35'); lattice.box(x0, x1, y0, y0 + 0.3, 0, F)
    walls = u.part('walls', '#3b3a48'); walls.prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], F, F + WALL)
    roof = u.part('roof', '#242428'); roof.gable(x0, x1, y0, y1, F + WALL, F + WALL + 15, along='y', oh=1.5)
    # cross gable over the entry (front)
    roof.gable(-4, 4, y0 - 2, y0 + 8, F + WALL - 0.2, F + WALL + 8, along='y', oh=1.0)
    attic = u.part('attic wall', '#3b3a48'); attic.prism([(x0, y0 + 0.05), (x1, y0 + 0.05), (0, y0 + 0.05)], F + WALL, F + WALL + 0.01)  # placeholder tiny
    # gable end triangles (front/back walls up to the ridge)
    for yy, s in ((y0, 1), (y1, -1)):
        tri = [(x0, yy, F + WALL), (x1, yy, F + WALL), (0, yy, F + WALL + 15)]
        walls.add_face(tri[::-1] if s == 1 else tri)
    turret = u.part('turret', '#33323f'); turret.octagon(x1 - 1, y0 + 3.5, 4.6, F, F + 18)
    hat = u.part('turret roof', '#1b1b1f'); hat.cone(x1 - 1, y0 + 3.5, 5.6, F + 18, F + 31, 16); hat.cylinder(x1 - 1, y0 + 3.5, 0.3, F + 31, F + 33, 8)
    porch = u.part('porch', '#6d6a75'); porch.box(x0 - 1, x1 - 5.5, y0 - 7, y0 + 0.2, F - 0.6, F)
    posts = u.part('posts', '#8a8794')
    for px in (x0 - 0.5, x0 + 3.5, x1 - 6.5):
        posts.box(px - 0.35, px + 0.35, y0 - 6.7, y0 - 6.0, F, F + 8.5)
    porch.gable(x0 - 1, x1 - 5.5, y0 - 7, y0 - 0.5, F + 8.5, F + 11.5, along='x', oh=0.8)
    rail = u.part('railing', '#8a8794'); rail.box(x0 - 1, x1 - 5.5, y0 - 7, y0 - 6.7, F + 0.6, F + 3.2); rail.box(x0 - 1, x0 - 0.7, y0 - 7, y0, F + 0.6, F + 3.2)
    porch.stairs(-1, 3, y0 - 12, y0 - 7, 0, F, 4)
    win = u.part('windows', '#f2c14e')
    for (wx, wy, along) in [(x0, y0 + 10, 'x'), (x0, y0 + 17, 'x'), (x1, y0 + 12, 'x'), (x1, y0 + 19, 'x'), (-3.5, y0, 'y'), (3.5, y0, 'y'), (-3, y1, 'y'), (3, y1, 'y')]:
        if along == 'x': win.box(wx - 0.25, wx + 0.25, wy - 1.2, wy + 1.2, F + 2.5, F + 8.5)
        else: win.box(wx - 1.2, wx + 1.2, wy - 0.25, wy + 0.25, F + 2.5, F + 8.5)
    win.cylinder(0, y0 - 0.1, 1.4, F + WALL + 4, F + WALL + 4.6, 20)   # round attic window (as a puck on the gable)
    for ang in (200, 250, 300):
        a = math.radians(ang); win.box(x1 - 1 + 4.6 * math.cos(a) - 0.6, x1 - 1 + 4.6 * math.cos(a) + 0.6, y0 + 3.5 + 4.6 * math.sin(a) - 0.6, y0 + 3.5 + 4.6 * math.sin(a) + 0.6, F + 3, F + 8)
    door = u.part('door', '#1a1a1a'); door.box(-2, 2, y0 - 0.3, y0 + 0.1, F, F + 8)
    chim = u.part('chimney', '#5a3a30'); chim.box(x0 + 3, x0 + 5, y1 - 5, y1 - 3, F + WALL + 6, F + WALL + 20)
    trim = u.part('trim', '#15151a'); trim.box(x0 - 0.3, x1 + 0.3, y0 - 0.3, y1 + 0.3, F + WALL - 0.4, F + WALL)
    weather = u.part('weathervane', '#8a8794'); weather.box(-0.1, 0.1, y0 + D / 2 - 0.1, y0 + D / 2 + 0.1, F + WALL + 15, F + WALL + 19)
    p = u.plan; p['walls'] = [[(x0, y0), (x1, y0), (x1, y1), (x0, y1)], [(x1 - 1 + 4.6 * math.cos(math.pi / 8 + k * math.pi / 4), y0 + 3.5 + 4.6 * math.sin(math.pi / 8 + k * math.pi / 4)) for k in range(8)]]
    p['rooms'] = [('PARLOUR', (-2, y0 + 5), 120), ('KITCHEN', (-2, y0 + 13), 90), ('BATH', (4, y0 + 17), 45), ('STAIR TO LOFT', (-4.5, y0 + 20.5), 30), ('TURRET READING NOOK', (x1 - 1, y0 + 3.5), 60), ('SLEEP LOFT ABOVE', (0, y0 + 9), 168), ('PORCH', (x0 + 3.7, y0 - 3.5), 78)]
    p['doors'] = [((-2, y0), (2, y0))]; p['windows'] = [(x0, y0 + 10), (x0, y0 + 17), (x1, y0 + 12), (x1, y0 + 19), (-3.5, y0), (3.5, y0), (-3, y1), (3, y1)]
    p['deck'] = [[(x0 - 1, y0 - 7), (x1 - 5.5, y0 - 7), (x1 - 5.5, y0), (x0 - 1, y0)]]; p['roof'] = [[(x0 - 1.5, y0 - 1.5), (x1 + 1.5, y0 - 1.5), (x1 + 1.5, y1 + 1.5), (x0 - 1.5, y1 + 1.5)]]
    p['furn'] = [('sofa', Rectangle((x0 + 1, y0 + 2), 2.5, 6)), ('kitchen', Rectangle((x0 + 0.5, y0 + 11), 2, 6)), ('wc', Rectangle((x1 - 3, y0 + 15.5), 1.6, 2)), ('shower', Rectangle((x1 - 3.2, y0 + 18.2), 3, 3)), ('stair', Rectangle((x0 + 0.5, y0 + 18.5), 3, 5)), ('wardrobe', Rectangle((x1 - 2.2, y0 + 21.5), 2, 2))]
    u.spec = dict(footprint='14 x 24 ft main body, 9 ft octagonal turret, 6 ft deep front porch', floor_sf=336, loft_sf=168, turret_sf=60, gross_sf=564, height_ft=34, pad='fits 35 x 50 pad; total length with porch and steps 36 ft',
                  materials='Board-and-batten in charcoal slate with black-plum trim; steep 24:12 standing-seam roof in matte black; turret with fish-scale shingles and a witch-hat spire; turned porch posts; tall 2 x 6 ft lancet windows with amber glass; wrought-iron weathervane; brick chimney',
                  concept='A narrow Gothic cottage with a steep gable, a corner turret with a reading nook, a hooded front porch on a raised lattice base, and a sleeping loft tucked under the roof with a round attic window over the door.',
                  florida='Steep roof and turret need engineered wind bracing (Zone 2, 140 mph); raised floor gives flood clearance and crawl-space ventilation; amber glazing must be impact rated; shutters double as storm protection.')
    return u

# ---------------- 3. Florida swamp ----------------
def swamp():
    u = Unit('swamp', 'Cypress stilt cracker', 'Florida swamp')
    W, D, F, WALL, P = 12.0, 26.0, 7.0, 9.0, 6.0        # core width/depth, floor height on stilts, wall height, porch depth
    x0, x1, y0, y1 = -W / 2, W / 2, -8, -8 + D
    px0, px1, py0, py1 = x0 - P, x1 + P, y0 - P, y1      # porch wraps front and both sides
    piers = u.part('piers', '#3d2e22')
    for px in np.linspace(px0 + 0.5, px1 - 0.5, 5):
        for py in np.linspace(py0 + 0.5, py1 - 0.5, 5): piers.box(px - 0.4, px + 0.4, py - 0.4, py + 0.4, 0, F)
    brace = u.part('bracing', '#4a3a2c')
    for px in (px0 + 0.5, px1 - 0.5): brace.box(px - 0.15, px + 0.15, py0 + 0.5, py1 - 0.5, F - 2.2, F - 1.8)
    floor = u.part('floor', '#8a6a48'); floor.box(px0, px1, py0, py1, F - 0.8, F)
    walls = u.part('walls', '#8b6b4a'); walls.prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], F, F + WALL)
    batten = u.part('battens', '#6f5238')
    for bx in np.arange(x0 + 1, x1, 1.5): batten.box(bx - 0.08, bx + 0.08, y0 - 0.12, y0, F, F + WALL); batten.box(bx - 0.08, bx + 0.08, y1, y1 + 0.12, F, F + WALL)
    for by in np.arange(y0 + 1, y1, 1.5): batten.box(x0 - 0.12, x0, by - 0.08, by + 0.08, F, F + WALL); batten.box(x1, x1 + 0.12, by - 0.08, by + 0.08, F, F + WALL)
    posts = u.part('porch posts', '#5a4632')
    for px in np.linspace(px0 + 0.4, px1 - 0.4, 5): posts.box(px - 0.3, px + 0.3, py0 + 0.4, py0 + 1.0, F, F + WALL)
    for py in np.linspace(py0 + 0.4, py1 - 0.4, 5):
        posts.box(px0 + 0.4, px0 + 1.0, py - 0.3, py + 0.3, F, F + WALL); posts.box(px1 - 1.0, px1 - 0.4, py - 0.3, py + 0.3, F, F + WALL)
    screen = u.part('screen', '#5d6b60'); screen.box(px0 + 0.5, px1 - 0.5, py0 + 0.5, py0 + 0.6, F + 3, F + WALL - 0.3)
    screen.box(px0 + 0.5, px0 + 0.6, py0 + 0.5, py1 - 0.5, F + 3, F + WALL - 0.3); screen.box(px1 - 0.6, px1 - 0.5, py0 + 0.5, py1 - 0.5, F + 3, F + WALL - 0.3)
    rail = u.part('railing', '#6f5238'); rail.box(px0 + 0.4, px1 - 0.4, py0 + 0.4, py0 + 0.7, F + 2.6, F + 3.0); rail.box(px0 + 0.4, px0 + 0.7, py0 + 0.4, py1, F + 2.6, F + 3.0); rail.box(px1 - 0.7, px1 - 0.4, py0 + 0.4, py1, F + 2.6, F + 3.0)
    roof = u.part('roof', '#9aa3a8'); roof.hip(px0, px1, py0, py1, F + WALL, F + WALL + 7.5, oh=2.5)
    cup = u.part('cupola', '#8b6b4a'); cup.box(-2, 2, y0 + D / 2 - P / 2 - 2, y0 + D / 2 - P / 2 + 2, F + WALL + 6.5, F + WALL + 10)
    cuproof = u.part('cupola roof', '#9aa3a8'); cuproof.hip(-2, 2, y0 + D / 2 - P / 2 - 2, y0 + D / 2 - P / 2 + 2, F + WALL + 10, F + WALL + 12, oh=0.8)
    win = u.part('windows', '#3d6a7a'); shut = u.part('shutters', '#3f5f4a')
    for (wx, wy, along) in [(x0, y0 + 6, 'x'), (x0, y0 + 14, 'x'), (x0, y0 + 21, 'x'), (x1, y0 + 6, 'x'), (x1, y0 + 14, 'x'), (x1, y0 + 21, 'x'), (-3, y0, 'y'), (3, y0, 'y'), (0, y1, 'y')]:
        if along == 'x':
            win.box(wx - 0.2, wx + 0.2, wy - 1.5, wy + 1.5, F + 3, F + 7.5); s = 1 if wx > 0 else -1
            shut.box(wx + s * 0.2, wx + s * 0.35, wy - 3.2, wy - 1.6, F + 3, F + 7.5); shut.box(wx + s * 0.2, wx + s * 0.35, wy + 1.6, wy + 3.2, F + 3, F + 7.5)
        else:
            win.box(wx - 1.5, wx + 1.5, wy - 0.2, wy + 0.2, F + 3, F + 7.5)
    door = u.part('door', '#2f4a3c'); door.box(-1.6, 1.6, y0 - 0.25, y0 + 0.05, F, F + 7)
    sdoor = u.part('screen door', '#2f4a3c'); sdoor.box(-1.6, 1.6, py0 + 0.45, py0 + 0.65, F, F + 7)
    stair = u.part('stairs', '#6f5238'); stair.stairs(-2, 2, py0 - 11, py0, 0, F, 11)
    stair.box(-2.4, -2.0, py0 - 11, py0, F - 0.5, F + 3); stair.box(2.0, 2.4, py0 - 11, py0, F - 0.5, F + 3)
    barrel = u.part('rain barrel', '#4a4a4a'); barrel.cylinder(px1 + 1.2, py1 - 2, 1.4, 0, 4, 16)
    p = u.plan; p['walls'] = [[(x0, y0), (x1, y0), (x1, y1), (x0, y1)]]
    p['rooms'] = [('LIVING', (0, y0 + 5), 108), ('GALLEY KITCHEN', (0, y0 + 12), 84), ('BATH', (-3, y0 + 19), 42), ('BEDROOM', (0, y0 + 23.5), 60), ('SCREENED PORCH (wraps 3 sides)', (0, py0 + 3), 300), ('LOFT OVER BEDROOM', (2.5, y0 + 19), 90)]
    p['doors'] = [((-1.6, y0), (1.6, y0)), ((-1.6, py0 + 0.5), (1.6, py0 + 0.5))]; p['windows'] = [(x0, y0 + 6), (x0, y0 + 14), (x0, y0 + 21), (x1, y0 + 6), (x1, y0 + 14), (x1, y0 + 21), (-3, y0), (3, y0), (0, y1)]
    p['deck'] = [[(px0, py0), (px1, py0), (px1, py1), (x1, py1), (x1, y0), (x0, y0), (x0, py1), (px0, py1)]]; p['roof'] = [[(px0 - 2.5, py0 - 2.5), (px1 + 2.5, py0 - 2.5), (px1 + 2.5, py1 + 2.5), (px0 - 2.5, py1 + 2.5)]]
    p['furn'] = [('sofa', Rectangle((x0 + 0.5, y0 + 1.5), 2.5, 6)), ('kitchen', Rectangle((x1 - 2.5, y0 + 9), 2, 7)), ('wc', Rectangle((x0 + 0.5, y0 + 17), 1.6, 2)), ('shower', Rectangle((x0 + 0.5, y0 + 19.5), 3, 3)), ('bed', Rectangle((-2.7, y0 + 21), 5.4, 6.5)), ('stair', Rectangle((x1 - 3, y0 + 16.8), 2.5, 4)), ('hammock', Rectangle((px1 - 5.5, y0 + 4), 4.5, 2))]
    u.spec = dict(footprint='12 x 26 ft core on 7 ft stilts, 6 ft screened porch wrapping the front and both sides (24 x 32 ft overall), 11-tread front stair', floor_sf=312, porch_sf=300, loft_sf=90, gross_sf=702, height_ft=28, pad='fits 35 x 50 pad; overall length with stair 43 ft',
                  materials='Pressure-treated pier grid with cross bracing; cypress board-and-batten walls; 5V-crimp galvanized tin hip roof with 2.5 ft overhangs and a vented cupola; fibreglass screen panels between 6 x 6 posts; louvered shutters in bottle green; rain barrel; oak porch floor',
                  concept='A Florida cracker house lifted clear of the wet ground on piers, wrapped in a deep screened porch for bugs and afternoon rain, with a cupola pulling hot air out through the roof and shutters that close for storms.',
                  florida='Stilts put the floor above the flood elevation and let storm surge or lake rise pass under; hip roof and short overhangs perform best in hurricanes; screens and cross-ventilation reduce cooling load; cupola needs a storm closure.')
    return u

units = [mushroom(), haunted(), swamp()]
for u in units: print(u.key, u.name, 'faces', u.nfaces(), 'parts', len(u.parts))

# ---------------- exports per unit ----------------
def unit_dxf(u, path):
    doc = ezdxf.new('R2018', setup=True); doc.header['$INSUNITS'] = 2; msp = doc.modelspace()
    for name, color in {'A-WALL': 7, 'A-DOOR': 3, 'A-GLAZ': 4, 'A-DECK': 32, 'A-ROOF-OUTL': 8, 'A-FURN': 9, 'A-ANNO': 2}.items(): doc.layers.add(name, color=color)
    for p in u.parts:
        lname = 'M-' + p.name.upper().replace(' ', '-'); doc.layers.add(lname, true_color=int(p.color[1:], 16))
        mb = MeshBuilder(); mb.add_vertices(p.v)
        for f in p.f: mb.faces.append(f)
        mb.render_mesh(msp, dxfattribs={'layer': lname})
    pl = u.plan
    for w in pl['walls']: msp.add_lwpolyline(w, close=True, dxfattribs={'layer': 'A-WALL', 'const_width': 0.5})
    for d in pl['deck']: msp.add_lwpolyline(d, close=True, dxfattribs={'layer': 'A-DECK'})
    for r in pl['roof']: msp.add_lwpolyline(r, close=True, dxfattribs={'layer': 'A-ROOF-OUTL', 'linetype': 'DASHED'})
    for a, b in pl['doors']: msp.add_line(a, b, dxfattribs={'layer': 'A-DOOR'})
    for x, y in pl['windows']: msp.add_circle((x, y), 0.6, dxfattribs={'layer': 'A-GLAZ'})
    for name, (cx, cy), sf in pl['rooms']: msp.add_text(f'{name}  {sf} SF', height=0.8, dxfattribs={'layer': 'A-ANNO'}).set_placement((cx, cy), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    for name, patch in pl['furn']:
        if isinstance(patch, Rectangle): x, y = patch.get_xy(); msp.add_lwpolyline([(x, y), (x + patch.get_width(), y), (x + patch.get_width(), y + patch.get_height()), (x, y + patch.get_height())], close=True, dxfattribs={'layer': 'A-FURN'})
        else: msp.add_circle(patch.center, patch.radius, dxfattribs={'layer': 'A-FURN'})
    msp.add_mtext(f"{u.name.upper()} ({u.theme}) - TINY HOME CONCEPT\\P{u.spec['footprint']}\\PGROSS {u.spec['gross_sf']} SF, HEIGHT {u.spec['height_ft']} FT\\PLOCAL ORIGIN AT PAD CENTRE; -Y FACES THE LANE; UNITS FEET",
                  dxfattribs={'layer': 'A-ANNO', 'char_height': 0.9, 'width': 40}).set_location((-17, 28))
    doc.saveas(path)

def shade(tri, light=np.array([0.4, -0.6, 0.7])):
    n = np.cross(tri[1] - tri[0], tri[2] - tri[0]); L = np.linalg.norm(n); n = n / L if L else n
    return 0.55 + 0.45 * max(0.0, float(np.dot(n, light / np.linalg.norm(light))))

def hexrgb(h): return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
def draw3d(ax, u, elev, azim, ortho=False, dx=0, dy=0, dz=0):
    polys, cols = [], []
    for p in u.parts:
        V = np.array(p.v); c = np.array(hexrgb(p.color))
        for f in p.f:
            tri = V[list(f)] + np.array([dx, dy, dz]); polys.append(tri); cols.append(np.clip(c * shade(tri), 0, 1))
    pc = Poly3DCollection(polys, facecolors=cols, edgecolors='none'); ax.add_collection3d(pc)
    allv = np.vstack([np.array(p.v) for p in u.parts]); mn, mx = allv.min(0), allv.max(0); span = (mx - mn).max()
    ax.set_xlim(mn[0] + dx, mn[0] + dx + span); ax.set_ylim(mn[1] + dy, mn[1] + dy + span); ax.set_zlim(0, span)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=elev, azim=azim)
    if ortho: ax.set_proj_type('ortho')
    ax.set_axis_off()

def unit_sheet(u, path):
    fig = plt.figure(figsize=(18, 12), dpi=110); fig.patch.set_facecolor('#f6f4ee')
    ax = fig.add_subplot(2, 3, 1); pl = u.plan
    for r in pl['roof']: ax.add_patch(MPoly(r, closed=True, fc='none', ec='#999', ls='--', lw=0.8))
    for d in pl['deck']: ax.add_patch(MPoly(d, closed=True, fc='#e6d3b3', ec='#8a6d1a', lw=0.8))
    for w in pl['walls']: ax.add_patch(MPoly(w, closed=True, fc='#f3efe6', ec='#222', lw=2.2))
    for name, patch in pl['furn']:
        pt = Rectangle(patch.get_xy(), patch.get_width(), patch.get_height(), fc='#ddd', ec='#666', lw=0.6) if isinstance(patch, Rectangle) else Circle(patch.center, patch.radius, fc='#ddd', ec='#666', lw=0.6); ax.add_patch(pt)
        cxp, cyp = (patch.get_xy()[0] + patch.get_width() / 2, patch.get_xy()[1] + patch.get_height() / 2) if isinstance(patch, Rectangle) else patch.center
        ax.text(cxp, cyp, name, fontsize=5, ha='center', va='center', color='#444')
    for a, b in pl['doors']: ax.plot([a[0], b[0]], [a[1], b[1]], color='#2a8', lw=3)
    for x, y in pl['windows']: ax.plot(x, y, 's', ms=4, color='#3a8fb7')
    for name, (cx, cy), sf in pl['rooms']: ax.text(cx, cy, f'{name}\n{sf} sf', fontsize=6.5, ha='center', va='center', weight='bold', color='#222')
    ax.add_patch(Rectangle((-17.5, -25), 35, 50, fc='none', ec='#c33', ls=':', lw=1)); ax.text(0, -27.5, 'pad 35 x 50 ft, lane side', ha='center', fontsize=7, color='#c33')
    ax.set_xlim(-22, 22); ax.set_ylim(-30, 32); ax.set_aspect('equal'); ax.set_title('Floor plan (ft)', fontsize=10); ax.tick_params(labelsize=6)
    for i, (title, elev, azim, ortho) in enumerate([('Front elevation (from the lane)', 0, -90, True), ('Side elevation', 0, 0, True), ('Axonometric', 28, -55, False), ('Rear quarter view', 22, 135, False)]):
        ax3 = fig.add_subplot(2, 3, i + 2 if i < 2 else i + 3, projection='3d'); draw3d(ax3, u, elev, azim, ortho); ax3.set_title(title, fontsize=10)
    axt = fig.add_subplot(2, 3, 4); axt.set_axis_off()
    s = u.spec; txt = (f"{u.name}\n{u.theme.title()} tiny home\n\nFootprint: {s['footprint']}\nGross area: {s['gross_sf']} sq ft (floor {s['floor_sf']}"
                       + (f", loft {s['loft_sf']}" if 'loft_sf' in s else '') + (f", porch {s['porch_sf']}" if 'porch_sf' in s else '') + (f", pod {s['pod_sf']}" if 'pod_sf' in s else '') + (f", turret {s['turret_sf']}" if 'turret_sf' in s else '')
                       + f")\nHeight: {s['height_ft']} ft\nPad: {s['pad']}\n\nConcept: {s['concept']}\n\nMaterials: {s['materials']}\n\nFlorida notes: {s['florida']}")
    import textwrap; axt.text(0, 1, '\n'.join(textwrap.fill(line, 62) for line in txt.split('\n')), va='top', fontsize=7.6, family='DejaVu Sans')
    fig.suptitle(f'{u.name} — {u.theme} tiny home concept · Sausage Castle lake zones · concept massing, not construction drawings', fontsize=12)
    fig.tight_layout(); fig.savefig(path, dpi=110, facecolor=fig.get_facecolor()); plt.close(fig)

viewer_units = {}
for u in units:
    unit_dxf(u, f'{OUT}/{u.key}_unit_local_ft.dxf'); unit_sheet(u, f'{OUT}/{u.key}_sheet.png')
    viewer_units[u.key] = dict(name=u.name, theme=u.theme, parts=[dict(name=p.name, color=p.color, positions=[round(c, 2) for v in p.v for c in v], indices=[i for f in p.f for i in f]) for p in u.parts], spec=u.spec)
    print('exported', u.key)

# ---------------- placement on the lake-zone pads ----------------
lz = json.load(open(f'{BASE}/focus/lakes/lake_zones_concept.json'))
ll_to_sp = Transformer.from_crs('EPSG:4326', 'EPSG:2236', always_xy=True)
segs = [ll_to_sp and shp_transform(lambda x, y, z=None: ll_to_sp.transform(x, y), shape(f['geometry'])) for f in json.load(open('astatula_segment.geojson'))['features']]
lakec = Point(*lz['lake']['centroid']); loop = max((g for g in segs if g.distance(lakec) < 300 and g.length > 1000), key=lambda g: g.length)
import gzip
# ground elevation from the lakes DTM
meta = json.load(open(f'{BASE}/viewer/data/meta.json'))['zones']['lakes']
from PIL import Image
im = np.asarray(Image.open(f"{BASE}/viewer/data/{meta['ground']['file']}").convert('RGB')).astype(float); dtm = ((im[..., 0] * 256 + im[..., 1]) * meta['ground']['scale'] + meta['ground']['zmin'])[::-1]
def ground(x, y): i = int((x - meta['x0']) / meta['cell_ft']); j = int((y - meta['y0']) / meta['cell_ft']); return float(dtm[min(max(j, 0), dtm.shape[0] - 1), min(max(i, 0), dtm.shape[1] - 1)])
theme_for_zone = {'A': ['haunted'], 'B': ['swamp'], 'C': ['mushroom'], 'D': ['mushroom', 'haunted', 'swamp']}
placements = []; cyc = {z: 0 for z in theme_for_zone}
for pd in lz['pads']:
    cx, cy = pd['center']; ang = pd['angle_deg']; z = pd['zone']; keys = theme_for_zone[z]; ukey = keys[cyc[z] % len(keys)]; cyc[z] += 1
    near = loop.interpolate(loop.project(Point(cx, cy))); fx, fy = near.x - cx, near.y - cy
    pyx, pyy = -math.sin(math.radians(ang)), math.cos(math.radians(ang))      # pad local +Y axis
    rot = ang if (fx * pyx + fy * pyy) < 0 else ang + 180                        # unit -Y must face the lane
    placements.append(dict(pad=pd['id'], zone=z, unit=ukey, x=round(cx, 1), y=round(cy, 1), z=round(ground(cx, cy), 2), rot_deg=round(rot % 360, 1)))
json.dump(dict(generated=str(datetime.date.today()), crs='EPSG:2236 ftUS', units=viewer_units, placements=placements), open(f'{BASE}/viewer/data/units.json', 'w'))
print('placements', len(placements), {k: sum(1 for p in placements if p['unit'] == k) for k in viewer_units})
# DXF with blocks + inserts
doc = ezdxf.new('R2018', setup=True); doc.header['$INSUNITS'] = 21; msp = doc.modelspace()
for u in units:
    blk = doc.blocks.new(name=u.key.upper())
    for p in u.parts:
        lname = 'M-' + u.key.upper() + '-' + p.name.upper().replace(' ', '-'); doc.layers.add(lname, true_color=int(p.color[1:], 16))
        mb = MeshBuilder(); mb.add_vertices(p.v)
        for f in p.f: mb.faces.append(f)
        mb.render_mesh(blk, dxfattribs={'layer': lname})
doc.layers.add('A-UNIT-INSERT', color=30); doc.layers.add('A-UNIT-ANNO', color=2)
for pl_ in placements:
    msp.add_blockref(pl_['unit'].upper(), (pl_['x'], pl_['y'], pl_['z']), dxfattribs={'rotation': pl_['rot_deg'], 'layer': 'A-UNIT-INSERT'})
    msp.add_text(f"{pl_['pad']} {pl_['unit'].upper()} FFE~{pl_['z'] + (7 if pl_['unit'] == 'swamp' else 3 if pl_['unit'] == 'haunted' else 0.5):.1f}", height=3, dxfattribs={'layer': 'A-UNIT-ANNO'}).set_placement((pl_['x'], pl_['y'] - 28))
msp.add_mtext(f"TINY HOME UNITS PLACED ON THE LAKE-ZONE PADS ({datetime.date.today()})\\PBLOCKS MUSHROOM / HAUNTED / SWAMP DEFINED AT LOCAL ORIGIN (PAD CENTRE, -Y TOWARD THE LANE), INSERTED AT PAD CENTRES WITH LANE-FACING ROTATION AND GROUND ELEVATION FROM THE LIDAR DTM\\PEPSG:2236 ftUS, NAVD88 FT. XREF lake_zones_concept AND THE LAKES FOCUS DXF UNDERNEATH. CONCEPT MASSING ONLY.",
              dxfattribs={'layer': 'A-UNIT-ANNO', 'char_height': 4, 'width': 520}).set_location((lz['lake']['centroid'][0] - 300, lz['lake']['centroid'][1] + 420))
doc.saveas(f'{OUT}/tiny_homes_on_pads_EPSG2236_ftUS.dxf'); print('placement DXF written')
# catalog markdown
md = f"# Tiny home concepts for the lake zones\n\nGenerated {datetime.date.today()}. Concept massing models, not construction drawings. Each unit is designed to sit on a 35 x 50 ft pad with its front toward the loop lane.\n\n"
for u in units:
    s = u.spec; md += f"## {u.name} ({u.theme})\n\n{s['concept']}\n\n| Item | Value |\n|---|---|\n| Footprint | {s['footprint']} |\n| Gross area | {s['gross_sf']} sq ft |\n| Height | {s['height_ft']} ft |\n| Pad fit | {s['pad']} |\n| Materials | {s['materials']} |\n| Florida notes | {s['florida']} |\n\nFiles: `{u.key}_sheet.png` (plan, elevations, axon), `{u.key}_unit_local_ft.dxf` (3D mesh parts by material layer plus 2D plan layers, local feet).\n\n"
md += f"## Placement\n\n`tiny_homes_on_pads_EPSG2236_ftUS.dxf` defines the three units as blocks and inserts them on all {len(placements)} pads of the lake zones concept (zone A haunted, B swamp, C mushroom, D mixed), rotated to face the lane and set at the lidar ground elevation. The 3D viewer's Lakes zone has a \"Tiny homes\" toggle that shows the same placement in 3D.\n\n| Unit | Count |\n|---|---|\n" + '\n'.join(f"| {k} | {sum(1 for p in placements if p['unit'] == k)} |" for k in viewer_units) + '\n'
open(f'{OUT}/README.md', 'w').write(md); print('done')
