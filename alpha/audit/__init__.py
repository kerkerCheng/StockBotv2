"""Runtime invariant audit — 骨架。

## 為什麼 Phase 1 就建骨架，即使一個 check 都還沒實作

`historical-failure-matrix.md` 實測：36 筆歷史事故有 **10 筆只有文字保護**。
L14 已經寫過「真正的防呆是會自己出現的常駐計數器，不是要人讀的段落」。
先建註冊表，是為了讓「還沒實作」在**每次執行時現形**，而不是躺在 roadmap 裡。

## 唯一一條 Phase 1 就生效的規則

**未實作的 check 一律回 `SKIPPED`，絕不回 `PASS`。**
L13：成功與未實作若在同一個訊號上同形，讀的人會以為那項健全性有人在管。
`tests/test_layer_separation.py::test_audit_registry_reports_not_implemented_not_pass`
守住這一條。

## 這個 audit 自己也受 INV-5 約束

上線後要能回答「它抓到了幾筆」。長期抓到 0 筆的 check 是**恆滅的閘門**，
鑑別力與恆亮的閘門同樣是零——屆時要嘛拿掉，要嘛明說它只是回歸保險。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Mapping


class AuditStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True, slots=True)
class AuditResult:
    check: str
    status: AuditStatus
    summary: str
    findings: tuple[str, ...] = ()
    reason: str | None = None

    @property
    def ok(self) -> bool:
        return self.status is AuditStatus.PASS


@dataclass(frozen=True, slots=True)
class AuditCheck:
    """一個 invariant check 的登記。

    `owner_phase` 是**哪個 Phase 負責把它從 SKIPPED 變成真的會跑**；
    `invariant` 與 `failures` 讓輸出能直接指回 `historical-failure-matrix.md`。
    """

    name: str
    invariant: str
    failures: tuple[str, ...]
    owner_phase: str
    description: str
    run: Callable[[], AuditResult] | None = None

    def execute(self) -> AuditResult:
        if self.run is None:
            return AuditResult(
                check=self.name,
                status=AuditStatus.SKIPPED,
                summary="not_implemented",
                reason=f"由 {self.owner_phase} 負責實作（{self.invariant}）",
            )
        return self.run()


#: 12 個 check。**新增 check 只加一列；把 `run` 補上就從 SKIPPED 變成真的跑。**
CHECKS: tuple[AuditCheck, ...] = (
    AuditCheck("Identity", "INV-1", ("F-01", "F-04", "F-05"), "Phase 2",
               "registry / graph / Engine C 三側的 company 集合對齊；圖∖registry 必須為 0"),
    AuditCheck("Duplicates", "INV-1", ("F-04",), "Phase 3",
               "alias 碰撞、同公司多 cohort、同 URL 多 SourceDoc"),
    AuditCheck("Lifecycle", "INV-2", ("F-06", "F-07", "F-08"), "Phase 3",
               "禁止 active-but-unreachable／expired-but-active；terminal 動詞語意正確"),
    AuditCheck("Expiry", "INV-2", ("F-15", "F-16"), "Phase 3",
               "每個等待都有到期；watch／RA／cohort expiry 皆可達"),
    AuditCheck("Orphans", "INV-3", ("F-17", "F-20"), "Phase 3",
               "沒有 disposition 的 item；被 filter 掉卻沒有理由的 item"),
    AuditCheck("QueueLiveness", "INV-4", ("F-09", "F-10", "F-11", "F-13"), "Phase 3",
               "queued_without_consumer／watching_without_next_action／"
               "expired_still_scheduled／blocked_without_reason／stalled_over_threshold"),
    AuditCheck("GateDiscrimination", "INV-5", ("F-26",), "Phase 4",
               "每個 gate 的觸發率與清除率——偵測恆亮（近 100%）與恆滅（近 0%）"),
    AuditCheck("PointInTime", "INV-6", ("F-27", "F-28", "F-31"), "Phase 6",
               "as-of fallback 次數必須為 0；published_at／bar_date 覆蓋率"),
    AuditCheck("EvidenceProvenance", "INV-6", ("F-36",), "Phase 2",
               "每個非 None 的 AlphaSignal score 都列得出 EvidenceRef"),
    AuditCheck("GraphFinancialJoin", "INV-1", ("F-03", "F-04"), "Phase 2",
               "A→C join key 兩側對齊；identity 部分缺漏不得靜默關掉整條管線"),
    AuditCheck("AlphaLineage", "INV-6", (), "Phase 2",
               "AlphaSignal.research_context_digest 解析得到實際的 ResearchContext"),
    AuditCheck("DecisionLineage", "INV-6", (), "Phase 3",
               "decision → context bundle digest 解析得到實際的 bundle"),
)

CHECKS_BY_NAME: Mapping[str, AuditCheck] = {c.name: c for c in CHECKS}


def run_all() -> tuple[AuditResult, ...]:
    return tuple(check.execute() for check in CHECKS)


def render(results: tuple[AuditResult, ...]) -> str:
    """fail loudly 的文字輸出。"""
    lines: list[str] = []
    for result in results:
        lines.append(f"{result.status.value:<7} {result.check:<20} {result.summary}")
        for finding in result.findings:
            lines.append(f"          {finding}")
        if result.status is AuditStatus.SKIPPED and result.reason:
            lines.append(f"          ({result.reason})")
    failed = sum(1 for r in results if r.status is AuditStatus.FAIL)
    skipped = sum(1 for r in results if r.status is AuditStatus.SKIPPED)
    lines.append("")
    lines.append(
        f"總計 {len(results)} 項｜FAIL {failed}｜SKIPPED {skipped}"
        f"｜PASS {len(results) - failed - skipped}"
    )
    if skipped:
        lines.append(
            "⚠ SKIPPED 不是 PASS——那些 invariant 目前沒有任何東西在檢查它們。"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    results = run_all()
    print(render(results))
    return 1 if any(r.status is AuditStatus.FAIL for r in results) else 0
