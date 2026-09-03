"""突變測試：證明 `alpha/` 的斷言**不是空跑**。

## 為什麼需要這支

Phase 1 是純新增，沒有任何現有數字會變（L14 的誠實答案）。所以它**不得用
「行為沒壞」當驗收**——那是恆真的。替代驗收是：
**每條新斷言都要做過「故意違規 → 確認會紅」的檢查。**

2026-08-28 的教訓：U2 宣稱「零行為變化的純重構」，若當時只寫在 commit message，
錯誤會原封不動進 master；因為寫成了 characterization 測試，它三分鐘後就自己打臉。
這支腳本把那個做法自動化——**手動做一次會忘記，做成腳本才會在每次重構後重跑**。

## 做法

對每個 mutation：改一行原始碼 → 跑指定測試 → **斷言它變紅** → 還原。
若某個 mutation 之後測試仍然綠，代表那條斷言守不住它宣稱要守的東西。

用法：
    python scripts/verify_test_nonvacuity.py           # 全部
    python scripts/verify_test_nonvacuity.py --list    # 只列出突變
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Mutation:
    """一個「故意違規」。

    `guards` 是它應該讓哪條測試變紅——寫出來是為了讓「守衛與被守的東西」
    這層對應關係本身可稽核。
    """

    name: str
    path: str
    old: str
    new: str
    test: str
    guards: str


MUTATIONS: tuple[Mutation, ...] = (
    Mutation(
        name="AlphaSignal 長出部位欄位",
        path="alpha/contracts.py",
        old="    direction: Literal[\"long\", \"short\", \"neutral\"]\n    confidence: float\n    expected_horizon: str",
        new="    direction: Literal[\"long\", \"short\", \"neutral\"]\n    confidence: float\n    target_weight: float = 0.0\n    expected_horizon: str",
        test="tests/test_alpha_contracts.py",
        guards="AlphaSignal != Position（import 時的 shape guard）",
    ),
    Mutation(
        name="AlphaSignal 長出 scalar 總分",
        path="alpha/contracts.py",
        old="    direction: Literal[\"long\", \"short\", \"neutral\"]\n    confidence: float",
        new="    direction: Literal[\"long\", \"short\", \"neutral\"]\n    value: float = 0.0\n    confidence: float",
        test="tests/test_alpha_contracts.py",
        guards="v1 不產生加權總分（2026-08-21 pq1 補償性）",
    ),
    Mutation(
        name="把 None 當 0 參與排序",
        path="alpha/contracts.py",
        old="    if score is None:\n        return math.inf\n    return -float(score.effective)",
        new="    if score is None:\n        return 0.0\n    return -float(score.effective)",
        test="tests/test_alpha_contracts.py::test_none_is_not_zero",
        guards="None（不知道）≠ 0.0（判斷它很弱）",
    ),
    Mutation(
        name="排序改讀 declared 而非 effective",
        path="alpha/contracts.py",
        old="    return -float(score.effective)",
        new="    return -float(score.declared)",
        test="tests/test_alpha_contracts.py::test_tiebreak_uses_effective_not_declared",
        guards="F-25：宣告值與生效值分開，排序的 tie-break 分量用生效值",
    ),
    Mutation(
        name="weakest 改讀 declared",
        path="alpha/contracts.py",
        old="        return min(known, key=lambda a: (self.score_for(a).effective, AXES.index(a)))",
        new="        return min(known, key=lambda a: (self.score_for(a).declared, AXES.index(a)))",
        test="tests/test_alpha_contracts.py::test_weakest_uses_effective_not_declared",
        guards="F-25 的第二個出口：weakest（該補什麼）也不得讀宣告值",
    ),
    Mutation(
        name="RankedList 成員判斷改讀截斷後的 rows",
        path="alpha/contracts.py",
        old="        return str(identifier) in set(self.full_ids)",
        new="        return str(identifier) in set(self.row_ids)",
        test="tests/test_alpha_contracts.py::test_ranked_list_membership_reads_full_ids_not_rows",
        guards="F-20：截斷集合被當成全集",
    ),
    Mutation(
        name="Score 允許無理由的降級",
        path="alpha/contracts.py",
        old="        if self.effective < self.declared and not self.downgrade_reason:",
        new="        if False and self.effective < self.declared and not self.downgrade_reason:",
        test="tests/test_alpha_contracts.py::test_downgrade_requires_a_reason",
        guards="L12：因果不得被截斷",
    ),
    Mutation(
        name="DisproofCondition 不要求 48 小時動作",
        path="alpha/contracts.py",
        old="        _nonempty(\n            self.action_within_48h,",
        new="        _skip = lambda *a, **k: None\n        _skip(\n            self.action_within_48h,",
        test="tests/test_alpha_contracts.py::test_disproof_requires_frequency_and_action",
        guards="L7：欄位有填但沒有後續流程＝永遠不會響的火警警報",
    ),
    Mutation(
        name="未標日期的證據被當成在 T 之前",
        path="alpha/contracts.py",
        old="        if ref.published_at is None:\n            undated.append(ref)",
        new="        if ref.published_at is None:\n            kept.append(ref)",
        test="tests/test_alpha_point_in_time.py::test_missing_published_at_is_excluded_and_counted",
        guards="L11-5：「我找不到」≠「它不存在」",
    ),
    Mutation(
        name="provider 不支援 as-of 時靜默回傳當前資料",
        path="alpha/testing.py",
        old="        if as_of is not None and not self.supports_as_of:\n            raise PointInTimeUnsupported(",
        new="        if False and as_of is not None and not self.supports_as_of:\n            raise PointInTimeUnsupported(",
        test="tests/test_alpha_point_in_time.py::test_as_of_raises_when_unsupported",
        guards="L13：成功與失敗不得在同一個訊號上同形（Phase 6 的保險絲）",
    ),
    Mutation(
        name="因果 confidence 改取平均",
        path="alpha/causal.py",
        old="        return min(self.link_confidences, key=lambda c: c.value)",
        new="        avg = sum(c.value for c in self.link_confidences) / len(self.link_confidences)\n        return min(ImpactConfidence, key=lambda c: abs(c.value - avg))",
        test="tests/test_alpha_causal.py::test_causal_confidence_is_weakest_link",
        guards="補償性：三段強＋一段沒證據 ≠ 可靠",
    ),
    Mutation(
        name="CompanyImpact 允許非 derived（可入圖）",
        path="alpha/causal.py",
        old="        if not self.derived:",
        new="        if False and not self.derived:",
        test="tests/test_alpha_causal.py::test_company_impact_is_always_derived",
        guards="多跳推論不得混進圖的事實層",
    ),
    Mutation(
        name="audit 未實作卻回 PASS",
        path="alpha/audit/__init__.py",
        old="                status=AuditStatus.SKIPPED,\n                summary=\"not_implemented\",",
        new="                status=AuditStatus.PASS,\n                summary=\"not_implemented\",",
        test="tests/test_layer_separation.py::test_audit_registry_reports_not_implemented_not_pass",
        guards="L13：未實作不得偽裝成通過",
    ),
    Mutation(
        name="alpha 依賴 Neo4j",
        path="alpha/contracts.py",
        old="import hashlib\nimport json",
        new="import hashlib\nimport json\nimport neo4j  # noqa: F401",
        test="tests/test_layer_separation.py::test_alpha_has_no_external_or_engine_dependencies",
        guards="alpha/ 零外部相依",
    ),
    Mutation(
        name="alpha 出現 Cypher",
        path="alpha/provider.py",
        old="_ROOT_MARKER = None" if False else "PROVIDER_METHODS: tuple[str, ...] = (",
        new="_LEAK = \"MATCH (n:Entity) RETURN n\"\nPROVIDER_METHODS: tuple[str, ...] = (",
        test="tests/test_layer_separation.py::test_cypher_stays_out_of_alpha",
        guards="Cypher 的家是 query/，不是 alpha/",
    ),
    Mutation(
        name="Engine D 反向 import alpha",
        path="decision_lab/bootstrap.py",
        old="\"\"\"建立本機 private Decision Store。\"\"\"",
        new="\"\"\"建立本機 private Decision Store。\"\"\"\nimport alpha  # noqa: F401",
        test="tests/test_layer_separation.py::test_decision_lab_does_not_import_new_layers",
        guards="依賴方向：Engine D 是下游，不呼叫 Alpha Research",
    ),
    Mutation(
        name="source_reliability 被當成第六個 score",
        path="alpha/legacy_axes.py",
        old='    "source_reliability": None,          # meta 軸 → EvidenceQuality',
        new='    "source_reliability": "catalyst",    # meta 軸 → EvidenceQuality',
        test="tests/test_alpha_legacy_conversion.py::test_source_reliability_maps_to_nothing_on_purpose",
        guards="它不是投資問題，是套在所有維度上的上限——不得參與排序",
    ),
    Mutation(
        name="catalyst 沒有來源時填預設值",
        path="alpha/legacy_axes.py",
        old="UNMAPPED_SCORES: frozenset[str] = frozenset({\"catalyst\"})",
        new="UNMAPPED_SCORES: frozenset[str] = frozenset()",
        test="tests/test_alpha_legacy_conversion.py::test_catalyst_has_no_legacy_source",
        guards="「沒有結構化催化劑」不得看起來像「催化劑很弱」",
    ),
    Mutation(
        name="證據品質上限不套用",
        path="alpha/contracts.py",
        old="        return self.ceiling, \"evidence_quality_ceiling\"",
        new="        return declared, None",
        test="tests/test_alpha_legacy_conversion.py::test_weak_source_reliability_caps_every_dimension",
        guards="L8：供應商自報不能撐起外部印證等級的結論",
    ),
    Mutation(
        name="earnings_exposure 假裝是完整轉換",
        path="alpha/legacy_axes.py",
        old='PARTIAL_SCORES: Mapping[str, str] = {\n    "earnings_exposure": (',
        new='PARTIAL_SCORES: Mapping[str, str] = {\n    "earnings_exposure_DISABLED": (',
        test="tests/test_alpha_legacy_conversion.py::test_earnings_exposure_is_marked_partial",
        guards="舊軸問「撐不撐得住」，新 Q3 問「對 EPS/FCF 多重要」——不是同一件事",
    ),
    Mutation(
        name="golden fixture 少一類",
        path="tests/test_golden_fixtures.py",
        old='    "truncation_boundary": "F-20",\n',
        new="",
        test="tests/test_golden_fixtures.py::test_all_fourteen_classes_are_present",
        guards="14 類全在場——少一類代表某個歷史事故的 frozen input 不存在",
    ),
    Mutation(
        name="tracked golden fixture 混入金額",
        path="tests/fixtures/golden/normal_company.json",
        old='  "note":',
        new='  "nav_base": 123456.78,\n  "note":',
        test="tests/test_golden_fixtures.py::test_tracked_fixtures_carry_no_monetary_values",
        guards="private authority（NAV／部位金額）永不進 Git",
    ),
    Mutation(
        name="新增第 6 個 core → mcp_server 消費端",
        path="identity/registry.py",
        old="from __future__ import annotations",
        new="from __future__ import annotations\nimport mcp_server  # noqa: F401",
        test="tests/test_layer_separation.py::test_core_does_not_import_mcp_server",
        guards="依賴方向只准 peripheral → core（allowlist 擋新增）",
    ),
)


def _write(path: Path, text: str, *, attempts: int = 5) -> None:
    """原子寫入 ＋ 重試。

    ⚠ 第一版直接用 `path.write_text()`，在 Windows 上被剛結束的 pytest 子行程
    短暫鎖住而拋 `OSError: [Errno 22]`，**於是把一個突變留在了原始碼裡**——
    測試套件當場多一條紅，而原因看起來完全無關。
    突變工具自己造成永久損壞是最糟的失敗模式，所以還原必須是原子的、會重試的，
    而且結束後要 **verify**。
    """
    tmp = path.with_suffix(path.suffix + ".mutbak")
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, path)
            return
        except OSError as exc:  # pragma: no cover - 平台相依
            last = exc
            time.sleep(0.2 * (attempt + 1))
    tmp.unlink(missing_ok=True)
    raise RuntimeError(f"無法還原 {path}：{last}")


def _run(test: str) -> bool:
    """回傳測試是否通過。

    ⚠ **每次都用全新的 bytecode 快取目錄。**
    第一版沒有這樣做，結果工具本身出現**偽陰性**：每跑一次就有一條不同的斷言被
    報成「空跑」，而手動重現時它明明會紅。成因是 Python 的 pyc 失效判準是
    `(source_mtime_秒, source_size)`——`os.replace` 保留來源檔的 mtime，
    而相鄰兩個突變若讓 `alpha/contracts.py` 大小相同又落在同一秒，
    直譯器就沿用上一輪的 bytecode，**新突變根本沒被載入**。

    這個 bug 的形狀正是它自己要防的東西：一個看起來在檢查、實際上沒在檢查的檢查。
    """
    env = dict(os.environ)
    env["PYTHONPYCACHEPREFIX"] = tempfile.mkdtemp(prefix="mutcache-")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", *test.split(), "-q", "--no-header",
             "-p", "no:cacheprovider"],
            cwd=ROOT, capture_output=True, text=True, env=env,
        )
        return result.returncode == 0
    finally:
        shutil.rmtree(env["PYTHONPYCACHEPREFIX"], ignore_errors=True)


def verify(mutation: Mutation) -> tuple[bool, str]:
    path = ROOT / mutation.path
    original = path.read_text(encoding="utf-8")
    if mutation.old not in original:
        return False, "突變錨點在原始碼中找不到（程式已改？請更新本腳本）"
    _write(path, original.replace(mutation.old, mutation.new, 1))
    try:
        still_green = _run(mutation.test)
    finally:
        _write(path, original)
        assert path.read_text(encoding="utf-8") == original, f"{path} 還原後仍不一致"
    if still_green:
        return False, "突變後測試仍然綠——這條斷言守不住它宣稱要守的東西"
    return True, "突變後測試變紅"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="只列出突變，不執行")
    args = parser.parse_args()

    if args.list:
        for mutation in MUTATIONS:
            print(f"{mutation.name:<40s} → {mutation.test}")
            print(f"{'':<42s}守：{mutation.guards}")
        return 0

    failures: list[str] = []
    for index, mutation in enumerate(MUTATIONS, 1):
        ok, detail = verify(mutation)
        mark = "✓" if ok else "✗"
        print(f"{mark} [{index:2d}/{len(MUTATIONS)}] {mutation.name}")
        print(f"        守：{mutation.guards}")
        print(f"        {detail}")
        if not ok:
            failures.append(f"{mutation.name}：{detail}")

    print()
    print(f"總計 {len(MUTATIONS)} 個突變｜通過 {len(MUTATIONS) - len(failures)}"
          f"｜**空跑 {len(failures)}**")
    if failures:
        print("\n⚠ 以下斷言是空跑，必須修：")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("所有斷言都被證明會紅——它們守得住自己宣稱要守的東西。")
    # 收尾完整性檢查：突變工具自己不得留下任何殘留
    if not _run("tests/test_alpha_contracts.py tests/test_alpha_causal.py "
                "tests/test_alpha_point_in_time.py tests/test_alpha_provider_contract.py "
                "tests/test_alpha_real_fixtures.py tests/test_layer_separation.py"):
        print("⚠ 收尾檢查失敗——有突變未被還原乾淨")
        return 1
    print("收尾完整性檢查通過：原始碼已還原乾淨。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
