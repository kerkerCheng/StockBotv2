"""ValuationAssumption ledger 的 I/O：`library/private/alpha/valuation/<TICKER>.jsonl`。

與 `alpha/providers/assumptions.py` 同一個位置慣例與同一套規則：private、append-only、
content-addressed id 拒絕重複、secret 拒絕、supersedes_id 必須指到既有紀錄。
純邏輯（解析、選取、supersede）在 `alpha/valuation/assumptions.py`；這裡只讀寫檔。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from shared.redaction import sensitive_payload_path

from ..errors import ContractViolation
from ..valuation.assumptions import parse_valuation_assumption_record
from ..valuation.contracts import ValuationAssumption

_ROOT = Path(__file__).resolve().parents[2]
VALUATION_DIR = _ROOT / "library" / "private" / "alpha" / "valuation"


def ledger_path(ticker: str, *, directory: Path | None = None) -> Path:
    return (directory or VALUATION_DIR) / f"{ticker.strip().upper()}.jsonl"


def read_valuation_assumption_records(
    ticker: str, *, directory: Path | None = None,
) -> tuple[list[ValuationAssumption], list[str]]:
    """讀一檔的全部紀錄。壞掉的行**不靜默丟棄**——回在第二個 list 裡，模型端計數（INV-3）。"""
    path = ledger_path(ticker, directory=directory)
    if not path.is_file():
        return [], []
    records: list[ValuationAssumption] = []
    errors: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if not text:
            continue
        try:
            records.append(parse_valuation_assumption_record(json.loads(text)))
        except (ValueError, ContractViolation) as exc:
            errors.append(f"{path.name}:{number}: {str(exc)[:120]}")
    return records, errors


def append_valuation_assumption_record(record: Mapping[str, Any], *, directory: Path | None = None) -> Path:
    """append 一筆（已由 `valuation_assumption_record()` 驗證過的）紀錄；只 append，永不改寫既有行。"""
    parsed = parse_valuation_assumption_record(record)
    sensitive = sensitive_payload_path(dict(record), "valuation_assumption")
    if sensitive is not None:
        raise ContractViolation(f"secret-bearing valuation assumption rejected at {sensitive}")
    path = ledger_path(parsed.ticker, directory=directory)
    existing, _ = read_valuation_assumption_records(parsed.ticker, directory=directory)
    if any(r.assumption_id == parsed.assumption_id for r in existing):
        raise ContractViolation(f"估值假設 {parsed.assumption_id} 已在 ledger 中——同內容不得重複 append")
    if parsed.supersedes_id and not any(r.assumption_id == parsed.supersedes_id for r in existing):
        raise ContractViolation(f"supersedes_id {parsed.supersedes_id} 不在 ledger 中")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n")
    return path


__all__ = ["VALUATION_DIR", "append_valuation_assumption_record", "ledger_path", "read_valuation_assumption_records"]
