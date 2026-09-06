"""HorizonAssumption ledger 的 I/O：`library/private/alpha/horizon/<TICKER>.jsonl`。

與 `alpha/providers/valuation_assumptions.py` 同一個位置慣例與同一套規則：private、append-only、
content-addressed id 拒絕重複、secret 拒絕、supersedes_id 必須指到既有紀錄。
純邏輯（解析、選取、supersede）在 `alpha/implied_return/assumptions.py`；這裡只讀寫檔。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from shared.redaction import sensitive_payload_path

from ..errors import ContractViolation
from ..implied_return.assumptions import parse_horizon_assumption_record
from ..implied_return.contracts import HorizonAssumption

_ROOT = Path(__file__).resolve().parents[2]
HORIZON_DIR = _ROOT / "library" / "private" / "alpha" / "horizon"


def ledger_path(ticker: str, *, directory: Path | None = None) -> Path:
    return (directory or HORIZON_DIR) / f"{ticker.strip().upper()}.jsonl"


def read_horizon_assumption_records(
    ticker: str, *, directory: Path | None = None,
) -> tuple[list[HorizonAssumption], list[str]]:
    """讀一檔的全部紀錄。壞掉的行**不靜默丟棄**——回在第二個 list 裡，模型端計數（INV-3）。"""
    path = ledger_path(ticker, directory=directory)
    if not path.is_file():
        return [], []
    records: list[HorizonAssumption] = []
    errors: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if not text:
            continue
        try:
            records.append(parse_horizon_assumption_record(json.loads(text)))
        except (ValueError, ContractViolation) as exc:
            errors.append(f"{path.name}:{number}: {str(exc)[:120]}")
    return records, errors


def append_horizon_assumption_record(record: Mapping[str, Any], *, directory: Path | None = None) -> Path:
    """append 一筆（已由 `horizon_assumption_record()` 驗證過的）紀錄；只 append，永不改寫既有行。"""
    parsed = parse_horizon_assumption_record(record)
    sensitive = sensitive_payload_path(dict(record), "horizon_assumption")
    if sensitive is not None:
        raise ContractViolation(f"secret-bearing horizon assumption rejected at {sensitive}")
    path = ledger_path(parsed.ticker, directory=directory)
    existing, _ = read_horizon_assumption_records(parsed.ticker, directory=directory)
    if any(r.assumption_id == parsed.assumption_id for r in existing):
        raise ContractViolation(f"horizon 假設 {parsed.assumption_id} 已在 ledger 中——同內容不得重複 append")
    if parsed.supersedes_id and not any(r.assumption_id == parsed.supersedes_id for r in existing):
        raise ContractViolation(f"supersedes_id {parsed.supersedes_id} 不在 ledger 中")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n")
    return path


__all__ = ["HORIZON_DIR", "append_horizon_assumption_record", "ledger_path", "read_horizon_assumption_records"]
