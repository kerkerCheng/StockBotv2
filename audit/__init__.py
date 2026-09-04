"""Runtime invariant audit — 跨層健全性檢查的註冊表。

## 為什麼它在 top level，不在 `alpha/audit/`

Phase 1 把骨架放在 `alpha/audit/`，那是便宜行事。真的要實作就會發現：
這些 check 必須同時讀 registry、Neo4j、Engine C、leads state 與 Decision Store——
而 `FORBIDDEN_IN_ALPHA` 明文禁止 `alpha/` 依賴 `neo4j`／`engine_b`／`decision_lab`／
`query`。**一個讀遍所有層的東西不可能住在 core 裡**，那正是本次重構要建立的
依賴方向（peripheral → core）。

所以 audit 是 **composition root**：它站在所有層之上往下看，不被任何層 import。

## 兩條在 Phase 1 就定下、實作後更重要的規則

**① 未實作的 check 一律回 `SKIPPED`，絕不回 `PASS`。**
L13：成功與未實作若在同一個訊號上同形，讀的人會以為那項健全性有人在管。

**② 「讀不到」也一律 `SKIPPED`，絕不回 `PASS`。**
Neo4j 沒開、DB 不存在、欄位還沒建——這些都是「我看不到」，不是「它沒問題」。
L11-5：**「我找不到」與「它不存在」是兩個不同的 claim。**

## ③ 檢查了 0 筆不得算 PASS（本次實作新增）

`examined == 0` 的 check 回 `SKIPPED("no_data")`。理由是這個 audit 自己也受
INV-5 約束：**一個看了 0 筆資料的檢查，鑑別力與恆滅的閘門一樣是零**，
但它會在報表上顯示成一個綠色的 PASS——那是本 audit 存在要防的形狀本身。
"""
from __future__ import annotations

from dataclasses import dataclass
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
    #: 這次**實際看了幾筆資料**。0 筆的 PASS 是假的（見模組 docstring ③）。
    examined: int = 0

    @property
    def ok(self) -> bool:
        return self.status is AuditStatus.PASS


def ok(check: str, summary: str, examined: int, findings: tuple[str, ...] = ()) -> AuditResult:
    """通過。⚠ `examined == 0` 會自動降級成 SKIPPED——看了 0 筆不算通過。"""
    if examined <= 0:
        return AuditResult(
            check=check, status=AuditStatus.SKIPPED, summary="no_data",
            reason=f"{summary}——但實際檢查了 0 筆，通過與否無從得知",
            examined=0, findings=findings,
        )
    return AuditResult(check=check, status=AuditStatus.PASS, summary=summary,
                       findings=findings, examined=examined)


def fail(check: str, summary: str, findings: tuple[str, ...], examined: int) -> AuditResult:
    return AuditResult(check=check, status=AuditStatus.FAIL, summary=summary,
                       findings=findings, examined=examined)


def skip(check: str, reason: str, summary: str = "unavailable") -> AuditResult:
    """讀不到。**這不是通過**——見模組 docstring ②。"""
    return AuditResult(check=check, status=AuditStatus.SKIPPED, summary=summary,
                       reason=reason, examined=0)


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
        try:
            return self.run()
        except Exception as exc:  # noqa: BLE001 — audit 不得因單一 check 爆掉而整份停擺
            return AuditResult(
                check=self.name, status=AuditStatus.FAIL,
                summary="check_raised",
                findings=(f"{type(exc).__name__}: {exc}",),
                reason="⚠ check 自己爆了。這算 FAIL 不算 SKIPPED——"
                       "一個跑不起來的檢查等於沒有檢查，而它偽裝成有。",
            )


