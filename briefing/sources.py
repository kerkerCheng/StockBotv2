"""Brief 各 pane 的取數：狀態檔與 live 部位事件。

取數住組裝層而不是 domain，沿用 `engine_d_runtime.adapters` 已建立的同一條線：
**pane 的純轉換住 domain（可離線測），碰檔案／provider 的部分住組裝層。**
每一支都 fail-soft——首屏計數器讀不到只該讓那一行說「讀不到」，不該讓整份 brief
失敗（它們是加值訊號，不是 brief 的前置條件）。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

__all__ = [
    "load_backup_status",
    "load_outcome_aggregate",
    "fetch_alpha_position_events",
]

_PRIVATE_ROOT = Path(__file__).resolve().parents[1] / "library" / "private"


def load_outcome_aggregate(private_root: Path | None = None) -> dict[str, Any] | None:
    """讀 `scripts/outcome_if_settled_today.py` 落的等權聚合狀態檔（2026-09-02）。

    None＝檔不存在或壞掉——renderer 顯示「未量測」提示，不靜默。"""
    if private_root is None:
        private_root = _PRIVATE_ROOT
    path = private_root / "decision_lab" / "outcome_aggregate.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return {
            "date": str(raw["date"]),
            "n": int(raw["n"]),
            "equal_weight_absolute": float(raw["equal_weight_absolute"]),
            "equal_weight_excess": (
                float(raw["equal_weight_excess"])
                if raw.get("equal_weight_excess") is not None
                else None
            ),
            "benchmark": str(raw.get("benchmark") or ""),
        }
    except (OSError, ValueError, KeyError, TypeError):
        return None


def load_backup_status(
    now: datetime | None = None, private_root: Path | None = None
) -> dict[str, Any] | None:
    """讀 `scripts/backup_private.py` 寫的 status 檔，轉成首屏計數器 payload。

    回傳值三分（L12——別把不同語意壓進同一訊號）：
    - ``None``：這個 surface 沒有 private root，renderer 整行略過；
    - ``{"status": "never"}``：有 private root 但從未備份；
    - ``{"status": "invalid"}``：status 檔存在但無法解讀——視同沒有備份現形，
      不得因為讀不到就安靜消失（那正是備份「安靜停掉」的形狀）。
    """
    if private_root is None:
        private_root = _PRIVATE_ROOT
    if not private_root.is_dir():
        return None
    status_path = private_root / "backups" / "last_backup.json"
    if not status_path.is_file():
        return {"status": "never"}
    try:
        raw = json.loads(status_path.read_text(encoding="utf-8"))
        created = datetime.fromisoformat(
            str(raw["created_at"]).replace("Z", "+00:00")
        )
    except (OSError, ValueError, KeyError, TypeError):
        return {"status": "invalid"}
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    drive = raw.get("drive") if isinstance(raw.get("drive"), dict) else {}
    verification = (
        raw.get("restore_verification")
        if isinstance(raw.get("restore_verification"), dict)
        else {}
    )
    return {
        "status": "ok",
        "age_days": max(0, (current - created).days),
        "backup_id": str(raw.get("backup_id") or ""),
        "drive_status": str((drive or {}).get("status") or "unknown"),
        "restore_verified": bool((verification or {}).get("verified_at")),
    }


def fetch_alpha_position_events(
    store: Any,
    *,
    series_by_ticker: Mapping[str, Any] | None,
) -> list[dict[str, Any]] | None:
    """Alpha live 部位的事件 packet；surface 不提供這個能力時回 None。

    ⚠ 這條路徑存在的理由見 `alpha.position_events` 的模組 docstring：beta 的事件
    監控對 alpha 部位結構上恆不觸發。行情缺失、provider 失敗或未登記門檻都只降級成
    空 list，不阻斷 brief——事件監控是加值訊號，不是 brief 的前置條件。
    """

    positions_fn = getattr(store, "open_live_positions", None)
    if not callable(positions_fn):
        return None
    try:
        from alpha.position_events import alpha_event_search_requests
        from alpha.providers.close_series import fetch_close_series
        from risk.policy import load_policy

        positions = list(positions_fn())
        if not positions:
            return []
        policy = load_policy()
        monitor = policy.get("live_position_monitor") or {}
        series = series_by_ticker
        if series is None:
            series = fetch_close_series(
                (position.get("ticker") for position in positions),
                sessions=int(monitor.get("history_sessions") or 10),
            )
        return alpha_event_search_requests(
            positions, series_by_ticker=series or {}, policy=policy
        )
    except Exception:  # noqa: BLE001 — 監控失敗不得讓整份 brief 失敗
        return []
