"""Session-start safety net for unfinished intake git work."""

from __future__ import annotations

import subprocess
from pathlib import Path

from crons.weekly_scan_digest import intake_pending_summary
from intake import actions as research_actions


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", message)


def _ready(tmp_git_repo: Path, tmp_path: Path) -> Path:
    (tmp_git_repo / "baseline.txt").write_text("base", encoding="utf-8")
    _commit(tmp_git_repo, "baseline")
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    _git(tmp_git_repo, "remote", "add", "origin", str(remote))
    _git(tmp_git_repo, "push", "-u", "origin", "master")
    return remote


def test_digest_counts_only_pending_ledger_files(tmp_git_repo: Path) -> None:
    (tmp_git_repo / "extractions").mkdir()
    tracked = tmp_git_repo / "extractions" / "tracked.json"
    tracked.write_text("{}", encoding="utf-8")
    (tmp_git_repo / "outside.txt").write_text("outside", encoding="utf-8")
    _commit(tmp_git_repo, "baseline")
    tracked.write_text('{"changed":true}', encoding="utf-8")
    (tmp_git_repo / "library" / "raw").mkdir(parents=True)
    (tmp_git_repo / "library" / "raw" / "new.txt").write_text("new", encoding="utf-8")
    (tmp_git_repo / "other.txt").write_text("ignore", encoding="utf-8")

    summary = intake_pending_summary(tmp_git_repo)

    assert summary["modified"] == ["extractions/tracked.json"]
    assert summary["untracked"] == ["library/raw/new.txt"]
    assert summary["total"] == 2


def test_digest_is_quiet_after_push_and_counts_unpushed_intake_commit(
    tmp_git_repo: Path, tmp_path: Path
) -> None:
    _ready(tmp_git_repo, tmp_path)
    assert intake_pending_summary(tmp_git_repo)["total"] == 0

    (tmp_git_repo / "extractions").mkdir()
    (tmp_git_repo / "extractions" / "new.json").write_text("{}", encoding="utf-8")
    _commit(tmp_git_repo, "local intake")

    summary = intake_pending_summary(tmp_git_repo)
    assert summary["untracked"] == []
    assert summary["modified"] == []
    assert summary["unpushed_commits"] == 1
    assert summary["total"] == 1


def test_digest_surfaces_research_action_lifecycle_without_ledger_double_count(
    tmp_git_repo: Path,
) -> None:
    extraction = {
        "schema_version": "0.1",
        "source_doc": {
            "doc_id": "digest_action_doc",
            "title": "Digest action",
            "source_type": "filing",
            "evidence_tier": 1,
            "origin_entity": "Test Issuer",
            "storage_permission": "repo_full",
            "permission_basis": "Official filing retained for private research",
        },
        "sources": [],
        "nodes": [],
        "edges": [],
        "claims": [],
    }
    research_actions.create_action(
        {
            "schema_version": research_actions.ACTION_PAYLOAD_SCHEMA,
            "action_slug": "digest-action",
            "report": {
                "title": "Digest action",
                "why_now": "New evidence",
                "findings": "New finding",
                "search_summary": "Primary source traced",
                "l8_notes": "Independent origin checked",
                "counterevidence_and_gaps": "No decisive contradiction",
            },
            "documents": [
                {
                    "doc_id": "digest_action_doc",
                    "extraction": extraction,
                    "raw_payload": {},
                    "storage_permission": "repo_full",
                    "permission_basis": "Official filing retained for private research",
                    "validation_warnings": [],
                }
            ],
        },
        root=tmp_git_repo,
    )

    summary = intake_pending_summary(tmp_git_repo)

    assert summary["research_actions"]["ready_for_approval"] == 1
    assert summary["total"] == 1


def test_pushed_action_does_not_hide_a_later_ledger_modification(
    tmp_git_repo: Path,
) -> None:
    (tmp_git_repo / "extractions").mkdir()
    extraction_path = tmp_git_repo / "extractions" / "historical.json"
    extraction_path.write_text("{}", encoding="utf-8")
    _commit(tmp_git_repo, "published action")

    extraction = {
        "schema_version": "0.1",
        "source_doc": {
            "doc_id": "historical",
            "title": "Historical action",
            "source_type": "filing",
            "evidence_tier": 1,
            "origin_entity": "Test Issuer",
            "storage_permission": "repo_full",
            "permission_basis": "Official filing retained for private research",
        },
        "sources": [],
        "nodes": [],
        "edges": [],
        "claims": [],
    }
    record = research_actions.create_action(
        {
            "schema_version": research_actions.ACTION_PAYLOAD_SCHEMA,
            "action_slug": "historical-action",
            "report": {
                "title": "Historical action",
                "why_now": "Historical evidence",
                "findings": "Historical finding",
                "search_summary": "Primary source traced",
                "l8_notes": "Independent origin checked",
                "counterevidence_and_gaps": "No decisive contradiction",
            },
            "documents": [
                {
                    "doc_id": "historical",
                    "extraction": extraction,
                    "raw_payload": {},
                    "storage_permission": "repo_full",
                    "permission_basis": "Official filing retained for private research",
                    "validation_warnings": [],
                }
            ],
        },
        root=tmp_git_repo,
    )
    record["state"] = "pushed"
    record["git"]["status"] = "pushed"
    record["git"]["eligible_paths"] = ["extractions/historical.json"]
    research_actions.save_action(record, root=tmp_git_repo)
    extraction_path.write_text('{"later":true}', encoding="utf-8")

    summary = intake_pending_summary(tmp_git_repo)

    assert summary["modified"] == ["extractions/historical.json"]
    assert summary["total"] == 1


def test_pending_onboard_reports_undecided_companies_only(
    tmp_path: Path, monkeypatch
) -> None:
    import json

    import identity.registry as registry_module
    from crons.weekly_scan_digest import pending_onboard_companies

    extraction_dir = tmp_path / "extractions"
    extraction_dir.mkdir()
    (extraction_dir / "doc.json").write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": "co:decided_ticker", "type": "Company"},
                    {"id": "co:decided_private", "type": "Company"},
                    {"id": "co:undecided", "type": "Company"},
                    {"id": "prod:not_company", "type": "Product"},
                ]
            }
        ),
        encoding="utf-8",
    )
    (extraction_dir / "broken.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(
        registry_module,
        "TICKER_MAP",
        {"co:decided_ticker": "TICK", "co:decided_private": None},
    )

    assert pending_onboard_companies(tmp_path) == ["co:undecided"]


def test_pending_onboard_is_quiet_without_extraction_dir(tmp_path: Path) -> None:
    from crons.weekly_scan_digest import pending_onboard_companies

    assert pending_onboard_companies(tmp_path) == []
