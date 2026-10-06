"""Phase 7 Step 7.0g-1：三個資料檢查的原始案例回放（plan A4；failure log #20、#23、#27）。

閉環收窄之後非倍率檔不再寫敘事，而這三個資料錯當初都是**寫非邊緣檔的敘事時**被人撞到的。
所以撤掉那些敘事之前，檢查本身要證明抓得到原始案例——數字照當時的原始資料寫死，拿掉檢查就紅。
"""
from __future__ import annotations

from alpha import closure


# ---- #20：6680.HK 的快照股數只算 H 股（市值低估約 5.7 倍）----

def test_replay_20_a_plus_h_snapshot_shares_are_flagged() -> None:
    rows = closure.share_count_mismatches({"6680.HK": (241_144_516.0, 1_360_000_000.0)})
    assert [r[0] for r in rows] == ["6680.HK"]
    assert 5.5 < rows[0][3] < 5.8


def test_a_page_without_filed_shares_is_listed_not_skipped() -> None:
    """比不了 ≠ 比過沒問題（INV-3）：沒有基期觀測的檔逐檔列出，港股加註 H 股。"""
    got = dict(closure.share_count_uncompared({
        "6680.HK": (241_144_516.0, None),
        "AXTI": (54_000_000.0, 47_000_000.0),
        "XPEV": (None, None),
    }, {"XPEV": "讀不到（RuntimeError）"}))
    assert set(got) == {"6680.HK", "XPEV"}
    assert "H 股" in got["6680.HK"]
    assert got["XPEV"] == "讀不到（RuntimeError）"
    line = " ".join(closure.render_share_count_coverage(1, tuple(got.items())))
    assert "比了 1 檔" in line and "比不了 2 檔" in line


# ---- #23：UMC 的快照營收（新台幣）被貼上基期的美元標籤，印成「2,507 億 USD」----

_UMC_SNAPSHOT_REVENUE_TWD = 250_707_148_800.0      # 快照 revenue_ttm（2026-10-05）
_UMC_BASE_REVENUE_USD = 7_572_623_000.0            # FY2025 20-F 美元便利換算（mo_b737e8a1…）


def test_replay_23_currency_label_error_is_flagged() -> None:
    """修法前：標籤取基期幣別 USD，值卻是快照的新台幣——換成美元時不換（它以為已經是 USD）。"""
    pairs = {"UMC": {
        "printed_value": _UMC_SNAPSHOT_REVENUE_TWD, "printed_currency": "USD",
        "printed_usd": _UMC_SNAPSHOT_REVENUE_TWD,
        "base_value": _UMC_BASE_REVENUE_USD, "base_currency": "USD", "base_usd": _UMC_BASE_REVENUE_USD,
    }}
    rows = closure.revenue_magnitude_mismatches(pairs)
    assert [r[0] for r in rows] == ["UMC"]
    assert 32 < rows[0][5] < 34
    assert "⚠⚠ 營收量級對不上：1 檔" in closure.render_revenue_magnitude(pairs)[0]


def test_correct_label_after_the_fix_is_not_flagged() -> None:
    """修法後：標籤是快照自己宣告的 TWD，換匯後與 20-F 基期差不到 10%——不得誤報（L16-4）。"""
    pairs = {"UMC": {
        "printed_value": _UMC_SNAPSHOT_REVENUE_TWD, "printed_currency": "TWD",
        "printed_usd": _UMC_SNAPSHOT_REVENUE_TWD / 31.37,
        "base_value": _UMC_BASE_REVENUE_USD, "base_currency": "USD", "base_usd": _UMC_BASE_REVENUE_USD,
    }}
    assert closure.revenue_magnitude_mismatches(pairs) == ()
    assert "0 檔" in closure.render_revenue_magnitude(pairs)[0]


def test_legitimate_growth_inside_the_band_is_not_flagged() -> None:
    """近四季對上一個會計年度，營收成長三倍是合法的——帶子不得把成長當成錯。"""
    pairs = {"NBIS": {"printed_value": 1.36e9, "printed_currency": "USD", "printed_usd": 1.36e9,
                      "base_value": 0.45e9, "base_currency": "USD", "base_usd": 0.45e9}}
    assert closure.revenue_magnitude_mismatches(pairs) == ()


