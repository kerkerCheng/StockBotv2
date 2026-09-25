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
#: v3（Phase 2 Step 2.3，2026-09-25，plan A1／A2）加 `unit`（讀的是一層還是一格插槽）、`citations[]`
#: （判讀憑的每一半都指得回圖上原文）與 `disproof[].source`（反證出處）。**v1／v2 解析成 `unit=layer`、不改寫。**
RECORD_VERSION = "structure-reading/v3"
RECORD_VERSION_V2 = "structure-reading/v2"
RECORD_VERSION_V1 = "structure-reading/v1"

#: 讀的是哪一種單位（封閉字彙，A1）。**不是判讀結論**——結論仍是 `READING_KINDS`；把「讀的是什麼」塞進
#: 「讀成什麼」會讓一個欄位承載兩種語意（L12）。插槽讀圖本身也要回答護城河還是量（決定紀錄 G5）。
READING_UNITS: Mapping[str, str] = {
    "layer": "層讀圖：技術／材料節點（含變體）",
    "socket": "插槽讀圖：客戶的產品／專案 × 那一格零件",
}

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
#: ⚠ v3 同樣只在 v3 的欄位集合裡加（`unit`、`citations`）——加進 `_ID_FIELDS`／`_ID_FIELDS_V2` 會讓舊 10 行 id 全變、
#: Phase 1 的語意 watch 全部變孤兒（plan §13 第一條陷阱）。
_ID_FIELDS_V3 = _ID_FIELDS_V2 + ("unit", "citations")

#: 這兩種讀法本身就是賭注，必須寫下什麼會推翻它（v2 起）；`neither`／`undecided` 可以沒有。
KINDS_REQUIRING_DISPROOF = frozenset({"moat", "volume"})
#: 這兩種讀法必須引用需求側與供給側各至少一段原文（v3 起，A2）——A/B 判準表讀的正是這兩半。
KINDS_REQUIRING_CITATIONS = frozenset({"moat", "volume"})
#: 引用的原文片段最短長度：太短的片段（「sole source」）在任何一段逐字裡都找得到，核對不出憑的是哪一段。
MIN_QUOTE_CHARS = 20
#: 反證的出處（v3）：本份寫下的，或沿用同節點 ledger 裡既有的某一份（Phase 1 待決 #19：追回原文不必跳兩層）。
DISPROOF_SOURCE_SELF = "self"


@dataclass(frozen=True, slots=True)
class DisproofEntry:
    """讀圖的一條反證／確認條件（L7 三件套：條件、核查頻率、觸發後 48 小時動作）。"""

    condition: str
    entities: tuple[str, ...]
    check_frequency: str
    action_48h: str
    expires: date | None = None
    #: v3 必填：`self` 或同節點既有讀圖的 `sr_*`；v1／v2 沒有這一欄（`None`）。
    source: str | None = None

    def __post_init__(self) -> None:
        if len(str(self.condition).strip()) < 20:
            raise ContractViolation("disproof.condition 必須是原文、至少 20 字")
        if not any(str(e).startswith("co:") for e in self.entities):
            raise ContractViolation("disproof.entities 至少要有一個 co:*——只寫 ticker 的 watch 叫不醒")
        if not str(self.check_frequency).strip() or not str(self.action_48h).strip():
            raise ContractViolation("disproof 缺 L7 件：check_frequency 與 action_48h 都必填")
        if self.source is not None and not (self.source == DISPROOF_SOURCE_SELF or self.source.startswith("sr_")):
            raise ContractViolation(f"disproof.source 只能是 'self' 或既有讀圖的 sr_*：{self.source!r}")

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"condition": self.condition, "entities": list(self.entities),
                               "check_frequency": self.check_frequency, "action_48h": self.action_48h}
        if self.expires is not None:
            out["expires"] = self.expires.isoformat()
        if self.source is not None:
            out["source"] = self.source
        return out


def _disproof_entries(raw: Any) -> tuple[DisproofEntry, ...]:
    entries = []
    for item in raw or ():
        if not isinstance(item, Mapping):
            raise ContractViolation("disproof 的每一條必須是 object")
        expires = item.get("expires")
        source = item.get("source")
        entries.append(DisproofEntry(
            condition=str(item.get("condition") or ""),
            entities=tuple(str(e) for e in (item.get("entities") or ())),
            check_frequency=str(item.get("check_frequency") or ""),
            action_48h=str(item.get("action_48h") or ""),
            expires=date.fromisoformat(str(expires)[:10]) if expires else None,
            source=str(source) if source is not None else None,
        ))
    return tuple(entries)


