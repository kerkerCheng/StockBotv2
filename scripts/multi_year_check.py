"""Phase 4b 的驗收，做成一條可以跑的命令（2026-09-20）。

驗收行逐字：「**多年橋算得出倍率與它的前提鏈，且每一格配 disproof**」。
那句話拆成三個可機械驗證的問題，**逐檔報 input／accepted／filtered／reasons**（INV-3）：

1. **算得出倍率嗎** — `multi_year` artifact 的 status 是 `available`，且四級階梯裡
   至少有一級解得出某個 driver。
2. **前提鏈指得回去嗎** — 那個解出來的 driver 指得回一筆生效假設（`assumption_id`），
   而那筆假設有非空的 `evidence_refs`。⚠ 指得回**一個 id** 還不夠：id 指向的假設若
   自己沒有證據，鏈條就斷在最後一節。
3. **每一格配 disproof 嗎** — 那個 driver 出現在某條 `DisproofCondition.invalidates` 裡。

⚠ **這支腳本不改任何東西**，它只回答「今天到哪了」。跑它之前要先
`python -m webapp materialize --multi-year`——多年橋是金融模型，APP 呈現契約禁止
request path 跑模型，所以唯一的真相來源是 materialize 出來的 artifact。

⚠ 第 3 格今天預期是 0：`invalidates` 是 2026-09-20 才加的欄位，而填值是 judgment
（要決定「這條反證真的在講這個 driver 嗎」），走 pq2。**那個 0 是誠實的起點，不是故障**
——它會隨核准逐檔變動，這正是 L14-1 要的「現有資料有幾筆真的變了」。
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ARTIFACT = ROOT / "library/private/app/state/multi_year.json"

REASONS = {
    "no_ladder": "算不出倍率——多年橋本身沒有 available 的階梯（理由看 artifact 的 reason）",
    "no_solved_driver": "階梯在，但四級裡沒有任何一級解得出 driver——沒有前提可談",
    "assumption_missing": "解出來的 driver 指不回任何生效假設（鏈條在第一節就斷）",
    "assumption_without_evidence": "指得回假設，但那筆假設自己沒有 evidence_refs——鏈條斷在最後一節",
    "no_disproof_link": "前提鏈完整，但沒有任何 disproof 的 `invalidates` 指名這個 driver",
}


def _live_assumptions(ticker: str) -> dict[str, object]:
    from alpha.providers import assumptions as ledger

    records, _errors = ledger.read_assumption_records(ticker)
    superseded = {r.supersedes_id for r in records if getattr(r, "supersedes_id", None)}
    return {r.assumption_id: r for r in records
            if not r.retracted and r.assumption_id not in superseded}


def _invalidated_drivers(ticker: str) -> set[str]:
    """這一檔的 disproof 指名了哪些 driver（scope 去掉，只比 driver 層）。"""
    from briefing.alpha_view.sources import locate_judgment

    path = locate_judgment(ticker)
    if path is None:
        return set()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    out: set[str] = set()
    for condition in (raw.get("disproof_conditions") or []):
        if not isinstance(condition, dict):
            continue
        for item in (condition.get("invalidates") or ()):
            out.add(str(item).split("[", 1)[0].strip())
    return out


def main() -> int:
    if not ARTIFACT.exists():
        print(f"✗ 找不到 {ARTIFACT.relative_to(ROOT)}"
              "——先跑 `python -m webapp materialize --multi-year`", file=sys.stderr)
        return 2
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    rows = payload.get("rows") or []

    reasons: Counter[str] = Counter()
    accepted: list[str] = []
    detail: list[tuple[str, str, str]] = []

    for row in rows:
        ticker = str(row.get("ticker"))
        if row.get("status") != "available" or not (row.get("ladder") or []):
            reasons["no_ladder"] += 1
            detail.append((ticker, "no_ladder", str(row.get("status"))))
            continue
        solved = [s for step in row["ladder"] for s in (step.get("solutions") or [])
                  if s.get("status") in ("solved", "already_equal")]
        if not solved:
            reasons["no_solved_driver"] += 1
            detail.append((ticker, "no_solved_driver", ""))
            continue

        live = _live_assumptions(ticker)
        named = _invalidated_drivers(ticker)
        why = None
        for s in solved:
            record = live.get(s.get("assumption_id"))
            if record is None:
                why = "assumption_missing"
                break
            if not getattr(record, "evidence_refs", ()):
                why = "assumption_without_evidence"
                break
            if str(s.get("driver")) not in named:
                why = "no_disproof_link"
                break
        if why:
            reasons[why] += 1
            drivers = "、".join(sorted({str(s.get("driver")) for s in solved}))
            detail.append((ticker, why, drivers))
        else:
            accepted.append(ticker)

    total = len(rows)
    print("# Phase 4b 驗收：多年橋算得出倍率與前提鏈，且每一格配 disproof")
    print()
    print(f"input {total}｜accepted {len(accepted)}｜filtered {total - len(accepted)}")
    print()
    print("## filtered 的理由（逐條，不合併）")
    for key, count in reasons.most_common():
        print(f"  {count:3d}  {key}：{REASONS.get(key, '（未登記的理由——補一行到 REASONS）')}")
    if accepted:
        print()
        print("## accepted")
        for ticker in accepted:
            print(f"  ✓ {ticker}")
    print()
    print("## 逐檔")
    for ticker, key, extra in detail:
        print(f"  {ticker:12s} {key:28s} {extra}")
    print()
    actionable = [d for d in detail if d[1] == "no_disproof_link"]
    if actionable:
        print("⚠ `no_disproof_link` 是**我們自己沒填**，不是標的的缺點——"
              "填 `DisproofCondition.invalidates` 是 judgment，走 pq2。要填的是：")
        for ticker, _key, drivers in actionable:
            print(f"  · {ticker}：{drivers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
