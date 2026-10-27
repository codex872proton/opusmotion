"""Sound design: user's keystrokes on every typed glyph + synthesised, non-musical effects. No music."""
import json, os, random, sys
import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS = os.path.join(ROOT, "assets", "sfx", "keys")
rng = np.random.default_rng(7)

def db(x): return 10 ** (x / 20)

def noise(n, color="white"):
    w = rng.standard_normal(n)
    if color == "white": return w
    f = np.fft.rfftfreq(n, 1 / SR); f[0] = f[1]
    p = {"pink": 0.5, "brown": 1.0}[color]
    s = np.fft.irfft(np.fft.rfft(w) / f ** p, n)
    return s / (np.abs(s).max() + 1e-9)

def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], "bandpass", fs=SR, output="sos"); return signal.sosfilt(sos, x)

def lp(x, fc, order=2):
    sos = signal.butter(order, fc, "lowpass", fs=SR, output="sos"); return signal.sosfilt(sos, x)

def hp(x, fc, order=2):
    sos = signal.butter(order, fc, "highpass", fs=SR, output="sos"); return signal.sosfilt(sos, x)

def env_adsr(n, a, d_or_none=None, r=0.05):
    e = np.ones(n)
    na = max(int(a * SR), 1); nr = max(int(r * SR), 1)
    e[:na] = np.linspace(0, 1, na) ** 2
    e[-nr:] *= np.linspace(1, 0, nr) ** 2
    return e

def expdecay(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))

def sweep_bp(x, f0, f1, q=2.0, steps=48):
    """Time-varying band-pass by overlap-add blocks."""
    n = len(x); out = np.zeros(n); blk = n // steps + 1
    win = np.hanning(blk * 2)
    for i in range(steps):
        s = i * blk; e = min(s + blk * 2, n)
        if s >= n: break
        f = f0 * (f1 / f0) ** (i / max(steps - 1, 1))
        lo, hi = max(f / (1 + 1 / q), 30), min(f * (1 + 1 / q), SR / 2 - 100)
        seg = bp(x[s:e], lo, hi)
        out[s:e] += seg * win[: e - s]
    return out

def stereo(m, pan=0.0, width=0.0):
    l = m * np.sqrt(0.5 * (1 - pan)); r = m * np.sqrt(0.5 * (1 + pan))
    if width > 0:
        d = int(width * 0.012 * SR)
        r = np.concatenate([np.zeros(d), r[:-d]]) if d else r
    return np.stack([l, r], 1)

def norm(x, peak=1.0):
    return x / (np.abs(x).max() + 1e-12) * peak

# ------------------------------------------------------------------ effect generators (return stereo arrays)
def fx_air_bed(dur, fade_in=1.0, fade_out=1.0, **_):
    n = int(dur * SR)
    a = lp(noise(n, "pink"), 900) * 0.5 + bp(noise(n, "white"), 1200, 4000) * 0.05
    b = lp(noise(n, "pink"), 900) * 0.5 + bp(noise(n, "white"), 1200, 4000) * 0.05
    rum = lp(noise(n, "brown"), 90) * 1.2
    mod = 0.75 + 0.25 * np.sin(np.arange(n) / SR * 2 * np.pi * 0.23)
    e = np.ones(n); fi, fo = int(fade_in * SR), int(fade_out * SR)
    e[:fi] = np.linspace(0, 1, fi) ** 2; e[-fo:] *= np.linspace(1, 0, fo) ** 1.5
    out = np.stack([(a + rum) * mod * e, (b + rum) * mod * e], 1)
    return norm(out, db(-24))

def fx_whoosh(up=True, dur=0.9, **_):
    n = int(dur * SR)
    x = noise(n, "pink")
    y = sweep_bp(x, 250 if up else 2600, 2600 if up else 220, q=1.6)
    t = np.linspace(0, 1, n)
    e = np.sin(np.pi * t ** (0.6 if up else 0.35)) ** 2
    y *= e
    pan = np.linspace(-0.5, 0.5, n) if up else np.linspace(0.4, -0.4, n)
    return norm(np.stack([y * np.sqrt(0.5 * (1 - pan)), y * np.sqrt(0.5 * (1 + pan))], 1), db(-10))

def tone(f, dur, decay, n_h=1):
    n = int(dur * SR); t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * k * t) / k ** 1.5 for k in range(1, n_h + 1))
    return s * expdecay(n, decay)

