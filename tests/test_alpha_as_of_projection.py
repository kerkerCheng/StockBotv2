"""Phase 6：as-of 圖投影與 anti-lookahead。

驗收條件（ROADMAP Phase 6）：**同一個查詢在 `as_of=T` 時看不到 T 之後 published
的證據**。這裡用注入的 assertion 測，不連 Neo4j。

⚠ 本檔守的是一個**方向性**的失敗：lookahead 不會讓任何東西壞掉，它只會讓回測
結果變好看。所以每一條斷言都要問「如果偷看了未來，這條會紅嗎」——不會紅的斷言
在這裡沒有價值。
"""
from __future__ import annotations

from datetime import date

import pytest

from alpha.errors import PointInTimeUnsupported
from alpha.providers.graph_neo4j import Neo4jGraphResearchProvider
from loader.source_dating import (
    DATING_METHODS, DatingRejected, audit_backfills, dates_in_url, validate_proposal,
)
from query.bottleneck import latest_possible_date, project_assertions_as_of

AS_OF = date(2026, 6, 30)


def _assertion(dst: str, published: str | None, *, sub: int = 5,
               doc: str = "sd_1", src: str = "co:coherent",
               relation: str = "depends_on", **attrs) -> dict:
    return {
        "src": src, "relation": relation, "dst": dst,
        "attributes": {"substitutability": sub, **attrs},
        "confidence": 0.9, "origin": "Third Party Research",
        "source_type": "news", "source_doc_id": doc, "published_at": published,
    }


def _provider(*rows) -> Neo4jGraphResearchProvider:
    return Neo4jGraphResearchProvider(driver=object(), _assertion_rows=list(rows))


# ---------------------------------------------------------------------------
# 1. 驗收條件本身：T 之後發表的東西在 T 看不到
# ---------------------------------------------------------------------------

def test_evidence_published_after_as_of_is_invisible() -> None:
    """ROADMAP Phase 6 的 exit criterion，逐字。

    空跑檢查：把 `project_assertions_as_of` 改成不篩 → 這條會紅（rows 變 2）。
    """
    provider = _provider(
        _assertion("mat:inp_substrate", "2026-06-02"),
        _assertion("tech:cpo", "2026-08-14", doc="sd_future", relation="supplies_to"),
    )
    at_t = provider.get_bottlenecks(as_of=AS_OF)
    now = provider.get_bottlenecks()

    assert {str(r.target_id) for r in at_t} == {"mat:inp_substrate"}
    assert {str(r.target_id) for r in now} == {"mat:inp_substrate", "tech:cpo"}


def test_every_evidence_ref_in_the_projection_predates_as_of() -> None:
    """列對了還不夠——**每一條 `EvidenceRef` 的日期也要 ≤ as_of**。

    這是 `select_point_in_time_evidence` 的輸入；ref 若不帶日期，下游會把它
    整批判成 `excluded_undated`，於是「投影正確」與「證據全被丟掉」同時發生。
    """
    provider = _provider(
        _assertion("mat:inp_substrate", "2026-06-02"),
        _assertion("mat:inp_substrate", "2026-08-14", doc="sd_future"),
    )
    rows = provider.get_bottlenecks(as_of=AS_OF)

    refs = [ref for row in rows for ref in row.evidence]
    assert refs, "投影不得產出沒有證據的列"
    assert all(ref.published_at is not None for ref in refs), "ref 必須帶日期"
    assert all(ref.published_at <= AS_OF for ref in refs)
    assert "sd_future" not in {ref.source_doc_id for ref in refs}


def test_attributes_from_future_documents_do_not_leak_into_the_projection() -> None:
    """**過濾必須在排序之前。**

    這是 lookahead 最難察覺的形式：列是對的（那條邊當時真的存在），
    但 `substitutability` 是後來那份文件才填的——先排序再砍列會留下這個值。

    空跑檢查：把 `_rank` 改成「先 rank 再依日期砍 rows」→ 這條會紅
    （sub 會變成 5，且該列會出現在排序裡）。
    """
    old = _assertion("mat:inp_substrate", "2026-01-05", sub=3, doc="sd_old")
    old["confidence"] = 0.5
    provider = _provider(
        old,                                    # 當時只知道 sub=3（排不進 rows）
        _assertion("mat:inp_substrate", "2026-08-14", sub=5, doc="sd_new"),
    )
    assert provider.get_bottlenecks(as_of=AS_OF) == ()
    assert [r.inputs.substitutability for r in provider.get_bottlenecks()] == [5]


