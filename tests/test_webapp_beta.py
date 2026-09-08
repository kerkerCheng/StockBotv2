"""`beta` state artifact：**照抄 Engine D beta monitor 的輸出**，不重算、不排序、不帶任何動能指標。

fixture 離線：一份最小但形狀正確的 `daily_beta_snapshot --format json` report，配 Engine C 觀測序列。
守的是 AGENTS 的 Beta 呈現契約：只回答「距目標多遠」與「在什麼水位」；band 是容忍區間不是 gate；
水位只呈現；動能指標整組不得回來。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from portfolio.allocation import _gap_state_label, _sleeve_label
from webapp.api import create_app
from webapp.contracts import STATE_KINDS, ArtifactUnavailable, validate_state_artifact
from webapp.materialize import build_beta_artifact, materialize_view
from webapp.store import ArtifactStore, StateArtifactStore

from test_webapp_materialize import fake_view

ROOT = Path(__file__).resolve().parents[1]

_RISK = {
    "leveraged_nominal_warning": 0.125, "leveraged_nominal_cap": 0.2,
    "leveraged_effective_warning": 0.3, "leveraged_effective_cap": 0.4,
    "total_exposure_warning": 1.5, "total_exposure_cap": 1.75,
    "issuer_concentration_warning": 0.25, "alpha_total_warning": 0.2,
}


def _sleeve(name, target, band, actual, gap, state, **kw):
    return {"sleeve": name, "target": target, "band": band, "actual": actual, "gap": gap, "state": state,
            "invested_base": kw.get("invested_base", 1000.0), "actual_source": "policy_instruments",
            "role": kw.get("role", "role"), "unavailable_reason": kw.get("unavailable_reason")}


def _item(ticker, sleeve, key, *, status="observed", percentile=0.86, r1=0.002, blockers=()):
    return {"ticker": ticker, "sleeve": sleeve, "price_series_key": key, "price_symbol": ticker,
            "price_status": status, "blockers": list(blockers), "warnings": [],
            "current_nominal_weight": 0.148, "current_effective_weight": 0.148,
            "heartbeat": {"session_date": "2026-09-04", "return_1d": r1, "return_5d": 0.0035, "return_20d": -0.0056},
            "water_level": {"status": status, "range_percentile_52w": percentile, "pct_from_52w_high": -0.035,
                            "pct_from_sma200": 0.094,
                            "interpretation": "position_only_no_momentum_not_a_timing_signal"}}


def fake_report():
    return {
        "as_of": "2026-09-08T05:41:32+00:00", "status": "degraded", "schema_version": "beta-monitor-v1",
        "refresh": {"status": "skipped", "observed_count": 0, "total_count": 2},
        "twse_freshness": {"status": "not_available", "source": None, "symbols": []},
        "blockers": [], "warnings": ["drawn_debt_present", "issuer_concentration_warning:TSMC"],
        "allocation_gap": {
            "status": "available", "unavailable_reason": None, "basis": "invested_non_cash",
            "invested_non_cash_base": 439277.12, "policy_version": "2026-08-29.1",
            "rebalancing": {"method": "new_money_only", "loan_tranche_excluded": True},
            "sleeves": [
                _sleeve("beta_core", 0.4, 0.05, 0.3326, -0.0674, "below_band"),
                _sleeve("beta_tilt", 0.25, 0.05, 0.3018, 0.0518, "above_band"),
                _sleeve("alpha", 0.1, 0.05, None, None, "unknown", unavailable_reason="sleeve_value_unavailable"),
            ],
            "correlation_warnings": [{"name": "alpha 與 beta 是同一個賭注", "detail": "d1", "surface_in": "x"},
                                     {"name": "TSMC look-through", "detail": "d2", "surface_in": "y"}],
        },
        "capital_view": {"status": "available", "authority_as_of": "2026-07-28", "base_currency": "USD",
                         "blockers": [], "fx": {"TWD/USD": {"rate": 0.0318, "status": "available"}}},
        "portfolio": {"base_currency": "USD", "nav_base": 470601.07, "invested_non_cash_base": 439277.12,
                      "cash_base": 31323.95, "cash_floor_base": 635.2, "deployable_cash_base": 30688.75},
        "self_funded_supported_range": [0.0, 30688.75],
        "loan_funded_supported_range": "manual_review_required",
        "contingent_credit_available": {"status": "available", "terms_status": "complete", "currency": "USD",
                                        "undrawn_amount_base": 166740.78, "drawn_amount_base": 23820.11,
                                        "estimated_monthly_interest_base": 61.54, "estimated_annual_interest_base": 738.42,
                                        "facilities": [{"annual_rate_pct": 3.1, "currency": "TWD"}], "blockers": []},
        "items": [
            _item("QQQ", "beta_tilt", "qqq"),
            _item("00981A.TW", "beta_tilt_active", "active_tw_growth", status="quarantined", percentile=0.87,
                  blockers=["technical_session_stale_vs_twse"]),
        ],
        "risk_snapshot": {
            "as_of": "2026-09-08T05:41:32+00:00", "base_currency": "USD", "nav_base": 470601.07,
            "total_exposure_weight": 1.08, "total_exposure_cap": 1.75, "wipeout_index_drawdown": 0.92,
            "etf_leverage": {"nominal_weight": 0.0734, "effective_weight": 0.1698},
            "loan_leverage_weight": 0.0506, "combined_leverage_weight": 0.2204, "callable_debt_weight": 0.0,
            "alpha_total_weight": 0.0148, "hard_blocks": [],
            "warnings": ["issuer_concentration_warning:TSMC", "issuer_lookthrough_partial"],
            "issuer_coverage": {"status": "partial", "method": "policy_registered_issuer_loads_plus_direct_alpha"},
            "issuer_exposures": {"TSMC": {"direct_weight": 0.1695, "indirect_weight": 0.1295, "total_weight": 0.2989},
                                 "NVIDIA": {"direct_weight": 0.0098, "indirect_weight": 0.0, "total_weight": 0.0098}},
        },
    }


def fake_series():
    """Engine C `recent_technical_observations` 的形狀——**故意帶著 08-29 前的動能欄位**，artifact 必須把它們丟掉。"""
    rows = []
    for i, (day, close) in enumerate((("2026-09-04", 718.96), ("2026-09-03", 717.7), ("2026-09-02", 712.1))):
        rows.append({"session_date": day, "close_adjusted": close, "sma_200": 656.78, "range_percentile_252": 0.85,
                     "rsi_14": 61.2 + i, "macd_line": 1.5, "macd_signal": 1.2, "macd_histogram": 0.3,
                     "data_status": "observed", "benchmark_key": "qqq"})
    return {"qqq": rows}     # active_tw_growth 沒有 observed 序列（全被隔離）


def fake_beta_payload(**kw):
    return build_beta_artifact(fake_report(), series_by_key=fake_series(), policy_risk=_RISK, **kw)


# ---------------------------------------------------------------------------
# 照抄與標籤
# ---------------------------------------------------------------------------

def test_every_number_is_copied_verbatim() -> None:
    report = fake_report()
    payload = build_beta_artifact(report, series_by_key=fake_series(), policy_risk=_RISK)
    for got, src in zip(payload["allocation"]["sleeves"], report["allocation_gap"]["sleeves"]):
        for key, value in src.items():
            assert got[key] == value, key
    for got, src in zip(payload["instruments"], report["items"]):
        for key, value in src.items():
            assert got[key] == value, key
    assert payload["risk"]["snapshot"] == report["risk_snapshot"]
    assert payload["capital"]["deployable_cash_base"] is report["portfolio"]["deployable_cash_base"]
    assert payload["capital"]["credit"]["undrawn_amount_base"] is report["contingent_credit_available"]["undrawn_amount_base"]
    assert payload["risk"]["thresholds"] == _RISK


def test_labels_come_from_the_allocation_module_not_a_second_table() -> None:
    payload = fake_beta_payload()
    for s in payload["allocation"]["sleeves"]:
        assert s["label"] == _sleeve_label(s["sleeve"])
        assert s["state_label"] == _gap_state_label(s["state"])
    assert payload["allocation"]["sleeves"][2]["unavailable_label"] == "此 sleeve 的部位金額不可得"
    assert payload["vocab"]["sleeve_labels"]["beta_core"] == "全球廣度錨"
    tw = payload["instruments"][1]
    assert tw["status_label"] == "🔴 資料不足"
    assert tw["blocker_labels"] == ["TWSE 官方行情較新，本列暫時隔離"]


def test_color_slot_is_fixed_by_sleeve_order_not_by_value() -> None:
    payload = fake_beta_payload()
    assert [s["slot"] for s in payload["allocation"]["sleeves"]] == [1, 2, 3]


def test_missing_is_never_zero() -> None:
    payload = fake_beta_payload()
    alpha = payload["allocation"]["sleeves"][2]
    assert alpha["actual"] is None and alpha["gap"] is None and alpha["state"] == "unknown"
    tw = payload["instruments"][1]
    assert tw["series"] == [] and "不是價格為 0" in tw["series_note"]


# ---------------------------------------------------------------------------
# 契約紅線
# ---------------------------------------------------------------------------

def test_momentum_columns_never_reach_the_artifact() -> None:
    """Engine C 的 technical_observations 還留著 08-29 前的動能欄位；artifact 一格都不准帶。"""
    keys: set[str] = set()

    def walk(value):
        if isinstance(value, dict):
            for k, v in value.items():
                keys.add(str(k).lower()); walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)

    walk(fake_beta_payload())
    banned = [k for k in keys if k.startswith(("rsi", "macd", "sma_50_slope")) or k in {"pace", "tier", "signal"}]
    assert not banned, banned
    series = fake_beta_payload()["instruments"][0]["series"]
    assert series == [{"session_date": "2026-09-02", "close": 712.1}, {"session_date": "2026-09-03", "close": 717.7},
                      {"session_date": "2026-09-04", "close": 718.96}]      # 由舊到新，只有兩格


def test_no_timing_language_anywhere() -> None:
    text = json.dumps(fake_beta_payload(), ensure_ascii=False)
    for token in ("可評估", "冷卻", "暫停新增", "本輪上限", "節奏", "熱度"):
        assert token not in text, token
    assert "不是該等回檔的訊號" in text
    assert "不賣出" in text


def test_freshness_identity_tracks_states_not_prices() -> None:
    a = fake_beta_payload()
    report = fake_report()
    report["items"][0]["heartbeat"]["return_1d"] = 0.05
    report["items"][0]["water_level"]["range_percentile_52w"] = 0.5
    b = build_beta_artifact(report, series_by_key=fake_series(), policy_risk=_RISK)
    assert b["freshness_identity"] == a["freshness_identity"]
    assert b["content_digest"] != a["content_digest"]
    report["allocation_gap"]["sleeves"][0]["state"] = "on_target"
    c = build_beta_artifact(report, series_by_key=fake_series(), policy_risk=_RISK)
    assert c["freshness_identity"] != a["freshness_identity"]


def test_state_kind_registered_and_validates() -> None:
    assert "beta" in STATE_KINDS
    payload = fake_beta_payload()
    assert validate_state_artifact("beta", payload) is payload
    with pytest.raises(ArtifactUnavailable, match="content_digest"):
        validate_state_artifact("beta", dict(payload, instruments=[]))
    with pytest.raises(ArtifactUnavailable, match="kind"):
        validate_state_artifact("ranking", payload)


def test_issuer_focus_only_lists_issuers_at_or_above_the_warning() -> None:
    payload = fake_beta_payload()
    assert list(payload["risk"]["issuer_focus"]) == ["TSMC"]


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path):
    ArtifactStore(tmp_path).write(materialize_view(fake_view("QQQ")))
    StateArtifactStore(tmp_path / "state").write(fake_beta_payload())
    return TestClient(create_app(tmp_path))


def test_beta_endpoint_serves_the_artifact_verbatim(client) -> None:
    body = client.get("/api/v1/beta").json()
    payload = fake_beta_payload()
    assert body["kind"] == "beta"
    assert body["allocation"] == payload["allocation"]
    assert body["instruments"] == payload["instruments"]
    assert body["freshness"]["state"] == "fresh"
    assert body["analyst_view_tickers"] == ["QQQ"]


def test_beta_absent_is_503_with_its_own_remedy(tmp_path) -> None:
    ArtifactStore(tmp_path).write(materialize_view(fake_view("QQQ")))
    client = TestClient(create_app(tmp_path))
    response = client.get("/api/v1/beta")
    assert response.status_code == 503
    error = response.json()["error"]
    assert error["state_kind"] == "beta" and "materialize --beta" in error["remedy"]
    assert not (tmp_path / "state" / "beta.json").exists()


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_beta_rejects_mutation_verbs(client, method: str) -> None:
    assert client.request(method, "/api/v1/beta").status_code == 405


def test_meta_declares_beta(client) -> None:
    meta = client.get("/api/v1/meta").json()
    assert "GET /api/v1/beta" in meta["endpoints"]


# ---------------------------------------------------------------------------
# 前端
# ---------------------------------------------------------------------------

def test_frontend_beta_view_has_no_momentum_no_timing_no_sizing() -> None:
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    assert "function renderBeta" in source
    for token in ("rsi_", "RSI", "macd", "MACD", "可評估", "冷卻", "暫停新增", "該買", "建議買", "加碼", ".sort("):
        assert token not in source, token
    # 圖表只做座標換算與 ×100 排版；沒有任何財務算術（差距、比例、金額都來自 artifact）
    for token in ("= s.actual -", "actual - target", "target - actual", "/ nav", "* nav"):
        assert token not in source, token
    html = (ROOT / "webapp" / "static" / "index.html").read_text(encoding="utf-8")
    assert 'href="#/beta"' in html
    css = (ROOT / "webapp" / "static" / "styles.css").read_text(encoding="utf-8")
    assert "--viz-s1" in css and "--viz-good" in css


def test_charts_read_palette_from_css_roles_not_inline_hex() -> None:
    """dataviz：色跟角色走，圖表程式不硬寫 hex。"""
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    import re
    assert not re.search(r"#[0-9a-fA-F]{6}\b", source), "app.js 不得硬寫 hex 顏色（放 styles.css 的 --viz-* 角色）"
