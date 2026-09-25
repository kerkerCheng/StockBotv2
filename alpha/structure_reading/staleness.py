"""讀圖 staleness 的**分級**（2026-09-17 Q5，設計見 `docs/brainstorms/2026-09-17-structural-reading-layer.md` §6b）。

## 為什麼要分級而不是 binary

⚠ **binary 的 stale 會恆亮**，而恆亮＝零鑑別力（L14-4），還會訓練人忽略它。
分級的判準只有一個：**這個變化會不會改變 A／B 的讀法？**

| 變了什麼 | 會不會翻轉 A/B | 等級 |
|---|---|---|
| 供給側多／少一家，或某家 sub 變了 | 很可能（分布是 B 的核心判準） | `high` |
| 需求側 sub 變了 | 很可能（這是「繞不繞得過」） | `high` |
| 下一層變了 | 可能（會改變「更卡的在哪一層」） | `normal` |
| 反向路徑新增或消失 | 可能，**而且它本來就是 disproof 的來源** | `normal`（另標 `disproof`） |
| 只有 evidence 等級變 | 不改變結構，改變的是可下注性 | `low` |
| **插槽讀圖**的供貨邊 evidence 變（v3） | 會——客戶或第三方第一次具名就是插槽賭注的確認或推翻 | `high`（`supply_evidence`） |

## `documents` 為什麼不在上表裡

因為它**在更上游就被擋掉了**：`query/structure.py::EdgeView.key()` 不含 `documents`，
所以多讀一份文件不會改變 `result_digest`，這一層根本收不到那種變化。
這是刻意的——`documents` 是研究量的函數（`AGENTS.md` 明列「會隨我們多讀一份文件而單調上升」
的指標），讓它觸發重讀等於讓「我們讀得多」自己製造工作。

## ⚠ 為什麼「供給側多一家」可以觸發，`documents` 不行

`AGENTS.md` 把**同一 chokepoint 的供應商計數**與 `documents` 計數並列為「會隨我們多讀一份文件
而單調上升」的指標，兩者都**不得單獨用作瓶頸性證據**。這一層沒有違反它，但差別要講清楚：

- 這裡用供應商增減做的是 **staleness 偵測**（「我那份判讀還能不能用」），
  **不是瓶頸性證據**（「這個位置卡不卡」）。後者仍然只由 `structure_table()` 的逐邊事實回答。
- 而且**多一家供應商本來就會改變 B 型賭注的結論**——供給側分布正是「量的賭注」的判準，
  那一家是世界上新出現的、還是我們今天才讀到的，對「我該不該重看這份判讀」都一樣。
- `documents` 不同：多一份文件支持**同一條邊**，結構一個位元都沒動。所以它被擋在 digest 之外。

判準一句話：**改變「邊的集合或邊的值」的才觸發；只改變「我們有多少份佐證」的不觸發。**

## 這一層不做的事

- **不重跑圖查詢**：`build_structure()` 的結果由呼叫端給，本模組是純函式。
- **不自動重新推理**：重讀是研究，只在互動 session 做（D12）。這裡只產生「誰該被重讀」。
- **不寫任何 authority**。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, Mapping, Sequence

#: 一份讀圖紀錄相對於**現在的圖**是什麼狀態。封閉字彙。
#: ⚠ `expired` 與 `stale` 不得壓成一格：前者是「時間到了該重看」，後者是「圖真的變了」。
#: 一份可以同時兩者皆是——那時回 `expired`，因為它更該優先處理。
READING_STATUSES: Mapping[str, str] = {
    "current": "與圖一致，且未到期",
    "stale": "圖變了，且變化分級後仍可能改變 A/B 讀法",
    "stale_low": "圖變了，但只有 evidence 等級——記錄，不優先",
    "expired": "到期未重讀（INV-2：每個等待都必須有到期）",
}

#: 變化的種類。封閉字彙——**每一種都要說得出它為什麼會（或不會）翻轉 A/B**。
CHANGE_KINDS: Mapping[str, tuple[str, str]] = {
    "supply_added": ("high", "供給側多了一家——分布是 B（量的賭注）的核心判準"),
    "supply_removed": ("high", "供給側少了一家——分布變了"),
    "supply_substitutability": ("high", "供給側某家的 substitutability 變了"),
    "demand_substitutability": ("high", "需求側 substitutability 變了——這是「繞不繞得過」"),
    "demand_edges": ("high", "需求側的邊增減——誰需要它變了"),
    "next_layer": ("normal", "下一層變了——更卡的可能換了一層"),
    "counter_path": ("normal", "反向路徑新增或消失——它本來就是 disproof 的來源"),
    "anchor": ("normal", "需求錨可達性變了——走不走得到有人花錢的地方"),
    "evidence": ("low", "只有 evidence 等級變——不改變結構，改變的是可下注性"),
    # v3（Phase 2 Step 2.4）：插槽讀圖的供貨邊證據變動是高等級。插槽賭的是「客戶的這一格指定了誰」，
    # 客戶或第三方第一次具名（evidence 由自報升成外部印證）本身就是確認或推翻事件；層讀圖的分級一字不動。
    "supply_evidence": ("high", "插槽的供貨邊證據等級變了——客戶或第三方第一次具名，是插槽賭注的確認或推翻事件"),
}

#: 哪些變化**同時**是既有 disproof 機制的觸發來源（§6b ④）。
#: ⚠ 這裡只標記；**不自動寫進任何 thesis**——thesis mutation 是四個人工 gate 之一。
DISPROOF_KINDS: frozenset[str] = frozenset({"counter_path", "supply_added"})

_ANGLE_TO_KINDS: Mapping[str, tuple[str, str]] = {
    # 角度 → (成員增減用哪個 kind, 屬性變動用哪個 kind)
    "supply_side": ("supply_added", "supply_substitutability"),
    "demand_side": ("demand_edges", "demand_substitutability"),
    "next_layer": ("next_layer", "next_layer"),
    "counter_path": ("counter_path", "counter_path"),
}

#: 邊的 key 在快照裡的欄位順序（與 `structure_reading_record` 寫入時一致）。
_SRC, _REL, _DST, _SUB, _SOLE, _QUAL, _EVID = range(7)


@dataclass(frozen=True)
class StructureChange:
    angle: str
    kind: str
    detail: str

    @property
    def grade(self) -> str:
        return CHANGE_KINDS[self.kind][0]

    @property
    def is_disproof_trigger(self) -> bool:
        return self.kind in DISPROOF_KINDS

    def as_dict(self) -> dict[str, Any]:
        return {"angle": self.angle, "kind": self.kind, "grade": self.grade,
                "detail": self.detail, "disproof_trigger": self.is_disproof_trigger}


def _identity(row: Sequence[Any]) -> tuple[str, str, str]:
    return (str(row[_SRC]), str(row[_REL]), str(row[_DST]))


def _rows_by_identity(rows: Iterable[Sequence[Any]]) -> dict[tuple[str, str, str], list[Any]]:
    return {_identity(r): list(r) for r in rows}


def _angle_changes(angle: str, before: Iterable[Sequence[Any]], after: Iterable[Sequence[Any]],
                   *, unit: str = "layer") -> list[StructureChange]:
    member_kind, attr_kind = _ANGLE_TO_KINDS[angle]
    old = _rows_by_identity(before)
    new = _rows_by_identity(after)
    changes: list[StructureChange] = []

    added = [k for k in new if k not in old]
    removed = [k for k in old if k not in new]
    if added:
        changes.append(StructureChange(angle, member_kind,
                                       f"新增 {len(added)} 條：" + "、".join(f"{s}→{d}" for s, _r, d in added[:3])))
    if removed:
        kind = "supply_removed" if angle == "supply_side" else member_kind
        changes.append(StructureChange(angle, kind,
                                       f"消失 {len(removed)} 條：" + "、".join(f"{s}→{d}" for s, _r, d in removed[:3])))

    for key in (k for k in new if k in old):
        before_row, after_row = old[key], new[key]
        label = f"{key[0]}→{key[2]}"
        # substitutability／sole_source／qualification 都是結構屬性，走同一個 kind；
        # evidence 單獨一級——它改變的是「可不可以下注」，不是「結構長什麼樣」。
        for index, name in ((_SUB, "substitutability"), (_SOLE, "sole_source"), (_QUAL, "qualification_status")):
            if before_row[index] != after_row[index]:
                changes.append(StructureChange(
                    angle, attr_kind, f"{label} 的 {name}：{before_row[index]} → {after_row[index]}"))
        if before_row[_EVID] != after_row[_EVID]:
            kind = "supply_evidence" if (unit == "socket" and angle == "supply_side") else "evidence"
            changes.append(StructureChange(
                angle, kind, f"{label} 的 evidence：{before_row[_EVID]} → {after_row[_EVID]}"))
    return changes


def grade_changes(before_angles: Mapping[str, Sequence[Sequence[Any]]],
                  after_structure: Mapping[str, Any],
                  *, before_anchor: Sequence[str] | None = None, unit: str) -> list[StructureChange]:
    """快照 vs 現在的圖 → 逐項分級的變化清單。**純函式，不查圖。**

    `after_structure` 吃 `query.structure.StructureView.as_dict()`。
    `unit` 沒有預設（v3）：同一個變化對層與插槽的意義不同——插槽的供貨邊證據變動是高等級。
    """
    after_angles = after_structure.get("angles") or {}
    changes: list[StructureChange] = []
    for angle in _ANGLE_TO_KINDS:
        after_rows = [
            [str(e.get("src")), str(e.get("relation")), str(e.get("dst")),
             e.get("substitutability"), e.get("sole_source"),
             e.get("qualification_status"), e.get("evidence")]
            for e in after_angles.get(angle, ())
        ]
        changes += _angle_changes(angle, before_angles.get(angle) or (), after_rows, unit=unit)

    after_anchor = list(after_structure.get("anchor_chain") or [])
    if list(before_anchor or []) != after_anchor:
        changes.append(StructureChange(
            "anchor", "anchor",
            f"需求錨鏈：{'→'.join(before_anchor or []) or '（走不到）'} ⇒ {'→'.join(after_anchor) or '（走不到）'}"))
    return changes


def reading_status(reading: Any, after_structure: Mapping[str, Any] | None, *, today: date) -> dict[str, Any]:
    """一份讀圖紀錄現在是什麼狀態，以及**憑什麼**。

    `after_structure=None` ＝ 這次沒讀到圖（例如 Neo4j 沒開）：回 `None` 狀態並說明，
    **不得回 `current`**——「沒查」與「查過沒變」不得同形（L13-2）。
    """
    if after_structure is None:
        return {"status": None, "reason": "這次沒有讀到圖，無法比對（不是 current）",
                "changes": [], "expired": reading.is_expired(today)}
    changes = grade_changes(reading.angles, after_structure, before_anchor=reading.anchor_chain,
                            unit=reading.unit)
    digest_changed = str(after_structure.get("result_digest") or "") != reading.result_digest
    grades = {c.grade for c in changes}
    if reading.is_expired(today):
        status = "expired"
    elif not digest_changed:
        status = "current"
    elif grades <= {"low"}:
        status = "stale_low"
    else:
        status = "stale"
    # ⚠ digest 變了卻找不出任何變化＝比對邏輯與 digest 的欄位不同步。安靜回 current 會讓
    # 整個機制失效，所以明說（INV-3：不得靜默丟棄）。
    reason = None
    if digest_changed and not changes:
        reason = "result_digest 變了但逐項比對找不出差異——比對欄位與 digest 欄位可能不同步"
    return {
        "status": status,
        "digest_changed": digest_changed,
        "expired": reading.is_expired(today),
        "days_to_expiry": (reading.expires - today).days,
        "changes": [c.as_dict() for c in changes],
        "highest_grade": ("high" if "high" in grades else "normal" if "normal" in grades
                          else "low" if "low" in grades else None),
        "disproof_triggers": [c.as_dict() for c in changes if c.is_disproof_trigger],
        "reason": reason,
    }


def needs_reread(status: Mapping[str, Any]) -> bool:
    """該進 pq1 嗎？**`stale_low` 不進**——它記錄但不優先（否則佇列會被 evidence 微調灌滿）。"""
    return str(status.get("status")) in ("stale", "expired")


__all__ = [
    "CHANGE_KINDS", "DISPROOF_KINDS", "READING_STATUSES", "StructureChange",
    "grade_changes", "needs_reread", "reading_status",
]
