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


# ---------------------------------------------------------------------------
# 量測基準：每一列用自己所屬的組（多主題等權組 S1，plan 2026-10-05-002 選項 A，使用者 2026-10-06）
# ---------------------------------------------------------------------------

#: 「這一列跟哪一組比」答不出來時的缺席種類——追蹤表與計分表共用，由這一支宣告（L16），消費端不得從 reason 猜。
#: 先前（Phase 5 Step 5.2–5.5）是「全域一組」：只有一組時每一列都跟它比、多於一組整格 `ambiguous_cohort`——
#: 非組員（稀土、機器人、記憶體）也拿光通訊籃子當基準，一個欄位承載「同題材比較」與「跨題材比較」兩種語意（L12）。
ROW_COHORT_ABSENCES: Mapping[str, str] = {
    "not_yet_recorded": "主題等權組一組都還沒定義（pq2 complete-theme-cohort 才寫得進來）",
    "not_in_any_cohort": "這一檔不是任何主題等權組的組員——不借別的題材的組；補的路是替它的題材定組（研究）",
    "ambiguous_membership": "這一檔同時是兩組以上的組員——哪一組適用不由程式猜",
    "identity_unresolved": "這一列沒有 company_id——不拿 ticker 猜組員（INV-1）",
    # 以下三種是「是組員（或組 ledger 讀壞），但這一格算不出來」——不是「不是組員」（R2 2026-10-06 C2：對稱面）
    "theme_cohort_unpriced": "這一檔是組員，但組裡其他成員在這段期間都取不到價——不是 0",
    "no_measurement_window": "這一列有報酬但沒有起訖日——組報酬的窗算不出來（不猜）",
    "upstream_unavailable": "主題等權組 ledger 讀不到——上游缺席，不是「不是組員」",
}
#: 給人看的短標籤（APP、心跳、markdown 共用）。**跟著資料走**（每一筆缺席與每份摘要都帶），消費端不另寫一份對照表（L16）。
ROW_COHORT_ABSENCE_LABELS: Mapping[str, str] = {
    "not_yet_recorded": "還沒有組",
    "not_in_any_cohort": "不是任何組的組員",
    "ambiguous_membership": "同時屬於多組，不猜",
    "identity_unresolved": "身分未解析",
    "theme_cohort_unpriced": "組員都取不到價",
    "no_measurement_window": "沒有起訖日",
    "upstream_unavailable": "組讀不到",
}
#: 「不是組員」的那幾種——計分表判斷「等時間」只看組員點名時，要排除的就是這幾種（組員但組報酬取不到的不在裡面）。
NON_MEMBER_KINDS: frozenset[str] = frozenset({"not_in_any_cohort", "ambiguous_membership", "identity_unresolved"})


def cohort_absence(kind: str, **extra: Any) -> dict[str, Any]:
    """一筆具名缺席 `{kind, label, reason, ...}`——種類、標籤、理由都從上面兩張表取（產生缺席的程式宣告，L16）。"""
    if kind not in ROW_COHORT_ABSENCES:
        raise ContractViolation(f"未登記的主題等權組缺席種類 {kind!r}；只收 {sorted(ROW_COHORT_ABSENCES)}")
    return {"kind": kind, "label": ROW_COHORT_ABSENCE_LABELS[kind],
            "reason": str(extra.pop("reason", None) or ROW_COHORT_ABSENCES[kind]), **extra}


def summarize_cohorts(cohorts: Sequence[ThemeCohort], errors: Sequence[str]) -> dict[str, Any]:
    """現行各組的來歷（追蹤表與計分表共用）：`{mode, cohorts: [{cohort_id, theme, decided_on, members, members_total}],
    absence, absence_labels, parse_errors}`。一組都沒有＝`not_yet_recorded`；壞行原樣帶出（INV-3）。**哪一列用哪一組不在這裡**——
    那是 `cohort_for_row` 的事，這裡只說「有哪些組」。"""
    info: dict[str, Any] = {
        "mode": "per_row",
        "cohorts": [{"cohort_id": c.cohort_id, "theme": c.theme, "decided_on": c.decided_on.isoformat(),
                     "members": [m.ticker for m in c.members], "members_total": len(c.members)} for c in cohorts],
        "absence": None, "absence_labels": dict(ROW_COHORT_ABSENCE_LABELS), "parse_errors": list(errors)}
    if not cohorts:
        info["absence"] = cohort_absence("not_yet_recorded")
    return info


