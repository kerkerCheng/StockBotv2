"""估值假設 ledger 紀錄的**純邏輯**：序列化、解析、as-of 選取、supersede。

I/O（JSONL 檔）在 `alpha/providers/valuation_assumptions.py`；這裡不讀檔、不開連線。

## 與營運假設共用同一套語意（刻意）

ledger 形狀（append-only、改值＝append、撤回＝append `retracted=true`）、content-addressed id、
as-of 選取（`created_at <= T`）、同 key 最新者勝出、證據必須解析得到——全部**直接沿用**
`alpha.fundamental.assumptions.select_assumptions`（duck-typed：`ValuationAssumption` 露出同形的
`key`／`driver`／`scope`／`period`／`created_on`／`retracted`／`supersedes_id`／`evidence_refs`）。
不另寫第二套選取器，是為了讓「什麼時候一條判斷算存在」在兩種假設上永遠是同一個答案。
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any, Mapping, Sequence

from ..errors import ContractViolation
from ..fundamental.assumptions import select_assumptions
from ..fundamental.contracts import AssumptionSelection, FiscalPeriod
from .contracts import (
    METHOD_FORWARD_EARNINGS_MULTIPLE, METHOD_PARAMETERS, ValuationAssumption,
)

RECORD_VERSION = "valuation-assumption/v1"

_ID_FIELDS = ("company_id", "ticker", "period_end", "period_kind", "method", "parameter", "scope",
              "value", "unit", "basis", "accounting_basis", "rationale", "evidence_refs", "created_at",
              "author", "supersedes_id", "retracted", "dependency_roles", "review_conditions")


def new_valuation_assumption_id(payload: Mapping[str, Any]) -> str:
    """content-addressed id：同一份內容永遠得到同一個 id（重複 append 可被偵測）。"""
    body = {k: payload.get(k) for k in _ID_FIELDS}
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return "va_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def valuation_assumption_record(
    *,
    company_id: str,
    ticker: str,
    period_end: date,
    value: float,
    basis: str,
    accounting_basis: str,
    rationale: str,
    evidence_refs: Sequence[str],
    method: str = METHOD_FORWARD_EARNINGS_MULTIPLE,
    parameter: str = "target_pe",
    created_at: datetime | None = None,
    author: str = "session",
    supersedes_id: str | None = None,
    retracted: bool = False,
    period_kind: str = "fiscal_year",
    calibration_refs: Sequence[str] = (),
    comparison_refs: Sequence[str] = (),
    review_conditions: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """建一筆可寫進 ledger 的紀錄（先經 `ValuationAssumption` 驗證，驗不過就不產生）。

    `evidence_refs` 是 **supporting** 證據；`calibration_refs`／`comparison_refs` 另列——
    同期共識、市場倍數、賣方目標價只能出現在後兩者（出現在 supporting 會被契約拒絕）。
    撤回紀錄沿用被撤回者的 refs 與角色。
    """
    params = METHOD_PARAMETERS.get(method)
    if params is None or parameter not in params:
        raise ContractViolation(f"valuation method 未登記或 parameter 未登記：{method}.{parameter}"
                                f"；已知 {{m: sorted(p) for m, p in METHOD_PARAMETERS.items()}}")
    stamp = created_at or datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        raise ContractViolation("created_at 必須帶時區")
    stamp = stamp.astimezone(timezone.utc)
    supporting = [str(r) for r in evidence_refs]
    calibration = [str(r) for r in calibration_refs]
    comparison = [str(r) for r in comparison_refs]
    all_refs = supporting + [r for r in calibration if r not in supporting] \
        + [r for r in comparison if r not in supporting and r not in calibration]
    roles: dict[str, str] = {}
    roles.update({r: "supporting" for r in supporting})
    roles.update({r: "calibration" for r in calibration})
    roles.update({r: "comparison" for r in comparison})
    payload: dict[str, Any] = {
        "record_version": RECORD_VERSION,
        "company_id": str(company_id),
        "ticker": str(ticker).upper(),
        "period_end": period_end.isoformat(),
        "period_kind": period_kind,
        "method": method,
        "parameter": parameter,
        "scope": "total",
        "value": float(value),
        "unit": params[parameter].unit,
        "basis": basis,
        "accounting_basis": accounting_basis,
        "rationale": rationale,
        "evidence_refs": all_refs,
        "dependency_roles": roles,
        "provenance_semantics": "v2",
        "created_at": stamp.isoformat(),
        "author": author,
        "supersedes_id": supersedes_id,
        "retracted": bool(retracted),
    }
    if review_conditions:
        from ..refresh.contracts import ReviewCondition

        payload["review_conditions"] = [ReviewCondition.from_dict(c).to_dict() for c in review_conditions]
    payload["assumption_id"] = new_valuation_assumption_id(payload)
    parse_valuation_assumption_record(payload)          # 驗證；不合法就在這裡炸，不會寫進 ledger
    return payload


def parse_valuation_assumption_record(raw: Mapping[str, Any]) -> ValuationAssumption:
    """dict → `ValuationAssumption`；任何欄位不合法都 raise `ContractViolation`。"""
    try:
        period = FiscalPeriod(end=date.fromisoformat(str(raw["period_end"])[:10]),
                              kind=str(raw.get("period_kind") or "fiscal_year"))
        created = datetime.fromisoformat(str(raw["created_at"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractViolation(f"估值假設紀錄欄位不合法：{exc}") from None
    refs = raw.get("evidence_refs") or []
    if isinstance(refs, str):
        raise ContractViolation("evidence_refs 必須是 list")
    roles_raw = raw.get("dependency_roles") or {}
    if not isinstance(roles_raw, Mapping):
        raise ContractViolation("dependency_roles 必須是物件（ref → role）")
    conditions_raw = raw.get("review_conditions") or []
    if not isinstance(conditions_raw, (list, tuple)):
        raise ContractViolation("review_conditions 必須是 list")
    from ..refresh.contracts import ReviewCondition

    return ValuationAssumption(
        assumption_id=str(raw.get("assumption_id") or ""),
        company_id=str(raw.get("company_id") or ""),
        ticker=str(raw.get("ticker") or ""),
        period=period,
        method=str(raw.get("method") or ""),
        parameter=str(raw.get("parameter") or ""),
        scope=str(raw.get("scope") or "total"),
        value=raw.get("value"),                       # type: ignore[arg-type]
        unit=str(raw.get("unit") or ""),
        basis=str(raw.get("basis") or ""),
        rationale=str(raw.get("rationale") or ""),
        evidence_refs=tuple(str(r) for r in refs),
        created_at=created,
        author=str(raw.get("author") or "session"),
        accounting_basis=str(raw.get("accounting_basis") or ""),
        supersedes_id=(str(raw["supersedes_id"]) if raw.get("supersedes_id") else None),
        retracted=bool(raw.get("retracted")),
        dependency_roles={str(k): str(v) for k, v in roles_raw.items()},
        review_conditions=tuple(ReviewCondition.from_dict(c) for c in conditions_raw),
        provenance_semantics=str(raw.get("provenance_semantics") or "v2"),
    )


def select_valuation_assumptions(
    records: Sequence[ValuationAssumption],
    *,
    target: FiscalPeriod,
    as_of: date | None,
    today: date,
    evidence_index: Mapping[str, Any],
    parse_errors: Sequence[str] = (),
) -> tuple[tuple[ValuationAssumption, ...], AssumptionSelection]:
    """as-of → 期間 → retract／supersede → 證據解析。**與營運假設同一個選取器**。"""
    accepted, selection = select_assumptions(
        records, target=target, as_of=as_of, today=today,      # type: ignore[arg-type]
        evidence_index=evidence_index, parse_errors=parse_errors)
    return tuple(accepted), selection                           # type: ignore[return-value]


__all__ = [
    "RECORD_VERSION", "new_valuation_assumption_id", "parse_valuation_assumption_record",
    "select_valuation_assumptions", "valuation_assumption_record",
]
