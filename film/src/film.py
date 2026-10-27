"""SENIOR BOWL — the full film: timeline, shots, frame renderer."""
import math, random
import numpy as np
import skia
from scipy.interpolate import PchipInterpolator
from config import W, H
from kit import *
from kit import KEY_CUES
import shapes as S

DUR = 69.2
SFX = []   # (time, name, gain, dict)

def sfx(t, name, gain=1.0, **kw):
    SFX.append((t, name, gain, kw))

class Track:
    """Monotone-cubic keyframe track (C1, no overshoot)."""
    def __init__(self, kfs):
        self.ts = [k[0] for k in kfs]
        self.vs = np.array([k[1] for k in kfs], float)
        self.f = PchipInterpolator(self.ts, self.vs, axis=0)

    def __call__(self, t):
        if t <= self.ts[0]: return self.vs[0]
        if t >= self.ts[-1]: return self.vs[-1]
        return self.f(t)

# ====================================================================== text timeline
CARDS = []
LABELS = []   # (shot-agnostic) labels drawn on UI layer

def card(lead, key, t0, t1, **kw):
    c = Card(lead, key, t0, t1, seed=len(CARDS) * 13 + 5, **kw); CARDS.append(c); return c

def label(text, x, y, t0, t1=None, **kw):
    l = Label(text, x, y, t0, t1, seed=len(LABELS) * 7 + 3, **kw); LABELS.append(l); return l

# --- SHOT 1 HERO
cA = card("1969. A secret U.S. drone", "crosses China at Mach\u00a03.", 0.25, 3.6, accent=("Mach\u00a03.",))
lCode = label("CODENAME  SENIOR BOWL", 80, 1610, 2.62, 6.0, size=26, rgb=BONE)
cB = card("Its plan: drop the film,", "then destroy itself.", 3.75, 6.75)
# --- SHOT 2 TARGET
cC = card("Its target:", "China's nuclear test site.", 6.85, 10.1, accent=("nuclear test site.",))
lLop1 = label("LOP NUR", 0, 0, 8.95, 10.3, size=30, rgb=AMBER, a=1.0)
lLop2 = label("FIRST TEST · 1964", 0, 0, 9.25, 10.3, size=22, rgb=BONE)
cD = card("Manned spy planes", "kept getting shot\u00a0down.", 10.75, 14.35, accent=("shot\u00a0down.",), key_rgb=BONE)
lU2 = label("5 U-2s DOWNED · 1962–67", 0, 0, 13.25, 14.4, size=24, rgb=SIGNAL, a=1.0)
# --- SHOT 3 BLUEPRINT
cE = card("Enter the", "Lockheed D-21.", 14.75, 17.5, accent=("D-21.",))
lLen = label("13.1 M", 0, 0, 15.95, 21.3, size=24, rgb=ICE, align="center")
lSpan = label("5.8 M", 0, 0, 16.2, 21.3, size=24, rgb=ICE, align="center")
lSp1 = label("SPEED      MACH 3.3+", 56, 790, 16.5, 21.3, size=25, cps=46)
lSp2 = label("ALTITUDE   90,000 FT", 56, 835, 16.95, 21.3, size=25, cps=46)
lSp3 = label("RANGE      3,000 NMI", 56, 880, 17.4, 21.3, size=25, cps=46)
cF = card("No pilot.", "Built for a one-way trip.", 18.0, 21.35, accent=("one-way",))
# --- SHOT 4 LAUNCH
cG = card("Dropped from a B-52,", "then rocket-boosted to Mach\u00a03.", 21.65, 25.3, accent=("Mach\u00a03.",))
lMach = label("MACH 3.3 · 90,000 FT", 0, 0, 25.85, 27.75, size=26, rgb=AMBER, a=1.0)
# --- SHOT 5 ROUTE
lGuam = label("GUAM", 0, 0, 27.95, 33.0, size=24, rgb=BONE)
cI = card("Photograph Lop Nur,", "then race back to sea.", 28.35, 33.2, accent=("Lop Nur,",))
lIll = label("ILLUSTRATIVE ROUTE · NOT THE EXACT TRACK", 80, 1640, 31.35, 35.0, size=19, rgb=DIM, a=0.9, cps=52)
lRec = label("RECOVERY ZONE", 0, 0, 33.3, 35.0, size=24, rgb=AMBER, a=1.0)
# --- SHOT 6 RECOVERY
cK = card("Over the sea, it ejected", "its camera\u00a0hatch.", 35.35, 38.2, accent=("camera\u00a0hatch.",))
lHatch = label("CAMERA · FILM · GUIDANCE", 0, 0, 37.45, 40.5, size=23, rgb=AMBER, a=1.0, cps=40)
cL = card("Then the drone", "blew itself up.", 38.35, 40.75)
cM = card("A JC-130 snagged the hatch", "in mid-air.", 40.9, 44.85, accent=("in mid-air.",))
# --- SHOT 7 LEDGER
cN = card("That was the plan.", "Here's what happened.", 45.1, 48.0)
lHead = label("SENIOR BOWL — FLIGHTS OVER CHINA", 80, 640, 47.6, 57.45, size=25, rgb=AMBER, a=1.0, cps=46)
ROWS = [("09 NOV 1969", "Never turned back. Lost in the USSR."),
        ("16 DEC 1970", "Chute failed. Film lost at sea."),
        ("04 MAR 1971", "Catch missed. Hatch sank."),
        ("20 MAR 1971", "Lost over Yunnan, China.")]
ROW_Y0, ROW_DY = 780, 196
ledger = []
_t = 48.3
for i, (d, o) in enumerate(ROWS):
    y = ROW_Y0 + i * ROW_DY
    ld = Label(d, 80, y, _t, 57.45, size=28, rgb=AMBER, a=1.0, cps=58, seed=300 + i)
    lo = Typed(o, "key", 46, 80, y + 64, ld.ty.t_end + 0.08, 43, 400 + i, align="left", maxw=860, t_out=57.1, vel=0.85,
               tracking=-0.01)
    ledger.append((ld, lo, lo.t_end))
    sfx(lo.t_end + 0.08, "stamp", 0.8)
    _t = lo.t_end + 0.2
cO = card("Four documented flights.", "No\u00a0film came home.", 53.75, 57.35, accent=("No\u00a0film",), key_rgb=BONE)
lFoot = label("ONE LATER ACCOUNT ALLEGES TWO MORE FLIGHTS", 80, 1640, 55.75, 57.45, size=20, rgb=DIM, a=0.95, cps=50)
# --- SHOT 8 CANCEL + MUSEUM + END
cP = card("July 1971:", "program canceled.", 57.65, 61.35, accent=("canceled.",))
lWhy = label("FAILURES · NEW SATELLITES · NIXON'S CHINA OPENING", 540, 1660, 59.75, 61.4, size=21, rgb=BONE, align="center", cps=48)
cQ = card("The last one never left China.", "Its wreck went on display in Beijing.", 61.7, 66.15, accent=("Beijing.",))
lMus1 = label("中国航空博物馆", 540, 1600, 64.25, 66.2, size=34, rgb=BONE, align="center", k="cjk", cps=9, tracking=0.12, vel=0.6)
lMus2 = label("CHINA AVIATION MUSEUM · BEIJING", 540, 1650, 64.95, 66.2, size=20, rgb=DIM, align="center", cps=46)
lEnd1 = label("DECLASSIFIED BY THE NRO · 2019", 540, 940, 66.45, None, size=34, rgb=AMBER, a=1.0, align="center", cps=40)
lEnd2 = label("97 DOCUMENTS RELEASED", 540, 1000, 67.35, None, size=25, rgb=BONE, align="center", cps=40)

