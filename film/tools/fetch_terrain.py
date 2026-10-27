"""Fetch AWS Terrain Tiles (terrarium encoding, public dataset) for the story region at zoom 7."""
import math, os, urllib.request, concurrent.futures as cf
Z = 7
def tile(lon, lat):
    n = 2 ** Z; x = (lon + 180) / 360 * n
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return int(x), int(y)
x0, y0 = tile(114.0, 52.0); x1, y1 = tile(147.0, 28.0)
os.makedirs('terrain/tiles', exist_ok=True)
jobs = [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]
def get(xy):
    x, y = xy; p = f'terrain/tiles/{Z}_{x}_{y}.png'
    if not os.path.exists(p):
        urllib.request.urlretrieve(f'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{Z}/{x}/{y}.png', p)
    return p
with cf.ThreadPoolExecutor(8) as ex: list(ex.map(get, jobs))
print('tiles', len(jobs), 'x', x0, x1, 'y', y0, y1)
