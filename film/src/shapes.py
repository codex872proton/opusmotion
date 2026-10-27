"""Vector silhouettes (side views face right, nose at x=1; y down; unit = aircraft length)."""
import numpy as np
import skia
from kit import paint, lin_grad, col, BONE, ICE, AMBER, INK, STEEL, poly

def smooth_closed(pts, tension=0.5, sharp=()):
    """Catmull-Rom closed spline through pts -> skia.Path. Indices in `sharp` become corners."""
    P = [np.asarray(p, float) for p in pts]
    n = len(P)
    path = skia.Path(); path.moveTo(*P[0])
    for i in range(n):
        p0, p1, p2, p3 = P[i - 1], P[i], P[(i + 1) % n], P[(i + 2) % n]
        t1 = (p2 - p0) * tension / 3 if i not in sharp else np.zeros(2)
        t2 = (p3 - p1) * tension / 3 if (i + 1) % n not in sharp else np.zeros(2)
        c1, c2 = p1 + t1, p2 - t2
        path.cubicTo(c1[0], c1[1], c2[0], c2[1], p2[0], p2[1])
    path.close()
    return path

def xf(path, x, y, s, flip=False, rot=0.0):
    m = skia.Matrix()
    m.setTranslate(x, y)
    m.preRotate(np.degrees(rot))
    m.preScale(-s if flip else s, s)
    out = skia.Path(path); out.transform(m)
    return out

# ------------------------------------------------------------------ B-52H (side)
def b52_parts():
    fus = smooth_closed([(0.0, -0.016), (0.06, -0.030), (0.22, -0.037), (0.80, -0.038), (0.885, -0.037), (0.925, -0.045),
                         (0.955, -0.047), (0.978, -0.036), (0.996, -0.014), (1.0, 0.0), (0.993, 0.016), (0.965, 0.030),
                         (0.90, 0.035), (0.25, 0.035), (0.07, 0.022), (0.0, 0.006)], 0.55, sharp=(0, 15))
    fin = smooth_closed([(0.19, -0.034), (0.085, -0.185), (0.030, -0.188), (0.004, -0.020)], 0.0, sharp=(0, 1, 2, 3))
    stab = poly([(0.17, -0.036), (0.02, -0.046), (0.01, -0.040), (0.17, -0.030)], True)
    wing = poly([(0.66, -0.030), (0.47, -0.032), (0.215, 0.082), (0.285, 0.085)], True)
    pods = []
    for (x0, y0, a) in ((0.375, 0.062, 1.0), (0.262, 0.090, 0.9)):
        for dx in (0.0, 0.012):
            pods.append((skia.Path().addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x0 + dx, y0 - 0.011, 0.105, 0.022), 0.011, 0.011)), a))
    win = poly([(0.935, -0.040), (0.955, -0.042), (0.972, -0.033)])
    return dict(fus=fus, fin=fin, stab=stab, wing=wing, pods=pods, win=win)

def draw_dark_body(c, path, top, bot, rim=ICE, rim_a=0.35, base=(24, 29, 35), base2=(10, 13, 17), alpha=1.0):
    c.drawPath(path, paint(base, alpha, shader=lin_grad((0, top), (0, bot), [(0, base, alpha), (1, base2, alpha)])))
    c.save(); c.clipPath(path, doAntiAlias=True)
    c.drawPath(path, paint(rim, rim_a * alpha, stroke=3.0, blur=1.2))
    c.restore()

def draw_b52(c, x, y, s, alpha=1.0, light=1.0):
    P = b52_parts()
    T = lambda p: xf(p, x, y, s)
    draw_dark_body(c, T(P["stab"]), y - 0.05 * s, y - 0.03 * s, alpha=alpha)
    draw_dark_body(c, T(P["fin"]), y - 0.19 * s, y, alpha=alpha, base=(26, 31, 38))
    draw_dark_body(c, T(P["fus"]), y - 0.05 * s, y + 0.04 * s, alpha=alpha, base=(34, 40, 48))
    c.drawPath(T(P["win"]), paint(ICE, 0.5 * alpha, stroke=max(1.5, s * 0.003)))
    draw_dark_body(c, T(P["wing"]), y - 0.04 * s, y + 0.09 * s, alpha=alpha, base=(30, 36, 43), base2=(14, 17, 21))
    for p, a in P["pods"]:
        draw_dark_body(c, T(p), y + 0.05 * s, y + 0.1 * s, alpha=alpha * a, base=(40, 46, 54))
    # pylon under wing for the drone
    return P

