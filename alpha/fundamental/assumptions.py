"""假設 ledger 紀錄的**純邏輯**：序列化、解析、as-of 選取、supersede、證據解析。

I/O（JSONL 檔）在 `alpha/providers/assumptions.py`；這裡不讀檔、不開連線。

## Ledger 的形狀（append-only）

一行一筆 JSON。改一條假設＝append 一筆新的（同 driver／scope／period 的較新者勝出），
撤回＝append 一筆 `retracted=true` 且 `supersedes_id` 指向被撤回者。兩筆都留著——
研究判斷可重算，但「當時假設了什麼」是稽核紀錄。

## as-of 選取（INV-6）

`build as_of=T` 只能看到 `created_at <= T` 的紀錄。歷史時點還沒寫過假設就是 `missing`，
**不得偷用現在的假設去重建過去的 gap**。
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any, Mapping, Sequence

from ..errors import ContractViolation
from .contracts import (
    ASSUMPTION_DRIVERS, TOTAL_SCOPE, AssumptionSelection, FiscalPeriod, OperatingAssumption,
)

RECORD_VERSION = "operating-assumption/v1"

_ID_FIELDS = ("company_id", "ticker", "period_end", "period_kind", "driver", "scope", "value",
              "unit", "basis", "accounting_basis", "rationale", "evidence_refs", "created_at",
              "author", "supersedes_id", "retracted")


def new_assumption_id(payload: Mapping[str, Any]) -> str:
    """content-addressed id：同一份內容永遠得到同一個 id（重複 append 可被偵測）。"""
    canonical = json.dumps({k: payload.get(k) for k in _ID_FIELDS}, ensure_ascii=False,
                           sort_keys=True, separators=(",", ":"), default=str)
    return "oa_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def assumption_record(
    *,
    company_id: str,
    ticker: str,
    period_end: date,
    driver: str,
    scope: str,
    value: float,
    basis: str,
    rationale: str,
    evidence_refs: Sequence[str],
    created_at: datetime | None = None,
    author: str = "session",
    accounting_basis: str = "not_applicable",
    supersedes_id: str | None = None,
    retracted: bool = False,
    period_kind: str = "fiscal_year",
) -> dict[str, Any]:
    """建一筆可寫進 ledger 的紀錄（先經 `OperatingAssumption` 驗證，驗不過就不產生）。"""
    spec = ASSUMPTION_DRIVERS.get(driver)
    if spec is None:
        raise ContractViolation(f"driver 未登記：{driver!r}；已知 {sorted(ASSUMPTION_DRIVERS)}")
    stamp = created_at or datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        raise ContractViolation("created_at 必須帶時區")
    stamp = stamp.astimezone(timezone.utc)
    payload: dict[str, Any] = {
        "record_version": RECORD_VERSION,
        "company_id": str(company_id),
        "ticker": str(ticker).upper(),
        "period_end": period_end.isoformat(),
        "period_kind": period_kind,
        "driver": driver,
        "scope": str(scope or (TOTAL_SCOPE if spec.scope_kind == "total" else "")),
        "value": float(value),
        "unit": spec.unit,
        "basis": basis,
        "accounting_basis": accounting_basis,
        "rationale": rationale,
        "evidence_refs": [str(r) for r in evidence_refs],
        "created_at": stamp.isoformat(),
        "author": author,
        "supersedes_id": supersedes_id,
        "retracted": bool(retracted),
    }
    payload["assumption_id"] = new_assumption_id(payload)
    parse_assumption_record(payload)          # 驗證；不合法就在這裡炸，不會寫進 ledger
    return payload


def parse_assumption_record(raw: Mapping[str, Any]) -> OperatingAssumption:
    """dict → `OperatingAssumption`；任何欄位不合法都 raise `ContractViolation`。"""
    try:
        period = FiscalPeriod(end=date.fromisoformat(str(raw["period_end"])[:10]),
                              kind=str(raw.get("period_kind") or "fiscal_year"))
        created = datetime.fromisoformat(str(raw["created_at"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractViolation(f"假設紀錄欄位不合法：{exc}") from None
    refs = raw.get("evidence_refs") or []
    if isinstance(refs, str):
        raise ContractViolation("evidence_refs 必須是 list")
    return OperatingAssumption(
        assumption_id=str(raw.get("assumption_id") or ""),
        company_id=str(raw.get("company_id") or ""),
        ticker=str(raw.get("ticker") or ""),
        period=period,
        driver=str(raw.get("driver") or ""),
        scope=str(raw.get("scope") or ""),
        value=raw.get("value"),                       # type: ignore[arg-type]
        unit=str(raw.get("unit") or ""),
        basis=str(raw.get("basis") or ""),
        rationale=str(raw.get("rationale") or ""),
        evidence_refs=tuple(str(r) for r in refs),
        created_at=created,
        author=str(raw.get("author") or "session"),
        accounting_basis=str(raw.get("accounting_basis") or "not_applicable"),
        supersedes_id=(str(raw["supersedes_id"]) if raw.get("supersedes_id") else None),
        retracted=bool(raw.get("retracted")),
    )


def select_assumptions(
    records: Sequence[OperatingAssumption],
    *,
    target: FiscalPeriod,
    as_of: date | None,
    today: date,
    evidence_index: Mapping[str, Any],
    parse_errors: Sequence[str] = (),
) -> tuple[tuple[OperatingAssumption, ...], AssumptionSelection]:
    """挑出**在 T 時刻存在、針對目標期間、證據解析得到**的假設；其餘逐筆計數。

    順序刻意固定：先 as-of（T 之後寫的紀錄根本不存在），再期間，再 retract／supersede，
    最後才解析證據——解析是最後一關，因為它要的是「有資格參賽的紀錄」的證據。
    """
    cutoff = as_of or today
    reasons: dict[str, int] = {}
    rejected: list[tuple[str, str]] = []

    def _reject(item_id: str, reason: str) -> None:
        reasons[reason] = reasons.get(reason, 0) + 1
        rejected.append((item_id, reason))

    for error in parse_errors:
        _reject("?", "invalid_record")
        rejected[-1] = ("?", f"invalid_record: {error}")

    ordered = sorted(records, key=lambda r: (r.created_at, r.assumption_id))
    visible: list[OperatingAssumption] = []
    for record in ordered:
        if record.created_on > cutoff:
            _reject(record.assumption_id, "created_after_as_of")
            continue
        if not record.period.same_as(target):
            _reject(record.assumption_id, "other_period")
            continue
        visible.append(record)

    # 同一個 key（driver／scope）只看**最新一筆**：較新者取代較舊者（明確指名 supersedes_id
    # 時記為 superseded，否則 superseded_by_newer）；最新一筆若是撤回紀錄，這個 key 就沒有
    # 生效假設——撤回不會讓更早的舊值復活，要沿用舊值必須再 append 一筆（稽核痕跡）。
    latest_by_key: dict[tuple[str, str], OperatingAssumption] = {}
    for record in visible:
        previous = latest_by_key.get(record.key)
        if previous is not None:
            _reject(previous.assumption_id,
                    "superseded" if record.supersedes_id == previous.assumption_id
                    else "superseded_by_newer")
        latest_by_key[record.key] = record

    accepted: list[OperatingAssumption] = []
    for record in latest_by_key.values():
        if record.retracted:
            _reject(record.assumption_id, "retracted")
            continue
        unresolved = [r for r in record.evidence_refs if r not in evidence_index]
        if unresolved:
            _reject(record.assumption_id, "unresolved_evidence")
            rejected[-1] = (record.assumption_id,
                            f"unresolved_evidence: {unresolved[:2]}")
            continue
        accepted.append(record)
    accepted.sort(key=lambda r: (r.driver, r.scope))

    selection = AssumptionSelection(
        input_count=len(records) + len(parse_errors),
        accepted_count=len(accepted),
        reasons=dict(reasons),
        rejected=tuple(rejected),
    )
    return tuple(accepted), selection


__all__ = [
    "RECORD_VERSION", "assumption_record", "new_assumption_id", "parse_assumption_record",
    "select_assumptions",
]
