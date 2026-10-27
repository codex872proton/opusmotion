"""Slice the user's 'Deep Thock' keyboard recording into clean one-shot keystroke samples."""
import os, json, numpy as np, soundfile as sf
from scipy import signal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "keyboard_src.wav")
OUT = os.path.join(ROOT, "assets", "sfx", "keys")

def main():
    x, sr = sf.read(SRC)
    x = x[int(1.0 * sr):]                       # typing starts at ~1.0 s
    m = x.mean(1)
    sos = signal.butter(4, [900, 9000], "bandpass", fs=sr, output="sos")
    hf = signal.sosfiltfilt(sos, m)
    w = int(0.002 * sr)
    env = np.sqrt(np.convolve(hf ** 2, np.ones(w) / w, "same"))
    flux = np.maximum(np.diff(env, prepend=env[0]), 0)
    flux = np.convolve(flux, np.ones(w) / w, "same")
    peaks, props = signal.find_peaks(flux, distance=int(0.045 * sr), prominence=flux.max() * 0.04)
    # refine onset: walk back to where envelope rises above 10% of local peak
    onsets = []
    for p in peaks:
        loc = env[p:p + int(0.01 * sr)].max()
        q = p
        while q > 0 and env[q] > 0.12 * loc and p - q < int(0.006 * sr):
            q -= 1
        onsets.append(q)
    onsets = np.array(sorted(set(onsets)))
    hp = signal.butter(2, 38, "highpass", fs=sr, output="sos")
    xs = signal.sosfiltfilt(hp, x, axis=0)
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    meta, k = [], 0
    for i, o in enumerate(onsets):
        nxt = onsets[i + 1] if i + 1 < len(onsets) else len(m)
        L = min(nxt - o - int(0.003 * sr), int(0.17 * sr))
        if L < int(0.06 * sr):
            continue
        a = max(o - int(0.0015 * sr), 0)
        seg = xs[a:o + L].copy()
        pre = np.abs(xs[max(a - int(0.01 * sr), 0):a]).max() if a > 0 else 0
        pk = np.abs(seg).max()
        if pk < 0.05 or pre / pk > 0.35:        # weak hits or heavy bleed from previous stroke
            continue
        n = len(seg); fo = min(int(0.04 * sr), n // 2)
        fade = np.ones(n); fade[-fo:] = np.cos(np.linspace(0, np.pi / 2, fo)) ** 2
        fade[:int(0.0015 * sr)] = np.linspace(0, 1, int(0.0015 * sr))
        seg *= fade[:, None]
        mono = seg.mean(1)
        spec = np.abs(np.fft.rfft(mono, 8192)); fr = np.fft.rfftfreq(8192, 1 / sr)
        cen = float((spec * fr).sum() / spec.sum())
        low = float((spec[(fr > 60) & (fr < 400)] ** 2).sum() / (spec ** 2).sum())
        rms = float(np.sqrt((mono ** 2).mean()))
        seg = seg / pk * 0.89
        name = f"key_{k:02d}.wav"
        sf.write(os.path.join(OUT, name), seg.astype(np.float32), sr, subtype="FLOAT")
        meta.append(dict(file=name, t=round((o / sr) + 1.0, 3), dur=round(n / sr, 3), centroid=round(cen), low=round(low, 3),
                         bleed=round(float(pre / pk), 3), rms=round(rms, 4)))
        k += 1
    # heaviest / deepest strokes act as 'space' and 'enter' variants
    order = sorted(meta, key=lambda d: -d["low"])
    for d in order[: max(3, len(order) // 5)]:
        d["role"] = "heavy"
    json.dump(meta, open(os.path.join(OUT, "keys.json"), "w"), indent=1)
    print(len(onsets), "onsets ->", len(meta), "clean samples")
    for d in meta:
        print(d)

if __name__ == "__main__":
    main()
