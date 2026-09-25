"""讀圖契約 v3（Phase 2 Step 2.3，plan 2026-09-25-001 §4、amendment A1／A2）。

守四件事：
1. **舊 id 一個字都不能變**：v1／v2 的 `reading_id` 用新程式重算必須逐字相同——Phase 1 登記的語意 watch
   與 audit `Orphans` 以 reading_id 指回來源（plan 不可越線 2）。下面的 golden 值是**改動前的程式**算的。
2. **單位是新欄位，不是判讀字彙的新值**（A1）：`unit ∈ {layer, socket}`；v1／v2 一律解析成 `layer`。
3. **判讀指得回原文**（A2，L18）：moat／volume 兩半各至少一段引用；插槽的護城河另需一段不是供應商自己的來源（L8）。
4. **反證有出處**：v3 每條 `disproof` 帶 `source`（`self` 或同節點既有的 `sr_*`）。
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from alpha.errors import ContractViolation
from alpha.structure_reading.contracts import (
    READING_KINDS, READING_UNITS, RECORD_VERSION, new_reading_id, parse_structure_reading_record,
    select_reading, select_readings, structure_reading_record,
)

_BASE = {
    "node": "tech:cw_dfb_laser", "result_digest": "d" * 64, "kind": "volume",
    "reading": "供給側大家差不多，賭的是產能一時補不上（golden 測試用）",
    "created_at": "2026-09-18T15:24:18.445462+00:00", "author": "session", "expires": "2026-10-18",
    "tickers": ["COHR", "LITE"], "supersedes_id": None, "retracted": False,
}
_V2_DISPROOF = [{"condition": "任一需求側客戶在正式文件宣布改用不經這個節點的替代路徑並量產",
                 "entities": ["co:coherent"], "check_frequency": "每季", "action_48h": "重讀這個節點"}]


def test_v1_and_v2_ids_are_byte_for_byte_unchanged() -> None:
    """golden 值由 2026-09-25 改動前的 `new_reading_id` 算出（Step 2.3 動手前先寫這條並讓它綠）。"""
    v1 = dict(_BASE, record_version="structure-reading/v1")
    v2 = dict(_BASE, record_version="structure-reading/v2", disproof=_V2_DISPROOF)
    assert new_reading_id(v1) == "sr_dd4533fcc300da2f"
    assert new_reading_id(v2) == "sr_c01a938cf2085c67"
    # 沒有 record_version 的舊紀錄照 v1 算
    assert new_reading_id(dict(_BASE)) == "sr_dd4533fcc300da2f"


# ---------------------------------------------------------------------------
# 夾具：一個插槽（prod:supernova）與一個層（tech:cw_dfb_laser）的快照＋同一次查詢的逐字
# ---------------------------------------------------------------------------

SOCKET = "prod:supernova"
LAYER = "tech:cw_dfb_laser"
SIVERS = "co:sivers_semiconductors"
NOW = datetime(2026, 9, 25, 3, 0, tzinfo=timezone.utc)
TODAY = date(2026, 9, 25)
LATER = date(2026, 12, 24)

DEMAND_Q = "TeraPHY optical chiplet relies on the SuperNova multi-wavelength light source"
SUPPLY_Q = "Sivers supplies the laser array for the SuperNova light source in volume"
CUSTOMER_Q = "Ayar Labs selected Sivers as the laser array supplier for SuperNova"


def _structure(node: str) -> dict:
    return {
        "node": node, "result_digest": "e" * 64, "anchor_chain": None,
        "angles": {
            "demand_side": [{"src": "prod:teraphy_chiplet", "relation": "depends_on", "dst": node,
                             "substitutability": 5, "sole_source": None, "qualification_status": None,
                             "evidence": "needs_review", "documents": 1}],
            "supply_side": [{"src": SIVERS, "relation": "supplies_to", "dst": node,
                             "substitutability": None, "sole_source": None, "qualification_status": "designed_in",
                             "evidence": "needs_review", "documents": 1}],
            "next_layer": [], "counter_path": [],
        },
    }


def _quotes(node: str, *, supply_origin: str = "Sivers Semiconductors") -> dict:
    return {
        ("prod:teraphy_chiplet", "depends_on", node): [
            {"quote": DEMAND_Q + "，並寫進產品規格", "doc": "doc_demand", "origin": "Ayar Labs"}],
        (SIVERS, "supplies_to", node): [
            {"quote": SUPPLY_Q, "doc": "doc_supply", "origin": supply_origin},
            {"quote": CUSTOMER_Q, "doc": "doc_customer", "origin": "Ayar Labs"}],
    }


def _cite(angle: str, quote: str, source_id: str, node: str, *, independent: bool = False) -> dict:
    edge = (["prod:teraphy_chiplet", "depends_on", node] if angle == "demand_side"
            else [SIVERS, "supplies_to", node])
    return {"angle": angle, "edge": edge, "quote": quote, "source_id": source_id, "independent": independent}


def _two_halves(node: str) -> list[dict]:
    return [_cite("demand_side", DEMAND_Q, "doc_demand", node), _cite("supply_side", SUPPLY_Q, "doc_supply", node)]


def _disproof(source: str = "self") -> list[dict]:
    return [{"condition": "Ayar Labs 的一手文件具名另一家雷射陣列供應商進入 SuperNova 量產",
             "entities": [SIVERS, "co:ayar_labs"], "check_frequency": "每季", "action_48h": "重讀這個插槽",
             "source": source}]


def _v3(node: str = SOCKET, *, unit: str = "socket", kind: str = "volume", citations=None, disproof=None,
        **kw) -> dict:
    params = dict(node=node, structure=_structure(node), unit=unit, kind=kind,
                  reading="插槽讀圖測試：需求側繞不過，供給側只有一家、證據只有一篇——判讀寫清楚缺哪一格。",
                  expires=LATER, created_at=NOW, author="test",
                  citations=_two_halves(node) if citations is None else citations,
                  disproof=_disproof() if disproof is None else disproof)
    params.update(kw)
    return structure_reading_record(**params)


# ---------------------------------------------------------------------------
# A1：單位
# ---------------------------------------------------------------------------

def test_units_are_a_closed_vocabulary_separate_from_kinds() -> None:
    assert set(READING_UNITS) == {"layer", "socket"}
    assert set(READING_KINDS) == {"moat", "volume", "neither", "undecided"}, "判讀字彙不動（A1）"


def test_v1_and_v2_parse_as_layer_and_v3_must_declare_its_unit() -> None:
    v2 = dict(_BASE, record_version="structure-reading/v2", disproof=_V2_DISPROOF, angles={}, anchor_chain=None,
              unit="socket")
    v2["reading_id"] = new_reading_id(v2)
    assert parse_structure_reading_record(v2).unit == "layer", "v1／v2 一律是層讀圖，檔內多寫的 unit 不算"
    record = _v3()
    assert record["record_version"] == RECORD_VERSION and record["unit"] == "socket"
    missing = dict(record)
    missing.pop("unit")
    with pytest.raises(ContractViolation, match="unit"):
        parse_structure_reading_record(missing)
    with pytest.raises(TypeError):
        structure_reading_record(node=LAYER, structure=_structure(LAYER), kind="undecided",
                                 reading="沒有宣告單位的讀圖——不讓程式替寫的人補預設值。",
                                 expires=LATER, created_at=NOW)


def test_socket_unit_only_on_product_nodes_and_layer_never_on_companies() -> None:
    with pytest.raises(ContractViolation, match="prod"):
        _v3(LAYER, unit="socket")
    with pytest.raises(ContractViolation, match="公司"):
        _v3("co:sivers_semiconductors", unit="layer", kind="undecided", citations=[], disproof=[])


def test_selection_is_per_unit_and_select_reading_has_no_default_unit() -> None:
    layer = parse_structure_reading_record(_v3(SOCKET, unit="layer"))
    socket = parse_structure_reading_record(_v3(SOCKET, unit="socket", created_at=NOW.replace(hour=4)))
    records = [layer, socket]
    assert select_reading(records, unit="layer", today=TODAY).reading_id == layer.reading_id
    assert select_reading(records, unit="socket", today=TODAY).reading_id == socket.reading_id
    assert {u: r.reading_id for u, r in select_readings(records, today=TODAY).items()} == {
        "layer": layer.reading_id, "socket": socket.reading_id}, "較新的插槽讀圖不得蓋掉層讀圖"
    with pytest.raises(TypeError):
        select_reading(records, today=TODAY)


# ---------------------------------------------------------------------------
# A2：契約層的拒收規則（不查圖）
# ---------------------------------------------------------------------------

def test_volume_or_moat_missing_one_half_is_rejected() -> None:
    with pytest.raises(ContractViolation, match="supply_side"):
        _v3(citations=[_cite("demand_side", DEMAND_Q, "doc_demand", SOCKET)])
    with pytest.raises(ContractViolation, match="demand_side"):
        _v3(kind="moat", citations=[_cite("supply_side", CUSTOMER_Q, "doc_customer", SOCKET, independent=True)])
    # undecided／neither 不強制引用（判不出來才誠實）
    assert _v3(kind="undecided", citations=[], disproof=[])["kind"] == "undecided"


def test_socket_moat_needs_an_independent_supply_side_citation() -> None:
    with pytest.raises(ContractViolation, match="independent"):
        _v3(kind="moat")   # 兩半都有，但供給側只有供應商自己的原文
    ok = _v3(kind="moat", citations=[_cite("demand_side", DEMAND_Q, "doc_demand", SOCKET),
                                     _cite("supply_side", CUSTOMER_Q, "doc_customer", SOCKET, independent=True)])
    assert ok["kind"] == "moat"
    # 層的護城河不需要 independent（L8 的這條只綁插槽，plan R-1）
    assert _v3(LAYER, unit="layer", kind="moat")["kind"] == "moat"


def test_v3_disproof_must_state_its_source() -> None:
    bad = _disproof()
    bad[0].pop("source")
    with pytest.raises(ContractViolation, match="source"):
        _v3(disproof=bad)
    with pytest.raises(ContractViolation, match="source"):
        _v3(disproof=_disproof(source="somewhere"))


def test_short_quotes_cannot_identify_a_passage() -> None:
    with pytest.raises(ContractViolation, match="至少"):
        _v3(citations=[_cite("demand_side", "sole source", "doc_demand", SOCKET),
                       _cite("supply_side", SUPPLY_Q, "doc_supply", SOCKET)])


# ---------------------------------------------------------------------------
# A2：寫入端核對（對同一份快照的逐字）
# ---------------------------------------------------------------------------

def test_a_legal_v3_reading_appends_and_registers_its_watches(tmp_path) -> None:
    from alpha.providers.structure_readings import append_reading_record, read_reading_records, register_reading_watches

    record = _v3()
    append_reading_record(record, directory=tmp_path, quotes=_quotes(SOCKET))
    records, errors = read_reading_records(SOCKET, directory=tmp_path)
    assert not errors and records[0].unit == "socket" and len(records[0].citations) == 2
    summary = register_reading_watches(record)
    assert len(summary["registered"]) == 1, "v3 的反證照樣登記成語意 watch（G7）"


def test_citation_edge_must_be_in_this_snapshot(tmp_path) -> None:
    from alpha.providers.structure_readings import append_reading_record

    stray = _cite("supply_side", SUPPLY_Q, "doc_supply", SOCKET)
    stray["edge"] = ["co:coherent", "supplies_to", SOCKET]
    record = _v3(citations=[_cite("demand_side", DEMAND_Q, "doc_demand", SOCKET), stray])
    with pytest.raises(ContractViolation, match="不在這次快照"):
        append_reading_record(record, directory=tmp_path, quotes=_quotes(SOCKET))


def test_citation_quote_must_be_verbatim_from_that_source(tmp_path) -> None:
    from alpha.providers.structure_readings import append_reading_record

    invented = _v3(citations=[_cite("demand_side", DEMAND_Q, "doc_demand", SOCKET),
                              _cite("supply_side", "Sivers is the only supplier that can ever make this part", "doc_supply", SOCKET)])
    with pytest.raises(ContractViolation, match="任何一段逐字"):
        append_reading_record(invented, directory=tmp_path, quotes=_quotes(SOCKET))
    wrong_doc = _v3(citations=[_cite("demand_side", DEMAND_Q, "doc_demand", SOCKET),
                               _cite("supply_side", SUPPLY_Q, "doc_customer", SOCKET)])
    with pytest.raises(ContractViolation, match="任何一段逐字"):
        append_reading_record(wrong_doc, directory=tmp_path, quotes=_quotes(SOCKET))


def test_citations_without_the_same_snapshot_quotes_fail_closed(tmp_path) -> None:
    from alpha.providers.structure_readings import append_reading_record

    with pytest.raises(ContractViolation, match="quotes"):
        append_reading_record(_v3(), directory=tmp_path)


def test_independent_citation_from_the_supplier_itself_is_rejected(tmp_path) -> None:
    from alpha.providers.structure_readings import append_reading_record

    self_claim = _v3(kind="moat", citations=[_cite("demand_side", DEMAND_Q, "doc_demand", SOCKET),
                                             _cite("supply_side", SUPPLY_Q, "doc_supply", SOCKET, independent=True)])
    with pytest.raises(ContractViolation, match="自己"):
        append_reading_record(self_claim, directory=tmp_path, quotes=_quotes(SOCKET))


def test_independent_citation_whose_origin_does_not_resolve_is_rejected(tmp_path) -> None:
    """SuperNova 現況：唯一的原文是一篇 substack（origin 解析不到）——依 A2 它**不能**讀成護城河。"""
    from alpha.providers.structure_readings import append_reading_record

    record = _v3(kind="moat", citations=[_cite("demand_side", DEMAND_Q, "doc_demand", SOCKET),
                                         _cite("supply_side", SUPPLY_Q, "doc_supply", SOCKET, independent=True)])
    with pytest.raises(ContractViolation, match="解析不到"):
        append_reading_record(record, directory=tmp_path, quotes=_quotes(SOCKET, supply_origin="Silicon Matter"))


def test_disproof_source_must_be_an_existing_reading_of_this_node(tmp_path) -> None:
    from alpha.providers.structure_readings import append_reading_record

    first = _v3()
    append_reading_record(first, directory=tmp_path, quotes=_quotes(SOCKET))
    with pytest.raises(ContractViolation, match="沒有這一份"):
        append_reading_record(_v3(disproof=_disproof(source="sr_0000000000000000"), created_at=NOW.replace(hour=5)),
                              directory=tmp_path, quotes=_quotes(SOCKET))
    carried = _v3(disproof=_disproof(source=first["reading_id"]), supersedes_id=first["reading_id"],
                  created_at=NOW.replace(hour=6))
    append_reading_record(carried, directory=tmp_path, quotes=_quotes(SOCKET))


# ---------------------------------------------------------------------------
# 消費端：單位不得讓讀圖安靜消失
# ---------------------------------------------------------------------------

def test_a_new_socket_reading_does_not_close_the_layer_readings_watches(tmp_path, monkeypatch) -> None:
    from alpha.providers import structure_readings as sr
    from engine_b import event_watch as ew

    monkeypatch.setattr(sr, "STRUCTURE_READING_DIR", tmp_path)
    layer = _v3(SOCKET, unit="layer")
    sr.append_reading_record(layer, quotes=_quotes(SOCKET))
    assert len(sr.register_reading_watches(layer)["registered"]) == 1
    socket = _v3(SOCKET, unit="socket", created_at=NOW.replace(hour=4))
    sr.append_reading_record(socket, quotes=_quotes(SOCKET))
    summary = sr.register_reading_watches(socket)
    assert summary["consumed"] == [], "新的插槽讀圖不得收掉層讀圖還在盯的條件"
    still = [w for w in ew.load_watches()["watches"]
             if str(w.get("source_ref", "")).startswith(f"reading:{layer['reading_id']}")]
    assert still and all(w["status"] == "active" for w in still)


def test_v3_disproof_is_counted_as_structured_not_as_v1_prose() -> None:
    """2026-09-25 前反證計數用 `endswith("/v2")` 判斷結構化——v3 會被誤算成 v1 散文、它的條件變成「未盯」。"""
    from engine_b import disproof

    reading = parse_structure_reading_record(_v3())
    counts = disproof.disproof_counts([], lifecycle={}, readings={(SOCKET, "socket"): reading})
    assert counts["v1_prose_readings"] == 0
    assert counts["unwatched"] == 1, "這份讀圖的一條反證還沒登記 watch——要算成未盯，不是散文"
