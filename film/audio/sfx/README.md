# Procedural SFX library (no samples, no music)

This library contains deep, warm, physically inspired sound effects for the 1952 Manchuria C-47 short. It uses only `numpy`, `scipy` and `soundfile`, renders at 48 kHz stereo float32, and is fully deterministic: all randomness comes from the `rng` you pass in.

```
/tmp/tts/bin/python render_cues.py cues.json OUTDIR   # stems fx/amb/hits + verb_room/verb_night
/tmp/tts/bin/python audition.py                       # film/build/sfx/{audition/,report.md}
```

## Files
- `dsp.py`: shared building blocks.
  - Envelopes: `exp_env`, `adsr`, `fade`, `curve`.
  - Filters: RBJ biquads (`biquad`, `tv_biquad` for time-varying sweeps) and Butterworth `lp`/`hp`/`bp`.
  - Noise: `pink`, `brown`, `colored_noise`.
  - Modal synthesis: `modal_ir`, `modal`, `resonator_bank`, `hann_pulse`, `half_sine`.
  - Saturation: `soft_clip`, `asym_sat`, `saturate_os` (oversampled).
  - Stereo: `pan_mono`, `pan_stereo`, `widen`, `haas`, `ms_width`.
  - Doppler: `doppler`, a cubic fractional delay line, plus `pass_by` fly-by geometry.
  - Reverb: procedural-IR convolution via `make_ir('room'|'night')` and `reverb`. `rt60_bands` verifies the IRs.
- `generators.py`: `gen_<type>(rng, **params) -> (N, 2) float32`, collected in `GENERATORS`. It also defines `ANCHOR_OFFSETS`, `FLASH_HIT_PREROLL` (7200 samples) and `THOCK_PREROLL` (384 samples).
- `render_cues.py`: the cue mixer. The full field reference is in its docstring.
- `audition.py`: renders every type, produces spectrograms and writes the metrics, targets-check and iteration-log report.
- `example_cues.json`: 30 cues over 8 s.

## Levels and anchors
- **One-shots** are peak-normalised to -1 dBFS.
- **`thock` levels** are not re-normalised, so velocity and per-key variation survive. The peak is base (-1.0 to -1.5 dBFS) minus 10·(1-vel) dB, ±2 dB per key.
- **Beds** are RMS-normalised: wind -26, radio_static -24, fire -24 and room_tone -32 dBFS.
- **Engine** is peak-normalised over the whole cue, so distance changes within one cue are preserved; set the absolute level with `gain_db`.
- **Anchors:** by default the renderer puts the generator's *hit* sample on cue `t`. The hit is the bottom-out for `thock` and the white-flash impact for `flash_hit`. For any other type, use `"anchor":"end"` (for example on `riser`) or `"anchor": <seconds into the sound>`.
- **Reverb returns** are 100 % wet. Each IR is calibrated to 0 dB power gain over 400 Hz–1.2 kHz, so a send of 0.25 means the wet signal sits about 12 dB below the dry in the mids for sustained sounds; transients read quieter.
  - `room` is a wooden office: RT60 0.35 s.
  - `night` is a snowy forest: RT60 2.8 s, 40 ms pre-delay, heavy HF damping and smeared tree-line echoes.

