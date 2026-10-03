"""新股發行金額（稀釋燈的輸入）與 `fundamental_history` 的 CHECK 遷移（Phase 4 Step 4.6）。

守四件事：
1. 抽取：`us-gaap:StockIssuedDuringPeriodValueNewIssues` 照營收的規則存季度／年度，第四季由「年度 − 前三季累計」衍生。
2. 未遷移的舊庫：新指標只被略過並計數，既有指標照寫——一個新指標不得讓整批寫不進去（L11-6 ④）。
3. 遷移：先用 backup API 備份、一個交易重建、列數與內容摘要相同、冪等；對帳不符就 rollback、正式庫一字不動。
4. 讀取端：最近四季（52／53 週制也剛好四季）、as-of 只看已申報的、年度正好在窗尾就用年度；國內申報人以外是方法不適用；從沒有這個
   tag 是 provider_missing——三種缺席分開（L12）。
"""
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pytest

from engine_c import history_backfill as hb
from engine_c import migrate_fundamental_metrics as mig

TODAY = date(2026, 9, 29)
FETCHED = "2026-09-29T03:00:00+00:00"
TAG = "StockIssuedDuringPeriodValueNewIssues"


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


def _issuance_facts() -> dict:
    return _companyfacts({("us-gaap", TAG): [
        _fact("2025-01-01", "2025-03-31", 10.0, "Q1", "10-Q", "2025-05-01"),
        _fact("2025-01-01", "2025-09-30", 40.0, "Q3", "10-Q", "2025-11-01"),       # 9 個月累計
        _fact("2025-01-01", "2025-12-31", 100.0, "FY", "10-K", "2026-02-20"),
        _fact("2026-04-01", "2026-06-30", 600.0, "Q2-26", "10-Q", "2026-08-01"),
    ]})


def test_issuance_is_stored_like_revenue_with_a_derived_fourth_quarter() -> None:
    rows, rejected = hb.build_fundamental_rows(_issuance_facts(), ticker="XYZ", filer="domestic_quarterly",
                                               today=TODAY, fetched_at=FETCHED)
    by = {(r["metric"], r["period_end"]): r for r in rows}
    assert by[("equity_issued_value_quarter", "2025-03-31")]["value"] == 10.0
    assert by[("equity_issued_value_annual", "2025-12-31")]["value"] == 100.0
    q4 = by[("equity_issued_value_quarter", "2025-12-31")]
    assert q4["value"] == 60.0 and q4["derived"].startswith("FY−9M") and q4["filed"] == "2026-02-20"
    assert q4["tag"] == f"us-gaap:{TAG}" and rejected == []
    # 外國年報申報人只存年度點（燈對它們是方法不適用，但資料照存）
    foreign, _ = hb.build_fundamental_rows(_companyfacts({("us-gaap", TAG): [
        _fact("2025-01-01", "2025-12-31", 5.0, "F", "20-F", "2026-04-01")]}), ticker="ADR", filer="foreign_annual",
        today=TODAY, fetched_at=FETCHED)
    assert {r["metric"] for r in foreign} == {"equity_issued_value_annual"}


def test_without_a_nine_month_fact_the_fourth_quarter_comes_from_three_single_quarters_or_not_at_all() -> None:
    """MRVL 型：前三季單季都在、沒有 9M → 第四季＝年度 − 三季之和。NVDA FY2024 型：只有年度、三季一列都沒有 →
    不衍生（缺席不等於 0）。缺一季也不衍生。"""
    def facts(*quarters):
        return _companyfacts({("us-gaap", TAG): [
            *quarters, _fact("2025-02-02", "2026-01-31", 78.7, "FY", "10-K", "2026-03-11")]})

    q1 = _fact("2025-02-02", "2025-05-03", 0.6, "Q1", "10-Q", "2025-05-30")
    q2 = _fact("2025-05-04", "2025-08-02", 50.5, "Q2", "10-Q", "2025-08-29")
    q3 = _fact("2025-08-03", "2025-11-01", 0.4, "Q3", "10-Q", "2025-12-03")

    def q4(rows):
        return [r for r in rows if r["metric"] == "equity_issued_value_quarter" and r["period_end"] == "2026-01-31"]

    rows, _ = hb.build_fundamental_rows(facts(q1, q2, q3), ticker="MRVL", filer="domestic_quarterly",
                                        today=TODAY, fetched_at=FETCHED)
    (derived,) = q4(rows)
    assert derived["value"] == pytest.approx(27.2) and derived["period_start"] == "2025-11-02"
    assert derived["derived"].startswith("FY−ΣQ1..Q3") and derived["filed"] == "2026-03-11"
    for partial in ((), (q1, q3)):
        rows, _ = hb.build_fundamental_rows(facts(*partial), ticker="X", filer="domestic_quarterly",
                                            today=TODAY, fetched_at=FETCHED)
        assert q4(rows) == [], partial


