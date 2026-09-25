"""結構讀圖紀錄（Q5，2026-09-17）：append-only ledger ＋ staleness 分級 ＋ 心跳接線。

設計見 `docs/brainstorms/2026-09-17-structural-reading-layer.md` §5b／§6b。這份測試守五件：

1. **存輸入不存結論**：快照必須來自 `query.structure`，手組的一律拒收——
   手組的偵測不了「多了一條我當初沒讀到的邊」，而那正是這本 ledger 存在的理由。
2. **分級不是 binary**：供給側多一家是 `high`（進 pq1），只有 evidence 變是 `low`（不進）。
   ⚠ binary 的 stale 會恆亮，而恆亮＝零鑑別力（L14-4）。
3. **`documents` 不製造工作**：它是研究量的函數，多讀一份文件不得觸發重讀。
4. **每個等待都有到期**（INV-2）：`expires` 必填、且到期即使圖沒變也要 `expired`。
5. **producer 指得出 consumer**（INV-4）：該重讀的數字落在 `stale_structure_readings` 段，
   並且出現在心跳上——偵測到 stale 卻沒有人去重讀，計數器只會愈長愈大（L13）。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from alpha.errors import ContractViolation
from alpha.providers.structure_readings import (
    append_reading_record, known_nodes, ledger_path, read_reading_records,
)
from alpha.structure_reading import (
    READING_KINDS, needs_reread, reading_status, select_reading, structure_reading_record,
)
from engine_b import queue_segments as qs
from webapp.structure_readings import build_structure_readings_artifact

NODE = "tech:cw_dfb_laser"
NOW = datetime(2026, 9, 17, 3, 0, tzinfo=timezone.utc)
TODAY = date(2026, 9, 17)
LATER = TODAY + timedelta(days=90)


def _edge(src, dst="tech:cw_dfb_laser", relation="supplies_to", sub=2, sole=False,
          qual="qualified", evidence="company_disclosure", documents=1):
    return {"src": src, "relation": relation, "dst": dst, "substitutability": sub,
            "sole_source": sole, "qualification_status": qual, "evidence": evidence,
            "documents": documents}


def _structure(*, supply=("co:a", "co:b"), demand=("tech:cpo",), digest="d0", anchor=("tech:ai_switch",),
               supply_sub=2, evidence="company_disclosure"):
    return {
        "node": NODE,
        "angles": {
            "supply_side": [_edge(s, sub=supply_sub, evidence=evidence) for s in supply],
            "demand_side": [_edge(d, relation="depends_on", sub=5) for d in demand],
            "next_layer": [], "counter_path": [],
        },
        "anchor_chain": list(anchor),
        "result_digest": digest,
    }


#: v2（Phase 1 Step 1.5）：moat／volume 讀法必須寫下至少一條反證。
DISPROOF = [{"condition": "任一需求側客戶在正式文件宣布改用不經這個節點的替代路徑並量產",
             "entities": ["co:sivers_semiconductors"], "check_frequency": "每季財報後",
             "action_48h": "重讀這個節點並決定是否改寫讀法", "source": "self"}]

#: v3（Phase 2 Step 2.3）：moat／volume 兩半各一段引用；`QUOTES` 是「同一份快照」的逐字，append 時核對。
DEMAND_QUOTE = "CPO switch 的每一個光引擎都需要外部 CW 雷射光源，沒有替代設計"
SUPPLY_QUOTE = "我們出貨 CW DFB 雷射給多家 CPO 客戶，產能正在擴充中"
CITATIONS = [
    {"angle": "demand_side", "edge": ["tech:cpo", "depends_on", NODE], "quote": DEMAND_QUOTE, "source_id": "doc_demand"},
    {"angle": "supply_side", "edge": ["co:a", "supplies_to", NODE], "quote": SUPPLY_QUOTE, "source_id": "doc_supply"},
]
QUOTES = {
    ("tech:cpo", "depends_on", NODE): [{"quote": DEMAND_QUOTE, "doc": "doc_demand", "origin": "Someone Else"}],
    ("co:a", "supplies_to", NODE): [{"quote": SUPPLY_QUOTE, "doc": "doc_supply", "origin": "A Corp"}],
}


def _record(**kw):
    params = dict(node=NODE, structure=_structure(), kind="volume", unit="layer",
                  reading="供給側兩家的 substitutability 都是 2，沒有人明顯高於其他——需求側繞不過但供給端誰都不獨佔。",
                  expires=LATER, created_at=NOW, author="test", disproof=DISPROOF, citations=CITATIONS)
    params.update(kw)
    return structure_reading_record(**params)


# ---------------------------------------------------------------------------
# ledger：存輸入、必須有到期、append-only
# ---------------------------------------------------------------------------

def test_a_snapshot_must_come_from_query_structure() -> None:
    """手組的快照偵測不了「多了一條我當初沒讀到的邊」——沒有 digest 就不是快照。"""
    with pytest.raises(ContractViolation, match="result_digest"):
        _record(structure={"angles": {}, "anchor_chain": []})


def test_a_reading_without_an_expiry_is_rejected() -> None:
    """INV-2：每個等待都必須有到期。到期日不得早於或等於寫下的那天。"""
    with pytest.raises(ContractViolation, match="expires"):
        _record(expires=TODAY)
    with pytest.raises(ContractViolation, match="expires"):
        _record(expires=TODAY - timedelta(days=1))


def test_kind_is_a_closed_vocabulary_declared_by_the_writer() -> None:
    """A/B 判準表**不得被寫成程式自動分類**（設計 §3）——這裡只驗字彙，不看 angles 推 kind。"""
    with pytest.raises(ContractViolation, match="未登記"):
        _record(kind="probably_a_moat")
    assert set(READING_KINDS) == {"moat", "volume", "neither", "undecided"}


def test_a_reading_must_say_why() -> None:
    with pytest.raises(ContractViolation, match="太短"):
        _record(reading="B 型")


def test_append_only_rules(tmp_path: Path) -> None:
    record = _record()
    append_reading_record(record, directory=tmp_path, quotes=QUOTES)
    with pytest.raises(ContractViolation, match="已在 ledger"):
        append_reading_record(record, directory=tmp_path, quotes=QUOTES)
    with pytest.raises(ContractViolation, match="supersedes_id"):
        append_reading_record(_record(kind="moat", supersedes_id="sr_nonexistent"), directory=tmp_path, quotes=QUOTES)


def test_retraction_removes_the_current_reading(tmp_path: Path) -> None:
    first = _record()
    append_reading_record(first, directory=tmp_path, quotes=QUOTES)
    append_reading_record(_record(created_at=NOW + timedelta(hours=1), retracted=True,
                                  supersedes_id=first["reading_id"]), directory=tmp_path)
    records, errors = read_reading_records(NODE, directory=tmp_path)
    assert len(records) == 2 and not errors, "撤回是 append 一筆，舊行永不改寫（L10）"
    assert select_reading(records, unit="layer", today=TODAY) is None


def test_broken_lines_are_reported_not_silently_dropped(tmp_path: Path) -> None:
    append_reading_record(_record(), directory=tmp_path, quotes=QUOTES)
    with ledger_path(NODE, directory=tmp_path).open("a", encoding="utf-8") as handle:
        handle.write('{"node": "x", "kind": "volume"}\n')
    records, errors = read_reading_records(NODE, directory=tmp_path)
    assert len(records) == 1 and len(errors) == 1, "壞行要現形（INV-3）"


def test_node_id_is_safe_as_a_filename() -> None:
    """`tech:cw_dfb_laser` 直接當檔名在 Windows 上會被當成 NTFS 資料流而靜默寫到別處。"""
    assert ":" not in ledger_path(NODE).name
    assert ledger_path(NODE).name == "tech_cw_dfb_laser.jsonl"


def test_known_nodes_reads_the_real_node_not_the_slug(tmp_path: Path) -> None:
    append_reading_record(_record(), directory=tmp_path, quotes=QUOTES)
    assert known_nodes(directory=tmp_path) == [NODE], "檔名是 slug，node 要從內容讀回來"


# ---------------------------------------------------------------------------
# staleness：分級（§6b ①）
# ---------------------------------------------------------------------------

def _status(after, *, today=TODAY, record=None):
    reading = record or _record()
    from alpha.structure_reading.contracts import parse_structure_reading_record
    return reading_status(parse_structure_reading_record(reading), after, today=today)


def test_nothing_changed_is_current() -> None:
    status = _status(_structure())
    assert status["status"] == "current" and not status["changes"]
    assert not needs_reread(status)


def test_one_more_supplier_is_high_grade_and_a_disproof_trigger() -> None:
    """供給側分布是 B（量的賭注）的核心判準，而「多一家」正是那個假設被推翻的樣子（§6b ④）。"""
    status = _status(_structure(supply=("co:a", "co:b", "co:new"), digest="d1"))
    assert status["status"] == "stale" and status["highest_grade"] == "high"
    assert needs_reread(status)
    kinds = {c["kind"] for c in status["changes"]}
    assert "supply_added" in kinds
    assert status["disproof_triggers"], "供給側多一家沒有被標成 disproof 觸發"


def test_counter_path_added_is_a_disproof_trigger_but_removed_is_not() -> None:
    """對稱面（Step 2.5 實測）：替代路線多一條是反證的樣子；少一條是它的反方向，不得同樣標成觸發。"""
    rival = _edge("tech:rival", dst=NODE, relation="competes_with", sub=None)
    with_rival = _structure(digest="d_rival")
    with_rival["angles"]["counter_path"] = [rival]

    added = _status(with_rival)
    assert {c["kind"] for c in added["changes"]} == {"counter_path"}
    assert added["disproof_triggers"], "反向路徑新增沒有被標成 disproof 觸發"

    removed = _status(_structure(digest="d_gone"), record=_record(structure=with_rival))
    assert {c["kind"] for c in removed["changes"]} == {"counter_path_removed"}
    assert removed["status"] == "stale", "反向路徑變了仍要重讀（normal），只是不是反證觸發"
    assert not removed["disproof_triggers"], "反向路徑消失被誤標成 disproof 觸發"


def test_only_evidence_changed_is_low_and_stays_out_of_the_queue() -> None:
    """記錄，但不優先——否則佇列會被 evidence 微調灌滿，而恆亮＝零鑑別力（L14-4）。"""
    status = _status(_structure(evidence="externally_corroborated", digest="d2"))
    assert status["status"] == "stale_low" and status["highest_grade"] == "low"
    assert not needs_reread(status), "stale_low 不得進 pq1"


def test_substitutability_change_on_the_supply_side_is_high() -> None:
    status = _status(_structure(supply_sub=4, digest="d3"))
    assert status["highest_grade"] == "high" and needs_reread(status)


def test_documents_count_never_reaches_this_layer() -> None:
    """`documents` 是研究量的函數——多讀一份文件不得製造工作（`AGENTS.md` 明列）。

    它在更上游就被擋掉了：`EdgeView.key()` 不含 documents，所以 digest 不會變。
    這裡驗的是**分級層也不看它**——兩道都在，才不會有人哪天把它加回 key 就靜默破功。
    """
    after = _structure()
    after["angles"]["supply_side"][0]["documents"] = 999
    status = _status(after)
    assert status["status"] == "current" and not status["changes"]


def test_an_expired_reading_is_expired_even_when_the_graph_did_not_move() -> None:
    """INV-2：到期就是到期。圖沒變不表示那份判讀還能用——世界會變，圖只是我們知道的部分。"""
    status = _status(_structure(), today=LATER + timedelta(days=1))
    assert status["status"] == "expired" and needs_reread(status)


def test_not_reading_the_graph_is_not_current() -> None:
    """「這次沒查」與「查過沒變」不得同形（L13-2）。"""
    status = _status(None)
    assert status["status"] is None and "沒有讀到圖" in status["reason"]


def test_digest_moved_but_nothing_found_says_so() -> None:
    """digest 變了卻找不出差異＝比對欄位與 digest 欄位不同步。安靜回 current 會讓機制失效。"""
    status = _status(_structure(digest="moved"))
    assert status["reason"] and "不同步" in status["reason"]


def test_anchor_reachability_change_is_graded() -> None:
    status = _status(_structure(anchor=(), digest="d4"))
    assert any(c["kind"] == "anchor" for c in status["changes"])


# ---------------------------------------------------------------------------
# artifact 與 consumer（INV-4）
# ---------------------------------------------------------------------------

def test_artifact_counts_every_status_and_points_at_its_consumer() -> None:
    rows = [{"node": "a", "status": "current", "reading_id": "sr_1", "needs_reread": False},
            {"node": "b", "status": "stale", "reading_id": "sr_2", "needs_reread": True,
             "disproof_triggers": [{"kind": "supply_added"}]}]
    payload = build_structure_readings_artifact(rows=rows)
    assert payload["counts"] == {"current": 1, "stale": 1, "stale_low": 0, "expired": 0, "unknown": 0}
    assert payload["needs_reread"]["n"] == 1 and payload["needs_reread"]["nodes"] == ["b"]
    # plan 待決 #13（Step 2.7）：給命令用的結構化 {node, unit}——標籤帶［socket］，拿標籤跑 --check 會找不到。
    assert payload["needs_reread"]["items"] == [{"node": "b", "unit": None}]
    assert payload["disproof_triggers"]["items"] == [{"node": "b", "unit": None}]
    # Step 2.6：圖那一側住 `graph_holes`（走圖第 4 型）、watch 那一側住 `fired_reading_reread`——兩段都得指得出來。
    assert "graph_holes" in payload["needs_reread"]["segment"]
    assert "fired_reading_reread" in payload["needs_reread"]["segment"]
    for key in ("graph_holes", "fired_reading_reread"):
        assert key in qs.SEGMENT_BY_KEY, key
    assert payload["needs_reread"]["consumer"], "producer 必須指得出 consumer（INV-4）"
    assert payload["disproof_triggers"]["n"] == 1


def test_the_segment_is_registered_with_a_consumer() -> None:
    # Step 2.6：`stale_structure_readings` 併進 `graph_holes`（走圖第 4 型 `reading_stale`）。
    segment = qs.SEGMENT_BY_KEY["graph_holes"]
    assert segment.consumer, "沒有 consumer 的段就是黑洞"
    assert segment.cost == "research"
    observation = qs.observe(graph_holes=3)
    counts = {s["key"]: s["count"] for s in observation["segments"]}
    assert counts["graph_holes"] == 3
    # 沒注入時是 None（本次沒讀到那個 authority），**不是 0**（INV-3）
    assert {s["key"]: s["count"] for s in qs.observe()["segments"]}["graph_holes"] is None
    from query.graph_walk import QUESTION_TYPE_KEYS

    assert "reading_stale" in QUESTION_TYPE_KEYS


def test_artifact_is_json_serialisable_and_has_the_required_state_fields() -> None:
    from webapp.contracts import STATE_KINDS, STATE_REQUIRED_FIELDS

    assert "structure_readings" in STATE_KINDS
    payload = build_structure_readings_artifact(rows=[])
    json.dumps(payload, ensure_ascii=False)
    for field in STATE_REQUIRED_FIELDS:
        assert field in payload, field


# ---------------------------------------------------------------------------
# 心跳：讓它不可能安靜腐壞（§5b）
# ---------------------------------------------------------------------------

def test_heartbeat_prints_the_reread_backlog(tmp_path: Path) -> None:
    from crons import heartbeat as hb
    from webapp.store import StateArtifactStore

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    rows = [{"node": NODE, "status": "stale", "reading_id": "sr_1", "needs_reread": True,
             "disproof_triggers": [{"kind": "supply_added", "grade": "high", "angle": "supply_side",
                                    "detail": "新增 1 條", "disproof_trigger": True}]}]
    StateArtifactStore(state_dir).write(build_structure_readings_artifact(rows=rows))
    text = "\n".join(hb.build_changes(now=datetime.now(timezone.utc), state_dir=state_dir,
                                      thesis_path=tmp_path / "missing.json").lines)
    assert "該重讀 1" in text, text
    assert NODE in text, "要指出是哪個節點，重新推理時才有焦點"
    assert "disproof" in text.lower() or "觸發" in text


def test_heartbeat_says_when_no_reading_exists_yet(tmp_path: Path) -> None:
    """一份都還沒寫**不是** 0 份 stale——那會讓「沒東西要重讀」與「還沒開始用」同形。"""
    from crons import heartbeat as hb
    from webapp.store import StateArtifactStore

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    StateArtifactStore(state_dir).write(build_structure_readings_artifact(rows=[]))
    text = "\n".join(hb.build_changes(now=datetime.now(timezone.utc), state_dir=state_dir,
                                      thesis_path=tmp_path / "missing.json").lines)
    assert "一份都還沒寫" in text


def test_heartbeat_does_not_take_out_its_neighbours_when_readings_are_missing(tmp_path: Path) -> None:
    from crons import heartbeat as hb

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    section = hb.build_changes(now=datetime.now(timezone.utc), state_dir=state_dir,
                               thesis_path=tmp_path / "missing.json")
    text = "\n".join(section.lines)
    assert "結構讀圖：" in text and "watch：今日醒" in text and "beta" in text   # 1.8：watch 行改讀 registry
