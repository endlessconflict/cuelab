# 04. The score

A score for a video is an arrangement that follows the story, written as code so that every musical event has a frame.

## Layers (stems)

| stem | job | typical content |
|---|---|---|
| `pad` | the harmonic bed | detuned saw trios per chord note, slow attack, crossfaded at cuts |
| `bass` | pulse and root | sine sub + low-passed saw, 0.3 to 0.5 s notes on beats, octave ghost notes on offbeats |
| `drums` | the groove | kick on beats (from the first mechanism, four to the floor at the drop), hats on 8ths or 16ths, claps on 2 and 4 |
| `arp` | motion | plucked chord tones on 16ths, alternating pan, climbing with the explanation |
| `lead` | payoffs | a few sine notes (the root stated at the end), risers |

Stems are separate Tracks so the mix can arc, mute and filter them independently.

## Harmony as a table

```python
pad_bed(st, [(start, end, "Em9", level_dB, brightness), ...], CH)   # CH: name -> (pad midi list, bass root midi)
```

- Chords change **at scene cuts** (or at the frame where the picture's meaning changes: the root matching). That is how the ear links the music to the picture.
- Levels around -25 dB with brightness 0.3 to 0.55 for the bed; the release chord is louder and brighter (-21 dB, 0.75 to 0.8).
- Voicings in the 3rd to 5th octave (midi 43 to 66); bass roots in the 1st to 2nd octave (midi 29 to 43); pings and bells above (midi 74 to 93) so they sit above the pad.
- A tension chord for the counter-example (a diminished stack, not E minor) and a hollow open fifth for "nothing yet" (root + fifth + octave, no third).

## Arrangement by scene (a template)

| scene role | arrangement |
|---|---|
| hook / premise | open fifth, no rhythm; a low note when the number or object lands |
| mechanism step 1 to n | a single bass pulse enters with the first mechanism; hats on the offbeat at -34 dB |
| build | kick joins, bass root follows the harmony, claps on 2 and 4 from the second half, an arp climbs |
| the check / proof | sparse: low pulse every two beats and hats; the harmony sits on a suspended minor |
| the payoff | the drop: full kick, bass on beats and offbeats, 16th arp, the only major chord; or a short burst if the payoff is brief |
| counter-example | a slowing heartbeat (kicks at 22, 28, 36, 44 frame gaps), a low dark chord, then the designed silence |
| scale / summary | the groove returns, brighter, the last two chords major-leaning |
| ending | pad only, a lead note or two, one last chord, fade |

## Grid rules

- All rhythm helpers use `beats(f0, f1, step, offset)` on the global grid. A fill that starts at an odd frame still lands on grid because you pass `offset`.
- Keep rhythm gaps intentional: the 20 frames before a drop have no kick (the `touch` fill finishes, then a pause, then the drop); say so in a comment.
- Swing and humanisation are off: the picture is rigid, and the audit would only find "errors".

## Bass that survives a phone

Sine sub gives weight on headphones; a low-passed saw (650 Hz) carries the pitch through harmonics; a faint octave-up sine helps small speakers. Set the master high-pass at about 36 Hz so headroom is not spent on content nobody will hear.

## Arps

Eight-note patterns over chord tones, one pluck per 5 frames, alternating pan (`+-0.4`), gain -24 to -27 dB, climbing an octave over a build by transposing `12 * int(u * 2.2)` with `u` the progress through the scene. During a drop the arp changes pattern at the moment the harmony turns major (a note changes from the minor third to the major third at the exact frame the chord lifts).

## Payoff music

The payoff is chord + a short release of rhythm, not a long reward. One bar of E major with kick and bass is enough; the effects (`chord`, `glide`) carry the rest. Resolve the loop or tension that the picture built: if the picture shows a cycle that cannot close, withhold the last note of the motif until the break arrives (the coreboot loop scene: the arpeggio D F A C D is rung twice, the second time it never reaches the final D, then the resolving chord arrives with the cache node).

## Post hooks (mute, close the lid)

In `music.py`:

```python
def post(arrays, ctx):
    mx, T = ctx["mix"], ctx["T"]
    mx.mute([arrays["pad"], arrays["bass"], arrays["drums"], arrays["arp"]], f0, f1)          # a designed silence
    mx.bus_filter_sweep(list(arrays.values()), (a, b, c))                                      # close a low-pass lid between a and b, reopen by c
```

The lid closing is a good sound for "something is torn down" (the coreboot CAR teardown); reopen it bigger.

## What to avoid

- Chord progressions chosen for beauty that the picture does not earn.
- A melody that competes with the focal ping: the lead plays only at the end.
- A rhythm that does not stop for the silence it is supposed to frame.
- Long reverb tails over rhythmic material (the hall send belongs to bells and pings).
