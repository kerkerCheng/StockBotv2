"""EntryCriterion ledger 的 I/O：`library/private/alpha/entry_criteria/<TICKER>.jsonl`。

與 `alpha/providers/horizon_assumptions.py` 同一個位置慣例與同一套規則：private、append-only、
content-addressed id 拒絕重複、secret 拒絕、supersedes_id 必須指到既有紀錄。
純邏輯（解析、選取、supersede）在 `alpha/entry/criteria.py`；這裡只讀寫檔。

⚠ **這是全系統唯一會寫這個 ledger 的入口，而它只被互動 CLI（`python -m alpha entry-criterion --add`）呼叫。**
refresh 引擎、排程、情境模擬、sandbox 驗算都不寫它——hurdle 是投資人的政策，不得被自動改。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from shared.redaction import sensitive_payload_path

from ..entry.contracts import EntryCriterion
from ..entry.criteria import parse_entry_criterion_record
from ..errors import ContractViolation

_ROOT = Path(__file__).resolve().parents[2]
ENTRY_CRITERIA_DIR = _ROOT / "library" / "private" / "alpha" / "entry_criteria"


def ledger_path(ticker: str, *, directory: Path | None = None) -> Path:
    return (directory or ENTRY_CRITERIA_DIR) / f"{ticker.strip().upper()}.jsonl"


def read_entry_criterion_records(
    ticker: str, *, directory: Path | None = None,
) -> tuple[list[EntryCriterion], list[str]]:
    """讀一檔的全部紀錄。壞掉的行**不靜默丟棄**——回在第二個 list 裡，模型端計數（INV-3）。"""
    path = ledger_path(ticker, directory=directory)
    if not path.is_file():
        return [], []
    records: list[EntryCriterion] = []
    errors: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if not text:
            continue
        try:
            records.append(parse_entry_criterion_record(json.loads(text)))
        except (ValueError, ContractViolation) as exc:
            errors.append(f"{path.name}:{number}: {str(exc)[:120]}")
    return records, errors


def append_entry_criterion_record(record: Mapping[str, Any], *, directory: Path | None = None) -> Path:
    """append 一筆（已由 `entry_criterion_record()` 驗證過的）紀錄；只 append，永不改寫既有行。"""
    parsed = parse_entry_criterion_record(record)
    sensitive = sensitive_payload_path(dict(record), "entry_criterion")
    if sensitive is not None:
        raise ContractViolation(f"secret-bearing entry criterion rejected at {sensitive}")
    if parsed.author.lower() == "sandbox":
        raise ContractViolation("author=sandbox 的判準是驗算用的非持久物件，不得寫進 ledger")
    path = ledger_path(parsed.ticker, directory=directory)
    existing, _ = read_entry_criterion_records(parsed.ticker, directory=directory)
    if any(r.criterion_id == parsed.criterion_id for r in existing):
        raise ContractViolation(f"entry criterion {parsed.criterion_id} 已在 ledger 中——同內容不得重複 append")
    if parsed.supersedes_id and not any(r.criterion_id == parsed.supersedes_id for r in existing):
        raise ContractViolation(f"supersedes_id {parsed.supersedes_id} 不在 ledger 中")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n")
    return path


__all__ = ["ENTRY_CRITERIA_DIR", "append_entry_criterion_record", "ledger_path", "read_entry_criterion_records"]
