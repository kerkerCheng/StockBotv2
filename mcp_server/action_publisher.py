"""Local-only Git publication for applied Research Actions.

This module is intentionally not imported by the remote MCP tool surface. It
accepts only server-derived eligible paths and explains every ahead commit with
an action ID + digest trailer before a batch push.
"""

from __future__ import annotations

import copy
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from mcp_server import research_actions
from mcp_server.intake import (
    LEDGER_PREFIXES,
    ROOT,
    canonical_extraction_hash,
    validate_doc_id,
    verify_graph_complete,
)


class PublicationError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code = code
        self.detail = detail


def _run_git(
    args: list[str], *, root: Path, timeout: int = 30
) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        command = args[0] if args else "command"
        raise PublicationError(
            "git_timeout", f"git {command} exceeded {timeout}s"
        ) from exc
    except OSError as exc:
        raise PublicationError("git_unavailable", type(exc).__name__) from exc


def _git_text(args: list[str], *, root: Path, timeout: int = 30) -> str:
    result = _run_git(args, root=root, timeout=timeout)
    if result.returncode != 0:
        raise PublicationError(
            "git_failed", result.stderr.strip() or f"git {' '.join(args)} failed"
        )
    return result.stdout.strip()


def _is_ancestor(ancestor: str, descendant: str, *, root: Path) -> bool:
    result = _run_git(
        ["merge-base", "--is-ancestor", ancestor, descendant], root=root
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise PublicationError(
        "git_ancestry_failed", result.stderr.strip() or "cannot verify ancestry"
    )


def _validate_relative_path(value: str, *, root: Path) -> str:
    if not isinstance(value, str) or not value:
        raise PublicationError("invalid_action_path", repr(value))
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise PublicationError("invalid_action_path", value)
    normalized = path.as_posix()
    if not any(normalized.startswith(prefix) for prefix in LEDGER_PREFIXES):
        raise PublicationError("path_outside_ledger", normalized)
    absolute = (root / path).resolve()
    try:
        absolute.relative_to(root.resolve())
    except ValueError as exc:
        raise PublicationError("path_outside_repository", normalized) from exc
    if not absolute.exists() or not absolute.is_file():
        raise PublicationError("action_path_missing", normalized)
    return normalized


def _eligible_paths(record: dict, *, root: Path) -> list[str]:
    paths = record.get("git", {}).get("eligible_paths") or []
    normalized = sorted({_validate_relative_path(item, root=root) for item in paths})
    if record.get("git", {}).get("status") != "not_required" and not normalized:
        raise PublicationError("action_has_no_eligible_paths", record["action_id"])
    return normalized


def _verify_action_receipts(record: dict, *, root: Path) -> None:
    try:
        research_actions.verify_action_reports(record, root=root)
    except (OSError, ValueError) as exc:
        raise PublicationError(
            "report_receipt_invalid", record.get("action_id", "unknown")
        ) from exc
    for manifest, execution in zip(
        record.get("document_manifest") or [],
        record.get("execution", {}).get("documents") or [],
        strict=True,
    ):
        if execution.get("status") != "complete":
            raise PublicationError("document_receipt_incomplete", manifest["doc_id"])
        doc_id = validate_doc_id(manifest["doc_id"])
        extraction_path = (
            root / "library" / "private" / "extractions" / f"{doc_id}.json"
            if manifest["storage_permission"] == "local_only"
            else root / "extractions" / f"{doc_id}.json"
        )
        try:
            extraction = json.loads(extraction_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PublicationError("stored_extraction_invalid", doc_id) from exc
        result = execution.get("result") or {}
        if result.get("extraction_sha256") != canonical_extraction_hash(extraction):
            raise PublicationError("document_receipt_hash_mismatch", doc_id)
        try:
            verify_graph_complete(doc_id, extraction, root=root)
        except ValueError as exc:
            raise PublicationError("graph_receipt_invalid", doc_id) from exc


def _validate_action_worktree(record: dict, *, root: Path) -> list[str]:
    """Validate receipts and exact path readiness without staging anything."""

    _verify_action_receipts(record, root=root)
    eligible = _eligible_paths(record, root=root)
    statuses = _path_status(eligible, root=root)
    modified = {path: status for path, status in statuses.items() if status != "??"}
    if modified:
        raise PublicationError("modified_tracked_action_path", repr(modified))
    for path in sorted(set(eligible) - set(statuses)):
        tracked = _run_git(["ls-files", "--error-unmatch", "--", path], root=root)
        if tracked.returncode != 0:
            raise PublicationError(
                "eligible_path_not_staged_or_tracked",
                f"{path} may be ignored or otherwise missing from the action commit",
            )
    return eligible


def _preflight(root: Path) -> dict:
    branch = _git_text(["branch", "--show-current"], root=root)
    if branch != "master":
        raise PublicationError("not_master", branch)
    staged = _run_git(["diff", "--cached", "--quiet"], root=root)
    if staged.returncode == 1:
        raise PublicationError("index_not_clean", "staged changes exist")
    if staged.returncode != 0:
        raise PublicationError("git_failed", staged.stderr.strip())
    fetched = _run_git(["fetch", "origin", "master"], root=root, timeout=60)
    if fetched.returncode != 0:
        raise PublicationError("fetch_failed", fetched.stderr.strip())
    head = _git_text(["rev-parse", "HEAD"], root=root)
    remote = _git_text(["rev-parse", "origin/master"], root=root)
    if not _is_ancestor(remote, head, root=root):
        relation = "behind" if _is_ancestor(head, remote, root=root) else "diverged"
        raise PublicationError(f"head_{relation}", f"HEAD={head} origin/master={remote}")
    ahead_text = _git_text(
        ["rev-list", "--reverse", "origin/master..HEAD"], root=root
    )
    return {
        "head": head,
        "remote": remote,
        "ahead": [line for line in ahead_text.splitlines() if line],
    }


def _commit_message(commit: str, *, root: Path) -> str:
    return _git_text(["show", "-s", "--format=%B", commit], root=root)


def _trailers(message: str) -> tuple[str | None, str | None]:
    action_ids = []
    digests = []
    for line in message.splitlines():
        if line.startswith("Research-Action-ID:"):
            action_ids.append(line.split(":", 1)[1].strip())
        elif line.startswith("Research-Action-Digest:"):
            digests.append(line.split(":", 1)[1].strip())
    if len(action_ids) != 1 or len(digests) != 1:
        return None, None
    return action_ids[0], digests[0]


def _commit_paths(commit: str, *, root: Path) -> list[str]:
    raw = _git_text(
        ["diff-tree", "--no-commit-id", "--name-only", "-r", "-z", commit],
        root=root,
    )
    return sorted(item.replace("\\", "/") for item in raw.split("\0") if item)


def _path_status(paths: list[str], *, root: Path) -> dict[str, str]:
    if not paths:
        return {}
    result = _run_git(
        ["status", "--porcelain=v1", "-z", "--untracked-files=all", "--", *paths],
        root=root,
    )
    if result.returncode != 0:
        raise PublicationError("git_status_failed", result.stderr.strip())
    statuses = {}
    entries = result.stdout.split("\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        status = entry[:2]
        path = entry[3:].replace("\\", "/")
        statuses[path] = status
        if "R" in status or "C" in status:
            index += 1
    return statuses


def _record_commit(
    action_id: str,
    action_digest: str,
    commit: str,
    paths: list[str],
    *,
    root: Path,
) -> dict:
    with research_actions.action_lock(action_id, root=root):
        record = research_actions.read_action(action_id, root=root)
        if record["action_digest"] != action_digest:
            raise PublicationError("action_digest_mismatch", action_id)
        if record["state"] not in {"applied", "committed_not_pushed"}:
            raise PublicationError("action_not_commit_eligible", record["state"])
        record["state"] = "committed_not_pushed"
        record["git"]["status"] = "committed_not_pushed"
        record["git"]["commit"] = commit
        record["git"]["committed_paths"] = list(paths)
        record["git"]["committed_at"] = datetime.now(timezone.utc).isoformat()
        return research_actions.save_action(record, root=root)


def _mark_pushed(action_id: str, commit: str, *, root: Path) -> dict:
    with research_actions.action_lock(action_id, root=root):
        record = research_actions.read_action(action_id, root=root)
        if record.get("git", {}).get("commit") != commit:
            raise PublicationError("action_commit_mismatch", action_id)
        record["state"] = "pushed"
        record["git"]["status"] = "pushed"
        record["git"]["pushed_at"] = datetime.now(timezone.utc).isoformat()
        return research_actions.save_action(record, root=root)


def _record_map(root: Path) -> dict[str, dict]:
    return {record["action_id"]: record for record in research_actions.iter_actions(root=root)}


def _reconcile_ahead(
    commits: list[str], *, root: Path, dry_run: bool
) -> list[dict]:
    records = _record_map(root)
    explained = []
    seen_actions = set()
    for commit in commits:
        action_id, action_digest = _trailers(_commit_message(commit, root=root))
        if not action_id or not action_digest:
            raise PublicationError("unexplained_ahead_commit", commit)
        if action_id in seen_actions:
            raise PublicationError("duplicate_action_commit", action_id)
        seen_actions.add(action_id)
        record = records.get(action_id)
        if record is None or record["action_digest"] != action_digest:
            raise PublicationError("unknown_action_commit", commit)
        if record["state"] not in {"applied", "committed_not_pushed"}:
            raise PublicationError("ahead_action_state_invalid", record["state"])
        eligible = set(_eligible_paths(record, root=root))
        changed = _commit_paths(commit, root=root)
        if not changed or not set(changed).issubset(eligible):
            raise PublicationError(
                "action_commit_path_mismatch",
                f"{action_id}: changed={changed}, eligible={sorted(eligible)}",
            )
        remaining = _path_status(sorted(eligible), root=root)
        if remaining:
            raise PublicationError(
                "action_commit_incomplete",
                f"{action_id}: remaining={remaining}",
            )
        if not dry_run and (
            record.get("git", {}).get("commit") != commit
            or record.get("state") != "committed_not_pushed"
        ):
            record = _record_commit(
                action_id, action_digest, commit, changed, root=root
            )
        explained.append(
            {"action_id": action_id, "commit": commit, "paths": changed}
        )
    return explained


def _mark_already_pushed(*, root: Path, remote: str, dry_run: bool) -> list[str]:
    marked = []
    for record in list(research_actions.iter_actions(root=root)):
        if record["state"] != "committed_not_pushed":
            continue
        commit = record.get("git", {}).get("commit")
        if not commit or not _is_ancestor(commit, remote, root=root):
            continue
        action_id, digest = _trailers(_commit_message(commit, root=root))
        if action_id != record["action_id"] or digest != record["action_digest"]:
            raise PublicationError("pushed_commit_trailer_mismatch", record["action_id"])
        if set(_commit_paths(commit, root=root)) - set(_eligible_paths(record, root=root)):
            raise PublicationError("pushed_commit_path_mismatch", record["action_id"])
        if not dry_run:
            _mark_pushed(record["action_id"], commit, root=root)
        marked.append(record["action_id"])
    return marked


def _commit_action(
    record: dict,
    *,
    root: Path,
    after_commit: Callable[[dict, str], None] | None = None,
) -> dict:
    eligible = _validate_action_worktree(record, root=root)
    added = _run_git(["add", "--", *eligible], root=root)
    if added.returncode != 0:
        staged_after_failure = _run_git(
            ["diff", "--cached", "--name-only", "-z"], root=root
        )
        if staged_after_failure.returncode == 0:
            staged_paths = [
                item.replace("\\", "/")
                for item in staged_after_failure.stdout.split("\0")
                if item
            ]
            if staged_paths:
                _run_git(["restore", "--staged", "--", *staged_paths], root=root)
        raise PublicationError("git_add_failed", added.stderr.strip())
    try:
        staged_raw = _git_text(
            ["diff", "--cached", "--name-only", "-z"], root=root
        )
        staged = sorted(
            item.replace("\\", "/") for item in staged_raw.split("\0") if item
        )
        if not staged:
            raise PublicationError("no_action_changes", record["action_id"])
        if not set(staged).issubset(set(eligible)):
            raise PublicationError(
                "staged_path_mismatch", f"staged={staged}, eligible={eligible}"
            )
        for path in sorted(set(eligible) - set(staged)):
            tracked = _run_git(["ls-files", "--error-unmatch", "--", path], root=root)
            if tracked.returncode != 0:
                raise PublicationError(
                    "eligible_path_not_staged_or_tracked",
                    f"{path} may be ignored or otherwise missing from the action commit",
                )
        deleted = _git_text(
            ["diff", "--cached", "--diff-filter=D", "--name-only"], root=root
        )
        if deleted:
            raise PublicationError("action_commit_contains_deletion", deleted)
        title = (
            (record.get("review") or {}).get("title") or record["action_id"]
        )
        headline = " ".join(str(title).split())[:72]
        body = (
            f"Research-Action-ID: {record['action_id']}\n"
            f"Research-Action-Digest: {record['action_digest']}"
        )
        committed = _run_git(
            ["commit", "-m", f"intake: {headline}", "-m", body],
            root=root,
            timeout=60,
        )
        if committed.returncode != 0:
            raise PublicationError("git_commit_failed", committed.stderr.strip())
        commit = _git_text(["rev-parse", "HEAD"], root=root)
        changed = _commit_paths(commit, root=root)
        if changed != staged:
            raise PublicationError(
                "committed_path_mismatch", f"staged={staged}, committed={changed}"
            )
        if after_commit is not None:
            after_commit(record, commit)
        _record_commit(
            record["action_id"],
            record["action_digest"],
            commit,
            changed,
            root=root,
        )
        return {"action_id": record["action_id"], "commit": commit, "paths": changed}
    except Exception:
        current = _git_text(["rev-parse", "HEAD"], root=root)
        if _trailers(_commit_message(current, root=root))[0] != record["action_id"]:
            _run_git(["restore", "--staged", "--", *eligible], root=root)
        raise


def publication_status(*, root: Path = ROOT) -> dict:
    rows = []
    for record in research_actions.iter_actions(root=root):
        git_status = record.get("git", {}).get("status")
        if git_status in {"pending", "committed_not_pushed"}:
            rows.append(
                {
                    "action_id": record["action_id"],
                    "state": record["state"],
                    "git_status": git_status,
                    "commit": record.get("git", {}).get("commit"),
                    "path_count": len(record.get("git", {}).get("eligible_paths") or []),
                }
            )
    return {
        "status": "ok",
        "counts": research_actions.count_action_states(root=root),
        "actions": rows,
    }


def publish_pending_actions(
    *,
    root: Path = ROOT,
    dry_run: bool = False,
    after_commit: Callable[[dict, str], None] | None = None,
) -> dict:
    """Commit each pending action separately, then push the explained chain once."""

    try:
        preflight = _preflight(root)
        already_pushed = _mark_already_pushed(
            root=root, remote=preflight["remote"], dry_run=dry_run
        )
        explained = _reconcile_ahead(
            preflight["ahead"], root=root, dry_run=dry_run
        )
        records = [
            record
            for record in research_actions.iter_actions(root=root)
            if record["state"] == "applied"
            and record.get("git", {}).get("status") == "pending"
        ]
        records.sort(key=lambda item: (item.get("applied_at") or item["created_at"]))
        if dry_run:
            for record in records:
                _validate_action_worktree(record, root=root)
            return {
                "status": "dry_run",
                "would_commit": [record["action_id"] for record in records],
                "would_push_existing": [item["action_id"] for item in explained],
                "already_pushed": already_pushed,
            }

        committed = []
        for record in records:
            committed.append(
                _commit_action(record, root=root, after_commit=after_commit)
            )

        head = _git_text(["rev-parse", "HEAD"], root=root)
        remote = _git_text(["rev-parse", "origin/master"], root=root)
        if head == remote:
            return {
                "status": "nothing_to_push",
                "committed": committed,
                "already_pushed": already_pushed,
            }

        # Re-run the explanation check after new commits and before the one batch push.
        ahead = _git_text(
            ["rev-list", "--reverse", "origin/master..HEAD"], root=root
        ).splitlines()
        _reconcile_ahead([item for item in ahead if item], root=root, dry_run=False)
        pushed = _run_git(["push", "origin", "master"], root=root, timeout=90)
        if pushed.returncode != 0:
            return {
                "status": "committed_not_pushed",
                "committed": committed,
                "push_error": pushed.stderr.strip() or "git push failed",
            }
        fetched = _run_git(["fetch", "origin", "master"], root=root, timeout=60)
        if fetched.returncode != 0:
            return {
                "status": "committed_not_pushed",
                "committed": committed,
                "push_error": "push returned success but origin/master verification failed",
            }
        remote_after = _git_text(["rev-parse", "origin/master"], root=root)
        if remote_after != head:
            return {
                "status": "committed_not_pushed",
                "committed": committed,
                "push_error": "origin/master does not match the pushed HEAD",
            }
        pushed_actions = []
        for record in research_actions.iter_actions(root=root):
            if record["state"] != "committed_not_pushed":
                continue
            commit = record.get("git", {}).get("commit")
            if commit and _is_ancestor(commit, remote_after, root=root):
                _mark_pushed(record["action_id"], commit, root=root)
                pushed_actions.append(record["action_id"])
        return {
            "status": "pushed",
            "committed": committed,
            "pushed_actions": pushed_actions,
            "commit_count": len(ahead),
        }
    except PublicationError as exc:
        return {"status": "rejected", "reason": exc.code, "detail": exc.detail}