OLD_DDL = """CREATE TABLE fundamental_history (
    ticker TEXT NOT NULL,
    metric TEXT NOT NULL CHECK (metric IN ('revenue_quarter', 'revenue_annual', 'operating_income_quarter', 'operating_income_annual', 'cash', 'total_debt', 'shares_outstanding_cover')),
    period_start TEXT,
    period_end TEXT NOT NULL,
    filed TEXT NOT NULL,
    accession TEXT NOT NULL,
    form TEXT NOT NULL,
    value REAL NOT NULL,
    currency TEXT NOT NULL,
    unit_scale INTEGER NOT NULL DEFAULT 1 CHECK (unit_scale > 0),
    derived TEXT,
    tag TEXT NOT NULL,
    source TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (ticker, metric, period_end, accession)
)"""


def _row(metric="revenue_quarter", *, end="2026-03-31", filed="2026-05-10", accn="A1", value=100.0,
         start="2026-01-01", form="10-Q", ticker="XYZ"):
    return {"ticker": ticker, "metric": metric, "period_start": start, "period_end": end, "filed": filed,
            "accession": accn, "form": form, "value": value, "currency": "USD", "unit_scale": 1, "derived": None,
            "tag": "us-gaap:X", "source": hb.SOURCE_EDGAR, "fetched_at": FETCHED}


def _old_db(path: Path, rows=()) -> Path:
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")                       # 正式庫是 WAL：備份必須拿得到 -wal 裡的頁
    conn.execute(OLD_DDL)
    conn.execute("CREATE INDEX idx_fundamental_history_asof ON fundamental_history (ticker, metric, period_end, filed)")
    conn.executemany(f"INSERT INTO fundamental_history ({', '.join(mig.COLUMNS)}) VALUES "
                     f"({', '.join(':' + c for c in mig.COLUMNS)})", list(rows))
    conn.commit()
    conn.close()
    return path


def test_an_unmigrated_database_skips_only_the_new_metric_and_says_so(tmp_path) -> None:
    db = _old_db(tmp_path / "old.db")
    conn = sqlite3.connect(str(db))
    assert hb.late_metrics_supported(conn) is False
    report = hb.backfill_ticker_edgar(conn, "XYZ", "0000000001", today=TODAY, incremental=False, fetched_at=FETCHED,
                                      fetch_facts=lambda cik: {**_issuance_facts(), "facts": {
                                          **_issuance_facts()["facts"],
                                          "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [
                                              {"end": "2026-07-25", "val": 1000, "accn": "Q2-26", "form": "10-Q",
                                               "filed": "2026-08-01"}]}}}}},
                                      lag_status=lambda *a, **k: {"status": "current"})
    # 新指標 4 列：Q1、衍生 Q4（FY − 9M）、FY、Q2-26——9 個月累計本身不存成季度
    assert report["outcome"] == "written" and report["late_metrics_skipped"]["rows"] == 4
    stored = {r[0] for r in conn.execute("SELECT metric FROM fundamental_history")}
    assert stored == {"shares_outstanding_cover"}                 # 既有指標照寫，新指標一列都沒硬塞
    assert hb.summarize({"tickers": {"XYZ": {"edgar": report}}})["late_metrics_skipped"] == 4   # daily 印得出來