def fx_lock(**_):
    a = tone(1320, 0.09, 0.03) * env_adsr(int(0.09 * SR), 0.004)
    b = tone(1760, 0.14, 0.05) * env_adsr(int(0.14 * SR), 0.004)
    gap = np.zeros(int(0.07 * SR))
    m = np.concatenate([a, gap, b])
    return stereo(norm(m, db(-24)))

def fx_tick(**_):
    n = int(0.25 * SR)
    th = tone(70, 0.25, 0.06) * 0.9 + hp(noise(n), 2500) * expdecay(n, 0.004) * 0.25
    return stereo(norm(th, db(-17)), pan=rng.uniform(-0.2, 0.2))

def fx_sweep(**_):
    n = int(1.0 * SR); t = np.linspace(0, 1, n)
    y = sweep_bp(noise(n, "pink"), 600, 3500, q=3) * np.sin(np.pi * t) ** 2
    return stereo(norm(y, db(-26)), width=0.6)

def fx_dive(**_):
    n = int(0.8 * SR); t = np.arange(n) / SR
    f = 90 * np.exp(-t * 1.6) + 30
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * np.clip(t / 0.8, 0, 1)) ** 1.5
    wh = sweep_bp(noise(n, "pink"), 3000, 300, q=1.4) * np.sin(np.pi * t / 0.8) ** 2
    return stereo(norm(sub * 0.9 + wh * 0.5, db(-12)), width=0.5)

def fx_scan(**_):
    n = int(1.4 * SR); t = np.arange(n) / SR
    f = 180 + 260 * (t / 1.4) ** 1.5
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.4 + bp(noise(n), 2000, 6000) * 0.08
    s *= np.sin(np.pi * t / 1.4) ** 2
    return stereo(norm(s, db(-30)), width=0.4)

def fx_jet_bed(dur, fade_in=0.4, fade_out=0.8, **_):
    n = int(dur * SR); t = np.arange(n) / SR
    m = lp(noise(n, "brown"), 380) * 1.0 + bp(noise(n, "pink"), 900, 2600) * 0.12 + 0.05 * np.sin(2 * np.pi * 118 * t)
    e = np.ones(n); fi, fo = int(fade_in * SR), int(fade_out * SR)
    e[:fi] = np.linspace(0, 1, fi); e[-fo:] *= np.linspace(1, 0, fo)
    return stereo(norm(m * e, db(-20)), pan=-0.2, width=0.8)

def fx_clunk(**_):
    n = int(0.45 * SR)
    m = tone(140, 0.45, 0.07) + tone(910, 0.45, 0.02) * 0.4 + tone(1530, 0.45, 0.012) * 0.25
    m += hp(noise(n), 1500) * expdecay(n, 0.006) * 0.6
    return stereo(norm(m, db(-10)), pan=-0.1)

def fx_booster(dur=1.75, **_):
    n = int((dur + 1.4) * SR); t = np.arange(n) / SR
    roar = lp(noise(n, "pink"), 1700, 3) * 1.0 + lp(noise(n, "brown"), 120) * 1.4
    crack = np.zeros(n)
    idx = rng.choice(n, 900, replace=False); crack[idx] = rng.standard_normal(900)
    roar += hp(crack, 1800) * 0.6
    e = np.clip(t / 0.06, 0, 1) ** 0.5 * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.35))
    ign = tone(55, 1.0, 0.25)
    ign = np.concatenate([ign, np.zeros(n - len(ign))])
    return stereo(norm(roar * e + ign * 1.2, db(-6)), width=1.0)

def fx_sep(**_):
    n = int(0.6 * SR)
    m = hp(noise(n), 900) * expdecay(n, 0.01) + tone(95, 0.6, 0.09) * 0.8 + tone(640, 0.6, 0.03) * 0.25
    return stereo(norm(m, db(-13)), pan=-0.25)

def fx_shutter(**_):
    n = int(0.06 * SR)
    a = hp(noise(n), 2500) * expdecay(n, 0.0025)
    b = np.zeros(int(0.018 * SR))
    m = np.concatenate([a, b, a * 0.7])
    return stereo(norm(m, db(-24)), pan=rng.uniform(-0.15, 0.15))

