# SENIOR BOWL — the D-21 drone flights over China (1969–71)

A 69-second vertical film (1080×1920, 60 fps, no music) rendered entirely from code.

- `src/film.py` — script, timeline, shots, frame renderer
- `src/gfx.py` — GL relief map (real DEM), parametric 3D D-21, compositing
- `src/kit.py` — HarfBuzz-shaped typed captions, easing, drawing helpers
- `src/shapes.py` — B-52H, JC-130, D-21 side views, booster, hatch, parachute
- `src/audio.py` — keystroke placement (user-recorded keys) + synthesised effects
- `docs/SOURCES.md` — sources and claim-by-claim support

Render: `tools/fetch_assets.py` (data), `tools/render_all.sh`, `python3 src/audio.py build/mix.wav`, `tools/finalize.sh`.
