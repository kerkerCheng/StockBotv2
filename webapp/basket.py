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
    # ⚠ 舊的 `no_catalyst_in_horizon` 已於 2026-09-19 拆成下面四個（七缺陷之 1）。
    # 它同時承載四件事，而**其中三件是資料沒填、只有一件是判準真的在運作**——
    # 實測 16 檔亮 15 檔（93.75%）、清除率 0，那不是 gate，那是牆（L14-4）。
    # gate 的意圖沒有錯（沒有裁決點的賭注不知道何時認錯，與 L7 同源），錯的是它問的問題：
    # 它問「一個可選欄位填了沒」，而不是「這個賭注有沒有裁決點」（L15-1）。
    # ⚠ **四個理由全部仍然 filtered**——拆開不是放寬（AGENTS.md 明文禁止為了非空放寬條件），
    # 拆開是為了讓「我們沒填」與「它真的不合格」不再長得一樣。
    "catalyst_missing_resolves": ("催化劑有日期、也落在目標價日期之前，**只差沒填 `resolves`**"
                                  "（指不出它會裁決哪一條假設）——這是我們的待辦，不是標的的缺點"),
    "catalyst_undated": "有催化劑散文但**沒有日期**——排不進射程，也無從判斷是否來得及",
    "catalyst_after_value_date": "有指名假設的催化劑，但**日期晚於目標價日期**——判準正確運作的那一種",
    "no_catalyst_recorded": "**根本沒有記錄任何催化劑**（或沒有判斷檔）",
}

#: 催化劑四種形狀的判準順序（2026-09-19）。**順序即優先序**，第一個命中的就是理由。
CATALYST_REASONS: tuple[str, ...] = (
    "no_catalyst_recorded", "catalyst_missing_resolves", "catalyst_undated", "catalyst_after_value_date",
)

#: 一列的**賭注終局**（Q2，2026-09-17 使用者核准）。封閉字彙，三個值但只有兩個是終局。
#:
#: 進了籃子就得回答「我們賭什麼」，答案只有兩種誠實形狀：寫一個帶 disproof 的賭注，
#: 或在 `bet/variant.overlay` ledger 宣告「目前沒有可辯護的賭注 ＋ revisit_when」。
#: **`unanswered` 不是第三種終局，是欠一個答案**——它被計數、被印出來，不會安靜地
#: 混在「沒通過 filter」裡（2026-09-17 實測：16 檔有 15 檔卡在這裡，而那才是籃子空的原因）。
BET_STATES: Mapping[str, str] = {
    "bet": "有賭注：variant 假設已寫，payoff 算得出來",
    "abstained": "刻意不主張：已研究，結論是目前沒有可辯護的賭注（append-only 紀錄，附 revisit_when）",
    "opinion_in_base": ("**觀點已在 base 裡，還沒決定 overlay**：base 的 derivation 是 "
                        "`independent`／`company_guidance`，差異看法整個住在 base，"
                        "於是 overlay 只剩那個來源本身的寬度——仍欠一個答案，但欠的不是「有沒有人看過」"),
    "unanswered": "**欠一個答案**：既沒有賭注，也沒有宣告不主張——不是狀態，是待辦",
}

#: `opinion_in_base` 的判準（2026-09-19，七缺陷之 5）。**只有這兩種 stance**，且必須同時
#: 沒有 payoff、沒有 abstention——`opinion_stance` 本身是既有純函式，這裡只消費不重算（L16）。
#:
#: ⚠ **不得因此自動把它算成有賭注**：COHR 是 `independent` **且**寫得出 variant（錨在指引上緣），
#: 證明「base 有觀點」與「寫得出 overlay」可以並存。所以這一格分的是**欠的是什麼**，
#: 不是**欠不欠**——`opinion_in_base` 與 `unanswered` 一樣不是終局，兩者都還欠一個答案。
#:
#: 事發（2026-09-19 實測）：LITE 的 base derivation 是 `company_guidance`，「我們的差異看法」
#: 內容就是「相信公司的指引」，variant overlay 只剩指引區間本身的寬度（實測賭注空間 +0.5pp）。
#: 硬要把格子填滿，寫出來的會是「隨便樂觀一點」，正是 `ASSUMPTION_SCENARIOS` 註解要擋的 bull case。
OPINION_IN_BASE_STANCES: frozenset[str] = frozenset({"independent", "company_guidance"})
BET_LEDGER_RULE = ("籃子的每一列強制二選一：有賭注，或一筆 Abstention。沒有第三種安靜狀態——"
                   "兩者皆無時記成 unanswered 並計數（Q2，2026-09-17）。"
                   "⚠ 2026-09-19 起「欠一個答案」拆成兩格：`unanswered`（沒人看過）與 "
                   "`opinion_in_base`（base 的 derivation 已是 independent／company_guidance，"
                   "差異看法住在 base、overlay 還沒決定）。**兩者都不是終局，欠的東西不同。**"
                   "⚠ 賭注的 Abstention 只認 layer=bet／subject=variant.overlay：估值層的 "
                   "`target_pe` abstention 說的是「本益比法沒有可校準的對象」，不是「沒有可辯護的賭注」。")
