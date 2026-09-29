"""主題等權組（theme cohort）的契約（Phase 3 Step 3.3，ROADMAP amendment A2）。

「已定價嗎」的第二、三行要一個**同題材的對照組**：組的中位數倍數、相對組的 30／90 日漲幅。
決定紀錄 §4.2：這個組的定義與 Phase 5 量測基準（G9）**共用同一個**；§6.7：成分是一個判斷，
寫下時附理由與日期，變動 append-only。

## 三條規則

1. **append-only、content-addressed。** 成分變動＝新紀錄（`supersedes_id` 指舊的），舊紀錄一字不改。
2. **成分是判斷，寫入綁使用者的 go。** 研究步驟把成分 spec 凍結進一個 pq2 編號（digest 一起存），使用者 go 之後
   唯一的寫入入口是 `python -m engine_b.todo complete-theme-cohort <n>`——它讀**凍結的那一份**、比對 digest 才寫，
   bare `go` 拒收。核准的東西＝寫進去的東西（比照 `ra_admission`）。
3. **等權、不排序。** 組內沒有權重、沒有名次；中位數與平均只當脈絡印（`alpha/three_questions.py`）。

⚠ 名字刻意不沿用 Phase 0 退役的那個 filter 的名字（殭屍 grep B 組會攔）：這裡一律叫「主題等權組」／`theme_cohort`。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Mapping, Sequence

from .errors import ContractViolation

RECORD_VERSION = "theme-cohort/v1"
_ID_FIELDS = ("theme", "members", "excluded", "reason", "decided_on", "pq2_ref", "supersedes_id",
              "created_at", "author")
#: spec（凍結進 pq2 的那一份）的欄位。`decided_on`／`pq2_ref`／`created_at` 由寫入端補，不在 spec 裡。
SPEC_FIELDS = ("theme", "members", "excluded", "reason", "supersedes_id")


@dataclass(frozen=True)
class CohortMember:
    ticker: str
    company_id: str
    reason: str


@dataclass(frozen=True)
class ThemeCohort:
    cohort_id: str
    theme: str
    members: tuple[CohortMember, ...]
    excluded: tuple[Mapping[str, str], ...]
    reason: str
    decided_on: date
    pq2_ref: int
    created_at: datetime
    author: str = "session"
    supersedes_id: str | None = None
    record_version: str = RECORD_VERSION
    extra: Mapping[str, Any] = field(default_factory=dict)

    @property
    def tickers(self) -> tuple[str, ...]:
        return tuple(m.ticker for m in self.members)


def _nonempty(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ContractViolation(f"{label} 必填")
    return text


def validate_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    """研究步驟寫的 spec → 正規化後的 spec（**不查 registry**——身分解析在 provider）。不合法就 raise。"""
    unknown = sorted(set(spec) - set(SPEC_FIELDS))
    if unknown:
        raise ContractViolation(f"theme cohort spec 有未登記的欄位 {unknown}；只收 {list(SPEC_FIELDS)}")
    theme = _nonempty(spec.get("theme"), "theme")
    reason = _nonempty(spec.get("reason"), "reason（整組為什麼這樣選）")
    raw_members = spec.get("members")
    if not isinstance(raw_members, (list, tuple)) or len(raw_members) < 2:
        raise ContractViolation("members 至少兩檔（一檔沒有「組」可言）")
    members = []
    seen: set[str] = set()
    for m in raw_members:
        if not isinstance(m, Mapping):
            raise ContractViolation("members 每一項必須是 {ticker, company_id, reason}")
        ticker = _nonempty(m.get("ticker"), "members[].ticker").upper()
        cid = _nonempty(m.get("company_id"), f"members[{ticker}].company_id")
        why = _nonempty(m.get("reason"), f"members[{ticker}].reason（入選理由一句）")
        if not cid.startswith("co:"):
            raise ContractViolation(f"members[{ticker}].company_id 必須是 co:*（收到 {cid!r}）")
        if ticker in seen:
            raise ContractViolation(f"members 重複：{ticker}")
        seen.add(ticker)
        members.append({"ticker": ticker, "company_id": cid, "reason": why})
    raw_excluded = spec.get("excluded")
    if not isinstance(raw_excluded, (list, tuple)):
        raise ContractViolation("excluded 必填（排除了誰與為什麼；一個都沒排除就寫空 list 並在 reason 說明）")
    excluded = []
    for e in raw_excluded:
        if not isinstance(e, Mapping):
            raise ContractViolation("excluded 每一項必須是 {name, reason}")
        excluded.append({"name": _nonempty(e.get("name"), "excluded[].name"),
                         "reason": _nonempty(e.get("reason"), "excluded[].reason")})
    supersedes = spec.get("supersedes_id")
    if supersedes is not None and not str(supersedes).startswith("tc_"):
        raise ContractViolation("supersedes_id 必須是 tc_ 開頭的既有 cohort_id")
    return {"theme": theme, "members": members, "excluded": excluded, "reason": reason,
            "supersedes_id": (str(supersedes) if supersedes else None)}


def spec_digest(spec: Mapping[str, Any]) -> str:
    """凍結 spec 的 digest（鑄號時記、寫入時比對）。"""
    canonical = json.dumps(validate_spec(spec), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def new_cohort_id(payload: Mapping[str, Any]) -> str:
    body = {k: payload.get(k) for k in _ID_FIELDS}
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return "tc_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def cohort_record(spec: Mapping[str, Any], *, pq2_ref: int, decided_on: date,
                  created_at: datetime | None = None, author: str = "session") -> dict[str, Any]:
    """凍結 spec＋寫入端補的三欄 → 一筆可寫進 ledger 的紀錄（先驗證）。"""
    clean = validate_spec(spec)
    if not isinstance(pq2_ref, int) or pq2_ref <= 0:
        raise ContractViolation("pq2_ref 必須是正整數編號")
    stamp = (created_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    payload = {"record_version": RECORD_VERSION, **clean, "decided_on": decided_on.isoformat(),
               "pq2_ref": pq2_ref, "created_at": stamp.isoformat(), "author": author}
    payload["cohort_id"] = new_cohort_id(payload)
    parse_cohort_record(payload)
    return payload


def parse_cohort_record(raw: Mapping[str, Any]) -> ThemeCohort:
    try:
        created = datetime.fromisoformat(str(raw["created_at"]).replace("Z", "+00:00"))
        decided = date.fromisoformat(str(raw["decided_on"])[:10])
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractViolation(f"theme cohort 紀錄欄位不合法：{exc}") from None
    clean = validate_spec({k: raw.get(k) for k in SPEC_FIELDS})
    cohort_id = str(raw.get("cohort_id") or "")
    if not cohort_id.startswith("tc_"):
        raise ContractViolation("cohort_id 必須以 tc_ 開頭")
    return ThemeCohort(
        cohort_id=cohort_id, theme=clean["theme"],
        members=tuple(CohortMember(m["ticker"], m["company_id"], m["reason"]) for m in clean["members"]),
        excluded=tuple(clean["excluded"]), reason=clean["reason"], decided_on=decided,
        pq2_ref=int(raw.get("pq2_ref") or 0), created_at=created, author=str(raw.get("author") or "session"),
        supersedes_id=clean["supersedes_id"], record_version=str(raw.get("record_version") or RECORD_VERSION))


def select_current(records: Sequence[ThemeCohort], *, as_of: date | None = None) -> ThemeCohort | None:
    """同一本 ledger（一個題材）裡 as-of 生效的那一份：`decided_on ≤ T`、最新者勝出。"""
    visible = [r for r in records if as_of is None or r.decided_on <= as_of]
    if not visible:
        return None
    return sorted(visible, key=lambda r: (r.created_at, r.cohort_id))[-1]


__all__ = ["RECORD_VERSION", "SPEC_FIELDS", "CohortMember", "ThemeCohort", "cohort_record", "new_cohort_id",
           "parse_cohort_record", "select_current", "spec_digest", "validate_spec"]
