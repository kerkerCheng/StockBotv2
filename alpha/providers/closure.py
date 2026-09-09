"""每檔閉環的 I/O 收集端（alpha/providers 是 alpha 底下唯一准碰外部世界的子套件）。

讀三個來源，各自 fail-soft：analyst view artifact（必要）、Engine C 共識（選）、ranking state＋registry（選）。
純函式（終局、排序、摘要）住 `alpha/closure.py`；本檔只負責把資料送進去。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from alpha.closure import BacklogRow, _consensus_flags, _sector_and_rank, row_from_artifact


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
    try:
        if conn is None:
            from engine_c.db import get_conn

            conn = get_conn()
        flags = _consensus_flags([r.ticker for r in rows], conn)
    except Exception as exc:  # noqa: BLE001
        notes.append(f"Engine C 共識讀不到：{type(exc).__name__}")

    # 產業與名次：ranking state ＋ registry
    sector_rank: dict[str, tuple[str | None, int | None]] = {}
    try:
        payload, _fresh = StateArtifactStore(resolve_state_dir(artifact_dir, state_dir)).read("ranking")
        from identity import get_registry

        sector_rank = _sector_and_rank(payload, get_registry())
    except Exception as exc:  # noqa: BLE001
        notes.append(f"ranking state 讀不到：{type(exc).__name__}")

    enriched: list[BacklogRow] = []
    for r in rows:
        has_c, pos = flags.get(r.ticker, (None, None))
        sector, rank = sector_rank.get(r.ticker.upper(), (None, None))
        enriched.append(BacklogRow(
            ticker=r.ticker, readiness=r.readiness, open_panels=r.open_panels, settled_panels=r.settled_panels,
            absence_kinds=r.absence_kinds, has_consensus=has_c, forward_eps_positive=pos,
            sector=sector, bottleneck_rank=rank, generated_at=r.generated_at,
        ))
    return enriched, notes



__all__ = ["collect_backlog"]
