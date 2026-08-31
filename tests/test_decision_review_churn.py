"""corroboration 殘餘類 decision_review 的 churn 抑制（2026-08-31）。

事發形狀：[294] NVDA 補獨立來源做完 resolve → 下次 sync 用同標題鑄 [308]。
修法：residual_digest 當復活判準——內容沒變不重生；變了才鑄號且標題講新缺口。
"""

from engine_b.todo import (
    _corroboration_only_user_codes,
    _residual_digest,
    active_items,
    empty_pool,
    sync,
)


def _row(digest=None, title="co:x：殘餘缺口——量產良率第三方量化"):
    row = {
        "type": "decision_review",
        "ref_id": "dc_test",
        "title": title,
        "hint": "當前 missing_data：量產良率第三方量化（共 1 項）｜test",
        "source": "decision_lab",
    }
    if digest:
        row["residual_digest"] = digest
    return row


def test_same_residual_does_not_resurrect_after_resolve():
    pool = empty_pool()
    digest = _residual_digest(["source_reliability_corroboration_incomplete"], ["md1"])
    sync(pool, [_row(digest)])
    item = active_items(pool)[0]
    assert item["residual_digest"] == digest
    item["resolved_at"] = "2026-08-31T00:00:00+00:00"
    item["resolution"] = "go"
    result = sync(pool, [_row(digest)])
    assert result["churn_suppressed"] == 1
    assert active_items(pool) == []


def test_changed_residual_mints_new_number_with_new_title():
    pool = empty_pool()
    d1 = _residual_digest(["source_reliability_corroboration_incomplete"], ["md1"])
    sync(pool, [_row(d1)])
    first = active_items(pool)[0]
    first["resolved_at"] = "2026-08-31T00:00:00+00:00"
    first["resolution"] = "go"
    d2 = _residual_digest(["source_reliability_corroboration_incomplete"], ["md2"])
    result = sync(pool, [_row(d2, title="co:x：殘餘缺口——新的缺口")])
    assert result["churn_suppressed"] == 0
    items = active_items(pool)
    assert len(items) == 1 and items[0]["n"] != first["n"]
    assert "新的缺口" in items[0]["title"]


def test_active_item_unaffected_by_digest_path():
    pool = empty_pool()
    digest = _residual_digest(["a_corroboration_incomplete"], ["m"])
    sync(pool, [_row(digest)])
    result = sync(pool, [_row(digest)])
    # active 中：照常 upsert 保留編號，不觸發抑制
    assert result["churn_suppressed"] == 0
    assert len(active_items(pool)) == 1


def test_corroboration_only_classifier_uses_registry():
    # 真缺口（unknown 類屬 user_decision 且非 corroboration 字尾）→ None
    assert _corroboration_only_user_codes(
        ["commercial_maturity_unknown", "source_reliability_corroboration_incomplete"]
    ) is None
    # 純殘餘 → 回傳 codes
    codes = _corroboration_only_user_codes(
        ["source_reliability_corroboration_incomplete", "execution_intent_research_only"]
    )
    assert codes == ["source_reliability_corroboration_incomplete"]
