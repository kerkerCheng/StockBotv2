"""Phase 7 批次二 E2（failure log #63；使用者 2026-10-21 Q2 A）：例行重訊叫醒的反證照（公司、主旨類別）分組、一組判一次。

守：①類別從重訊自己的主旨機械判、封閉字彙，認不得落「其他」；「取得或處分資產」不是例行；②醒來時附上類別；③佇列照（公司、類別）
分組，非重訊每條自成一組；④judge 一次收一組，有一筆不合法整組不寫；⑤判定記類別、計數器量例行占比；⑥喚醒條件不動。
"""
from __future__ import annotations

from datetime import date

import pytest

from engine_b import announcement_category as ac
from engine_b import event_watch as ew

C1 = "任一需求側客戶在正式文件宣布改用不經這個節點的替代路徑並量產出貨"


@pytest.mark.parametrize("subject, category", [
    ("公布注意交易資訊", "attention_trading"),
    ("本公司受邀參加法人說明會", "investor_conference"),
    ("澄清媒體報導", "insider_or_clarification"),
    ("公告本公司內部人持股轉讓事前申報", "insider_or_clarification"),
    ("代子公司公告取得機器設備", "asset_transaction"),
    ("公告本公司處分有價證券", "asset_transaction"),
    ("代子公司公告為他公司背書保證", "intercompany"),
    ("董事會決議股利分派", "other"),
    ("", "other"),
])
def test_categories_come_from_the_subject_and_unknown_falls_into_other(subject, category) -> None:
    assert ac.category_of(subject) == category


def test_asset_transactions_are_never_routine() -> None:
    """快接頭層反證 #3 的條件就是「取得或處分資產」——它不得被當成零內容的例行重訊。"""
    assert "asset_transaction" not in ac.ROUTINE and set(ac.ROUTINE) <= set(ac.CATEGORIES)


def _mops_lead(ticker="3081.TWO", subject="澄清媒體報導", first_seen="2026-10-17T01:00:00+00:00"):
    return {"source": f"mops:{ticker}", "source_class": "primary", "first_seen": first_seen,
            "published_at": "2026-10-17", "title": f"{ticker} 聯亞 重訊 2026-10-17：{subject}",
            "raw_text": f"{subject}\n\n說明……", "entities": {"company_ids": ["co:landmark_optoelectronics"], "tickers": [ticker]}}


def test_only_announcements_get_a_category() -> None:
    assert ac.lead_category(_mops_lead()) == {"ticker": "3081.TWO", "category": "insider_or_clarification",
                                              "subject": "澄清媒體報導"}
    assert ac.lead_category({"source": "edgar:COHR", "title": "COHR 8-K"}) is None
    assert ac.lead_category({"source": "edgar:COHR", "title": "COHR 8-K：Item 2.01",
                             "raw_text": "Completion of Acquisition or Disposition of Assets"}) is None


def _data_with(n, entity="co:landmark_optoelectronics"):
    data = {"watches": []}
    for i in range(n):
        ew.add_watch(data, kind=ew.SEMANTIC_KIND, disproof_ref=f"brief:co:x#{i}", source_ref=f"brief:co:x#{i}",
                     expires="2027-06-30", entities=[entity], condition=C1 + f"（第 {i} 條）", check_frequency="每季",
                     action_48h="重讀", today=date(2026, 10, 1), created_at="2026-10-01T00:00:00+00:00")
    return data


def test_an_announcement_wake_carries_its_category_and_the_queue_groups_by_company_and_category(monkeypatch) -> None:
    data = _data_with(3)
    leads = {"l_clarify": _mops_lead()}
    fired = ew.check_watches(data, leads=leads, today=date(2026, 10, 17))
    assert len(fired) == 3                                            # 喚醒條件不動：A 不減少叫醒
    assert all(w["woken_by"]["announcement"]["category"] == "insider_or_clarification" for w in data["watches"])
    single = _data_with(1, entity="co:win_semiconductor")["watches"][0]
    single.update(status="fired", woken_by={"lead_id": "l_edgar", "at": "2026-10-17T02:00:00+00:00"})
    groups = ew.semantic_queue_groups([*data["watches"], single], {**leads, "l_edgar": {"source": "edgar:X"}})
    assert [len(g["watches"]) for g in groups] == [3, 1]
    assert groups[0]["announcement"]["ticker"] == "3081.TWO" and groups[1]["announcement"] is None


def test_an_old_wake_without_the_annotation_is_grouped_from_the_lead_itself() -> None:
    data = _data_with(2)
    for w in data["watches"]:
        w.update(status="fired", woken_by={"lead_id": "l1", "at": "2026-10-16T00:00:00+00:00"})
    groups = ew.semantic_queue_groups(data["watches"], {"l1": _mops_lead(subject="公布注意交易資訊")})
    assert len(groups) == 1 and groups[0]["announcement"]["category"] == "attention_trading"


def test_one_judgment_for_a_group_records_the_category_and_a_bad_id_writes_nothing(tmp_path, monkeypatch) -> None:
    data = _data_with(3)
    ew.check_watches(data, leads={"l_clarify": _mops_lead()}, today=date(2026, 10, 17))
    path = tmp_path / "watches.json"
    monkeypatch.setattr(ew, "WATCHES_PATH", path)
    ew.save_watches(data)
    ids = [w["watch_id"] for w in data["watches"]]
    assert ew.main(["judge", *ids[:2], "ew_9999", "--touches", "no", "--note", "例行澄清，與替代路徑無關"]) == 2
    assert all(w["status"] == "fired" for w in ew.load_watches()["watches"])          # 整組不寫
    assert ew.main(["judge", *ids, "--touches", "no", "--note", "例行澄清，與替代路徑無關"]) == 0
    saved = ew.load_watches()["watches"]
    assert all(w["status"] == "active" for w in saved)
    assert all(w["judgments"][-1]["announcement_category"] == "insider_or_clarification" for w in saved)
    share = ew.routine_judgment_share({"watches": saved}, today=date.today())
    assert share["judgments"] == 3 and share["routine"] == 3 and share["with_category"] == 3
