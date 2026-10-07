"""層說明的純文字閱讀頁（個股頁 plan S4b；2026-10-07）。

守的事：①全文照印，三段依 ①②③ 的固定順序（不看存檔順序）；②每個出處並列兩種等級——層說明寫的（誰說的）與
**文件自宣告**（文件自己帶的等級與檔頭說明，逐字），沒宣告才印「文件沒宣告」，問不到的另有理由（L12、L16、L18）；
③每條主張的 watch 狀態只有一個判定（`claim_state`），與「該重讀」同一套；④「哪幾頁連過來」由圖推、與個股頁
「坐的層」同一個函式，缺席分型由產生端宣告；⑤它不 gate 任何東西：讀圖面板的狀態不因層說明而變。
"""
from __future__ import annotations

import json
from collections import namedtuple
from datetime import date, datetime, timezone

import pytest
from starlette.testclient import TestClient

from alpha.layer_note import layer_note_record, parse_layer_note_record

CO = "co:coherent"
COND = "任一 IDM 公告自建磊晶產能足以自給，或客戶 filing 列出外包比例下降"
NODE = "tech:external_laser_source"
Edge = namedtuple("Edge", "src relation dst")


def _spec(**over):
    spec = {
        "node": NODE, "unit": "layer", "title": "外部光源", "expires": "2027-01-31",
        "reread_reason": "Q4 財報出來時重讀供給側家數",
        # 刻意把段的順序寫成 ③①②：閱讀頁要照 SECTION_KEYS 排，不看 spec 或存檔的順序
        "sections": {
            "selection": {"text": "客戶選光源看的是功率、波長穩定與長期供貨；換掉要重新認證一整輪。" * 2,
                          "citations": [{"evidence": "inference"}]},
            "physics": {"text": "## ① 物理與變體\n\n| 公司 | 變體 |\n|---|---|\n| A | CW |\n\n- 第一點\n  - 縮排的第二點" * 2,
                        "citations": [{"evidence": "primary", "ref": "raw:doc_a", "quote": "逐字的一句"}]},
            "variants": {"text": "IDM 自己做、外購兩條路；各家走到量產的階段不同。" * 2,
                         "citations": [{"evidence": "primary", "ref": "raw:doc_b"},
                                       {"evidence": "industry_report", "ref": "lead:lead_x1"}]},
        },
        "claims": [{
            "claim": "外部光源的需求會隨 CPO 放量而增加，IDM 自己的產能不夠",
            "condition": COND, "entities": [CO], "check_frequency": "每季財報",
            "action_48h": "重讀層說明、改受影響的敘事那一格", "evidence": "primary",
            "citations": [{"evidence": "primary", "ref": "raw:doc_a"}],
        }],
    }
    spec.update(over)
    return spec


def _record(spec=None, at="2026-10-07T00:00:00+00:00"):
    return layer_note_record(spec or _spec(), created_at=at)


def _watch(note, n=1, **over):
    ref = f"layer_note:{note.note_id}#{n}"
    watch = {"watch_id": f"ew_{note.note_id[-4:]}_{n}", "kind": "semantic_condition", "status": "active",
             "source_ref": ref, "disproof_ref": ref, "node": note.node, "expires": "2027-01-31",
             "condition": note.claims[n - 1].condition, "entities": [CO]}
    watch.update(over)
    return watch


