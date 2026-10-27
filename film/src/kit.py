"""2D toolkit: easing, colour, HarfBuzz-shaped glyph paths, typed text, drawing helpers (skia)."""
import os, math, random
import numpy as np
import skia
import uharfbuzz as hb
from config import FONTS, W, H

# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x

def lin(t, a, b):
    return clamp((t - a) / (b - a)) if b != a else float(t >= b)

def sstep(t, a, b):
    x = lin(t, a, b); return x * x * (3 - 2 * x)

def ease_io(x):  # cubic in-out
    x = clamp(x); return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2

def ease_o(x, p=3):
    x = clamp(x); return 1 - (1 - x) ** p

def ease_i(x, p=3):
    x = clamp(x); return x ** p

def expo_o(x):
    x = clamp(x); return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)

def expo_io(x):
    x = clamp(x)
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    return 2 ** (20 * x - 10) / 2 if x < 0.5 else (2 - 2 ** (-20 * x + 10)) / 2

def back_o(x, s=1.4):
    x = clamp(x) - 1; return 1 + (s + 1) * x ** 3 + s * x ** 2

def spring(x, f=2.2, d=6.0):
    x = max(x, 0.0); return 1 - math.exp(-d * x) * math.cos(f * 2 * math.pi * x)

def mix(a, b, t):
    if isinstance(a, (tuple, list)):
        return tuple(x + (y - x) * t for x, y in zip(a, b))
    return a + (b - a) * t

def keyframes(t, kfs, ease=ease_io):
    """kfs: [(time, value), ...] piecewise eased interpolation (values may be tuples)."""
    if t <= kfs[0][0]: return kfs[0][1]
    for (t0, v0), (t1, v1) in zip(kfs, kfs[1:]):
        if t <= t1:
            return mix(v0, v1, ease((t - t0) / (t1 - t0)))
    return kfs[-1][1]

