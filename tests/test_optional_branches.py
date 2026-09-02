"""ROADMAP code-review 項（2026-08-29）：例外分支要有會真的觸發的測試。

`cli._optional` 與 `adapters.fetch_ranking_view` 的「拿不到 → None」承諾，
此前只有正常路徑覆蓋——吞例外的分支從未被真的觸發過。
（原清單第三項 `store.complete_paper_amendment` 已不存在於 codebase，2026-09-02 查證。）
"""
from __future__ import annotations

import pytest

from decision_lab.cli import _optional


def test_optional_swallows_exception_to_none() -> None:
    def boom() -> dict:
        raise RuntimeError("builder exploded")

    assert _optional(boom) is None


def test_optional_passes_through_result() -> None:
    assert _optional(lambda: {"x": 1}) == {"x": 1}


def test_fetch_ranking_view_transform_exception_returns_none(monkeypatch) -> None:
    """docstring 承諾「讀不到回 None」——轉換段（rank/build）的例外同樣適用。"""
    import query.bottleneck as bottleneck
    from engine_d_runtime import adapters

    class _FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class _FakeDriver:
        def session(self):
            return _FakeSession()

        def close(self):
            pass

    class _FakeGraphDatabase:
        @staticmethod
        def driver(*args, **kwargs):
            return _FakeDriver()

    monkeypatch.setenv("NEO4J_PASSWORD", "x")
    import neo4j

    monkeypatch.setattr(neo4j, "GraphDatabase", _FakeGraphDatabase)
    monkeypatch.setattr(bottleneck, "fetch_assertions", lambda session: [])

    def raise_transform(*args, **kwargs):
        raise ValueError("transform exploded")

    monkeypatch.setattr(bottleneck, "rank_bottlenecks", raise_transform)

    assert adapters.fetch_ranking_view() is None


def test_assessment_scaffold_prefills_refs_and_leaves_judgment_blank() -> None:
    """ROADMAP 2026-09-02：骨架抄引用、不代寫判斷（level 恆 unknown、reason 是佔位）。"""
    from decision_lab.references import (
        SCAFFOLD_NO_AUTHORITY_NOTE,
        SCAFFOLD_REASON_PLACEHOLDER,
        build_assessment_scaffold,
    )

    scaffold = build_assessment_scaffold({})
    assert set(scaffold) == {
        "source_reliability",
        "technical_causal_link",
        "commercial_maturity",
        "financial_resilience",
        "valuation_payoff",
    }
    for body in scaffold.values():
        assert body["level"] == "unknown"
        assert body["reason"] == SCAFFOLD_REASON_PLACEHOLDER
        assert body["evidence_refs"] == []
        assert body["missing_data"] == [SCAFFOLD_NO_AUTHORITY_NOTE]


def test_identity_alignment_pure_diff() -> None:
    """公司對齊計數（2026-09-02）：洩漏逐一列出、未研究只計數。"""
    from engine_d_runtime.adapters import compute_identity_alignment

    out = compute_identity_alignment(
        {"co:a", "co:b", "co:leak"}, {"co:a", "co:b", "co:only_reg"}
    )
    assert out["graph_not_in_registry"] == ["co:leak"]
    assert out["registry_not_in_graph_count"] == 1
    assert out["graph_companies"] == 3
    assert out["registry_companies"] == 3


def test_variant_perception_roundtrip_and_supersede(tmp_path) -> None:
    """cohort thesis(2026-09-02):append-only、supersede 後只回最新。"""
    from decision_lab.store import DecisionStore
    from storage.relational import initialize_private_root

    repo = tmp_path / "repo"
    repo.mkdir()
    private_root = repo / "library" / "private"
    initialize_private_root(private_root, repo_root=repo)
    store = DecisionStore.open(
        private_root / "decision_lab" / "decision_lab.db",
        private_root=private_root,
        repo_root=repo,
    )
    try:
        cohort = store.ensure_cohort(
            dedupe_key="vp-test", company_id="co:nvidia", research_ticker="NVDA"
        )
        cid = (
            cohort.cohort_id
            if hasattr(cohort, "cohort_id")
            else cohort["cohort_id"]
        )
        t1 = store.record_variant_perception(cid, variant_perception="v1")
        assert store.latest_variant_perception(cid)["variant_perception"] == "v1"
        store.record_variant_perception(
            cid, variant_perception="v2", supersedes_id=t1
        )
        assert store.latest_variant_perception(cid)["variant_perception"] == "v2"
        assert store.latest_variant_perception("dc_nonexistent") is None
        by_co = store.latest_variant_perception_for_company("co:nvidia")
        assert by_co is not None and by_co["variant_perception"] == "v2"
        assert store.latest_variant_perception_for_company("co:absent") is None
    finally:
        store.close()
