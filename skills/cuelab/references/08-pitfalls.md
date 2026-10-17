# 08. Pitfalls

Each one happened while building the two reference pieces.

## Timing

1. **Sound placed at the end of a motion instead of the landing.** `inv_prog(1.0)` is the frame the eased progress reaches 1; the object has been visually still for several frames. Use `landing(a, b, ease, dist_px)`.
2. **Key clicks on fractional frames.** The text changes on whole frames. Compute characters per integer frame, and put the click on that frame.
3. **`end - 1` versus `end`.** The picture settles when `frame >= end`. A lock tick one frame early is audible as anticipation, one late as lag.
4. **Slow-start easing.** The first 6 to 10 frames of an inOut sweep show almost no change. Start the whoosh where the first change is visible.
5. **Overlapping scenes.** A wipe overlaps 10 frames; sounds for the next scene must not begin until the new scene is the only thing on screen, unless they belong to the wipe.
6. **Hidden elements.** An object drawn under another does not exist for the viewer. Time its sounds to visibility.
7. **Discrete steps from continuous progress.** Use `ceil(inv_prog(...))`.

## Measuring

8. **Color tolerance overlap** between two similar palette colours gave a pass 20 frames early.
9. **Lit edges from frame 0** make a colour probe useless for "lights up". Use luminance.
10. **Thresholds on tiny regions.** A ROI of a few pixels with an anti-aliased edge has a threshold crossing that depends on subpixel position. Use bigger ROIs or frame difference.
11. **Probing the wrong frame range.** After a wipe the old scene still shows. Start the window at the new scene frame plus 10.
12. **Cached series.** The audit reuses its cache when it is newer than the video and the ROI names match. If you change only ROI coordinates, pass `--force`.

## Synthesis

13. **Voices that end mid-wave** click. Everything goes through `_norm()`.
14. **Cold filters** click at the start of a processed segment. Warm-up.
15. **Chirp formulas.** Integrate the frequency.
16. **Randomness.** Seeded per cue index, never `np.random.random()`.
17. **Brightness.** Everything bright at once sounds cheap; the `tilt` setting removes part of the content above 6.5 kHz (a taste default, not a measured fix).

## Mix

18. **A flat bed.** Without the arc the music reads as wallpaper.
19. **Over-limiting.** Fixing a loud mix with the limiter instead of the cues. Read the loudest-frames list.
20. **Pre-limiter peaks at +1.7 dBTP** at a chord that coincided with a kick, a bass note and an impact (match at proof frame ~656): trimmed gains there; the pre-limiter peak is now +0.8 dBTP.
21. **Ducking depth too low** leaves focal events barely over the bed; check the focal-over-bed median in the quality output.
22. **Loudness target on the wrong stem.** Measure the mix, not the effects.

## Muxing

23. **AAC priming delay.** Check the decoded lag (the example decodes at 0 samples). A player that ignores edit lists may shift the sound.
24. **Different durations.** Read stream durations and start times in `mux_check.json`; the mux does not pad or trim.
25. **Video re-encoding.** Never. `-c:v copy`. If the video needs a change, it goes back to the picture's author.

## Process

26. **Nudging numbers.** If the cue is 3 frames off, find out why (is the constant wrong? is the element hidden?) before changing it. Write the reason in the comment.
27. **Believing the cue sheet.** It is the plan. The audit is the evidence.
28. **Skipping the listen.** The numbers are necessary and not sufficient. See 07.
29. **Overfitting to the audit.** Moving a cue to pass a check when the picture does not show the thing at that frame.
30. **Platform guesses.** Loudness targets change; check the current guidance of the platform you deliver to.
