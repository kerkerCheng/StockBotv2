"""層說明（layer note）的紀錄契約——個股頁 plan S4a（2026-10-07 amendment；Phase 7 plan A5）。

**這是什麼：** 一個薄層（或一個技術轉換）一份的研究說明，主鍵是節點或轉換 id，同層每一頁共用、個股頁只引用它
（個股頁 brainstorm §5.5 B4、規則 1）。它是研究判斷（A3）：append-only、可換版、不 gate 任何東西、不排序、不給尺寸。

**四段（2026-10-06 amendment）＝封閉段鍵**，與 B4 元素的對照（brainstorm §5.5；L16：兩份規格只能有一份對照）：

| 段鍵 | 四段 | 涵蓋的 B4 元素 |
|---|---|---|
| `physics` | ①物理與變體 | 做什麼、為什麼難、示意圖 |
| `variants` | ②各家變體與階段（附證據等級） | 轉換時需求怎麼變（走到哪一步）、瓶頸在哪一步形成（圖上幾家） |
| `selection` | ③客戶為什麼選這家的變體、什麼會讓它被換掉（附客戶端出處） | 在系統裡多重要（換不換得掉、替代技術、什麼會讓瓶頸鬆掉） |
| `claims[]` | ④每條主張登記成 watch | （B4 沒有；L7 三件套） |

之後要加段是**加字**（`SECTION_KEYS` 加一個鍵），不是搬資料（L2：表的形狀鎖死、字彙留鬆）。

**證據等級**：圖外的研究內容用封閉字彙（brainstorm §5.2）「一手／學理／產業報告／推一步／共識／媒體／沒有」；
圖上的內容沿用 `evidence_class`，兩者不另造第三套。**每句有出處或標「推一步」**——出處只認 `raw:<SourceDoc id>`
（`library/raw/<id>.txt`）或 `lead:<lead id>`，「推一步」與「沒有」可以不附出處但必須標明。出處指不指得回去由寫入端
（`alpha/providers/layer_notes.py`）機械核對；本檔只驗形狀（與 `alpha/structure_reading/contracts.py` 同一個分工）。
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping, Sequence

from alpha.errors import ContractViolation

RECORD_VERSION = "layer-note/v1"

#: 這份說明掛在哪種單位上：一個層（節點）或一個技術轉換（例：可插拔 → CPO）。
UNITS: tuple[str, ...] = ("layer", "transition")

#: 四段裡的前三段（文字＋出處）。第四段是 `claims[]`。**封閉字彙**——未登記的段鍵拒收。
SECTION_KEYS: tuple[str, ...] = ("physics", "variants", "selection")
SECTION_LABELS: Mapping[str, str] = {
    "physics": "①物理與變體",
    "variants": "②各家變體與階段",
    "selection": "③客戶為什麼選這家的變體、什麼會讓它被換掉",
}

#: 圖外研究內容的證據等級（brainstorm §5.2；封閉字彙）。
EVIDENCE_LEVELS: tuple[str, ...] = ("primary", "theory", "industry_report", "inference", "consensus", "media", "none")
EVIDENCE_LABELS: Mapping[str, str] = {
    "primary": "一手", "theory": "學理", "industry_report": "產業報告", "inference": "推一步",
    "consensus": "共識", "media": "媒體", "none": "沒有",
}
#: 可以不附出處的兩級（「推一步」要寫出是從哪裡推的，但那是文字，不是出處）。
_REF_OPTIONAL: frozenset[str] = frozenset({"inference", "none"})
#: 出處只認這兩種：SourceDoc（library/raw）與 lead registry。網址不算——網址會死、也不經過入庫紀律（L11、L18）。
CITATION_PREFIXES: tuple[str, ...] = ("raw:", "lead:")

#: 節點或轉換 id 的形狀：`前綴:snake_case`（轉換用 `transition:` 前綴）。
_NODE_RE = re.compile(r"^[a-z]+:[a-z0-9][a-z0-9_]*$")
MIN_SECTION_CHARS = 40
MIN_CLAIM_CHARS = 20

_ID_FIELDS = ("record_version", "node", "unit", "title", "created_at", "author", "expires", "reread_reason",
              "sections", "claims", "supersedes_id", "retracted", "body_ref")


@dataclass(frozen=True, slots=True)
class Citation:
    """一句話憑的出處。`ref` 可空只在證據等級是「推一步」或「沒有」時。"""

    evidence: str
    ref: str | None = None
    quote: str | None = None

    def __post_init__(self) -> None:
        if self.evidence not in EVIDENCE_LEVELS:
            raise ContractViolation(f"citation.evidence 未登記：{self.evidence!r}；已知 {list(EVIDENCE_LEVELS)}")
        if self.ref is None:
            if self.evidence not in _REF_OPTIONAL:
                raise ContractViolation(
                    f"citation 證據等級是「{EVIDENCE_LABELS[self.evidence]}」就必須附出處（raw:<SourceDoc id> 或 lead:<id>）")
        elif not str(self.ref).startswith(CITATION_PREFIXES) or len(str(self.ref).split(":", 1)[1].strip()) < 4:
            raise ContractViolation(f"citation.ref 只認 {list(CITATION_PREFIXES)} 開頭：{self.ref!r}")

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"evidence": self.evidence}
        if self.ref is not None:
            out["ref"] = self.ref
        if self.quote:
            out["quote"] = self.quote
        return out


def _citations(raw: Any, where: str) -> tuple[Citation, ...]:
    out = []
    for item in raw or ():
        if not isinstance(item, Mapping):
            raise ContractViolation(f"{where}.citations 的每一項必須是 object")
        ref = item.get("ref")
        quote = item.get("quote")
        out.append(Citation(evidence=str(item.get("evidence") or ""),
                            ref=str(ref) if ref not in (None, "") else None,
                            quote=str(quote) if quote else None))
    return tuple(out)


@dataclass(frozen=True, slots=True)
class Section:
    key: str
    text: str
    citations: tuple[Citation, ...]

    def __post_init__(self) -> None:
        if self.key not in SECTION_KEYS:
            raise ContractViolation(f"段鍵未登記：{self.key!r}；已知 {list(SECTION_KEYS)}")
        if len(" ".join(str(self.text).split())) < MIN_SECTION_CHARS:
            raise ContractViolation(f"{SECTION_LABELS[self.key]} 至少 {MIN_SECTION_CHARS} 字")
        if not self.citations:
            raise ContractViolation(f"{SECTION_LABELS[self.key]} 至少要有一個出處（或標「推一步」）")

    def as_dict(self) -> dict[str, Any]:
        return {"text": self.text, "citations": [c.as_dict() for c in self.citations]}


@dataclass(frozen=True, slots=True)
class Claim:
    """第四段的一條主張——寫下即登記成語意 watch（`layer_note:<note_id>#<n>`）。L7 三件套必填。"""

    claim: str
    condition: str
    entities: tuple[str, ...]
    check_frequency: str
    action_48h: str
    evidence: str
    citations: tuple[Citation, ...]
    expires: date | None = None

    def __post_init__(self) -> None:
        if len(str(self.claim).strip()) < MIN_CLAIM_CHARS:
            raise ContractViolation(f"claims[].claim 至少 {MIN_CLAIM_CHARS} 字")
        if len(str(self.condition).strip()) < MIN_CLAIM_CHARS:
            raise ContractViolation("claims[].condition（什麼會讓這條變假／什麼事件要叫醒）至少 20 字——它就是 watch 的條件原文")
        if not any(str(e).startswith("co:") for e in self.entities):
            raise ContractViolation("claims[].entities 至少要有一個 co:*——只寫 ticker 的 watch 叫不醒")
        if not str(self.check_frequency).strip() or not str(self.action_48h).strip():
            raise ContractViolation("claims[] 缺 L7 件：check_frequency 與 action_48h 都必填")
        if self.evidence not in EVIDENCE_LEVELS:
            raise ContractViolation(f"claims[].evidence 未登記：{self.evidence!r}")
        if not self.citations and self.evidence not in _REF_OPTIONAL:
            raise ContractViolation("claims[] 至少要有一個出處（證據等級是「推一步」或「沒有」除外）")

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"claim": self.claim, "condition": self.condition, "entities": list(self.entities),
                               "check_frequency": self.check_frequency, "action_48h": self.action_48h,
                               "evidence": self.evidence, "citations": [c.as_dict() for c in self.citations]}
        if self.expires is not None:
            out["expires"] = self.expires.isoformat()
        return out


def _claims(raw: Any) -> tuple[Claim, ...]:
    out = []
    for index, item in enumerate(raw or (), 1):
        if not isinstance(item, Mapping):
            raise ContractViolation("claims 的每一條必須是 object")
        expires = item.get("expires")
        out.append(Claim(
            claim=str(item.get("claim") or ""), condition=str(item.get("condition") or ""),
            entities=tuple(str(e) for e in (item.get("entities") or ())),
            check_frequency=str(item.get("check_frequency") or ""), action_48h=str(item.get("action_48h") or ""),
            evidence=str(item.get("evidence") or ""), citations=_citations(item.get("citations"), f"claims[{index}]"),
            expires=date.fromisoformat(str(expires)[:10]) if expires else None,
        ))
    return tuple(out)


@dataclass(frozen=True, slots=True)
class LayerNote:
    note_id: str
    node: str
    unit: str
    title: str
    created_at: str
    author: str
    expires: date | None
    reread_reason: str
    sections: Mapping[str, Section]
    claims: tuple[Claim, ...]
    supersedes_id: str | None = None
    retracted: bool = False
    body_ref: str | None = None
    record_version: str = RECORD_VERSION

    def __post_init__(self) -> None:
        if not _NODE_RE.match(self.node):
            raise ContractViolation(f"node 的形狀必須是 前綴:snake_case：{self.node!r}")
        if self.unit not in UNITS:
            raise ContractViolation(f"unit 未登記：{self.unit!r}；已知 {list(UNITS)}")
        if self.supersedes_id is not None and not str(self.supersedes_id).startswith("ln_"):
            raise ContractViolation(f"supersedes_id 必須是 ln_*：{self.supersedes_id!r}")
        if self.retracted:
            if not self.supersedes_id:
                raise ContractViolation("撤回（retracted）必須指名撤回哪一份（supersedes_id）")
            return
        if not str(self.title).strip():
            raise ContractViolation("title 必填")
        if self.expires is None:
            raise ContractViolation("expires（重讀日）必填——每份層說明都要有到期（INV-2）")
        if not str(self.reread_reason).strip():
            raise ContractViolation("reread_reason 必填：到期時要重看什麼")
        missing = [SECTION_LABELS[k] for k in SECTION_KEYS if k not in self.sections]
        if missing:
            raise ContractViolation(f"缺段：{'、'.join(missing)}")
        if self.body_ref is not None and not str(self.body_ref).startswith("library/private/research_notes/"):
            raise ContractViolation("body_ref 只能指向 library/private/research_notes/ 底下的全文")

    @property
    def current_claim_refs(self) -> tuple[str, ...]:
        return tuple(f"layer_note:{self.note_id}#{i}" for i in range(1, len(self.claims) + 1))


def new_note_id(payload: Mapping[str, Any]) -> str:
    """content-addressed id：同一份內容永遠得到同一個 id（重複 append 可被偵測）。"""
    body = {k: payload.get(k) for k in _ID_FIELDS}
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return "ln_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def layer_note_record(spec: Mapping[str, Any], *, created_at: datetime | str | None = None,
                      author: str = "session") -> dict[str, Any]:
    """spec（研究 session 寫的 JSON）→ 驗證過、帶 `note_id` 的 ledger 紀錄。任何一處不合形狀就整筆拒收。"""
    stamp = created_at.isoformat() if isinstance(created_at, datetime) else (created_at or datetime.now().astimezone().isoformat())
    sections_raw = spec.get("sections") or {}
    if not isinstance(sections_raw, Mapping):
        raise ContractViolation("sections 必須是 object（段鍵 → {text, citations}）")
    unknown = sorted(set(sections_raw) - set(SECTION_KEYS))
    if unknown:
        raise ContractViolation(f"段鍵未登記：{unknown}；已知 {list(SECTION_KEYS)}")
    record: dict[str, Any] = {
        "record_version": RECORD_VERSION,
        "node": str(spec.get("node") or "").strip(),
        "unit": str(spec.get("unit") or "layer"),
        "title": str(spec.get("title") or ""),
        "created_at": stamp,
        "author": author,
        "expires": str(spec.get("expires"))[:10] if spec.get("expires") else None,
        "reread_reason": str(spec.get("reread_reason") or ""),
        "sections": {k: {"text": str((v or {}).get("text") or ""),
                         "citations": [c.as_dict() for c in _citations((v or {}).get("citations"), k)]}
                     for k, v in sections_raw.items()},
        "claims": [c.as_dict() for c in _claims(spec.get("claims"))],
        "supersedes_id": spec.get("supersedes_id") or None,
        "retracted": bool(spec.get("retracted", False)),
        "body_ref": spec.get("body_ref") or None,
    }
    record["note_id"] = new_note_id(record)
    parse_layer_note_record(record)          # 形狀不合就在這裡 raise
    return record


def parse_layer_note_record(raw: Mapping[str, Any]) -> LayerNote:
    version = str(raw.get("record_version") or "")
    if version != RECORD_VERSION:
        raise ContractViolation(f"record_version 未登記：{version!r}；已知 {RECORD_VERSION}")
    sections_raw = raw.get("sections") or {}
    if not isinstance(sections_raw, Mapping):
        raise ContractViolation("sections 必須是 object")
    sections = {str(k): Section(key=str(k), text=str((v or {}).get("text") or ""),
                                citations=_citations((v or {}).get("citations"), str(k)))
                for k, v in sections_raw.items()}
    expires = raw.get("expires")
    note = LayerNote(
        note_id=str(raw.get("note_id") or ""), node=str(raw.get("node") or ""), unit=str(raw.get("unit") or ""),
        title=str(raw.get("title") or ""), created_at=str(raw.get("created_at") or ""),
        author=str(raw.get("author") or ""),
        expires=date.fromisoformat(str(expires)[:10]) if expires else None,
        reread_reason=str(raw.get("reread_reason") or ""), sections=sections, claims=_claims(raw.get("claims")),
        supersedes_id=raw.get("supersedes_id") or None, retracted=bool(raw.get("retracted", False)),
        body_ref=raw.get("body_ref") or None, record_version=version,
    )
    if not note.note_id.startswith("ln_") or note.note_id != new_note_id(raw):
        raise ContractViolation("note_id 對不上內容（被改過或手寫）——id 必須由 new_note_id 算")
    return note


def select_current(records: Sequence[LayerNote]) -> LayerNote | None:
    """一個節點的現行層說明：最新一份、沒有被取代、沒有被撤回。沒有就回 None（不猜）。"""
    superseded = {r.supersedes_id for r in records if r.supersedes_id}
    retracted = {r.supersedes_id for r in records if r.retracted and r.supersedes_id}
    live = [r for r in records if not r.retracted and r.note_id not in superseded and r.note_id not in retracted]
    return max(live, key=lambda r: r.created_at) if live else None


__all__ = [
    "CITATION_PREFIXES", "EVIDENCE_LABELS", "EVIDENCE_LEVELS", "RECORD_VERSION", "SECTION_KEYS", "SECTION_LABELS",
    "UNITS", "Citation", "Claim", "LayerNote", "Section", "layer_note_record", "new_note_id",
    "parse_layer_note_record", "select_current",
]
