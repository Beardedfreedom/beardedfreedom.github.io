#!/usr/bin/env python3
"""Whole-estate views of Gator Greens: the cameras and the labels, shared by scripts/golf_mockup.py.

golf_mockup.py --polish polish_estate --views estate,estate_golden,estate_top renders the views and
calls draw_labels() for a labelled copy of each. This file can also relabel finished renders without
Blender (the same cameras, projected with numpy):

  python3 scripts/estate_views.py --relabel      # mockup/golf_mockup_estate*_labeled.jpg from the renders

Labels: the yellow hole numbers sit on the greens, the Castle, the two lakes, a dashed line on the
assumed estate edge (three quarter-quarters, see scripts/golf_course.py) and a title box.
"""
import argparse, json, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon
from shapely.ops import unary_union

FT = 0.3048
E_BRK, N_BRK, QQ = 427050.0, 1578500.0, 1320.0          # the survey-grid breaks scripts/golf_course.py uses


def estate_polygon(G):
    qq = {'SW': (E_BRK - QQ, N_BRK - QQ), 'NW': (E_BRK - QQ, N_BRK), 'NE': (E_BRK, N_BRK), 'SE': (E_BRK, N_BRK - QQ)}
    parcels = json.load(open(f'{G}/golf_course.json')).get('parcels_assumed', ['SW', 'NW', 'SE'])
    return unary_union([Polygon([(a, b), (a + QQ, b), (a + QQ, b + QQ), (a, b + QQ)]) for a, b in (qq[k] for k in parcels)])


def estate_cameras(G, zg, X0, Y0, X1, Y1):
    """name -> (dict(pos, tgt, lens[, ortho in m]), light preset, size or None); positions in ftUS, heights NAVD88 ft"""
    E = estate_polygon(G); ec = (E.centroid.x, E.centroid.y); ez = zg(*ec)
    high = dict(pos=(ec[0] + 2150, ec[1] - 2400, ez + 2400), tgt=(ec[0] + 150, ec[1] - 150, ez), lens=34)
    return {'estate': (high, 'day', None), 'estate_golden': (dict(high), 'golden', None),
            'estate_top': (dict(pos=((X0 + X1) / 2, (Y0 + Y1) / 2, 4000), tgt=((X0 + X1) / 2, (Y0 + Y1) / 2 + 0.01, 0), lens=50,
                                ortho=max(X1 - X0, Y1 - Y0) * FT), 'day', (int(X1 - X0), int(Y1 - Y0)))}


def pinhole(spec, W, H, sensor=36.0):
    """the projection Blender uses for these cameras (no roll, sensor fit to the width): (x, y, z) ft -> (px, py, depth)"""
    p = np.array(spec['pos'], float); t = np.array(spec['tgt'], float); f = t - p; f /= np.linalg.norm(f)
    r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r); u = np.cross(r, f)
    def proj(x, y, z):
        d = np.array([x, y, z], float) - p; xc, yc, zc = d @ r, d @ u, d @ f
        if spec.get('ortho'):
            w = spec['ortho'] / FT; return (0.5 + xc / w) * W, (0.5 - yc / w * W / H) * H, zc
        if zc <= 0: return 0.0, 0.0, zc
        k = spec['lens'] / sensor; return (0.5 + k * xc / zc) * W, (0.5 - k * yc / zc * W / H) * H, zc
    return proj


