#!/usr/bin/env python3
"""2D CAD drawing sets for the three tiny homes: dimensioned floor plan, two elevations, a section, notes and title block.
Units feet. One DXF per house (model space sheet) plus a PNG rendered from the DXF."""
import math, os, datetime, ezdxf
from ezdxf.enums import TextEntityAlignment as TA
from ezdxf.addons.drawing import matplotlib as ezmpl
from shapely.geometry import Polygon, Point, box, LineString
from shapely.affinity import rotate
from shapely.ops import unary_union
OUT = '/home/user/beardedfreedom.github.io/reports/sausage-castle-base/units/cad'
DIMO = {'dimtxt': 0.9, 'dimasz': 0.45, 'dimexe': 0.3, 'dimexo': 0.35, 'dimgap': 0.2, 'dimdec': 1, 'dimpost': "<>'", 'dimclrt': 1, 'dimclrd': 1, 'dimclre': 1}
LAYERS = {'A-WALL': 7, 'A-WALL-PATT': 8, 'A-DOOR': 3, 'A-GLAZ': 4, 'A-GLAZ-PATT': 151, 'A-FURN': 9, 'A-FLOR-ANNO': 7, 'A-ANNO-DIMS': 1, 'A-ELEV': 7, 'A-ELEV-HIDN': 8, 'A-ROOF': 5, 'A-GRND': 8, 'A-SECT-PATT': 8, 'A-DECK': 32, 'G-TITLE': 7, 'G-ANNO-TEXT': 7, 'A-LEVL': 1}

