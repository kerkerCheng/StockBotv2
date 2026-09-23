"""Portfolio 的 pane renderer：持股 NAV 比例（純呈現，零門檻）。

⚠ 2026-09-23（Phase 0 Step 0b.4）：`build_sheet_only_items`（「這檔 Sheet 持股有沒有人負責」的
sheet-only 分類，靠 Engine D 的 cohort 名單）與 `beta_covered_aliases`／`ignored_holdings` 隨
decision_lab 研究側與 `sheet_only_holding` kind 退役；Sheet 有、敘事沒有的持股改列候選板
「已持有、缺敘事」（ROADMAP Phase 3）。本檔只剩 NAV 比例的 renderer；它目前沒有組裝端消費
（today brief 已退役），Phase 1 心跳要不要接是待決問題。
"""
from __future__ import annotations

from typing import Any, Mapping

from shared.markdown import markdown_text, pct

__all__ = ["render_nav_exposure"]


def render_nav_exposure(nav: Mapping[str, Any] | None) -> list[str]:
    """持股 NAV 比例——排序之後。純呈現，不判斷失衡。

    ⚠ `None`（未注入）不得讓整區靜默消失。先前 `return []` 會讓「呼叫端沒給」與
    「這個人沒有持股」在畫面上完全同形——而使用者看這一區就是為了看曝險集中在哪，
    整區不見時他不會知道自己少看了什麼。排序區對 `None` 早就明說「未提供」，
    這裡沿用同一個處置。
    """
    if nav is None:
        return [
            "# 持股 NAV 比例",
            "",
            "⚠ 本次未提供持股資料（未注入 nav_exposure）——不是「沒有持股」。",
            "",
        ]
    if nav.get("status") != "available":
        failure = nav.get("failure")
        detail = f"（{markdown_text(failure)}）" if failure else ""
        return [
            "# 持股 NAV 比例",
            "",
            f"⚠ 持股讀不到{detail}——這不是「零曝險」。",
            "",
        ]
    lines = ["# 持股 NAV 比例", ""]
    lines.append("| 標的 | bucket | 佔 NAV |")
    lines.append("|---|---|---|")
    for position in nav.get("positions") or []:
        lines.append(
            f"| {markdown_text(position.get('ticker') or '?')} "
            f"| {markdown_text(position.get('bucket') or '')} "
            f"| {pct(position.get('nav_pct'))} |"
        )
    lines.append("")
    buckets = nav.get("buckets") or {}
    if buckets:
        parts = "、".join(
            f"{markdown_text(name)} {pct(share)}"
            for name, share in sorted(buckets.items(), key=lambda kv: -kv[1])
        )
        lines += [f"- bucket 分布：{parts}", ""]
    groups = nav.get("groups") or {}
    if groups:
        parts = "、".join(
            f"{markdown_text(name)} {pct(share)}"
            for name, share in sorted(groups.items(), key=lambda kv: -kv[1])
        )
        lines += [f"- 相關性分組：{parts}", ""]
    return lines