# ====================================================================== sound design cues (non-musical)
sfx(0.0, "air_bed", 1.0, dur=6.9, fade_in=1.6, fade_out=1.0)
sfx(0.35, "whoosh_up", 0.9)
sfx(5.45, "whoosh_by", 0.9)
sfx(7.05, "lock", 0.7)
sfx(10.05, "sweep", 0.5)
for i in range(5):
    sfx(11.45 + i * 0.24, "tick", 0.55)
sfx(14.2, "dive", 0.7)
sfx(14.75, "scan", 0.5)
sfx(21.35, "jet_bed", 0.8, dur=2.4, fade_in=0.4, fade_out=0.8)
sfx(22.92, "clunk", 0.9)
sfx(23.35, "booster", 1.0, dur=1.75)
sfx(25.05, "sep", 0.7)
sfx(26.95, "whoosh_by", 0.8)
sfx(28.05, "sweep", 0.35)
for i in range(4):
    sfx(30.92 + i * 0.09, "shutter", 0.6)
sfx(34.6, "dive", 0.6)
sfx(35.25, "air_bed", 0.6, dur=9.6, fade_in=0.6, fade_out=0.6)
sfx(35.95, "bolts", 0.9)
sfx(37.05, "chute", 0.9)
sfx(38.92, "boom", 1.0)
sfx(39.9, "prop", 0.8, dur=5.0)
sfx(42.62, "snag", 0.9)
sfx(44.65, "whoosh_by", 0.7)
sfx(45.0, "room", 0.5, dur=12.4, fade_in=0.5, fade_out=0.6)
sfx(57.4, "sub", 0.7)
sfx(61.15, "lamp", 0.7)
sfx(61.5, "room", 0.45, dur=4.7, fade_in=0.6, fade_out=0.6)
sfx(66.1, "sub", 0.5)
sfx(66.2, "room", 0.3, dur=3.0, fade_in=0.3, fade_out=1.2)

# ====================================================================== geo overlays
class GeoOverlays:
    def __init__(self, R):
        self.R = R; g = R.geo
        self.lines = []
        for r in g.rings(None):
            if r[:, 0].max() < 55 or r[:, 0].min() > 157 or r[:, 1].max() < -8 or r[:, 1].min() > 58:
                continue
            if len(r) > 40: r = r[::2]
            self.lines.append(r)
        china = sorted(list(g.rings("CHN")), key=len, reverse=True)
        self.china = china[0]
        self.china_all = china
        allp = np.concatenate(self.lines)
        self.split = np.cumsum([len(l) for l in self.lines])[:-1]
        self.allp = allp
        self.h_all = None

    def project_lines(self, cam, exag):
        sc = self.R.M.project(cam, self.allp[:, 0], self.allp[:, 1], exag=exag)
        return np.split(sc, self.split)

    def draw_borders(self, c, cam, exag, a=0.22, china_a=0.0, china_trace=1.0, china_rgb=AMBER):
        segs = self.project_lines(cam, exag)
        p = skia.Path()
        for s in segs:
            if (s[:, 2] <= 0).any(): continue
            if s[:, 0].max() < -200 or s[:, 0].min() > W + 200 or s[:, 1].max() < -200 or s[:, 1].min() > H + 200: continue
            p.moveTo(*s[0, :2])
            for q in s[1:]: p.lineTo(q[0], q[1])
        c.drawPath(p, paint(BONE, a, stroke=1.3))
        if china_a > 0:
            s = self.R.M.project(cam, self.china[:, 0], self.china[:, 1], exag=exag)
            cp = poly(s[:, :2], close=False)
            if china_trace < 1: cp = trim(cp, 0, china_trace)
            glow_stroke(c, cp, china_rgb, 2.4, a=china_a, glow=9, ga=0.5)

def cam_map(R, lon, lat, alt, tilt, heading, fov=36.0):
    from camera import Camera
    lx, ly = R.geo.local(lon, lat)
    h = math.radians(heading); f = np.array([math.sin(h), 0, -math.cos(h)])
    back = alt * math.tan(math.radians(tilt))
    eye = np.array([lx - f[0] * back, alt, ly - f[2] * back])
    cam = Camera(eye=eye, target=(lx, 0, ly), fov=fov)
    r = alt * (0.75 + math.tan(math.radians(min(tilt + 24, 70))))
    rect = (max(lx - r, 0), max(ly - r, 0), min(lx + r, R.geo.W - 1), min(ly + r, R.geo.H - 1))
    return cam, rect, (lx, ly)

def scrim(c, h=820, a=0.78):
    c.drawRect(skia.Rect.MakeXYWH(0, 0, W, h), paint(INK, 1, shader=lin_grad((0, 0), (0, h), [(0, INK, a), (0.55, INK, a * 0.6), (1, INK, 0)])))

def bottom_scrim(c, y0=1450, a=0.6):
    c.drawRect(skia.Rect.MakeXYWH(0, y0, W, H - y0), paint(INK, 1, shader=lin_grad((0, y0), (0, H), [(0, INK, 0), (1, INK, a)])))

def reticle(c, em, x, y, t, t0, size=120, rgb=SIGNAL, a=1.0):
    k = clamp((t - t0) / 0.55)
    if k <= 0: return
    s = size * (1 + 1.4 * (1 - spring(k * 0.9, 1.4, 5.5)))
    al = a * ease_o(k * 3)
    bracket_box(c, x - s / 2, y - s / 2, x + s / 2, y + s / 2, s * 0.22, rgb, al, 2.4)
    c.drawLine(x - s * 0.62, y, x - s * 0.36, y, paint(rgb, al * 0.8, stroke=1.6))
    c.drawLine(x + s * 0.36, y, x + s * 0.62, y, paint(rgb, al * 0.8, stroke=1.6))
    c.drawLine(x, y - s * 0.62, x, y - s * 0.36, paint(rgb, al * 0.8, stroke=1.6))
    c.drawLine(x, y + s * 0.36, x, y + s * 0.62, paint(rgb, al * 0.8, stroke=1.6))
    c.drawCircle(x, y, 5.5, paint(rgb, al))
    em.drawCircle(x, y, 9, paint(rgb, al * 0.8, blur=6))
    ph = math.fmod(max(t - t0, 0), 1.3) / 1.3
    c.drawCircle(x, y, 8 + ph * size * 0.55, paint(rgb, al * (1 - ph) * 0.7, stroke=2))

def x_mark(c, em, x, y, k, rgb=SIGNAL, s=16):
    if k <= 0: return
    e = back_o(k, 2.2)
    q = s * e
    p = paint(rgb, min(1, k * 3), stroke=3.2, cap=skia.Paint.kRound_Cap)
    c.drawLine(x - q, y - q, x + q, y + q, p); c.drawLine(x - q, y + q, x + q, y - q, p)
    em.drawCircle(x, y, s * 1.2, paint(rgb, 0.45 * min(1, k * 3) * (1 - 0.6 * clamp(k - 1)), blur=10))
    if k < 1.6:
        rr = s * (1 + 3 * ease_o(clamp(k / 1.2)))
        c.drawCircle(x, y, rr, paint(rgb, 0.6 * (1 - clamp(k / 1.2)), stroke=2))

