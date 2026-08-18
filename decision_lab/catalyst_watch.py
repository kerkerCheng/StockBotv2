"""賣出側：把 `disproof`／`catalyst`／`expiry` 從卡片上的散文變成每天被檢查的狀態。

## 為什麼是賣出側先做

L7 的原話：**「光是填 `disproof_condition` 不夠。欄位有填但沒有後續流程，等於貼了一個
永遠不會響的火警警報。」** 每筆 decision 都強制有 disproof，但至今**沒有任何機制每天
檢查它**。這一支就是那個缺掉的流程。

它**不受 D7「先量測後放閘」限制**——因為它是**條件檢查，不是訊號**：不預測任何東西、
不主張任何預測能力，只回答「你自己寫下的條件，今天到了沒」。買入時點則相反，任何
「現在該買」的機制都是未經量測的新訊號（且 beta 那套已實測 0 勝 3 敗），不在此範圍。

## 刻意的限制：不解析散文日期

`catalyst` 是自由文字（「AXT 2026 Q3 10-Q（預計 2026 年 11 月初）」）。從散文抽日期是
語意工作，依 L15 **語意可以交給語言處理，但權限與狀態必須 deterministic**。因此本模組
只用結構化欄位判定：

- `expiry`：真 timestamp，可判逾期與剩餘天數。
- `catalyst`／`disproof` 是否為空：確定性。
- `thesis/lifecycle_schedule.catalyst_checkpoints`（若該 cohort 對得上 lifecycle 條目）：
  已結構化且帶 `date_confidence`，可與 `expiry` 比對。

散文裡的日期**不猜**。猜錯會產生一個「看起來有排程、其實日期是編的」的提醒，
比沒有提醒危險（同 §8.8 需求鏈那次教訓）。

## 這一支第一天就有產出

2026-08-18 首跑即抓到兩個壞設定：IQE 的 `expiry` 早於它自己的催化劑（催化劑不可能在
有效期內發生，保證產生一次假到期），AVGO 的 catalyst／disproof 是空字串（`expiry`
是一個沒有內容的鬧鐘）。
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping

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


def fetch_entries(conn) -> list[dict[str, Any]]:
    """每個 cohort 取最新一份 coverage assessment。

    ⚠ 資料源刻意是 Engine D 的 `coverage_assessments`，不是 `thesis/lifecycle.json`。
    後者只有 3 條 thesis，前者涵蓋全部 cohort；兩套 lifecycle 互不知道是既有的
    整合縫隙（已登記 ROADMAP），這裡不再蓋第三套。
    """
    rows = conn.execute(
        """
        SELECT co.company_id AS company_id, co.research_ticker AS ticker,
               ca.catalyst AS catalyst, ca.disproof AS disproof,
               ca.expiry AS expiry, ca.created_at AS created_at
          FROM coverage_assessments ca
          JOIN decision_cohorts co ON co.cohort_id = ca.cohort_id
         WHERE co.company_id IS NOT NULL
         ORDER BY ca.created_at DESC
        """
    ).fetchall()
    seen: set[str] = set()
    latest: list[dict[str, Any]] = []
    for row in rows:
        company = str(row["company_id"])
        if company in seen:
            continue
        seen.add(company)
        latest.append(dict(row))
    return latest


def build_watchlist(
    conn, *, today: date | None = None, checkpoints_by_company: Mapping[str, Any] | None = None
) -> list[dict[str, Any]]:
    checkpoints_by_company = checkpoints_by_company or {}
    results = [
        assess_entry(
            entry,
            today=today,
            checkpoints=checkpoints_by_company.get(str(entry.get("company_id")), ()),
        )
        for entry in fetch_entries(conn)
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