@dataclass(frozen=True, slots=True)
class Citation:
    """判讀憑的一段圖上原文（v3，A2）。**契約層只驗形狀**；「邊在不在當次快照、片段是不是那條邊的逐字、
    independent 的來源是不是供應商自己」要查圖，由寫入端（`alpha/providers/structure_readings.py`）核對。"""

    angle: str
    edge: tuple[str, str, str]
    quote: str
    source_id: str
    #: 插槽護城河用：這段原文的來源不是該供應商自己，且解析得到（L8：sole_source 需客戶端或第三方印證）。
    independent: bool = False

    def __post_init__(self) -> None:
        if self.angle not in ANGLE_KEYS:
            raise ContractViolation(f"citation.angle 未登記：{self.angle!r}；已知 {list(ANGLE_KEYS)}")
        if len(self.edge) != 3 or not all(str(x).strip() for x in self.edge):
            raise ContractViolation("citation.edge 必須是 [src, relation, dst]")
        if len(" ".join(str(self.quote).split())) < MIN_QUOTE_CHARS:
            raise ContractViolation(f"citation.quote 至少 {MIN_QUOTE_CHARS} 字——太短的片段核對不出憑的是哪一段")
        if not str(self.source_id).strip():
            raise ContractViolation("citation.source_id 必填（SourceDoc id）")

    def as_dict(self) -> dict[str, Any]:
        return {"angle": self.angle, "edge": list(self.edge), "quote": self.quote,
                "source_id": self.source_id, "independent": self.independent}


def _strict_bool(value: Any) -> bool:
    if not isinstance(value, bool):
        raise ContractViolation(f"citation.independent 必須是 true／false，不是 {value!r}（字串 \"false\" 會被讀成真）")
    return value


def _citations(raw: Any) -> tuple[Citation, ...]:
    out = []
    for item in raw or ():
        if not isinstance(item, Mapping):
            raise ContractViolation("citations 的每一條必須是 object")
        edge = item.get("edge") or ()
        if not isinstance(edge, (list, tuple)):
            raise ContractViolation("citation.edge 必須是 [src, relation, dst]")
        out.append(Citation(
            angle=str(item.get("angle") or ""),
            edge=tuple(str(x) for x in edge),
            quote=str(item.get("quote") or ""),
            source_id=str(item.get("source_id") or ""),
            independent=_strict_bool(item.get("independent", False)),
        ))
    return tuple(out)


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
    unit: str = "layer"
    citations: tuple[Citation, ...] = ()

    def __post_init__(self) -> None:
        if self.unit not in READING_UNITS:
            raise ContractViolation(f"reading unit 未登記：{self.unit!r}；已知 {sorted(READING_UNITS)}")
        node = str(self.node)
        if self.unit == "socket" and not node.startswith("prod:"):
            raise ContractViolation(f"插槽讀圖（unit=socket）的節點必須是客戶的產品 prod:*：{node!r}")
        if self.unit == "layer" and node.startswith("co:"):
            raise ContractViolation(f"層讀圖（unit=layer）不讀公司節點：{node!r}——讀的是位置，不是公司")
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
        if (self.record_version in (RECORD_VERSION, RECORD_VERSION_V2) and not self.retracted
                and self.kind in KINDS_REQUIRING_DISPROOF and not self.disproof):
            raise ContractViolation(
                f"{self.kind} 讀法本身就是賭注——v2 起必須寫下至少一條 disproof（什麼會推翻這份讀法）")
        if self.record_version == RECORD_VERSION and not self.retracted:
            self._check_v3()

    def _check_v3(self) -> None:
        """v3 的契約層規則（A2）。查圖的那一半在寫入端。"""
        missing_source = [i for i, e in enumerate(self.disproof, 1) if e.source is None]
        if missing_source:
            raise ContractViolation(
                f"v3 的每一條 disproof 都要寫出處 source（'self' 或沿用的 sr_*）；缺：第 {missing_source} 條")
        if self.kind not in KINDS_REQUIRING_CITATIONS:
            return
        angles = {c.angle for c in self.citations}
        lacking = [a for a in ("demand_side", "supply_side") if a not in angles]
        if lacking:
            raise ContractViolation(
                f"{self.kind} 必須引用需求側與供給側各至少一段圖上原文（A2）；缺：{lacking}——"
                "答不出「憑哪一段」就寫不進來；判不出來請寫 undecided 並說缺哪一格")
        if (self.unit == "socket" and self.kind == "moat"
                and not any(c.angle == "supply_side" and c.independent for c in self.citations)):
            raise ContractViolation(
                "插槽的護城河需要至少一段供給側引用來自不是該供應商自己的來源（independent=true；L8）——"
                "供應商自稱是弱主張")

    @property
    def created_on(self) -> date:
        return self.created_at.astimezone(timezone.utc).date()

    def is_expired(self, today: date) -> bool:
        return today > self.expires