# ====================================================================== shots
def shot_hero_and_target(t, R, F):
    """0 – 14.6 s: chase over the Tarim Basin, lock on Lop Nur, pull back over China, U-2 losses."""
    M, G = R.M, R.geo
    kf = R.trk_hero
    lon, lat, alt, tilt, head = kf(t)
    cam, rect, (fx, fy) = cam_map(R, lon, lat, alt, tilt, head)
    exag = 5.0
    sx, sy = G.local(89.79, 40.81)
    dim = sstep(t, 0.05, 1.5) * (1 - 0.92 * sstep(t, 14.05, 14.6))
    spot_g = 0.55 * sstep(t, 6.6, 7.8) * (1 - sstep(t, 10.0, 11.0))
    M.render_map(R.C.scene_fbo, cam, rect, exag=exag, detail=0.75, dimmer=dim, spot=(sx, sy, 90, spot_g),
                 fog_k=0.00045 * 900 / max(alt, 300), fog_c=(0.035, 0.05, 0.068), grat_a=sstep(t, 6.5, 9.0) * 0.8,
                 china_lift=0.9 + 0.1 * sstep(t, 10, 11))
    scene = R.C.scene_tex
    ov, em, ui = F.ov.c, F.em.c, F.ui.c
    drone = None
    # ---- hero drone 0..6.4
    if t < 6.6:
        blur_px = 26 * (1 - sstep(t, 5.0, 6.2))
        scene = R.C.defocus(scene, 3.2 * (1 - sstep(t, 5.2, 6.4)))
        scene = R.C.blur(scene, 0, blur_px * 0.9)
        # drone screen placement
        enter = expo_o(lin(t, 0.25, 1.7))
        leave = ease_i(lin(t, 5.35, 6.25), 2.4)
        sy_d = mix(2500, 1235, enter) - 1750 * leave
        sx_d = 540 + 16 * math.sin(t * 1.1)
        dist = 360 + 900 * leave
        ndc = np.array([(sx_d / W) * 2 - 1, 1 - (sy_d / H) * 2])
        th = math.tan(math.radians(cam.fov / 2))
        ray = np.array([ndc[0] * th * W / H, ndc[1] * th, -1.0]); ray /= np.linalg.norm(ray)
        wdir = cam.R[:3, :3].T @ ray
        center = cam.eye + wdir * dist
        h = math.radians(head)
        yaw = math.atan2(-math.cos(h), -math.sin(h)) + 0.035 * math.sin(t * 0.8)
        roll = 0.10 * math.sin(t * 1.25 + 0.4) - 0.25 * (1 - enter)
        pitch = -math.radians(tilt) * 0.35
        drone = R.D.render(cam, center, 122, yaw=yaw, pitch=pitch, roll=roll, sun=(-0.55, 0.78, 0.30), glow=1.0,
                           rim=(0.50, 0.42, 0.34))
        # exhaust plume + heat
        tail = R.D.project_model([[1.0, 0, 0], [1.25, 0, 0]])
        if tail[0, 2] > 0:
            (x0, y0), (x1, y1) = tail[0, :2], tail[1, :2]
            dx, dy = x1 - x0, y1 - y0
            for k, (ww, aa, rgb) in enumerate(((26, 0.35, (255, 140, 60)), (12, 0.7, (255, 210, 150)))):
                p = skia.Path(); p.moveTo(x0, y0); p.lineTo(x0 + dx * (1.6 - k * 0.6), y0 + dy * (1.6 - k * 0.6))
                em.drawPath(p, paint(rgb, aa * (1 - leave), stroke=ww, blur=ww * 0.6))
        # speed streaks
        rng = random.Random(11)
        for i in range(34):
            x = rng.uniform(30, W - 30); sp = rng.uniform(1400, 2600); ln = rng.uniform(90, 260)
            y = (rng.uniform(0, H + 600) + t * sp) % (H + 600) - 300
            a = rng.uniform(0.05, 0.16) * sstep(t, 0.4, 1.4) * (1 - sstep(t, 5.6, 6.4))
            ov.drawLine(x, y, x, y + ln, paint(BONE, a, stroke=rng.uniform(1.0, 2.2)))
    # ---- Lop Nur reticle
    if 6.6 < t < 11.2:
        p = M.project(cam, 89.79, 40.81, exag=exag)[0]
        fade = 1 - sstep(t, 10.3, 10.9)
        reticle(ov, em, p[0], p[1], t, 7.0, size=130, a=fade)
        R.place(lLop1, p[0] + 95, p[1] - 8); R.place(lLop2, p[0] + 95, p[1] + 28)
    # ---- China outline + U-2 losses
    if t > 9.9:
        trace = ease_io(lin(t, 10.05, 11.6))
        ca = 0.9 * (1 - sstep(t, 14.0, 14.5))
        R.geoov.draw_borders(ov, cam, exag, a=0.16 * dim, china_a=ca, china_trace=trace)
        u2 = [(115.9, 28.7), (116.9, 27.4), (117.6, 24.6), (109.8, 40.6), (120.75, 30.75)]
        pts = M.project(cam, [p[0] for p in u2], [p[1] for p in u2], exag=exag)
        for i, q in enumerate(pts):
            k = (t - (11.45 + i * 0.24)) / 0.45
            x_mark(ov, em, q[0], q[1], k * (1 - sstep(t, 14.0, 14.45)), s=13)
        cx = pts[:, 0].mean(); cy = pts[:, 1].max()
        R.place(lU2, min(cx - 140, W - 420), cy + 70)
    else:
        R.geoov.draw_borders(ov, cam, exag, a=0.10 * dim * sstep(t, 6.5, 9.0))
    scrim(ov, a=0.72 * sstep(t, 0.3, 1.0))
    bottom_scrim(ov)
    return dict(scene=scene, drone=drone, post=dict(bloom_k=0.07, vig=0.6, grain=0.04, ca=0.005))

def blueprint_grid(c, t, a=1.0, zoom=1.0, cx=540, cy=1100):
    for step, al in ((36, 0.035), (180, 0.075)):
        s = step * zoom
        x0 = cx - math.ceil(cx / s) * s; y0 = cy - math.ceil(cy / s) * s
        p = skia.Path()
        x = x0
        while x < W: p.moveTo(x, 0); p.lineTo(x, H); x += s
        y = y0
        while y < H: p.moveTo(0, y); p.lineTo(W, y); y += s
        c.drawPath(p, paint(ICE, al * a, stroke=1.0))