def cohort_for_row(cohorts: Sequence[ThemeCohort], *, company_id: str | None
                   ) -> tuple[ThemeCohort | None, dict[str, Any] | None]:
    """這一列跟哪一組比：以 `company_id` 比對組員（INV-1：ticker 不是 identity）。追蹤表與計分表共用這一支
    （plan §12 #4：「哪一組是基準」只有一個答案——答案從「全域一組」縮到「這一列」）。

    1 組＝`(組, None)`；0 組＝`not_in_any_cohort`；≥2 組＝`ambiguous_membership`（列出組 id，不猜）；
    沒有 company_id＝`identity_unresolved`；一組都還沒定義＝`not_yet_recorded`。"""
    if not cohorts:
        return None, cohort_absence("not_yet_recorded")
    cid = str(company_id or "").strip()
    if not cid:
        return None, cohort_absence("identity_unresolved")
    hits = [c for c in cohorts if any(m.company_id == cid for m in c.members)]
    if len(hits) == 1:
        return hits[0], None
    if not hits:
        return None, cohort_absence("not_in_any_cohort")
    return None, cohort_absence("ambiguous_membership", cohort_ids=[c.cohort_id for c in hits])


def _usable_close(value: Any) -> bool:
    """收盤能不能用：數字、不是 NaN、正數。yfinance 會對尚未收盤的歐洲標的回一根 NaN 收盤（2026-10-01：IQE.L、SIVE.ST…），
    混進來的話等權平均與中位數都會被靜默污染（NaN 不等於自己，排序結果不確定）。"""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and value > 0


def close_on_or_before(series: Mapping[date, float] | None, day: date) -> tuple[date, float] | None:
    """`day` 或之前最近的一根**可用**收盤（INV-6：錨點不得用之後的價）。沒有就 `None`。"""
    candidates = [d for d, v in (series or {}).items() if d <= day and _usable_close(v)]
    if not candidates:
        return None
    best = max(candidates)
    return best, float((series or {})[best])


def series_return(series: Mapping[date, float] | None, start: date, end: date) -> float | None:
    """同一條收盤序列 `start`→`end` 的報酬：兩端各取該日或之前最近的可用收盤；**同序列相除，報價單位自動相消**
    （GBp 不必先換成 GBP）。任一端取不到、起點那根晚於終點那根、或**要求的起點本身就晚於終點**，回 `None`——不是 0。

    ⚠ 最後一條是 R2（2026-10-06 F3）找到的：錨點 10-05、終點 10-02（最後一根）時，兩端都落在 10-02 那一根，
    K 棒日期相同所以舊的比法放行、算出 0.0——窗是倒過來的，那不是「沒漲」，是「還量不到」。"""
    if start > end:
        return None
    a = close_on_or_before(series, start)
    b = close_on_or_before(series, end)
    if a is None or b is None or a[0] > b[0]:
        return None
    return b[1] / a[1] - 1.0


def cohort_return(cohort: ThemeCohort, *, start: date, end: date, series: Mapping[str, Mapping[date, float]],
                  exclude_company: str | None = None, exclude_ticker: str | None = None) -> dict[str, Any]:
    """主題等權組（**排除本檔**）在 `start`→`end` 的等權報酬——追蹤表與計分表共用這一支（plan §12 #4：一個函式）。

    每個成員用自己的序列算 `series_return`，取不到的成員**列出、不進平均**；本檔以 `company_id`（INV-1）或研究 ticker
    比對排除。回 `{return, members_total, members_used, missing, excluded}`——`members_total` 是排除本檔之後的成員數；
    一個都取不到時 `return` 是 `None`（缺席），不是 0。**只算、不比、不設門檻**（plan 不可越線 4）。"""
    company = str(exclude_company or "")
    ticker = str(exclude_ticker or "").strip().upper()
    excluded = [m.ticker for m in cohort.members
                if (company and m.company_id == company) or (ticker and m.ticker.upper() == ticker)]
    pool = [m for m in cohort.members if m.ticker not in excluded]
    returns: list[float] = []
    missing: list[str] = []
    for member in pool:
        value = series_return(series.get(member.ticker), start, end)
        if value is None:
            missing.append(member.ticker)
        else:
            returns.append(value)
    return {
        "return": (sum(returns) / len(returns)) if returns else None,
        "members_total": len(pool),
        "members_used": len(returns),
        "missing": missing,
        "excluded": excluded,
    }


__all__ = ["NON_MEMBER_KINDS", "RECORD_VERSION", "ROW_COHORT_ABSENCES", "ROW_COHORT_ABSENCE_LABELS", "SPEC_FIELDS",
           "CohortMember", "ThemeCohort", "close_on_or_before", "cohort_absence", "cohort_for_row", "cohort_record",
           "cohort_return", "new_cohort_id", "parse_cohort_record", "select_current", "series_return", "spec_digest",
           "summarize_cohorts", "validate_spec"]
