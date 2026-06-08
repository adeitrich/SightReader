from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .instruments import program_for_instrument
from .midi import set_single_instrument
from .pipeline import PlaybackOptions, run_playback
from .tools import doctor_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sightreader",
        description="Convert sheet music files into playable audio.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("doctor", help="Check local tool availability.")

    play = subparsers.add_parser("play", help="Render a score to audio.")
    play.add_argument("input", type=Path, help="PDF, MusicXML, MXL, or MIDI file.")
    play.add_argument(
        "--instrument",
        default="piano",
        help="General MIDI instrument name, e.g. piano, tenor-sax, alto-sax, tuba.",
    )
    play.add_argument(
        "--out-dir",
        type=Path,
        default=Path("out"),
        help="Directory for generated files.",
    )
    play.add_argument(
        "--play",
        action="store_true",
        help="Play the rendered audio with the local audio player.",
    )
    play.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned commands without running them.",
    )

    set_instrument = subparsers.add_parser(
        "set-instrument",
        help="Write a MIDI copy with an initial General MIDI program change.",
    )
    set_instrument.add_argument("input", type=Path, help="Input MIDI file.")
    set_instrument.add_argument("output", type=Path, help="Output MIDI file.")
    set_instrument.add_argument(
        "instrument",
        help="Instrument name such as tuba, tenor-sax, or a zero-based GM program.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        print(doctor_report())
        return 0

    if args.command == "play":
        options = PlaybackOptions(
            input_path=args.input,
            instrument=args.instrument,
            out_dir=args.out_dir,
            play=args.play,
            dry_run=args.dry_run,
        )
        try:
            result = run_playback(options)
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

        print(result.summary)
        return 0

    if args.command == "set-instrument":
        try:
            program = int(args.instrument)
        except ValueError:
            try:
                program = program_for_instrument(args.instrument)
            except ValueError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 1
        try:
            set_single_instrument(args.input, args.output, program)
        except (OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"Wrote {args.output}")
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
