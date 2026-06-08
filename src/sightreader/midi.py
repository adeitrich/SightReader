from __future__ import annotations

import struct
from pathlib import Path


def _read_vlq(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    while True:
        byte = data[offset]
        offset += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, offset


def _write_vlq(value: int) -> bytes:
    buffer = value & 0x7F
    value >>= 7
    while value:
        buffer <<= 8
        buffer |= (value & 0x7F) | 0x80
        value >>= 7

    output = bytearray()
    while True:
        output.append(buffer & 0xFF)
        if buffer & 0x80:
            buffer >>= 8
        else:
            return bytes(output)


def _skip_event(data: bytes, offset: int, status: int) -> tuple[int, int]:
    if status == 0xFF:
        offset += 1
        length, offset = _read_vlq(data, offset)
        return offset + length, status

    if status in (0xF0, 0xF7):
        length, offset = _read_vlq(data, offset)
        return offset + length, status

    event_type = status & 0xF0
    data_len = 1 if event_type in (0xC0, 0xD0) else 2
    return offset + data_len, status


def _channel_used(track: bytes, channel: int) -> bool:
    offset = 0
    running_status: int | None = None

    while offset < len(track):
        _, offset = _read_vlq(track, offset)
        if offset >= len(track):
            return False

        status = track[offset]
        if status & 0x80:
            offset += 1
            running_status = status
        elif running_status is not None:
            status = running_status
        else:
            return False

        if 0x80 <= status <= 0xEF and (status & 0x0F) == channel:
            return True

        offset, running_status = _skip_event(track, offset, status)

    return False


def _rewrite_track_programs(track: bytes, program: int) -> bytes:
    output = bytearray()
    prefix = bytearray()
    for channel in range(16):
        if channel == 9:
            continue
        if _channel_used(track, channel):
            prefix.extend((0x00, 0xC0 | channel, program))

    offset = 0
    running_status: int | None = None
    pending_delta = 0

    while offset < len(track):
        delta, offset = _read_vlq(track, offset)
        pending_delta += delta
        if offset >= len(track):
            break

        status = track[offset]
        if status & 0x80:
            offset += 1
            running_status = status
        elif running_status is not None:
            status = running_status
        else:
            raise ValueError("MIDI event is missing running status")

        if status == 0xFF:
            meta_type = track[offset]
            offset += 1
            length, offset = _read_vlq(track, offset)
            payload = track[offset : offset + length]
            offset += length
            output.extend(_write_vlq(pending_delta))
            output.extend((status, meta_type))
            output.extend(_write_vlq(length))
            output.extend(payload)
            pending_delta = 0
            continue

        if status in (0xF0, 0xF7):
            length, offset = _read_vlq(track, offset)
            payload = track[offset : offset + length]
            offset += length
            output.extend(_write_vlq(pending_delta))
            output.append(status)
            output.extend(_write_vlq(length))
            output.extend(payload)
            pending_delta = 0
            continue

        event_type = status & 0xF0
        channel = status & 0x0F
        data_len = 1 if event_type in (0xC0, 0xD0) else 2
        payload = track[offset : offset + data_len]
        offset += data_len

        if event_type == 0xC0 and channel != 9:
            continue

        output.extend(_write_vlq(pending_delta))
        output.append(status)
        output.extend(payload)
        pending_delta = 0

    return bytes(prefix) + bytes(output)


def set_single_instrument(input_path: Path, output_path: Path, program: int) -> None:
    """Write a MIDI copy that forces non-drum channels to one GM program."""

    data = input_path.read_bytes()
    if data[:4] != b"MThd":
        raise ValueError(f"{input_path} is not a standard MIDI file")

    header_length = struct.unpack(">I", data[4:8])[0]
    cursor = 8 + header_length
    output = bytearray(data[:cursor])

    while cursor < len(data):
        if data[cursor : cursor + 4] != b"MTrk":
            raise ValueError(f"unexpected MIDI chunk at byte {cursor}")

        length = struct.unpack(">I", data[cursor + 4 : cursor + 8])[0]
        track_start = cursor + 8
        track = data[track_start : track_start + length]
        cursor = track_start + length

        new_track = _rewrite_track_programs(track, program)
        output.extend(b"MTrk")
        output.extend(struct.pack(">I", len(new_track)))
        output.extend(new_track)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output)