def _raw_tree(tmp_path):
    """raw 與抽取檔的小宇宙：三種自宣告各一份、什麼都沒有一份、對不上名字的抽取檔一份、壞掉的抽取檔一份。"""
    raw = tmp_path / "raw"
    ext = tmp_path / "extractions"
    raw.mkdir(parents=True)
    ext.mkdir(parents=True)
    (raw / "doc_a.txt").write_text(
        "SOURCE: 某報導\nURL: https://example.com/a\nNOTE: 媒體轉述（tier 3）。法說錄音沒有取得。\n\n正文第一段\n",
        encoding="utf-8")
    (raw / "doc_b.txt").write_text(
        "SOURCE: 某法說轉錄\nhttps://example.com/b\n\n⚠ EVIDENCE TIER：第三方逐字轉錄，**非 issuer 官方發布**。\n"
        "未核對前不得標記為 issuer 一手。\n\n--- 逐字 quote ---\nNOTE: 正文裡的字不算\n", encoding="utf-8")
    (raw / "doc_c.pdf").write_bytes(b"%PDF-1.4 binary")
    (raw / "doc_c.meta.json").write_text(json.dumps({"doc_id": "doc_c", "evidence_tier": 1}), encoding="utf-8")
    (raw / "doc_d.txt").write_text("# Source: 某新聞稿\n# URL: https://example.com/d\n\n正文\n", encoding="utf-8")
    (raw / "doc_e.txt").write_text("SOURCE: 某頁\nURL: https://example.com/e\n\n" + "正文\n" * 25
                                   + "NOTE: 第 29 行的 NOTE 不在檔頭\n", encoding="utf-8")
    # 檔頭之後另起一段的 Note（改寫過的節錄自己聲明）照收
    (raw / "doc_f.txt").write_text("# Source: 某法說\n# URL: https://example.com/f\n\nNote: Technical content below is "
                                   "paraphrased, not verbatim.\n\n[Passage 1]\n正文\n", encoding="utf-8")
    (ext / "doc_d_extraction.json").write_text(json.dumps({"source_doc": {"doc_id": "doc_d", "evidence_tier": 2}}),
                                               encoding="utf-8")
    # 名字對不上的抽取檔（failure log #37 的形狀）：不得被算成 doc_e 的等級
    (ext / "doc_e_2026.json").write_text(json.dumps({"source_doc": {"doc_id": "doc_e_2026", "evidence_tier": 1}}),
                                         encoding="utf-8")
    (ext / "broken.json").write_text("{not json", encoding="utf-8")
    return raw, ext


# ---- 文件自宣告 ----

def test_source_declarations_copy_what_the_document_says_and_never_guess(tmp_path) -> None:
    from alpha.providers.layer_notes import source_declarations

    raw, ext = _raw_tree(tmp_path)
    result = source_declarations(
        ["raw:doc_a", "raw:doc_b", "raw:doc_c", "raw:doc_d", "raw:doc_e", "raw:doc_f", "lead:lead_1", "raw:gone"],
        raw_dir=raw, extraction_dir=ext)
    by_ref = result["by_ref"]
    # 檔頭的 NOTE 段逐字（L18）；不從句子裡抽 tier 數字
    assert by_ref["raw:doc_a"] == {"tiers": [], "lines": ["NOTE: 媒體轉述（tier 3）。法說錄音沒有取得。"], "absence": None}
    # `⚠ EVIDENCE TIER：` 段（全形冒號）連同續行；正文裡的 NOTE 不算
    assert by_ref["raw:doc_b"]["lines"] == [
        "⚠ EVIDENCE TIER：第三方逐字轉錄，**非 issuer 官方發布**。\n未核對前不得標記為 issuer 一手。"]
    assert by_ref["raw:doc_c"]["tiers"] == [{"tier": 1, "from": "raw 附檔 doc_c.meta.json"}]
    assert by_ref["raw:doc_c"]["lines"] == []                       # PDF 不讀檔頭
    assert by_ref["raw:doc_d"]["tiers"] == [{"tier": 2, "from": "抽取檔 doc_d_extraction.json"}]
    # 什麼都沒有才是「文件沒宣告」；第 29 行的 NOTE、名字對不上的抽取檔都不算（不猜）
    assert by_ref["raw:doc_e"]["absence"] == {"kind": "not_declared", "label": "文件沒宣告"}
    assert by_ref["raw:doc_f"]["lines"] == ["Note: Technical content below is paraphrased, not verbatim."]
    assert by_ref["lead:lead_1"]["absence"]["kind"] == "lead_ref"
    assert by_ref["raw:gone"]["absence"]["kind"] == "raw_missing"
    # 讀不懂的抽取檔逐檔回報（它可能正是帶著等級的那一份，INV-3）
    assert result["unreadable"] == ["broken.json"]


# ---- 主張狀態：一個判定 ----