# ------------------------------------------------------------------ D-21 (side), booster, hatch
def d21_side():
    body = smooth_closed([(0.0, -0.031), (0.10, -0.035), (0.50, -0.036), (0.93, -0.036), (1.0, -0.033), (1.0, 0.033),
                          (0.93, 0.036), (0.50, 0.036), (0.10, 0.035), (0.0, 0.031)], 0.4, sharp=(0, 4, 5, 9))
    spike = poly([(1.0, -0.018), (1.05, 0.0), (1.0, 0.018)], True)
    fin = poly([(0.33, -0.035), (0.135, -0.128), (0.035, -0.128), (0.048, -0.035)], True)
    chine = poly([(0.98, 0.004), (0.55, 0.008), (0.09, 0.010)])
    hatch = skia.Path().addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(0.70, 0.004, 0.925, 0.038), 0.012, 0.012))
    noz = poly([(0.0, -0.028), (-0.012, -0.026), (-0.012, 0.026), (0.0, 0.028)], True)
    return dict(body=body, spike=spike, fin=fin, chine=chine, hatch=hatch, noz=noz)

def draw_d21_side(c, x, y, s, rot=0.0, alpha=1.0, hatch_on=True, hatch_hi=0.0, glow=0.0, em=None):
    P = d21_side()
    T = lambda p: xf(p, x, y, s, rot=rot)
    draw_dark_body(c, T(P["fin"]), y - 0.13 * s, y, alpha=alpha, base=(26, 31, 37))
    draw_dark_body(c, T(P["body"]), y - 0.04 * s, y + 0.04 * s, alpha=alpha, base=(36, 42, 50), base2=(9, 11, 14))
    draw_dark_body(c, T(P["spike"]), y - 0.02 * s, y + 0.02 * s, alpha=alpha, base=(70, 76, 84))
    draw_dark_body(c, T(P["noz"]), y - 0.03 * s, y + 0.03 * s, alpha=alpha, base=(20, 22, 25))
    c.drawPath(T(P["chine"]), paint(ICE, 0.22 * alpha, stroke=max(1.0, s * 0.0025)))
    if hatch_on:
        c.drawPath(T(P["hatch"]), paint(AMBER, (0.25 + 0.75 * hatch_hi) * alpha, stroke=max(1.5, s * 0.003)))
    if glow > 0 and em is not None:
        pt = xf(skia.Path().addCircle(-0.01, 0, 0.026), x, y, s, rot=rot)
        em.drawPath(pt, paint((255, 170, 90), glow * alpha, blur=s * 0.012))
    return P

def hatch_path():
    return skia.Path().addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(-0.112, -0.017, 0.112, 0.017), 0.012, 0.012))

def draw_hatch(c, x, y, s, rot=0.0, alpha=1.0, hi=1.0):
    p = xf(hatch_path(), x, y, s, rot=rot)
    draw_dark_body(c, p, y - 0.02 * s, y + 0.02 * s, alpha=alpha, base=(52, 54, 56), base2=(22, 24, 27))
    c.drawPath(p, paint(AMBER, alpha * hi, stroke=max(2.0, s * 0.004)))

def booster_side():
    tube = smooth_closed([(-0.13, 0.050), (0.80, 0.050), (0.875, 0.064), (0.90, 0.075), (0.875, 0.086), (0.80, 0.100),
                          (-0.13, 0.100)], 0.3, sharp=(0, 1, 5, 6))
    fin = poly([(0.02, 0.098), (-0.09, 0.16), (-0.13, 0.16), (-0.11, 0.098)], True)
    noz = poly([(-0.13, 0.055), (-0.17, 0.047), (-0.17, 0.103), (-0.13, 0.095)], True)
    return dict(tube=tube, fin=fin, noz=noz)

