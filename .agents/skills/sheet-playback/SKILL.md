---
name: sheet-playback
description: Use when working in the SightReader repo to convert sheet music PDFs, MusicXML, MXL, or MIDI files into playable audio with Audiveris, MuseScore, FluidSynth, SoundFonts, and macOS playback.
---

# Sheet Playback

Use this skill in the SightReader repository when the user wants Codex to play,
render, inspect, or debug sheet music playback from PDF, MusicXML, MXL, or MIDI.

## Workflow

1. Run `sightreader doctor` first to check local tool availability.
2. If the input is PDF, require Audiveris for OMR and export to MusicXML/MXL.
3. If the input is MusicXML/MXL, require MuseScore to export MIDI.
4. If the user requests a specific instrument, use General MIDI names such as
   `piano`, `alto-sax`, `tenor-sax`, `baritone-sax`, `trumpet`, or `tuba`.
5. Require FluidSynth and `SIGHTREADER_SOUNDFONT` to render MIDI to WAV.
6. Use `--dry-run` before running an unfamiliar score or environment.
7. Use `--play` only when the user wants local audio playback.

## Commands

Check setup:

```sh
sightreader doctor
```

Plan a PDF conversion:

```sh
sightreader play /path/to/score.pdf --instrument tenor-sax --dry-run
```

Render and play:

```sh
sightreader play /path/to/score.pdf --instrument tenor-sax --play
```

## Boundaries

- Do not claim OMR output is correct without inspecting or validating it.
- Treat handwritten scores, poor scans, repeats, tuplets, and multi-voice piano
  writing as higher-risk inputs.
- If Audiveris, MuseScore, FluidSynth, or a SoundFont is missing, explain the
  missing dependency and stop before pretending playback succeeded.
