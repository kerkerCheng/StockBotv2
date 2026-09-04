"""`scripts/alpha_expectation_gap.py`——Phase 4 缺掉的那個下游消費端。

⚠ 這一組測試守的不是「數字算得對」（那是 4 個除法），而是**三件會讓這張表變質的事**：
① 它被拿去排序；② 兩個分母不同的成長率被相減；③ 不可算被寫成 0。
三件都發生過或差點發生，所以每一件各有一條專屬測試。
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "alpha_expectation_gap", ROOT / "scripts" / "alpha_expectation_gap.py"
)
gap = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(gap)


class _Registry:
    companies = ()

    @staticmethod
    def company_id_for_ticker(ticker: str) -> str | None:
        return {"COHR": "co:coherent", "LITE": "co:lumentum"}.get(ticker)


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute(
        """
        CREATE TABLE financial_snapshots (
            id INTEGER PRIMARY KEY, ticker TEXT, snapshot_date TEXT, price REAL,
            pe_trailing REAL, pe_forward REAL, ev_revenue REAL,
            revenue_estimate_next_fy_growth REAL,
            revenue_estimate_next_fy_analysts INTEGER,
            analyst_target_mean REAL, fetched_at TEXT
        )
        """
    )
    return c


def _insert(c: sqlite3.Connection, ticker: str, **kw) -> None:
    row = {
        "snapshot_date": "2026-09-04", "price": 100.0, "pe_trailing": 60.0,
        "pe_forward": 20.0, "ev_revenue": 7.5,
        "revenue_estimate_next_fy_growth": 0.38,
        "revenue_estimate_next_fy_analysts": 18,
        "analyst_target_mean": 150.0, "fetched_at": "2026-09-04T00:00:00Z",
    }
    row.update(kw)
    cols = ", ".join(["ticker", *row])
    marks = ", ".join(["?"] * (len(row) + 1))
    c.execute(f"INSERT INTO financial_snapshots ({cols}) VALUES ({marks})",
              [ticker, *row.values()])


def _row(payload: dict, ticker: str) -> dict:
    return next(r for r in payload["rows"] if r["ticker"] == ticker)


# ── ① 不得排序 ────────────────────────────────────────────────────────────────

def test_output_order_is_the_input_order_not_sorted_by_any_number(conn) -> None:
    """**順序＝呼叫端傳進來的順序。**

    呼叫端傳的是瓶頸排序。這張表一旦自己重排，就等於在 `rank_bottlenecks()` 之外
    長出第二套排名，而 `AGENTS.md` 明訂唯一排序權威只有一個。更實際的risk 是：
    估值落差參與排序就從「脈絡」變成「訊號」——那類機制 2026-08-01 三次實測全敗、
    已整組移除。

    空跑檢查：在 `build_snapshot` 的 return 前加一行按 `target_vs_price` 排序 → 這條會紅。
    """
    # 刻意讓「估值最誘人」的排最後，「最不誘人」的排最前——任何按數字排序都會改變順序
    _insert(conn, "AAA", analyst_target_mean=101.0, pe_forward=59.0)
    _insert(conn, "BBB", analyst_target_mean=500.0, pe_forward=2.0)
    _insert(conn, "CCC", analyst_target_mean=300.0, pe_forward=10.0)

    payload = gap.build_snapshot(conn, ["AAA", "BBB", "CCC"], registry=_Registry)
    assert [r["ticker"] for r in payload["rows"]] == ["AAA", "BBB", "CCC"]

    payload = gap.build_snapshot(conn, ["CCC", "AAA", "BBB"], registry=_Registry)
    assert [r["ticker"] for r in payload["rows"]] == ["CCC", "AAA", "BBB"]


def test_duplicate_tickers_are_kept_because_the_ranking_has_duplicates(conn) -> None:
    """瓶頸排序裡同一家公司會出現多次（COHR 有 4 條邊在前 6 名），**不得去重**。

    去重會讓這張表與它要對齊的排序對不起來——使用者無從把第 3 列對回排序第 3 名。
    """
    _insert(conn, "COHR")
    payload = gap.build_snapshot(conn, ["COHR", "COHR", "COHR"], registry=_Registry)
    assert [r["ticker"] for r in payload["rows"]] == ["COHR", "COHR", "COHR"]


# ── ② 兩個成長率不可相減 ──────────────────────────────────────────────────────

def test_payload_never_exposes_a_merged_or_subtracted_growth_field(conn) -> None:
    """**不得有任何合併欄位。**

    `market_implied_eps_growth` 是每股盈餘成長，`analyst_revenue_growth` 是營收成長，
    分母不同（EPS 受利潤率與股數影響，營收不受）。COHR 實例：+244.6% vs +38.2%，
    差值 206pp 只反映「市場預期利潤率大幅擴張」，不是任何一種落差。

    只要 payload 裡出現一個看起來可以直接讀的合併數字，下游就一定會有人拿去用。
    """
    _insert(conn, "COHR")
    payload = gap.build_snapshot(conn, ["COHR"], registry=_Registry)
    keys = set(_row(payload, "COHR"))
    forbidden = {"growth_gap", "expectation_gap", "gap", "implied_minus_estimate",
                 "excess_growth", "spread"}
    assert not (keys & forbidden), f"出現合併欄位：{keys & forbidden}"
    assert "不得相減" in payload["note"]


def test_markdown_says_the_two_columns_must_not_be_subtracted(conn) -> None:
    """警語必須印在**表旁邊**，不是只寫在 docstring 裡——讀表的人不會去讀原始碼。"""
    _insert(conn, "COHR")
    text = gap.render_markdown(gap.build_snapshot(conn, ["COHR"], registry=_Registry))
    assert "不可相減" in text
    assert "不由估值重排" in text


# ── ③ 不可算就是不知道，不是 0 ────────────────────────────────────────────────

def test_loss_making_company_reports_a_reason_not_zero_growth(conn) -> None:
    """虧損公司沒有 trailing PE。那是**不知道**，不是「成長 0%」。

    這是 `alpha/contracts.py::test_none_is_not_zero` 同一條紀律在呈現層的延伸：
    寫 0 會讓 LITE／SOI.PA／MP／POET／IQE.L 這五檔看起來「市場沒給它們任何成長預期」，
    而事實是它們現在還在虧錢。
    """
    _insert(conn, "LITE", pe_trailing=None)
    row = _row(gap.build_snapshot(conn, ["LITE"], registry=_Registry), "LITE")
    assert row["market_implied_eps_growth"] is None
    assert "pe_trailing_missing" in row["unavailable"]
    assert row["status"] == "degraded"


def test_negative_forward_pe_is_rejected_not_turned_into_a_negative_ratio(conn) -> None:
    """forward PE 為負＝分析師預估下一年度仍虧損，比值**無意義**。

    若不擋，`60 / -43 - 1` 會算出 −2.4 並印成「−240%」——一個看起來像資訊、
    實際上什麼都不是的數字。POET 的 forward PE 現值就是 −43.1。
    """
    _insert(conn, "POET", pe_trailing=60.0, pe_forward=-43.1)
    row = _row(gap.build_snapshot(conn, ["POET"], registry=_Registry), "POET")
    assert row["market_implied_eps_growth"] is None
    assert "pe_forward_nonpositive" in row["unavailable"]


def test_every_unavailable_code_has_a_human_readable_reason() -> None:
    """封閉字彙：每個代碼都要講得出人話，否則使用者只看到一串英文 slug。

    ⚠ 這也擋住「隨手多寫一個代碼」——新增一種不可算就必須同時想清楚怎麼跟人解釋。
    """
    import inspect
    source = inspect.getsource(gap.build_snapshot) + inspect.getsource(gap._implied_eps_growth)
    emitted = {
        literal for literal in gap.UNAVAILABLE_REASONS
        if f'"{literal}"' in source
    }
    assert emitted, "至少該有一個代碼真的被用到"
    used_but_undocumented = {
        code for code in
        (line.split('"')[1] for line in source.splitlines() if 'unavailable.append("' in line)
        if code not in gap.UNAVAILABLE_REASONS
    }
    assert not used_but_undocumented, f"代碼沒有人話說明：{used_but_undocumented}"


def test_missing_snapshot_is_a_row_with_a_reason_not_a_dropped_ticker(conn) -> None:
    """沒有快照的標的**仍然出現在表上**（INV-3：不得靜默消失）。

    悄悄少一列，使用者會以為那檔不在候選裡。
    """
    payload = gap.build_snapshot(conn, ["NOPE"], registry=_Registry)
    assert [r["ticker"] for r in payload["rows"]] == ["NOPE"]
    assert payload["rows"][0]["unavailable"] == ["financial_snapshot_missing"]


# ── 數值正確性（最小限度） ────────────────────────────────────────────────────

def test_implied_eps_growth_is_trailing_over_forward_minus_one(conn) -> None:
    """PE 60 → 20 代表市場定價 EPS 要漲 2 倍。"""
    _insert(conn, "COHR", pe_trailing=60.0, pe_forward=20.0)
    row = _row(gap.build_snapshot(conn, ["COHR"], registry=_Registry), "COHR")
    assert abs(float(row["market_implied_eps_growth"]) - 2.0) < 1e-9


def test_target_vs_price_is_a_unit_free_ratio_so_no_fx_is_needed(conn) -> None:
    """目標價與現價同為交易所報價單位，比值無單位——**不需 FX、也不需 quote-unit 換算**。

    這是本表能同時容納 GBp 報價的 IQE.L 與日圓報價的 6324.T 的原因；
    `alpha_purity_snapshot.py` 的市值就沒有這個性質，所以那邊必須換算。
    """
    _insert(conn, "IQE.L", price=47.35, analyst_target_mean=61.333)
    row = _row(gap.build_snapshot(conn, ["IQE.L"], registry=_Registry), "IQE.L")
    assert abs(float(row["target_vs_price"]) - (61.333 / 47.35 - 1)) < 1e-9


def test_json_output_round_trips(conn) -> None:
    _insert(conn, "COHR")
    payload = gap.build_snapshot(conn, ["COHR"], registry=_Registry)
    assert json.loads(json.dumps(payload, ensure_ascii=False))["rows"][0]["ticker"] == "COHR"