def fx_bolts(**_):
    out = np.zeros(int(0.5 * SR))
    for i in range(3):
        n = int(0.25 * SR)
        c = hp(noise(n), 1200) * expdecay(n, 0.004) + tone(210, 0.25, 0.03) * 0.5
        s = int(i * 0.03 * SR); out[s:s + n] += c * (1 - 0.15 * i)
    return stereo(norm(out, db(-11)), pan=0.1)

def fx_chute(**_):
    n = int(1.4 * SR); t = np.arange(n) / SR
    snap = bp(noise(n), 180, 2200) * expdecay(n, 0.05)
    flutter = bp(noise(n, "pink"), 120, 900) * (0.5 + 0.5 * np.sin(2 * np.pi * 22 * t)) * expdecay(n, 0.35) * 0.6
    return stereo(norm(snap + flutter, db(-12)), width=0.6)

def fx_boom(**_):
    n = int(3.2 * SR); t = np.arange(n) / SR
    body = lp(noise(n, "brown"), 260) * expdecay(n, 0.7)
    sub = np.sin(2 * np.pi * np.cumsum(55 * np.exp(-t * 0.8) + 28) / SR) * expdecay(n, 0.6)
    crack = hp(noise(n), 900) * expdecay(n, 0.05) * 0.35
    deb = np.zeros(n); idx = rng.choice(np.arange(int(0.3 * SR), int(2.2 * SR)), 140, replace=False)
    deb[idx] = rng.standard_normal(140); deb = bp(deb, 1500, 6000) * 0.3
    pre = np.zeros(int(0.12 * SR))     # distance delay
    m = body * 1.2 + sub * 1.1 + crack + deb
    return stereo(norm(np.concatenate([pre, m]), db(-5)), pan=0.3, width=1.0)

def fx_prop(dur=5.0, **_):
    n = int(dur * SR); t = np.arange(n) / SR
    bpf = 68 * (1 + 0.04 * (0.5 - t / dur))       # slight doppler fall
    ph = 2 * np.pi * np.cumsum(bpf) / SR
    harm = sum(np.sin(k * ph) / k for k in range(1, 9))
    whine = np.sin(2 * np.pi * np.cumsum(1850 * (1 + 0.03 * (0.5 - t / dur))) / SR) * 0.05
    m = harm * 0.5 + lp(noise(n, "brown"), 300) * 0.9 + whine
    e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.6
    pan = np.linspace(-0.7, 0.7, n)
    m = m * e
    return norm(np.stack([m * np.sqrt(0.5 * (1 - pan)), m * np.sqrt(0.5 * (1 + pan))], 1), db(-14))

def fx_snag(**_):
    n = int(0.7 * SR); t = np.arange(n) / SR
    th = tone(80, 0.7, 0.12) + hp(noise(n), 700) * expdecay(n, 0.012) * 0.7
    zip_ = sweep_bp(noise(n), 400, 3000, q=3) * expdecay(n, 0.2) * 0.6
    return stereo(norm(th + zip_, db(-10)), pan=0.05)

def fx_room(dur, fade_in=0.5, fade_out=0.5, **_):
    n = int(dur * SR)
    m = lp(noise(n, "brown"), 250) + lp(noise(n, "pink"), 2000) * 0.08
    e = np.ones(n); fi, fo = int(fade_in * SR), int(fade_out * SR)
    e[:fi] = np.linspace(0, 1, fi); e[-fo:] *= np.linspace(1, 0, fo)
    return stereo(norm(m * e, db(-34)), width=1.0)

def fx_stamp(**_):
    n = int(0.35 * SR)
    m = tone(92, 0.35, 0.06) + bp(noise(n), 300, 2500) * expdecay(n, 0.01) * 0.5
    return stereo(norm(m, db(-15)))

def fx_sub(**_):
    n = int(1.8 * SR); t = np.arange(n) / SR
    m = np.sin(2 * np.pi * np.cumsum(48 * np.exp(-t * 0.5) + 22) / SR) * np.clip(t / 0.02, 0, 1) * expdecay(n, 0.6)
    return stereo(norm(m, db(-8)))

