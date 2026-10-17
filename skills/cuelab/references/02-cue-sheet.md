# 02. The cue sheet

`cues.py` is the specification of the sound. It reads like a table of the picture's events, each with the source constant that defines it.

## Schema

```python
C.add(frame, "type", tier=1|2|3, gain=dB, pan=-1..1, **params)
```

| field | meaning |
|---|---|
| `frame` | global frame, fractional allowed. Convert scene-local frames with `T.g("scene", local)` |
| `type` | handler name in `engine/cuelib.py` (or your own with `@handler`, or `HANDLERS = {...}` in `cues.py`) |
| `tier` | 1 focal (music ducks under it, counted in the focal-over-bed check), 2 interface detail, 3 ambience and captions |
| `gain` | dB at placement; the master normalises overall level |
| `pan` | -1 left .. 1 right; derive it from the picture (`pan_x(px)`) |

Built-in types: `wipe`, `cap`, `title_rise`, `bell`, `ping`, `ui`, `wood`, `glass_tick`, `swish`, `revswell`, `impact`, `thunk`, `reject`, `chord`, `glide`, `sweep`, `bed`, `rise`, `scramble`, `note`, `bit`, `key`, `enter`, `power_down`, `shimmer`, `marker`. A `marker` makes no sound; it carries data for the mix or the quality check (`silence=frame`).

## Quote the source

Every block begins with a comment naming the scene file and the local frames the cue follows:

```python
# reveal = prog(f, 8, 52, inOut): a diagonal wave sweeps the field; the audit shows the first visible change at frame 19-22
C.add(g("hook", 16), "sweep", tier=1, a=g("hook", 16), b=g("hook", 52), ease="inOut", ...)
```

This is what lets a later session re-derive the cue after a picture change instead of nudging numbers.

## From picture event to cue (the recipes)

| picture does | recipe | notes |
|---|---|---|
| appears instantly | cue on that frame | |
| fades or slides in | cue 1 to 3 frames after the first visible change | measure the first change with a frame-difference probe, not the colour threshold (a fading colour passes a threshold late) |
| moves along an eased path | one `glide` (pitch and pan follow position), or `sweep` (a noise band follows a front, loud when it moves fast), or `rise` (object grows) with `a`, `b`, `ease` | loudness follows speed: `gradient(prog)`; the sound ends when the thing stops |
| arrives and stops | a settle sound at `T.landing(a, b, ease, dist_px)` | the first frame the speed is under 0.5 px/frame; `inv_prog(1.0)` is too late by several frames |
| crosses a value | `T.inv_prog(y, a, b, ease)` | a dot passing a node, a progress bar crossing a mark |
| a discrete step derived from a continuous progress (row finished, column known, counter increments) | `math.ceil(T.inv_prog(k / N, a, b, ease))` | the picture only changes on whole frames; the step is visible on the first frame at or after the crossing; `ceil` puts the sound exactly there (the DRAM scan: 24 steps at +0.00 frames) |
| typed text | for each integer frame, characters = `floor(prog(frame, at, at+dur, ease) * n)`; one `key` per new character on that frame, several in one frame spread by 0.3 frame | key clicks on fractional frames were up to 2 frames off in the first audit |
| a value is being computed, then fixed | `scramble` over the window (a thinning stream of tiny clicks) and a bell or glass tick on the lock frame | the lock frame is when the picture's text settles (`frame >= end`), not `end - 1` |
| a state flips (a bit) | `bit` on the flip frame, up for 0 to 1, down for 1 to 0; ping if the changed bit is the focus | |
| a counter counts up | one `glide` over the count, not a click per number | |
| a scene cut | `wipe` at `START - 2` (the whoosh peaks 8 frames after its start, centred on the 10-frame wipe) | |
| a caption line rises | `cap` at `from + i*5 + 1`, quiet, tier 3 | a tick is not the words; keep it at -32 dB or cut it |
| the end | `chord` on the last statement, fade by the `outro` curve | |

## Visibility reasoning (the mistakes that audits found)

Before timing a cue to an element, ask whether the eye can see it at that frame.

- **Hidden behind something.** A dot drawn in an SVG underneath DOM cards disappears when it passes under them. In the coreboot loop scene the dot started hidden under the top node and became visible 17 frames after the animation clock started; its pings had to be timed to the node entry angles, computed from the node geometry. Look at the frames.
- **Drawn semi-transparent.** A 3D object fading in via alpha shows at 20 to 30 percent opacity for several frames; a colour-threshold probe sees it late but the eye sees it early. Use the frame-difference onset for the cue and a colour probe only for the settled state.
- **Edges present from frame 0.** A lit-outline node already has its focus-coloured edges before it "lights up"; probe luminance change, not colour presence.
- **Slow-start easing.** `inOut` curves move almost nothing for the first frames: start the sound where motion is visible (the wave at frame 19 to 22, not 8), or let the loudness-follows-speed envelope make the early frames quiet.
- **Two scenes overlap during a wipe.** For 10 frames the old scene is still on the left; measure after the wipe ends.

## Tiers, gain and pan defaults

| tier | typical gain | pan | examples |
|---|---|---|---|
| 1 | -9 to -15 dB | from the picture | pings, resolutions, impacts, glides of the focus element |
| 2 | -14 to -26 dB | from the picture | bell on a value lock, bit blips, interface ticks, typing |
| 3 | -26 to -36 dB | gentle | caption ticks, shimmer, scramble streams |

Pan from the screen x position: `pan = clip((x / width * 2 - 1) * 0.8, -0.85, 0.85)`. Vertical position can map to pitch (higher on screen, higher note) or be ignored; be consistent.

## Pitch choices

Choose pings and bells from the chord that is sounding at that frame (check `music.py` HARMONY). Ladders (eight hash rows) walk a pentatonic scale upward so the scene sounds like one gesture. For data-driven pitch (the DRAM scan: pitch = passing count), build the mapping from the same seeded function the picture uses (`T.hash01` is a bit-exact port of the template's `hash`) and verify the total equals the number on screen.

## Density and clutter

After writing the sheet run `python scripts/cuelab.py build` and read `out/cue_sheet.csv` sorted by time. If two tier-1 cues are within 3 frames of each other, one of them is redundant. If a scene has more than about 25 cues per 10 seconds outside typing and scrambles, remove tier-3 first.

## Changing the picture later

The cue sheet is a function of the picture's constants. After any picture change: re-extract the constants, update the comments and values, rebuild, rerun the audit; the audit will point at exactly the cues that moved.
