"""MOPS fetcher 的解析與挑選邏輯測試（不打網路）。

這支 fetcher 存在的理由是台股 source-trace 有幾個會讓人誤判成「查無資料」的坑，
每個坑都在本 session 實際踩過一次，所以逐一鎖進測試。
"""
from __future__ import annotations

from fetchers.mops import (
    DOC_KINDS,
    _form_code,
    latest_only,
    make_mops_doc_id,
    select_documents,
)

# 取自 3081／4971 的真實列表結構（欄位順序與 list_documents 的解析一致）。
DOCS = [
    {
        "co_id": "4971", "data_year": "114 年", "category": "股東會相關資料",
        "detail": "股東會年報(尚未適用永續揭露準則)",
        "filename": "2025_4971_20260623F04.pdf",
        "size": "3,107,906", "uploaded_at": "115/05/28 17:52:23",
    },
    {
        "co_id": "4971", "data_year": "114 年", "category": "股東會相關資料",
        "detail": "股東會年報(股東會後修訂本)",
        "filename": "2025_4971_20260623F11.pdf",
        "size": "3,157,372", "uploaded_at": "115/08/27 17:07:55",
    },
    {
        "co_id": "4971", "data_year": "114 年", "category": "股東會相關資料",
        "detail": "英文版-股東會年報(尚未適用永續揭露準則)",
        "filename": "2025_4971_20260623FE4.pdf",
        "size": "2,731,393", "uploaded_at": "115/05/12 17:59:06",
    },
    {
        "co_id": "4971", "data_year": "115 年", "category": "股東會相關資料",
        "detail": "年報前十大股東相互間關係表",
        "filename": "2026_4971_20260623F17.pdf",
        "size": "139,576", "uploaded_at": "115/05/18 15:42:34",
    },
]


def test_select_documents_excludes_english_by_default() -> None:
    """中文版是 issuer 正本；英文版只是譯本，預設不抓以免同一事實被算成兩份來源。"""
    picked = select_documents(DOCS, "annual_report")
    assert [d["filename"] for d in picked] == [
        "2025_4971_20260623F04.pdf",
        "2025_4971_20260623F11.pdf",
    ]


def test_select_documents_can_include_english() -> None:
    picked = select_documents(DOCS, "annual_report", include_english=True)
    assert len(picked) == 3


def test_select_documents_ignores_shareholder_relation_table() -> None:
    """「年報前十大股東相互間關係表」帶「年報」二字但不是年報本體。

    公司官網靜態抓取時只拿得到這一份，若把它當年報就會得出「年報沒有客戶集中度」
    的錯誤結論——那正是聯亞追源一度卡住的原因。
    """
    picked = select_documents(DOCS, "annual_report")
    assert all("關係表" not in d["detail"] for d in picked)


def test_unknown_kind_is_rejected() -> None:
    """kind 是封閉字彙：打錯應該報錯，而不是靜默回空集合被誤讀成「查無文件」。"""
    try:
        select_documents(DOCS, "not_a_kind")
    except ValueError as exc:
        assert "未登記的文件種類" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("未登記的 kind 應該 raise ValueError")


def test_latest_only_picks_the_newest_revision() -> None:
    """修訂本 supersede 原始版；上傳時間是民國年字串，字串序即時間序。"""
    picked = select_documents(DOCS, "annual_report")
    newest = latest_only(picked)
    assert len(newest) == 1
    assert newest[0]["filename"] == "2025_4971_20260623F11.pdf"