def draw_labels(src, dst, project, G, D, world, ponds, zg):
    E = estate_polygon(G); C = json.load(open(f'{G}/golf_course.json'))
    im = Image.open(src).convert('RGBA'); W, H = im.size; ov = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov); u = W / 100.0
    try:
        fb, fs, fn = (ImageFont.truetype('DejaVuSans-Bold.ttf', int(u * s)) for s in (1.15, 0.95, 0.9))
    except OSError:
        fb = fs = fn = ImageFont.load_default()
    def onimg(X, Y, Z): return Z > 0 and 0 <= X < W and 0 <= Y < H
    ring = list(E.exterior.coords); pts = []                                                    # the estate edge, dashed
    for (ax, ay), (bx, by) in zip(ring[:-1], ring[1:]):
        for t in np.linspace(0, 1, max(2, int(math.hypot(bx - ax, by - ay) / 15))):
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t; pts.append(project(x, y, zg(x, y) + 3))
    for k in range(0, len(pts) - 1, 2):
        if pts[k][2] > 0 and pts[k + 1][2] > 0: d.line([pts[k][:2], pts[k + 1][:2]], fill=(255, 255, 255, 215), width=max(2, int(u * 0.22)))
    def tag(x, y, z, text, font, fill, side=0):
        """a label on a leader; side -1 puts the box to the left of the point, +1 to the right, 0 centred above"""
        X, Y, Z = project(x, y, z)
        if not onimg(X, Y, Z): return
        tb = d.textbbox((0, 0), text, font=font); tw, th = tb[2] - tb[0], tb[3] - tb[1]; pad = u * 0.35
        bw, bh = tw + 2 * pad, th + 2 * pad; by_ = Y - bh - u * 0.9
        bx_ = X - bw / 2 if side == 0 else (X - bw - u * 0.6 if side < 0 else X + u * 0.6)
        anchor = (X, by_ + bh) if side == 0 else ((bx_ + bw, by_ + bh / 2) if side < 0 else (bx_, by_ + bh / 2))
        d.line([(X, Y), anchor], fill=(255, 255, 255, 230), width=max(1, int(u * 0.12)))
        d.ellipse([X - u * 0.22, Y - u * 0.22, X + u * 0.22, Y + u * 0.22], fill=(255, 255, 255, 240))
        d.rounded_rectangle([bx_, by_, bx_ + bw, by_ + bh], radius=u * 0.3, fill=fill); d.text((bx_ + pad - tb[0], by_ + pad - tb[1]), text, font=font, fill=(255, 255, 255, 255))
    cx, cy = D['clubhouse']; tag(cx, cy, zg(cx, cy) + 45, 'THE CASTLE · clubhouse', fb, (120, 24, 24, 220), side=-1)
    for w in world['water']:
        lp = Polygon(list(zip(w['pts'][0::2], w['pts'][1::2])))
        if lp.intersects(ponds) or lp.area < 20000: continue
        rr = list(lp.minimum_rotated_rectangle.exterior.coords); a, b = math.dist(rr[0], rr[1]), math.dist(rr[1], rr[2])
        c = lp.centroid; tag(c.x, c.y, float(w['wse']), 'LONG LAKE' if max(a, b) > 2.2 * min(a, b) else 'ROUND LAKE', fs, (18, 60, 80, 210))
    sw = min(E.exterior.coords, key=lambda p: p[0] + p[1])
    tag(sw[0] + 420, sw[1] + 25, zg(sw[0] + 420, sw[1] + 25) + 3, 'ESTATE EDGE (ASSUMED, ABOUT 120 AC)', fs, (40, 40, 40, 190))
    for h in D['holes']:                                                                        # numbers last, so nothing covers them
        x, y = h['pin']; X, Y, Z = project(x, y, zg(x, y) + 4)
        if not onimg(X, Y, Z): continue
        r = u * 0.75; d.ellipse([X - r, Y - r, X + r, Y + r], fill=(255, 198, 26, 240), outline=(20, 20, 20, 255), width=max(1, int(u * 0.1)))
        t = str(h['n']); tb = d.textbbox((0, 0), t, font=fn); d.text((X - (tb[2] + tb[0]) / 2, Y - (tb[3] + tb[1]) / 2), t, font=fn, fill=(20, 20, 20, 255))
    lines = [(f"SAUSAGE CASTLE ESTATE · ABOUT {C.get('estate_acres', 120):.0f} AC", fb),
             (f"Gator Greens: {len(D['holes'])} holes, par {C['par']}, {C['yards']:,} yd · the Castle is the clubhouse · yellow = greens", fs)]
    y0 = u * 1.2; bw = max(d.textbbox((0, 0), t, font=f)[2] for t, f in lines) + u * 1.6; bh = sum(d.textbbox((0, 0), t, font=f)[3] for t, f in lines) + u * 1.9
    d.rounded_rectangle([u * 1.2, y0, u * 1.2 + bw, y0 + bh], radius=u * 0.4, fill=(16, 22, 18, 205)); yy = y0 + u * 0.7
    for t, f in lines:
        d.text((u * 2.0, yy), t, font=f, fill=(255, 255, 255, 255)); yy += d.textbbox((0, 0), t, font=f)[3] + u * 0.5
    Image.alpha_composite(im, ov).convert('RGB').save(dst, quality=90)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--base', default=os.path.join(os.path.dirname(__file__), '..'))
    ap.add_argument('--relabel', action='store_true', help='relabel mockup/golf_mockup_estate*.jpg'); a = ap.parse_args()
    B = os.path.abspath(a.base); G = f'{B}/masterplan/golf'
    T = np.load(f'{G}/polish_estate/terrain.npz'); Z = T['Z'].astype(np.float64); X0, Y0, X1, Y1, g = (float(T[k]) for k in ('X0', 'Y0', 'X1', 'Y1', 'grid'))
    def zg(x, y):
        fi, fj = np.clip((x - X0) / g, 0, Z.shape[1] - 1.001), np.clip((y - Y0) / g, 0, Z.shape[0] - 1.001); i0, j0 = int(fi), int(fj); ti, tj = fi - i0, fj - j0
        return float(Z[j0, i0] * (1 - ti) * (1 - tj) + Z[j0, i0 + 1] * ti * (1 - tj) + Z[j0 + 1, i0] * (1 - ti) * tj + Z[j0 + 1, i0 + 1] * ti * tj)
    D = json.load(open(f'{G}/polish/design.json')); world = json.load(open(f'{B}/game/data/world.json'))
    ponds = unary_union([Polygon(h['pond']) for h in D['holes'] if h['pond']])
    for name, (spec, _, _) in estate_cameras(G, zg, X0, Y0, X1, Y1).items():
        src = f'{G}/mockup/golf_mockup_{name}.jpg'
        if not (a.relabel and os.path.exists(src)): continue
        W, H = Image.open(src).size; draw_labels(src, src.replace('.jpg', '_labeled.jpg'), pinhole(spec, W, H), G, D, world, ponds, zg); print('labelled', name)