def test_migration_backs_up_rebuilds_reconciles_and_is_idempotent(tmp_path) -> None:
    db = _old_db(tmp_path / "prod.db", rows=[_row(), _row(accn="A2", filed="2026-08-10"), _row("cash", accn="C1")])
    conn = sqlite3.connect(str(db), isolation_level=None)
    before = mig.table_fingerprint(conn)
    assert mig.missing_metrics(conn) == ["equity_issued_value_quarter", "equity_issued_value_annual"]
    conn.close()
    backup = mig.backup_database(db, tmp_path / "backups" / "prod.pre.db")
    assert backup["rows"] == 3 and Path(backup["path"]).is_file()
    conn = sqlite3.connect(str(db), isolation_level=None)
    result = mig.migrate(conn)
    assert result["status"] == "migrated" and result["rows"] == 3
    assert mig.table_fingerprint(conn) == before and mig.missing_metrics(conn) == []
    assert hb.late_metrics_supported(conn) is True
    hb.insert_fundamentals(conn, [_row("equity_issued_value_quarter", accn="E1", value=600.0)])   # 新 CHECK 收得下
    assert mig.migrate(conn)["status"] == "already_current"
    indexes = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'")}
    assert "idx_fundamental_history_asof" in indexes
    with pytest.raises(mig.MigrationError, match="已存在"):
        mig.backup_database(db, Path(backup["path"]))             # 不覆寫既有備份


def test_a_reconciliation_mismatch_rolls_back_and_leaves_the_table_untouched(tmp_path, monkeypatch) -> None:
    db = _old_db(tmp_path / "prod.db", rows=[_row(), _row("cash", accn="C1")])
    conn = sqlite3.connect(str(db), isolation_level=None)
    before = mig.table_fingerprint(conn)
    real = mig.table_fingerprint

    def lying(c, table=mig.TABLE):
        count, digest = real(c, table)
        return (count + 1, digest) if table.endswith("__new") else (count, digest)

    monkeypatch.setattr(mig, "table_fingerprint", lying)
    with pytest.raises(mig.MigrationError, match="不符"):
        mig.migrate(conn)
    monkeypatch.setattr(mig, "table_fingerprint", real)
    assert mig.table_fingerprint(conn) == before
    assert mig.missing_metrics(conn) == ["equity_issued_value_quarter", "equity_issued_value_annual"]
    assert "fundamental_history__new" not in {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}


def _reader_conn(rows) -> sqlite3.Connection:
    from engine_c.db import _ensure_sqlite_schema

    conn = sqlite3.connect(":memory:")
    _ensure_sqlite_schema(conn)
    hb.insert_fundamentals(conn, rows)
    return conn


def _domestic_rows(*extra):
    return [_row("revenue_quarter", end="2026-06-30", start="2026-04-01", filed="2026-08-01", accn="Q2-26"),
            _row("revenue_quarter", end="2026-03-31", start="2026-01-01", filed="2026-05-01", accn="Q1-26"),
            *extra]


def test_reader_sums_the_last_four_calendar_quarters_as_known_today_and_never_fills_missing_quarters() -> None:
    from engine_c.checklist import _equity_issuance

    conn = _reader_conn(_domestic_rows(
        _row("equity_issued_value_quarter", end="2026-06-30", start="2026-04-01", filed="2026-08-01", accn="Q2-26",
             value=600.0),
        _row("equity_issued_value_quarter", end="2025-09-30", start="2025-07-01", filed="2025-11-01", accn="Q3-25",
             value=50.0),
        _row("equity_issued_value_quarter", end="2025-09-30", start="2025-07-01", filed="2026-10-20", accn="Q3-25/A",
             value=5000.0),                                  # 今天之後才申報的修正：今天看不到，仍用原申報的 50
        _row("equity_issued_value_quarter", end="2025-06-30", start="2025-04-01", filed="2025-08-01", accn="Q2-25",
             value=7.0),                                     # 五季前：期末離窗尾正好 365 天，窗外
        _row("revenue_quarter", end="2026-09-30", start="2026-07-01", filed="2026-11-01", accn="FUT"),
        _row("equity_issued_value_quarter", end="2026-09-30", start="2026-07-01", filed="2026-11-01", accn="FUT",
             value=999.0),                                   # 還沒申報（filed > 今天）：既不可見、也不推動窗尾
        _row("shares_outstanding_cover", end="2026-07-25", start=None, filed="2026-08-01", accn="Q2-26",
             value=1000.0)))                                 # 封面日不是期末：不當窗尾
    got = _equity_issuance(conn, "XYZ", today=TODAY)
    assert got["status"] == "ok" and got["window_end"] == date(2026, 6, 30)
    assert got["trailing_total"] == 650.0 and got["quarters_found"] == 2 and got["basis"] == "quarters"


