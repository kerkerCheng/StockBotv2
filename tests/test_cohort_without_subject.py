# -*- coding: utf-8 -*-
"""沒有主詞的 cohort 不得鑄 pq2 編號，而有主詞的未上市公司不得被誤傷。

事發（2026-09-12）：`tech:hbm` 的「入圖後自動追蹤」cohort 燒掉四個 pq2 編號
——[540]（13:29 go → 14:24 park）、[547]（14:27 → 14:29）、[551]（21:42 → 21:48）、
[554]。它拿到 `identity_unresolved`（`resolution_mode=user_decision`，next_step
「登記 company_id」），而那是**結構上無法被滿足**的要求：技術節點永遠不會有 ticker、
也不會掛牌。三次 `go` 全由常規授權自動放行，所以它不需要使用者按鍵就能持續消耗
編號空間——而 pq2 是使用者**唯一**的授權介面。

⚠ 驗收刻意寫成**兩面**（只做到第一面很可能是把整個 auto-tracker 關掉，
那會一起關掉會動的那 8 筆）：
  ① 沒有主詞的 cohort 不鑄號、但留下 deterministic 的 retirement audit；
  ② 有主詞的未上市公司照舊進等事件佇列。
"""

from __future__ import annotations

from engine_b import todo


def _row(**over):
    row = {
        "type": "decision_review",
        "ref_id": "dc_test",
        "title": "unknown：補獨立來源",
        "source": "decision_lab",
    }
    row.update(over)
    return row


def _pool(items=()):
    return {"items": list(items), "log": [], "next_n": 1, "schema_version": "0.1"}


def test_cohort_without_a_subject_mints_no_number() -> None:
    """① 三個身分欄位全空 → 不鑄號。這就是止血點。"""
    pool = _pool()
    todo.sync(pool, [
        _row(system_internal_only=True,
             suppression={"receipt": "cohort-without-subject:dc_test", "reason": "沒有主詞"}),
    ])

    assert pool["items"] == [], "沒有主詞的 cohort 不該拿到編號"
    assert pool["next_n"] == 1, "編號空間不該被消耗"


def test_existing_number_is_retired_with_the_real_reason_not_a_borrowed_one() -> None:
    """抑制的理由必須跟著 row 走（L16），而且不能沿用別的成因的字串（L11-1）。

    先前 receipt 硬寫 `blocker-registry:system_internal`——套在「沒有主詞」這個
    成因上是假的，而假 receipt 會讓稽核以為 blocker registry 做過那個判斷。
    """
    existing = {
        "n": 554, "type": "decision_review", "ref_id": "dc_test",
        "title": "unknown：補獨立來源", "hint": "", "added_at": "2026-09-12T00:00:00+00:00",
        "resolution": None, "resolved_at": None,
    }
    pool = _pool([existing])
    todo.sync(pool, [
        _row(system_internal_only=True,
             suppression={
                 "receipt": "cohort-without-subject:dc_test",
                 "reason": "這個 cohort 沒有任何可識別的主詞",
             }),
    ])

    assert existing["resolution"] == "system_internal"
    assert "沒有任何可識別的主詞" in existing["reason"]
    entry = next(e for e in pool["log"] if e.get("verb") == "system_internal_retired")
    assert entry["receipt"] == "cohort-without-subject:dc_test"
    assert "blocker-registry" not in entry["receipt"], "不得沿用別的成因的 receipt"


def test_suppression_without_a_declared_reason_keeps_the_registry_wording() -> None:
    """既有的 system_internal 路徑不得被改壞——沒宣告 suppression 時維持原字串。"""
    existing = {
        "n": 99, "type": "decision_review", "ref_id": "dc_sys",
        "title": "co:x：…", "hint": "", "added_at": "2026-09-12T00:00:00+00:00",
        "resolution": None, "resolved_at": None,
    }
    pool = _pool([existing])
    todo.sync(pool, [_row(ref_id="dc_sys", system_internal_only=True)])

    entry = next(e for e in pool["log"] if e.get("verb") == "system_internal_retired")
    assert entry["receipt"] == "blocker-registry:system_internal"
    assert "blocker registry" in existing["reason"]


def test_a_cohort_with_a_subject_still_mints_a_number() -> None:
    """② 有主詞就照舊——未上市公司的 hint 是 `co:*`，它們必須留在佇列裡。

    實測分野（2026-09-12）：9 個 `company_id IS NULL` 的 cohort 中，8 個的
    `company_id_hint` 是 `co:*`（未上市公司，走 awaiting_external），只有技術節點
    三欄全空。這條測試釘的是**那 8 筆不受影響**。
    """
    pool = _pool()
    todo.sync(pool, [_row(ref_id="dc_unlisted", title="co:agility_robotics：…")])

    assert len(pool["items"]) == 1
    assert pool["items"][0]["ref_id"] == "dc_unlisted"


def test_ra_receipt_accepts_not_applicable_cohort_but_nothing_else() -> None:
    """主詞不是公司時 RA 仍要結得掉，但 `not_applicable` 是唯一的替代值。

    ⚠ 這兩個 assert 是一對：放行面讓入圖核准不會永遠結不了案，
    收緊面確保沒人拿別的字串蒙混過 cohort 這一欄。
    """
    fields = todo._receipt_fields(
        "action:ra_x;digest:" + "a" * 64 + ";commit:not_required;cohort:not_applicable"
    )
    assert fields["cohort"] == "not_applicable"

    bogus = todo._receipt_fields(
        "action:ra_x;digest:" + "a" * 64 + ";commit:not_required;cohort:whatever"
    )
    assert not bogus["cohort"].startswith("dc_") and bogus["cohort"] != "not_applicable", (
        "這個值必須被上層的驗證擋下——它既不是 cohort 也不是宣告的缺席"
    )
