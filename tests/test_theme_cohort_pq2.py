"""主題等權組的寫入綁使用者的 go（Phase 3 Step 3.3，plan §4.2）。

「只驗有編號」證明不了使用者 go 的是這一份：spec 在鑄號時凍結進編號（含 digest），go 之後唯一的寫入入口
`complete-theme-cohort` 讀**凍結的那一份**、比對 digest 才寫；bare go 拒收（比照 ra_admission／engine_c_observation）。
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from engine_b import todo

SPEC = {"theme": "ai_capex", "reason": "同題材的邊緣供應商，等權",
        "members": [{"ticker": "AXTI", "company_id": "co:axt", "reason": "InP 基板"},
                    {"ticker": "AAOI", "company_id": "co:applied_optoelectronics", "reason": "光收發模組"},
                    {"ticker": "SIVE.ST", "company_id": "co:sivers_semiconductors", "reason": "CW DFB 雷射"}],
        "excluded": [{"name": "COHR", "reason": "非邊緣（市值遠超 10B）"}]}


def _minted():
    pool = todo.empty_pool()
    item = todo.propose_theme_cohort(pool, copy.deepcopy(SPEC), at="2026-09-30T01:00:00+00:00")
    return pool, item


def test_proposing_freezes_the_spec_and_the_same_spec_gets_the_same_number() -> None:
    pool, item = _minted()
    frozen = item[todo.FROZEN_SPEC_KEY]
    assert frozen["kind"] == "theme_cohort" and len(frozen["digest"]) == 64
    assert item["type"] == "manual" and item["ref_id"].endswith(frozen["digest"][:16])
    again = todo.propose_theme_cohort(pool, copy.deepcopy(SPEC))
    assert again["n"] == item["n"] and pool["next_n"] == item["n"] + 1
    changed = copy.deepcopy(SPEC)
    changed["reason"] = "改一個字就是另一份"
    assert todo.propose_theme_cohort(pool, changed)["n"] != item["n"]


def test_unresolvable_members_are_refused_before_a_number_is_minted() -> None:
    pool = todo.empty_pool()
    bad = copy.deepcopy(SPEC)
    bad["members"][0]["company_id"] = "co:not_axt"
    with pytest.raises(todo.TodoError, match="身分解析"):
        todo.propose_theme_cohort(pool, bad)
    assert pool["items"] == []


@pytest.mark.parametrize("receipt", ["", "authority:theme_cohort;ref:tc_fake"])
def test_bare_go_or_a_hand_written_receipt_is_refused(receipt: str) -> None:
    pool, item = _minted()
    with pytest.raises(todo.TodoError, match="complete-theme-cohort"):
        todo.resolve(pool, item["n"], "go", receipt=receipt)
    assert item["resolved_at"] is None


def test_complete_writes_exactly_the_frozen_spec_and_closes_with_a_receipt(tmp_path: Path) -> None:
    pool, item = _minted()
    result = todo.complete_theme_cohort(pool, item["n"], at="2026-09-30T02:00:00+00:00", directory=tmp_path)
    assert result["receipt"] == f"authority:theme_cohort;ref:{result['cohort_id']}"
    assert item["resolution"] == "go" and item["resolved_at"]
    # 新題材的檔名＝slug＋題材雜湊（多主題等權組 S1：「電力」「散熱」的 slug 都是 `__`，不能再靠 slug 當檔名）
    ledger = tmp_path / f"ai_capex_{hashlib.sha1('ai_capex'.encode('utf-8')).hexdigest()[:8]}.jsonl"
    lines = ledger.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["pq2_ref"] == item["n"] and record["decided_on"] == "2026-09-30"
    assert [m["ticker"] for m in record["members"]] == ["AXTI", "AAOI", "SIVE.ST"]
    with pytest.raises(todo.TodoError, match="已處理|已結案"):
        todo.complete_theme_cohort(pool, item["n"], directory=tmp_path)
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == 1


def test_a_spec_edited_after_minting_is_refused_and_nothing_is_written(tmp_path: Path) -> None:
    pool, item = _minted()
    item[todo.FROZEN_SPEC_KEY]["spec"]["members"].pop()          # 鑄號之後被改
    with pytest.raises(todo.TodoError, match="digest"):
        todo.complete_theme_cohort(pool, item["n"], directory=tmp_path)
    assert not (tmp_path / "ai_capex.jsonl").exists() and item["resolved_at"] is None


def test_dropped_missing_or_wrong_type_numbers_are_refused(tmp_path: Path) -> None:
    pool, item = _minted()
    todo.resolve(pool, item["n"], "drop", reason="不要這一組")
    with pytest.raises(todo.TodoError):
        todo.complete_theme_cohort(pool, item["n"], directory=tmp_path)
    with pytest.raises(Exception):
        todo.complete_theme_cohort(pool, 999, directory=tmp_path)
    plain = todo.upsert(pool, item_type="manual", ref_id="manual:x", title="一般 manual")
    with pytest.raises(todo.TodoError, match="沒有凍結"):
        todo.complete_theme_cohort(pool, plain["n"], directory=tmp_path)
    assert not (tmp_path / "ai_capex.jsonl").exists()


def test_a_plain_manual_item_keeps_its_old_receipt_contract() -> None:
    """凍結 spec 的守門只攔帶 spec 的項——一般 manual 的 go 照舊（L11-6 ④：現有 manual 項不得被波及）。"""
    pool = todo.empty_pool()
    plain = todo.upsert(pool, item_type="manual", ref_id="manual:y", title="一般 manual")
    todo.resolve(pool, plain["n"], "go", receipt="authority:note;ref:abc")
    assert plain["resolution"] == "go"
