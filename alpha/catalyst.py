"""賣出側 watchlist：把 `disproof`／`catalyst`／`expiry` 從卡片上的散文變成每天被
檢查的狀態。

## 為什麼是賣出側先做

L7 的原話：**「光是填 `disproof_condition` 不夠。欄位有填但沒有後續流程，等於貼了一個
永遠不會響的火警警報。」** 每筆 decision 都強制有 disproof，但至今**沒有任何機制每天
檢查它**。這一支就是那個缺掉的流程。

它**不受 D7「先量測後放閘」限制**——因為它是**條件檢查，不是訊號**：不預測任何東西、
不主張任何預測能力，只回答「你自己寫下的條件，今天到了沒」。買入時點則相反，任何
「現在該買」的機制都是未經量測的新訊號（且 beta 那套已實測 0 勝 3 敗），不在此範圍。

## 這一支第一天就有產出

2026-08-18 首跑即抓到兩個壞設定：IQE 的 `expiry` 早於它自己的催化劑（催化劑不可能在
有效期內發生，保證產生一次假到期），AVGO 的 catalyst／disproof 是空字串（`expiry`
是一個沒有內容的鬧鐘）。

## 邊界

狀態判定本身住 `shared/catalyst_state.py`（Engine D 的 work order lifecycle 也消費
它，見那支的 docstring）。這裡只負責**研究視角的聚合與呈現**：排序、統計、
「設定不完整的提醒是假的」這句警告。

`entries` 由呼叫端注入（`decision_lab.coverage_queries.latest_coverage_assessments`）
——`alpha/` 不碰 Decision Store。
"""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable, Mapping, Sequence

from shared.catalyst_state import STATE_LABEL, STATE_RANK, assess_entry

__all__ = ["build_watchlist", "render_markdown"]


def build_watchlist(
    entries: Sequence[Mapping[str, Any]],
    *,
    today: date | None = None,
    checkpoints_by_company: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """把每個 cohort 的最新 coverage assessment 判成狀態，最急的排最前。"""
    checkpoints_by_company = checkpoints_by_company or {}
    results = [
        assess_entry(
            entry,
            today=today,
            checkpoints=checkpoints_by_company.get(str(entry.get("company_id")), ()),
        )
        for entry in entries
    ]
    results.sort(
        key=lambda r: (
            STATE_RANK.get(r["state"], 0),
            -(r["days_to_expiry"] if r["days_to_expiry"] is not None else 9999),
        ),
        reverse=True,
    )
    return results


def render_markdown(rows: Iterable[Mapping[str, Any]]) -> list[str]:
    rows = list(rows)
    if not rows:
        return []
    broken = [r for r in rows if r["state"] == "config_broken"]
    urgent = [r for r in rows if r["state"] in {"expired", "due_soon"}]

    lines = ["", "## 證偽條件與催化劑（賣出側）", ""]
    lines.append(
        f"追蹤 {len(rows)} 檔｜設定不完整 **{len(broken)}**｜逾期或即將到期 **{len(urgent)}**"
    )
    if broken:
        lines.append(
            "　⚠ 設定不完整的項目，它的到期提醒是假的——在補好之前不要依賴它。"
        )
    lines.append("")
    lines.append("| 標的 | 狀態 | 到期 | 剩餘 | 下個催化劑 |")
    lines.append("|---|---|---|---|---|")
    for r in rows:
        days = r["days_to_expiry"]
        remain = "—" if days is None else (f"{days} 天" if days >= 0 else f"逾期 {-days} 天")
        catalyst_cell = r["next_catalyst"] or "—"
        if r["next_catalyst"] and r["next_catalyst_confidence"] != "confirmed":
            catalyst_cell += "（推估）"
        lines.append(
            f"| {r['ticker'] or r['company_id']} | {STATE_LABEL[r['state']]} "
            f"| {r['expiry'] or '—'} | {remain} | {catalyst_cell} |"
        )
    for r in rows:
        if not r["problems"]:
            continue
        lines.append("")
        lines.append(f"**{r['ticker'] or r['company_id']} 設定問題：**")
        for problem in r["problems"]:
            lines.append(f"- {problem}")
    return lines
