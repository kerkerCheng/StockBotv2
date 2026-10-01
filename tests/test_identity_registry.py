from __future__ import annotations

import ast
import json
from pathlib import Path

from shared.identity_resolution import resolve_identity
from identity.registry import TICKER_MAP, get_registry
from loader.load_to_neo4j import TICKER_MAP as LOADER_TICKER_MAP


ROOT = Path(__file__).resolve().parents[1]
KNOWN_CONSUMERS = (
    "loader/migrate_add_ticker.py",
    "thesis/preconditions.py",
    "thesis/generate_lane_memo.py",
    "engine_c/etl_yfinance.py",
    "query/health_audit.py",
    "scripts/add_tickers.py",
)


def test_neutral_registry_preserves_known_company_mappings() -> None:
    registry = get_registry()

    assert TICKER_MAP is LOADER_TICKER_MAP
    assert registry.research_ticker("co:coherent") == "COHR"
    assert registry.research_ticker("co:sivers_semiconductors") == "SIVE.ST"
    assert registry.research_ticker("co:anthropic") is None
    assert registry.research_ticker("co:agility_robotics") is None
    assert registry.research_ticker("co:gxo_logistics") == "GXO"
    assert registry.research_ticker("co:schaeffler") == "SHA0.DE"
    assert registry.research_ticker("co:hyundai_mobis") == "012330.KS"
    assert registry.research_ticker("co:boston_dynamics") is None
    assert registry.company_id_for_ticker("sive.st") == "co:sivers_semiconductors"
    # 每個 registry 條目都要出現在 TICKER_MAP（含 research_ticker 為 None 的私人公司）。
    # 比對 config 而非硬編數字，才不會每 onboard 一家公司就得改測試。
    registered = json.loads(
        (ROOT / "config" / "company_identity.json").read_text(encoding="utf-8")
    )["companies"]
    assert len(TICKER_MAP) == len(registered)


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


def test_alias_resolves_to_same_company() -> None:
    """同一家公司的第二個交易代號必須解析得到——否則一部分 lead 永遠對不上。

    事發（2026-08-20）：SIVEF 是 Sivers 的美國 OTC 代號、SKHY 是 SK Hynix 的美國
    OTC，兩者都出現在推文 cashtag。`engine_b/entities.py` 的 base 反查只去交易所
    後綴（SIVE→SIVE.ST 可解），SIVEF 不是任何 research ticker 的 base，於是解析
    不到 company_id。該檔第 64 行的註解早已寫下「正解是在 registry 明列 alias」。
    """

    from identity.registry import CompanyIdentity, IdentityRegistry

    registry = IdentityRegistry(
        version=1,
        companies=(
            CompanyIdentity(
                company_id="co:sivers_semiconductors",
                research_ticker="SIVE.ST",
                aliases=("SIVEF",),
            ),
        ),
    )
    assert registry.company_id_for_ticker("SIVE.ST") == "co:sivers_semiconductors"
    assert registry.company_id_for_ticker("SIVEF") == "co:sivers_semiconductors"
    assert registry.company_id_for_ticker("sivef") == "co:sivers_semiconductors"


def test_alias_colliding_with_another_company_fails_closed() -> None:
    """registry 是 identity authority：寧可啟動失敗，也不要靜默指向錯的公司。"""

    import pytest

    from identity.registry import CompanyIdentity, IdentityRegistry

    with pytest.raises(ValueError, match="alias"):
        IdentityRegistry(
            version=1,
            companies=(
                CompanyIdentity(company_id="co:a", research_ticker="AAA"),
                CompanyIdentity(
                    company_id="co:b", research_ticker="BBB", aliases=("AAA",)
                ),
            ),
        )


def test_alias_absent_keeps_previous_behaviour() -> None:
    """沒填 aliases 的公司行為完全不變（預設空 tuple）。"""

    from identity.registry import CompanyIdentity, IdentityRegistry

    registry = IdentityRegistry(
        version=1,
        companies=(CompanyIdentity(company_id="co:a", research_ticker="AAA"),),
    )
    assert registry.company("co:a").aliases == ()
    assert registry.company_id_for_ticker("AAA") == "co:a"
    assert registry.company_id_for_ticker("ZZZ") is None


