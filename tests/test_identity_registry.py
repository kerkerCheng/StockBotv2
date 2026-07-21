from __future__ import annotations

import ast
from pathlib import Path

from decision_lab.identity import resolve_identity
from identity.registry import TICKER_MAP, get_registry
from loader.load_to_neo4j import TICKER_MAP as LOADER_TICKER_MAP


ROOT = Path(__file__).resolve().parents[1]
KNOWN_CONSUMERS = (
    "loader/migrate_add_ticker.py",
    "thesis/preconditions.py",
    "thesis/generate_lane_memo.py",
    "engine_c/etl_yfinance.py",
    "query/health_audit.py",
    "crons/weekly_scan_digest.py",
    "scripts/add_tickers.py",
)


def test_neutral_registry_preserves_known_company_mappings() -> None:
    registry = get_registry()

    assert TICKER_MAP is LOADER_TICKER_MAP
    assert registry.research_ticker("co:coherent") == "COHR"
    assert registry.research_ticker("co:sivers_semiconductors") == "SIVE.ST"
    assert registry.research_ticker("co:anthropic") is None
    assert registry.company_id_for_ticker("sive.st") == "co:sivers_semiconductors"
    assert len(TICKER_MAP) == 47


def test_all_known_consumers_import_ticker_map_from_neutral_registry() -> None:
    for relative in KNOWN_CONSUMERS:
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        imports = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and any(alias.name == "TICKER_MAP" for alias in node.names)
        }
        assert imports == {"identity.registry"}, relative

    loader_tree = ast.parse(
        (ROOT / "loader/load_to_neo4j.py").read_text(encoding="utf-8")
    )
    loader_imports = {
        node.module
        for node in ast.walk(loader_tree)
        if isinstance(node, ast.ImportFrom)
        and any(alias.name == "TICKER_MAP" for alias in node.names)
    }
    assert loader_imports == {"identity.registry"}


def test_repo_has_no_reverse_identity_or_decision_lab_authority_imports() -> None:
    forbidden_ticker_imports: list[str] = []
    for path in ROOT.rglob("*.py"):
        if any(part in {".venv", ".git", "tests"} for part in path.parts):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module == "loader.load_to_neo4j" and any(
                alias.name == "TICKER_MAP" for alias in node.names
            ):
                forbidden_ticker_imports.append(str(path.relative_to(ROOT)))
    assert forbidden_ticker_imports == []

    forbidden_decision_imports: list[tuple[str, str]] = []
    for path in (ROOT / "decision_lab").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module == "engine_c" or node.module.startswith("engine_c."):
                    forbidden_decision_imports.append((str(path), node.module))
                if node.module == "loader" or node.module.startswith("loader."):
                    forbidden_decision_imports.append((str(path), node.module))
    assert forbidden_decision_imports == []


def test_application_identity_composes_sheet_alias_without_second_mapping() -> None:
    resolved = resolve_identity(
        company_id="co:sivers_semiconductors",
        execution_aliases={"SIVE.ST": "FRA:2DG"},
    )

    assert resolved.company_id == "co:sivers_semiconductors"
    assert resolved.research_ticker == "SIVE.ST"
    assert resolved.execution_symbol == "FRA:2DG"
    assert resolved.blockers == ()


def test_unresolved_identity_fails_closed_with_application_blocker() -> None:
    resolved = resolve_identity(research_ticker="UNKNOWN")

    assert resolved.company_id is None
    assert resolved.execution_symbol is None
    assert resolved.blockers == ("unresolved_company_identity",)
