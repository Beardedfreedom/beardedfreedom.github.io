import json, numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
from PIL import Image
D = '/home/user/beardedfreedom.github.io/reports/sausage-castle-base/viewer/data'
OUT = '/home/user/beardedfreedom.github.io/reports/sausage-castle-base/focus'
meta = json.load(open(f'{D}/meta.json'))
def height(zn, which):
    z = meta['zones'][zn]; im = np.asarray(Image.open(f"{D}/{z[which]['file']}").convert('RGB')).astype(np.float64)
    return (im[..., 0] * 256 + im[..., 1]) * z[which]['scale'] + z[which]['zmin']   # row 0 = north
for zn, step, az, alt, exag in (('house', 4, 300, 35, 1.0), ('lakes', 4, 240, 35, 1.0)):
    z = meta['zones'][zn]; c = z['cell_ft']
    H = height(zn, 'surface')[::step, ::step]; col = np.asarray(Image.open(f"{D}/{z['color']}").convert('RGB'))[::step, ::step] / 255.0
    ny, nx = H.shape; xs = np.arange(nx) * c * step; ys = -np.arange(ny) * c * step   # north up = decreasing row
    Xg, Yg = np.meshgrid(xs, ys)
    ls = LightSource(azdeg=315, altdeg=50); rgb = ls.shade_rgb(col, H, vert_exag=1.0, dx=c * step, dy=c * step, blend_mode='soft')
    fig = plt.figure(figsize=(16, 11), dpi=120); ax = fig.add_subplot(111, projection='3d')
    ax.plot_surface(Xg, Yg, H * exag, facecolors=rgb, rstride=1, cstride=1, linewidth=0, antialiased=False, shade=False)
    zr = (H.max() - H.min()) * exag
    ax.set_box_aspect((xs.max() - xs.min(), ys.max() - ys.min(), zr * 1.0))
    ax.view_init(elev=alt, azim=az); ax.set_axis_off(); ax.set_zlim(H.min(), H.min() + zr)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    t = z['title'] + ' — 3D render from USGS 2018 lidar (surface with trees and roofs), colours = lidar land cover, north toward the top-left'
    fig.text(0.01, 0.01, t, fontsize=9, color='#333')
    fig.savefig(f'{OUT}/{zn}/{zn}_render3d.jpg', dpi=120, pil_kwargs={'quality': 88}); plt.close(fig); print('rendered', zn)
