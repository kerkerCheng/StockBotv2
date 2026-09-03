"""封閉字彙載入——`config/*.json` 是唯一權威，不在 Python 裡寫死第二份。

判準（`docs/solutions/architecture-patterns/closed-vocabulary-registry.md`）：
**taxonomy**（世界會長出新品類）→ 留鬆，住 `config/`；
**contract**（刻意有限，打開它是 bug）→ 鎖死，住 code 的 `Literal`。

`Catalyst.kind` 與 `StructuralEvent.kind` 是 taxonomy；`EvidenceRef.kind` 是 contract。

⚠ 只用標準庫。`alpha/` 的零外部相依是 Phase 1 的驗收條件之一。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .errors import ContractViolation

_ROOT = Path(__file__).resolve().parents[1]
CATALYST_KINDS_PATH = _ROOT / "config" / "catalyst_kinds.json"
STRUCTURAL_EVENT_KINDS_PATH = _ROOT / "config" / "structural_event_kinds.json"


def _load_kinds(path: Path, label: str) -> frozenset[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:  # fail closed，不預設空集合
        raise ContractViolation(
            f"{label} 字彙檔不存在：{path}。"
            "⚠ 新增 config/*.json 必須同時在 .gitignore 補 !config/<name>.json，"
            "否則 fresh clone 會缺檔而靜默失效"
        ) from exc
    kinds = payload.get("kinds")
    if not isinstance(kinds, list) or not kinds:
        raise ContractViolation(f"{label} 字彙檔的 kinds 必須是非空 list：{path}")
    keys = {str(item["key"]) for item in kinds if isinstance(item, dict) and item.get("key")}
    if len(keys) != len(kinds):
        raise ContractViolation(f"{label} 字彙檔有重複或缺 key 的條目：{path}")
    return frozenset(keys)


@lru_cache(maxsize=1)
def catalyst_kinds() -> frozenset[str]:
    return _load_kinds(CATALYST_KINDS_PATH, "Catalyst.kind")


@lru_cache(maxsize=1)
def structural_event_kinds() -> frozenset[str]:
    return _load_kinds(STRUCTURAL_EVENT_KINDS_PATH, "StructuralEvent.kind")


def validate_kind(value: str, allowed: frozenset[str], label: str) -> str:
    """未登記一律拒收。

    ⚠ 拒收的理由不是拼法整齊，是 F-18：`trace_status` 曾是自由字串卻決定 lead 去留，
    打錯不報錯、只是靜默沉底。**同義詞的危險是它讓寫的人以為表達了一個沒被記錄的區別。**
    """
    if value not in allowed:
        raise ContractViolation(
            f"{label} 未登記：{value!r}；已知 {sorted(allowed)}。"
            f"新增品類請改 config（taxonomy 留鬆），不要在程式裡放行"
        )
    return value
