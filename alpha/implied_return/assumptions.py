"""Horizon 假設 ledger 紀錄的**純邏輯**：序列化、解析、as-of 選取、supersede。

I/O（JSONL 檔）在 `alpha/providers/horizon_assumptions.py`；這裡不讀檔、不開連線。

與營運／估值假設共用同一套語意（刻意）：append-only、content-addressed id、as-of 選取、同 key 最新者勝出、
證據必須解析得到——全部**直接沿用** `alpha.fundamental.assumptions.select_assumptions`（duck-typed）。
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any, Mapping, Sequence

from ..errors import ContractViolation
from ..fundamental.assumptions import select_assumptions
from ..fundamental.contracts import AssumptionSelection, FiscalPeriod
from .contracts import HorizonAssumption

RECORD_VERSION = "horizon-assumption/v1"

_ID_FIELDS = ("company_id", "ticker", "period_end", "period_kind", "horizon_end", "scope", "basis",
              "rationale", "evidence_refs", "created_at", "author", "supersedes_id", "retracted",
              "dependency_roles", "review_conditions")


def new_horizon_assumption_id(payload: Mapping[str, Any]) -> str:
    """content-addressed id：同一份內容永遠得到同一個 id（重複 append 可被偵測）。"""
    body = {k: payload.get(k) for k in _ID_FIELDS}
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return "ha_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def horizon_assumption_record(
    *,
    company_id: str,
    ticker: str,
    period_end: date,
    horizon_end: date,
    basis: str,
    rationale: str,
    evidence_refs: Sequence[str],
    created_at: datetime | None = None,
    author: str = "session",
    supersedes_id: str | None = None,
    retracted: bool = False,
    period_kind: str = "fiscal_year",
    calibration_refs: Sequence[str] = (),
    comparison_refs: Sequence[str] = (),
    review_conditions: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """建一筆可寫進 ledger 的紀錄（先經 `HorizonAssumption` 驗證，驗不過就不產生）。

    `period_end` 是這條 horizon 服務的目標會計期間結束日（＝估值 target_period）；`horizon_end` 是
    明示的實現日期。`evidence_refs` 是 supporting 證據；同期共識只能出現在 `calibration_refs`。
    """
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
        "horizon_end": horizon_end.isoformat(),
        "scope": "total",
        "basis": basis,
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
    payload["assumption_id"] = new_horizon_assumption_id(payload)
    parse_horizon_assumption_record(payload)          # 驗證；不合法就在這裡炸，不會寫進 ledger
    return payload


def parse_horizon_assumption_record(raw: Mapping[str, Any]) -> HorizonAssumption:
    """dict → `HorizonAssumption`；任何欄位不合法都 raise `ContractViolation`。"""
    try:
        period = FiscalPeriod(end=date.fromisoformat(str(raw["period_end"])[:10]),
                              kind=str(raw.get("period_kind") or "fiscal_year"))
        horizon_end = date.fromisoformat(str(raw["horizon_end"])[:10])
        created = datetime.fromisoformat(str(raw["created_at"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractViolation(f"horizon 假設紀錄欄位不合法：{exc}") from None
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

    return HorizonAssumption(
        assumption_id=str(raw.get("assumption_id") or ""),
        company_id=str(raw.get("company_id") or ""),
        ticker=str(raw.get("ticker") or ""),
        period=period,
        horizon_end=horizon_end,
        scope=str(raw.get("scope") or "total"),
        basis=str(raw.get("basis") or ""),
        rationale=str(raw.get("rationale") or ""),
        evidence_refs=tuple(str(r) for r in refs),
        created_at=created,
        author=str(raw.get("author") or "session"),
        supersedes_id=(str(raw["supersedes_id"]) if raw.get("supersedes_id") else None),
        retracted=bool(raw.get("retracted")),
        dependency_roles={str(k): str(v) for k, v in roles_raw.items()},
        review_conditions=tuple(ReviewCondition.from_dict(c) for c in conditions_raw),
        provenance_semantics=str(raw.get("provenance_semantics") or "v2"),
    )


def select_horizon_assumptions(
    records: Sequence[HorizonAssumption],
    *,
    target: FiscalPeriod,
    as_of: date | None,
    today: date,
    evidence_index: Mapping[str, Any],
    parse_errors: Sequence[str] = (),
) -> tuple[tuple[HorizonAssumption, ...], AssumptionSelection]:
    """as-of → 期間 → retract／supersede → 證據解析。**與營運／估值假設同一個選取器**。"""
    accepted, selection = select_assumptions(
        records, target=target, as_of=as_of, today=today,      # type: ignore[arg-type]
        evidence_index=evidence_index, parse_errors=parse_errors)
    return tuple(accepted), selection                           # type: ignore[return-value]


__all__ = [
    "RECORD_VERSION", "horizon_assumption_record", "new_horizon_assumption_id",
    "parse_horizon_assumption_record", "select_horizon_assumptions",
]