# ---------------------------------------------------------------------------
# Phase 4 Step 4.1c：name_aliases（名字）與 execution_symbol（執行代號）——兩者都不進 by_ticker
# ---------------------------------------------------------------------------

def test_name_aliases_and_execution_symbol_never_widen_ticker_resolution() -> None:
    """`company_id_for_ticker` 是資本歸屬路徑（plan 不可越線 12）：名字與執行代號都不得讓它多解析出任何東西。"""

    from identity.registry import CompanyIdentity, IdentityRegistry

    registry = IdentityRegistry(
        version=1,
        companies=(
            CompanyIdentity(company_id="co:sivers_semiconductors", research_ticker="SIVE.ST",
                            aliases=("SIVEF",), name_aliases=("Sivers",), execution_symbol="FRA:2DG"),
        ),
    )
    assert registry.company_id_for_ticker("SIVE.ST") == "co:sivers_semiconductors"
    assert registry.company_id_for_ticker("Sivers") is None
    assert registry.company_id_for_ticker("FRA:2DG") is None
    assert registry.execution_aliases() == {"SIVE.ST": "FRA:2DG"}


def test_execution_symbol_collisions_fail_closed() -> None:
    """執行代號撞到任何公司的 research ticker／ticker alias、或另一家的執行代號 → 啟動失敗，不靜默指錯（INV-1）。"""

    import pytest

    from identity.registry import CompanyIdentity, IdentityRegistry

    cases = (
        # 撞到「後面才登記」的那家 research ticker——by_ticker 要建完才比
        (CompanyIdentity(company_id="co:a", research_ticker="AAA", execution_symbol="BBB"),
         CompanyIdentity(company_id="co:b", research_ticker="BBB")),
        (CompanyIdentity(company_id="co:a", research_ticker="AAA", execution_symbol="XB"),
         CompanyIdentity(company_id="co:b", research_ticker="BBB", aliases=("XB",))),
        (CompanyIdentity(company_id="co:a", research_ticker="AAA", execution_symbol="FRA:X"),
         CompanyIdentity(company_id="co:b", research_ticker="BBB", execution_symbol="fra:x")),
    )
    for companies in cases:
        with pytest.raises(ValueError, match="execution_symbol"):
            IdentityRegistry(version=1, companies=companies)


def test_registry_file_parses_new_fields_preserving_name_case(tmp_path) -> None:
    from identity.registry import IdentityRegistry

    path = tmp_path / "company_identity.json"
    path.write_text(json.dumps({"version": 1, "companies": [
        {"company_id": "co:luxnet", "research_ticker": "4979.TWO", "display_name": "LuxNet Corporation",
         "name_aliases": ["華星光", " LuxNet ", ""], "execution_symbol": " tpe:4979 ",
         "_display_name_source": "ignored by the loader"},
    ]}), encoding="utf-8")
    company = IdentityRegistry.from_path(path).company("co:luxnet")
    assert company.name_aliases == ("華星光", "LuxNet")      # 名字保留大小寫、去空白、丟空字串
    assert company.execution_symbol == "TPE:4979"            # 代號照 ticker 慣例大寫


def test_real_registry_names_are_complete_except_documented_gaps() -> None:
    """2026-10-01 Phase 4 Step 4.1c：100 家補到 99；唯一沒補的那家在 `_note` 寫了為什麼（不替疑似抽取錯誤編名字）。
    共用寫法只准是已登記的那一對重複 id（名字比對對兩家都不算，見 `query.bottleneck.shared_name_forms`）。"""

    from query.bottleneck import shared_name_forms

    payload = json.loads((Path(__file__).resolve().parent.parent / "config" / "company_identity.json")
                         .read_text(encoding="utf-8"))
    missing = {c["company_id"]: c.get("_note") for c in payload["companies"] if not c.get("display_name")}
    assert set(missing) <= {"co:nava_thailand"}, missing
    assert all(missing.values()), "沒補 display_name 的公司必須在 _note 寫理由"
    shared = shared_name_forms(get_registry())
    assert shared <= {"openlight", "openlight photonics", "openlight photonics inc."}, shared
