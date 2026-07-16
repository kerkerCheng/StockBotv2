"""Provider-independent Lane Memo transport helpers."""

from __future__ import annotations

import json

from thesis.generate_lane_memo import _atomic_write_pair, _parse_envelope


def test_parse_envelope_accepts_plain_json_and_outer_code_fence() -> None:
    payload = {"memo_markdown": "# Memo [E1]", "evidence_items": []}
    raw = json.dumps(payload)

    assert _parse_envelope(raw) == (payload, None)
    assert _parse_envelope(f"```json\n{raw}\n```") == (payload, None)


def test_parse_envelope_rejects_non_json() -> None:
    envelope, error = _parse_envelope("# Markdown only")

    assert envelope is None
    assert "valid JSON" in error


def test_atomic_write_pair_publishes_memo_and_sidecar(tmp_path) -> None:
    memo = tmp_path / "sample.md"

    sidecar = _atomic_write_pair(memo, "# Memo\n", {"ok": True})

    assert memo.read_text(encoding="utf-8") == "# Memo\n"
    assert json.loads(sidecar.read_text(encoding="utf-8")) == {"ok": True}
    assert not list(tmp_path.glob("*.tmp"))
