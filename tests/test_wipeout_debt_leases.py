"""負債燈只算借款、租賃另列（2026-11-10；failure log #118 第 3 次；使用者「#118 只做租賃那一半」）。

總債同時承載「到期要還、要再融資的借款」與 IFRS 16／ASC 842 掛上資產負債表的租約（L12）：IQE.L 2026-06-30 現金 4,160 萬、
總債 5,394 萬（其中租賃 4,253 萬）、營業現金流近四季 −392 萬英鎊——含租賃判紅、不含是淨現金（公司自己寫的 adjusted net cash）。

這份測試守三件事：
1. 燈比**借款**（總債扣掉同一份來源、同一季的租賃負債），總債與租賃照印在稽核層；
2. **分不出租賃不是租賃為 0**：沒有租賃的資料就照總債判，理由句說總債可能含租約；租賃比總債大（口徑對不上）不扣；
3. 租賃只跟同一份來源的總債走——人工觀測補的跑道不拿快照的租賃拼（PIT／provenance）；ETL 只讀 `mostRecentQuarter` 那一季的欄。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone

import pandas as pd
import pytest

from alpha.wipeout import LEASE_BASES, debt_flag
from engine_c.checklist import _parse_runway_inputs, get_probe_financial_baseline, get_wipeout_inputs
from engine_c.db import _ensure_sqlite_schema, upsert_snapshot
from engine_c.etl_yfinance import fetch_snapshot, lease_liabilities_from_balance_sheet
from shared.runway import derive_runway

AS_OF = "2026-11-10T00:00:00+00:00"


def _runway(*, cash, debt, fcf=-10.0, ocf=None, lease=None, source="yfinance.info"):
    out = {"cash_and_equivalents": cash, "total_debt": debt, "free_cash_flow_ttm": fcf, "source": source, "as_of": AS_OF,
           "status": "calculated", "runway_months": 12.0}
    if ocf is not None:
        out["operating_cash_flow_ttm"] = ocf
    if lease is not None:
        out["lease_liabilities"] = lease
    return out


# ---------------------------------------------------------------------------
# 1. 燈比借款；總債與租賃照印
# ---------------------------------------------------------------------------

def test_iqe_shape_is_green_on_borrowings_and_red_on_total_debt() -> None:
    iqe = _runway(cash=41.596, debt=53.939, ocf=-3.92, lease=42.528)
    flag = debt_flag(iqe)
    assert flag["colour"] == "green" and "租約另列" in flag["reason"] and flag["short"] == "現金比借款多"
    assert flag["inputs"]["total_debt"] == 53.939                     # 總債照印，不被改寫成借款
    assert flag["inputs"]["lease_liabilities"] == 42.528
    assert flag["inputs"]["borrowings"] == pytest.approx(11.411)
    assert flag["inputs"]["lease_basis"] == "separated"
    # 同一組數字分不出租賃 → 照舊紅，並說總債可能含租約
    old = debt_flag(_runway(cash=41.596, debt=53.939, ocf=-3.92))
    assert old["colour"] == "red" and "可能含租約" in old["reason"] and "欠的債" in old["reason"]
    assert old["inputs"]["lease_basis"] == "not_separated" and old["inputs"]["borrowings"] is None
    assert old["inputs"]["lease_liabilities"] is None


def test_net_borrowings_still_go_by_the_business() -> None:
    """扣掉租賃仍是借款比現金多 → 照本業判（MXL 型：借款 1.64 億 > 現金 0.81 億、營業現金流為負 → 紅）。"""
    red = debt_flag(_runway(cash=81.0, debt=186.0, ocf=-5.0, lease=21.9))
    assert red["colour"] == "red" and "借的錢" in red["reason"] and "借款到期" in red["reason"]
    assert red["short"] == "借款比現金多，本業又在燒錢" and "分不出" not in red["reason"]
    amber = debt_flag(_runway(cash=81.0, debt=186.0, ocf=5.0, lease=21.9))
    assert amber["colour"] == "amber" and amber["short"] == "借款比現金多，本業賺得還"
    no_ocf = debt_flag(_runway(cash=81.0, debt=186.0, fcf=3.0, lease=21.9))
    assert no_ocf["colour"] == "amber" and no_ocf["short"] == "借款比現金多，賺得還"
    burn = debt_flag(_runway(cash=81.0, debt=186.0, fcf=-3.0, lease=21.9))
    assert burn["colour"] == "red" and "分不出是本業燒錢還是擴產" in burn["reason"]


def test_equal_cash_and_borrowings_is_green() -> None:
    assert debt_flag(_runway(cash=20.0, debt=50.0, ocf=-1.0, lease=30.0))["colour"] == "green"


# ---------------------------------------------------------------------------
# 2. 分不出租賃 ≠ 租賃為 0；口徑對不上不扣
# ---------------------------------------------------------------------------

def test_zero_lease_is_a_measured_zero() -> None:
    """量到的 0（那一季總債裡沒有租賃這一項）＝借款就是總債：說「借的錢」、不補「分不出來」，綠燈也不說「租約另列」。"""
    amber = debt_flag(_runway(cash=50.0, debt=100.0, fcf=10.0, lease=0.0))
    assert amber["colour"] == "amber" and amber["inputs"]["lease_basis"] == "separated"
    assert "借的錢" in amber["reason"] and "分不出" not in amber["reason"]
    green = debt_flag(_runway(cash=150.0, debt=100.0, lease=0.0))
    assert green["colour"] == "green" and "租約另列" not in green["reason"]


def test_lease_larger_than_total_debt_is_not_subtracted() -> None:
    """扣了會算出負的借款、塗成綠——不扣，照總債判並說口徑對不上。"""
    flag = debt_flag(_runway(cash=50.0, debt=100.0, ocf=-1.0, lease=120.0))
    assert flag["colour"] == "red" and flag["inputs"]["lease_basis"] == "inconsistent"
    assert "口徑對不上" in flag["reason"] and flag["inputs"]["borrowings"] is None
    green = debt_flag(_runway(cash=150.0, debt=100.0, lease=120.0))
    assert green["colour"] == "green" and "租約另列" not in green["reason"]


@pytest.mark.parametrize("bad", [-1.0, "42", True])
def test_unusable_lease_values_count_as_not_separated(bad) -> None:
    flag = debt_flag(_runway(cash=50.0, debt=100.0, fcf=10.0, lease=bad))
    assert flag["inputs"]["lease_basis"] == "not_separated" and flag["inputs"]["lease_liabilities"] is None


def test_lease_bases_is_the_closed_list_the_lamp_emits() -> None:
    seen = {debt_flag(_runway(cash=1.0, debt=2.0, fcf=1.0, lease=x))["inputs"]["lease_basis"] for x in (None, 1.0, 3.0)}
    assert seen == set(LEASE_BASES)


# ---------------------------------------------------------------------------
# 3. 租賃只跟同一份來源的總債走
# ---------------------------------------------------------------------------

def test_runway_carries_leases_only_from_the_same_source() -> None:
    snap = {"cash_and_equivalents": 10.0, "total_debt": 5.0, "free_cash_flow_ttm": -1.0, "lease_liabilities": 3.0,
            "source": "yfinance.info", "as_of": AS_OF}
    assert derive_runway(snap)["lease_liabilities"] == 3.0
    manual = {"cash_and_equivalents": 10.0, "total_debt": 5.0, "free_cash_flow_ttm": -1.0,
              "source": "10-Q", "as_of": "2026-10-01T00:00:00+00:00"}
    assert "lease_liabilities" not in derive_runway(dict(snap, free_cash_flow_ttm=None), manual_observation=manual)
    assert derive_runway(dict(snap, free_cash_flow_ttm=None),
                         manual_observation=dict(manual, lease_liabilities=2.0))["lease_liabilities"] == 2.0
    assert "lease_liabilities" not in derive_runway(dict(snap, lease_liabilities=-1.0))


def test_manual_runway_inputs_carry_an_optional_lease_from_the_same_document() -> None:
    base = {"cash_and_equivalents": 41.6e6, "total_debt": 53.9e6, "free_cash_flow_ttm": -10e6}
    parsed = _parse_runway_inputs(json.dumps(dict(base, lease_liabilities=42.5e6)), "IQE H1 2026", AS_OF)
    assert parsed["lease_liabilities"] == 42.5e6
    for bad in ({}, {"lease_liabilities": True}, {"lease_liabilities": "42"}):
        assert "lease_liabilities" not in _parse_runway_inputs(json.dumps(dict(base, **bad)), "src", AS_OF)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _ensure_sqlite_schema(conn)
    return conn


def _snapshot(**overrides) -> dict:
    snap = {"ticker": "IQE.L", "snapshot_date": "2026-11-10", "gross_margin": None, "operating_margin": None,
            "revenue_ttm": None, "shares_outstanding": None, "cash_and_equivalents": 41.596e6, "total_debt": 53.939e6,
            "free_cash_flow_ttm": -10e6, "operating_cash_flow_ttm": -3.92e6, "lease_liabilities": 42.528e6,
            "ev_revenue": None, "pe_trailing": None, "pe_forward": None, "price": 20.0, "analyst_target_mean": None,
            "analyst_target_high": None, "analyst_target_low": None, "analyst_target_count": None,
            "fetched_at": "2026-11-10T01:00:00+00:00"}
    snap.update(overrides)
    return snap


def test_snapshot_round_trip_reaches_the_lamp_inputs() -> None:
    conn = _conn()
    assert "lease_liabilities" in {row[1] for row in conn.execute("PRAGMA table_info(financial_snapshots)")}
    upsert_snapshot(conn, _snapshot())
    assert get_probe_financial_baseline("IQE.L", conn=conn)["lease_liabilities"] == 42.528e6
    runway = get_wipeout_inputs("IQE.L", conn=conn)["runway"]
    assert runway["lease_liabilities"] == 42.528e6
    assert debt_flag(runway)["colour"] == "green"


def test_snapshot_without_lease_stays_not_separated() -> None:
    conn = _conn()
    upsert_snapshot(conn, _snapshot(lease_liabilities=None))
    runway = get_wipeout_inputs("IQE.L", conn=conn)["runway"]
    assert runway.get("lease_liabilities") is None
    assert debt_flag(runway)["inputs"]["lease_basis"] == "not_separated"


def test_manual_runway_never_borrows_the_snapshot_lease() -> None:
    """快照的自由現金流被清空 → 跑道取自人工觀測（另一份文件）：快照的租賃不得補進來。"""
    conn = _conn()
    upsert_snapshot(conn, _snapshot(free_cash_flow_ttm=None))
    payload = {"cash_and_equivalents": 41.596e6, "total_debt": 53.939e6, "free_cash_flow_ttm": -10e6,
               "operating_cash_flow_ttm": -3.92e6}
    conn.execute("INSERT INTO manual_fields (ticker, field_name, value, source_note, updated_at) VALUES (?,?,?,?,?)",
                 ("IQE.L", "runway_inputs", json.dumps(payload), "IQE H1 2026 interim", "2026-06-30T00:00:00+00:00"))
    conn.commit()
    runway = get_wipeout_inputs("IQE.L", conn=conn)["runway"]
    assert runway["source"] == "IQE H1 2026 interim"
    assert "lease_liabilities" not in runway
    assert debt_flag(runway)["colour"] == "red"   # 人工那份沒寫租賃 → 照總債判


def test_manual_required_without_manual_uses_the_snapshot_lease() -> None:
    """快照缺自由現金流、也沒有人工觀測：燈拿快照的現金與總債判（同一份），租賃也跟著同一份走。"""
    conn = _conn()
    upsert_snapshot(conn, _snapshot(free_cash_flow_ttm=None))
    runway = get_wipeout_inputs("IQE.L", conn=conn)["runway"]
    assert runway["status"] == "manual_required" and runway["source"] == "yfinance.info"
    assert runway["lease_liabilities"] == 42.528e6
    assert debt_flag(runway)["colour"] == "green"


# ---------------------------------------------------------------------------
# ETL：租賃只取 info.totalDebt 那一季的欄
# ---------------------------------------------------------------------------

Q3 = pd.Timestamp("2026-09-30")
Q2 = pd.Timestamp("2026-06-30")
Q1 = pd.Timestamp("2026-03-31")
NAN = float("nan")


def _frame(rows: dict, columns=(Q2, Q1)) -> pd.DataFrame:
    return pd.DataFrame(rows, index=list(columns)).T


def _lease(frame, mrq, total_debt):
    return lease_liabilities_from_balance_sheet(frame, mrq, total_debt)


def test_the_column_whose_total_debt_is_the_same_number_wins() -> None:
    """IQE.L 型：季報表 Total Debt 與 info 逐位相同。KSHINTL.NS 型：`mostRecentQuarter` 寫 6 月、info 的總債其實是 3 月那一欄
    （季報表沒有 6 月）——同一個數就是同一季，不看 mostRecentQuarter。"""
    iqe = _frame({"Total Debt": [53.939e6, 60e6], "Capital Lease Obligations": [42.528e6, 44e6],
                  "Long Term Capital Lease Obligation": [37.065e6, 1.0], "Current Capital Lease Obligation": [5.463e6, 1.0]})
    assert _lease(iqe, date(2026, 6, 30), 53.939e6) == 42.528e6
    assert _lease(iqe, None, 53.939e6) == 42.528e6
    ksh = _frame({"Total Debt": [3717.42e6, 3211.43e6], "Capital Lease Obligations": [304.84e6, 49.32e6]}, (Q3, Q1))
    assert _lease(ksh, date(2026, 6, 30), 3211.43e6) == 49.32e6
    # float32 轉出來的 info（MXL：186,004,992 vs 186,005,000）算同一個數
    mxl = _frame({"Total Debt": [186.005e6, 1.0], "Capital Lease Obligations": [21.943e6, 1.0]}, (Q3, Q2))
    assert _lease(mxl, None, 186_004_992.0) == 21.943e6


def test_a_column_within_a_week_needs_the_info_total_to_include_the_lease() -> None:
    """52／53 週制（AMD、LITE：mostRecentQuarter 9-26、欄標 9-30）與 info 跟季報表差一點（3234.TWO 3.983 億 vs 3.999 億）：
    取一週內的欄，info 的總債離「含租賃」比離「扣掉租賃」近才扣。"""
    tw = _frame({"Total Debt": [399.882e6, 151.4e6], "Capital Lease Obligations": [99.614e6, 100.0e6]})
    assert _lease(tw, date(2026, 6, 30), 398.307e6) == 99.614e6
    amd = _frame({"Total Debt": [8916e6, 4276e6], "Capital Lease Obligations": [1837e6, 1050e6]}, (Q3, Q2))
    assert _lease(amd, date(2026, 9, 26), 9211e6) == 1837e6
    # info 的總債其實就是借款（離扣掉租賃的數比較近）→ 不扣，扣了會把借款低估、塗成綠
    assert _lease(tw, date(2026, 6, 30), 300.5e6) is None
    # 超過一週不算同一季
    assert _lease(amd, date(2026, 10, 8), 9211e6) is None


def test_a_lagging_balance_sheet_cannot_separate_the_lease() -> None:
    """AXTI 型：info 已是第三季（1.166 億）、季報表只到第二季（0.860 億）——拿第二季的租賃扣第三季的總債是兩季拼一個值（INV-6）。"""
    axti = _frame({"Total Debt": [86.03e6, 70.773e6], "Capital Lease Obligations": [1.797e6, 1.902e6]})
    assert _lease(axti, date(2026, 9, 30), 116.606e6) is None
    assert _lease(axti, None, 116.606e6) is None
    assert _lease(pd.DataFrame(), date(2026, 6, 30), 1.0) is None
    assert _lease(axti, date(2026, 6, 30), None) is None


def test_lease_parts_and_measured_zero() -> None:
    parts = _frame({"Total Debt": [10.0, 12.0], "Long Term Capital Lease Obligation": [3.0, NAN],
                    "Current Capital Lease Obligation": [1.0, NAN]})
    assert _lease(parts, None, 10.0) == 4.0
    # 租賃列在、但那一季是 NaN，同一欄有 Total Debt → 量到的 0（一週內的欄同樣是 0、不必再核含不含）
    assert _lease(parts, None, 12.0) == 0.0
    assert _lease(parts, date(2026, 3, 29), 11.0) == 0.0
    no_debt = _frame({"Total Debt": [NAN, 5.0], "Capital Lease Obligations": [NAN, 1.0]})
    assert _lease(no_debt, date(2026, 6, 30), 7.0) is None     # 連總債都沒有 → 分不出
    lease_only = _frame({"Total Debt": [NAN, 5.0], "Capital Lease Obligations": [2.0, 1.0]})
    assert _lease(lease_only, date(2026, 6, 30), 7.0) is None  # 有租賃、沒總債 → 核不了含不含 → 分不出


def test_fetch_snapshot_reads_the_lease_of_most_recent_quarter(monkeypatch) -> None:
    epoch = datetime(2026, 6, 30, tzinfo=timezone.utc).timestamp()

    class FakeTicker:
        info = {"regularMarketPrice": 20.0, "totalCash": 41.596e6, "totalDebt": 53.939e6, "freeCashflow": -10e6,
                "mostRecentQuarter": epoch}
        quarterly_balance_sheet = _frame({"Total Debt": [53.939e6, 60e6], "Capital Lease Obligations": [42.528e6, 44e6]})

    class FakeYFinance:
        @staticmethod
        def Ticker(_ticker):
            return FakeTicker()

    monkeypatch.setattr("engine_c.etl_yfinance.yf", FakeYFinance())
    assert fetch_snapshot("IQE.L")["lease_liabilities"] == 42.528e6
    # 季報表落後一季：info 的總債對不到任何一欄、mostRecentQuarter 也不在一週內 → 分不出
    FakeTicker.info = dict(FakeTicker.info, totalDebt=70e6, mostRecentQuarter=datetime(2026, 9, 30,
                                                                                         tzinfo=timezone.utc).timestamp())
    assert fetch_snapshot("IQE.L")["lease_liabilities"] is None


def test_fetch_snapshot_survives_a_failing_balance_sheet(monkeypatch) -> None:
    class FakeTicker:
        info = {"regularMarketPrice": 20.0, "totalCash": 1.0, "totalDebt": 2.0, "freeCashflow": -1.0,
                "mostRecentQuarter": datetime(2026, 6, 30, tzinfo=timezone.utc).timestamp()}

        @property
        def quarterly_balance_sheet(self):
            raise RuntimeError("rate limited")

    class FakeYFinance:
        @staticmethod
        def Ticker(_ticker):
            return FakeTicker()

    monkeypatch.setattr("engine_c.etl_yfinance.yf", FakeYFinance())
    snap = fetch_snapshot("IQE.L")
    assert snap is not None and snap["lease_liabilities"] is None and snap["total_debt"] == 2.0
