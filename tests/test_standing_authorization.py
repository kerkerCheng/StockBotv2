"""常規授權類別（config/standing_authorization.json＋engine_b/standing_authorization.py＋todo.standing_go）。

守三件事：①封閉性——每種 pq2 類型都必須被明確分到 authorized 或 never；②四個 authority gate 的類型
永遠在 never；③standing_go 只對「使用者本來會下 go」的項目動手：pending 的、等世界的、付費的都不碰。

⚠ **2026-09-22（Phase 0 Step 0a.1）：`decision_review` 從 authorized 搬到 never**——decision_lab
研究側整批退役（ROADMAP Phase 0／G3、G12）。本檔的斷言跟著**翻面**而不是刪掉：現在守的是
「standing-go 不再對 decision_review 動手」，所以有人把它加回 authorized 會變紅。
`authorized` 只剩 `source_trace_review` 一種。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine_b import standing_authorization as sa
from engine_b import todo


def test_shipped_config_is_closed_over_item_types_and_never_lists_the_gates() -> None:
    auth = sa.load()
    assert set(auth.authorized) | set(auth.never) == set(todo.ITEM_TYPES)
    assert not (set(auth.authorized) & set(auth.never))
    for gate_type in ("ra_admission", "engine_c_observation", "thesis_mutation"):
        assert gate_type in auth.never and not auth.is_authorized(gate_type)
    assert auth.is_authorized("source_trace_review")
    assert "付費" in auth.skip_hint_tokens("source_trace_review")
    # 2026-09-22 Step 0a.1：退役後唯一的 authorized 類型就是追源派回 pq1。
    assert set(auth.authorized) == {"source_trace_review"}
    assert not auth.is_authorized("decision_review")
    assert "退役" in (auth.why_never("decision_review") or "")


def test_loader_rejects_unclassified_or_overlapping_types(tmp_path: Path) -> None:
    base = json.loads(sa.DEFAULT_PATH.read_text(encoding="utf-8"))
    missing = dict(base)
    missing["never"] = {k: v for k, v in base["never"].items() if k != "manual"}
    p = tmp_path / "a.json"
    p.write_text(json.dumps(missing), encoding="utf-8")
    with pytest.raises(sa.StandingAuthorizationError, match="未分類"):
        sa.load(p)
    overlap = dict(base)
    # 用一個**現在確實在 authorized 裡**的 key 來製造交集；拿已經在 never 的 decision_review
    # 來試會驗不到任何東西（它本來就在那邊）。
    overlap["never"] = {**base["never"], "source_trace_review": "x"}
    p.write_text(json.dumps(overlap), encoding="utf-8")
    with pytest.raises(sa.StandingAuthorizationError, match="同時"):
        sa.load(p)
    with pytest.raises(sa.StandingAuthorizationError, match="不存在"):
        sa.load(tmp_path / "nope.json")


def _pool():
    pool = todo.empty_pool()
    todo.sync(pool, [
        {"type": "decision_review", "ref_id": "dc_go", "title": "A：補獨立來源"},
        {"type": "decision_review", "ref_id": "dc_deferred", "title": "B"},
        {"type": "decision_review", "ref_id": "dc_waiting", "title": "C"},
        {"type": "decision_review", "ref_id": "dc_inflight", "title": "D"},
        {"type": "source_trace_review", "ref_id": "lead_free", "title": "E 追原文", "hint": "go 只排入 bounded pq1"},
        {"type": "source_trace_review", "ref_id": "lead_paid", "title": "F Rosenblatt 券商報告",
         "hint": "若需付費，另核准 exact 金額／方案"},
        {"type": "ra_admission", "ref_id": "ra_x", "title": "G 入圖"},
        {"type": "manual", "ref_id": "m1", "title": "H"},
    ])
    by = {it["ref_id"]: it for it in todo.active_items(pool)}
    todo.resolve(pool, by["dc_deferred"]["n"], "pending")
    todo.resolve(pool, by["dc_waiting"]["n"], "pending", trigger="等 Q3 財報")
    by["dc_inflight"]["dispatch_status"] = "queued"
    return pool, by


class _StoreStub:
    def __init__(self, work_orders: dict[str, object] | None = None):
        self._wo = work_orders or {}

    def latest_research_work_order(self, cohort_id: str):
        return self._wo.get(cohort_id)


#: brief：dc_go 有需人決定的 blocker（go → assessment-gap 排入 pq1）；dc_stale_only 只剩 system_internal／awaiting_external
BRIEF = [
    {"cohort_id": "dc_go", "blockers": ["financial_resilience_corroboration_incomplete", "market_stale_since_decision"]},
    {"cohort_id": "dc_deferred", "blockers": ["financial_resilience_corroboration_incomplete"]},
    {"cohort_id": "dc_waiting", "blockers": ["financial_resilience_corroboration_incomplete"]},
    {"cohort_id": "dc_inflight", "blockers": ["financial_resilience_corroboration_incomplete"]},
    {"cohort_id": "dc_stale_only", "blockers": ["market_stale_since_decision", "execution_fx_missing"]},
]


def test_candidates_exclude_pending_waiting_inflight_paid_and_never_types() -> None:
    pool, by = _pool()
    todo.sync(pool, [{"type": "decision_review", "ref_id": "dc_stale_only", "title": "I"}])
    by = {it["ref_id"]: it for it in todo.active_items(pool)}
    candidates, skipped = todo.standing_go_candidates(
        pool, authorization=sa.load(), store=_StoreStub(), brief_items=BRIEF)
    # 2026-09-22 Step 0a.1：decision_review 已是 never 類型——**一個都不進候選**，
    # 連「有 work order」「有 user_decision blocker」那兩條放行路徑也不再走得到。
    assert [it["ref_id"] for it in candidates] == ["lead_free"]
    with_wo, _ = todo.standing_go_candidates(
        pool, authorization=sa.load(),
        store=_StoreStub({"dc_stale_only": {"work_order_id": "wo_1"}}), brief_items=BRIEF)
    assert [it["ref_id"] for it in with_wo] == ["lead_free"]
    # brief 讀不到也不影響：唯一的 authorized 類型不看 brief。
    none_brief, _ = todo.standing_go_candidates(
        pool, authorization=sa.load(), store=_StoreStub(), brief_items=None)
    assert [it["ref_id"] for it in none_brief] == ["lead_free"]
    reasons = {row["n"]: row["reason"] for row in skipped}
    assert "付費" in reasons[by["lead_paid"]["n"]]
    # never 類型不進 skipped——它們本來就不是候選，不是「被跳過」（與 ra_admission／manual 同形）。
    for ref in ("dc_go", "dc_deferred", "dc_waiting", "dc_inflight", "dc_stale_only", "ra_x", "m1"):
        assert by[ref]["n"] not in reasons, ref


def test_standing_go_runs_the_same_go_the_user_would_and_logs_it(monkeypatch) -> None:
    pool, by = _pool()
    calls: list[tuple] = []

    def fake_advance(p, n, *, store, at=None):
        calls.append(("decision", n))
        return {"outcome": "queued_assessment_gap"}

    def fake_dispatch(p, n, *, leads_path, at=None):
        calls.append(("trace", n))
        todo.get(p, n)["dispatch_ref"] = "lead:lead_free"
        return {"item": todo.get(p, n)}

    monkeypatch.setattr(todo, "advance_decision_review", fake_advance)
    monkeypatch.setattr(todo, "dispatch_source_trace_review", fake_dispatch)

    dry = todo.standing_go(pool, _StoreStub(), dry_run=True, brief_items=BRIEF)
    assert dry["dry_run"] and calls == []

    out = todo.standing_go(pool, _StoreStub(), at="2026-09-09T00:00:00+00:00", brief_items=BRIEF)
    # 2026-09-22 Step 0a.1：只剩追源那一條路；`advance_decision_review` **一次都不該被呼叫**
    # ——這是「退役真的生效了」的那個可證偽斷言，不是「rules 檔裡找不到某串字」。
    assert [(c[0]) for c in calls] == ["trace"]
    assert [row["outcome"] for row in out["done"]] == ["dispatched"]
    logs = [e for e in pool["log"] if e["verb"] == "standing_go"]
    assert {e["n"] for e in logs} == {by["lead_free"]["n"]}
    assert all("standing_authorization.json" in e["reason"] for e in logs)
    assert all(e["receipt"] for e in logs)
    # 沒動到 never 類型與使用者明示 pending 的項目
    assert todo.get(pool, by["ra_x"]["n"]).get("dispatch_status") is None
    assert todo.get(pool, by["dc_deferred"]["n"]).get("deferred_at")


def test_standing_go_reports_single_failures_without_stopping(monkeypatch) -> None:
    """一筆失敗不得讓其餘停下。

    ⚠ 2026-09-22 Step 0a.1：原本的失敗源是 `advance_decision_review`（decision_review 退役後
    永遠不會被呼叫，拿它當失敗源這條測試就恆綠＝零鑑別力）。改用兩筆追源項，其中一筆炸。
    """
    pool, by = _pool()
    todo.sync(pool, [{"type": "source_trace_review", "ref_id": "lead_free2",
                      "title": "J 追原文", "hint": "go 只排入 bounded pq1"}])
    by = {it["ref_id"]: it for it in todo.active_items(pool)}

    def dispatch(p, n, *, leads_path, at=None):
        if todo.get(p, n)["ref_id"] == "lead_free":
            raise RuntimeError("leads 檔壞了")
        return {"item": todo.get(p, n)}

    monkeypatch.setattr(todo, "dispatch_source_trace_review", dispatch)
    out = todo.standing_go(pool, _StoreStub(), brief_items=BRIEF)
    assert [row["n"] for row in out["failed"]] == [by["lead_free"]["n"]]
    assert [row["n"] for row in out["done"]] == [by["lead_free2"]["n"]]


# ---------------------------------------------------------------------------
# 開發改動的常規授權（2026-09-11）——**不以 pq2 item type 為 key**
# ---------------------------------------------------------------------------

def test_dev_change_is_not_keyed_by_item_types() -> None:
    """開發項不鑄號，所以 dev_change 不參與 ITEM_TYPES 封閉性檢查。

    把它塞進 `authorized` 會直接違反封閉性（config 列了 ITEM_TYPES 沒有的類型），
    那正是它必須另開一區的原因——carrier 仍是 ROADMAP（AGENTS.md 2026-08-31 未動）。
    """
    from engine_b.standing_authorization import load

    auth = load()
    assert "dev_change" not in auth.authorized
    assert "dev_change" not in auth.never
    assert auth.dev_change_conditions()          # 有內容
    assert auth.dev_change_never()


def test_dev_change_conditions_are_and_not_or() -> None:
    """四個條件全部成立才在範圍內。空集合等於無條件授權，載入就該失敗。"""
    import json

    from engine_b.standing_authorization import StandingAuthorizationError, load

    base = json.loads((_CONFIG := __import__("pathlib").Path(
        "config/standing_authorization.json")).read_text(encoding="utf-8"))
    assert set(base["dev_change"]["authorized_when_all"]) == {
        "reversible", "no_authority_write", "has_verification", "fix_level_declared"}

    import tempfile
    import pathlib as _p

    broken = dict(base)
    broken["dev_change"] = dict(base["dev_change"], authorized_when_all={})
    with tempfile.TemporaryDirectory() as d:
        path = _p.Path(d) / "sa.json"
        path.write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
        try:
            load(path)
        except StandingAuthorizationError as exc:
            assert "無條件授權" in str(exc)
        else:
            raise AssertionError("空的 authorized_when_all 必須拒絕載入")


def test_dev_change_never_covers_the_four_authority_gates_and_self_widening() -> None:
    """never 必須擋住 authority 寫入、不可逆、以及「改本檔」——授權範圍不得自我擴張。"""
    from engine_b.standing_authorization import load

    never = load().dev_change_never()
    for key in ("authority_write", "irreversible", "this_config",
                "agents_md_judgment", "roadmap_phase_step", "gate_widening"):
        assert key in never, f"dev_change.never 少了 {key}"
