"""Render every SFX type (2-4 variations each) + objective measurements.

Usage: /tmp/tts/bin/python audition.py [OUTROOT]   (default film/build/sfx)

Writes OUTROOT/audition/<type>_<n>.wav, OUTROOT/audition/audition.wav (all
concatenated), OUTROOT/audition/spec_<type>.png and OUTROOT/report.md.
"""
import os
import subprocess
import sys
import time

import numpy as np
import soundfile as sf
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dsp  # noqa: E402
import generators as G  # noqa: E402

SR = dsp.SR
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, "build", "sfx")
AUD = os.path.join(OUT, "audition")
BANDS = [("sub", 0, 80), ("low", 80, 300), ("lowmid", 300, 1000), ("mid", 1000, 3000),
         ("high", 3000, 8000), ("air", 8000, 24000)]

FLYBY = dict(dur=9.0, rpm=[[0, 2050], [9, 2000]], dist=[[0, 1600], [4.5, 70], [9, 1600]],
             pan=[[0, -0.8], [4.5, 0.0], [9, 0.8]])
VARIATIONS = {
    "thock": [dict(variant="alpha", vel=0.75), dict(variant="alpha", vel=0.45), dict(variant="alpha", vel=1.0),
              dict(variant="space", vel=0.8), dict(variant="enter", vel=0.85), dict(variant="backspace", vel=0.7)],
    "pop": [dict(weight="light"), dict(weight="light", pitch=3), dict(weight="bold"), dict(weight="bold", pitch=-2)],
    "whoosh": [dict(dur=1.0, motion="pass"), dict(dur=0.7, motion="in", intensity=0.8),
               dict(dur=1.4, motion="out", brightness=0.3), dict(dur=1.8, motion="pass", intensity=1.0, brightness=0.8)],
    "boom": [dict(), dict(intensity=1.0, dur=3.5, pitch_hz=42), dict(intensity=0.5, dur=1.5, pitch_hz=55)],
    "stamp": [dict(intensity=0.9), dict(intensity=0.6), dict(intensity=1.0)],
    "paper": [dict(kind="slide"), dict(kind="flip"), dict(kind="rustle"), dict(kind="slide", dur=1.4)],
    "radio_static": [dict(dur=6.0, crackle=0.4), dict(dur=4.0, crackle=0.9)],
    "morse": [dict(pattern="-.-. .. .-"), dict(pattern="... --- ...", wpm=14, freq=600),
              dict(pattern=".-- .- .. -", wpm=22, freq=700)],
    "tune": [dict(dur=1.2), dict(dur=1.8)],
    "engine": [FLYBY, dict(dur=4.0, rpm=2100, dist=60, pan=0.0),
               dict(dur=6.0, rpm=[[0, 2050]], dist=[[0, 120], [6, 160]], pan=[[0, 0.2]], sputter_at=2.5)],
    "wind": [dict(dur=8.0, gust=0.5), dict(dur=6.0, gust=0.9)],
    "cloth_whip": [dict(dur=0.9), dict(dur=1.2)],
    "aa_gun": [dict(shots=4, interval=0.32, dist=150), dict(shots=6, interval=0.33, dist=60),
               dict(shots=3, interval=0.35, dist=400)],
    "tracer_whiz": [dict(dur=0.5), dict(dur=0.35, pan_from=0.7, pan_to=-0.5), dict(dur=0.8, pan_from=-0.2, pan_to=0.9)],
    "metal_impact": [dict(count=5, spread=0.6), dict(count=3, spread=0.25), dict(count=8, spread=1.0)],
    "crash": [dict(dur=3.0), dict(dur=4.0)],
    "fire": [dict(dur=6.0), dict(dur=4.0)],
    "counter_tick": [dict(), dict(), dict()],
    "ink_bleed": [dict(dur=1.5), dict(dur=2.5)],
    "riser": [dict(dur=2.0, intensity=0.7), dict(dur=3.5, intensity=1.0), dict(dur=1.2, intensity=0.4)],
    "sub_drop": [dict(dur=1.2), dict(dur=2.0)],
    "rope_snap": [dict(intensity=0.8), dict(intensity=1.0), dict(intensity=0.5)],
    "winch": [dict(dur=2.5), dict(dur=4.0)],
    "footsteps": [dict(count=4, interval=0.65, surface="bridge"), dict(count=4, interval=0.6, surface="stone")],
    "room_tone": [dict(dur=6.0, kind="office"), dict(dur=12.0, kind="cell")],
    "gavel": [dict(intensity=0.8), dict(intensity=1.0), dict(intensity=0.5)],
    "flash_hit": [dict(intensity=1.0), dict(intensity=0.7)],
}
BEDS = {"radio_static", "wind", "fire", "room_tone", "engine"}


