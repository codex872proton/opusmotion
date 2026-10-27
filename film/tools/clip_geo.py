"""Clip Natural Earth layers to the story region and simplify them into compact JSON."""
import json, math, sys
sys.setrecursionlimit(100000)
W, S, E, N = 114.0, 28.0, 147.0, 52.0

def clip_poly(pts):
    def clip(pts, inside, inter):
        out = []
        for i in range(len(pts)):
            a, b = pts[i - 1], pts[i]
            if inside(b):
                if not inside(a): out.append(inter(a, b))
                out.append(b)
            elif inside(a): out.append(inter(a, b))
        return out
    def ix(x):  return lambda a, b: (x, a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]))
    def iy(y):  return lambda a, b: (a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]), y)
    for inside, inter in [(lambda p: p[0] >= W, ix(W)), (lambda p: p[0] <= E, ix(E)),
                          (lambda p: p[1] >= S, iy(S)), (lambda p: p[1] <= N, iy(N))]:
        if not pts: break
        pts = clip(pts, inside, inter)
    return pts

def clip_line(pts):
    runs, cur = [], []
    for p in pts:
        if W <= p[0] <= E and S <= p[1] <= N: cur.append(p)
        else:
            if len(cur) > 1: runs.append(cur)
            cur = []
    if len(cur) > 1: runs.append(cur)
    return runs

def dp(pts, tol):
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1e-12
    dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * (pts[i][0] - a[0]) - dx * (pts[i][1] - a[1])) / L
        if d > dmax: dmax, idx = d, i
    if dmax > tol: return dp(pts[:idx + 1], tol)[:-1] + dp(pts[idx:], tol)
    return [a, b]

def geoms(f):
    g = f['geometry']
    if g is None: return []
    t, c = g['type'], g['coordinates']
    if t == 'Polygon': return [('poly', r) for r in c]
    if t == 'MultiPolygon': return [('poly', r) for p in c for r in p]
    if t == 'LineString': return [('line', c)]
    if t == 'MultiLineString': return [('line', l) for l in c]
    return []

out = {'bbox': [W, S, E, N]}
for name, tol, filt in [('ne_10m_land', 0.01, None), ('ne_10m_coastline', 0.008, None),
                        ('ne_10m_admin_0_boundary_lines_land', 0.01, None),
                        ('ne_10m_rivers_lake_centerlines', 0.01, lambda p: (p.get('scalerank') or 9) <= 7),
                        ('ne_10m_lakes', 0.01, lambda p: (p.get('scalerank') or 9) <= 6)]:
    d = json.load(open(f'geo/{name}.geojson'))
    items = []
    for f in d['features']:
        if filt and not filt(f['properties']): continue
        for kind, pts in geoms(f):
            pts = [(round(p[0], 4), round(p[1], 4)) for p in pts]
            if kind == 'poly':
                c = clip_poly(pts)
                if len(c) >= 3:
                    # simplify the open ring (a closed ring has coincident endpoints, which breaks DP)
                    half = len(c) // 2
                    c = dp(c[:half + 1], tol)[:-1] + dp(c[half:] + [c[0]], tol)
                    if len(c) >= 4: items.append([[round(x, 3), round(y, 3)] for x, y in c])
            else:
                for run in clip_line(pts):
                    r = dp(run, tol)
                    if len(r) >= 2: items.append([[round(x, 3), round(y, 3)] for x, y in r])
    out[name.replace('ne_10m_', '')] = items
    print(name, len(items), sum(len(i) for i in items))
json.dump(out, open('geo/region.json', 'w'), separators=(',', ':'))
