"""證偽條件／催化劑／到期的**確定性**狀態判定。

## 為什麼在 shared 而不是 alpha

`engine-d-decomposition.md` 把 `catalyst_watch.py` 整支判給 **A**，但實作時它撞上
一件文件沒看到的事：**`assess_entry` 有兩個分屬不同層的消費端。**

- `alpha/catalyst.py` 的賣出側 watchlist——「我的 thesis 今天到期了嗎」＝研究判斷。
- `decision_lab/store.py::_work_order_lifecycle`——「這張 pq1 工單還算不算 live」
  ＝研究注意力的 permission，是 Engine D。

判給 alpha 就得讓 `store.py` 反向 import `alpha/`（方向違規）；留在 Engine D 就得
讓 alpha 反向 import Engine D。**兩邊都錯，代表歸屬本身錯了**——它是被兩層共用、
自己不擁有任何 authority 的原語，正好是 `shared/__init__.py` 寫的判準。

## 刻意的限制：不解析散文日期

`catalyst` 是自由文字（「AXT 2026 Q3 10-Q（預計 2026 年 11 月初）」）。從散文抽日期
是語意工作，依 L15 **語意可以交給語言處理，但權限與狀態必須 deterministic**。
因此這裡只用結構化欄位判定：`expiry`（真 timestamp）、`catalyst`／`disproof` 是否
為空、以及注入的 `checkpoints`（已結構化且帶 `date_confidence`）。

散文裡的日期**不猜**。猜錯會產生一個「看起來有排程、其實日期是編的」的提醒，
比沒有提醒危險。
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping

__all__ = ["DUE_SOON_DAYS", "STATE_LABEL", "STATE_RANK", "assess_entry"]

# 催化劑／到期在幾天內算「即將到期」。與 daily brief 的節奏對齊，不是風險參數。
DUE_SOON_DAYS = 14

STATE_LABEL = {
    "config_broken": "🔴 設定不完整",
    "expired": "🟠 已逾期",
    "due_soon": "🟡 即將到期",
    "watch": "🟢 監控中",
}
# 排序用：數字越大越前面。
STATE_RANK = {"config_broken": 3, "expired": 2, "due_soon": 1, "watch": 0}


def _as_date(value: Any) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def assess_entry(
    entry: Mapping[str, Any],
    *,
    today: date | None = None,
    checkpoints: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """判定單一 cohort 的證偽／催化劑狀態。純函式，不碰 DB。"""
    today = today or datetime.now(timezone.utc).date()
    catalyst = str(entry.get("catalyst") or "").strip()
    disproof = str(entry.get("disproof") or "").strip()
    expiry = _as_date(entry.get("expiry"))

    problems: list[str] = []
    if not disproof:
        problems.append("disproof 未填——證偽條件是必填，缺它等於警報永遠不會響（L7）")
    if not catalyst:
        problems.append("catalyst 未填——expiry 因此是一個沒有內容的鬧鐘")
    if expiry is None:
        problems.append("expiry 無法解析")

    # `expiry` 不得早於催化劑的預期時點：催化劑不可能在有效期內發生，
    # 保證產生一次假到期（daily-brief SKILL.md 的 AXT 實例）。
    nearest = None
    for checkpoint in checkpoints:
        cp_date = _as_date(checkpoint.get("date"))
        if cp_date and (nearest is None or cp_date < nearest[0]):
            nearest = (cp_date, str(checkpoint.get("date_confidence") or "estimated"))
    if expiry and nearest and expiry < nearest[0]:
        problems.append(
            f"expiry {expiry} 早於最近的催化劑 {nearest[0]}"
            f"（{'已公告' if nearest[1] == 'confirmed' else '推估'}）"
            "——催化劑不可能在有效期內發生"
        )

    if problems:
        state = "config_broken"
    elif expiry and expiry <= today:
        state = "expired"
    elif expiry and (expiry - today).days <= DUE_SOON_DAYS:
        state = "due_soon"
    else:
        state = "watch"

    return {
        "company_id": entry.get("company_id"),
        "ticker": entry.get("ticker"),
        "state": state,
        "expiry": expiry.isoformat() if expiry else None,
        "days_to_expiry": (expiry - today).days if expiry else None,
        "next_catalyst": nearest[0].isoformat() if nearest else None,
        "next_catalyst_confidence": nearest[1] if nearest else None,
        "catalyst": catalyst,
        "disproof": disproof,
        "problems": problems,
    }
