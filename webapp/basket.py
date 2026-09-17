"""籃子頁（V3，2026-09-15）：**結構排序 × 賭注 × 熟成度 × 市場承認 × 部位** 的 join，加一個 filter 式首選。

## 這一頁回答什麼

「現在該加碼哪一檔」。AGENTS 要求有序清單與明確首選；但唯一排序權威是 `rank_bottlenecks()`，
本頁**不重排、不加權、不自建第二套評分**：列的順序＝可行動排序去重（同一 ticker 只留最前的名次）。

## 首選（2026-09-15 使用者定案 D2）＝ filter，不是重算

結構順序不動；首選是順序中**第一個**同時滿足三條的：
1. 有賭注（variant 已寫，payoff 算得出來）；
2. payoff 為正；
3. 至少一條指名了假設的催化劑落在目標價的 value_date 之前（未到或到期待重看都算）。
INV-3：filter 逐檔報 input／accepted／filtered／reasons（封閉字彙 `FILTER_REASONS`）。沒有一檔通過就
`top_pick=null` ＋ 各理由的計數——那是誠實的答案，不是壞掉。

## 每一列強制「有賭注 或 Abstention」（Q2，2026-09-17 使用者核准）

進了籃子就得回答「我們賭什麼」。答案只有兩種誠實形狀，`bet_state` 是那個答案的封閉字彙：
`bet`（variant 已寫）／`abstained`（`bet/variant.overlay` ledger 有一筆明示紀錄）／
`unanswered`（**兩者皆無——欠一個答案，不是一種狀態**）。三者逐列印、逐項計數（`bet_ledger`）。

為什麼這是籃子層最要緊的一格：2026-09-17 實測 16 檔有 **15 檔** 卡在「沒人寫賭注」，
**沒有一檔**是因為 substitutability 或證據強度被擋——開別的門、擴別的宇宙都不會讓籃子非空。

## 純函式

`build_basket_artifact` 只吃三份已 materialize 的 artifact（ranking／positions／每檔 overview），不連 DB、
不跑模型；同一份輸入永遠得到同一份輸出。
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from typing import Any, Mapping, Sequence

from .contracts import canonical_digest, state_freshness_identity

BASKET_MATERIALIZER_VERSION = "webapp-materialize-basket/1"

#: filter 理由的封閉字彙（一檔可能同時有多個）。
FILTER_REASONS: Mapping[str, str] = {
    "no_bet": "還沒寫賭注（variant 假設）",
    "bet_abstained": "已宣告刻意不主張賭注（append-only ledger 的研究結論，不是待辦）",
    "payoff_not_positive": "賭注對了也不比現價高",
    "no_catalyst_in_horizon": "沒有指名假設、且落在目標價日期之前的催化劑",
}

#: 一列的**賭注終局**（Q2，2026-09-17 使用者核准）。封閉字彙，三個值但只有兩個是終局。
#:
#: 進了籃子就得回答「我們賭什麼」，答案只有兩種誠實形狀：寫一個帶 disproof 的賭注，
#: 或在 `bet/variant.overlay` ledger 宣告「目前沒有可辯護的賭注 ＋ revisit_when」。
#: **`unanswered` 不是第三種終局，是欠一個答案**——它被計數、被印出來，不會安靜地
#: 混在「沒通過 filter」裡（2026-09-17 實測：16 檔有 15 檔卡在這裡，而那才是籃子空的原因）。
BET_STATES: Mapping[str, str] = {
    "bet": "有賭注：variant 假設已寫，payoff 算得出來",
    "abstained": "刻意不主張：已研究，結論是目前沒有可辯護的賭注（append-only 紀錄，附 revisit_when）",
    "unanswered": "**欠一個答案**：既沒有賭注，也沒有宣告不主張——不是狀態，是待辦",
}
BET_LEDGER_RULE = ("籃子的每一列強制二選一：有賭注，或一筆 Abstention。沒有第三種安靜狀態——"
                   "兩者皆無時記成 unanswered 並計數（Q2，2026-09-17）。"
                   "⚠ 賭注的 Abstention 只認 layer=bet／subject=variant.overlay：估值層的 "
                   "`target_pe` abstention 說的是「本益比法沒有可校準的對象」，不是「沒有可辯護的賭注」。")
FILTER_RULE = ("結構順序不動；首選＝順序中第一個「有賭注、payoff 為正、至少一條指名假設的催化劑落在目標價日期之前」的。"
               "這是 filter 不是重算：沒有一檔通過就沒有首選。")

BASKET_THIS_IS_NOT: tuple[str, ...] = (
    "不是新的排序：列的順序照抄 rank_bottlenecks() 的可行動排序（同一檔只留最前名次）；本頁不重排、不加權。",
    "首選不是買進指令：它只是「結構順序中第一個有正 payoff 賭注且有裁決點的」；買多少、何時買由使用者決定。",
    "不是分散：同一產業群的檔是同一個賭注下 N 次；相關性群照抄排序頁的產業分組。",
    "不是預測：payoff 是賭注的確定性函數；熟成度與市場承認是量測不是訊號。",
)


def _num(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _cell_value(cell: Mapping[str, Any] | None) -> Any:
    return (cell or {}).get("value")


def _sector_by_rank(ranking: Mapping[str, Any]) -> dict[int, str]:
    out: dict[int, str] = {}
    for group in ranking.get("sectors") or ():
        for rank in group.get("actionable_ranks") or ():
            out[int(rank)] = str(group.get("sector") or "")
    return out


def _catalyst_in_horizon(ripeness: Mapping[str, Any] | None, value_date: str | None) -> bool:
    links = ((ripeness or {}).get("links") or ())
    for link in links:
        if link.get("state") not in ("pending", "due"):
            continue
        expected = link.get("expected_at")
        if not expected:
            continue
        if value_date is None or str(expected)[:10] <= str(value_date)[:10]:
            return True
    return False


def build_basket_row(rank_row: Mapping[str, Any], overview: Mapping[str, Any] | None,
                     live: Mapping[str, Any] | None, *, sector: str | None) -> dict[str, Any]:
    ov = overview or {}
    payoff = ov.get("payoff") or {}
    ripeness = _cell_value(ov.get("ripeness"))
    closure = _cell_value(ov.get("gap_closure")) or {}
    reached = _cell_value(ov.get("target_reached")) or {}
    value_date = _cell_value(((ov.get("future_target") or {}).get("value_date")))
    payoff_value = _num(_cell_value(payoff.get("simple")))
    # 賭注終局：有值＝有賭注；沒值時由**上游宣告的** absence_kind 決定是哪一種沒有——
    # 呈現層不 parse 理由句去猜（L16）。`deliberate_abstention` 來自 bet ledger，
    # 由 briefing/alpha_view/sources.py 在 variant 缺席分支查出後一路帶下來。
    abstained = str(payoff.get("absence_kind") or "") == "deliberate_abstention"
    bet_state = "bet" if payoff_value is not None else ("abstained" if abstained else "unanswered")
    reasons: list[str] = []
    if payoff_value is None:
        reasons.append("bet_abstained" if abstained else "no_bet")
    elif payoff_value <= 0:
        reasons.append("payoff_not_positive")
    if not _catalyst_in_horizon(ripeness, value_date):
        reasons.append("no_catalyst_in_horizon")
    base_closure = (closure.get("base") or {}) if isinstance(closure, Mapping) else {}
    return {
        "rank": rank_row.get("rank"),
        "ticker": rank_row.get("ticker"),
        "company_id": rank_row.get("company_id"),
        "company_label": rank_row.get("company_label") or ov.get("company_label"),
        "sector": sector,
        "bottleneck": rank_row.get("bottleneck"),
        "relation": rank_row.get("relation"),
        "evidence": rank_row.get("evidence"),
        "evidence_label": rank_row.get("evidence_label"),
        "has_overview": overview is not None,
        "readiness": (ov.get("readiness") or {}).get("state"),
        "opinion_stance": _cell_value(ov.get("opinion_stance")),
        "our_bet": _cell_value((ov.get("brief") or {}).get("our_bet")),
        "price": ov.get("price"),
        "base_return": _cell_value((ov.get("implied_return") or {}).get("simple")),
        "payoff": payoff_value,
        "payoff_status": payoff.get("status"),
        "payoff_absence_kind": payoff.get("absence_kind"),
        "bet_state": bet_state,
        "bet_absence_reason": (payoff.get("reason") if payoff_value is None else None),
        "ripeness": (ripeness or {}).get("counts") if isinstance(ripeness, Mapping) else None,
        "consensus_moved": base_closure.get("closed_fraction") if isinstance(base_closure, Mapping) else None,
        "consensus_points": base_closure.get("n_points") if isinstance(base_closure, Mapping) else None,
        "price_above_target": bool(reached.get("any_reached")) if isinstance(reached, Mapping) else None,
        "held": live is not None,
        "position": ({"shares": live.get("shares"), "entry_price": live.get("price"), "currency": live.get("currency"),
                      "executed_at": live.get("executed_at"), "live_return": live.get("live_return")} if live else None),
        "filter_reasons": reasons,
        "passes_filter": not reasons,
    }


def build_basket_artifact(*, ranking: Mapping[str, Any], overviews: Mapping[str, Mapping[str, Any]],
                          positions: Mapping[str, Any] | None, generated_at: datetime | None = None) -> dict[str, Any]:
    """三份 artifact → `basket` state artifact。**純函式**：不重排、不加權、不算任何新數。"""
    stamp = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    sector_of = _sector_by_rank(ranking)
    live_by_ticker = {str(r.get("ticker")): r for r in ((positions or {}).get("live") or {}).get("rows") or ()
                      if r.get("ticker")}
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rank_row in ranking.get("rows") or ():
        ticker = rank_row.get("ticker")
        if not ticker or ticker in seen:
            continue                                    # 同一檔只留最前名次；順序＝排序權威的順序
        seen.add(str(ticker))
        rows.append(build_basket_row(rank_row, overviews.get(str(ticker)), live_by_ticker.get(str(ticker)),
                                     sector=sector_of.get(int(rank_row.get("rank") or 0))))
    accepted = [r for r in rows if r["passes_filter"]]
    reason_counts = {key: sum(1 for r in rows if key in r["filter_reasons"]) for key in FILTER_REASONS}
    # 賭注帳：每個 state 都印，**0 也印**——「欠 0 個答案」與「這一格沒算」不得同形（INV-3）。
    bet_counts = {state: sum(1 for r in rows if r["bet_state"] == state) for state in BET_STATES}
    top = accepted[0] if accepted else None
    groups: dict[str, list[str]] = {}
    for r in rows:
        groups.setdefault(str(r["sector"] or "（未分組）"), []).append(str(r["ticker"]))
    payload: dict[str, Any] = {
        "schema_version": "stockbot-app/basket/1",
        "kind": "basket",
        "title": "籃子：現在該加碼哪一檔（結構順序 × 賭注 × 熟成度 × 市場承認 × 部位）",
        "generated_at": stamp.isoformat(),
        "as_of": ranking.get("as_of"),
        "point_in_time": dict(ranking.get("point_in_time") or {"as_of": None, "mode": "current"}),
        "authority": {
            "function": "query.bottleneck.rank_bottlenecks（順序）＋ 各檔 analyst view overview（賭注／熟成度／承認）＋ positions（部位）",
            "command": "python -m webapp materialize --ranking --positions && python -m webapp materialize --basket",
            "note": "本頁是三份 artifact 的 join：不重排、不加權、不自建第二套評分。首選是 filter 的結果，不是分數。",
        },
        "sources": {"ranking_generated_at": ranking.get("generated_at"),
                    "positions_generated_at": (positions or {}).get("generated_at"),
                    "overview_count": len(overviews)},
        "rows": rows,
        "top_pick": ({"rank": top["rank"], "ticker": top["ticker"], "company_label": top["company_label"],
                      "payoff": top["payoff"], "our_bet": top["our_bet"], "sector": top["sector"],
                      "note": "首選＝結構順序中第一個通過三條 filter 的；不是買進指令"} if top else None),
        "top_pick_absent_reason": (None if top else
                                   f"沒有一檔通過 filter：" + "、".join(
                                       f"{FILTER_REASONS[k]} {v} 檔" for k, v in reason_counts.items() if v)),
        "filter": {"input": len(rows), "accepted": len(accepted), "filtered": len(rows) - len(accepted),
                   "reasons": reason_counts, "reason_labels": dict(FILTER_REASONS), "rule": FILTER_RULE},
        "bet_ledger": {**bet_counts, "input": len(rows),
                       "state_labels": dict(BET_STATES), "rule": BET_LEDGER_RULE,
                       "owed": [r["ticker"] for r in rows if r["bet_state"] == "unanswered"]},
        "groups": [{"sector": k, "tickers": v} for k, v in groups.items()],
        "correlation_notes": list(ranking.get("correlation_notes") or ()),
        "this_is_not": list(BASKET_THIS_IS_NOT),
        "materializer": {
            "version": BASKET_MATERIALIZER_VERSION,
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "note": "artifact 是 derived cache，不是 authority——刪掉重跑就會回來（L10）",
        },
    }
    payload["freshness_identity"] = state_freshness_identity(
        kind="basket", as_of=payload["as_of"],
        # 認知狀態＝順序、每檔有沒有賭注／payoff 正負／通過 filter 與否；現價與報酬的小數變動不算。
        identity={"rows": [[r["ticker"], r["rank"], r["payoff_status"], r["bet_state"],
                            r["passes_filter"], r["filter_reasons"]] for r in rows],
                  "top_pick": top["ticker"] if top else None})
    payload["content_digest"] = canonical_digest(payload)
    return payload


__all__ = ["BASKET_THIS_IS_NOT", "BET_LEDGER_RULE", "BET_STATES", "FILTER_REASONS", "FILTER_RULE",
           "build_basket_artifact", "build_basket_row"]
