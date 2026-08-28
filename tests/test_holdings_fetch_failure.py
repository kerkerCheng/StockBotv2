"""持股取得失敗要留下原因，並一路凍進 context。

這是 `tests/test_workflow_snapshot_failure.py` 的同形狀第二處。實測（2026-08-28）：
COHR 第一次 live reassess 回了五個 blocker，其中 holdings_unavailable 只可能由
adapter 層的 `except Exception` 產生——也就是那次 Google Sheet 呼叫真的拋錯了。
但原因被吞掉，於是四個連鎖 blocker（live_nav_missing、portfolio_leverage_unavailable、
live_context_not_ready）看起來像各自獨立的資料缺失，把一次瞬時 API 失敗誤讀成研究不足。

持股來自 Google Sheet API，瞬時失敗是常態而非例外，所以這一處比 `_snapshot()` 更常被觸發。
"""
from __future__ import annotations

from decision_lab.context import _normalize_holdings
from engine_d_runtime.adapters import DefaultRuntimeProvider


class _Store:
    """_normalize_holdings 在 upstream 失敗時不會走到 store。"""

    def latest_holdings_confirmation(self, digest):  # noqa: ANN001 - 測試替身
        raise AssertionError("upstream 失敗時不該查 confirmation")


def _provider(fetcher) -> DefaultRuntimeProvider:
    return DefaultRuntimeProvider(holdings_fetcher=fetcher)


def test_fetch_exception_records_type() -> None:
    def boom():
        raise TimeoutError("sheets API timed out")

    result = _provider(boom).current_holdings(evaluation_at="2026-08-28T00:00:00+00:00")

    assert result["status"] == "unavailable"
    assert result["blockers"] == ["holdings_unavailable"]
    assert result["failure"] == "TimeoutError"


def test_failure_marker_never_carries_the_message() -> None:
    """例外訊息可能含 service account 路徑或 token，只准進 log。"""
    secret = "/home/user/.config/gcloud/sa-key-abc123.json"

    def boom():
        raise RuntimeError(f"cannot open {secret}")

    result = _provider(boom).current_holdings(evaluation_at="2026-08-28T00:00:00+00:00")

    assert result["failure"] == "RuntimeError"
    assert secret not in str(result)
    assert "sa-key" not in str(result)


def test_successful_fetch_has_no_failure_marker() -> None:
    """成功時不留 key——恆亮的 marker 沒有鑑別力（L14）。"""
    result = _provider(lambda: []).current_holdings(
        evaluation_at="2026-08-28T00:00:00+00:00"
    )

    assert result["status"] == "available"
    assert "failure" not in result


def test_failure_reason_survives_into_frozen_context() -> None:
    """marker 要一路到 context，否則 decision 只留下一個沒有成因的 blocker。"""
    upstream = {
        "status": "unavailable",
        "rows": [],
        "blockers": ["holdings_unavailable"],
        "failure": "TimeoutError",
    }

    frozen = _normalize_holdings(
        _Store(),
        upstream,
        evaluation_at="2026-08-28T00:00:00+00:00",
        expected_symbol=None,
        expected_currency=None,
    )

    assert frozen["status"] == "unavailable"
    assert frozen["blockers"] == ["holdings_unavailable"]
    assert frozen["failure"] == "TimeoutError"


def test_upstream_without_failure_marker_stays_clean() -> None:
    """沒有 marker 的舊 payload 不得憑空長出 failure 欄位。"""
    frozen = _normalize_holdings(
        _Store(),
        {"status": "unavailable", "rows": [], "blockers": ["holdings_unavailable"]},
        evaluation_at="2026-08-28T00:00:00+00:00",
        expected_symbol=None,
        expected_currency=None,
    )

    assert "failure" not in frozen
