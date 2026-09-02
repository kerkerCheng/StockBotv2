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


def test_wake_target_exactly_one_of_three():
    data = _fresh()
    with pytest.raises(ew.EventWatchError):
        ew.add_watch(data, kind="date", wake_pq2=1, expires="2027-01-01",
                     until="2026-09-01", hypothesis_ref="hy_x")
    with pytest.raises(ew.EventWatchError):
        # 三選一：lead 與 pq2 同時給也不行
        ew.add_watch(data, kind="date", wake_pq2=1, expires="2027-01-01",
                     until="2026-09-01", wake_lead="lead_x")
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


# --- [321] trace 引擎併入：related_entity_signal ＋ wake_lead ---


def test_related_entity_signal_fires_on_any_tier_unlike_filing_signal():
    """related_entity_signal 等的是「同一標的有新動靜」，不限一手來源。"""
    data = _fresh()
    w = ew.add_watch(
        data, kind="related_entity_signal", wake_lead="lead_parked",
        expires="2027-01-01", entities=["co:coherent"],
        created_at="2026-09-01T00:00:00+00:00",
    )
    leads = {"l1": _lead(tier=3, entities=["co:coherent"])}
    fired = ew.check_watches(data, leads=leads, today=date(2026, 9, 2))
    assert len(fired) == 1
    assert fired[0]["woken_by"]["wake_lead"] == "lead_parked"
    # 觸發後標的進 consumed——同一檔的第二則轉述不再重排 pq1
    assert w["consumed_entities"] == ["CO:COHERENT"]


def test_consumed_entities_block_repeat_but_expires_still_surfaces():
    """核心修法：標的用完只是停滯，不是死亡——到期仍會現形。"""
    data = _fresh()
    ew.add_watch(
        data, kind="related_entity_signal", wake_lead="lead_x",
        expires="2026-12-01", entities=["co:nvidia"],
        consumed_entities=["CO:NVIDIA"],
        created_at="2026-09-01T00:00:00+00:00",
    )
    # 標的已消化 → 被動層不再觸發
    leads = {"l1": _lead(entities=["co:nvidia"])}
    assert ew.check_watches(data, leads=leads, today=date(2026, 9, 2)) == []
    # 但它有名字、有計數器（[321] 前這個狀態沒有名字，靜默沉底）
    assert ew.is_stalled(data["watches"][0]) is True
    assert ew.counters(data)["stalled"] == 1
    # 到期後強制現形，不會無聲躺著
    ew.check_watches(data, leads=leads, today=date(2026, 12, 2))
    assert data["watches"][0]["status"] == "expired"


def test_new_entity_still_wakes_stalled_related_watch():
    """只擋同一標的的第二次，不擋新標的。"""
    data = _fresh()
    ew.add_watch(
        data, kind="related_entity_signal", wake_lead="lead_x",
        expires="2027-01-01", entities=["co:nvidia", "co:coherent"],
        consumed_entities=["CO:NVIDIA"],
        created_at="2026-09-01T00:00:00+00:00",
    )
    leads = {"l1": _lead(tier=3, entities=["co:coherent"])}
    fired = ew.check_watches(data, leads=leads, today=date(2026, 9, 2))
    assert fired and fired[0]["woken_by"]["shared_entities"] == ["co:coherent"]


def test_reactivate_keeps_lead_watch_waiting():
    """lead 型喚醒後回 active 續等——那份原文可能要等好幾輪才出現。"""
    data = _fresh()
    w = ew.add_watch(
        data, kind="related_entity_signal", wake_lead="lead_x",
        expires="2027-01-01", entities=["co:axt"],
        created_at="2026-09-01T00:00:00+00:00",
    )
    ew.check_watches(data, leads={"l1": _lead(tier=3, entities=["co:axt"])},
                     today=date(2026, 9, 2))
    assert w["status"] == "fired"
    ew.reactivate(data, w["watch_id"])
    assert w["status"] == "active"
    assert w["consumed_entities"] == ["CO:AXT"]


def test_primary_source_tier_has_single_ssot():
    """[321]：tier-1 判準不得再各寫一份（L16）。"""
    from engine_b import lead_refs, leads as leads_mod

    assert ew.PRIMARY_SOURCE_TIER is lead_refs.PRIMARY_SOURCE_TIER
    assert leads_mod.PRIMARY_SOURCE_TIER is lead_refs.PRIMARY_SOURCE_TIER


def test_render_watch_covers_every_kind_and_wake_target():
    """2026-09-02 事故：[321] 新增 related_entity_signal 後 _render_watch 的平行
    dict 沒跟上，daily sweep 整批 KeyError、38 筆 watch 一輪 0 檢查（L16）。
    本測試對 WATCH_KINDS 全集逐一 render——新增 kind 漏補條目時在這裡先炸。"""
    data = _fresh()
    ew.add_watch(data, kind="date", wake_pq2=1, expires="2027-01-01", until="2026-10-01")
    ew.add_watch(
        data, kind="entity_filing_signal", wake_pq2=2,
        expires="2027-01-01", entities=["NVDA"],
    )
    ew.add_watch(
        data, kind="fact_verification", wake_pq2=3,
        expires="2027-01-01", fact="x", fact_check_ref="lead_1", entities=["AMD"],
    )
    ew.add_watch(
        data, kind="related_entity_signal", wake_lead="lead_2",
        expires="2027-01-01", entities=["COHR"],
    )
    rendered_kinds = set()
    for watch in data["watches"]:
        line = ew._render_watch(watch)
        assert "未知 kind" not in line, f"{watch['kind']} 缺 render 條目"
        rendered_kinds.add(watch["kind"])
    assert rendered_kinds == set(ew.WATCH_KINDS)
    lead_line = ew._render_watch(data["watches"][-1])
    assert "lead lead_2" in lead_line
