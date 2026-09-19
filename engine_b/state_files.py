"""Engine B 本機 authority 檔案集合與備份邊界。

這四份 JSON 是本機可變狀態，不再以 public Git 當同步／備份機制。路徑維持不變，
讓既有 producer/consumer 不需要多一套 storage adapter；本模組只集中定義：

- 哪四份檔案必須同時存在且可解析；
- pending leads 指名的 ``library/raw/`` provenance 檔案也必須一起備份。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


STATE_PATHS = (
    "library/leads/pending_leads.json",
    "library/leads/todo_pool.json",
    "library/leads/event_watches.json",
    "library/leads/hypotheses.json",
)
EVIDENCE_PREFIX = "library/raw/"

_REQUIRED_SHAPES: dict[str, dict[str, type]] = {
    STATE_PATHS[0]: {"leads": dict, "schema_version": str},
    STATE_PATHS[1]: {"items": list, "log": list, "next_n": int},
    STATE_PATHS[2]: {"watches": list, "schema_version": int},
    STATE_PATHS[3]: {"hypotheses": list, "schema_version": int},
}


class StateFileError(RuntimeError):
    """State 缺失、損毀或 provenance 引用不安全。"""


def _load_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StateFileError(f"無法解析 state：{path.as_posix()}") from exc
    if not isinstance(payload, dict):
        raise StateFileError(f"state 頂層不是 object：{path.as_posix()}")
    return payload


def validate_state_files(root: Path | str) -> list[dict[str, Any]]:
    """驗證四份 authority 並回傳可稽核的 digest；不修改任何檔案。"""
    repo = Path(root)
    result: list[dict[str, Any]] = []
    for relative in STATE_PATHS:
        path = repo / relative
        if not path.is_file():
            raise StateFileError(f"缺少 state：{relative}")
        payload = _load_object(path)
        for key, expected_type in _REQUIRED_SHAPES[relative].items():
            value = payload.get(key)
            # bool 是 int 的子類；next_n/schema_version 不接受 True/False。
            if not isinstance(value, expected_type) or (
                expected_type is int and isinstance(value, bool)
            ):
                raise StateFileError(
                    f"state 欄位型別錯誤：{relative}:{key}"
                )
        result.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return result


def raw_evidence_refs(payload: dict[str, Any]) -> tuple[str, ...]:
    """從 pending leads payload 推導合法的 raw provenance 路徑集合。"""
    found: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str):
            ref = node.strip().replace("\\", "/")
            if not ref.startswith(EVIDENCE_PREFIX):
                return
            if len(ref.split()) != 1 or ".." in ref or ref.endswith("/"):
                raise StateFileError(f"不安全的 raw evidence 引用：{ref}")
            found.add(ref)

    walk(payload.get("leads") or {})
    return tuple(sorted(found))


def referenced_raw_evidence(root: Path | str) -> tuple[str, ...]:
    """回傳 pending leads 指名的 raw provenance；缺檔或不安全路徑即 fail closed。"""
    repo = Path(root)
    payload = _load_object(repo / STATE_PATHS[0])
    refs = raw_evidence_refs(payload)
    for ref in refs:
        if not (repo / ref).is_file():
            raise StateFileError(f"raw evidence 引用不存在：{ref}")
    return refs


def backup_members(root: Path | str) -> tuple[str, ...]:
    """Engine B state archive 的完整、可重算成員集合。"""
    validate_state_files(root)
    return (*STATE_PATHS, *referenced_raw_evidence(root))
