"""層說明 ledger（個股頁 plan S4a；2026-10-07）：形狀、出處指得回去、主張寫下即登記 watch、換版收掉舊條件。

守的事：①每一句有出處或標「推一步」，出處指得回 library/raw 或 lead（L18）；②每條主張與整份都有到期，到期有去處（INV-2、INV-4）；
③換版或撤回時舊條件不留成孤兒、舊版不復活（R2 F3）；④寫入失敗不留半筆（R2 C1）；⑤它不 gate 任何東西。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pytest

from alpha.errors import ContractViolation
from alpha.layer_note import (
    EVIDENCE_LEVELS, SECTION_KEYS, layer_note_record, parse_layer_note_record, select_current,
)

CO = "co:coherent"           # 名冊裡一定有的公司（語意 watch 的實體要過 registry，INV-1）
COND = "任一 IDM 公告自建磊晶產能足以自給，或客戶 filing 列出外包比例下降"


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
            "condition": COND,
            "entities": [CO], "check_frequency": "每季財報", "action_48h": "重讀磊晶層說明、改受影響的敘事那一格",
            "evidence": "primary", "citations": [{"evidence": "primary", "ref": "raw:doc_a"}],
        }],
    }
    spec.update(over)
    return spec


def _rec(spec=None, at="2026-10-07T00:00:00+00:00"):
    return layer_note_record(spec or _spec(), created_at=at)


# ---- 契約 ----

def test_a_valid_note_round_trips_with_a_content_addressed_id() -> None:
    record = _rec()
    note = parse_layer_note_record(record)
    assert record["note_id"].startswith("ln_") and note.note_id == record["note_id"]
    assert set(note.sections) == set(SECTION_KEYS) and len(note.claims) == 1
    assert note.current_claim_refs == (f"layer_note:{note.note_id}#1",)
    assert note.created_at.tzinfo is not None and record["created_at"].endswith("+00:00")
    # 它不 gate 任何東西：沒有候選、排序、尺寸的欄位
    assert not {"candidate_state", "rank", "score", "size", "weight"} & set(record)


def test_sections_come_back_in_their_fixed_order_after_a_sorted_round_trip() -> None:
    """ledger 以 sort_keys 落地（physics、selection、variants）；讀回來要照 ①②③，不照存檔順序。"""
    stored = json.loads(json.dumps(_rec(), sort_keys=True))
    assert list(stored["sections"]) == sorted(SECTION_KEYS)
    assert list(parse_layer_note_record(stored).sections) == list(SECTION_KEYS)


def test_the_id_detects_tampering() -> None:
    record = _rec()
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
    (lambda s: s.__setitem__("expires", "2026-10-01"), "晚於寫入日"),
    (lambda s: s.__setitem__("node", "InP 磊晶"), "形狀"),
    (lambda s: s.__setitem__("unit", "socket"), "unit 未登記"),
    (lambda s: s.__setitem__("unit", "transition"), "transition"),             # 轉換要用 transition: 前綴
    (lambda s: s["sections"]["physics"]["citations"][0].__setitem__("page", 3), "未登記的欄位"),
    (lambda s: s["claims"][0].__setitem__("severity", "high"), "未登記的欄位"),
    (lambda s: s.__setitem__("ranking", 1), "未登記的欄位"),
    (lambda s: s.__setitem__("body_ref", "library/private/research_notes/../../config/x.md"), "body_ref"),
])
def test_shape_violations_are_rejected(mutate, message) -> None:
    spec = json.loads(json.dumps(_spec()))
    mutate(spec)
    with pytest.raises(ContractViolation, match=message):
        _rec(spec)


def test_a_transition_needs_its_own_prefix() -> None:
    record = _rec(_spec(node="transition:pluggable_to_cpo", unit="transition"))
    assert parse_layer_note_record(record).unit == "transition"


def test_created_at_must_carry_a_timezone_and_is_compared_as_time() -> None:
    with pytest.raises(ContractViolation, match="時區"):
        _rec(at="2026-10-07T08:00:00")
    with pytest.raises(ContractViolation, match="ISO"):
        _rec(at="not-a-date")
    # +08:00 的 09:00 早於 UTC 的 02:00——字串比大小會排錯（R2 F5）
    early = parse_layer_note_record(_rec(at="2026-10-07T09:00:00+08:00"))
    late = parse_layer_note_record(_rec(_spec(title="InP 磊晶片 v2"), at="2026-10-07T02:00:00+00:00"))
    assert select_current([late, early]).note_id == late.note_id


def test_inference_may_stand_without_a_reference_but_must_be_labelled() -> None:
    assert "inference" in EVIDENCE_LEVELS and "none" in EVIDENCE_LEVELS
    assert _rec()["sections"]["selection"]["citations"] == [{"evidence": "inference"}]


def test_select_current_is_the_latest_and_a_retraction_revives_nothing() -> None:
    first = parse_layer_note_record(_rec(at="2026-10-01T00:00:00+00:00"))
    second = parse_layer_note_record(_rec(_spec(title="InP 磊晶片 v2", supersedes_id=first.note_id),
                                          at="2026-10-05T00:00:00+00:00"))
    assert select_current([first, second]).note_id == second.note_id
    retract = parse_layer_note_record(layer_note_record(
        {"node": "mat:inp_epiwafer", "unit": "layer", "retracted": True, "supersedes_id": second.note_id,
         "sections": {}, "claims": []}, created_at="2026-10-06T00:00:00+00:00"))
    # 撤回 v2 不讓 v1「復活」——v1 的條件早在換版時收掉了（R2 F3）
    assert select_current([first, second, retract]) is None


# ---- 寫入端：出處指得回去、預演在 append 之前 ----

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
    with pytest.raises(ContractViolation) as exc:
        append_note_record(_rec(spec), directory=ledger, raw_dir=raw, lead_exists=lambda _id: False)
    text = str(exc.value)
    assert "raw:doc_missing" in text and "lead:lead_x1" in text      # 兩個都逐條說出來
    assert not (ledger / "mat_inp_epiwafer.jsonl").exists()


def test_append_refuses_duplicates_orphans_and_twin_conditions(tmp_path) -> None:
    from alpha.providers.layer_notes import append_note_record, read_note_records

    raw, ledger = _write_env(tmp_path)
    record = _rec()
    append_note_record(record, directory=ledger, raw_dir=raw, lead_exists=lambda i: i == "lead_x1")
    records, errors = read_note_records("mat:inp_epiwafer", directory=ledger)
    assert [r.note_id for r in records] == [record["note_id"]] and errors == []
    with pytest.raises(ContractViolation, match="重複"):
        append_note_record(record, directory=ledger, raw_dir=raw, lead_exists=lambda i: True)
    with pytest.raises(ContractViolation, match="supersedes_id"):
        append_note_record(_rec(_spec(supersedes_id="ln_0000000000000000"), at="2026-10-08T00:00:00+00:00"),
                           directory=ledger, raw_dir=raw, lead_exists=lambda i: True)
    twin = _spec()
    twin["claims"] = twin["claims"] * 2
    with pytest.raises(ContractViolation, match="相同"):
        append_note_record(_rec(twin, at="2026-10-09T00:00:00+00:00"), directory=ledger, raw_dir=raw,
                           lead_exists=lambda i: True)


def _ew(monkeypatch):
    from engine_b import event_watch as ew

    monkeypatch.setattr(ew, "_today", lambda *a, **k: date(2026, 10, 7))
    return ew


def test_a_failed_watch_rehearsal_leaves_the_ledger_untouched(tmp_path, monkeypatch) -> None:
    """R2 C1：實體不在名冊——預演就拒收，ledger 一行都沒寫（否則重跑會被「已在 ledger 中」擋掉）。"""
    from alpha.providers.layer_notes import ledger_path, write_note

    ew = _ew(monkeypatch)
    raw, ledger = _write_env(tmp_path)
    watches = tmp_path / "w.json"
    spec = _spec()
    spec["claims"][0]["entities"] = ["co:zz_not_in_registry"]
    with pytest.raises(ContractViolation, match="預演失敗，ledger 未動"):
        write_note(_rec(spec), watches_path=watches, directory=ledger, raw_dir=raw, lead_exists=lambda i: True)
    assert not ledger_path("mat:inp_epiwafer", directory=ledger).exists()
    assert ew.load_watches(watches)["watches"] == []


def test_a_new_version_supersedes_the_latest_note_not_an_older_one(tmp_path) -> None:
    """2026-10-08 failure log #56（讀圖那一側的對稱面）：換版只取代最新那一筆；取代更舊的一版拒收、說出最新是哪一筆。"""
    from alpha.providers.layer_notes import append_note_record, read_note_records

    raw, ledger = _write_env(tmp_path)
    v1 = _rec()
    append_note_record(v1, directory=ledger, raw_dir=raw, lead_exists=lambda i: True)
    v2 = _rec(_spec(title="InP 磊晶片 v2", supersedes_id=v1["note_id"]), at="2026-10-09T00:00:00+00:00")
    append_note_record(v2, directory=ledger, raw_dir=raw, lead_exists=lambda i: True)
    stale = _rec(_spec(title="InP 磊晶片 v3", supersedes_id=v1["note_id"]), at="2026-10-10T00:00:00+00:00")
    with pytest.raises(ContractViolation, match=v2["note_id"]):
        append_note_record(stale, directory=ledger, raw_dir=raw, lead_exists=lambda i: True)
    append_note_record(_rec(_spec(title="InP 磊晶片 v3", supersedes_id=v2["note_id"]), at="2026-10-10T00:00:00+00:00"),
                       directory=ledger, raw_dir=raw, lead_exists=lambda i: True)
    records, _errors = read_note_records("mat:inp_epiwafer", directory=ledger)
    assert len(records) == 3, "被拒收的那一筆沒有寫進 ledger"


