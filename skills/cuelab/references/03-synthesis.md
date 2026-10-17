# 03. Synthesis: the DSP kit

Everything is generated with numpy and scipy at 48 kHz, float64, seeded and deterministic. No samples, no network, no keys. The kit is small on purpose; new voices are recipes on top of it.

## Layers

| module | role |
|---|---|
| `dsp.py` | oscillators (sine, additive saw and square, noise), exponential and ADSR envelopes, biquad filters including a **time-varying** low/band/high-pass with state carried across blocks, stereo panning (static and per-sample), convolution reverb IRs, feedback delay taps, saturation, the `Track` buffer with sample-accurate placement |
| `synth.py` | the voices (below), every one peak-normalised and ending on a 4 ms fade |
| `cuelib.py` | the handlers that turn a cue into voices, plus reverb sends and the tier-1 copy used for ducking |
| `music_kit.py` | `Stems`, `pad_bed`, drum and bass helpers, `arp`, `beats()` |

## Voices

| voice | recipe | used for |
|---|---|---|
| `ping(freq)` | sine + faint octave and third partial, 0.8 ms attack, 160 ms decay | the focus element |
| `bell(freq)` | 2-operator FM, modulation index decays faster than the carrier, plus a fast second partial | data locked, chords, resolutions |
| `wood(freq)` | short damped sine with a downward pitch tick plus a noise click | an empty slot, a hollow reject |
| `tick(freq)` | band-passed noise burst plus a faint sine | interface, captions, scramble streams |
| `key_click(seed)` | thock body (200 Hz down-bend), 2 to 6 kHz click, low-passed tap; varies with the seed | typing |
| `enter_thock` | heavier version | return key |
| `bitflip(up)` | two short blips a fourth apart with a square partial | register bits |
| `pluck(freq)` | additive; higher harmonics decay faster | arps, stack pushes, note events |
| `sub_hit(freq)` | sine with a pitch drop plus partials at 2x (0.75), 3x (0.38), 4x (0.16) | impacts that must read on a phone |
| `kick`, `hat`, `clap` | classic synthesis | the groove |
| `denied()` | thud + low-passed clack + a minor second (311 and 330 Hz) | something has nowhere to land |
| `whoosh(...)` | noise through a swept band-pass, swell or rise envelope, panned across | cuts, motion |
| `power_up/down` | harmonic stack with falling or rising pitch and a closing or opening low-pass | machine start, a teardown |
| `reverse_swell` | noise swept up with a cubic ramp | the inhale before a silence |
| `pad_note` | three detuned additive saws through a low-pass with slow attack and release | the harmonic bed |
| `bass_note` | sine sub + low-passed saw + octave, soft-clipped | pulse; the saw carries pitch on phones |
| `lead_note` | sine with decaying 2nd and 3rd partial | melodic payoffs |
| `room_tone` | pink noise through a low-pass | the floor under silences |

## Rules for new voices (each came from a bug)

1. **End every voice on a fade.** A voice whose envelope has not decayed when its buffer ends clicks (a 0.3 s kick still at 12 percent amplitude produced a discontinuity every 40 frames). `_norm()` applies a 4 ms fade to everything; do not bypass it.
2. **Band-limit.** Additive saws stop at `maxf` (6.5 to 9 kHz). Noise bursts are band-passed. Nothing is meant to be loud above 9 kHz.
3. **Pitch glides integrate frequency.** `phase = 2*pi*cumsum(f)/SR`, never `sin(2*pi*f(t)*t)` (that makes a different, wrong chirp).
4. **Time-varying filters need warm-up.** Filtering only a segment starts the filter with zero state and clicks at the segment start. Filter 0.6 s earlier at a transparent cutoff and write back only the settled part (`bus_filter_sweep`).
5. **Seed everything.** `np.random.default_rng(seed)` with a seed derived from the cue index. A rebuild must give the same samples.
6. **Do not rely on sub bass.** Give low sounds harmonics. A phone speaker removes everything under about 150 to 200 Hz.
7. **Mono voices, stereo placement.** Voices are mono; placement does the pan (equal power). Stereo voices (whoosh) carry their own motion.
8. **Perceptual levels, not peaks.** Normalise voices to peak 1 and set loudness with `gain`; compare in the cue sheet by tier.

## Reverb and space

Two sends, shared by all cues: a **room** (RT60 0.42 s, 6 ms pre-delay) for interface sounds, a **hall** (RT60 2.6 s, 22 ms pre-delay) for bells, pings and impacts. The IRs are synthetic (decaying noise in three bands, a few early reflections), convolved once for the whole track with `fftconvolve`, so cost does not grow with cue count. Return levels are fixed (-4 dB room, -3 dB hall) and per-cue send amounts are set in the handler (`room=-9`, `hall=-6`). Dry-ish for typing, deep for the resolution.

## Adding a voice and a handler

```python
# synth.py
def my_voice(freq, dur=0.4):
    t = tt(dur)
    x = np.sin(TWO_PI * freq * t) * np.exp(-t / 0.08)
    return _norm(x)

# cues.py
from cuelib import handler
@handler("my_type")
def _my(rig, c, i):
    rig.emit(S.my_voice(float(midi(c["midi"]))), c["f"], c["gain"], c.get("pan", 0), room=-8, tier=c["tier"], label="my")
```

`rig.emit(sig, frame, gain_dB, pan, room=dB send, hall=dB send, tier, label)` is the only way sound enters the mix; tier 1 emissions also go to the ducking copy.

## Performance

A 77 s piece with 619 cues and 23 s of pad notes renders effects in 2 seconds and the score in about 25 seconds on a laptop; the master (loudness, limiter, figure) another 15 to 20 s. The additive pad is the slowest part: lower `maxf` or the number of voices if needed.
