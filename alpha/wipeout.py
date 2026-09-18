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

看到股數增加是**事實**（可證實，窗多短都算數）；沒看到增加**不等於沒有增發**（窗可能太短）。
所以：增加 → 判色；沒增加且窗不滿一個完整會計年度 → 灰並帶到期日（INV-2：每個等待都必須有到期）。

## 燈只給顏色與一句話，數字住稽核層

`reason` 刻意不含該公司的任何數值（D2「紅黃綠不給數字」）；`inputs` 帶著算出這盞燈的原始值，
供稽核層逐格顯示。消費層渲染 `colour` ＋ `reason`，稽核層渲染 `inputs` ＋ `rule`。
"""
from __future__ import annotations

from datetime import date
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
    """`runway` 是 `decision_lab.derive_runway` 的輸出形狀（status／runway_months／三個輸入）。"""
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
    f"窗滿 {FULL_YEAR_DAYS} 天（一個完整會計年度）才判色：沒增加 → 綠；增加 → 黃。"
    "**窗不滿就是灰**——「我沒看到增發」與「它沒有增發」是兩個不同的 claim，後者舉證責任高得多"
    "（L11-5）。⚠ **刻意不用燒錢與否把黃再切成紅**：那需要分辨員工股酬與真增發，而那是量級問題，"
    "今天沒有非憑空的門檻可用（實測見 docstring）"
)


def dilution_flag(shares_series: Sequence[tuple[date, float]] | None,
                  runway: Mapping[str, Any] | None, *, today: date) -> dict[str, Any]:
    """`shares_series` 是**同口徑**的在外流通股數序列（日期遞增）。

    ⚠ 刻意不吃「會計年度稀釋股數 vs 今日在外流通股數」那一組：窗夠長但**口徑不同**
    （diluted 含潛在股份、outstanding 不含），相減出來的數字沒有意義——那正是封閉字彙
    `inputs_incompatible` 在描述的東西。

    ⚠⚠ **首版被真實資料當場推翻，經過留在這裡**（2026-09-18）：第一版用「窗內有沒有增加」
    ×「燒不燒錢」判紅黃，一跑 16 檔就看到 COHR **+0.10%**（54 天，員工股酬等級）與 LITE
    **+15.30%**（53 天，量級完全不同）拿到同一組規則的顏色，IQE.L 更是靠 **+0.0044%** 亮紅。
    那是 L12 的形狀：`change > 0` 這一個表示同時承載「員工股酬雜訊」與「靠發股補現金缺口」，
    下游二選一而兩邊都錯。**修法不是設一個量級門檻**（那是憑空參數，INV-5），是把判不出來的
    那一半留白：量級問題交給稽核層的數字，而「是不是靠外部資金活著」本來就由現金跑道與負債
    那兩盞回答了——這盞燈在那個問題上沒有增加任何資訊。
    """
    rows = [(d, v) for d, v in (shares_series or ()) if isinstance(v, (int, float)) and v > 0]
    fcf = (runway or {}).get("free_cash_flow_ttm")
    if len(rows) < 2:
        return _flag(None, "同口徑的股數序列不足兩點，看不出增減", rule=_DILUTION_RULE,
                     inputs={"n_points": len(rows)}, absence_kind="upstream_unavailable")
    first, last = rows[0], rows[-1]
    span_days = (last[0] - first[0]).days
    change = (last[1] - first[1]) / first[1]
    # `span_days` 量的是**觀測窗**（第一點到最後一點），不是「從第一點到今天」——ETL 停了半年的話，
    # 我們有的不是一年的觀測，是半年的觀測加半年的空白。`days_since_last` 把那段空白單獨印出來，
    # 讓稽核層看得到「這條序列還活著嗎」，而不是讓它悄悄混進窗長裡（L12）。
    inputs = {"n_points": len(rows), "distinct_values": len({v for _, v in rows}),
              "first_date": first[0], "first_shares": first[1],
              "last_date": last[0], "last_shares": last[1],
              "span_days": span_days, "days_since_last": (today - last[0]).days,
              "change": change, "free_cash_flow_ttm": fcf}
    if span_days >= FULL_YEAR_DAYS:
        if change > 0:
            return _flag("amber", "滿一個完整會計年度的同口徑股數增加了", rule=_DILUTION_RULE, inputs=inputs)
        return _flag("green", "滿一個完整會計年度的同口徑股數沒有增加", rule=_DILUTION_RULE, inputs=inputs)
    # 有到期的等待（INV-2：每個等待都必須有到期）：窗會自己長到一年，那天這盞燈自己判色，
    # 不必有人記得回來。**窗內看到的變化照樣進 `inputs`**——稽核層看得到，只是不拿它上色。
    inputs["colour_available_on"] = first[0].replace(year=first[0].year + 1)
    return _flag(None, "同口徑的股數觀測窗還不滿一個完整會計年度，窗內的變化分不出員工股酬與增發",
                 rule=_DILUTION_RULE, inputs=inputs, absence_kind="insufficient_evidence")


_GOING_CONCERN_RULE = (
    "只認**結構化**的 going-concern 判讀。逐字的審計意見是 `judgment` 欄位（L11-1：going concern、"
    "保留意見這類措辭精度本身就是一個 claim），機械比對不得從自由文字推顏色（L15-2：語意交給語言"
    "處理、權限永遠 deterministic）——所以這盞燈寧可不亮，也不猜"
)


def going_concern_flag(observation: Mapping[str, Any] | None) -> dict[str, Any]:
    """今天必然回灰：系統還沒有承載「結構化 going-concern 判讀」的欄位。

    ⚠ 這不是「沒資料」，是**沒有能讓它判色的欄位**（`capability_absent`）。IQE.L 是 D7 指定的
    第一個案例，它的逐字內容目前躺在 `debt_maturity_and_covenants` 裡——**分類有 SSOT 卻沒有
    跟著資料走到需要它的地方**，那正是 L16 的形狀。
    """
    has_text = bool((observation or {}).get("value"))
    return _flag(None,
                 ("已有逐字核對的審計意見紀錄，但它是自由文字，機械判不出顏色"
                  if has_text else "還沒有任何結構化的 going-concern 判讀"),
                 rule=_GOING_CONCERN_RULE,
                 inputs={"has_verbatim_record": has_text,
                         "source_field": "litigation_and_audit_flags"},
                 absence_kind="capability_absent")


def wipeout_flags(*, runway: Mapping[str, Any] | None,
                  shares_series: Sequence[tuple[date, float]] | None,
                  going_concern: Mapping[str, Any] | None,
                  today: date) -> dict[str, dict[str, Any]]:
    """四盞燈一次算出。**每盞都回值**——少一盞與「那盞是綠的」不得同形（INV-3）。"""
    out = {
        "cash_runway": cash_runway_flag(runway),
        "debt": debt_flag(runway),
        "dilution": dilution_flag(shares_series, runway, today=today),
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