# ---------------------------------------------------------------------------
# 2. 排除必須計數（INV-3 no silent drop）
# ---------------------------------------------------------------------------

def test_projection_counts_what_it_dropped_and_why() -> None:
    """「as-of 之後證據變少」與「本來就沒有證據」不得同形（L13）。"""
    projection = project_assertions_as_of([
        _assertion("mat:inp_substrate", "2026-06-02"),
        _assertion("tech:cpo", "2026-08-14"),
        _assertion("tech:uhp_laser", None),
    ], AS_OF)

    assert projection.input_count == 3
    assert len(projection.rows) == 1
    assert projection.reasons() == {"published_after_as_of": 1, "undated": 1}
    assert projection.dated_total == 2, "未定日不算進『已定日總數』"


def test_undated_evidence_is_excluded_not_assumed_old() -> None:
    """「我找不到日期」不等於「它在 T 之前」（L11-5）。

    ⚠ 這條方向很重要：把未定日當可用，回測就會看到未來；而它**不會報錯**，
    只會讓結果變好看。
    """
    projection = project_assertions_as_of(
        [_assertion("mat:inp_substrate", None)], AS_OF)
    assert projection.rows == ()
    assert projection.excluded_undated == 1


def test_projection_coverage_travels_with_the_data() -> None:
    """投影的計數要跟著結果走（L16），否則消費端會自己猜為什麼變少。"""
    provider = _provider(
        _assertion("mat:inp_substrate", "2026-06-02"),
        _assertion("tech:cpo", "2026-08-14", relation="supplies_to"),
    )
    provider.get_bottlenecks(as_of=AS_OF)
    coverage = provider._rank(AS_OF)["coverage"]

    assert coverage["as_of"] == AS_OF.isoformat()
    assert coverage["as_of_input_assertions"] == 2
    assert coverage["as_of_excluded"]["published_after_as_of"] == 1


# ---------------------------------------------------------------------------
# 3. 年月精度：一個欄位兩種精度（L12）
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("2026-06-02", date(2026, 6, 2)),
    ("2026-06-02T10:00:00", date(2026, 6, 2)),
    ("2025-12", date(2025, 12, 31)),        # 年月 → 當月**最後**一天（保守）
    ("2026-02", date(2026, 2, 28)),
    ("2026-13", None),
    ("", None),
    (None, None),
])
def test_partial_dates_resolve_to_the_latest_possible_day(text, expected) -> None:
    """`2025-12` 可能是 12/31 發表的。取月初＝把「不確定」讀成「對我有利」。

    空跑檢查：把它改成取當月**第一天** → 下一條會紅。
    """
    assert latest_possible_date(text) == expected


def test_a_month_precision_document_is_not_visible_at_the_start_of_that_month() -> None:
    """實測有 2 筆 `YYYY-MM`（`optica_opn_marvell_celestial_2025` 等）。"""
    rows = [_assertion("mat:inp_substrate", "2025-12")]
    assert project_assertions_as_of(rows, date(2025, 12, 1)).rows == ()
    assert len(project_assertions_as_of(rows, date(2025, 12, 31)).rows) == 1


# ---------------------------------------------------------------------------
# 4. 保險絲：它換了條件，沒有被拿掉
# ---------------------------------------------------------------------------

def test_the_fuse_still_blows_when_the_graph_carries_no_time_information() -> None:
    """圖上一條 `published_at` 都沒有 → 拒絕，不回空 list。

    空跑檢查：把 `_MIN_DATED_FOR_PROJECTION` 改成 0 → 這條會紅。
    """
    with pytest.raises(PointInTimeUnsupported, match="沒有任何一條"):
        _provider(_assertion("mat:inp_substrate", None)).get_bottlenecks(as_of=AS_OF)


