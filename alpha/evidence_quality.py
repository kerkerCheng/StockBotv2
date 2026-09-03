"""`source_reliability` 的新家：它是 **meta 軸**，不是第六個 score。

## 為什麼不能直接搬成第六個維度

舊系統的五軸是 `source_reliability`／`technical_causal_link`／`commercial_maturity`／
`financial_resilience`／`valuation_payoff`，用 `min()` 取最弱。新系統的五個 score 是
prompt §6 的五個**投資問題**（結構稀缺／價值攫取／盈餘曝險／預期落差／催化劑）。

**`source_reliability` 不是一個投資問題，它是「你憑什麼相信前面那些答案」。**
2026-09-03 用 COHR 真實資料映射時實測到這件事：其他四軸都找得到對應的投資問題，
只有它找不到。硬塞成第六個維度會產生一個奇怪的東西——一個與標的好壞無關、卻和
其他四個並列參與排序的分量。

## 正確的形狀：它是**上限**，不是分量

證據品質限定的是「這組證據**能撐多高**」，而那對每一個維度都成立。
所以它從「第五個被 `min()` 的分量」變成「套在所有維度上的 ceiling」。

- 舊語意：`weakest = min(五軸)`；若 `source_reliability` 最弱，它就是 weakest。
- 新語意：`effective = min(declared, evidence_ceiling)`；被壓下去的維度帶
  `downgrade_reason="evidence_quality_ceiling"`。

**兩者的排序結果在單調情況下等價**，但新語意多回答了一個問題：
**是哪一個投資維度被證據拖住了**——舊語意只會說「證據不夠」，不會說「所以什麼看不清」。

## L8 的門檻直接沿用，不另創

`AGENTS.md` L8：多文件入圖前至少 **3 個不同 `origin_entity`**；供應商自報不算獨立佐證；
某條 `sole_source=true` 的邊若所有 source 的 `origin_entity` 都是同一家供應商 → 標 weak。
下面的三階對應就是把那條規則寫成程式，**沒有新增任何門檻**。
"""
from __future__ import annotations

from typing import Sequence

from .contracts import EvidenceQuality, EvidenceRef
from .levels import LEVEL_SCALE_VERSION

#: L8 的獨立來源門檻。**沿用既有規則，不是新發明的數字。**
INDEPENDENT_ORIGINS_FOR_CORROBORATED = 3
INDEPENDENT_ORIGINS_FOR_BOUNDED = 2

CEILING_REASON = "evidence_quality_ceiling"


def assess_evidence_quality(refs: Sequence[EvidenceRef]) -> EvidenceQuality:
    """由一組 `EvidenceRef` 導出證據品質。

    **獨立性只在不同 `origin_entity` 之間累加**——同一場法說會的多份摘要、
    同一則 PR 被多家媒體轉發，算一個來源不是多重佐證（`schema/graph_schema.md` §6）。
    ⚠ 沒有 `origin_entity` 的引用**不計入**獨立來源，也不因此被丟掉：
    它仍在 `total_refs` 裡，只是不能替獨立性背書（L11-5 的同一形狀）。
    """
    origins = {
        str(ref.origin_entity).strip().casefold()
        for ref in refs
        if ref.origin_entity and str(ref.origin_entity).strip()
    }
    # `corroborating_origins` 是研究者明確登記的其他獨立來源，一併計入
    for ref in refs:
        origins.update(
            str(origin).strip().casefold()
            for origin in ref.corroborating_origins
            if str(origin).strip()
        )
    tiers = [ref.evidence_tier for ref in refs if ref.evidence_tier is not None]
    best_tier = min(tiers) if tiers else None
    count = len(origins)

    if count >= INDEPENDENT_ORIGINS_FOR_CORROBORATED:
        level = "corroborated"
        reason = f"{count} 個獨立 origin_entity（L8 門檻 {INDEPENDENT_ORIGINS_FOR_CORROBORATED}）"
    elif count >= INDEPENDENT_ORIGINS_FOR_BOUNDED:
        level = "bounded_hypothesis"
        reason = f"僅 {count} 個獨立 origin_entity，未達 L8 的獨立佐證門檻"
    else:
        level = "unknown"
        reason = (
            "0 個可辨識的獨立 origin_entity——單一來源自報不構成佐證（L8）"
            if count == 0 else
            "僅 1 個 origin_entity；供應商自報不能當作『自己是瓶頸』的獨立佐證（L8）"
        )
    return EvidenceQuality(
        level=level,
        independent_origins=count,
        best_tier=best_tier,
        total_refs=len(refs),
        reason=reason,
    )


def from_legacy_level(level: str, reason: str) -> EvidenceQuality:
    """從舊 `source_reliability` 軸直接建立（讀歷史 payload 用）。

    舊 payload 的 level 是研究者當時的判斷，**比重新從引用推導更可信**——
    它看得到當時的完整脈絡。轉換時沿用它，不重算（避免用今天的圖去改寫當時的判斷）。
    """
    return EvidenceQuality(
        level=level,
        independent_origins=-1,       # -1 ＝ 未重算，沿用當時判斷
        best_tier=None,
        total_refs=0,
        reason=f"沿用舊 source_reliability 軸：{reason[:200]}",
    )
