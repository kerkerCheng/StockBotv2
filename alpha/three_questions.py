"""財務三題（Phase 3 Step 3.3）：**會死嗎／已定價嗎／出現在數字裡了嗎**——判定只住這裡，取數在 Engine C。

純函式，零相依、不連 DB（比照 `alpha/wipeout.py`）。輸入由 `engine_c.three_question_inputs.get_three_question_inputs`
組好帶進來；輸出每一行都是 `{value, source, as_of, basis（口徑）, rule}` **或** `absence_kind`（封閉字彙，
`alpha.absence`），兩者不同時出現（L12：燈滅與燈綠不同形）。

## 三條不可退讓的設計判準（ROADMAP「明確不做」、決定紀錄 §4）

1. **不長回估值模型。** 不算目標價、不算報酬期望、不對同業倍數校準、**不設「已定價」門檻**。
   ①自家歷史百分位是**自己跟自己比**；②主題等權組中位數與③相對組漲幅**只印、不比較、不算差**。
   本檔沒有任何布林結論欄位——「是／否」由寫敘事的人宣告（使用者定案 #5），程式只印數字並強制引用。
2. **今天那一點與歷史每一點用同一個函式算。** 不讀 `financial_snapshots.ev_revenue`（yfinance 口徑）：
   兩個口徑混著比，百分位就是在比口徑差（2026-09-19 的 IQE.L 單位事故同一個形狀）。
3. **T 時刻知道什麼。** 每一天的倍數只用當天之前已申報（`filed ≤ d`）的財報、當天的收盤、當天的股數
   （封面股數再乘上之後的分割）；月營收只用過了法定期限的月份（`engine_c.history`）。

## 口徑由今天決定、整條序列同一口徑

今天 TTM 營業利益 ≥ 0 **且**有同期淨負債 → EV/S；否則 P/S。台股沒有營業利益 → 一律 P/S。口徑寫在 `basis`。
"""
from __future__ import annotations

from datetime import date, timedelta
from statistics import median
from typing import Any, Iterable, Mapping, Sequence

#: 三題的封閉清單（鍵＝API 契約）。
QUESTIONS: tuple[str, ...] = ("will_it_die", "priced_in", "in_numbers")
QUESTION_LABELS: Mapping[str, str] = {
    "will_it_die": "會死嗎", "priced_in": "已定價嗎", "in_numbers": "出現在數字裡了嗎",
}

#: 自家歷史的窗：3 年。窗不滿（剛上市、分拆、回填不夠）→ `insufficient_evidence` 並印實際窗長。
HISTORY_YEARS = 3
#: 窗長容許的短缺：回填從「今天 − 3 年 − 30 天」起抓，第一個交易日可能晚幾天；超過 30 天短缺才算不滿。
HISTORY_SLACK_DAYS = 30
#: 最後一點太舊就不算「今天」：沿用 Engine C 快照的既有鮮度判準（`alpha/providers/fundamentals.py::_freshness`，14 天）。
PRICE_FRESH_DAYS = 14
#: 相對組漲幅的兩個窗（本檔自己的交易日數）。
RELATIVE_WINDOWS: tuple[int, ...] = (30, 90)
#: 季度連續的判準：相鄰兩季 period_end 相距 80–100 天（13／14 週季度都落在裡面）。
_QUARTER_GAP = (80, 100)
#: TTM 與淨負債的最新一期距 d 最多多舊（天）：一季（~91 天）＋申報期限與緩衝。超過＝那一天的財報已經過期，
#: 樣本不算（2026-09-29 Step 3.5 試跑：COHR 的營業利益 tag 停在 2024-06，舊版拿兩年前的 TTM 當「今天」判成 EV/S）。
FUNDAMENTAL_MAX_AGE_DAYS = 200

