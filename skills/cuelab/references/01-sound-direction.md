# 01. Sound direction

Decide before synthesizing, and write the decisions into `cues.py` and `music.py` headers so a change in the picture can be followed.

## The semantic map

Take the picture's own colour or object semantics and give each class a timbre. Two videos, same method:

| picture | coreboot video (hardware, purple) | Merkle video (data, frost blue) |
|---|---|---|
| the focus element (the one bright thing) | **ping**: a pure sine with a faint octave, instant attack, short bloom. Only ever the current step | the same ping, only when the focus colour appears or lands |
| data or firmware objects | glass: FM bells, detuned saw pads, hollow woodblock ticks for empty slots | a bell that rings when a value is fixed (a hash locks) |
| mechanical detail | filtered-noise clicks (typing, bit flips) | clicks for typed lines; a scramble stream for computation |
| 3D objects moving | Foley: pitch follows eased position, loudness follows speed | the same: pillar and bars |
| failure | a dull thud plus a minor second; never a siren | descending minor seconds, a thud, silence, no resolution |
| success | the single major chord of the piece | E major, once, when the root matches |

Write the table first. If a sound has no row it either needs one (a new class of picture event) or it should not exist.

## Sonification before decoration

The test for every sound: *what did the viewer just see change?* Good: a bell per locked hash (the ladder of eight rows ascends a pentatonic scale), one note per finished row of a grid, the pitch of each scanned column equal to its count of passing points so an eye diagram is literally the melody, a noise band that rides a wave front and gets loud when the front moves fastest. Decoration (a pad, a bass pulse) is allowed, but it is the bed under the sonification, never the other way round.

## Key, mode, one lift

- Pick a **modal minor** for technical subjects: dorian (D) or aeolian (E) are cold and open, and the pings (chord tones in the 5th and 6th octave) sit in the chords.
- **Spend the major chord once.** In both videos the first major chord arrives at the payoff (the return address pushed onto the stack; the root matching), and returns only for the final bar. If major is everywhere it is nowhere.
- Check each focal ping against the pad chord under it: a B natural over a Bb chord is a clash (found and avoided in the DRAM scan: the scale was chosen so the pings used chord tones). Choose ping pitches from the current chord.

## The tempo grid (computed, not chosen)

Rhythm lives on a **global grid** so it never shifts at a cut; chords change at the cuts. For that to sound right every scene start must land on a half beat.

1. List scene start frames (from `timeline.json`): e.g. 0, 110, 250, 450, 680, 850, 960.
2. Take the greatest common divisor (here 10 frames). A beat of `2 x gcd` or a divisor of `4 x gcd` works: beat = 20 frames at 30 fps = 90 BPM, sixteenth = 5 frames.
3. If the gcd is 1 or odd (starts like 0, 133, ...), either accept off-grid cuts and keep rhythm sparse around them, or retime the video's scene lengths (tell the user: it is one number in `timeline.json`).

BPM = `60 * fps / beat_frames`. 20 frames at 30 fps is 90 BPM; 16 frames is 112.5; 18 frames is 100.

## The energy arc

Write the arc as numbers in `project.json` (`arc`, dB over frames) after writing it in words. A shape that held up:

```
open quiet -> pulse enters with the first mechanism -> build through the explanation -> a designed gap -> THE DROP at the payoff
-> short release -> darker section for the counter-example -> silence -> brighter return -> thin ending, one last chord, fade
```

The drop is the loudest music of the piece, not the loudest sound (the resolution chord may exceed it). Pre-plan where each rhythm layer joins: bass first, then kick, then hats and claps, then arp, then lead.

## Designed silences

| silence | where it worked | how |
|---|---|---|
| "0 bytes" | the hook: everything cuts when the number zero appears, room tone only, one low note, then the first focal ping | `mute()` on pad, bass, drums, arp from the frame before the numeral until the next scene |
| the gap before the drop | 20 frames after a fill completes | duck the pad 9 dB and stop the kick 20 frames early |
| after a failure | the tamper scene: the X is drawn, the music stems stop for 1 s, the next scene returns with a wipe and the groove | `mute()` plus a `marker` cue declaring the silence so the quality check can assert it |

Keep a room-tone floor (pink noise around -50 dBFS) so silence reads as a quiet room, not a dropped signal.

## Openings and endings (feeds loop)

- First second: give a recognizable gesture (a rise, two bells) so an unmuted viewer hears intent in the first 500 ms.
- The video may loop in the feed. End on a decaying chord, fade to about -60 dB over the last 1 to 2 s (`outro` curve in `project.json`), and keep the opening gentle enough that a restart is not a jolt.
- Never end on a hit that is cut by the file end.

## Density budget

Count cues per second per tier. About 3 to 5 tier-2 sounds per second is busy but acceptable when quiet; tier 1 should be sparse (the viewer should be able to name each one). If a section reads as clutter, drop the tier-3 layer first (caption ticks), then tier 2 (interface ticks), never tier 1.

## What not to do

- No sound that mimics a different medium's convention for effect (swooshes on text for no reason, laser blips, camera shutters).
- No harsh high end: nothing loud above about 9 kHz; the master removes a quarter of the energy above 6.5 kHz.
- No emotive music that overrules the subject: the mood words in the brief decide ("exact, cold, physical"), not a genre.
- No sub-bass the phone cannot play: always give low sounds upper harmonics.