def test_a_registration_failure_after_append_names_the_repair_command(tmp_path, monkeypatch) -> None:
    """R2 複審：append 之後才失敗（例如 registry 存不進去）——紀錄已在 ledger，錯誤要說出冪等補登的命令，
    而且是 CLI 接得住的 AlphaError，不是 traceback。"""
    from alpha.errors import AlphaError
    from alpha.providers.layer_notes import read_note_records, write_note

    ew = _ew(monkeypatch)
    raw, ledger = _write_env(tmp_path)

    def _disk_full(*_a, **_k):
        raise OSError("disk full")

    monkeypatch.setattr(ew, "save_watches", _disk_full)
    record = _rec()
    with pytest.raises(AlphaError, match="--register-watches") as exc:
        write_note(record, watches_path=tmp_path / "w.json", directory=ledger, raw_dir=raw, lead_exists=lambda i: True)
    assert record["note_id"] in str(exc.value) and "已寫入" in str(exc.value)
    assert [r.note_id for r in read_note_records("mat:inp_epiwafer", directory=ledger)[0]] == [record["note_id"]]


# ---- watch：寫下即登記、換版收掉、到期走重讀 ----

def _write(record, tmp_path, watches):
    from alpha.providers.layer_notes import write_note

    raw = tmp_path / "raw"
    if not raw.exists():
        raw.mkdir()
        (raw / "doc_a.txt").write_text("source text", encoding="utf-8")
    return write_note(record, watches_path=watches, directory=tmp_path / "ledger", raw_dir=raw,
                      lead_exists=lambda i: True)


