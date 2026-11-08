"""首頁最上面那一行：大盤同期（2026-11-08 使用者：「首屏的比組跟幾趴是什麼時間區間的？可以在這一頁最上面簡單列一下
指標性大盤 qqq Soxx 之類的同區間的變化嗎？看你推薦列哪幾檔」）。

守四件事：
1. 視窗與算法是卡片那一個（`RELATIVE_WINDOWS[0]`、`trailing_return`），每檔帶自己的起訖日；抓不到、不夠長的照列並說為什麼（不是 0）。
2. 跟候選板一起寫，但**不進 freshness_identity**（行情每天在動，不是認知變了）；抓失敗候選板照寫。
3. `/api/v1/stocks` 照抄；候選板讀不到、或是沒有這一格的舊板，說讀不到與怎麼補。
4. 首頁先畫這一行再畫日曆；前端不算報酬。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from starlette.testclient import TestClient

from alpha.three_questions import RELATIVE_WINDOWS, trailing_return
from webapp import materialize as mat
from webapp.api import create_app
from webapp.contracts import canonical_digest, validate_state_artifact
from webapp.store import StateArtifactStore

from test_webapp_candidates import fake_candidates_payload

N = RELATIVE_WINDOWS[0]


def _series(n, *, start=date(2026, 8, 3), base=100.0):
    return [{"session_date": (start + timedelta(days=i)).isoformat(), "close": base + i} for i in range(n)]


# ---------------------------------------------------------------------------
# 1. 視窗與算法
# ---------------------------------------------------------------------------

def test_moves_use_the_card_window_and_the_card_function() -> None:
    qqq, tw = _series(45), _series(N + 1, start=date(2026, 9, 1), base=50.0)
    rows = {r["symbol"]: r for r in mat.benchmark_moves({"QQQ": qqq, "0050.TW": tw})}
    bars = [(date.fromisoformat(p["session_date"]), p["close"]) for p in qqq]
    value, last = trailing_return(bars, N)
    assert N == 30 and rows["QQQ"]["sessions"] == N
    assert rows["QQQ"]["return"] == round(value, 4) == round(qqq[-1]["close"] / qqq[-1 - N]["close"] - 1, 4)
    assert rows["QQQ"]["start"] == qqq[-1 - N]["session_date"] and rows["QQQ"]["end"] == last.isoformat()
    # 剛好 N+1 根算得出來；起點是第一根
    assert rows["0050.TW"]["start"] == tw[0]["session_date"] and rows["0050.TW"]["absence"] is None
    assert rows["0050.TW"]["short"] == "0050" and rows["0050.TW"]["market"] == "台股"


def test_missing_or_short_series_are_listed_with_a_reason_not_zero() -> None:
    rows = mat.benchmark_moves({"QQQ": _series(40), "IWM": _series(N)})
    assert [r["symbol"] for r in rows] == [s["symbol"] for s in mat.HOME_BENCHMARKS]    # 每一檔都列、照設定的順序
    by = {r["symbol"]: r for r in rows}
    assert by["SOXX"]["return"] is None and "抓不到" in by["SOXX"]["absence"]
    assert by["IWM"]["return"] is None and f"只有 {N} 根，不足 {N + 1} 根" in by["IWM"]["absence"]
    assert by["IWM"]["start"] is None and by["IWM"]["end"] is None
    assert by["QQQ"]["absence"] is None


def test_the_fetch_asks_for_one_more_session_than_the_window_and_counts_bar_states() -> None:
    seen = {}

    def fake_fetch(symbols, *, sessions, now=None, states=None):
        seen.update(symbols=list(symbols), sessions=sessions)
        states.update({"QQQ": "closed", "SOXX": "dropped_unfinished", "IWM": "closed", "0050.TW": None})
        return {"QQQ": _series(N + 1), "SOXX": _series(N + 1), "IWM": _series(N + 1)}

    now = datetime(2026, 11, 8, 1, 0, tzinfo=timezone.utc)
    block = mat.home_benchmarks(fetch=fake_fetch, now=now)
    assert seen == {"symbols": ["QQQ", "SOXX", "IWM", "0050.TW"], "sessions": N + 1}
    assert block["window_sessions"] == N and block["fetched_at"] == now.isoformat()
    assert block["bar_states"]["checked"] == 3 and block["bar_states"]["dropped_unfinished"] == ["SOXX"]
    assert [r["return"] is None for r in block["rows"]] == [False, False, False, True]
    assert "只是脈絡" in block["note"]


# ---------------------------------------------------------------------------
# 2. 跟候選板一起寫、不進 freshness_identity
# ---------------------------------------------------------------------------

def _board(benchmarks=None):
    payload = fake_candidates_payload()
    board = {k: payload[k] for k in ("groups", "side_groups", "counts", "oldest_stall_days", "holdings",
                                     "narrative_rewrite", "ledger", "rollup", "universe", "today", "no_narrative")}
    if benchmarks is not None:
        board["benchmarks"] = benchmarks
    return board


def _block(value):
    return {"window_sessions": N, "rows": [{"symbol": "QQQ", "short": "QQQ", "label": "那斯達克 100", "market": "美股",
                                             "sessions": N, "return": value, "start": "2026-09-25", "end": "2026-11-06",
                                             "absence": None}]}


def test_the_board_carries_the_block_but_its_identity_does_not() -> None:
    stamp = datetime(2026, 11, 8, tzinfo=timezone.utc)
    up = mat.build_candidates_artifact(_board(_block(0.05)), generated_at=stamp)
    down = mat.build_candidates_artifact(_board(_block(-0.05)), generated_at=stamp)
    assert up["benchmarks"]["rows"][0]["return"] == 0.05 and validate_state_artifact("candidates", up) is up
    assert up["freshness_identity"] == down["freshness_identity"]          # 大盤動了不是認知變了
    assert up["content_digest"] != down["content_digest"]
    old = mat.build_candidates_artifact(_board(), generated_at=stamp)
    assert old["benchmarks"]["rows"] == [] and "沒有這一格" in old["benchmarks"]["absence"]


@pytest.fixture()
def board_only(monkeypatch):
    import alpha.providers.candidates as cand

    monkeypatch.setattr(cand, "load_board", lambda universe, context=None, structure=None: _board())
    monkeypatch.setattr(mat, "_graph_node_names", lambda ids: {})          # 測試不連真的圖


def test_materialize_writes_the_block_and_a_failed_fetch_does_not_fail_the_board(board_only, tmp_path,
                                                                                monkeypatch) -> None:
    monkeypatch.setattr(mat, "home_benchmarks", lambda: _block(-0.032))
    _path, payload = mat.materialize_candidates(tickers=["AXTI"], store=StateArtifactStore(tmp_path / "a"))
    assert payload["benchmarks"]["rows"][0]["return"] == -0.032

    def broken():
        raise RuntimeError("rate limited")

    monkeypatch.setattr(mat, "home_benchmarks", broken)
    path, payload = mat.materialize_candidates(tickers=["AXTI"], store=StateArtifactStore(tmp_path / "b"))
    assert path.is_file() and payload["counts"]["open"] == 1                # 候選板照寫
    assert payload["benchmarks"]["rows"] == [] and "RuntimeError: rate limited" in payload["benchmarks"]["absence"]


# ---------------------------------------------------------------------------
# 3. API 照抄；讀不到說讀不到
# ---------------------------------------------------------------------------

def _write_board(tmp_path, payload):
    StateArtifactStore(tmp_path / "state").write(payload)
    return TestClient(create_app(tmp_path)).get("/api/v1/stocks").json()["benchmarks"]


def test_stocks_copies_the_block_verbatim(tmp_path) -> None:
    payload = mat.build_candidates_artifact(_board(_block(-0.032)), generated_at=datetime(2026, 11, 8, tzinfo=timezone.utc))
    assert _write_board(tmp_path, payload) == payload["benchmarks"]


def test_stocks_says_why_when_the_board_or_the_cell_is_missing(tmp_path) -> None:
    missing = TestClient(create_app(tmp_path / "none")).get("/api/v1/stocks").json()["benchmarks"]
    assert missing["rows"] == [] and "materialize --candidates" in missing["absence"]
    old = mat.build_candidates_artifact(_board(), generated_at=datetime(2026, 11, 8, tzinfo=timezone.utc))
    del old["benchmarks"]                                                    # 改版前寫的板：沒有這一格
    old["content_digest"] = canonical_digest({k: v for k, v in old.items() if k != "content_digest"})
    body = _write_board(tmp_path, old)
    assert body["rows"] == [] and "還沒有這一格" in body["absence"]


# ---------------------------------------------------------------------------
# 4. 首頁先畫這一行；前端不算報酬
# ---------------------------------------------------------------------------

def test_the_home_page_draws_the_line_first_and_does_not_compute() -> None:
    from pathlib import Path

    static = Path(__file__).resolve().parents[1] / "webapp" / "static"
    source = (static / "app.js").read_text(encoding="utf-8")
    body = source[source.index("async function renderList"):]
    assert body.index("renderBenchmarks(data.benchmarks)") < body.index("renderCalendar(data.calendar)")
    fn = source[source.index("function renderBenchmarks"):]
    fn = fn[:fn.index("\n}\n") + 2]                                          # 到這個函式的右括號為止
    code = "\n".join(line.split("//")[0] for line in fn.splitlines())       # 行內註解不算
    assert "signedPct(r.return)" in code
    assert "/" not in code and ".close" not in code                          # 沒有除法、不讀收盤：照抄 materialize 算好的數
    # 沒抓到的原因印在畫面上（不只在滑過提示裡——手機看不到）
    assert "typeof r.return !== 'number'" in fn and "${r.absence || '沒有值'}`).join" in fn
    assert ".bench-line" in (static / "styles.css").read_text(encoding="utf-8")