def test_a_52_week_fiscal_year_still_sums_exactly_four_quarters() -> None:
    """LITE 型（會計年度結束在 6 月最後一個週六附近）：四季前那一季的期末離窗尾只有 364 天——365 天窗會多加一季。"""
    from engine_c.checklist import _equity_issuance

    ends = ["2026-06-27", "2026-03-28", "2025-12-27", "2025-09-27", "2025-06-28"]     # 每季 13 週
    rows = [_row("revenue_quarter", end=ends[0], start="2026-03-29", filed="2026-08-14", accn="Q4-26", form="10-K")]
    rows += [_row("equity_issued_value_quarter", end=end, start=None, filed="2026-08-14", accn=f"E{i}", value=10.0 ** i)
             for i, end in enumerate(ends)]
    got = _equity_issuance(_reader_conn(rows), "XYZ", today=TODAY)
    assert got["window_end"] == date(2026, 6, 27) and got["quarters_found"] == 4
    assert got["trailing_total"] == 1.0 + 10.0 + 100.0 + 1000.0                      # 2025-06-28 那一季（10⁴）不算


def test_an_annual_amount_the_quarters_cannot_account_for_is_printed_not_dropped_or_filled() -> None:
    """AXTI 型：FY2025 年報 9355 萬、三份 10-Q 都沒有這一行；窗內另有 Q2'26 的 6 億。已知部分只算 6 億，
    年度差額列進 `unattributed`（不補 0、不硬塞進第四季）。"""
    from engine_c.checklist import _equity_issuance

    conn = _reader_conn(_domestic_rows(
        _row("equity_issued_value_annual", end="2025-12-31", start="2025-01-01", filed="2026-03-17", accn="FY25",
             value=93_550_000.0, form="10-K"),
        _row("equity_issued_value_quarter", end="2026-06-30", start="2026-04-01", filed="2026-08-01", accn="Q2-26",
             value=600_083_000.0)))
    got = _equity_issuance(conn, "XYZ", today=TODAY)
    assert got["trailing_total"] == 600_083_000.0 and got["basis"] == "quarters"
    assert got["unattributed"] == [{"fiscal_year_end": "2025-12-31", "annual": 93_550_000.0, "known_quarters": 0.0,
                                    "remainder": 93_550_000.0, "accession": "FY25"}]


def test_reader_uses_the_annual_row_when_the_fiscal_year_ends_at_the_window_end() -> None:
    from engine_c.checklist import _equity_issuance

    conn = _reader_conn([
        _row("revenue_quarter", end="2025-12-31", start="2025-10-01", filed="2026-02-20", accn="FY"),
        _row("equity_issued_value_annual", end="2025-12-31", start="2025-01-01", filed="2026-02-20", accn="FY",
             value=93.55, form="10-K"),
        _row("equity_issued_value_quarter", end="2025-09-30", start="2025-07-01", filed="2025-11-01", accn="Q3",
             value=1.0)])
    got = _equity_issuance(conn, "XYZ", today=date(2026, 3, 1))
    assert got["basis"] == "annual" and got["trailing_total"] == 93.55


