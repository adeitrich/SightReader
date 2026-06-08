from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


SOURCE_URI_RE = re.compile(r"/URI\(textedit://([^:)]+\.ly):(\d+):(\d+):(\d+)\)")


@dataclass(frozen=True)
class PdfInspection:
    path: Path
    pages: str | None
    title: str | None
    creator: str | None
    source_files: tuple[str, ...]


def inspect_pdf(path: Path) -> PdfInspection:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(resolved)
    if resolved.suffix.lower() != ".pdf":
        raise ValueError(f"expected a PDF file: {resolved}")

    metadata = _read_mdls(resolved)
    source_files = _extract_lilypond_source_files(resolved)
    return PdfInspection(
        path=resolved,
        pages=metadata.get("kMDItemNumberOfPages"),
        title=metadata.get("kMDItemTitle"),
        creator=metadata.get("kMDItemCreator"),
        source_files=tuple(source_files),
    )


def format_pdf_inspection(inspection: PdfInspection) -> str:
    lines = [f"PDF: {inspection.path}"]
    lines.append(f"  pages:   {inspection.pages or 'unknown'}")
    lines.append(f"  title:   {inspection.title or 'unknown'}")
    lines.append(f"  creator: {inspection.creator or 'unknown'}")
    if inspection.source_files:
        lines.append("  LilyPond source references:")
        for source_file in inspection.source_files:
            lines.append(f"    {source_file}")
    else:
        lines.append("  LilyPond source references: none found")
    return "\n".join(lines)


def _read_mdls(path: Path) -> dict[str, str]:
    command = [
        "mdls",
        "-name",
        "kMDItemCreator",
        "-name",
        "kMDItemTitle",
        "-name",
        "kMDItemNumberOfPages",
        str(path),
    ]
    result = subprocess.run(command, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        return {}

    metadata: dict[str, str] = {}
    for line in result.stdout.splitlines():
        key, _, raw_value = line.partition("=")
        value = raw_value.strip()
        if value == "(null)":
            value = ""
        metadata[key.strip()] = value.strip('"')
    return metadata


def _extract_lilypond_source_files(path: Path) -> list[str]:
    result = subprocess.run(
        ["strings", "-n", "4", str(path)],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return []

    files = set()
    for match in SOURCE_URI_RE.finditer(result.stdout):
        files.add(match.group(1))
    return sorted(files)
