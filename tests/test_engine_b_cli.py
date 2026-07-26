"""engine_b.cli：leads 狀態機的命令列入口。"""
from __future__ import annotations

import json
from pathlib import Path

from engine_b import cli, leads


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
                     "--go", "--tier", "2", "--reason", "有新角度"]) == 0
    assert cli.main(["--leads", str(path), "advance", lead_id, "researching"]) == 0

    store = leads.load(path)
    assert store["leads"][lead_id]["status"] == "researching"
    assert store["leads"][lead_id]["triage"]["decision"] == "go"


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


def test_advance_records_ref(tmp_path) -> None:
    path = tmp_path / "pending_leads.json"
    lead_id = _seed(path)
    cli.main(["--leads", str(path), "triage", lead_id, "--go", "--tier", "2", "--reason", "x"])
    cli.main(["--leads", str(path), "advance", lead_id, "researching",
              "--ref", "research_action_id=ra_abc"])

    store = leads.load(path)
    assert store["leads"][lead_id]["refs"]["research_action_id"] == "ra_abc"


def test_triage_stores_priority_flags(tmp_path) -> None:
    path = tmp_path / "pending_leads.json"
    lead_id = _seed(path)
    cli.main(["--leads", str(path), "triage", lead_id, "--go", "--tier", "3",
              "--reason", "反證", "--contradiction", "--novelty"])
    tri = leads.load(path)["leads"][lead_id]["triage"]
    assert tri["priority_flags"]["contradiction"] is True
    assert tri["priority_flags"]["novelty"] is True
    assert tri["priority_flags"].get("independent_source", False) is False


def test_drain_lists_triaged_go_and_researching_by_priority(tmp_path, capsys) -> None:
    path = tmp_path / "pending_leads.json"
    store = leads.empty_store()
    a, _ = leads.register(store, source="edgar:AAOI", url="https://x.io/a")
    b, _ = leads.register(store, source="edgar:COHR", url="https://x.io/b")
    c, _ = leads.register(store, source="edgar:LITE", url="https://x.io/c")
    leads.triage(store, a, go=True, tier=4, reason="弱")
    leads.triage(store, b, go=True, tier=1, reason="強", priority_flags={"contradiction": True})
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
    leads.triage(store, lead_id, go=True, tier=1, reason="x")
    leads.advance(store, lead_id, "researching")  # 中斷在 pq1 中途
    leads.save(store, path)

    cli.main(["--leads", str(path), "drain", "--json"])
    out = json.loads(capsys.readouterr().out.strip())
    # researching（中斷待續）仍要被 drain 撿回
    assert out[0]["lead"]["status"] == "researching"
