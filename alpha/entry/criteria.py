"""EntryCriterion ledger 紀錄的**純邏輯**：序列化、解析、as-of 選取、supersede。

I/O（JSONL 檔）在 `alpha/providers/entry_criteria.py`；這裡不讀檔、不開連線。

與營運／估值／horizon 假設同一套 append-only 語意（content-addressed id、as-of 選取、同 key 最新者勝出、
撤回不讓舊值復活），但**刻意不共用 `select_assumptions`**：那支選取器以會計期間為身分（`period.same_as`）
並要求證據解析到公司的 evidence index；要求報酬判準既不屬於某一年、其 provenance 也不在公司的證據池裡
（投資人的機會成本不是公司文件）。硬套會製造「換了估值年度 hurdle 就 other_period」這種假失效。
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any, Mapping, Sequence

from ..errors import ContractViolation
from ..fundamental.contracts import AssumptionSelection
from .contracts import CONVENTION_ANNUALIZED_PRICE_RETURN, EntryCriterion

RECORD_VERSION = "entry-criterion/v1"

_ID_FIELDS = ("company_id", "ticker", "convention", "value", "basis", "rationale", "reference_refs",
              "created_at", "author", "supersedes_id", "retracted")


def new_entry_criterion_id(payload: Mapping[str, Any]) -> str:
    """content-addressed id：同一份內容永遠得到同一個 id（重複 append 可被偵測）。"""
    body = {k: payload.get(k) for k in _ID_FIELDS}
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return "ec_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def entry_criterion_record(
    *,
    company_id: str,
    ticker: str,
    value: float,
    basis: str,
    rationale: str,
    convention: str = CONVENTION_ANNUALIZED_PRICE_RETURN,
    reference_refs: Sequence[str] = (),
    created_at: datetime | None = None,
    author: str = "user",
    supersedes_id: str | None = None,
    retracted: bool = False,
) -> dict[str, Any]:
    """建一筆可寫進 ledger 的紀錄（先經 `EntryCriterion` 驗證，驗不過就不產生）。

    `basis` 沒有預設——呼叫端必須明寫 `investor_policy`，這是「我知道我在宣告的是自己的政策」的簽名。
    """
    stamp = created_at or datetime.now(timezone.utc)
    if stamp.tzinfo is None:
        raise ContractViolation("created_at 必須帶時區")
    stamp = stamp.astimezone(timezone.utc)
    payload: dict[str, Any] = {
        "record_version": RECORD_VERSION,
        "company_id": str(company_id),
        "ticker": str(ticker).upper(),
        "convention": convention,
        "value": float(value),
        "unit": "ratio",
        "basis": basis,
        "rationale": rationale,
        "reference_refs": [str(r) for r in reference_refs],
        "created_at": stamp.isoformat(),
        "author": author,
        "supersedes_id": supersedes_id,
        "retracted": bool(retracted),
    }
    payload["criterion_id"] = new_entry_criterion_id(payload)
    parse_entry_criterion_record(payload)          # 驗證；不合法就在這裡炸，不會寫進 ledger
    return payload


def parse_entry_criterion_record(raw: Mapping[str, Any]) -> EntryCriterion:
    """dict → `EntryCriterion`；任何欄位不合法都 raise `ContractViolation`。"""
    try:
        created = datetime.fromisoformat(str(raw["created_at"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractViolation(f"entry criterion 紀錄欄位不合法：{exc}") from None
    refs = raw.get("reference_refs") or []
    if isinstance(refs, str):
        raise ContractViolation("reference_refs 必須是 list")
    if raw.get("unit", "ratio") != "ratio":
        raise ContractViolation(f"entry criterion 的 unit 只能是 ratio，收到 {raw.get('unit')!r}")
    return EntryCriterion(
        criterion_id=str(raw.get("criterion_id") or ""),
        company_id=str(raw.get("company_id") or ""),
        ticker=str(raw.get("ticker") or ""),
        convention=str(raw.get("convention") or ""),
        value=raw.get("value"),                       # type: ignore[arg-type]
        basis=str(raw.get("basis") or ""),
        rationale=str(raw.get("rationale") or ""),
        created_at=created,
        author=str(raw.get("author") or ""),
        reference_refs=tuple(str(r) for r in refs),
        supersedes_id=(str(raw["supersedes_id"]) if raw.get("supersedes_id") else None),
        retracted=bool(raw.get("retracted")),
    )


def select_entry_criteria(
    records: Sequence[EntryCriterion],
    *,
    as_of: date | None,
    today: date,
    parse_errors: Sequence[str] = (),
) -> tuple[tuple[EntryCriterion, ...], AssumptionSelection]:
    """挑出**在 T 時刻存在、同 convention 最新、未撤回**的判準；其餘逐筆計數（INV-3）。

    順序刻意與 `select_assumptions` 同形：先 as-of（T 之後寫的紀錄根本不存在），再同 key 最新者勝出
    （較舊者 superseded／superseded_by_newer），最新一筆若是撤回就沒有生效判準——撤回不讓舊值復活。
    **沒有期間過濾、沒有證據解析**（理由見模組 docstring）。
    """
    cutoff = as_of or today
    reasons: dict[str, int] = {}
    rejected: list[tuple[str, str]] = []

    def _reject(item_id: str, reason: str) -> None:
        reasons[reason.split(":")[0]] = reasons.get(reason.split(":")[0], 0) + 1
        rejected.append((item_id, reason))

    for error in parse_errors:
        _reject("?", f"invalid_record: {error}")

    ordered = sorted(records, key=lambda r: (r.created_at, r.criterion_id))
    latest_by_key: dict[tuple[str, str], EntryCriterion] = {}
    for record in ordered:
        if record.created_on > cutoff:
            _reject(record.criterion_id, "created_after_as_of")
            continue
        previous = latest_by_key.get(record.key)
        if previous is not None:
            _reject(previous.criterion_id,
                    "superseded" if record.supersedes_id == previous.criterion_id else "superseded_by_newer")
        latest_by_key[record.key] = record

    accepted: list[EntryCriterion] = []
    for record in latest_by_key.values():
        if record.retracted:
            _reject(record.criterion_id, "retracted")
            continue
        accepted.append(record)
    accepted.sort(key=lambda r: r.key)
    selection = AssumptionSelection(
        input_count=len(records) + len(parse_errors), accepted_count=len(accepted),
        reasons=dict(reasons), rejected=tuple(rejected),
    )
    return tuple(accepted), selection


__all__ = [
    "RECORD_VERSION", "entry_criterion_record", "new_entry_criterion_id", "parse_entry_criterion_record",
    "select_entry_criteria",
]
