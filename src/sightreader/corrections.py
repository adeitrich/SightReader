from __future__ import annotations

import json
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[2]
CORRECTIONS_ROOT = ROOT / "corrections"


def apply_score_corrections(score_path: Path, source_stem: str) -> list[str]:
    correction_path = CORRECTIONS_ROOT / f"{source_stem}.json"
    if not correction_path.exists():
        return []

    corrections = json.loads(correction_path.read_text())
    applied: list[str] = []

    if score_path.suffix.lower() == ".mxl":
        applied.extend(_apply_mxl_corrections(score_path, corrections))
    elif score_path.suffix.lower() in {".xml", ".musicxml"}:
        applied.extend(_apply_xml_corrections(score_path, corrections))
    else:
        raise ValueError(f"cannot apply corrections to {score_path}")

    return applied


def _apply_mxl_corrections(score_path: Path, corrections: dict) -> list[str]:
    with ZipFile(score_path) as source:
        names = source.namelist()
        xml_name = _find_score_xml_name(names)
        xml_bytes = source.read(xml_name)
        updated_xml, applied = _apply_xml_bytes(xml_bytes, corrections)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mxl") as tmp:
            tmp_path = Path(tmp.name)

        try:
            with ZipFile(tmp_path, "w", ZIP_DEFLATED) as target:
                for name in names:
                    data = updated_xml if name == xml_name else source.read(name)
                    target.writestr(name, data)
            tmp_path.replace(score_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    return applied


def _apply_xml_corrections(score_path: Path, corrections: dict) -> list[str]:
    updated_xml, applied = _apply_xml_bytes(score_path.read_bytes(), corrections)
    score_path.write_bytes(updated_xml)
    return applied


def _apply_xml_bytes(xml_bytes: bytes, corrections: dict) -> tuple[bytes, list[str]]:
    root = ET.fromstring(xml_bytes)
    applied: list[str] = []
    for operation in corrections.get("operations", []):
        action = operation.get("action")
        note = _find_note(root, operation.get("match", {}))
        if note is None:
            raise ValueError(f"correction did not match any note: {operation}")

        if action == "set_pitch":
            _set_pitch(note, operation)
        elif action == "add_tie":
            _add_tie(note, operation["type"])
        else:
            raise ValueError(f"unknown correction action: {action}")
        applied.append(operation.get("description") or action)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True), applied


def _find_score_xml_name(names: list[str]) -> str:
    for name in names:
        if name.lower().endswith((".xml", ".musicxml")) and not name.startswith(
            "META-INF/"
        ):
            return name
    raise ValueError("MXL archive does not contain a score XML file")


def _find_note(root: ET.Element, match: dict) -> ET.Element | None:
    measure_number = str(match["measure"])
    matches = []
    for measure in root.iter("measure"):
        if measure.attrib.get("number") != measure_number:
            continue
        for note in measure.findall("note"):
            if _note_matches(note, match):
                matches.append(note)
    if len(matches) > 1:
        raise ValueError(f"correction matched multiple notes: {match}")
    return matches[0] if matches else None


def _note_matches(note: ET.Element, match: dict) -> bool:
    pitch = note.find("pitch")
    if pitch is None:
        return False

    expected_x = match.get("default_x")
    if expected_x is not None:
        actual_x = float(note.attrib.get("default-x", "nan"))
        if abs(actual_x - float(expected_x)) > float(match.get("x_tolerance", 1)):
            return False

    for field in ("step", "octave", "alter"):
        if field not in match:
            continue
        child = pitch.find(field)
        actual = child.text if child is not None else None
        if actual != str(match[field]):
            return False

    if "duration" in match:
        duration = note.find("duration")
        if duration is None or duration.text != str(match["duration"]):
            return False

    if "type" in match:
        note_type = note.find("type")
        if note_type is None or note_type.text != str(match["type"]):
            return False

    return True


def _set_pitch(note: ET.Element, operation: dict) -> None:
    pitch = note.find("pitch")
    if pitch is None:
        raise ValueError("cannot set pitch on a rest")

    _set_child_text(pitch, "step", operation["step"])
    if "alter" in operation:
        _set_child_text(pitch, "alter", operation["alter"], after="step")
    else:
        alter = pitch.find("alter")
        if alter is not None:
            pitch.remove(alter)
    _set_child_text(pitch, "octave", operation["octave"])

    accidental = note.find("accidental")
    if "accidental" in operation:
        if accidental is None:
            accidental = ET.Element("accidental")
            _insert_after(note, accidental, "type")
        accidental.text = str(operation["accidental"])
    elif accidental is not None:
        note.remove(accidental)


def _add_tie(note: ET.Element, tie_type: str) -> None:
    if not any(tie.attrib.get("type") == tie_type for tie in note.findall("tie")):
        tie = ET.Element("tie", {"type": tie_type})
        _insert_after(note, tie, "duration")

    notations = note.find("notations")
    if notations is None:
        notations = ET.Element("notations")
        note.append(notations)
    if not any(tied.attrib.get("type") == tie_type for tied in notations.findall("tied")):
        notations.append(ET.Element("tied", {"type": tie_type}))


def _set_child_text(
    parent: ET.Element, tag: str, value: object, after: str | None = None
) -> None:
    child = parent.find(tag)
    if child is None:
        child = ET.Element(tag)
        if after:
            _insert_after(parent, child, after)
        else:
            parent.append(child)
    child.text = str(value)


def _insert_after(parent: ET.Element, child: ET.Element, after_tag: str) -> None:
    children = list(parent)
    for index, existing in enumerate(children):
        if existing.tag == after_tag:
            parent.insert(index + 1, child)
            return
    parent.append(child)
