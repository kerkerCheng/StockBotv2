"""列出各信心軸有哪些合格引用可用——寫 assessment 之前該查的東西。

事發（2026-08-14）：Lumentum 與 AXT 兩筆 reassess 的 live 區間都是 0，成因不是
證據不足、不是風控、也不是研究不完整，而是 `assessment_context_mismatch`——
assessment 引用的字串和 `reference_index` 的 key 對不上。其中最刺眼的一筆，兩邊
指的是**同一份 10-Q、同一個 SEC accession**，只因為一邊寫 `filed 2026-05-06`、
另一邊寫 `Note 17, …, https://…`，分歧落在字串中段，exact／trailing-slash／
unique-prefix 三種解析全部不命中，整筆決策資本歸零。

L15 的判準是「gate 攔下的若是格式而不是風險，該修的是它問問題的方式」。這裡選擇
**在源頭消除歧義**而不是在事後放寬比對：解析規則一個字都不動，因此也沒有「引用去
尋找能通過的權威」的空間；寫 assessment 的人只是終於看得到有哪些 key 可以引用。
"""
from __future__ import annotations

from typing import Any, Mapping

from .sizing import describe_axis_references, diagnose_assessment_references
from .store import DecisionStore


def _resolve_context(store: DecisionStore, target_id: str) -> Any:
    """target 可以是 decision_id 或 cohort_id；兩者都回到同一份 frozen context。"""

    decision: Mapping[str, Any] | None = None
    try:
        decision = store.get_decision(target_id)
    except KeyError:
        decision = store.latest_decision_for_cohort(target_id)
    if decision is None:
        raise KeyError(f"找不到 decision 或 cohort：{target_id}")
    digest = decision.get("context_digest")
    if not isinstance(digest, str) or not digest:
        raise KeyError(f"decision 沒有 context_digest：{target_id}")
    return decision, store.get_context_bundle(digest)


def build_reference_options(
    store: DecisionStore,
    target_id: str,
    *,
    assessment: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    decision, bundle = _resolve_context(store, target_id)
    index = bundle.payload.get("reference_index") or {}
    result: dict[str, Any] = {
        "target_id": target_id,
        "cohort_id": bundle.cohort_id,
        "decision_id": decision.get("decision_id"),
        "context_digest": bundle.digest,
        "evaluation_at": bundle.evaluation_at,
        "reference_index_size": len(index),
        "axes": {
            axis: [dict(row) for row in rows]
            for axis, rows in describe_axis_references(index).items()
        },
    }
    if assessment is not None:
        result["diagnosis"] = diagnose_assessment_references(assessment, index)
    return result


def render_reference_options_markdown(payload: Mapping[str, Any]) -> str:
    lines = [
        f"# 可用引用 — {payload.get('cohort_id')}",
        "",
        f"- context：`{payload.get('context_digest')}`（frozen {payload.get('evaluation_at')}）",
        f"- reference_index 共 {payload.get('reference_index_size')} 筆",
        "",
        "> 這是**最近一次凍結**的 index。reassess 會重新 freeze，來源集合可能變動；",
        "> 引用請整串複製，字面必須完全一致。",
        "",
    ]
    diagnosis = payload.get("diagnosis") or {}
    for axis, rows in (payload.get("axes") or {}).items():
        report = diagnosis.get(axis) or {}
        accepts = "、".join(report.get("accepts_authorities") or ()) or "—"
        lines.append(f"## {axis}")
        lines.append(f"接受 authority：{accepts}")
        if not rows:
            lines.append("")
            lines.append("⚠ **這一軸在本次 context 沒有任何合格引用**——不是引用寫錯，")
            lines.append("是上游根本沒有產出該 authority。改引用救不了，需要補上游資料。")
            lines.append("")
            continue
        lines.append("")
        for row in rows:
            lines.append(f"- `{row['reference']}`")
            lines.append(f"    authorities：{'、'.join(row['authorities'])}")
        lines.append("")
        if report:
            if report.get("would_zero_out"):
                lines.append(
                    f"❌ 目前的 assessment 在這一軸 accepted = 0 → 會被改寫成 "
                    f"`unknown`、ceiling 歸零（宣告的是 `{report.get('declared_level')}`）。"
                )
            elif report.get("accepted_refs"):
                lines.append(
                    f"✅ 目前有 {len(report['accepted_refs'])} 個合格引用，這一軸不歸零。"
                )
            for rejected in report.get("rejected_refs") or ():
                why = rejected.get("why")
                if why == "unresolved":
                    lines.append(f"  - ✗ `{rejected['reference']}` — 解析不到任何 key")
                else:
                    lines.append(
                        f"  - ✗ `{rejected['reference']}` — 解析到 "
                        f"`{rejected.get('resolved_to')}`，但 authority 是 "
                        f"{'、'.join(rejected.get('authorities') or ())}，這一軸不接受"
                    )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"
