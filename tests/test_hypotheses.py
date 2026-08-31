"""截圖假設層測試（docs/brainstorms/2026-08-31-unverified-screenshot-leads-requirements.md）。"""

from datetime import date

import pytest

from engine_b import hypotheses as hy
from query.bottleneck import rank_bottlenecks, render_what_if


def _fresh():
    return {"schema_version": 1, "hypotheses": [], "source_credibility": {}}


def test_add_requires_source_and_expiry():
    data = _fresh()
    with pytest.raises(hy.HypothesisError):
        hy.add_hypothesis(data, source_handle="", expires="2027-01-01", statement="x")
    with pytest.raises(hy.HypothesisError):
        hy.add_hypothesis(data, source_handle="@a", expires="", statement="x")
    with pytest.raises(hy.HypothesisError):
        hy.add_hypothesis(
            data, source_handle="@a", expires="2027-01-01", statement="x",
            edges=[{"src_id": "co:x"}],
        )


def test_expire_and_credibility_ledger():
    data = _fresh()
    h1 = hy.add_hypothesis(
        data, source_handle="@leaker", expires="2026-09-01", statement="a",
    )
    h2 = hy.add_hypothesis(
        data, source_handle="@leaker", expires="2027-01-01", statement="b",
    )
    assert hy.expire_stale(data, today=date(2026, 9, 2)) == 1
    assert data["hypotheses"][0]["status"] == "expired"
    # expired 仍可事後驗證（遲到的一手）
    hy.record_verification(data, h1["hypothesis_id"], outcome="hit", receipt="doc:x")
    hy.record_verification(data, h2["hypothesis_id"], outcome="miss", receipt="doc:y")
    ledger = data["source_credibility"]["@leaker"]
    assert ledger == {"hits": 1, "misses": 1}
    # 已終態不可重複驗證
    with pytest.raises(hy.HypothesisError):
        hy.record_verification(data, h1["hypothesis_id"], outcome="hit", receipt="doc:z")


def test_overlay_shape_and_isolation():
    data = _fresh()
    hy.add_hypothesis(
        data, source_handle="@s", expires="2027-01-01", statement="x supplies y",
        edges=[{"src_id": "co:x", "relation": "supplies_to", "dst_id": "tech:y",
                "attributes": {"substitutability": 5, "sole_source": True}}],
    )
    rows = hy.overlay_assertions(data)
    assert len(rows) == 1
    assert rows[0]["origin"] == hy.HYPOTHESIS_ORIGIN
    assert rows[0]["source_type"] == "hypothesis"
    # refuted/expired 的不再疊加
    data["hypotheses"][0]["status"] = "refuted"
    assert hy.overlay_assertions(data) == []


from tests.test_bottleneck_ranking import _FakeRegistry as _Reg


def _assertion(src, dst, sub, origin="Acme", relation="supplies_to"):
    import json as _json
    return {
        "src": src, "relation": relation, "dst": dst,
        "attributes": _json.dumps({"substitutability": sub}),
        "confidence": 0.8, "origin": origin, "source_type": "transcript",
    }


def test_what_if_diff_detects_structural_change():
    registry = _Reg()
    base_rows = [
        _assertion("co:a", "tech:t1", 5),
        _assertion("co:b", "tech:t2", 4),
    ]
    baseline = rank_bottlenecks(base_rows, registry)
    data = _fresh()
    hy.add_hypothesis(
        data, source_handle="@s", expires="2027-01-01", statement="c is the real choke",
        edges=[{"src_id": "co:c", "relation": "supplies_to", "dst_id": "tech:t3",
                "attributes": {"substitutability": 5, "sole_source": True}}],
    )
    hyp_rows = hy.overlay_assertions(data)
    overlaid = rank_bottlenecks(base_rows + hyp_rows, registry)
    text = render_what_if(baseline, overlaid, hyp_rows)
    assert "co:c" in text and "新進結構排序" in text
    # 無變化情境
    text_same = render_what_if(baseline, baseline, hyp_rows)
    assert "無變化" in text_same