def shot_blueprint(t, R, F):
    """14.6 – 21.4: scan-reveal of the D-21 on a blueprint grid, dimensions + specs."""
    from camera import Camera
    ov, em, ui = F.ov.c, F.em.c, F.ui.c
    lt = t - 14.6
    fade_in = sstep(lt, 0.0, 0.35)
    out = sstep(t, 21.0, 21.4)
    blueprint_grid(ov, t, a=fade_in * (1 - out), zoom=1.0 + 0.04 * lt / 6.8)
    cam = Camera(eye=(0, 980, 440), target=(0, 0, -20), fov=34)
    yaw = math.radians(-90 + keyframes(lt, [(0, -7), (6.8, 5)], ease=ease_io))
    roll = keyframes(lt, [(0, 0.16), (6.8, -0.10)], ease=ease_io)
    pitch = keyframes(lt, [(0, 0.05), (6.8, -0.02)], ease=ease_io)
    scan = keyframes(lt, [(0.15, 360), (1.45, 1900)], ease=ease_io) if lt < 1.6 else -1.0
    drone = R.D.render(cam, np.array([0, 0, 40.0]), 365, yaw=yaw, pitch=pitch, roll=roll, sun=(-0.5, 0.75, 0.45), glow=0.0,
                       rim=(0.45, 0.55, 0.65), clip_y=scan, alpha=1 - out)
    if 0.1 < lt < 1.6:
        ov.drawLine(0, scan, W, scan, paint(ICE, 0.8, stroke=1.5))
        em.drawRect(skia.Rect.MakeXYWH(0, scan - 3, W, 6), paint(ICE, 0.6, blur=6))
    # dimension lines
    P = R.D.project_model([[-0.05, 0, 0], [1.0, 0, 0], [0.89, 0, -0.222], [0.89, 0, 0.222]])
    k1 = ease_io(lin(lt, 1.2, 1.8)) * (1 - out)
    k2 = ease_io(lin(lt, 1.45, 2.05)) * (1 - out)
    nose, tail, wl, wr = P[0, :2], P[1, :2], P[2, :2], P[3, :2]
    if k1 > 0:
        off = 120
        ax = max(wl[0], wr[0]) + 40
        n2 = (ax, nose[1]); t2 = (ax, tail[1])
        ym = (n2[1] + t2[1]) / 2
        pp = paint(ICE, 0.75 * k1, stroke=1.6)
        ov.drawLine(ax, ym - (ym - n2[1]) * k1, ax, ym + (t2[1] - ym) * k1, pp)
        for q, src in ((n2, nose), (t2, tail)):
            ov.drawLine(q[0] - 12, q[1], q[0] + 12, q[1], paint(ICE, 0.75 * k1, stroke=1.6))
            ov.drawLine(src[0] + 20, src[1], q[0] - 16, q[1], paint(ICE, 0.25 * k1, stroke=1.0, ))
        R.place(lLen, ax - 2, ym + 9, bg=True)
    if k2 > 0:
        yb = max(wl[1], wr[1]) + 90
        xm = (wl[0] + wr[0]) / 2
        pp = paint(ICE, 0.75 * k2, stroke=1.6)
        a0, a1 = min(wl[0], wr[0]), max(wl[0], wr[0])
        ov.drawLine(xm - (xm - a0) * k2, yb, xm + (a1 - xm) * k2, yb, pp)
        for xx in (a0, a1):
            ov.drawLine(xx, yb - 12, xx, yb + 12, paint(ICE, 0.75 * k2, stroke=1.6))
        R.place(lSpan, xm, yb + 9, bg=True)
    scrim(ov, a=0.7)
    return dict(scene=None, drone=drone, post=dict(bloom_k=0.06, vig=0.62, grain=0.04, ca=0.004), bg=(0.0019, 0.0026, 0.0036))

def sky_bg(c, horizon_y, alt_k, warm=0.0):
    """alt_k 0 (low) .. 1 (edge of space)."""
    top = mix((14, 26, 44), (4, 6, 10), alt_k)
    mid = mix((30, 52, 80), (10, 18, 30), alt_k)
    hor = mix((92, 120, 150), (60, 92, 130), alt_k)
    c.drawRect(skia.Rect.MakeWH(W, H), paint(top, 1, shader=lin_grad((0, horizon_y - 1700), (0, horizon_y),
               [(0, top, 1), (0.7, mid, 1), (0.97, hor, 1), (1, hor, 1)])))
    # horizon glow + below-horizon haze
    c.drawRect(skia.Rect.MakeXYWH(0, horizon_y - 60, W, 120), paint(hor, 0.35, blur=40))
    c.drawRect(skia.Rect.MakeXYWH(0, horizon_y, W, H), paint(INK, 1, shader=lin_grad((0, horizon_y), (0, horizon_y + 500),
               [(0, mix(hor, (20, 30, 40), 0.6), 1), (1, (8, 12, 17), 1)])))

def launch_state(t):
    """Drone (with booster until separation) world state: x px, altitude ft, rotation."""
    bs = 860
    b_x = lambda tt: keyframes(tt, [(21.4, -900), (22.7, 210)], ease=ease_o) + 60 * max(tt - 22.7, 0)
    rel, ig, lvl = 22.92, 23.35, 25.55
    mount = (0.50, 0.060)
    alt0 = 40000 - mount[1] * bs / 0.026
    def pos(tt):
        if tt < rel:
            return b_x(tt) + mount[0] * bs, alt0
        x_rel = b_x(rel) + mount[0] * bs
        u = tt - rel
        # horizontal speed ramps 70 -> 640 px/s from ignition to level-off (integrated)
        ts = np.linspace(rel, tt, 64)
        sp = 60 + 1100 * np.array([sstep(q, ig - 0.1, lvl - 0.3) for q in ts])
        x = x_rel + np.trapezoid(sp, ts) if len(ts) > 1 else x_rel
        drop = 0.5 * 9000 * min(u, 0.43) ** 2
        a_drop = alt0 - drop
        a = a_drop + (90000 - a_drop + 0) * sstep(tt, ig, lvl) ** 1.0 if tt > ig else a_drop - 9000 * 0.43 * max(u - 0.43, 0)
        return x, a
    x, a = pos(t)
    x2, a2 = pos(t + 0.02)
    rot = math.atan2(-(a2 - a) * 0.026, max(x2 - x, 1e-3)) if t > rel else 0.0
    return b_x(t), x, a, rot

