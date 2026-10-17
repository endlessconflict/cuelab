# 05. Mix and master

The mix is a recipe in `engine/mix.py` driven by `project.json`. You change numbers, not code.

## The chain

```
effects (dry) + room reverb return + hall reverb return          = sfx bus
score stems: pad (low-pass 7 kHz), bass (high-pass 32 Hz), arp (low-pass 9 kHz), drums, lead
  -> post() hook (mutes, bus filter sweeps) -> sum -> energy arc (project.json "arc")
  -> side-chain duck from tier-1 sounds (up to duck_db, release 0.32 s)
mix = music * music_trim + sfx * sfx_trim + room tone (-50 dBFS pink)
  -> top-end tilt (remove 22% of the energy above 6.5 kHz) -> master fade ("outro")
  -> high-pass (36 Hz, 4th order) -> soft glue (tanh 0.9)
  -> gain to the loudness target -> look-ahead true-peak limiter -> verify true peak, adjust -> AAC
```

## Levels and ducking

- `music_trim` +8 and `sfx_trim` -6 are starting values; the report prints music-alone and effects-alone loudness (the example: -18.0 and -16.8 LUFS) and the focal-over-bed median (+0.7 dB in the example). Aim for focal events clearly over the bed.
- Ducking from the **tier-1 copy** of the effects: envelope follower (attack 4 ms, release 0.32 s) scaled so that sounds at or above -27 dBFS duck the music by the full `duck_db` (6.5 dB). 6.5 dB is the default; check the focal-over-bed median in the quality output. Raise depth before raising effect gain.
- Tier 3 never ducks the music.

## The energy arc

`arc` is a list of `[frame, dB]` points, interpolated linearly in dB, applied to the music bus. It is where the "quiet open, build, gap, drop" shape becomes numbers. Without it the music is a flat bed and the piece has no arc even when the arrangement does. A good arc is monotone within a scene, steps at cuts, and has a 6 to 10 dB swing across the piece.

## Loudness

Target integrated loudness by platform (check the platform's current guidance; these are the usual ranges):

| delivery | integrated | true peak |
|---|---|---|
| social feed video (LinkedIn, Instagram, X, TikTok) | -14 to -16 LUFS | at most -1 dBTP |
| YouTube | about -14 LUFS | at most -1 dBTP |
| broadcast (EBU R128) | -23 LUFS | -1 dBTP |
| podcast | -16 LUFS stereo | -1 dBTP |

The meter is ITU-R BS.1770-4 (K-weighting, 400 ms blocks, absolute gate -70, relative gate -10 LU) and was within 0.2 LU of ffmpeg's `ebur128` filter on the example (-15.0 against -15.1). Loudness range is reported; the example has 7.0 LU. A very low value means a flat piece; a very high one is hard to follow on a phone.

## Limiter

A look-ahead limiter on the 4x oversampled peak: the required gain is the running minimum over a 4 ms look-ahead, smoothed (no clicks), released with a 90 ms one-pole. It adds no delay (the look-ahead shapes the gain only). The pipeline limits to `ceiling - 0.25` dB, measures the oversampled peak again, trims if needed, and re-measures loudness; if the limiter ate more than 0.3 LU it raises the input once and limits again. `build` prints `pre_limiter_true_peak_db` and `loudest_frames_pre_limiter`: **reduce the cues at those frames** instead of letting the limiter work harder. Up to about 3 dB of limiting on a few frames is fine; more means a stacked moment (chord + impact + kick + sweep) and the fix is to move one of them a few frames or lower it.

## Phone speaker and mono

Simulate: high-pass 230 Hz (4th order) and low-pass 9 kHz (2nd order), then measure the loudness loss (1.8 dB for the Merkle example; much more means the energy is in the sub). Mono: sum L and R and re-measure (0.94 dB loss, L/R correlation 0.68 in the example).

## Room tone and the tilt

- Room tone: pink noise through a 1.8 kHz low-pass at -50 dBFS RMS. It makes the silence a room.
- Tilt: subtract 22 percent of the signal above 6.5 kHz. The interface sounds are bright and the video is likely watched at low volume on a phone; the tilt takes the edge off without dulling the pings (their energy is below 6 kHz).

## Output files

`out/mix.wav` (float32 stereo), `out/stems/sfx.wav` and `music.wav` (post-gain stems for analysis), `out/<video>-sound.mp4` (video copied untouched, AAC 192 kb/s, 48 kHz, faststart), `cue_sheet.csv`, `mix_report.json`, `quality_report.json`, `sync_audit.json`, `QA_REPORT.md`, `mix_analysis.png`, `mux_check.json`.

## AAC and the container

Encoding to AAC adds a priming delay that the MP4 edit list compensates; verify rather than trust: decode the AAC from the final file and cross-correlate with `mix.wav` at four points (the check accepts up to 48 samples, 1 ms; the example gives 0) and compare `ffmpeg ebur128` to your meter. `cuelab.py report` does both.
