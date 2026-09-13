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

import pytest
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


# ---------------------------------------------------------------------------
# 2026-09-13：快照股數錯得離譜時，市值拒絕輸出（ROADMAP L222）
# ---------------------------------------------------------------------------

def test_market_cap_refuses_to_output_when_snapshot_shares_contradict_the_filing() -> None:
    """`market_cap = price × shares`，而快照股數錯 5 倍時那個數看起來完全正常。

    ⚠ 選「拒絕輸出」而不是「照給但標記」的理由：市值的唯一用途是拿去比較，
    而一個錯 5.25 倍的市值在比較時不會露出任何破綻。缺席會讓消費端停下來問為什麼。
    """
    conn = _conn()
    payload = json.dumps({
        "fiscal_year_end": "2025-12-31", "currency": "TWD", "revenue": 1.0e10,
        "gaap": {"operating_income": 1.0e9, "diluted_shares": 424_512_000.0},
    }, ensure_ascii=False)
    conn.execute(
        "INSERT INTO manual_observations (observation_id, ticker, field_name, value, source_ref, "
        "as_of, recorded_at, author, supersedes_id, payload_digest) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (OLD, "3105.TWO", "fiscal_year_results", payload, "年報", "2025-12-31T00:00:00+00:00",
         "2026-09-12T00:00:00+00:00", "session", None, "d"))
    conn.execute(
        "INSERT INTO financial_snapshots (ticker, snapshot_date, price, shares_outstanding, "
        "bar_date, fetched_at) VALUES (?,?,?,?,?,?)",
        ("3105.TWO", "2026-09-11", 437.5, 80_825_000, "2026-09-11", "2026-09-11T00:00:00+00:00"))
    conn.commit()
    market, _fresh = EngineCFundamentalsProvider(conn=conn).market(Ticker("3105.TWO"))
    assert market.price == 437.5
    assert market.market_cap is None                          # 不是 0，是拒答
    assert "5.25" in (market.market_cap_absence_reason or "")
    assert "至少一邊錯了" in (market.market_cap_absence_reason or "")


def test_share_count_counter_lists_the_wrong_one_and_not_the_legitimate_one() -> None:
    """常駐計數器：3105.TWO（5.25）在列上，AXTI（0.67 的合法差異）不在。"""
    from alpha.closure import SHARE_COUNT_TOLERANCE, render_share_count_mismatches, share_count_mismatches

    rows = share_count_mismatches({
        "3105.TWO": (80_825_000.0, 424_512_000.0),            # 錯 5.25 倍
        "AXTI": (48_000_000.0, 32_160_000.0),                 # 0.67——現金增資，合法
        "COHR": (155_000_000.0, 158_000_000.0),               # 1.02
        "NOBASE": (10_000_000.0, None),                       # 沒有對照物 → 不判
    })
    assert [r[0] for r in rows] == ["3105.TWO"]
    assert rows[0][3] == pytest.approx(5.25, rel=1e-3)
    assert SHARE_COUNT_TOLERANCE == (0.5, 2.0)
    text = " ".join(render_share_count_mismatches(rows))
    assert "3105.TWO" in text and "AXTI" not in text
    # 沒有命中時也要印一行——否則「沒有問題」與「沒有跑」同形（L13-2）。
    assert "0 檔" in " ".join(render_share_count_mismatches(()))


# ---------------------------------------------------------------------------
# 2026-09-13：目標年度已報導的 YTD 實績有 authority 載體了（ROADMAP L211）
# ---------------------------------------------------------------------------

def test_interim_period_results_is_readable_and_its_ref_can_be_cited() -> None:
    """YTD 實績是整個模型最硬的輸入，先前只能寫進 rationale 的散文裡。

    ⚠ 它**不進橋**（橋的基期依定義是完整的上一個年度）——讀它的唯一理由是讓它的
    evidence ref 進 index，於是假設的 `evidence_refs` 指得到它。
    """
    conn = _conn()
    payload = json.dumps({
        "period_start": "2025-09-28", "period_end": "2026-06-27", "periods_reported": 3,
        "currency": "USD", "revenue": 305_610_000_000.0,
        "gaap": {"operating_income": 98_000_000_000.0, "diluted_eps": 5.31,
                 "diluted_shares": 15_000_000_000.0},
    }, ensure_ascii=False)
    oid = "mo_" + "7" * 32
    conn.execute(
        "INSERT INTO manual_observations (observation_id, ticker, field_name, value, source_ref, "
        "as_of, recorded_at, author, supersedes_id, payload_digest) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (oid, "AAPL", "interim_period_results", payload, "10-Q accession x",
         "2026-06-27T00:00:00+00:00", "2026-08-01T00:00:00+00:00", "session", None, "d2"))
    conn.commit()
    provider = EngineCFundamentalsProvider(conn=conn)
    rows, reason = provider.interim_period_results(Ticker("AAPL"))
    assert reason is None and len(rows) == 1
    item = rows[0]
    assert item.periods_reported == 3 and item.period_end == date(2026, 6, 27)
    assert item.gaap["diluted_eps"] == pytest.approx(5.31)
    assert item.refs == (f"engine_c://manual_observation/{oid}",)
    # 沒有這個欄位的標的回空——那不是錯（多數標的的目標年度還沒報導）。
    empty, reason2 = provider.interim_period_results(Ticker("NOSUCH"))
    assert empty == () and reason2 is None


def test_interim_period_results_is_a_mechanical_field_so_it_needs_no_pq2() -> None:
    """它的每個數字都印在 10-Q／半年報的表上 → `mechanical` → 不需 pq2（判準沿用 L10）。"""
    from engine_c.observation_fields import get_observation_field_registry

    registry = get_observation_field_registry()
    assert "interim_period_results" in registry.mechanical_field_names
    # ⚠ 放行與收緊同時發生：`mechanical` 欄位的 value 被強制必須是可機械比對的 JSON 數值，
    # 而它**不得**進 gate 五項（`gate_member=false`）。
    assert "interim_period_results" not in registry.gate_field_names
