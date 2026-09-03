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

#: **Engine D 不得 import 的層。**
#:
#: ⚠ `risk` **不在列上**，而且那是刻意的：pipeline 是
#: `alpha → portfolio → risk → Engine D`，Engine D 的職責**就是執行硬上限**，
#: 所以它消費 `risk/policy.py` 的政策數值是正確方向（下游消費上游）。
#: 真正不准的是反過來——`risk/` 不得 import `decision_lab`（見下一條測試）。
FORBIDDEN_FOR_ENGINE_D = ("alpha", "portfolio")

#: 掃描範圍：所有 first-party package（不含 tests 與 .venv）。
CORE_PACKAGES = (
    "alpha", "portfolio", "risk", "shared", "intake",
    "decision_lab", "engine_b", "engine_c",
    "engine_d_runtime", "query", "loader", "thesis", "identity", "storage",
    "fetchers", "notifications", "crons", "scripts",
)

#: ✅ **2026-09-03 Phase 3b：5 → 0，欠債清空。**
#:
#: 原本這裡有 5 個 core 消費端被迫 import `mcp_server`（含 pq2 待辦池本身），
#: 成因是 `mcp_server/` 4,016 行有 **79% 不是 MCP**——Research Action 的 domain、
#: filesystem provenance 原語、local-only Git 發布，全被關在 transport package 裡。
#: 抽出到 `intake/` 之後，**新核心可以在完全沒有 MCP 的情況下運作**。
#:
#: ⚠ 這個集合現在是空的，而檢查**仍然在跑**——它擋的是第 1 個新增者。
KNOWN_MCP_CONSUMERS: frozenset[str] = frozenset()

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
            if rel in COMPOSITION_ROOTS and root in ("identity", "decision_lab"):
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

#: **搬遷期的 module aliasing shim。** 舊路徑轉發到新家，讓既有 import 不必一次全改。
#:
#: ⚠ 這是一份**會縮小的欠債清單**，不是豁免：`test_listed_shims_really_are_shims`
#: 會驗證每一個列出的檔案**真的只是 shim**（極短、含 aliasing 標記、無業務邏輯），
#: 所以它不能被拿來藏真正的違規。
#: **Phase 3 收尾的驗收條件是這個集合變成空的。**
TRANSITIONAL_SHIMS = frozenset({
    "decision_lab/beta_policy.py",
    "decision_lab/beta_monitor.py",
    "decision_lab/nav_exposure.py",
    "decision_lab/portfolio_risk.py",
    "decision_lab/ranking_view.py",
    "decision_lab/capital_authority.py",
    "decision_lab/adapters/market.py",
    "decision_lab/redaction.py",
    "decision_lab/blockers.py",
    "decision_lab/blocker_severity.py",
    "thesis/investment_policy.py",
    "mcp_server/research_actions.py",
    "mcp_server/intake.py",
    "mcp_server/action_publisher.py",
    "mcp_server/decision_tools.py",
})

#: `engine_d_runtime` 是 **composition root**——它的職責就是把各層接起來，
#: 所以它 import `portfolio`／`alpha` 是**正確方向**（peripheral → core 的組裝端）。
#: 真正不准的是 `decision_lab/` 的 domain 模組反向依賴新層。
COMPOSITION_ROOTS = frozenset({
    "engine_d_runtime/adapters.py",
    "engine_d_runtime/bootstrap.py",
    "decision_lab/cli.py",
    # ⚠ `alpha/cli.py` 是 entry point：它負責把 `AlphaSignal` **序列化**後交給
    # Engine D 的 adapter。domain 模組（contracts／context／models）仍然完全
    # 不知道 Engine D 存在——`test_alpha_core_has_no_external_or_engine_dependencies`
    # 守著那一半。
    "alpha/cli.py",
})


def test_decision_lab_domain_does_not_import_new_layers() -> None:
    """Engine D 的 **domain 模組**是下游：它消費 `AlphaSignal`，不呼叫 Alpha Research。

    Phase 3 的 adapter（`decision_lab/adapters/alpha.py`）只吃已經算好的
    `AlphaSignal` payload，不 import `alpha/`。
    """
    offenders: list[str] = []
    for package in ("decision_lab", "engine_d_runtime"):
        for path in _python_files(package):
            rel = _rel(path)
            if rel in TRANSITIONAL_SHIMS or rel in COMPOSITION_ROOTS:
                continue
            for module in _imported_roots(path):
                if module.split(".")[0] in FORBIDDEN_FOR_ENGINE_D:
                    offenders.append(f"{rel} → {module}")
    assert not offenders, (
        "Engine D 的 domain 模組不得 import alpha／portfolio：\n" + "\n".join(offenders)
    )


