"""Engine C 人工觀測的待核准提案層。

為什麼需要這一層：`decision_lab` 的 gap research packet 明寫
`engine_c_manual_observation_requires_user_approval: true`，但在 2026-08-06 之前
那句話沒有任何程式實現——`engine_c/set_manual_field.py` 是唯一入口，寫下去就直接
落 append-only ledger，沒有編號、沒有核准、沒有收據鏈。對照 graph admission 有
完整的 prepare → pq2 編號 → 核准 → apply → receipt，Engine C 這一側是敞開的。

本模組提供 graph admission 的對應物：提案是 content-addressed 的凍結物件，進
統一待辦池取得編號，使用者核准該 exact 編號後才由 `engine_b.todo complete-observation`
執行實際 ledger 寫入。提案本身不是 authority——它只是等待核准的內容。
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

from engine_c.observation_fields import validate_field_name

ROOT = Path(__file__).resolve().parent.parent
PENDING_DIR = ROOT / "library" / "private" / "engine_c_observations"
PROPOSAL_SCHEMA = "engine-c-observation-proposal/v1"

_PAYLOAD_FIELDS = ("ticker", "field_name", "value", "source_ref", "as_of", "author")


class ProposalError(ValueError):
    """提案內容不合法，或狀態轉移不被允許。"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _path(proposal_id: str) -> Path:
    if not proposal_id.startswith("po_") or not proposal_id[3:].isalnum():
        raise ProposalError(f"非法 proposal_id：{proposal_id}")
    path = PENDING_DIR / f"{proposal_id}.json"
    if path.parent.resolve() != PENDING_DIR.resolve():
        raise ProposalError("proposal path escapes pending root")
    return path


def _write(record: Mapping[str, Any]) -> None:
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    path = _path(str(record["proposal_id"]))
    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent,
        prefix=f".{path.name}.", suffix=".tmp", delete=False,
    )
    temp = Path(handle.name)
    try:
        with handle:
            json.dump(record, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def propose(
    *,
    ticker: str,
    field_name: str,
    value: str,
    source_ref: str,
    as_of: str,
    author: str,
    supersedes_id: str | None = None,
) -> dict[str, Any]:
    """建立（或沿用）一筆待核准觀測提案。同內容重複提案不會產生第二個編號。"""

    spec = validate_field_name(field_name)
    payload = {
        "ticker": ticker.upper().strip(),
        "field_name": spec.field_name,
        "value": value.strip(),
        "source_ref": source_ref.strip(),
        "as_of": as_of.strip(),
        "author": author.strip(),
    }
    missing = [key for key in _PAYLOAD_FIELDS if not payload[key]]
    if missing:
        raise ProposalError(f"提案缺少必填欄位：{missing}")
    if supersedes_id is not None:
        payload["supersedes_id"] = str(supersedes_id).strip() or None

    digest = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    proposal_id = "po_" + digest[:32]
    path = _path(proposal_id)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    record = {
        "schema_version": PROPOSAL_SCHEMA,
        "proposal_id": proposal_id,
        "payload_digest": digest,
        "state": "pending",
        "created_at": _now(),
        "payload": payload,
        "observation_id": None,
        "resolved_at": None,
    }
    _write(record)
    return record


def read(proposal_id: str) -> dict[str, Any] | None:
    path = _path(proposal_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def iter_pending() -> Iterator[dict[str, Any]]:
    """只吐尚未落 ledger 的提案；已 applied／dropped 的保留在磁碟供稽核。"""

    if not PENDING_DIR.exists():
        return
    for path in sorted(PENDING_DIR.glob("po_*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if record.get("state") == "pending":
            yield record


def mark_applied(proposal_id: str, *, observation_id: str) -> dict[str, Any]:
    record = read(proposal_id)
    if record is None:
        raise ProposalError(f"找不到提案 {proposal_id}")
    if record.get("state") != "pending":
        raise ProposalError(f"提案 {proposal_id} 已是 {record.get('state')}，不可重複套用")
    record["state"] = "applied"
    record["observation_id"] = observation_id
    record["resolved_at"] = _now()
    _write(record)
    return record


def mark_dropped(proposal_id: str, *, reason: str) -> dict[str, Any]:
    record = read(proposal_id)
    if record is None:
        raise ProposalError(f"找不到提案 {proposal_id}")
    if record.get("state") != "pending":
        raise ProposalError(f"提案 {proposal_id} 已是 {record.get('state')}")
    record["state"] = "dropped"
    record["drop_reason"] = reason
    record["resolved_at"] = _now()
    _write(record)
    return record