def test_reader_separates_not_applicable_never_reported_and_not_yet_ready() -> None:
    """四種缺席分開（L12）：方法不適用／這家從沒申報／表還存不下／表存得下但還沒回填——後兩種是我們這邊的事。"""
    from engine_c.checklist import _equity_issuance

    other = _row("equity_issued_value_quarter", ticker="OTHER", end="2026-06-30", accn="O1", value=1.0)
    never = _equity_issuance(_reader_conn(_domestic_rows(other)), "XYZ", today=TODAY)
    assert never["status"] == "provider_missing"
    foreign = _reader_conn([_row("revenue_annual", end="2025-12-31", start="2025-01-01", filed="2026-04-01",
                                 accn="F", form="20-F")])
    assert _equity_issuance(foreign, "XYZ", today=TODAY)["status"] == "method_not_applicable"
    not_backfilled = _equity_issuance(_reader_conn(_domestic_rows()), "XYZ", today=TODAY)
    assert not_backfilled["status"] == "upstream_unavailable" and "還沒回填" in not_backfilled["reason"]


def test_an_unmigrated_table_is_upstream_unavailable_not_never_reported(tmp_path) -> None:
    from engine_c.checklist import _equity_issuance

    conn = sqlite3.connect(str(_old_db(tmp_path / "old.db", rows=_domestic_rows())))
    got = _equity_issuance(conn, "XYZ", today=TODAY)
    assert got["status"] == "upstream_unavailable" and "CHECK 尚未遷移" in got["reason"]


def test_both_consumers_go_through_the_one_wiring_point(monkeypatch) -> None:
    """候選板與個股頁共用 `alpha.providers.wipeout.wipeout_for`（closeout §5 #19）：串接不再各寫一份。"""
    from pathlib import Path as _Path

    root = _Path(__file__).resolve().parent.parent
    for rel in ("alpha/providers/candidates.py", "briefing/alpha_view/sources.py"):
        text = (root / rel).read_text(encoding="utf-8")
        assert "wipeout_for" in text and "get_wipeout_inputs" not in text, rel

    import engine_c.checklist as checklist
    from alpha.providers import market_normalization
    from alpha.providers.wipeout import wipeout_for

    # Phase 6 Step 6.6 起金額 > 0 還要窗內一份募資文件才黃（本條守的是串接點，所以假輸入帶一份）
    offerings = {"status": "ok", "complete": True, "gaps": [], "context": [],
                 "documents": [{"form": "424B5", "items": "", "filed": "2026-04-20", "accession": "A-1"}]}
    monkeypatch.setattr(checklist, "get_wipeout_inputs", lambda t: {
        "status": "ok", "runway": {"status": "manual_required"}, "shares_series": [], "going_concern": None,
        "issuance": {"status": "ok", "filer_class": "domestic_quarterly", "trailing_total": 600.0,
                     "currencies": ["USD"], "quarters_found": 1, "offerings": offerings}})
    monkeypatch.setattr(market_normalization, "screen_inputs",
                        lambda tickers, **_: {tickers[0]: {"market_cap_usd": 2000.0, "market_cap_absence": None}})
    flags, reason = wipeout_for("AXTI", today=TODAY)
    assert reason is None and flags["dilution"]["colour"] == "amber"
    assert flags["dilution"]["inputs"]["pct_of_market_cap"] == pytest.approx(0.3)
    monkeypatch.setattr(checklist, "get_wipeout_inputs", lambda t: {"status": "unavailable", "reason": "DB 不可用"})
    assert wipeout_for("AXTI", today=TODAY) == (None, "DB 不可用")


# ---------------------------------------------------------------------------
# R2-c 覆核收尾（2026-10-01）
# ---------------------------------------------------------------------------

