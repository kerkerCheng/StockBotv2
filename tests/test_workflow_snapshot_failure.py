"""snapshot 取得失敗時要留下可稽核的原因，而不是靜默塌成「什麼都沒有」。

事發（2026-08-28）：對 COHR 跑 live reassess 不給 `--as-of` 時，decision 回了五個
blocker（holdings_unavailable／live_nav_missing／execution_fx_missing／
live_context_not_ready／portfolio_leverage_unavailable），看起來像五項資料各自缺失。
實際上 provider 的 holdings、fx、market 全部正常——那五個是同一次 `provider.snapshot()`
例外的投影，而 `_snapshot()` 的 `except Exception` 把原因丟掉了。

結果是把一次取得失敗誤讀成研究不足，並讓「20/21 個 cohort 卡住」這個判斷偏掉。
fail closed 的行為本身是對的（不讓整份 Daily 崩掉），錯的是不留痕跡。
"""
from __future__ import annotations

from decision_lab.workflow import _snapshot
from decision_lab.workflow_ports import AuthoritySnapshot, IdentityAuthority

IDENT = IdentityAuthority(
    status="resolved",
    company_id="co:example",
    research_ticker="EXMPL",
)


class _RaisingProvider:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def snapshot(self, *, identity, evaluation_at):  # noqa: ANN001 - 測試替身
        raise self._exc


class _WrongTypeProvider:
    def snapshot(self, *, identity, evaluation_at):  # noqa: ANN001 - 測試替身
        return {"not": "a snapshot"}


class _GoodProvider:
    def snapshot(self, *, identity, evaluation_at):  # noqa: ANN001 - 測試替身
        return AuthoritySnapshot(
            identity=identity,
            evidence={"status": "available"},
            financial={"status": "observed"},
            market={"status": "observed"},
            fx={"status": "observed"},
            holdings={"status": "available", "rows": []},
            statuses={"identity": "resolved", "holdings": "available"},
        )


def test_provider_exception_records_type_not_silence() -> None:
    """例外類型要出現在 statuses，讓下游知道這批 unavailable 同源。"""
    snap = _snapshot(_RaisingProvider(TimeoutError("upstream timed out")), IDENT, "2026-08-28T00:00:00+00:00")

    assert snap.statuses["snapshot_failure"] == "TimeoutError"
    assert snap.holdings["status"] == "unavailable"
    assert snap.fx["status"] == "unavailable"


def test_failure_marker_carries_type_only_never_the_message() -> None:
    """例外訊息可能含憑證路徑或 token，只准進 log，不准進 decision payload。"""
    secret = "/home/user/.config/gcloud/service-account-abc123.json"
    snap = _snapshot(
        _RaisingProvider(RuntimeError(f"could not read {secret}")),
        IDENT,
        "2026-08-28T00:00:00+00:00",
    )

    assert snap.statuses["snapshot_failure"] == "RuntimeError"
    rendered = str(snap.statuses)
    assert secret not in rendered
    assert "service-account" not in rendered


def test_wrong_return_type_is_distinguishable_from_an_exception() -> None:
    """provider 回錯型別與 provider 拋錯是兩件事，不該共用同一個訊號。"""
    snap = _snapshot(_WrongTypeProvider(), IDENT, "2026-08-28T00:00:00+00:00")

    assert snap.statuses["snapshot_failure"] == "InvalidSnapshotType"


def test_successful_snapshot_has_no_failure_marker() -> None:
    """成功時不得留下這個 key——否則它會變成恆亮而失去鑑別力（L14）。"""
    snap = _snapshot(_GoodProvider(), IDENT, "2026-08-28T00:00:00+00:00")

    assert "snapshot_failure" not in snap.statuses
    assert snap.holdings["status"] == "available"


def test_failure_still_fails_closed() -> None:
    """留痕跡不等於放行：所有 authority section 仍必須是 unavailable。"""
    snap = _snapshot(_RaisingProvider(ValueError("boom")), IDENT, "2026-08-28T00:00:00+00:00")

    for section in (snap.financial, snap.market, snap.fx, snap.holdings):
        assert section["status"] == "unavailable"
    assert "graph_unavailable" in snap.evidence["blockers"]
