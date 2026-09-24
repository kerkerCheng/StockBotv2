"""Phase 1 Step 1.10：稽核改讀新的等待 registry——每條新判準一個會紅的 fixture（空跑檢查）。

資料源一律 monkeypatch `audit.sources` 的 loader，memo／sidecar 寫在 tmp（`checks.ROOT` 指過去）；
不讀真檔、不寫任何東西。真實資料上的結果由 `python -m audit invariants` 驗（plan §11 L11-6 ④）。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from audit import checks, sources
from audit.sources import SourceUnavailable

NOW = datetime.now(timezone.utc)
TODAY = NOW.date()
FUTURE = (TODAY + timedelta(days=60)).isoformat()
PAST = (TODAY - timedelta(days=5)).isoformat()
MEMO = "thesis/x_memo.md"
COND_1 = "客戶端 10-K 列出第二家 InP 基板供應商，且其份額在一年內超過三成"
COND_2 = "公司自己的季報毛利率連續兩季跌破 35%，且管理層把原因歸給價格而非產品組合"
READING_COND = "需求側客戶在法定文件裡具名第二家 CW DFB 雷射供應商並揭露採購份額"


def _ago(**delta: float) -> str:
    return (NOW - timedelta(**delta)).isoformat()


def _watch(wid: str, **fields) -> dict:
    base = {"watch_id": wid, "kind": "entity_filing_signal", "status": "active", "expires": FUTURE,
            "entities": ["co:x"], "created_at": _ago(days=30)}
    base.update(fields)
    return base


def _thesis_watch(wid: str, index: int = 1, condition: str = COND_1, memo: str = MEMO, **fields) -> dict:
    ref = f"thesis:{memo}#{index}"
    return _watch(wid, kind="semantic_condition", condition=condition, source_ref=ref, disproof_ref=ref, **fields)


def _reading_watch(wid: str, reading_id: str = "sr_new", node: str = "tech:laser", **fields) -> dict:
    ref = f"reading:{reading_id}#1"
    return _watch(wid, kind="semantic_condition", condition=READING_COND, source_ref=ref, disproof_ref=ref,
                  node=node, **fields)


def _expired(watch: dict, *, days: float = 2) -> dict:
    watch.update(status="expired", expires=PAST, expired_at=_ago(days=days))
    return watch


def _reading(reading_id: str, *conditions: str) -> SimpleNamespace:
    return SimpleNamespace(reading_id=reading_id,
                           disproof=tuple(SimpleNamespace(condition=c) for c in conditions))


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch, tmp_path):
    state: dict = {"items": [], "watches": [], "leads": {}, "hypotheses": [],
                   "lifecycle": {"x": {"memo": MEMO, "status": "active", "check_interval_days": 90}},
                   "ledgers": {}}

    def lifecycle():
        if state["lifecycle"] is None:
            raise SourceUnavailable("thesis/lifecycle.json 不存在")
        return state["lifecycle"]

    def ledgers():
        if state["ledgers"] is None:
            raise SourceUnavailable("讀圖 ledger 未掛載")
        return state["ledgers"]

    monkeypatch.setattr(sources, "todo_items", lambda: state["items"])
    monkeypatch.setattr(sources, "event_watches", lambda: state["watches"])
    monkeypatch.setattr(sources, "leads", lambda: state["leads"])
    monkeypatch.setattr(sources, "hypotheses", lambda: state["hypotheses"])
    monkeypatch.setattr(sources, "thesis_lifecycle", lifecycle)
    monkeypatch.setattr(sources, "reading_ledgers", ledgers)
    monkeypatch.setattr(checks, "ROOT", tmp_path)
    (tmp_path / "thesis").mkdir()
    (tmp_path / MEMO).write_text(f"# x\n\n## 什麼會推翻它\n\n- {COND_1}\n- {COND_2}\n", encoding="utf-8")
    state["root"] = tmp_path
    return state


def _item(n: int, type_: str = "manual", **fields) -> dict:
    return {"n": n, "type": type_, "ref_id": f"{type_}:{n}", "title": "t", **fields}


def _findings(result) -> str:
    return "\n".join(result.findings)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_lifecycle_no_longer_reads_the_frozen_decision_store(world, monkeypatch) -> None:
    """凍結資料恆 PASS＝不會滅（L14-4）：拿掉之後，舊店打不開也不影響這條的判定。"""

    def boom():
        raise AssertionError("Lifecycle 不該再開舊 Decision Store")

    monkeypatch.setattr(sources, "decision_store", boom)
    world["watches"] = [_watch("ew_a")]
    world["items"] = [_item(1)]
    assert checks.check_lifecycle().status.name == "PASS"


@pytest.mark.parametrize("watch,needle", [
    (_watch("ew_bad", status="retired"), "不在封閉字彙"),
    (_watch("ew_bad", status="fired"), "fired 卻沒有 woken_by"),
    (_watch("ew_bad", status="expired"), "expired 卻沒有 expired_at"),
    (_watch("ew_bad", status="consumed"), "consumed 卻沒有任何收據"),
    (_watch("ew_bad", status="expired", expired_at=_ago(days=1), expiry_resolution={"kind": "gone"}), "不在封閉字彙裡"),
    (_watch("ew_bad", expiry_resolution={"kind": "dropped"}), "active 卻帶到期處置"),
    (_watch("ew_bad", status="consumed", woken_by={"at": _ago(days=1)},
            expiry_resolution={"kind": "dropped"}), "只有 touched"),
])
def test_watch_state_and_receipts_must_agree(world, watch, needle) -> None:
    world["watches"] = [watch]
    result = checks.check_lifecycle()
    assert result.status.name == "FAIL"
    assert needle in _findings(result)


def test_legitimate_watch_states_pass_lifecycle(world) -> None:
    """研究結論＝觸及的兩條合法路徑：假設型停在 fired、語意型 consumed，都帶 touched。"""
    world["watches"] = [
        _watch("ew_a"),
        _watch("ew_b", status="fired", woken_by={"kind": "watch_decision", "at": _ago(days=1)},
               expiry_resolution={"kind": "touched"}),
        _thesis_watch("ew_c", status="consumed", judgment={"touches": "yes"}, expiry_resolution={"kind": "touched"}),
        _watch("ew_d", status="consumed", closed={"kind": "pq2_item_gone"}),
        _expired(_watch("ew_e"), days=3) | {"expiry_resolution": {"kind": "dropped"}},
    ]
    assert checks.check_lifecycle().status.name == "PASS"


# ---------------------------------------------------------------------------
# Expiry（A7：到期之後有沒有去處）
# ---------------------------------------------------------------------------


def test_thesis_condition_expired_must_be_listed_in_an_open_review(world) -> None:
    world["watches"] = [_expired(_thesis_watch("ew_t"))]
    world["items"] = [_item(7, "thesis_lifecycle", disproof_watch_ids=["ew_t"], resolution="drop",
                            resolved_at=_ago(days=1))]
    result = checks.check_expiry()
    assert result.status.name == "FAIL" and "沒有列進任何未結案 thesis 複查" in _findings(result)

    world["items"] = [_item(8, "thesis_lifecycle", disproof_watch_ids=["ew_t"])]
    assert checks.check_expiry().status.name == "PASS"


def test_expiry_within_one_day_is_still_in_the_sync_window(world) -> None:
    world["watches"] = [_expired(_thesis_watch("ew_t"), days=0.5)]
    assert checks.check_expiry().status.name == "PASS"


def test_unreadable_lifecycle_is_unchecked_not_a_verdict(world) -> None:
    world["lifecycle"] = None
    world["watches"] = [_expired(_thesis_watch("ew_t"))]
    result = checks.check_expiry()
    assert result.status.name == "PASS"
    assert "沒檢查去處" in _findings(result)


def test_reading_condition_expired_must_show_up_in_the_node_reread_reasons(world) -> None:
    world["watches"] = [_expired(_reading_watch("ew_r"))]
    world["ledgers"] = {"tech:laser": {"records": [], "errors": [], "current": _reading("sr_new", READING_COND)}}
    assert checks.check_expiry().status.name == "PASS"

    world["ledgers"] = {"tech:laser": {"records": [], "errors": [], "current": None}}
    result = checks.check_expiry()
    assert result.status.name == "FAIL" and "沒有現行讀圖" in _findings(result)

    world["watches"] = [_expired(_reading_watch("ew_r", node=""))]
    assert "沒寫 node" in _findings(checks.check_expiry())


def test_hypothesis_expiry_needs_an_open_watch_decision_or_a_resolution(world) -> None:
    watch = _expired(_watch("ew_h", kind="fact_verification", hypothesis_ref="hy_1", fact="ASP 大漲"))
    world["watches"] = [watch]
    result = checks.check_expiry()
    assert result.status.name == "FAIL" and "watch_decision" in _findings(result)

    world["items"] = [_item(9, "watch_decision", ref_id=f"ew_h@{PAST}")]
    assert checks.check_expiry().status.name == "PASS"

    world["items"] = []
    watch["expiry_resolution"] = {"kind": "dropped"}
    assert checks.check_expiry().status.name == "PASS"


def test_pq2_expiry_that_left_the_item_waiting_is_caught(world) -> None:
    world["watches"] = [_expired(_watch("ew_p", wake_pq2=5), days=3) | {"expiry_resolution": {"kind": "requeued_to_pq2"}}]
    world["items"] = [_item(5, waiting_on={"trigger": "x", "set_at": _ago(days=10)})]
    result = checks.check_expiry()
    assert result.status.name == "FAIL" and "仍掛在等待" in _findings(result)

    # 使用者在到期**之後**自己又 pending → 合法（同 `_check_event_watches` 的冪等規則）
    world["items"] = [_item(5, waiting_on={"trigger": "x", "set_at": _ago(days=1), "until": FUTURE})]
    assert checks.check_expiry().status.name == "PASS"


def test_mechanical_expiry_left_unresolved_means_the_sync_did_not_run(world) -> None:
    world["watches"] = [_expired(_watch("ew_l", wake_lead="lead_1"))]
    result = checks.check_expiry()
    assert result.status.name == "FAIL" and "處置沒跑" in _findings(result)


def test_active_watch_two_days_past_expiry_is_caught(world) -> None:
    world["watches"] = [_watch("ew_a", expires=PAST)]
    result = checks.check_expiry()
    assert result.status.name == "FAIL" and "mark_expired" in _findings(result)

    world["watches"] = [_watch("ew_a", expires=(TODAY - timedelta(days=1)).isoformat())]
    assert checks.check_expiry().status.name == "PASS"


def test_pq2_waiting_on_until_passed_is_caught(world) -> None:
    world["items"] = [_item(3, waiting_on={"until": PAST, "set_at": _ago(days=40)})]
    result = checks.check_expiry()
    assert result.status.name == "FAIL" and "日期已過仍掛在「等事件」" in _findings(result)


def test_pq2_waiting_without_expiry_or_watch_is_an_inv2_violation(world) -> None:
    """`pending --trigger` 不帶 `--until`、也沒有 watch 會叫醒它＝永遠不會被重問（2026-09-24 真實資料 [586]）。"""
    world["items"] = [_item(4, waiting_on={"until": None, "trigger": "客戶端文件具名", "set_at": _ago(days=7)})]
    result = checks.check_expiry()
    assert result.status.name == "FAIL" and "永遠不會被重問" in _findings(result)

    world["watches"] = [_watch("ew_w", wake_pq2=4)]
    assert checks.check_expiry().status.name == "PASS"


# ---------------------------------------------------------------------------
# Orphans
# ---------------------------------------------------------------------------


def test_watch_waking_a_resolved_pq2_item_is_an_orphan(world) -> None:
    """NB2-12：6 筆 pq2 型 watch 指向 2026-09-22 已 drop 的 decision_review。"""
    world["watches"] = [_watch("ew_p", wake_pq2=200)]
    world["items"] = [_item(200, resolution="drop", resolved_at=_ago(days=2))]
    result = checks.check_orphans()
    assert result.status.name == "FAIL" and "卻已 drop" in _findings(result)

    world["watches"] = [_watch("ew_p", wake_pq2=200, hypothesis_ref="hy_1")]   # 還有第二個喚醒目標
    assert checks.check_orphans().status.name == "PASS"
    world["watches"] = [_watch("ew_p", wake_pq2=200, status="consumed", woken_by={"at": _ago(days=1)})]
    assert checks.check_orphans().status.name == "PASS"


def test_watch_requeueing_a_closed_or_missing_lead_is_an_orphan(world) -> None:
    world["watches"] = [_watch("ew_l", wake_lead="lead_1")]
    world["leads"] = {"lead_1": {"status": "applied"}}
    assert "卻已 applied" in _findings(checks.check_orphans())
    world["leads"] = {}
    assert "不存在" in _findings(checks.check_orphans())
    world["leads"] = {"lead_1": {"status": "parked"}}
    assert checks.check_orphans().status.name == "PASS"


def test_disproof_ref_must_point_at_its_own_memo_item(world) -> None:
    world["watches"] = [_thesis_watch("ew_t", index=3)]
    assert "對不到它的條件" in _findings(checks.check_orphans())
    world["watches"] = [_thesis_watch("ew_t", index=2)]            # 位置在、文字不是它
    assert "對不到它的條件" in _findings(checks.check_orphans())
    world["watches"] = [_thesis_watch("ew_t", memo="thesis/gone.md")]
    world["lifecycle"]["y"] = {"memo": "thesis/gone.md", "status": "active"}
    assert "讀不到的 memo" in _findings(checks.check_orphans())
    world["watches"] = [_thesis_watch("ew_t", index=1)]
    assert checks.check_orphans().status.name == "PASS"


def test_waiting_condition_on_a_non_current_memo_is_an_orphan(world) -> None:
    """X2：換版後舊 memo 檔還在，「指向不存在」抓不到——要比對 lifecycle 的現行 memo。"""
    world["lifecycle"] = {"x": {"memo": "thesis/x_v2.md", "status": "active"}}
    world["watches"] = [_thesis_watch("ew_t")]
    result = checks.check_orphans()
    assert result.status.name == "FAIL" and "不是 lifecycle 的現行 memo" in _findings(result)


def test_condition_missing_from_a_structured_sidecar_is_an_orphan(world) -> None:
    """N4-12：memo 原地重產、hash 相符的 sidecar 沒有這條 → 舊條件沒收。"""
    from thesis.memo_structure import memo_file_sha256

    root = world["root"]
    sidecar = root / "thesis" / "x_memo.evidence.json"
    sidecar.write_text(json.dumps({"memo_sha256": memo_file_sha256(root / MEMO),
                                   "disproof_conditions": [{"condition": COND_2}]}), encoding="utf-8")
    world["watches"] = [_thesis_watch("ew_t")]
    result = checks.check_orphans()
    assert result.status.name == "FAIL" and "sidecar" in _findings(result)

    # sidecar 沒有結構化反證 → 不適用（1.6 手動登記的合法地不在任何 sidecar 裡）
    sidecar.write_text(json.dumps({"memo_sha256": memo_file_sha256(root / MEMO)}), encoding="utf-8")
    assert checks.check_orphans().status.name == "PASS"


def test_reading_disproof_ref_must_resolve_to_the_current_reading(world) -> None:
    old, new = _reading("sr_old", READING_COND), _reading("sr_new", READING_COND)
    world["ledgers"] = {"tech:laser": {"records": [old, new], "errors": [], "current": new}}
    world["watches"] = [_reading_watch("ew_r", reading_id="sr_gone")]
    assert "ledger 裡沒有這一份" in _findings(checks.check_orphans())
    world["watches"] = [_reading_watch("ew_r", reading_id="sr_old")]
    assert "不是 tech:laser 的現行讀圖" in _findings(checks.check_orphans())
    world["watches"] = [_reading_watch("ew_r", reading_id="sr_new")]
    assert checks.check_orphans().status.name == "PASS"


def test_wake_reading_on_a_node_without_a_current_reading_is_an_orphan(world) -> None:
    world["watches"] = [_watch("ew_w", wake_reading="mat:inp")]
    world["ledgers"] = {}
    assert "沒有現行讀圖" in _findings(checks.check_orphans())
    world["ledgers"] = {"mat:inp": {"records": [], "errors": [], "current": _reading("sr_1")}}
    assert checks.check_orphans().status.name == "PASS"


# ---------------------------------------------------------------------------
# QueueLiveness
# ---------------------------------------------------------------------------


def test_fired_semantic_watch_left_unjudged_is_stalled(world) -> None:
    world["watches"] = [_thesis_watch("ew_t", status="fired", woken_by={"at": _ago(days=20)})]
    result = checks.check_queue_liveness()
    assert result.status.name == "FAIL" and "還沒判定" in _findings(result)
    world["watches"] = [_thesis_watch("ew_t", status="fired", woken_by={"at": _ago(days=3)})]
    assert checks.check_queue_liveness().status.name == "PASS"


def test_watch_decision_pointing_at_a_missing_watch_is_stalled(world) -> None:
    world["items"] = [_item(11, "watch_decision", ref_id=f"ew_gone@{PAST}")]
    result = checks.check_queue_liveness()
    assert result.status.name == "FAIL" and "指向不存在的 watch ew_gone" in _findings(result)


def test_touched_thesis_condition_must_be_caught_by_an_open_review_within_48h(world) -> None:
    """C3 的接點：判定觸及、未處置，48 小時後池裡沒有一筆未結案複查接住它 → 等待消失。"""
    touched = {"touches": "yes", "handled": None, "at": _ago(hours=60)}
    world["watches"] = [_thesis_watch("ew_t", status="consumed", judgment=touched)]
    result = checks.check_queue_liveness()
    assert result.status.name == "FAIL" and "觸及後的等待消失了" in _findings(result)

    world["items"] = [_item(12, "thesis_lifecycle", disproof_watch_ids=["ew_t"])]
    assert checks.check_queue_liveness().status.name == "PASS"

    world["items"] = []
    world["watches"] = [_thesis_watch("ew_t", status="consumed", judgment={**touched, "at": _ago(hours=10)})]
    assert checks.check_queue_liveness().status.name == "PASS"


# ---------------------------------------------------------------------------
# 源頭：`todo sync` 收掉喚醒目標已結案的 watch（NB2-12）
# ---------------------------------------------------------------------------


def test_sync_closes_waits_whose_only_consumer_is_gone() -> None:
    from engine_b import event_watch as ew
    from engine_b import todo

    data = {"watches": [
        _watch("ew_p", wake_pq2=200),                              # 編號已 drop → 收
        _watch("ew_open", wake_pq2=201),                           # 編號還開著 → 不動
        _watch("ew_missing", wake_pq2=999),                        # 編號不存在 → 不動（資料錯，audit 現形）
        _watch("ew_two", wake_pq2=200, hypothesis_ref="hy_1"),     # 還有第二個喚醒目標 → 不動
        _watch("ew_l", wake_lead="lead_done"),                     # lead applied → 收
        _watch("ew_lp", wake_lead="lead_parked"),                  # lead 還在 park → 不動
    ]}
    pool = {"items": [_item(200, resolution="drop", resolved_at=_ago(days=2)), _item(201)]}
    leads = {"lead_done": {"status": "applied"}, "lead_parked": {"status": "parked"}}
    closed = todo._close_orphaned_waits(data, pool, leads)
    assert sorted(closed) == ["ew_l", "ew_p"]
    by_id = {w["watch_id"]: w for w in data["watches"]}
    assert by_id["ew_p"]["status"] == "consumed" and by_id["ew_p"]["closed"]["kind"] == "pq2_item_gone"
    assert by_id["ew_l"]["closed"]["kind"] == "lead_closed"
    assert all(by_id[w]["status"] == "active" for w in ("ew_open", "ew_missing", "ew_two", "ew_lp"))

    # leads 讀不到（None）≠ 空：整個不動追源型
    data2 = {"watches": [_watch("ew_l", wake_lead="lead_done")]}
    assert todo._close_orphaned_waits(data2, pool, None) == []

    with pytest.raises(ew.EventWatchError):
        ew.close_orphan(data, "ew_open", kind="whatever", note="x")
