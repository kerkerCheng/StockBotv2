"""反證登記 hook、`wake_reading`、計數、判定觸及後的等待（Phase 1 Step 1.5；G7、G8、C3／A5）。

守的機制：
- 讀圖 contract v2：moat／volume 必有反證；v1 照樣解析成 `disproof=()`、id 重算不變；v2 的 id 含反證。
- 讀圖寫入後的等待登記（冪等）：反證→語意 watch、需求側客戶→`wake_reading`、被取代／撤回的收掉、
  重讀完成收掉 fired 的重讀 watch 與讀圖來源的觸及。
- thesis 反證只由 `todo sync` 對帳登記：hash 用 generator 同一算法（CRLF 也對得上）、原地重產換條件、
  換 memo、retire、沒有結構化反證時不收手動登記、hash 不符不登記。
- 判定觸及 → 恰好一筆 `thesis_lifecycle`（理由合併、帶 watch_id）；go／drop 標 handled；同日再觸及再出一筆；
  等事件區的項目被叫回。
- 五個計數各有一個會變的 fixture。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from alpha.errors import ContractViolation
from alpha.structure_reading.contracts import (
    RECORD_VERSION, RECORD_VERSION_V1, new_reading_id, parse_structure_reading_record, structure_reading_record,
)
from engine_b import disproof
from engine_b import event_watch as ew
from thesis.memo_structure import disproof_items, memo_file_sha256, memo_text_sha256

SIVERS = "co:sivers_semiconductors"
NOW = datetime(2026, 9, 24, 8, 0, tzinfo=timezone.utc)
LATER = date(2026, 12, 31)
DISPROOF = [{"condition": "任一需求側客戶在正式文件宣布改用不經這個節點的替代路徑並量產",
             "entities": [SIVERS], "check_frequency": "每季財報後", "action_48h": "重讀這個節點並決定是否改寫"}]


def _structure(customers=("co:nvidia",)):
    return {"result_digest": "d" * 16,
            "angles": {"demand_side": [{"src": c, "relation": "USES", "dst": "tech:cw_dfb_laser"} for c in customers]},
            "anchor_chain": []}


def _reading(**kw):
    params = dict(node="tech:cw_dfb_laser", structure=_structure(), kind="volume",
                  reading="供給側大家差不多，賭的是產能一時補不上——需求側繞不過。", expires=LATER,
                  created_at=NOW, author="test", disproof=DISPROOF)
    params.update(kw)
    return structure_reading_record(**params)


# ---------------------------------------------------------------------------
# v2 contract
# ---------------------------------------------------------------------------

def test_v2_requires_disproof_for_bets_and_v1_parses_unchanged() -> None:
    with pytest.raises(ContractViolation):
        _reading(disproof=None)
    assert _reading(kind="undecided", disproof=None)["record_version"] == RECORD_VERSION
    v1 = {k: v for k, v in _reading().items() if k not in ("disproof", "reading_id")}
    v1["record_version"] = RECORD_VERSION_V1
    v1["reading_id"] = new_reading_id(v1)
    parsed = parse_structure_reading_record(v1)
    assert parsed.disproof == () and parsed.record_version == RECORD_VERSION_V1
    body_without_disproof = {k: v1.get(k) for k in ("node", "result_digest", "kind", "reading", "created_at",
                                                     "author", "expires", "tickers", "supersedes_id", "retracted")}
    import hashlib

    canonical = json.dumps(body_without_disproof, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    assert v1["reading_id"] == "sr_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16], \
        "v1 的 id 算法一個字不能動（既有 8 筆紀錄要重算得回來）"


def test_two_v2_readings_differing_only_in_disproof_get_different_ids() -> None:
    other = [dict(DISPROOF[0], condition="另一條：某客戶正式文件宣布第二家量產供應商通過認證")]
    assert _reading()["reading_id"] != _reading(disproof=other)["reading_id"]


# ---------------------------------------------------------------------------
# 讀圖寫入後的等待登記
# ---------------------------------------------------------------------------

def test_reading_registration_is_idempotent_and_supersede_or_retract_closes_the_old(tmp_path) -> None:
    from alpha.providers.structure_readings import register_reading_watches

    first = _reading()
    s1 = register_reading_watches(first)
    assert len(s1["registered"]) == 1 and len(s1["reread_registered"]) == 1
    assert register_reading_watches(first)["registered"] == [], "重跑不得重複登記"
    data = ew.load_watches()
    semantic = next(w for w in data["watches"] if w["kind"] == ew.SEMANTIC_KIND)
    assert semantic["source_ref"] == f"reading:{first['reading_id']}#1" and semantic["expires"] == LATER.isoformat()
    reread = next(w for w in data["watches"] if w.get("wake_reading"))
    assert reread["kind"] == "entity_filing_signal" and reread["entities"] == ["co:nvidia"]
    # fired 的重讀 watch＋讀圖來源的觸及——下一份讀圖（重讀完成）收掉它們
    reread["status"] = "fired"
    semantic["judgment"] = {"touches": "yes", "handled": None}
    semantic["status"] = "consumed"
    ew.save_watches(data)
    second = _reading(supersedes_id=first["reading_id"],
                      disproof=[dict(DISPROOF[0], condition="新讀法的反證：某客戶宣布自製這一層並量產出貨")])
    s2 = register_reading_watches(second)
    assert s2["reread_consumed"] == [reread["watch_id"]] and s2["touched_handled"] == [semantic["watch_id"]]
    third = _reading(supersedes_id=second["reading_id"], retracted=True, disproof=None, created_at=NOW + timedelta(hours=1))
    s3 = register_reading_watches(third)
    assert len(s3["consumed"]) == 1 and s3["registered"] == []


def test_reread_reasons_name_the_customer_and_the_touched_condition() -> None:
    from alpha.providers.structure_readings import reread_reasons

    watches = [
        {"wake_reading": "tech:x", "status": "fired", "entities": ["co:nvidia"],
         "woken_by": {"lead_id": "L9", "shared_entities": ["co:nvidia"]}},
        {"kind": ew.SEMANTIC_KIND, "node": "tech:x", "source_ref": "reading:sr_1#1", "status": "consumed",
         "condition": "客戶宣布自製這一層", "judgment": {"touches": "yes", "handled": None}},
        {"kind": ew.SEMANTIC_KIND, "node": "tech:x", "source_ref": "reading:sr_1#2", "status": "consumed",
         "condition": "已處置的不算", "judgment": {"touches": "yes", "handled": {"verb": "reread"}}},
    ]
    reasons = reread_reasons("tech:x", watches)
    assert reasons == ["客戶 co:nvidia 出了新文件 L9", "反證被判觸及：客戶宣布自製這一層"]


def test_wake_reading_is_a_first_class_target() -> None:
    from engine_b import queue_segments as qs

    data = {"schema_version": 1, "watches": []}
    watch = ew.add_watch(data, kind="entity_filing_signal", wake_reading="tech:x", expires="2027-01-01",
                         entities=["co:nvidia"])
    assert ew.wake_target(watch)["kind"] == "reading"
    assert qs.classify_watch(dict(watch, status="fired")) == "fired_reading_reread"
    with pytest.raises(ew.EventWatchError):
        ew.add_watch(data, kind="related_entity_signal", wake_reading="tech:x", expires="2027-01-01",
                     entities=["co:nvidia"])


# ---------------------------------------------------------------------------
# memo：hash 與「推翻」那一節
# ---------------------------------------------------------------------------

AXT_STYLE = "# memo\n\n## 7. 什麼會推翻這個 thesis\n\n- 第一條條件寫在這裡足夠二十個字以上\n- 第二條\n\n### 7b 補充\n\n- 不算\n"
SIVERS_STYLE = "# memo\n\n## 6. 什麼會推翻 thesis\n\n1. 第一條\n2. 第二條\n3. 第三條\n\n## 7. 接下來\n- 不算\n"


def test_disproof_items_stop_at_any_heading_and_accept_both_list_styles() -> None:
    assert len(disproof_items(AXT_STYLE)) == 2
    assert disproof_items(SIVERS_STYLE) == ["第一條", "第二條", "第三條"]
    assert disproof_items("# memo\n沒有那一節\n") == []


def test_disproof_items_join_indented_continuation_lines() -> None:
    """AXT §7 第 2 條跨兩行（Phase 1 Step 1.6 實測）：只取第一行會把條件截斷。"""
    text = ("## 7. 什麼會推翻這個 thesis\n\n- 條款 → 「防禦性鎖客」\n  的解讀被推翻，議價權解讀成立。\n"
            "- second item wraps\n  onto a new line\n\n  not part of any item\n- 第三條\n")
    assert disproof_items(text) == ["條款 → 「防禦性鎖客」的解讀被推翻，議價權解讀成立。",
                                    "second item wraps onto a new line", "第三條"]
    axt = (Path(__file__).resolve().parents[1] / "thesis" / "axt_inp_v1_lane_memo.md").read_text(encoding="utf-8")
    assert disproof_items(axt)[1].endswith("「防禦性鎖客」的解讀被推翻，議價權解讀成立。")


def test_memo_hash_matches_the_generator_under_crlf_and_detects_real_edits(tmp_path) -> None:
    lf = "# memo\nline\n"
    memo = tmp_path / "m.md"
    memo.write_bytes(lf.replace("\n", "\r\n").encode("utf-8"))
    assert memo_file_sha256(memo) == memo_text_sha256(lf), "CRLF 存檔、LF 文字算的 sidecar 必須判相符"
    memo.write_bytes("# memo\nline changed\n".encode("utf-8"))
    assert memo_file_sha256(memo) != memo_text_sha256(lf)
    source = (Path(__file__).resolve().parents[1] / "thesis" / "generate_lane_memo.py").read_text(encoding="utf-8")
    assert '"memo_sha256": memo_text_sha256(full_output)' in source, "generator 與對帳必須呼叫同一個函式"


def test_generator_requires_structured_disproof_matching_the_section() -> None:
    from thesis.generate_lane_memo import _structured_disproof

    cond = {"condition": "第一條條件寫在這裡足夠二十個字以上", "entities": [SIVERS],
            "check_frequency": "每季", "action_48h": "重讀"}
    envelope = {"memo_markdown": AXT_STYLE}
    assert "缺 disproof_conditions" in _structured_disproof(envelope)[1]
    assert "必須相等" in _structured_disproof({**envelope, "disproof_conditions": [cond]})[1]
    bad = dict(cond, condition="不在那一節裡的文字")
    assert "原文" in _structured_disproof({**envelope, "disproof_conditions": [cond, bad]})[1]
    ok = dict(cond, condition="第二條")
    out, error = _structured_disproof({**envelope, "disproof_conditions": [cond, ok]})
    assert error is None and len(out) == 2


# ---------------------------------------------------------------------------
# thesis 對帳
# ---------------------------------------------------------------------------

def _thesis_env(tmp_path, *, conditions, memo_name="x_v1_lane_memo.md", section=None, status="active",
                corrupt=False):
    memo_text = section or "# memo\n\n## 6. 什麼會推翻這個 thesis\n\n" + "".join(f"- {c}\n" for c in conditions)
    memo = tmp_path / "thesis" / memo_name
    memo.parent.mkdir(parents=True, exist_ok=True)
    memo.write_bytes(memo_text.replace("\n", "\r\n").encode("utf-8"))           # working tree 是 CRLF
    sidecar = {"memo_sha256": memo_text_sha256(memo_text + ("x" if corrupt else "")),
               "disproof_conditions": [{"condition": c, "entities": [SIVERS], "check_frequency": "每季",
                                        "action_48h": "重讀 thesis"} for c in conditions]}
    memo.with_suffix(".evidence.json").write_text(json.dumps(sidecar, ensure_ascii=False), encoding="utf-8")
    return {"x": {"status": status, "memo": f"thesis/{memo_name}", "check_interval_days": 90,
                  "last_checked": "2026-09-01", "next_check": "2099-01-01"}}


C1 = "Sivers 期中報告揭露 CW DFB 雷射陣列進入量產並具名客戶"
C2 = "任一 hyperscaler 在正式文件宣布改用不經外部雷射的整合方案"
C2B = "任一 hyperscaler 在正式文件宣布第二家外部雷射供應商通過認證"


def test_reconcile_registers_once_and_handles_in_place_regeneration(tmp_path) -> None:
    data = {"schema_version": 1, "watches": []}
    life = _thesis_env(tmp_path, conditions=[C1, C2])
    s1 = disproof.reconcile_thesis_disproof(data, lifecycle=life, root=tmp_path, today=date(2026, 9, 24))
    assert len(s1["registered"]) == 2
    assert disproof.reconcile_thesis_disproof(data, lifecycle=life, root=tmp_path)["registered"] == []
    # 原地重產：同路徑、第 2 條換了
    life = _thesis_env(tmp_path, conditions=[C1, C2B])
    s2 = disproof.reconcile_thesis_disproof(data, lifecycle=life, root=tmp_path, today=date(2026, 9, 24))
    assert len(s2["registered"]) == 1 and len(s2["consumed"]) == 1
    active = {w["condition"] for w in data["watches"] if w["status"] == "active"}
    assert active == {C1, C2B}


def test_reconcile_follows_memo_switch_and_retire(tmp_path) -> None:
    data = {"schema_version": 1, "watches": []}
    disproof.reconcile_thesis_disproof(data, lifecycle=_thesis_env(tmp_path, conditions=[C1]), root=tmp_path,
                                       today=date(2026, 9, 24))
    life2 = _thesis_env(tmp_path, conditions=[C2], memo_name="x_v2_lane_memo.md")
    s = disproof.reconcile_thesis_disproof(data, lifecycle=life2, root=tmp_path, today=date(2026, 9, 24))
    assert len(s["registered"]) == 1 and len(s["consumed"]) == 1
    closed = next(w for w in data["watches"] if w["status"] == "consumed")
    assert "superseded" in closed["closed"]["note"]
    life2["x"]["status"] = "retired"
    s = disproof.reconcile_thesis_disproof(data, lifecycle=life2, root=tmp_path)
    assert all(w["status"] == "consumed" for w in data["watches"])
    assert any(w["closed"]["note"] == "thesis retired" for w in data["watches"])


def test_hash_mismatch_is_not_registered_and_manual_ones_survive_without_structured(tmp_path) -> None:
    data = {"schema_version": 1, "watches": []}
    life = _thesis_env(tmp_path, conditions=[C1], corrupt=True)
    s = disproof.reconcile_thesis_disproof(data, lifecycle=life, root=tmp_path)
    assert s["sidecar_mismatch"] == ["x"] and s["registered"] == []
    # 沒有結構化反證的現行 memo：手動登記（Step 1.6）不得被收掉
    memo = tmp_path / "thesis" / "x_v1_lane_memo.md"
    memo.with_suffix(".evidence.json").write_text(json.dumps({"memo_sha256": "x"}), encoding="utf-8")
    ew.add_watch(data, kind=ew.SEMANTIC_KIND, disproof_ref="thesis:thesis/x_v1_lane_memo.md#1",
                 source_ref="thesis:thesis/x_v1_lane_memo.md#1", expires="2027-06-30", entities=[SIVERS],
                 condition=C1, check_frequency="每季", action_48h="重讀", today=date(2026, 9, 24))
    s = disproof.reconcile_thesis_disproof(data, lifecycle=life, root=tmp_path)
    assert s["no_structured"] == ["x"] and s["consumed"] == [] and data["watches"][0]["status"] == "active"


# ---------------------------------------------------------------------------
# 判定觸及後的等待（C3）
# ---------------------------------------------------------------------------

def _touched_setup(tmp_path, monkeypatch, *, due=False):
    from crons import thesis_freshness_check as tfc

    life = _thesis_env(tmp_path, conditions=[C1])
    if due:
        life["x"]["status"] = "review_required"
    lifecycle_path = tmp_path / "lifecycle.json"
    lifecycle_path.write_text(json.dumps(life, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(tfc, "LIFECYCLE", lifecycle_path)
    data = ew.load_watches()
    watch = ew.add_watch(data, kind=ew.SEMANTIC_KIND, disproof_ref="thesis:thesis/x_v1_lane_memo.md#1",
                         source_ref="thesis:thesis/x_v1_lane_memo.md#1", expires="2027-06-30", entities=[SIVERS],
                         condition=C1, check_frequency="每季", action_48h="重讀 thesis 並決定 revise",
                         today=date(2026, 9, 24))
    watch["status"] = "fired"
    watch["woken_by"] = {"lead_id": "L1"}
    ew.judge(data, watch["watch_id"], touches=True, note="量產了", quote="entered volume production")
    ew.save_watches(data)
    return watch["watch_id"]


def _sync(monkeypatch):
    from engine_b import todo

    pool = {"items": [], "log": [], "next_n": 1}
    monkeypatch.setattr(todo, "SOURCE_COLLECTORS", (("lifecycle", "_collect_lifecycle_rows"),))
    return todo, pool


def test_touch_yields_exactly_one_lifecycle_item_and_go_marks_it_handled(tmp_path, monkeypatch) -> None:
    watch_id = _touched_setup(tmp_path, monkeypatch)
    todo, pool = _sync(monkeypatch)
    rows = todo._collect_lifecycle_rows()
    assert len(rows) == 1 and rows[0]["disproof_watch_ids"] == [watch_id]
    assert "反證被判觸及" in rows[0]["title"] and "48 小時動作" in rows[0]["title"]
    todo.sync(pool, rows)
    item = pool["items"][0]
    assert item["disproof_watch_ids"] == [watch_id]
    todo.resolve(pool, item["n"], "drop", reason="已複查")
    handled = next(w for w in ew.load_watches()["watches"] if w["watch_id"] == watch_id)["judgment"]["handled"]
    assert handled["verb"] == "drop" and handled["n"] == item["n"]
    assert todo._collect_lifecycle_rows() == [], "處置過的觸及不再出項目"


def test_schedule_due_and_touch_merge_into_one_row(tmp_path, monkeypatch) -> None:
    _touched_setup(tmp_path, monkeypatch, due=True)
    todo, _pool = _sync(monkeypatch)
    rows = todo._collect_lifecycle_rows()
    assert len(rows) == 1 and "；" in rows[0]["title"]


def test_same_day_second_touch_after_handling_opens_a_new_item(tmp_path, monkeypatch) -> None:
    first = _touched_setup(tmp_path, monkeypatch)
    todo, pool = _sync(monkeypatch)
    todo.sync(pool, todo._collect_lifecycle_rows())
    todo.resolve(pool, pool["items"][0]["n"], "drop", reason="已複查")
    data = ew.load_watches()
    second = ew.add_watch(data, kind=ew.SEMANTIC_KIND, disproof_ref="thesis:thesis/x_v1_lane_memo.md#1",
                          source_ref="thesis:thesis/x_v1_lane_memo.md#1", expires="2027-06-30", entities=[SIVERS],
                          condition=C1 + "（再一次）", check_frequency="每季", action_48h="重讀",
                          today=date(2026, 9, 24))
    second["status"] = "fired"
    second["woken_by"] = {"lead_id": "L2"}
    ew.judge(data, second["watch_id"], touches=True, note="又觸及", quote="again")
    ew.save_watches(data)
    rows = todo._collect_lifecycle_rows()
    assert rows and rows[0]["disproof_watch_ids"] == [second["watch_id"]] and first not in rows[0]["disproof_watch_ids"]
    todo.sync(pool, rows)
    open_items = [i for i in pool["items"] if not i.get("resolved_at")]
    assert len(open_items) == 1


def test_new_touch_pulls_an_item_out_of_the_waiting_area(tmp_path, monkeypatch) -> None:
    watch_id = _touched_setup(tmp_path, monkeypatch)
    todo, pool = _sync(monkeypatch)
    todo.sync(pool, [{"type": "thesis_lifecycle", "ref_id": "x", "title": "thesis x：到期", "source": "lifecycle"}])
    todo.resolve(pool, pool["items"][0]["n"], "pending", trigger="等 Q3 財報")
    assert pool["items"][0].get("waiting_on")
    todo.sync(pool, todo._collect_lifecycle_rows())
    assert not pool["items"][0].get("waiting_on")
    assert pool["log"][-1]["verb"] == "disproof_touch" and watch_id in pool["log"][-1]["reason"]


# ---------------------------------------------------------------------------
# 計數
# ---------------------------------------------------------------------------

class _Reading:
    def __init__(self, rid, n, version=RECORD_VERSION):
        self.reading_id = rid
        self.disproof = tuple(range(n))
        self.record_version = version


def test_five_counts_each_move(tmp_path) -> None:
    life = _thesis_env(tmp_path, conditions=[C1, C2])
    readings = {"tech:a": _Reading("sr_a", 1), "tech:b": _Reading("sr_b", 0, version=RECORD_VERSION_V1)}
    watches: list[dict] = []
    base = disproof.disproof_counts(watches, lifecycle=life, readings=readings, root=tmp_path,
                                    coverage=frozenset({SIVERS}), frozen_history=3)
    assert base["expected"] == 3 and base["unwatched"] == 3 and base["v1_prose_readings"] == 1
    assert base["frozen_history"] == 3 and base["watching"] == 0
    watches.append({"kind": ew.SEMANTIC_KIND, "status": "active", "source_ref": "thesis:thesis/x_v1_lane_memo.md#1",
                    "entities": [SIVERS]})
    watches.append({"kind": ew.SEMANTIC_KIND, "status": "active", "source_ref": "reading:sr_a#1",
                    "entities": ["co:jx_advanced_metals"]})
    watches.append({"kind": ew.SEMANTIC_KIND, "status": "consumed", "source_ref": "thesis:thesis/x_v1_lane_memo.md#2",
                    "judgment": {"touches": "yes", "handled": None}})
    c = disproof.disproof_counts(watches, lifecycle=life, readings=readings, root=tmp_path,
                                 coverage=frozenset({SIVERS}))
    assert (c["watching"], c["unreachable"], c["touched_pending"], c["unwatched"]) == (2, 1, 1, 0)
    assert disproof.disproof_counts(watches, lifecycle=life, readings=readings, root=tmp_path)["unreachable"] is None