@pytest.mark.parametrize("over, state", [
    (None, "unwatched"),
    ({"status": "consumed"}, "unwatched"),
    ({}, "active"),
    ({"status": "fired"}, "fired"),
    ({"status": "fired", "judgment": {"touches": "yes"}}, "touched"),
    ({"status": "active", "judgment": {"touches": "yes", "handled": {"verb": "reread"}}}, "active"),
    ({"status": "expired"}, "expired"),
    ({"status": "expired", "expiry_resolution": {"kind": "source_superseded"}}, "settled"),
])
def test_claim_state_is_one_judgment_shared_with_reread(over, state) -> None:
    from alpha.providers.layer_notes import CLAIM_STATES, claim_watch_rows, layer_note_reread_rows

    note = parse_layer_note_record(_record())
    watches = [] if over is None else [_watch(note, **over)]
    row = claim_watch_rows(note, watches)[0]
    assert row["state"] == state and row["state_label"] == CLAIM_STATES[state]
    reasons = (layer_note_reread_rows({note.node: note}, watches, today=date(2026, 10, 8)) or [{"reasons": []}])[0]
    # 「該重讀」的三種主張理由恰好是這三格——同一個判定，不是第二套
    assert bool(reasons["reasons"]) == (state in ("unwatched", "touched", "expired"))


# ---- 閱讀頁的一列 ----

def test_note_page_row_prints_sections_in_fixed_order_with_both_levels(tmp_path) -> None:
    from alpha.providers.layer_notes import note_citation_refs, note_page_row, source_declarations

    raw, ext = _raw_tree(tmp_path)
    note = parse_layer_note_record(_record())
    declarations = source_declarations(note_citation_refs(note), raw_dir=raw, extraction_dir=ext)["by_ref"]
    row = note_page_row(note, watches=[_watch(note)], declarations=declarations, reread=["整份重讀日已過"], versions=2)
    assert [s["key"] for s in row["sections"]] == ["physics", "variants", "selection"]
    assert [s["label"][0] for s in row["sections"]] == ["①", "②", "③"]
    physics = row["sections"][0]
    assert physics["text"] == note.sections["physics"].text            # 全文照印，一個字不改
    cite = physics["citations"][0]
    assert cite["evidence_label"] == "一手" and cite["quote"] == "逐字的一句"
    assert cite["declared"]["lines"] == ["NOTE: 媒體轉述（tier 3）。法說錄音沒有取得。"]   # 兩種等級並列、不合併
    # 推一步沒有出處：沒有文件可問——是 None，不是「文件沒宣告」（L12）
    assert row["sections"][2]["citations"][0]["declared"] is None
    claim = row["claims"][0]
    assert claim["state"] == "active" and claim["watch_id"] == _watch(note)["watch_id"]
    assert claim["source_ref"] == f"layer_note:{note.note_id}#1"
    assert row["reread"] == ["整份重讀日已過"] and row["versions"] == 2
    assert "body_ref" not in row                                        # private 路徑不出門
    # 有出處卻沒算到文件自宣告＝呼叫端漏算：直接 KeyError，不退回一句假的「文件沒宣告」
    with pytest.raises(KeyError):
        note_page_row(note, watches=[], declarations={}, reread=())


# ---- 哪幾頁連過來 ----

