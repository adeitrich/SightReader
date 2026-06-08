# SightReader

SightReader is a local tool for turning sheet music into playable audio from
Codex. The first target workflow is:

```text
PDF sheet music -> MusicXML -> MIDI -> WAV -> playback
```

The project intentionally keeps the first implementation small. It orchestrates
existing music tools instead of trying to build optical music recognition or
instrument synthesis from scratch.

## Current Status

This repo contains an early command-line scaffold:

- `sightreader doctor` checks for required local tools.
- `sightreader play score.pdf` plans or runs the PDF-to-audio pipeline.
- `sightreader play score.musicxml --instrument tuba --play` renders and plays a score when the required tools are installed.
- `.agents/skills/sheet-playback/SKILL.md` lets Codex reuse the workflow in this repo.

## External Tools

SightReader expects command-line tools to be installed separately:

- Audiveris: converts scanned or exported sheet music PDFs to MusicXML.
- MuseScore Studio: converts MusicXML to MIDI or audio.
- FluidSynth plus a General MIDI SoundFont: renders MIDI as instruments like saxophone or tuba.
- `afplay`: macOS audio playback, already present on most Macs.

The CLI detects tools from `PATH`, or from these environment variables:

```sh
export SIGHTREADER_AUDIVERIS=/path/to/audiveris
export SIGHTREADER_MUSESCORE=/path/to/musescore
export SIGHTREADER_FLUIDSYNTH=/path/to/fluidsynth
export SIGHTREADER_SOUNDFONT=/path/to/GeneralUser.sf2
```

## Quick Start

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
sightreader doctor
```

Plan a run without executing external tools:

```sh
sightreader play path/to/score.pdf --instrument tenor-sax --dry-run
```

Render and play once tools are installed:

```sh
sightreader play path/to/score.pdf --instrument tenor-sax --play
```

## Roadmap

1. Make the PDF -> MusicXML -> MIDI -> WAV path reliable on macOS.
2. Add better installation discovery for Audiveris and MuseScore app bundles.
3. Add a small drag-and-drop local web UI.
4. Add score preview, measure-level diagnostics, and OMR correction hints.
5. Add singing voice synthesis as a separate backend after instrumental playback works.
