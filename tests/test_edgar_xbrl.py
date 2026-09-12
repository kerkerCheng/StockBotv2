"""`fetchers/edgar_xbrl.py`：XBRL → 基期實績的四條收緊，每一條都有對應的實測事故。

全部用合成 fixture，不打網路。每個 fixture 的形狀都照 companyfacts 原文
（`facts.<namespace>.<tag>.units.<unit>[]`，每筆帶 start／end／val／accn／form／filed／fy）。
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from fetchers import edgar_xbrl as x


def _entry(start: str, end: str, val: float, *, accn: str = "0000000000-00-000000",
           form: str = "10-K", filed: str = "2026-02-01", fy: int = 2025) -> dict:
    return {"start": start, "end": end, "val": val, "accn": accn,
            "form": form, "filed": filed, "fy": fy, "fp": "FY"}


def _facts(**namespaces) -> dict:
    """`_facts(**{"us-gaap": {"Revenues": {"USD": [entry, ...]}}})`"""
    return {"facts": {ns: {tag: {"units": units} for tag, units in tags.items()}
                      for ns, tags in namespaces.items()}}


def _recent(days_ago: int = 60) -> tuple[str, str]:
    """回 (start, end)，end 距今 `days_ago` 天——避免測試被 `_MAX_BASELINE_AGE_DAYS` 卡住。"""
    end = date.today() - timedelta(days=days_ago)
    return (end - timedelta(days=364)).isoformat(), end.isoformat()


# ---------------------------------------------------------------------------
# 收緊 3：只收年報期間
# ---------------------------------------------------------------------------

def test_quarterly_and_non_annual_forms_are_not_annual_facts() -> None:
    """一季的數字被當成一年的基期，是靜默且昂貴的錯誤。"""
    facts = _facts(**{"us-gaap": {"Revenues": {"USD": [
        _entry("2025-01-01", "2025-12-31", 100.0),                       # ✓ 年度 10-K
        _entry("2025-10-01", "2025-12-31", 25.0),                        # ✗ 一季
        _entry("2025-01-01", "2025-12-31", 100.0, form="10-Q"),          # ✗ 非年報
        _entry("2025-01-01", "2025-12-31", 100.0, form="6-K"),           # ✗ 非年報
    ]}}})
    got = x.annual_facts(facts, "Revenues")
    assert len(got) == 1 and got[0].value == 100.0


def test_20f_counts_as_an_annual_form() -> None:
    """外國發行人的年報是 20-F。只放行 10-K 時六檔被誤判成「沒有年度事實」（2026-09-10 實測）。"""
    facts = _facts(**{"ifrs-full": {"Revenue": {"TWD": [
        _entry("2025-01-01", "2025-12-31", 900.0, form="20-F")]}}})
    assert len(x.annual_facts(facts, "Revenue", namespace="ifrs-full")) == 1
    assert "20-F" in x.ANNUAL_FORM_PREFIXES


def test_fact_without_accession_is_dropped() -> None:
    """沒有 accession 就沒有「一手來源的確切位置」，那筆就不再是 mechanical。"""
    facts = _facts(**{"us-gaap": {"Revenues": {"USD": [
        _entry("2025-01-01", "2025-12-31", 100.0, accn="")]}}})
    assert x.annual_facts(facts, "Revenues") == []


# ---------------------------------------------------------------------------
# 收緊 1：白名單歧異就拒絕
# ---------------------------------------------------------------------------

def test_disagreeing_whitelist_tags_refuse_instead_of_picking_one() -> None:
    facts = _facts(**{"us-gaap": {
        "Revenues": {"USD": [_entry("2025-01-01", "2025-12-31", 100.0)]},
        "SalesRevenueNet": {"USD": [_entry("2025-01-01", "2025-12-31", 111.0)]},
    }})
    fact, reason = x.pick_for_period(facts, ("Revenues", "SalesRevenueNet"), date(2025, 12, 31))
    assert fact is None and reason is not None and "不挑一個" in reason


def test_agreeing_whitelist_tags_are_fine() -> None:
    facts = _facts(**{"us-gaap": {
        "Revenues": {"USD": [_entry("2025-01-01", "2025-12-31", 100.0)]},
        "SalesRevenueNet": {"USD": [_entry("2025-01-01", "2025-12-31", 100.0)]},
    }})
    fact, reason = x.pick_for_period(facts, ("Revenues", "SalesRevenueNet"), date(2025, 12, 31))
    assert reason is None and fact is not None and fact.value == 100.0


def test_restated_value_takes_the_later_filing() -> None:
    """同一 tag 同一期間有原申報與重編值時取 filed 最新的；filed 日期會誠實留在 source_ref。"""
    facts = _facts(**{"us-gaap": {"Revenues": {"USD": [
        _entry("2025-01-01", "2025-12-31", 100.0, accn="A", filed="2026-02-01"),
        _entry("2025-01-01", "2025-12-31", 98.0, accn="B", filed="2027-02-01"),
    ]}}})
    fact, reason = x.pick_for_period(facts, ("Revenues",), date(2025, 12, 31))
    assert reason is None and fact is not None
    assert fact.value == 98.0 and fact.accession == "B"


# ---------------------------------------------------------------------------
# 收緊 4：多幣別單位不換算
# ---------------------------------------------------------------------------

def test_multiple_currency_units_refuse_rather_than_convert() -> None:
    facts = _facts(**{"us-gaap": {"Revenues": {
        "USD": [_entry("2025-01-01", "2025-12-31", 100.0)],
        "TWD": [_entry("2025-01-01", "2025-12-31", 3000.0)],
    }}})
    fact, reason = x.pick_for_period(facts, ("Revenues",), date(2025, 12, 31))
    assert fact is None and reason is not None and "不做換算" in reason


# ---------------------------------------------------------------------------
# 收緊 2：source_filed_at 是申報日，永遠不是今天（INV-6）
# ---------------------------------------------------------------------------

def test_source_filed_at_is_the_filing_date_never_today() -> None:
    start, end = _recent()
    filed = (date.today() - timedelta(days=30)).isoformat()
    facts = _facts(**{"us-gaap": {
        "Revenues": {"USD": [_entry(start, end, 100.0, filed=filed)]},
        "OperatingIncomeLoss": {"USD": [_entry(start, end, 10.0, filed=filed)]},
    }})
    payload, source_ref, reason = x.build_fiscal_year_results("TEST", facts)
    assert reason is None and payload is not None
    assert payload["source_filed_at"] == filed
    assert payload["source_filed_at"] != date.today().isoformat()
    assert source_ref is not None and "accession" in source_ref


# ---------------------------------------------------------------------------
# 兩個 2026-09-10 實測撞出來的靜默錯誤
# ---------------------------------------------------------------------------

def test_namespace_with_the_latest_year_wins_not_the_first_that_succeeds() -> None:
    """HIMX 回歸：`us-gaap` 停在 FY2017、`ifrs-full` 才是當期。先到先贏會拿到八年前的基期。"""
    start, end = _recent()
    facts = _facts(**{
        "us-gaap": {
            "Revenues": {"USD": [_entry("2017-01-01", "2017-12-31", 685.0, form="20-F")]},
            "OperatingIncomeLoss": {"USD": [_entry("2017-01-01", "2017-12-31", 8.0, form="20-F")]},
        },
        "ifrs-full": {
            "Revenue": {"USD": [_entry(start, end, 832.0, form="20-F")]},
            "ProfitLossFromOperatingActivities": {"USD": [_entry(start, end, 50.0, form="20-F")]},
        },
    })
    payload, _ref, reason = x.build_fiscal_year_results("HIMXLIKE", facts)
    assert reason is None and payload is not None
    assert payload["revenue"] == 832.0
    assert payload["xbrl_provenance"]["namespace"] == "ifrs-full"
    # 落選的那個要留下來，否則沒人知道曾經有一份 2017 的資料在旁邊
    assert payload["xbrl_provenance"]["namespaces_considered"]["us-gaap"] == "2017-12-31"


def test_stale_baseline_is_refused_not_silently_written() -> None:
    """TSM 回歸：companyfacts 最新只到 FY2024（距今 618 天），而 FY2025 在世界上存在。

    照寫會得到一個**看起來完全正常**、實際落後一整年的 forward view——沒有東西會變紅。
    """
    facts = _facts(**{"ifrs-full": {
        "Revenue": {"TWD": [_entry("2024-01-01", "2024-12-31", 2894.0, form="20-F")]},
        "ProfitLossFromOperatingActivities": {
            "TWD": [_entry("2024-01-01", "2024-12-31", 1322.0, form="20-F")]},
    }})
    payload, _ref, reason = x.build_fiscal_year_results("TSMLIKE", facts)
    assert payload is None
    assert reason is not None and "不寫過期基期" in reason


def test_negative_revenue_and_empty_facts_report_reasons_not_zeros() -> None:
    """缺就是缺——**永遠不補 0**（INV-3：「查不到了」不是合法 lifecycle）。"""
    payload, _ref, reason = x.build_fiscal_year_results("EMPTY", _facts())
    assert payload is None and reason is not None and "us-gaap" in reason and "ifrs-full" in reason


def test_operating_income_must_share_the_revenue_period() -> None:
    """營益率＝營業利益／營收；兩個數來自不同年度就是把兩年兜在一起。"""
    start, end = _recent()
    facts = _facts(**{"us-gaap": {
        "Revenues": {"USD": [_entry(start, end, 100.0)]},
        "OperatingIncomeLoss": {"USD": [_entry("2019-01-01", "2019-12-31", 10.0)]},
    }})
    payload, _ref, reason = x.build_fiscal_year_results("MISMATCH", facts)
    assert payload is None and reason is not None and "營業利益" in reason


def test_whitelists_are_written_down_not_inferred() -> None:
    """「哪個 tag 是 revenue」帶判讀成分，所以候選必須是寫死的清單，且要進 provenance。"""
    assert x.REVENUE_TAGS and x.OPERATING_INCOME_TAGS == ("OperatingIncomeLoss",)
    assert x.IFRS_OPERATING_INCOME_TAGS == ("ProfitLossFromOperatingActivities",)
    # IFRS 的營收刻意只收損益表那一行——把附註分解小計也放進來，歧異守則會擋掉整批合法的檔
    assert x.IFRS_REVENUE_TAGS == ("Revenue",)
    start, end = _recent()
    facts = _facts(**{"us-gaap": {
        "Revenues": {"USD": [_entry(start, end, 100.0)]},
        "OperatingIncomeLoss": {"USD": [_entry(start, end, 10.0)]},
    }})
    payload, _ref, _reason = x.build_fiscal_year_results("T", facts)
    assert payload is not None
    assert payload["xbrl_provenance"]["whitelist"]["revenue"] == list(x.REVENUE_TAGS)


def test_unavailable_is_an_error_not_an_empty_result() -> None:
    """取不到 ≠ 這家沒有財報。空 dict 會被下游讀成後者（L12 的一表兩義）。"""
    assert issubclass(x.XbrlUnavailable, RuntimeError)
    with pytest.raises(x.XbrlUnavailable):
        x.fetch_companyfacts(9999999999, timeout=5.0, retries=0)


# ---------------------------------------------------------------------------
# 收緊 9：companyfacts 可能落後 EDGAR，而落後時取到的資料**完全合法**
# ---------------------------------------------------------------------------


def test_latest_filed_reads_the_newest_filing_date_across_namespaces() -> None:
    facts = _facts(**{
        "us-gaap": {"Revenues": {"USD": [_entry("2025-01-01", "2025-12-31", 1.0, filed="2026-02-01")]}},
        "ifrs-full": {"Revenue": {"USD": [_entry("2025-01-01", "2025-12-31", 1.0, filed="2026-05-01")]}},
    })
    assert x.latest_filed(facts) == date(2026, 5, 1)


def test_latest_filed_on_empty_facts_is_none_not_today() -> None:
    assert x.latest_filed({"facts": {}}) is None


def test_companyfacts_lag_warns_when_edgar_has_a_newer_periodic_report(monkeypatch) -> None:
    """實測形狀（2026-09-12，CIK 813672）：快照停在 2026-05-01，EDGAR 已有 2026-07-29 的 10-Q。

    少掉的那一季**不會讓任何欄位報錯**——這正是它要被做成一個會自己出現的警語的理由。
    """
    facts = _facts(**{"us-gaap": {"Revenues": {"USD": [
        _entry("2025-01-01", "2025-12-31", 1.0, filed="2026-05-01")]}}})
    monkeypatch.setattr("fetchers.edgar.get_filings",
                        lambda cik, forms, n: [{"filed_date": "2026-07-29", "form_type": "10-Q"}])
    snapshot, newest, warning = x.companyfacts_lag(813672, facts)
    assert (snapshot, newest) == (date(2026, 5, 1), date(2026, 7, 29))
    assert warning is not None and "89" in warning


def test_companyfacts_lag_is_quiet_when_in_sync(monkeypatch) -> None:
    facts = _facts(**{"us-gaap": {"Revenues": {"USD": [
        _entry("2025-01-01", "2025-12-31", 1.0, filed="2026-07-31")]}}})
    monkeypatch.setattr("fetchers.edgar.get_filings",
                        lambda cik, forms, n: [{"filed_date": "2026-07-31", "form_type": "10-Q"}])
    assert x.companyfacts_lag(320193, facts)[2] is None


def test_companyfacts_lag_does_not_fabricate_a_warning_when_edgar_is_unreachable(monkeypatch) -> None:
    """「對照不到」與「沒問題」不得同形，但也不得冒充成警告——這裡選擇不下判斷。"""
    facts = _facts(**{"us-gaap": {"Revenues": {"USD": [
        _entry("2025-01-01", "2025-12-31", 1.0, filed="2026-05-01")]}}})

    def _boom(*_args, **_kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr("fetchers.edgar.get_filings", _boom)
    snapshot, newest, warning = x.companyfacts_lag(813672, facts)
    assert snapshot == date(2026, 5, 1) and newest is None and warning is None