def test_cited_by_comes_from_the_graph_and_names_why_not() -> None:
    from webapp.layer_notes import cited_by

    seats = {"co:coherent": [NODE], "co:danfoss": [NODE], "co:ghost": [NODE], "co:lumentum": [NODE, "tech:other"],
             "co:poet": ["tech:other"]}
    graph_nodes = frozenset({NODE, "tech:other", "tech:lonely"})
    companies = {"co:coherent": {"known": True, "ticker": "cohr", "label": "Coherent"},
                 "co:danfoss": {"known": True, "ticker": None, "label": "Danfoss"},
                 "co:lumentum": {"known": True, "ticker": "LITE", "label": "Lumentum"},
                 "co:ghost": {"known": False, "ticker": None, "label": None}}
    out = cited_by(NODE, "layer", seats=seats, graph_nodes=graph_nodes, companies=companies,
                   pages=frozenset({"LITE", "COHR"}))
    assert [p["ticker"] for p in out["pages"]] == ["COHR", "LITE"] and out["absence"] is None   # 依代號字母，不是名次
    reasons = {w["company_id"]: w["reason"] for w in out["without_page"]}
    assert "null" in reasons["co:danfoss"] and "不猜" in reasons["co:danfoss"]
    assert "解析不到" in reasons["co:ghost"]
    no_page = cited_by(NODE, "layer", seats=seats, graph_nodes=graph_nodes, companies=companies, pages=frozenset())
    assert "還沒有個股頁" in {w["company_id"]: w["reason"] for w in no_page["without_page"]}["co:coherent"]
    kind = lambda **kw: cited_by(**{"node": NODE, "unit": "layer", "seats": seats, "graph_nodes": graph_nodes,  # noqa: E731
                                    "companies": companies, "pages": frozenset(), **kw})["absence"]["kind"]
    assert kind(unit="transition", node="transition:pluggable_to_cpo") == "transition"
    assert kind(seats=None, graph_nodes=None) == "upstream_unavailable"
    assert kind(node="mat:inp_epiwafer") == "node_absent_from_graph"
    assert kind(node="tech:lonely") == "no_seated_company"


# ---- artifact ----

def fake_layer_notes_payload():
    """空的層說明 artifact（`tests/test_webapp_request_path.py` 的四種證明用）。"""
    return _artifact([])


def _artifact(rows, **kw):
    from alpha.layer_note import EVIDENCE_LABELS, SECTION_LABELS
    from alpha.providers.layer_notes import CLAIM_STATES, DECLARATION_ABSENCES
    from webapp.layer_notes import build_layer_notes_artifact

    labels = {"sections": SECTION_LABELS, "evidence": EVIDENCE_LABELS, "claim_states": CLAIM_STATES,
              "declaration_absences": DECLARATION_ABSENCES}
    return build_layer_notes_artifact(rows=rows, labels=labels, **kw)


def _row(tmp_path, watches=None):
    from alpha.providers.layer_notes import note_citation_refs, note_page_row, source_declarations
    from webapp.layer_notes import cited_by

    raw, ext = _raw_tree(tmp_path)
    note = parse_layer_note_record(_record())
    declarations = source_declarations(note_citation_refs(note), raw_dir=raw, extraction_dir=ext)["by_ref"]
    row = note_page_row(note, watches=[_watch(note)] if watches is None else watches, declarations=declarations)
    row["cited_by"] = cited_by(NODE, "layer", seats={CO: [NODE]}, graph_nodes=frozenset({NODE}),
                               companies={CO: {"known": True, "ticker": "COHR", "label": "Coherent"}},
                               pages=frozenset({"COHR"}))
    return note, row


def test_artifact_validates_and_identity_tracks_cognition_not_time(tmp_path) -> None:
    from webapp.contracts import STATE_KINDS, validate_state_artifact

    assert "layer_notes" in STATE_KINDS
    note, row = _row(tmp_path)
    one = _artifact([row], generated_at=datetime(2026, 10, 7, tzinfo=timezone.utc))
    validate_state_artifact("layer_notes", one)
    counts = one["counts"]
    assert counts["notes"] == 1 and counts["claims"] == 1 and counts["claim_states"] == {"active": 1}
    # 出處 5 個（三段 4＋主張 1），其中推一步 1 個沒有文件可問；有出處的 4 個裡 lead 那個問不到
    assert (counts["citations"], counts["citations_with_ref"], counts["citations_declared"]) == (5, 4, 3)
    assert one["pages_linked"] == ["COHR"] and counts["pages_linked"] == 1
    later = _artifact([row], generated_at=datetime(2026, 10, 8, tzinfo=timezone.utc))
    assert later["freshness_identity"] == one["freshness_identity"]          # 時間不是認知
    assert later["content_digest"] != one["content_digest"]
    _note, unwatched = _row(tmp_path / "b", watches=[])
    assert _artifact([unwatched])["freshness_identity"] != one["freshness_identity"]   # 主張沒人盯了＝認知變了
    # 不 gate 任何東西：沒有排序、分數、尺寸的欄位
    assert not {"rank", "score", "size", "weight", "candidate_state"} & set(one["rows"][0])


