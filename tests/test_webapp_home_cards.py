"""首頁 compact 卡片（2026-10-28 使用者：「首頁根本不用講這麼多…compact 一點…30d 折線圖…10 字左右的介紹」）。

三件事各自守：
1. `overview.card` 是**選取不是計算**：折線取最後 31 點、漲跌照抄三題已算好的數、介紹的來源分開標（L12）。
2. 介紹 ledger 只 append、整批核對（名冊、字數、禁字、跟現行一樣的不寫）。
3. API 的日曆與依層由後端排好（時間序／節點 id 序，不是名次）；攤開哪幾組由後端說。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from starlette.testclient import TestClient

from alpha.errors import ContractViolation
from alpha.providers.taglines import current_taglines, read_records, write_taglines
from webapp.api import MAIN_GROUPS, create_app
from webapp.materialize import CARD_SPARK_SESSIONS, build_overview, materialize_view
from webapp.store import ArtifactStore

from test_webapp_materialize import fake_view


def _with_card_panels(view, *, rides=(), row=None, rel=None):
    """在 fake_view 上補首頁卡片讀的三格：敘事押的層、候選列、三題的相對組 30 日。"""
    view = dict(view)
    view["bet"] = {"key": "bet", "lines": [{"key": "rides", "datum": {"value": [dict(r) for r in rides]}}]}
    view["candidate"] = {"key": "candidate", "lines": [{"key": "candidate:state", "datum": {"value": row}}]}
    tq = []
    if rel is not None:
        tq.append({"key": "tq:priced_in:2:rel_return_30d", "datum": {
            "value": rel, "as_of": "2026-10-27", "label": "已定價③：相對組 30 個交易日漲幅",
            "dependencies": {"detail": {"own_return": -0.1228, "cohort_mean_return": -0.1755}}}})
    view["three_questions"] = {"key": "three_questions", "lines": tq}
    return view


RIDE = {"node": "tech:cw_dfb_laser", "node_name": "High-power CW DFB laser", "unit_label": "層",
        "kind_label": "B：量的賭注"}
ROW = {"derived": "priced_wait", "declared": "priced_wait", "derived_label": "已定價等回落",
       "since": "2026-10-15T14:48:05+00:00", "stall_days": 13,
       "watch": {"until": "2026-11-14", "status": "active", "watch_id": "ew_1", "expires": "2027-01-31"}}


def _series(n):
    start = date(2026, 6, 1)
    return [{"session_date": (start + timedelta(days=i)).isoformat(), "close": 100.0 + i} for i in range(n)]


# ---------------------------------------------------------------------------
# 1. overview.card 是選取
# ---------------------------------------------------------------------------

def test_card_takes_the_last_sessions_and_copies_the_cohort_numbers_verbatim() -> None:
    view = _with_card_panels(fake_view(), rides=[RIDE], row=ROW, rel=0.0527)
    series = _series(180)
    card = build_overview(view, card={"tagline": None, "labels_zh": {}, "price_series": series})["card"]
    assert len(card["spark"]) == CARD_SPARK_SESSIONS == 31
    assert card["spark"][-1] == {"session_date": series[-1]["session_date"], "close": series[-1]["close"]}
    assert card["spark"][0]["close"] is series[-31]["close"]           # 挑點：同一個物件，不是重算出來的值
    # 漲跌只抄三題那一格（本檔、組、差），不另算一個報酬
    assert card["move"] == {"relative": 0.0527, "own": -0.1228, "cohort": -0.1755, "as_of": "2026-10-27",
                            "label": "已定價③：相對組 30 個交易日漲幅"}
    assert card["watch"] == {"until": "2026-11-14", "status": "active"}
    assert card["stall_days"] == 13 and card["since"] == "2026-10-15"


def test_card_without_a_cohort_has_no_number_only_the_line() -> None:
    view = _with_card_panels(fake_view(), rides=[RIDE], row=ROW, rel=None)
    card = build_overview(view, card={"price_series": _series(40)})["card"]
    assert card["move"] is None and len(card["spark"]) == 31


def test_tagline_sources_stay_separate() -> None:
    """研究寫的介紹、押的層的中文名、什麼都沒有——三種來源分開標（L12）。"""
    rec = {"short_name": "聯亞", "text": "CW 雷射磊晶片", "created_at": "2026-10-28T01:00:00+00:00"}
    view = _with_card_panels(fake_view(), rides=[RIDE], row=ROW)
    ledger = build_overview(view, card={"tagline": rec, "labels_zh": {"tech:cw_dfb_laser": "高功率 CW DFB 雷射"}})["card"]
    assert ledger["short_name"] == "聯亞"
    assert ledger["tagline"] == {"text": "CW 雷射磊晶片", "source": "ledger", "written_at": "2026-10-28"}
    assert ledger["rides"][0]["label"] == "高功率 CW DFB 雷射"
    layer = build_overview(view, card={"labels_zh": {"tech:cw_dfb_laser": "高功率 CW DFB 雷射"}})["card"]
    assert layer["short_name"] is None
    assert layer["tagline"] == {"text": "高功率 CW DFB 雷射", "source": "layer", "written_at": None}
    english = build_overview(view, card={})["card"]
    assert english["rides"][0]["label"] == "High-power CW DFB laser"   # 沒有中文名就照印圖上的英文名，不臨時翻譯
    bare = build_overview(_with_card_panels(fake_view(), row=None), card={})["card"]
    assert bare["tagline"] == {"text": None, "source": None, "written_at": None}
    assert bare["watch"] is None and bare["stall_days"] is None and bare["spark"] == []


def test_stall_days_only_when_the_shown_state_is_the_declared_one() -> None:
    """已持有來自 Sheet；那份敘事宣告的是「不要」——「已持有 29 天」會是錯的話。"""
    held = dict(ROW, derived="held", declared="pass", derived_label="已持有", stall_days=29, watch=None)
    card = build_overview(_with_card_panels(fake_view(), rides=[RIDE], row=held), card={})["card"]
    assert card["stall_days"] is None and card["since"] is None


def test_card_is_written_into_the_artifact() -> None:
    view = _with_card_panels(fake_view(), rides=[RIDE], row=ROW, rel=0.0527)
    payload = materialize_view(view, price_series=_series(60),
                               tagline={"short_name": "聯亞", "text": "CW 雷射磊晶片", "created_at": "2026-10-28T01:00:00+00:00"},
                               labels_zh={"tech:cw_dfb_laser": "高功率 CW DFB 雷射"})
    assert payload["overview"]["card"]["tagline"]["text"] == "CW 雷射磊晶片"
    assert len(payload["overview"]["card"]["spark"]) == 31


# ---------------------------------------------------------------------------
# 2. 介紹 ledger
# ---------------------------------------------------------------------------

class _Registry:
    def __init__(self, mapping):
        self.mapping = mapping

    def company_id_for_ticker(self, ticker):
        return self.mapping.get(ticker)


REG = _Registry({"3081.TWO": "co:landmark_optoelectronics", "4979.TWO": "co:luxnet"})
T0 = datetime(2026, 10, 28, 1, 0, tzinfo=timezone.utc)


def test_tagline_ledger_appends_and_latest_wins(tmp_path) -> None:
    path = tmp_path / "taglines.jsonl"
    write_taglines([{"ticker": "3081.TWO", "short_name": "聯亞", "text": "CW 雷射磊晶片"}], path=path, registry=REG, now=T0)
    write_taglines([{"ticker": "3081.TWO", "short_name": "聯亞", "text": "磷化銦雷射磊晶片"}], path=path, registry=REG,
                   now=T0 + timedelta(hours=1))
    records, errors = read_records(path=path)
    assert len(records) == 2 and errors == []                       # 舊的留著（只 append）
    current, _ = current_taglines(path=path)
    head = current["co:landmark_optoelectronics"]
    assert head["text"] == "磷化銦雷射磊晶片" and head["supersedes_id"] == records[0]["tagline_id"]


@pytest.mark.parametrize("spec, message", [
    ({"ticker": "9999.TW", "short_name": "某", "text": "某某"}, "不在名冊"),
    ({"ticker": "3081.TWO", "short_name": "聯亞", "text": "一二三四五六七八九十一二三四五"}, "上限 14"),
    ({"ticker": "3081.TWO", "short_name": "聯亞", "text": "營收年增 90%"}, "%"),
    ({"ticker": "3081.TWO", "short_name": "聯亞", "text": "sole_source 雷射"}, "禁字"),
    ({"ticker": "3081.TWO", "short_name": "", "text": "CW 雷射磊晶片"}, "非空"),
    ({"ticker": "3081.TWO", "short_name": "聯亞", "text": "{market_cap}"}, "placeholder"),
])
def test_tagline_rejections_name_the_reason(tmp_path, spec, message) -> None:
    with pytest.raises(ContractViolation, match=message):
        write_taglines([spec], path=tmp_path / "t.jsonl", registry=REG, now=T0)


def test_one_bad_item_rejects_the_whole_batch(tmp_path) -> None:
    path = tmp_path / "t.jsonl"
    with pytest.raises(ContractViolation, match="整批都沒寫"):
        write_taglines([{"ticker": "4979.TWO", "short_name": "華星光", "text": "雷射晶粒與光模組"},
                        {"ticker": "9999.TW", "short_name": "某", "text": "某某"}], path=path, registry=REG, now=T0)
    assert not path.exists()


def test_same_as_current_is_not_rewritten(tmp_path) -> None:
    path = tmp_path / "t.jsonl"
    spec = {"ticker": "4979.TWO", "short_name": "華星光", "text": "雷射晶粒與光模組"}
    write_taglines([spec], path=path, registry=REG, now=T0)
    with pytest.raises(ContractViolation, match="一樣"):
        write_taglines([spec], path=path, registry=REG, now=T0 + timedelta(hours=1))


def test_bad_lines_are_reported_not_dropped(tmp_path) -> None:
    path = tmp_path / "t.jsonl"
    path.write_text('{"tagline_id": "tl_x"}\nnot json\n', encoding="utf-8")
    records, errors = read_records(path=path)
    assert records == [] and len(errors) == 2


# ---------------------------------------------------------------------------
# 3. API：日曆、依層、攤開哪幾組
# ---------------------------------------------------------------------------

def _payload(ticker, group, *, until=None, rides=(), short=None, stall=5):
    row = {"derived": group, "declared": group, "derived_label": group, "since": "2026-10-01T00:00:00+00:00",
           "stall_days": stall, "watch": {"until": until, "status": "active"} if until else None}
    view = _with_card_panels(fake_view(ticker), rides=rides, row=row)
    payload = materialize_view(view, tagline={"short_name": short, "text": "做什麼", "created_at": "2026-10-28T00:00:00+00:00"}
                               if short else None)
    payload["overview"]["candidate"] = {"list_group": group, "label": group, "absence_kind": None}
    from webapp.contracts import canonical_digest

    payload["content_digest"] = canonical_digest({k: v for k, v in payload.items() if k != "content_digest"})
    return payload


@pytest.fixture()
def client(tmp_path):
    from webapp.materialize import write_vocabularies

    store = ArtifactStore(tmp_path)
    today = date.today()
    soon = (today + timedelta(days=3)).isoformat()
    later = (today + timedelta(days=40)).isoformat()
    past = (today - timedelta(days=2)).isoformat()
    other = {**RIDE, "node": "mat:inp_substrate", "node_name": "InP substrate"}
    for payload in (_payload("AAA", "missing", until=soon, rides=[RIDE], short="甲"),
                    _payload("BBB", "priced_wait", until=past, rides=[RIDE, other]),
                    _payload("CCC", "missing", until=later, rides=[other], stall=12),
                    _payload("DDD", "pass", until=soon, rides=[RIDE]),
                    _payload("EEE", "held")):
        store.write(payload)
    write_vocabularies(store)
    return TestClient(create_app(tmp_path)), today


def test_calendar_is_by_date_within_two_weeks_and_keeps_past_ones(client) -> None:
    http, today = client
    body = http.get("/api/v1/stocks").json()
    cal = body["calendar"]
    dates = [d["date"] for d in cal["dates"]]
    assert dates == sorted(dates)                                   # 時間序
    tickers = [s["ticker"] for d in cal["dates"] for s in d["stocks"]]
    assert "CCC" not in tickers                                     # 40 天後不在兩週內
    assert "BBB" in tickers and next(d for d in cal["dates"] if d["stocks"][0]["ticker"] == "BBB")["past"] is True
    soon = next(d for d in cal["dates"] if d["date"] == (today + timedelta(days=3)).isoformat())
    assert [s["ticker"] for s in soon["stocks"]] == ["AAA", "DDD"]  # 同一天照組序（缺 X 在不要之前）
    assert soon["stocks"][0]["name"] == "甲"                         # 有短名印短名
    by = {r["ticker"]: r for r in body["stocks"]}
    assert by["BBB"]["card"]["watch"]["past"] is True and by["AAA"]["card"]["watch"]["past"] is False
    # 印法：今年的只印月-日；別年的印全日期（否則 2027 年的重看日會被讀成今年）
    soon_day = (today + timedelta(days=3)).isoformat()
    assert by["AAA"]["card"]["watch"]["label"] == (soon_day[5:] if soon_day[:4] == today.isoformat()[:4] else soon_day)
    later_day = (today + timedelta(days=40)).isoformat()
    assert by["CCC"]["card"]["watch"]["label"] == (later_day[5:] if later_day[:4] == today.isoformat()[:4] else later_day)


def test_a_watch_in_another_year_prints_the_year(tmp_path) -> None:
    from webapp.materialize import write_vocabularies

    store = ArtifactStore(tmp_path)
    far = date(date.today().year + 1, 5, 1).isoformat()
    store.write(_payload("FAR", "missing", until=far, rides=[RIDE]))
    write_vocabularies(store)
    row = TestClient(create_app(tmp_path)).get("/api/v1/stocks").json()["stocks"][0]
    assert row["card"]["watch"]["label"] == far and row["card"]["watch"]["past"] is False


def test_by_layer_lists_main_groups_and_counts_the_rest(client) -> None:
    http, _ = client
    body = http.get("/api/v1/stocks").json()
    layers = {layer["node"]: layer for layer in body["by_layer"]["layers"]}
    assert list(layers) == sorted(layers)                           # 節點 id 序，不是名次
    assert layers["tech:cw_dfb_laser"]["tickers"] == ["AAA", "BBB"]  # 不要（DDD）不攤開、照數
    assert [(o["group"], o["count"]) for o in layers["tech:cw_dfb_laser"]["others"]] == [("pass", 1)]
    assert layers["mat:inp_substrate"]["tickers"] == ["CCC", "BBB"]  # 層內照組序（缺 X 在等回落之前）、再照 ticker
    assert body["by_layer"]["unridden"] == ["EEE"]                   # 持有但敘事沒宣告押哪一層
    expanded = {g["key"] for g in body["groups"] if g["expanded"]}
    assert expanded == set(MAIN_GROUPS)


# ---------------------------------------------------------------------------
# 4. 候選板與在等什麼併進首頁（2026-10-28 使用者照推薦：11 頁收成 5 頁的第二步）
# ---------------------------------------------------------------------------

def test_every_group_comes_back_with_its_count_and_oldest_stall(client) -> None:
    """候選板「各組檔數（0 也印）＋最老滯留」那一行搬到首頁最下面：0 檔的組照回，最老滯留＝組內敘事天數最大的那一個（挑值）。"""
    http, _ = client
    groups = {g["key"]: g for g in http.get("/api/v1/stocks").json()["groups"]}
    assert groups["missing"]["count"] == 2 and groups["missing"]["oldest_stall_days"] == 12
    assert groups["open"]["count"] == 0 and groups["open"]["oldest_stall_days"] is None and groups["open"]["expanded"]


def test_held_group_says_unverified_when_the_sheet_was_not_read(tmp_path) -> None:
    """候選板原本在 Sheet 讀不到時把「已持有」印成「未驗」；首頁「0 也印」不得把它壓成「已持有 0」（L12）。"""
    from webapp.contracts import canonical_digest
    from webapp.materialize import _candidate_overview, write_vocabularies

    panel = {"lines": [{"key": "candidate:state", "datum": {"value": dict(ROW, sheet_verified=False)}}]}
    assert _candidate_overview(panel)["sheet_verified"] is False              # 照抄個股頁那一列

    def written(verified):
        store = ArtifactStore(tmp_path / str(verified))
        payload = _payload("AAA", "missing")
        payload["overview"]["candidate"]["sheet_verified"] = verified
        payload["content_digest"] = canonical_digest({k: v for k, v in payload.items() if k != "content_digest"})
        store.write(payload)
        write_vocabularies(store)
        groups = TestClient(create_app(tmp_path / str(verified))).get("/api/v1/stocks").json()["groups"]
        return {g["key"]: g for g in groups}

    unread = written(False)
    assert "Sheet 讀不到" in unread["held"]["warning"] and unread["missing"]["warning"] is None
    assert written(True)["held"]["warning"] is None


def test_card_counts_the_rewrite_flags_it_does_not_copy_them() -> None:
    """候選板那一列的「敘事該重寫」搬到卡片上：只帶筆數（是哪幾條、為什麼在個股頁候選狀態那一行）。"""
    row = dict(ROW, rewrite=["敘事該重寫：ew_1 醒來", "敘事該重寫：ew_2 到期未判"])
    assert build_overview(_with_card_panels(fake_view(), rides=[RIDE], row=row), card={})["card"]["rewrite"] == 2
    assert build_overview(_with_card_panels(fake_view(), rides=[RIDE], row=ROW), card={})["card"]["rewrite"] == 0
    assert build_overview(_with_card_panels(fake_view(), row=None), card={})["card"]["rewrite"] is None


def test_the_two_pages_are_gone_and_every_page_says_its_question() -> None:
    """兩頁拿掉；舊連結落到首頁並說一句（不落到「讀不到判讀」）。每一頁宣告它回答你的哪一個問題——
    字串只住 index.html 的 data-question，app.js 照抄（不另寫一份）。"""
    import re
    from pathlib import Path

    static = Path(__file__).resolve().parents[1] / "webapp" / "static"
    source = (static / "app.js").read_text(encoding="utf-8")
    html = (static / "index.html").read_text(encoding="utf-8")
    for gone in ("function renderCandidates", "function candidateRow", "function renderWatches", "function watchRow"):
        assert gone not in source, gone
    assert 'href="#/candidates"' not in html and 'href="#/watches"' not in html
    assert "target === 'watches' || target === 'candidates'" in source
    links = re.findall(r'<a href="#/[^"]*" data-view="[^"]+"([^>]*)>([^<]+)</a>', html)
    # 幾頁只在一個地方數（`tests/test_webapp_graph_page.py` 的導覽列標籤）；這裡守的是「每一頁都有問句」。
    assert links and all(re.search(r'data-question="[^"]+？"', attrs) for attrs, _ in links), links
    assert links[0][1] == "公司"
    assert 'id="page-question"' in html and "link.dataset.question" in source