def test_the_fuse_blows_when_asked_about_a_time_before_any_evidence() -> None:
    with pytest.raises(PointInTimeUnsupported, match="早於圖上最早的證據"):
        _provider(_assertion("mat:inp_substrate", "2026-06-02")).get_bottlenecks(
            as_of=date(2020, 1, 1))


def test_current_view_is_unaffected_by_the_projection() -> None:
    """`as_of=None` 是「當前視角」——不篩、也不因未定日而拒絕。"""
    provider = _provider(
        _assertion("mat:inp_substrate", None),
        _assertion("tech:cpo", "2026-08-14", relation="supplies_to"),
    )
    assert len(provider.get_bottlenecks()) == 2


# ---------------------------------------------------------------------------
# 5. 結構變化偵測（Phase 5b）——真實資料只走得到一個分支，其餘在這裡守
# ---------------------------------------------------------------------------

def test_a_new_supplier_for_a_known_chokepoint_is_a_loosening_event() -> None:
    provider = _provider(
        _assertion("tech:cpo", "2026-01-05", relation="supplies_to"),
        _assertion("tech:cpo", "2026-08-14", relation="supplies_to",
                   src="co:lumentum", doc="sd_new"),
    )
    events = provider.get_structural_changes_since(AS_OF)

    assert [(e.kind, e.direction) for e in events] == [("substitution", "loosening")]
    assert events[0].observed_at == date(2026, 8, 14)
    assert str(events[0].subject_id) == "tech:cpo"


def test_the_first_known_supplier_is_not_a_structural_change() -> None:
    """⚠ 我們**開始研究**一個新領域，不是世界鬆了。

    這是 `documents` 不參與排序的同一個理由：任何會隨「我們多讀一份文件」
    單調上升的東西，量的是研究量不是世界。

    空跑檢查：拿掉 `known_targets` 那道判斷 → 這條會紅。
    """
    provider = _provider(
        _assertion("tech:cpo", "2026-01-05", relation="supplies_to"),
        _assertion("tech:ndfeb_magnet", "2026-08-14", relation="supplies_to",
                   src="co:mp_materials", doc="sd_new"),
    )
    assert provider.get_structural_changes_since(AS_OF) == ()


def test_no_new_document_in_the_window_means_no_event() -> None:
    """窗內沒有新文件 ⇒ 沒有新資訊 ⇒ 不是事件。"""
    provider = _provider(_assertion("tech:cpo", "2026-01-05", relation="supplies_to"))
    assert provider.get_structural_changes_since(AS_OF) == ()


def test_a_row_that_only_appeared_because_of_undated_evidence_is_not_an_event() -> None:
    """⚠ 這是首跑真的產出過的自相矛盾事件：**`observed_at` 早於觀察窗**。

    成因是差集混了兩件事。這裡重現它：同一條邊有兩份 assertion，一份**已定日
    且在窗前**（低 confidence、sub=5），一份**未定日**（高 confidence、sub=3）。
    - `since` 的投影只看得到已定日那份 → sub=5 → 進得了 rows。

    反過來擺（未定日那份 sub 較高）才會讓它「只在當前視角出現」：

    - `since` 投影：只有已定日的 sub=3 → 排不進 rows。
    - 當前視角：兩份都在，高 confidence 的 sub=5 勝出 → 進 rows。

    於是它在差集裡看起來像「新出現的邊」，但**支持它的文件一份都不在窗內**——
    真正變的是我們補讀了一份沒有日期的文件，不是世界。

    空跑檢查：把 `arrived` 的 `ref.published_at > since` 條件拿掉 → 這條會紅
    （會產出一個 `observed_at=2026-01-05` 的「2026-06-30 之後的變化」）。
    """
    old = _assertion("tech:cpo", "2026-01-05", sub=3, doc="sd_dated",
                     relation="supplies_to")
    old["confidence"] = 0.4
    undated = _assertion("tech:cpo", None, sub=5, doc="sd_undated",
                         relation="supplies_to")
    # 讓 `tech:cpo` 在 `since` 時就已經是「已知瓶頸」（否則會先被
    # known_targets 那道判斷擋下，測不到本條要守的東西）。
    incumbent = _assertion("tech:cpo", "2026-01-05", sub=5, doc="sd_incumbent",
                           src="co:lumentum", relation="supplies_to")
    provider = _provider(old, undated, incumbent)

    assert provider.get_bottlenecks(as_of=AS_OF), "前提：投影本身要有列"
    assert provider.get_structural_changes_since(AS_OF) == ()