def shot_launch(t, R, F):
    """21.4 - 27.8: side view - B-52 release, booster climb to 90,000 ft."""
    ov, em, ui = F.ov.c, F.em.c, F.ui.c
    K = 0.026  # px per ft
    bs = 860
    ds = bs * 0.264
    b_x, d_x, d_alt, d_rot = launch_state(t)
    b_alt = 40000
    sep = 25.05
    follow = sstep(t, 23.3, 24.3)
    cam_x = mix(keyframes(t, [(21.4, 0), (23.3, 120)], ease=ease_io), d_x - 520, follow) + 1500 * ease_i(lin(t, 26.75, 27.8), 2.4)
    cam_alt = mix(40500, d_alt + 1200, follow)
    def sy(alt): return 1150 - (alt - cam_alt) * K
    def sx(x): return x - cam_x
    alt_k = clamp((cam_alt - 40000) / 50000)
    hz = 1780 + (cam_alt - 40000) * 0.004
    sky_bg(ov, hz, alt_k)
    rx = 70
    for alt in range(0, 100001, 5000):
        y = sy(alt)
        if -40 < y < H + 40:
            major = alt % 10000 == 0
            ov.drawLine(rx, y, rx + (30 if major else 16), y, paint(BONE, 0.55 if major else 0.3, stroke=1.6))
            if major:
                draw_text(ov, f"{alt:,} FT", rx + 40, y + 8, "mono", 22, AMBER if alt == 90000 else BONE, 0.75, tracking=0.06)
    ov.drawLine(rx, 0, rx, H, paint(BONE, 0.18, stroke=1.2))
    y90 = sy(90000)
    k90 = sstep(t, 24.9, 25.6)
    if k90 > 0:
        dash = paint(AMBER, 0.5 * k90, stroke=1.6); dash.setPathEffect(skia.DashPathEffect.Make([10, 10], -t * 40))
        ov.drawLine(rx + 150, y90, rx + 150 + (W - rx - 190) * k90, y90, dash)
    if -bs - 100 < sx(b_x) < W + 200:
        S.draw_b52(ov, sx(b_x), sy(b_alt), bs)
    if t < sep:
        S.draw_booster(ov, sx(d_x), sy(d_alt), ds, rot=d_rot)
    else:
        u = t - sep
        _, bx0, balt0, brot0 = launch_state(sep)
        bx = bx0 + 300 * u; balt = balt0 - (1500 * u + 14000 * u * u)
        S.draw_booster(ov, sx(bx), sy(balt), ds, rot=brot0 + 1.3 * u, alpha=1 - sstep(u, 0.7, 1.5))
    if 23.35 < t < sep:
        fl = ease_o(lin(t, 23.35, 23.5)) * (1 - sstep(t, sep - 0.08, sep))
        ca, sa = math.cos(d_rot), math.sin(d_rot)
        nx = sx(d_x) + (-0.17 * ca - 0.075 * sa) * ds
        ny = sy(d_alt) + (-0.17 * sa + 0.075 * ca) * ds
        L = ds * (0.75 + 0.10 * math.sin(t * 57))
        for (ww, aa, rgb, ll) in ((30, 0.35, (255, 120, 40), 1.0), (14, 0.75, (255, 200, 120), 0.62), (6, 0.9, (255, 250, 230), 0.32)):
            p = skia.Path(); p.moveTo(nx, ny); p.lineTo(nx - ca * L * ll, ny - sa * L * ll)
            em.drawPath(p, paint(rgb, aa * fl, stroke=ww, blur=ww * 0.5))
        em.drawCircle(nx, ny, 26, paint((255, 170, 90), 0.45 * fl, blur=22))
    # smoke trail from history of nozzle positions
    if t > 23.4:
        for i in range(1, 40):
            tb = t - i * 0.045
            if tb < 23.4 or tb > sep: continue
            _, hx, ha, hr = launch_state(tb)
            ca, sa = math.cos(hr), math.sin(hr)
            px = sx(hx) + (-0.25 * ca - 0.075 * sa) * ds; py = sy(ha) + (-0.25 * sa + 0.075 * ca) * ds
            age = t - tb
            ov.drawCircle(px, py, 12 + age * 70, paint((150, 158, 166), 0.16 * math.exp(-age * 1.4), blur=8 + age * 30))
    glow = sstep(t, sep + 0.2, sep + 0.7)
    S.draw_d21_side(ov, sx(d_x), sy(d_alt), ds, rot=d_rot, glow=glow, em=em, hatch_on=False)
    if glow > 0:
        ca, sa = math.cos(d_rot), math.sin(d_rot)
        nx, ny = sx(d_x) - 0.012 * ds * ca, sy(d_alt) - 0.012 * ds * sa
        em.drawLine(nx, ny, nx - 150 * glow, ny, paint((255, 150, 70), 0.55 * glow, stroke=9, blur=8))
    R.place(lMach, sx(d_x) + ds * 0.5, sy(d_alt) - 90, align="center")
    if t > 26.7:
        k = sstep(t, 26.8, 27.8)
        rng = random.Random(5)
        for i in range(30):
            y = rng.uniform(0, H); ln = rng.uniform(200, 700) * k
            x = (rng.uniform(0, W + 800) - t * 4000) % (W + 800) - 400
            ov.drawLine(x, y, x + ln, y, paint(BONE, 0.10 * k, stroke=1.5))
    scrim(ov, a=0.55)
    whip = sstep(t, 27.2, 27.8)
    return dict(scene=None, drone=None, post=dict(bloom_k=0.09, vig=0.6, grain=0.04, ca=0.005 + 0.02 * whip),
                bg=(0.002, 0.003, 0.005), hblur=60 * whip)

ROUTE_PTS = [(131.0, 21.0), (123.0, 25.0), (112.0, 31.0), (100.5, 37.0), (92.0, 40.2), (88.6, 41.3), (87.6, 40.4),
             (89.2, 39.4), (96.0, 35.0), (105.0, 28.0), (112.0, 21.5), (117.5, 17.5)]