def fx_lamp(**_):
    n = int(1.6 * SR); t = np.arange(n) / SR
    clunk = tone(120, 1.6, 0.08) + hp(noise(n), 1800) * expdecay(n, 0.006) * 0.8 + tone(780, 1.6, 0.02) * 0.3
    hum = (np.sin(2 * np.pi * 100 * t) * 0.03 + bp(noise(n), 4000, 9000) * 0.01) * np.clip((t - 0.05) / 0.3, 0, 1) * np.exp(-t / 1.2)
    return stereo(norm(clunk + hum * 6, db(-12)))

TRIM = {"lock": 2.2, "tick": 1.4, "shutter": 3.0, "sweep": 2.5, "scan": 2.2, "sep": 1.4, "stamp": 1.2}

FX = {"air_bed": fx_air_bed, "whoosh_up": lambda **k: fx_whoosh(True, 1.1), "whoosh_by": lambda **k: fx_whoosh(False, 0.9),
      "lock": fx_lock, "tick": fx_tick, "sweep": fx_sweep, "dive": fx_dive, "scan": fx_scan, "jet_bed": fx_jet_bed,
      "clunk": fx_clunk, "booster": fx_booster, "sep": fx_sep, "shutter": fx_shutter, "bolts": fx_bolts, "chute": fx_chute,
      "boom": fx_boom, "prop": fx_prop, "snag": fx_snag, "room": fx_room, "stamp": fx_stamp, "sub": fx_sub, "lamp": fx_lamp}

# ------------------------------------------------------------------ keystrokes
def load_keys():
    meta = json.load(open(os.path.join(KEYS, "keys.json")))
    normal, heavy = [], []
    for m in meta:
        a, sr = sf.read(os.path.join(KEYS, m["file"]), always_2d=True)
        assert sr == SR
        pk = np.abs(a).max()
        if pk < db(-12):          # weak / unusable take
            continue
        head = a[: int(0.03 * SR)]
        rms = np.sqrt((head ** 2).mean()) + 1e-9
        a = a / rms * db(-26)     # loudness-match on the transient
        nf = int(0.012 * SR); a[-nf:] *= np.linspace(1, 0, nf)[:, None]
        a[:48] *= np.linspace(0, 1, 48)[:, None]
        (heavy if m.get("role") == "heavy" else normal).append(a)
    return normal, heavy

def resample(a, ratio):
    n = int(len(a) / ratio)
    return signal.resample(a, n, axis=0) if n > 8 else a

def place(buf, x, t):
    s = int(round(t * SR))
    if s < 0: x = x[-s:]; s = 0
    e = min(s + len(x), len(buf))
    if e > s: buf[s:e] += x[: e - s]

def build(key_cues, sfx_cues, dur, out_path):
    buf = np.zeros((int(dur * SR) + SR, 2))
    normal, heavy = load_keys()
    rk = random.Random(42)
    last = -1
    for t, kind, vel in sorted(key_cues):
        pool = heavy if (kind == "space" and heavy) else normal
        i = rk.randrange(len(pool))
        if pool is normal and i == last: i = (i + 1) % len(pool)
        if pool is normal: last = i
        a = pool[i]
        a = resample(a, rk.uniform(0.96, 1.04))
        g = db(rk.uniform(-2.0, 1.0)) * (0.35 + 0.65 * vel) * (1.15 if kind == "space" else 1.0)
        pan = rk.uniform(-0.12, 0.12)
        a = a * g * np.array([np.sqrt(0.5 * (1 - pan)), np.sqrt(0.5 * (1 + pan))]) * np.sqrt(2)
        place(buf, a, t + rk.uniform(-0.003, 0.003))
    keys_only = buf.copy()
    for t, name, gain, kw in sfx_cues:
        x = FX[name](**kw)
        place(buf, x * gain * TRIM.get(name, 1.0), t)
    place(buf, fx_room(dur, fade_in=0.05, fade_out=0.3) * db(-14), 0.0)   # never true digital silence
    buf = buf[: int(dur * SR)]
    # gentle bus glue: soft clip only at the very top
    buf = np.tanh(buf * 1.2) / 1.2
    buf = buf / (np.abs(buf).max() + 1e-9) * db(-1.5)
    sf.write(out_path, buf.astype(np.float32), SR, subtype="FLOAT")
    return buf

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import film
    from kit import KEY_CUES
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "mix.wav")
    b = build(KEY_CUES, film.SFX, film.DUR, out)
    print("keys", len(KEY_CUES), "sfx", len(film.SFX), "dur", len(b) / SR)
