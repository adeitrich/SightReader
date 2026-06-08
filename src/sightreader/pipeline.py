from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .instruments import program_for_instrument
from .midi import set_single_instrument
from .tools import ToolSet, find_tools


MUSICXML_SUFFIXES = {".xml", ".musicxml", ".mxl"}
MIDI_SUFFIXES = {".mid", ".midi"}


@dataclass(frozen=True)
class PlaybackOptions:
    input_path: Path
    instrument: str
    out_dir: Path
    play: bool = False
    dry_run: bool = False


@dataclass(frozen=True)
class PlaybackResult:
    summary: str
    audio_path: Path | None


def run_playback(options: PlaybackOptions) -> PlaybackResult:
    tools = find_tools()
    input_path = options.input_path.expanduser().resolve()
    if not input_path.exists():
        raise RuntimeError(f"input file does not exist: {input_path}")

    out_dir = options.out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem
    suffix = input_path.suffix.lower()

    commands: list[list[str]] = []

    if suffix == ".pdf":
        musicxml_path = out_dir / f"{stem}.mxl"
        audiveris = _require_or_placeholder(
            tools.audiveris,
            "Audiveris",
            "PDF to MusicXML conversion",
            options.dry_run,
        )
        commands.append(
            [
                audiveris,
                "-batch",
                "-transcribe",
                "-export",
                "-output",
                str(out_dir),
                "--",
                str(input_path),
            ]
        )
    elif suffix in MUSICXML_SUFFIXES:
        musicxml_path = input_path
    elif suffix in MIDI_SUFFIXES:
        musicxml_path = None
    else:
        raise RuntimeError(
            "unsupported input type; expected PDF, MusicXML/MXL, or MIDI file"
        )

    if suffix in MIDI_SUFFIXES:
        midi_path = input_path
    else:
        midi_path = out_dir / f"{stem}.mid"
        musescore = _require_or_placeholder(
            tools.musescore,
            "MuseScore",
            "MusicXML to MIDI conversion",
            options.dry_run,
        )
        commands.append([musescore, "-o", str(midi_path), str(musicxml_path)])

    program = program_for_instrument(options.instrument)
    instrument_midi_path = out_dir / f"{stem}-{options.instrument}.mid"
    audio_path = out_dir / f"{stem}-{options.instrument}.wav"

    if not options.dry_run:
        for command in commands:
            expected_output = midi_path if command[0] == tools.musescore else None
            if expected_output:
                expected_output.unlink(missing_ok=True)
            _run(command, expected_output=expected_output)
        if not midi_path.exists():
            raise RuntimeError(f"expected MIDI output was not created: {midi_path}")
        set_single_instrument(midi_path, instrument_midi_path, program)
    else:
        commands.append(
            [
                "python",
                "-m",
                "sightreader",
                "set-instrument",
                str(midi_path),
                str(instrument_midi_path),
                str(program),
            ]
        )

    fluidsynth = _require_or_placeholder(
        tools.fluidsynth,
        "FluidSynth",
        "MIDI to WAV rendering",
        options.dry_run,
    )
    if not tools.soundfont and not options.dry_run:
        raise RuntimeError(
            "no SoundFont found; set SIGHTREADER_SOUNDFONT to a .sf2 or .sf3 file"
        )
    soundfont = tools.soundfont or "<soundfont.sf2>"

    render_command = [
        fluidsynth,
        "-ni",
        "-F",
        str(audio_path),
        "-r",
        "44100",
        soundfont,
        str(instrument_midi_path),
    ]
    commands.append(render_command)

    if not options.dry_run:
        audio_path.unlink(missing_ok=True)
        _run(render_command)
        if not audio_path.exists():
            raise RuntimeError(f"expected audio output was not created: {audio_path}")

    if options.play:
        player = _require_or_placeholder(
            tools.player,
            "audio player",
            "local playback",
            options.dry_run,
        )
        play_command = [player, str(audio_path)]
        commands.append(play_command)
        if not options.dry_run:
            _run(play_command)

    return PlaybackResult(
        summary=_format_summary(commands, audio_path, options.dry_run),
        audio_path=audio_path,
    )


def _require_tool(value: str | None, name: str, purpose: str) -> None:
    if not value:
        raise RuntimeError(f"{name} is required for {purpose}, but was not found")


def _require_or_placeholder(
    value: str | None, name: str, purpose: str, dry_run: bool
) -> str:
    if value:
        return value
    if dry_run:
        return f"<{name.lower()}>"
    raise RuntimeError(f"{name} is required for {purpose}, but was not found")


def _run(command: list[str], expected_output: Path | None = None) -> None:
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        if expected_output and expected_output.exists():
            return
        quoted = " ".join(shlex.quote(part) for part in command)
        raise RuntimeError(f"command failed with exit code {exc.returncode}: {quoted}")


def _format_summary(commands: list[list[str]], audio_path: Path, dry_run: bool) -> str:
    lines = ["Planned commands:" if dry_run else "Completed commands:"]
    for command in commands:
        lines.append("  " + " ".join(shlex.quote(part) for part in command))
    lines.append(f"Audio output: {audio_path}")
    return "\n".join(lines)
