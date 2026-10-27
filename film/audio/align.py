"""Assemble the narration track and compute word-level timings (faster-whisper) mapped onto script words.

Outputs build/vo_track.wav (48 kHz mono) and build/timeline.json used by the renderer and the SFX cue builder.
"""
import json, os, re, difflib
import numpy as np, soundfile as sf, scipy.signal as ss
from faster_whisper import WhisperModel

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = json.load(open(f'{root}/script/narration.json'))
man = json.load(open(f'{root}/build/vo/manifest.json'))
PRE, TAIL, SR = cfg.get('preroll', 0.8), cfg.get('tail', 1.9), 48000
model = WhisperModel('small.en', device='cpu', compute_type='int8')

def norm(w):
    w = w.lower().replace('’', "'")
    return re.sub(r"[^a-z0-9']", '', w)

clips, beats, t = [], [], PRE
for b in man:
    a, sr = sf.read(b['file'])
    idx = np.where(np.abs(a) > 0.008)[0]
    s0, s1 = max(0, idx[0] - int(0.012 * sr)), min(len(a), idx[-1] + int(0.06 * sr))
    a = a[s0:s1]
    fade = int(0.006 * sr); a[:fade] *= np.linspace(0, 1, fade); a[-fade:] *= np.linspace(1, 0, fade)
    a48 = ss.resample_poly(a, 2, 1)  # 24k -> 48k
    a16 = ss.resample_poly(a, 2, 3).astype(np.float32)
    segs, _ = model.transcribe(a16, language='en', word_timestamps=True)
    ww = [w for s in segs for w in s.words]
    script_words = b['text'].split()
    sn = [norm(w) for w in script_words]; wn = [norm(w.word) for w in ww]
    times = [None] * len(script_words)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, sn, wn, autojunk=False).get_opcodes():
        if tag == 'equal' or (tag == 'replace' and i2 - i1 == j2 - j1):
            for k in range(i2 - i1): times[i1 + k] = (ww[j1 + k].start, ww[j1 + k].end)
    # interpolate unmatched words between known neighbours, weighted by length
    dur = len(a) / sr
    known = [(i, tm) for i, tm in enumerate(times) if tm]
    for i in range(len(times)):
        if times[i] is None:
            prev = max([k for k in known if k[0] < i], default=(None, (0.0, 0.0)), key=lambda k: k[0])
            nxt = min([k for k in known if k[0] > i], default=(None, (dur, dur)), key=lambda k: k[0])
            lo, hi = prev[1][1], nxt[1][0]
            gi = [j for j in range((prev[0] if prev[0] is not None else -1) + 1, nxt[0] if nxt[0] is not None else len(times))]
            L = sum(len(script_words[j]) for j in gi) or 1
            acc = sum(len(script_words[j]) for j in gi if j < i)
            times[i] = (lo + (hi - lo) * acc / L, lo + (hi - lo) * (acc + len(script_words[i])) / L)
    words = [{'w': w, 'start': round(t + tm[0], 3), 'end': round(t + tm[1], 3)} for w, tm in zip(script_words, times)]
    beats.append({'id': b['id'], 'scene': b['scene'], 'text': b['text'], 'start': round(t, 3), 'end': round(t + dur, 3), 'words': words})
    clips.append((t, a48))
    print(b['id'], f'{t:6.2f}-{t + dur:6.2f}', ' '.join(f"{x['w']}@{x['start']:.2f}" for x in words[:6]), '...')
    t += dur + b['gap']
total = t + TAIL
track = np.zeros(int(total * SR) + 1, np.float32)
for st, a48 in clips:
    i = int(round(st * SR)); track[i:i + len(a48)] += a48.astype(np.float32)
os.makedirs(f'{root}/build', exist_ok=True)
sf.write(f'{root}/build/vo_track.wav', track, SR, subtype='FLOAT')
json.dump({'fps': 30, 'width': 1080, 'height': 1920, 'duration': round(total, 3), 'preroll': PRE, 'beats': beats},
          open(f'{root}/build/timeline.json', 'w'), indent=1)
print('duration', round(total, 3))
