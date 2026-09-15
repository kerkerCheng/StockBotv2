"""Gap closure（V2，2026-09-15）：**市場承認了嗎**——共識朝我們的看法移動了幾成、股價到了目標價沒。

兩個純函式，零相依。它們是**量測不是訊號**（AGENTS「須區分量測、訊號與脈絡」）：不排序、不決定尺寸，
只回答「自判斷那天以來，共識與價格各走了多少」。

- `consensus_progress`：共識序列（日期、值）＋起算日＋我們的值 → 起點、現值、朝我們移動的比例。
  比例＝(現值 − 起點) ÷ (我們的值 − 起點)；起點等於我們的值時無定義（None，不是 0）。負值＝反向移動。
- `target_reached`：現價對兩個目標價的機械比較（≥ 即到達）。到達不是「該賣」，是「該重看要不要收割」——
  這是 L7 出場靠 disproof 的對稱面：出場也要有「對了」的觸發。
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping, Sequence


def consensus_progress(points: Sequence[tuple[date, float]], *, since: date | None, our_value: float | None) -> dict[str, Any]:
    """`points` 依日期遞增、同一天只留一筆（呼叫端負責）。"""
    ordered = [(d, v) for d, v in points if isinstance(v, (int, float))]
    if not ordered:
        return {"status": "missing", "reason": "沒有共識序列", "n_points": 0}
    start = next(((d, v) for d, v in ordered if since is None or d >= since), None)
    if start is None:
        # 判斷日之後還沒有任何共識抓取——用最後一筆當起點會讓比例恆為 0，那是假的「沒動」。
        return {"status": "missing", "reason": f"判斷日 {since} 之後尚無共識抓取", "n_points": len(ordered)}
    now = ordered[-1]
    fraction: float | None = None
    if our_value is not None and start[1] != our_value:
        fraction = (now[1] - start[1]) / (our_value - start[1])
    return {
        "status": "available",
        "start_date": start[0], "start_value": start[1],
        "now_date": now[0], "now_value": now[1],
        "our_value": our_value,
        "moved": now[1] - start[1],
        "closed_fraction": fraction,
        "n_points": sum(1 for d, _ in ordered if since is None or d >= since),
        "rule": "closed_fraction=(現值−起點)÷(我們的值−起點)；起點＝判斷日當天或之後第一筆共識；起點等於我們的值時無定義",
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


__all__ = ["consensus_progress", "target_reached"]