#: 量的候選（Q1，2026-09-17 使用者核准 A）的 filter 理由。**封閉字彙，與護城河那組分開**：
#: 兩個宇宙問的是不同的問題，用同一組理由會讓人以為它們可比。
#:
#: ⚠ 第一條**比護城河宇宙更嚴，不是放寬**：量的賭注賭的是「需求階躍時這家吃得到」，
#: 所以要求**已經在出貨**；而 sub≥4 的護城河宇宙裡有 6 條是 `qualifying`／未填——
#: 還沒出貨的護城河可以進 A，進不了 B。這證明擴大宇宙不是「為了讓籃子非空而放寬條件」。
VOLUME_FILTER_REASONS: Mapping[str, str] = {
    "not_shipping_yet": "還沒在出貨（qualification_status 不是 qualified／designed_in）——需求來了吃不到",
    "no_demand_anchor": "走不到需求錨：沒有人在為它花錢",
    "already_in_moat_basket": "這家已經在護城河籃子裡——對它而言這只是多幾條邊，不是多一家公司",
    "no_bet": "還沒寫賭注（variant 假設）",
    "bet_abstained": "已宣告刻意不主張賭注（append-only ledger 的研究結論，不是待辦）",
}

#: ⚠ **量的候選刻意沒有排序，也沒有首選。**
#: `rank_bottlenecks()` 是唯一排序權威，而這些邊正是被它濾掉的——它們沒有名次。
#: 它的排序鍵是為**護城河問題**設計的（substitutability 是第二鍵），套到「量」這個問題上
#: 等於自建第二套評分（AGENTS 明禁）。所以這一頁只回答「哪幾家通過了可機械驗證的條件」，
#: 依 ticker 列出，**那是字母序不是排名**。要有排序，得先有一個被量測過的判準（INV-5）。
VOLUME_ORDER_NOTE = ("量的候選依 ticker 列出——**那是字母序，不是排名**。"
                     "這些邊是被排序權威濾掉的，它們沒有名次；而它的排序鍵是為護城河問題設計的，"
                     "套到「量」上就是自建第二套評分。要排序得先有一個被量測過的判準。")

#: 今天還沒有資料源的兩條 D11 條件——**明說，不假裝**（INV-3）。
VOLUME_MISSING_CRITERIA: tuple[str, ...] = (
    "覆蓋厚薄（analyst_count、市值）：analyst view 的 overview 今天不帶這兩格，籃子是純函式（只吃 artifact）所以讀不到。要它得先讓 materialize 把 alpha_purity_snapshot 的輸出帶進 overview。",
    "瓶頸業務占營收比例：住 Engine C 的 product_line_revenue_share（八家有值），同樣還沒進 overview。",
)
FILTER_RULE = ("結構順序不動；首選＝順序中第一個「有賭注、payoff 為正、至少一條指名假設的催化劑落在目標價日期之前」的。"
               "這是 filter 不是重算：沒有一檔通過就沒有首選。"
               "⚠ 2026-09-19 起催化劑那一條的**理由**拆成四種形狀（`CATALYST_REASONS`）——"
               "**條件一字未放寬**，拆開只是讓「我們沒填 `resolves`」與「它的催化劑真的太晚」不再長得一樣。")

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


