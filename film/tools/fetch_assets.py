"""Fetch open-licensed fonts, terrain tiles and border data used by the film.

Everything here is re-downloadable; outputs land in assets/ and data/ (data/ is git-ignored).
"""
import io, json, math, os, sys, concurrent.futures as cf, urllib.request
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "assets", "fonts")
DATA = os.path.join(ROOT, "data")
UA = {"User-Agent": "Mozilla/5.0 film-build"}

FONT_URLS = {
    # fontsource static builds of OFL families
    "InterTight-900.ttf": "https://cdn.jsdelivr.net/fontsource/fonts/inter-tight@latest/latin-900-normal.ttf",
    "InterTight-700.ttf": "https://cdn.jsdelivr.net/fontsource/fonts/inter-tight@latest/latin-700-normal.ttf",
    "InterTight-500.ttf": "https://cdn.jsdelivr.net/fontsource/fonts/inter-tight@latest/latin-500-normal.ttf",
    "InstrumentSerif-Italic.ttf": "https://cdn.jsdelivr.net/fontsource/fonts/instrument-serif@latest/latin-400-italic.ttf",
    "InstrumentSerif-Regular.ttf": "https://cdn.jsdelivr.net/fontsource/fonts/instrument-serif@latest/latin-400-normal.ttf",
    "IBMPlexMono-400.ttf": "https://cdn.jsdelivr.net/fontsource/fonts/ibm-plex-mono@latest/latin-400-normal.ttf",
    "IBMPlexMono-500.ttf": "https://cdn.jsdelivr.net/fontsource/fonts/ibm-plex-mono@latest/latin-500-normal.ttf",
    "IBMPlexMono-600.ttf": "https://cdn.jsdelivr.net/fontsource/fonts/ibm-plex-mono@latest/latin-600-normal.ttf",
    "NotoSerifSC-700.otf": "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Serif/SubsetOTF/SC/NotoSerifSC-Bold.otf",
}

NE = {
    "ne_50m_admin_0_countries.geojson": "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson",
    "ne_10m_admin_1_states_provinces.geojson": "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_1_states_provinces.geojson",
}

def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except Exception as e:  # noqa
            err = e
    raise RuntimeError(f"{url}: {err}")

def fetch(path, url):
    if not os.path.exists(path):
        open(path, "wb").write(get(url))
    return path

# Web-Mercator terrarium tiles (AWS open data, elevation = R*256 + G + B/256 - 32768)
Z = 6
LON0, LON1, LAT0, LAT1 = 56.0, 152.0, 2.0, 58.0

def tile_xy(lon, lat, z):
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return x, y

def terrain():
    out = os.path.join(DATA, f"dem_z{Z}.npz")
    if os.path.exists(out):
        return
    x0, y0 = tile_xy(LON0, LAT1, Z); x1, y1 = tile_xy(LON1, LAT0, Z)
    xs = range(int(x0), int(x1) + 1); ys = range(int(y0), int(y1) + 1)
    def one(xy):
        x, y = xy
        b = get(f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{Z}/{x}/{y}.png")
        a = np.asarray(Image.open(io.BytesIO(b)).convert("RGB")).astype(np.float32)
        return xy, a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
    H = np.zeros((len(ys) * 256, len(xs) * 256), np.float32)
    with cf.ThreadPoolExecutor(16) as ex:
        for (x, y), e in ex.map(one, [(x, y) for y in ys for x in xs]):
            H[(y - ys[0]) * 256:(y - ys[0] + 1) * 256, (x - xs[0]) * 256:(x - xs[0] + 1) * 256] = e
    np.savez_compressed(out, h=H, z=Z, x0=xs[0], y0=ys[0])
    print("dem", H.shape, H.min(), H.max())

if __name__ == "__main__":
    os.makedirs(FONTS, exist_ok=True); os.makedirs(DATA, exist_ok=True)
    for name, url in FONT_URLS.items():
        fetch(os.path.join(FONTS, name), url)
    for name, url in NE.items():
        fetch(os.path.join(DATA, name), url)
    terrain()
    print("ok")
