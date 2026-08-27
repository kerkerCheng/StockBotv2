"""engine_b.cli：leads 狀態機的命令列入口。"""
from __future__ import annotations

import json
from pathlib import Path

from engine_b import cli, leads


PASS_CLASSIFICATION_ARGS = [
    "--content-type", "structural_fact",
    "--decision-impact", "ranking",
]
PASS_CLASSIFICATION = {
    "content_type": "structural_fact",
    "decision_impact": "ranking",
}


def _seed(path: Path) -> str:
    store = leads.empty_store()
    lead_id, _ = leads.register(store, source="edgar:COHR",
                                url="https://x.io/1", title="COHR 8-K")
    leads.save(store, path)
    return lead_id


def test_register_is_url_idempotent(tmp_path, capsys) -> None:
    path = tmp_path / "pending_leads.json"
    args = [
        "--leads", str(path), "register",
        "--source", "weekly:sivers",
        "--url", "https://example.com/sivers",
        "--title", "Sivers insider transactions",
        "--published-at", "2026-07-21",
    ]

    assert cli.main(args) == 0
    first = capsys.readouterr().out.strip()
    assert first.endswith("new")
    assert cli.main(args) == 0
    second = capsys.readouterr().out.strip()
    assert second.endswith("existing")
    assert len(leads.load(path)["leads"]) == 1


def test_triage_then_advance_round_trip(tmp_path, capsys) -> None:
    path = tmp_path / "pending_leads.json"
    lead_id = _seed(path)

    assert cli.main(["--leads", str(path), "triage", lead_id,
                     "--go", "--tier", "2", "--reason", "有新角度",
                     *PASS_CLASSIFICATION_ARGS]) == 0
    assert cli.main(["--leads", str(path), "advance", lead_id, "researching"]) == 0

    store = leads.load(path)
    assert store["leads"][lead_id]["status"] == "researching"
    assert store["leads"][lead_id]["triage"]["decision"] == "go"
    classification = store["leads"][lead_id]["triage"]["classification"]
    assert classification["content_type"] == "structural_fact"
    assert classification["decision_impact"] == "ranking"
    assert classification["classified_by"] == "triage_semantic_v1"
    assert classification["reason"] == "有新角度"


def test_triage_pass_requires_structured_classification(tmp_path, capsys) -> None:
    path = tmp_path / "pending_leads.json"
    lead_id = _seed(path)

    assert cli.main([
        "--leads", str(path), "triage", lead_id,
        "--go", "--tier", "2", "--reason", "有新角度",
    ]) == 1
    assert leads.load(path)["leads"][lead_id]["status"] == "pending"
    assert "PASS 必須同時指定" in capsys.readouterr().err


def test_capital_commitment_requires_payment_direction(tmp_path, capsys) -> None:
    path = tmp_path / "pending_leads.json"
    lead_id = _seed(path)

    assert cli.main([
        "--leads", str(path), "triage", lead_id,
        "--go", "--tier", "2", "--reason", "長約",
        "--content-type", "capital_commitment",
        "--decision-impact", "candidate_set",
    ]) == 1
    assert leads.load(path)["leads"][lead_id]["status"] == "pending"
    assert "payment_direction" in capsys.readouterr().err


def test_illegal_advance_returns_nonzero_and_does_not_persist(tmp_path) -> None:
    path = tmp_path / "pending_leads.json"
    lead_id = _seed(path)

    # pending 不能直接 applied
    assert cli.main(["--leads", str(path), "advance", lead_id, "applied"]) == 1
    assert leads.load(path)["leads"][lead_id]["status"] == "pending"


def test_list_status_filter_and_counts(tmp_path, capsys) -> None:
    path = tmp_path / "pending_leads.json"
    lead_id = _seed(path)
    cli.main(["--leads", str(path), "triage", lead_id,
              "--no-go", "--tier", "4", "--reason", "純社群猜測"])
    capsys.readouterr()  # flush triage 的成功訊息

    cli.main(["--leads", str(path), "counts"])
    counts = json.loads(capsys.readouterr().out.strip())
    assert counts == {"triaged_no_go": 1}

    assert cli.main(["--leads", str(path), "list", "--status", "pending", "--json"]) == 0
    assert json.loads(capsys.readouterr().out.strip()) == []


