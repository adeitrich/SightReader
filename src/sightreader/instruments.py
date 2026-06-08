from __future__ import annotations


# General MIDI program numbers are stored as zero-based values in MIDI files.
GENERAL_MIDI_PROGRAMS = {
    "piano": 0,
    "acoustic-grand-piano": 0,
    "bright-piano": 1,
    "electric-piano": 4,
    "organ": 16,
    "guitar": 24,
    "violin": 40,
    "cello": 42,
    "contrabass": 43,
    "trumpet": 56,
    "trombone": 57,
    "tuba": 58,
    "french-horn": 60,
    "soprano-sax": 64,
    "alto-sax": 65,
    "tenor-sax": 66,
    "baritone-sax": 67,
    "oboe": 68,
    "clarinet": 71,
    "flute": 73,
}


def normalize_instrument(name: str) -> str:
    return name.strip().lower().replace("_", "-").replace(" ", "-")


def program_for_instrument(name: str) -> int:
    key = normalize_instrument(name)
    if key not in GENERAL_MIDI_PROGRAMS:
        choices = ", ".join(sorted(GENERAL_MIDI_PROGRAMS))
        raise ValueError(f"unknown instrument {name!r}; choose one of: {choices}")
    return GENERAL_MIDI_PROGRAMS[key]
