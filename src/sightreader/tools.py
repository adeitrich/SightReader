from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ToolSet:
    audiveris: str | None
    musescore: str | None
    fluidsynth: str | None
    soundfont: str | None
    player: str | None


def find_tools() -> ToolSet:
    return ToolSet(
        audiveris=_from_env_or_path("SIGHTREADER_AUDIVERIS", ["audiveris"]),
        musescore=_from_env_or_path(
            "SIGHTREADER_MUSESCORE",
            ["musescore", "musescore4", "mscore"],
        ),
        fluidsynth=_from_env_or_path("SIGHTREADER_FLUIDSYNTH", ["fluidsynth"]),
        soundfont=_find_soundfont(),
        player=_from_env_or_path("SIGHTREADER_PLAYER", ["afplay", "open"]),
    )


def doctor_report() -> str:
    tools = find_tools()
    rows = [
        ("Audiveris", tools.audiveris, "PDF -> MusicXML"),
        ("MuseScore", tools.musescore, "MusicXML -> MIDI"),
        ("FluidSynth", tools.fluidsynth, "MIDI -> WAV"),
        ("SoundFont", tools.soundfont, "instrument samples"),
        ("Player", tools.player, "local audio playback"),
    ]

    lines = ["SightReader tool check:"]
    for name, value, purpose in rows:
        status = value if value else "missing"
        lines.append(f"  {name:10} {status} ({purpose})")

    if not tools.soundfont:
        lines.append("")
        lines.append("Set SIGHTREADER_SOUNDFONT to a General MIDI .sf2 or .sf3 file.")

    return "\n".join(lines)


def _from_env_or_path(env_name: str, candidates: list[str]) -> str | None:
    env_value = os.environ.get(env_name)
    if env_value:
        expanded = str(Path(env_value).expanduser())
        return expanded if Path(expanded).exists() else env_value

    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    return None


def _find_soundfont() -> str | None:
    env_value = os.environ.get("SIGHTREADER_SOUNDFONT")
    if env_value:
        return str(Path(env_value).expanduser())

    candidates = [
        "/usr/local/share/soundfonts/FluidR3_GM.sf2",
        "/opt/homebrew/share/soundfonts/FluidR3_GM.sf2",
        "/usr/share/sounds/sf2/FluidR3_GM.sf2",
        "/usr/share/soundfonts/FluidR3_GM.sf2",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None
