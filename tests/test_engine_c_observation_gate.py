"""Engine C 人工觀測的 pq2 門。

事發（2026-08-06）：`decision_lab` 的 gap research packet 明寫
`engine_c_manual_observation_requires_user_approval: true`，但那句話沒有任何程式
實現——`set_manual_field.py` 是唯一入口，寫下去就直接落 append-only ledger，沒有
編號、沒有核准、沒有收據鏈。對照 graph admission 的完整 gate，Engine C 這一側是
敞開的；同一天就有一筆 runway 觀測是這樣直接寫進去的。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from engine_b import todo
from engine_c import pending_observations
from engine_c.manual_observations import ensure_manual_observation_schema


@pytest.fixture
def pending_root(tmp_path, monkeypatch):
    monkeypatch.setattr(pending_observations, "PENDING_DIR", tmp_path / "pending")
    return tmp_path


def _open(path: Path) -> sqlite3.Connection:
    """完整 Engine C schema：ledger 寫入同時會更新 manual_fields projection。"""

    from engine_c.db import _ensure_sqlite_schema

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    _ensure_sqlite_schema(conn)
    ensure_manual_observation_schema(conn)
    return conn


def _propose(**overrides):
    payload = {
        "ticker": "AXTI",
        "field_name": "runway_inputs",
        "value": '{"cash_and_equivalents": 1.0, "total_debt": 0.0, "free_cash_flow_ttm": -1.0}',
        "source_ref": "fixture://filing",
        "as_of": "2026-06-30T00:00:00+00:00",
        "author": "test",
    }
    payload.update(overrides)
    return pending_observations.propose(**payload)


def test_proposal_is_content_addressed_and_idempotent(pending_root) -> None:
    first = _propose()
    second = _propose()

    assert first["proposal_id"] == second["proposal_id"]
    assert first["state"] == "pending"
    assert len(list(pending_observations.iter_pending())) == 1


def test_unregistered_field_name_is_rejected_before_minting(pending_root) -> None:
    with pytest.raises(Exception):
        _propose(field_name="not_a_registered_field")

    assert list(pending_observations.iter_pending()) == []


def test_date_only_as_of_survives_the_whole_gate(pending_root, tmp_path, monkeypatch) -> None:
    """事發（2026-08-14）：LITE 客戶集中度提案的 as_of 是財季結束日 `2026-03-28`。

    提案層當時不驗 as_of、ledger 層要求帶時區，於是提案建得成、進得了池、拿得到
    編號、使用者也核准了，卻在最後一刻寫入時炸掉——核准動作完全無法完成。驗收
    條件因此是「ledger 裡真的多一列」，不是「propose 回傳成功」。
    """

    record = _propose(as_of="2026-03-28")
    assert record["payload"]["as_of"] == "2026-03-28T00:00:00+00:00"

    db_path = tmp_path / "engine_c.db"
    monkeypatch.setattr("engine_c.db.get_conn", lambda *a, **k: _open(db_path))
    pool = todo.empty_pool()
    todo.sync(pool, todo._collect_engine_c_observation_rows())
    todo.complete_engine_c_observation(pool, 1)

    with _open(db_path) as check:
        stored = check.execute("SELECT as_of FROM manual_observations").fetchall()
    assert [row[0] for row in stored] == ["2026-03-28T00:00:00+00:00"]


def test_as_of_without_timezone_is_rejected_before_minting(pending_root) -> None:
    """帶時刻卻沒有時區的字串仍然要在發編號前就擋下，不能替它猜一個。"""

    with pytest.raises(pending_observations.ProposalError, match="as_of"):
        _propose(as_of="2026-03-28T09:30:00")

    assert list(pending_observations.iter_pending()) == []


def test_bare_go_cannot_write_the_ledger(pending_root) -> None:
    """核准動詞不能替代實際寫入——否則 pq2 會顯示已完成，ledger 卻是空的。"""

    record = _propose()
    pool = todo.empty_pool()
    todo.sync(pool, todo._collect_engine_c_observation_rows())

    with pytest.raises(todo.TodoError, match="不得 bare go"):
        todo.resolve(pool, 1, "go", receipt=f"observation:mo_{'0' * 32}")

    assert todo.get(pool, 1)["ref_id"] == record["proposal_id"]
    assert pending_observations.read(record["proposal_id"])["state"] == "pending"


def test_completion_writes_ledger_once_and_leaves_a_receipt(
    pending_root, tmp_path, monkeypatch
) -> None:
    record = _propose()
    db_path = tmp_path / "engine_c.db"
    monkeypatch.setattr("engine_c.db.get_conn", lambda *a, **k: _open(db_path))

    pool = todo.empty_pool()
    todo.sync(pool, todo._collect_engine_c_observation_rows())
    result = todo.complete_engine_c_observation(pool, 1)

    with _open(db_path) as check:
        rows = check.execute(
            "SELECT observation_id, ticker, field_name FROM manual_observations"
        ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == result["observation_id"]
    assert result["receipt"].startswith(f"observation:{result['observation_id']};proposal:")
    assert pending_observations.read(record["proposal_id"])["state"] == "applied"
    assert todo.active_items(pool) == []

    # 同一個提案不得重複落帳。
    pool2 = todo.empty_pool()
    todo.upsert(
        pool2, item_type="engine_c_observation",
        ref_id=record["proposal_id"], title="重複",
    )
    with pytest.raises(todo.TodoError, match="不可重複寫入"):
        todo.complete_engine_c_observation(pool2, 1)


def test_applied_proposal_leaves_the_pending_queue(pending_root, tmp_path, monkeypatch) -> None:
    record = _propose()
    db_path = tmp_path / "engine_c.db"
    monkeypatch.setattr("engine_c.db.get_conn", lambda *a, **k: _open(db_path))

    pool = todo.empty_pool()
    todo.sync(pool, todo._collect_engine_c_observation_rows())
    todo.complete_engine_c_observation(pool, 1)

    assert list(pending_observations.iter_pending()) == []
    # 記錄本身保留在磁碟供稽核。
    assert pending_observations.read(record["proposal_id"])["observation_id"]


def test_set_manual_field_cli_only_proposes(pending_root, capsys) -> None:
    """CLI 不得再直接寫 ledger——它是 agent 最常用的入口。"""

    source = Path("engine_c/set_manual_field.py").read_text(encoding="utf-8")

    assert "append_manual_observation" not in source
    assert "pending_observations.propose" in source
