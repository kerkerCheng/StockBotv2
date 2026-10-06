"""層說明 ledger（個股頁 plan S4a；2026-10-07）：形狀、出處指得回去、主張寫下即登記 watch、換版收掉舊條件。

守的事：①每一句有出處或標「推一步」，出處指得回 library/raw 或 lead（L18）；②每條主張都有到期（INV-2、L7）；
③換版或撤回時舊條件不留成孤兒；④到期走「重讀」、不鑄號；⑤它不 gate 任何東西（沒有任何候選、排序、尺寸的欄位）。
"""
from __future__ import annotations

import json
from datetime import date

import pytest

from alpha.errors import ContractViolation
from alpha.layer_note import (
    EVIDENCE_LEVELS, SECTION_KEYS, layer_note_record, parse_layer_note_record, select_current,
)

CO = "co:coherent"           # 名冊裡一定有的公司（語意 watch 的實體要過 registry，INV-1）


def _spec(**over):
    spec = {
        "node": "mat:inp_epiwafer", "unit": "layer", "title": "InP 磊晶片", "expires": "2027-01-31",
        "reread_reason": "Q4 財報與客戶 filing 出來時重讀供給側家數",
        "sections": {
            "physics": {"text": "磊晶決定雷射的功率與壽命；InP 上長多量子井結構，良率與均勻度是門檻。" * 2,
                        "citations": [{"evidence": "primary", "ref": "raw:doc_a"}]},
            "variants": {"text": "IDM 自己長、外包給專業磊晶廠兩條路；各家走到量產的階段不同。" * 2,
                         "citations": [{"evidence": "industry_report", "ref": "lead:lead_x1"}]},
            "selection": {"text": "客戶選磊晶廠看的是良率與長期供貨；換掉要重新認證一整輪。" * 2,
                          "citations": [{"evidence": "inference"}]},
        },
        "claims": [{
            "claim": "外包磊晶的需求會隨 CW 雷射放量而增加，IDM 自己的磊晶產能不夠",
            "condition": "任一 IDM 公告自建磊晶產能足以自給，或客戶 filing 列出外包比例下降",
            "entities": [CO], "check_frequency": "每季財報", "action_48h": "重讀磊晶層說明、改受影響的敘事那一格",
            "evidence": "primary", "citations": [{"evidence": "primary", "ref": "raw:doc_a"}],
        }],
    }
    spec.update(over)
    return spec


# ---- 契約 ----

def test_a_valid_note_round_trips_with_a_content_addressed_id() -> None:
    record = layer_note_record(_spec(), created_at="2026-10-07T00:00:00+00:00")
    note = parse_layer_note_record(record)
    assert record["note_id"].startswith("ln_") and note.note_id == record["note_id"]
    assert set(note.sections) == set(SECTION_KEYS) and len(note.claims) == 1
    assert note.current_claim_refs == (f"layer_note:{note.note_id}#1",)
    # 它不 gate 任何東西：沒有候選、排序、尺寸的欄位
    assert not {"candidate_state", "rank", "score", "size", "weight"} & set(record)


def test_the_id_detects_tampering() -> None:
    record = layer_note_record(_spec(), created_at="2026-10-07T00:00:00+00:00")
    record["title"] = "改過的標題"
    with pytest.raises(ContractViolation, match="note_id 對不上"):
        parse_layer_note_record(record)


@pytest.mark.parametrize("mutate, message", [
    (lambda s: s["sections"].pop("selection"), "缺段"),
    (lambda s: s["sections"].__setitem__("bogus", {"text": "x" * 50, "citations": [{"evidence": "inference"}]}), "段鍵未登記"),
    (lambda s: s["sections"]["physics"]["citations"].__setitem__(0, {"evidence": "blog"}), "evidence 未登記"),
    (lambda s: s["sections"]["physics"]["citations"].__setitem__(0, {"evidence": "primary"}), "必須附出處"),
    (lambda s: s["sections"]["physics"]["citations"].__setitem__(0, {"evidence": "primary", "ref": "https://x.com/a"}),
     "只認"),
    (lambda s: s["claims"][0].pop("action_48h"), "L7"),
    (lambda s: s["claims"][0].__setitem__("entities", ["COHR"]), "co:"),
    (lambda s: s.__setitem__("expires", None), "到期"),
    (lambda s: s.__setitem__("node", "InP 磊晶"), "形狀"),
    (lambda s: s.__setitem__("unit", "socket"), "unit 未登記"),
])
def test_shape_violations_are_rejected(mutate, message) -> None:
    spec = json.loads(json.dumps(_spec()))
    mutate(spec)
    with pytest.raises(ContractViolation, match=message):
        layer_note_record(spec, created_at="2026-10-07T00:00:00+00:00")


