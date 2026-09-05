"""Session-in-the-loop 的研究模型：**packet builder ＋ judgment 驗證**。

## 這裡沒有 LLM API 呼叫，而且刻意如此

**LLM 就是 session 本身**（Claude Code／Codex），不是一個被呼叫的服務。
這不是省錢的權宜，是這個 repo 已經跑了幾個月、有 268 筆紀錄的既有形狀：

```
decision_lab assessment-scaffold   ← deterministic 取料，判斷欄位刻意留白
        ↓
   session 讀 packet，寫判斷 JSON   ← 零 API 呼叫
        ↓
decision_lab reassess --assessment ← deterministic 驗證引用、凍結
```

四個理由（`target-architecture.md` §6.1）：零成本不依賴 credit；provider-neutral
（Codex 與 Claude Code 可互換，寫死 `anthropic` 會破壞它）；`alpha/` 得以離線測試；
`AGENTS.md`「不值得自己開發」已明文要求長文解讀直接給 Claude 原始 context。

## 分工：session 給判斷，程式給權限

- **session 負責（語意）**：pricing power、switching cost、segment 曝險判讀、
  市場隱含假設 vs 本 thesis 的差異、催化劑辨識、disproof 條件。
- **程式負責（確定性）**：Q1 計分、引用解析、evidence ceiling、schema 驗證、
  排序。**session 提出的引用若解析不到 `ResearchContext` 內的物件，一律 reject。**

L15 的順序不可反：先解析身分，再查權限。**LLM 可以解析與提議，不可以授權。**
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Sequence

from ..contracts import (
    AXES, AlphaSignal, Catalyst, ComponentTrace, DisproofCondition, EvidenceQuality,
    EvidenceRef, ResearchContext, Score,
)
from ..errors import ContractViolation
from ..evidence_quality import assess_evidence_quality
from ..identity import CompanyId, Ticker

MODEL_NAME = "session-assessor"
MODEL_VERSION = "v1"

#: 需要 session 判斷的四個維度。**Q1 不在列上**——它由已入圖的事實確定性算出，
#: 再讓 session 判一次等於在 admission gate 之後開第二個沒有 gate 的入口。
SESSION_AXES: tuple[str, ...] = (
    "value_capture", "earnings_exposure", "expectation_gap", "catalyst",
)

#: 每一軸要 session 回答的具體問題，以及**不得用什麼代替**。
AXIS_PROMPTS: Mapping[str, Mapping[str, str]] = {
    "value_capture": {
        "question": "即使結構上重要，這家公司能不能把重要性轉成 economic rent？",
        "look_at": "定價權、毛利率趨勢、合約結構（take-or-pay／預付款）、"
                   "客戶議價力、ASP、產能紀律、競爭者反應",
        "do_not": "⚠ 不得用「結構重要」代替——structural importance != value capture。"
                  "⚠ 客戶掏錢綁供應商＝真瓶頸；供應商付錢或給股權換訂單＝不是。",
    },
    "earnings_exposure": {
        "question": "這個結構優勢對上市公司的 EPS／FCF 到底有多重要？",
        "look_at": "分部營收占比、毛利貢獻、ASP／量的敏感度、增量利潤率、營運槓桿",
        "do_not": "⚠ **Engine C 沒有 segment revenue 欄位**——若 packet 裡沒有分部資料，"
                  "誠實回 unknown，不要用整體毛利率代替。"
                  "⚠ 同為 sub=5，市值 1.7 兆的公司那塊業務可能只佔 3%。",
    },
    "expectation_gap": {
        "question": "我們預期的未來，跟市場現在 pricing 的未來差多少？",
        "look_at": "packet 的 market_implied_growth；用 variant perception 的操作定義寫："
                   "市場隱含 X／本 thesis 認為 Y／催化劑 Z 會讓市場重新定價",
        "do_not": "⚠ **低本益比不等於 expectation gap。** 便宜可能是市場正確地"
                  "反映了風險。必須說得出「市場現在信什麼」與「為什麼那是錯的」。",
    },
    "catalyst": {
        "question": "是 mispriced，還是 likely to reprice soon？",
        "look_at": "qualification／design win／競爭者退出／產能拐點／重新定價／"
                   "毛利拐點／量產爬坡／庫存反轉／預估調整／法規或技術轉折",
        "do_not": "⚠ 「終究會被發現」不是催化劑。催化劑要有**可觀測的事件與時點**。"
                  "⚠ 舊系統沒有這一軸，所以 packet 裡沒有現成資料——"
                  "找不到具體事件時回 unknown，不要編一個。",
    },
}

_LEVELS: Mapping[str, float | None] = {
    "unknown": None, "weak": 0.25, "moderate": 0.5, "strong": 0.75, "very_strong": 0.9,
}


@dataclass(frozen=True, slots=True)
class JudgmentPacket:
    """給 session 讀的研究包。**純資料，不含任何指示要 session 得出什麼結論。**"""

    ticker: str
    company_id: str
    as_of: str | None
    context_digest: str
    deterministic: Mapping[str, Any]
    evidence_index: Mapping[str, Mapping[str, Any]]
    axis_prompts: Mapping[str, Mapping[str, str]]
    schema: Mapping[str, Any]
    notes: tuple[str, ...]

    def to_json(self) -> str:
        return json.dumps({
            "_how_to_use": (
                "1) 讀 deterministic 與 evidence_index；"
                "2) 對 axis_prompts 的四個問題各給一個判斷；"
                "3) 每個判斷的 evidence 必須是 evidence_index 的 key——"
                "**不在索引裡的引用會被 reject**（L15：先解析身分，再查權限）；"
                "4) 答不出來就填 unknown，**不要猜**——unknown 與 weak 是不同的資訊。"
            ),
            "ticker": self.ticker, "company_id": self.company_id,
            "as_of": self.as_of, "context_digest": self.context_digest,
            "deterministic": self.deterministic,
            "evidence_index": self.evidence_index,
            "axis_prompts": self.axis_prompts,
            "judgment_schema": self.schema,
            "notes": list(self.notes),
        }, ensure_ascii=False, indent=2, default=str)


JUDGMENT_SCHEMA: Mapping[str, Any] = {
    "axes": {
        axis: {
            "level": f"必填，其一：{sorted(_LEVELS)}",
            "reason": "必填，一句話；unknown 時說明缺什麼",
            "evidence": "必填 list（unknown 時可空）；每一項必須是 evidence_index 的 key",
        } for axis in SESSION_AXES
    },
    "direction": "long | short | neutral",
    "confidence": "0..1",
    "expected_horizon": "例 '2-4 quarters'",
    "thesis": "一段話",
    "variant_view": "市場隱含 X／本 thesis 認為 Y／催化劑 Z（三段都要）",
    "bull_case": "…", "base_case": "…", "bear_case": "…",
    "risks": ["…"],
    "catalysts": [{"kind": "見 config/catalyst_kinds.json", "description": "…",
                   "expected_at": "YYYY-MM-DD 或 null",
                   "date_confidence": "confirmed|estimated|unknown"}],
    "disproof_conditions": [{
        "condition": "什麼出現就推翻本 thesis",
        "check_frequency": "L7 必填：多久核查一次",
        "action_within_48h": "L7 必填：觸發後 48 小時內做什麼",
    }],
}


def build_packet(build: Any) -> JudgmentPacket:
    """把 `ContextBuild` 轉成 session 可讀的 packet。"""
    context: ResearchContext = build.context
    evidence_index = {
        ref.ref: {
            "kind": ref.kind, "origin_entity": ref.origin_entity,
            "published_at": ref.published_at.isoformat() if ref.published_at else None,
            "evidence_tier": ref.evidence_tier, "evidence_class": ref.evidence_class,
            "quote": (ref.quote[:160] if ref.quote else None),
        } for ref in context.evidence_refs
    }
    deterministic = {
        "structural_score_q1": (
            None if build.structural is None else {
                "declared": build.structural.declared,
                "effective": build.structural.effective,
                "downgrade_reason": build.structural.downgrade_reason,
                "_note": "Q1 由已入圖的事實確定性算出——**不要重新判斷它**，"
                         "那些判斷已經過 admission gate",
            }
        ),
        "scarcity_inputs": {
            "substitutability": context.structural.substitutability,
            "sole_source": context.structural.sole_source,
            "qualification_status": context.structural.qualification_status,
            "dependency_depth": context.structural.dependency_depth,
            "demand_anchor": str(context.structural.demand_anchor or "") or None,
        },
        "fundamentals": _public(context.fundamentals),
        "market": _public(context.market),
        "consensus": _public(context.consensus),
        "valuation_market_implied": _public(context.valuation),
        # ⚠ context-wide 的證據品質**只是摘要**，不是任何軸的上限——
        # 上限逐軸算（見 compose_signal）。放在這裡是讓 session 知道整體證據厚度。
        "evidence_quality_overview": {
            "level": build.evidence_quality.level,
            "independent_origins": build.evidence_quality.independent_origins,
            "reason": build.evidence_quality.reason,
            "_note": "這是整體摘要；每一軸的上限由該軸自己引用的證據決定",
        },
        "graph_coverage": build.coverage,
        "freshness": {k: {"status": v.status, "as_of": v.as_of, "age_days": v.age_days}
                      for k, v in context.freshness.items()},
    }
    return JudgmentPacket(
        ticker=str(context.ticker),
        company_id=str(context.company_id or ""),
        as_of=context.as_of.isoformat() if context.as_of else None,
        context_digest=context.digest,
        deterministic=deterministic,
        evidence_index=evidence_index,
        axis_prompts=AXIS_PROMPTS,
        schema=JUDGMENT_SCHEMA,
        notes=tuple(build.notes),
    )


def compose_signal(
    build: Any, judgment: Mapping[str, Any], *, allow_stale_context: bool = False,
) -> AlphaSignal:
    """驗證 session 的判斷並組成 `AlphaSignal`。

    **每一個引用都必須解析得到 `ResearchContext` 內的物件，否則 reject。**
    L15：解析時若偏好「能通過的答案」，等於讓引用去尋找能通過的權威——
    那正是 authority laundering。

    `allow_stale_context`（預設 False）：**唯讀 read model 專用**。`True` 時判斷對舊
    context 做的不再 raise，改把 `{"judged_context_digest", "current_context_digest"}`
    寫進 `metadata["context_mismatch"]`——view 要能呈現「有一份舊判斷」而不是把它藏起來，
    但呈現時必須標 stale。引用解析那一關**不因此放寬**：refs 仍必須落在目前 context 內。
    `python -m alpha research --judgment` 維持嚴格（預設值）。
    """
    context: ResearchContext = build.context
    index = {ref.ref: ref for ref in context.evidence_refs}

    # ⚠ 判斷是對**某一份** ResearchContext 做的。context 變了（新的行情、新入圖的邊）
    # 而判斷沒重做時，必須**明說是哪一種失敗**——否則它會退化成「引用不存在」，
    # 看起來像 authority laundering，實際上只是資料更新了（2026-09-04 實測踩到）。
    declared_digest = str(judgment.get("_packet_digest") or "").rstrip("…").strip()
    context_mismatch: dict[str, str] | None = None
    if declared_digest and not context.digest.startswith(declared_digest):
        if not allow_stale_context:
            raise ContractViolation(
                f"judgment 是對 context {declared_digest} 做的，但目前 context 是 "
                f"{context.digest[:24]}——**資料已更新，判斷需要重做**。"
                "這不是引用錯誤，也不得用放寬解析來繞過"
            )
        context_mismatch = {
            "judged_context_digest": declared_digest,
            "current_context_digest": context.digest,
        }

    scores: dict[str, Score | None] = {axis: None for axis in AXES}
    traces: dict[str, ComponentTrace] = {}
    if build.structural is not None:
        scores["structural"] = build.structural
        traces[build.structural.trace_id] = build.structural_trace

    axes_payload = judgment.get("axes")
    if not isinstance(axes_payload, Mapping):
        raise ContractViolation("judgment 缺 axes")
    unknown_axes = set(axes_payload) - set(SESSION_AXES)
    if unknown_axes:
        raise ContractViolation(
            f"judgment 出現非 session 維度：{sorted(unknown_axes)}。"
            "⚠ structural（Q1）由程式算，不接受 session 覆寫——"
            "那會在 admission gate 之後開第二個沒有 gate 的判斷入口"
        )

    # ⚠ **上限逐軸算，不共用一個全域值。**
    # 「這組證據能撐多高」的「這組」必須是**該軸自己引用的那組**。
    # 第一版用 context-wide 的品質當所有軸的上限，於是行情快照的 origin
    # 會參與結構主張的獨立性計數——類別錯誤，且會把好軸拖下水。
    context_quality: EvidenceQuality = build.evidence_quality
    for axis in SESSION_AXES:
        payload = axes_payload.get(axis)
        if not isinstance(payload, Mapping):
            raise ContractViolation(f"judgment.axes 缺 {axis}")
        level = str(payload.get("level") or "")
        if level not in _LEVELS:
            raise ContractViolation(
                f"{axis}.level 未登記：{level!r}；已知 {sorted(_LEVELS)}")
        declared = _LEVELS[level]
        reason = str(payload.get("reason") or "").strip()
        if not reason:
            raise ContractViolation(f"{axis}.reason 不得為空——說不出理由的分數無法被檢查")
        if declared is None:
            continue                       # unknown → None，不是 0

        raw_refs = payload.get("evidence") or []
        if not isinstance(raw_refs, Sequence) or isinstance(raw_refs, str):
            raise ContractViolation(f"{axis}.evidence 必須是 list")
        resolved: list[EvidenceRef] = []
        missing: list[str] = []
        for raw in raw_refs:
            ref = index.get(str(raw))
            (resolved.append(ref) if ref is not None else missing.append(str(raw)))
        if missing:
            raise ContractViolation(
                f"{axis} 引用了不在 ResearchContext 裡的證據：{missing[:3]}。"
                "⚠ 不得放寬解析——那會讓引用去尋找能通過的權威（L15／L8）"
            )
        if not resolved:
            raise ContractViolation(
                f"{axis}.level={level} 但沒有任何 evidence——"
                "算不出來就填 unknown，不要出一個沒有引用的分數（INV-6）"
            )

        axis_quality = assess_evidence_quality(resolved)
        effective, downgrade = axis_quality.apply(declared)
        trace_id = f"ct_{axis}"
        traces[trace_id] = ComponentTrace(
            trace_id=trace_id,
            rule_version=f"{MODEL_NAME}/{MODEL_VERSION}",
            inputs={"session_level": level,
                    "evidence_ceiling": axis_quality.ceiling,
                    "axis_evidence_level": axis_quality.level},
            evidence_refs=tuple(resolved),
            note=reason[:400],
        )
        scores[axis] = Score(declared=declared, effective=round(effective, 4),
                             trace_id=trace_id, downgrade_reason=downgrade)

    disproofs = tuple(
        DisproofCondition(
            condition=str(d.get("condition") or ""),
            check_frequency=str(d.get("check_frequency") or ""),
            action_within_48h=str(d.get("action_within_48h") or ""),
        ) for d in (judgment.get("disproof_conditions") or [])
    )
    catalysts = tuple(
        Catalyst(
            kind=str(c.get("kind") or ""),
            description=str(c.get("description") or ""),
            expected_at=_date_or_none(c.get("expected_at")),
            date_confidence=str(c.get("date_confidence") or "unknown"),  # type: ignore[arg-type]
        ) for c in (judgment.get("catalysts") or [])
    )

    return AlphaSignal(
        ticker=Ticker(str(context.ticker)),
        company_id=CompanyId(str(context.company_id)) if context.company_id else None,
        as_of=context.as_of or date.today(),
        direction=str(judgment.get("direction") or "neutral"),  # type: ignore[arg-type]
        confidence=float(judgment.get("confidence") or 0.0),
        expected_horizon=str(judgment.get("expected_horizon") or "unspecified"),
        thesis=str(judgment.get("thesis") or ""),
        variant_view=str(judgment.get("variant_view") or ""),
        bull_case=str(judgment.get("bull_case") or ""),
        base_case=str(judgment.get("base_case") or ""),
        bear_case=str(judgment.get("bear_case") or ""),
        disproof_conditions=disproofs,
        catalysts=catalysts,
        risks=tuple(str(r) for r in (judgment.get("risks") or [])),
        # 整體摘要，**不是任何軸的閘門**（閘門是逐軸的，見 contracts.py）
        evidence_quality=context_quality,
        evidence_refs=context.evidence_refs,
        model_components=traces,
        research_context_digest=context.digest,
        metadata={
            "model": MODEL_NAME, "model_version": MODEL_VERSION,
            "packet_digest": context.digest,
            # 判斷檔自報的產出日（session 寫的），read model 用它標「判斷是哪天做的」。
            "judged_at": str(judgment.get("_produced_at") or "") or None,
            # None＝判斷就是對目前 context 做的；非 None＝舊判斷（只在 allow_stale_context 下出現）
            "context_mismatch": context_mismatch,
        },
        **{f"{axis}_score": scores[axis] for axis in AXES},
    )


def _public(snapshot: Any) -> dict[str, Any]:
    """把 snapshot 轉成 packet 可讀的 dict，**丟掉 evidence（另有索引）**。"""
    from dataclasses import fields as dc_fields

    return {f.name: getattr(snapshot, f.name) for f in dc_fields(snapshot)
            if f.name != "evidence"}


def _date_or_none(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None
