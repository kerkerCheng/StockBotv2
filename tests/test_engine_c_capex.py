"""現金資本支出（個股頁 S3a，2026-10-08；需求錨序列的原料）：`fundamental_history` 的 `capex_quarter`／`capex_annual`。

守四件事：
1. 現金流量表在季報裡是**年初累計**：單季＝累計差分（Q2＝6M−Q1、Q3＝9M−6M、Q4＝FY−9M），標 derived、`filed` 取兩份較晚的
   （GOOGL／META 的形狀）；直接有 3 個月 fact 的季（MSFT、AMZN 的形狀）照用直接的、不衍生。
2. 時點（INV-6）：減數取「被減的那份累計申報時已知的最新版本」；直接的單季若要到隔年比較欄才出現，中間那一年仍有衍生值。
3. 年度只認會計年度：季報裡一年長、又不是任何一份年報的期間（AMZN 的近 12 個月欄）不當年度、不存、計數進報告——
   否則 FY−9M 會拿 TTM 去減。
4. 營收那類有單季的指標不受影響：半年累計照舊不存、不衍生。
"""
from __future__ import annotations

from datetime import date

from engine_c import history_backfill as hb

TODAY = date(2026, 10, 8)
FETCHED = "2026-10-08T03:00:00+00:00"
PPE = "PaymentsToAcquirePropertyPlantAndEquipment"


def _fact(start, end, val, accn, form, filed, unit="USD"):
    item = {"end": end, "val": val, "accn": accn, "form": form, "filed": filed}
    if start:
        item["start"] = start
    return unit, item


def _companyfacts(entries: dict) -> dict:
    facts: dict = {}
    for (ns, tag), items in entries.items():
        units: dict = {}
        for unit, item in items:
            units.setdefault(unit, []).append(item)
        facts.setdefault(ns, {})[tag] = {"units": units}
    return {"facts": facts}


def _rows(entries: dict):
    rows, rejected = hb.build_fundamental_rows(_companyfacts(entries), ticker="XYZ", filer="domestic_quarterly",
                                               today=TODAY, fetched_at=FETCHED)
    capex = [r for r in rows if r["metric"].startswith("capex")]
    return capex, rejected


def _ytd_year(tag: str = PPE) -> dict:
    """GOOGL／META 的形狀：Q1 是 3 個月，Q2、Q3 只有年初累計，年報給全年。"""
    return {("us-gaap", tag): [
        _fact("2025-01-01", "2025-03-31", 10.0, "Q1-25", "10-Q", "2025-04-25"),
        _fact("2025-01-01", "2025-06-30", 25.0, "Q2-25", "10-Q", "2025-07-25"),
        _fact("2025-01-01", "2025-09-30", 45.0, "Q3-25", "10-Q", "2025-10-25"),
        _fact("2025-01-01", "2025-12-31", 70.0, "FY-25", "10-K", "2026-02-05"),
    ]}


def test_quarters_are_differenced_from_year_to_date_and_carry_the_later_filing_date() -> None:
    capex, rejected = _rows(_ytd_year())
    q = {r["period_end"]: r for r in capex if r["metric"] == "capex_quarter"}
    assert {end: r["value"] for end, r in q.items()} == {
        "2025-03-31": 10.0, "2025-06-30": 15.0, "2025-09-30": 20.0, "2025-12-31": 25.0}
    assert q["2025-03-31"]["derived"] is None                                        # Q1 是直接的
    assert q["2025-06-30"]["derived"].startswith("6M−Q1") and q["2025-06-30"]["filed"] == "2025-07-25"
    assert q["2025-09-30"]["derived"].startswith("9M−6M") and q["2025-09-30"]["filed"] == "2025-10-25"
    assert q["2025-12-31"]["derived"].startswith("FY−9M") and q["2025-12-31"]["filed"] == "2026-02-05"
    assert q["2025-06-30"]["period_start"] == "2025-04-01" and q["2025-09-30"]["period_start"] == "2025-07-01"
    annual = [r for r in capex if r["metric"] == "capex_annual"]
    assert [(r["period_end"], r["value"]) for r in annual] == [("2025-12-31", 70.0)]
    assert not [x for x in rejected if x.get("metric", "").startswith("capex")]
    # 半年累計本身不存成任何一列
    assert not [r for r in capex if r["period_start"] == "2025-01-01" and r["period_end"] == "2025-06-30"]


def test_direct_three_month_quarters_are_used_as_they_are() -> None:
    """MSFT、AMZN 的形狀：每季都給 3 個月 fact（也給累計）——不衍生、不重複一列。"""
    entries = _ytd_year()
    entries[("us-gaap", PPE)] += [
        _fact("2025-04-01", "2025-06-30", 15.0, "Q2-25", "10-Q", "2025-07-25"),
        _fact("2025-07-01", "2025-09-30", 20.0, "Q3-25", "10-Q", "2025-10-25"),
    ]
    capex, _ = _rows(entries)
    q = [r for r in capex if r["metric"] == "capex_quarter"]
    assert sorted((r["period_end"], r["value"], bool(r["derived"])) for r in q) == [
        ("2025-03-31", 10.0, False), ("2025-06-30", 15.0, False), ("2025-09-30", 20.0, False),
        ("2025-12-31", 25.0, True)]


