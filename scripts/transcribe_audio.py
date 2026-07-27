"""Local-first timestamped transcription for source tracing.

Inference runs locally with faster-whisper. Model weights are downloaded once
and cached under ignored ``library/private/``. Full transcripts are always
stored as local-only research material and never promoted to evidence by this
tool alone.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit

import requests


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_CACHE = ROOT / "library" / "private" / "models" / "faster-whisper"
DEFAULT_OUTPUT_DIR = ROOT / "library" / "private" / "transcripts"


def format_timestamp(seconds: float) -> str:
    total_ms = max(0, round(float(seconds) * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"


def safe_source(value: str) -> str:
    """Strip URL credentials/query/fragment before persisting provenance."""

    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        return str(Path(value).resolve())
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_audio(url: str, destination: Path, *, max_bytes: int) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("audio URL must use http or https")
    written = 0
    with requests.get(url, stream=True, timeout=(15, 60)) as response:
        response.raise_for_status()
        length = response.headers.get("content-length")
        if length and int(length) > max_bytes:
            raise ValueError("audio download exceeds configured size limit")
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                written += len(chunk)
                if written > max_bytes:
                    raise ValueError("audio download exceeds configured size limit")
                handle.write(chunk)


def build_payload(
    *,
    source: str,
    audio_sha256: str,
    model: str,
    device: str,
    compute_type: str,
    language: str | None,
    language_probability: float | None,
    duration_seconds: float | None,
    segments: Iterable[Any],
) -> dict[str, Any]:
    rows = []
    for segment in segments:
        start = float(segment.start)
        end = float(segment.end)
        rows.append({
            "start_seconds": start,
            "end_seconds": end,
            "start_timestamp": format_timestamp(start),
            "end_timestamp": format_timestamp(end),
            "text": str(segment.text).strip(),
        })
    return {
        "schema_version": "1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": safe_source(source),
        "audio_sha256": audio_sha256,
        "engine": "faster-whisper",
        "model": model,
        "device": device,
        "compute_type": compute_type,
        "language": language,
        "language_probability": language_probability,
        "duration_seconds": duration_seconds,
        "storage_permission": "local_only",
        "evidence_status": "asr_locator_only",
        "evidence_note": (
            "AI transcription locates candidate passages; verify technical terms "
            "against the timestamped audio before using an exact quote."
        ),
        "segments": rows,
        "text": " ".join(row["text"] for row in rows if row["text"]),
    }


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run local timestamped speech recognition for source tracing."
    )
    parser.add_argument("input", help="Local audio path or direct http(s) audio URL")
    parser.add_argument("--model", default="small.en")
    parser.add_argument("--language", default="en", help="Language code or 'auto'")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--compute-type", default=None)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model-cache", type=Path, default=DEFAULT_MODEL_CACHE)
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--max-download-mb", type=int, default=500)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    compute_type = args.compute_type or ("int8" if args.device == "cpu" else "float16")
    source = args.input
    parsed = urlsplit(source)
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    if parsed.scheme in {"http", "https"}:
        temp_dir = tempfile.TemporaryDirectory(prefix="stockbot-audio-")
        suffix = Path(parsed.path).suffix or ".audio"
        audio_path = Path(temp_dir.name) / f"source{suffix}"
        download_audio(source, audio_path, max_bytes=args.max_download_mb * 1024 * 1024)
    else:
        audio_path = Path(source).expanduser().resolve()
        if not audio_path.is_file():
            raise FileNotFoundError(f"audio file not found: {audio_path}")

    try:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper is unavailable; install requirements.txt in .venv"
            ) from exc
        args.model_cache.mkdir(parents=True, exist_ok=True)
        model = WhisperModel(
            args.model,
            device=args.device,
            compute_type=compute_type,
            download_root=str(args.model_cache),
            local_files_only=args.local_files_only,
        )
        segments, info = model.transcribe(
            str(audio_path),
            language=None if args.language == "auto" else args.language,
            beam_size=5,
            vad_filter=True,
        )
        digest = sha256_file(audio_path)
        payload = build_payload(
            source=source,
            audio_sha256=digest,
            model=args.model,
            device=args.device,
            compute_type=compute_type,
            language=getattr(info, "language", None),
            language_probability=getattr(info, "language_probability", None),
            duration_seconds=getattr(info, "duration", None),
            segments=segments,
        )
        output = args.output or DEFAULT_OUTPUT_DIR / f"{digest[:16]}_{args.model}.json"
        output = output.expanduser().resolve()
        write_json_atomic(output, payload)
        print(json.dumps({
            "status": "ok",
            "output": str(output),
            "audio_sha256": digest,
            "segments": len(payload["segments"]),
            "duration_seconds": payload["duration_seconds"],
            "storage_permission": "local_only",
        }, ensure_ascii=False))
        return 0
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
