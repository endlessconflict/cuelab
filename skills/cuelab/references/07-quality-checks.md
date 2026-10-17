# 07. Quality checks

`engine/quality.py` measures the rendered stems and master. It has no ears. It reports numbers; you decide what is acceptable. The script does not enforce pass/fail thresholds except where stated, so the guide values below are starting points to judge the printed numbers against, not gates the code applies.

## What is measured (`cuelab.py quality`)

| # | measurement | how | guide value |
|---|---|---|---|
| 1 | onset latency | for `latency_cue_types` (default key, bit, ui; tier 1 and 2 only), find the onset of the cue's own click in the effects stem within -10 to +30 ms of the cue time (3 kHz high-pass, envelope derivative); cues with another sound within 40 ms are skipped | mean near 0, p95 under about 30 ms (one frame is 33 ms) |
| 2 | focal over bed | level of the tier-1 copy against the music stem in the 250 ms after each tier-1 cue | median positive; the example's median is only +0.7 dB with p10 at -2.0, so some focal events sit under the bed. Raise `duck_db` or tier-1 gain if the low tail matters |
| 3 | spectral balance | per-scene share of energy in 7 bands (sub, bass, lowmid, mid, presence, air, top) | no band that dominates a scene for no reason; "air" and "top" low relative to mid |
| 4 | phone speaker | 230 Hz high-pass plus 9 kHz low-pass, loudness drop | the example loses 1.8 dB; a drop of 3 dB or more means the energy lives in the sub |
| 5 | mono sum | loudness loss and L/R correlation | the example loses 0.94 dB, correlation 0.68 |
| 6 | hygiene | last 10 ms level, DC offset, music stem level during each `marker silence=` window | tail under -60 dBFS, DC about 1e-5 |
| 7 | click detector | second difference of the master and of the music stem against a local median; ignores samples within 20 ms of a tier 1/2 cue and drum hits on the music grid (`grid_frames`) | an empty list; investigate each entry |

`cuelab.py build` also reports (in `mix_report.json`): integrated loudness, loudness range (EBU 3342 style), true peak, the pre-limiter true peak, the six loudest pre-limiter frames, and the loudness of music and effects alone.

## Honest reading of the example

`examples/merkle-proof-scored` reports, from its own files: -15.0 LUFS integrated, LRA 7.0 LU, true peak -1.71 dBTP, pre-limiter true peak +0.79 dBTP at frame 656, music alone -18.0 LUFS against effects alone -16.8 LUFS, the mux decoded with lag 0 samples at four points, and ffmpeg's own meter at -15.1 LUFS and -1.6 dBFS peak.

Items that are not clean and are left visible on purpose:

- the click detector lists one unexplained discontinuity at frame 366.3 in the master and the music stem, and one at frame 146.0 in the music stem; neither was investigated by ear;
- focal events sit only +0.7 dB over the bed in the median (the report calls them "focal"; many are quiet detail by design);
- the music stem inside the declared silence (frames 826 to 846) measures -61.8 dBFS.

Seven audit checks use a wider window than HARD or FADE because the sound deliberately leads a slow-start motion (sweeps, glides, the payoff chord, the X impact); those windows are written in the example's `checks.py` next to the check.

## Fixing common findings

| finding | likely cause | fix |
|---|---|---|
| pre-limiter true peak above 0 dBTP | stacked cues at the frames in `loudest_frames_pre_limiter` | lower a gain or move one cue a few frames; avoid relying on the limiter |
| limiter ate loudness | same | the build raises the input once and limits again; fewer stacked peaks is better |
| click | a voice without a fade, a filter started cold, a mute at non-zero crossing | rules in 03-synthesis; `mute` uses a ramp |
| focal events under the bed | duck too shallow or arc too high there | raise `duck_db`, lower that stretch of the arc, then raise tier-1 gain |
| phone loss large | bass and kick carry the energy | strengthen the harmonics of the sub, lower the sub |
| mono loss | wide reverb or detuned pad cancelling | reduce the hall return, reduce pad detune |

## What no measurement can tell you

Whether the sounds feel right, the rhythm is pleasant or the mix translates in a noisy room. Listen on headphones, on a phone speaker and at low volume. Nothing in this repository has been auditioned by ear by its author; the examples pass the numbers above, and that is all that is claimed.
