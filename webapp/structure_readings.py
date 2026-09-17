"""結構讀圖的 state artifact（2026-09-17 Q5）：**每一份讀圖現在跟圖還一不一致。**

## 為什麼要 materialize 而不是心跳自己算

比對要讀圖（Neo4j）。心跳的契約是**零 LLM、零網路、只讀本機 authority 與已 materialize 的
state artifact**——它不是一個會去查圖的東西。所以分工照既有的那條線：
**materialize 算一次判讀，心跳與 APP 讀它**（`LLM changes cognition; APP reads cognition`；
這裡連 LLM 都不用，是純確定性比對）。

## 它回答什麼

- 有幾份讀圖、其中幾份 `current`／`stale`／`stale_low`／`expired`；
- **哪幾個節點的哪個角度變了**（分級後仍可能改變 A／B 讀法的才算 `stale`）；
- 哪幾筆同時是既有 disproof 機制的觸發來源（§6b ④；**只標記，不寫任何 thesis**）。

## 它不做的事

- **不重新推理**：重讀是研究，只在互動 session（D12）。這裡只回答「誰該被重讀」。
- **不寫 ledger**：讀圖紀錄是 append-only authority，只有人能寫。
- **不 gate 任何東西**：不濾候選、不改排序、不給尺寸。
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from typing import Any, Mapping, Sequence

from .contracts import canonical_digest, state_freshness_identity

STRUCTURE_READINGS_MATERIALIZER_VERSION = "webapp-materialize-structure-readings/1"

STRUCTURE_READINGS_THIS_IS_NOT: tuple[str, ...] = (
    "不是新的判讀：每一列的 kind 與理由都是研究 session 當時寫進 ledger 的，本層一個字都不改。",
    "不是重新推理：它只比對「當時那五條查詢回什麼」與「現在回什麼」，重讀是互動 session 的事。",
    "維護的是「讀圖跟圖還一不一致」，不是「讀圖對不對」——一份跟圖一致但判斷錯誤的讀圖，"
    "這裡永遠是 current。對不對要靠 outcome 量測，兩件事不得混為一談。",
    "不 gate 任何東西：不濾候選、不改排序、不給尺寸（L15-2：LLM 可以解析與提議，不可以授權）。",
)


def build_structure_readings_artifact(
    *, rows: Sequence[Mapping[str, Any]], parse_errors: Sequence[str] = (),
    generated_at: datetime | None = None, as_of: date | None = None,
) -> dict[str, Any]:
    """逐節點的狀態列 → state artifact。**純函式**：不查圖、不讀 ledger。"""
    stamp = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    counts: dict[str, int] = {"current": 0, "stale": 0, "stale_low": 0, "expired": 0, "unknown": 0}
    for row in rows:
        counts[str(row.get("status") or "unknown")] = counts.get(str(row.get("status") or "unknown"), 0) + 1
    needs = [r for r in rows if r.get("needs_reread")]
    triggers = [r for r in rows if r.get("disproof_triggers")]
    payload: dict[str, Any] = {
        "schema_version": "stockbot-app/structure_readings/1",
        "kind": "structure_readings",
        "title": "結構讀圖：每一份讀圖跟圖還一不一致",
        "generated_at": stamp.isoformat(),
        "as_of": as_of.isoformat() if as_of else None,
        "point_in_time": {"as_of": as_of.isoformat() if as_of else None,
                          "mode": "as_of" if as_of else "current"},
        "authority": {
            "function": "alpha/providers/structure_readings（ledger）＋ query.structure（現在的圖）"
                        "＋ alpha.structure_reading.staleness（分級）",
            "command": "python -m webapp materialize --structure-readings",
            "note": "ledger 是 append-only authority，本層唯讀；分級是確定性比對，零 LLM。",
        },
        "counts": counts,
        "rows": list(rows),
        # producer 必須指得出 consumer（INV-4）：這個數字就是 pq1 那一段的長度。
        "needs_reread": {"n": len(needs), "nodes": [str(r.get("node")) for r in needs],
                         "segment": "stale_structure_readings",
                         "consumer": "research-drain：重跑 python -m query.structure <node> 後改寫讀圖紀錄"},
        "disproof_triggers": {"n": len(triggers),
                              "nodes": [str(r.get("node")) for r in triggers],
                              "note": "供給側多一家／反向路徑變動本來就是量的賭注的 disproof 條件（§6b ④）。"
                                      "**這裡只標記**——thesis mutation 是四個人工 gate 之一，不自動寫。"},
        "parse_errors": list(parse_errors),
        "this_is_not": list(STRUCTURE_READINGS_THIS_IS_NOT),
        "materializer": {
            "version": STRUCTURE_READINGS_MATERIALIZER_VERSION,
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "note": "artifact 是 derived cache，不是 authority——刪掉重跑就會回來（L10）",
        },
    }
    payload["freshness_identity"] = state_freshness_identity(
        kind="structure_readings", as_of=payload["as_of"],
        # 認知狀態＝每個節點現在是什麼狀態、現行讀圖是哪一筆。變化明細的措辭不算。
        identity={"rows": [[r.get("node"), r.get("status"), r.get("reading_id")] for r in rows]})
    payload["content_digest"] = canonical_digest(payload)
    return payload


__all__ = ["STRUCTURE_READINGS_MATERIALIZER_VERSION", "STRUCTURE_READINGS_THIS_IS_NOT",
           "build_structure_readings_artifact"]
