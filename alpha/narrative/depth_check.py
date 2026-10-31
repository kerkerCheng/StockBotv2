"""宣告可開前的深挖清單（2026-10-31 使用者「都做」；failure log #119；ROADMAP「宣告可開前的深挖清單」）——**純規則，不讀不寫任何檔**。

## 它解什麼

可開最容易出現在研究最淺的地方：SLNG 的可開來自新鏈入圖隔天寫的第一版讀圖，讀圖自己列的缺格（單價有沒有溢價）正好是「量」的
核心前提；深讀後層改判不出、可開變缺 X。研究越淺，找到的反證越少，可開反而越容易——所以可開要用深挖換。

## 怎麼用

寫的人在 `alpha brief --add` 的 spec 放 `depth_check`：`{鍵: 引用（library/raw/…、sr_…）｜「缺：…」｜「不適用：理由」}`。
宣告可開（`candidate_state.state=open`）時，CLI 逐項印出哪一項還缺——**只印、不擋、不存檔**（先看它印出什麼，L16）。
執行者的紀律在 research-drain 段 5「可開要用深挖換」：還有「缺」的項目就寫缺 X，不寫可開。

項目是封閉清單：AGENTS「出投資建議前必看五項」＋最新定期報告與法說＋讀到邊（2026-10-06）＋所押讀圖的核心前提（L8）。
"""
from __future__ import annotations

from typing import Any, Mapping

#: (鍵, 印給人看的名字)。新增一項＝改清單，不是加一個字串。
DEPTH_CHECK_ITEMS: tuple[tuple[str, str], ...] = (
    ("latest_report", "最新一份定期報告（季報／年報）"),
    ("latest_call", "最新一場法說或股東會的逐字"),
    ("customer_concentration", "客戶集中度"),
    ("margin_utilization", "毛利率／產能利用率"),
    ("backlog_mix", "backlog／營收結構"),
    ("dilution", "稀釋"),
    ("valuation_pressure", "估值壓力"),
    ("why_chosen", "讀到邊：客戶為什麼選它的變體"),
    ("replaced_by", "讀到邊：什麼會讓它被換掉"),
    ("core_premise", "所押讀圖的核心前提有供應商自述以外的證據（L8）"),
)
DEPTH_CHECK_KEYS: tuple[str, ...] = tuple(k for k, _ in DEPTH_CHECK_ITEMS)


def _answered(value: Any) -> bool:
    """答了＝非空字串、而且不是「缺…」。引用與「不適用：理由」都算答了（沒有法說的小公司不該永遠卡在缺）。"""
    return isinstance(value, str) and bool(value.strip()) and not value.strip().startswith("缺")


def depth_check_gaps(depth_check: Mapping[str, Any] | None) -> tuple[list[str], list[str]]:
    """(還缺的項目名, 不認得的鍵)。"""
    given = dict(depth_check) if isinstance(depth_check, Mapping) else {}
    missing = [label for key, label in DEPTH_CHECK_ITEMS if not _answered(given.get(key))]
    return missing, sorted(str(k) for k in given if k not in DEPTH_CHECK_KEYS)


def depth_check_lines(depth_check: Mapping[str, Any] | None) -> list[str]:
    """宣告可開時印的幾行（CLI 用）。"""
    if not depth_check:
        return ["  ⚠ 宣告可開，但 spec 沒有深挖清單（depth_check）——可開要用深挖換（research-drain 段 5；只印、不擋）"]
    missing, unknown = depth_check_gaps(depth_check)
    lines = ([f"  ⚠ 深挖清單還缺 {len(missing)} 項（只印、不擋；還有缺就該寫缺 X）：" + "、".join(missing)] if missing
             else [f"  ✓ 深挖清單 {len(DEPTH_CHECK_ITEMS)} 項都答了"])
    if unknown:
        lines.append("  ⚠ depth_check 有不認得的鍵（不算數）：" + "、".join(unknown))
    return lines


__all__ = ["DEPTH_CHECK_ITEMS", "DEPTH_CHECK_KEYS", "depth_check_gaps", "depth_check_lines"]
