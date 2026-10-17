# 09. Voice-over and external sound sources

The engine synthesises everything itself. Voice is the one thing it does not do. This note says how to add a voice-over or sampled sound without breaking the guarantees (frame accuracy, loudness, determinism).

**Status: untested.** No voice-over has been produced with this skill. The notes below describe a design, not something that was run. Check the current documentation of whichever text-to-speech service you use; model names, parameters and licence terms change.

## Principles

1. **The script is part of the picture.** Voice-over is timed by the script, not the other way round. If the video has captions, the script is the captions; if not, write the script from the fact ledger and keep one idea per sentence.
2. **A voice line is a cue.** Its start frame comes from the picture (a scene's first caption, an element appearing), and its duration comes from the audio file. A `voice` cue type does not exist yet; add one through `HANDLERS` in `cues.py` (parameters `file`, `frame`, `gain`) that loads the file and calls `rig.emit(sig, frame, gain, 0, tier=1)`.
3. **Measure the real duration before timing the picture.** Generate the lines first, read their durations, and set the scene lengths in `timeline.json` from them (a two-pass process: audio then picture). If the picture is already fixed, fit the line to the window by rewriting the text, not by time-stretching.
4. **Ducking.** A voice cue is tier 1 and ducks the music by `duck_db`; consider a deeper duck (8 to 10 dB) and a high-pass at 120 Hz on the music while the voice speaks, so that speech is intelligible on a phone.
5. **Loudness.** Measure the voice stem alone; target -16 to -18 LUFS integrated on the voice, and let the mix reach the platform target. A voice that is 6 dB under the effects is unintelligible.
6. **Determinism.** Cache generated files in `assets/voice/` keyed on a hash of text + voice id + settings, commit them or document how to regenerate; never call a network service in `build`.

## Services (not tested here)

- A hosted text-to-speech API such as ElevenLabs can produce natural speech; you need an API key (never committed; environment variable), you must read the current licence for commercial use and attribution, and output may change between model versions. The natural place to use it is a separate script `tools/voice.py` that writes `assets/voice/*.mp3` and a JSON with durations; the engine reads files only.
- A local engine avoids keys and cost but quality varies; check its licence.
- A human recording is the best option for anything important.

## Sync of a voice with the picture

- Word-level sync (a highlighted word as it is spoken) needs word timestamps; many TTS APIs can return alignments. If you have them, treat them as data like the scene constants and write them to a JSON the picture reads (the sound drives the picture here). Do not estimate them.
- Sentence-level sync is enough for explainers: the line starts when the scene's key element appears, ends before the next scene's wipe.
- Audit: there is nothing to measure in the video for a voice; compare each file's duration with its window yourself.

## Sound effects from files

If you must use a sampled sound, load it as a voice with the same rules: peak normalise, 4 ms fade, resample to 48 kHz with `scipy.signal.resample_poly`, record the licence in `CREDITS.md`, and put the file in `assets/`. Do not download assets at build time.

## Music from outside

A licensed track can replace `music.py`. Then the cue sheet must be timed to the track's beats: detect tempo and downbeats (a fixed tempo can be set by hand), and make the picture cuts land on bars; the engine's `beats()` helper takes a grid so you can pass the track's. Remember the licence for the platform you publish on.
