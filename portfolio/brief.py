"""Portfolio 在 daily brief 裡的 pane：持股 NAV 比例、以及「誰在看這檔持股」。

## 為什麼 sheet-only 分類搬到這裡（B6 解掉的那條耦合）

`decision_lab/brief.py → portfolio.policy` 是搬遷期最後一條方向違規，具名列在
`tests/test_layer_separation.py::PENDING_B6_COUPLINGS`。成因是 `_sheet_only_items`
要回答「這檔 Sheet 持股有沒有人負責」，而 beta 覆蓋名單的唯一 SSOT 是
`config/beta_policy.json`——Engine D 於是往上游伸手。

**問題不在 import，在歸屬。**「我的持股裡哪一檔沒有任何機制在看」是投組覆蓋問題，
不是決策問題；Engine D 該知道的只有「哪些 company 已經有 cohort」，而那由呼叫端
傳進來。分開之後兩邊都更嚴格：本檔完全不認識 Decision Store，Engine D 完全不認識
beta policy。

⚠ **這條鏈上動壞了會讓持股從待辦池消失**：`engine_b todo sync → briefing.public_view
→ build_today_brief → build_sheet_only_items`。`AGENTS.md`「Sheet 持股覆蓋分類」是
它的政策 SSOT，三分類與 fail-safe 語意一字未改。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from shared.markdown import markdown_text, pct

__all__ = [
    "beta_covered_aliases",
    "build_sheet_only_items",
    "ignored_holdings",
    "render_nav_exposure",
]

_COVERAGE_PATH = Path(__file__).resolve().parents[1] / "config" / "holdings_coverage.json"

_USABLE_HOLDINGS_STATUSES = frozenset({"available", "confirmed", "confirmed_empty"})


def beta_covered_aliases() -> dict[str, str]:
    """Sheet alias → sleeve，取自 beta policy（唯一 numeric SSOT）。

    讀不到就回空 dict：覆蓋資訊不可得時必須退回 REVIEW，寧可重複提醒，
    也不能因設定檔壞掉而讓未覆蓋持股從 pq2 靜默消失。
    """
    try:
        from portfolio.policy import load_beta_policy

        policy = load_beta_policy()
    except Exception:
        return {}
    aliases: dict[str, str] = {}
    for instrument in policy.get("instruments") or []:
        sleeve = str(instrument.get("sleeve") or "")
        for alias in instrument.get("sheet_aliases") or ():
            aliases[str(alias).upper()] = sleeve
    return aliases


def ignored_holdings() -> dict[str, str]:
    """Sheet ticker → 使用者不做 alpha 研究的理由。讀不到同樣退回 REVIEW。"""
    try:
        value = json.loads(_COVERAGE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(value, dict):
        return {}
    ignored: dict[str, str] = {}
    for entry in value.get("ignored") or ():
        if not isinstance(entry, Mapping):
            continue
        ticker = str(entry.get("sheet_ticker") or "").strip().upper()
        if ticker:
            ignored[ticker] = str(entry.get("reason") or "使用者明確指示不做 alpha 研究。")
    return ignored


def build_sheet_only_items(
    holdings: Mapping[str, Any] | None,
    *,
    cohort_company_ids: Sequence[str] | set[str],
    registry: Any,
) -> list[dict[str, Any]]:
    """Google Sheet 有部位、Engine D 卻沒有對應 cohort 的持股，依覆蓋分三類。

    `cohort_company_ids` 由 Engine D 提供（`decision_lab.brief.cohort_company_ids`）
    ——本檔不認識 Decision Store，只認識「這些 company 已經有人負責」。

    回傳的 item 用的是 Engine D 的 pq2 詞彙（`attention`／`blockers`／
    `user_response_needed`），因為它們要與 decision item 併成同一份待辦清單；
    決定**分類**的是投組覆蓋，決定**清單形狀**的是 Engine D。
    """
    if not holdings or holdings.get("status") not in _USABLE_HOLDINGS_STATUSES:
        return []
    beta_aliases = beta_covered_aliases()
    ignored = ignored_holdings()
    covered = set(cohort_company_ids)
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in holdings.get("rows") or []:
        if not isinstance(row, Mapping):
            continue
        shares = row.get("shares")
        if not isinstance(shares, (int, float)) or isinstance(shares, bool) or shares <= 0:
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        company_id = row.get("company_id") or (
            registry.company_id_for_ticker(ticker) if ticker else None
        )
        identity = str(company_id or (f"ticker:{ticker}" if ticker else "unresolved"))
        if identity in covered or identity in seen:
            continue
        seen.add(identity)

        # 已由別的機制負責的持股仍要在 brief 現形，但不是 alpha 待辦：改用
        # MONITOR，統一待辦池才不會每天替它們配一個新 pq2 編號。
        sleeve = beta_aliases.get(ticker)
        ignore_reason = ignored.get(ticker)
        if sleeve:
            attention = "MONITOR"
            coverage = "beta_policy"
            reason = (
                f"由 beta policy 涵蓋（sleeve={sleeve}），"
                "配置與 timing 走 daily beta monitor，不需 alpha cohort。"
            )
            portfolio_action = "covered_by_beta_policy"
            # 沒有 alpha cohort 對這些持股是預期狀態，不是 blocker；覆蓋事實由
            # coverage 欄位承載，不讓它冒泡進全域 blockers 製造噪音。
            blockers: list[str] = []
            request = "無；如需 single-name thesis 再另行 evaluate-signal 建 cohort。"
        elif ignore_reason:
            attention = "MONITOR"
            coverage = "user_ignored"
            reason = f"使用者指定不做 alpha 研究：{ignore_reason}"
            portfolio_action = "user_ignored_holding"
            blockers = []
            request = "無；要恢復追蹤請移除 config/holdings_coverage.json 的該筆登記。"
        else:
            attention = "REVIEW"
            coverage = "uncovered"
            reason = "Google Sheet 有 live 持股，但 Engine D 尚無對應 cohort／decision。"
            portfolio_action = "review_uncovered_holding"
            blockers = ["sheet_only_holding", "decision_missing"]
            request = "請先 evaluate-signal／onboard，讓這檔進入瓶頸排序。"

        result.append(
            {
                "cohort_id": None,
                "decision_id": None,
                "company_id": str(company_id or "unresolved"),
                "ticker": ticker,
                "sheet_only": True,
                "coverage": coverage,
                "attention": attention,
                "reason": reason,
                "alpha_thesis_change": {
                    "classification": "unknown",
                    "thesis_changed": False,
                },
                "beta_portfolio_risk": {
                    "portfolio_action": portfolio_action,
                    "classification": "unknown",
                },
                "blockers": blockers,
                "next_review_at": None,
                "disproof_condition": "",
                "user_response_needed": request,
            }
        )
    return result


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
