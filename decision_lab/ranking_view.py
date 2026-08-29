"""瓶頸排序輸出——系統的終點。

以股票為單位呈現「哪些標的值得看」，**不給額度**。買多少由使用者在買入前自行判斷。

⚠ 這一層是純轉換：排序本身的唯一權威是 `query/bottleneck.py` 的 `rank_bottlenecks()`，
本模組不重算、不加權、不另建平行排序（R2）。它只負責把那份輸出接上最弱軸與 disproof，
再整理成可讀的股票清單。排序結果由呼叫端注入，因為 `decision_lab` 不得 import neo4j
（架構邊界見 `tests/test_engine_d_runtime.py`）。
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

# 兩份排序回答不同問題，措辭在這裡定死，避免下游各自發明說法而讓它們看起來可互換。
ACTIONABLE_PURPOSE = "現在能投什麼——證據夠強才可行動（evidence 優先於 substitutability）"
STRUCTURAL_PURPOSE = "該去補誰的證據——結構很卡但證據沒跟上，研究 ROI 最高（完全不看證據等級）"

JUDGMENT_NOTE = (
    "這是研究判斷，不是回測結果也不是統計勝率。排序反映目前圖中已抽取的證據與結構，"
    "沒有任何績效驗證。"
)


def _caveats(coverage: Mapping[str, Any]) -> list[str]:
    """沿用排序表既有的限制聲明，不重寫措辭。"""
    notes: list[str] = []
    total = coverage.get("canonical_edges")
    with_sub = coverage.get("edges_with_substitutability")
    share = coverage.get("substitutability_coverage")
    if total and with_sub is not None:
        pct = f"{share:.1%}" if isinstance(share, (int, float)) else "?"
        notes.append(
            f"substitutability 覆蓋 {with_sub}/{total}（{pct}）——排名必然偏向已被抽取過的邊，"
            "沒填的邊是隱形的。"
        )
    self_reported = coverage.get("self_reported_share")
    if isinstance(self_reported, (int, float)):
        notes.append(
            f"其中 {self_reported:.0%} 是供應商自報——升級成客戶端或第三方印證會改變排序。"
        )
    lead_time = coverage.get("edges_with_lead_time")
    if lead_time is not None:
        notes.append(
            f"本排名不含 lead time（有值的邊只有 {lead_time} 條）。「難替代」與「換掉要多久」"
            "是兩件事：第二供應商若半年可合格，sub=5 也很脆。"
        )
    notes.append(
        "documents 是注意力指標，不參與排序——否則分數會變成「我們讀了幾份文件」。"
    )
    return notes


def _entry(
    row: Mapping[str, Any],
    rank: int,
    weakest_axes: Mapping[str, str],
    disproofs: Mapping[str, str],
) -> dict[str, Any]:
    company_id = str(row.get("company_id") or "")
    anchor = row.get("demand_anchor")
    return {
        "rank": rank,
        "ticker": row.get("ticker"),
        "company_id": company_id,
        "relation": row.get("relation"),
        "bottleneck": row.get("bottleneck"),
        "substitutability": row.get("substitutability"),
        "sole_source": bool(row.get("sole_source")),
        "qualification_status": row.get("qualification_status"),
        "evidence": row.get("evidence"),
        "demand_anchor": anchor,
        "demand_hops": row.get("demand_hops"),
        # 無需求錨點者依 alpha 判準不是候選，但要現形而非消失——安靜過濾掉會讓
        # 「為什麼這檔不見了」變成無法回答的問題。
        "no_demand_anchor": anchor is None,
        "weakest_axis": weakest_axes.get(company_id),
        "disproof": disproofs.get(company_id),
    }


def build_ranking_view(
    ranking: Mapping[str, Any],
    *,
    weakest_axes: Mapping[str, str] | None = None,
    disproofs: Mapping[str, str] | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """把 `rank_bottlenecks()` 的輸出整理成以股票為單位的排序視圖。

    `weakest_axes` 與 `disproofs` 以 `co:*` 為鍵。缺項留 None——不猜測，也不用
    「無」之類的字串佔位，那會讓「沒查到」與「確實沒有」變成同一個訊號。
    """
    axes = dict(weakest_axes or {})
    proofs = dict(disproofs or {})

    def _build(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        return [_entry(row, i + 1, axes, proofs) for i, row in enumerate(rows[:limit])]

    actionable_rows = list(ranking.get("rows") or [])
    structural_rows = list(ranking.get("structural_rows") or [])

    return {
        "actionable": _build(actionable_rows),
        "actionable_total": len(actionable_rows),
        "actionable_purpose": ACTIONABLE_PURPOSE,
        "structural": _build(structural_rows),
        "structural_total": len(structural_rows),
        "structural_purpose": STRUCTURAL_PURPOSE,
        # 截斷前的完整候選公司集合。「在不在排序內」必須對整份候選比對，
        # 不能對只帶前 limit 名的 rows 比——否則排 11 名之後的公司會被誤判成
        # 「不在排序」（C-1 常駐清單的消費端踩過的坑）。
        "company_ids": sorted(
            {
                str(row.get("company_id") or "")
                for row in (*actionable_rows, *structural_rows)
                if row.get("company_id")
            }
        ),
        "judgment_note": JUDGMENT_NOTE,
        "caveats": _caveats(ranking.get("coverage") or {}),
    }
