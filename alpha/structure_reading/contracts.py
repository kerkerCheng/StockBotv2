"""結構讀圖紀錄（Structure Reading，2026-09-17 Q5）——**存輸入，不存結論**。

## 它擁有什麼真相

一件事：**「某年某月某日，我對某個節點跑了那五條查詢，它們回了這些，於是我讀成這樣。」**

存「CW laser 是 B 型」這個**結論**沒有用——它不會告訴你什麼時候不再成立。
所以每一筆紀錄的主體是 `angles`（當時的查詢結果集），判讀（`kind` ＋ `reading`）只是附帶。
偵測「還成不成立」因此是零 LLM 的：重跑 `query.structure`，比對結果集。

## 為什麼是結果集而不是「我讀過哪幾條邊」

**最危險的變化是「多了一條我當初沒讀到的邊」**——有人替 CW laser 補上第七家供應商，
供給側分布就變了、A/B 判讀可能翻轉。存邊清單偵測不到，存結果集偵測得到。

## 四條硬要求

1. **`expires` 必填**（INV-2：每個等待都必須有到期）。建議跟著該檔 thesis 的
   `check_interval_days` 走，不要另設全域天數（L7）。到期未重讀 → `expired` 並計數，不刪。
2. **append-only**：改寫用新紀錄 `supersedes_id`，撤回 append 一筆 `retracted=true`（L10）。
3. **`kind` 由 session 宣告，不由程式推導。** 設計文件 §3 的 A/B 判準表逐字寫著
   **「這張表不得被寫成程式去自動分類」**——INV-5 在這裡的意思是先產出幾十份、看它準不準，
   再談機械化。所以本模組只驗字彙在不在封閉清單裡，**不看 `angles` 去推 `kind`**。
4. **它不 gate 任何東西**：不濾候選、不改排序、不給尺寸（L15-2：LLM 可以解析與提議，不可以授權）。

## 它不是什麼

- **不是第二份圖**：`angles` 是某個時點的查詢快照，圖永遠是 `structure_table` 那條路的權威。
- **不是賭注**：讀圖是**寫賭注的輸入**。賭注住 variant assumptions，不主張住 `alpha/abstention/`。
- **維護的是「讀圖跟圖還一不一致」，不是「讀圖對不對」。** 一份跟圖完全一致但判斷錯誤的讀圖，
  digest 永遠不會變——**那是設計如此，不是漏洞**；「對不對」要靠 outcome 量測。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Mapping, Sequence

from ..errors import ContractViolation

#: v2（Phase 1 Step 1.5，2026-09-24）加結構化 `disproof[]`：寫讀圖時就寫下「什麼會推翻這份讀法」，
#: append 成功後由 provider 登記成語意 watch。**v1 紀錄照樣解析成 `disproof=()`、不改寫**（L10：append-only）。
RECORD_VERSION = "structure-reading/v2"
RECORD_VERSION_V1 = "structure-reading/v1"

#: 讀成什麼。封閉字彙，**由寫的人宣告**（見檔頭第 3 條：不得由程式從 `angles` 推導）。
#:
#: - `moat`（A：護城河賭注）：需求側繞不過，且供給側有人明顯高於其他。
#: - `volume`（B：量的賭注）：需求側繞不過，但供給側大家都差不多——賭的是「產能一時補不上」，
#:   **不需要護城河**。歷史上最可靠的 power-law 樣式之一（DRAM 2017、ABF 載板 2021）。
#: - `neither`：這個位置本來就不卡（需求側 sub 低）。**這是答案，不是失敗。**
#: - `undecided`：查了，但現有的格填不出判斷（缺哪一項要寫進 `reading`）。
READING_KINDS: Mapping[str, str] = {
    "moat": "A：護城河賭注——需求側繞不過，且供給側有人明顯難替代",
    "volume": "B：量的賭注——需求側繞不過，供給側大家差不多；賭的是產能一時補不上",
    "neither": "都不是：這個位置本來就不卡（需求側可替代）",
    "undecided": "查了但判不出來——缺哪一格要寫在 reading 裡",
}

#: 五個角度的 key，與 `query/structure.py::ANGLES` 同一組封閉字彙。
#: ⚠ 兩邊不一致時寫入端拒收——分類有 SSOT 就不該在第二個地方重造一份（L16）。
ANGLE_KEYS: tuple[str, ...] = ("demand_side", "supply_side", "next_layer", "counter_path")

_ID_FIELDS = ("node", "result_digest", "kind", "reading", "created_at", "author",
              "expires", "tickers", "supersedes_id", "retracted")
#: ⚠ v2 才把 `disproof` 納入 id：直接加進 `_ID_FIELDS` 會讓 v1 重算出不同的 id（body 多一個 `"disproof": null`），
#: 既有 8 筆紀錄的 id 就對不上了。所以**依 `record_version` 分支**，v1 的算法一個字不動。
_ID_FIELDS_V2 = _ID_FIELDS + ("disproof",)

#: 這兩種讀法本身就是賭注，必須寫下什麼會推翻它（v2 起）；`neither`／`undecided` 可以沒有。
KINDS_REQUIRING_DISPROOF = frozenset({"moat", "volume"})


@dataclass(frozen=True, slots=True)
class DisproofEntry:
    """讀圖的一條反證／確認條件（L7 三件套：條件、核查頻率、觸發後 48 小時動作）。"""

    condition: str
    entities: tuple[str, ...]
    check_frequency: str
    action_48h: str
    expires: date | None = None

    def __post_init__(self) -> None:
        if len(str(self.condition).strip()) < 20:
            raise ContractViolation("disproof.condition 必須是原文、至少 20 字")
        if not any(str(e).startswith("co:") for e in self.entities):
            raise ContractViolation("disproof.entities 至少要有一個 co:*——只寫 ticker 的 watch 叫不醒")
        if not str(self.check_frequency).strip() or not str(self.action_48h).strip():
            raise ContractViolation("disproof 缺 L7 件：check_frequency 與 action_48h 都必填")

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"condition": self.condition, "entities": list(self.entities),
                               "check_frequency": self.check_frequency, "action_48h": self.action_48h}
        if self.expires is not None:
            out["expires"] = self.expires.isoformat()
        return out


def _disproof_entries(raw: Any) -> tuple[DisproofEntry, ...]:
    entries = []
    for item in raw or ():
        if not isinstance(item, Mapping):
            raise ContractViolation("disproof 的每一條必須是 object")
        expires = item.get("expires")
        entries.append(DisproofEntry(
            condition=str(item.get("condition") or ""),
            entities=tuple(str(e) for e in (item.get("entities") or ())),
            check_frequency=str(item.get("check_frequency") or ""),
            action_48h=str(item.get("action_48h") or ""),
            expires=date.fromisoformat(str(expires)[:10]) if expires else None,
        ))
    return tuple(entries)


@dataclass(frozen=True, slots=True)
class StructureReading:
    """一份讀圖紀錄。`angles` 是當時的**查詢結果集**，不是「我讀過哪幾條邊」。"""

    reading_id: str
    node: str
    result_digest: str
    kind: str
    reading: str
    angles: Mapping[str, tuple[tuple[Any, ...], ...]]
    anchor_chain: tuple[str, ...] | None
    created_at: datetime
    expires: date
    author: str = "session"
    tickers: tuple[str, ...] = ()
    supersedes_id: str | None = None
    retracted: bool = False
    disproof: tuple[DisproofEntry, ...] = ()
    record_version: str = RECORD_VERSION_V1

    def __post_init__(self) -> None:
        if not self.reading_id.startswith("sr_"):
            raise ContractViolation("reading_id 必須以 sr_ 開頭（由 new_reading_id 產生）")
        if not str(self.node).strip():
            raise ContractViolation("StructureReading.node 必須是非空字串")
        if self.kind not in READING_KINDS:
            raise ContractViolation(
                f"reading kind 未登記：{self.kind!r}；已知 {sorted(READING_KINDS)}——"
                "字彙是 contract：多一種就要多一段消費端語意")
        if not self.retracted:
            if len(str(self.reading).strip()) < 20:
                raise ContractViolation(
                    "StructureReading.reading 太短——讀圖的價值在「憑什麼」，"
                    "一個沒有理由的 kind 下次沒有人能重看它")
            unknown = set(self.angles) - set(ANGLE_KEYS)
            if unknown:
                raise ContractViolation(
                    f"angles 出現未登記的角度 {sorted(unknown)}；已知 {list(ANGLE_KEYS)}——"
                    "角度清單的 SSOT 是 query/structure.py::ANGLES")
        if self.created_at.tzinfo is None:
            raise ContractViolation("created_at 必須帶時區")
        if self.expires <= self.created_at.astimezone(timezone.utc).date():
            raise ContractViolation(
                "expires 必須晚於 created_at——沒有到期的等待就是不會到期的等待（INV-2）")
        if (self.record_version == RECORD_VERSION and not self.retracted
                and self.kind in KINDS_REQUIRING_DISPROOF and not self.disproof):
            raise ContractViolation(
                f"{self.kind} 讀法本身就是賭注——v2 起必須寫下至少一條 disproof（什麼會推翻這份讀法）")

    @property
    def created_on(self) -> date:
        return self.created_at.astimezone(timezone.utc).date()

    def is_expired(self, today: date) -> bool:
        return today > self.expires


def new_reading_id(payload: Mapping[str, Any]) -> str:
    """content-addressed id：同一份內容永遠得到同一個 id（重複 append 可被偵測）。

    v2 把 `disproof` 納入（只差反證的兩份 v2 才不會同 id）；v1 的欄位與算法不變。"""
    fields = _ID_FIELDS_V2 if payload.get("record_version") == RECORD_VERSION else _ID_FIELDS
    body = {k: payload.get(k) for k in fields}
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return "sr_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _angle_rows(raw: Any) -> dict[str, tuple[tuple[Any, ...], ...]]:
    out: dict[str, tuple[tuple[Any, ...], ...]] = {}
    for key, rows in dict(raw or {}).items():
        out[str(key)] = tuple(tuple(row) for row in (rows or ()))
    return out


def structure_reading_record(
    *,
    node: str,
    structure: Mapping[str, Any],
    kind: str,
    reading: str,
    expires: date,
    created_at: datetime | None = None,
    author: str = "session",
    tickers: Sequence[str] = (),
    supersedes_id: str | None = None,
    retracted: bool = False,
    disproof: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """建一筆可寫進 ledger 的紀錄（v2：`disproof` 是結構化反證，moat／volume 至少一條）。

    `structure` 直接吃 `query.structure.StructureView.as_dict()`——**快照由那一支產生，
    這裡不自己查圖**，否則同一個節點會有兩套查法而它們遲早會漂開（L16）。
    """
    stamp = created_at or datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        raise ContractViolation("created_at 必須帶時區")
    digest = str(structure.get("result_digest") or "")
    if not digest:
        raise ContractViolation(
            "structure 沒有 result_digest——快照必須來自 query.structure 的輸出，"
            "手組的快照偵測不了「多了一條我當初沒讀到的邊」")
    angles = {
        key: sorted(
            [str(edge.get("src")), str(edge.get("relation")), str(edge.get("dst")),
             edge.get("substitutability"), edge.get("sole_source"),
             edge.get("qualification_status"), edge.get("evidence")]
            for edge in (structure.get("angles") or {}).get(key, ())
        )
        for key in ANGLE_KEYS
    }
    payload: dict[str, Any] = {
        "record_version": RECORD_VERSION,
        "node": str(node),
        "result_digest": digest,
        "kind": str(kind),
        "reading": str(reading),
        "angles": angles,
        "anchor_chain": list(structure.get("anchor_chain") or []) or None,
        "created_at": stamp.astimezone(timezone.utc).isoformat(),
        "expires": expires.isoformat(),
        "author": str(author),
        "tickers": [str(t).upper() for t in tickers],
        "supersedes_id": supersedes_id,
        "retracted": bool(retracted),
        "disproof": [entry.as_dict() for entry in _disproof_entries(disproof)],
    }
    payload["reading_id"] = new_reading_id(payload)
    parse_structure_reading_record(payload)   # 驗證；不合法就在這裡炸，不會寫進 ledger
    return payload


def parse_structure_reading_record(raw: Mapping[str, Any]) -> StructureReading:
    """dict → `StructureReading`；任何欄位不合法都 raise `ContractViolation`。"""
    try:
        created = datetime.fromisoformat(str(raw["created_at"]))
        expires = date.fromisoformat(str(raw["expires"])[:10])
    except (KeyError, ValueError) as exc:
        raise ContractViolation(f"structure reading 的時間欄位不合法：{exc}") from None
    anchor = raw.get("anchor_chain")
    return StructureReading(
        reading_id=str(raw.get("reading_id") or ""),
        node=str(raw.get("node") or ""),
        result_digest=str(raw.get("result_digest") or ""),
        kind=str(raw.get("kind") or ""),
        reading=str(raw.get("reading") or ""),
        angles=_angle_rows(raw.get("angles")),
        anchor_chain=tuple(str(n) for n in anchor) if anchor else None,
        created_at=created,
        expires=expires,
        author=str(raw.get("author") or "session"),
        tickers=tuple(str(t).upper() for t in (raw.get("tickers") or ())),
        supersedes_id=(str(raw["supersedes_id"]) if raw.get("supersedes_id") else None),
        retracted=bool(raw.get("retracted")),
        disproof=_disproof_entries(raw.get("disproof")),
        record_version=str(raw.get("record_version") or RECORD_VERSION_V1),
    )


def select_reading(
    records: Sequence[StructureReading], *, as_of: date | None = None, today: date,
) -> StructureReading | None:
    """as-of 視角下這個節點**現行**的那一筆；沒有就是 `None`。

    選取規則與 abstention／假設 ledger **同一套**：`created_on <= 視角日` → 取最新 →
    最新那筆是 `retracted` 就等於沒有。⚠ **過期的仍然回得出來**——`expired` 是一種要被
    計數與重讀的狀態，不是「不存在」（把它讀成不存在，就回到了「安靜消失」）。
    """
    cutoff = as_of or today
    visible = [r for r in records if r.created_on <= cutoff]
    if not visible:
        return None
    latest = max(visible, key=lambda r: (r.created_at, r.reading_id))
    return None if latest.retracted else latest


__all__ = [
    "ANGLE_KEYS", "DisproofEntry", "KINDS_REQUIRING_DISPROOF", "READING_KINDS", "RECORD_VERSION",
    "RECORD_VERSION_V1", "StructureReading",
    "new_reading_id", "parse_structure_reading_record", "select_reading", "structure_reading_record",
]