def test_a_negative_fourth_quarter_from_inconsistent_tags_cannot_cancel_a_real_issuance() -> None:
    """R2-c #1（CRWV 型＋F1 反例，走真正的 build_fundamental_rows → _equity_issuance → dilution_flag）：年度 6800 萬
    小於 9 個月累計 14.59 億 → 衍生出 −13.9 億的第四季；同窗 Q1'26 有 5 億真實發行。判色看窗內正值 → 黃；
    負的衍生季列進 inconsistent；淨加總只印。"""
    from alpha.wipeout import dilution_flag
    from engine_c.checklist import _equity_issuance

    facts = _companyfacts({("us-gaap", TAG): [
        _fact("2025-01-01", "2025-03-31", 1_391_515_000.0, "Q1", "10-Q", "2025-05-15"),
        _fact("2025-04-01", "2025-06-30", 67_669_000.0, "Q2", "10-Q", "2025-08-13"),
        _fact("2025-01-01", "2025-09-30", 1_459_184_000.0, "Q3", "10-Q", "2025-11-13"),
        _fact("2025-01-01", "2025-12-31", 68_000_000.0, "FY", "10-K", "2026-03-02"),
        _fact("2026-01-01", "2026-03-31", 500_000_000.0, "Q1-26", "10-Q", "2026-05-14")]})
    rows, _ = hb.build_fundamental_rows(facts, ticker="XYZ", filer="domestic_quarterly", today=TODAY,
                                        fetched_at=FETCHED)
    conn = _reader_conn(rows)
    # Phase 6 Step 6.6：窗內一份私募公告（8-K 第 3.02 項）——走正式的寫入路徑，判色才走得到黃那一支
    from engine_c.offerings import store_offerings

    store_offerings(conn, [{"form_type": "8-K", "filed_date": "2026-02-10", "accession_dashed": "8K-1",
                            "items": "1.01,3.02,9.01"},
                           {"form_type": "10-K", "filed_date": "2020-01-01", "accession_dashed": "OLD"}],
                    ticker="XYZ", cik="0000000009", fetched_at=FETCHED)
    got = _equity_issuance(conn, "XYZ", today=TODAY)
    assert got["issued_total"] == 567_669_000.0 and got["trailing_total"] < 0
    assert [d["accession"] for d in got["offerings"]["documents"]] == ["8K-1"]
    # 兩種前後不一都標出：負的衍生第四季、年度（6800 萬）小於已知季度（Q1＋Q2 14.59 億）
    assert [i["kind"] for i in got["inconsistent"]] == ["negative_derived_quarter", "annual_below_quarters"]
    series = [(date(2025, 6, 1), 100.0), (date(2026, 7, 1), 100.0)]
    flag = dilution_flag(series, {"status": "manual_required"}, today=TODAY, issuance=got)
    assert flag["colour"] == "amber"


def test_tag_inconsistency_without_a_positive_fact_is_grey_not_green() -> None:
    """R2-c #1：窗內只有負的衍生季（沒有任何正值）→ 灰（insufficient_evidence），不得因淨加總 ≤ 0 判綠。"""
    from alpha.wipeout import dilution_flag
    from engine_c.checklist import _equity_issuance

    conn = _reader_conn([
        _row("revenue_quarter", end="2026-03-31", start="2026-01-01", filed="2026-05-14", accn="Q1-26"),
        _row("equity_issued_value_quarter", end="2025-12-31", start="2025-10-01", filed="2026-03-02", accn="FY",
             value=-1_391_184_000.0, form="10-K") | {"derived": "FY−9M：FY − Q3"},
        _row("equity_issued_value_annual", end="2025-12-31", start="2025-01-01", filed="2026-03-02", accn="FY",
             value=68_000_000.0, form="10-K")])
    got = _equity_issuance(conn, "XYZ", today=TODAY)
    assert got["issued_total"] == 0.0 and [i["kind"] for i in got["inconsistent"]] == ["negative_derived_quarter"]
    # 負的衍生季不算「已知」：FY2025 的 6800 萬整筆歸不到季（不是被灌大成 14.59 億）
    assert [(u["annual"], u["known_quarters"], u["remainder"]) for u in got["unattributed"]] == [
        (68_000_000.0, 0.0, 68_000_000.0)]
    series = [(date(2025, 6, 1), 100.0), (date(2026, 7, 1), 100.0)]
    flag = dilution_flag(series, {"status": "manual_required"}, today=TODAY, issuance=got)
    assert flag["colour"] is None and flag["absence_kind"] == "insufficient_evidence" and "前後不一" in flag["reason"]


