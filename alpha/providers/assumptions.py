"""OperatingAssumption ledger 的 I/O：`library/private/alpha/assumptions/<TICKER>.jsonl`。

## 為什麼是 private append-only JSONL

- **A3 研究判斷，可重算但要留稽核痕跡**：改假設＝append 新紀錄（同 key 較新者勝出），
  撤回＝append `retracted=true`。舊紀錄永遠留著，as-of 視角靠 `created_at` 回放。
- **private，不進 Git**：與 session 判斷檔（`library/private/alpha/judgments/`）同一個位置慣例；
  假設是研究判斷，不是可公開的事實。
- **不是 Engine C**：Engine C 只擁有觀測；把內部預測塞進它會讓它同時成為 actual／consensus／
  forecast 三種 authority（Phase 2 明文禁止）。

純邏輯（解析、選取、supersede）在 `alpha/fundamental/assumptions.py`；這裡只讀寫檔。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from shared.redaction import sensitive_payload_path

from ..errors import ContractViolation
from ..fundamental.assumptions import parse_assumption_record
from ..fundamental.contracts import OperatingAssumption

_ROOT = Path(__file__).resolve().parents[2]
ASSUMPTION_DIR = _ROOT / "library" / "private" / "alpha" / "assumptions"


def ledger_path(ticker: str, *, directory: Path | None = None) -> Path:
    return (directory or ASSUMPTION_DIR) / f"{ticker.strip().upper()}.jsonl"


def read_assumption_records(
    ticker: str, *, directory: Path | None = None,
) -> tuple[list[OperatingAssumption], list[str]]:
    """讀一檔的全部紀錄。壞掉的行**不靜默丟棄**——回在第二個 list 裡，模型端計數（INV-3）。"""
    path = ledger_path(ticker, directory=directory)
    if not path.is_file():
        return [], []
    records: list[OperatingAssumption] = []
    errors: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if not text:
            continue
        try:
            records.append(parse_assumption_record(json.loads(text)))
        except (ValueError, ContractViolation) as exc:
            errors.append(f"{path.name}:{number}: {str(exc)[:120]}")
    return records, errors


def append_assumption_record(record: Mapping[str, Any], *, directory: Path | None = None) -> Path:
    """append 一筆（已由 `assumption_record()` 驗證過的）紀錄。

    - 同 `assumption_id` 已存在 → 拒絕（content-addressed，重複 append 是呼叫端錯誤）。
    - 帶 secret 的 payload → 拒絕（與 Engine C ledger 同一道 redaction）。
    - 只 append，永不改寫既有行。
    """
    parsed = parse_assumption_record(record)              # 寫入前再驗一次
    sensitive = sensitive_payload_path(dict(record), "assumption")
    if sensitive is not None:
        raise ContractViolation(f"secret-bearing assumption rejected at {sensitive}")
    path = ledger_path(parsed.ticker, directory=directory)
    existing, _ = read_assumption_records(parsed.ticker, directory=directory)
    if any(r.assumption_id == parsed.assumption_id for r in existing):
        raise ContractViolation(f"假設 {parsed.assumption_id} 已在 ledger 中——同內容不得重複 append")
    if parsed.supersedes_id and not any(r.assumption_id == parsed.supersedes_id for r in existing):
        raise ContractViolation(f"supersedes_id {parsed.supersedes_id} 不在 ledger 中")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n")
    return path


__all__ = ["ASSUMPTION_DIR", "append_assumption_record", "ledger_path", "read_assumption_records"]