# ---------------------------------------------------------------- colour
def hx(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

INK = hx("06080B"); SLATE = hx("10161D"); BONE = hx("ECE6D8"); SIGNAL = hx("FF4A2B")
AMBER = hx("F2B33D"); ICE = hx("A9D3EE"); DIM = hx("8B929B"); STEEL = hx("2A323B")

def col(rgb, a=1.0):
    return skia.Color4f(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, clamp(a))

def paint(rgb=BONE, a=1.0, stroke=None, cap=skia.Paint.kRound_Cap, join=skia.Paint.kRound_Join, blur=0.0, shader=None, blend=None):
    p = skia.Paint(AntiAlias=True)
    p.setColor4f(col(rgb, a))
    if stroke is not None:
        p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(stroke); p.setStrokeCap(cap); p.setStrokeJoin(join)
    if blur > 0:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if shader is not None:
        p.setShader(shader)
    if blend is not None:
        p.setBlendMode(blend)
    return p

# ---------------------------------------------------------------- surfaces
class Layer:
    """RGBA8888 premultiplied skia surface backed by a numpy array (zero copy)."""
    def __init__(self, w=W, h=H):
        self.arr = np.zeros((h, w, 4), np.uint8)
        self.surf = skia.Surface(self.arr, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)
        self.c = self.surf.getCanvas()

    def clear(self):
        self.c.clear(skia.Color4f(0, 0, 0, 0))
        return self.c

# ---------------------------------------------------------------- fonts / shaping
FONT_FILES = {
    "lead": "InstrumentSerif-Italic.ttf", "serif": "InstrumentSerif-Regular.ttf",
    "key": "InterTight-700.ttf", "black": "InterTight-900.ttf", "sans": "InterTight-500.ttf",
    "mono": "IBMPlexMono-500.ttf", "mono6": "IBMPlexMono-600.ttf", "mono4": "IBMPlexMono-400.ttf",
    "cjk": "NotoSerifSC-700.otf",
}
_tf, _hb, _paths, _shape = {}, {}, {}, {}

def typeface(k):
    if k not in _tf:
        _tf[k] = skia.Typeface.MakeFromFile(os.path.join(FONTS, FONT_FILES[k]))
    return _tf[k]

def hbfont(k):
    if k not in _hb:
        blob = hb.Blob.from_file_path(os.path.join(FONTS, FONT_FILES[k]))
        face = hb.Face(blob); f = hb.Font(face)
        _hb[k] = (f, face.upem)
    return _hb[k]

def glyph_path(k, size, gid):
    key = (k, round(size, 2), gid)
    if key not in _paths:
        f = skia.Font(typeface(k), size); f.setSubpixel(True); f.setEdging(skia.Font.Edging.kSubpixelAntiAlias)
        p = f.getPath(gid)
        _paths[key] = p if p is not None else skia.Path()
    return _paths[key]

def shape(text, k, size, tracking=0.0):
    """-> list of (gid, x, cluster) and total advance. tracking in em."""
    key = (text, k, size, tracking)
    if key in _shape:
        return _shape[key]
    f, upem = hbfont(k)
    buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties()
    hb.shape(f, buf, {"kern": True, "liga": True})
    sc = size / upem
    out, x = [], 0.0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        out.append((info.codepoint, x + pos.x_offset * sc, info.cluster))
        x += pos.x_advance * sc + tracking * size
    res = (out, x - (tracking * size if out else 0))
    _shape[key] = res
    return res

def metrics(k, size):
    f = skia.Font(typeface(k), size)
    m = f.getMetrics()
    return m.fAscent, m.fDescent, m.fCapHeight

def text_width(text, k, size, tracking=0.0):
    return shape(text, k, size, tracking)[1]

def draw_text(c, text, x, y, k, size, rgb=BONE, a=1.0, tracking=0.0, align="left", p=None):
    g, w = shape(text, k, size, tracking)
    if align == "center": x -= w / 2
    elif align == "right": x -= w
    p = p or paint(rgb, a)
    for gid, gx, _ in g:
        c.save(); c.translate(x + gx, y); c.drawPath(glyph_path(k, size, gid), p); c.restore()
    return w

# ---------------------------------------------------------------- typing schedule + key cue log
KEY_CUES = []   # (time, kind, velocity)

def type_times(text, t0, cps, seed, burst=True):
    rng = random.Random(seed)
    ts, t = [], t0
    for i, ch in enumerate(text):
        ts.append(t)
        d = rng.uniform(0.62, 1.38) / cps
        if ch in " \u00a0": d *= 1.3
        if ch in ",.:;?!—": d += rng.uniform(0.07, 0.12)
        if burst and rng.random() < 0.12: d *= 0.55   # finger rolls
        t += d
    return ts, t

def log_keys(text, times, vel):
    for ch, t in zip(text, times):
        KEY_CUES.append((t, "space" if ch in " \u00a0" else "key", vel))

# ---------------------------------------------------------------- typed text block
class Typed:
    """A typed line-set. Each glyph appears at its keystroke time with a hot->settled colour ramp."""
    def __init__(self, text, k, size, x, y, t0, cps, seed, rgb=BONE, a=1.0, align="center", tracking=0.0,
                 maxw=920, lh=1.08, accent=(), accent_rgb=AMBER, hot=AMBER, vel=1.0, log=True, t_out=None, out_dur=0.38,
                 caret=False, rise=10.0):
        self.text, self.k, self.size = text, k, size
        self.rgb, self.a, self.align, self.tracking = rgb, a, align, tracking
        self.hot, self.t_out, self.out_dur, self.caret, self.rise = hot, t_out, out_dur, caret, rise
        self.times, self.t_end = type_times(text, t0, cps, seed)
        if log: log_keys(text, self.times, vel)
        # word wrap
        words, lines, cur = text.split(" "), [], ""
        for wd in words:
            trial = (cur + " " + wd) if cur else wd
            if cur and text_width(trial, k, size, tracking) > maxw:
                lines.append(cur); cur = wd
            else:
                cur = trial
        lines.append(cur)
        self.glyphs = []  # (gid, x, y, char_index, colour)
        ci = 0
        acc_ranges = []
        for aw in accent:
            i = text.find(aw)
            if i >= 0: acc_ranges.append((i, i + len(aw)))
        self.lines_y = []
        for li, line in enumerate(lines):
            g, wdt = shape(line, k, size, tracking)
            lx = x - wdt / 2 if align == "center" else (x - wdt if align == "right" else x)
            ly = y + li * size * lh
            self.lines_y.append(ly)
            for gid, gx, cl in g:
                idx = ci + cl
                rgbc = accent_rgb if any(a0 <= idx < a1 for a0, a1 in acc_ranges) else rgb
                self.glyphs.append((gid, lx + gx, ly, idx, rgbc))
            ci += len(line) + 1
        self.bottom = y + (len(lines) - 1) * size * lh
        self.n_lines = len(lines)
        asc, desc, cap = metrics(k, size)
        self.cap = cap

    def draw(self, c, t, alpha=1.0, dy=0.0):
        if t < self.times[0] - 0.01:
            return
        out = 1.0
        last = None
        for gid, gx, gy, idx, rgbc in self.glyphs:
            ts = self.times[min(idx, len(self.times) - 1)]
            if t < ts:
                continue
            u = (t - ts)
            ap = ease_o(u / 0.06, 2)
            if self.t_out is not None:
                to = self.t_out + idx * 0.006
                ap *= 1 - sstep(t, to, to + self.out_dur)
                yo = -18 * ease_i(lin(t, to, to + self.out_dur), 2)
            else:
                yo = 0.0
            if ap <= 0.002:
                continue
            heat = 1 - ease_o(u / 0.22, 2)
            rr = mix(rgbc, self.hot, heat * 0.85) if rgbc == self.rgb else rgbc
            yy = gy + dy + yo + self.rise * (1 - ease_o(u / 0.09, 3))
            c.save(); c.translate(gx, yy)
            c.drawPath(glyph_path(self.k, self.size, gid), paint(rr, self.a * ap * alpha))
            c.restore()
            last = (gx, yy, gid)
        if self.caret and last is not None:
            idle = t - self.times[-1]
            vis = 1.0 if t < self.times[-1] + 0.1 else (1.0 if math.fmod(idle, 0.9) < 0.5 else 0.0)
            vis *= 1 - sstep(t, self.times[-1] + 1.4, self.times[-1] + 1.6)
            if self.t_out is not None: vis *= 1 - sstep(t, self.t_out, self.t_out + 0.1)
            # caret after the most recently typed glyph
            n = sum(1 for gl in self.glyphs if self.times[min(gl[3], len(self.times) - 1)] <= t)
            gid, gx, gy, idx, _ = self.glyphs[max(n - 1, 0)]
            f = skia.Font(typeface(self.k), self.size)
            adv = f.getWidths([gid])[0]
            if vis > 0:
                c.drawRect(skia.Rect.MakeXYWH(gx + adv + self.size * 0.06, gy + dy - self.cap * 1.05, max(3, self.size * 0.07), self.cap * 1.3),
                           paint(AMBER, vis * alpha))

class Card:
    """Narrative caption: italic serif lead line + heavy sans key line(s)."""
    def __init__(self, lead, key, t0, t1, y=330, seed=0, accent=(), lead_cps=34, key_cps=27, key_size=86, lead_size=58,
                 gap=0.12, key_rgb=BONE, maxw=960):
        self.t0, self.t1 = t0, t1
        self.lead = Typed(lead, "lead", lead_size, W / 2, y, t0, lead_cps, seed, a=0.86, t_out=t1 - 0.4, vel=0.8, rise=8) if lead else None
        kt0 = (self.lead.t_end + gap) if lead else t0
        ky = y + (lead_size * 0.18 + key_size * 1.02 if lead else 0)
        self.key = Typed(key, "key", key_size, W / 2, ky, kt0, key_cps, seed + 101, accent=accent, tracking=-0.018, maxw=maxw,
                         lh=1.04, t_out=t1 - 0.4, vel=1.0, rgb=key_rgb, caret=True)
        self.t_typed = self.key.t_end
        self.bottom = self.key.bottom

    def draw(self, c, t):
        if t < self.t0 - 0.05 or t > self.t1 + 0.05:
            return
        if self.lead: self.lead.draw(c, t)
        self.key.draw(c, t)

class Label:
    """Mono telemetry label, typed fast. Block cursor leads the text."""
    def __init__(self, text, x, y, t0, t1=None, size=27, rgb=BONE, a=0.82, align="left", cps=34, seed=7, tracking=0.08,
                 vel=0.55, k="mono", log=True):
        self.ty = Typed(text, k, size, x, y, t0, cps, seed, rgb=rgb, a=a, align=align, tracking=tracking, maxw=5000,
                        t_out=(t1 - 0.3) if t1 else None, out_dur=0.25, vel=vel, hot=AMBER, rise=0, log=log)
        self.t0, self.t1 = t0, t1
        self.size, self.x, self.y = size, x, y
        self.width = text_width(text, k, size, tracking)

    def draw(self, c, t, alpha=1.0):
        if t < self.t0 - 0.01 or (self.t1 and t > self.t1 + 0.05):
            return
        self.ty.draw(c, t, alpha)
        # block cursor while typing
        if t < self.ty.t_end + 0.12:
            n = sum(1 for ts in self.ty.times if ts <= t)
            gl = [g for g in self.ty.glyphs if g[3] < n]
            x = (gl[-1][1] + self.size * 0.62) if gl else self.ty.glyphs[0][1]
            c.drawRect(skia.Rect.MakeXYWH(x, self.y - self.size * 0.78, self.size * 0.58, self.size * 0.95), paint(AMBER, 0.9 * alpha))

# ---------------------------------------------------------------- path helpers
def trim(path, a, b):
    """Sub-path between fractions a..b of total length."""
    pm = skia.PathMeasure(path, False)
    out = skia.Path()
    lens = []
    while True:
        lens.append(pm.getLength())
        if not pm.nextContour(): break
    total = sum(lens)
    if total <= 0: return out
    pm = skia.PathMeasure(path, False)
    s0, s1 = a * total, b * total
    acc = 0.0
    for L in lens:
        lo, hi = max(s0 - acc, 0), min(s1 - acc, L)
        if hi > lo:
            pm.getSegment(lo, hi, out, True)
        acc += L
        if not pm.nextContour(): break
    return out

def poly(pts, close=False):
    p = skia.Path()
    if len(pts) == 0: return p
    p.moveTo(*pts[0])
    for q in pts[1:]: p.lineTo(*q)
    if close: p.close()
    return p

def path_len(path):
    pm = skia.PathMeasure(path, False); L = 0.0
    while True:
        L += pm.getLength()
        if not pm.nextContour(): break
    return L

def point_at(path, f):
    pm = skia.PathMeasure(path, False)
    L = pm.getLength()
    ok, pos, tan = pm.getPosTan(clamp(f) * L)
    return (pos.x(), pos.y()), (tan.x(), tan.y())

def glow_stroke(c, path, rgb, w, a=1.0, glow=14.0, ga=0.55, cap=skia.Paint.kRound_Cap, dash=None):
    p1 = paint(rgb, a * ga, stroke=w * 2.2, blur=glow, cap=cap)
    p2 = paint(rgb, a, stroke=w, cap=cap)
    if dash:
        e = skia.DashPathEffect.Make(dash, 0)
        p1.setPathEffect(e); p2.setPathEffect(e)
    c.drawPath(path, p1); c.drawPath(path, p2)

def bracket_box(c, x0, y0, x1, y1, L, rgb=BONE, a=1.0, w=2.0):
    p = paint(rgb, a, stroke=w, cap=skia.Paint.kSquare_Cap)
    for (x, y, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        c.drawPath(poly([(x, y + sy * L), (x, y), (x + sx * L, y)]), p)

def lin_grad(p0, p1, stops):
    """stops: [(pos, rgb, a)]"""
    return skia.GradientShader.MakeLinear([skia.Point(*p0), skia.Point(*p1)], [col(s[1], s[2]).toColor() for s in stops], [s[0] for s in stops])

def rad_grad(cx, cy, r, stops):
    return skia.GradientShader.MakeRadial(skia.Point(cx, cy), r, [col(s[1], s[2]).toColor() for s in stops], [s[0] for s in stops])