def new_reading_id(payload: Mapping[str, Any]) -> str:
    """content-addressed id：同一份內容永遠得到同一個 id（重複 append 可被偵測）。

    v2 把 `disproof` 納入（只差反證的兩份 v2 才不會同 id）；v3 再納入 `unit`、`citations`；
    v1／v2 的欄位與算法不變（舊 id 一個字都不能變）。"""
    version = payload.get("record_version")
    fields = (_ID_FIELDS_V3 if version == RECORD_VERSION
              else _ID_FIELDS_V2 if version == RECORD_VERSION_V2 else _ID_FIELDS)
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
    unit: str,
    citations: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """建一筆可寫進 ledger 的紀錄（v3）。

    v2 起：`disproof` 是結構化反證，moat／volume 至少一條。v3 起：`unit` 必填（**沒有預設**——
    讀的是一層還是一格插槽要由寫的人宣告，不讓程式替他補）；moat／volume 要 `citations` 兩半各一；
    每條 disproof 要 `source`。引用「是不是真的在圖上」由寫入端核對（`alpha/providers/structure_readings.py`）。

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
        "unit": str(unit),
        "citations": [c.as_dict() for c in _citations(citations)],
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
    version = str(raw.get("record_version") or RECORD_VERSION_V1)
    if version not in (RECORD_VERSION, RECORD_VERSION_V2, RECORD_VERSION_V1):
        raise ContractViolation(f"record_version 未登記：{version!r}——不靜默當成哪一版（拼錯的 v3 會丟掉引用）")
    is_v3 = version == RECORD_VERSION
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
        record_version=version,
        # v1／v2 一律是層讀圖（A1）；v3 的 unit 必須寫出來，缺就拒收（不替寫的人補預設）。
        unit=str(raw.get("unit") or "") if is_v3 else "layer",
        citations=_citations(raw.get("citations")) if is_v3 else (),
    )


def select_reading(
    records: Sequence[StructureReading], *, unit: str, as_of: date | None = None, today: date,
) -> StructureReading | None:
    """as-of 視角下這個節點、**這個單位**現行的那一筆；沒有就是 `None`。

    選取規則與 abstention／假設 ledger **同一套**：`created_on <= 視角日` → 取最新 →
    最新那筆是 `retracted` 就等於沒有。⚠ **過期的仍然回得出來**——`expired` 是一種要被
    計數與重讀的狀態，不是「不存在」（把它讀成不存在，就回到了「安靜消失」）。
    ⚠ `unit` 沒有預設（A1）：同一個 prod 節點可以同時有層讀圖與插槽讀圖，兩份各自是現行——
    漏給單位的呼叫端會只看到其中一種，另一種安靜消失。要全部單位用 `select_readings`。
    """
    if unit not in READING_UNITS:
        raise ContractViolation(f"reading unit 未登記：{unit!r}；已知 {sorted(READING_UNITS)}")
    cutoff = as_of or today
    visible = [r for r in records if r.unit == unit and r.created_on <= cutoff]
    if not visible:
        return None
    latest = max(visible, key=lambda r: (r.created_at, r.reading_id))
    return None if latest.retracted else latest


def select_readings(
    records: Sequence[StructureReading], *, as_of: date | None = None, today: date,
) -> dict[str, StructureReading]:
    """每個單位各自現行的那一筆（`unit → reading`；沒有現行的單位不出現）。"""
    out: dict[str, StructureReading] = {}
    for unit in READING_UNITS:
        current = select_reading(records, unit=unit, as_of=as_of, today=today)
        if current is not None:
            out[unit] = current
    return out


__all__ = [
    "ANGLE_KEYS", "Citation", "DISPROOF_SOURCE_SELF", "DisproofEntry", "KINDS_REQUIRING_CITATIONS",
    "KINDS_REQUIRING_DISPROOF", "MIN_QUOTE_CHARS", "READING_KINDS", "READING_UNITS", "RECORD_VERSION",
    "RECORD_VERSION_V1", "RECORD_VERSION_V2", "StructureReading",
    "new_reading_id", "parse_structure_reading_record", "select_reading", "select_readings",
    "structure_reading_record",
]
