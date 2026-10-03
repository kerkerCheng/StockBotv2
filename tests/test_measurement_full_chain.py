"""Phase 5 新管線的 full chain（Step 5.7；plan §8）：夾具輸入 → 真的組裝函式 → state artifact → 心跳文字／APP API。

**斷言的是數字出現在下游**（artifact、心跳那一行、APP 回的 JSON），不是函式會動（L13：基礎設施的驗收是
「產出出現在下游消費者手上」）。每一個被斷言的數字都由夾具手算得出，寫在測試旁邊。

三條鏈：
1. 追蹤表：`collect()`（夾具 trade_log＋敘事＋主題等權組＋注入價格）→ `build_positions_artifact` → 心跳段 4 的 lane 行 → `/api/v1/positions`。
2. 圖預測：讀圖紀錄經**真的寫入端**進 ledger → 真的 `materialize_structure_readings` → 心跳段 4 的「圖預測」行 → `/api/v1/structure-readings`。
3. 計分表：真的 `materialize_account_scorecard`（夾具 lead、登記表、名冊、組、注入價格）→ 對組的超額格 → 心跳段 5 那一格 → `/api/v1/account-scorecard`。

既有 `tests/test_full_chain_acceptance.py` 不動。外部世界（Neo4j、yfinance、Sheet、舊店）一律以夾具替換，不打網路。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import pytest
from starlette.testclient import TestClient

import crons.heartbeat as hb
from webapp.api import create_app
from webapp.store import StateArtifactStore

from test_measurement_lanes import OIST, _collect
from test_webapp_positions import _COUNTERS


def _text(section) -> str:
    return "\n".join(section.lines)


# ---------------------------------------------------------------------------
# 1. 追蹤表三條 lane
# ---------------------------------------------------------------------------

def test_lane_numbers_reach_the_positions_artifact_the_heartbeat_and_the_api(tmp_path, monkeypatch) -> None:
    """paper 兩列（夾具價格手算）：AAA 09-29 收 100 → 10-02 收 120＝＋20%；GGG.L 44 → 55 GBp＝＋25%（同序列相除，單位相消）。
    主題等權組（MEM1 10 → 11＝＋10%；MEM2 50 → 10-02 是 NaN、退回 10-01 的 50＝0%；AAA ＋20%）排除本檔：
    AAA 對組＝20% − (10%+0%)/2＝＋15%；GGG.L 不是成員＝25% − (20%+10%+0%)/3＝＋15% → paper 對組超額平均 15.00%。"""
    import engine_b.event_watch as ew
    from webapp.materialize import build_positions_artifact, positions_lanes

    monkeypatch.setattr(ew, "_local_timezone", lambda: timezone(timedelta(hours=8)))
    collected = _collect(tmp_path)
    results = collected["lanes"]["history"]["rows"]
    live_rows, paper_only = OIST.live_lane_rows(results, {})
    payload = build_positions_artifact(
        results, collected["lanes"]["history"]["unavailable"], has_benchmark=bool(collected["benchmarks"]),
        aggregate=OIST.equal_weight_aggregate(results), power_law=OIST.power_law_aggregate(results),
        bet_convergence=None, health=OIST.anchor_health(results), live_rows=live_rows, paper_only=paper_only,
        counters=_COUNTERS, benchmarks=(OIST.PRIMARY_BENCHMARK, OIST.REFERENCE_BENCHMARK),
        lanes=positions_lanes(OIST, collected), theme_cohort=collected["theme_cohort"],
        price_budget=collected["price_budget"])
    state = tmp_path / "state"
    StateArtifactStore(state).write(payload)

    # artifact：逐列與 lane 聚合
    paper = payload["lanes"]["paper"]
    by_ticker = {row["ticker"]: row for row in paper["rows"]}
    assert by_ticker["AAA"]["absolute_return"] == pytest.approx(0.20)
    assert by_ticker["GGG.L"]["absolute_return"] == pytest.approx(0.25)
    assert by_ticker["AAA"]["excess_theme_cohort"] == pytest.approx(0.15)
    assert by_ticker["GGG.L"]["excess_theme_cohort"] == pytest.approx(0.15)
    assert paper["theme_cohort_excess"]["mean"] == pytest.approx(0.15) and paper["theme_cohort_excess"]["n"] == 2

    # 心跳段 4：同一個數字出現在人讀的那一行
    text = _text(hb.build_positions(state_dir=state))
    assert "paper（第一份 v2 敘事日起）：2 檔｜量測起始 2026-09-29｜等權總報酬 22.50%" in text, text
    assert "對主題等權組超額 15.00%（2/2 列）" in text, text
    assert "追蹤表 history 0｜paper 2｜live 3（beta 事件 1 不進 lane）｜主題等權組 tc_test（2026-09-30 定）" in text

    # APP：同一個數字照抄（API 不重算）
    body = TestClient(create_app(tmp_path)).get("/api/v1/positions").json()
    assert body["lanes"]["paper"]["theme_cohort_excess"]["mean"] == pytest.approx(0.15)


# ---------------------------------------------------------------------------
# 2. 圖預測對錯表
# ---------------------------------------------------------------------------

class _FixedDate(date):
    """materialize 端的「今天」釘在 2026-10-02（夾具讀圖 12 月才到期；不讓測試在 2027 年自己變紅）。"""

    @classmethod
    def today(cls):  # noqa: D102
        return date(2026, 10, 2)


def _utc(day: str) -> datetime:
    return datetime.fromisoformat(f"{day}T03:00:00+00:00")


def test_prediction_outcomes_reach_the_artifact_the_heartbeat_and_the_api(tmp_path, monkeypatch) -> None:
    """夾具三個節點、五份讀圖，全部經真的寫入端（契約＋引文逐字核對）進 ledger：

    - 插槽 r1（volume）→ r2（volume，同版、digest 變、多一份來源 doc_customer）＝ r1 **對**；r2 **現行**（12-31 到期）
    - 層 r3（volume）＋反證 watch 被判觸及（lead 09-30 發布、晚於讀圖 09-25）＝ **錯／之後才出現**
    - 層 r4（moat）→ r5（neither、digest 變、沒有新來源）＝ r4 **錯／未定日**；r5 **非斷言**
    → 心跳：對 1｜錯 2（當時已有 0／之後才出現 1／未定日 1）｜現行 1｜到期未重讀 0｜改寫 0｜非斷言 1｜現行最早到期 2026-12-31
    """
    import engine_b.event_watch as ew
    import engine_b.leads as leads_mod
    import query.structure as qs
    from alpha.providers import structure_readings as sr
    from webapp import materialize as mat

    from test_structure_reading_v3 import CUSTOMER_Q, LAYER, SOCKET, _cite, _quotes, _structure, _two_halves, _v3

    ledger = tmp_path / "readings"
    monkeypatch.setattr(sr, "STRUCTURE_READING_DIR", ledger)
    other = "mat:test_node"
    changed = lambda node: dict(_structure(node), result_digest="f" * 64)  # noqa: E731

    r1 = _v3(SOCKET, unit="socket", kind="volume", created_at=_utc("2026-09-25"), expires=date(2026, 12, 24))
    r2 = _v3(SOCKET, unit="socket", kind="volume", created_at=_utc("2026-10-01"), expires=date(2026, 12, 31),
             supersedes_id=r1["reading_id"], structure=changed(SOCKET),
             citations=_two_halves(SOCKET) + [_cite("supply_side", CUSTOMER_Q, "doc_customer", SOCKET)])
    r3 = _v3(LAYER, unit="layer", kind="volume", created_at=_utc("2026-09-25"), expires=date(2026, 12, 24),
             citations=_two_halves(LAYER))
    r4 = _v3(other, unit="layer", kind="moat", created_at=_utc("2026-09-26"), expires=date(2026, 12, 24),
             citations=_two_halves(other))
    r5 = _v3(other, unit="layer", kind="neither", created_at=_utc("2026-09-28"), expires=date(2026, 12, 28),
             supersedes_id=r4["reading_id"], structure=changed(other), citations=[], disproof=[])
    for record, node in ((r1, SOCKET), (r2, SOCKET), (r3, LAYER), (r4, other), (r5, other)):
        sr.append_reading_record(record, directory=ledger, quotes=_quotes(node))

    touched = {"watch_id": "ew_touch", "kind": "semantic_condition", "source_ref": f"reading:{r3['reading_id']}#1",
               "status": "consumed", "judgment": {"touches": "yes", "lead_id": "lead_x", "quote": "客戶具名第二家"}}
    monkeypatch.setattr(ew, "load_watches", lambda *a, **k: {"watches": [touched]})
    monkeypatch.setattr(leads_mod, "load", lambda *a, **k: {"leads": {"lead_x": {"published_at": "2026-09-30T08:00:00Z"}}})
    monkeypatch.setattr(mat, "_source_doc_published",
                        lambda: {"doc_demand": "2026-09-01", "doc_supply": "2026-09-01", "doc_customer": "2026-09-20"})
    monkeypatch.setattr(qs, "_load_edges", lambda *a, **k: [])                 # 不連圖：staleness 不是判定
    monkeypatch.setattr(mat, "date", _FixedDate)

    state = tmp_path / "state"
    _path, payload = mat.materialize_structure_readings(store=StateArtifactStore(state))

    table = payload["predictions"]
    outcomes = {row["reading_id"]: (row["outcome"], row["wrong_kind"]) for row in table["rows"]}
    assert outcomes == {
        r1["reading_id"]: ("held", None), r2["reading_id"]: ("open", None),
        r3["reading_id"]: ("disproof_touched", "emerged_later"),
        r4["reading_id"]: ("reversed", "undated"), r5["reading_id"]: ("non_assertion", None)}
    assert table["wrong_total"] == 2 and table["earliest_open_expiry"] == "2026-12-31"

    line = next(l for l in hb.build_positions(state_dir=state).lines if l.startswith("圖預測："))
    assert line == ("圖預測：對 1｜錯 2（當時已有 0／之後才出現 1／未定日 1）｜現行 1｜到期未重讀 0｜改寫 0｜非斷言 1"
                    "｜現行最早到期 2026-12-31"), line

    body = TestClient(create_app(tmp_path)).get("/api/v1/structure-readings").json()
    assert body["predictions"]["counts"]["held"] == 1 and body["predictions"]["wrong_total"] == 2


# ---------------------------------------------------------------------------
# 3. 計分表的第三個基準
# ---------------------------------------------------------------------------

def _linear(step: float, base: float = 100.0) -> dict[date, float]:
    start = date(2026, 7, 1)
    return {start + timedelta(days=i): base + i * step for i in range(130)}


SCORE_PRICES = {"AAA": _linear(1.0), "BBB": _linear(0.5), "CCC": _linear(2.0), "QQQ": _linear(0.3), "SOXX": _linear(0.8)}


def test_scorecard_cohort_cell_reaches_the_artifact_the_heartbeat_and_the_api(tmp_path, monkeypatch) -> None:
    """一則點名 AAA（2026-08-01）；組＝BBB、CCC（AAA 不是成員）。30 天（08-01 → 08-31）手算：
    AAA 131 → 161、BBB 115.5 → 130.5、CCC 162 → 222 → 對組超額＝161/131 − 1 − ((130.5/115.5 − 1)＋(222/162 − 1))/2。"""
    from datetime import datetime as _dt

    import alpha.providers.theme_cohorts as cohort_provider
    import identity.registry as registry_mod
    from alpha.theme_cohort import CohortMember, ThemeCohort
    from engine_b import account_scorecard as sc
    from engine_b import signal_source_registry as ssr
    from webapp.materialize import materialize_account_scorecard

    sources = tmp_path / "signal_sources.json"
    sources.write_text(json.dumps({"version": 1, "schema_version": 2, "sources": [
        {"source_id": "acct", "platform": "x", "handle": "acct", "status": "active", "tier": "probation",
         "research_priority": 1, "auto_capture": True}]}), encoding="utf-8")
    real_load = ssr.load
    monkeypatch.setattr(ssr, "load", lambda path=None: real_load(sources))

    class _Registry:
        ticker_map = {"co:AAA": "AAA"}

    monkeypatch.setattr(registry_mod, "get_registry", lambda: _Registry())
    leads = tmp_path / "pending_leads.json"
    leads.write_text(json.dumps({"leads": {"lead_1": {
        "lead_id": "lead_1", "source": "x:acct", "published_at": "2026-08-01T12:00:00Z", "status": "parked",
        "entities": {"company_ids": ["co:AAA"], "tickers": ["AAA"]}, "refs": {}}}}), encoding="utf-8")
    monkeypatch.setattr(sc, "DEFAULT_LEADS_PATH", leads)
    cohort = ThemeCohort(cohort_id="tc_chain", theme="測試題材",
                         members=(CohortMember("BBB", "co:BBB", "成員"), CohortMember("CCC", "co:CCC", "成員")),
                         excluded=(), reason="測試", decided_on=date(2026, 9, 30), pq2_ref=1,
                         created_at=_dt(2026, 9, 30, tzinfo=timezone.utc))
    monkeypatch.setattr(cohort_provider, "current_cohorts", lambda **_kw: ([cohort], []))
    asked: list[list[str]] = []

    def prices(symbols, start, end, states=None):  # Phase 6 Step 6.7c：預設取價多一個可選的 states（收盤狀態收集器）
        asked.append(list(symbols))
        return {s: SCORE_PRICES[s] for s in symbols if s in SCORE_PRICES}

    monkeypatch.setattr(sc, "_yfinance_closes", prices)

    state = tmp_path / "state"
    _path, payload = materialize_account_scorecard(store=StateArtifactStore(state))

    expected = (161 / 131 - 1) - ((130.5 / 115.5 - 1) + (222 / 162 - 1)) / 2
    cell = payload["accounts"][0]["metrics"]["excess_returns"]["excess_30d_vs_theme_cohort"]
    assert cell["value"] == pytest.approx(expected) and cell["n"] == 1
    assert asked == [["AAA", "BBB", "CCC", "QQQ", "SOXX"]]                    # 成員併進同一次取價
    assert payload["theme_cohort"]["members_priced"] == 2 and payload["price_budget"]["theme_cohort_added"] == ["BBB", "CCC"]

    line = hb.build_scorecard(state_dir=state).lines[-1]
    assert line.endswith("已知偏差 4 條（也在 APP）｜主題等權組基準：有"), line

    body = TestClient(create_app(tmp_path)).get("/api/v1/account-scorecard").json()
    got = body["accounts"][0]["metrics"]["excess_returns"]["excess_30d_vs_theme_cohort"]["value"]
    assert got == pytest.approx(expected)
