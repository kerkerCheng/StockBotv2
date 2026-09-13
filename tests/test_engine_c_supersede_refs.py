"""更正一筆基期觀測之後，引用舊 id 的假設**不得**整條消失（2026-09-13）。

## 為什麼要有這一份

Engine C 的人工 ledger 是 append-only：更正的做法是 append 一筆新紀錄並指定 `--supersedes`（L10）。
但假設層是用 `engine_c://manual_observation/<observation_id>` 這個**字串**引用基期的，
而被 supersede 的 id 原本就不再出現在 evidence index 裡 → 每一條引用它的假設變成
`unresolved_evidence`，而下游的表現是**整檔一起消失**，不是「這一條的證據過期了」。

實測代價（2026-09-13 同日兩次，都是**數字一字未改**的更正）：
AEVA 更正 `coverage_note` 之後 probe 立刻變成
`why → 沒有任何可用的 OperatingAssumption（unresolved_evidence=8）`，
要復原必須把 8 條 operating ＋ 1 條 valuation ＋ 1 條 horizon 共 10 筆全部重寫；
4971.TWO 更正交易對手名稱時同樣要重寫 6 條 ＋ 估值 ＋ horizon。

⚠ 最危險的是訊號形狀：**「更正成功」與「更正成功但打掉十筆假設」在寫入端是同一個
`✓ 已寫入 mo_xxx`**（L13-2：成功與失敗在同一個訊號上同形）。
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import date

from alpha.contracts import Ticker
from alpha.providers.fundamentals import EngineCFundamentalsProvider
from engine_c.db import _ensure_sqlite_schema

OLD = "mo_" + "1" * 32
MID = "mo_" + "2" * 32
NEW = "mo_" + "3" * 32


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _ensure_sqlite_schema(conn)
    return conn


def _payload(note: str) -> str:
    return json.dumps({
        "fiscal_year_end": "2025-12-31", "currency": "USD", "revenue": 18_079_000.0,
        "gaap": {"operating_income": -127_597_000.0}, "coverage_note": note,
    }, ensure_ascii=False)


def _insert(conn, observation_id: str, supersedes: str | None, note: str, recorded: str) -> None:
    conn.execute(
        "INSERT INTO manual_observations (observation_id, ticker, field_name, value, source_ref, "
        "as_of, recorded_at, author, supersedes_id, payload_digest) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (observation_id, "AEVA", "fiscal_year_results", _payload(note), "10-K accession x",
         "2025-12-31T00:00:00+00:00", recorded, "session", supersedes,
         hashlib.sha256(note.encode("utf-8")).hexdigest()))
    conn.commit()


def test_supersede_chain_stays_resolvable_so_older_assumptions_do_not_vanish() -> None:
    conn = _conn()
    _insert(conn, OLD, None, "第一版（xbrl_backfill 只有兩格）", "2026-09-10T00:00:00+00:00")
    _insert(conn, MID, OLD, "第二版（完整組合）", "2026-09-12T00:00:00+00:00")
    _insert(conn, NEW, MID, "第三版（只改結論，數字未動）", "2026-09-13T00:00:00+00:00")
    provider = EngineCFundamentalsProvider(conn=conn)
    actuals, reason = provider.fiscal_year_results(Ticker("AEVA"))
    assert reason is None and actuals is not None
    assert actuals.observation_id == NEW                     # 生效的還是最新那一筆
    assert "第三版" in (actuals.coverage_note or "")           # 值取自最新，不是祖先

    refs = {r.ref: r for r in actuals.evidence}
    # ⚠ 驗收的就是這一行：整條鏈都解析得到，所以引用舊 id 的假設不會變成 unresolved。
    assert set(refs) == {f"engine_c://manual_observation/{i}" for i in (OLD, MID, NEW)}
    # 而且**看得出來哪一筆是舊版**——不是讓舊引用「看起來還有效」。
    assert "取代" not in (refs[f"engine_c://manual_observation/{NEW}"].quote or "")
    assert f"已被 {NEW} 取代" in (refs[f"engine_c://manual_observation/{MID}"].quote or "")
    assert f"已被 {MID} 取代" in (refs[f"engine_c://manual_observation/{OLD}"].quote or "")


def test_a_single_observation_has_no_superseded_refs() -> None:
    """沒有更正過的標的不得多出任何 ref（這道機制只在有鏈的時候作用）。"""
    conn = _conn()
    _insert(conn, OLD, None, "唯一一版", "2026-09-10T00:00:00+00:00")
    actuals, reason = EngineCFundamentalsProvider(conn=conn).fiscal_year_results(Ticker("AEVA"))
    assert reason is None and actuals is not None
    assert [r.ref for r in actuals.evidence] == [f"engine_c://manual_observation/{OLD}"]
