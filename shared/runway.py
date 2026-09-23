"""現金跑道（runway）的純函式——「會死嗎」那一題的輸入之一。

2026-09-23（Phase 0 Step 0b.4）由 `decision_lab/context.py::derive_runway` 搬來：Engine D 研究側退役，
但 `engine_c/checklist.get_wipeout_inputs` 與 `alpha/wipeout.py` 的歸零旗標仍要這個形狀。
住 `shared/` 的理由與其他 shared 模組相同：多個消費端、分屬不同層（Engine C 取數、alpha 判色）。

輸出形狀（消費端依賴，不得改）：
- `{"status": "manual_required", "runway_months": None}`：三個輸入缺任一、或沒有 source／as_of。
- `{"status": "self_funding", "runway_months": None, ...三個輸入＋source＋as_of}`：FCF ≥ 0。
- `{"status": "calculated", "runway_months": <月數>, ...}`：現金 ÷ 每月燒錢。
人工觀測（`manual_observation`）優先於快照缺值時使用，但必須自帶 source 與 as_of（INV-6）。
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Mapping

__all__ = ["derive_runway"]


def _parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include timezone")
    return parsed


def _finite(value: Any, *, non_negative: bool = False) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    if not math.isfinite(result) or (non_negative and result < 0):
        return None
    return result


def derive_runway(
    financial: Mapping[str, Any],
    *,
    manual_observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source = financial
    required = ("cash_and_equivalents", "total_debt", "free_cash_flow_ttm")
    if any(financial.get(key) is None for key in required):
        if manual_observation is None:
            return {"status": "manual_required", "runway_months": None}
        if not manual_observation.get("source") or not manual_observation.get("as_of"):
            raise ValueError("manual runway observation requires source and as_of")
        _parse_time(manual_observation["as_of"], "manual_runway.as_of")
        source = manual_observation
    cash = _finite(source.get("cash_and_equivalents"), non_negative=True)
    debt = _finite(source.get("total_debt"), non_negative=True)
    free_cash_flow = _finite(source.get("free_cash_flow_ttm"))
    if cash is None or debt is None or free_cash_flow is None:
        return {"status": "manual_required", "runway_months": None}
    if not source.get("source") or not source.get("as_of"):
        return {"status": "manual_required", "runway_months": None}
    _parse_time(source["as_of"], "runway.as_of")
    result = {
        "cash_and_equivalents": cash,
        "total_debt": debt,
        "free_cash_flow_ttm": free_cash_flow,
        "source": source["source"],
        "as_of": source["as_of"],
    }
    if free_cash_flow >= 0:
        return result | {"status": "self_funding", "runway_months": None}
    return result | {
        "status": "calculated",
        "runway_months": cash / (-free_cash_flow / 12.0),
    }
