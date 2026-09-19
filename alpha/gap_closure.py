"""Gap closure（V2，2026-09-15）：**市場承認了嗎**——共識朝我們的看法移動了幾成、股價到了目標價沒。

兩個純函式，零相依。它們是**量測不是訊號**（AGENTS「須區分量測、訊號與脈絡」）：不排序、不決定尺寸，
只回答「自判斷那天以來，共識與價格各走了多少」。

- `consensus_progress`：共識序列（日期、值）＋起算日＋我們的值 → 起點、現值、朝我們移動的比例。
  比例＝(現值 − 起點) ÷ `gap_at_start`，其中 `gap_at_start`＝(我們的值 − 起點)；分母為 0 時無定義（None，不是 0）。
  負值＝反向移動。**分母跟著輸出**——它極小時比例會被放大到不可讀（V4，2026-09-19）。
  ⚠ **起算日是呼叫端的責任，而且 base 與 variant 不是同一天**：base 是判斷日，variant 是**賭注寫下那天**。
- `target_reached`：現價對兩個目標價的機械比較（≥ 即到達）。到達不是「該賣」，是「該重看要不要收割」——
  這是 L7 出場靠 disproof 的對稱面：出場也要有「對了」的觸發。
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping, Sequence


def consensus_progress(points: Sequence[tuple[date, float]], *, since: date | None, our_value: float | None) -> dict[str, Any]:
    """`points` 依日期遞增、同一天只留一筆（呼叫端負責）。"""
    ordered = [(d, v) for d, v in points if isinstance(v, (int, float))]
    if not ordered:
        return {"status": "missing", "reason": "沒有共識序列", "n_points": 0}
    start = next(((d, v) for d, v in ordered if since is None or d >= since), None)
    if start is None:
        # 起算日之後還沒有任何共識抓取——用最後一筆當起點會讓比例恆為 0，那是假的「沒動」。
        return {"status": "missing", "reason": f"起算日 {since} 之後尚無共識抓取", "n_points": len(ordered)}
    now = ordered[-1]
    # `gap_at_start` 就是比例的**分母**：判斷當下我們與共識的距離。它必須跟著比例一起輸出——
    # 分母趨近 0 時比例會被放大到不可讀（2026-09-19 實測：5802.T 分母 −0.000188、共識移動 1.347，
    # 比例 −7175.7；AVGO −1188.9）。那兩個數字在數學上正確，但單獨讀會被當成「反向跑了七千倍」。
    # ⚠ 修法刻意**不設門檻**：門檻要憑空挑一個參數（INV-5），而恆等式不會爆——
    # 讀者看到分母是 −0.000188 就知道這個比例不具資訊（同 power-law「籃子總報酬＝最大單檔＋其餘」的取捨）。
    gap_at_start: float | None = (our_value - start[1]) if our_value is not None else None
    fraction: float | None = None
    if gap_at_start is not None and gap_at_start != 0:
        fraction = (now[1] - start[1]) / gap_at_start
    return {
        "status": "available",
        "start_date": start[0], "start_value": start[1],
        "now_date": now[0], "now_value": now[1],
        "our_value": our_value,
        "moved": now[1] - start[1],
        "gap_at_start": gap_at_start,
        "closed_fraction": fraction,
        "n_points": sum(1 for d, _ in ordered if since is None or d >= since),
        "rule": "closed_fraction=(現值−起點)÷gap_at_start，其中 gap_at_start=(我們的值−起點)；"
                "起點＝起算日當天或之後第一筆共識；起點等於我們的值時無定義（分母 0）；"
                "⚠ gap_at_start 極小時比例會被放大，要連分母一起讀",
    }


def bet_recorded_on(model: Any) -> date | None:
    """賭注寫下那天＝該 overlay 的生效假設裡**最晚**的建立時點（本機日）；沒有就 `None`。

    ⚠ **取最晚不是最早。** 一個賭注可能由多條 override 組成（實測 AXTI 兩條、LITE 兩條），
    而 `variant` EPS 的**現值**是它們合起來算出來的——最後一條寫下之前，今天這個主張還不完整。
    取最早會把「主張尚未成形」那段期間的共識變動算成朝它移動，方向恆為對我們有利（INV-6）。

    本機日而非 UTC 日：`consensus_estimates.snapshot_date` 是 ETL 執行日（本機時區），
    兩邊要用同一把尺，否則跨日的 UTC 時戳會讓起點早一天。

    `model` 只用 duck typing 讀 `overrides`（本模組維持零相依）。撤回的假設本來就不在 `overrides` 裡。
    """
    days: list[date] = []
    for assumption in (getattr(model, "overrides", None) or ()):
        created = getattr(assumption, "created_at", None)
        if isinstance(created, str):
            try:
                created = datetime.fromisoformat(created)
            except ValueError:
                continue
        if not isinstance(created, datetime):
            continue
        try:
            days.append((created.astimezone() if created.tzinfo is not None else created).date())
        except (OSError, OverflowError, ValueError):
            continue
    return max(days) if days else None


def bet_convergence(
    entries: Sequence[tuple[str, Mapping[str, Any]]], *, today: date | None = None,
) -> dict[str, Any]:
    """V4（2026-09-19）：把各檔的賭注收斂聚合成**不依賴賣出的驗證序列**。

    `entries` 是 `(ticker, gap_closure 的 value 字典)`——**直接吃已經算好的那一格，
    一個數字都不重算**。第二份實作會立刻開始偏離（L16）。

    ## 它回答什麼、不回答什麼

    回答「**自我們寫下賭注那天起，共識朝我們移動了嗎**」。這是等權報酬追蹤答不了的一題：
    報酬的錨點是入圖日、含市場 beta，而本圖標的同漲同跌（AGENTS「N 檔不等於 N 個獨立機會」）；
    共識修正不受 beta 污染，而且**不需要賣出就能驗證**。

    **不**回答「該不該買、該買多少」。它是量測不是訊號（AGENTS「須區分量測、訊號與脈絡」）：
    不排序、不決定尺寸；一旦有人拿它排序，它就變回訊號。

    ## 三個刻意分開、不得壓成一個數字的地方

    1. **`unchanged`（共識沒動）與 `not_yet_observable`（賭注寫下後還沒有任何共識抓取）**。
       前者是「市場看過了、沒改」，後者是「還沒輪到市場說話」——壓成一個 0% 會被讀成
       「市場否定了我們」（L12）。
    2. **方向由 `moved` 與 `gap_at_start` 是否同號判定。** 這與「`closed_fraction` 為正」
       在數學上**等價**（比例就是兩者相除），分開寫不是因為結果不同，是因為除法會吃掉
       兩個必須保留的狀態：分母為 0 時比例是 `None`（→ `direction_undefined`，共識動了
       但我們與它起點一致，沒有「朝我們」可言），`moved` 為 0 時比例是 0（→ `unchanged`）。
       ⚠ 初稿在這裡寫過「分母為負時比例的正負與方向相反」——**那是錯的**，寫下來免得再犯。
    3. **觀測窗長度跟著數字走，而且「已觀測幾天」與「還在等第一次抓取」是兩個量。**
       窗只有幾天時「沒動」幾乎是必然的——分析師不是每天改估計。不印窗長就等於邀請讀者
       把「還沒發生」讀成「不會發生」；把 `days_waiting` 混進 `window_days` 的 min/max，
       則會讓「窗 0–3 天」同時意味兩件事。

    ⚠ **樣本太少時這張表量到的是雜訊。** `n_bets` 今天是個位數；它與帳號計分表受同一條
    限制（AGENTS「計分表必印量測起始日與樣本數」），所以 `known_biases` 跟著輸出。
    """
    rows: list[dict[str, Any]] = []
    no_bet = 0
    for ticker, value in entries:
        variant = (value or {}).get("variant")
        bet_since = (value or {}).get("bet_since")
        row: dict[str, Any] = {"ticker": ticker, "bet_since": bet_since}
        if not isinstance(variant, Mapping):
            # 沒有賭注的檔**只進計數，不進 rows**：19 筆空列會把 3 筆真資料淹掉，
            # 而它們要講的事（有幾檔沒下注）`no_bet` 這個數字已經講完了（不是靜默丟棄，INV-3）。
            no_bet += 1
            continue
        if variant.get("status") != "available":
            row["state"] = "not_yet_observable"
            row["reason"] = variant.get("reason")
            # ⚠ **`days_waiting` 不是 `window_days`。** 前者是「賭注寫下到今天還沒等到一次
            # 共識抓取」，後者是「已經觀測了幾天」——把兩者算進同一個 min/max，
            # 「窗 0–3 天」會同時意味兩件事（L12）。
            row["days_waiting"] = (
                (today - bet_since).days if today is not None and isinstance(bet_since, date) else None)
            rows.append(row)
            continue
        moved = variant.get("moved")
        gap = variant.get("gap_at_start")
        start, now = variant.get("start_date"), variant.get("now_date")
        row.update({
            "moved": moved, "gap_at_start": gap, "closed_fraction": variant.get("closed_fraction"),
            "n_points": variant.get("n_points"), "start_date": start, "now_date": now,
            "window_days": ((now - start).days if isinstance(start, date) and isinstance(now, date) else None),
        })
        if not isinstance(moved, (int, float)) or moved == 0:
            row["state"] = "unchanged"
        elif not isinstance(gap, (int, float)) or gap == 0:
            row["state"] = "direction_undefined"   # 共識動了，但我們與它起點一致——沒有「朝我們」可言
        else:
            row["state"] = "toward_us" if (moved > 0) == (gap > 0) else "away_from_us"
        rows.append(row)
    states = [r["state"] for r in rows]
    windows = [r["window_days"] for r in rows if isinstance(r.get("window_days"), int)]
    waiting = [r["days_waiting"] for r in rows if isinstance(r.get("days_waiting"), int)]
    return {
        # ⚠ `scanned` 與 `n_bets` 不是同一個數字，**不得合併**：分母是「寫了賭注的檔」，
        # 不是「掃過的檔」。掃了 22 份 artifact 但只有 3 份有賭注時，用 22 當分母會把
        # 「大部分人沒下注」稀釋成「大部分賭注沒動」（2026-09-19 首版就印錯成「有賭注 22 檔」）。
        "scanned": len(rows) + no_bet,
        "n_bets": len(rows),
        "measurable": sum(1 for s in states if s in ("unchanged", "toward_us", "away_from_us", "direction_undefined")),
        "toward_us": states.count("toward_us"),
        "away_from_us": states.count("away_from_us"),
        "unchanged": states.count("unchanged"),
        "direction_undefined": states.count("direction_undefined"),
        "not_yet_observable": states.count("not_yet_observable"),
        "no_bet": no_bet,
        "shortest_window_days": (min(windows) if windows else None),
        "longest_window_days": (max(windows) if windows else None),
        "longest_days_waiting": (max(waiting) if waiting else None),
        "rows": rows,
        "rule": "起算日＝賭注寫下那天（不是判斷日）；方向由 moved 與 gap_at_start 同號判定；"
                "unchanged 與 not_yet_observable 不得合併；window_days（已觀測）與 "
                "days_waiting（還沒等到第一次抓取）是兩個量，不進同一個 min/max",
        "known_biases": [
            "觀測窗短時「共識沒動」幾乎是必然——分析師不是每天改估計；要連 window_days 一起讀。",
            "賭注只寫在少數幾檔上，`n_bets` 是個位數；這張表今天量到的接近雜訊，不是結論。",
            "共識修正不等於我們對了：共識可能因為我們沒想到的理由朝同一個方向動（同向不等於同因）。",
        ],
    }


def target_reached(*, price: float | None, base_target: float | None, bet_target: float | None) -> dict[str, Any]:
    if price is None:
        return {"status": "missing", "reason": "無現價"}
    out: dict[str, Any] = {"status": "available", "price": price,
                           "base_reached": (base_target is not None and price >= base_target),
                           "bet_reached": (bet_target is not None and price >= bet_target),
                           "base_target": base_target, "bet_target": bet_target}
    out["any_reached"] = bool(out["base_reached"] or out["bet_reached"])
    out["rule"] = "現價 ≥ 目標價即「高於」；它同時涵蓋「市場比我們樂觀」與「該收割」兩種情況，只表示該重看，不是賣出指令"
    return out


__all__ = ["bet_convergence", "bet_recorded_on", "consensus_progress", "target_reached"]