class Sheet:
    def __init__(self, name):
        self.doc = ezdxf.new('R2018', setup=True); self.doc.header['$INSUNITS'] = 2; self.msp = self.doc.modelspace()
        for n, c in LAYERS.items(): self.doc.layers.add(n, color=c)
        self.doc.linetypes.add('HIDDEN2', pattern=[0.5, 0.25, -0.25]) if 'HIDDEN2' not in self.doc.linetypes else None
        self.name = name
    # primitives
    def pl(self, pts, layer, close=False, ox=0, oy=0, lt=None):
        a = {'layer': layer}; a.update({'linetype': lt} if lt else {}); e = self.msp.add_lwpolyline([(x + ox, y + oy) for x, y in pts], dxfattribs=a); e.close(close); return e
    def rect(self, x0, y0, x1, y1, layer, ox=0, oy=0, lt=None): return self.pl([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer, True, ox, oy, lt)
    def line(self, a, b, layer, ox=0, oy=0, lt=None):
        at = {'layer': layer}; at.update({'linetype': lt} if lt else {}); return self.msp.add_line((a[0] + ox, a[1] + oy), (b[0] + ox, b[1] + oy), dxfattribs=at)
    def circ(self, c, r, layer, ox=0, oy=0, lt=None):
        at = {'layer': layer}; at.update({'linetype': lt} if lt else {}); return self.msp.add_circle((c[0] + ox, c[1] + oy), r, dxfattribs=at)
    def arc(self, c, r, a0, a1, layer, ox=0, oy=0): return self.msp.add_arc((c[0] + ox, c[1] + oy), r, a0, a1, dxfattribs={'layer': layer})
    def text(self, s, p, h=0.9, layer='G-ANNO-TEXT', align=TA.LEFT, ox=0, oy=0, rot=0):
        return self.msp.add_text(s, height=h, dxfattribs={'layer': layer, 'rotation': rot}).set_placement((p[0] + ox, p[1] + oy), align=align)
    def hatch(self, geom, layer, color=8, ox=0, oy=0):
        for pg in (list(geom.geoms) if hasattr(geom, 'geoms') else [geom]):
            if pg.is_empty or pg.geom_type != 'Polygon': continue
            h = self.msp.add_hatch(color=color, dxfattribs={'layer': layer}); h.paths.add_polyline_path([(x + ox, y + oy) for x, y in pg.exterior.coords], is_closed=True)
            for r in pg.interiors: h.paths.add_polyline_path([(x + ox, y + oy) for x, y in r.coords], is_closed=True)
    def region(self, geom, layer='A-WALL', hatch='A-WALL-PATT', ox=0, oy=0):
        for pg in (list(geom.geoms) if hasattr(geom, 'geoms') else [geom]):
            if pg.is_empty or pg.geom_type != 'Polygon': continue
            self.pl(list(pg.exterior.coords)[:-1], layer, True, ox, oy)
            for r in pg.interiors: self.pl(list(r.coords)[:-1], layer, True, ox, oy)
        self.hatch(geom, hatch, 8, ox, oy)
    def dim(self, p1, p2, offset, ox=0, oy=0, angle=None):
        (x1, y1), (x2, y2) = p1, p2
        if angle is None: angle = 0 if abs(y2 - y1) < 1e-6 else (90 if abs(x2 - x1) < 1e-6 else None)
        if angle == 0: base = (x1 + ox, y1 + oy + offset); d = self.msp.add_linear_dim(base=base, p1=(x1 + ox, y1 + oy), p2=(x2 + ox, y2 + oy), angle=0, dxfattribs={'layer': 'A-ANNO-DIMS'}, override=DIMO)
        elif angle == 90: base = (x1 + ox + offset, y1 + oy); d = self.msp.add_linear_dim(base=base, p1=(x1 + ox, y1 + oy), p2=(x2 + ox, y2 + oy), angle=90, dxfattribs={'layer': 'A-ANNO-DIMS'}, override=DIMO)
        else: d = self.msp.add_aligned_dim(p1=(x1 + ox, y1 + oy), p2=(x2 + ox, y2 + oy), distance=offset, dxfattribs={'layer': 'A-ANNO-DIMS'}, override=DIMO)
        d.render()
    def level(self, x, z, label, ox=0, oy=0, left=False):
        self.line((x, z), (x + (-4 if left else 4), z), 'A-LEVL', ox, oy); self.text(f"{label}  {z:.1f}'", (x + (-4.2 if left else 4.2), z + 0.15), 0.7, 'A-LEVL', TA.RIGHT if left else TA.LEFT, ox, oy)
    def title(self, s, p, ox=0, oy=0): self.text(s, p, 1.4, 'G-TITLE', TA.LEFT, ox, oy); self.line((p[0], p[1] - 0.5), (p[0] + 40, p[1] - 0.5), 'G-TITLE', ox, oy)
    def ground(self, x0, x1, ox=0, oy=0):
        self.line((x0, 0), (x1, 0), 'A-GRND', ox, oy)
        for x in range(int(x0), int(x1), 2): self.line((x, 0), (x - 1, -0.8), 'A-GRND', ox, oy)
    def glazing(self, x0, y0, x1, y1, ox=0, oy=0, lancet=0):
        pts = [(x0, y0), (x1, y0), (x1, y1)] + ([((x0 + x1) / 2, y1 + lancet)] if lancet else []) + [(x0, y1)]
        self.pl(pts, 'A-GLAZ', True, ox, oy); self.hatch(Polygon(pts), 'A-GLAZ-PATT', 151, ox, oy)
        self.line(((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1), 'A-GLAZ', ox, oy); self.line((x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2), 'A-GLAZ', ox, oy)
    def door_plan(self, hinge, width, wall_dir_deg, swing_in=True, ox=0, oy=0):
        a = math.radians(wall_dir_deg + (90 if swing_in else -90)); end = (hinge[0] + width * math.cos(a), hinge[1] + width * math.sin(a))
        self.line(hinge, end, 'A-DOOR', ox, oy); a0 = wall_dir_deg; a1 = wall_dir_deg + (90 if swing_in else -90)
        self.arc(hinge, width, min(a0, a1), max(a0, a1), 'A-DOOR', ox, oy)
    def window_plan(self, c, width, wall_dir_deg, thick, ox=0, oy=0):
        a = math.radians(wall_dir_deg); dx, dy = math.cos(a), math.sin(a); nx, ny = -dy, dx
        for k in (-0.3, 0, 0.3):
            p0 = (c[0] - dx * width / 2 + nx * k * thick, c[1] - dy * width / 2 + ny * k * thick); p1 = (c[0] + dx * width / 2 + nx * k * thick, c[1] + dy * width / 2 + ny * k * thick)
            self.line(p0, p1, 'A-GLAZ', ox, oy)
    def frame(self, W, H, title, sub, notes, ox=0, oy=0):
        self.rect(0, 0, W, H, 'G-TITLE', ox, oy); self.rect(0, 0, W, 6, 'G-TITLE', ox, oy)
        self.text('FLORIDA FREEDOM WORLD  ·  LAKESIDE CABINS', (1, 4.2), 1.3, 'G-TITLE', TA.LEFT, ox, oy); self.text(title, (1, 1.6), 1.6, 'G-TITLE', TA.LEFT, ox, oy)
        self.text(sub, (W - 1, 4.2), 0.9, 'G-TITLE', TA.RIGHT, ox, oy); self.text(f"CONCEPT DESIGN · NOT FOR CONSTRUCTION · {datetime.date.today()} · UNITS: FEET (DECIMAL)", (W - 1, 1.6), 0.9, 'G-TITLE', TA.RIGHT, ox, oy)
        y = H - 3
        for n in notes: self.text(n, (W - 58, y), 0.75, 'G-ANNO-TEXT', TA.LEFT, ox, oy); y -= 1.4
    def save(self, key):
        self.doc.saveas(f'{OUT}/{key}_cad_set.dxf'); ezmpl.qsave(self.msp, f'{OUT}/{key}_cad_set.png', bg='#FFFFFF', dpi=260)
        print('saved', key)

def opening(c, along_deg, width, depth):
    return rotate(box(c[0] - width / 2, c[1] - depth / 2, c[0] + width / 2, c[1] + depth / 2), along_deg, origin=c)

# ============================== MUSHROOM ==============================
def mushroom():
    S = Sheet('Amanita cottage'); W, H = 190, 120; S.frame(W, H, 'AMANITA COTTAGE  ·  MUSHROOM CABIN  ·  PLAN, ELEVATIONS, SECTION', 'SHEET A-1 · 1 of 1',
        ['NOTES', '1. Stem: 8 in shotcrete or SIP shell on a 6 in slab plinth, lime plaster finish.', '2. Cap: sprayed foam over steel ribs, elastomeric red coating with cream spots; gill soffit T&G cypress.', '3. Loft floor at 9.6 ft inside the cap, 10 ft radius, spiral stair 4.4 ft dia.', '4. Portholes 3 ft dia impact-rated; skylight 4.4 ft dia at the crown.', '5. Bath pod grows off the stem at the rear; 6 in shell.', '6. Finished floor 0.5 ft above pad; pad graded flat (see clearing and grading).', '7. All dimensions decimal feet to face of shell.'])
    ox, oy = 30, 62   # plan origin on sheet
    R, t, C = 9.0, 0.67, (0, 4); PC, pr, pt = (-9.2, 12.2), 3.6, 0.5
    stem_o = Point(*C).buffer(R, 64); stem_i = Point(*C).buffer(R - t, 64); pod_o = Point(*PC).buffer(pr, 48); pod_i = Point(*PC).buffer(pr - pt, 48)
    door_c = (C[0], C[1] - R + t / 2); ops = [opening(door_c, 0, 3.0, t + 0.4)]
    for a in (35, 145, 215, 325):
        wc = (C[0] + (R - t / 2) * math.cos(math.radians(a)), C[1] + (R - t / 2) * math.sin(math.radians(a))); ops.append(opening(wc, a + 90, 3.0, t + 0.4))
    jd = math.degrees(math.atan2(PC[1] - C[1], PC[0] - C[0])); jc = (C[0] + (R - 0.2) * math.cos(math.radians(jd)), C[1] + (R - 0.2) * math.sin(math.radians(jd)))
    ops.append(opening(jc, jd + 90, 2.6, 2.4))
    walls = unary_union([stem_o.difference(stem_i), pod_o.difference(pod_i)]).difference(unary_union(ops)).difference(stem_i.intersection(pod_o))
    S.region(walls, ox=ox, oy=oy)
    S.door_plan((door_c[0] - 1.5, door_c[1] - t / 2), 3.0, 0, True, ox, oy)
    for a in (35, 145, 215, 325):
        wc = (C[0] + (R - t / 2) * math.cos(math.radians(a)), C[1] + (R - t / 2) * math.sin(math.radians(a))); S.window_plan(wc, 3.0, a + 90, t, ox, oy)
    S.circ(C, 10.0, 'A-ELEV-HIDN', ox, oy, 'DASHED'); S.text('LOFT ABOVE R 10.0', (C[0], C[1] + 8.6), 0.7, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy)
    S.circ(C, 15.0, 'A-ROOF', ox, oy, 'DASHED'); S.text('CAP ABOVE R 15.0', (C[0], C[1] + 14.3), 0.7, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy)
    S.circ(PC, 6.2, 'A-ROOF', ox, oy, 'DASHED')
    S.circ((5.5, 7.5), 2.2, 'A-FURN', ox, oy); S.line((5.5, 7.5), (5.5, 9.7), 'A-FURN', ox, oy); S.text('SPIRAL STAIR UP', (5.5, 4.9), 0.55, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy)
    S.pl([(-7.8, 7.5), (-7.8, 9.6), (-2.5, 11.3)], 'A-FURN', False, ox, oy); S.text('KITCHEN COUNTER', (-6.2, 6.6), 0.55, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy)
    S.rect(-3, -1.5, 3, 0.7, 'A-FURN', ox, oy); S.text('SOFA', (0, -0.5), 0.55, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy)
    S.rect(-11.6, 13.2, -10.0, 15.2, 'A-FURN', ox, oy); S.text('WC', (-10.8, 12.6), 0.5, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy); S.rect(-10.4, 9.4, -7.6, 12.2, 'A-FURN', ox, oy); S.text('SHOWER', (-9, 10.8), 0.5, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy)
    deck = [(x, y) for x, y in [(6.5 * math.cos(math.radians(a)), C[1] - R + 1 + 6.5 * math.sin(math.radians(a))) for a in range(180, 361, 10)]]
    S.pl(deck + [(-6.5, C[1] - R + 0.5), (6.5, C[1] - R + 0.5)][::-1], 'A-DECK', True, ox, oy); S.rect(-2.5, C[1] - R - 9.5, 2.5, C[1] - R - 6.0, 'A-DECK', ox, oy); S.line((-2.5, C[1] - R - 7.75), (2.5, C[1] - R - 7.75), 'A-DECK', ox, oy)
    S.text('DECK  55 SF', (0, C[1] - R - 3.2), 0.7, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy); S.text('DN', (0, C[1] - R - 8.4), 0.6, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy)
    S.text('LIVING / KITCHEN', (0, 3.2), 0.9, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy); S.text('254 SF  ·  FF 0.5', (0, 1.9), 0.7, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy)
    S.text('BATH POD 38 SF', (PC[0], PC[1] - 4.6), 0.6, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy)
    S.dim((-R, C[1]), (R, C[1]), -22, ox, oy, 0); S.dim((C[0], C[1] - R), (C[0], C[1] + R), 24, ox, oy, 90); S.dim((-15, C[1]), (15, C[1]), -25.5, ox, oy, 0)
    S.dim((-1.5, C[1] - R), (1.5, C[1] - R), -3.5, ox, oy, 0); S.dim((PC[0] - pr, PC[1]), (PC[0] + pr, PC[1]), 8, ox, oy, 0)
    S.title('FLOOR PLAN', (-17, -20), ox, oy); S.text('N', (20, 22), 1.2, 'G-TITLE', TA.MIDDLE_CENTER, ox, oy); S.line((20, 18), (20, 21), 'G-TITLE', ox, oy)
    # ---- front elevation (looking north)
    ex, ey = 82, 62; prof = [(0, 23.5), (4, 23.2), (8, 22.0), (11, 20.0), (13, 17.5), (14.5, 14.0), (15, 11.8), (14.6, 10.8), (12, 9.8), (9.1, 9.6)]
    outline = [(-r, z) for r, z in prof[::-1]] + [(r, z) for r, z in prof]
    def elev_common(S, ox, oy, side=False):
        S.ground(-24, 24, ox, oy); S.rect(-9.6, 0, 9.6, 0.5, 'A-ELEV', ox, oy); S.rect(-9, 0.5, 9, 9.6, 'A-ELEV', ox, oy)
        S.pl(outline, 'A-ROOF', True, ox, oy); S.line((-9, 9.6), (9, 9.6), 'A-ELEV', ox, oy); S.rect(-2.2, 23.3, 2.2, 23.9, 'A-GLAZ', ox, oy)
        for (rr, ang, zz, sr) in [(6, 20, 22.5, 2.0), (10, 95, 20.4, 2.6), (4, 160, 23.0, 1.5), (11.5, 210, 19.2, 2.2), (8, 275, 21.7, 2.4), (12.5, 330, 18.2, 1.8)]:
            xx = (rr * math.cos(math.radians(ang))) if not side else -(rr * math.sin(math.radians(ang))); S.circ((xx, zz), sr * 0.8, 'A-ROOF', ox, oy)
        S.level(15.5, 0.5, 'FIN FLOOR', ox, oy); S.level(15.5, 9.6, 'LOFT / GILL LINE', ox, oy); S.level(15.5, 23.5, 'CROWN', ox, oy); S.level(15.5, 11.8, 'CAP RIM', ox, oy)
        S.dim((0, 0), (0, 23.5), -21, ox, oy, 90)
    elev_common(S, ex, ey)
    S.rect(-1.5, 0.5, 1.5, 7.5, 'A-DOOR', ex, ey); S.circ((1.1, 4.0), 0.15, 'A-DOOR', ex, ey)
    for xx in (-7.37, 7.37): S.circ((xx, 5.4), 1.5, 'A-GLAZ', ex, ey); S.hatch(Point(xx, 5.4).buffer(1.5), 'A-GLAZ-PATT', 151, ex, ey)
    S.rect(-6.5, 0, 6.5, 0.5, 'A-DECK', ex, ey); S.rect(-2.5, 0, 2.5, 0.25, 'A-DECK', ex, ey)
    S.rect(-12.8, 0, -9, 7.5, 'A-ELEV-HIDN', ex, ey, 'DASHED'); S.pl([(-15.4, 7.6), (-15.2, 8.8), (-14, 10.6), (-11.7, 12.2), (-9.2, 12.5)], 'A-ELEV-HIDN', False, ex, ey, 'DASHED')
    S.title('FRONT ELEVATION (FROM THE LANE)', (-17, -6), ex, ey)
    # ---- side elevation (from the west; horizontal axis = -y, front at right)
    sx, sy = 138, 62; elev_common(S, sx, sy, side=True)
    for yy in (4 + 9 * math.sin(math.radians(145)), 4 + 9 * math.sin(math.radians(215))): S.circ((-(yy - 4), 5.4), 1.5, 'A-GLAZ', sx, sy); S.hatch(Point(-(yy - 4), 5.4).buffer(1.5), 'A-GLAZ-PATT', 151, sx, sy)
    py = -(PC[1] - 4); S.rect(py - 3.6, 0, py + 3.6, 7.5, 'A-ELEV', sx, sy); podprof = [(0, 12.5), (2.5, 12.2), (4.8, 10.6), (6.0, 8.8), (6.2, 7.6), (5.4, 6.9), (3.7, 7.0)]
    S.pl([(py - r, z) for r, z in podprof[::-1]] + [(py + r, z) for r, z in podprof], 'A-ROOF', True, sx, sy)
    S.rect(5, 0, 11.5, 0.5, 'A-DECK', sx, sy); S.rect(11.5, 0, 15, 0.25, 'A-DECK', sx, sy)
    S.title('SIDE ELEVATION (FROM THE WEST)', (-17, -6), sx, sy)
    # ---- section through the stem centre, looking north
    cx_, cy_ = 82, 14; S.ground(-20, 20, cx_, cy_); S.rect(-9.6, 0, 9.6, 0.5, 'A-ELEV', cx_, cy_); S.hatch(box(-9.6, 0, 9.6, 0.5), 'A-SECT-PATT', 8, cx_, cy_)
    for sgn in (-1, 1): S.rect(sgn * (R - t), 0.5, sgn * R, 9.6, 'A-ELEV', cx_, cy_); S.hatch(box(min(sgn * (R - t), sgn * R), 0.5, max(sgn * (R - t), sgn * R), 9.6), 'A-SECT-PATT', 8, cx_, cy_)
    shell_o = Polygon(outline); shell_i = Polygon([(-(r - 0.6 if r > 1 else 0), z - 0.6) for r, z in prof[::-1] if z > 9.7] + [((r - 0.6 if r > 1 else 0), z - 0.6) for r, z in prof if z > 9.7])
    S.pl(outline, 'A-ROOF', True, cx_, cy_); S.hatch(shell_o.difference(shell_i).difference(box(-9.1, 0, 9.1, 9.6)), 'A-SECT-PATT', 8, cx_, cy_)
    S.rect(-10, 9.6, 10, 10.4, 'A-ELEV', cx_, cy_); S.hatch(box(-10, 9.6, 10, 10.4), 'A-SECT-PATT', 8, cx_, cy_); S.rect(-2.2, 23.0, 2.2, 23.9, 'A-GLAZ', cx_, cy_)
    S.pl([(5.5, 0.5), (5.5, 9.6)], 'A-FURN', False, cx_, cy_)
    for k in range(12): S.line((5.5 - 2.2, 0.5 + k * 0.76), (5.5 + 2.2, 0.5 + k * 0.76), 'A-FURN', cx_, cy_)
    S.rect(-1.5, 0.5, 1.5, 7.5, 'A-DOOR', cx_, cy_)
    S.text('LIVING / KITCHEN', (-3, 5), 0.8, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, cx_, cy_); S.text('SLEEP LOFT', (-3, 15), 0.8, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, cx_, cy_)
    S.level(15.5, 0.5, 'FIN FLOOR', cx_, cy_); S.level(15.5, 10.4, 'LOFT FLOOR', cx_, cy_); S.level(15.5, 23.5, 'CROWN', cx_, cy_)
    S.dim((-R, 0), (R, 0), -3.5, cx_, cy_, 0); S.dim((-10, 10.4), (10, 10.4), 2, cx_, cy_, 0); S.dim((0, 0.5), (0, 10.4), -21, cx_, cy_, 90); S.dim((0, 10.4), (0, 23.0), -21, cx_, cy_, 90)
    S.title('SECTION A-A (THROUGH THE STEM, LOOKING NORTH)', (-17, -6), cx_, cy_)
    S.save('mushroom')

# ============================== HAUNTED ==============================
def haunted():
    S = Sheet("Widow's Peak"); W, H = 190, 120; S.frame(W, H, "WIDOW'S PEAK  ·  HAUNTED HOUSE CABIN  ·  PLAN, ELEVATIONS, SECTION", 'SHEET A-1 · 1 of 1',
        ['NOTES', '1. Raised floor 3.0 ft on masonry piers with lattice skirt; crawl space vented.', '2. Exterior walls 2x6 at 16 in, board-and-batten in charcoal; interior partitions 2x4.', '3. Main roof 24:12 standing seam, 1.5 ft overhang; cross gable 24:12 over the entry.', '4. Turret: 8-sided, 4.6 ft radius, 18 ft wall height, witch-hat spire to 34 ft.', '5. Lancet windows 2.4 x 6 ft with 0.8 ft pointed head, amber impact glass.', '6. Sleep loft at 13.0 ft under the roof, stair at the rear left.', '7. All dimensions decimal feet to face of stud.'])
    ox, oy = 30, 62; W_, D_, t, ti = 14.0, 24.0, 0.5, 0.33; x0, x1, y0, y1 = -7, 7, -6, 18; TC, tr = (6, -2.5), 4.6
    body = box(x0, y0, x1, y1); turret = Polygon([(TC[0] + tr * math.cos(math.pi / 8 + k * math.pi / 4), TC[1] + tr * math.sin(math.pi / 8 + k * math.pi / 4)) for k in range(8)])
    outer = unary_union([body, turret]); inner = unary_union([box(x0 + t, y0 + t, x1 - t, y1 - t), turret.buffer(-t)])
    ops = [opening((0, y0), 0, 4.0, t + 0.4)]
    wins = [((x0, y0 + 10), 90), ((x0, y0 + 17), 90), ((x1, y0 + 12), 90), ((x1, y0 + 19), 90), ((-3.5, y0), 0), ((3.5, y0), 0), ((-3, y1), 0), ((3, y1), 0)]
    for (wc, ang) in wins: ops.append(opening(wc, ang, 2.4, t + 0.4))
    for a in (200, 250, 300): ops.append(opening((TC[0] + tr * math.cos(math.radians(a)), TC[1] + tr * math.sin(math.radians(a))), a + 90, 1.6, 2.0))
    ops.append(opening((5.2, -2.5), 90, 3.0, 1.2))   # turret to parlour
    parts = [box(x0 + t, y0 + 10, x1 - t, y0 + 10 + ti), box(x0 + t, y0 + 15, x1 - t, y0 + 15 + ti), box(1.5, y0 + 15, 1.5 + ti, y1 - t)]
    parts_ops = [opening((-2.5, y0 + 10 + ti / 2), 0, 2.5, ti + 0.4), opening((4, y0 + 15 + ti / 2), 0, 2.5, ti + 0.4), opening((1.5 + ti / 2, y0 + 21), 90, 2.5, ti + 0.4)]
    walls = outer.difference(inner).difference(unary_union(ops)); parts_g = unary_union(parts).difference(unary_union(parts_ops))
    S.region(walls, ox=ox, oy=oy); S.region(parts_g, ox=ox, oy=oy)
    S.door_plan((-2, y0 - t / 2), 4.0, 0, True, ox, oy); S.door_plan((-3.75, y0 + 10 + ti / 2), 2.5, 0, True, ox, oy); S.door_plan((2.75, y0 + 15 + ti / 2), 2.5, 0, True, ox, oy); S.door_plan((1.5 + ti / 2, y0 + 19.75), 2.5, 90, True, ox, oy)
    for (wc, ang) in wins: S.window_plan(wc, 2.4, ang, t, ox, oy)
    porch = box(x0 - 1, y0 - 7, x1 - 5.5, y0); S.pl(list(porch.exterior.coords)[:-1], 'A-DECK', True, ox, oy)
    for px in (x0 - 0.5, x0 + 3.5, x1 - 6.5): S.rect(px - 0.35, y0 - 6.7, px + 0.35, y0 - 6.0, 'A-DECK', ox, oy)
    S.rect(-1, y0 - 12, 3, y0 - 7, 'A-DECK', ox, oy)
    for k in range(1, 4): S.line((-1, y0 - 12 + k * 1.25), (3, y0 - 12 + k * 1.25), 'A-DECK', ox, oy)
    S.rect(x0 - 1.5, y0 - 1.5, x1 + 1.5, y1 + 1.5, 'A-ROOF', ox, oy, 'DASHED'); S.line((0, y0 - 1.5), (0, y1 + 1.5), 'A-ROOF', ox, oy, 'DASHED'); S.text('RIDGE', (0.4, y1 - 1), 0.5, 'A-FLOR-ANNO', TA.LEFT, ox, oy)
    S.rect(x0 + 3, y1 - 5, x0 + 5, y1 - 3, 'A-FURN', ox, oy); S.text('CHIMNEY', (x0 + 4, y1 - 5.8), 0.45, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy)
    for nm, r in [('SOFA', (x0 + 1, y0 + 2, x0 + 3.5, y0 + 8)), ('KITCHEN', (x0 + 0.5, y0 + 11, x0 + 2.5, y0 + 15 - ti)), ('WC', (x1 - 3, y0 + 15.5, x1 - 1.4, y0 + 17.5)), ('SHOWER', (x1 - 3.5, y0 + 18.2, x1 - 0.5, y1 - 0.5)), ('STAIR UP', (x0 + 0.5, y0 + 18.5, x0 + 3.5, y1 - 0.5)), ('WARDROBE', (x0 + 4, y1 - 2.5, 1.2, y1 - 0.5))]:
        S.rect(*r, 'A-FURN', ox, oy); S.text(nm, ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2), 0.45, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy)
    for k in range(6): S.line((x0 + 0.5, y0 + 18.5 + k * 0.9), (x0 + 3.5, y0 + 18.5 + k * 0.9), 'A-FURN', ox, oy)
    for nm, p, sf in [('PARLOUR', (-1.5, y0 + 5), '120 SF'), ('KITCHEN', (-1, y0 + 12.5), '90 SF'), ('BATH', (4.5, y0 + 17), '45 SF'), ('STAIR', (-4.5, y0 + 17), ''), ('TURRET NOOK', (TC[0] + 0.5, TC[1] - 1.5), '60 SF'), ('PORCH', (x0 + 3.7, y0 - 3.5), '78 SF')]:
        S.text(nm, p, 0.8, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy); S.text(sf, (p[0], p[1] - 1.1), 0.6, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy) if sf else None
    S.text('SLEEP LOFT ABOVE (DASHED)', (0, y0 + 9), 0.6, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy); S.rect(x0 + 1, y0 + 4, x1 - 1, y0 + 20, 'A-ELEV-HIDN', ox, oy, 'DASHED')
    S.dim((x0, y1), (x1, y1), 4, ox, oy, 0); S.dim((x1, y0), (x1, y1), 7, ox, oy, 90); S.dim((x0 - 1, y0 - 7), (x1 - 5.5, y0 - 7), -3, ox, oy, 0); S.dim((x0 - 1, y0 - 7), (x0 - 1, y0), -3, ox, oy, 90)
    S.dim((-2, y0), (2, y0), -1.5, ox, oy, 0); S.dim((TC[0] - tr, TC[1]), (TC[0] + tr, TC[1]), -6.5, ox, oy, 0); S.dim((x0, y0), (x0, y0 + 10), -3, ox, oy, 90); S.dim((x0, y0 + 10), (x0, y0 + 15), -3, ox, oy, 90); S.dim((x0, y0 + 15), (x0, y1), -3, ox, oy, 90)
    S.title('FLOOR PLAN', (-17, -20), ox, oy); S.text('N', (20, 22), 1.2, 'G-TITLE', TA.MIDDLE_CENTER, ox, oy); S.line((20, 18), (20, 21), 'G-TITLE', ox, oy)
    # ---- front elevation
    ex, ey = 82, 60; F, WL = 3.0, 10.0; S.ground(-20, 22, ex, ey)
    S.rect(x0, 0, x1, F, 'A-ELEV', ex, ey)
    for k in range(-6, 7, 2): S.line((k, 0), (k + 2, F), 'A-ELEV-HIDN', ex, ey); S.line((k + 2, 0), (k, F), 'A-ELEV-HIDN', ex, ey)
    S.rect(x0, F, x1, F + WL, 'A-ELEV', ex, ey); S.pl([(x0, F + WL), (0, F + WL + 15), (x1, F + WL)], 'A-ELEV', False, ex, ey)
    S.pl([(x0 - 1.5, F + WL - 3.2), (0, F + WL + 15), (x1 + 1.5, F + WL - 3.2)], 'A-ROOF', False, ex, ey); S.pl([(x0 - 1.5, F + WL - 2.6), (0, F + WL + 15.6), (x1 + 1.5, F + WL - 2.6)], 'A-ROOF', False, ex, ey)
    S.pl([(-5, F + WL - 2.2), (0, F + WL + 7.8), (5, F + WL - 2.2)], 'A-ROOF', False, ex, ey); S.pl([(-5, F + WL - 1.6), (0, F + WL + 8.4), (5, F + WL - 1.6)], 'A-ROOF', False, ex, ey); S.pl([(-4, F + WL - 0.2), (0, F + WL + 7.8), (4, F + WL - 0.2)], 'A-ELEV', False, ex, ey)
    S.circ((0, F + WL + 4), 1.4, 'A-GLAZ', ex, ey); S.hatch(Point(0, F + WL + 4).buffer(1.4), 'A-GLAZ-PATT', 151, ex, ey)
    S.pl([(-2, F), (-2, F + 7.2), (0, F + 8.4), (2, F + 7.2), (2, F)], 'A-DOOR', True, ex, ey); S.circ((1.5, F + 3.5), 0.15, 'A-DOOR', ex, ey)
    for xx in (-3.5, 3.5): S.glazing(xx - 1.2, F + 2.5, xx + 1.2, F + 8.5, ex, ey, lancet=0.8)
    for f in (-4.25, -1.76, 1.76, 4.25): S.line((TC[0] + f, F), (TC[0] + f, F + 18), 'A-ELEV', ex, ey)
    S.rect(TC[0] - 4.6, F, TC[0] + 4.6, F + 18, 'A-ELEV', ex, ey); S.pl([(TC[0] - 5.6, F + 18), (TC[0], F + 31), (TC[0] + 5.6, F + 18)], 'A-ROOF', True, ex, ey); S.rect(TC[0] - 0.3, F + 31, TC[0] + 0.3, F + 33, 'A-ROOF', ex, ey)
    for a in (250, 300): xx = TC[0] + tr * math.cos(math.radians(a)); S.glazing(xx - 0.6, F + 3, xx + 0.6, F + 8, ex, ey, lancet=0.5)
    S.rect(x0 - 1, F - 0.6, x1 - 5.5, F, 'A-DECK', ex, ey)
    for px in (x0 - 0.5, x0 + 3.5, x1 - 6.5): S.rect(px - 0.35, F, px + 0.35, F + 8.5, 'A-DECK', ex, ey)
    S.rect(x0 - 1, F + 0.6, x1 - 5.5, F + 3.2, 'A-DECK', ex, ey); S.rect(x0 - 1.8, F + 8.5, x1 - 4.7, F + 11.5, 'A-ROOF', ex, ey); S.line((x0 - 1.8, F + 9.1), (x1 - 4.7, F + 9.1), 'A-ROOF', ex, ey)
    for k in range(4): S.rect(-1, k * 0.75, 3, (k + 1) * 0.75, 'A-DECK', ex, ey)
    S.rect(x0 + 3, F + WL + 8.6, x0 + 5, F + WL + 20, 'A-ELEV', ex, ey); S.rect(-0.1, F + WL + 15, 0.1, F + WL + 19, 'A-ELEV', ex, ey)
    S.level(11, F, 'FIN FLOOR', ex, ey); S.level(11, F + WL, 'LOFT FLOOR', ex, ey); S.level(11, F + WL + 15, 'RIDGE', ex, ey); S.level(11, F + 31, 'SPIRE', ex, ey); S.level(11, F + WL + 20, 'CHIMNEY', ex, ey)
    S.dim((x0, 0), (x1, 0), -4, ex, ey, 0); S.dim((0, 0), (0, F + WL + 15), -18, ex, ey, 90)
    S.title('FRONT ELEVATION (FROM THE LANE)', (-17, -6), ex, ey)
    # ---- right side elevation (from the east; horizontal = y, front at left)
    sx, sy = 138, 60; S.ground(-20, 22, sx, sy)
    S.rect(y0, 0, y1, F, 'A-ELEV', sx, sy)
    for k in range(-6, 18, 2): S.line((k, 0), (k + 2, F), 'A-ELEV-HIDN', sx, sy); S.line((k + 2, 0), (k, F), 'A-ELEV-HIDN', sx, sy)
    S.rect(y0, F, y1, F + WL, 'A-ELEV', sx, sy); S.rect(y0 - 1.5, F + WL - 3.2, y1 + 1.5, F + WL + 15, 'A-ROOF', sx, sy); S.line((y0 - 1.5, F + WL - 2.6), (y1 + 1.5, F + WL - 2.6), 'A-ROOF', sx, sy)
    S.rect(y0 - 2, F + WL - 2.2, y0 + 8, F + WL + 7.8, 'A-ROOF', sx, sy); S.line((y0 - 2, F + WL + 7.8), (y0 + 8, F + WL + 7.8), 'A-ROOF', sx, sy)
    for yy in (y0 + 12, y0 + 19): S.glazing(yy - 1.2, F + 2.5, yy + 1.2, F + 8.5, sx, sy, lancet=0.8)
    S.rect(TC[1] - 4.6, F, TC[1] + 4.6, F + 18, 'A-ELEV', sx, sy)
    for f in (-4.25, -1.76, 1.76, 4.25): S.line((TC[1] + f, F), (TC[1] + f, F + 18), 'A-ELEV', sx, sy)
    S.pl([(TC[1] - 5.6, F + 18), (TC[1], F + 31), (TC[1] + 5.6, F + 18)], 'A-ROOF', True, sx, sy); S.rect(TC[1] - 0.3, F + 31, TC[1] + 0.3, F + 33, 'A-ROOF', sx, sy)
    yy = TC[1] + tr * math.sin(math.radians(300)); S.glazing(yy - 0.6, F + 3, yy + 0.6, F + 8, sx, sy, lancet=0.5)
    S.rect(y0 - 7, F - 0.6, y0, F, 'A-DECK', sx, sy); S.rect(y0 - 6.7, F, y0 - 6.0, F + 8.5, 'A-DECK', sx, sy); S.rect(y0 - 7, F + 0.6, y0, F + 3.2, 'A-DECK', sx, sy)
    S.pl([(y0 - 7.8, F + 8.5), (y0 - 3.5, F + 11.5), (y0 + 0.8, F + 8.5)], 'A-ROOF', True, sx, sy)
    for k in range(4): S.rect(y0 - 12 + k * 1.25, 0, y0 - 7, (k + 1) * 0.75, 'A-DECK', sx, sy)
    S.rect(y1 - 5, F + WL + 15, y1 - 3, F + WL + 20, 'A-ELEV', sx, sy); S.rect(6 - 0.1, F + WL + 15, 6 + 0.1, F + WL + 19, 'A-ELEV', sx, sy)
    S.level(21, F, 'FIN FLOOR', sx, sy); S.level(21, F + WL, 'LOFT FLOOR', sx, sy); S.level(21, F + WL + 15, 'RIDGE', sx, sy)
    S.dim((y0, 0), (y1, 0), -4, sx, sy, 0); S.dim((y0 - 7, 0), (y0, 0), -4, sx, sy, 0)
    S.title('RIGHT SIDE ELEVATION (FROM THE EAST)', (-17, -6), sx, sy)
    # ---- section through parlour, looking north
    cx_, cy_ = 82, 12; S.ground(-16, 16, cx_, cy_)
    for sgn in (-1, 1): S.rect(sgn * 6.5 - 0.4, 0, sgn * 6.5 + 0.4, F - 0.8, 'A-ELEV', cx_, cy_); S.hatch(box(sgn * 6.5 - 0.4, 0, sgn * 6.5 + 0.4, F - 0.8), 'A-SECT-PATT', 8, cx_, cy_)
    S.rect(x0, F - 0.8, x1, F, 'A-ELEV', cx_, cy_); S.hatch(box(x0, F - 0.8, x1, F), 'A-SECT-PATT', 8, cx_, cy_)
    for sgn in (-1, 1): S.rect(min(sgn * x1, sgn * (x1 - t)), F, max(sgn * x1, sgn * (x1 - t)), F + WL, 'A-ELEV', cx_, cy_); S.hatch(box(min(sgn * x1, sgn * (x1 - t)), F, max(sgn * x1, sgn * (x1 - t)), F + WL), 'A-SECT-PATT', 8, cx_, cy_)
    raf = Polygon([(x0 - 1.5, F + WL - 3.2), (0, F + WL + 15), (x1 + 1.5, F + WL - 3.2), (x1 + 1.5, F + WL - 2.4), (0, F + WL + 15.8), (x0 - 1.5, F + WL - 2.4)]); S.pl(list(raf.exterior.coords)[:-1], 'A-ROOF', True, cx_, cy_); S.hatch(raf, 'A-SECT-PATT', 8, cx_, cy_)
    S.rect(x0 + t, F + WL - 0.8, x1 - t, F + WL, 'A-ELEV', cx_, cy_); S.hatch(box(x0 + t, F + WL - 0.8, x1 - t, F + WL), 'A-SECT-PATT', 8, cx_, cy_)
    S.rect(x0 + t, F + WL, x0 + t + 0.3, F + WL + 3.5, 'A-ELEV', cx_, cy_); S.rect(x1 - t - 0.3, F + WL, x1 - t, F + WL + 3.5, 'A-ELEV', cx_, cy_)
    S.text('PARLOUR', (0, F + 5), 0.8, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, cx_, cy_); S.text('SLEEP LOFT', (0, F + WL + 5), 0.8, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, cx_, cy_); S.text('CRAWL SPACE', (0, 1.2), 0.6, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, cx_, cy_)
    S.level(11, F, 'FIN FLOOR', cx_, cy_); S.level(11, F + WL - 0.8, 'LOFT FLOOR', cx_, cy_); S.level(11, F + WL + 15, 'RIDGE', cx_, cy_)
    S.dim((x0, 0), (x1, 0), -3.5, cx_, cy_, 0); S.dim((0, F), (0, F + WL - 0.8), -14, cx_, cy_, 90); S.dim((0, F + WL - 0.8), (0, F + WL + 15), -14, cx_, cy_, 90)
    S.title('SECTION A-A (THROUGH THE PARLOUR, LOOKING NORTH)', (-17, -6), cx_, cy_)
    S.save('haunted')

# ============================== SWAMP ==============================
def swamp():
    S = Sheet('Cypress stilt cracker'); W, H = 190, 120; S.frame(W, H, 'CYPRESS STILT CRACKER  ·  FLORIDA SWAMP CABIN  ·  PLAN, ELEVATIONS, SECTION', 'SHEET A-1 · 1 of 1',
        ['NOTES', '1. Floor at 7.0 ft on a 5 x 5 grid of 8x8 pressure-treated piers with cross bracing; verify flood elevation.', '2. Core walls 2x6 at 16 in, cypress board-and-batten; interior partitions 2x4.', '3. Screened porch 6 ft deep on three sides, 6x6 posts, fibreglass screen panels, 2.6 ft rail.', '4. 5V-crimp galvanized hip roof, 5:12, 2.5 ft overhang; vented cupola 4 x 4 ft.', '5. Windows 3 x 4.5 ft with louvered shutters that close for storms.', '6. Loft over the bedroom at 16.0 ft; stair at the kitchen end.', '7. All dimensions decimal feet to face of stud.'])
    ox, oy = 30, 62; Wc, Dc, F, WL, P = 12.0, 26.0, 7.0, 9.0, 6.0; t, ti = 0.5, 0.33
    x0, x1, y0, y1 = -6, 6, -8, 18; px0, px1, py0, py1 = x0 - P, x1 + P, y0 - P, y1
    core = box(x0, y0, x1, y1); inner = box(x0 + t, y0 + t, x1 - t, y1 - t)
    wins = [((x0, y0 + 6), 90), ((x0, y0 + 14), 90), ((x0, y0 + 21), 90), ((x1, y0 + 6), 90), ((x1, y0 + 14), 90), ((x1, y0 + 21), 90), ((-3, y0), 0), ((3, y0), 0), ((0, y1), 0)]
    ops = [opening((0, y0), 0, 3.2, t + 0.4)] + [opening(wc, ang, 3.0, t + 0.4) for wc, ang in wins]
    parts = [box(x0 + t, y0 + 16.5, x1 - t, y0 + 16.5 + ti), box(x0 + t, y0 + 20.5, 0.5, y0 + 20.5 + ti), box(-1.6, y0 + 16.5, -1.6 + ti, y0 + 20.5)]
    pops = [opening((3, y0 + 16.5 + ti / 2), 0, 2.5, ti + 0.4), opening((-1.6 + ti / 2, y0 + 19), 90, 2.4, ti + 0.4)]
    S.region(core.difference(inner).difference(unary_union(ops)), ox=ox, oy=oy); S.region(unary_union(parts).difference(unary_union(pops)), ox=ox, oy=oy)
    S.door_plan((-1.6, y0 - t / 2), 3.2, 0, True, ox, oy); S.door_plan((1.75, y0 + 16.5 + ti / 2), 2.5, 0, True, ox, oy); S.door_plan((-1.6 + ti / 2, y0 + 17.8), 2.4, 90, True, ox, oy)
    for wc, ang in wins:
        S.window_plan(wc, 3.0, ang, t, ox, oy)
        if ang == 90:
            s = 1 if wc[0] > 0 else -1
            for k in (-2.4, 2.4): S.rect(wc[0] + s * 0.2, wc[1] + k - 0.8, wc[0] + s * 0.35, wc[1] + k + 0.8, 'A-GLAZ', ox, oy)
    deck = Polygon([(px0, py0), (px1, py0), (px1, py1), (x1, py1), (x1, y0), (x0, y0), (x0, py1), (px0, py1)]); S.pl(list(deck.exterior.coords)[:-1], 'A-DECK', True, ox, oy)
    import numpy as np
    for pxx in np.linspace(px0 + 0.4, px1 - 0.4, 5): S.rect(pxx - 0.3, py0 + 0.4, pxx + 0.3, py0 + 1.0, 'A-DECK', ox, oy)
    for pyy in np.linspace(py0 + 0.4, py1 - 0.4, 5): S.rect(px0 + 0.4, pyy - 0.3, px0 + 1.0, pyy + 0.3, 'A-DECK', ox, oy); S.rect(px1 - 1.0, pyy - 0.3, px1 - 0.4, pyy + 0.3, 'A-DECK', ox, oy)
    S.line((px0 + 0.5, py0 + 0.55), (px1 - 0.5, py0 + 0.55), 'A-GLAZ', ox, oy); S.line((px0 + 0.55, py0 + 0.5), (px0 + 0.55, py1 - 0.5), 'A-GLAZ', ox, oy); S.line((px1 - 0.55, py0 + 0.5), (px1 - 0.55, py1 - 0.5), 'A-GLAZ', ox, oy)
    S.door_plan((-1.6, py0 + 0.55), 3.2, 0, False, ox, oy)
    S.rect(-2, py0 - 11, 2, py0, 'A-DECK', ox, oy)
    for k in range(1, 11): S.line((-2, py0 - 11 + k), (2, py0 - 11 + k), 'A-DECK', ox, oy)
    S.text('UP', (0, py0 - 5.5), 0.6, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy)
    S.rect(px0 - 2.5, py0 - 2.5, px1 + 2.5, py1 + 2.5, 'A-ROOF', ox, oy, 'DASHED'); S.line((0, -2), (0, 6), 'A-ROOF', ox, oy, 'DASHED'); S.text('RIDGE', (0.4, 2), 0.5, 'A-FLOR-ANNO', TA.LEFT, ox, oy); S.rect(-2, 0, 2, 4, 'A-ROOF', ox, oy, 'DASHED'); S.text('CUPOLA', (0, 4.6), 0.45, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy)
    S.circ((px1 + 1.2, py1 - 2), 1.4, 'A-FURN', ox, oy); S.text('RAIN BBL', (px1 + 1.2, py1 - 4.1), 0.45, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy)
    for nm, r in [('SOFA', (x0 + 0.5, y0 + 1.5, x0 + 3, y0 + 7.5)), ('KITCHEN', (x1 - 2.5, y0 + 9, x1 - 0.5, y0 + 16)), ('WC', (x0 + 0.5, y0 + 17, x0 + 2.1, y0 + 19)), ('SHOWER', (x0 + 0.5, y0 + 19.5, x0 + 3.5, y0 + 22.5)), ('BED', (-2.7, y0 + 21, 2.7, y1 - 0.5)), ('STAIR', (x1 - 3, y0 + 16.8, x1 - 0.5, y0 + 20.8)), ('HAMMOCK', (px1 - 5.5, y0 + 4, px1 - 1, y0 + 6))]:
        S.rect(*r, 'A-FURN', ox, oy); S.text(nm, ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2), 0.45, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy)
    for nm, p, sf in [('LIVING', (0, y0 + 5), '108 SF'), ('GALLEY KITCHEN', (-1, y0 + 12), '84 SF'), ('BATH', (-3.5, y0 + 18.5), '42 SF'), ('BEDROOM', (0, y1 - 3.5), '60 SF'), ('SCREENED PORCH', (0, py0 + 3.2), '300 SF'), ('LOFT ABOVE BEDROOM 90 SF', (2.5, y0 + 19.2), '')]:
        S.text(nm, p, 0.8 if len(nm) < 18 else 0.55, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy); S.text(sf, (p[0], p[1] - 1.1), 0.6, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, ox, oy) if sf else None
    S.dim((px0, py1), (px1, py1), 4, ox, oy, 0); S.dim((x0, py1), (x1, py1), 2, ox, oy, 0); S.dim((px1, py0), (px1, py1), 6, ox, oy, 90); S.dim((x1, y0), (x1, y1), 3, ox, oy, 90)
    S.dim((px0, py0), (x0, py0), -3, ox, oy, 0); S.dim((-1.6, y0), (1.6, y0), 1.5, ox, oy, 0); S.dim((x0, y0), (x0, y0 + 16.5), -9, ox, oy, 90); S.dim((x0, y0 + 16.5), (x0, y1), -9, ox, oy, 90); S.dim((-2, py0 - 11), (-2, py0), -3, ox, oy, 90)
    S.title('FLOOR PLAN', (-17, -30), ox, oy); S.text('N', (20, 24), 1.2, 'G-TITLE', TA.MIDDLE_CENTER, ox, oy); S.line((20, 20), (20, 23), 'G-TITLE', ox, oy)
    # ---- front elevation
    ex, ey = 84, 60; S.ground(-22, 22, ex, ey)
    for pxx in np.linspace(px0 + 0.5, px1 - 0.5, 5): S.rect(pxx - 0.4, 0, pxx + 0.4, F - 0.8, 'A-ELEV', ex, ey)
    S.line((px0 + 0.5, F - 2.2), (px1 - 0.5, F - 1.8), 'A-ELEV', ex, ey); S.rect(px0, F - 0.8, px1, F, 'A-DECK', ex, ey)
    S.rect(x0, F, x1, F + WL, 'A-ELEV-HIDN', ex, ey); S.rect(-1.6, F, 1.6, F + 7, 'A-DOOR', ex, ey)
    for xx in (-3, 3): S.glazing(xx - 1.5, F + 3, xx + 1.5, F + 7.5, ex, ey)
    for pxx in np.linspace(px0 + 0.4, px1 - 0.4, 5): S.rect(pxx - 0.3, F, pxx + 0.3, F + WL, 'A-DECK', ex, ey)
    S.rect(px0 + 0.5, F + 3, px1 - 0.5, F + WL - 0.3, 'A-GLAZ', ex, ey); S.hatch(box(px0 + 0.5, F + 3, px1 - 0.5, F + WL - 0.3), 'A-GLAZ-PATT', 151, ex, ey); S.rect(px0 + 0.4, F + 2.6, px1 - 0.4, F + 3.0, 'A-DECK', ex, ey)
    S.pl([(px0 - 2.5, F + WL - 1.3), (0, F + WL + 7.5), (px1 + 2.5, F + WL - 1.3)], 'A-ROOF', True, ex, ey); S.line((px0 - 2.5, F + WL - 0.8), (px1 + 2.5, F + WL - 0.8), 'A-ROOF', ex, ey)
    S.rect(-2, F + WL + 6.5, 2, F + WL + 10, 'A-ELEV', ex, ey); S.pl([(-2.8, F + WL + 10), (0, F + WL + 12), (2.8, F + WL + 10)], 'A-ROOF', True, ex, ey)
    S.rect(-2, 0, 2, F, 'A-DECK', ex, ey)
    for k in range(1, 11): S.line((-2, k * F / 11), (2, k * F / 11), 'A-DECK', ex, ey)
    S.rect(-2.4, F - 0.5, -2.0, F + 3, 'A-DECK', ex, ey); S.rect(2.0, F - 0.5, 2.4, F + 3, 'A-DECK', ex, ey); S.rect(px1 - 0.2, 0, px1 + 2.6, 4, 'A-ELEV', ex, ey)
    S.level(px1 + 3.5, F, 'FIN FLOOR', ex, ey); S.level(px1 + 3.5, F + WL, 'EAVE / LOFT', ex, ey); S.level(px1 + 3.5, F + WL + 7.5, 'RIDGE', ex, ey); S.level(px1 + 3.5, F + WL + 12, 'CUPOLA', ex, ey)
    S.dim((px0, 0), (px1, 0), -4, ex, ey, 0); S.dim((0, 0), (0, F + WL + 7.5), -19, ex, ey, 90)
    S.title('FRONT ELEVATION (FROM THE LANE)', (-17, -6), ex, ey)
    # ---- side elevation (from the east; horizontal = y, front at left)
    sx, sy = 138, 60; S.ground(-22, 24, sx, sy)
    for pyy in np.linspace(py0 + 0.5, py1 - 0.5, 5): S.rect(pyy - 0.4, 0, pyy + 0.4, F - 0.8, 'A-ELEV', sx, sy)
    S.line((py0 + 0.5, F - 2.2), (py1 - 0.5, F - 1.8), 'A-ELEV', sx, sy); S.rect(py0, F - 0.8, py1, F, 'A-DECK', sx, sy)
    S.rect(y0, F, y1, F + WL, 'A-ELEV-HIDN', sx, sy)
    for yy in (y0 + 6, y0 + 14, y0 + 21):
        S.glazing(yy - 1.5, F + 3, yy + 1.5, F + 7.5, sx, sy); S.rect(yy - 3.2, F + 3, yy - 1.6, F + 7.5, 'A-GLAZ', sx, sy); S.rect(yy + 1.6, F + 3, yy + 3.2, F + 7.5, 'A-GLAZ', sx, sy)
    for pyy in np.linspace(py0 + 0.4, py1 - 0.4, 5): S.rect(pyy - 0.3, F, pyy + 0.3, F + WL, 'A-DECK', sx, sy)
    S.rect(py0 + 0.5, F + 3, py1 - 0.5, F + WL - 0.3, 'A-GLAZ', sx, sy); S.hatch(box(py0 + 0.5, F + 3, py1 - 0.5, F + WL - 0.3), 'A-GLAZ-PATT', 151, sx, sy); S.rect(py0 + 0.4, F + 2.6, py1 - 0.4, F + 3.0, 'A-DECK', sx, sy)
    S.pl([(py0 - 2.5, F + WL - 1.3), (-2, F + WL + 7.5), (6, F + WL + 7.5), (py1 + 2.5, F + WL - 1.3)], 'A-ROOF', True, sx, sy); S.line((py0 - 2.5, F + WL - 0.8), (py1 + 2.5, F + WL - 0.8), 'A-ROOF', sx, sy)
    S.rect(0, F + WL + 6.5, 4, F + WL + 10, 'A-ELEV', sx, sy); S.pl([(-0.8, F + WL + 10), (2, F + WL + 12), (4.8, F + WL + 10)], 'A-ROOF', True, sx, sy)
    for k in range(11): S.pl([(py0 - 11 + k, k * F / 11), (py0 - 11 + k + 1, k * F / 11), (py0 - 11 + k + 1, (k + 1) * F / 11)], 'A-DECK', False, sx, sy)
    S.line((py0 - 11, 3), (py0, F + 3), 'A-DECK', sx, sy); S.rect(py1 - 3.4, 0, py1 - 0.6, 4, 'A-ELEV', sx, sy)
    S.level(py1 + 4, F, 'FIN FLOOR', sx, sy); S.level(py1 + 4, F + WL, 'EAVE / LOFT', sx, sy); S.level(py1 + 4, F + WL + 7.5, 'RIDGE', sx, sy)
    S.dim((py0, 0), (py1, 0), -4, sx, sy, 0); S.dim((py0 - 11, 0), (py0, 0), -4, sx, sy, 0); S.dim((-2, F + WL + 7.5), (6, F + WL + 7.5), 3, sx, sy, 0)
    S.title('SIDE ELEVATION (FROM THE EAST)', (-17, -6), sx, sy)
    # ---- section through bedroom and loft, looking north
    cx_, cy_ = 84, 12; S.ground(-18, 18, cx_, cy_)
    for pxx in (-11.5, -5.75, 0, 5.75, 11.5): S.rect(pxx - 0.4, 0, pxx + 0.4, F - 0.8, 'A-ELEV', cx_, cy_); S.hatch(box(pxx - 0.4, 0, pxx + 0.4, F - 0.8), 'A-SECT-PATT', 8, cx_, cy_)
    S.rect(px0, F - 0.8, px1, F, 'A-DECK', cx_, cy_); S.hatch(box(px0, F - 0.8, px1, F), 'A-SECT-PATT', 8, cx_, cy_)
    for sgn in (-1, 1): S.rect(min(sgn * x1, sgn * (x1 - t)), F, max(sgn * x1, sgn * (x1 - t)), F + WL, 'A-ELEV', cx_, cy_); S.hatch(box(min(sgn * x1, sgn * (x1 - t)), F, max(sgn * x1, sgn * (x1 - t)), F + WL), 'A-SECT-PATT', 8, cx_, cy_)
    for pxx in (px0 + 0.7, px1 - 0.7): S.rect(pxx - 0.3, F, pxx + 0.3, F + WL, 'A-ELEV', cx_, cy_); S.hatch(box(pxx - 0.3, F, pxx + 0.3, F + WL), 'A-SECT-PATT', 8, cx_, cy_)
    S.line((px0 + 1, F + 3), (px0 + 1, F + WL - 0.3), 'A-GLAZ', cx_, cy_); S.line((px1 - 1, F + 3), (px1 - 1, F + WL - 0.3), 'A-GLAZ', cx_, cy_)
    raf = Polygon([(px0 - 2.5, F + WL - 1.3), (0, F + WL + 7.5), (px1 + 2.5, F + WL - 1.3), (px1 + 2.5, F + WL - 0.8), (0, F + WL + 8.0), (px0 - 2.5, F + WL - 0.8)]); S.pl(list(raf.exterior.coords)[:-1], 'A-ROOF', True, cx_, cy_); S.hatch(raf, 'A-SECT-PATT', 8, cx_, cy_)
    S.rect(x0 + t, F + WL - 0.8, x1 - t, F + WL, 'A-ELEV', cx_, cy_); S.hatch(box(x0 + t, F + WL - 0.8, x1 - t, F + WL), 'A-SECT-PATT', 8, cx_, cy_)
    S.rect(-2, F + WL + 6.5, 2, F + WL + 10, 'A-ELEV', cx_, cy_); S.pl([(-2.8, F + WL + 10), (0, F + WL + 12), (2.8, F + WL + 10)], 'A-ROOF', True, cx_, cy_)
    S.text('BEDROOM', (0, F + 4), 0.8, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, cx_, cy_); S.text('LOFT', (0, F + WL + 2.5), 0.8, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, cx_, cy_); S.text('PORCH', (-9, F + 4), 0.7, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, cx_, cy_); S.text('PORCH', (9, F + 4), 0.7, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, cx_, cy_); S.text('OPEN BELOW (FLOOD / AIRFLOW)', (0, 3), 0.6, 'A-FLOR-ANNO', TA.MIDDLE_CENTER, cx_, cy_)
    S.level(px1 + 3.5, F, 'FIN FLOOR', cx_, cy_); S.level(px1 + 3.5, F + WL - 0.8, 'LOFT FLOOR', cx_, cy_); S.level(px1 + 3.5, F + WL + 7.5, 'RIDGE', cx_, cy_)
    S.dim((px0, 0), (px1, 0), -3.5, cx_, cy_, 0); S.dim((0, 0), (0, F), -16, cx_, cy_, 90); S.dim((0, F), (0, F + WL - 0.8), -16, cx_, cy_, 90); S.dim((0, F + WL - 0.8), (0, F + WL + 7.5), -16, cx_, cy_, 90)
    S.title('SECTION A-A (THROUGH THE BEDROOM, LOOKING NORTH)', (-17, -6), cx_, cy_)
    S.save('swamp')

for fn in (mushroom, haunted, swamp):
    try: fn()
    except Exception as e:
        import traceback; traceback.print_exc()
