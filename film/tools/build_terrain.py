"""Mosaic AWS terrarium tiles into an Int16 Web-Mercator heightfield (metres) + JSON metadata."""
import glob, json, math, re, numpy as np
from PIL import Image
Z = 7
tiles = {}
for p in glob.glob('assets/terrain/tiles/*.png'):
    z, x, y = map(int, re.findall(r'(\d+)_(\d+)_(\d+)', p)[0]); tiles[(x, y)] = p
xs = sorted({k[0] for k in tiles}); ys = sorted({k[1] for k in tiles})
W, H = len(xs) * 256, len(ys) * 256
elev = np.zeros((H, W), np.float32)
for (x, y), p in tiles.items():
    a = np.asarray(Image.open(p).convert('RGB')).astype(np.float32)
    e = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
    elev[(y - ys[0]) * 256:(y - ys[0] + 1) * 256, (x - xs[0]) * 256:(x - xs[0] + 1) * 256] = e
# downsample 2x with box filter for a smoother, lighter field
elev = elev.reshape(H // 2, 2, W // 2, 2).mean(axis=(1, 3))
n = 2 ** Z
def lon(x): return x / n * 360 - 180
def lat(y): return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
meta = {'w': elev.shape[1], 'h': elev.shape[0], 'lon0': lon(xs[0]), 'lon1': lon(xs[-1] + 1),
        'lat0': lat(ys[-1] + 1), 'lat1': lat(ys[0]), 'min': float(elev.min()), 'max': float(elev.max())}
np.clip(elev, -32000, 32000).astype('<i2').tofile('assets/terrain/height.i16')
json.dump(meta, open('assets/terrain/height.json', 'w'), indent=1)
print(meta)