def test_claims_register_as_semantic_watches_and_a_new_version_consumes_the_old(tmp_path, monkeypatch) -> None:
    ew = _ew(monkeypatch)
    watches = tmp_path / "w.json"
    v1 = _rec()
    first = _write(v1, tmp_path, watches)
    assert len(first["registered"]) == 1
    w = ew.load_watches(watches)["watches"][0]
    assert w["source_ref"] == f"layer_note:{v1['note_id']}#1" and w["node"] == "mat:inp_epiwafer"
    assert w["expires"] == "2027-01-31" and w["status"] == "active"
    assert ew.expiry_class(w) == "reread"                  # 到期走重讀、不鑄號
    from alpha.providers.layer_notes import register_note_watches
    assert register_note_watches(v1, watches_path=watches, directory=tmp_path / "ledger")["registered"] == []  # 冪等
    v2 = _rec(_spec(title="InP 磊晶片 v2", supersedes_id=v1["note_id"]), at="2026-10-09T00:00:00+00:00")
    second = _write(v2, tmp_path, watches)
    assert second["consumed"] == [w["watch_id"]] and len(second["registered"]) == 1
    statuses = {x["source_ref"]: x["status"] for x in ew.load_watches(watches)["watches"]}
    assert statuses[f"layer_note:{v1['note_id']}#1"] == "consumed"
    assert statuses[f"layer_note:{v2['note_id']}#1"] == "active"