def _catalyst_reason(ripeness: Mapping[str, Any] | None, shape: Mapping[str, Any] | None,
                     value_date: str | None) -> str | None:
    """催化劑那一格擋不擋、**因為哪一種「沒有」**。通過就回 `None`。

    四種形狀（2026-09-19 實測 16 檔：A 4／B 6／C 1／D 4）先前全部被壓成一句
    「沒有指名假設、且落在目標價日期之前的催化劑」——**其中只有 C 是判準真的在運作**。
    形狀本身由 producer 宣告（`catalyst_shape`），這裡只做順序判定，不 parse 理由句（L16）。
    """
    if _catalyst_in_horizon(ripeness, value_date):
        return None
    counts = shape if isinstance(shape, Mapping) else {}
    if ((ripeness or {}).get("links") or ()):
        # 有指名假設的催化劑，但上面那一關沒過 → 沒有一條落在射程內。
        # ⚠ 這一支刻意**不依賴 `catalyst_shape`**：舊 artifact 還沒有那一格，
        # 而「有 linked 但太晚」是唯一一種**判準真的在運作**的形狀，不能因為缺一格就降級成「根本沒有」。
        return "catalyst_after_value_date"
    total = int(counts.get("total") or 0)
    if not total:
        return "no_catalyst_recorded"
    if int(counts.get("linked") or 0) == 0:
        # 有催化劑但一條都沒填 resolves：再分「有日期」與「沒日期」。
        if int(counts.get("unlinked_dated") or 0):
            earliest = str(counts.get("earliest_unlinked_date") or "")[:10]
            if value_date is None or (earliest and earliest <= str(value_date)[:10]):
                return "catalyst_missing_resolves"
            return "catalyst_after_value_date"
        return "catalyst_undated"
    # 有 linked 的，但沒有一條落在射程內——判準正確運作的那一種。
    return "catalyst_after_value_date"


def _bet_state(payoff_value: float | None, *, abstained: bool, stance: Any) -> str:
    """賭注終局的四分之一格。**純選取，不重算 stance**（`opinion_stance` 的 SSOT 在
    `alpha/fundamental/contracts.py`，這裡只消費它被帶到 overview 上的那個值）。"""
    if payoff_value is not None:
        return "bet"
    if abstained:
        return "abstained"
    if str(stance or "") in OPINION_IN_BASE_STANCES:
        return "opinion_in_base"
    return "unanswered"


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
    stance = _cell_value(ov.get("opinion_stance"))
    bet_state = _bet_state(payoff_value, abstained=abstained, stance=stance)
    reasons: list[str] = []
    if payoff_value is None:
        reasons.append("bet_abstained" if abstained else "no_bet")
    elif payoff_value <= 0:
        reasons.append("payoff_not_positive")
    catalyst_shape = _cell_value(ov.get("catalyst_shape"))
    catalyst_reason = _catalyst_reason(ripeness, catalyst_shape, value_date)
    if catalyst_reason is not None:
        reasons.append(catalyst_reason)
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
        "opinion_stance": stance,
        "our_bet": _cell_value((ov.get("brief") or {}).get("our_bet")),
        "price": ov.get("price"),
        "base_return": _cell_value((ov.get("implied_return") or {}).get("simple")),
        "payoff": payoff_value,
        "payoff_status": payoff.get("status"),
        "payoff_absence_kind": payoff.get("absence_kind"),
        "bet_state": bet_state,
        "bet_absence_reason": (payoff.get("reason") if payoff_value is None else None),
        "ripeness": (ripeness or {}).get("counts") if isinstance(ripeness, Mapping) else None,
        # 催化劑那一格的形狀（七缺陷之 1）：跟著列走，否則 APP 只看得到理由字串、
        # 看不到「幾條、幾條有日期、最早那條是哪天」——而那正是決定要不要去補的資訊。
        "catalyst_shape": catalyst_shape,
        "consensus_moved": base_closure.get("closed_fraction") if isinstance(base_closure, Mapping) else None,
        "consensus_points": base_closure.get("n_points") if isinstance(base_closure, Mapping) else None,
        "price_above_target": bool(reached.get("any_reached")) if isinstance(reached, Mapping) else None,
        # D2（2026-09-18）：歸零旗標跟著列走。**不進 `filter_reasons`**——燈是量測不是篩選條件，
        # 拿它擋掉候選就等於讓一個未經 outcome 驗證的指標決定去留（INV-5／L14）。
        "wipeout": ov.get("wipeout"),
        "held": live is not None,
        "position": ({"shares": live.get("shares"), "entry_price": live.get("price"), "currency": live.get("currency"),
                      "executed_at": live.get("executed_at"), "live_return": live.get("live_return")} if live else None),
        "filter_reasons": reasons,
        "passes_filter": not reasons,
    }


