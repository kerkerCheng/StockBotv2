"""舊五軸 → 新五 score 的 old/new dual run。

## 為什麼一定要做這一步

`historical-failure-matrix.md` §8：**critical migration 階段，舊 pipeline 與新 pipeline
對同一 frozen input 並行執行，產生 semantic diff；每個差異必須被分類為
`EXPECTED_CHANGE`／`BUG_FIX`／`INTENTIONAL_REMOVAL`／`REGRESSION`。
禁止存在 unexplained behavioral diff。**

本 repo 已有一次成功先例可照抄：2026-08-29 改 `research_status` 判準前，
先對 21 個 operational cohort 套用新判準、量出 **3 筆改判**，才動手。

## 這一輪要回答的三個問題

1. 新的 `weakest`（投資維度）與舊的 `weakest_axis`（證據軸）差在哪、差多少？
2. `EvidenceQuality` 上限有沒有把任何維度壓下去？壓了幾筆？
3. 有沒有**無法解釋**的差異？（有的話就不能宣稱轉換乾淨）

⚠ 唯讀。不寫 Decision Store、不改任何 authority。

用法：
    python scripts/dualrun_axis_conversion.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alpha.contracts import AXES  # noqa: E402
from alpha.legacy_axes import (  # noqa: E402
    LEGACY_AXIS_TO_SCORE, UNMAPPED_SCORES, convert_axis_results, legacy_weakest,
)

#: 每一種預期中的差異，配一句「為什麼它是預期的」。
#: ⚠ 不在這張表上的差異一律算 `UNEXPECTED`——那才是這支腳本的重點。
EXPECTED: dict[str, str] = {
    "weakest_moved_off_source_reliability": (
        "EXPECTED_CHANGE：舊 weakest 是 source_reliability（證據軸）時，新語意會指向"
        "**被證據拖住的那個投資維度**。這正是轉換的目的——舊語意只說「證據不夠」，"
        "新語意說「所以什麼看不清」"
    ),
    "catalyst_is_none": (
        "INTENTIONAL_REMOVAL：Q5 在舊系統沒有任何軸。維持 None 是正確答案；"
        "填預設值會讓「沒有結構化催化劑」看起來像「催化劑很弱」"
    ),
    "earnings_exposure_partial": (
        "EXPECTED_CHANGE：舊 financial_resilience 問「公司撐不撐得住」，"
        "新 Q3 問「對 EPS/FCF 多重要」。缺 segment revenue share（Engine C 無此欄位），"
        "所以帶 partial 標記而不是假裝完整"
    ),
    "evidence_ceiling_applied": (
        "EXPECTED_CHANGE：source_reliability 由「第五個被 min() 的分量」"
        "變成「套在所有維度上的上限」。壓下去的維度帶 evidence_quality_ceiling"
    ),
    "axis_unknown_stays_none": (
        "EXPECTED_CHANGE：舊軸 level=unknown → 新 score 維持 None（不知道），"
        "不填 0（判斷它很弱）"
    ),
}


def main() -> int:
    from decision_lab.bootstrap import open_default_store

    store = open_default_store()
    rows: list[dict] = []
    try:
        cohorts = store.list_operational_cohorts(
            as_of=datetime.now().astimezone().isoformat()
        )
        for cohort in cohorts:
            decision_id = cohort.get("latest_decision_id")
            if not decision_id:
                continue
            decision = store.get_decision(str(decision_id))
            payload = decision.get("payload", decision)
            if isinstance(payload, str):
                payload = json.loads(payload)
            sizing = payload.get("sizing") or {}
            axis_results = sizing.get("axis_results") or {}
            if not axis_results:
                continue
            result = convert_axis_results(
                axis_results, rubric_version=str(sizing.get("rubric_version") or "")
            )
            old_weakest = sizing.get("weakest_axis") or legacy_weakest(axis_results)
            known = [a for a in AXES if result.scores.get(a) is not None]
            new_weakest = (
                min(known, key=lambda a: (result.scores[a].effective, AXES.index(a)))
                if known else None
            )
            ceiling_hits = [
                a for a in known
                if "evidence_quality_ceiling" in (result.scores[a].downgrade_reason or "")
            ]
            rows.append({
                "company": cohort.get("company_id"),
                "old_weakest": old_weakest,
                "old_weakest_maps_to": LEGACY_AXIS_TO_SCORE.get(str(old_weakest)),
                "new_weakest": new_weakest,
                "known": known,
                "unmapped": list(result.unmapped_scores),
                "unmapped_axes": list(result.unmapped_axes),
                "ceiling_hits": ceiling_hits,
                "ceiling": result.evidence_quality.ceiling,
                "partial": list(result.partial_scores),
            })
    finally:
        store.close()

    if not rows:
        print("沒有帶 axis_results 的 cohort——無從對照")
        return 1

    print(f"對照 {len(rows)} 個 operational cohort 的最新 decision\n")
    print(f"{'公司':<32}{'舊 weakest':<24}{'新 weakest':<20}{'已知':<6}{'上限壓制'}")
    print("-" * 96)
    diffs: Counter[str] = Counter()
    unexpected: list[str] = []

    for row in rows:
        ceiling_mark = ",".join(row["ceiling_hits"]) or "-"
        print(f"{str(row['company'])[:31]:<32}{str(row['old_weakest'])[:23]:<24}"
              f"{str(row['new_weakest'])[:19]:<20}{len(row['known'])}/5   {ceiling_mark}")

        if row["old_weakest"] == "source_reliability":
            diffs["weakest_moved_off_source_reliability"] += 1
        elif row["old_weakest_maps_to"] and row["new_weakest"] != row["old_weakest_maps_to"]:
            # 舊 weakest 有對應的新維度，卻不是新 weakest —— 需要解釋
            if row["old_weakest_maps_to"] not in row["known"]:
                diffs["axis_unknown_stays_none"] += 1
            elif row["ceiling_hits"]:
                diffs["evidence_ceiling_applied"] += 1
            else:
                unexpected.append(
                    f"{row['company']}：舊 weakest={row['old_weakest']} "
                    f"→ 應對應 {row['old_weakest_maps_to']}，實際新 weakest="
                    f"{row['new_weakest']}（無上限壓制、該維度已知）"
                )
        if set(row["unmapped"]) & UNMAPPED_SCORES:
            diffs["catalyst_is_none"] += 1
        if row["ceiling_hits"]:
            diffs["evidence_ceiling_applied"] += 1
        if row["partial"]:
            diffs["earnings_exposure_partial"] += 1
        if row["unmapped_axes"]:
            unexpected.append(
                f"{row['company']}：出現對應表沒有的舊軸 {row['unmapped_axes']}"
            )

    # ---- L14 鑑別力量測：舊軸是不是「恆亮」？ ----
    old_dist = Counter(str(r["old_weakest"]) for r in rows)
    new_dist = Counter(str(r["new_weakest"]) for r in rows)
    total = len(rows)
    print("\n=== L14 鑑別力量測（恆亮＝觸發率近 100%＝零鑑別力）===")
    print("舊 weakest_axis 分佈：")
    for name, count in old_dist.most_common():
        print(f"  {count:>3} / {total}  ({count / total:.0%})  {name}")
    print("新 weakest（投資維度）分佈：")
    for name, count in new_dist.most_common():
        print(f"  {count:>3} / {total}  ({count / total:.0%})  {name}")
    top_old = old_dist.most_common(1)[0]
    top_new = new_dist.most_common(1)[0]
    if top_old[1] / total >= 0.7:
        print(
            f"\n🔴 舊 `{top_old[0]}` 佔 {top_old[1] / total:.0%}——依 L14 的三個免 outcome 測試，"
            "\n   這接近**恆亮**：它幾乎總是最弱，於是其他四軸的判斷很少改變結論。"
            "\n   這是把它從『第五個被 min() 的分量』改成『套在所有維度上的上限』的實測依據"
            "\n   ——上限不參與排序，所以不會再吞掉其他維度的訊息。"
        )
    if top_new[1] / total >= 0.7:
        print(
            f"\n⚠ **但新 `{top_new[0]}` 也佔 {top_new[1] / total:.0%}——集中度並沒有消失。**"
            "\n   誠實的結論是：轉換**換了標籤，沒有解決集中**。依同一條 L14 測試，"
            "\n   新 weakest 同樣接近恆亮，所以它目前也不具鑑別力。"
            "\n   差別只在**可行動性**：舊標籤說「證據不夠獨立」，新標籤說「結構這一維看不清」，"
            "\n   後者指得出下一步（補 counter-path）。**那是可讀性的改善，不是鑑別力的改善。**"
            "\n   真正要讓這個數字下降的是 Phase 4／5（補 Q3 的 segment revenue、Q5 的結構化"
            "\n   catalyst），而不是再改一次標籤。"
        )

    print("\n=== semantic diff 分類 ===")
    for key, count in diffs.most_common():
        print(f"  {count:>3}  {key}")
        print(f"       {EXPECTED[key]}")

    print(f"\n=== UNEXPECTED（必須為 0 才算轉換乾淨）：{len(unexpected)} ===")
    for item in unexpected:
        print(f"  ✗ {item}")

    if unexpected:
        print("\n⚠ 存在無法解釋的行為差異——依 §8，不得移除 legacy implementation。")
        return 1
    print("\n✓ 所有差異都可歸類為 EXPECTED_CHANGE／INTENTIONAL_REMOVAL。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
