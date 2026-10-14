"""營收從哪來的取數（個股頁 S3d，2026-10-14）：讀 Engine C `manual_observations` 的分部／產品線占比、客戶集中度、backlog，
與台股年報地區別（`tw_region_revenue_observations`，S3d 第二段），交給 `alpha.revenue_mix` 整理。

- **生效那一筆**：同一 (欄位, 觀測期) 只取沒被 `supersedes_id` 指到的；兩筆以上同時生效＝衝突，照列、不挑一個
  （INV-3；與 `engine_c.three_question_inputs._segment_points` 同一條規則）。
- **時點**：as-of T 只看 T 以前**記錄**（`recorded_at`）的觀測——記錄日是我們確定知道的那天（比申報日晚，往晚估不會偷看；INV-6）；
  更正也一樣，T 以後才寫的更正在 T 時還不算數。
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any, Mapping

from alpha.revenue_mix import SHARE_LABELS, backlog_text, customers_text, headline, region_mix, share_series

FIELDS = ("segment_revenue_share", "product_line_revenue_share", "customer_concentration", "backlog")
FIELD_LABELS = {"segment_revenue_share": "分部營收占比", "product_line_revenue_share": "產品線營收占比",
                "customer_concentration": "客戶集中度", "backlog": "backlog 與長約"}


def _decode(value: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value


def live_observations(conn: Any, ticker: str, *, as_of: date | None = None
                      ) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    """欄位 → 生效的觀測（觀測期升序），與衝突清單。"""
    marks = ",".join("?" for _ in FIELDS)
    rows = conn.execute(
        f"SELECT observation_id, field_name, value, source_ref, as_of, recorded_at, supersedes_id "
        f"FROM manual_observations WHERE ticker = ? AND field_name IN ({marks})", (ticker, *FIELDS)).fetchall()
    if as_of is not None:
        rows = [r for r in rows if str(r[5])[:10] <= as_of.isoformat()]
    superseded = {str(r[6]) for r in rows if r[6]}
    by_key: dict[tuple[str, str], list[Any]] = {}
    for r in rows:
        if str(r[0]) not in superseded:
            by_key.setdefault((str(r[1]), str(r[4])[:10]), []).append(r)
    out: dict[str, list[dict[str, Any]]] = {}
    conflicts: list[dict[str, Any]] = []
    for (field, period), live in sorted(by_key.items()):
        if len(live) > 1:
            conflicts.append({"field": field, "label": FIELD_LABELS[field], "as_of": period,
                              "ids": sorted(str(r[0]) for r in live)})
            continue
        r = live[0]
        out.setdefault(field, []).append({"as_of": period, "value": _decode(r[2]), "source_ref": str(r[3] or ""),
                                          "observation_id": str(r[0])})
    return out, conflicts


TW_SUFFIXES = (".TW", ".TWO")


def _regions(conn: Any, ticker: str, as_of: date | None) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """台股年報地區別 → (一塊占比, 缺席)。不是台股＝兩個都 None（這一種本來就不適用，不印缺席）。"""
    from engine_c.tw_region_revenue import region_revenue

    if not ticker.upper().endswith(TW_SUFFIXES):
        return None, None
    found = region_revenue(conn, ticker, as_of=as_of)
    if found is None:
        return None, {"kind": "not_yet_recorded", "reason": "還沒從年度財報抽地區別營收"}
    if found["status"] == "ok":
        return region_mix(found), None
    kind = "not_yet_recorded" if found["status"] == "not_yet_available" else "capability_absent"
    return None, {"kind": kind, "reason": str(found.get("reason") or found["status"])}


def revenue_mix(conn: Any, ticker: str, *, as_of: date | None = None) -> dict[str, Any]:
    """一頁的「營收從哪來」：`{shares: [...], regions, customers, backlog, conflicts, absences}`——沒有觀測的那一種具名缺席。"""
    live, conflicts = live_observations(conn, ticker, as_of=as_of)
    shares = []
    for field, label in SHARE_LABELS.items():
        points = [p for p in live.get(field) or () if isinstance(p["value"], Mapping)]
        if points:
            shares.append({"field": field, "label": label, "points": share_series(points)})
    regions, region_absence = _regions(conn, ticker, as_of)
    out: dict[str, Any] = {"shares": shares, "regions": regions, "customers": None, "backlog": None, "conflicts": conflicts,
                           "absences": {"regions": region_absence} if region_absence else {}}
    for field, key, render in (("customer_concentration", "customers", customers_text), ("backlog", "backlog", backlog_text)):
        latest = (live.get(field) or [None])[-1]
        if latest is None:
            out["absences"][key] = {"kind": "not_yet_recorded",
                                    "reason": "還沒有人從年報或申報表記下" + ("客戶集中度" if key == "customers" else "backlog 與長約")}
            continue
        text = render(latest["value"])
        out[key] = {"as_of": latest["as_of"], "headline": headline(text), "text": text, "source_ref": latest["source_ref"]}
    if not shares:
        out["absences"]["shares"] = {"kind": "not_yet_recorded", "reason": "還沒有人從年報或申報表記下分部或產品線的營收占比"}
    return out


__all__ = ["FIELDS", "live_observations", "revenue_mix"]