#: 「已經在出貨」＝需求來了吃得到。字彙與圖的 `qualification_status` 同一組（L16：不另造一份）。
SHIPPING_STATUSES: frozenset[str] = frozenset({"qualified", "designed_in"})


def build_volume_row(filtered_row: Mapping[str, Any], overview: Mapping[str, Any] | None,
                     live: Mapping[str, Any] | None, *, in_moat_basket: bool) -> dict[str, Any]:
    """一條被門檻擋下、但已研究過的邊 → 量的候選列。**判定，不排序。**"""
    ov = overview or {}
    payoff = ov.get("payoff") or {}
    payoff_value = _num(_cell_value(payoff.get("simple")))
    abstained = str(payoff.get("absence_kind") or "") == "deliberate_abstention"
    bet_state = _bet_state(payoff_value, abstained=abstained, stance=_cell_value(ov.get("opinion_stance")))
    reasons: list[str] = []
    if str(filtered_row.get("qualification_status") or "") not in SHIPPING_STATUSES:
        reasons.append("not_shipping_yet")
    if not filtered_row.get("demand_anchor"):
        reasons.append("no_demand_anchor")
    if in_moat_basket:
        reasons.append("already_in_moat_basket")
    if payoff_value is None:
        reasons.append("bet_abstained" if abstained else "no_bet")
    return {
        "ticker": filtered_row.get("ticker"),
        "company_id": filtered_row.get("company_id"),
        "company_label": ov.get("company_label") or filtered_row.get("company_id"),
        "bottleneck": filtered_row.get("bottleneck"),
        "relation": filtered_row.get("relation"),
        "substitutability": filtered_row.get("substitutability"),
        "threshold": filtered_row.get("threshold"),
        "qualification_status": filtered_row.get("qualification_status"),
        "evidence": filtered_row.get("evidence"),
        "demand_anchor": filtered_row.get("demand_anchor"),
        "demand_hops": filtered_row.get("demand_hops"),
        "has_overview": overview is not None,
        "our_bet": _cell_value((ov.get("brief") or {}).get("our_bet")),
        "payoff": payoff_value,
        "bet_state": bet_state,
        "bet_absence_reason": (payoff.get("reason") if payoff_value is None else None),
        "held": live is not None,
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
    # 第二個宇宙（Q1）：被門檻擋下、但**已研究過**的那些（`below_threshold`）。
    # `unfilled` 刻意不進來——那是研究缺口不是候選，它的去處是 pq1（zoom-out §7 Q1-A）。
    moat_tickers = {str(r["ticker"]) for r in rows if r.get("ticker")}
    volume_rows: list[dict[str, Any]] = []
    volume_seen: set[str] = set()
    for filtered_row in ranking.get("filtered_rows") or ():
        if "substitutability_below_threshold" not in (filtered_row.get("reasons") or ()):
            continue
        ticker = filtered_row.get("ticker")
        if not ticker or str(ticker) in volume_seen:
            continue                                # 一家一列：這一頁的單位是公司不是邊
        volume_seen.add(str(ticker))
        volume_rows.append(build_volume_row(
            filtered_row, overviews.get(str(ticker)), live_by_ticker.get(str(ticker)),
            in_moat_basket=str(ticker) in moat_tickers))
    volume_rows.sort(key=lambda r: str(r["ticker"]))   # 字母序；見 VOLUME_ORDER_NOTE
    volume_accepted = [r for r in volume_rows if r["passes_filter"]]
    volume_reason_counts = {key: sum(1 for r in volume_rows if key in r["filter_reasons"])
                            for key in VOLUME_FILTER_REASONS}
    volume_bet_counts = {state: sum(1 for r in volume_rows if r["bet_state"] == state)
                         for state in BET_STATES}

    accepted = [r for r in rows if r["passes_filter"]]
    reason_counts = {key: sum(1 for r in rows if key in r["filter_reasons"]) for key in FILTER_REASONS}
    # 賭注帳：每個 state 都印，**0 也印**——「欠 0 個答案」與「這一格沒算」不得同形（INV-3）。
    bet_counts = {state: sum(1 for r in rows if r["bet_state"] == state) for state in BET_STATES}
    # 歸零旗標帳（D2）：**盞數**與**有紅燈的檔數**分開算。合成一個數字就答不出
    # 「是一檔亮四盞，還是四檔各亮一盞」——那是兩件完全不同的事。
    wipe_lamp_counts = {colour: 0 for colour in ("red", "amber", "green", "unlit")}
    wipe_red_tickers: list[str] = []
    wipe_no_flags: list[str] = []
    for r in rows:
        tally = ((r.get("wipeout") or {}).get("tally")) or {}
        if not tally:
            wipe_no_flags.append(str(r["ticker"]))
            continue
        for colour in wipe_lamp_counts:
            wipe_lamp_counts[colour] += int(tally.get(colour) or 0)
        if int(tally.get("red") or 0):
            wipe_red_tickers.append(str(r["ticker"]))
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
        # 量的候選（Q1）：**分開呈現、分開判定**，刻意不與護城河那份合併計數——
        # 兩個宇宙問的是不同的問題，合起來的數字沒有意義。
        "volume_rows": volume_rows,
        "volume_filter": {
            "input": len(volume_rows), "accepted": len(volume_accepted),
            "filtered": len(volume_rows) - len(volume_accepted),
            "reasons": volume_reason_counts, "reason_labels": dict(VOLUME_FILTER_REASONS),
            "order_note": VOLUME_ORDER_NOTE,
            "missing_criteria": list(VOLUME_MISSING_CRITERIA),
            "universe_note": ("來源＝rank_bottlenecks 的 filtered_rows 中 substitutability_below_threshold 那些"
                              "（已研究、答案是否定的）。substitutability_unfilled 不進來——"
                              "那是研究缺口，去 pq1。門檻與排序一字未動。"),
        },
        "volume_bet_ledger": {**volume_bet_counts, "input": len(volume_rows),
                              "owed": [r["ticker"] for r in volume_rows if r["bet_state"] == "unanswered"],
                              "owed_opinion_in_base": [r["ticker"] for r in volume_rows
                                                       if r["bet_state"] == "opinion_in_base"]},
        "bet_ledger": {**bet_counts, "input": len(rows),
                       "state_labels": dict(BET_STATES), "rule": BET_LEDGER_RULE,
                       "owed": [r["ticker"] for r in rows if r["bet_state"] == "unanswered"],
                       "owed_opinion_in_base": [r["ticker"] for r in rows
                                                if r["bet_state"] == "opinion_in_base"]},
        # D2（2026-09-18）歸零旗標帳。**量測不是篩選**：它不參與 `filter`、不進 `top_pick` 的條件。
        "wipeout_ledger": {
            "companies": len(rows), "lamps": wipe_lamp_counts,
            "red_tickers": wipe_red_tickers,
            "no_flags_tickers": wipe_no_flags,
            "rule": ("每檔四盞：現金跑道／負債／稀釋／going concern。**灰＝沒量到，不是綠**；"
                     "燈不參與排序、不決定尺寸、不進 filter（AGENTS「須區分量測、訊號與脈絡」）"),
        },
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
                  "volume": [[r["ticker"], r["bet_state"], r["passes_filter"]] for r in volume_rows],
                  "top_pick": top["ticker"] if top else None})
    payload["content_digest"] = canonical_digest(payload)
    return payload


__all__ = ["BASKET_THIS_IS_NOT", "BET_LEDGER_RULE", "BET_STATES", "CATALYST_REASONS",
           "FILTER_REASONS", "FILTER_RULE",
           "OPINION_IN_BASE_STANCES",
           "SHIPPING_STATUSES", "VOLUME_FILTER_REASONS", "VOLUME_MISSING_CRITERIA", "VOLUME_ORDER_NOTE",
           "build_volume_row",
           "build_basket_artifact", "build_basket_row"]