def test_a_direct_quarter_that_only_appears_a_year_later_does_not_blank_the_year_in_between() -> None:
    entries = _ytd_year()
    # 隔年 Q2 季報的比較欄才第一次給去年 Q2 的 3 個月數字
    entries[("us-gaap", PPE)].append(_fact("2025-04-01", "2025-06-30", 15.0, "Q2-26", "10-Q", "2026-07-24"))
    capex, _ = _rows(entries)
    q2 = sorted((r["filed"], r["value"], bool(r["derived"])) for r in capex
                if r["metric"] == "capex_quarter" and r["period_end"] == "2025-06-30")
    assert q2 == [("2025-07-25", 15.0, True), ("2026-07-24", 15.0, False)]


def test_the_subtrahend_is_the_version_known_when_the_later_ytd_was_filed() -> None:
    """Q1 後來被重編（下一年的比較欄給 12）：2025 年 7 月申報 H1 時只知道 10——Q2 衍生用 10，不用未來的 12。"""
    entries = _ytd_year()
    entries[("us-gaap", PPE)].append(_fact("2025-01-01", "2025-03-31", 12.0, "Q1-26", "10-Q", "2026-04-24"))
    capex, _ = _rows(entries)
    q2 = [r for r in capex if r["metric"] == "capex_quarter" and r["period_end"] == "2025-06-30"]
    assert [(r["value"], r["filed"]) for r in q2] == [(15.0, "2025-07-25")]
    assert "Q1-25" in q2[0]["derived"] and "Q1-26" not in q2[0]["derived"]


def test_a_trailing_twelve_month_column_in_a_quarterly_report_is_not_a_fiscal_year() -> None:
    """AMZN 的形狀：Q2 季報的現金流量有「近 12 個月」欄（2024-07-01 → 2025-06-30）——不是會計年度。"""
    entries = _ytd_year("PaymentsToAcquireProductiveAssets")
    entries[("us-gaap", "PaymentsToAcquireProductiveAssets")].append(
        _fact("2024-07-01", "2025-06-30", 65.0, "Q2-25", "10-Q", "2025-07-25"))
    capex, rejected = _rows(entries)
    annual = [r for r in capex if r["metric"] == "capex_annual"]
    assert [(r["period_start"], r["period_end"]) for r in annual] == [("2025-01-01", "2025-12-31")]
    ttm = [x for x in rejected if x.get("kind") == "not_fiscal_year"]
    assert ttm and ttm[0]["metric"] == "capex" and ttm[0]["key"][:2] == ["2024-07-01", "2025-06-30"]
    assert {r["tag"] for r in capex} == {"us-gaap:PaymentsToAcquireProductiveAssets"}


def test_a_full_year_repeated_in_a_quarterly_report_still_counts_as_that_fiscal_year() -> None:
    """APO 的形狀：季報重列去年整年（期間與年報相同）——它是會計年度，照存（與年報同一個數）。"""
    entries = _ytd_year()
    entries[("us-gaap", PPE)].append(_fact("2025-01-01", "2025-12-31", 70.0, "Q1-26", "10-Q", "2026-04-24"))
    capex, rejected = _rows(entries)
    annual = sorted((r["accession"], r["value"]) for r in capex if r["metric"] == "capex_annual")
    assert annual == [("FY-25", 70.0), ("Q1-26", 70.0)]
    assert not [x for x in rejected if x.get("kind") == "not_fiscal_year"]


def test_two_capex_tags_disagreeing_on_the_same_period_are_rejected_not_picked() -> None:
    entries = _ytd_year()
    entries[("us-gaap", "PaymentsToAcquireProductiveAssets")] = [
        _fact("2025-01-01", "2025-03-31", 11.0, "Q1-25", "10-Q", "2025-04-25")]
    capex, rejected = _rows(entries)
    assert not [r for r in capex if r["period_end"] == "2025-03-31"]
    assert any(x.get("metric") == "capex_quarter" and "不挑一個" in x.get("reason", "") for x in rejected)


def test_revenue_with_direct_quarters_does_not_store_or_difference_half_years() -> None:
    entries = {("us-gaap", "Revenues"): [
        _fact("2025-01-01", "2025-03-31", 100.0, "Q1-25", "10-Q", "2025-04-25"),
        _fact("2025-04-01", "2025-06-30", 120.0, "Q2-25", "10-Q", "2025-07-25"),
        _fact("2025-01-01", "2025-06-30", 220.0, "Q2-25", "10-Q", "2025-07-25"),
    ]}
    rows, rejected = hb.build_fundamental_rows(_companyfacts(entries), ticker="XYZ", filer="domestic_quarterly",
                                               today=TODAY, fetched_at=FETCHED)
    revenue = sorted((r["period_start"], r["period_end"], r["value"], r["derived"]) for r in rows
                     if r["metric"] == "revenue_quarter")
    assert revenue == [("2025-01-01", "2025-03-31", 100.0, None), ("2025-04-01", "2025-06-30", 120.0, None)]
    assert not [x for x in rejected if x.get("kind") == "irregular_period"]


def test_capex_is_a_late_metric_so_an_unmigrated_database_skips_it_and_counts() -> None:
    assert {"capex_quarter", "capex_annual"} <= hb.LATE_METRICS <= set(hb.METRICS)
    assert hb.YTD_CONCEPTS == frozenset({"capex"})
