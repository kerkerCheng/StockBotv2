"""TWSE freshness oracle 與 Yahoo session reconciliation。"""
from __future__ import annotations

import json
import ssl

import pytest

import engine_c.twse as twse
from engine_c.technical import build_technical_observation, reconcile_twse_freshness
from engine_c.twse import TWSE_STOCK_DAY_ALL_URL, fetch_twse_latest_rows


class _Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


def test_fetch_twse_latest_rows_parses_roc_date_and_change() -> None:
    calls = []

    def opener(url, *, timeout):
        calls.append((url, timeout))
        return _Response(
            [
                {
                    "Date": "1150731",
                    "Code": "0050",
                    "ClosingPrice": "102.85",
                    "Change": "+9.3500",
                },
                {
                    "Date": "1150731",
                    "Code": "00981A",
                    "ClosingPrice": "26.13",
                    "Change": "+2.3700",
                },
            ]
        )

    rows = fetch_twse_latest_rows(opener=opener)

    assert calls == [(TWSE_STOCK_DAY_ALL_URL, 10.0)]
    assert rows["0050"]["code"] == "0050"
    assert rows["0050"]["session_date"] == "2026-07-31"
    assert rows["0050"]["close_raw"] == 102.85
    assert rows["0050"]["change_raw"] == 9.35
    assert rows["0050"]["change_pct"] == 0.1
    assert rows["0050"]["source"] == TWSE_STOCK_DAY_ALL_URL
    assert rows["00981A"]["change_pct"] == pytest.approx(2.37 / 23.76)


def test_fetch_twse_latest_rows_retries_one_transient_transport_error() -> None:
    calls = []

    def opener(url, *, timeout):
        calls.append((url, timeout))
        if len(calls) == 1:
            raise TimeoutError("temporary")
        return _Response(
            [
                {
                    "Date": "1150731",
                    "Code": "0050",
                    "ClosingPrice": "102.85",
                    "Change": "+9.3500",
                }
            ]
        )

    rows = fetch_twse_latest_rows(opener=opener)

    assert len(calls) == 2
    assert rows["0050"]["session_date"] == "2026-07-31"


def test_default_transport_keeps_tls_verification_without_x509_strict(
    monkeypatch,
) -> None:
    captured = {}

    def fake_urlopen(url, *, timeout, context):
        captured.update(url=url, timeout=timeout, context=context)
        return _Response(
            [
                {
                    "Date": "1150731",
                    "Code": "0050",
                    "ClosingPrice": "102.85",
                    "Change": "+9.3500",
                }
            ]
        )

    monkeypatch.setattr(twse, "urlopen", fake_urlopen)

    rows = fetch_twse_latest_rows()

    context = captured["context"]
    assert rows["0050"]["session_date"] == "2026-07-31"
    assert captured["url"] == TWSE_STOCK_DAY_ALL_URL
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    strict_flag = getattr(ssl, "VERIFY_X509_STRICT", 0)
    if strict_flag:
        assert not context.verify_flags & strict_flag


def test_twse_newer_session_quarantines_old_yahoo_signal() -> None:
    origin_rows = [
        {
            "as_of": f"2025-01-{index:02d}T00:00:00+00:00",
            "close_raw": 100.0 + index,
            "close_adjusted": 100.0 + index,
            "complete": True,
        }
        for index in range(1, 10)
    ]
    observation = build_technical_observation(
        benchmark_key="tw50",
        provider_symbol="0050.TW",
        rows=origin_rows,
        fetched_at="2026-08-01T00:00:00+00:00",
        source="fixture://yahoo",
    )
    observation["session_date"] = "2026-07-30"
    observation["data_status"] = "observed"
    observation["blockers"] = []

    reconciled = reconcile_twse_freshness(
        observation,
        reference={
            "code": "0050",
            "session_date": "2026-07-31",
            "close_raw": 102.85,
            "change_raw": 9.35,
            "change_pct": 0.1,
            "source": TWSE_STOCK_DAY_ALL_URL,
        },
    )

    assert reconciled["data_status"] == "quarantined"
    assert reconciled["blockers"] == ["technical_session_stale_vs_twse"]
    assert reconciled["_twse_reference"]["status"] == "provider_lagging"
    assert reconciled["_twse_reference"]["change_pct"] == 0.1


def test_twse_oracle_failure_fails_closed_for_observed_tw_symbol() -> None:
    observation = {
        "benchmark_key": "tw50",
        "provider_symbol": "0050.TW",
        "session_date": "2026-07-30",
        "data_status": "observed",
        "blockers": [],
        "warnings": [],
    }

    reconciled = reconcile_twse_freshness(
        observation,
        reference=None,
        oracle_error="TimeoutError",
    )

    assert reconciled["data_status"] == "quarantined"
    assert reconciled["blockers"] == ["technical_twse_freshness_unavailable"]
    assert reconciled["_twse_reference"]["status"] == "unavailable"
