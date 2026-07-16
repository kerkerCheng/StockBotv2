"""Local Research Action commit batching and recovery proofs."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from mcp_server import action_publisher, intake, research_actions


BASIS = "Official public filing retained for private research"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _ready_remote(repo: Path, remote: Path) -> None:
    (repo / ".gitignore").write_text(
        (intake.ROOT / ".gitignore").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (repo / "baseline.txt").write_text("baseline", encoding="utf-8")
    _git(repo, "add", ".gitignore", "baseline.txt")
    _git(repo, "commit", "-m", "baseline")
    subprocess.run(
        ["git", "init", "--bare", str(remote)], check=True, capture_output=True
    )
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-u", "origin", "master")


def _extraction(doc_id: str, permission: str) -> dict:
    return {
        "schema_version": "0.1",
        "source_doc": {
            "doc_id": doc_id,
            "title": f"Document {doc_id}",
            "source_type": "filing",
            "evidence_tier": 1,
            "origin_entity": "Test Issuer",
            "storage_permission": permission,
            "permission_basis": BASIS,
        },
        "sources": [],
        "nodes": [],
        "edges": [],
        "claims": [],
    }


def _report(title: str) -> dict:
    return {
        "title": title,
        "why_now": "New primary evidence arrived.",
        "findings": "The evidence adds a durable graph claim.",
        "search_summary": "Primary registry and issuer IR were checked.",
        "l8_notes": "Origin entity and event remain independently counted.",
        "counterevidence_and_gaps": "No decisive counterevidence found.",
    }


def _create_applied_action(
    repo: Path,
    action_name: str,
    *permissions: str,
) -> dict:
    documents = []
    for index, permission in enumerate(permissions or ("repo_full",)):
        doc_id = f"{action_name}_doc_{index}"
        extraction = _extraction(doc_id, permission)
        documents.append(
            {
                "doc_id": doc_id,
                "extraction": extraction,
                "raw_payload": {"raw_text": f"raw {doc_id}"},
                "storage_permission": permission,
                "permission_basis": BASIS,
                "validation_warnings": [],
            }
        )
    payload = {
        "schema_version": research_actions.ACTION_PAYLOAD_SCHEMA,
        "action_slug": action_name,
        "report": _report(f"Action {action_name}"),
        "documents": documents,
    }
    record = research_actions.create_action(payload, root=repo)
    for index, document in enumerate(documents):
        provenance = intake.publish_provenance(
            document["doc_id"],
            document["extraction"],
            document["raw_payload"],
            root=repo,
        )
        intake.mark_graph_complete(
            document["doc_id"], document["extraction"], root=repo
        )
        record["execution"]["documents"][index] = {
            "doc_id": document["doc_id"],
            "status": "complete",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "result": {
                "status": "loaded_or_already_complete",
                "doc_id": document["doc_id"],
                "resolved_paths": provenance["paths"],
                "open_conflict_ids": [],
                "stale_resolution_ids": [],
                "finalize_eligible": provenance["finalize_eligible"],
                "extraction_sha256": intake.canonical_extraction_hash(
                    document["extraction"]
                ),
            },
        }
    record["state"] = "partial"
    record["execution"]["report"] = research_actions.publish_action_reports(
        record, root=repo
    )
    record["state"] = "applied"
    record["applied_at"] = datetime.now(timezone.utc).isoformat()
    eligible = research_actions.eligible_action_paths(record)
    record["git"]["eligible_paths"] = eligible
    record["git"]["status"] = "pending" if eligible else "not_required"
    record["final_result"] = {
        "status": "applied",
        "action_id": record["action_id"],
        "action_digest": record["action_digest"],
    }
    record = research_actions.compact_applied_payload(record)
    return research_actions.save_action(record, root=repo)


def _new_commit_count(repo: Path) -> int:
    return int(_git(repo, "rev-list", "--count", "origin/master..HEAD") or "0")


def test_two_actions_create_two_exact_commits_and_one_push_preserving_unrelated(
    tmp_git_repo: Path, tmp_path: Path, monkeypatch
) -> None:
    _ready_remote(tmp_git_repo, tmp_path / "remote.git")
    first = _create_applied_action(tmp_git_repo, "first")
    second = _create_applied_action(tmp_git_repo, "second")
    unrelated = tmp_git_repo / "notes.txt"
    unrelated.write_text("do not touch", encoding="utf-8")
    real_run_git = action_publisher._run_git
    push_calls = 0

    def counting_git(args, *, root, timeout=30):
        nonlocal push_calls
        if args[:2] == ["push", "origin"]:
            push_calls += 1
        return real_run_git(args, root=root, timeout=timeout)

    monkeypatch.setattr(action_publisher, "_run_git", counting_git)
    result = action_publisher.publish_pending_actions(root=tmp_git_repo)

    assert result["status"] == "pushed"
    assert push_calls == 1
    assert len(result["committed"]) == 2
    assert unrelated.read_text(encoding="utf-8") == "do not touch"
    assert _git(tmp_git_repo, "status", "--porcelain", "--", "notes.txt") == "?? notes.txt"
    assert _new_commit_count(tmp_git_repo) == 0
    history = _git(tmp_git_repo, "log", "-2", "--format=%B")
    assert first["action_id"] in history
    assert second["action_id"] in history
    for action in (first, second):
        stored = research_actions.read_action(action["action_id"], root=tmp_git_repo)
        assert stored["state"] == "pushed"


def test_push_failure_preserves_commits_and_retry_does_not_recommit(
    tmp_git_repo: Path, tmp_path: Path
) -> None:
    remote = tmp_path / "remote.git"
    _ready_remote(tmp_git_repo, remote)
    action = _create_applied_action(tmp_git_repo, "pushfail")
    _git(
        tmp_git_repo,
        "remote",
        "set-url",
        "--push",
        "origin",
        str(tmp_path / "missing.git"),
    )

    failed = action_publisher.publish_pending_actions(root=tmp_git_repo)
    commit = research_actions.read_action(action["action_id"], root=tmp_git_repo)[
        "git"
    ]["commit"]
    assert failed["status"] == "committed_not_pushed"
    assert _new_commit_count(tmp_git_repo) == 1

    _git(tmp_git_repo, "remote", "set-url", "--push", "origin", str(remote))
    retried = action_publisher.publish_pending_actions(root=tmp_git_repo)
    assert retried["status"] == "pushed"
    assert _git(tmp_git_repo, "rev-parse", "HEAD") == commit
    assert research_actions.read_action(action["action_id"], root=tmp_git_repo)[
        "state"
    ] == "pushed"


def test_crash_after_commit_before_receipt_reconciles_from_trailers(
    tmp_git_repo: Path, tmp_path: Path
) -> None:
    _ready_remote(tmp_git_repo, tmp_path / "remote.git")
    action = _create_applied_action(tmp_git_repo, "crash")

    def crash(_record, _commit):
        raise RuntimeError("simulated process death")

    with pytest.raises(RuntimeError, match="process death"):
        action_publisher.publish_pending_actions(
            root=tmp_git_repo, after_commit=crash
        )
    assert _new_commit_count(tmp_git_repo) == 1
    assert research_actions.read_action(action["action_id"], root=tmp_git_repo)[
        "state"
    ] == "applied"

    recovered = action_publisher.publish_pending_actions(root=tmp_git_repo)
    assert recovered["status"] == "pushed"
    assert _git(tmp_git_repo, "rev-list", "--count", "HEAD~1..HEAD") == "1"
    stored = research_actions.read_action(action["action_id"], root=tmp_git_repo)
    assert stored["state"] == "pushed"
    assert stored["git"]["committed_paths"]


def test_unexplained_ahead_commit_fails_before_action_staging(
    tmp_git_repo: Path, tmp_path: Path
) -> None:
    _ready_remote(tmp_git_repo, tmp_path / "remote.git")
    action = _create_applied_action(tmp_git_repo, "blocked")
    (tmp_git_repo / "unrelated-commit.txt").write_text("x", encoding="utf-8")
    _git(tmp_git_repo, "add", "unrelated-commit.txt")
    _git(tmp_git_repo, "commit", "-m", "unexplained")

    result = action_publisher.publish_pending_actions(root=tmp_git_repo)

    assert result["status"] == "rejected"
    assert result["reason"] == "unexplained_ahead_commit"
    assert research_actions.read_action(action["action_id"], root=tmp_git_repo)[
        "state"
    ] == "applied"


def test_mid_batch_commit_failure_preserves_first_and_retry_finishes(
    tmp_git_repo: Path, tmp_path: Path, monkeypatch
) -> None:
    _ready_remote(tmp_git_repo, tmp_path / "remote.git")
    first = _create_applied_action(tmp_git_repo, "batchfirst")
    second = _create_applied_action(tmp_git_repo, "batchsecond")
    real_run_git = action_publisher._run_git
    commit_calls = 0

    def fail_second_commit(args, *, root, timeout=30):
        nonlocal commit_calls
        if args and args[0] == "commit":
            commit_calls += 1
            if commit_calls == 2:
                return subprocess.CompletedProcess(args, 1, "", "simulated hook rejection")
        return real_run_git(args, root=root, timeout=timeout)

    monkeypatch.setattr(action_publisher, "_run_git", fail_second_commit)
    failed = action_publisher.publish_pending_actions(root=tmp_git_repo)

    assert failed["status"] == "rejected"
    assert failed["reason"] == "git_commit_failed"
    assert research_actions.read_action(first["action_id"], root=tmp_git_repo)[
        "state"
    ] == "committed_not_pushed"
    assert research_actions.read_action(second["action_id"], root=tmp_git_repo)[
        "state"
    ] == "applied"

    monkeypatch.setattr(action_publisher, "_run_git", real_run_git)
    recovered = action_publisher.publish_pending_actions(root=tmp_git_repo)
    assert recovered["status"] == "pushed"
    assert research_actions.read_action(second["action_id"], root=tmp_git_repo)[
        "state"
    ] == "pushed"


def test_local_only_action_requires_no_git_commit(
    tmp_git_repo: Path, tmp_path: Path
) -> None:
    _ready_remote(tmp_git_repo, tmp_path / "remote.git")
    action = _create_applied_action(tmp_git_repo, "private", "local_only")

    result = action_publisher.publish_pending_actions(root=tmp_git_repo)

    assert result["status"] == "nothing_to_push"
    assert _new_commit_count(tmp_git_repo) == 0
    stored = research_actions.read_action(action["action_id"], root=tmp_git_repo)
    assert stored["state"] == "applied"
    assert stored["git"]["status"] == "not_required"


def test_mixed_action_commit_contains_stub_and_only_repo_eligible_documents(
    tmp_git_repo: Path, tmp_path: Path
) -> None:
    _ready_remote(tmp_git_repo, tmp_path / "remote.git")
    action = _create_applied_action(
        tmp_git_repo, "mixed", "repo_full", "local_only"
    )

    result = action_publisher.publish_pending_actions(root=tmp_git_repo)
    assert result["status"] == "pushed"
    commit = research_actions.read_action(action["action_id"], root=tmp_git_repo)[
        "git"
    ]["commit"]
    changed = _git(tmp_git_repo, "show", "--pretty=", "--name-only", commit).splitlines()
    assert any(path.startswith("library/intake/") for path in changed)
    assert "extractions/mixed_doc_0.json" in changed
    assert all("mixed_doc_1" not in path for path in changed)


def test_dry_run_and_unsafe_index_are_non_mutating(
    tmp_git_repo: Path, tmp_path: Path
) -> None:
    _ready_remote(tmp_git_repo, tmp_path / "remote.git")
    action = _create_applied_action(tmp_git_repo, "dryrun")
    dry = action_publisher.publish_pending_actions(root=tmp_git_repo, dry_run=True)
    assert dry["status"] == "dry_run"
    assert dry["would_commit"] == [action["action_id"]]
    assert _new_commit_count(tmp_git_repo) == 0

    (tmp_git_repo / "staged.txt").write_text("staged", encoding="utf-8")
    _git(tmp_git_repo, "add", "staged.txt")
    rejected = action_publisher.publish_pending_actions(root=tmp_git_repo)
    assert rejected["status"] == "rejected"
    assert rejected["reason"] == "index_not_clean"
    assert _new_commit_count(tmp_git_repo) == 0


def test_dry_run_rejects_stale_report_receipt_without_mutation(
    tmp_git_repo: Path, tmp_path: Path
) -> None:
    _ready_remote(tmp_git_repo, tmp_path / "remote.git")
    action = _create_applied_action(tmp_git_repo, "stale-report")
    report_path = action["execution"]["report"]["public_path"]
    (tmp_git_repo / report_path).write_text("tampered", encoding="utf-8")

    result = action_publisher.publish_pending_actions(
        root=tmp_git_repo, dry_run=True
    )

    assert result["status"] == "rejected"
    assert result["reason"] == "report_receipt_invalid"
    assert _new_commit_count(tmp_git_repo) == 0


def test_ignored_action_path_cannot_silently_drop_out_of_commit(
    tmp_git_repo: Path, tmp_path: Path
) -> None:
    _ready_remote(tmp_git_repo, tmp_path / "remote.git")
    action = _create_applied_action(tmp_git_repo, "ignored")
    ignored_path = "extractions/ignored_doc_0.json"
    with (tmp_git_repo / ".gitignore").open("a", encoding="utf-8") as handle:
        handle.write(f"\n{ignored_path}\n")

    result = action_publisher.publish_pending_actions(root=tmp_git_repo)

    assert result["status"] == "rejected"
    assert result["reason"] in {
        "git_add_failed",
        "eligible_path_not_staged_or_tracked",
    }
    assert _new_commit_count(tmp_git_repo) == 0
    assert _git(tmp_git_repo, "diff", "--cached", "--name-only") == ""
    assert research_actions.read_action(action["action_id"], root=tmp_git_repo)[
        "state"
    ] == "applied"


def test_git_timeout_is_returned_as_structured_publication_error(
    tmp_path: Path, monkeypatch
) -> None:
    def timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="git fetch", timeout=1)

    monkeypatch.setattr(action_publisher.subprocess, "run", timeout)

    with pytest.raises(action_publisher.PublicationError) as captured:
        action_publisher._run_git(["fetch", "origin", "master"], root=tmp_path)

    assert captured.value.code == "git_timeout"