def test_doc_id_collides_across_revisions_unless_disambiguated() -> None:
    """同年度兩份修訂若共用 doc_id，後寫的會靜默覆蓋先寫的。

    實測（2026-08-28）：IET-KY 114 年度同時有 F04 原始版與 F11 股東會後修訂本，
    fetcher 印出兩行成功訊息、磁碟上卻只剩一個檔案。這是「成功與失敗在同一個訊號上
    同形」的形狀，故把兩種行為都鎖進測試。
    """
    f04 = "2025_4971_20260623F04.pdf"
    f11 = "2025_4971_20260623F11.pdf"

    assert make_mops_doc_id("4971", "annual_report", f04) == make_mops_doc_id(
        "4971", "annual_report", f11
    )

    assert make_mops_doc_id("4971", "annual_report", f04, disambiguate=True) != (
        make_mops_doc_id("4971", "annual_report", f11, disambiguate=True)
    )
    assert make_mops_doc_id("4971", "annual_report", f11, disambiguate=True).endswith("_f11")


def test_doc_id_uses_data_year_not_query_year() -> None:
    """MOPS 檔名首段是資料年度（西元）。查詢年度（民國）與資料年度差一年以上，
    doc_id 必須跟著資料年度走，否則 114 年度年報會被標成 115。"""
    assert make_mops_doc_id("3081", "annual_report", "2025_3081_20260527F04.pdf") == (
        "mops_3081_annual_report_2025"
    )


def test_form_code_extraction() -> None:
    assert _form_code("2025_4971_20260623F11.pdf") == "F11"
    assert _form_code("2025_3081_20260527F04.pdf") == "F04"
    assert _form_code("garbage.pdf") == "unknown"


def test_every_registered_kind_has_a_tier() -> None:
    """新增文件種類時必須同時決定 evidence_tier，否則會靜默落到預設值。"""
    from fetchers.mops import KIND_TIER

    assert set(DOC_KINDS) <= set(KIND_TIER)


# ---------------------------------------------------------------------------
# 坑 4（2026-09-04）：財報區與股東會區是兩個 mtype
# ---------------------------------------------------------------------------

def test_every_kind_declares_which_mops_region_it_lives_in() -> None:
    """`DOC_KINDS` 的每一種都要在 `KIND_MTYPE` 有對應，否則會靜默查錯區。

    空跑檢查：在 `DOC_KINDS` 加一種但不加 `KIND_MTYPE` → 這條會紅。
    """
    from fetchers.mops import DOC_KINDS, KIND_MTYPE

    assert set(DOC_KINDS) == set(KIND_MTYPE), (
        "新增文件種類時必須同時宣告它住哪一區："
        f"{set(DOC_KINDS) ^ set(KIND_MTYPE)}"
    )


def test_financial_statement_kinds_live_in_region_a_not_f() -> None:
    """⚠ **分部附註（IFRS 8）在財報區，不在股東會年報裡。**

    事發（2026-09-04）：3081 的股東會年報 112 頁抽得出 281,784 字，`部門`／`IFRS 8`
    命中 0 次，於是被記成「小型單一部門公司」——但那份文件**根本不含財務報表附註**
    （`Independent Auditor` 0 次）。從一份結構上不會有分部附註的文件得出「未揭露」，
    是 L11-5 的教科書案例。改抓 `mtype=A` 後，附註「十四、部門資訊」逐字寫著
    「歸屬為單一報導部門」——結論剛好相同，但**這次是證據，之前是巧合**。
    """
    from fetchers.mops import KIND_MTYPE

    assert KIND_MTYPE["consolidated_financial_statement"] == "A"
    assert KIND_MTYPE["separate_financial_statement"] == "A"
    assert KIND_MTYPE["annual_report"] == "F"


def test_the_download_error_message_names_the_region() -> None:
    """下載失敗時的訊息不得只說「檔名可能有誤」。

    ⚠ 原訊息是「檔名可能有誤，或該文件已下架」——但最常見的成因其實是
    **mtype 用錯區**，檔名完全正確。一個訊息承載兩種語意，下游只能猜（L12）。
    """
    import inspect

    from fetchers.mops import fetch_document

    source = inspect.getsource(fetch_document)
    assert "mtype={mtype}" in source
    assert "先確認 mtype 與列檔時相同" in source