def test_inference_may_stand_without_a_reference_but_must_be_labelled() -> None:
    assert "inference" in EVIDENCE_LEVELS and "none" in EVIDENCE_LEVELS
    record = layer_note_record(_spec(), created_at="2026-10-07T00:00:00+00:00")
    assert record["sections"]["selection"]["citations"] == [{"evidence": "inference"}]


def test_select_current_skips_superseded_and_retracted() -> None:
    first = parse_layer_note_record(layer_note_record(_spec(), created_at="2026-10-01T00:00:00+00:00"))
    second = parse_layer_note_record(layer_note_record(_spec(title="InP 磊晶片 v2", supersedes_id=first.note_id),
                                                       created_at="2026-10-05T00:00:00+00:00"))
    assert select_current([first, second]).note_id == second.note_id
    retract = parse_layer_note_record(layer_note_record(
        {"node": "mat:inp_epiwafer", "unit": "layer", "retracted": True, "supersedes_id": second.note_id,
         "sections": {}, "claims": []}, created_at="2026-10-06T00:00:00+00:00"))
    assert select_current([first, second, retract]) is None


# ---- 寫入端：出處指得回去 ----

def _write_env(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "doc_a.txt").write_text("source text", encoding="utf-8")
    ledger = tmp_path / "ledger"
    return raw, ledger


def test_append_rejects_references_that_do_not_resolve(tmp_path) -> None:
    from alpha.providers.layer_notes import append_note_record

    raw, ledger = _write_env(tmp_path)
    spec = _spec()
    spec["sections"]["physics"]["citations"] = [{"evidence": "primary", "ref": "raw:doc_missing"}]
    record = layer_note_record(spec, created_at="2026-10-07T00:00:00+00:00")
    with pytest.raises(ContractViolation) as exc:
        append_note_record(record, directory=ledger, raw_dir=raw, lead_exists=lambda _id: False)
    text = str(exc.value)
    assert "raw:doc_missing" in text and "lead:lead_x1" in text      # 兩個都逐條說出來
    assert not (ledger / "mat_inp_epiwafer.jsonl").exists()


def test_append_accepts_resolvable_references_and_refuses_duplicates(tmp_path) -> None:
    from alpha.providers.layer_notes import append_note_record, read_note_records

    raw, ledger = _write_env(tmp_path)
    record = layer_note_record(_spec(), created_at="2026-10-07T00:00:00+00:00")
    append_note_record(record, directory=ledger, raw_dir=raw, lead_exists=lambda i: i == "lead_x1")
    records, errors = read_note_records("mat:inp_epiwafer", directory=ledger)
    assert [r.note_id for r in records] == [record["note_id"]] and errors == []
    with pytest.raises(ContractViolation, match="重複"):
        append_note_record(record, directory=ledger, raw_dir=raw, lead_exists=lambda i: True)
    orphan = layer_note_record(_spec(supersedes_id="ln_0000000000000000"), created_at="2026-10-08T00:00:00+00:00")
    with pytest.raises(ContractViolation, match="supersedes_id"):
        append_note_record(orphan, directory=ledger, raw_dir=raw, lead_exists=lambda i: True)


# ---- watch：寫下即登記、換版收掉、到期走重讀 ----

def _ew_paths(tmp_path, monkeypatch):
    from engine_b import event_watch as ew

    watches = tmp_path / "event_watches.json"
    monkeypatch.setattr(ew, "_today", lambda: date(2026, 10, 7))
    return ew, watches