def test_tag_inconsistency_alone_is_grey_even_when_nothing_is_unattributed() -> None:
    """R2-c #1 的另一條路（變異檢查抓到上一條測試同時觸發 unattributed）：季度加回來剛好等於年度、沒有差額，
    但 9 個月累計與單季不一致衍生出負的第四季，窗內又沒有正值 → 只靠 inconsistent 判灰。"""
    from alpha.wipeout import dilution_flag
    from engine_c.checklist import _equity_issuance

    conn = _reader_conn([
        _row("revenue_quarter", end="2026-06-30", start="2026-04-01", filed="2026-08-01", accn="Q2-26"),
        _row("equity_issued_value_quarter", end="2025-03-31", start="2025-01-01", filed="2025-05-01", accn="Q1",
             value=30_000_000.0),
        _row("equity_issued_value_quarter", end="2025-06-30", start="2025-04-01", filed="2025-08-01", accn="Q2",
             value=38_000_000.0),
        _row("equity_issued_value_quarter", end="2025-12-31", start="2025-10-01", filed="2026-03-02", accn="FY",
             value=-1_391_184_000.0, form="10-K") | {"derived": "FY−9M：FY − Q3"},
        _row("equity_issued_value_annual", end="2025-12-31", start="2025-01-01", filed="2026-03-02", accn="FY",
             value=68_000_000.0, form="10-K")])
    got = _equity_issuance(conn, "XYZ", today=TODAY)
    assert got["issued_total"] == 0 and got["unattributed"] == []
    assert [i["kind"] for i in got["inconsistent"]] == ["negative_derived_quarter"]
    series = [(date(2025, 6, 1), 100.0), (date(2026, 7, 1), 100.0)]
    flag = dilution_flag(series, {"status": "manual_required"}, today=TODAY, issuance=got)
    assert flag["colour"] is None and flag["absence_kind"] == "insufficient_evidence" and "前後不一" in flag["reason"]


def test_the_window_end_comes_from_flow_periods_before_balance_sheet_instants() -> None:
    """R2-c #5：期末之後的時點值（例：期後事項的債務）不得把窗尾往後推；這家沒有任何季度流量時才退到時點值。"""
    from engine_c.checklist import _equity_issuance

    late_instant = _row("total_debt", end="2026-08-29", start=None, filed="2026-09-01", accn="8K")
    conn = _reader_conn(_domestic_rows(late_instant, _row(
        "equity_issued_value_quarter", end="2025-09-30", start="2025-07-01", filed="2025-11-01", accn="Q3-25",
        value=300.0)))
    got = _equity_issuance(conn, "XYZ", today=TODAY)
    assert got["window_end"] == date(2026, 6, 30) and got["issued_total"] == 300.0
    only_instants = _reader_conn([                               # 沒有任何季度流量（例：尚無營收的公司）
        _row("cash", end="2026-03-31", start=None, filed="2026-05-01", accn="Q3", form="10-Q"),
        _row("cash", end="2026-06-30", start=None, filed="2026-08-20", accn="FY", form="10-K"),
        _row("equity_issued_value_annual", end="2026-06-30", start="2025-07-01", filed="2026-08-20", accn="FY",
             value=10.0, form="10-K")])
    fallback = _equity_issuance(only_instants, "XYZ", today=TODAY)
    assert fallback["window_end"] == date(2026, 6, 30) and fallback["basis"] == "annual"
    assert fallback["quarters_found"] is None                     # 年度當基礎時不印窗內季數（R2-c #6d）