def test_materialize_end_to_end_reads_ledger_graph_and_registry(tmp_path, monkeypatch) -> None:
    """真的走 materialize：ledger（conftest 導向的空目錄）＋假的圖＋真的名冊；圖讀不到時全文照印、只有連過來那一欄說讀不到。"""
    import query.structure
    from alpha.providers import layer_notes
    from engine_b import event_watch as ew
    from webapp.materialize import materialize_layer_notes
    from webapp.store import StateArtifactStore

    raw, ext = _raw_tree(tmp_path)
    monkeypatch.setattr(layer_notes, "RAW_DIR", raw)
    monkeypatch.setattr(layer_notes, "EXTRACTION_DIR", ext)
    record = _record()
    path = layer_notes.ledger_path(record["node"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False) + "\n{broken\n", encoding="utf-8")
    (path.parent / "orphan.jsonl").write_text("{broken\n", encoding="utf-8")
    note = parse_layer_note_record(record)
    monkeypatch.setattr(ew, "load_watches", lambda *a, **k: {"watches": [_watch(note)]})
    monkeypatch.setattr(query.structure, "_load_edges", lambda: [
        Edge(CO, "supplies_to", NODE), Edge("co:danfoss", "supplies_to", NODE), Edge("tech:cpo", "depends_on", NODE)])
    store = StateArtifactStore(tmp_path / "state")
    _path, payload = materialize_layer_notes(store=store, pages=["COHR", "LITE"])
    stored, _fresh = store.read("layer_notes")
    assert stored == payload
    row = payload["rows"][0]
    assert row["node"] == NODE and [p["ticker"] for p in row["cited_by"]["pages"]] == ["COHR"]
    assert [w["company_id"] for w in row["cited_by"]["without_page"]] == ["co:danfoss"]
    assert payload["company_labels"][CO]                      # 盯的公司與坐的公司有名字（名冊，不從 id 猜）
    # 壞行與一行都讀不出 node 的檔都現形（INV-3）
    assert any(":2:" in e for e in payload["parse_errors"]) and any("orphan.jsonl" in e for e in payload["parse_errors"])
    assert payload["declaration_problems"] == ["broken.json"]

    def no_graph():
        raise ConnectionError("bolt down")

    monkeypatch.setattr(query.structure, "_load_edges", no_graph)
    _path, down = materialize_layer_notes(store=store, pages=["COHR"])
    assert down["graph"]["absence"]["kind"] == "upstream_unavailable"
    assert down["rows"][0]["cited_by"]["absence"]["kind"] == "upstream_unavailable"
    assert down["rows"][0]["sections"][0]["text"] == row["sections"][0]["text"]     # 全文不靠圖


# ---- 個股頁「坐的層」→ 閱讀頁 ----

def test_seat_readings_link_only_the_seated_nodes_with_a_current_note() -> None:
    from alpha.providers.structure_readings import seat_readings_for

    context = {"seats": {CO: ["tech:fau", NODE, "tech:none"]}, "by_node": {},
               "layer_notes": {NODE: {"node": NODE, "note_id": "ln_a", "title": "外部光源"},
                               "tech:fau": {"node": "tech:fau", "note_id": "ln_b", "title": "FAU"},
                               "mat:elsewhere": {"node": "mat:elsewhere", "note_id": "ln_c", "title": "別處"}}}
    out = seat_readings_for(context, CO)
    assert [n["node"] for n in out["layer_notes"]] == ["tech:fau", NODE]          # 與坐的層同一個順序
    assert seat_readings_for(context, "co:nobody")["layer_notes"] == []
    absent = {**context, "layer_notes": {}, "layer_notes_absence": {"kind": "upstream_unavailable", "reason": "x"}}
    assert seat_readings_for(absent, CO)["layer_notes_absence"]["kind"] == "upstream_unavailable"