def test_claims_register_as_semantic_watches_and_a_new_version_consumes_the_old(tmp_path, monkeypatch) -> None:
    from alpha.providers.layer_notes import append_note_record, register_note_watches

    ew, watches = _ew_paths(tmp_path, monkeypatch)
    raw, ledger = _write_env(tmp_path)
    v1 = layer_note_record(_spec(), created_at="2026-10-07T00:00:00+00:00")
    append_note_record(v1, directory=ledger, raw_dir=raw, lead_exists=lambda i: True)
    first = register_note_watches(v1, watches_path=watches, directory=ledger)
    assert len(first["registered"]) == 1
    data = ew.load_watches(watches)
    w = data["watches"][0]
    assert w["source_ref"] == f"layer_note:{v1['note_id']}#1" and w["node"] == "mat:inp_epiwafer"
    assert w["expires"] == "2027-01-31" and w["status"] == "active"
    assert ew.expiry_class(w) == "reread"                  # 到期走重讀、不鑄號
    # 冪等
    assert register_note_watches(v1, watches_path=watches, directory=ledger)["registered"] == []
    # 換版：舊條件收掉、新條件登記
    v2 = layer_note_record(_spec(title="InP 磊晶片 v2", supersedes_id=v1["note_id"]), created_at="2026-10-09T00:00:00+00:00")
    append_note_record(v2, directory=ledger, raw_dir=raw, lead_exists=lambda i: True)
    second = register_note_watches(v2, watches_path=watches, directory=ledger)
    assert second["consumed"] == [w["watch_id"]] and len(second["registered"]) == 1
    statuses = {x["source_ref"]: x["status"] for x in ew.load_watches(watches)["watches"]}
    assert statuses[f"layer_note:{v1['note_id']}#1"] == "consumed"
    assert statuses[f"layer_note:{v2['note_id']}#1"] == "active"


def test_retracting_consumes_its_conditions(tmp_path, monkeypatch) -> None:
    from alpha.providers.layer_notes import append_note_record, register_note_watches

    ew, watches = _ew_paths(tmp_path, monkeypatch)
    raw, ledger = _write_env(tmp_path)
    v1 = layer_note_record(_spec(), created_at="2026-10-07T00:00:00+00:00")
    append_note_record(v1, directory=ledger, raw_dir=raw, lead_exists=lambda i: True)
    register_note_watches(v1, watches_path=watches, directory=ledger)
    retract = layer_note_record({"node": "mat:inp_epiwafer", "unit": "layer", "retracted": True,
                                 "supersedes_id": v1["note_id"], "sections": {}, "claims": []},
                                created_at="2026-10-08T00:00:00+00:00")
    append_note_record(retract, directory=ledger, raw_dir=raw, lead_exists=lambda i: True)
    out = register_note_watches(retract, watches_path=watches, directory=ledger)
    assert len(out["consumed"]) == 1 and out["registered"] == []


def test_a_layer_note_watch_must_name_its_node(monkeypatch) -> None:
    from engine_b import event_watch as ew

    monkeypatch.setattr(ew, "_today", lambda: date(2026, 10, 7))
    data = {"watches": []}
    with pytest.raises(ew.EventWatchError, match="node"):
        ew.add_watch(data, kind=ew.SEMANTIC_KIND, disproof_ref="layer_note:ln_1#1", source_ref="layer_note:ln_1#1",
                     expires="2027-01-31", entities=[CO], condition="任一 IDM 公告自建磊晶產能足以自給、不再外包磊晶",
                     check_frequency="每季", action_48h="重讀")


def test_source_is_current_follows_the_current_layer_note() -> None:
    from engine_b.disproof import source_is_current

    current = parse_layer_note_record(layer_note_record(_spec(), created_at="2026-10-07T00:00:00+00:00"))
    notes = {"mat:inp_epiwafer": current}
    assert source_is_current({"source_ref": f"layer_note:{current.note_id}#1"}, layer_notes=notes)
    assert not source_is_current({"source_ref": "layer_note:ln_0000000000000000#1"}, layer_notes=notes)


def test_a_narrative_disproof_may_link_to_a_layer_claim() -> None:
    from alpha.narrative.contracts import LINKABLE_SOURCE_PREFIXES

    assert "layer_note:" in LINKABLE_SOURCE_PREFIXES


