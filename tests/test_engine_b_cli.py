"""engine_b.cli：leads 狀態機的命令列入口（list／triage／advance／counts）。"""
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