def test_upstream_layers_do_not_import_engine_d() -> None:
    """**方向只准一邊。** `alpha`／`portfolio`／`risk`／`shared` 都在 Engine D 上游。

    它們若 import `decision_lab`，就形成環——而環的實際後果是
    「Engine C 為了讀一個字彙表而載入整個決策層」
    （2026-09-03 實測的三條環全是這個形狀）。
    """
    offenders: list[str] = []
    for package in ("alpha", "portfolio", "risk", "shared"):
        for path in _python_files(package):
            if _rel(path) in COMPOSITION_ROOTS:
                continue
            for module in _imported_roots(path):
                if module.split(".")[0] in ("decision_lab", "engine_d_runtime"):
                    offenders.append(f"{_rel(path)} → {module}")
    assert not offenders, "上游層不得 import Engine D：\n" + "\n".join(offenders)


@pytest.mark.parametrize("rel", sorted(TRANSITIONAL_SHIMS))
def test_listed_shims_really_are_shims(rel: str) -> None:
    """**欠債清單不得被拿來藏真正的違規。**

    每個列在 `TRANSITIONAL_SHIMS` 的檔案必須真的只是轉發：
    極短、含 aliasing 標記、且沒有任何 `def`／`class`。
    """
    text = (ROOT / rel).read_text(encoding="utf-8")
    assert "_sys.modules[__name__] = _impl" in text, f"{rel} 不是 aliasing shim"
    assert "def " not in text and "class " not in text, f"{rel} 含業務邏輯，不是純轉發"
    assert len(text.splitlines()) < 25, f"{rel} 太長，可能不只是 shim"


def test_shim_list_has_no_stale_entries() -> None:
    """搬完卻沒從清單移除，下一個人會以為還欠著（「清單會腐壞，判準不會」）。"""
    stale = {rel for rel in TRANSITIONAL_SHIMS if not (ROOT / rel).exists()}
    assert not stale, f"shim 已刪除但清單未更新：{sorted(stale)}"


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
    # 反向也要成立：清單為空時，實際依賴也必須為空
    assert not (actual - KNOWN_MCP_CONSUMERS), (
        f"出現未登記的 mcp_server 依賴：{sorted(actual - KNOWN_MCP_CONSUMERS)}"
    )


def test_no_core_module_depends_on_mcp() -> None:
    """**Phase 3b 的驗收：core → `mcp_server` 的 import 數 5 → 0。**

    這個數字寫成斷言才不會悄悄變回去。若日後真的又需要一個例外，
    加進 `KNOWN_MCP_CONSUMERS` 會讓這條紅——那是刻意的摩擦：
    每一個例外都應該是被討論過的決定，不是順手加的 import。
    """
    assert KNOWN_MCP_CONSUMERS == frozenset(), (
        "core 不應再有任何 mcp_server 依賴；"
        f"目前欠債清單：{sorted(KNOWN_MCP_CONSUMERS)}"
    )


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


# ---------------------------------------------------------------------------
# 5. intake/ 是 application layer，不得依賴 transport
# ---------------------------------------------------------------------------

def test_intake_does_not_import_mcp() -> None:
    """**`intake/` 可以在完全沒有 MCP 的情況下運作。**

    這是「MCP 是 optional adapter」這句話唯一可執行的形式——
    若 `intake/` 需要 `mcp`，那它就不是 application layer，只是換了個目錄的 transport。
    """
    offenders = [
        f"{_rel(p)} → {m}"
        for p in _python_files("intake")
        for m in _imported_roots(p)
        if m.split(".")[0] in ("mcp", "mcp_server")
    ]
    assert not offenders, "intake/ 不得依賴 MCP：\n" + "\n".join(offenders)


def test_mcp_adapter_is_thin() -> None:
    """adapter 只該有 `@mcp.tool()` 包裝——**business logic 不得回流**。

    baseline（2026-09-03 抽出後）：`graph_mcp.py` 從 1,349 行降到 ~350。
    若它又長回 500 行以上，代表 application 邏輯正在回流到 transport 層。
    """
    text = (ROOT / "mcp_server" / "graph_mcp.py").read_text(encoding="utf-8")
    assert len(text.splitlines()) < 500, (
        "mcp_server/graph_mcp.py 又變厚了——application 邏輯應該住 intake/"
    )
