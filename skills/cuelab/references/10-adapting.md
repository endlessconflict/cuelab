# 10. Adapting cuelab

The engine knows frames, cues, voices, a mix and an audit. Everything else is configuration. Here is how it bends to different jobs.

## By video type

| type | what changes |
|---|---|
| silent social explainer (the default) | as in the examples; loudness -15 LUFS; music at the arc, sparse effects |
| product demo / UI walk-through | more tier-2 interface sounds, fewer tier-1 events; no drops; music quiet and steady; add voice (see 09) |
| data visualisation / chart animation | pitch mapped to data (see 02, "Pitch choices"); a counting glide per number; verify totals against the data |
| trailer / teaser | strong arc, silence gaps declared, risers into cuts, hits at cut frames; target louder (-14) with a limiter ceiling at -1 |
| loop / GIF-like piece | end the file near silence with the `outro` curve so a looped video restarts cleanly; no loop-seam check exists, listen to it |
| long form (3+ minutes) | the structure changes more than the engine: define sections with their own `HARMONY` and arc; expect longer render times |
| broadcast | read the delivery spec; set `target_lufs` and `ceiling_db` to it |

## By picture source

The engine does not care how the video was made. It needs: the video file, `timeline.json` (scene starts and lengths, overlap, fps, easing curves) and the source constants. If the video came from a non-Remotion tool, the easing port may not apply: then skip the model-based timing and derive every cue from measurement (the audit helpers work directly on the decoded video), and note that no source constants exist.

If the video has no `timeline.json`: write one by hand (fps, scene starts and lengths, overlap, easing curves) after finding the cuts on a contact sheet; the engine has no automatic cut detection.

## By frame rate and resolution

`fps` comes from `timeline.json`. Everything is computed in seconds from frames, so 24, 25, 30 and 60 fps all work; tolerance windows are in frames, so at 60 fps they are half as wide in time. Revisit `A.HARD` and `A.FADE` in `engine/audit.py` if you target high frame rates.

## By taste

- **Genre of score.** The score is `music.py`. Replace harmony tables, arrangement and the arc. The instruments (`pad_note`, `bass_note`, etc.) can be re-parameterised. For acoustic or orchestral scores this engine is the wrong tool.
- **Ambient only.** Drop drums and arps; keep pad, one pulse and the effects.
- **Silent-friendly minimalism.** Only tier 1 and 2, no music; loudness target stays; the arc is flat.
- **Different personality of effects.** Adjust `synth.py` constants (decay times, partials, FM index). Keep the family consistent: one set of timbres for a whole piece.

## By risk

- Platform with strict loudness (broadcast): read their delivery spec, set `target_lufs` and `ceiling_db` accordingly, run `report` and keep the printed numbers.
- Accessibility: provide a captioned or transcribed version; remember sound is not available to everyone and must never be the only carrier of information.
- Photosensitive or sound-sensitive viewers: avoid sudden loud sounds; the quality check on loudest frames helps.

## Extending the engine

1. **New voice** in `synth.py`, new handler in `cuelib.py` (or in your project's `cues.py`).
2. **New check** in your `checks.py`; add a helper to `audit.py` only if three projects need it.
3. **New measurement** in `quality.py`: add it to `rep`; `report.py` prints only the keys it knows, so extend `qa_markdown` too.

Keep determinism: no clocks, no network, seeded randomness.

## Handing a project over

A project directory is self-contained: `project.json`, `cues.py`, `music.py`, `checks.py`, `timeline.json`, the video, and `out/`. Commit all but `out/*.wav`, `out/stems/`, `out/series.pkl`. The person who takes over runs `python scripts/cuelab.py all <dir>` and gets the same report.