def test_a_new_version_handles_touched_and_settles_expired_old_conditions(tmp_path, monkeypatch) -> None:
    """R2 M6／M7：換版是舊條件的處置——觸及未處置的標 handled（verb reread）、到期待決的記 source_superseded。"""
    ew = _ew(monkeypatch)
    watches = tmp_path / "w.json"
    v1 = _rec()
    _write(v1, tmp_path, watches)
    data = ew.load_watches(watches)
    touched = data["watches"][0]
    touched["status"] = "fired"
    touched["judgment"] = {"touches": "yes"}
    expired = dict(touched, watch_id="ew_9999_2026-10-07", status="expired", judgment={},
                   source_ref=touched["source_ref"], expired_at="2026-10-06T00:00:00+00:00")
    data["watches"].append(expired)
    ew.save_watches(data, watches)
    v2 = _rec(_spec(title="InP 磊晶片 v2", supersedes_id=v1["note_id"]), at="2026-10-09T00:00:00+00:00")
    _write(v2, tmp_path, watches)
    by_id = {x["watch_id"]: x for x in ew.load_watches(watches)["watches"]}
    assert by_id[touched["watch_id"]]["judgment"]["handled"]["verb"] == "reread"
    assert by_id[touched["watch_id"]]["judgment"]["handled"]["note_id"] == v2["note_id"]
    assert (by_id["ew_9999_2026-10-07"].get("expiry_resolution") or {}).get("kind") == "source_superseded"


def test_retracting_consumes_its_conditions(tmp_path, monkeypatch) -> None:
    _ew(monkeypatch)
    watches = tmp_path / "w.json"
    v1 = _rec()
    _write(v1, tmp_path, watches)
    retract = layer_note_record({"node": "mat:inp_epiwafer", "unit": "layer", "retracted": True,
                                 "supersedes_id": v1["note_id"], "sections": {}, "claims": []},
                                created_at="2026-10-08T00:00:00+00:00")
    out = _write(retract, tmp_path, watches)
    assert len(out["consumed"]) == 1 and out["registered"] == []


def test_a_layer_note_watch_must_name_its_node(monkeypatch) -> None:
    ew = _ew(monkeypatch)
    with pytest.raises(ew.EventWatchError, match="node"):
        ew.add_watch({"watches": []}, kind=ew.SEMANTIC_KIND, disproof_ref="layer_note:ln_1#1",
                     source_ref="layer_note:ln_1#1", expires="2027-01-31", entities=[CO], condition=COND,
                     check_frequency="每季", action_48h="重讀")


def test_source_is_current_follows_the_current_layer_note() -> None:
    from engine_b.disproof import source_is_current

    current = parse_layer_note_record(_rec())
    notes = {"mat:inp_epiwafer": current}
    assert source_is_current({"source_ref": f"layer_note:{current.note_id}#1"}, layer_notes=notes)
    assert not source_is_current({"source_ref": "layer_note:ln_0000000000000000#1"}, layer_notes=notes)


def test_a_narrative_disproof_may_link_to_a_layer_claim_and_nothing_else_new() -> None:
    """R2 M9：驗證器真的接受 layer_note: 連結鍵，而且沒有因此放寬到別的前綴。"""
    from alpha.narrative.contracts import NarrativeDisproof

    base = dict(condition=COND, check_frequency="每季", action_48h="重讀", entities=(CO,),
                expires=date(2027, 1, 31), source="self")
    assert NarrativeDisproof(**base, link_source_ref="layer_note:ln_aaaaaaaaaaaaaaaa#1").link_source_ref
    with pytest.raises(ContractViolation, match="link_source_ref"):
        NarrativeDisproof(**base, link_source_ref="brief:ib_aaaaaaaaaaaaaaaa#1")


# ---- 反證計數、心跳、重讀清單、audit ----

