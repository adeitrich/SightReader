from __future__ import annotations

import cgi
import json
import mimetypes
import re
import threading
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .pipeline import PlaybackOptions, run_playback
from .tools import doctor_report


ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = ROOT / "web"
PDF_ROOT = ROOT / "PDF"
UPLOAD_ROOT = ROOT / "uploads"
OUT_ROOT = ROOT / "out"


class JobStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._next_id = 1
        self._jobs: dict[str, dict[str, object]] = {}

    def create(self, label: str) -> str:
        with self._lock:
            job_id = str(self._next_id)
            self._next_id += 1
            self._jobs[job_id] = {
                "id": job_id,
                "label": label,
                "status": "queued",
                "summary": "",
                "audioUrl": None,
                "error": None,
            }
            return job_id

    def update(self, job_id: str, **values: object) -> None:
        with self._lock:
            self._jobs[job_id].update(values)

    def get(self, job_id: str) -> dict[str, object] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None


JOBS = JobStore()


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    UPLOAD_ROOT.mkdir(exist_ok=True)
    OUT_ROOT.mkdir(exist_ok=True)
    server = ThreadingHTTPServer((host, port), SightReaderHandler)
    print(f"SightReader UI running at http://{host}:{port}")
    server.serve_forever()


class SightReaderHandler(BaseHTTPRequestHandler):
    server_version = "SightReaderHTTP/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_static(WEB_ROOT / "index.html")
        elif parsed.path.startswith("/static/"):
            self._send_static(WEB_ROOT / parsed.path.removeprefix("/static/"))
        elif parsed.path == "/api/doctor":
            self._send_json({"report": doctor_report()})
        elif parsed.path == "/api/pdfs":
            self._send_json({"pdfs": _list_pdfs()})
        elif parsed.path.startswith("/api/jobs/"):
            job_id = parsed.path.rsplit("/", 1)[-1]
            job = JOBS.get(job_id)
            if not job:
                self._send_json({"error": "job not found"}, status=404)
            else:
                self._send_json(job)
        elif parsed.path == "/files":
            query = parse_qs(parsed.query)
            rel_path = query.get("path", [""])[0]
            self._send_workspace_file(rel_path)
        else:
            self._send_json({"error": "not found"}, status=404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/render":
            self._send_json({"error": "not found"}, status=404)
            return

        try:
            render_request = self._parse_render_request()
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=400)
            return

        job_id = JOBS.create(render_request["label"])
        thread = threading.Thread(
            target=_render_job,
            args=(job_id, render_request["input_path"], render_request["instrument"]),
            daemon=True,
        )
        thread.start()
        self._send_json({"jobId": job_id})

    def log_message(self, format: str, *args: object) -> None:
        return

    def _parse_render_request(self) -> dict[str, object]:
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
            },
        )
        instrument = str(form.getfirst("instrument", "piano"))

        existing = form.getfirst("existingPdf")
        if existing:
            input_path = _safe_existing_pdf(str(existing))
            return {
                "input_path": input_path,
                "instrument": instrument,
                "label": input_path.name,
            }

        upload = form["file"] if "file" in form else None
        if not upload or not getattr(upload, "filename", ""):
            raise ValueError("choose a PDF file or bundled example")

        filename = _safe_filename(upload.filename)
        if not filename.lower().endswith(".pdf"):
            raise ValueError("only PDF uploads are supported")

        input_path = UPLOAD_ROOT / filename
        input_path.write_bytes(upload.file.read())
        return {"input_path": input_path, "instrument": instrument, "label": filename}

    def _send_static(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self._send_json({"error": "not found"}, status=404)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_workspace_file(self, rel_path: str) -> None:
        try:
            path = _safe_served_path(unquote(rel_path))
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=400)
            return
        self._send_static(path)

    def _send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _render_job(job_id: str, input_path: Path, instrument: str) -> None:
    JOBS.update(job_id, status="running")
    try:
        result = run_playback(
            PlaybackOptions(
                input_path=input_path,
                instrument=instrument,
                out_dir=OUT_ROOT,
                play=False,
                dry_run=False,
            )
        )
        audio_url = None
        if result.audio_path:
            audio_url = f"/files?path={result.audio_path.relative_to(ROOT)}"
        JOBS.update(
            job_id,
            status="complete",
            summary=result.summary,
            audioUrl=audio_url,
        )
    except Exception as exc:
        JOBS.update(job_id, status="failed", error=str(exc))


def _list_pdfs() -> list[dict[str, str]]:
    if not PDF_ROOT.exists():
        return []
    return [
        {
            "name": path.name,
            "path": str(path.relative_to(ROOT)),
            "url": f"/files?path={path.relative_to(ROOT)}",
        }
        for path in sorted(PDF_ROOT.glob("*.pdf"))
    ]


def _safe_existing_pdf(rel_path: str) -> Path:
    path = _safe_served_path(rel_path)
    if path.parent != PDF_ROOT.resolve() or path.suffix.lower() != ".pdf":
        raise ValueError("example PDF must come from the PDF folder")
    return path


def _safe_served_path(rel_path: str) -> Path:
    if not rel_path:
        raise ValueError("missing file path")
    path = (ROOT / rel_path).resolve()
    allowed_roots = [PDF_ROOT.resolve(), UPLOAD_ROOT.resolve(), OUT_ROOT.resolve()]
    if not any(path == root or root in path.parents for root in allowed_roots):
        raise ValueError("file is outside served folders")
    if not path.exists():
        raise ValueError("file does not exist")
    return path


def _safe_filename(filename: str) -> str:
    base = Path(filename).name
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", base).strip(".-")
    if not safe:
        raise ValueError("invalid filename")
    return safe