def _registry() -> tuple[AuditCheck, ...]:
    """⚠ 延遲 import：`import audit` 不得把 neo4j／sqlite 連線拉起來。"""
    from audit import checks

    return (
        AuditCheck("Identity", "INV-1", ("F-01", "F-04", "F-05"), "Phase 2",
                   "registry / graph / Engine C 三側的 company 集合對齊；圖∖registry 必須為 0",
                   run=checks.check_identity),
        AuditCheck("Duplicates", "INV-1", ("F-04",), "Phase 3",
                   "alias 碰撞、同公司多 cohort、同 URL 多 SourceDoc",
                   run=checks.check_duplicates),
        AuditCheck("Lifecycle", "INV-2", ("F-06", "F-07", "F-08"), "Phase 3",
                   "禁止 active-but-unreachable／expired-but-active；terminal 動詞語意正確",
                   run=checks.check_lifecycle),
        AuditCheck("Expiry", "INV-2", ("F-15", "F-16"), "Phase 3",
                   "每個等待都有到期；watch／RA／cohort expiry 皆可達",
                   run=checks.check_expiry),
        AuditCheck("Orphans", "INV-3", ("F-17", "F-20"), "Phase 3",
                   "沒有 disposition 的 item；被 filter 掉卻沒有理由的 item",
                   run=checks.check_orphans),
        AuditCheck("QueueLiveness", "INV-4", ("F-09", "F-10", "F-11", "F-13"), "Phase 3",
                   "queued_without_consumer／watching_without_next_action／"
                   "expired_still_scheduled／blocked_without_reason／stalled_over_threshold",
                   run=checks.check_queue_liveness),
        AuditCheck("GateDiscrimination", "INV-5", ("F-26",), "Phase 4",
                   "每個 gate 的觸發率與清除率——偵測恆亮（近 100%）與恆滅（近 0%）"),
        AuditCheck("PointInTime", "INV-6", ("F-27", "F-28", "F-31"), "Phase 6",
                   "as-of fallback 次數必須為 0；published_at／bar_date 覆蓋率"),
        AuditCheck("EvidenceProvenance", "INV-6", ("F-36",), "Phase 2",
                   "每個非 None 的 AlphaSignal score 都列得出 EvidenceRef",
                   run=checks.check_evidence_provenance),
        AuditCheck("GraphFinancialJoin", "INV-1", ("F-03", "F-04"), "Phase 2",
                   "A→C join key 兩側對齊；identity 部分缺漏不得靜默關掉整條管線",
                   run=checks.check_graph_financial_join),
        AuditCheck("AlphaLineage", "INV-6", (), "Phase 2",
                   "AlphaSignal.research_context_digest 解析得到實際的 ResearchContext",
                   run=checks.check_alpha_lineage),
        AuditCheck("DecisionLineage", "INV-6", (), "Phase 3",
                   "decision → context bundle digest 解析得到實際的 bundle",
                   run=checks.check_decision_lineage),
    )


def all_checks() -> tuple[AuditCheck, ...]:
    return _registry()


def run_all(only: str | None = None) -> tuple[AuditResult, ...]:
    checks = all_checks()
    if only:
        wanted = {n.strip().lower() for n in only.split(",") if n.strip()}
        checks = tuple(c for c in checks if c.name.lower() in wanted)
        if not checks:
            names = ", ".join(c.name for c in all_checks())
            raise SystemExit(f"沒有這個 check：{only}。可用：{names}")
    return tuple(check.execute() for check in checks)


def render(results: tuple[AuditResult, ...]) -> str:
    """fail loudly 的文字輸出。"""
    lines: list[str] = []
    for result in results:
        seen = f"[{result.examined} 筆]" if result.examined else ""
        lines.append(
            f"{result.status.value:<7} {result.check:<20} {result.summary} {seen}".rstrip())
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
        f"｜共檢查 {sum(r.examined for r in results)} 筆"
    )
    if skipped:
        lines.append(
            "⚠ SKIPPED 不是 PASS——那些 invariant 目前沒有任何東西在檢查它們。"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m audit", description="runtime invariant audit")
    parser.add_argument("what", nargs="?", default="invariants", choices=("invariants",))
    parser.add_argument("--only", help="只跑指定 check（逗號分隔）")
    parser.add_argument("--json", action="store_true", help="輸出機器可讀 JSON")
    args = parser.parse_args(argv)

    results = run_all(args.only)
    if args.json:
        import json

        print(json.dumps([{
            "check": r.check, "status": r.status.value, "summary": r.summary,
            "examined": r.examined, "findings": list(r.findings), "reason": r.reason,
        } for r in results], ensure_ascii=False, indent=2))
    else:
        print(render(results))
    return 1 if any(r.status is AuditStatus.FAIL for r in results) else 0


#: 相容別名——`historical-failure-matrix.md` 與測試都用 `CHECKS`。
#: ⚠ 這是 property-like 呼叫而不是常數，因為建構它需要延遲 import checks。
def CHECKS_BY_NAME() -> Mapping[str, AuditCheck]:  # noqa: N802
    return {c.name: c for c in all_checks()}
