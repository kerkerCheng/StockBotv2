"""`engine_b.cli triage-apply`（Phase 1 Step 1.3）：LLM 只提議，程式逐則驗證後寫入。

守的機制：寫入路徑與 CLI `triage` 同一個 `leads.triage()`；一則都不寫的三種情形（沒有結果檔、壞 JSON、
`run_id` 不符——含同日期的舊檔）；逐則拒收（批次外、重複、寫入當下已非 pending、缺欄位、PASS 缺分類、
字彙不在 CLI 範圍、no_go 帶分類）；收據帶 `decided_by`；計數正確（INV-3：拒收不得靜默）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine_b import cli, leads


def _store(tmp_path: Path, n: int = 4) -> tuple[Path, list[str]]:
    store = leads.empty_store()
    ids = []
    for i in range(n):
        lead_id, _ = leads.register(store, source="x:test", url=f"https://example.com/{i}", title=f"t{i}")
        ids.append(lead_id)
    path = tmp_path / "pending_leads.json"
    leads.save(store, path)
    return path, ids


def _write(path: Path, payload) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _go(lead_id: str, **over) -> dict:
    item = {"lead_id": lead_id, "decision": "go", "tier": 2, "reason": "有具名公司與可查核數字",
            "content_type": "structural_fact", "decision_impact": "candidate_set",
            "payment_direction": None, "priority_flags": {"contradiction": False, "novelty": True,
                                                          "independent_source": False},
            "decided_by": "claude-p:sess-1"}
    item.update(over)
    return item


def _no_go(lead_id: str, **over) -> dict:
    item = {"lead_id": lead_id, "decision": "no_go", "tier": 4, "reason": "沒有可查核內容",
            "content_type": None, "decision_impact": None, "payment_direction": None,
            "priority_flags": {"contradiction": False, "novelty": False, "independent_source": False},
            "decided_by": "claude-p:sess-1"}
    item.update(over)
    return item


def _apply(tmp_path: Path, leads_path: Path, batch_ids, items, *, run_id="r1", batch_run_id="r1",
           result_run_id="r1", result_raw: str | None = None, capsys=None):
    batch = _write(tmp_path / "batch.json", {"run_id": batch_run_id, "payload": [{"lead_id": i} for i in batch_ids]})
    result = tmp_path / "result.json"
    if result_raw is not None:
        result.write_text(result_raw, encoding="utf-8")
    elif items is not None:
        _write(result, {"run_id": result_run_id, "items": items})
    code = cli.main(["--leads", str(leads_path), "triage-apply", "--file", str(result),
                     "--batch", str(batch), "--run-id", run_id])
    out = capsys.readouterr().out if capsys else ""
    payload = json.loads(out.splitlines()[0]) if out.strip() else {}
    return code, payload, leads.load(leads_path)


def test_valid_items_are_written_through_the_same_path_with_decided_by(tmp_path, capsys) -> None:
    path, ids = _store(tmp_path)
    code, out, store = _apply(tmp_path, path, ids[:2], [_go(ids[0]), _no_go(ids[1])], capsys=capsys)
    assert code == 0
    assert out["summary"] == {"processed": 2, "pass": 1, "filter": 1, "rejected": 0, "not_answered": 0}
    go = store["leads"][ids[0]]
    assert go["status"] == "triaged_go"
    assert go["triage"]["decided_by"] == "claude-p:sess-1"
    assert go["triage"]["classification"]["content_type"] == "structural_fact"
    assert go["triage"]["priority_flags"] == {"novelty": True}
    assert store["leads"][ids[1]]["status"] == "triaged_no_go"

    # 收據形狀與 CLI `triage` 相同（差別只在可選的 decided_by）
    (tmp_path / "cli").mkdir()
    path2, ids2 = _store(tmp_path / "cli", n=1)
    assert cli.main(["--leads", str(path2), "triage", ids2[0], "--go", "--tier", "2",
                     "--reason", "有具名公司與可查核數字", "--content-type", "structural_fact",
                     "--decision-impact", "candidate_set", "--novelty"]) == 0
    manual = leads.load(path2)["leads"][ids2[0]]["triage"]
    assert set(go["triage"]) - {"decided_by"} == set(manual)


@pytest.mark.parametrize("kwargs", [
    {"run_id": "r2"},                                   # 參數與檔案不符
    {"batch_run_id": "old"},                            # 批次是舊的
    {"result_run_id": "old"},                           # 結果是同日稍早那一輪的
])
def test_run_id_mismatch_writes_nothing(tmp_path, capsys, kwargs) -> None:
    path, ids = _store(tmp_path)
    code, out, store = _apply(tmp_path, path, ids[:1], [_go(ids[0])], capsys=capsys, **kwargs)
    assert code != 0 and out["status"] == "error" and "run_id" in out["error"]
    assert store["leads"][ids[0]]["status"] == "pending"


def test_missing_result_file_writes_nothing(tmp_path, capsys) -> None:
    path, ids = _store(tmp_path)
    code, out, store = _apply(tmp_path, path, ids[:1], None, capsys=capsys)
    assert code != 0 and "沒有結果檔" in out["error"]
    assert all(lead["status"] == "pending" for lead in store["leads"].values())


def test_bad_json_writes_nothing(tmp_path, capsys) -> None:
    path, ids = _store(tmp_path)
    code, out, store = _apply(tmp_path, path, ids[:1], None, result_raw="{not json", capsys=capsys)
    assert code != 0 and out["status"] == "error"
    assert all(lead["status"] == "pending" for lead in store["leads"].values())


def test_rejections_are_itemised_and_nothing_else_is_touched(tmp_path, capsys) -> None:
    path, ids = _store(tmp_path, n=4)
    # ids[3] 在批次後、寫入前已被別人 triage（寫入當下讀 live store）
    store = leads.load(path)
    leads.triage(store, ids[3], go=False, tier=4, reason="互動 session 先處理了")
    leads.save(store, path)
    items = [
        _go("lead_not_in_batch"),                              # 批次外
        _go(ids[0]), _no_go(ids[0]),                           # 重複 → 全拒
        _go(ids[1], content_type=None),                        # PASS 缺分類
        _go(ids[2], content_type="unknown"),                   # 字彙不在 CLI 範圍（unknown 不得寫入）
        _no_go(ids[3]),                                        # 寫入當下已非 pending
    ]
    code, out, after = _apply(tmp_path, path, ids, items, capsys=capsys)
    assert code == 0
    reasons = {r["lead_id"]: r["reason"] for r in out["rejected"]}
    assert reasons["lead_not_in_batch"] == "not_in_batch"
    assert reasons[ids[0]] == "duplicate"
    assert "content-type" in reasons[ids[1]] or "content_type" in reasons[ids[1]]
    assert "unknown" in reasons[ids[2]]
    assert reasons[ids[3]].startswith("not_pending")
    assert out["summary"]["processed"] == 0 and out["summary"]["rejected"] == 6
    assert after["leads"][ids[0]]["status"] == "pending" and after["leads"][ids[1]]["status"] == "pending"


@pytest.mark.parametrize("bad", [
    {"decision": "maybe"}, {"tier": 7}, {"tier": "2"}, {"reason": "  "},
])
def test_invalid_fields_are_rejected(tmp_path, capsys, bad) -> None:
    path, ids = _store(tmp_path, n=1)
    code, out, store = _apply(tmp_path, path, ids, [_no_go(ids[0], **bad)], capsys=capsys)
    assert code == 0 and out["summary"]["rejected"] == 1
    assert store["leads"][ids[0]]["status"] == "pending"


def test_no_go_with_classification_is_rejected_like_the_cli(tmp_path, capsys) -> None:
    path, ids = _store(tmp_path, n=1)
    code, out, store = _apply(tmp_path, path, ids, [_no_go(ids[0], content_type="sentiment")], capsys=capsys)
    assert out["summary"]["rejected"] == 1 and store["leads"][ids[0]]["status"] == "pending"


def test_legacy_ranking_is_rejected_and_counted_structure_change_passes(tmp_path, capsys) -> None:
    """plan A4／R-2（2026-09-26）：triage 不再提供「誰是第一會變」——新分類寫 `ranking` 拒收並計入拒收數，
    同一批其他項照寫；`structure_change` 是它的接替。schema 的 enum 也不含它（test_daily_task 守相等）。"""
    from engine_b.cli import _cli_vocabulary

    assert "ranking" not in _cli_vocabulary()["decision_impact"]
    assert "structure_change" in _cli_vocabulary()["decision_impact"]
    path, ids = _store(tmp_path, n=2)
    items = [_go(ids[0], decision_impact="ranking"), _go(ids[1], decision_impact="structure_change")]
    code, out, store = _apply(tmp_path, path, ids, items, capsys=capsys)
    assert code == 0 and out["summary"]["rejected"] == 1 and out["summary"]["pass"] == 1
    assert "ranking" in out["rejected"][0]["reason"]
    assert store["leads"][ids[0]]["status"] == "pending"
    assert store["leads"][ids[1]]["triage"]["classification"]["decision_impact"] == "structure_change"


def test_capital_commitment_requires_payment_direction(tmp_path, capsys) -> None:
    path, ids = _store(tmp_path, n=2)
    items = [_go(ids[0], content_type="capital_commitment"),
             _go(ids[1], content_type="capital_commitment", payment_direction="customer_to_supplier")]
    code, out, store = _apply(tmp_path, path, ids, items, capsys=capsys)
    assert out["summary"]["rejected"] == 1 and out["summary"]["pass"] == 1
    assert store["leads"][ids[1]]["triage"]["classification"]["payment_direction"] == "customer_to_supplier"


def test_leads_in_the_batch_without_an_answer_are_counted(tmp_path, capsys) -> None:
    path, ids = _store(tmp_path, n=3)
    code, out, _ = _apply(tmp_path, path, ids, [_go(ids[0])], capsys=capsys)
    assert out["summary"]["not_answered"] == 2 and set(out["not_answered"]) == set(ids[1:])
