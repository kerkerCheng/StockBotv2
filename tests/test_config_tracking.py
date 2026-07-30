"""Config 與封閉字彙登記表的防腐測試。

兩個各自獨立、但成因相同的靜默失效：

1. **config 檔沒被追蹤。** `.gitignore` 對 `config/*.json` 是預設忽略、靠白名單開例外
   （該目錄放 Google service account 憑證）。新增 config 忘了加 `!config/<name>.json`
   時，本機一切正常、測試全綠，但 fresh clone 與另一個 agent 會缺檔而功能靜默失效。
   2026-07-30 一天內踩到兩次（engine_c_observation_fields、decision_blockers）。

2. **登記表腐爛。** `docs/solutions/architecture-patterns/closed-vocabulary-registry.md`
   列出每個封閉字彙住在哪個檔的哪個符號。檔案搬家或符號改名後，那張表會安靜地開始
   說謊——而它存在的理由正是「不必讀 Python 就知道邊界在哪」。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOC = (
    ROOT
    / "docs"
    / "solutions"
    / "architecture-patterns"
    / "closed-vocabulary-registry.md"
)

# 允許不被追蹤的 config（憑證類）。除此之外，被程式碼引用的 config 都必須進版控。
UNTRACKED_BY_DESIGN = {"config/my-project-stockbot-c6320591f129.json"}


def _git_ignored(relpath: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "-q", relpath],
        cwd=ROOT,
        capture_output=True,
    )
    return result.returncode == 0


def _config_paths_referenced_in_code() -> set[str]:
    """掃 Python 原始碼中出現的 config/<name>.json 引用。"""
    pattern = re.compile(r'"(config/[A-Za-z0-9_\-]+\.json)"')
    found: set[str] = set()
    for path in ROOT.rglob("*.py"):
        parts = set(path.parts)
        if parts & {".venv", "__pycache__", ".pytest_tmp"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        found.update(pattern.findall(text))
        # registry loader 慣用 _ROOT / "config" / "<name>.json" 的寫法
        for match in re.finditer(
            r'"config"\s*/\s*"([A-Za-z0-9_\-]+\.json)"', text
        ):
            found.add(f"config/{match.group(1)}")
    return found


def test_every_config_referenced_by_code_is_tracked_by_git() -> None:
    referenced = _config_paths_referenced_in_code()
    assert referenced, "應至少找到一些 config 引用，否則此測試失去意義"
    ignored = sorted(
        rel
        for rel in referenced
        if rel not in UNTRACKED_BY_DESIGN and _git_ignored(rel)
    )
    assert not ignored, (
        "以下 config 被程式碼引用但被 .gitignore 忽略；"
        f"請在 .gitignore 補 `!<path>`：{ignored}"
    )


def test_shipped_config_registries_exist_on_disk() -> None:
    for rel in (
        "config/company_identity.json",
        "config/engine_c_observation_fields.json",
        "config/decision_blockers.json",
        "config/investment_policy.json",
        "config/beta_policy.json",
    ):
        assert (ROOT / rel).exists(), f"缺少 {rel}"


# ── 封閉字彙登記表的防腐 ──────────────────────────────────────────────────────


def test_closed_vocabulary_doc_exists() -> None:
    assert DOC.exists(), "封閉字彙登記表不存在；它是交接時判斷擴充點的入口"


def _doc_text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_every_path_cited_in_the_registry_table_exists() -> None:
    """表上列的每個檔案路徑都必須真的存在。"""
    cited = set(
        re.findall(r"`([A-Za-z0-9_\-/]+\.(?:py|json))`", _doc_text())
    )
    assert cited, "應至少擷取到一些路徑"
    missing = sorted(rel for rel in cited if not (ROOT / rel).exists())
    assert not missing, f"登記表引用了不存在的檔案：{missing}"


def test_every_symbol_cited_in_the_registry_table_still_exists() -> None:
    """表上寫「`<檔案>` 的 `<符號>`」時，該符號必須真的在那個檔裡。

    這是登記表最容易腐爛的地方：檔案還在，但符號被改名或搬走，
    表就會安靜地把人導向錯的位置。
    """
    pairs = re.findall(
        r"`([A-Za-z0-9_\-/]+\.py)`\s*的\s*`([A-Za-z0-9_]+)`", _doc_text()
    )
    assert pairs, "應至少擷取到一組『檔案 的 符號』"
    broken: list[str] = []
    for rel, symbol in pairs:
        path = ROOT / rel
        if not path.exists():
            broken.append(f"{rel}（檔案不存在）")
            continue
        if not re.search(rf"\b{re.escape(symbol)}\b", path.read_text(encoding="utf-8")):
            broken.append(f"{rel} 的 {symbol}")
    assert not broken, f"登記表指向已不存在的符號：{broken}"


@pytest.mark.parametrize(
    "rel,symbol",
    [
        ("decision_lab/sizing.py", "AXIS_REFERENCE_AUTHORITIES"),
        ("decision_lab/sizing.py", "AXES"),
        ("decision_lab/sizing.py", "LEVELS"),
        ("engine_b/leads.py", "ALLOWED_TRANSITIONS"),
        ("decision_lab/workflow.py", "_INTENTS"),
        ("decision_lab/capital_authority.py", "_ALLOWED_TYPES"),
        ("engine_c/technical.py", "_METRIC_COLUMNS"),
        ("thesis/evidence_manifest.py", "HIGH_RISK_ATTRIBUTES"),
        ("loader/edge_resolution.py", "ALLOWED_ACTIONS"),
        ("engine_c/observation_fields.py", "KNOWN_AUTHORITIES"),
        ("decision_lab/context.py", "_ENGINE_C_AUTHORITIES"),
    ],
)
def test_frozen_and_at_risk_vocabularies_are_where_the_table_says(
    rel: str, symbol: str
) -> None:
    """明確釘住登記表宣稱的每個位置，改名時直接失敗而不是靜默漂移。"""
    path = ROOT / rel
    assert path.exists(), f"{rel} 不存在"
    assert re.search(
        rf"^{re.escape(symbol)}\b", path.read_text(encoding="utf-8"), re.MULTILINE
    ), f"{rel} 中找不到 {symbol}"
