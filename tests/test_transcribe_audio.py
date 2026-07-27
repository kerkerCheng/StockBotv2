from __future__ import annotations

from types import SimpleNamespace

from scripts.transcribe_audio import build_payload, format_timestamp, safe_source


def test_timestamp_format_is_stable() -> None:
    assert format_timestamp(0) == "00:00:00.000"
    assert format_timestamp(65.4321) == "00:01:05.432"
    assert format_timestamp(3661.001) == "01:01:01.001"


def test_transcript_payload_is_local_only_and_timestamped() -> None:
    payload = build_payload(
        source="https://example.com/audio.mp3?secret=redacted#fragment",
        audio_sha256="a" * 64,
        model="small.en",
        device="cpu",
        compute_type="int8",
        language="en",
        language_probability=0.99,
        duration_seconds=12.5,
        segments=[SimpleNamespace(start=1.25, end=3.5, text="  optical engine  ")],
    )

    assert payload["source"] == "https://example.com/audio.mp3"
    assert payload["storage_permission"] == "local_only"
    assert payload["evidence_status"] == "asr_locator_only"
    assert payload["segments"] == [{
        "start_seconds": 1.25,
        "end_seconds": 3.5,
        "start_timestamp": "00:00:01.250",
        "end_timestamp": "00:00:03.500",
        "text": "optical engine",
    }]
    assert payload["text"] == "optical engine"


def test_safe_source_keeps_local_path_and_removes_url_credentials() -> None:
    assert safe_source("https://user:pass@example.com/a.mp3?token=x") == (
        "https://example.com/a.mp3"
    )