_RULE_OWN = (
    "每個交易日 d：市值＝當天 raw 收盤 ×（d 之前最新一份封面股數 × 其後到 d 的分割比例）；"
    "TTM 營收＝d 之前已申報（filed ≤ d）的最近四個連續季度；EV＝市值＋（同一期末的債務 − 現金）。"
    "口徑由今天決定、整條序列同一口徑：今天 TTM 營業利益 ≥ 0 且有同期淨負債 → EV/S，否則 P/S。"
    "百分位＝窗內（今天往前 3 年）比今天低的樣本占全部樣本的比例 ×100。**不設門檻**——幾分算「已定價」由寫的人判斷。"
    "另印樣本數／窗內交易日數＝覆蓋率（倍數算不出來的日子不是樣本；只印，不設門檻）。"
    "台股：股數＝d 之前已過法定期限的最新一季季報股本換算（核對沒過的季不用，見 shares_rejected），"
    "營收＝d 之前已過法定期限的最近 12 個月月營收，口徑一律 P/S")
_RULE_COHORT = ("主題等權組成員（本檔除外）今天的倍數，只取與本檔同口徑、有值的成員取中位數並印 n；"
                "只印，不比較、不算差")
_RULE_REL = ("本檔最近 N 個交易日的調整後收盤報酬（當地幣別）− 成員（本檔除外）各自最近 N 個交易日報酬的等權平均；"
             "只印，不比較、不設門檻")
_RULE_NUMBERS = ("依序取第一個有 ≥2 點的來源：分部／產品線營收占比序列 → 台股月營收（最近 12 個月 YoY，可用日＝法定期限）"
                 "→ EDGAR 季營收（最近 8 季，YoY 對同一季）→ 20-F 年度營收；每行宣告實際用了哪個來源")