def test_irregular_period_facts_are_counted_not_silently_dropped() -> None:
    """R2-c #2（CCXI 型：成立未滿一季的 26 天、210 天期間）：不存，但進拒寫清單並在 summary 計數；
    半年累計（Q2 10-Q 的 YTD）是預期內的不存，不計。"""
    facts = _companyfacts({("us-gaap", TAG): [
        _fact("2025-06-04", "2025-06-30", 25_000.0, "Q", "10-Q", "2026-08-13"),
        _fact("2025-06-04", "2025-12-31", 24_999.0, "K", "10-K", "2026-03-26"),
        _fact("2026-01-01", "2026-06-30", 7.0, "H1", "10-Q", "2026-08-13")]})
    rows, rejected = hb.build_fundamental_rows(facts, ticker="CCXI", filer="domestic_quarterly", today=TODAY,
                                               fetched_at=FETCHED)
    irregular = [r for r in rejected if r.get("kind") == "irregular_period"]
    assert len(irregular) == 2 and all("不存" in r["reason"] for r in irregular)
    assert not [r for r in rows if r["metric"].startswith("equity_issued_value")]
    summary = hb.summarize({"tickers": {"CCXI": {"edgar": {"rejected": rejected}}}})
    assert summary["irregular_period_facts"] == 2 and summary["rejected_groups"] == len(rejected) - 2


def test_migration_refuses_a_table_whose_columns_it_does_not_know(tmp_path) -> None:
    """R2-c #4：新表 DDL 只有這 14 欄——舊表多一欄時重建會把那一欄連資料丟掉、對帳卻看不出來 → 不動它。"""
    db = _old_db(tmp_path / "extra.db", rows=[_row()])
    conn = sqlite3.connect(str(db), isolation_level=None)
    conn.execute("ALTER TABLE fundamental_history ADD COLUMN note TEXT")
    conn.execute("UPDATE fundamental_history SET note = 'keep me'")
    with pytest.raises(mig.MigrationError, match="欄位"):
        mig.migrate(conn)
    assert conn.execute("SELECT note FROM fundamental_history").fetchone()[0] == "keep me"
    assert mig.missing_metrics(conn)                                # CHECK 原樣、沒重建


def test_migration_cli_refuses_a_missing_db_and_leaves_a_users_lock_alone(tmp_path, monkeypatch) -> None:
    """R2-c #4：打錯 --db 不得建出 0 位元組的空庫；使用者先用 writer_guard 取得的同 owner 鎖，遷移不續期、不釋放。"""
    from engine_b import writer_lock

    missing = tmp_path / "typo.db"
    assert mig.main(["--db", str(missing)]) == 2 and not missing.exists()
    monkeypatch.setattr(writer_lock, "LOCK_PATH", tmp_path / ".writer_lock.json")
    writer_lock.acquire(writer_lock.INTERACTIVE_OWNER, ttl_minutes=30, purpose="使用者的回填")
    before = writer_lock.holder()
    db = _old_db(tmp_path / "prod.db", rows=[_row()])
    assert mig.main(["--db", str(db), "--apply"]) == 0
    assert writer_lock.holder() == before                           # 沒續期（TTL 不變）、也沒拆
    writer_lock.release(writer_lock.INTERACTIVE_OWNER)
    db2 = _old_db(tmp_path / "prod2.db", rows=[_row()])
    assert mig.main(["--db", str(db2), "--apply"]) == 0 and writer_lock.holder() is None   # 自己取的鎖自己還


def test_authorizations_registered_on_different_days_are_all_shown() -> None:
    """R2-c #6d：不同日登記、同時有效的授權都要印（原本只取最新那一天）。"""
    from engine_c.checklist import _equity_authorizations

    conn = _reader_conn([])
    for oid, as_of, kind in (("o1", "2026-03-01", "ATM"), ("o2", "2026-08-21", "shelf")):
        conn.execute("INSERT INTO manual_observations (observation_id, ticker, field_name, value, source_ref, as_of, "
                     "author, supersedes_id, recorded_at, payload_digest) VALUES (?, 'XYZ', "
                     "'equity_issuance_authorizations', ?, '424B5', ?, 'test', NULL, ?, ?)",
                     (oid, f'{{"kind": "{kind}"}}', as_of, as_of, f"digest-{oid}"))
    got = _equity_authorizations(conn, "XYZ")
    assert [(a["as_of"], a["value"]["kind"]) for a in got] == [("2026-08-21", "shelf"), ("2026-03-01", "ATM")]
