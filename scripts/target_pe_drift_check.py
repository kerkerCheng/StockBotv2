#!/usr/bin/env python
"""目標倍數 vs 今天的市場倍數，**哪幾筆已經背離到該重新校準**（七缺陷之 6 的驗收基準）。

判準（AGENTS.md 2026-09-09）不會腐壞：**沒有 re-rating 證據時，目標倍數預設等於校準用的
市場倍數**。腐壞的是那個被存進 ledger 的**數字**——而先前沒有任何機制在盯兩者背離。

⚠ 本檔**只讀不寫**：不改任何 ledger、不重新校準、不動 thesis。
完整判準與三道 fail closed 見 `alpha/valuation/drift.py` 的 docstring。

用法：
    python scripts/target_pe_drift_check.py
    python scripts/target_pe_drift_check.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from alpha.valuation.drift import heartbeat_line, scan  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = scan()
    if args.json:
        payload = dict(result)
        payload["rows"] = [asdict(r) for r in result["rows"]]
        print(json.dumps(payload, ensure_ascii=False, indent=1))
        return 0

    print("# 目標倍數背離掃描（只讀；不重新校準、不改 ledger）")
    print(f"門檻 {result['threshold']:.0%}｜生效 target_pe {result['input']} 筆")
    print(json.dumps(result["counts"], ensure_ascii=False))
    print()
    print(f"{'tick':<11}{'status':<16}{'target':>9}{'market':>9}{'drift':>9}  理由")
    print("-" * 96)
    for row in result["rows"]:
        target = f"{row.target:.2f}" if row.target is not None else "—"
        market = f"{row.market:.2f}" if row.market is not None else "—"
        drift = f"{row.drift:+.1%}" if row.drift is not None else "—"
        print(f"{row.ticker:<11}{row.status:<16}{target:>9}{market:>9}{drift:>9}  {row.reason or ''}")
    print()
    print(heartbeat_line(result))
    print("⚠ `cannot_compare` **不是「沒背離」**——它是「不知道」，而先前那些會靜默落進在帶內。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