def catmull(pts, n=500):
    P = np.array(pts, float)
    P = np.vstack([P[0] * 2 - P[1], P, P[-1] * 2 - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s in np.linspace(0, 1, n // (len(pts) - 1), endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * s + (2 * p0 - 5 * p1 + 4 * p2 - p3) * s * s + (-p0 + 3 * p1 - 3 * p2 + p3) * s ** 3))
    out.append(P[-2])
    return np.array(out)

ROUTE = catmull(ROUTE_PTS, 660)
_seg = np.linalg.norm(np.diff(ROUTE, axis=0), axis=1)
ROUTE_S = np.concatenate([[0], np.cumsum(_seg)]) / _seg.sum()
LOP_S = ROUTE_S[np.argmin(np.linalg.norm(ROUTE - np.array([89.79, 40.81]), axis=1))]

def route_progress(t):
    """Launch 28.8 s, over Lop Nur 30.95 s, recovery zone 33.6 s."""
    if t < 28.8: return 0.0
    if t < 30.95: return LOP_S * lin(t, 28.8, 30.95) ** 1.15
    return LOP_S + (1 - LOP_S) * ease_o(lin(t, 30.95, 33.6), 1.6)

def shot_route(t, R, F):
    """27.8 – 35.2: illustrative mission profile on the map."""
    M, G = R.M, R.geo
    ov, em, ui = F.ov.c, F.em.c, F.ui.c
    lon, lat, alt, tilt, head = R.trk_route(t)
    cam, rect, _ = cam_map(R, lon, lat, alt, tilt, head)
    exag = 4.0
    dim = sstep(t, 27.8, 28.3) * (1 - sstep(t, 34.75, 35.2))
    sx_, sy_ = G.local(117.5, 17.5)
    M.render_map(R.C.scene_fbo, cam, rect, exag=exag, detail=0.6, dimmer=dim, grat_a=0.9, fog_k=0.00011, fog_c=(0.03, 0.045, 0.06),
                 spot=(sx_, sy_, 60, 0.5 * sstep(t, 33.2, 34.0)))
    scene = R.C.scene_tex
    if t < 28.2:
        scene = R.C.blur(scene, -70 * (1 - sstep(t, 27.8, 28.2)), 0)
    R.geoov.draw_borders(ov, cam, exag, a=0.15 * dim, china_a=0.55 * dim, china_trace=1.0)
    ALT = 30000
    # B-52 track from Guam
    gm = M.project(cam, [144.8, 131.0], [13.4, 21.0], exag=exag, alt_m=ALT)
    bk = ease_io(lin(t, 27.9, 28.8))
    guam = M.project(cam, 144.8, 13.4, exag=exag)[0]
    ov.drawCircle(guam[0], guam[1], 7, paint(BONE, 0.9 * dim))
    ov.drawCircle(guam[0], guam[1], 14, paint(BONE, 0.4 * dim, stroke=1.5))
    R.place(lGuam, guam[0] + 24, guam[1] + 8)
    if bk > 0:
        lp = poly(gm[:, :2]); lp = trim(lp, 0, bk)
        glow_stroke(ov, lp, BONE, 2.0, a=0.7 * dim, glow=6, ga=0.3, dash=[12, 10])
    L0 = gm[1]
    if t > 28.7:
        k = ease_o(lin(t, 28.7, 29.2))
        ov.drawCircle(L0[0], L0[1], 6 + 10 * (1 - k), paint(AMBER, k * dim))
    # D-21 route
    pr = route_progress(t)
    if pr > 0:
        sc = M.project(cam, ROUTE[:, 0], ROUTE[:, 1], exag=exag, alt_m=ALT)
        n = max(2, int(np.searchsorted(ROUTE_S, pr)))
        path = poly(sc[:n, :2])
        glow_stroke(ov, path, AMBER, 3.0, a=0.95 * dim, glow=10, ga=0.55)
        head_pt = sc[n - 1, :2]; prev = sc[max(n - 6, 0), :2]
        ang = math.atan2(head_pt[1] - prev[1], head_pt[0] - prev[0])
        if pr < 0.999:
            em.drawCircle(head_pt[0], head_pt[1], 16, paint((255, 220, 160), 0.9 * dim, blur=10))
            pl = S.xf(S.d21_planform(), head_pt[0], head_pt[1], 54, rot=ang + math.pi / 2)
            ov.drawPath(pl, paint(BONE, dim))
        # recovery point
        rp = M.project(cam, 117.5, 17.5, exag=exag)[0]
        if t > 32.9:
            reticle(ov, em, rp[0], rp[1], t, 33.0, size=96, rgb=AMBER, a=dim)
            R.place(lRec, rp[0] + 70, rp[1] + 8)
    # Lop Nur target marker + photo flashes
    lp_ = M.project(cam, 89.79, 40.81, exag=exag)[0]
    if t > 29.4:
        reticle(ov, em, lp_[0], lp_[1], t, 29.6, size=84, rgb=SIGNAL, a=dim * (1 - sstep(t, 33.5, 34.2)))
    for i in range(4):
        tf = 30.92 + i * 0.09
        if tf < t < tf + 0.25:
            k = 1 - (t - tf) / 0.25
            em.drawCircle(lp_[0], lp_[1], 26, paint(BONE, 0.45 * k, blur=14))
            ov.drawCircle(lp_[0], lp_[1], 30 + 40 * (1 - k), paint(BONE, 0.5 * k, stroke=1.5))
    scrim(ov, a=0.75)
    bottom_scrim(ov, 1500, 0.7)
    return dict(scene=scene, drone=None, post=dict(bloom_k=0.08, vig=0.6, grain=0.04, ca=0.005))

def ocean_bg(c, t, hz):
    sky_bg(c, hz, 0.55)
    # ocean
    c.drawRect(skia.Rect.MakeXYWH(0, hz, W, H - hz + 10), paint(INK, 1, shader=lin_grad((0, hz), (0, H),
               [(0, (38, 54, 70), 1), (0.08, (16, 26, 36), 1), (1, (5, 9, 13), 1)])))
    rng = random.Random(3)
    for i in range(70):
        yy = hz + (rng.random() ** 2.2) * (H - hz)
        depth = (yy - hz) / max(H - hz, 1)
        ln = 20 + depth * 220
        x = (rng.uniform(-200, W + 200) + t * (8 + 30 * depth)) % (W + 400) - 200
        c.drawLine(x, yy, x + ln, yy, paint(ICE, 0.05 + 0.08 * (1 - depth), stroke=1 + depth * 2))
    c.drawRect(skia.Rect.MakeXYWH(0, hz - 2, W, 4), paint((140, 170, 200), 0.35, blur=3))

EJ, BOOM, SNAG = 35.95, 38.92, 42.62
REC_DS, REC_CS = 760, 600

def rec_drone(t):
    x = keyframes(t, [(35.2, -1100), (EJ, -167)], ease=ease_o) + (225 * (t - EJ) if t > EJ else 0)
    y = 1000 + 40 * (t - 35.2) - 300 * sstep(t, EJ, BOOM + 0.3)
    rot = 0.06 - 0.34 * sstep(t, EJ, 37.4) + 0.28 * max(t - 37.9, 0) ** 1.5
    return x, y, rot

def rec_hatch(t):
    hx_rel, hy_rel = 0.8125 * REC_DS, 0.022 * REC_DS
    if t < EJ:
        x, y, r = rec_drone(t)
        return x + hx_rel, y + hy_rel, r
    x0, y0, r0 = rec_drone(EJ)
    u = t - EJ
    x = x0 + hx_rel + 170 * (1 - math.exp(-u * 1.5)) / 1.5
    g, tc, vd = 420.0, 1.1, 55.0
    if u < tc:
        dy = 0.5 * g * u * u
    else:
        v1 = g * tc
        dy = 0.5 * g * tc * tc + vd * (u - tc) + (v1 - vd) * (1 - math.exp(-(u - tc) * 4)) / 4
    rot = r0 * math.exp(-u * 2) + 0.10 * math.sin(u * 2.3) * sstep(u, 1.0, 1.8)
    return x, y0 + hy_rel + dy, rot

def rec_plane(t):
    hx, hy, _ = rec_hatch(SNAG)
    cs = REC_CS
    X = hx + 0.175 * cs
    Y = hy - 165 - 0.465 * cs
    vp = 520
    return X + vp * (t - SNAG), Y - 18 * (t - SNAG)

def shot_recovery(t, R, F):
    """35.2 - 45.0: hatch ejection, self-destruct, mid-air catch."""
    ov, em, ui = F.ov.c, F.em.c, F.ui.c
    ds, cs = REC_DS, REC_CS
    hx, hy, hrot = rec_hatch(min(t, SNAG))
    hy0 = rec_hatch(35.2)[1]
    cam_y = (max(hy, hy0) - hy0) * sstep(t, 36.4, 38.0) - 230 * sstep(t, 36.4, 38.0) if t < SNAG else (rec_hatch(SNAG)[1] - hy0 - 230)
    px, py = rec_plane(t)
    pX0, _ = rec_plane(SNAG)
    cam_x = 230 * ease_io(lin(t, 38.9, 42.3)) + max(px - pX0, 0) * sstep(t, SNAG - 0.2, SNAG + 1.1) + 1300 * ease_i(lin(t, 44.5, 45.0), 2.2)
    hz = 1640 - cam_y * 0.22
    ocean_bg(ov, t, hz)
    X = lambda x: x - cam_x
    Y = lambda y: y - cam_y
    dx, dy, drot = rec_drone(t)
    if t < BOOM:
        S.draw_d21_side(ov, X(dx), Y(dy), ds, rot=drot, hatch_on=(t < EJ), hatch_hi=sstep(t, 35.6, EJ))
    ca, sa = math.cos(drot), math.sin(drot)
    for i, fx in enumerate((0.71, 0.81, 0.915)):
        tf = EJ - 0.02 + i * 0.03
        if tf < t < tf + 0.2:
            k = 1 - (t - tf) / 0.2
            qx = X(dx) + fx * ds * ca - 0.036 * ds * sa; qy = Y(dy) + fx * ds * sa + 0.036 * ds * ca
            em.drawCircle(qx, qy, 10 + 22 * (1 - k), paint((255, 230, 180), k, blur=8))
    if t >= BOOM:
        u3 = t - BOOM
        bx, by, br = rec_drone(BOOM)
        ex = X(bx + 0.5 * ds * math.cos(br)); ey = Y(by + 0.5 * ds * math.sin(br))
        fl = math.exp(-u3 * 5.0)
        em.drawCircle(ex, ey, 40 + 150 * ease_o(min(u3 / 0.5, 1)), paint((255, 150, 70), 0.55 * fl, blur=40))
        em.drawCircle(ex, ey, 22 + 50 * ease_o(min(u3 / 0.3, 1)), paint((255, 240, 210), 0.9 * fl, blur=14))
        ov.drawCircle(ex, ey, 20 + 380 * ease_o(min(u3 / 1.1, 1)), paint(BONE, 0.3 * math.exp(-u3 * 2.5), stroke=2.5))
        rng = random.Random(9)
        for i in range(10):
            ang = rng.uniform(0, 2 * math.pi); sp = rng.uniform(30, 140)
            qx = ex + math.cos(ang) * sp * min(u3, 1.5); qy = ey + math.sin(ang) * sp * min(u3, 1.5) - 25 * u3
            ov.drawCircle(qx, qy, 34 + 70 * min(u3, 2), paint((110, 114, 118), 0.25 * clamp(1 - u3 / 4), blur=20))
        for i in range(48):
            ang = rng.uniform(0, 2 * math.pi); sp = rng.uniform(120, 480)
            d = sp * (1 - math.exp(-u3 * 2.2)) / 2.2 * 2.0
            qx = ex + math.cos(ang) * d; qy = ey + math.sin(ang) * d + 180 * u3 * u3
            sz = rng.uniform(3, 13); a = clamp(1.5 - u3 * 0.5)
            ov.save(); ov.rotate(math.degrees(ang + u3 * rng.uniform(-9, 9)), qx, qy)
            ov.drawRect(skia.Rect.MakeXYWH(qx - sz / 2, qy - sz / 4, sz, sz / 2), paint((34, 38, 44), a)); ov.restore()
            if i % 3 == 0:
                em.drawCircle(qx, qy, 3, paint((255, 170, 80), a * math.exp(-u3 * 1.4), blur=2))
    if t > EJ:
        open_k = clamp(spring(max(t - 37.05, 0) * 1.05, 1.1, 4.2), 0, 1.15) if t > 37.05 else 0.0
        if t < SNAG:
            hx_d, hy_d = X(hx), Y(hy)
            if open_k > 0:
                top = hy_d - 340 * min(1.0, ease_o(min((t - 37.05) / 0.35, 1)))
                S.draw_chute(ov, hx_d, top, 230, min(open_k, 1.08), sway=8 * math.sin(t * 1.7), lines_to=(hx_d, hy_d - 18))
            rotd = hrot
        else:
            u2 = t - SNAG
            tipx = X(px) + (0.11 - 0.30) * cs + 0.015 * cs
            tipy = Y(py) + 0.45 * cs + 0.015 * cs
            h0x, h0y = X(rec_hatch(SNAG)[0]), Y(rec_hatch(SNAG)[1])
            k = ease_o(min(u2 / 0.7, 1), 2)
            hx_d = mix(h0x, tipx - 150, k); hy_d = mix(h0y, tipy + 190, k)
            ctx_ = mix(h0x, tipx - 230, k); cty = mix(h0y - 340, tipy + 30, k)
            S.draw_chute(ov, ctx_, cty, 230, 1.0, lines_to=(hx_d, hy_d - 18), collapse=ease_o(min(u2 / 0.45, 1)))
            ov.drawLine(tipx, tipy, ctx_ + 20, cty + 40, paint(BONE, 0.8, stroke=2.2))
            rotd = 0.35 * math.sin(u2 * 4.5) * math.exp(-u2 * 1.3) - 0.2 * k
            if u2 < 0.25:
                em.drawCircle(tipx, tipy, 30, paint(AMBER, 0.8 * (1 - u2 / 0.25), blur=14))
        S.draw_hatch(ov, hx_d, hy_d, ds, rot=rotd)
        R.place(lHatch, hx_d + 120, hy_d + 9)
        if 37.4 < t < 40.6:
            k = ease_o(lin(t, 37.35, 37.6)) * (1 - sstep(t, 40.2, 40.5))
            ov.drawLine(hx_d + 92, hy_d, hx_d + 112, hy_d, paint(AMBER, k, stroke=1.6))
    if t > 39.9:
        S.draw_c130(ov, X(px), Y(py), cs, t)
    scrim(ov, a=0.7)
    whip = sstep(t, 44.55, 45.0)
    return dict(scene=None, drone=None, post=dict(bloom_k=0.08, vig=0.58, grain=0.04, ca=0.005 + 0.02 * whip),
                bg=(0.002, 0.003, 0.005), hblur=-70 * whip)

def shot_ledger(t, R, F):
    """45.0 – 57.4: what actually happened."""
    ov, em, ui = F.ov.c, F.em.c, F.ui.c
    lt = t - 45.0
    ov.drawRect(skia.Rect.MakeWH(W, H), paint(INK, 1, shader=rad_grad(540, 900, 1400, [(0, (20, 25, 31), 1), (1, (6, 8, 11), 1)])))
    zoom = 1 + 0.02 * lt / 12
    # ruled lines
    for i in range(30):
        y = 600 + i * 49 * zoom
        ov.drawLine(60, y, W - 60, y, paint(BONE, 0.025, stroke=1))
    hk = ease_io(lin(t, 47.0, 47.8))
    ov.drawLine(80, 668, 80 + (W - 160) * hk, 668, paint(AMBER, 0.6 * (1 - sstep(t, 57.1, 57.4)), stroke=1.6))
    for i, (ld, lo, tend) in enumerate(ledger):
        dimk = 1 - 0.45 * sstep(t, 54.0, 54.5)
        ld.draw(ui, t, dimk)
        lo.draw(ui, t, dimk)
        y = ROW_Y0 + i * ROW_DY
        k = (t - tend - 0.05) / 0.35
        x_mark(ui, em, W - 120, y + 40, k * (1 - sstep(t, 57.05, 57.4)), s=20)
    return dict(scene=None, drone=None, post=dict(bloom_k=0.05, vig=0.55, grain=0.045, ca=0.004), bg=(0.002, 0.003, 0.004),
                hblur=70 * (1 - sstep(t, 45.0, 45.35)))

def shot_cancel(t, R, F):
    """57.4 – 61.5: the drone alone in the dark; the lights go down."""
    from camera import Camera
    ov, em, ui = F.ov.c, F.em.c, F.ui.c
    lt = t - 57.4
    cam = Camera(eye=(0, 760, 700), target=(0, 0, 40), fov=32)
    lk = sstep(lt, 0.0, 0.7) * (1 - sstep(t, 60.9, 61.45))
    ov.drawRect(skia.Rect.MakeWH(W, H), paint(INK, 1, shader=rad_grad(540, 1150, 900, [(0, (24, 28, 34), lk), (1, (6, 8, 11), 1)])))
    drone = R.D.render(cam, np.array([0, 0, 60.0]), 330, yaw=math.radians(-90 + 30 * lt / 4.1 - 18), pitch=0.05,
                       roll=0.25 - 0.1 * lt, sun=(0.1, 1.0, 0.15), glow=0.0, rim=(0.5, 0.45, 0.4), light_k=0.12 + 0.88 * lk)
    return dict(scene=None, drone=drone, post=dict(bloom_k=0.06, vig=0.7, grain=0.045, ca=0.004), bg=(0.0015, 0.002, 0.003))

def wreck_pieces():
    """Cut the D-21 planform into jagged fragments."""
    base = S.d21_planform()
    cuts = [[(-0.5, -0.62), (0.5, -0.62), (0.5, -0.18), (0.1, -0.22), (-0.06, -0.12), (-0.5, -0.16)],
            [(-0.5, -0.16), (-0.06, -0.12), (0.1, -0.22), (0.5, -0.18), (0.5, 0.12), (0.02, 0.05), (-0.5, 0.15)],
            [(-0.5, 0.15), (0.02, 0.05), (0.5, 0.12), (0.5, 0.6), (-0.5, 0.6)]]
    pieces = []
    for cpts in cuts:
        cp = poly(cpts, True)
        out = skia.Op(base, cp, skia.PathOp.kIntersect_PathOp)
        pieces.append(out)
    return pieces

WRECK = None

def shot_museum(t, R, F):
    """61.5 – 66.2: wreckage under a museum spotlight."""
    global WRECK
    if WRECK is None:
        WRECK = wreck_pieces()
    ov, em, ui = F.ov.c, F.em.c, F.ui.c
    lt = t - 61.5
    on = sstep(lt, 0.05, 0.35) * (0.92 + 0.08 * (1 - math.exp(-lt * 6)))
    flick = 1.0 if lt > 0.32 else (0.4 if 0.12 < lt < 0.18 else 1.0)
    on *= flick
    push = 1 + 0.06 * ease_io(lin(t, 61.5, 66.2))
    out = 1 - sstep(t, 65.9, 66.25)
    ov.drawRect(skia.Rect.MakeWH(W, H), paint(INK))
    ov.save(); ov.translate(540, 1150); ov.scale(push, push); ov.translate(-540, -1150)
    # floor with spotlight pool
    floor_y = 980
    ov.drawRect(skia.Rect.MakeXYWH(0, floor_y, W, H - floor_y), paint(INK, 1, shader=lin_grad((0, floor_y), (0, H),
                [(0, (10, 12, 15), 1), (1, (16, 18, 21), 1)])))
    ov.drawOval(skia.Rect.MakeXYWH(90, 1060, 900, 420), paint((120, 112, 98), 0.55 * on * out, blur=60))
    # beam
    beam = poly([(470, -50), (610, -50), (1020, 1300), (60, 1300)], True)
    ov.drawPath(beam, paint(BONE, 1, shader=lin_grad((0, 0), (0, 1300), [(0, BONE, 0.10 * on * out), (1, BONE, 0.02 * on * out)]),
                blur=30))
    # dust motes
    rng = random.Random(21)
    for i in range(70):
        y = (rng.uniform(0, 1300) - lt * rng.uniform(8, 30)) % 1300
        xw = 470 + (y / 1300) * 0 - 0
        span = 140 + (y / 1300) * 820
        x = 540 + (rng.uniform(-0.5, 0.5)) * span + 10 * math.sin(lt * rng.uniform(0.3, 1.2) + i)
        ov.drawCircle(x, y, rng.uniform(1, 2.6), paint(BONE, rng.uniform(0.1, 0.5) * on * out))
    # wreck fragments laid on the floor in perspective
    src = [skia.Point(-0.5, -0.6), skia.Point(0.5, -0.6), skia.Point(0.5, 0.6), skia.Point(-0.5, 0.6)]
    dst = [skia.Point(200, 1040), skia.Point(900, 1050), skia.Point(1060, 1430), skia.Point(30, 1415)]
    m = skia.Matrix(); m.setPolyToPoly(src, dst)
    ghost = skia.Path(S.d21_planform()); ghost.transform(m)
    gk = sstep(t, 62.6, 63.6) * out
    gp = paint(ICE, 0.32 * gk, stroke=1.6); gp.setPathEffect(skia.DashPathEffect.Make([9, 8], -lt * 12))
    gh = skia.Path(ghost); gh.offset(0, -150 * gk)
    ov.drawPath(gh, gp)
    offs = [((0.02, -0.06), -0.10), ((-0.05, 0.0), 0.06), ((0.06, 0.07), -0.04)]
    for pc, ((ox, oy), rot) in zip(WRECK, offs):
        q = skia.Path(pc)
        mm = skia.Matrix(); mm.setRotate(math.degrees(rot)); mm.postTranslate(ox, oy)
        q.transform(mm); q.transform(m)
        sh = skia.Path(q); sh.offset(10, 14)
        ov.drawPath(sh, paint(INK, 0.7 * on, blur=10))
        ov.drawPath(q, paint((30, 33, 37), out, shader=lin_grad((0, 1100), (0, 1400), [(0, (52, 55, 60), out * (0.3 + 0.7 * on)),
                                                                                         (1, (18, 20, 23), out)])))
        ov.drawPath(q, paint((190, 180, 160), 0.35 * on * out, stroke=1.6))
    ov.restore()
    return dict(scene=None, drone=None, post=dict(bloom_k=0.07, vig=0.68, grain=0.05, ca=0.004), bg=(0.001, 0.0013, 0.002))

def shot_end(t, R, F):
    ov = F.ov.c
    ov.drawRect(skia.Rect.MakeWH(W, H), paint(INK))
    fade = 1 - sstep(t, 68.5, 69.2)
    return dict(scene=None, drone=None, post=dict(bloom_k=0.04, vig=0.6, grain=0.04, ca=0.003, fade=fade), bg=(0.0013, 0.0017, 0.0024))

SHOTS = [(0.0, 14.6, shot_hero_and_target), (14.6, 21.4, shot_blueprint), (21.4, 27.8, shot_launch), (27.8, 35.2, shot_route),
         (35.2, 45.0, shot_recovery), (45.0, 57.4, shot_ledger), (57.4, 61.5, shot_cancel), (61.5, 66.2, shot_museum),
         (66.2, 69.21, shot_end)]

# ====================================================================== renderer
class Frames:
    def __init__(self):
        self.ov, self.em, self.ui = Layer(), Layer(), Layer()

class Renderer:
    def __init__(self):
        from geo import Geo
        from gfx import MapGL, Drone3D, Compositor
        from post import Post
        self.geo = Geo()
        self.M = MapGL(self.geo)
        self.D = Drone3D()
        self.C = Compositor()
        self.P = Post()
        self.F = Frames()
        self.geoov = GeoOverlays(self)
        self.trk_hero = Track([
            (0.0, (83.2, 39.75, 640, 30, 76)),
            (5.3, (88.0, 40.55, 660, 30, 76)),
            (7.3, (89.79, 40.81, 1250, 17, 8)),
            (9.6, (89.79, 40.81, 1420, 15, 0)),
            (11.3, (103.5, 34.5, 4100, 24, 0)),
            (13.9, (107.0, 33.0, 3800, 26, 0)),
            (14.6, (110.0, 32.0, 2300, 14, 0))])
        self.trk_route = Track([
            (27.8, (133.0, 21.0, 2900, 16, -6)),
            (28.9, (127.0, 25.0, 3500, 18, -4)),
            (30.9, (106.0, 33.0, 4300, 20, 0)),
            (31.7, (103.0, 32.5, 4400, 20, 0)),
            (33.5, (113.0, 24.0, 3500, 18, 0)),
            (35.2, (117.5, 18.2, 650, 8, 0))])
        self.placed = {}

    def place(self, lab, x, y, align="left", bg=False):
        """Move a label so its first glyph lands at x,y (or centred)."""
        if not hasattr(lab, "_g"):
            lab._g = list(lab.ty.glyphs)
            lab._x0, lab._y0 = lab._g[0][1], lab._g[0][2]
        if align == "center" or lab.ty.align == "center":
            x = x - lab.width / 2
        dx, dy = x - lab._x0, y - lab._y0
        lab.ty.glyphs = [(gid, gx + dx, gy + dy, idx, rgb) for gid, gx, gy, idx, rgb in lab._g]
        lab.x, lab.y = x, y
        self.placed[id(lab)] = bg

    def frame(self, t):
        F = self.F
        F.ov.clear(); F.em.clear(); F.ui.clear()
        for t0, t1, fn in SHOTS:
            if t0 <= t < t1:
                res = fn(t, self, F)
                break
        ui = F.ui.c
        for c in CARDS:
            c.draw(ui, t)
        for l in LABELS:
            if id(l) in self.placed and self.placed[id(l)]:
                if l.t0 - 0.01 <= t <= (l.t1 or 99):
                    n = sum(1 for ts in l.ty.times if ts <= t)
                    if n:
                        ui.drawRect(skia.Rect.MakeXYWH(l.x - 10, l.y - l.size * 0.95, l.width + 20, l.size * 1.3), paint(INK, 0.85))
            l.draw(ui, t)
        bg = res.get("bg", (0.0016, 0.0024, 0.0036))
        scene = res.get("scene")
        out = self.C.run(scene, F.ov.arr, F.em.arr, res.get("drone"), em_gain=3.0, bg=bg)
        hb = res.get("hblur", 0.0)
        if abs(hb) > 0.5:
            out = self.C.blur(out, hb, 0, taps=18)
        self.P.set_ui(F.ui.arr)
        pp = dict(res.get("post", {}))
        self.P.run(out, t, **pp)
        return self.P.read()
