"""Render narration beats with Kokoro-82M (ONNX). Writes one WAV per beat plus a manifest."""
import json, re, sys, os
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = json.load(open(f'{root}/script/narration.json'))
voice = sys.argv[1] if len(sys.argv) > 1 else cfg['voice']
speed = float(sys.argv[2]) if len(sys.argv) > 2 else cfg['speed']
outdir = sys.argv[3] if len(sys.argv) > 3 else f'{root}/build/vo'
os.makedirs(outdir, exist_ok=True)
k = Kokoro(os.environ.get('KOKORO_MODEL', '/tmp/models/kokoro-v1.0.onnx'), os.environ.get('KOKORO_VOICES', '/tmp/models/voices-v1.0.bin'))

def spoken(text):
    for a, b in cfg['pronounce'].items():
        text = re.sub(rf'\b{re.escape(a)}\b', b, text)
    return text

manifest = []
for b in cfg['beats']:
    samples, sr = k.create(spoken(b['text']), voice=voice, speed=speed, lang='en-us')
    path = f"{outdir}/{b['id']}.wav"
    sf.write(path, samples, sr)
    manifest.append({**b, 'file': path, 'sr': sr, 'dur': len(samples) / sr})
    print(b['id'], round(len(samples) / sr, 2), flush=True)
json.dump(manifest, open(f'{outdir}/manifest.json', 'w'), indent=1)
print('total speech', round(sum(m['dur'] for m in manifest), 2), 'with gaps', round(sum(m['dur'] + m['gap'] for m in manifest), 2))