def _watch(note, n=1, **over):
    ref = f"layer_note:{note.note_id}#{n}"
    w = {"watch_id": f"ew_{note.note_id[-4:]}_{n}", "kind": "semantic_condition", "status": "active",
         "source_ref": ref, "disproof_ref": ref, "node": note.node, "expires": "2027-01-31",
         "condition": note.claims[0].condition, "entities": [CO]}
    w.update(over)
    return w


def test_layer_claims_count_in_the_disproof_counter_instead_of_vanishing(tmp_path) -> None:
    """心跳段 2 的反證計數：不放進「預期」的 watch 會被整類跳過（INV-3）——層說明的主張要被數到。"""
    from engine_b import disproof

    note = parse_layer_note_record(_rec())
    watch = _watch(note)
    without = disproof.disproof_counts([watch], lifecycle={}, readings={}, briefs=(), root=tmp_path)
    with_notes = disproof.disproof_counts([watch], lifecycle={}, readings={}, briefs=(), root=tmp_path,
                                          layer_notes={note.node: note})
    assert without["watching"] == 0 and without["expected"] == 0           # 沒傳＝沒算（不讀真 ledger）
    assert with_notes["expected"] == 1 and with_notes["watching"] == 1 and with_notes["unwatched"] == 0


def test_both_heartbeat_call_sites_pass_the_layer_notes(tmp_path, monkeypatch) -> None:
    """R2 M8／M8b：心跳的反證行與快照兩處都要把現行層說明傳進計數——沒傳，這類條件在兩處都消失。"""
    from crons import heartbeat as hb
    from engine_b import disproof
    from engine_b import event_watch as ew

    note = parse_layer_note_record(_rec())
    monkeypatch.setattr(ew, "load_watches", lambda *a, **k: {"watches": [_watch(note)]})
    monkeypatch.setattr(ew, "primary_coverage", lambda: frozenset())
    monkeypatch.setattr(disproof, "current_readings", lambda: {})
    monkeypatch.setattr(disproof, "current_layer_notes", lambda: {note.node: note})
    monkeypatch.setattr(disproof, "frozen_history_count", lambda: 0)
    monkeypatch.setattr(disproof, "load_lifecycle", lambda: {})
    monkeypatch.setattr(disproof, "current_briefs", lambda: [])
    assert "反證：在盯 1" in "\n".join(hb._disproof_lines())
    values = hb.collect_snapshot(now=datetime(2026, 10, 7, tzinfo=timezone.utc), state_dir=tmp_path,
                                 leads_path=tmp_path / "nope.json", thesis_path=tmp_path / "nope2.json",
                                 run_record_path=None, capture_dir=None)
    assert values["disproof.watching"] == 1


def test_reading_reread_reasons_do_not_absorb_layer_claims() -> None:
    """R2 F7：層說明主張不得撐大「結構讀圖該重讀」——重讀讀圖清不掉它。"""
    from alpha.providers.structure_readings import reread_reasons

    expired = {"kind": "semantic_condition", "node": "mat:inp_epiwafer", "source_ref": "layer_note:ln_a#1",
               "condition": COND, "status": "expired"}
    assert reread_reasons("mat:inp_epiwafer", [expired]) == []


def test_layer_note_reread_rows_name_every_reason_without_a_structure_reading() -> None:
    """R2 C2／F6：逐節點、不依賴讀圖——整份到期、主張到期、主張觸及、主張沒人盯，四種都列。"""
    from alpha.providers.layer_notes import layer_note_reread_rows

    note = parse_layer_note_record(_rec(_spec(node="transition:pluggable_to_cpo", unit="transition")))
    notes = {note.node: note}
    assert layer_note_reread_rows(notes, [_watch(note)], today=date(2026, 10, 8)) == []
    rows = layer_note_reread_rows(notes, [], today=date(2026, 10, 8))
    assert rows and "沒有 watch 在盯" in rows[0]["reasons"][0]
    rows = layer_note_reread_rows(notes, [_watch(note, status="expired")], today=date(2026, 10, 8))
    assert "等滿一輪" in rows[0]["reasons"][0]
    rows = layer_note_reread_rows(notes, [_watch(note, status="fired", judgment={"touches": "yes"})],
                                  today=date(2026, 10, 8))
    assert "被判觸及" in rows[0]["reasons"][0]
    rows = layer_note_reread_rows(notes, [_watch(note)], today=date(2027, 2, 1))
    assert "整份重讀日 2027-01-31 已過" in rows[0]["reasons"][0]


