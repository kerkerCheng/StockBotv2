"""層代表公司宣告 ledger 的 I/O 與寫入端核對（個股頁 S3c；2026-10-09 使用者 ②A）。

純邏輯在 `alpha/layer_rep/contracts.py`；慣例照 `alpha/providers/layer_notes.py`：一個節點一個 JSONL、只 append、
壞行不靜默丟棄（INV-3）、寫入端核對不過就整筆拒收並逐條說出原因。**唯一的寫入入口是 `write_declaration`。**

**寫入端核對（契約層驗不了、要碰檔案或名冊的那幾件）：**
- 每家代表公司要在名冊裡（`identity.registry`；INV-1：不從公司名猜代號）。
- 出處 `raw:<檔名>`／`lead:<id>` 指得回去——與層說明**同一支** `verify_refs`（L16）。
- `supersedes_id` 要是這個節點最新的一筆（取代鏈不分岔）；同內容不得重複 append；密鑰形狀的內容拒收。
- **同一家、同一口徑（全公司，或同一個分部）只能代表一層**：跟其他節點的現行宣告撞到就拒收、指名那個節點與它的 lr_ id
  （同一份營收算進兩層的年增，兩層看起來都在長、其實是同一個數）。已被取代或撤回的舊宣告不算。

它**不寫 watch**：宣告本身沒有主張要盯；重看日到期由心跳計數（`ledger_snapshot`），重問＝換版。
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from alpha.errors import ContractViolation
from alpha.layer_rep.contracts import LayerRepresentatives, parse_layer_reps_record, select_current

_ROOT = Path(__file__).resolve().parents[2]
LAYER_REPS_DIR = _ROOT / "library" / "private" / "alpha" / "layer_representatives"
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


def _slug(node: str) -> str:
    text = _UNSAFE.sub("_", str(node).strip())
    if not text:
        raise ContractViolation("node 正規化後是空字串——檔名推不出來")
    return text


def ledger_path(node: str, *, directory: Path | None = None) -> Path:
    return (directory or LAYER_REPS_DIR) / f"{_slug(node)}.jsonl"


def read_records(node: str, *, directory: Path | None = None) -> tuple[list[LayerRepresentatives], list[str]]:
    """一個節點的全部紀錄；壞行回在第二個 list（不靜默丟）。"""
    path = ledger_path(node, directory=directory)
    if not path.is_file():
        return [], []
    records: list[LayerRepresentatives] = []
    errors: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ContractViolation("這一行不是 object")
            records.append(parse_layer_reps_record(raw))
        except (ValueError, ContractViolation) as exc:
            errors.append(f"{path.name}:{number}: {str(exc)[:120]}")
    return records, errors


def all_nodes(*, directory: Path | None = None) -> list[str]:
    """ledger 裡有紀錄的節點（讀每個檔第一個解析得到 node 的行；壞行跳過）。"""
    out: set[str] = set()
    root = directory or LAYER_REPS_DIR
    if not root.is_dir():
        return []
    for path in sorted(root.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                raw = json.loads(line) if line.strip() else None
            except ValueError:
                continue
            node = raw.get("node") if isinstance(raw, dict) else None
            if node:
                out.add(str(node))
                break
    return sorted(out)


def current_declarations(*, as_of: date | None = None, directory: Path | None = None
                         ) -> tuple[dict[str, LayerRepresentatives], dict[str, Any]]:
    """每個節點在 as-of 那天的現行宣告，與讀 ledger 的帳（壞行、as-of 時還沒寫下的節點各自的第一份宣告日）。"""
    out: dict[str, LayerRepresentatives] = {}
    errors: list[str] = []
    later: dict[str, str] = {}
    retracted: dict[str, str] = {}
    for node in all_nodes(directory=directory):
        records, bad = read_records(node, directory=directory)
        errors += bad
        current = select_current(records, as_of=as_of)
        if current is not None:
            out[node] = current
            continue
        seen = [r for r in records if as_of is None or r.created_at.date() <= as_of]
        if seen:                                   # 那天以前寫過、最新一筆是撤回
            retracted[node] = max(seen, key=lambda r: (r.created_at, r.rep_id)).created_at.date().isoformat()
        elif records:                              # 那天以後才寫——這個時點還沒宣告（INV-6）
            later[node] = min(r.created_at for r in records).date().isoformat()
    return out, {"parse_errors": errors, "declared_later": later, "retracted": retracted}


def _scope_key(rep: Any) -> tuple[str, str, str]:
    return (rep.company_id, rep.scope, rep.segment or "")


def write_declaration(record: Mapping[str, Any], *, directory: Path | None = None, raw_dir: Path | None = None,
                      lead_exists: Any = None, registry: Any = None) -> Path:
    """唯一的寫入入口：寫入端核對全過才 append 一行；不過就整筆拒收、逐條說原因。"""
    from shared.redaction import sensitive_payload_path

    from .layer_notes import verify_refs

    parsed = parse_layer_reps_record(record)
    sensitive = sensitive_payload_path(dict(record), "layer_reps")
    if sensitive is not None:
        raise ContractViolation(f"secret-bearing layer representatives rejected at {sensitive}")
    existing, _errors = read_records(parsed.node, directory=directory)
    if any(r.rep_id == parsed.rep_id for r in existing):
        raise ContractViolation(f"{parsed.rep_id} 已在 ledger 中——同內容不得重複 append")
    if parsed.supersedes_id:
        if not any(r.rep_id == parsed.supersedes_id for r in existing):
            raise ContractViolation(f"supersedes_id {parsed.supersedes_id} 不在 {parsed.node} 的 ledger 中")
        head = max(existing, key=lambda r: (r.created_at, r.rep_id))
        if head.rep_id != parsed.supersedes_id:
            raise ContractViolation(f"supersedes_id {parsed.supersedes_id} 不是 {parsed.node} 最新的一筆（最新是 {head.rep_id}）"
                                    "——換版只取代現行那一份，否則取代鏈會分岔")
    elif existing and select_current(existing) is not None:
        raise ContractViolation(f"{parsed.node} 已有現行宣告 {select_current(existing).rep_id}——換版要寫 supersedes_id")
    if not parsed.retracted:
        problems: list[str] = []
        if registry is None:
            from identity.registry import get_registry

            registry = get_registry()
        for rep in parsed.representatives:
            if not registry.has_company(rep.company_id):
                problems.append(f"{rep.company_id} 不在名冊（config/company_identity.json）——先補名冊，不從公司名猜（INV-1）")
        pairs = [(f"representatives[{i}]（{rep.company_id}）", c.ref) for i, rep in enumerate(parsed.representatives, 1)
                 for c in rep.citations if c.ref]
        problems += verify_refs(pairs, raw_dir=raw_dir, lead_exists=lead_exists)
        current, _book = current_declarations(directory=directory)
        mine = {_scope_key(rep) for rep in parsed.representatives}
        for node, other in sorted(current.items()):
            if node == parsed.node:
                continue
            for rep in other.representatives:
                if _scope_key(rep) in mine:
                    label = "全公司" if rep.scope == "whole_company" else f"分部「{rep.segment}」"
                    problems.append(f"{rep.company_id} 的{label}營收已經代表 {node}（{other.rep_id}）——同一份營收不得算進兩層；"
                                    "要搬就先把那一層換版")
        if problems:
            raise ContractViolation("代表公司宣告拒收：\n  - " + "\n  - ".join(problems))
    path = ledger_path(parsed.node, directory=directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n")
    return path


def ledger_snapshot(*, today: date, directory: Path | None = None) -> dict[str, Any]:
    """心跳與稽核用的計數：現行宣告幾份、過重看日幾份、壞行幾行（0 也回）。"""
    current, book = current_declarations(directory=directory)
    overdue = sorted(node for node, rec in current.items() if rec.expires is not None and rec.expires < today)
    return {"current": len(current), "overdue": overdue, "parse_errors": len(book["parse_errors"])}


__all__ = ["LAYER_REPS_DIR", "all_nodes", "current_declarations", "ledger_path", "ledger_snapshot", "read_records",
           "write_declaration"]
