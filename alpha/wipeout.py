"""歸零旗標（D2，2026-09-18）：**這家公司會不會歸零**的四盞燈——現金跑道／負債／稀釋／going concern。

純函式，零相依、不連 DB。它們是**量測不是訊號**（AGENTS「須區分量測、訊號與脈絡」，歸零旗標與
總曝險倍數、追繳門檻同一類）：**不參與排序、不決定尺寸、不產生進出場建議**。

## 兩條不可退讓的設計判準

1. **綠燈只能由「量到了而且沒事」產生，不得由「沒量到」產生。**
   這是 L12（一表兩義：同一個表示同時承載兩件事，下游二選一而兩邊都錯）在這裡的樣子——
   把「沒查」塗成綠會給出一個憑空的安心，而那正是歸零旗標要防的失敗。所以每盞燈的第四態是
   **灰（`colour=None`）＋ 封閉字彙的 `absence_kind`**，由走到那個分支的程式自己宣告（L16），
   呈現層不得 parse 理由句去猜。

2. **零憑空參數。** 可判色的三盞只用「符號比較」加**兩個外部錨定的常數**：
   `GOING_CONCERN_HORIZON_MONTHS = 12` 是 IFRS／UK 規定董事與查核人員評估 going concern 的
   最短期間；`FULL_YEAR_DAYS = 365` 是一個完整會計年度。兩個都指得出出處，不是我們挑的數字
   （INV-5：未量測的機制不得享有默認信任——門檻自己也要指得出出處）。

## 稀釋那盞刻意**不對稱**

看到**新股發行紀錄**是**事實**（可證實，窗多短都算數）；沒看到**不等於沒有增發**（窗可能太短、公司可能沒標 tag）。
所以：有發行紀錄 → 黃；沒有紀錄、股數也沒增加、窗滿一年 → 綠；其餘 → 灰並說是哪一種（INV-2：窗不滿的等待帶到期日）。
⚠ 2026-10-01（Phase 4 Step 4.6）判色輸入由「封面股數有沒有增加」改成「新股發行金額」：股數增加同時承載員工股酬與
真增發（L12），4.0 實測國內申報人 30 檔有 24 檔亮黃——那是恆亮（L14-4）。股數變化仍照印在稽核層。

## 燈只給顏色與一句話，數字住稽核層

`reason` 刻意不含該公司的任何數值（D2「紅黃綠不給數字」）；`inputs` 帶著算出這盞燈的原始值，
供稽核層逐格顯示。消費層渲染 `colour` ＋ `reason`，稽核層渲染 `inputs` ＋ `rule`。
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Mapping, Sequence

#: 四盞燈的封閉清單。新增一盞＝改契約，不是加一個字串。
WIPEOUT_LANES: tuple[str, ...] = ("cash_runway", "debt", "dilution", "going_concern")

#: 顏色的封閉字彙。**灰不在這裡**——灰是「沒有顏色」（`colour=None`）＋ 一個 `absence_kind`，
#: 讓「這盞燈是綠的」與「這盞燈沒點亮」在型別上就不可能同形。
FLAG_COLOURS: tuple[str, ...] = ("red", "amber", "green")

LANE_LABELS: Mapping[str, str] = {
    "cash_runway": "現金跑道",
    "debt": "負債",
    "dilution": "稀釋",
    "going_concern": "going concern",
}

#: IFRS／UK 要求董事與查核人員評估 going concern 的**最短期間**。外部錨，不是我們挑的數字。
GOING_CONCERN_HORIZON_MONTHS: int = 12

#: 一個完整會計年度。稀釋那盞要判「綠」時，觀測窗至少要這麼長。
FULL_YEAR_DAYS: int = 365


def _flag(colour: str | None, reason: str, *, rule: str, inputs: Mapping[str, Any],
          absence_kind: str | None = None) -> dict[str, Any]:
    if colour is not None and colour not in FLAG_COLOURS:
        raise ValueError(f"未登記的燈色：{colour!r}；已知 {FLAG_COLOURS}")
    if colour is None and not absence_kind:
        raise ValueError("沒有顏色的燈必須宣告 absence_kind——缺席不得被壓成一句「無資料」")
    if colour is not None and absence_kind:
        raise ValueError("有顏色的燈不得帶缺席語意")
    return {"colour": colour, "reason": reason, "absence_kind": absence_kind,
            "rule": rule, "inputs": dict(inputs)}


_CASH_RULE = (f"自由現金流 ≥ 0 → 綠（自籌）；燒錢且現金跑道短於 {GOING_CONCERN_HORIZON_MONTHS} 個月"
              "（IFRS／UK going-concern 最短評估期）→ 紅；燒錢但跑道長於它 → 黃；三個輸入缺一 → 灰")


def cash_runway_flag(runway: Mapping[str, Any] | None) -> dict[str, Any]:
    """`runway` 是 `shared.runway.derive_runway` 的輸出形狀（status／runway_months／三個輸入）。"""
    runway = dict(runway or {})
    inputs = {k: runway.get(k) for k in ("cash_and_equivalents", "total_debt", "free_cash_flow_ttm",
                                         "as_of", "source", "status", "runway_months")}
    status = runway.get("status")
    if status == "self_funding":
        return _flag("green", "自由現金流為正——不靠外部資金也能維持營運", rule=_CASH_RULE, inputs=inputs)
    if status == "calculated":
        months = runway.get("runway_months")
        if not isinstance(months, (int, float)):
            return _flag(None, "跑道狀態宣稱已算出，卻沒有月數", rule=_CASH_RULE, inputs=inputs,
                         absence_kind="upstream_unavailable")
        if months < GOING_CONCERN_HORIZON_MONTHS:
            return _flag("red", "手上現金撐不到一個 going-concern 評估期", rule=_CASH_RULE, inputs=inputs)
        return _flag("amber", "在燒錢，但現金撐得過一個 going-concern 評估期", rule=_CASH_RULE, inputs=inputs)
    return _flag(None, "現金／總債／自由現金流三個輸入缺一即不推導（部分推導只會給出看起來精確的錯值）",
                 rule=_CASH_RULE, inputs=inputs, absence_kind="upstream_unavailable")


_DEBT_RULE = ("現金 ≥ 總債 → 綠（淨現金）；淨負債且自由現金流 ≥ 0 → 黃；淨負債且在燒錢 → 紅。"
              "**純符號比較，沒有門檻**——歸零的機制是「要還的錢多於手上的錢，而且自己生不出來」")


def debt_flag(runway: Mapping[str, Any] | None) -> dict[str, Any]:
    """與現金跑道共用同一組輸入：債務的歸零風險問的是「還得出來嗎」，不是「借了多少」。"""
    runway = dict(runway or {})
    cash = runway.get("cash_and_equivalents")
    debt = runway.get("total_debt")
    fcf = runway.get("free_cash_flow_ttm")
    inputs = {"cash_and_equivalents": cash, "total_debt": debt, "free_cash_flow_ttm": fcf,
              "as_of": runway.get("as_of"), "source": runway.get("source")}
    if not isinstance(cash, (int, float)) or not isinstance(debt, (int, float)):
        return _flag(None, "缺現金或總債，不推導", rule=_DEBT_RULE, inputs=inputs,
                     absence_kind="upstream_unavailable")
    if cash >= debt:
        return _flag("green", "淨現金——手上的錢多於要還的錢", rule=_DEBT_RULE, inputs=inputs)
    if not isinstance(fcf, (int, float)):
        return _flag(None, "是淨負債，但缺自由現金流，判不出還得出來還不出來", rule=_DEBT_RULE,
                     inputs=inputs, absence_kind="upstream_unavailable")
    if fcf >= 0:
        return _flag("amber", "淨負債，但自由現金流為正——還本靠自己生得出來", rule=_DEBT_RULE, inputs=inputs)
    return _flag("red", "淨負債而且在燒錢——還本得靠再融資", rule=_DEBT_RULE, inputs=inputs)


_DILUTION_RULE = (
    "**10-K／10-Q 國內申報人**：最近四季（期末落在最新已申報季度期末往回 320 天內的季度——相鄰季度期末相距 80–100 天，"
    "日曆季與 52／53 週制都剛好四季；年度期末正好是窗尾就用年度那一列）的新股發行金額"
    "（us-gaap:StockIssuedDuringPeriodValueNewIssues，SEC companyfacts）**任何一筆 > 0** → 黃（淨加總只印：負值多半是更正，"
    "或年報與季報 tag 前後不一衍生出的負第四季——不拿來抵銷真實發行）；窗內沒有正值、但期末落在窗內的年度有歸不到季的發行"
    "（年報有、季報加起來不到），或 tag 前後不一（負的衍生季、年度小於季度加總）→ 灰（insufficient_evidence）；"
    f"窗內沒有發行紀錄、同口徑股數也沒增加、股數觀測窗滿 {FULL_YEAR_DAYS} 天 → 綠；"
    "股數增加了卻沒有發行紀錄 → 灰（insufficient_evidence：分不出員工股酬與沒標 tag 的增發）；"
    "股數窗不滿一年且沒有發行紀錄 → 灰（附到期日）。5 年回填窗內沒有可存的這個 tag → 灰（provider_missing）；"
    "其他申報人 → 灰（method_not_applicable）。金額、占正規化市值 %、tag、歸不到季的年度差額、前後不一、同期股數變化與"
    " ATM／shelf 授權只印在稽核層、不參與判色；金額只計這一個 tag（公司另用自訂 tag 標的發行不在內）＝已知至少。"
    "可轉換特別股的發行照算黃——companyfacts 分不出普通股或特別股，稽核層的 accession 指得回申報原文，讀原文可改判；"
    "員工股票計畫若標在同一個 tag 也算黃（占市值 % 印出來）。⚠ 刻意不用量級門檻把黃再切成紅或綠（INV-5：沒有非憑空的門檻）"
)


def _shares_window(shares_series: Sequence[tuple[date, float]] | None, *, today: date) -> dict[str, Any]:
    """同口徑股數的 trailing 一年窗：最新一點 vs 距它 ≥365 天的最近一點（不是整條序列的頭尾）。

    ⚠ 2026-09-29（Phase 3 Step 3.3）：比頭尾會讓回填到 2021 的序列幾乎每一檔都亮黃（五年的員工股酬累積，L14-4）。
    `span_days` 量的是觀測窗（比較的兩點之間），`days_since_last` 另印那段空白（序列還活著嗎，L12）。
    ⚠ 欄位名不得含 `shares`（`alpha.contracts.FORBIDDEN_POSITION_TOKENS`：黑箱輸出不帶部位語意的欄位名）——
    股數一律寫 `outstanding`。
    """
    rows = sorted((d, v) for d, v in (shares_series or ()) if isinstance(v, (int, float)) and v > 0)
    if len(rows) < 2:
        return {"n_points": len(rows), "eligible": False, "change": None}
    first, last = rows[0], rows[-1]
    eligible = [r for r in rows if (last[0] - r[0]).days >= FULL_YEAR_DAYS]
    base = eligible[-1] if eligible else first
    out = {"n_points": len(rows), "distinct_values": len({v for _, v in rows}),
           "series_start": first[0], "base_date": base[0], "base_outstanding": base[1],
           "last_date": last[0], "last_outstanding": last[1], "span_days": (last[0] - base[0]).days,
           "days_since_last": (today - last[0]).days, "change": (last[1] - base[1]) / base[1],
           "eligible": bool(eligible)}
    if not eligible:
        # 與上面的判準同一把尺（≥ FULL_YEAR_DAYS 天）；`replace(year=+1)` 遇到 2 月 29 日的封面日會丟例外
        out["colour_available_on"] = first[0] + timedelta(days=FULL_YEAR_DAYS)
    return out


def dilution_flag(shares_series: Sequence[tuple[date, float]] | None,
                  runway: Mapping[str, Any] | None, *, today: date, source: str | None = None,
                  issuance: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """稀釋燈。判色只看 `issuance`（新股發行金額，`engine_c.checklist._equity_issuance` 的形狀）；
    `shares_series`（同口徑在外流通股數）只決定「沒有發行紀錄時能不能說沒稀釋」並印在稽核層。

    ⚠⚠ **兩次被真實資料推翻，經過留在這裡**：
    ① 2026-09-18 首版用「窗內股數有沒有增加」×「燒不燒錢」判紅黃——COHR **+0.10%**（員工股酬等級）與 LITE
    **+15.30%** 拿到同一組顏色，IQE.L 靠 **+0.0044%** 亮紅（L12：`change > 0` 同時承載員工股酬與靠發股補缺口）。
    ② 2026-10-01 4.0 基準：trailing 一年股數比較讓國內申報人 30 檔亮黃 24 檔——仍是同一個形狀（恆亮，L14-4）。
    修法不是設量級門檻（INV-5），是換一個**只在真的發行新股時才有值**的輸入：companyfacts 的發行金額。
    """
    shares = _shares_window(shares_series, today=today)
    issuance = dict(issuance or {})
    status = issuance.get("status")
    inputs: dict[str, Any] = {key: value for key, value in shares.items() if key != "eligible"}
    inputs.update(source=source, free_cash_flow_ttm=(runway or {}).get("free_cash_flow_ttm"),
                  issuance_status=status or "not_provided", filer_class=issuance.get("filer_class"),
                  authorizations=issuance.get("authorizations"))
    change = shares.get("change")
    if isinstance(change, (int, float)):
        inputs["outstanding_note"] = f"同期封面股數 {change:+.1%}"
    if status == "method_not_applicable":
        return _flag(None, "不是按季申報的美國國內申報人——新股發行金額這個方法不適用（股數變化照印在稽核層）",
                     rule=_DILUTION_RULE, inputs=inputs, absence_kind="method_not_applicable")
    if status == "provider_missing":
        inputs["issuance_reason"] = issuance.get("reason")
        return _flag(None, "回填窗內沒有新股發行金額的申報紀錄——說不出有沒有增發（股數變化照印在稽核層）",
                     rule=_DILUTION_RULE, inputs=inputs, absence_kind="provider_missing")
    if status != "ok":
        inputs["issuance_reason"] = issuance.get("reason")
        return _flag(None, "沒有讀到新股發行金額（上游缺席）", rule=_DILUTION_RULE, inputs=inputs,
                     absence_kind="upstream_unavailable")
    total = float(issuance.get("trailing_total") or 0.0)
    # 判色看窗內正值的加總（R2-c 覆核 #1：淨加總會被負值——更正或 tag 前後不一的負第四季——抵掉真實發行）
    issued = float(issuance["issued_total"]) if issuance.get("issued_total") is not None else max(total, 0.0)
    unattributed, inconsistent = list(issuance.get("unattributed") or ()), list(issuance.get("inconsistent") or ())
    currencies = list(issuance.get("currencies") or ())
    cap = issuance.get("market_cap_usd")
    inputs.update(window_after=issuance.get("window_after"), window_end=issuance.get("window_end"),
                  issuance_basis=issuance.get("basis"), quarters_found=issuance.get("quarters_found"),
                  trailing_issued=total, issued_total=issued, issued_currencies=currencies, tags=issuance.get("tags"),
                  facts=issuance.get("facts"), unattributed=unattributed, inconsistent=inconsistent,
                  market_cap_usd=cap, market_cap_absence=issuance.get("market_cap_absence"),
                  pct_of_market_cap=(issued / cap if currencies == ["USD"] and isinstance(cap, (int, float)) and cap > 0
                                     else None))
    if issued > 0:
        return _flag("amber", "一個完整會計年度內有新股發行紀錄", rule=_DILUTION_RULE, inputs=inputs)
    if unattributed or inconsistent:
        why = "；".join(x for x in ("年報有新股發行、季報加起來不到——歸不到季" if unattributed else "",
                                   "年報與季報的 tag 前後不一（負的衍生季或年度小於季度加總）" if inconsistent else "")
                       if x)
        return _flag(None, f"{why}——說不出最近四季有沒有增發",
                     rule=_DILUTION_RULE, inputs=inputs, absence_kind="insufficient_evidence")
    if not shares.get("eligible"):
        inputs["colour_available_on"] = shares.get("colour_available_on")
        return _flag(None, "窗內沒有新股發行紀錄，但同口徑股數的觀測窗還不滿一個完整會計年度——說不出沒有增發",
                     rule=_DILUTION_RULE, inputs=inputs, absence_kind="insufficient_evidence")
    if isinstance(change, (int, float)) and change > 0:
        inputs["outstanding_note"] = f"股數 {change:+.1%}（無新股發行紀錄）"
        return _flag(None, "同口徑股數增加了，但窗內沒有新股發行紀錄——分不出員工股酬與沒標 tag 的增發",
                     rule=_DILUTION_RULE, inputs=inputs, absence_kind="insufficient_evidence")
    return _flag("green", "一個完整會計年度內沒有新股發行紀錄，同口徑股數也沒有增加", rule=_DILUTION_RULE,
                 inputs=inputs)


_GOING_CONCERN_RULE = (
    "只認**結構化**的 going-concern 判讀（Engine C 欄位 `going_concern_opinion`，judgment、經 pq2 寫入）："
    "substantial_doubt → 紅；no_substantial_doubt → 綠；not_reviewed 或沒有紀錄 → 灰。逐字的審計意見本身"
    "是 claim（L11-1：going concern、保留意見這類措辭精度），機械比對不得從自由文字推顏色（L15-2）——"
    "`litigation_and_audit_flags` 的散文不讀"
)


def going_concern_flag(observation: Mapping[str, Any] | None) -> dict[str, Any]:
    """`observation`：`going_concern_opinion` 的生效紀錄 `{value: {opinion, quote, page, report_date}, source, as_of}`
    （Phase 3 Step 3.2 新增欄位、Step 3.3 接上）；沒有紀錄給 None。

    ⚠ 2026-09-29 以前這盞燈恆灰（`capability_absent`：沒有能讓它判色的欄位）。欄位存在之後，沒有紀錄就是
    **還沒人寫**（`not_yet_recorded`），不再是能力缺席——兩者的下一步不同（前者去讀年報，後者去建能力）。
    IQE.L 的 KPMG 逐字仍躺在 `debt_maturity_and_covenants`；它要經 pq2 寫進新欄位才會亮。
    """
    value = (observation or {}).get("value")
    opinion = value.get("opinion") if isinstance(value, Mapping) else None
    inputs = {"opinion": opinion, "source_field": "going_concern_opinion",
              "report_date": value.get("report_date") if isinstance(value, Mapping) else None,
              "page": value.get("page") if isinstance(value, Mapping) else None,
              "quote": value.get("quote") if isinstance(value, Mapping) else None,
              "as_of": (observation or {}).get("as_of"), "source": (observation or {}).get("source"),
              "conflict": (observation or {}).get("conflict")}
    if (observation or {}).get("conflict"):
        return _flag(None, "同一日期有多筆生效的 going-concern 判讀，不挑一個", rule=_GOING_CONCERN_RULE,
                     inputs=inputs, absence_kind="insufficient_evidence")
    if opinion == "substantial_doubt":
        return _flag("red", "查核意見對繼續經營表示重大疑慮", rule=_GOING_CONCERN_RULE, inputs=inputs)
    if opinion == "no_substantial_doubt":
        return _flag("green", "查核意見沒有繼續經營的重大疑慮", rule=_GOING_CONCERN_RULE, inputs=inputs)
    if opinion == "not_reviewed":
        return _flag(None, "已登記「還沒讀查核意見」", rule=_GOING_CONCERN_RULE, inputs=inputs,
                     absence_kind="not_yet_recorded")
    return _flag(None, "還沒有任何結構化的 going-concern 判讀", rule=_GOING_CONCERN_RULE, inputs=inputs,
                 absence_kind="not_yet_recorded")


def wipeout_flags(*, runway: Mapping[str, Any] | None,
                  shares_series: Sequence[tuple[date, float]] | None,
                  going_concern: Mapping[str, Any] | None,
                  today: date, shares_source: str | None = None,
                  issuance: Mapping[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """四盞燈一次算出。**每盞都回值**——少一盞與「那盞是綠的」不得同形（INV-3）。

    `issuance`：稀釋燈的新股發行金額（Phase 4 Step 4.6）；不給＝上游缺席（灰，不是綠）。"""
    out = {
        "cash_runway": cash_runway_flag(runway),
        "debt": debt_flag(runway),
        "dilution": dilution_flag(shares_series, runway, today=today, source=shares_source, issuance=issuance),
        "going_concern": going_concern_flag(going_concern),
    }
    if tuple(out) != WIPEOUT_LANES:
        raise ValueError(f"燈的順序／集合必須等於 WIPEOUT_LANES：{tuple(out)}")
    return out


def tally(flags: Mapping[str, Mapping[str, Any]]) -> dict[str, int]:
    """紅／黃／綠／灰各幾盞。**灰也是一個計數**，不是 0 的另一種寫法。"""
    counts: dict[str, int] = {colour: 0 for colour in FLAG_COLOURS}
    counts["unlit"] = 0
    for lane in flags.values():
        colour = (lane or {}).get("colour")
        counts[colour if colour in counts else "unlit"] += 1
    return counts


__all__ = ["FLAG_COLOURS", "FULL_YEAR_DAYS", "GOING_CONCERN_HORIZON_MONTHS", "LANE_LABELS",
           "WIPEOUT_LANES", "cash_runway_flag", "debt_flag", "dilution_flag",
           "going_concern_flag", "tally", "wipeout_flags"]
