"""Geodata cache: Web-Mercator DEM (z6), reprojected Blue Marble albedo, country masks and border polylines."""
import json, math, os
import numpy as np
from config import DATA

TILE = 256
Z = 6

def merc_px(lon, lat, z=Z):
    """lon/lat (deg) -> global Web-Mercator pixel coords at zoom z."""
    n = TILE * 2 ** z
    lon = np.asarray(lon, dtype=np.float64); lat = np.asarray(lat, dtype=np.float64)
    x = (lon + 180.0) / 360.0 * n
    s = np.sin(np.radians(lat))
    y = (0.5 - np.log((1 + s) / (1 - s)) / (4 * np.pi)) * n
    return x, y

def px_lonlat(x, y, z=Z):
    n = TILE * 2 ** z
    lon = x / n * 360.0 - 180.0
    lat = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * y / n))))
    return lon, lat

def m_per_px(lat, z=Z):
    return 156543.03392 * np.cos(np.radians(lat)) / 2 ** z

class Geo:
    def __init__(self):
        cache = os.path.join(DATA, "geo_cache.npz")
        d = np.load(os.path.join(DATA, f"dem_z{Z}.npz"))
        self.h = d["h"].astype(np.float32)
        self.ox = int(d["x0"]) * TILE; self.oy = int(d["y0"]) * TILE   # global px of local (0,0)
        self.H, self.W = self.h.shape
        self.countries = json.load(open(os.path.join(DATA, "ne_50m_admin_0_countries.geojson")))
        if os.path.exists(cache):
            c = np.load(cache)
            self.albedo, self.china, self.land = c["albedo"], c["china"], c["land"]
            self.relief, self.slope = c["relief"], c["slope"]
        else:
            self.albedo = self._albedo(); self.china = self._mask("CHN"); self.land = self._mask(None)
            self.relief, self.slope = self._relief()
            np.savez_compressed(cache, albedo=self.albedo, china=self.china, land=self.land, relief=self.relief, slope=self.slope)

    # local DEM pixel coords
    def local(self, lon, lat):
        x, y = merc_px(lon, lat)
        return x - self.ox, y - self.oy

    def lonlat(self, lx, ly):
        return px_lonlat(np.asarray(lx) + self.ox, np.asarray(ly) + self.oy)

    def height(self, lx, ly):
        lx = np.clip(np.asarray(lx, dtype=np.float64), 0, self.W - 1.001); ly = np.clip(np.asarray(ly, dtype=np.float64), 0, self.H - 1.001)
        x0 = np.floor(lx).astype(int); y0 = np.floor(ly).astype(int); fx = lx - x0; fy = ly - y0
        h = self.h
        return (h[y0, x0] * (1 - fx) * (1 - fy) + h[y0, x0 + 1] * fx * (1 - fy) + h[y0 + 1, x0] * (1 - fx) * fy + h[y0 + 1, x0 + 1] * fx * fy)

    def _albedo(self):
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        im = Image.open(os.path.join(DATA, "bluemarble_200407_21600.jpg"))
        BW, BH = im.size
        ys = np.arange(self.H) + 0.5; xs = np.arange(self.W) + 0.5
        lon, _ = px_lonlat(xs + self.ox, np.zeros_like(xs) + self.oy)
        _, lat = px_lonlat(np.zeros_like(ys) + self.ox, ys + self.oy)
        bx = (lon + 180) / 360 * BW - 0.5; by = (90 - lat) / 180 * BH - 0.5
        cx0, cx1 = int(bx.min()) - 2, int(bx.max()) + 3; cy0, cy1 = int(by.min()) - 2, int(by.max()) + 3
        crop = np.asarray(im.crop((cx0, cy0, cx1, cy1)).convert("RGB")).astype(np.float32)
        bx -= cx0; by -= cy0
        X, Y = np.meshgrid(bx, by)
        x0 = np.floor(X).astype(int); y0 = np.floor(Y).astype(int); fx = (X - x0)[..., None]; fy = (Y - y0)[..., None]
        out = (crop[y0, x0] * (1 - fx) * (1 - fy) + crop[y0, x0 + 1] * fx * (1 - fy) + crop[y0 + 1, x0] * (1 - fx) * fy + crop[y0 + 1, x0 + 1] * fx * fy)
        return np.clip(out, 0, 255).astype(np.uint8)

    def _relief(self):
        """Multi-directional shaded relief (cartographic) + metric slopes for dynamic lighting."""
        from scipy import ndimage
        h = np.maximum(self.h, -200.0).astype(np.float64)
        rows = np.arange(self.H) + 0.5
        _, lat = px_lonlat(np.zeros_like(rows) + self.ox, rows + self.oy)
        mpp = m_per_px(lat)[:, None]
        hs = ndimage.gaussian_filter(h, 0.6)
        gy, gx = np.gradient(hs)
        sx = gx / mpp; sy = gy / mpp                      # dz/dx (east), dz/dy (south) in m/m
        slope = np.stack([sx, sy], -1).astype(np.float16)
        z = 2.2
        nx, ny, nz = -sx * z, -sy * z, np.ones_like(sx)
        n = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2); nx /= n; ny /= n; nz /= n
        def shade(az, alt):
            a, e = np.radians(az), np.radians(alt)
            lx, ly, lz = np.sin(a) * np.cos(e), -np.cos(a) * np.cos(e), np.sin(e)   # az from north, y axis points south
            return np.clip(nx * lx + ny * ly + nz * lz, 0, 1)
        hsd = 0.40 * shade(315, 38) + 0.25 * shade(270, 40) + 0.20 * shade(345, 45) + 0.15 * shade(225, 45)
        flat = shade(0, 90)
        rel = hsd / np.percentile(hsd, 99.5)
        # local relief (ridge/valley accent)
        lr = hs - ndimage.gaussian_filter(hs, 6)
        rel = rel + np.tanh(lr / 400.0) * 0.08
        rel = 0.7 * rel + 0.3 * (rel * flat)
        rel = np.clip(rel, 0, 1)
        return (rel * 255).astype(np.uint8), slope

    def rings(self, iso):
        for f in self.countries["features"]:
            p = f["properties"]
            if iso is None or p.get("ADM0_A3") == iso:
                g = f["geometry"]
                polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
                for poly in polys:
                    for ring in poly:
                        yield np.array(ring)

    def _mask(self, iso):
        import skia
        s = skia.Surface(self.W, self.H); c = s.getCanvas(); c.clear(skia.ColorBLACK)
        path = skia.Path(); path.setFillType(skia.PathFillType.kEvenOdd)
        for r in self.rings(iso):
            x, y = self.local(r[:, 0], r[:, 1])
            path.moveTo(x[0], y[0])
            for a, b in zip(x[1:], y[1:]):
                path.lineTo(a, b)
            path.close()
        c.drawPath(path, skia.Paint(AntiAlias=True, Color=skia.ColorWHITE))
        return s.toarray()[..., 0].copy()

    def border_lines(self, lon_range=(40, 160), lat_range=(-5, 65)):
        """All country polygon rings in the region as local px polylines with ISO tags."""
        out = []
        for f in self.countries["features"]:
            iso = f["properties"].get("ADM0_A3")
            g = f["geometry"]
            polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            for poly in polys:
                for ring in poly:
                    r = np.array(ring)
                    if r[:, 0].max() < lon_range[0] or r[:, 0].min() > lon_range[1] or r[:, 1].max() < lat_range[0] or r[:, 1].min() > lat_range[1]:
                        continue
                    x, y = self.local(r[:, 0], r[:, 1])
                    out.append((iso, np.stack([x, y], 1)))
        return out

if __name__ == "__main__":
    g = Geo()
    print(g.h.shape, g.albedo.shape, g.china.shape, g.china.mean())
    from PIL import Image
    Image.fromarray(g.albedo[::4, ::4]).save("/tmp/verify/albedo.png")
    Image.fromarray(g.china[::4, ::4]).save("/tmp/verify/china.png")
    print("lop nur local px", g.local(88.4, 41.6), "h", g.height(*g.local(88.4, 41.6)))
