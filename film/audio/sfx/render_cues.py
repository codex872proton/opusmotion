"""Mix a JSON cue list into bus stems and 100%-wet reverb returns.

Usage: /tmp/tts/bin/python render_cues.py cues.json OUTDIR

cues.json:
  {"sr": 48000, "duration": 69.5, "cues": [
     {"t": 1.234, "type": "thock", "params": {...}, "gain_db": -8, "pan": 0.0,
      "bus": "fx", "send": {"room": 0.15, "night": 0.0}, "seed": 17,
      "lp": 9000, "hp": 40, "fade_in": 0.0, "fade_out": 0.0, "dur": 3.0,
      "anchor": "end"}, ...]}

Cue fields (all optional except t/type):
  bus       fx | amb | hits (default fx)
  send      {"room": lvl, "night": lvl}, linear post-fader send levels
  seed      default crc32(f"{index}:{type}")
  lp / hp   2nd-order Butterworth low/high-pass (Hz)
  fade_in / fade_out   raised-cosine fades at the sound's start/end (s)
  dur       passed to the generator as params["dur"] if it takes one
  anchor    which point of the sound lands on t: "start", "end", "hit"
            (generator's ANCHOR_OFFSETS entry) or a number of seconds into
            the sound. Default: "hit" for types listed in ANCHOR_OFFSETS
            (flash_hit, thock), else "start".

Writes OUTDIR/{fx,amb,hits,verb_room,verb_night}.wav (stereo float32, exactly
round(duration*sr) samples) and OUTDIR/render_log.json (per-cue placement).
Identical (type, params, seed) generator calls are rendered once and cached.
"""
import inspect
import json
import os
import sys
import time
import zlib

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dsp  # noqa: E402
import generators as G  # noqa: E402

BUSES = ("fx", "amb", "hits")
SENDS = ("room", "night")


def default_seed(i, typ):
    return zlib.crc32(f"{i}:{typ}".encode()) & 0x7FFFFFFF


def _anchor_offset(cue, typ, n, sr):
    a = cue.get("anchor")
    if a is None or a == "hit":
        return G.ANCHOR_OFFSETS.get(typ, 0)
    if a == "start":
        return 0
    if a == "end":
        return n
    return int(round(float(a) * sr))


def render(cfg, outdir, verbose=True):
    t0 = time.time()
    sr = int(cfg.get("sr", dsp.SR))
    if sr != dsp.SR:
        raise ValueError(f"generators run at {dsp.SR} Hz; cues.json asks for {sr}")
    total = int(round(float(cfg["duration"]) * sr))
    buses = {b: np.zeros((total, 2)) for b in BUSES}
    sends = {s: np.zeros((total, 2)) for s in SENDS}
    cache, log = {}, []
    n_gen = 0
    t_gen = 0.0
    for i, cue in enumerate(cfg["cues"]):
        typ = cue["type"]
        if typ not in G.GENERATORS:
            raise KeyError(f"cue {i}: unknown type {typ!r}; valid: {sorted(G.GENERATORS)}")
        fn = G.GENERATORS[typ]
        params = dict(cue.get("params") or {})
        if "dur" in cue and "dur" not in params and "dur" in inspect.signature(fn).parameters:
            params["dur"] = cue["dur"]
        seed = int(cue.get("seed", default_seed(i, typ)))
        key = (typ, json.dumps(params, sort_keys=True), seed)
        if key not in cache:
            tg = time.time()
            try:
                cache[key] = fn(np.random.default_rng(seed), **params)
            except TypeError as e:
                raise TypeError(f"cue {i} ({typ}): bad params {params}: {e}") from None
            t_gen += time.time() - tg
            n_gen += 1
        y = cache[key].astype(np.float64)
        if cue.get("hp"):
            y = dsp.hp(y, float(cue["hp"]))
        if cue.get("lp"):
            y = dsp.lp(y, float(cue["lp"]))
        if cue.get("fade_in") or cue.get("fade_out"):
            y = dsp.fade(y, float(cue.get("fade_in", 0.0)), float(cue.get("fade_out", 0.0)))
        y *= dsp.undb(float(cue.get("gain_db", 0.0)))
        if cue.get("pan"):
            y = dsp.pan_stereo(y, float(cue["pan"]))
        bus = cue.get("bus", "fx")
        if bus not in buses:
            raise KeyError(f"cue {i}: bus must be one of {BUSES}, got {bus!r}")
        start = int(round(float(cue["t"]) * sr)) - _anchor_offset(cue, typ, len(y), sr)
        dsp.place(buses[bus], start, y)
        for s, lvl in (cue.get("send") or {}).items():
            if s not in sends:
                raise KeyError(f"cue {i}: send must be one of {SENDS}, got {s!r}")
            if lvl:
                dsp.place(sends[s], start, y * float(lvl))
        log.append(dict(i=i, type=typ, bus=bus, seed=seed, start_sample=start, length=len(y),
                        start_s=round(start / sr, 4), end_s=round((start + len(y)) / sr, 4),
                        peak_db=round(float(dsp.todb(np.max(np.abs(y)))), 2)))
    t_rev = time.time()
    rets = {}
    for s in SENDS:
        rets[s] = dsp.reverb(sends[s], s, tail=False) if np.any(sends[s]) else np.zeros((total, 2))
    t_rev = time.time() - t_rev
    os.makedirs(outdir, exist_ok=True)
    out = {**buses, **{f"verb_{s}": rets[s] for s in SENDS}}
    summary = {}
    for name, sig in out.items():
        sig = np.nan_to_num(sig).astype(np.float32)
        assert sig.shape == (total, 2)
        sf.write(os.path.join(outdir, f"{name}.wav"), sig, sr, subtype="FLOAT")
        pk = float(np.max(np.abs(sig)))
        summary[name] = dict(peak_db=round(float(dsp.todb(pk)), 2),
                             rms_db=round(float(dsp.todb(np.sqrt(np.mean(sig.astype(np.float64) ** 2)))), 2))
    elapsed = time.time() - t0
    with open(os.path.join(outdir, "render_log.json"), "w") as fh:
        json.dump(dict(sr=sr, samples=total, cues=log, stems=summary, unique_renders=n_gen,
                       generator_s=round(t_gen, 3), reverb_s=round(t_rev, 3), total_s=round(elapsed, 3)), fh, indent=1)
    if verbose:
        print(f"{len(cfg['cues'])} cues ({n_gen} unique renders, {t_gen:.2f}s), reverbs {t_rev:.2f}s, "
              f"total {elapsed:.2f}s -> {outdir}")
        for name, s in summary.items():
            warn = "  <-- above 0 dBFS (float stem; trim in the mix)" if s["peak_db"] > 0 else ""
            print(f"  {name:10s} peak {s['peak_db']:7.2f} dBFS  rms {s['rms_db']:7.2f} dBFS{warn}")
    return summary


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    with open(sys.argv[1]) as fh:
        cfg = json.load(fh)
    render(cfg, sys.argv[2])


if __name__ == "__main__":
    main()
