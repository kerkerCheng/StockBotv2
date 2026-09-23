"""Alpha 在 daily brief 裡的 pane：等權聚合、持倉事件。

⚠ 2026-09-23（Phase 0 Step 0b.3）：瓶頸排序 pane（`render_ranking`）與「研究完整但不在排序內」
常駐清單（`build_ready_not_ranked`／`render_ready_not_ranked`）隨跨檔排序退役（G1／L19）。

## 為什麼 pane 住在 domain 而不是 brief

`brief.py` 會長成 1,462 行的全系統儀表板，成因只有一個（`engine-d-decomposition.md`
§0 第 3 點）：**使用者說「這個也放進來」時，最短路徑是在 `brief.py` 加一段。**
把 pane 放回它自己的 domain，那條最短路徑就通往正確的地方——要加一塊 alpha 的
呈現，你會來這裡，而這裡看不到 Decision Store，所以加不出需要凍結 authority 的
東西。**只搬 code 不改這條，兩個月後會原地重演。**

## 這一層絕不做的事

- **不排序。** 跨檔排序已退役；本檔只渲染注入的量測，不產生任何順序。
- **不取數。** 讀 Neo4j／狀態檔的部分住 `engine_d_runtime.adapters` 與
  `briefing/sources.py`；這裡是純函式，注入什麼渲染什麼。
- **不給尺寸。** Alpha 呈現契約：系統終點是瓶頸度排序，資本表達層已於
  2026-08-28 整組移除。
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from shared.markdown import markdown_text, pct

__all__ = [
    "render_outcome_aggregate",
    "render_position_events",
]


def render_position_events(events: Sequence[Mapping[str, Any]] | None) -> list[str]:
    """Alpha live 部位的單日跌幅事件。

    擺在首屏 counters 之前：它講的是**已經投出去的錢正在發生什麼**，優先於研究
    進展。exception-first——沒觸發就完全不出現，不佔版面。
    """
    lines: list[str] = []
    for event in events or []:
        ticker = markdown_text(event.get("ticker") or "未知標的")
        session = markdown_text(event.get("session_date") or "最近交易日")
        day = pct(event.get("return_1d"))
        since = pct(event.get("return_since_entry"))
        raw_weight = event.get("position_weight")
        weight = (
            f"{raw_weight * 100:.2f}%"
            if isinstance(raw_weight, (int, float)) and not isinstance(raw_weight, bool)
            else "未知"
        )
        lines.append(
            f"- 🔴 持倉事件：{ticker} 於 {session} 單日 {day}"
            f"（距進場 {since}，部位約 {weight} NAV）"
            "　→ 請對此標的做一次 WebSearch 找可能原因，結果未經查證、不建 lead"
        )
    return lines


def _render_power_law_line(power: Mapping[str, Any] | None) -> list[str]:
    """D15 三量的首屏一行：**一檔扛了多少、其餘幾檔合計多少、有沒有翻過倍**。

    ⚠ 等權絕對報酬回答「排序整體準不準」，這一行回答**完全不同的問題**——
    「有沒有抓到那一檔」。power-law 的賭注是小賠多檔一檔補回，所以平均值天生
    看不到它想看的東西（AGENTS「目標是倍率不是錯價」）。兩行並存不是重複。

    ⚠ **沒有 `power_law` 就整行不印**，不印 0：`outcome_aggregate.json` 是舊版
    腳本落下的（那時還沒有這三個數字）與「跑了但一檔都沒翻倍」是兩件事（L12）。
    """
    if not isinstance(power, Mapping) or not power.get("n"):
        return []
    top = power.get("top_contributor") or {}
    rest = top.get("rest_contribution")
    contribution = top.get("contribution")
    if not isinstance(contribution, (int, float)) or not isinstance(rest, (int, float)):
        return []
    days = power.get("max_days_held")
    # ⚠ 尾句由資料決定，**不寫死「分母還沒出現」**——那是會腐壞的現況句
    # （AGENTS「現況數字會過期，判準不會」）。有檔滿 12 個月的那天，它要自己改口。
    maturity = power.get("maturity") or {}
    matured = [label for label in ("12m", "24m")
               if (maturity.get(label) or {}).get("matured")]
    if matured:
        tail = "　←" + "；".join(
            f"{label} 分母 {maturity[label]['matured']} 檔、達 2 倍 {maturity[label]['reached_2x']}"
            for label in matured
        )
    else:
        tail = "　←12／24 個月的分母都還沒出現，這是進行中的下界"
    return [
        f"- power-law：最大單檔 {markdown_text(str(top.get('ticker') or '?'))} "
        f"貢獻 {contribution:+.2%}，其餘 {top.get('rest_n')} 檔合計 {rest:+.2%}；"
        f"曾達 2 倍 {power.get('reached_2x_ever')}/{power.get('peak_measured')} 檔"
        f"（現價仍在 2 倍以上 {power.get('reached_2x_now')}）"
        f"｜量測起始 {markdown_text(str(power.get('measurement_start') or '?'))}、"
        f"最長已持有 {days if days is not None else '?'} 天"
        + tail
    ]


def render_outcome_aggregate(
    aggregate: Mapping[str, Any] | None, *, measured_key_present: bool
) -> list[str]:
    """等權聚合計數器（2026-09-02）：研究 cohort 等權的量測基準（L14 常駐；2026-09-23 起不再叫「排序品質」——排序退役）。

    `measured_key_present` 區分兩種缺席（L12）：這個 surface 根本沒有這一欄
    （整行略過）vs. 有這一欄但從未量測（要現形，並附產生指令）。
    """
    if aggregate:
        excess = aggregate.get("equal_weight_excess")
        excess_text = (
            f"｜超額({markdown_text(aggregate.get('benchmark') or '?')}) {excess:+.1%}"
            if isinstance(excess, (int, float))
            else ""
        )
        lines = [
            f"- 等權聚合：研究 cohort 等權 {aggregate.get('n')} 檔 絕對 "
            f"{aggregate.get('equal_weight_absolute'):+.1%}{excess_text}"
            f"（量測日 {markdown_text(aggregate.get('date') or '?')}；粗聚合非回測）"
        ]
        lines += _render_power_law_line(aggregate.get("power_law"))
        return lines
    if measured_key_present:
        return ["- 等權聚合：尚無量測——跑 `scripts/outcome_if_settled_today.py` 產生"]
    return []