def _iso(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def line(key: str, label: str, *, value: Any = None, source: str | None = None, as_of: Any = None,
         basis: str | None = None, rule: str, absence_kind: str | None = None, reason: str | None = None,
         detail: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """一行稽核。**有值與缺席二擇一**：有 `absence_kind` 就不得有 `value`，反之亦然（L12）。"""
    from alpha.absence import check_absence_kind

    if absence_kind is not None:
        check_absence_kind(absence_kind)
        if value is not None:
            raise ValueError(f"{key}：缺席的行不得帶 value")
        if not reason:
            raise ValueError(f"{key}：缺席必須說明理由（absence_kind 之外的一句話）")
    elif value is None:
        raise ValueError(f"{key}：沒有值的行必須宣告 absence_kind——缺席不得被壓成一句「無資料」")
    return {"key": key, "label": label, "value": value, "source": source,
            "as_of": as_of.isoformat() if isinstance(as_of, date) else as_of,
            "basis": basis, "rule": rule, "absence_kind": absence_kind, "reason": reason,
            "detail": dict(detail or {})}


# ---------------------------------------------------------------------------
# as-of 小工具（純函式；輸入是 engine_c.history 讀出來的全部列，含每份申報）
# ---------------------------------------------------------------------------

def _as_of_map(rows: Sequence[Mapping[str, Any]], d: date) -> dict[date, Mapping[str, Any]]:
    """每個 period_end 取 `filed ≤ d` 的最新一列——規則只住 `shared.as_of`（Engine C 讀取端同一支）。"""
    from shared.as_of import latest_known_by_period

    return latest_known_by_period(rows, d)


def ttm(quarters: Sequence[Mapping[str, Any]], d: date) -> tuple[float | None, date | None, str | None]:
    """d 時刻已知的最近四個**連續**季度之和 → `(值, 最新一季期末, 幣別)`；不足四季或不連續回 None。"""
    known = _as_of_map(quarters, d)
    ends = sorted(known)
    if len(ends) < 4:
        return None, None, None
    last4 = ends[-4:]
    for a, b in zip(last4, last4[1:]):
        if not (_QUARTER_GAP[0] <= (b - a).days <= _QUARTER_GAP[1]):
            return None, None, None
    currencies = {str(known[e].get("currency")) for e in last4}
    if len(currencies) != 1:
        return None, None, None
    return sum(float(known[e]["value"]) for e in last4), last4[-1], currencies.pop()


def monthly_ttm(months: Sequence[Mapping[str, Any]], d: date) -> tuple[float | None, str | None]:
    """台股：d 時刻已過法定期限的最近 12 個**連續**月份之和（千元 → 元）。"""
    avail = [m for m in months if (_iso(m.get("available_on")) or date.max) <= d and m.get("revenue") is not None]
    if len(avail) < 12:
        return None, None
    last = sorted(avail, key=lambda m: m["data_month"])[-12:]
    seq = [(int(m["data_month"][:4]), int(m["data_month"][5:7])) for m in last]
    for (y1, m1), (y2, m2) in zip(seq, seq[1:]):
        if (y2 * 12 + m2) - (y1 * 12 + m1) != 1:
            return None, None
    return sum(float(m["revenue"]) * float(m.get("unit_scale") or 1) for m in last), last[-1]["data_month"]


def shares_on(cover: Sequence[Mapping[str, Any]], splits: Sequence[tuple[date, float]], d: date) -> float | None:
    """d 時刻已申報的最新一份封面股數，再乘上封面日之後、d 之前（含）發生的分割比例——「當天」的股數。"""
    known = _as_of_map(cover, d)
    if not known:
        return None
    end = max(known)
    shares = float(known[end]["value"])
    for split_date, ratio in splits:
        if end < split_date <= d:
            shares *= ratio
    return shares


def net_debt_on(cash: Sequence[Mapping[str, Any]], debt: Sequence[Mapping[str, Any]], d: date
                ) -> tuple[float | None, date | None]:
    """同一期末的債務 − 現金（兩者都要 d 時刻已申報）；沒有同期的一對就回 None——不拿不同期相減。"""
    c, b = _as_of_map(cash, d), _as_of_map(debt, d)
    common = sorted(set(c) & set(b))
    if not common:
        return None, None
    end = common[-1]
    return float(b[end]["value"]) - float(c[end]["value"]), end


# ---------------------------------------------------------------------------
# 已定價① 自家歷史百分位
# ---------------------------------------------------------------------------

def _multiple_series(inp: Mapping[str, Any], *, basis: str) -> list[tuple[date, float]]:
    """每個交易日的倍數（同一個函式算今天與歷史）。"""
    bars = inp["price_bars"]
    factor = float(inp.get("price_to_settlement") or 1.0)
    splits = [(s, r) for s, r in (inp.get("splits") or ())]
    out: list[tuple[date, float]] = []
    for d, close_raw in bars:
        if close_raw is None:
            continue
        if inp.get("revenue_kind") == "monthly":
            revenue, _ = monthly_ttm(inp.get("monthly_revenue") or (), d)
        else:
            revenue, last_end, _ = ttm(inp.get("revenue_quarters") or (), d)
            if last_end is None or (d - last_end).days > FUNDAMENTAL_MAX_AGE_DAYS:
                continue                                 # 那一天的營收 TTM 已經過期——不拿舊數字冒充當天
        shares = shares_on(inp.get("shares_cover") or (), splits, d)
        if not revenue or revenue <= 0 or not shares:
            continue
        cap = float(close_raw) * factor * shares
        value = cap
        if basis == "EV/S":
            nd, nd_end = net_debt_on(inp.get("cash") or (), inp.get("total_debt") or (), d)
            if nd is None or nd_end is None or (d - nd_end).days > FUNDAMENTAL_MAX_AGE_DAYS:
                continue
            value = cap + nd
        out.append((d, value / revenue))
    return out


def decide_basis(inp: Mapping[str, Any], today: date) -> tuple[str, str]:
    """今天的口徑：TTM 營業利益 ≥ 0 且有同期淨負債 → EV/S；否則 P/S（理由寫明）。"""
    if inp.get("revenue_kind") == "monthly":
        return "P/S", "台股月營收沒有營業利益 → 一律 P/S"
    op, op_end, _ = ttm(inp.get("operating_income_quarters") or (), today)
    _rev, rev_end, _ = ttm(inp.get("revenue_quarters") or (), today)
    nd, nd_end = net_debt_on(inp.get("cash") or (), inp.get("total_debt") or (), today)
    if op is None:
        return "P/S", "今天的 TTM 營業利益取不到 → P/S"
    if op_end != rev_end or (today - op_end).days > FUNDAMENTAL_MAX_AGE_DAYS:
        return "P/S", (f"TTM 營業利益的最新一季（{op_end}）與營收（{rev_end}）不同步或已過期——不拿舊的營業利益判口徑 → P/S")
    if op < 0:
        return "P/S", "今天 TTM 營業利益 < 0（虧損期）→ P/S"
    if nd is None or nd_end is None or (today - nd_end).days > FUNDAMENTAL_MAX_AGE_DAYS:
        return "P/S", "今天沒有夠新的同一期末債務與現金 → 淨負債缺席 → P/S"
    return "EV/S", "今天 TTM 營業利益 ≥ 0 且有同期淨負債 → EV/S"


def own_history(inp: Mapping[str, Any], *, today: date,
                history_not_comparable: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """已定價①。`inp` 的形狀見 `engine_c.three_question_inputs.get_three_question_inputs`。"""
    key, label = "own_history_pctile", "已定價①：自家歷史百分位"
    gate = inp.get("gate")
    if gate:
        return line(key, label, rule=_RULE_OWN, absence_kind=gate["absence_kind"], reason=gate["reason"])
    if history_not_comparable:
        since = history_not_comparable.get("since")
        return line(key, label, rule=_RULE_OWN, absence_kind="inputs_incompatible",
                    reason=f"敘事宣告自 {since} 起不可比：{history_not_comparable.get('reason')}",
                    detail={"declared": dict(history_not_comparable)})
    settlement = inp.get("price_settlement_currency")
    report_ccy = sorted({str(r.get("currency")) for r in (inp.get("revenue_quarters") or ())
                         if r.get("currency")} | ({"TWD"} if inp.get("revenue_kind") == "monthly" else set())
                        | {str(r.get("currency")) for r in (inp.get("revenue_annual") or ()) if r.get("currency")})
    if settlement and report_ccy and any(c != settlement for c in report_ccy):
        # 不換匯、不猜 ADR 比率（plan §0.3）：報表幣別 ≠ 報價結算幣別，市值與營收不得相除。
        return line(key, label, rule=_RULE_OWN, absence_kind="inputs_incompatible",
                    reason=f"報表幣別 {'／'.join(report_ccy)} ≠ 報價結算幣別 {settlement}（不換匯）",
                    detail={"report_currency": report_ccy, "settlement_currency": settlement})
    if inp.get("filer_class") == "foreign_annual":
        return line(key, label, rule=_RULE_OWN, absence_kind="inputs_incompatible",
                    reason="20-F／40-F 發行人：companyfacts 的股數是普通股，掛牌的可能是 ADS——"
                           "兩者不是同一種證券單位，比率沒有登記，不猜（只存年度點）",
                    detail={"filer_class": "foreign_annual"})
    bars = inp.get("price_bars") or ()
    if not bars:
        return line(key, label, rule=_RULE_OWN, absence_kind="upstream_unavailable", reason="沒有價格歷史")
    last_bar = bars[-1][0]
    days_since = (today - last_bar).days
    if days_since > PRICE_FRESH_DAYS:
        return line(key, label, rule=_RULE_OWN, absence_kind="insufficient_evidence",
                    reason=f"最後一個收盤是 {last_bar.isoformat()}，距今 {days_since} 天（超過 {PRICE_FRESH_DAYS} 天）",
                    detail={"days_since_last": days_since})
    basis, basis_reason = decide_basis(inp, today)
    series = [(d, v) for d, v in _multiple_series(inp, basis=basis)
              if d >= today - timedelta(days=365 * HISTORY_YEARS)]
    if not series or series[-1][0] != last_bar:
        return line(key, label, rule=_RULE_OWN, basis=basis, absence_kind="insufficient_evidence",
                    reason=f"今天（{last_bar.isoformat()}）的 {basis} 算不出來（{basis_reason}；"
                           "TTM 營收、股數或淨負債缺一或已過期）",
                    detail={"basis_reason": basis_reason, "samples": len(series)})
    window_days = (series[-1][0] - series[0][0]).days
    today_value = series[-1][1]
    past = [v for _, v in series[:-1]]
    # 覆蓋率（Phase 4 Step 4.7c）：百分位只用得到「當天倍數算得出來」的日子——同一窗內有收盤卻沒有樣本的天
    # （TTM 過期、股數缺）不會出現在百分位裡。只印、**不設門檻**（多少算夠由讀的人判斷）。
    trading_days = sum(1 for d, _ in bars if series[0][0] <= d <= series[-1][0])
    detail = {"multiple_today": round(today_value, 4), "basis_reason": basis_reason, "samples": len(series),
              "trading_days_in_window": trading_days,
              "coverage": round(len(series) / trading_days, 2) if trading_days else None,
              "window_start": series[0][0].isoformat(), "window_end": series[-1][0].isoformat(),
              "window_days": window_days, "min": round(min(v for _, v in series), 4),
              "median": round(median(v for _, v in series), 4), "max": round(max(v for _, v in series), 4),
              "days_since_last": days_since}
    if inp.get("shares_rejected"):
        # 台股：交叉核對沒過或同季衝突的季整季不用——稽核區逐筆印出，不讓「少了一段樣本」看起來像沒事（INV-3）。
        detail["shares_rejected"] = list(inp["shares_rejected"])
    if window_days < 365 * HISTORY_YEARS - HISTORY_SLACK_DAYS:
        return line(key, label, rule=_RULE_OWN, basis=basis, absence_kind="insufficient_evidence",
                    reason=f"窗只有 {window_days} 天（{series[0][0].isoformat()} 起），不滿 {HISTORY_YEARS} 年",
                    detail=detail)
    pct = 100.0 * sum(1 for v in past if v < today_value) / len(past)
    return line(key, label, value=round(pct, 1), source=inp.get("source"), as_of=last_bar, basis=basis,
                rule=_RULE_OWN, detail=detail)


# ---------------------------------------------------------------------------
# 已定價② 主題等權組中位數、③ 相對組漲幅
# ---------------------------------------------------------------------------

def cohort_median(own: Mapping[str, Any], members: Mapping[str, Mapping[str, Any]], *,
                  cohort: Mapping[str, Any] | None, cohort_absence: Mapping[str, str] | None) -> dict[str, Any]:
    """`members`：成員 ticker → 該成員的 ①（本檔除外，由呼叫端排除）。只取同口徑、今天有倍數的成員。"""
    key, label = "cohort_median", "已定價②：主題等權組中位數"
    if cohort_absence:
        return line(key, label, rule=_RULE_COHORT, **cohort_absence)
    basis = own.get("basis")
    if not basis:
        return line(key, label, rule=_RULE_COHORT, absence_kind="upstream_unavailable",
                    reason="本檔自己的口徑算不出來（見①），同口徑無從比對")
    same = {t: float(m["detail"]["multiple_today"]) for t, m in members.items()
            if m.get("basis") == basis and (m.get("detail") or {}).get("multiple_today") is not None}
    n_members = len(members)
    detail = {"cohort_id": (cohort or {}).get("record_id"), "theme": (cohort or {}).get("theme"),
              "n_same_basis": len(same), "n_members": n_members, "members_used": sorted(same)}
    if n_members == 0 or len(same) * 2 < n_members:
        return line(key, label, rule=_RULE_COHORT, basis=basis, absence_kind="insufficient_evidence",
                    reason=f"同口徑（{basis}）有值的成員 {len(same)}／{n_members}，不足一半", detail=detail)
    return line(key, label, value=round(median(same.values()), 4), source="theme_cohort ledger＋各成員①",
                as_of=own.get("as_of"), basis=basis, rule=_RULE_COHORT, detail=detail)


def trailing_return(bars: Sequence[tuple[date, float | None]], n: int) -> tuple[float | None, date | None]:
    """最近 n 個交易日的報酬（調整後收盤）。不足 n+1 點回 None。"""
    usable = [(d, v) for d, v in bars if v is not None]
    if len(usable) < n + 1:
        return None, None
    return usable[-1][1] / usable[-1 - n][1] - 1.0, usable[-1][0]


def relative_returns(own_bars: Sequence[tuple[date, float | None]],
                     member_bars: Mapping[str, Sequence[tuple[date, float | None]]], *, today: date,
                     cohort: Mapping[str, Any] | None, cohort_absence: Mapping[str, str] | None
                     ) -> list[dict[str, Any]]:
    """已定價③：30／90 個交易日相對組漲幅，各一行。"""
    out = []
    for n in RELATIVE_WINDOWS:
        key, label = f"rel_return_{n}d", f"已定價③：相對組 {n} 個交易日漲幅"
        if cohort_absence:
            out.append(line(key, label, rule=_RULE_REL, **cohort_absence))
            continue
        own, last = trailing_return(own_bars, n)
        if own is None or last is None:
            out.append(line(key, label, rule=_RULE_REL, absence_kind="insufficient_evidence",
                            reason=f"本檔的調整後收盤不足 {n + 1} 個交易日"))
            continue
        days_since = (today - last).days
        if days_since > PRICE_FRESH_DAYS:
            out.append(line(key, label, rule=_RULE_REL, absence_kind="insufficient_evidence",
                            reason=f"本檔最後一個收盤距今 {days_since} 天", detail={"days_since_last": days_since}))
            continue
        rets = {}
        for t, bars in member_bars.items():
            r, lb = trailing_return(bars, n)
            if r is not None and lb is not None and (today - lb).days <= PRICE_FRESH_DAYS:
                rets[t] = r
        if not member_bars or len(rets) * 2 < len(member_bars):
            out.append(line(key, label, rule=_RULE_REL, absence_kind="insufficient_evidence",
                            reason=f"有 {n} 日報酬的成員 {len(rets)}／{len(member_bars)}，不足一半",
                            detail={"members_used": sorted(rets)}))
            continue
        mean = sum(rets.values()) / len(rets)
        out.append(line(key, label, value=round(own - mean, 4), source="price_history（調整後收盤）",
                        as_of=last, rule=_RULE_REL,
                        detail={"own_return": round(own, 4), "cohort_mean_return": round(mean, 4),
                                "members_used": sorted(rets), "cohort_id": (cohort or {}).get("record_id")}))
    return out


# ---------------------------------------------------------------------------
# 出現在數字裡了嗎
# ---------------------------------------------------------------------------

def _yoy_quarters(rows: Sequence[Mapping[str, Any]], today: date, *, n: int) -> list[dict[str, Any]]:
    known = _as_of_map(rows, today)
    ends = sorted(known)
    out = []
    for e in ends[-n:]:
        prior = [p for p in ends if 350 <= (e - p).days <= 380]
        prev = float(known[prior[-1]]["value"]) if prior else None
        value = float(known[e]["value"])
        out.append({"period_end": e.isoformat(), "value": value, "filed": known[e].get("filed"),
                    "yoy": (round(value / prev - 1.0, 4) if prev not in (None, 0.0) else None),
                    "derived": known[e].get("derived")})
    return out


def in_numbers(inp: Mapping[str, Any], *, today: date) -> list[dict[str, Any]]:
    """出現在數字裡了嗎：一行序列（第一個有 ≥2 點的來源）＋（可選）一行結構脈絡。"""
    key, label = "in_numbers_series", "出現在數字裡了嗎：序列"
    out: list[dict[str, Any]] = []
    # 分部占比與產品線占比是兩種切法（口徑不同）：**同一個欄位**有 ≥2 個觀測日才成序列，不跨欄位湊點（L12）。
    by_field: dict[str, list[Mapping[str, Any]]] = {}
    conflicts = []
    for seg in inp.get("segment_shares") or ():
        if seg.get("conflict"):
            conflicts.append(line(
                "in_numbers_conflict", "出現在數字裡了嗎：同一觀測日有多筆生效紀錄", source=str(seg.get("field")),
                as_of=seg.get("as_of"), rule="同一 (欄位, 觀測日) 只能有一筆生效；多筆就不挑一個，這一點不進序列（INV-3）",
                absence_kind="insufficient_evidence", detail={"conflict": list(seg["conflict"])},
                reason=f"{seg.get('as_of')} 有 {len(seg['conflict'])} 筆生效紀錄（{'、'.join(seg['conflict'])}），不挑一個"))
            continue
        by_field.setdefault(str(seg.get("field")), []).append(seg)
    series_field = next((f for f, pts in sorted(by_field.items()) if len(pts) >= 2), None)
    if series_field is not None:
        pts = sorted(by_field[series_field], key=lambda s: str(s.get("as_of")))
        out.append(line(key, label, value=[{"as_of": p.get("as_of"), "revenue_mix": p["value"]} for p in pts[-4:]],
                        source=series_field, as_of=pts[-1].get("as_of"), basis="分部／產品線營收占比（同一欄位）",
                        rule=_RULE_NUMBERS))
        return out + conflicts
    contexts = [line("in_numbers_structure", "出現在數字裡了嗎：結構脈絡（只有一點）", value=pts[0]["value"],
                     source=f, as_of=pts[0].get("as_of"), rule="這個欄位只有一個觀測日——當結構脈絡印，不佔序列位置")
                for f, pts in sorted(by_field.items())] + conflicts
    months = [m for m in (inp.get("monthly_revenue") or ())
              if (_iso(m.get("available_on")) or date.max) <= today and m.get("revenue") is not None]
    if len(months) >= 2:
        last = sorted(months, key=lambda m: m["data_month"])[-12:]
        series = [{"data_month": m["data_month"], "revenue_twd_thousand": m["revenue"],
                   "yoy": (round(m["revenue"] / m["revenue_year_ago"] - 1.0, 4)
                           if m.get("revenue_year_ago") else None),
                   "available_on": m.get("available_on")} for m in last]
        out.append(line(key, label, value=series, source="monthly_revenue_observations（MOPS）",
                        as_of=last[-1].get("available_on"), basis="台股月營收 YoY（可用日＝法定期限，非實際公告日）",
                        rule=_RULE_NUMBERS, detail={"currency": "TWD"}))
    elif inp.get("revenue_kind") != "monthly" and len(_as_of_map(inp.get("revenue_quarters") or (), today)) >= 2:
        series = _yoy_quarters(inp["revenue_quarters"], today, n=8)
        out.append(line(key, label, value=series, source="fundamental_history（SEC companyfacts 季營收）",
                        as_of=series[-1]["filed"], basis="EDGAR 季營收（YoY 對同一季）", rule=_RULE_NUMBERS,
                        detail=_series_currency(inp["revenue_quarters"])))
    elif len(_as_of_map(inp.get("revenue_annual") or (), today)) >= 2:
        series = _yoy_quarters(inp["revenue_annual"], today, n=4)
        out.append(line(key, label, value=series, source="fundamental_history（SEC companyfacts 年度營收）",
                        as_of=series[-1]["filed"], basis="20-F 年度營收（YoY）", rule=_RULE_NUMBERS,
                        detail=_series_currency(inp["revenue_annual"])))
    else:
        points = (len(months) or len(_as_of_map(inp.get("revenue_quarters") or (), today))
                  or len(_as_of_map(inp.get("revenue_annual") or (), today)))
        out.append(line(key, label, rule=_RULE_NUMBERS,
                        absence_kind="insufficient_evidence" if points == 1 else "upstream_unavailable",
                        reason=("只有一個點，看不出趨勢" if points == 1 else
                                "沒有機械的營收序列來源（非美國申報人、非台股，或 companyfacts 缺這一段）")))
    out[0] = _stale_series_check(out[0], today=today)
    out.extend(contexts)
    return out


#: 「出現在數字裡了嗎」的最新一點最多可以多舊（天）：季報 200、年報 550（沿用 `fetchers.edgar_xbrl._MAX_BASELINE_AGE_DAYS`
#: 的量級）、月營收 75（法定期限次月 10 日＋一個月緩衝）。超過就不是「現在的數字」——缺席並印 days_since_last。
_SERIES_MAX_AGE = {"EDGAR 季營收（YoY 對同一季）": 200, "20-F 年度營收（YoY）": 550}
_MONTHLY_MAX_AGE = 75


def _series_currency(rows: Any) -> dict[str, Any]:
    """序列的報表幣別（個股頁 S5b 的營收柱狀照抄，2026-10-08）：資料列上實際寫的幣別；混了多種就照實列出、不挑一個（L12）。"""
    found = sorted({str(r.get("currency")) for r in rows or () if r.get("currency")})
    return {"currency": found[0]} if len(found) == 1 else {"currency": None, "currencies": found}


def _stale_series_check(row: dict[str, Any], *, today: date) -> dict[str, Any]:
    if row.get("absence_kind") is not None or not isinstance(row.get("value"), list) or not row["value"]:
        return row
    last = row["value"][-1]
    anchor = _iso(last.get("period_end") or last.get("as_of")
                  or (f"{last['data_month']}-01" if last.get("data_month") else None))
    basis = str(row.get("basis") or "")
    limit = _SERIES_MAX_AGE.get(basis, _MONTHLY_MAX_AGE if "月營收" in basis else None)
    if anchor is None or limit is None:
        return row
    age = (today - anchor).days
    if age <= limit:
        row["detail"]["days_since_last"] = age
        return row
    return line(row["key"], row["label"], rule=row["rule"], basis=basis, absence_kind="insufficient_evidence",
                reason=f"最新一期 {anchor.isoformat()} 距今 {age} 天（超過 {limit} 天）——不是現在的數字",
                detail={"days_since_last": age, "last_point": last})


# ---------------------------------------------------------------------------
# 組起來
# ---------------------------------------------------------------------------

def evaluate(inp: Mapping[str, Any], *, today: date, wipeout: Mapping[str, Mapping[str, Any]] | None,
             wipeout_reason: str | None = None, cohorts: Sequence[Mapping[str, Any]] = (),
             cohort_absence: Mapping[str, str] | None = None,
             history_not_comparable: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """一檔的三題稽核區。**沒有任何結論欄位**：`answers`（是／否）由敘事宣告，不在這裡。

    `cohorts`：本檔所屬的每一個主題等權組各一份 `{cohort: {record_id, theme}, member_results, member_bars}`
    （一檔屬於多組時②③逐組印）；一組都沒有時 `cohort_absence` 說明是哪一種沒有（組未定義／不是成員）。
    """
    own = own_history(inp, today=today, history_not_comparable=history_not_comparable)
    priced = [own]
    if cohort_absence or not cohorts:
        absence = cohort_absence or {"absence_kind": "not_yet_recorded", "reason": "不在任何主題等權組"}
        priced.append(cohort_median(own, {}, cohort=None, cohort_absence=absence))
        priced.extend(relative_returns((), {}, today=today, cohort=None, cohort_absence=absence))
    for ctx in cohorts:
        cohort = ctx.get("cohort")
        priced.append(cohort_median(own, ctx.get("member_results") or {}, cohort=cohort, cohort_absence=None))
        priced.extend(relative_returns(inp.get("adjusted_bars") or (), ctx.get("member_bars") or {}, today=today,
                                       cohort=cohort, cohort_absence=None))
    die = []
    from alpha.wipeout import LANE_LABELS, WIPEOUT_LANES

    for lane in WIPEOUT_LANES:
        flag = (wipeout or {}).get(lane)
        label = f"會死嗎：{LANE_LABELS[lane]}"
        if flag is None:
            die.append(line(f"wipeout_{lane}", label, rule="alpha.wipeout", absence_kind="upstream_unavailable",
                            reason=wipeout_reason or "歸零旗標取數失敗"))
        elif flag.get("colour") is None:
            die.append(line(f"wipeout_{lane}", label, rule=str(flag.get("rule")),
                            absence_kind=str(flag.get("absence_kind")), reason=str(flag.get("reason")),
                            detail=_jsonable(flag.get("inputs") or {})))
        else:
            die.append(line(f"wipeout_{lane}", label, value=flag["colour"], rule=str(flag.get("rule")),
                            source=str((flag.get("inputs") or {}).get("source") or "engine_c"),
                            detail=_jsonable(flag.get("inputs") or {})))
    return {"will_it_die": die, "priced_in": priced, "in_numbers": in_numbers(inp, today=today),
            "today": today.isoformat()}


def _jsonable(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def rollup(results: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    """多檔的「每行有值／依 kind 缺席」計數（心跳與候選板用；**只數有值與缺席，不得讀成結論**）。"""
    counts: dict[str, dict[str, int]] = {}
    for result in results:
        for question in QUESTIONS:
            for row in result.get(question) or ():
                bucket = counts.setdefault(row["key"], {})
                state = "value" if row.get("absence_kind") is None else str(row["absence_kind"])
                bucket[state] = bucket.get(state, 0) + 1
    return counts


__all__ = [
    "HISTORY_YEARS", "PRICE_FRESH_DAYS", "QUESTIONS", "QUESTION_LABELS", "RELATIVE_WINDOWS",
    "cohort_median", "decide_basis", "evaluate", "in_numbers", "line", "monthly_ttm", "net_debt_on",
    "own_history", "relative_returns", "rollup", "shares_on", "trailing_return", "ttm",
]
