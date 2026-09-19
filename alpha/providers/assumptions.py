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
from ..fundamental.assumptions import live_base_keys, parse_assumption_record
from ..fundamental.contracts import BASE_SCENARIO, OperatingAssumption

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


def append_assumption_record(
    record: Mapping[str, Any], *, directory: Path | None = None,
    allow_new_scope: bool = False,
) -> Path:
    """append 一筆（已由 `assumption_record()` 驗證過的）紀錄。

    - 同 `assumption_id` 已存在 → 拒絕（content-addressed，重複 append 是呼叫端錯誤）。
    - 帶 secret 的 payload → 拒絕（與 Engine C ledger 同一道 redaction）。
    - overlay 的 `(driver, scope)` 未命中任何生效 base 假設 → 拒絕（見下）。
    - 只 append，永不改寫既有行。

    `allow_new_scope=True` 才放行「引入 base 沒有的切分」那條 overlay。預設拒收是因為
    **那個情況與打錯 scope 在資料上長得一模一樣**，而兩者的後果天差地別：打錯時 overlay
    不會覆蓋 base，兩條假設會同時生效、數值相加。
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
    if parsed.supersedes_id:
        # V0：base 與 variant 是兩條鏈。跨 scenario 的 supersede 會讓 variant「關掉」一條 base，
        # 而 overlay 的語意是覆蓋不是取代——寫入端擋住，選取端才不必猜。
        target = next(r for r in existing if r.assumption_id == parsed.supersedes_id)
        if target.scenario != parsed.scenario:
            raise ContractViolation(
                f"supersedes_id {parsed.supersedes_id} 屬於 scenario={target.scenario!r}，"
                f"本筆是 {parsed.scenario!r}——不得跨 scenario supersede（variant 是 overlay，不是取代）")
    if parsed.scenario != BASE_SCENARIO and not parsed.retracted and not allow_new_scope:
        # 缺陷（2026-09-19 實測）：overlay 的覆蓋鍵是 `(driver, scope)`。scope 打錯時它不會
        # 覆蓋 base，而是**被當成第三條假設一起生效**——LITE 的營益率因此變成
        # 29.8＋10.2＋10.7＝50.7%，產出假的隱含報酬 +50.3%（真值 +20.7%）。
        # ⚠ 這個錯誤的方向永遠是「對自己有利」（多疊一個正的 delta），而且不報錯、測試不紅。
        # ⚠ **retracted 的 overlay 必須跳過這道檢查**：撤回紀錄沿用被撤回那筆的 driver/scope，
        #   擋住它等於「寫錯的 overlay 永遠撤不回」——正是 2026-09-19 才修好的那個 bug。
        base_keys = live_base_keys(existing, period=parsed.period)
        if parsed.key not in base_keys:
            same_driver = sorted(scope for driver, scope in base_keys if driver == parsed.driver)
            hint = (f"該 driver 在 base 的 scope 是 {same_driver}" if same_driver
                    else f"base 在 {parsed.period.label} 沒有任何 {parsed.driver!r} 假設")
            raise ContractViolation(
                f"{parsed.scenario} 假設 {parsed.driver}[{parsed.scope}] 未命中任何生效 base 假設"
                f"——overlay 的覆蓋鍵是 (driver, scope)，未命中不會覆蓋而是**與 base 同時生效**"
                f"（數值相加）。{hint}。"
                f"確實要引入 base 沒有的新切分才傳 allow_new_scope=True（CLI：--allow-new-scope）")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n")
    return path


__all__ = ["ASSUMPTION_DIR", "append_assumption_record", "ledger_path", "read_assumption_records"]