def test_layer_claims_count_in_the_disproof_counter_instead_of_vanishing(tmp_path) -> None:
    """心跳段 2 的反證計數：不放進「預期」的 watch 會被整類跳過（INV-3）——層說明的主張要被數到。"""
    from engine_b import disproof

    note = parse_layer_note_record(layer_note_record(_spec(), created_at="2026-10-07T00:00:00+00:00"))
    watch = {"kind": "semantic_condition", "status": "active", "source_ref": f"layer_note:{note.note_id}#1",
             "condition": note.claims[0].condition, "expires": "2027-01-31"}
    without = disproof.disproof_counts([watch], lifecycle={}, readings={}, briefs=(), root=tmp_path)
    with_notes = disproof.disproof_counts([watch], lifecycle={}, readings={}, briefs=(), root=tmp_path,
                                          layer_notes={note.node: note})
    assert without["watching"] == 0 and without["expected"] == 0           # 沒傳＝沒算（不讀真 ledger）
    assert with_notes["expected"] == 1 and with_notes["watching"] == 1 and with_notes["unwatched"] == 0


def test_audit_resolves_layer_claim_watches_instead_of_skipping_them(monkeypatch) -> None:
    """audit 的語意來源檢查：layer_note 的 watch 要被解析（原本 if/elif 沒有這一支，會整類跳過——INV-3）。"""
    from audit import checks, sources

    v1 = parse_layer_note_record(layer_note_record(_spec(), created_at="2026-10-01T00:00:00+00:00"))
    v2 = parse_layer_note_record(layer_note_record(_spec(title="InP 磊晶片 v2", supersedes_id=v1.note_id),
                                                   created_at="2026-10-05T00:00:00+00:00"))
    monkeypatch.setattr(sources, "thesis_lifecycle", lambda: {})
    monkeypatch.setattr(sources, "reading_ledgers", lambda: {})
    monkeypatch.setattr(sources, "brief_ledgers", lambda: {})
    monkeypatch.setattr(sources, "layer_note_ledgers",
                        lambda: {v1.node: {"records": [v1, v2], "errors": [], "current": v2}})

    def watch(note, n=1, condition=None, status="active"):
        ref = f"layer_note:{note.note_id}#{n}"
        return {"watch_id": f"ew_{note.note_id[-4:]}_{n}", "kind": "semantic_condition", "status": status,
                "source_ref": ref, "disproof_ref": ref, "node": note.node, "expires": "2027-01-31",
                "condition": condition or note.claims[0].condition, "entities": [CO]}

    findings, _soft, examined = checks._semantic_source_orphans([watch(v2)])
    assert examined == 1 and findings == []
    findings, _soft, _ = checks._semantic_source_orphans([watch(v1)])          # 舊版還在等＝換版後沒收
    assert any("不是" in f and "現行層說明" in f for f in findings)
    findings, _soft, _ = checks._semantic_source_orphans([watch(v2, n=2)])     # 第 2 條不存在
    assert any("claims[] 對不到" in f for f in findings)
    ghost = dict(watch(v2), source_ref="layer_note:ln_ffffffffffffffff#1", disproof_ref="layer_note:ln_ffffffffffffffff#1")
    findings, _soft, _ = checks._semantic_source_orphans([ghost])
    assert any("ledger 裡沒有這一份" in f for f in findings)


def test_a_touched_or_expired_layer_claim_puts_its_node_on_the_reread_list() -> None:
    """INV-4：主張觸及或到期之後要有消費端——同一個節點的重讀理由列出它（讀圖頁、心跳「該重讀」都讀這一份）。"""
    from alpha.providers.structure_readings import reread_reasons

    base = {"kind": "semantic_condition", "node": "mat:inp_epiwafer", "source_ref": "layer_note:ln_a#1",
            "condition": "任一 IDM 公告自建磊晶產能足以自給、不再外包磊晶"}
    touched = dict(base, status="fired", judgment={"touches": "yes"})
    expired = dict(base, status="expired")
    handled = dict(base, status="fired", judgment={"touches": "yes", "handled": {"verb": "reread"}})
    other_node = dict(base, node="tech:x", status="expired")
    reasons = reread_reasons("mat:inp_epiwafer", [touched, expired, handled, other_node])
    assert len(reasons) == 2 and all(r.startswith("層說明主張") for r in reasons)


def test_claim_rows_print_unwatched_instead_of_disappearing() -> None:
    from alpha.providers.layer_notes import claim_watch_rows

    note = parse_layer_note_record(layer_note_record(_spec(), created_at="2026-10-07T00:00:00+00:00"))
    assert claim_watch_rows(note, [])[0]["status"] == "未盯"
