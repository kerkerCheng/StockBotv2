"""`Abstention`——**「我們刻意不主張這一格」的 append-only 紀錄**。

## 它擁有什麼真相

只有一件事：**「對某一層的某個主題，現在沒有可辯護的假設，所以刻意不 assert」**。

它**不是**第二份 `ValuationAssumption` authority——後者擁有「目標倍數是幾」，而這裡
**結構上不可能**擁有任何數字：`_assert_no_value_fields` 在 import 當下掃描欄位名，
長出 `value`／`target_pe`／`multiple`／`fair_value`／`price` 之類的欄位是 **import 失敗**，
不是 lint 警告。所以「用 abstention 偷渡一個估值」在型別層就走不通。

## 為什麼要有它（2026-09-07 Coverage Pilot 實測）

6324.T 的估值 blocker 逐字是「尚未寫入任何估值假設」，而真實狀態是研究結論
**「126x 的隱含倍數錨不住任何可辯護的目標倍數，所以不寫」**。兩種語意共用一句話（L12），
下一個讀者——包括 APP 的使用者——無從分辨「還沒做」與「這已經是答案」。

## 三條硬要求

1. **`reason` 與 `revisit_when` 都必填。** 一條沒有「什麼證據出現才會改寫」的 abstention
   就是一個永遠不會響的火警警報（L7：disproof 要附核查頻率與觸發後動作）。
2. **append-only。** 改寫用新紀錄 `supersedes_id`，撤回 append 一筆 `retracted=true`；
   舊行永不改寫（L10：private ledger 沒有第二份來源）。
3. **`layer`／`subject` 是封閉字彙。** 沒登記的層不得宣告 abstention——否則它會變成
   「任何一格都可以宣布自己是刻意留白」的萬用擋箭牌。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields
from datetime import date, datetime, timezone
from typing import Any, Mapping, Sequence

from ..errors import ContractViolation

RECORD_VERSION = "abstention/v1"

#: 哪些層可以宣告「刻意不主張」。**contract 不是 taxonomy**——多一層就要多一段消費端語意。
#:
#: - `valuation`（v1）：唯一實測到「刻意不寫」與「還沒寫」被壓成同一句話的地方。
#: - `research`（2026-09-11 使用者核准）：研究軸。packet 的 `axis_prompts.catalyst.do_not`
#:   明文要求「找不到具體事件時回 unknown，**不要編一個**」，而 `unknown` 讓 catalysts 段
#:   `missing` → readiness `blocked`，於是**一個 session 越誠實，那一檔就越永久卡住**，
#:   `closure-gate` 還會一輪一輪把它重新提出來。研究做對了，系統卻沒有地方放這個結論。
#:   實測 GFS（2026-09-10）：bounded source-trace 找到的兩則 2026 年具名事件都**正確地**
#:   不具入圖資格（政府機關不符 Company node schema／無金額無產能的製造協議）。
#:
#: ⚠ 加層的代價寫在這裡：**多一層就要多一段消費端語意**，所以 `research` 只開一個 subject
#: （`axis.catalyst`），不是把五個軸一次打開——general 到資料支持的那一格為止（L17-4）。
ABSTENTION_LAYERS: tuple[str, ...] = ("valuation", "research")

#: 每一層可宣告的主題（method.parameter 形式，與 `METHOD_PARAMETERS` 對齊）。
ABSTENTION_SUBJECTS: Mapping[str, tuple[str, ...]] = {
    "valuation": ("forward_earnings_multiple.target_pe",),
    "research": ("axis.catalyst",),
}

#: 欄位名任何一段命中即 import 失敗——abstention 結構上不得攜帶任何數值主張。
FORBIDDEN_VALUE_TOKENS: frozenset[str] = frozenset({
    "value", "values", "multiple", "pe", "price", "eps", "target", "fair", "estimate",
    "forecast", "amount", "number", "score", "weight", "size", "position",
})


def _assert_no_value_fields(cls: type) -> None:
    for f in fields(cls):
        parts = set(f.name.lower().split("_"))
        banned = parts & FORBIDDEN_VALUE_TOKENS
        if banned:
            raise ContractViolation(
                f"{cls.__name__}.{f.name} 帶數值主張語意 {sorted(banned)}；"
                "Abstention 只說「我們刻意不主張」，任何數字必須住在它自己的 authority")


def _nonempty(text: Any, label: str) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ContractViolation(f"{label} 必須是非空字串")
    return text


@dataclass(frozen=True, slots=True)
class Abstention:
    """一筆「刻意不主張」。`period_end=None` ＝ 不綁會計期間（這一層對這檔股票整體不主張）。"""

    abstention_id: str
    company_id: str
    ticker: str
    layer: str
    subject: str
    reason: str
    revisit_when: str
    created_at: datetime
    period_end: date | None = None
    author: str = "session"
    evidence_refs: tuple[str, ...] = ()
    supersedes_id: str | None = None
    retracted: bool = False

    def __post_init__(self) -> None:
        _nonempty(self.abstention_id, "Abstention.abstention_id")
        if not self.abstention_id.startswith("ab_"):
            raise ContractViolation("abstention_id 必須以 ab_ 開頭（由 new_abstention_id 產生）")
        _nonempty(self.company_id, "Abstention.company_id")
        _nonempty(self.ticker, "Abstention.ticker")
        if self.layer not in ABSTENTION_LAYERS:
            raise ContractViolation(
                f"abstention layer 未登記：{self.layer!r}；已知 {ABSTENTION_LAYERS}——"
                "layer 是 contract：多一層就要多一段消費端語意")
        subjects = ABSTENTION_SUBJECTS[self.layer]
        if self.subject not in subjects:
            raise ContractViolation(f"layer {self.layer} 沒有 subject {self.subject!r}；已知 {subjects}")
        if not self.retracted:
            _nonempty(self.reason, "Abstention.reason")
            if len(self.reason.strip()) < 20:
                raise ContractViolation(
                    "Abstention.reason 太短——「刻意不主張」是研究結論，必須說得出為什麼錨不住")
            _nonempty(self.revisit_when, "Abstention.revisit_when")
            if len(self.revisit_when.strip()) < 10:
                raise ContractViolation(
                    "Abstention.revisit_when 必填且要具體：沒有「什麼證據出現才會改寫」的 abstention "
                    "是一個永遠不會響的火警警報（L7）")
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ContractViolation("created_at 必須是帶時區的 datetime")
        if self.period_end is not None and (not isinstance(self.period_end, date)
                                            or isinstance(self.period_end, datetime)):
            raise ContractViolation("Abstention.period_end 必須是 date 或 None")
        if any(not isinstance(r, str) or not r.strip() for r in self.evidence_refs):
            raise ContractViolation("evidence_refs 每一項必須是非空字串")

    @property
    def created_on(self) -> date:
        return self.created_at.astimezone(timezone.utc).date()

    @property
    def key(self) -> tuple[str, str, str | None]:
        """同一個 (layer, subject, period) 只有最新一筆生效。"""
        return (self.layer, self.subject, self.period_end.isoformat() if self.period_end else None)

    def to_display(self) -> dict[str, Any]:
        """給消費端看的最小投影——**不含檔案路徑**。"""
        return {
            "abstention_id": self.abstention_id, "layer": self.layer, "subject": self.subject,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "reason": self.reason, "revisit_when": self.revisit_when,
            "declared_on": self.created_on.isoformat(), "author": self.author,
        }


_assert_no_value_fields(Abstention)

_ID_FIELDS = ("company_id", "ticker", "layer", "subject", "period_end", "reason", "revisit_when",
              "created_at", "author", "evidence_refs", "supersedes_id", "retracted")


def new_abstention_id(payload: Mapping[str, Any]) -> str:
    """content-addressed id：同一份內容永遠得到同一個 id（重複 append 可被偵測）。"""
    body = {k: payload.get(k) for k in _ID_FIELDS}
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return "ab_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def abstention_record(
    *,
    company_id: str,
    ticker: str,
    layer: str,
    subject: str,
    reason: str,
    revisit_when: str,
    period_end: date | None = None,
    created_at: datetime | None = None,
    author: str = "session",
    evidence_refs: Sequence[str] = (),
    supersedes_id: str | None = None,
    retracted: bool = False,
) -> dict[str, Any]:
    """建一筆可寫進 ledger 的紀錄（先經 `Abstention` 驗證，驗不過就不產生）。"""
    stamp = created_at or datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        raise ContractViolation("created_at 必須帶時區")
    payload: dict[str, Any] = {
        "record_version": RECORD_VERSION,
        "company_id": str(company_id),
        "ticker": str(ticker).upper(),
        "layer": str(layer),
        "subject": str(subject),
        "period_end": period_end.isoformat() if period_end else None,
        "reason": str(reason),
        "revisit_when": str(revisit_when),
        "evidence_refs": [str(r) for r in evidence_refs],
        "created_at": stamp.astimezone(timezone.utc).isoformat(),
        "author": str(author),
        "supersedes_id": supersedes_id,
        "retracted": bool(retracted),
    }
    payload["abstention_id"] = new_abstention_id(payload)
    parse_abstention_record(payload)          # 驗證；不合法就在這裡炸，不會寫進 ledger
    return payload


def parse_abstention_record(raw: Mapping[str, Any]) -> Abstention:
    """dict → `Abstention`；任何欄位不合法都 raise `ContractViolation`。"""
    try:
        created = datetime.fromisoformat(str(raw["created_at"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractViolation(f"abstention 紀錄欄位不合法：{exc}") from None
    period_raw = raw.get("period_end")
    try:
        period = date.fromisoformat(str(period_raw)[:10]) if period_raw else None
    except ValueError as exc:
        raise ContractViolation(f"abstention period_end 不合法：{exc}") from None
    refs = raw.get("evidence_refs") or []
    if isinstance(refs, str):
        raise ContractViolation("evidence_refs 必須是 list")
    return Abstention(
        abstention_id=str(raw.get("abstention_id") or ""),
        company_id=str(raw.get("company_id") or ""),
        ticker=str(raw.get("ticker") or ""),
        layer=str(raw.get("layer") or ""),
        subject=str(raw.get("subject") or ""),
        reason=str(raw.get("reason") or ""),
        revisit_when=str(raw.get("revisit_when") or ""),
        created_at=created,
        period_end=period,
        author=str(raw.get("author") or "session"),
        evidence_refs=tuple(str(r) for r in refs),
        supersedes_id=(str(raw["supersedes_id"]) if raw.get("supersedes_id") else None),
        retracted=bool(raw.get("retracted")),
    )


def select_abstention(
    records: Sequence[Abstention],
    *,
    layer: str,
    subject: str,
    period_end: date | None,
    as_of: date | None,
    today: date,
) -> Abstention | None:
    """as-of 視角下對這個 (layer, subject, period) 生效的那一筆；沒有就是 `None`。

    選取規則與假設 ledger **同一套**：`created_on <= 視角日` → 同 key 取最新 →
    最新那筆是 `retracted` 就等於沒有。`period_end=None` 的紀錄涵蓋任何期間（整層不主張）。
    """
    cutoff = as_of or today
    visible = [r for r in records
               if r.created_on <= cutoff and r.layer == layer and r.subject == subject]
    scoped = [r for r in visible if r.period_end is None or r.period_end == period_end]
    if not scoped:
        return None
    latest = max(scoped, key=lambda r: (r.created_at, r.abstention_id))
    return None if latest.retracted else latest


__all__ = [
    "ABSTENTION_LAYERS", "ABSTENTION_SUBJECTS", "Abstention", "FORBIDDEN_VALUE_TOKENS",
    "RECORD_VERSION", "abstention_record", "new_abstention_id", "parse_abstention_record",
    "select_abstention",
]
