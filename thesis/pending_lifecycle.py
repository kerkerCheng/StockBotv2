"""Thesis lifecycle 變更的待核准提案層。

為什麼需要這一層：`crons/daily_brief_prompt.md` 要求「若結果需要 thesis revise／
retire，完整 packet 回 pq2」，但在 2026-08-06 之前那句話沒有鑄號機制——
`thesis_lifecycle` 型別的 pq2 只由到期檢查產生（「這條 thesis 該複查了」），研究
結論想主張「這條 thesis 該退場」時沒有任何路徑，`lifecycle.json` 也只是一個可以
直接手改的 tracked JSON。

本模組與 `engine_c/pending_observations.py` 同形：提案是 content-addressed 的凍結
物件，進統一待辦池取得編號，使用者核准該 exact 編號後才由
`engine_b.todo complete-thesis-mutation` 寫入 lifecycle.json。

狀態機依 AGENTS.md L7（thesis 生命週期）。`retired` 是終局；要復活必須重新建立
thesis，而不是把已 retire 的狀態改回來——那會讓「為什麼當時退場」的紀錄失去對象。
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

ROOT = Path(__file__).resolve().parent.parent
LIFECYCLE_PATH = ROOT / "thesis" / "lifecycle.json"
PENDING_DIR = ROOT / "library" / "private" / "thesis_mutations"
PROPOSAL_SCHEMA = "thesis-lifecycle-proposal/v1"

# L7 的生命週期狀態機。開啟它等於改變 thesis 的語意，不是補字彙。
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "active": frozenset({"watch", "review_required"}),
    "watch": frozenset({"active", "review_required"}),
    "review_required": frozenset({"retired", "revised"}),
    "revised": frozenset({"active"}),
    "retired": frozenset(),
}


class ThesisMutationError(ValueError):
    """提案內容不合法、狀態轉移不被允許，或狀態已改變。"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _path(proposal_id: str) -> Path:
    if not proposal_id.startswith("tm_") or not proposal_id[3:].isalnum():
        raise ThesisMutationError(f"非法 proposal_id：{proposal_id}")
    return PENDING_DIR / f"{proposal_id}.json"


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


def load_lifecycle(path: Path | None = None) -> dict[str, Any]:
    target = Path(path or LIFECYCLE_PATH)
    return json.loads(target.read_text(encoding="utf-8"))


def propose(
    *,
    thesis_id: str,
    to_status: str,
    rationale: str,
    evidence_refs: list[str] | tuple[str, ...],
    author: str,
    next_check: str | None = None,
    lifecycle_path: Path | None = None,
) -> dict[str, Any]:
    """建立一筆待核准的 lifecycle 變更提案。

    提案凍結「當下的 from_status」：核准時若實際狀態已經不同，就代表期間有別的
    變更發生，必須重新評估而不是照舊套用。
    """

    lifecycle = load_lifecycle(lifecycle_path)
    entry = lifecycle.get(thesis_id)
    if not isinstance(entry, dict):
        raise ThesisMutationError(f"lifecycle.json 沒有 thesis：{thesis_id}")
    from_status = str(entry.get("status") or "")
    allowed = ALLOWED_TRANSITIONS.get(from_status)
    if allowed is None:
        raise ThesisMutationError(f"未知的現行狀態：{from_status}")
    if to_status not in allowed:
        raise ThesisMutationError(
            f"不允許的轉移 {from_status} → {to_status}"
            f"（可用：{sorted(allowed) or '（終局狀態）'}）"
        )
    refs = [str(ref).strip() for ref in evidence_refs if str(ref).strip()]
    if not refs:
        raise ThesisMutationError("lifecycle 變更必須附至少一個 evidence ref")
    if not rationale.strip():
        raise ThesisMutationError("lifecycle 變更必須附理由")

    payload = {
        "thesis_id": thesis_id,
        "from_status": from_status,
        "to_status": to_status,
        "rationale": rationale.strip(),
        "evidence_refs": sorted(refs),
        "author": author.strip(),
        "next_check": next_check,
    }
    digest = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    proposal_id = "tm_" + digest[:32]
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
    if not PENDING_DIR.exists():
        return
    for path in sorted(PENDING_DIR.glob("tm_*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if record.get("state") == "pending":
            yield record


def apply_proposal(
    proposal_id: str, *, lifecycle_path: Path | None = None
) -> dict[str, Any]:
    """核准後寫入 lifecycle.json；from_status 不符即拒絕，不做盲目覆寫。"""

    record = read(proposal_id)
    if record is None:
        raise ThesisMutationError(f"找不到提案 {proposal_id}")
    if record.get("state") != "pending":
        raise ThesisMutationError(f"提案 {proposal_id} 已是 {record.get('state')}")

    target = Path(lifecycle_path or LIFECYCLE_PATH)
    lifecycle = load_lifecycle(target)
    payload = record["payload"]
    entry = lifecycle.get(payload["thesis_id"])
    if not isinstance(entry, dict):
        raise ThesisMutationError(f"lifecycle.json 沒有 thesis：{payload['thesis_id']}")
    current = str(entry.get("status") or "")
    if current != payload["from_status"]:
        raise ThesisMutationError(
            f"狀態已改變（提案時 {payload['from_status']}，現在 {current}）；請重新評估"
        )

    entry["status"] = payload["to_status"]
    entry["last_checked"] = datetime.now(timezone.utc).date().isoformat()
    if payload.get("next_check"):
        entry["next_check"] = payload["next_check"]
    # append-only 稽核軌跡留在 entry 自己身上：為什麼變、憑什麼變、誰核准的。
    history = entry.setdefault("mutations", [])
    history.append({
        "at": _now(),
        "from": payload["from_status"],
        "to": payload["to_status"],
        "rationale": payload["rationale"],
        "evidence_refs": payload["evidence_refs"],
        "author": payload["author"],
        "proposal_id": proposal_id,
    })
    target.write_text(
        json.dumps(lifecycle, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    record["state"] = "applied"
    record["resolved_at"] = _now()
    _write(record)
    return {"thesis_id": payload["thesis_id"], "status": payload["to_status"]}