## Types and parameters
| type | params | design notes |
|---|---|---|
| thock | variant alpha/space/enter/backspace, vel 0..1 | Three modal groups, each driven by its own smooth Hann contact pulse: body about 200/300 Hz, plate/cap 455–980 Hz, keycap 1.4–2.5 kHz at -10 dB. Adds a desk mode, a creamy 4th-order-LP noise layer, a foam layer and a lubed slider swish. Up-stroke 70–110 ms later at -14 dB. space has a 120–240 Hz body plus stabiliser flams and wire swish. A double-bonk rejection rule redraws any key whose modes beat. |
| pop | weight light/bold, pitch (semitones) | Wooden puck: a sine gliding 420→210 Hz with x2.42 and x3.9 wood partials, plus air puff and felt contact noise. bold adds a 90→55 Hz felt sub. 1.5 ms raised-cosine onset. |
| whoosh | dur, intensity, motion in/out/pass, brightness | Pink/brown noise through a 4-pole LP sweep plus a band-pass focus, loudness-compensated. Adds a brown body, fly-by doppler and a pan sweep. |
| boom | intensity, dur, pitch_hz | Sine sweeping 2·pitch→pitch, oversampled asymmetric saturation (100–250 Hz harmonics), LP punch and a dark decorrelated tail. |
| stamp | intensity | Rubber contact into desk modes 92–257 Hz and top modes, then paper slap, granular crunch and desk-object rattles. |
| paper | kind slide/flip/rustle, dur | Granular crinkle (Poisson micro-bursts into band-pass resonators) plus friction noise and a paper-body layer, LP 6.5 kHz. |
| radio_static | dur, crackle | 300–3500 Hz hiss, slow drift, QRN crackles and a faint 1.85 kHz heterodyne. |
| morse | pattern, wpm, freq | Hand-keyed timing, 5 ms raised-cosine keying, transmitter chirp, QSB fading, receiver BPF, and static ducked by the AGC. Pattern: `.` `-`, space = letter gap, `/` or double space = word gap. |
| tune | dur, land_freq | Heterodyne glide 2.9 kHz→land_freq with a hand-tuning overshoot and a second passing beat. Static swells, then the AGC quiets onto the carrier. |
| engine | dur, rpm, dist, pan (scalars or [[t,v],...]), sputter_at | Two R-1830s: jittered pulse-train exhaust at rpm/60·7 through formants, rasp, 18 blade-pass harmonics at rpm·0.5625/60·3 and prop wash. Engine 2 is 0.4–0.8 % fast, so the two beat. Distance gives 1/r level and air-absorption LP. Doppler is a zero-latency frequency warp, keeping picture sync. Sputter: misfires, backfires, rpm sag, then a 1 s fade. |
| wind | dur, gust | Brown+pink noise; gust LFOs drive level and an LP of 260 Hz–2.5 kHz. Adds a faint wandering whistle and pine hiss on gusts. |
| cloth_whip | dur | Whump, canvas crack, and flaps slowing 22→10 Hz while darkening and drifting off to one side. |
| aa_gun | shots, interval, dist | Per shot: chest thump 110→48 Hz, body, boom and a distance-dependent crack. Adds smeared tree-line echoes and an in-band-calibrated rumble tail. |
| tracer_whiz | dur, pan_from, pan_to | Softened N-wave snap, then a 3.2 kHz→700 Hz doppler whiz. |
| metal_impact | count, spread | 28 uniform-density plate modes (400 Hz–4 kHz, 15–32 ms decays), a panel thunk, a penetration tear and debris ticks. |
| crash | dur | Low thud, tearing metal (three successive panel mode banks plus stick-slip grind), branch snaps and settling debris. |
| fire | dur | Roar, flame flutter, bursty crackle resonators and wood pops. |
| counter_tick | — | Small rounded plastic modes (330/920 Hz) plus a flap-settle micro-tick. |
| ink_bleed | dur | Low swell with an opening LP (200→1100 Hz), tiny rising-chirp bubbles and a faint fizz. Very soft. |
| riser | dur, intensity | Non-tonal: an LP opening 300 Hz→3.5 kHz plus a low-Q band focus, a growing rumble and widening stereo. Use `anchor:"end"`. |
| sub_drop | dur | 90→30 Hz glide with light oversampled saturation and an onset thump. |
| rope_snap | intensity | Hook thwack, inharmonic stiff-cable twang (B = 0.02, 2 polarisations), stick-slip creak and fabric flap. |
| winch | dur | Gear-mesh impulses into housing resonances, motor orders, brush noise, pawl ratchet and drum rumble. |
| footsteps | count, interval, surface bridge/stone | Heel (soft sole plus heel-edge click) and toe. Bridge: wooden planks in two energy-balanced groups, steel girder ring and grit. Stone: dull thud plus grit. |
| room_tone | dur, kind office/cell | office: air, HVAC and a 60 Hz hum family. cell: concrete rumble, a 120 Hz bulb buzz and rare distant clanks. |
| gavel | intensity | Hardwood block modes, desk body, a bounce, and a short procedural room. |
| flash_hit | intensity | 150 ms reversed swell ending exactly at `FLASH_HIT_PREROLL`, then a dense transient, sub punch, body slam, air bloom and dark tail. |

## Known limitations
- Measurements stand in for listening; there was no human audition. The spectrograms were checked visually after calibrating ffmpeg (its `showspectrumpic stop=` zoom mis-maps frequencies, so full range is used).
- Generators assume 48 kHz.
- `engine` cost scales with duration: about 0.1 s of compute per second of audio.
- Doppler on the engine is a frequency warp, not a propagation delay, by design.
