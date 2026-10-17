# 06. The sync audit

The code that generated the picture says when things *should* happen. The video says when they *do*. The audit measures the second and compares it with the cue sheet.

## How it measures

`audit.py` decodes the video once with ffmpeg (half resolution, rgb24) and, for each ROI, records per frame:

- the pixel count and centroid of every colour in `project.json "colors"` (pixels within `color_tol` of the RGB value);
- mean luminance;
- `diff`: mean absolute change from the previous frame (the "something changed here" signal, robust to fades).

The result is cached in `out/series.pkl` and reused when it is newer than the video and has the same ROI names; `--force` ignores it (`all` always forces). A check is a small function in `checks.py`.

## Writing a check

```python
ROIS = {"row3": (660, 214 + 94 * 3, 340, 70), ...}          # x, y, w, h in full-resolution pixels

def checks(S, A):
    s = 6 + 7 * 3                                              # the scene constant the cue follows
    vis = A.first_above(S["row3"]["data"], A.T.g("leaves", s + 30), A.T.g("leaves", s + 44), 8)
    A.report("leaves: row 3 hash locks", vis, A.T.g("leaves", s + 34), "glass_tick", tol=A.HARD)
```

Helpers: `first_above(series, lo, hi, thr)` (first frame a signal exceeds a threshold), `edges(series, lo, hi, thr, rising)` (frames of steps up or down: a value *leaving* the focus colour is a falling edge), `steps_of(centroid, lo, jump)` (jumps of a moving thing), `last_move(series, lo, hi, thr)` (when a thing stops), `onset`, `settle`, `report` (one visual frame vs one cue frame), `stat` (many errors at once: all key clicks, all scan steps), `cue_frames`. The tolerance windows are in frames of `cue - visual`:

| window | range | for |
|---|---|---|
| `A.HARD` | -1 to +2 | elements that snap in or change colour on a frame (a hash locking, a bit flip, a step) |
| `A.FADE` | -1 to +4 | elements that fade or slide in |

Windows are in frames of `cue - visual` (at 30 fps, -33 ms to +67 ms for HARD); keep systematic offsets near zero and let the window absorb rounding. Values to expect when the cue sheet is right: exact 0.00 for discrete steps, 0 to +1 for fades, -1 for slow-start motions.

## Calibrating ROIs (never by eye)

1. Extract a frame where the element is on its own (e.g. the first frame after it appears).
2. Compute the bounding box of its colour (a short numpy script; see how `examples/merkle-proof-scored/checks.py` documents its boxes: "the focus-colour bounding box of the proof scene at frame 480 puts leaf 5 at x 608 to 680, y 620 to 706").
3. Add margin (10 to 20 px), keep ROIs from overlapping other changing things, avoid regions the previous scene still occupies during the 10-frame wipe (start search windows after it).

## Colour meters and what breaks them

- **Tolerance overlap.** With `color_tol` 55 an ember (255,122,69) pixel counted as rose (255,77,109); the "bad" check passed 20 frames early. Use a tolerance well under half the distance between the two nearest colours (38 worked for ember vs rose).
- **Edges and outlines.** A lit-edge box has its role colour on its edges from frame 0; a "colour appears" check sees it immediately. Use luminance change for "lights up".
- **Transparency.** A semi-transparent object does not match its colour until it is nearly opaque; use `diff` for the first change.
- **Compression.** Colours drift a few levels after h264; thresholds are on counts, not exact values.
- **Text colours.** A hash that locks by changing text colour from muted to data is a clean signal in a narrow ROI (the leaf rows of the Merkle example are audited this way).

## Which checks to write

One per class of cue, plus one per tier-1 cue:

| class | check |
|---|---|
| value locks | colour change in a narrow ROI |
| focus moves | focus-colour onset or centroid steps |
| typed text | `diff` in the card ROI; every key cue against the nearest frame with a text change (`stat`) |
| discrete scan steps | centroid steps vs the cue list (`stat`, expect mean 0.00) |
| arrivals | `last_move` of a centroid vs the landing cue |
| wipes | full-frame `diff` peak vs `cue + 8` (the whoosh peaks 8 frames after its start) |
| captions | `diff` in the caption band vs the first-line ticks |
| failures | the bad colour onset in the band of each node |

Minimum useful audit: wipes, captions, every tier-1 class. The Merkle example has 35 checks over 161 cues (35/35 inside tolerance).

## When a check fails: whose bug is it?

1. Print the series around the frame (`pickle.load(open("out/series.pkl","rb"))`) and look.
2. If the picture does the thing at a different frame than the code constant says (hidden element, slow start, draw order), **the cue was wrong**: change the cue and its comment.
3. If the ROI or threshold is wrong (another element in the box, tolerance overlap), fix the check, not the cue.
4. If the picture itself looks wrong (an element appears late, a dot starts hidden), tell the video's author; the audit has found a picture bug. That happened during the coreboot piece (a dot that started hidden under a node).

## Audit as regression test

Keep `checks.py` in the repo. When the picture changes, run `cuelab.py audit <dir> --force`; the failing rows are the cues to update. This is the main reason the cue sheet quotes source constants.

## Verifying the mux

`cuelab.py report` decodes the AAC track of the muxed file, cross-correlates it with `mix.wav` at four points (accepted if within 48 samples; the example is 0 at all four), reads stream info and duration with ffprobe (check start times yourself in `mux_check.json`), and runs ffmpeg's `ebur128` for an independent loudness and true-peak reading.

## The easing port

`cuelab.py ease-check <dir>` runs Remotion's own `Easing.bezier` (via node, with `npm install` done where `scripts/ease_ref.mjs` looks) for the `out`, `inOut` and `soft` curves and compares with the Python port; it exits non-zero above 1e-4. Run it once per project that uses Remotion easing.
