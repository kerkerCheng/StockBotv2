"""MOPS 歷史重訊回補（failure log #148；plan 2026-11-10-001 H）。

事發：金居（8358.TWO）9-14、10-16 兩則與高力（8996.TW）10-20 的重訊，lead 池裡都沒有——當日批次只有前一營業日，
漏抓那天或公司進監看範圍之前的就不在任何地方。守的事：
①回補列與每日那條算出**同一把去重鍵**（否則同一則進池兩次）；②查無資料是空、代號不存在與認不得的頁是錯（不回空集合）；
③說明頁對不上列就拒收（不把別則的說明掛上來）；④池裡已有的不抓說明、不重登；⑤90 天回補每輪限量、有敘事的先；
⑥說明沒抓到的那檔不算補完、下輪重來；⑦連續抓不到就停打這台主機；⑧上限由程式強制；⑨心跳段 1 有一行加總。

樣本照 2026-11-10 實抓的頁面結構手刻（列：代號、名稱、民國日期、時刻、`<pre>` 主旨、詳細資料按鈕；說明頁：標籤格與值格交錯）。"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from crons import harvest_leads
from crons import heartbeat as hb
from engine_b import leads
from fetchers import mops_open_data as mops

ROOT = Path(__file__).resolve().parents[1]
TODAY = date(2026, 11, 10)
SEEN = datetime(2026, 11, 10, 1, 0, tzinfo=timezone.utc).isoformat()
SUBJECT_A = "本公司董事會決議對子公司Co-Tech Development (Penang)\r\nSdn. Bhd.增資"
SUBJECT_B = "代子公司COTECH DEVELOPMENT (PENANG) SDN. BHD.公告取得土地 & 廠房"
HISTORY = {"lookback_days": 7, "backfill_days": 90, "backfill_tickers_per_run": 3, "detail_fetch_per_run": 40}


def _button(seq: str, clock: str, day: str, code: str = "8358", typek: str = "otc") -> str:
    return ("<input type='button' value='詳細資料' onclick=\"document.t05st01_fm.action='ajax_t05st01';"
            f"document.t05st01_fm.seq_no.value='{seq}';document.t05st01_fm.spoke_time.value='{clock}';"
            f"document.t05st01_fm.spoke_date.value='{day}';document.t05st01_fm.co_id.value='{code}';"
            f"document.t05st01_fm.TYPEK.value='{typek}';openWindow(this.form ,'');\">")


def _row(roc_day: str, clock: str, subject_html: str, button: str, code: str = "8358", name: str = "金居") -> str:
    cell = "<td style='text-align:left !important;'>"
    return (f"<tr class='even'>\r\n\r\n{cell}&nbsp;{code}</td>{cell}&nbsp;{name}</td>{cell}&nbsp;{roc_day}</td>"
            f"{cell}&nbsp;{clock}</td>{cell}<pre style='font-family:0;'><font size='3'>&nbsp;{subject_html}"
            f"</font></pre></td><td align='center'>{button}</td></tr>")


LIST_PAGE = (
    "<table class='hasBorder'><tr><td class='compName' align='center'>\r\n\r\n<b>\r\n\r\n本資料由　(上櫃公司) 8358 "
    "\r\n\r\n金居　公司提供</b>\r\n\r\n</td></tr><tr><td class='reportCont'></td></tr>"
    "<tr class='tblHead'><th>公司代號</th><th>公司名稱</th><th>發言日期</th><th>發言時間</th><th>主旨</th>"
    "<th>&nbsp;</th></tr>"
    + _row("115/10/16", "14:49:30", SUBJECT_A, _button("1", "144930", "20261016"))
    + _row("115/10/31", "18:16:50", SUBJECT_B.replace("&", "&amp;"), _button("1", "181650", "20261031"))
    + "</table>")

DETAIL_PAGE = (
    "<TR><TD align='right'>\r\n<form action='/server-java/t56ques' method='post'>\r\n</form></TD></TR>"
    "<tr><td class='reportCont'></td></tr>"
    "<TR><TD  class='tblHead'>序號</TD>\r\n<TD class='odd'>&nbsp;1</TD><TD  class='tblHead'>發言日期</TD>\r\n"
    "<TD class='odd'>&nbsp;115/10/16</TD><TD  class='tblHead'>發言時間</TD>\r\n<TD class='odd'>&nbsp;14:49:30</TD></TR>"
    "<tr><TD  class='tblHead'>發言人</TD>\r\n<TD class='odd'>&nbsp;李思賢</TD></tr>"
    f"<TR><TD  class='tblHead'>主旨</TD>\r\n<TD colspan=5 class='odd'><pre><font size='3'>&nbsp;{SUBJECT_A}"
    "</font></pre></TD></TR>"
    "<TR><TD  class='tblHead'>符合條款</TD>\r\n<TD class='odd'>　第\r\n15&nbsp;款\t</TD>\r\n"
    "<TD class='tblHead'>事實發生日</td>\r\n<TD class='odd'  colspan='3'>&nbsp;115/10/16\r\n</TD></TR>"
    "<TR><TD  class='tblHead'>說明</TD>\r\n<TD colspan=5 class='odd'><pre>\r\n1.董事會或股東會決議日期:115/10/16\n"
    "2.投資計畫內容:擬對本公司100%持有之子公司辦理增資。\n3.預計投資金額:新台幣14億元。</pre></TD></TR>")


class _Response:
    def __init__(self, body: str) -> None:
        self.content = body.encode("utf-8")


def _history_row(day: str, clock: str, subject: str, *, ticker: str = "8358.TWO", seq: str = "1") -> dict:
    """`parse_announcement_history` 會給的列（harvest 測試用，不經 HTML）。"""
    market, code = mops.market_for_ticker(ticker), mops.company_code(ticker)
    return {"market": market, "company_code": code, "ticker": ticker, "company_name": "測試", "subject": subject,
            "clause": None, "fact_date": None, "spoke_date": day, "spoke_time": clock, "detail": None,
            "report_date": None, "source_url": mops.ANNOUNCEMENT_URL[market],
            "detail_key": {"seq_no": seq, "spoke_time": clock.replace(":", ""), "spoke_date": day.replace("-", ""),
                           "co_id": code, "TYPEK": "otc" if market == "tpex" else "sii"}}


def _with_detail(row: dict) -> dict:
    return {**row, "detail": f"說明：{row['subject']}", "history_query": f"q:{row['ticker']}:{row['spoke_date']}"}


@pytest.fixture
def fake_mops(monkeypatch):
    """歷史列表照 `pages[(代號, 年, 月)]` 回、說明照列補；記下每次呼叫。"""
    calls: dict[str, list] = {"list": [], "detail": []}
    pages: dict[tuple[str, int, int], list[dict]] = {}
    failing: set[str] = set()

    def fetch_history(ticker, year, month):
        calls["list"].append((ticker, year, month))
        if ticker in failing:
            raise mops.MopsOpenDataError(f"{ticker} 取得失敗：ConnectionError")
        return [dict(r) for r in pages.get((ticker, year, month), [])]

    def fetch_detail(row):
        calls["detail"].append((row["ticker"], row["spoke_date"], row["spoke_time"]))
        return _with_detail(row)

    monkeypatch.setattr(mops, "fetch_announcement_history", fetch_history)
    monkeypatch.setattr(mops, "fetch_announcement_detail", fetch_detail)
    monkeypatch.setattr("engine_b.routine_config.narrative_tickers", lambda: frozenset())
    return calls, pages, failing


def _config(**history) -> dict:
    return {"mops_watch": {"tickers": [], "derive_from_registry": True, "history": {**HISTORY, **history}}}


def _log(store: dict) -> dict:
    return {e["source"]: e for e in store["harvest_log"]}


# ---- ① 去重鍵：回補與每日那條是同一把 ------------------------------------------------------------------------------

def test_history_rows_share_the_daily_dedupe_key() -> None:
    daily = mops._announcement_row({"公司代號": "8358", "公司名稱": "金居", "發言日期": "1151016", "發言時間": "144930",
                                    "主旨": SUBJECT_A, "說明": "1.董事會", "出表日期": "1151017"},
                                   market="tpex", source_url=mops.ANNOUNCEMENT_URL["tpex"])
    history = mops.parse_announcement_history(LIST_PAGE, ticker="8358.TWO")[0]
    url = harvest_leads.announcements_to_leads("8358.TWO", [daily])[0]["url"]
    assert harvest_leads.announcements_to_leads("8358.TWO", [history])[0]["url"] == url


def test_history_page_parses_rows_and_detail_keys() -> None:
    rows = mops.parse_announcement_history(LIST_PAGE, ticker="8358.TWO")
    assert [(r["spoke_date"], r["spoke_time"]) for r in rows] == [("2026-10-16", "14:49:30"), ("2026-10-31", "18:16:50")]
    assert rows[0]["subject"] == SUBJECT_A                       # 斷行原樣保留（去重鍵的一部分）
    assert rows[1]["subject"] == SUBJECT_B                       # entity 還原
    assert rows[0]["ticker"] == "8358.TWO" and rows[0]["company_name"] == "金居" and rows[0]["detail"] is None
    assert rows[0]["detail_key"] == {"seq_no": "1", "spoke_time": "144930", "spoke_date": "20261016",
                                     "co_id": "8358", "TYPEK": "otc"}


# ---- ② 查無資料是空、其餘認不得的頁是錯 ------------------------------------------------------------------------------

def test_no_data_is_empty_but_unknown_pages_raise() -> None:
    assert mops.parse_announcement_history("<html>公開資訊觀測站 資料庫中查無需求資料</html>", ticker="8996.TW") == []
    with pytest.raises(mops.MopsHistoryError) as missing:
        mops.parse_announcement_history("<html>公開資訊觀測站 0000 之公司不存在！</html>", ticker="0000.TW")
    assert (missing.value.result, missing.value.failure_class) == ("parse_failed", "not_found")
    with pytest.raises(mops.MopsHistoryError) as unknown:
        mops.parse_announcement_history("<html>FOR SECURITY REASONS, THIS PAGE CAN NOT BE ACCESSED!</html>",
                                        ticker="8996.TW")
    assert unknown.value.failure_class == "parse_error"


# ---- ③ 說明頁：解析、對不上列就拒收 ------------------------------------------------------------------------------------

def test_detail_page_is_parsed_with_line_breaks_kept() -> None:
    parsed = mops.parse_announcement_detail(DETAIL_PAGE)
    assert parsed["detail"].startswith("1.董事會或股東會決議日期:115/10/16\n2.投資計畫內容")
    assert (parsed["spoke_date"], parsed["spoke_time"]) == ("2026-10-16", "14:49:30")
    assert parsed["clause"] == "第 15 款" and parsed["fact_date"] == "2026-10-16"
    with pytest.raises(mops.MopsHistoryError):
        mops.parse_announcement_detail(DETAIL_PAGE.replace("說明", "附註"))


def test_list_query_is_the_roc_month_and_paced(monkeypatch) -> None:
    seen = []

    def post(url, data, **kw):
        seen.append((url, dict(data), kw.get("pace")))
        return _Response(LIST_PAGE)

    monkeypatch.setattr(mops, "_post", post)
    assert len(mops.fetch_announcement_history("8358.TWO", 2026, 10)) == 2
    url, data, pace = seen[0]
    assert url == mops.ANNOUNCEMENT_HISTORY_URL and pace == mops.HISTORY_PACE_SECONDS
    assert (data["co_id"], data["year"], data["month"], data["TYPEK"], data["step"]) == ("8358", "115", "10", "all", "1")


def test_detail_must_match_the_row_it_was_fetched_for(monkeypatch) -> None:
    seen = []

    def post(url, data, **kw):
        seen.append((dict(data), kw.get("pace")))
        return _Response(DETAIL_PAGE)

    monkeypatch.setattr(mops, "_post", post)
    row = mops.parse_announcement_history(LIST_PAGE, ticker="8358.TWO")[0]
    full = mops.fetch_announcement_detail(row)
    assert full["detail"].startswith("1.董事會") and full["subject"] == SUBJECT_A
    assert "seq_no=1" in full["history_query"] and "spoke_time=144930" in full["history_query"]
    data, pace = seen[0]
    assert pace == mops.HISTORY_PACE_SECONDS
    assert (data["step"], data["seq_no"], data["spoke_date"], data["TYPEK"], data["year"], data["month"]) == (
        "2", "1", "20261016", "otc", "115", "10")
    other = mops.parse_announcement_history(LIST_PAGE, ticker="8358.TWO")[1]      # 10-31 那則拿到 10-16 的說明頁
    with pytest.raises(mops.MopsHistoryError):
        mops.fetch_announcement_detail(other)


# ---- ④ 池裡已有的不抓說明、不重登；新的照每日那條路登記 ----------------------------------------------------------------

def test_backfill_registers_the_missing_one_and_skips_the_one_in_pool(fake_mops) -> None:
    calls, pages, _failing = fake_mops
    store = leads.empty_store()
    in_pool = _history_row("2026-10-16", "14:49:30", SUBJECT_A)
    missing = _history_row("2026-10-31", "18:16:50", SUBJECT_B)
    daily = harvest_leads.announcements_to_leads("8358.TWO", [{**in_pool, "detail": "1.董事會"}])[0]
    leads.register(store, source="mops:8358.TWO", url=daily["url"], title=daily["title"], raw_text=daily["raw_text"])
    pages[("8358.TWO", 2026, 10)] = [in_pool, missing]

    harvest_leads.harvest_mops_history(_config(), store, ["8358.TWO"], seen_at=SEEN, today=TODAY)

    assert calls["detail"] == [("8358.TWO", "2026-10-31", "18:16:50")]               # 池裡那則沒抓說明
    assert len(store["leads"]) == 2
    url = harvest_leads.announcements_to_leads("8358.TWO", [missing])[0]["url"]
    lead = store["leads"][leads.lead_id_for(url)]
    assert lead["source"] == "mops:8358.TWO" and lead["source_class"] == "primary"
    assert lead["company_id"] == "co:co_tech" and lead["published_at"] == "2026-10-31"     # 名冊解析，與每日同一條路
    assert lead["raw_text"] == f"{SUBJECT_B}\n\n說明：{SUBJECT_B}"
    assert lead["refs"]["mops_history_query"] == "q:8358.TWO:2026-10-31"
    entry = _log(store)["mops-history:8358.TWO"]
    assert entry["result"] == "ok" and entry["new"] == 1
    assert entry["filter"]["in_pool"] == 1 and entry["filter"]["registered"] == 1 and entry["filter"]["initial"] == 1
    assert [m for _t, *m in calls["list"]] == [[2026, 8], [2026, 9], [2026, 10], [2026, 11]]   # 90 天＝8/12 起
    state = leads.get_source_state(store, "mops-history:8358.TWO")
    assert state["backfill_from"] == "2026-08-12" and state["covered_through"] == "2026-11-09"     # 到昨天


def test_today_is_left_for_tomorrows_daily_batch(fake_mops) -> None:
    """今天發的是明天當日批次的份：回補先登記的話，「補進每日漏抓的」會把還沒輪到的算成漏抓（L12）。"""
    calls, pages, _failing = fake_mops
    pages[("8358.TWO", 2026, 11)] = [_history_row("2026-11-10", "15:00:00", "今天的"),
                                     _history_row("2026-11-09", "15:00:00", "昨天的")]
    store = leads.empty_store()
    leads.set_source_state(store, "mops-history:8358.TWO", backfill_from="2026-08-12", covered_through="2026-11-08")
    harvest_leads.harvest_mops_history(_config(), store, ["8358.TWO"], seen_at=SEEN, today=TODAY)
    assert calls["detail"] == [("8358.TWO", "2026-11-09", "15:00:00")]
    entry = _log(store)["mops-history:8358.TWO"]
    assert entry["filter"]["in_window"] == 1 and entry["filter"]["window_days"] == 7      # 11-03～11-09


# ---- ⑤ 90 天回補每輪限量、有敘事的先 ------------------------------------------------------------------------------------

def test_initial_backfill_is_capped_per_run_and_narratives_go_first(fake_mops, monkeypatch) -> None:
    calls, _pages, _failing = fake_mops
    monkeypatch.setattr("engine_b.routine_config.narrative_tickers", lambda: frozenset({"8996.TW"}))
    store = leads.empty_store()
    harvest_leads.harvest_mops_history(_config(backfill_tickers_per_run=1), store,
                                       ["2308.TW", "8358.TWO", "8996.TW"], seen_at=SEEN, today=TODAY)
    months = {}
    for ticker, year, month in calls["list"]:
        months.setdefault(ticker, []).append((year, month))
    assert months["8996.TW"] == [(2026, 8), (2026, 9), (2026, 10), (2026, 11)]        # 有敘事的先做 90 天
    assert months["2308.TW"] == months["8358.TWO"] == [(2026, 11)]                    # 其餘這輪只回看 7 天
    log = _log(store)
    assert log["mops-history:8996.TW"]["filter"]["awaiting_backfill"] == 0
    assert log["mops-history:2308.TW"]["filter"]["awaiting_backfill"] == 1
    assert leads.get_source_state(store, "mops-history:2308.TW") == {}                 # 沒輪到的不留狀態


# ---- ⑥ 說明沒抓到的那檔不算補完，下輪從同一天再來 -------------------------------------------------------------------

def test_unfinished_details_do_not_advance_the_state(fake_mops) -> None:
    calls, pages, _failing = fake_mops
    pages[("8358.TWO", 2026, 11)] = [_history_row("2026-11-06", "16:00:00", "甲"),
                                     _history_row("2026-11-07", "16:00:00", "乙")]
    store = leads.empty_store()
    harvest_leads.harvest_mops_history(_config(detail_fetch_per_run=1), store, ["8358.TWO"], seen_at=SEEN, today=TODAY)
    entry = _log(store)["mops-history:8358.TWO"]
    assert entry["filter"]["registered"] == 1 and entry["filter"]["deferred"] == 1     # 新的先補（11-07）
    assert calls["detail"] == [("8358.TWO", "2026-11-07", "16:00:00")]
    assert entry["filter"]["awaiting_backfill"] == 1
    assert leads.get_source_state(store, "mops-history:8358.TWO") == {}

    harvest_leads.harvest_mops_history(_config(), store, ["8358.TWO"], seen_at=SEEN, today=TODAY)
    entry = _log(store)["mops-history:8358.TWO"]
    assert entry["filter"]["registered"] == 1 and entry["filter"]["in_pool"] == 1 and entry["filter"]["deferred"] == 0
    assert leads.get_source_state(store, "mops-history:8358.TWO")["backfill_from"] == "2026-08-12"


def test_routine_window_reaches_back_to_the_last_complete_day(fake_mops) -> None:
    calls, pages, _failing = fake_mops
    store = leads.empty_store()
    leads.set_source_state(store, "mops-history:8358.TWO", backfill_from="2026-07-01", covered_through="2026-10-20")
    pages[("8358.TWO", 2026, 10)] = [_history_row("2026-10-18", "09:00:00", "窗外"),
                                     _history_row("2026-10-25", "09:00:00", "漏抓")]
    harvest_leads.harvest_mops_history(_config(), store, ["8358.TWO"], seen_at=SEEN, today=TODAY)
    assert [m for _t, *m in calls["list"]] == [[2026, 10], [2026, 11]]                  # 10-19 起，不是 11-03 起
    entry = _log(store)["mops-history:8358.TWO"]
    assert entry["filter"]["in_window"] == 1 and entry["filter"]["registered"] == 1 and entry["filter"]["initial"] == 0
    assert entry["filter"]["window_days"] == 22                                          # 10-19～11-09
    assert leads.get_source_state(store, "mops-history:8358.TWO")["covered_through"] == "2026-11-09"


# ---- ⑦ 連續抓不到就停打這台主機；代號不存在不算 ---------------------------------------------------------------------

def test_consecutive_failures_stop_hitting_the_host(fake_mops) -> None:
    calls, _pages, failing = fake_mops
    tickers = ["1101.TW", "1102.TW", "1103.TW", "1104.TW", "1105.TW"]
    failing.update(tickers)
    store = leads.empty_store()
    for ticker in tickers:
        leads.set_source_state(store, f"mops-history:{ticker}", backfill_from="2026-08-12",
                               covered_through="2026-11-09")
    summary = harvest_leads.harvest_mops_history(_config(), store, tickers, seen_at=SEEN, today=TODAY)
    assert [t for t, *_m in calls["list"]] == tickers[:3]
    log = _log(store)
    assert all(log[f"mops-history:{t}"]["result"] == "fetch_failed" for t in tickers)
    assert [log[f"mops-history:{t}"].get("filter") for t in tickers[3:]] == [{"not_attempted": 1}] * 2
    assert summary == {"failed": 3, "not_attempted": 2}
    assert leads.get_source_state(store, "mops-history:1101.TW")["covered_through"] == "2026-11-09"   # 狀態不動


def test_unknown_company_does_not_count_toward_the_streak(fake_mops, monkeypatch) -> None:
    calls, _pages, _failing = fake_mops

    def fetch_history(ticker, year, month):
        calls["list"].append((ticker, year, month))
        raise mops.MopsHistoryError(f"MOPS 說 {ticker} 這家公司不存在", failure_class="not_found")

    monkeypatch.setattr(mops, "fetch_announcement_history", fetch_history)
    tickers = ["1101.TW", "1102.TW", "1103.TW", "1104.TW"]
    store = leads.empty_store()
    harvest_leads.harvest_mops_history(_config(backfill_tickers_per_run=1), store, tickers, seen_at=SEEN, today=TODAY)
    assert sorted({t for t, *_m in calls["list"]}) == tickers                            # 四檔都打了
    assert {e["failure_class"] for e in store["harvest_log"]} == {"not_found"}
    assert {e["result"] for e in store["harvest_log"]} == {"parse_failed"}


def test_daily_harvest_runs_the_backfill_after_the_batch(fake_mops, monkeypatch) -> None:
    _calls, _pages, _failing = fake_mops
    monkeypatch.setattr(harvest_leads, "_mops_watch_tickers", lambda watch: ["8358.TWO"])
    monkeypatch.setattr(mops, "fetch_material_announcements", lambda market: [])
    store = leads.empty_store()
    harvest_leads.harvest_mops(_config(), store, seen_at=SEEN)
    log = _log(store)
    assert log["mops:8358.TWO"]["result"] == "ok"                     # 當日那一批照舊
    assert log["mops-history:8358.TWO"]["result"] == "ok"             # 接著回補


def test_without_history_config_nothing_runs(fake_mops) -> None:
    calls, _pages, _failing = fake_mops
    store = leads.empty_store()
    assert harvest_leads.harvest_mops_history({"mops_watch": {"tickers": ["8358.TWO"]}}, store, ["8358.TWO"]) == {}
    assert calls["list"] == [] and store["harvest_log"] == []


# ---- ⑧ 上限由程式強制 ------------------------------------------------------------------------------------------------

def _load(tmp_path: Path, history) -> dict:
    payload = {"feeds": [], "edgar_watch": {}, "mops_watch": {"tickers": [], "derive_from_registry": True,
                                                              "history": history}}
    path = tmp_path / "harvest_config.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return harvest_leads.load_config(path)


@pytest.mark.parametrize("bad", [
    {**HISTORY, "detail_fetch_per_run": 500},
    {**HISTORY, "backfill_tickers_per_run": 0},
    {**HISTORY, "lookback_days": True},
    {**HISTORY, "backfill_days": "90"},
    {**HISTORY, "lookback_days": 30, "backfill_days": 14},
    {k: v for k, v in HISTORY.items() if k != "lookback_days"},
    [],
])
def test_history_limits_fail_closed(tmp_path: Path, bad) -> None:
    with pytest.raises(ValueError):
        _load(tmp_path, bad)


def test_shipped_config_is_within_the_limits() -> None:
    config = harvest_leads.load_config()
    history = config["mops_watch"]["history"]
    for key, (low, high) in harvest_leads.MOPS_HISTORY_LIMITS.items():
        assert low <= history[key] <= high, key


# ---- ⑨ 心跳段 1 ------------------------------------------------------------------------------------------------------

def test_heartbeat_line_adds_up_the_last_run_of_each_ticker() -> None:
    def ok(**counts):
        base = {"listed": 0, "in_window": 0, "in_pool": 0, "registered": 0, "deferred": 0, "detail_failed": 0,
                "window_days": 7, "initial": 0, "awaiting_backfill": 0}
        return {"result": "ok", "filter": {**base, **counts}}

    latest = {
        "mops-history:8358.TWO": ok(registered=2, in_pool=3),
        "mops-history:8996.TW": ok(registered=9, in_pool=1, initial=1, deferred=1, awaiting_backfill=1),
        "mops-history:2308.TW": {"result": "fetch_failed", "failure_class": "timeout"},
        "mops:8358.TWO": {"result": "ok"},
    }
    line = hb.mops_history_line(latest)
    assert line == ("MOPS 重訊回補（各檔最後一輪，3 檔）：補進每日漏抓的 2 則＋90 天回補 9 則｜池裡已有 4｜"
                    "**說明沒抓到 1 則**（下輪重來）｜90 天回補待做 1 檔｜抓不到 1 檔")
    assert "說明沒抓到 0｜" in hb.mops_history_line({"mops-history:8358.TWO": ok()})
    assert hb.mops_history_line({"mops:8358.TWO": {"result": "ok"}}) is None


def test_section_one_prints_the_line_and_lists_the_failed_ticker(tmp_path: Path) -> None:
    """L13：產出要出現在消費者手上——段 1 真的印這一行，抓不到的檔進失敗清單（它算一個來源）。"""
    filled = {"listed": 5, "in_window": 4, "in_pool": 2, "registered": 2, "deferred": 0, "detail_failed": 0,
              "window_days": 7, "initial": 0, "awaiting_backfill": 0}
    log = [{"run_at": SEEN, "source": "mops:8358.TWO", "result": "ok", "new": 0},
           {"run_at": SEEN, "source": "mops-history:8358.TWO", "result": "ok", "new": 2, "filter": filled},
           {"run_at": SEEN, "source": "mops-history:2308.TW", "result": "fetch_failed", "new": 0,
            "failure_class": "timeout"}]
    path = tmp_path / "pending_leads.json"
    path.write_text(json.dumps({"leads": {}, "harvest_log": log}), encoding="utf-8")
    now = datetime(2026, 11, 10, 2, 0, tzinfo=timezone.utc)
    lines = hb.build_freshness(now=now, state_dir=tmp_path, leads_path=path).lines
    assert any(x.startswith("harvest 來源 3 個｜失敗 1 個：mops-history:2308.TW") for x in lines), lines
    assert any(x.startswith("MOPS 重訊回補（各檔最後一輪，2 檔）：補進每日漏抓的 2 則") and x.endswith("抓不到 1 檔")
               for x in lines), lines


# ---- sandbox impact review：主機、節流、review 寫在 OPERATIONS --------------------------------------------------------

def test_history_endpoint_pace_and_review_are_pinned() -> None:
    assert mops.ANNOUNCEMENT_HISTORY_URL.startswith("https://mopsov.twse.com.tw/")
    assert mops.HISTORY_PACE_SECONDS >= 2.0
    review = (ROOT / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")
    block = review.split("重訊回補（failure log #148", 1)[1][:6000]
    for needle in ("ajax_t05st01", "mopsov.twse.com.tw", "MOPS_HISTORY_LIMITS", "HISTORY_PACE_SECONDS"):
        assert needle in block, needle