def measure(y):
    """Objective metrics on the mono sum. Centroid is magnitude-weighted over
    the whole file; band shares are power fractions; attack = 10%->90% of the
    0.5 ms-smoothed Hilbert envelope; active length = span above -40 dB of
    the 5 ms RMS envelope maximum."""
    m = dsp.mono(y).astype(float)
    pk = np.max(np.abs(y))
    w5 = max(1, int(0.005 * SR))
    env5 = np.sqrt(np.convolve(m ** 2, np.ones(w5) / w5, mode="same"))
    act = np.nonzero(env5 > env5.max() * 10 ** (-40 / 20))[0]
    a0, a1 = (act[0], act[-1]) if len(act) else (0, len(m) - 1)
    seg = y[a0:a1 + 1]
    rms = np.sqrt(np.mean(seg ** 2))
    X = np.abs(np.fft.rfft(m))
    f = np.fft.rfftfreq(len(m), 1 / SR)
    cent = float(np.sum(f * X) / max(np.sum(X), 1e-12))
    P = X ** 2
    tot = max(P.sum(), 1e-30)
    bands = {b: 100.0 * P[(f >= lo) & (f < hi)].sum() / tot for b, lo, hi in BANDS}
    he = np.abs(signal.hilbert(m))
    w = max(1, int(0.0005 * SR))
    he = np.convolve(he, np.ones(w) / w, mode="same")
    ip = int(np.argmax(he))
    i10 = int(np.argmax(he[: ip + 1] >= 0.1 * he[ip]))
    i90 = int(np.argmax(he[: ip + 1] >= 0.9 * he[ip]))
    on = m[a0:a0 + int(0.005 * SR)]
    if len(on) > 32:
        Po = np.abs(np.fft.rfft(on * np.hanning(len(on)))) ** 2
        fo = np.fft.rfftfreq(len(on), 1 / SR)
        onset_hf = 100.0 * Po[fo > 5000].sum() / max(Po.sum(), 1e-30)
    else:
        onset_hf = 0.0
    return dict(len=len(m) / SR, active=(a1 - a0) / SR, peak=20 * np.log10(pk + 1e-12),
                rms=20 * np.log10(rms + 1e-12), cent=cent, attack_ms=1000.0 * (i90 - i10) / SR,
                onset_hf=onset_hf, dc=float(np.max(np.abs(y.mean(axis=0)))), **bands)


def fmt_row(label, mm):
    return (f"| {label} | {mm['len']:.3f} | {mm['active']:.3f} | {mm['peak']:.1f} | {mm['rms']:.1f} | "
            f"{mm['cent']:.0f} | " + " | ".join(f"{mm[b]:.1f}" for b, _, _ in BANDS) +
            f" | {mm['attack_ms']:.2f} | {mm['onset_hf']:.1f} |")


HDR = ("| var | len s | active s | peak dBFS | RMS dBFS | centroid Hz | sub% | low% | lowmid% | mid% | "
       "high% | air% | attack ms | onsetHF% |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")


def spectro(wav, png):
    for fs in ("fscale=log:", ""):
        cmd = ["/usr/bin/ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-lavfi",
               f"showspectrumpic=s=800x300:legend=1:scale=log:{fs}stop=12000", png]
        if subprocess.run(cmd).returncode == 0:
            return
    subprocess.run(["/usr/bin/ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-lavfi",
                    "showspectrumpic=s=800x300:legend=1:scale=log", png])


def stats(fn, params_list, seeds):
    rows = [measure(fn(np.random.default_rng(s), **p)) for p in params_list for s in seeds]
    keys = ["active", "peak", "cent", "high", "air", "attack_ms", "onset_hf", "sub", "low", "lowmid", "mid"]
    return {k: (np.mean([r[k] for r in rows]), np.min([r[k] for r in rows]), np.max([r[k] for r in rows]))
            for k in keys}


def typing_demo(seed=7):
    """24 keystrokes with human timing (incl. spaces/enter/backspace)."""
    rng = np.random.default_rng(seed)
    text = "manchuria 1952 / tr-c47  pickup\n"
    out = np.zeros((int(SR * 6.5), 2))
    t = 0.15
    for i, ch in enumerate(text):
        var = "space" if ch == " " else "enter" if ch == "\n" else "backspace" if ch == "/" else "alpha"
        y = G.gen_thock(np.random.default_rng(1000 + i), variant=var, vel=float(np.clip(rng.normal(0.72, 0.12), 0.3, 1)))
        s = int(t * SR) - G.THOCK_PREROLL
        dsp.place(out, max(s, 0), y)
        t += float(np.clip(rng.lognormal(np.log(0.14), 0.35), 0.06, 0.45)) + (0.12 if ch == " " else 0.0)
    wet = dsp.reverb(out, "room", tail=False)
    return out[: int(SR * (t + 0.4))] + 0.12 * wet[: int(SR * (t + 0.4))]