def test_harvest_health_only_lists_latest_unresolved_failures(tmp_path, capsys) -> None:
    path = tmp_path / "pending_leads.json"
    store = leads.empty_store()
    leads.record_run(
        store,
        source="edgar:AXTI",
        result="fetch_failed",
        new=0,
        failure_class="access_blocked",
    )
    leads.record_run(store, source="edgar:AXTI", result="ok", new=1)
    leads.record_run(
        store,
        source="customer_ir:casela",
        result="fetch_failed",
        new=0,
        failure_class="tls_failure",
    )
    leads.save(store, path)

    assert cli.main(["--leads", str(path), "harvest-health"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert [row["source"] for row in rows] == ["customer_ir:casela"]


def test_trace_backlog_keeps_legacy_parked_trace_visible(tmp_path, capsys) -> None:
    path = tmp_path / "pending_leads.json"
    store = leads.empty_store()
    lead_id, _ = leads.register(
        store, source="x:test", url="https://x.com/test/status/trace", title="券商截圖"
    )
    leads.advance(
        store,
        lead_id,
        "parked",
        ref={"parked_reason": "trace_backlog_after_bounded_search"},
    )
    leads.save(store, path)

    assert cli.main(["--leads", str(path), "trace-backlog"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows == [{
        "lead_id": lead_id,
        "title": "券商截圖",
        "url": "https://x.com/test/status/trace",
        "trace_status": "unstructured",
        "next_trigger": "unspecified",
        "attempts_ref": None,
        "requires_user": False,
        "lane": "event_or_scheduled_pq1",
        # 這筆正是「有入口沒出口」的樣本：不需人工 authority，卻也沒有任何具名標的可
        # 比對，兩種 trace_trigger_kind 都永遠不會命中。它看起來在等事件，實際已經死了。
        "auto_trigger_reachable": False,
        "unreachable_reason": (
            "無具名標的可比對：兩種 trace_trigger_kind 都不會命中，"
            "需人工重排或改設 trace_requires_user"
        ),
        "review_title": None,
        "review_hint": None,
        # 具名標的：讓「新 lead 是否與此 parked 有關」可確定性比對，
        # 不必每次重讀 next_trigger 自由文字。此例文字無 cashtag 故為空。
        "entities": [],
    }]


def test_trace_requeue_preserves_triage_receipt_and_returns_to_pq1(tmp_path) -> None:
    path = tmp_path / "pending_leads.json"
    store = leads.empty_store()
    lead_id, _ = leads.register(
        store, source="x:test", url="https://x.com/test/status/paywall"
    )
    leads.triage(store, lead_id, go=True, tier=4, reason="先追原報告")
    leads.advance(store, lead_id, "parked", ref={
        "trace_status": "isolated_tier_3",
        "trace_requires_user": "true",
    })

    lead = leads.requeue_trace(
        store,
        lead_id,
        trigger="user_go",
        reason="使用者提供合法 access，重排 pq1",
        requeued_at="2026-07-29T00:00:00+00:00",
    )

    assert lead["status"] == "triaged_go"
    assert lead["triage_history"][0]["triage"]["reason"] == "先追原報告"
    assert lead["triage"]["priority_flags"]["user_requested"] is True


def test_trace_requeue_restores_latest_classification_from_history() -> None:
    """2026-08-27 XFAB 迴歸：requeue 不得把分類只留在 history。"""

    store = leads.empty_store()
    lead_id, _ = leads.register(
        store, source="x:test", url="https://x.com/test/status/xfab"
    )
    leads.triage(store, lead_id, go=True, tier=4, reason="舊 active receipt")
    leads.advance(store, lead_id, "parked", ref={
        "trace_status": "partial",
        "trace_requires_user": "false",
    })
    old_receipt = {
        "content_type": "structural_fact",
        "decision_impact": "candidate_set",
        "classified_by": "semantic_v1",
        "classified_at": "2026-08-21T00:00:00+00:00",
        "reason": "X-FAB 可能新增 CPO 候選",
    }
    store["leads"][lead_id]["triage_history"] = [{
        "status": "parked",
        "triage": {"classification": old_receipt},
    }]

    lead = leads.requeue_trace(
        store,
        lead_id,
        trigger="related_triaged_lead:lead_event",
        reason="新一手事件觸發 bounded retry",
    )

    assert lead["triage"]["classification"] == old_receipt
    assert leads.classification_gaps(store) == []


def test_advance_records_ref(tmp_path) -> None:
    path = tmp_path / "pending_leads.json"
    lead_id = _seed(path)
    cli.main(["--leads", str(path), "triage", lead_id, "--go", "--tier", "2", "--reason", "x",
              *PASS_CLASSIFICATION_ARGS])
    cli.main(["--leads", str(path), "advance", lead_id, "researching",
              "--ref", "research_action_id=ra_abc"])

    store = leads.load(path)
    assert store["leads"][lead_id]["refs"]["research_action_id"] == "ra_abc"


def test_annotate_records_refs_without_changing_parked_status(tmp_path, capsys) -> None:
    path = tmp_path / "pending_leads.json"
    lead_id = _seed(path)
    cli.main(["--leads", str(path), "advance", lead_id, "parked"])
    capsys.readouterr()

    assert cli.main([
        "--leads", str(path), "annotate", lead_id,
        "--ref", "outcome=official_audio_obtained",
        "--ref", "asr_timestamp=00:08:38-00:09:10",
    ]) == 0

    lead = leads.load(path)["leads"][lead_id]
    assert lead["status"] == "parked"
    assert lead["refs"] == {
        "outcome": "official_audio_obtained",
        "asr_timestamp": "00:08:38-00:09:10",
    }
    assert "status=parked" in capsys.readouterr().out


def test_annotate_rejects_malformed_ref_without_persisting(tmp_path) -> None:
    path = tmp_path / "pending_leads.json"
    lead_id = _seed(path)

    assert cli.main([
        "--leads", str(path), "annotate", lead_id, "--ref", "missing-separator",
    ]) == 1
    assert leads.load(path)["leads"][lead_id]["refs"] == {}


def test_triage_stores_priority_flags(tmp_path) -> None:
    path = tmp_path / "pending_leads.json"
    lead_id = _seed(path)
    cli.main(["--leads", str(path), "triage", lead_id, "--go", "--tier", "3",
              "--reason", "反證", "--contradiction", "--novelty",
              *PASS_CLASSIFICATION_ARGS])
    tri = leads.load(path)["leads"][lead_id]["triage"]
    assert tri["priority_flags"]["contradiction"] is True
    assert tri["priority_flags"]["novelty"] is True
    assert tri["priority_flags"].get("independent_source", False) is False


def test_campaign_triage_passes_selected_and_filters_rest_atomically(
    tmp_path, capsys
) -> None:
    path = tmp_path / "leads.json"
    store = leads.empty_store()
    selected, _ = leads.register(
        store, source="x:test", url="https://x.com/test/status/11"
    )
    filtered, _ = leads.register(
        store, source="x:test", url="https://x.com/test/status/12"
    )
    outsider, _ = leads.register(
        store, source="x:test", url="https://x.com/test/status/13"
    )
    leads.tag_campaign(store, selected, campaign_id="robotics")
    leads.tag_campaign(store, filtered, campaign_id="robotics")
    leads.save(store, path)

    assert cli.main([
        "--leads", str(path), "triage-campaign",
        "--campaign-id", "robotics", "--go-id", selected,
        "--novelty", "--filter-rest", *PASS_CLASSIFICATION_ARGS,
    ]) == 0

    reloaded = leads.load(path)["leads"]
    assert reloaded[selected]["status"] == "triaged_go"
    assert reloaded[selected]["triage"]["priority_flags"] == {
        "novelty": True,
        "user_requested": True,
    }
    assert reloaded[filtered]["status"] == "triaged_no_go"
    assert reloaded[outsider]["status"] == "pending"
    receipt = json.loads(capsys.readouterr().out)
    assert receipt == {"campaign_id": "robotics", "filtered": 1, "passed": 1}


def test_drain_lists_triaged_go_and_researching_by_priority(tmp_path, capsys) -> None:
    path = tmp_path / "pending_leads.json"
    store = leads.empty_store()
    a, _ = leads.register(store, source="edgar:AAOI", url="https://x.io/a")
    b, _ = leads.register(store, source="edgar:COHR", url="https://x.io/b")
    c, _ = leads.register(store, source="edgar:LITE", url="https://x.io/c")
    leads.triage(
        store, a, go=True, tier=4, reason="弱",
        classification={"content_type": "financial_fact", "decision_impact": "confidence_only"},
    )
    leads.triage(
        store, b, go=True, tier=1, reason="強",
        priority_flags={"contradiction": True},
        classification=PASS_CLASSIFICATION,
    )
    leads.triage(store, c, go=False, tier=4, reason="no")  # no-go 不該進 drain
    leads.save(store, path)

    assert cli.main(["--leads", str(path), "drain", "--json"]) == 0
    out = json.loads(capsys.readouterr().out.strip())
    sources = [item["lead"]["source"] for item in out]
    assert "edgar:LITE" not in sources  # no-go 排除
    assert sources[0] == "edgar:COHR"  # 最高 priority 在前
    assert set(sources) == {"edgar:COHR", "edgar:AAOI"}


def test_drain_resumes_researching_leads(tmp_path, capsys) -> None:
    path = tmp_path / "pending_leads.json"
    store = leads.empty_store()
    lead_id, _ = leads.register(store, source="edgar:COHR", url="https://x.io/b")
    leads.triage(
        store, lead_id, go=True, tier=1, reason="x",
        classification=PASS_CLASSIFICATION,
    )
    leads.advance(store, lead_id, "researching")  # 中斷在 pq1 中途
    leads.save(store, path)

    cli.main(["--leads", str(path), "drain", "--json"])
    out = json.loads(capsys.readouterr().out.strip())
    # researching（中斷待續）仍要被 drain 撿回
    assert out[0]["lead"]["status"] == "researching"


def test_classification_health_and_drain_withhold_active_gap(tmp_path, capsys) -> None:
    path = tmp_path / "pending_leads.json"
    store = leads.empty_store()
    missing, _ = leads.register(store, source="x:test", url="https://x.io/missing")
    ready, _ = leads.register(store, source="x:test", url="https://x.io/ready")
    # 低階 API 保留 legacy 相容；production health／drain 必須讓缺口顯形並 withheld。
    leads.triage(store, missing, go=True, tier=1, reason="legacy")
    leads.triage(
        store, ready, go=True, tier=4, reason="classified",
        classification=PASS_CLASSIFICATION,
    )
    leads.save(store, path)

    assert cli.main(["--leads", str(path), "classification-health"]) == 2
    health = json.loads(capsys.readouterr().out)
    assert health["status"] == "error"
    assert [item["lead_id"] for item in health["items"]] == [missing]

    assert cli.main([
        "--leads", str(path), "drain", "--decision-work-orders", "skip", "--json",
    ]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert [row["lead"]["lead_id"] for row in rows if row["kind"] == "lead"] == [ready]
    withheld = [row for row in rows if row["kind"] == "withheld_unclassified_lead"]
    assert withheld[0]["health"]["lead_id"] == missing


def test_default_drain_fails_closed_when_decision_store_is_unavailable(
    tmp_path, capsys, monkeypatch
) -> None:
    path = tmp_path / "pending_leads.json"
    leads.save(leads.empty_store(), path)
    monkeypatch.setattr(leads, "DEFAULT_LEADS_PATH", path)

    import decision_lab.bootstrap

    def fail_open():
        raise RuntimeError("private store blocked")

    monkeypatch.setattr(decision_lab.bootstrap, "open_default_store", fail_open)

    assert cli.main(["--leads", str(path), "drain"]) == 2
    assert "Decision pq1 無法讀取" in capsys.readouterr().err


def test_default_priority_list_fails_closed_when_holdings_are_unavailable(
    tmp_path, capsys, monkeypatch
) -> None:
    path = tmp_path / "pending_leads.json"
    leads.save(leads.empty_store(), path)
    monkeypatch.setattr(leads, "DEFAULT_LEADS_PATH", path)

    def fail_held(*, strict: bool = False):
        assert strict is True
        raise cli.PriorityContextError("無法載入 Google Sheet 持股 context")

    monkeypatch.setattr(cli, "_held", fail_held)

    assert cli.main([
        "--leads", str(path), "list", "--by-priority",
    ]) == 2
    assert "pq1 priority context 無法讀取" in capsys.readouterr().err