def test_substitutability_and_qualification_changes_produce_events() -> None:
    """⚠ 這兩個分支在**真實圖上目前一次都沒觸發過**（2026-09-04 實測：
    `since` 兩側都存在的邊有 19／32 條，屬性有變的 0 條）。

    所以它們只有在這裡被守著。不寫這條 ＝ 兩段沒有任何東西驗過的程式。
    """
    diff = Neo4jGraphResearchProvider._structural_diff
    known = {"mat:inp_substrate"}
    old = {"bottleneck": "mat:inp_substrate", "substitutability": 4,
           "sole_source": False, "qualification_status": "sampling"}
    new = {"bottleneck": "mat:inp_substrate", "substitutability": 5,
           "sole_source": True, "qualification_status": "qualified"}

    assert diff(old, new, known) == [
        ("capacity_constraint", "tightening", "substitutability 4 → 5"),
        ("capacity_constraint", "tightening", "sole_source 由否轉是"),
        ("qualification", "tightening", "qualification_status sampling → qualified"),
    ]
    # 反向必須是 loosening——不得只認一個方向
    assert [d for _, d, _ in diff(new, old, known)] == ["loosening"] * 3


def test_confidence_changes_alone_do_not_produce_events() -> None:
    """confidence／證據等級上升量的是「我們讀了幾份」，不是世界變了。"""
    diff = Neo4jGraphResearchProvider._structural_diff
    old = {"bottleneck": "mat:inp_substrate", "substitutability": 5,
           "confidence": 0.5, "evidence": "self_reported"}
    new = {**old, "confidence": 0.95, "evidence": "externally_corroborated"}
    assert diff(old, new, {"mat:inp_substrate"}) == []


# ---------------------------------------------------------------------------
# 6. 回填走廊：放行與收緊同時發生（L15）
# ---------------------------------------------------------------------------

_NODE = {"id": "doc_1", "url": "https://www.fool.com/x/2026/02/03/y/",
         "published_at": None, "retrieved_at": "2026-08-30"}


def _propose(**over):
    kwargs = {"doc_id": "doc_1", "prop": "published_at", "value": "2026-02-03",
              "method": "url_path", "basis": "URL 路徑", "node": _NODE,
              "today": date(2026, 9, 4)}
    return validate_proposal(**{**kwargs, **over})


def test_the_corridor_accepts_a_well_formed_backfill() -> None:
    proposal = _propose()
    assert proposal.value == date(2026, 2, 3)
    assert proposal.properties["published_at_backfilled"] == "2026-02-03"


@pytest.mark.parametrize("over,needle", [
    ({"prop": "substitutability"}, "白名單"),
    ({"prop": "evidence_tier"}, "白名單"),
    ({"method": "ingest_date"}, "定日方法"),
    ({"method": "retrieval_date"}, "定日方法"),
    ({"basis": "   "}, "補償控制"),
    ({"value": "2026-02-04"}, "不在 url 導出的日期裡"),
    ({"value": "2027-01-01", "method": "document_masthead"}, "在未來"),
    ({"value": "2026-09-02", "method": "document_masthead"}, "晚於 retrieved_at"),
    ({"node": None}, "既有節點"),
    ({"node": {**_NODE, "published_at": "2020-01-01"}}, "已經是"),
])
def test_the_corridor_refuses_everything_it_should(over, needle) -> None:
    """⚠ **拒絕才是這條走廊的重點。** 什麼都寫得進去 ＝ 一條繞過 pq2 的後門。

    特別注意 `substitutability`／`evidence_tier`：那些是判讀，仍走 graph admission。
    """
    with pytest.raises(DatingRejected, match=needle):
        _propose(**over)


