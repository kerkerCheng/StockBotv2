#!/usr/bin/env python
"""把引用了**已被 supersede 的基期觀測**的假設，重新 append 一筆指向新版（append-only）。

## 什麼時候需要它

Engine C 的人工 ledger 是 append-only：更正一筆基期觀測＝append 新紀錄 ＋ `--supersedes`（L10）。
自 2026-09-13 起 `alpha/providers/fundamentals.py` 會把**整條 supersession 鏈**都放進 evidence
index（每一筆標明被誰取代），所以**舊引用不再會讓假設整條消失**——這支腳本因此**不是修復工具**。

它解決的是另一件事：**ledger 上「這條假設是看著哪一版基期寫的」這個宣告會逐漸過時。**
更正了基期之後，若那條假設的判斷本身沒有變，把它重新指向新版是一個誠實的簿記動作；
但那件事**只能由人決定**，因為「假設是否仍然成立」不是機械問題——所以本腳本預設 `--dry-run`，
且會把每一筆的差異列出來讓人看過再寫。

⚠ **它不改值、不改 rationale**（只在 rationale 前面加一段「本筆為 re-append，只換基期 ref」），
每一筆都帶 `supersedes_id`，舊紀錄全部留在 ledger。

用法：
    python scripts/realign_assumption_refs.py AEVA                 # 只列出要改什麼
    python scripts/realign_assumption_refs.py AEVA --apply         # 真的 append
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alpha.cli import _resolve_company                                    # noqa: E402
from alpha.providers.assumptions import (                                 # noqa: E402
    append_assumption_record, read_assumption_records,
)
from alpha.fundamental.assumptions import assumption_record               # noqa: E402

PREFIX = "engine_c://manual_observation/"
NOTE = ("⚠ 本筆為 re-append：基期觀測 {old} 已被 {new} 取代，本筆只把 evidence ref 指向新版。"
        "**值、scope、rationale 全部與原筆相同。**由 `scripts/realign_assumption_refs.py` 產生。\n\n")


def _live_chain(ticker: str) -> dict[str, str]:
    """superseded observation_id → 取代它的那一筆（遞移到最新）。"""
    private = ROOT / "library" / "private"
    db = private / json.loads((private / "runtime_pointer.json").read_text(encoding="utf-8"))["engine_c"]
    conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    rows = conn.execute(
        "SELECT observation_id, supersedes_id FROM manual_observations WHERE ticker = ?",
        (ticker,)).fetchall()
    direct = {str(parent): str(child) for child, parent in rows if parent}
    out: dict[str, str] = {}
    for old in direct:
        cur = old
        seen = {cur}
        while cur in direct and direct[cur] not in seen:
            cur = direct[cur]
            seen.add(cur)
        out[old] = cur
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ticker")
    ap.add_argument("--apply", action="store_true", help="真的 append（預設只列出）")
    args = ap.parse_args()
    resolved, company_id = _resolve_company(args.ticker)
    ticker = str(resolved)
    chain = _live_chain(ticker)
    if not chain:
        print(f"{ticker}：沒有任何 superseded 的基期觀測——不需要對齊")
        return 0
    records, _ = read_assumption_records(ticker)
    superseded_ids = {r.supersedes_id for r in records if r.supersedes_id}
    live = [r for r in records if not r.retracted and r.assumption_id not in superseded_ids]
    todo = [r for r in live if any(ref[len(PREFIX):] in chain
                                   for ref in r.evidence_refs if ref.startswith(PREFIX))]
    if not todo:
        print(f"{ticker}：{len(live)} 條生效假設都已指向最新基期——不需要對齊")
        return 0
    print(f"{ticker}：{len(todo)}／{len(live)} 條生效假設引用了舊版基期")
    for r in todo:
        olds = [ref[len(PREFIX):] for ref in r.evidence_refs
                if ref.startswith(PREFIX) and ref[len(PREFIX):] in chain]
        print(f"  - {r.driver}[{r.scope}] {r.assumption_id}：" + "、".join(f"{o} → {chain[o]}" for o in olds))
    if not args.apply:
        print("（dry-run；加 --apply 才會寫入）")
        return 0
    for r in todo:
        roles = dict(r.dependency_roles)
        mapped = [(PREFIX + chain[ref[len(PREFIX):]]) if (ref.startswith(PREFIX) and ref[len(PREFIX):] in chain)
                  else ref for ref in r.evidence_refs]
        old_ids = [ref[len(PREFIX):] for ref in r.evidence_refs
                   if ref.startswith(PREFIX) and ref[len(PREFIX):] in chain]
        note = NOTE.format(old=old_ids[0], new=chain[old_ids[0]])
        record = assumption_record(
            company_id=str(company_id), ticker=ticker, period_end=r.period.end, driver=r.driver,
            scope=r.scope, value=r.value, basis=r.basis, rationale=note + r.rationale,
            evidence_refs=[m for m, orig in zip(mapped, r.evidence_refs)
                           if roles.get(orig, "supporting") == "supporting"],
            calibration_refs=[m for m, orig in zip(mapped, r.evidence_refs)
                              if roles.get(orig) == "calibration"],
            comparison_refs=[m for m, orig in zip(mapped, r.evidence_refs)
                             if roles.get(orig) == "comparison"],
            accounting_basis=r.accounting_basis, derivation=r.derivation,
            supersedes_id=r.assumption_id, author=r.author)
        append_assumption_record(record)
        print(f"  ✓ {r.driver}[{r.scope}] → {record['assumption_id']}")
    print(f"完成 {len(todo)} 筆。⚠ 舊紀錄全部留在 ledger（append-only）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