def draw_booster(c, x, y, s, rot=0.0, alpha=1.0):
    P = booster_side()
    T = lambda p: xf(p, x, y, s, rot=rot)
    for k in ("fin", "noz", "tube"):
        draw_dark_body(c, T(P[k]), y + 0.04 * s, y + 0.11 * s, alpha=alpha, base=(58, 60, 62) if k == "tube" else (34, 36, 40),
                       base2=(18, 19, 21))

# ------------------------------------------------------------------ JC-130 (side)
def c130_parts():
    fus = smooth_closed([(0.0, -0.080), (0.12, -0.088), (0.35, -0.088), (0.86, -0.088), (0.93, -0.083), (0.958, -0.072),
                         (0.978, -0.055), (0.996, -0.028), (1.0, 0.0), (0.993, 0.026), (0.97, 0.045), (0.91, 0.058),
                         (0.42, 0.062), (0.31, 0.056), (0.13, -0.022), (0.02, -0.058)], 0.5, sharp=(0, 15))
    fin = poly([(0.23, -0.086), (0.095, -0.30), (0.035, -0.30), (0.012, -0.082)], True)
    stab = poly([(0.17, -0.090), (0.0, -0.102), (-0.005, -0.094), (0.17, -0.084)], True)
    wing = poly([(0.62, -0.101), (0.42, -0.105), (0.39, -0.092), (0.62, -0.088)], True)
    nac = [smooth_closed([(0.50, -0.102), (0.70, -0.114), (0.74, -0.106), (0.74, -0.086), (0.70, -0.080), (0.52, -0.090)], 0.4, sharp=(0, 5)),
           smooth_closed([(0.53, -0.114), (0.72, -0.126), (0.758, -0.118), (0.758, -0.099), (0.72, -0.093), (0.55, -0.102)], 0.4, sharp=(0, 5))]
    spon = smooth_closed([(0.40, 0.050), (0.45, 0.068), (0.60, 0.070), (0.64, 0.056)], 0.4)
    win = poly([(0.958, -0.068), (0.975, -0.054), (0.985, -0.040)])
    return dict(fus=fus, fin=fin, stab=stab, wing=wing, nac=nac, spon=spon, win=win)

def draw_c130(c, x, y, s, t, alpha=1.0, poles=1.0, em=None):
    P = c130_parts()
    T = lambda p: xf(p, x, y, s)
    # second (far-side) nacelle first
    draw_dark_body(c, T(P["nac"][1]), y - 0.11 * s, y - 0.07 * s, alpha=alpha * 0.85, base=(30, 35, 41))
    draw_dark_body(c, T(P["stab"]), y - 0.1 * s, y - 0.08 * s, alpha=alpha)
    draw_dark_body(c, T(P["fin"]), y - 0.3 * s, y - 0.08 * s, alpha=alpha, base=(30, 36, 43))
    draw_dark_body(c, T(P["fus"]), y - 0.09 * s, y + 0.06 * s, alpha=alpha, base=(40, 47, 56))
    draw_dark_body(c, T(P["spon"]), y + 0.05 * s, y + 0.07 * s, alpha=alpha, base=(30, 35, 41))
    draw_dark_body(c, T(P["wing"]), y - 0.09 * s, y - 0.08 * s, alpha=alpha, base=(36, 42, 50))
    draw_dark_body(c, T(P["nac"][0]), y - 0.1 * s, y - 0.06 * s, alpha=alpha, base=(44, 50, 58))
    c.drawPath(T(P["win"]), paint(ICE, 0.55 * alpha, stroke=max(1.5, s * 0.004)))
    # spinning props: translucent discs with blade shimmer
    for (px, py0, py1, a) in ((0.746, -0.165, -0.027, 0.30), (0.764, -0.178, -0.040, 0.18)):
        r = skia.Rect.MakeLTRB(x + (px - 0.006) * s, y + py0 * s, x + (px + 0.006) * s, y + py1 * s)
        c.drawOval(r, paint(ICE, a * alpha, blur=1.5))
        ph = (t * 23.0 + px * 7) % 1.0
        yy = y + (py0 + (py1 - py0) * ph) * s
        c.drawLine(x + (px - 0.004) * s, yy, x + (px + 0.004) * s, yy, paint(BONE, 0.35 * alpha, stroke=2))
    # recovery poles + loop (aft of the ramp)
    if poles > 0:
        a0 = (x + 0.11 * s, y + 0.01 * s)
        tip = (x + (0.11 - 0.30 * poles) * s, y + (0.01 + 0.44 * poles) * s)
        c.drawLine(*a0, *tip, paint(BONE, 0.75 * alpha, stroke=max(2.0, s * 0.004)))
        tip2 = (tip[0] + 0.03 * s, tip[1] + 0.03 * s)
        c.drawLine(a0[0] + 0.01 * s, a0[1], *tip2, paint(BONE, 0.45 * alpha, stroke=max(1.5, s * 0.003)))
        c.drawLine(*tip, *tip2, paint(AMBER, 0.9 * alpha * poles, stroke=max(1.5, s * 0.003)))
        return tip, tip2
    return None, None