def test_no_dating_method_means_ingest_date() -> None:
    """字彙裡刻意沒有「抓到的那天」——它會讓所有東西看起來都是最近才發表的。"""
    assert not any("retriev" in k or "ingest" in k for k in DATING_METHODS)


def test_url_rederivation_refuses_month_only_paths() -> None:
    """`/2026/jun/` 只有月份。補一個「1 號」進去是編造精度。"""
    assert dates_in_url("https://x.com/news_items/2026/jun/SIVERS.shtml") == ()
    assert dates_in_url("https://www.fool.com/a/2026/02/03/b/") == (date(2026, 2, 3),)
    assert dates_in_url("https://x.com/2026-02-03-post") == (date(2026, 2, 3),)
    assert dates_in_url(None) == ()


def test_supersede_keeps_the_old_value_visible() -> None:
    """更正既有值必須看得見——不從回填路徑默默通過。"""
    node = {**_NODE, "published_at": "2020-01-01"}
    proposal = _propose(node=node, supersede=True)
    assert "supersede 舊值 2020-01-01" in proposal.basis


# ---------------------------------------------------------------------------
# 7. 回填的事後抽查：basis 與現值脫鉤要看得見
# ---------------------------------------------------------------------------

def test_audit_detects_a_value_that_drifted_away_from_its_basis() -> None:
    """loader 重跑把值蓋掉、basis 還留著 → 這條要叫。

    空跑檢查：拿掉 `published_at_backfilled` 的比對 → 這條會紅。
    """
    problems = audit_backfills([{
        "id": "doc_1", "url": "https://x.com/a/2026/02/03/b/",
        "published_at": "2026-05-01", "method": "url_path",
        "basis": "URL 路徑", "backfilled": "2026-02-03",
    }])
    assert any("回填當時寫下的是 2026-02-03" in p for p in problems)


def test_audit_rederives_url_path_backfills() -> None:
    """宣稱「日期印在 URL 裡」的，audit 會拿現在的 url 再導一次。"""
    problems = audit_backfills([{
        "id": "doc_1", "url": "https://x.com/a/2026/02/03/b/",
        "published_at": "2026-05-01", "method": "url_path",
        "basis": "URL 路徑", "backfilled": "2026-05-01",
    }])
    assert any("重導得到" in p for p in problems)


def test_audit_passes_a_clean_backfill() -> None:
    assert audit_backfills([{
        "id": "doc_1", "url": "https://x.com/a/2026/02/03/b/",
        "published_at": "2026-02-03", "method": "url_path",
        "basis": "URL 路徑 x.com/a/2026/02/03/", "backfilled": "2026-02-03",
    }]) == []


def test_the_loader_cannot_wipe_a_backfilled_date_with_null() -> None:
    """抽取 JSON 沒帶日期時，重跑 loader **不得**把回填的日期洗掉。

    ⚠ 這條測字串而不是行為，因為那是一段 Cypher——但它守的風險是真的：
    `published_at` 是 as-of 投影的唯一時間線索，被 null 蓋掉的後果是回測重新
    看到未來，而且**不會有任何東西報錯**。

    空跑檢查：把 `coalesce($published_at, sd.published_at)` 改回
    `$published_at` → 這條會紅。
    """
    from loader.load_to_neo4j import MERGE_SOURCE_DOC

    assert "sd.published_at = coalesce($published_at, sd.published_at)" in MERGE_SOURCE_DOC
    assert "sd.retrieved_at = coalesce($retrieved_at, sd.retrieved_at)" in MERGE_SOURCE_DOC


def test_audit_rejects_a_method_outside_the_closed_vocabulary() -> None:
    problems = audit_backfills([{
        "id": "doc_1", "url": None, "published_at": "2026-02-03",
        "method": "guessed", "basis": "感覺", "backfilled": "2026-02-03",
    }])
    assert any("不在封閉字彙內" in p for p in problems)
