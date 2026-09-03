"""層邊界的 import 掃描。

這一組守的是**依賴方向**，而依賴方向是這次重構最容易在不知不覺中壞掉的東西——
壞掉時沒有任何測試會紅，只會多一條 import，然後三個月後發現 `alpha/` 需要 Neo4j
才能跑單元測試。

每條斷言都附「空跑檢查」的做法：故意加一行違規的 import，確認它會紅。
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from alpha import audit

ROOT = Path(__file__).resolve().parents[1]

#: 新架構的三個 package。
NEW_LAYERS = ("alpha", "portfolio", "risk")

#: 掃描範圍：所有 first-party package（不含 tests 與 .venv）。
CORE_PACKAGES = (
    "alpha", "portfolio", "risk", "decision_lab", "engine_b", "engine_c",
    "engine_d_runtime", "query", "loader", "thesis", "identity", "storage",
    "fetchers", "notifications", "crons", "scripts",
)

#: ⚠ `mcp_server` 的**已知例外**。實測（2026-09-03）：`mcp_server/` 4,016 行有 79%
#: 不是 MCP，而是被關在 transport package 裡的 domain——因此這 5 個 core 消費端
#: 被迫 import 它，其中包含 pq2 待辦池本身。
#:
#: **Phase 3 的驗收條件是這個集合變成空的。** 在那之前它是一份會被讀到的欠債清單，
#: 而不是一條被關掉的檢查——新增第 6 個消費端會讓測試紅。
KNOWN_MCP_CONSUMERS = frozenset({
    "engine_b/todo.py",
    "query/health_audit.py",
    "crons/weekly_scan_digest.py",
    "scripts/commit_pending_intake.py",
    "scripts/prepare_research_action.py",
})

#: Cypher 偵測。⚠ **刻意大小寫敏感，且前面不得是 `.`**——第一版用 IGNORECASE，
#: 結果把 `alpha/identity.py` 的 `_ENTITY_RE.match(` 判成 Cypher `MATCH (`。
#: 那是本 session 第二次「gate 攔下的是格式而不是風險」（L15），修法一樣是
#: **改它問問題的方式**：本 repo 的 Cypher 常數一律大寫，Python 的方法呼叫一律小寫且帶 `.`。
_CYPHER = re.compile(r"(?<![.\w])(MATCH|MERGE|OPTIONAL MATCH)\s*\(")


def _python_files(package: str) -> list[Path]:
    root = ROOT / package
    if not root.exists():
        return []
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


def _imported_roots(path: Path) -> set[str]:
    """該檔 import 了哪些 top-level 模組（含函式內的延遲 import）。"""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:  # pragma: no cover - 不應發生
        pytest.fail(f"{path} 無法解析")
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module)
    return roots


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


# ---------------------------------------------------------------------------
# 1. alpha/ 是純的
# ---------------------------------------------------------------------------

FORBIDDEN_IN_ALPHA = (
    "neo4j", "yfinance", "anthropic", "decision_lab", "engine_c", "engine_b",
    "engine_d_runtime", "mcp_server", "loader", "query", "thesis", "fetchers",
    "portfolio", "risk", "requests", "pandas",
)


#: **唯一允許碰外部世界的 `alpha/` 子套件。**
#: Phase 1 的測試 docstring 已預告：「Phase 2 的 concrete provider 住
#: `alpha/providers/`，屆時本條要**明確加例外，不是整條刪掉**」——現在兌現。
#: `alpha/contracts.py`／`causal.py`／`identity.py` 永遠不該需要資料庫。
ALPHA_IO_SUBPACKAGE = "alpha/providers/"

#: `alpha/cli.py` 允許 import `identity`——ticker → CompanyId 必須經 registry
#: 解析而不是用猜的（INV-1／F-01）。這是**窄**例外，不是把 cli 排除在檢查外。
ALPHA_IDENTITY_CONSUMERS = frozenset({"alpha/cli.py"})


def test_alpha_core_has_no_external_or_engine_dependencies() -> None:
    """`alpha/` 的**契約與模型層**維持零外部相依（要能離線測試）。

    空跑檢查：在 `alpha/contracts.py` 加一行 `import neo4j` → 這條會紅。
    """
    offenders: list[str] = []
    for path in _python_files("alpha"):
        rel = _rel(path)
        if rel.startswith(ALPHA_IO_SUBPACKAGE):
            continue
        for module in _imported_roots(path):
            root = module.split(".")[0]
            if root == "identity" and rel in ALPHA_IDENTITY_CONSUMERS:
                continue
            if root in FORBIDDEN_IN_ALPHA:
                offenders.append(f"{rel} → {module}")
    assert not offenders, (
        "alpha/ 的契約與模型層不得依賴外部世界：\n" + "\n".join(offenders)
        + f"\n（唯一例外是 {ALPHA_IO_SUBPACKAGE}）"
    )


def test_the_io_exception_stays_narrow() -> None:
    """例外必須**窄**——若 `alpha/providers/` 之外也開始 import 資料庫，這條會紅。

    ⚠ 這條與上一條是一對：上一條放行 providers，這一條確保放行的範圍沒有擴散。
    「清單會腐壞，判準不會」——例外清單尤其會。
    """
    io_files = {
        _rel(p) for p in _python_files("alpha")
        if any(m.split(".")[0] in ("neo4j", "engine_c", "yfinance", "loader")
               for m in _imported_roots(p))
    }
    outside = {f for f in io_files if not f.startswith(ALPHA_IO_SUBPACKAGE)}
    assert not outside, f"I/O 溢出到 providers 之外：{sorted(outside)}"


def test_alpha_imports_cleanly_without_optional_dependencies() -> None:
    """`import alpha` 不得把 neo4j／yfinance／anthropic 拉進 `sys.modules`。"""
    import subprocess
    import sys

    code = (
        "import alpha, sys;"
        "bad=[m for m in ('neo4j','yfinance','anthropic','decision_lab','engine_c')"
        " if m in sys.modules];"
        "print(','.join(bad))"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT,
                         capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "", f"import alpha 拉進了：{out.stdout.strip()}"


def test_cypher_stays_out_of_the_alpha_core() -> None:
    """Neo4j 是 implementation detail；Cypher 只准出現在 `alpha/providers/`。

    ⚠ 連 providers 裡也應該優先呼叫既有的 `query/`——那裡才是 Cypher 的家。
    `providers/` 允許少量 Cypher，是為了取 `query/` 沒有提供的 provenance
    （例如 claim → SourceDoc 的引用），不是為了重寫排序邏輯。
    """
    offenders = [
        _rel(p) for p in _python_files("alpha")
        if not _rel(p).startswith(ALPHA_IO_SUBPACKAGE)
        and _CYPHER.search(p.read_text(encoding="utf-8"))
    ]
    assert not offenders, f"alpha/ 的契約與模型層出現 Cypher：{offenders}"


# ---------------------------------------------------------------------------
# 2. Engine D 不得反向依賴新層
# ---------------------------------------------------------------------------

def test_decision_lab_does_not_import_new_layers() -> None:
    """Engine D 是**下游**：它消費 `AlphaSignal`，不呼叫 Alpha Research。

    Phase 3 的 adapter（`decision_lab/adapters/alpha.py`）只吃已經算好的
    `AlphaSignal` payload，不 import `alpha/`。
    """
    offenders: list[str] = []
    for package in ("decision_lab", "engine_d_runtime"):
        for path in _python_files(package):
            for module in _imported_roots(path):
                if module.split(".")[0] in NEW_LAYERS:
                    offenders.append(f"{_rel(path)} → {module}")
    assert not offenders, "Engine D 不得 import 新層：\n" + "\n".join(offenders)


# ---------------------------------------------------------------------------
# 3. Core 不得依賴 MCP（依賴方向只准 peripheral → core）
# ---------------------------------------------------------------------------

def test_core_does_not_import_mcp_server() -> None:
    """MCP／remote 是 **optional adapter**，不是核心架構。

    新核心必須能在完全沒有 MCP 的情況下運作。這條**現在就會通過**，因為 5 個
    已知消費端都在 allowlist 裡；它擋的是**第 6 個**。
    """
    offenders = sorted(
        _rel(path)
        for package in CORE_PACKAGES
        for path in _python_files(package)
        if any(m.split(".")[0] == "mcp_server" for m in _imported_roots(path))
    )
    unexpected = set(offenders) - KNOWN_MCP_CONSUMERS
    assert not unexpected, (
        "新增了 core → mcp_server 的依賴：\n" + "\n".join(sorted(unexpected))
        + "\n依賴方向必須 peripheral → core；請改為呼叫 application service"
    )


def test_mcp_allowlist_has_no_stale_entries() -> None:
    """欠債清單要跟著現實縮小——修好了卻沒從 allowlist 移除，下一個人會以為還欠著。

    ⚠ 這條與上一條是一對：上一條防新增，這一條防清單腐壞（「清單會腐壞，判準不會」）。
    """
    actual = {
        _rel(path)
        for package in CORE_PACKAGES
        for path in _python_files(package)
        if any(m.split(".")[0] == "mcp_server" for m in _imported_roots(path))
    }
    stale = KNOWN_MCP_CONSUMERS - actual
    assert not stale, f"allowlist 有已修好的殘留條目，請移除：{sorted(stale)}"


def test_known_mcp_debt_is_exactly_five_files() -> None:
    """Phase 3 的驗收 baseline：**5 → 0**。這個數字寫成斷言才不會悄悄變大。"""
    assert len(KNOWN_MCP_CONSUMERS) == 5


# ---------------------------------------------------------------------------
# 4. audit 骨架：未實作不得偽裝成通過
# ---------------------------------------------------------------------------

def test_audit_registry_reports_not_implemented_not_pass() -> None:
    """L13：成功與未實作若在同一個訊號上同形，讀的人會以為那項健全性有人在管。"""
    results = audit.run_all()
    assert len(results) == len(audit.CHECKS) == 12
    for result in results:
        assert result.status is not audit.AuditStatus.PASS, result.check
        assert result.status is audit.AuditStatus.SKIPPED
        assert result.summary == "not_implemented"


def test_audit_output_says_skipped_is_not_pass() -> None:
    """輸出必須自己講清楚，不能只靠讀的人知道。"""
    text = audit.render(audit.run_all())
    assert "SKIPPED" in text
    assert "SKIPPED 不是 PASS" in text


def test_every_audit_check_names_an_invariant_and_an_owner() -> None:
    """沒有 owner 的檢查＝沒有人會實作它（L13 的「管子只接一頭」）。"""
    for check in audit.CHECKS:
        assert check.invariant.startswith("INV-"), check.name
        assert check.owner_phase.startswith("Phase "), check.name
        assert check.description