def test_uncomparable_revenue_is_listed_with_its_reason() -> None:
    pairs = {
        "TSM": {"printed_value": 4.44e12, "printed_currency": "TWD", "printed_usd": None,
                "base_value": None, "base_currency": None, "base_usd": None,
                "missing": "同一年度 2 筆生效基期、幣別不一致"},
        "UMC": {"printed_value": _UMC_SNAPSHOT_REVENUE_TWD, "printed_currency": "TWD",
                "printed_usd": _UMC_SNAPSHOT_REVENUE_TWD / 31.37,
                "base_value": _UMC_BASE_REVENUE_USD, "base_currency": "USD", "base_usd": _UMC_BASE_REVENUE_USD},
    }
    assert closure.revenue_magnitude_uncompared(pairs) == (("TSM", "同一年度 2 筆生效基期、幣別不一致"),)
    cover = closure.render_revenue_magnitude(pairs)[1]
    assert "比了 1 檔" in cover and "TSM" in cover


def test_a_check_that_did_not_run_says_so() -> None:
    """materialize 還沒算 → 印「沒有跑」與理由，不印「0 檔」（沒有跑與沒有問題不得同形，L13）。"""
    lines = closure.render_revenue_magnitude(None, absence="materialize 還沒算這一項")
    assert len(lines) == 1 and "沒有跑" in lines[0] and "0 檔" not in lines[0]


# ---- #27：SOI.PA 的分部占比同一天兩筆生效，讀取端默默丟掉 ----

def test_replay_27_duplicate_live_observations_are_flagged() -> None:
    rows = closure.duplicate_live_observations({
        ("SOI.PA", "segment_revenue_share", "2026-03-31"): ("mo_cef1e324", "mo_9e7d3653"),
        ("AXTI", "backlog", "2026-06-30"): ("mo_only_one",),
    })
    assert [(r[0], r[1], r[2]) for r in rows] == [("SOI.PA", "segment_revenue_share", "2026-03-31")]


# ---- closure-gate 的接線：比不了的要回一列、讀不到候選板要說理由 ----

def test_share_pairs_return_a_row_for_every_page(monkeypatch) -> None:
    import webapp.__main__ as cli

    class _Snap:
        def __init__(self, shares):
            self.shares_outstanding = shares

    class _Actuals:
        gaap = {"diluted_shares": 2_000.0}
        non_gaap = None

    class _Provider:
        def fundamentals(self, ticker):
            if str(ticker) == "BAD":
                raise RuntimeError("boom")
            return _Snap(1_000.0), None

        def fiscal_year_results(self, ticker):
            return (_Actuals(), None) if str(ticker) == "HAS" else (None, "沒有生效的 fiscal_year_results。")

    import alpha.providers.fundamentals as fundamentals_mod
    monkeypatch.setattr(fundamentals_mod, "EngineCFundamentalsProvider", _Provider)
    pairs, reasons = cli._share_count_pairs(["HAS", "NONE", "BAD"])
    assert set(pairs) == {"HAS", "NONE", "BAD"}
    assert pairs["HAS"] == (1_000.0, 2_000.0)
    assert pairs["NONE"] == (1_000.0, None) and reasons["NONE"].startswith("沒有財報股數")
    assert pairs["BAD"] == (None, None) and "RuntimeError" in reasons["BAD"]


def test_revenue_pairs_absence_is_declared(tmp_path) -> None:
    import webapp.__main__ as cli

    class _Store:
        def __init__(self, payload):
            self.payload = payload

        def read(self, kind):
            assert kind == "candidates"
            return self.payload, None

    pairs, why = cli._revenue_magnitude_pairs(_Store(None))
    assert pairs is None and "還沒 materialize" in why
    pairs, why = cli._revenue_magnitude_pairs(_Store({"rows": []}))
    assert pairs is None and "data_checks" in why
    ok = {"data_checks": {"revenue_magnitude": {"pairs": {"UMC": {}}}}}
    assert cli._revenue_magnitude_pairs(_Store(ok)) == ({"UMC": {}}, None)
