"""追蹤表三條 lane（Phase 5 Step 5.2；plan §0.4 A1、§3）：live／paper／history 分印、分母分開，各自對主題等權組算超額。

夾具全部離線：trade_log 寫在 tmp、敘事紀錄與主題等權組直接注入、價格由注入的 loader 給（不連 yfinance、不開舊店）。
斷言的是**每一格的數字與缺席種類**，不是函式會動（L13）。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from alpha.theme_cohort import CohortMember, ThemeCohort, cohort_return, series_return

ROOT = Path(__file__).resolve().parents[1]
TODAY = date(2026, 10, 2)


def _oist():
    spec = importlib.util.spec_from_file_location("oist_lanes", ROOT / "scripts" / "outcome_if_settled_today.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["oist_lanes"] = module
    spec.loader.exec_module(module)
    return module


OIST = _oist()


# ---------------------------------------------------------------------------
# 夾具
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _State:
    state: str


@dataclass(frozen=True)
class _Brief:
    """敘事紀錄的最小形狀（`select_brief` 與 paper lane 讀到的欄位）。"""

    brief_id: str
    company_id: str
    created_at: datetime
    record_version: str = "investor-brief/v2"
    retracted: bool = False
    candidate_state: _State | None = field(default=None)

    @property
    def created_on(self) -> date:
        return self.created_at.date()


def _at(day: str, hour: int = 5) -> datetime:
    return datetime.fromisoformat(f"{day}T{hour:02d}:46:00+00:00")


BRIEFS = {
    # 先有 v1、再有兩份 v2：錨點是**第一份 v2**（09-29），不是現行那份（10-01）
    "AAA": ([_Brief("ib_a1", "co:aaa", _at("2026-09-15"), record_version="investor-brief/v1"),
             _Brief("ib_a2", "co:aaa", _at("2026-09-29"), candidate_state=_State("priced_wait")),
             _Brief("ib_a3", "co:aaa", _at("2026-10-01"), candidate_state=_State("open"))], []),
    # 只有一份 v2；報價單位是 GBp（便士）
    "GGG.L": ([_Brief("ib_g1", "co:ggg", _at("2026-09-29"), candidate_state=_State("pass"))], []),
    # 只有 v1：不是 paper 列（filter 報告列出理由）
    "OLD": ([_Brief("ib_o1", "co:old", _at("2026-09-10"), record_version="investor-brief/v1")], []),
}

COHORT = ThemeCohort(
    cohort_id="tc_test", theme="測試題材",
    members=(CohortMember("AAA", "co:aaa", "成員"), CohortMember("MEM1", "co:mem1", "成員"),
             CohortMember("MEM2", "co:mem2", "成員")),
    excluded=(), reason="測試", decided_on=date(2026, 9, 30), pq2_ref=1,
    created_at=datetime(2026, 9, 30, tzinfo=timezone.utc))


def _series(start: date, values: list[float]) -> dict[date, float]:
    return {start + timedelta(days=i): v for i, v in enumerate(values)}


#: 09-25 起每天一根。AAA：09-29 收 100 → 10-02 收 120；MEM1：09-29 → 10-02 ＋10%；MEM2：＋0%（10-02 那根是 NaN，要被略過）
PRICES = {
    "AAA": _series(date(2026, 9, 25), [90, 95, 98, 99, 100, 105, 110, 120]),
    "GGG.L": _series(date(2026, 9, 25), [40, 41, 42, 43, 44, 45, 46, 55]),
    "MEM1": _series(date(2026, 9, 25), [10, 10, 10, 10, 10, 10.5, 10.8, 11]),
    "MEM2": {**_series(date(2026, 9, 25), [50, 50, 50, 50, 50, 50, 50]), date(2026, 10, 2): float("nan")},
    "LIVEX": _series(date(2026, 9, 25), [20, 21, 22, 23, 24, 25, 26, 30]),
    "EURX.F": _series(date(2026, 9, 25), [5, 5, 5, 5, 5, 5, 5, 6]),
}
UNITS = {"AAA": "USD", "GGG.L": "GBp", "MEM1": "USD", "MEM2": "USD", "LIVEX": "USD", "EURX.F": "USD"}
QUOTE_UNITS = {"co:aaa": "USD", "co:ggg": "GBp"}
BENCH = {"QQQ": _series(date(2026, 9, 1), [100.0] * 29 + [101.0] * 3),   # 09-29 收 100、09-30 起 101
         "SOXX": _series(date(2026, 9, 1), [200.0] * 32)}
BETA = {"QQQ", "LON:VWRA"}
HOLDINGS = {"LIVEX": {"company_id": "co:livex", "research_ticker": "LIVEX", "source": "registry_ticker"},
            "BACKX": {"company_id": "co:livex", "research_ticker": "LIVEX", "source": "registry_ticker"},
            "EURX.F": {"company_id": "co:eurx", "research_ticker": "EURX", "source": "registry_ticker"}}
LEADS = {"L1": {"lead_id": "L1", "source": "x:someone", "first_seen": "2026-07-25T09:00:00+00:00",
                "published_at": "2026-07-24", "entities": {"company_ids": ["co:aaa"]}},
         "L0": {"lead_id": "L0", "source": "edgar:AAA", "first_seen": "2026-07-22T15:00:00+00:00",
                "published_at": None, "entities": {"company_ids": ["co:aaa"]}}}

RECEIPT = {"version": "research-receipt/v1", "narrative": "present", "narrative_label": "有現行 v2 敘事",
           "declared": {"brief_id": "ib_live", "candidate_state": {"state": "open"},
                        "answers": {"priced_in": "no", "in_numbers": "yes"}}}
EVENTS = [
    # 1 筆 alpha 有收據（之後被賣出）、1 筆 backfilled、1 筆 beta、1 筆賣出、1 筆幣別對不上
    {"trade_id": "t1", "symbol": "LIVEX", "side": "buy", "broker": "IB", "currency": "USD", "price": 20.0,
     "shares": 10, "executed_at": "2026-09-25T10:00:00-04:00", "research_receipt": RECEIPT},
    {"trade_id": "t2", "symbol": "BACKX", "side": "buy", "broker": "IB", "currency": "USD", "price": 24.0,
     "shares": 5, "executed_at": "2026-09-29T10:00:00-04:00",
     "research_receipt": {"narrative": "backfilled", "backfill_reason": "Sheet 已有、trade_log 沒有"}},
    {"trade_id": "t3", "symbol": "QQQ", "side": "buy", "broker": "IB", "currency": "USD", "price": 600.0,
     "shares": 1, "executed_at": "2026-09-26T10:00:00-04:00"},
    {"trade_id": "t4", "symbol": "LIVEX", "side": "sell", "broker": "IB", "currency": "USD", "price": 26.0,
     "shares": 10, "executed_at": "2026-10-01T10:00:00-04:00"},
    {"trade_id": "t5", "symbol": "EURX.F", "side": "buy", "broker": "IB", "currency": "EUR", "price": 5.0,
     "shares": 100, "executed_at": "2026-09-28T10:00:00+02:00"},
]


def _write_log(tmp_path: Path, events=EVENTS) -> Path:
    path = tmp_path / "trade_log.jsonl"
    path.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events), encoding="utf-8")
    return path


def _loader(symbol: str, start: date):
    return dict(PRICES.get(symbol) or {}), UNITS.get(symbol)


def _resolve(row):
    return HOLDINGS.get(str(row.get("ticker")), {"company_id": None, "research_ticker": None, "source": None})


def _collect(tmp_path: Path, *, history=None, cohorts=None, events=EVENTS, **overrides):
    kwargs = dict(
        today=TODAY, price_loader=_loader, history_loader=lambda: (history or [], []),
        benchmark_loader=lambda symbols, start, end: {s: BENCH[s] for s in symbols},
        trade_log_path=_write_log(tmp_path, events), briefs=BRIEFS, leads=LEADS,
        cohorts=([COHORT], []) if cohorts is None else cohorts,
        is_beta=lambda s: s in BETA, resolve=_resolve, quote_unit_for=lambda cid, t: QUOTE_UNITS.get(cid))
    kwargs.update(overrides)
    return OIST.collect(**kwargs)


@pytest.fixture()
def collected(tmp_path, monkeypatch):
    # 排程時區固定為台北（`_local_date` 讀排程設定；夾具不讀設定檔）
    import engine_b.event_watch as ew

    monkeypatch.setattr(ew, "_local_timezone", lambda: timezone(timedelta(hours=8)))
    return _collect(tmp_path)


def _row(collected, lane, ticker):
    return next(r for r in collected["lanes"][lane]["rows"] if r["ticker"] == ticker)


# ---------------------------------------------------------------------------
# 主題等權組報酬（追蹤表與計分表共用的那一支）
# ---------------------------------------------------------------------------

def test_cohort_return_excludes_the_row_itself_and_lists_missing_members() -> None:
    """排除本檔（以 company_id 或研究 ticker）；取不到的成員列出、不進平均；一個都取不到回 None 不是 0。

    變異：拿掉排除本檔 → members_total 變 3、平均混進 AAA 自己的 +20%，這條紅。"""
    result = cohort_return(COHORT, start=date(2026, 9, 29), end=date(2026, 10, 2), series=PRICES,
                           exclude_company="co:aaa")
    assert result["excluded"] == ["AAA"] and result["members_total"] == 2 and result["members_used"] == 2
    # MEM1 +10%、MEM2 0%（10-02 是 NaN → 用 10-01 那根）→ 等權 +5%
    assert result["return"] == pytest.approx(0.05)
    nothing = cohort_return(COHORT, start=date(2026, 9, 29), end=date(2026, 10, 2), series={},
                            exclude_ticker="aaa")
    assert nothing["return"] is None and nothing["missing"] == ["MEM1", "MEM2"] and nothing["excluded"] == ["AAA"]


def test_series_return_skips_nan_and_never_looks_ahead() -> None:
    """NaN 收盤不收（yfinance 的未完成 K 棒）；錨點只取那天或之前（INV-6）；起點晚於終點回 None。"""
    assert series_return(PRICES["MEM2"], date(2026, 9, 29), date(2026, 10, 2)) == pytest.approx(0.0)
    assert series_return(PRICES["AAA"], date(2026, 9, 20), date(2026, 10, 2)) is None   # 錨點前沒有收盤
    assert series_return(PRICES["AAA"], date(2026, 10, 2), date(2026, 9, 29)) is None


def test_an_inverted_window_is_none_even_when_both_ends_land_on_the_same_bar() -> None:
    """R2 F3：要求的起點（10-05）晚於終點（10-02），兩端都落在 10-02 那一根——舊的比法只比 K 棒日期，算出 0.0。

    變異：拿掉 `series_return` 的 `start > end` 檢查 → 這裡回 0.0，這條紅。"""
    assert series_return(PRICES["AAA"], date(2026, 10, 5), date(2026, 10, 2)) is None
    assert series_return(PRICES["AAA"], date(2026, 10, 3), date(2026, 10, 4)) == pytest.approx(0.0)   # 窗裡沒交易：真的是 0


def test_membership_is_by_company_id_only_and_every_absence_carries_its_label() -> None:
    """INV-1：ticker 不是 identity——ticker 對得上、company_id 對不上＝不是組員；沒有 company_id＝identity_unresolved（不拿 ticker 猜）。
    每一筆缺席都帶 SSOT 的短標籤（L16：消費端不另寫對照表）。

    變異：`cohort_for_row` 改成 ticker 也算組員 → 第一條紅；拿掉沒有 company_id 的那一支 → 第二條紅。"""
    from alpha.theme_cohort import ROW_COHORT_ABSENCE_LABELS, cohort_for_row

    cohort, absence = cohort_for_row([COHORT], company_id="co:someone_else_named_aaa")
    assert cohort is None and absence["kind"] == "not_in_any_cohort"
    cohort, absence = cohort_for_row([COHORT], company_id=None)
    assert cohort is None and absence["kind"] == "identity_unresolved"
    assert absence["label"] == ROW_COHORT_ABSENCE_LABELS["identity_unresolved"]
    assert cohort_for_row([COHORT], company_id="co:aaa") == (COHORT, None)


# ---------------------------------------------------------------------------
# 三條 lane
# ---------------------------------------------------------------------------

def test_live_lane_takes_alpha_buys_from_the_trade_log_and_counts_beta_separately(collected) -> None:
    live = collected["lanes"]["live"]
    assert [r["trade_id"] for r in live["rows"]] == ["t1", "t5", "t2"]          # 成交時間序，不是報酬序
    assert live["beta_events"] == 1 and live["unmatched_sells"] == [] and live["problems"] == []
    sold = _row(collected, "live", "LIVEX")
    # 有收據：照抄當時宣告，不讀今天的敘事
    assert sold["receipt"] == {"status": "present", "label": "有現行 v2 敘事", "brief_id": "ib_live",
                               "candidate_state": "open", "answers": {"priced_in": "no", "in_numbers": "yes"}}
    # 同 symbol＋broker 的賣出把它結掉：終點是賣出價（20 → 26）
    assert sold["closed"]["trade_id"] == "t4" and sold["realized"] is True
    assert sold["absolute_return"] == pytest.approx(0.30)
    assert sold["anchor_date"] == date(2026, 9, 25) and sold["current_date"] == date(2026, 10, 1)


def test_backfilled_receipt_is_labelled_and_never_borrows_todays_narrative(collected) -> None:
    back = next(r for r in collected["lanes"]["live"]["rows"] if r["trade_id"] == "t2")
    assert back["receipt"]["status"] == "backfilled" and "當時沒有收據" in back["receipt"]["label"]
    assert back["execution_symbol"] == "BACKX" and back["company_id"] == "co:livex"        # 解析走 resolve_holding
    assert back["absence_kind"] == "no_price_series"                                         # BACKX 沒有序列：缺席不是 0


def test_currency_mismatch_is_an_absence_not_a_guessed_fx(collected) -> None:
    """成交 EUR、provider 序列是 USD → `currency_mismatch`，不猜匯率、不進聚合。

    變異：拿掉幣別比對 → 這列會算出 +20%，這條紅。"""
    row = next(r for r in collected["lanes"]["live"]["rows"] if r["trade_id"] == "t5")
    assert row["absence_kind"] == "currency_mismatch" and row.get("absolute_return") is None
    summary = OIST.lane_summary(collected["lanes"]["live"]["rows"], lane="live")
    assert summary["n"] == 3 and summary["measured"] == 1


def test_paper_lane_anchors_on_the_first_v2_not_the_current_one(collected) -> None:
    rows = collected["lanes"]["paper"]["rows"]
    assert [r["ticker"] for r in rows] == ["AAA", "GGG.L"]
    report = collected["lanes"]["paper"]["filter"]
    assert report == {"input": 3, "accepted": 2, "filtered": {"no_v2": ["OLD"], "ledger_unreadable": []}}
    aaa = _row(collected, "paper", "AAA")
    assert (aaa["brief_id"], aaa["anchor_date"], aaa["anchor_state"]) == ("ib_a2", date(2026, 9, 29), "priced_wait")
    assert (aaa["current_brief_id"], aaa["current_state"], aaa["v2_records"]) == ("ib_a3", "open", 2)
    assert aaa["earliest_v1"].startswith("2026-09-15")
    # 錨點＝09-29 收盤 100；終點＝10-02 收盤 120
    assert (aaa["anchor_raw"], aaa["current_raw"], aaa["absolute_return"]) == (100, 120, pytest.approx(0.20))
    # 首次點名它的 lead：first_seen 最早那則（edgar 07-22 早於 x 07-25）
    assert aaa["first_named_by"]["source"] == "edgar:AAA" and aaa["first_named_absence"] is None


def test_quote_unit_is_settled_on_both_ends_gbp_pence_is_not_pounds(collected) -> None:
    ggg = _row(collected, "paper", "GGG.L")
    assert ggg["anchor_ccy"] == "GBP" and ggg["anchor_price"] == pytest.approx(0.44)   # 44 便士 → 0.44 英鎊
    assert ggg["absolute_return"] == pytest.approx(55 / 44 - 1)
    assert ggg["first_named_absence"] == "no_lead_named"


def test_each_row_compares_only_with_its_own_cohort_and_non_members_are_named(collected) -> None:
    """多主題等權組 S1（選項 A）：組員跟自己的組比（排除本檔）；不是組員的列印 `not_in_any_cohort`，不借別的題材的組。

    變異：把 `cohort_for_row` 改回「只有一組就每列都比」→ LIVEX 會有對組超額（三家都比），這條紅。"""
    aaa = _row(collected, "paper", "AAA")
    assert aaa["theme_cohort"]["members_total"] == 2 and aaa["theme_cohort_return"] == pytest.approx(0.05)
    assert aaa["theme_cohort"]["cohort_id"] == "tc_test"
    assert aaa["excess_theme_cohort"] == pytest.approx(0.20 - 0.05)
    assert aaa["excess_QQQ"] == pytest.approx(0.20 - 0.01)
    live_row = _row(collected, "live", "LIVEX")
    assert live_row["theme_cohort_absence"]["kind"] == "not_in_any_cohort"
    assert "excess_theme_cohort" not in live_row and "theme_cohort" not in live_row
    assert live_row["excess_QQQ"] is not None                                # QQQ／SOXX 的超額照印
    info = collected["theme_cohort"]
    assert info["mode"] == "per_row" and info["absence"] is None
    assert [(c["cohort_id"], c["decided_on"], c["missing_members"]) for c in info["cohorts"]] == [
        ("tc_test", "2026-09-30", [])]
    live = OIST.lanes_payload(collected)["live"]["theme_cohort_excess"]
    assert live["absent"] == {"not_in_any_cohort": ["LIVEX"]} and live["n"] == 0   # 缺席逐檔列名（INV-3）
    assert "對組超額缺席 1 列（不是任何組的組員；not_in_any_cohort）：LIVEX" in "\n".join(OIST.render_lanes(collected))


COHORT_COOLING = ThemeCohort(
    cohort_id="tc_cool", theme="散熱",
    members=(CohortMember("GGG.L", "co:ggg", "成員"), CohortMember("MEM3", "co:mem3", "成員")),
    excluded=(), reason="測試", decided_on=date(2026, 10, 1), pq2_ref=2,
    created_at=datetime(2026, 10, 1, tzinfo=timezone.utc))


def test_a_second_cohort_leaves_the_first_cohorts_rows_untouched(tmp_path, collected) -> None:
    """驗收①：加第二組之後，第一組的組員列逐列相同；第二組的組員用自己的組；兩組都不是的照舊缺席。

    變異：讓每一列都拿「第一組」比 → GGG.L 會變成對光通訊組的超額，這條紅。"""
    prices = {**PRICES, "MEM3": _series(date(2026, 9, 25), [8, 8, 8, 8, 8, 8.4, 8.8, 8.8])}   # 09-29 → 10-02 ＋10%
    both = _collect(tmp_path, cohorts=([COHORT, COHORT_COOLING], []),
                    price_loader=lambda symbol, start: (dict(prices.get(symbol) or {}), UNITS.get(symbol, "USD")))
    before, after = _row(collected, "paper", "AAA"), _row(both, "paper", "AAA")
    assert after["excess_theme_cohort"] == pytest.approx(before["excess_theme_cohort"])
    assert after["theme_cohort"] == before["theme_cohort"]
    ggg = _row(both, "paper", "GGG.L")
    assert ggg["theme_cohort"]["cohort_id"] == "tc_cool" and ggg["theme_cohort"]["excluded"] == ["GGG.L"]
    assert ggg["excess_theme_cohort"] == pytest.approx((55 / 44 - 1) - 0.10)
    assert "excess_theme_cohort" not in _row(collected, "paper", "GGG.L")     # 只有一組時它不是組員
    assert _row(both, "live", "LIVEX")["theme_cohort_absence"]["kind"] == "not_in_any_cohort"
    assert [c["cohort_id"] for c in both["theme_cohort"]["cohorts"]] == ["tc_test", "tc_cool"]


def test_lanes_keep_separate_denominators(tmp_path, monkeypatch) -> None:
    """三條 lane 各算各的：history 的等權與三量只看 history 的列。

    變異：把 paper 的列併進 history 的分母 → history 的 n 與等權都變，這條紅。"""
    import engine_b.event_watch as ew

    monkeypatch.setattr(ew, "_local_timezone", lambda: timezone(timedelta(hours=8)))
    history = [{"ticker": "HIST", "company_id": "co:hist", "anchor_date": date(2026, 8, 1),
                "current_date": date(2026, 10, 2), "absolute_return": -0.10, "peak_return": 0.05, "note": []}]
    collected = _collect(tmp_path, history=history)
    payload = OIST.lanes_payload(collected)
    assert payload["history"]["n"] == 1 and payload["history"]["aggregate"]["absolute"] == pytest.approx(-0.10)
    assert payload["paper"]["n"] == 2 and payload["paper"]["aggregate"]["absolute"] == pytest.approx(
        (0.20 + 55 / 44 - 1) / 2)
    assert payload["live"]["measured"] == 1
    assert payload["paper"]["measurement_start"] == "2026-09-29"
    # 錨點偏差跟著 lane 走：history 那句「錨點是入圖日」不得出現在 paper／live
    assert "入圖日" in payload["history"]["power_law"]["known_biases"][-1]
    assert "寫下判斷那天" in payload["paper"]["power_law"]["known_biases"][-1]
    assert "真實成交價" in payload["live"]["power_law"]["known_biases"][-1]


def test_missing_cohort_is_not_yet_recorded_and_excess_stays_absent(tmp_path, collected) -> None:
    empty = _collect(tmp_path, cohorts=([], []))
    assert empty["theme_cohort"]["absence"]["kind"] == "not_yet_recorded"
    assert all("excess_theme_cohort" not in r for r in empty["lanes"]["paper"]["rows"])
    assert {r["theme_cohort_absence"]["kind"] for r in empty["lanes"]["paper"]["rows"]} == {"not_yet_recorded"}


def _lane_balance(collected) -> dict:
    """每條 lane：有對組超額的列數＋各種缺席的列數，對分母（量得到報酬的列數）。"""
    out = {}
    for lane, summary in OIST.lanes_payload(collected).items():
        ex = summary["theme_cohort_excess"]
        out[lane] = (ex["n"] + sum(len(v) for v in ex["absent"].values()), ex["of"])
    return out


def test_every_measured_row_is_either_compared_or_named_absent(tmp_path, collected) -> None:
    """R2 C2：量得到報酬的列，不是有對組超額、就是具名缺席——每條 lane「有值＋缺席＝分母」。
    事發：組員 300308.SZ 的組員們都取不到價，它既不在 n、也不在缺席名單（paper 12＋45＝57，分母 58）。

    變異：拿掉 `theme_cohort_unpriced` 那一支 → 下面那一組的 lane 對不起來，這條紅。"""
    assert all(have == of for have, of in _lane_balance(collected).values())
    lonely = ThemeCohort(cohort_id="tc_lonely", theme="只有一個有價的組員",
                         members=(CohortMember("AAA", "co:aaa", "成員"), CohortMember("NOPX", "co:nopx", "成員")),
                         excluded=(), reason="測試", decided_on=date(2026, 9, 30), pq2_ref=4,
                         created_at=datetime(2026, 9, 30, tzinfo=timezone.utc))
    unpriced = _collect(tmp_path, cohorts=([lonely], []))
    aaa = _row(unpriced, "paper", "AAA")
    assert aaa["theme_cohort_absence"]["kind"] == "theme_cohort_unpriced" and "NOPX" in aaa["theme_cohort_absence"]["reason"]
    assert aaa["theme_cohort_absence"]["label"] == "組員都取不到價" and "excess_theme_cohort" not in aaa
    assert all(have == of for have, of in _lane_balance(unpriced).values())
    paper = OIST.lanes_payload(unpriced)["paper"]["theme_cohort_excess"]
    assert paper["absent"]["theme_cohort_unpriced"] == ["AAA"]
    assert paper["absent_labels"]["theme_cohort_unpriced"] == "組員都取不到價"


def test_a_narrative_written_after_the_last_close_is_not_yet_measurable_not_zero(tmp_path, monkeypatch) -> None:
    """R2 F3：敘事寫在最後一根收盤之後（錨點 10-03、序列停在 10-02）→ `no_close_since_anchor`，不是 0.0，也不進聚合；
    live 的對稱面：成交在最後一根收盤之後，同樣缺席。

    變異：拿掉 `_price_paper_row`（或 `_price_live_row`）那道檢查 → 那一列會算出報酬，這條紅。"""
    import engine_b.event_watch as ew

    monkeypatch.setattr(ew, "_local_timezone", lambda: timezone(timedelta(hours=8)))
    briefs = {**BRIEFS, "LATE": ([_Brief("ib_l1", "co:late", _at("2026-10-02", 22), candidate_state=_State("open"))], [])}
    prices = {**PRICES, "LATE": _series(date(2026, 9, 25), [10, 10, 10, 10, 10, 10, 10, 11])}
    events = EVENTS + [{"trade_id": "t6", "symbol": "LIVEX", "side": "buy", "broker": "IB", "currency": "USD",
                        "price": 31.0, "shares": 1, "executed_at": "2026-10-03T10:00:00-04:00", "research_receipt": RECEIPT}]
    late = _collect(tmp_path, briefs=briefs, events=events, today=date(2026, 10, 3),
                    price_loader=lambda symbol, start: (dict(prices.get(symbol) or {}), UNITS.get(symbol, "USD")))
    row = _row(late, "paper", "LATE")
    assert row["absence_kind"] == "no_close_since_anchor" and row.get("absolute_return") is None
    assert "還量不到" in row["note"][-1]
    t6 = next(r for r in late["lanes"]["live"]["rows"] if r["trade_id"] == "t6")
    assert t6["absence_kind"] == "no_close_since_anchor" and t6.get("absolute_return") is None
    summary = OIST.lane_summary(late["lanes"]["paper"]["rows"], lane="paper")
    assert summary["measured"] == 2 and summary["n"] == 3                  # LATE 在列，但不在「量得到報酬」的分母裡
    assert all(have == of for have, of in _lane_balance(late).values())


def test_a_member_of_two_cohorts_is_ambiguous_not_guessed(tmp_path, collected) -> None:
    """同一家公司同時是兩組的組員 → 那一列 `ambiguous_membership`（列出兩組 id），不猜；其他列不受影響。"""
    other = ThemeCohort(cohort_id="tc_other", theme="另一個題材",
                        members=(CohortMember("AAA", "co:aaa", "成員"), CohortMember("MEM2", "co:mem2", "成員")),
                        excluded=(), reason="測試", decided_on=date(2026, 9, 30), pq2_ref=3,
                        created_at=datetime(2026, 9, 30, tzinfo=timezone.utc))
    two = _collect(tmp_path, cohorts=([COHORT, other], []))
    aaa = _row(two, "paper", "AAA")
    assert aaa["theme_cohort_absence"]["kind"] == "ambiguous_membership"
    assert aaa["theme_cohort_absence"]["cohort_ids"] == ["tc_test", "tc_other"] and "excess_theme_cohort" not in aaa
    assert two["theme_cohort"]["absence"] is None


def test_unreadable_ledger_is_upstream_unavailable_on_every_row_not_not_in_any_cohort(tmp_path) -> None:
    """組 ledger 讀不到＝上游缺席：每一列照抄 `upstream_unavailable`，**不得**變成「不是組員」（L12：兩種沒有不同形）。"""
    class _Broken(tuple):
        def __getitem__(self, index):
            raise OSError("ledger unreadable")

    broken = _collect(tmp_path, cohorts=_Broken())
    assert broken["theme_cohort"]["absence"]["kind"] == "upstream_unavailable"
    assert {r["theme_cohort_absence"]["kind"] for r in broken["lanes"]["paper"]["rows"]} == {"upstream_unavailable"}


def test_price_cap_truncates_members_first_and_prints_what_was_cut(tmp_path, collected) -> None:
    capped = _collect(tmp_path, max_symbols=5)
    budget = capped["price_budget"]
    assert budget["truncated"] and budget["fetched"] == 5 and budget["requested"] > 5
    assert set(budget["truncated"]) <= {"MEM1", "MEM2", "AAA", "GGG.L"}          # 基準永遠留著、成交先於組成員
    assert "QQQ" not in budget["truncated"] and "SOXX" not in budget["truncated"]


def test_empty_lanes_print_no_rows_yet_never_zero_percent(tmp_path, collected) -> None:
    none = _collect(tmp_path, events=[], briefs={})
    lines = "\n".join(OIST.render_lanes(none))
    assert "還沒有列——trade_log 還沒有任何 alpha 成交事件" in lines
    assert "還沒有列——還沒有任何一檔寫下 v2 敘事" in lines
    assert "beta 事件 0 不進 lane" in lines


# ---------------------------------------------------------------------------
# 聚合檔：既有四欄一字不動、`--no-benchmark` 不寫
# ---------------------------------------------------------------------------

def test_persist_keeps_the_four_fields_and_adds_lanes(tmp_path, monkeypatch, collected) -> None:
    monkeypatch.chdir(tmp_path)
    lanes = OIST.lanes_payload(collected)
    OIST._persist_aggregate(n=22, ew_abs=0.0866, ew_excess=0.0403, power={"n": 22}, lanes=lanes,
                            theme_cohort=collected["theme_cohort"])
    OIST._persist_aggregate(n=22, ew_abs=0.0870, ew_excess=0.0410, power={"n": 22}, lanes=lanes,
                            theme_cohort=collected["theme_cohort"])
    path = next(tmp_path.rglob("outcome_aggregate.jsonl"))                      # 腳本寫的相對路徑落在 tmp 底下
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1                                                        # 同日去重照舊
    row = rows[0]
    assert {k: row[k] for k in ("n", "equal_weight_absolute", "equal_weight_excess", "benchmark")} == {
        "n": 22, "equal_weight_absolute": 0.0870, "equal_weight_excess": 0.0410, "benchmark": "QQQ"}
    assert set(row["lanes"]) == {"live", "paper", "history"} and row["lanes"]["paper"]["n"] == 2
    assert row["theme_cohort"] == {"mode": "per_row", "absence": None,
                                   "cohorts": [{"cohort_id": "tc_test", "theme": "測試題材", "decided_on": "2026-09-30"}]}


# ---------------------------------------------------------------------------
# 下游：positions artifact v2 與心跳段 4（數字出現在消費端，L13）
# ---------------------------------------------------------------------------

def _artifact(collected, **kw):
    from webapp.materialize import positions_lanes

    from test_webapp_positions import fake_positions_payload

    return fake_positions_payload(lanes=positions_lanes(OIST, collected), theme_cohort=collected["theme_cohort"],
                                  price_budget=collected["price_budget"], **kw)


def test_positions_artifact_v2_carries_the_three_lanes_verbatim(collected) -> None:
    from webapp.contracts import validate_state_artifact

    payload = _artifact(collected)
    validate_state_artifact("positions", payload)
    assert payload["schema_version"] == "stockbot-app/positions/3"
    lanes = payload["lanes"]
    assert set(lanes) == {"live", "paper", "history"} and lanes["history"]["rows_in"] == "rows"
    assert [r["ticker"] for r in lanes["paper"]["rows"]] == ["AAA", "GGG.L"]
    assert lanes["paper"]["rows"][0]["anchor_date"] == "2026-09-29"                # 日期序列化，值照抄
    assert lanes["live"]["beta_events"] == 1 and lanes["paper"]["filter"]["filtered"]["no_v2"] == ["OLD"]
    assert [c["cohort_id"] for c in payload["theme_cohort"]["cohorts"]] == ["tc_test"]
    assert lanes["live"]["rows"][0]["theme_cohort_absence"]["kind"] == "not_in_any_cohort"   # 非組員的理由跟著列走到 APP
    assert any("paper lane 的錨點是**我們寫下判斷那天**" in s for s in payload["this_is_not"])


def test_freshness_identity_follows_lane_membership_not_prices(collected) -> None:
    import copy

    base = _artifact(collected)
    moved = copy.deepcopy(collected)
    for row in moved["lanes"]["paper"]["rows"]:
        row["absolute_return"] = (row.get("absolute_return") or 0) + 0.5           # 價格變了：不算認知變化
    assert _artifact(moved)["freshness_identity"] == base["freshness_identity"]
    fewer = copy.deepcopy(collected)
    fewer["lanes"]["paper"]["rows"] = fewer["lanes"]["paper"]["rows"][:1]           # 少一檔 paper：算
    assert _artifact(fewer)["freshness_identity"] != base["freshness_identity"]


def test_heartbeat_section_four_prints_each_lane_and_snapshot_keys(tmp_path, collected) -> None:
    import crons.heartbeat as hb
    from webapp.store import StateArtifactStore

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    StateArtifactStore(state_dir).write(_artifact(collected))
    text = "\n".join(hb.build_positions(state_dir=state_dir).lines)
    # 夾具的 history lane 是 0 列（舊店的列住 artifact 的 `rows`，由別的夾具給）
    assert "追蹤表 history 0｜paper 2｜live 3（beta 事件 1 不進 lane）｜主題等權組 1 組（每列只比自己的組）" in text
    assert "敘事前已漲（paper）" in text
    assert "paper（第一份 v2 敘事日起）：2 檔｜量測起始 2026-09-29" in text and "對主題等權組超額" in text
    # live 3 列只有 1 列算得出報酬（另兩列缺席）：三量的分母是 1，不是 3
    assert "live（trade_log 成交）：1 檔｜量測起始 2026-09-25" in text
    values = hb.collect_snapshot(now=datetime(2026, 10, 2, tzinfo=timezone.utc), state_dir=state_dir,
                                 leads_path=tmp_path / "none.json", thesis_path=tmp_path / "none.json",
                                 run_record_path=None, capture_dir=None)
    assert values["positions.lane.paper.n"] == 2 and values["positions.lane.live.n"] == 3
    assert values["positions.lane.paper.reached_2x_ever"] == 0


def test_heartbeat_says_absent_when_an_old_artifact_has_no_lanes(tmp_path) -> None:
    import crons.heartbeat as hb
    from webapp.store import StateArtifactStore

    from test_webapp_positions import fake_positions_payload

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    StateArtifactStore(state_dir).write(fake_positions_payload())
    text = "\n".join(hb.build_positions(state_dir=state_dir).lines)
    assert "追蹤表三條 lane：這份 positions artifact 還沒有 lanes（下一次 materialize --positions 補上；不是 0）" in text


def test_a_lane_that_cannot_be_built_is_an_absence_and_history_still_runs(tmp_path, collected) -> None:
    """新 lane 讀壞（例：名冊解析丟例外）只讓那條 lane 缺席——history 照走、daily 步驟 05 不整步失敗（L13）；
    缺席帶理由，下游印它，**不印「還沒有列」**（L12）。變異：拿掉 live 的 try → 這條紅（collect 直接丟例外）。"""
    import crons.heartbeat as hb
    from webapp.store import StateArtifactStore

    def boom(row):
        raise RuntimeError("名冊讀不到")

    history = [{"ticker": "HIST", "company_id": "co:hist", "anchor_date": date(2026, 8, 1),
                "current_date": date(2026, 10, 2), "absolute_return": -0.10, "peak_return": 0.05, "note": []}]
    broken = _collect(tmp_path, history=history, resolve=boom)
    assert broken["lanes"]["live"]["absence"]["kind"] == "upstream_unavailable"
    assert broken["lanes"]["history"]["rows"][0]["ticker"] == "HIST" and broken["lanes"]["paper"]["rows"]
    lines = "\n".join(OIST.render_lanes(broken))
    assert "live lane 組不出來（RuntimeError: 名冊讀不到）" in lines and "不是 0，也不是「還沒有列」" in lines
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    StateArtifactStore(state_dir).write(_artifact(broken))
    text = "\n".join(hb.build_positions(state_dir=state_dir).lines)
    assert "｜live 讀不到（" in text and "live（trade_log 成交）：live lane 組不出來" in text
    assert "還沒有列——trade_log" not in text
    values = hb.collect_snapshot(now=datetime(2026, 10, 2, tzinfo=timezone.utc), state_dir=state_dir,
                                 leads_path=tmp_path / "none.json", thesis_path=tmp_path / "none.json",
                                 run_record_path=None, capture_dir=None)
    assert values["positions.lane.live.n"] is None and values["positions.lane.paper.n"] == 2


def test_no_benchmark_diagnostic_run_never_writes_the_series(monkeypatch) -> None:
    """`--no-benchmark` 是診斷旗標：不寫聚合檔（否則當天那一行的超額被蓋成 null，plan §0.6 #1）。

    變異：讓 `--no-benchmark` 照樣 persist → 這條紅。"""
    calls: list[bool] = []
    monkeypatch.setattr(OIST, "collect", lambda **kw: {"kw": kw})
    monkeypatch.setattr(OIST, "_render", lambda collected, *, persist: calls.append(persist))
    monkeypatch.setattr(sys, "argv", ["outcome_if_settled_today.py", "--no-benchmark"])
    assert OIST.main() == 0
    monkeypatch.setattr(sys, "argv", ["outcome_if_settled_today.py"])
    assert OIST.main() == 0
    assert calls == [False, True]
