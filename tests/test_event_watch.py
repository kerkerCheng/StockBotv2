"""Event Watch 模組測試（docs/brainstorms/2026-08-31-event-watch-module-requirements.md）。"""

from datetime import date

import pytest

from engine_b import event_watch as ew


def _fresh():
    return {"schema_version": 1, "watches": []}


def test_add_watch_closed_vocab():
    data = _fresh()
    with pytest.raises(ew.EventWatchError):
        ew.add_watch(data, kind="vibes", wake_pq2=1, expires="2027-01-01")
    with pytest.raises(ew.EventWatchError):
        ew.add_watch(data, kind="date", wake_pq2=1, expires="2027-01-01")  # 缺 until
    with pytest.raises(ew.EventWatchError):
        ew.add_watch(data, kind="entity_filing_signal", wake_pq2=1, expires="2027-01-01")
    with pytest.raises(ew.EventWatchError):
        # expires 必填——無限期等待會腐爛
        ew.add_watch(data, kind="date", wake_pq2=1, expires="", until="2026-09-01")


def test_t1_date_fires_on_due():
    data = _fresh()
    ew.add_watch(data, kind="date", wake_pq2=81, expires="2026-12-31", until="2026-09-01")
    assert ew.check_watches(data, today=date(2026, 8, 31)) == []
    fired = ew.check_watches(data, today=date(2026, 9, 1))
    assert len(fired) == 1 and fired[0]["wake_pq2"] == 81
    assert data["watches"][0]["status"] == "fired"


def test_expired_watch_archives_without_firing():
    data = _fresh()
    ew.add_watch(data, kind="date", wake_pq2=1, expires="2026-09-01", until="2026-08-01")
    fired = ew.check_watches(data, today=date(2026, 9, 2))
    assert fired == []
    assert data["watches"][0]["status"] == "expired"


def _lead(decision="go", tier=1, decided="2026-09-02T00:00:00+00:00", entities=None):
    return {
        "triage": {"decision": decision, "tier": tier, "decided_at": decided},
        "entities": {"company_ids": list(entities or []), "tickers": []},
        "first_seen": decided,
        "title": "",
    }


def test_t0_entity_filing_fires_only_on_new_primary_lead():
    data = _fresh()
    watch = ew.add_watch(
        data, kind="entity_filing_signal", wake_pq2=200,
        expires="2027-03-31", entities=["co:agility_robotics"],
    )
    watch["created_at"] = "2026-09-01T00:00:00+00:00"
    # tier 3 不觸發（等的是一手文件，不是任何提及）
    leads = {"l1": _lead(tier=3, entities=["co:agility_robotics"])}
    assert ew.check_watches(data, leads=leads, today=date(2026, 9, 2)) == []
    # watch 建立前的舊 lead 不觸發
    leads = {"l2": _lead(decided="2026-08-30T00:00:00+00:00", entities=["co:agility_robotics"])}
    assert ew.check_watches(data, leads=leads, today=date(2026, 9, 2)) == []
    # 建立後的 tier-1 具名 lead 觸發
    leads = {"l3": _lead(entities=["co:agility_robotics"])}
    fired = ew.check_watches(data, leads=leads, today=date(2026, 9, 2))
    assert len(fired) == 1
    assert fired[0]["woken_by"]["lead_id"] == "l3"


def test_sweep_budget_zero_degrades_to_passive(monkeypatch, tmp_path):
    data = _fresh()
    watch = ew.add_watch(
        data, kind="entity_filing_signal", wake_pq2=1, expires="2027-01-01",
        entities=["co:x"], poll_eligible=True,
    )
    monkeypatch.setattr(ew, "load_config", lambda: {
        "enabled": True, "sweep_budget_per_run": 0, "min_recheck_days": 3,
    })
    assert ew.sweep_due(data) == []
    monkeypatch.setattr(ew, "load_config", lambda: {
        "enabled": True, "sweep_budget_per_run": 2, "min_recheck_days": 3,
    })
    due = ew.sweep_due(data, today=date(2026, 9, 10))
    assert [w["watch_id"] for w in due] == [watch["watch_id"]]
    # min_recheck_days 生效
    ew.mark_checked(data, watch["watch_id"], today=date(2026, 9, 10))
    assert ew.sweep_due(data, today=date(2026, 9, 11)) == []
    assert len(ew.sweep_due(data, today=date(2026, 9, 14))) == 1


def test_counters_shape():
    data = _fresh()
    ew.add_watch(data, kind="date", wake_pq2=1, expires="2027-01-01", until="2026-09-01")
    ew.add_watch(
        data, kind="fact_verification", wake_pq2=2, expires="2027-01-01",
        entities=["AAOI"], fact="x", poll_eligible=True,
    )
    c = ew.counters(data)
    assert c["active"] == 2 and c["t1_date"] == 1 and c["t0_passive"] == 1
    assert c["t2_pollable"] == 1


def test_wake_target_exactly_one_of_pq2_or_hypothesis():
    data = _fresh()
    with pytest.raises(ew.EventWatchError):
        ew.add_watch(data, kind="date", wake_pq2=1, expires="2027-01-01",
                     until="2026-09-01", hypothesis_ref="hy_x")
    with pytest.raises(ew.EventWatchError):
        ew.add_watch(data, kind="date", expires="2027-01-01", until="2026-09-01")
    w = ew.add_watch(
        data, kind="fact_verification", expires="2027-01-01",
        entities=["AXTI"], fact="ASP 上調", hypothesis_ref="hy_0001",
    )
    assert w["wake_pq2"] is None and w["hypothesis_ref"] == "hy_0001"
    # 觸發後 woken_by 帶 hypothesis_ref＋fact
    w["created_at"] = "2026-09-01T00:00:00+00:00"
    leads = {"l1": _lead(entities=[], decided="2026-09-02T00:00:00+00:00")}
    leads["l1"]["entities"]["tickers"] = ["AXTI"]
    fired = ew.check_watches(data, leads=leads, today=date(2026, 9, 2))
    assert fired and fired[0]["woken_by"]["hypothesis_ref"] == "hy_0001"
    assert fired[0]["woken_by"]["fact"] == "ASP 上調"
    ew.consume_fired(data, w["watch_id"])
    assert data["watches"][0]["status"] == "consumed"
