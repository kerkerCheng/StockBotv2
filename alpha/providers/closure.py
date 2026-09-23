"""每檔閉環的 I/O 收集端（alpha/providers 是 alpha 底下唯一准碰外部世界的子套件）。

讀三個來源，各自 fail-soft：analyst view artifact（必要）、Engine C 共識（選）、structure_table state＋registry（選）。
純函式（終局、排序、摘要）住 `alpha/closure.py`；本檔只負責把資料送進去。
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from alpha.closure import (
    BacklogRow,
    _base_observation_tickers,
    _consensus_flags,
    _sector_and_structure_edge,
    deferred_tickers,
    row_from_artifact,
)


def collect_backlog(*, artifact_dir: Path | None = None, state_dir: Path | None = None,
            conn: Any = None) -> tuple[list[BacklogRow], list[str]]:
    """讀 artifact（必要）＋共識（選）＋結構表的產業與結構邊（選）。回 (rows, notes)。"""
    from webapp.store import ArtifactStore, StateArtifactStore, resolve_state_dir

    notes: list[str] = []
    store = ArtifactStore(artifact_dir)
    rows: list[BacklogRow] = []
    for ticker, payload, _fresh, reason in store.read_all():
        if payload is None:
            notes.append(f"{ticker} artifact 壞掉：{reason}")
            continue
        rows.append(row_from_artifact(ticker, payload, today=date.today()))
    if not rows:
        return [], notes + ["尚無 materialized analyst view（python -m webapp materialize --registry-listed）"]

    # 共識：Engine C
    flags: dict[str, tuple[bool, bool | None]] = {}
    base_obs: frozenset[str] | None = None
    try:
        if conn is None:
            from engine_c.db import get_conn

            conn = get_conn()
        flags = _consensus_flags([r.ticker for r in rows], conn)
    except Exception as exc:  # noqa: BLE001
        notes.append(f"Engine C 共識讀不到：{type(exc).__name__}")
    # 基期觀測分開 try：共識讀不到不該把成本維度一起拖成「全部未知」，反之亦然。
    # 讀不到時留 None（＝「未讀到」），不是 False——False 會把整批推到最後面（L12）。
    if conn is not None:
        try:
            base_obs = _base_observation_tickers(conn)
        except Exception as exc:  # noqa: BLE001
            notes.append(f"Engine C 基期觀測讀不到：{type(exc).__name__}")

    # 目標期間是不是已經結束（＝財報空窗）**現在由 `row_from_artifact` 自己判**（2026-09-19）：
    # artifact 的 `headline.context.period_end` 就是那一格，而它與共識 `0y` 的期末實測
    # **73/73 相同、0 例外**。先前這裡另查一次 Engine C，等於同一個分類有兩份實作——
    # 而 APP 端拿不到這一份，於是「等財報」在 APP 變成「還沒做」（L16）。
    # ⚠ **時鐘仍然住在這一層**：`row_from_artifact` 只在收到 `today` 時才判，純函式不看時鐘。

    # 產業與結構邊：structure_table state ＋ registry ＋ config/sector_anchors.json（錨→產業的 SSOT）
    sector_edge: dict[str, tuple[str | None, bool]] = {}
    try:
        payload, _fresh = StateArtifactStore(resolve_state_dir(artifact_dir, state_dir)).read("structure_table")
        from identity import get_registry

        sector_edge = _sector_and_structure_edge(payload, get_registry(), _anchor_to_sector())
    except Exception as exc:  # noqa: BLE001
        notes.append(f"structure_table state 讀不到：{type(exc).__name__}")

    # pq2 的使用者 defer：讀結構化欄位，讀不到就是空集合（不猜、不 parse 標題）
    deferred: frozenset[str] = frozenset()
    try:
        from engine_b.todo import load as load_pool
        from identity import get_registry

        registry = get_registry()

        def _resolve(company_id: str) -> str | None:
            try:
                return getattr(registry.company(company_id), "research_ticker", None)
            except Exception:  # noqa: BLE001
                return None

        deferred = deferred_tickers(load_pool(), _resolve)
    except Exception as exc:  # noqa: BLE001
        notes.append(f"pq2 待辦池讀不到，本輪不套「使用者已 defer」：{type(exc).__name__}")

    enriched: list[BacklogRow] = []
    for r in rows:
        has_c, pos = flags.get(r.ticker, (None, None))
        awaiting = r.awaiting_report_since      # 已由 row_from_artifact 判好，這裡只照抄
        sector, has_edge = sector_edge.get(r.ticker.upper(), (None, (False if sector_edge else None)))
        enriched.append(BacklogRow(
            ticker=r.ticker, readiness=r.readiness, open_panels=r.open_panels, settled_panels=r.settled_panels,
            absence_kinds=r.absence_kinds, has_consensus=has_c, forward_eps_positive=pos,
            sector=sector, has_structure_edge=has_edge,
            has_base_observation=(None if base_obs is None else r.ticker.upper() in base_obs),
            user_deferred=r.ticker.upper() in deferred,
            awaiting_report_since=awaiting,
            generated_at=r.generated_at,
        ))
    return enriched, notes



def _anchor_to_sector() -> dict[str, str]:
    """錨→產業對照。SSOT 是 `config/sector_anchors.json`；讀不到就回空（全部落入「產業未知」，不猜）。"""
    import json

    path = Path(__file__).resolve().parents[2] / "config" / "sector_anchors.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(anchor): str(sector)
            for sector, anchors in (data.get("sectors") or {}).items()
            for anchor in (anchors or [])}


__all__ = ["collect_backlog"]
