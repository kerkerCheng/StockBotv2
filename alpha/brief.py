"""Alpha 在 daily brief 裡的 pane：瓶頸排序、研究缺口、排序品質、持倉事件。

## 為什麼 pane 住在 domain 而不是 brief

`brief.py` 會長成 1,462 行的全系統儀表板，成因只有一個（`engine-d-decomposition.md`
§0 第 3 點）：**使用者說「這個也放進來」時，最短路徑是在 `brief.py` 加一段。**
把 pane 放回它自己的 domain，那條最短路徑就通往正確的地方——要加一塊 alpha 的
呈現，你會來這裡，而這裡看不到 Decision Store，所以加不出需要凍結 authority 的
東西。**只搬 code 不改這條，兩個月後會原地重演。**

## 這一層絕不做的事

- **不排序。** 唯一排序權威是 `query/bottleneck.py` 的 `rank_bottlenecks()`
  （`alpha/ranking.py` 是它的純轉換層）。本檔只把已排好的列渲染成表。
- **不取數。** 讀 Neo4j／狀態檔的部分住 `engine_d_runtime.adapters` 與
  `briefing/sources.py`；這裡是純函式，注入什麼渲染什麼。
- **不給尺寸。** Alpha 呈現契約：系統終點是瓶頸度排序，資本表達層已於
  2026-08-28 整組移除。
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from shared.markdown import markdown_text, pct

__all__ = [
    "build_ready_not_ranked",
    "render_outcome_aggregate",
    "render_position_events",
    "render_ranking",
    "render_ready_not_ranked",
]


def build_ready_not_ranked(
    items: Sequence[Mapping[str, Any]],
    ranking: Mapping[str, Any] | None,
) -> list[dict[str, Any]] | None:
    """C-1（ROADMAP 2026-08-29）：研究完整（READY）且尚無 live choice，卻不在瓶頸排序內。

    這兩邊都不在的標的等於「研究做完整之後反而消失」。這份常駐清單只呈現、
    不催辦、不建 pq2 編號。

    ⚠ `ranking` 未注入時回 `None`，**不與「沒有這類標的」的空 list 混用**（L12）：
    無法比對和比對後為空是兩件事，前者代表使用者少看了一塊，後者代表沒問題。
    """

    if not ranking:
        return None
    # 優先用截斷前的完整候選集合（`alpha.ranking` 的 `company_ids`）；舊 DTO 沒有
    # 這個欄位時退回 rows——此時只帶前 limit 名，排在其後的公司會被誤判成
    # 「不在排序」，寧可標示保守也不猜。
    ranked_company_ids = set(ranking.get("company_ids") or []) or {
        str(row.get("company_id") or "")
        for key in ("actionable", "structural")
        for row in (ranking.get(key) or [])
    }
    return [
        {
            "company_id": item["company_id"],
            "weakest_axis": item.get("weakest_axis"),
            "attention": item["attention"],
        }
        for item in items
        if item.get("research_status") == "READY"
        and not item.get("live_user_choice")
        and item["company_id"] != "unresolved"
        and item["company_id"] not in ranked_company_ids
    ]


_TABLE_HEAD = [
    "| 全域# | 標的 | 卡在哪 | 替代難度 | 證據 | 最弱軸 |",
    "|---|---|---|---|---|---|",
]


def _row_line(row: Mapping[str, Any]) -> str:
    ticker = markdown_text(row.get("ticker") or row.get("company_id") or "?")
    anchor_note = "" if not row.get("no_demand_anchor") else " 🔴無需求錨點"
    return (
        f"| {row.get('rank')} | {ticker}{anchor_note} "
        f"| {markdown_text(row.get('bottleneck') or '')} "
        f"| {row.get('substitutability') or '—'}"
        f"{'｜sole_source' if row.get('sole_source') else ''} "
        f"| {markdown_text(row.get('evidence') or '')} "
        f"| {markdown_text(row.get('weakest_axis') or '—')} |"
    )


def render_ranking(ranking: Mapping[str, Any] | None) -> list[str]:
    """瓶頸排序區——首屏第一塊。

    兩份排序並列且各自帶用途說明：它們回答不同問題、不可互換，並排放才看得出差異
    （可行動第 1 名與純結構第 1 名通常不同）。
    """
    if not ranking:
        return [
            "# 瓶頸排序",
            "",
            "⚠ 本次未提供排序資料（未注入 ranking）——不是「沒有候選」。",
            "",
        ]
    lines = ["# 瓶頸排序", ""]

    for key, label_key, total_key in (
        ("actionable", "actionable_purpose", "actionable_total"),
        ("structural", "structural_purpose", "structural_total"),
    ):
        lines.append(f"## {markdown_text(ranking.get(label_key) or key)}")
        lines.append("")
        # 族群分段視圖（2026-09-02 使用者定案）：各段有自己的第一名，# 欄保留全域名次
        # 供跨段比較。舊 DTO 沒有 *_by_sector 時回退到全域混排表。
        sectors = ranking.get(f"{key}_by_sector")
        if sectors:
            for seg in sectors:
                entries = seg.get("entries") or []
                if not entries:
                    continue
                seg_total = seg.get("total")
                more = (
                    f"（族群共 {seg_total}，顯示前 {len(entries)}）"
                    if isinstance(seg_total, int) and seg_total > len(entries)
                    else ""
                )
                lines.append(f"### {markdown_text(seg.get('sector') or '?')}{more}")
                lines.append("")
                lines += _TABLE_HEAD
                lines += [_row_line(row) for row in entries]
                lines.append("")
            total = ranking.get(total_key)
            if isinstance(total, int):
                lines.append(f"（全域候選共 {total}；# 欄為全域名次）")
            lines.append("")
            continue
        rows = ranking.get(key) or []
        if not rows:
            lines += ["（無候選）", ""]
            continue
        lines += _TABLE_HEAD
        lines += [_row_line(row) for row in rows]
        total = ranking.get(total_key)
        if isinstance(total, int) and total > len(rows):
            lines.append("")
            lines.append(f"（共 {total} 個候選，此處顯示前 {len(rows)}）")
        lines.append("")
    note = ranking.get("judgment_note")
    if note:
        lines += [f"⚠ {markdown_text(note)}", ""]
    for caveat in ranking.get("caveats") or []:
        lines.append(f"- {markdown_text(caveat)}")
    lines.append("")
    return lines


def render_ready_not_ranked(rows: Sequence[Mapping[str, Any]] | None) -> list[str]:
    """C-1 常駐清單：研究完整但不在瓶頸排序內——只呈現，不催辦。

    `None`（ranking 未注入、無法比對）時整區不渲染：成因已由排序區的
    「未提供排序資料」警告現形，這裡再印一次是重複噪音。空 list 仍要渲染
    「（無）」——常駐計數器的意義就是讓 0 也自己出現（L14）。
    """
    if rows is None:
        return []
    lines = ["## 研究完整但不在瓶頸排序內（常駐；只呈現，不催辦）", ""]
    if not rows:
        lines += ["（無）", ""]
        return lines
    for row in rows:
        axis = markdown_text(row.get("weakest_axis") or "—")
        lines.append(
            f"- {markdown_text(row.get('company_id') or '?')}（最弱軸：{axis}）"
            "——它的邊不在 substitutability≥4 的候選內（未填值或低替代難度），"
            "研究已完整，等事件即可；若認為它該進排序，該補的是邊上的 substitutability"
        )
    lines.append("")
    return lines


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


def render_outcome_aggregate(
    aggregate: Mapping[str, Any] | None, *, measured_key_present: bool
) -> list[str]:
    """排序品質計數器（2026-09-02）：等權聚合是「排序準不準」的裁判數字（L14 常駐）。

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
        return [
            f"- 排序品質：推薦籃等權 {aggregate.get('n')} 檔 絕對 "
            f"{aggregate.get('equal_weight_absolute'):+.1%}{excess_text}"
            f"（量測日 {markdown_text(aggregate.get('date') or '?')}；粗聚合非回測，"
            "前/後段對照待快照累積）"
        ]
    if measured_key_present:
        return ["- 排序品質：尚無量測——跑 `scripts/outcome_if_settled_today.py` 產生"]
    return []
