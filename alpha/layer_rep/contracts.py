"""層代表公司宣告（layer representatives）的紀錄契約——個股頁 S3c（使用者 2026-10-09 決定 ②A）。

**這是什麼：** 研究替一層宣告「用誰的營收代表這一層的成長」。個股頁 B2「路徑上各層」據此把代表公司同一曆季的營收
（換美元）加總、算年增。主鍵是節點 id，同層每一頁共用（schema 規則 1：層的知識掛在節點上）。
它是研究判斷（A3）：append-only、可換版、**不入圖**（誰代表一層不是圖上的事實，L4）、不 gate、不排序、不給尺寸。

**為什麼另一本 ledger，不放進層說明紀錄**（2026-10-09 決定紀錄，個股頁 plan Amendment G；使用者 A 的原文是「寫在層說明裡」）：
①路徑上頁數最多的層（CPO、CW DFB、CDU）還沒有層說明，寫在層說明裡等於要先寫完四段才能宣告；②只為換代表公司而讓
層說明換版，會把該層所有主張的 watch 收掉重登、讓敘事反證連到的層主張變成非現行。閱讀時照樣印在那一層的頁上。

**不是什麼：** 不是「同階段同業」（B2「份額（現在）」的分母）——代表公司是刻意挑過的子集，兩者不得共用（L12）。
「刻意不宣告」不由這本 ledger 表達（刻意不主張只來自 Abstention 紀錄）。

**現行（`select_current`）**：只看 as-of 那天以前寫下的紀錄、取最新一筆；最新一筆是撤回＝沒有現行（舊版不復活）。
as-of T 時還沒有宣告，就是「這個時點還沒宣告」——不拿今天的宣告冒充過去（INV-6）。

本檔只驗形狀；出處指不指得回去、公司在不在名冊、同一家同口徑有沒有已經代表別的層，由寫入端
（`alpha/providers/layer_reps.py`）核對。
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Mapping, Sequence

from alpha.errors import ContractViolation
from alpha.layer_note.contracts import Citation

RECORD_VERSION = "layer-reps/v1"

#: 營收口徑（封閉字彙；日後加產品線口徑是加字，L2）。
SCOPES: tuple[str, ...] = ("whole_company", "segment")
SCOPE_LABELS: Mapping[str, str] = {"whole_company": "全公司營收", "segment": "分部營收"}
#: 不收的節點前綴：公司節點直接用它自己的營收（不需宣告）；技術轉換不在路徑上。
REFUSED_PREFIXES: tuple[str, ...] = ("co:", "transition:")
MIN_WHY_CHARS = 20

_CITATION_KEYS = frozenset({"evidence", "ref", "quote"})
_REP_KEYS = frozenset({"company_id", "scope", "segment", "why", "citations"})
_SPEC_KEYS = frozenset({"node", "expires", "reread_reason", "representatives", "supersedes_id", "retracted", "author"})
_NODE_RE = re.compile(r"^[a-z]+:[a-z0-9][a-z0-9_]*$")
_ID_FIELDS = ("record_version", "node", "created_at", "author", "expires", "reread_reason", "representatives",
              "supersedes_id", "retracted")


def _unknown(raw: Mapping[str, Any], allowed: frozenset[str], where: str) -> None:
    extra = sorted(set(raw) - allowed)
    if extra:
        raise ContractViolation(f"{where} 有未登記的欄位 {extra}——不收（會被靜默丟掉的欄位不如一開始就拒收）")


def _utc(value: Any) -> datetime:
    try:
        stamp = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise ContractViolation(f"created_at 不是 ISO 時間：{value!r}") from exc
    if stamp.tzinfo is None:
        raise ContractViolation(f"created_at 必須帶時區：{value!r}")
    return stamp.astimezone(timezone.utc)


def _citations(raw: Any, where: str) -> tuple[Citation, ...]:
    out = []
    for item in raw or ():
        if not isinstance(item, Mapping):
            raise ContractViolation(f"{where}.citations 的每一項必須是 object")
        _unknown(item, _CITATION_KEYS, f"{where}.citations")
        ref, quote = item.get("ref"), item.get("quote")
        out.append(Citation(evidence=str(item.get("evidence") or ""), ref=str(ref) if ref not in (None, "") else None,
                            quote=str(quote) if quote else None))
    return tuple(out)


@dataclass(frozen=True, slots=True)
class Representative:
    """一家代表公司：用它的哪一種營收、為什麼它代表這一層、憑什麼。不存 ticker（INV-1：代號由名冊推）。"""

    company_id: str
    scope: str
    why: str
    citations: tuple[Citation, ...]
    segment: str | None = None

    def __post_init__(self) -> None:
        if not str(self.company_id).startswith("co:"):
            raise ContractViolation(f"representatives[].company_id 必須是 co:*（名冊 id，不是 ticker）：{self.company_id!r}")
        if self.scope not in SCOPES:
            raise ContractViolation(f"representatives[].scope 未登記：{self.scope!r}；已知 {list(SCOPES)}")
        if self.scope == "segment":
            if not str(self.segment or "").strip():
                raise ContractViolation("scope=segment 必須寫 segment（文件寫的分部名稱，逐字）")
            # 分部名稱要逐字出現在這一家某個帶出處的引文裡（L6／L18：標籤要指得回原文）
            if not any(c.ref and c.quote and str(self.segment) in c.quote for c in self.citations):
                raise ContractViolation(f"分部名稱「{self.segment}」沒有逐字出現在任何帶出處的引文裡")
        elif self.segment is not None:
            raise ContractViolation("scope=whole_company 不得帶 segment（一個欄位不承載兩種口徑，L12）")
        if len(" ".join(str(self.why).split())) < MIN_WHY_CHARS:
            raise ContractViolation(f"representatives[].why 至少 {MIN_WHY_CHARS} 字：為什麼它的營收代表這一層、不能代表的是什麼")
        if not self.citations:
            raise ContractViolation("representatives[] 至少要有一個出處（或標「推一步」並寫從哪裡推）")

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"company_id": self.company_id, "scope": self.scope, "why": self.why,
                               "citations": [c.as_dict() for c in self.citations]}
        if self.segment is not None:
            out["segment"] = self.segment
        return out


def _representatives(raw: Any) -> tuple[Representative, ...]:
    if raw is not None and not isinstance(raw, (list, tuple)):
        raise ContractViolation("representatives 必須是清單")
    out = []
    for index, item in enumerate(raw or (), 1):
        if not isinstance(item, Mapping):
            raise ContractViolation("representatives 的每一項必須是 object")
        _unknown(item, _REP_KEYS, f"representatives[{index}]")
        segment = item.get("segment")
        out.append(Representative(
            company_id=str(item.get("company_id") or ""), scope=str(item.get("scope") or ""),
            why=str(item.get("why") or ""), citations=_citations(item.get("citations"), f"representatives[{index}]"),
            segment=str(segment) if segment not in (None, "") else None))
    return tuple(out)


@dataclass(frozen=True, slots=True)
class LayerRepresentatives:
    rep_id: str
    node: str
    created_at: datetime
    author: str
    expires: date | None
    reread_reason: str
    representatives: tuple[Representative, ...]
    supersedes_id: str | None = None
    retracted: bool = False
    record_version: str = RECORD_VERSION

    def __post_init__(self) -> None:
        if not _NODE_RE.match(self.node):
            raise ContractViolation(f"node 的形狀必須是 前綴:snake_case：{self.node!r}")
        if self.node.startswith(REFUSED_PREFIXES):
            raise ContractViolation(f"{self.node} 不收：公司節點直接用它自己的營收（不需宣告）、技術轉換不在路徑上")
        if self.supersedes_id is not None and not str(self.supersedes_id).startswith("lr_"):
            raise ContractViolation(f"supersedes_id 必須是 lr_*：{self.supersedes_id!r}")
        if self.retracted:
            if not self.supersedes_id:
                raise ContractViolation("撤回（retracted）必須指名撤回哪一份（supersedes_id）")
            if self.representatives:
                raise ContractViolation("撤回紀錄不得帶代表公司")
            return
        if not self.representatives:
            raise ContractViolation("至少宣告一家代表公司——「刻意不宣告」要走 Abstention 紀錄，不是空清單")
        ids = [r.company_id for r in self.representatives]
        if len(ids) != len(set(ids)):
            raise ContractViolation("同一份裡同一家公司只能出現一次（不同時以全公司與分部出現，避免重複計入）")
        if self.expires is None:
            raise ContractViolation("expires（重看日）必填——每份宣告都要有到期（INV-2）")
        if self.expires <= self.created_at.date():
            raise ContractViolation("expires（重看日）必須晚於寫入日")
        if not str(self.reread_reason).strip():
            raise ContractViolation("reread_reason 必填：到期時要重看什麼")


def new_rep_id(payload: Mapping[str, Any]) -> str:
    """content-addressed id（含寫入時間）：改內容即對不上（防竄改；與層說明同一個設計）。"""
    body = {k: payload.get(k) for k in _ID_FIELDS}
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return "lr_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def layer_reps_record(spec: Mapping[str, Any], *, created_at: datetime | str | None = None,
                      author: str = "session") -> dict[str, Any]:
    """spec（研究 session 寫的 JSON）→ 驗證過、帶 `rep_id` 的 ledger 紀錄。寫入時間由這裡蓋（spec 不收 created_at）。"""
    _unknown(spec, _SPEC_KEYS, "spec")
    stamp = _utc(created_at if created_at is not None else datetime.now(timezone.utc)).isoformat()
    record: dict[str, Any] = {
        "record_version": RECORD_VERSION,
        "node": str(spec.get("node") or "").strip(),
        "created_at": stamp,
        "author": author,
        "expires": str(spec.get("expires"))[:10] if spec.get("expires") else None,
        "reread_reason": str(spec.get("reread_reason") or ""),
        "representatives": [r.as_dict() for r in _representatives(spec.get("representatives"))],
        "supersedes_id": spec.get("supersedes_id") or None,
        "retracted": bool(spec.get("retracted", False)),
    }
    record["rep_id"] = new_rep_id(record)
    parse_layer_reps_record(record)
    return record


def parse_layer_reps_record(raw: Mapping[str, Any]) -> LayerRepresentatives:
    version = str(raw.get("record_version") or "")
    if version != RECORD_VERSION:
        raise ContractViolation(f"record_version 未登記：{version!r}；已知 {RECORD_VERSION}")
    expires = raw.get("expires")
    parsed = LayerRepresentatives(
        rep_id=str(raw.get("rep_id") or ""), node=str(raw.get("node") or ""), created_at=_utc(raw.get("created_at")),
        author=str(raw.get("author") or ""), expires=date.fromisoformat(str(expires)[:10]) if expires else None,
        reread_reason=str(raw.get("reread_reason") or ""), representatives=_representatives(raw.get("representatives")),
        supersedes_id=raw.get("supersedes_id") or None, retracted=bool(raw.get("retracted", False)),
        record_version=version)
    if not parsed.rep_id.startswith("lr_") or parsed.rep_id != new_rep_id(raw):
        raise ContractViolation("rep_id 對不上內容（被改過或手寫）——id 必須由 new_rep_id 算")
    return parsed


def select_current(records: Sequence[LayerRepresentatives], *, as_of: date | None = None) -> LayerRepresentatives | None:
    """一個節點在 as-of 那天的現行宣告：只看那天以前寫下的、取最新一筆；最新一筆是撤回＝沒有現行（INV-6）。"""
    seen = [r for r in records if as_of is None or r.created_at.date() <= as_of]
    if not seen:
        return None
    latest = max(seen, key=lambda r: (r.created_at, r.rep_id))
    return None if latest.retracted else latest


__all__ = ["MIN_WHY_CHARS", "RECORD_VERSION", "REFUSED_PREFIXES", "SCOPES", "SCOPE_LABELS", "LayerRepresentatives",
           "Representative", "layer_reps_record", "new_rep_id", "parse_layer_reps_record", "select_current"]