# ------------------------------------------------------------------ parachute
def draw_chute(c, x, y, w, open_k, sway=0.0, alpha=1.0, lines_to=None, collapse=0.0):
    """Canopy centred at x, apex at top; open_k 0..1 inflation; lines_to: (x,y) of payload."""
    ow = w * (0.12 + 0.88 * open_k) * (1 - 0.7 * collapse)
    oh = w * (0.95 - 0.5 * open_k) * 0.55 + w * 0.05
    cx, cy = x + sway, y
    # canopy dome
    dome = skia.Path()
    dome.moveTo(cx - ow / 2, cy + oh * 0.55)
    dome.cubicTo(cx - ow / 2, cy - oh * 0.6, cx + ow / 2, cy - oh * 0.6, cx + ow / 2, cy + oh * 0.55)
    # scalloped skirt
    n = 7
    for i in range(n, 0, -1):
        x0 = cx - ow / 2 + ow * i / n; x1 = cx - ow / 2 + ow * (i - 1) / n
        dome.quadTo((x0 + x1) / 2, cy + oh * 0.55 - ow * 0.035, x1, cy + oh * 0.55)
    dome.close()
    c.drawPath(dome, paint(BONE, 0.92 * alpha, shader=lin_grad((cx - ow / 2, 0), (cx + ow / 2, 0),
               [(0, (120, 112, 100), alpha), (0.45, (236, 230, 216), alpha), (1, (150, 140, 124), alpha)])))
    # gores
    for i in range(1, n):
        gx = cx - ow / 2 + ow * i / n
        p = skia.Path(); p.moveTo(cx, cy - oh * 0.42); p.quadTo(gx + (gx - cx) * 0.25, cy, gx, cy + oh * 0.55)
        c.drawPath(p, paint((90, 84, 76), 0.6 * alpha, stroke=1.2))
    # orange band (recovery chutes were high-visibility)
    if lines_to is not None:
        lx, ly = lines_to
        pl = paint(BONE, 0.55 * alpha, stroke=1.2)
        for i in range(n + 1):
            sx = cx - ow / 2 + ow * i / n
            c.drawLine(sx, cy + oh * 0.55, lx, ly, pl)
    return (cx, cy - oh * 0.3)

# ------------------------------------------------------------------ D-21 planform (top view, nose up) from shared geometry
def d21_planform():
    from gfx import d21_halfspan
    xs = np.concatenate([np.linspace(-0.05, 0.0, 6), np.linspace(0.0, 0.905, 140), [0.905, 0.93, 1.0]])
    hw = d21_halfspan(xs)
    hw[:6] = np.linspace(0.0, 0.019, 6)
    hw[-3:] = [0.04, 0.033, 0.03]
    right = [(w, x - 0.5) for x, w in zip(xs, hw)]
    left = [(-w, x - 0.5) for x, w in zip(xs[::-1], hw[::-1])]
    return poly(right + left, True)