def test_layer_note_index_reads_the_ledger_and_says_when_it_cannot(monkeypatch) -> None:
    from alpha.providers import layer_notes, structure_readings

    record = _record()
    path = layer_notes.ledger_path(record["node"])                   # conftest 已導向空的暫存目錄
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    index = structure_readings._layer_note_index()
    assert index["layer_notes"][NODE] == {"node": NODE, "note_id": record["note_id"], "title": "外部光源"}

    def boom():
        raise OSError("disk")

    monkeypatch.setattr(layer_notes, "current_notes", boom)
    broken = structure_readings._layer_note_index()
    assert broken["layer_notes"] == {} and broken["layer_notes_absence"]["kind"] == "upstream_unavailable"


def test_readings_panel_carries_the_links_without_changing_its_status() -> None:
    """兩條路（有讀圖／沒讀圖）都帶連結；面板狀態與缺席分型一個字都不因層說明而變——它不 gate 任何東西。"""
    from briefing.analyst_view.compose import _readings_panel

    links = {"layer_notes": [{"node": NODE, "note_id": "ln_a", "title": "外部光源"}]}
    reading = {"node": NODE, "unit": "layer", "unit_label": "層", "kind": "volume", "kind_label": "量",
               "status": "current", "status_label": "現行", "reading_id": "sr_x"}
    for base in ({"seats": [NODE], "readings": [reading]},
                 {"seats": [NODE], "readings": [], "empty": {"kind": "not_yet_recorded", "reason": "還沒讀"}}):
        plain = _readings_panel(base)
        linked = _readings_panel({**base, **links})
        assert linked.context["layer_notes"] == links["layer_notes"]
        assert (linked.status, dict(linked.source_absence_kinds)) == (plain.status, dict(plain.source_absence_kinds))
        assert plain.context["layer_notes"] == []


# ---- APP 與 CLI ----

def test_the_route_serves_the_artifact_and_503s_with_the_remedy(tmp_path) -> None:
    from webapp.api import create_app
    from webapp.store import StateArtifactStore

    client = TestClient(create_app(tmp_path))
    missing = client.get("/api/v1/layer-notes")
    assert missing.status_code == 503 and "--layer-notes" in missing.json()["error"]["remedy"]
    _note, row = _row(tmp_path)
    StateArtifactStore(tmp_path / "state").write(_artifact([row]))
    body = client.get("/api/v1/layer-notes").json()
    assert body["kind"] == "layer_notes" and body["rows"][0]["node"] == NODE


def test_the_flag_is_a_state_only_materializer_and_status_reads_its_counts() -> None:
    from webapp.__main__ import _STATE_FLAGS, _layer_notes_summary, build_parser

    args = build_parser().parse_args(["materialize", "--layer-notes"])
    assert args.layer_notes is True and "layer_notes" in _STATE_FLAGS     # 只給它不會重跑每一檔單檔
    payload = {"counts": {"notes": 5, "claims": 6, "claim_states": {"active": 6}, "citations_with_ref": 125,
                          "citations_declared": 122, "pages_linked": 5, "needs_reread": 0}, "graph": {"absence": None}}
    assert "連過來的個股頁 5" in _layer_notes_summary(payload)
    payload["graph"] = {"absence": {"kind": "upstream_unavailable"}}
    assert "未算（圖讀不到）" in _layer_notes_summary(payload)            # 讀不到不是 0


def test_as_of_is_refused_instead_of_silently_serving_today(tmp_path, monkeypatch, capsys) -> None:
    """INV-6：閱讀頁只有現在的視角——帶 --as-of 要明確拒絕，不得寫出一份「現在」的 artifact 冒充 T 時刻。"""
    from webapp import __main__ as cli
    from webapp import materialize

    called = []
    monkeypatch.setattr(materialize, "materialize_layer_notes", lambda **kw: called.append(kw))
    code = cli.main(["materialize", "--layer-notes", "--as-of", "2026-09-01", "--dir", str(tmp_path)])
    assert code == 1 and called == []
    assert "as-of 視角明確拒絕" in capsys.readouterr().err
    assert not (tmp_path / "state" / "layer_notes.json").exists()