def main():
    os.makedirs(AUD, exist_ok=True)
    gap = np.zeros((int(0.35 * SR), 2), dtype=np.float32)
    allcat, lines = [], []
    t_all = time.time()
    lines.append("# SFX audition report\n")
    lines.append("All measurements on the mono sum at 48 kHz. *centroid* = magnitude-weighted spectral centroid "
                 "of the whole file; band columns = % of power; *active* = span above -40 dB of the 5 ms RMS "
                 "envelope peak; *attack* = 10%->90% rise of the 0.5 ms-smoothed Hilbert envelope; *onsetHF* = % "
                 "of energy above 5 kHz in the first 5 ms of the active span (click indicator).\n")
    for typ in sorted(VARIATIONS):
        fn = G.GENERATORS[typ]
        cat = []
        lines.append(f"\n## {typ}\n\n{HDR}")
        t0 = time.time()
        for k, p in enumerate(VARIATIONS[typ]):
            y = fn(np.random.default_rng(100 + 17 * k), **p)
            sf.write(os.path.join(AUD, f"{typ}_{k + 1}.wav"), y, SR, subtype="FLOAT")
            mm = measure(y)
            label = ", ".join(f"{a}={b}" for a, b in p.items() if a not in ("rpm", "dist", "pan")) or "default"
            lines.append(fmt_row(f"{k + 1}: {label}", mm))
            cat += [y, gap]
        dt = time.time() - t0
        c = np.concatenate(cat)
        wav = os.path.join(AUD, f"_cat_{typ}.wav")
        sf.write(wav, c, SR, subtype="FLOAT")
        spectro(wav, os.path.join(AUD, f"spec_{typ}.png"))
        os.remove(wav)
        allcat.append(c)
        lines.append(f"\nrender time for {len(VARIATIONS[typ])} variations: {dt * 1000:.0f} ms")
        print(f"{typ:14s} {dt * 1000:7.0f} ms", flush=True)

    # Robust statistics for the two sounds heard hundreds of times.
    lines.append("\n## Seed statistics (mean [min..max] over 40 seeds each)\n")
    lines.append("| sound | active s | peak dBFS | centroid Hz | high% | air% | attack ms | onsetHF% | sub% | low% | "
                 "lowmid% | mid% |\n|---|---|---|---|---|---|---|---|---|---|---|---|")
    seeds = range(40)
    for label, typ, p in [("thock alpha v0.75", "thock", dict(variant="alpha", vel=0.75)),
                          ("thock alpha v1.0", "thock", dict(variant="alpha", vel=1.0)),
                          ("thock enter", "thock", dict(variant="enter", vel=0.8)),
                          ("thock backspace", "thock", dict(variant="backspace", vel=0.8)),
                          ("thock space", "thock", dict(variant="space", vel=0.8)),
                          ("pop light", "pop", dict(weight="light")),
                          ("pop bold", "pop", dict(weight="bold")),
                          ("counter_tick", "counter_tick", dict())]:
        s = stats(G.GENERATORS[typ], [p], seeds)
        cell = lambda k, f="{:.0f}": f"{f.format(s[k][0])} [{f.format(s[k][1])}..{f.format(s[k][2])}]"
        lines.append(f"| {label} | {cell('active', '{:.3f}')} | {cell('peak', '{:.1f}')} | {cell('cent')} | "
                     f"{cell('high', '{:.1f}')} | {cell('air', '{:.2f}')} | {cell('attack_ms', '{:.2f}')} | "
                     f"{cell('onset_hf', '{:.2f}')} | {cell('sub', '{:.1f}')} | {cell('low', '{:.1f}')} | "
                     f"{cell('lowmid', '{:.1f}')} | {cell('mid', '{:.1f}')} |")

    demo = typing_demo().astype(np.float32)
    sf.write(os.path.join(AUD, "typing_demo.wav"), demo, SR, subtype="FLOAT")
    spectro(os.path.join(AUD, "typing_demo.wav"), os.path.join(AUD, "spec_typing_demo.png"))
    allcat.insert(0, np.concatenate([demo, gap]))

    lines.append("\n## Reverb IRs (Schroeder T30, seconds)\n\n| IR | broadband | 125 | 250 | 500 | 1k | 2k | 4k |\n"
                 "|---|---|---|---|---|---|---|---|")
    for k in ("room", "night"):
        r = dsp.rt60_bands(dsp.make_ir(k))
        lines.append(f"| {k} | " + " | ".join(f"{r[b]:.2f}" for b in ("broadband", 125, 250, 500, 1000, 2000, 4000)) + " |")

    fh = G.gen_flash_hit(np.random.default_rng(1))
    ipk = int(np.argmax(np.abs(fh).max(axis=1)))
    lines.append(f"\nflash_hit: FLASH_HIT_PREROLL = {G.FLASH_HIT_PREROLL} samples; measured hit onset "
                 f"(first sample > -20 dB re peak after pre-roll) at "
                 f"{G.FLASH_HIT_PREROLL + int(np.argmax(np.abs(fh[G.FLASH_HIT_PREROLL:]).max(axis=1) > 0.1 * np.abs(fh).max()))}"
                 f", peak at {ipk}.")

    full = np.concatenate(allcat).astype(np.float32)
    sf.write(os.path.join(AUD, "audition.wav"), full, SR, subtype="FLOAT")
    lines.append(f"\naudition.wav: {len(full) / SR:.1f} s; total render+analysis time {time.time() - t_all:.1f} s")
    with open(os.path.join(OUT, "report.md"), "w") as fh_:
        fh_.write("\n".join(lines) + "\n")
    print("wrote", os.path.join(OUT, "report.md"), f"{time.time() - t_all:.1f}s")


if __name__ == "__main__":
    main()
