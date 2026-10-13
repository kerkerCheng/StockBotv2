"""層代表公司宣告 ledger（個股頁 S3c；使用者 2026-10-09 ②A：研究替每一層宣告代表公司，不入圖）。

守：形狀封閉（未知鍵、口徑字彙、分部名稱逐字、why 長度、出處必附、同一份不重複、不收公司與轉換節點）；id 綁內容；
as-of 選法（INV-6：那天以後寫的看不到、撤回不讓舊版復活）；寫入端（名冊、出處指得回去、取代鏈不分岔、
**同一家同口徑只能代表一層**——只比現行，舊版拿掉後就收）；寫宣告不碰層說明 ledger。"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from alpha.errors import ContractViolation
from alpha.layer_rep import layer_reps_record, parse_layer_reps_record, select_current
from alpha.providers.layer_reps import current_declarations, read_records, write_declaration

T0 = datetime(2026, 10, 9, 1, 0, tzinfo=timezone.utc)
CITE = {"evidence": "primary", "ref": "raw:doc_a", "quote": "載板部門 82.11%"}
REP = {"company_id": "co:kinsus", "scope": "whole_company", "why": "載板部門占營收八成以上，全公司營收大致就是這一層",
       "citations": [CITE]}


def _spec(node="mat:ic_package_substrate", reps=None, **kw):
    return {"node": node, "expires": "2027-04-30", "reread_reason": "年報出來重看占比",
            "representatives": reps if reps is not None else [REP], **kw}


class _Registry:
    def __init__(self, known):
        self.known = set(known)

    def has_company(self, company_id):
        return company_id in self.known


REG = _Registry({"co:kinsus", "co:ats", "co:axt"})


def _raw(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    raw.mkdir(exist_ok=True)
    (raw / "doc_a.txt").write_text("x", encoding="utf-8")
    return raw


@pytest.mark.parametrize("change, message", [
    ({"extra": 1}, "未登記的欄位"),
    ({"representatives": [{**REP, "scope": "product_line"}]}, "scope 未登記"),
    ({"representatives": [{**REP, "scope": "segment"}]}, "必須寫 segment"),
    ({"representatives": [{**REP, "scope": "segment", "segment": "Microelectronics"}]}, "沒有逐字出現"),
    ({"representatives": [{**REP, "segment": "載板部門"}]}, "不得帶 segment"),
    ({"representatives": [{**REP, "why": "太短"}]}, "why 至少"),
    ({"representatives": [{**REP, "citations": []}]}, "至少要有一個出處"),
    ({"representatives": [{**REP, "company_id": "3189.TW"}]}, "必須是 co:"),
    ({"representatives": [REP, REP]}, "只能出現一次"),
    ({"representatives": []}, "至少宣告一家"),
    ({"node": "co:nvidia"}, "公司節點"),
    ({"node": "transition:pluggable_to_cpo"}, "公司節點"),
    ({"expires": "2026-10-01"}, "必須晚於寫入日"),
    ({"reread_reason": ""}, "reread_reason"),
    ({"representatives": [{**REP, "citations": [{"evidence": "primary", "quote": "x"}]}]}, "必須附出處"),
])
def test_the_shape_is_closed(change, message) -> None:
    with pytest.raises(ContractViolation, match=message):
        layer_reps_record({**_spec(), **change}, created_at=T0)


def test_a_segment_needs_its_name_verbatim_in_a_cited_quote_and_ids_bind_content() -> None:
    seg = {"company_id": "co:ats", "scope": "segment", "segment": "Microelectronics",
           "why": "分部定義就是 IC 載板，是這一層最純的口徑", "citations": [{**CITE, "quote": "The Microelectronics segment"}]}
    record = layer_reps_record(_spec(reps=[seg]), created_at=T0)
    assert parse_layer_reps_record(record).representatives[0].segment == "Microelectronics"
    tampered = json.loads(json.dumps(record))
    tampered["representatives"][0]["why"] = "改過的理由也要夠長才會走到 id 檢查這一步"
    with pytest.raises(ContractViolation, match="rep_id 對不上"):
        parse_layer_reps_record(tampered)
    with pytest.raises(ContractViolation, match="未登記的欄位"):
        layer_reps_record({**_spec(), "created_at": "2020-01-01T00:00:00+00:00"}, created_at=T0)   # 寫入時間不能回填


def test_as_of_sees_only_what_was_written_by_then_and_a_retraction_does_not_revive_the_old_one(tmp_path) -> None:
    d, raw = tmp_path / "ledger", _raw(tmp_path)
    first = layer_reps_record(_spec(), created_at=T0)
    write_declaration(first, directory=d, raw_dir=raw, registry=REG)
    records, _ = read_records("mat:ic_package_substrate", directory=d)
    assert select_current(records, as_of=date(2026, 10, 8)) is None
    assert select_current(records, as_of=date(2026, 10, 9)).rep_id == first["rep_id"]
    current, book = current_declarations(as_of=date(2026, 10, 8), directory=d)
    assert current == {} and book["declared_later"] == {"mat:ic_package_substrate": "2026-10-09"}
    retract = layer_reps_record({"node": "mat:ic_package_substrate", "retracted": True, "supersedes_id": first["rep_id"],
                                 "representatives": []}, created_at=datetime(2026, 10, 10, tzinfo=timezone.utc))
    write_declaration(retract, directory=d, raw_dir=raw, registry=REG)
    records, _ = read_records("mat:ic_package_substrate", directory=d)
    assert select_current(records) is None
    current, book = current_declarations(directory=d)
    assert current == {} and "mat:ic_package_substrate" in book["retracted"]


def test_the_write_side_checks_registry_refs_chain_and_duplicates(tmp_path) -> None:
    d, raw = tmp_path / "ledger", _raw(tmp_path)
    with pytest.raises(ContractViolation, match="不在名冊"):
        write_declaration(layer_reps_record(_spec(reps=[{**REP, "company_id": "co:nobody"}]), created_at=T0),
                          directory=d, raw_dir=raw, registry=REG)
    with pytest.raises(ContractViolation, match="找不到"):
        write_declaration(layer_reps_record(_spec(reps=[{**REP, "citations": [{**CITE, "ref": "raw:missing_doc"}]}]),
                                            created_at=T0), directory=d, raw_dir=raw, registry=REG)
    first = layer_reps_record(_spec(), created_at=T0)
    write_declaration(first, directory=d, raw_dir=raw, registry=REG)
    with pytest.raises(ContractViolation, match="已在 ledger"):
        write_declaration(first, directory=d, raw_dir=raw, registry=REG)
    later = datetime(2026, 10, 11, tzinfo=timezone.utc)
    with pytest.raises(ContractViolation, match="換版要寫 supersedes_id"):
        write_declaration(layer_reps_record(_spec(), created_at=later), directory=d, raw_dir=raw, registry=REG)
    second = layer_reps_record(_spec(supersedes_id=first["rep_id"]), created_at=later)
    write_declaration(second, directory=d, raw_dir=raw, registry=REG)
    with pytest.raises(ContractViolation, match="不是 mat:ic_package_substrate 最新的一筆"):
        write_declaration(layer_reps_record(_spec(supersedes_id=first["rep_id"]),
                                            created_at=datetime(2026, 10, 12, tzinfo=timezone.utc)),
                          directory=d, raw_dir=raw, registry=REG)


def test_one_company_with_the_same_scope_represents_one_layer_only_counting_current_declarations(tmp_path) -> None:
    """同一份營收算進兩層的年增，兩層看起來都在長、其實是同一個數——寫入端擋；舊版拿掉那一家之後就收。"""
    d, raw = tmp_path / "ledger", _raw(tmp_path)
    a = layer_reps_record(_spec(), created_at=T0)
    write_declaration(a, directory=d, raw_dir=raw, registry=REG)
    with pytest.raises(ContractViolation, match="已經代表 mat:ic_package_substrate"):
        write_declaration(layer_reps_record(_spec(node="mat:ic_substrate_glass_cloth"), created_at=T0),
                          directory=d, raw_dir=raw, registry=REG)
    # 分部口徑是另一份營收：同一家的分部可以代表別層
    seg = {**REP, "scope": "segment", "segment": "載板部門", "citations": [CITE]}
    write_declaration(layer_reps_record(_spec(node="mat:ic_substrate_glass_cloth", reps=[seg]), created_at=T0),
                      directory=d, raw_dir=raw, registry=REG)
    moved = layer_reps_record(_spec(reps=[{**REP, "company_id": "co:axt"}], supersedes_id=a["rep_id"]),
                              created_at=datetime(2026, 10, 10, tzinfo=timezone.utc))
    write_declaration(moved, directory=d, raw_dir=raw, registry=REG)
    write_declaration(layer_reps_record(_spec(node="tech:eml"), created_at=datetime(2026, 10, 11, tzinfo=timezone.utc)),
                      directory=d, raw_dir=raw, registry=REG)


def test_declaring_representatives_does_not_touch_the_layer_note_ledger(tmp_path, monkeypatch) -> None:
    import alpha.providers.layer_notes as ln

    sentinel = tmp_path / "layer_notes"
    sentinel.mkdir()
    (sentinel / "mat_ic_package_substrate.jsonl").write_text('{"keep": 1}\n', encoding="utf-8")
    monkeypatch.setattr(ln, "LAYER_NOTE_DIR", sentinel)
    write_declaration(layer_reps_record(_spec(), created_at=T0), directory=tmp_path / "reps", raw_dir=_raw(tmp_path),
                      registry=REG)
    assert (sentinel / "mat_ic_package_substrate.jsonl").read_text(encoding="utf-8") == '{"keep": 1}\n'


def test_the_heartbeat_line_prints_even_when_nothing_is_declared(tmp_path, monkeypatch) -> None:
    """常駐計數器（L14）：0 份、0 份過重看日也印；過重看日的節點逐一列名。"""
    from datetime import datetime as dt

    import alpha.providers.layer_reps as lr
    from crons.heartbeat import _layer_rep_line

    monkeypatch.setattr(lr, "LAYER_REPS_DIR", tmp_path / "empty")
    assert _layer_rep_line(now=dt(2026, 10, 9, tzinfo=timezone.utc)) == "層代表公司宣告 0 份｜**過重看日 0**"
    monkeypatch.setattr(lr, "LAYER_REPS_DIR", tmp_path / "ledger")
    write_declaration(layer_reps_record(_spec(), created_at=T0), raw_dir=_raw(tmp_path), registry=REG)
    line = _layer_rep_line(now=dt(2027, 6, 1, tzinfo=timezone.utc))
    assert "1 份" in line and "過重看日 1" in line and "mat:ic_package_substrate" in line
