"""每檔閉環的 I/O 收集端（alpha/providers 是 alpha 底下唯一准碰外部世界的子套件）。

讀三個來源，各自 fail-soft：analyst view artifact（必要）、Engine C 共識（選）、ranking state＋registry（選）。
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
    _sector_and_rank,
    _target_period_ends,
    deferred_tickers,
    row_from_artifact,
)


def collect_backlog(*, artifact_dir: Path | None = None, state_dir: Path | None = None,
            conn: Any = None) -> tuple[list[BacklogRow], list[str]]:
    """讀 artifact（必要）＋共識（選）＋排序產業（選）。回 (rows, notes)。"""
    from webapp.store import ArtifactStore, StateArtifactStore, resolve_state_dir

    notes: list[str] = []
    store = ArtifactStore(artifact_dir)
    rows: list[BacklogRow] = []
    for ticker, payload, _fresh, reason in store.read_all():
        if payload is None:
            notes.append(f"{ticker} artifact 壞掉：{reason}")
            continue
        rows.append(row_from_artifact(ticker, payload))
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

    # 目標期間是不是已經結束（＝財報空窗）。**時鐘住這裡**，`alpha/closure.py` 保持純函式。
    # 讀不到一律留 None——那會讓該檔照舊算成未到終局（寧可多排一檔，不把讀不到當終局，INV-3）。
    target_ends: dict[str, str | None] = {}
    if conn is not None:
        try:
            target_ends = _target_period_ends([r.ticker for r in rows], conn)
        except Exception as exc:  # noqa: BLE001
            notes.append(f"Engine C 目標期間讀不到，本輪不判「等財報」：{type(exc).__name__}")

    # 產業與名次：ranking state ＋ registry
    sector_rank: dict[str, tuple[str | None, int | None]] = {}
    try:
        payload, _fresh = StateArtifactStore(resolve_state_dir(artifact_dir, state_dir)).read("ranking")
        from identity import get_registry

        sector_rank = _sector_and_rank(payload, get_registry())
    except Exception as exc:  # noqa: BLE001
        notes.append(f"ranking state 讀不到：{type(exc).__name__}")

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

    today = date.today()
    enriched: list[BacklogRow] = []
    for r in rows:
        has_c, pos = flags.get(r.ticker, (None, None))
        end = target_ends.get(r.ticker)
        awaiting: str | None = None
        if end:
            try:
                awaiting = end if date.fromisoformat(end) <= today else None
            except ValueError:
                awaiting = None
        sector, rank = sector_rank.get(r.ticker.upper(), (None, None))
        enriched.append(BacklogRow(
            ticker=r.ticker, readiness=r.readiness, open_panels=r.open_panels, settled_panels=r.settled_panels,
            absence_kinds=r.absence_kinds, has_consensus=has_c, forward_eps_positive=pos,
            sector=sector, bottleneck_rank=rank,
            has_base_observation=(None if base_obs is None else r.ticker.upper() in base_obs),
            user_deferred=r.ticker.upper() in deferred,
            awaiting_report_since=awaiting,
            generated_at=r.generated_at,
        ))
    return enriched, notes



__all__ = ["collect_backlog"]
