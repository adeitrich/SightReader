import struct
import tempfile
import unittest
from pathlib import Path

from sightreader.midi import set_single_instrument


def make_minimal_midi() -> bytes:
    header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, 480)
    track = bytes(
        [
            0x00,
            0x90,
            0x3C,
            0x40,
            0x81,
            0x70,
            0x80,
            0x3C,
            0x00,
            0x00,
            0xFF,
            0x2F,
            0x00,
        ]
    )
    return header + b"MTrk" + struct.pack(">I", len(track)) + track


def make_midi_with_program_change() -> bytes:
    header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, 480)
    track = bytes(
        [
            0x00,
            0xC0,
            53,
            0x00,
            0x90,
            0x3C,
            0x40,
            0x81,
            0x70,
            0x80,
            0x3C,
            0x00,
            0x00,
            0xFF,
            0x2F,
            0x00,
        ]
    )
    return header + b"MTrk" + struct.pack(">I", len(track)) + track


class MidiTests(unittest.TestCase):
    def test_set_single_instrument_inserts_program_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "input.mid"
            output_path = Path(tmp) / "output.mid"
            input_path.write_bytes(make_minimal_midi())

            set_single_instrument(input_path, output_path, 58)

            data = output_path.read_bytes()
            self.assertIn(bytes([0x00, 0xC0, 58]), data)
            self.assertTrue(data.startswith(b"MThd"))

    def test_set_single_instrument_removes_existing_program_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "input.mid"
            output_path = Path(tmp) / "output.mid"
            input_path.write_bytes(make_midi_with_program_change())

            set_single_instrument(input_path, output_path, 56)

            data = output_path.read_bytes()
            self.assertIn(bytes([0x00, 0xC0, 56]), data)
            self.assertNotIn(bytes([0x00, 0xC0, 53]), data)


if __name__ == "__main__":
    unittest.main()