def test_the_heartbeat_prints_the_layer_note_line_even_at_zero(tmp_path, monkeypatch) -> None:
    from crons import heartbeat as hb
    from engine_b import event_watch as ew

    monkeypatch.setattr(ew, "load_watches", lambda *a, **k: {"watches": []})
    assert hb._layer_note_lines(now=datetime(2026, 10, 7, tzinfo=timezone.utc)) == [
        "層說明：一份都還沒寫（`python -m alpha layer-note <node> --add`）"]
    from alpha.providers import layer_notes

    record = _rec()
    path = layer_notes.ledger_path(record["node"])                 # conftest 已導向空的暫存目錄
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = hb._layer_note_lines(now=datetime(2026, 10, 7, tzinfo=timezone.utc))
    assert lines[0].startswith("層說明 1 份｜**該重讀 1**") and "沒有 watch 在盯" in lines[1]
    values = hb.collect_snapshot(now=datetime(2026, 10, 7, tzinfo=timezone.utc), state_dir=tmp_path,
                                 leads_path=tmp_path / "nope.json", thesis_path=tmp_path / "nope2.json",
                                 run_record_path=None, capture_dir=None)
    assert values["layer_note.current"] == 1 and values["layer_note.reread"] == 1


def test_all_nodes_skips_a_broken_first_line(tmp_path) -> None:
    """R2 F4：第一行壞掉不讓整個檔案消失。"""
    from alpha.providers.layer_notes import all_nodes, current_notes

    record = _rec()
    (tmp_path / "mat_inp_epiwafer.jsonl").write_text("{bad json\n[1, 2]\n" + json.dumps(record) + "\n",
                                                    encoding="utf-8")
    assert all_nodes(directory=tmp_path) == ["mat:inp_epiwafer"]
    assert list(current_notes(directory=tmp_path)) == ["mat:inp_epiwafer"]


def test_audit_resolves_layer_claim_watches_instead_of_skipping_them(monkeypatch) -> None:
    """audit 的語意來源檢查：layer_note 的 watch 要被解析（原本 if/elif 沒有這一支，會整類跳過——INV-3）。"""
    from audit import checks, sources

    v1 = parse_layer_note_record(_rec(at="2026-10-01T00:00:00+00:00"))
    v2 = parse_layer_note_record(_rec(_spec(title="InP 磊晶片 v2", supersedes_id=v1.note_id),
                                      at="2026-10-05T00:00:00+00:00"))
    monkeypatch.setattr(sources, "thesis_lifecycle", lambda: {})
    monkeypatch.setattr(sources, "reading_ledgers", lambda: {})
    monkeypatch.setattr(sources, "brief_ledgers", lambda: {})
    monkeypatch.setattr(sources, "layer_note_ledgers",
                        lambda: {v1.node: {"records": [v1, v2], "errors": [], "current": v2}})
    findings, _soft, examined = checks._semantic_source_orphans([_watch(v2)])
    assert examined == 1 and findings == []
    findings, _soft, _ = checks._semantic_source_orphans([_watch(v1)])          # 舊版還在等＝換版後沒收
    assert any("不是" in f and "現行層說明" in f for f in findings)
    findings, _soft, _ = checks._semantic_source_orphans([_watch(v2, n=2)])     # 第 2 條不存在
    assert any("claims[] 對不到" in f for f in findings)
    ghost = _watch(v2, source_ref="layer_note:ln_ffffffffffffffff#1", disproof_ref="layer_note:ln_ffffffffffffffff#1")
    findings, _soft, _ = checks._semantic_source_orphans([ghost])
    assert any("ledger 裡沒有這一份" in f for f in findings)


def test_claim_rows_print_unwatched_instead_of_disappearing() -> None:
    from alpha.providers.layer_notes import claim_watch_rows

    note = parse_layer_note_record(_rec())
    assert claim_watch_rows(note, [])[0]["status"] == "未盯"
