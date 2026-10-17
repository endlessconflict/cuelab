---
name: cuelab
description: Design and build synchronized sound (score, effects, mix, master) for a finished silent video by treating sound as a function of the picture's timeline. Builds a cue sheet from the video's own timing constants, synthesizes everything procedurally (no API keys, no samples), then proves the sync by measuring the picture and checks loudness, phone and mono playback, and clicks. Use when asked to add sound, music, sound effects, a soundtrack or sound design to a video, especially a Remotion video with a timeline.json, when frame-accurate sync matters, or when no audio assets exist. Voice-over is only outlined, not built.
---

# cuelab

A method and a small engine for scoring video **the way you would test a system**: the picture is the specification, every sound is a cue with a source (a frame constant in the picture's code), and the result is verified by measuring the video, not by trusting the numbers. It was distilled from scoring a 77 s technical explainer (619 cues, 37 sync checks, all inside their tolerance windows) and re-proven on an unrelated 36 s video (`examples/merkle-proof-scored`, 35 of 35).

Paths below are relative to this skill's folder.

## When to use it, when not to

Use it for: adding music and effects to an explainer, a UI or product animation, a diagram video, a motion piece made in code. It is strongest when the picture is **generated** (Remotion, canvas, three.js), because then every event time is known exactly.

Not for: recording or editing live audio, mixing a podcast, lyrics, voice cloning, or scoring footage where event times must be found by listening (the audit tooling still helps, the cue sheet cannot be derived from code). If the video has no timeline file, build one first (see `references/10-adapting.md`).

## The eight principles

1. **Sound is a function of the picture.** Sonification first, decoration second. Every sound must answer "what changed on screen". A sound that answers nothing is cut, or demoted to tier 3 and made quiet.
2. **One timeline.** Scene order, lengths, overlap and easing curves come from the same `timeline.json` the video renders from. The engine ports the easing exactly (tested to 5e-16 against Remotion), so a sound can follow a motion curve rather than guess it.
3. **Timbre carries the picture's semantics.** The picture has one focus colour; the sound has one bright pure tone (the "ping") reserved for that element. Data fixed in place rings as glass; mechanical details click; failures are minor seconds and muted thuds; verified claims resolve to the single major chord of the piece.
4. **Sound the first frame the eye sees it.** Not the first frame the animation clock runs. Fades, slow-start easings, elements hidden behind others and discrete steps all shift the visible moment; reason about visibility, then let the audit confirm.
5. **Measure the picture, not the code.** A pixel probe on the decoded video finds the real frame of each event. A check per cue class turns "synced" from an opinion into a table.
6. **Mix by measurement.** Loudness to a target (LUFS, true peak), a phone-speaker simulation, a mono sum, a click detector, a focal-over-bed ratio. If a number is out of band, fix the source of the number.
7. **Silence is material.** A designed gap (a drop-out at "zero", a pause before the drop, a silence after a failure) is louder than any hit. Never fill it out of nervousness.
8. **Honesty about ears.** An agent cannot listen. Say so, deliver what was measured, list what only a human can judge, and give them the shortest path to judge it (isolated samples, a short list of timestamps to check).

## The ten phases

| # | phase | deliverable | gate |
|---|---|---|---|
| 0 | intake | video, timeline, platform, whether a voice is wanted | the video is final (a picture change after scoring costs a rebuild) |
| 1 | analysis | list of picture events per scene with their source constants | each tier-1 event has a frame and a reason |
| 2 | direction | semantic map, key, tempo grid, arc, silences | grid check: scene starts land on half beats |
| 3 | cue sheet | `cues.py` | every cue quotes its source; densities sane |
| 4 | score | `music.py` | harmony changes at cuts; rhythm on the global grid |
| 5 | build | `python scripts/cuelab.py build <project>` | renders, masters, muxes |
| 6 | audit | `checks.py` and `cuelab.py audit` | every check inside tolerance, none "not measurable" |
| 7 | quality | `cuelab.py quality` | numbers in band (table in `references/07-quality-checks.md`) |
| 8 | iterate | trim sources of out-of-band numbers | max three rounds |
| 9 | deliver | muxed mp4, stems, cue sheet, QA report, listening checklist | honest limits stated |

### Phase 0: intake

Confirm: the video file (silent, final), its `timeline.json` (or how to make one), the platform (loudness target, loop behaviour), the mood in three words, whether a voice is wanted (default no for captioned explainers, see `references/09-voiceover.md`), and what is in the environment (python with numpy/scipy/matplotlib, ffmpeg, node if you want the easing check). Do not ask for API keys: nothing here needs them.

### Phase 1: analysis (the cue inventory)

Open the video's scene source and list, per scene, every change of state with its local frame and the constant that defines it: things appearing, values locking, steps advancing, counters running, motions starting and stopping, text typing, cuts. Classify each (recipes in `references/02-cue-sheet.md`):

| picture event | cue recipe |
|---|---|
| snaps in | one cue on that frame |
| fades in | one cue 1 to 3 frames after the first visible change |
| a continuous motion (eased) | one `glide` / `sweep` / `rise` cue with `a`, `b`, `ease` so pitch rides position and loudness rides speed |
| a thing arrives | a cue at `landing(a, b, ease, distance_px)` |
| a discrete step from a continuous progress (row finished, column known) | a cue at `ceil(inv_prog(...))`, the first frame the step is visible |
| typed text | one click per character on the integer frame it appears, several in one frame spread across the frame |
| a value computed then locked | a `scramble` over the window plus a bell on the lock frame |
| a scene cut | a wipe whoosh centred on the wipe, pan following its direction |

### Phase 2: direction

Fill the semantic map (what each colour or object class sounds like), pick the **key and mode** (minor or dorian for technical, a single major lift reserved for the payoff), the **tempo grid** (a beat length in frames such that every scene start is a multiple of half a beat: at 30 fps, 90 BPM is 20 frames per beat), and an **energy arc** (quiet open, build, designed gap, drop, resolution, thin ending). Decide where silence goes. Details and the worked examples in `references/01-sound-direction.md`.

### Phases 3 to 5: build

```
python scripts/cuelab.py new <dir> --video <silent.mp4> --timeline <timeline.json>
# edit <dir>/cues.py, music.py, checks.py, project.json
python scripts/cuelab.py all <dir>        # build, audit, quality, report
```

`cues.py` and `music.py` are plain Python that call the engine (`engine/cuelib.py` handlers, `engine/music_kit.py` blocks). Custom cue types are one decorated function. The engine is deterministic: the same inputs give the same samples.

### Phase 6: audit (what makes this more than a guess)

`checks.py` declares ROIs (regions of the frame) and, per cue class, a check that finds the frame where the picture really does the thing and compares it with the cue frame, with two tolerance windows: **HARD** (-1, +2 frames) for things that snap in and **FADE** (-1, +4) for things that fade. Calibrate ROIs by measuring the colour bounding box of a known frame, never by eye. A check that cannot measure is a failure, not a pass. Expect the first run to find real mistakes (a dot hidden under a node, cues four frames late, typing not on whole frames); those are the point. `references/06-sync-audit.md`.

### Phase 7 and 8: quality and iteration

Run `quality`. Bands: integrated loudness at the target (default -15 LUFS), true peak at or below -1.5 dBTP after AAC, loudness range 6 to 9 LU for a piece with an arc, focal events about 3 dB over the bed, phone loss under 3 dB, mono loss under 2 dB, zero unexplained clicks. If a number is out of band, change the source (a cue gain, a stem level, the arc), rebuild; do not patch the master. `build` reports the loudest pre-limiter frames: trim those cues.

### Phase 9: deliver

Deliver the muxed mp4 (video stream copied untouched, AAC 192 kb/s 48 kHz), `out/mix.wav`, stems, `cue_sheet.csv`, `QA_REPORT.md`, the analysis figure, and a **listening checklist**: five to ten timestamps for a human ear (the hook, the drop, the silence, the resolution, the end) with what to listen for. State that nothing was auditioned by an agent.

## Choosing between options

| question | choose | because |
|---|---|---|
| procedural or AI-generated music | procedural by default; AI stems only if the user wants a genre sound and accepts the sync cost | procedural keeps every musical event on a frame; generated stems cannot be edited to fit a moved scene |
| voice-over | not by default; plan windows first | the captions already carry the words; a voice competes with sonification |
| music under effects | duck 5 to 7 dB from tier-1 sounds | the focal sound must read at low volume |
| sub bass | give hits harmonics at 2x, 3x, 4x and a saw layer under bass notes; high-pass the master at about 36 Hz | phone speakers cannot reproduce below about 150 Hz |
| ending | fade to silence over the last 1 to 2 s | a looping feed restarts without a cut |
| key | modal minor with one major lift | the lift means something |
| tempo | pick it from the scene starts, not from taste | cuts land on beats |

## What this method prevents

Sound that drifts from the picture; sound that is loud on a laptop and gone on a phone; hits that clip or click; a soundtrack nobody can adjust after a picture change; a mix tuned by ear on one system; claims of "perfect sync" without a measurement. Concrete bugs met, each with symptom, cause and fix, are in `references/08-pitfalls.md`.

## Files in this skill

| path | what |
|---|---|
| `references/01-sound-direction.md` | semantic map, key and grid, arc, silence, loops |
| `references/02-cue-sheet.md` | cue schema, tiers, picture-event to cue recipes, visibility reasoning |
| `references/03-synthesis.md` | the DSP kit and how to add a voice without clicks |
| `references/04-music.md` | harmony, arrangement by scene, bass, drums, arps, payoff |
| `references/05-mix-master.md` | chain, ducking, loudness, true peak, limiter, phone and mono |
| `references/06-sync-audit.md` | ROI method, check recipes, tolerances, calibration |
| `references/07-quality-checks.md` | every quality check with its band |
| `references/08-pitfalls.md` | every real bug met |
| `references/09-voiceover.md` | design notes for adding a voice (untested): windows, ducking, files |
| `references/10-adapting.md` | other renderers, other styles, samples and AI stems |
| `engine/` | `timeline`, `dsp`, `synth`, `cuelib`, `music_kit`, `mix`, `audit`, `quality`, `report`, `project` |
| `templates/project/` | the project scaffold (`project.json`, `cues.py`, `music.py`, `checks.py`) |
| `scripts/cuelab.py` | `new`, `build`, `audit`, `quality`, `report`, `all`, `ease-check` |
| `../../examples/merkle-proof-scored/` | a complete scored example with QA report |
