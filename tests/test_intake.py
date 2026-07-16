"""Safe provenance publication and git-ledger primitives."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from mcp_server import intake
from mcp_server import graph_mcp


def _extraction(
    doc_id: str = "valid_doc",
    *,
    permission: str = "repo_full",
    basis: str = "Official public filing retained for private research",
) -> dict:
    return {
        "schema_version": "0.1",
        "source_doc": {
            "doc_id": doc_id,
            "title": "Test document",
            "source_type": "filing",
            "evidence_tier": 1,
            "origin_entity": "Test Issuer",
            "storage_permission": permission,
            "permission_basis": basis,
        },
        "sources": [],
        "nodes": [],
        "edges": [],
        "claims": [],
    }


def _publish_loaded(
    doc_id: str,
    *,
    root: Path,
    raw_text: str | None = None,
    permission: str = "repo_full",
    basis: str = "Official public filing retained for private research",
) -> dict:
    extraction = _extraction(
        doc_id, permission=permission, basis=basis
    )
    result = intake.publish_provenance(
        doc_id,
        extraction,
        {"raw_text": raw_text} if raw_text is not None else {},
        root=root,
    )
    intake.mark_graph_complete(doc_id, extraction, root=root)
    return result


@pytest.mark.parametrize(
    "value",
    ["", "../evil", "..\\evil", "C:evil", "C:\\evil", "/evil", "has/slash", "has space", "中文"],
)
def test_doc_id_and_action_slug_reject_path_capabilities(value: str) -> None:
    with pytest.raises(ValueError):
        intake.validate_doc_id(value)
    with pytest.raises(ValueError):
        intake.validate_action_slug(value)


def test_storage_permission_requires_real_basis_not_paid_or_free_label() -> None:
    assert intake.validate_storage_permission(
        "repo_full", "Paid license explicitly permits private-cloud archive"
    ) == "repo_full"
    for basis in ("", "paid", "已付費", "free", "免費"):
        with pytest.raises(ValueError):
            intake.validate_storage_permission("repo_full", basis)
    with pytest.raises(ValueError):
        intake.validate_storage_permission("unknown", "Some detailed permission")


def test_url_sanitization_rejects_credentials_and_removes_secret_queries() -> None:
    with pytest.raises(ValueError):
        intake.sanitize_source_url("https://user:pass@example.com/report")
    cleaned = intake.sanitize_source_url(
        "https://example.com/report?lang=en&token=secret&X-Amz-Signature=abc#page"
    )
    assert cleaned == "https://example.com/report?lang=en"


def test_canonical_extraction_hash_ignores_key_order() -> None:
    left = {"b": 2, "a": {"y": 2, "x": 1}}
    right = {"a": {"x": 1, "y": 2}, "b": 2}

    assert intake.canonical_extraction_hash(left) == intake.canonical_extraction_hash(right)
    right["b"] = 3
    assert intake.canonical_extraction_hash(left) != intake.canonical_extraction_hash(right)


def test_repo_full_text_limit_and_repo_excerpt_policy(tmp_path: Path) -> None:
    full = _extraction()
    result = intake.publish_provenance(
        "valid_doc", full, {"raw_text": "licensed full text"}, root=tmp_path
    )
    assert result["status"] == "published"
    assert (tmp_path / "library" / "raw" / "valid_doc.txt").read_text(
        encoding="utf-8"
    ) == "licensed full text"

    too_large = _extraction("large_doc")
    with pytest.raises(ValueError, match="200,000|200000"):
        intake.publish_provenance(
            "large_doc", too_large, {"raw_text": "x" * 200_001}, root=tmp_path
        )

    excerpt = _extraction(
        "excerpt_doc",
        permission="repo_excerpt",
        basis="Publisher terms permit limited research excerpts only",
    )
    with pytest.raises(ValueError):
        intake.publish_provenance(
            "excerpt_doc", excerpt, {"raw_text": "full text"}, root=tmp_path
        )
    with pytest.raises(ValueError):
        intake.publish_provenance(
            "excerpt_doc", excerpt, {"raw_url": "https://example.com/report"}, root=tmp_path
        )
    published = intake.publish_provenance(
        "excerpt_doc",
        excerpt,
        {"raw_url": "https://example.com/report?token=secret", "raw_excerpt": "short quote"},
        root=tmp_path,
    )
    raw = (tmp_path / "library" / "raw" / "excerpt_doc.txt").read_text(encoding="utf-8")
    assert published["status"] == "published"
    assert "token" not in raw
    assert "short quote" in raw


def test_raw_payload_rejects_headers_or_cookies(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cookie|header|credential"):
        intake.publish_provenance(
            "valid_doc",
            _extraction(),
            {"raw_url": "https://example.com", "raw_excerpt": "quote", "cookies": "secret"},
            root=tmp_path,
        )


def test_local_only_routes_both_artifacts_outside_git_ledger(tmp_path: Path) -> None:
    extraction = _extraction(
        "private_doc",
        permission="local_only",
        basis="Source terms do not permit third-party cloud storage",
    )

    result = intake.publish_provenance(
        "private_doc", extraction, {"raw_text": "private text"}, root=tmp_path
    )

    assert result["finalize_eligible"] is False
    assert (tmp_path / "library" / "private" / "extractions" / "private_doc.json").exists()
    assert (tmp_path / "library" / "private" / "raw" / "private_doc.txt").exists()
    assert not (tmp_path / "extractions" / "private_doc.json").exists()


def test_same_doc_is_matching_but_changed_extraction_or_raw_conflicts(tmp_path: Path) -> None:
    extraction = _extraction()
    raw = {"raw_text": "same"}
    intake.publish_provenance("valid_doc", extraction, raw, root=tmp_path)

    assert intake.inspect_provenance("valid_doc", extraction, raw, root=tmp_path)["status"] == "matching"

    changed = json.loads(json.dumps(extraction))
    changed["source_doc"]["title"] = "Changed"
    assert intake.inspect_provenance("valid_doc", changed, raw, root=tmp_path)["status"] == "conflict"
    assert intake.inspect_provenance(
        "valid_doc", extraction, {"raw_text": "changed"}, root=tmp_path
    )["status"] == "conflict"
    assert json.loads((tmp_path / "extractions" / "valid_doc.json").read_text(encoding="utf-8")) == extraction


def test_partial_publish_is_completed_by_identical_retry(tmp_path: Path, monkeypatch) -> None:
    extraction = _extraction()
    raw = {"raw_text": "same"}
    real_publish = intake._atomic_publish

    def fail_raw(path: Path, content: str) -> None:
        if path.parent.name == "raw":
            raise OSError("simulated raw failure")
        real_publish(path, content)

    monkeypatch.setattr(intake, "_atomic_publish", fail_raw)
    with pytest.raises(OSError, match="simulated"):
        intake.publish_provenance("valid_doc", extraction, raw, root=tmp_path)
    assert (tmp_path / "extractions" / "valid_doc.json").exists()
    assert not (tmp_path / "library" / "raw" / "valid_doc.txt").exists()

    monkeypatch.setattr(intake, "_atomic_publish", real_publish)
    result = intake.publish_provenance("valid_doc", extraction, raw, root=tmp_path)
    assert result["status"] == "published"
    assert (tmp_path / "library" / "raw" / "valid_doc.txt").exists()


def test_resolve_action_paths_is_manifest_scoped_and_rejects_local_only(tmp_path: Path) -> None:
    _publish_loaded("doc_a", root=tmp_path, raw_text="A")
    _publish_loaded("doc_b", root=tmp_path, raw_text="B")
    resolved = intake.resolve_action_paths(["doc_b"], root=tmp_path)
    assert resolved["paths"] == ["extractions/doc_b.json", "library/raw/doc_b.txt"]

    intake.publish_provenance(
        "private_doc",
        _extraction(
            "private_doc",
            permission="local_only",
            basis="No third-party cloud storage permission",
        ),
        {"raw_text": "private"},
        root=tmp_path,
    )
    with pytest.raises(ValueError, match="local_only"):
        intake.resolve_action_paths(["doc_b", "private_doc"], root=tmp_path)


@pytest.mark.parametrize(("first", "second"), [("repo_full", "local_only"), ("local_only", "repo_full")])
def test_doc_id_cannot_cross_storage_roots(
    tmp_path: Path, first: str, second: str
) -> None:
    bases = {
        "repo_full": "Official filing may be retained",
        "local_only": "No third-party cloud storage permission",
    }
    intake.publish_provenance(
        "same_doc",
        _extraction("same_doc", permission=first, basis=bases[first]),
        {"raw_text": "same"},
        root=tmp_path,
    )

    with pytest.raises(ValueError, match="provenance conflict"):
        intake.publish_provenance(
            "same_doc",
            _extraction("same_doc", permission=second, basis=bases[second]),
            {"raw_text": "same"},
            root=tmp_path,
        )


def test_write_report_validates_slug_and_never_overwrites(tmp_path: Path) -> None:
    paths = [intake.write_report("same-slug", "report", root=tmp_path) for _ in range(3)]

    assert [path.name for path in paths] == [
        f"{paths[0].name}",
        paths[0].name.replace(".md", "-2.md"),
        paths[0].name.replace(".md", "-3.md"),
    ]
    assert all(path.resolve().is_relative_to((tmp_path / "library" / "intake").resolve()) for path in paths)
    assert "intake_recorded_at" in paths[0].read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        intake.write_report("../evil", "report", root=tmp_path)


def _commit_all(repo: Path, message: str = "baseline") -> None:
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo, check=True, capture_output=True)


def test_pending_intake_files_separates_untracked_and_modified(tmp_git_repo: Path) -> None:
    for relative in ("library/raw", "extractions", "library/intake"):
        (tmp_git_repo / relative).mkdir(parents=True, exist_ok=True)
    tracked = tmp_git_repo / "extractions" / "tracked.json"
    tracked.write_text("{}", encoding="utf-8")
    (tmp_git_repo / "outside.txt").write_text("outside", encoding="utf-8")
    _commit_all(tmp_git_repo)
    tracked.write_text('{"changed": true}', encoding="utf-8")
    (tmp_git_repo / "library" / "raw" / "new.txt").write_text("new", encoding="utf-8")
    (tmp_git_repo / "other.txt").write_text("ignore", encoding="utf-8")

    pending = intake.pending_intake_files(root=tmp_git_repo)

    assert pending["modified"] == ["extractions/tracked.json"]
    assert pending["untracked"] == ["library/raw/new.txt"]


def test_production_gitignore_exposes_eligible_ledger_files_but_keeps_local_only_legacy_private(
    tmp_git_repo: Path,
) -> None:
    production_ignore = (intake.ROOT / ".gitignore").read_text(encoding="utf-8")
    migration = json.loads(
        (intake.ROOT / "loader/manifests/legacy-storage-permission-migration.json").read_text(
            encoding="utf-8"
        )
    )
    (tmp_git_repo / ".gitignore").write_text(production_ignore, encoding="utf-8")
    for relative in ("library/raw", "extractions", "library/intake", "library/private"):
        (tmp_git_repo / relative).mkdir(parents=True, exist_ok=True)
    (tmp_git_repo / "baseline.txt").write_text("base", encoding="utf-8")
    _commit_all(tmp_git_repo)
    (tmp_git_repo / "extractions" / "new_doc.json").write_text("{}", encoding="utf-8")
    (tmp_git_repo / "library" / "raw" / "new_doc.txt").write_text("new", encoding="utf-8")
    (tmp_git_repo / "library" / "raw" / "new_doc.meta.json").write_text(
        "{}", encoding="utf-8"
    )
    artifacts = migration["documents"] + migration["raw_artifacts"]
    for artifact in artifacts:
        path = tmp_git_repo / artifact["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture", encoding="utf-8")
    (tmp_git_repo / "library" / "private" / "secret.txt").write_text("secret", encoding="utf-8")

    pending = intake.pending_intake_files(root=tmp_git_repo)

    expected = {"extractions/new_doc.json", "library/raw/new_doc.txt"}
    expected.update(artifact["path"] for artifact in artifacts if artifact["git_eligible"])
    assert pending["untracked"] == sorted(expected)


def test_legacy_storage_permission_migration_reconciles_tracked_artifacts() -> None:
    migration = json.loads(
        (intake.ROOT / "loader/manifests/legacy-storage-permission-migration.json").read_text(
            encoding="utf-8"
        )
    )
    before = json.loads(
        (intake.ROOT / migration["pre_migration_manifest"]).read_text(encoding="utf-8")
    )
    before_by_path = {item["path"]: item for item in before["documents"]}

    for document in migration["documents"]:
        assert document["before_sha256"] == before_by_path[document["path"]]["sha256"]
        assert document["git_eligible"] is (document["storage_permission"] != "local_only")
        path = intake.ROOT / document["path"]
        if not document["git_eligible"] and not path.exists():
            continue
        extraction = json.loads(path.read_text(encoding="utf-8"))
        source_doc = extraction["source_doc"]
        assert source_doc["storage_permission"] == document["storage_permission"]
        intake.validate_storage_permission(
            source_doc["storage_permission"], source_doc["permission_basis"]
        )
        content = path.read_bytes()
        if document["git_eligible"]:
            content = content.replace(b"\r\n", b"\n")
        assert hashlib.sha256(content).hexdigest() == document["after_sha256"]
        validation = subprocess.run(
            [sys.executable, "loader/validate.py", str(path)],
            cwd=intake.ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert validation.returncode == 0, validation.stdout + validation.stderr

    for artifact in migration["raw_artifacts"]:
        assert artifact["git_eligible"] is (artifact["storage_permission"] != "local_only")
        path = intake.ROOT / artifact["path"]
        if not artifact["git_eligible"] and not path.exists():
            continue
        content = path.read_bytes()
        if artifact["git_eligible"]:
            content = content.replace(b"\r\n", b"\n")
        assert hashlib.sha256(content).hexdigest() == artifact["sha256"]


def _add_bare_remote(repo: Path, remote: Path) -> None:
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=repo, check=True)
    subprocess.run(["git", "push", "-u", "origin", "master"], cwd=repo, check=True, capture_output=True)


def test_git_preflight_requires_master_clean_index_and_synced_head(
    tmp_git_repo: Path, tmp_path: Path
) -> None:
    (tmp_git_repo / "baseline.txt").write_text("base", encoding="utf-8")
    _commit_all(tmp_git_repo)
    _add_bare_remote(tmp_git_repo, tmp_path / "remote.git")
    assert intake.git_preflight(root=tmp_git_repo)["ok"] is True

    (tmp_git_repo / "staged.txt").write_text("staged", encoding="utf-8")
    subprocess.run(["git", "add", "staged.txt"], cwd=tmp_git_repo, check=True)
    failed = intake.git_preflight(root=tmp_git_repo)
    assert failed["ok"] is False
    assert failed["reason"] == "index_not_clean"


def test_git_preflight_rejects_non_master(tmp_git_repo: Path) -> None:
    (tmp_git_repo / "baseline.txt").write_text("base", encoding="utf-8")
    _commit_all(tmp_git_repo)
    subprocess.run(["git", "switch", "-c", "feature"], cwd=tmp_git_repo, check=True, capture_output=True)

    result = intake.git_preflight(root=tmp_git_repo)

    assert result["ok"] is False
    assert result["reason"] == "not_master"


def test_git_preflight_rejects_head_ahead_of_remote(
    tmp_git_repo: Path, tmp_path: Path
) -> None:
    _ready_remote_repo(tmp_git_repo, tmp_path / "remote.git")
    (tmp_git_repo / "ahead.txt").write_text("ahead", encoding="utf-8")
    _commit_all(tmp_git_repo, "ahead")

    result = intake.git_preflight(root=tmp_git_repo)

    assert result["ok"] is False
    assert result["reason"] == "head_not_synced"


def _push_remote_commit(remote: Path, clone: Path, filename: str) -> None:
    subprocess.run(["git", "clone", str(remote), str(clone)], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Remote Tests"], cwd=clone, check=True)
    subprocess.run(["git", "config", "user.email", "remote@stockbot.invalid"], cwd=clone, check=True)
    (clone / filename).write_text(filename, encoding="utf-8")
    _commit_all(clone, filename)
    subprocess.run(["git", "push", "origin", "master"], cwd=clone, check=True, capture_output=True)


def test_git_preflight_rejects_head_behind_or_diverged(
    tmp_git_repo: Path, tmp_path: Path
) -> None:
    remote = tmp_path / "remote.git"
    _ready_remote_repo(tmp_git_repo, remote)
    _push_remote_commit(remote, tmp_path / "other", "remote.txt")

    behind = intake.git_preflight(root=tmp_git_repo)
    assert behind["ok"] is False
    assert behind["reason"] == "head_not_synced"

    (tmp_git_repo / "local.txt").write_text("local", encoding="utf-8")
    _commit_all(tmp_git_repo, "local")
    diverged = intake.git_preflight(root=tmp_git_repo)
    assert diverged["ok"] is False
    assert diverged["reason"] == "head_not_synced"


def test_git_preflight_fetch_failure_is_fail_closed(
    tmp_git_repo: Path, tmp_path: Path
) -> None:
    _ready_remote_repo(tmp_git_repo, tmp_path / "remote.git")
    subprocess.run(
        ["git", "remote", "set-url", "origin", str(tmp_path / "missing.git")],
        cwd=tmp_git_repo,
        check=True,
    )

    result = intake.git_preflight(root=tmp_git_repo)

    assert result["ok"] is False
    assert result["reason"] == "fetch_failed"


def test_commit_and_push_uses_exact_paths_and_preserves_commit_on_push_failure(
    tmp_git_repo: Path, tmp_path: Path
) -> None:
    (tmp_git_repo / "baseline.txt").write_text("base", encoding="utf-8")
    _commit_all(tmp_git_repo)
    remote = tmp_path / "remote.git"
    _add_bare_remote(tmp_git_repo, remote)
    (tmp_git_repo / "extractions").mkdir()
    (tmp_git_repo / "extractions" / "included.json").write_text("{}", encoding="utf-8")
    (tmp_git_repo / "extractions" / "leftover.json").write_text("{}", encoding="utf-8")

    subprocess.run(["git", "remote", "set-url", "--push", "origin", str(tmp_path / "missing.git")], cwd=tmp_git_repo, check=True)
    result = intake.commit_and_push(
        ["extractions/included.json"],
        "record evidence; no shell expansion $(ignored)",
        root=tmp_git_repo,
    )

    assert result["status"] == "committed_not_pushed"
    shown = subprocess.run(
        ["git", "show", "--pretty=", "--name-only", "HEAD"],
        cwd=tmp_git_repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert shown == ["extractions/included.json"]
    assert (tmp_git_repo / "extractions" / "leftover.json").exists()


def test_commit_failure_unstages_only_finalize_paths(tmp_path: Path, monkeypatch) -> None:
    calls = []

    def fake_git(args, *, root, timeout=None):
        calls.append(args)
        if args[:2] == ["commit", "-m"]:
            return subprocess.CompletedProcess(args, 1, "", "hook rejected")
        if args == ["rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(args, 0, "same-head\n", "")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(
        intake,
        "git_preflight",
        lambda **_kwargs: {"ok": True, "head": "same-head", "reason": None},
    )
    monkeypatch.setattr(intake, "_run_git", fake_git)

    result = intake.commit_and_push(
        ["extractions/included.json"], "rejected commit", root=tmp_path
    )

    assert result["status"] == "not_committed"
    assert ["restore", "--staged", "--", "extractions/included.json"] in calls


def test_intake_payloads_have_explicit_size_limits(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="permission_basis"):
        intake.publish_provenance(
            "basis_too_large",
            _extraction("basis_too_large", basis="x" * (intake.MAX_PERMISSION_BASIS_CHARS + 1)),
            {},
            root=tmp_path,
        )
    with pytest.raises(ValueError, match="2,000,000"):
        intake.publish_provenance(
            "raw_too_large",
            _extraction(
                "raw_too_large",
                permission="local_only",
                basis="No cloud storage permission",
            ),
            {"raw_text": "x" * (intake.MAX_LOCAL_RAW_CHARS + 1)},
            root=tmp_path,
        )
    with pytest.raises(ValueError, match="50,000"):
        intake.publish_provenance(
            "excerpt_too_large",
            _extraction(
                "excerpt_too_large",
                permission="repo_excerpt",
                basis="Publisher permits limited excerpts",
            ),
            {
                "raw_url": "https://example.com/report",
                "raw_excerpt": "x" * (intake.MAX_EXCERPT_CHARS + 1),
            },
            root=tmp_path,
        )
    with pytest.raises(ValueError, match="200,000"):
        intake.write_report(
            "large-report", "x" * (intake.MAX_REPORT_CHARS + 1), root=tmp_path
        )


class _FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute_write(self, callback):
        return callback(self)


class _FakeDriver:
    def session(self):
        return _FakeSession()

    def close(self):
        return None


def test_graph_write_readiness_requires_version_and_reconciliation() -> None:
    class Result:
        def __init__(self, value):
            self.value = value

        def single(self):
            return self.value

    class Session(_FakeSession):
        def __init__(self, version, counts):
            self.version = version
            self.counts = iter(counts)

        def run(self, query):
            if "GraphSchemaState" in query:
                return Result({"version": self.version})
            return Result({"count": next(self.counts)})

    class Driver:
        def __init__(self, version, counts):
            self.version = version
            self.counts = counts

        def session(self, **_kwargs):
            return Session(self.version, self.counts)

    graph_mcp._check_graph_write_readiness(
        Driver(graph_mcp.GRAPH_SCHEMA_VERSION, [0, 0, 0])
    )

    with pytest.raises(RuntimeError, match="schema is not ready"):
        graph_mcp._check_graph_write_readiness(Driver("old", [0, 0, 0]))
    with pytest.raises(RuntimeError, match="reconciliation is incomplete"):
        graph_mcp._check_graph_write_readiness(
            Driver(graph_mcp.GRAPH_SCHEMA_VERSION, [1, 0, 0])
        )


def _install_graph_success(monkeypatch, *, conflicts: list[str] | None = None) -> None:
    monkeypatch.setattr(graph_mcp, "_driver", lambda: _FakeDriver())
    monkeypatch.setattr(graph_mcp, "_check_graph_write_readiness", lambda _driver: None)
    monkeypatch.setattr(graph_mcp, "load_to_graph", lambda _doc, _session: None)
    monkeypatch.setattr(graph_mcp, "_verify_loaded_doc", lambda _driver, _doc: None)
    monkeypatch.setattr(
        graph_mcp,
        "project_edge_keys",
        lambda _driver, _keys: {
            "open_conflict_ids": conflicts or [],
            "stale_resolution_ids": [],
        },
    )


def test_load_extraction_publishes_before_graph_and_supports_extraction_only(
    tmp_path: Path, monkeypatch
) -> None:
    _install_graph_success(monkeypatch)

    result = graph_mcp._load_extraction_impl(
        json.dumps(_extraction("remote_doc")),
        "repo_full",
        "Official public filing retained for private research",
        root=tmp_path,
    )

    assert result["status"] == "loaded_or_already_complete"
    assert result["finalize_eligible"] is True
    assert (tmp_path / "extractions" / "remote_doc.json").exists()
    assert not (tmp_path / "library" / "raw" / "remote_doc.txt").exists()


@pytest.mark.parametrize("payload", ["null", "[]", '"text"', "42", "true"])
def test_load_extraction_rejects_non_object_json_before_driver(
    payload: str, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        graph_mcp, "_driver", lambda: (_ for _ in ()).throw(AssertionError())
    )

    result = graph_mcp._load_extraction_impl(
        payload,
        "repo_full",
        "Official public filing retained for private research",
        root=tmp_path,
    )

    assert result["status"] == "rejected"
    assert "object" in result["error"]


def test_load_extraction_uses_one_graph_write_transaction(
    tmp_path: Path, monkeypatch
) -> None:
    calls = []

    class TransactionSession(_FakeSession):
        def execute_write(self, callback):
            calls.append("execute_write")
            return callback(self)

    class TransactionDriver(_FakeDriver):
        def session(self):
            return TransactionSession()

    monkeypatch.setattr(graph_mcp, "_driver", lambda: TransactionDriver())
    monkeypatch.setattr(graph_mcp, "_check_graph_write_readiness", lambda _driver: None)
    monkeypatch.setattr(graph_mcp, "load_to_graph", lambda _doc, _tx: calls.append("load"))
    monkeypatch.setattr(graph_mcp, "_verify_loaded_doc", lambda _driver, _doc: None)
    monkeypatch.setattr(
        graph_mcp,
        "project_edge_keys",
        lambda _driver, _keys: {"open_conflict_ids": [], "stale_resolution_ids": []},
    )

    result = graph_mcp._load_extraction_impl(
        json.dumps(_extraction("transaction_doc")),
        "repo_full",
        "Official public filing retained for private research",
        root=tmp_path,
    )

    assert result["status"] == "loaded_or_already_complete"
    assert calls == ["execute_write", "load"]


def test_load_extraction_rejects_changed_same_doc_before_driver(
    tmp_path: Path, monkeypatch
) -> None:
    _install_graph_success(monkeypatch)
    first = _extraction("remote_doc")
    assert graph_mcp._load_extraction_impl(
        json.dumps(first),
        "repo_full",
        "Official public filing retained for private research",
        raw_text="same raw",
        root=tmp_path,
    )["status"] == "loaded_or_already_complete"

    changed = _extraction("remote_doc")
    changed["source_doc"]["title"] = "changed"

    def forbidden_driver():
        raise AssertionError("Neo4j driver must not be created for a provenance conflict")

    monkeypatch.setattr(graph_mcp, "_driver", forbidden_driver)
    rejected = graph_mcp._load_extraction_impl(
        json.dumps(changed),
        "repo_full",
        "Official public filing retained for private research",
        raw_text="same raw",
        root=tmp_path,
    )
    assert rejected["status"] == "rejected"
    assert "conflict" in rejected["error"]


def test_load_extraction_graph_failure_is_recoverable_with_identical_payload(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(graph_mcp, "_driver", lambda: _FakeDriver())
    monkeypatch.setattr(graph_mcp, "_check_graph_write_readiness", lambda _driver: None)

    def fail_graph(_doc, _session):
        raise RuntimeError("simulated graph outage")

    monkeypatch.setattr(graph_mcp, "load_to_graph", fail_graph)
    payload = json.dumps(_extraction("retry_doc"))
    pending = graph_mcp._load_extraction_impl(
        payload,
        "repo_full",
        "Official public filing retained for private research",
        raw_text="recoverable",
        root=tmp_path,
    )
    assert pending["status"] == "pending_graph"
    assert pending["finalize_eligible"] is False
    assert (tmp_path / "extractions" / "retry_doc.json").exists()
    assert (tmp_path / "library" / "raw" / "retry_doc.txt").exists()

    _install_graph_success(monkeypatch)
    retried = graph_mcp._load_extraction_impl(
        payload,
        "repo_full",
        "Official public filing retained for private research",
        raw_text="recoverable",
        root=tmp_path,
    )
    assert retried["status"] == "loaded_or_already_complete"


def test_pending_graph_document_cannot_finalize(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(graph_mcp, "_driver", lambda: _FakeDriver())
    monkeypatch.setattr(graph_mcp, "_check_graph_write_readiness", lambda _driver: None)
    monkeypatch.setattr(
        graph_mcp,
        "load_to_graph",
        lambda _doc, _tx: (_ for _ in ()).throw(RuntimeError("graph down")),
    )
    pending = graph_mcp._load_extraction_impl(
        json.dumps(_extraction("pending_doc")),
        "repo_full",
        "Official public filing retained for private research",
        raw_text="pending",
        root=tmp_path,
    )

    result = graph_mcp._finalize_research_action_impl(
        _valid_report(),
        "pending-doc",
        "must not commit",
        ["pending_doc"],
        root=tmp_path,
        enabled=True,
    )

    assert pending["status"] == "pending_graph"
    assert result["git_status"] == "not_committed"
    assert "completion receipt" in result["reason"]


def test_load_extraction_returns_conflicts_without_treating_document_as_failed(
    tmp_path: Path, monkeypatch
) -> None:
    _install_graph_success(monkeypatch, conflicts=["conflict:sole_source"])

    loaded = graph_mcp._load_extraction_impl(
        json.dumps(_extraction("conflict_doc")),
        "repo_excerpt",
        "Publisher terms permit limited research excerpts only",
        raw_url="https://example.com/report?token=secret",
        raw_excerpt="auditable quote",
        root=tmp_path,
    )

    assert loaded["status"] == "loaded_or_already_complete"
    assert loaded["open_conflict_ids"] == ["conflict:sole_source"]
    stored = json.loads(
        (tmp_path / "extractions" / "conflict_doc.json").read_text(encoding="utf-8")
    )
    assert stored["source_doc"]["url"] == "https://example.com/report"


def test_load_extraction_local_only_loads_graph_but_cannot_finalize(
    tmp_path: Path, monkeypatch
) -> None:
    _install_graph_success(monkeypatch)

    loaded = graph_mcp._load_extraction_impl(
        json.dumps(_extraction("private_remote")),
        "local_only",
        "Source terms do not permit third-party cloud storage",
        raw_text="private source",
        root=tmp_path,
    )

    assert loaded["status"] == "loaded_or_already_complete"
    assert loaded["finalize_eligible"] is False
    assert (tmp_path / "library" / "private" / "raw" / "private_remote.txt").exists()


def test_load_extraction_invalid_doc_id_and_permission_fail_before_graph(
    tmp_path: Path, monkeypatch
) -> None:
    def forbidden_driver():
        raise AssertionError("driver must not be created")

    monkeypatch.setattr(graph_mcp, "_driver", forbidden_driver)
    invalid_id = graph_mcp._load_extraction_impl(
        json.dumps(_extraction("../evil")),
        "repo_full",
        "Official public filing retained for private research",
        root=tmp_path,
    )
    assert invalid_id["status"] == "rejected"

    invalid_permission = graph_mcp._load_extraction_impl(
        json.dumps(_extraction("safe_doc")),
        "repo_excerpt",
        "",
        raw_text="forbidden full text",
        root=tmp_path,
    )
    assert invalid_permission["status"] == "rejected"


def _valid_report() -> str:
    return """# Intake report

## 為何此時入圖
New primary evidence.

## 文件清單
Server will append verified metadata.

## 搜尋過程摘要
Traced from SEC and customer IR.

## L8 確認備註
Origins remain independently counted.
"""


def _ready_remote_repo(repo: Path, remote: Path) -> None:
    (repo / "baseline.txt").write_text("base", encoding="utf-8")
    _commit_all(repo)
    _add_bare_remote(repo, remote)


def test_finalize_two_documents_creates_one_exact_commit_and_push(
    tmp_git_repo: Path, tmp_path: Path
) -> None:
    _ready_remote_repo(tmp_git_repo, tmp_path / "remote.git")
    for doc_id in ("doc_a", "doc_b"):
        _publish_loaded(doc_id, root=tmp_git_repo, raw_text=f"raw {doc_id}")

    result = graph_mcp._finalize_research_action_impl(
        _valid_report(),
        "two-docs",
        "record traced evidence",
        ["doc_a", "doc_b"],
        root=tmp_git_repo,
        enabled=True,
    )

    assert result["git_status"] == "committed+pushed"
    shown = subprocess.run(
        ["git", "show", "--pretty=", "--name-only", "HEAD"],
        cwd=tmp_git_repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert sorted(shown) == sorted(
        [
            "extractions/doc_a.json",
            "extractions/doc_b.json",
            "library/raw/doc_a.txt",
            "library/raw/doc_b.txt",
            result["report_path"],
        ]
    )
    report = (tmp_git_repo / result["report_path"]).read_text(encoding="utf-8")
    assert "repo_full" in report
    assert "Official public filing" in report


def test_finalize_is_manifest_scoped_and_warns_about_other_pending_files(
    tmp_git_repo: Path, tmp_path: Path
) -> None:
    _ready_remote_repo(tmp_git_repo, tmp_path / "remote.git")
    for doc_id in ("leftover", "selected"):
        _publish_loaded(doc_id, root=tmp_git_repo, raw_text=doc_id)

    result = graph_mcp._finalize_research_action_impl(
        _valid_report(),
        "selected-only",
        "record selected evidence",
        ["selected"],
        root=tmp_git_repo,
        enabled=True,
    )

    assert result["git_status"] == "committed+pushed"
    assert "extractions/leftover.json" in result["pending_warning"]["untracked"]
    assert (tmp_git_repo / "extractions" / "leftover.json").exists()


def test_finalize_preflight_failure_writes_no_report(
    tmp_git_repo: Path, tmp_path: Path
) -> None:
    _ready_remote_repo(tmp_git_repo, tmp_path / "remote.git")
    _publish_loaded("doc_a", root=tmp_git_repo, raw_text="A")
    (tmp_git_repo / "staged.txt").write_text("staged", encoding="utf-8")
    subprocess.run(["git", "add", "staged.txt"], cwd=tmp_git_repo, check=True)

    result = graph_mcp._finalize_research_action_impl(
        _valid_report(),
        "blocked",
        "must not commit",
        ["doc_a"],
        root=tmp_git_repo,
        enabled=True,
    )

    assert result["git_status"] == "not_committed"
    assert result["reason"] == "index_not_clean"
    assert not list((tmp_git_repo / "library" / "intake").glob("*.md"))


def test_finalize_propagates_second_preflight_failure(
    tmp_git_repo: Path, monkeypatch
) -> None:
    _publish_loaded("doc_a", root=tmp_git_repo, raw_text="A")
    monkeypatch.setattr(
        graph_mcp,
        "git_preflight",
        lambda **_kwargs: {"ok": True, "reason": None},
    )
    monkeypatch.setattr(
        graph_mcp,
        "pending_intake_files",
        lambda **_kwargs: {"untracked": [], "modified": [], "error": None},
    )
    monkeypatch.setattr(
        graph_mcp,
        "commit_and_push",
        lambda *_args, **_kwargs: {
            "status": "not_committed",
            "paths": [],
            "preflight": {"ok": False, "reason": "head_not_synced", "detail": "moved"},
        },
    )

    result = graph_mcp._finalize_research_action_impl(
        _valid_report(),
        "second-preflight",
        "must remain pending",
        ["doc_a"],
        root=tmp_git_repo,
        enabled=True,
    )

    assert result["git_status"] == "not_committed"
    assert result["error"] == "head_not_synced"
    assert result["detail"] == "moved"


def test_finalize_rejects_malicious_slug_and_local_only_before_report(
    tmp_git_repo: Path, tmp_path: Path
) -> None:
    _ready_remote_repo(tmp_git_repo, tmp_path / "remote.git")
    intake.publish_provenance(
        "private_doc",
        _extraction(
            "private_doc",
            permission="local_only",
            basis="No third-party cloud storage permission",
        ),
        {"raw_text": "private"},
        root=tmp_git_repo,
    )

    bad_slug = graph_mcp._finalize_research_action_impl(
        _valid_report(),
        "../evil",
        "must not commit",
        ["private_doc"],
        root=tmp_git_repo,
        enabled=True,
    )
    assert bad_slug["git_status"] == "not_committed"

    local_only = graph_mcp._finalize_research_action_impl(
        _valid_report(),
        "private",
        "must not commit",
        ["private_doc"],
        root=tmp_git_repo,
        enabled=True,
    )
    assert local_only["git_status"] == "not_committed"
    assert "local_only" in local_only["reason"]
    assert not list((tmp_git_repo / "library" / "intake").glob("*.md"))


def test_finalize_push_failure_keeps_local_commit(
    tmp_git_repo: Path, tmp_path: Path
) -> None:
    _ready_remote_repo(tmp_git_repo, tmp_path / "remote.git")
    _publish_loaded("doc_a", root=tmp_git_repo, raw_text="A")
    subprocess.run(
        ["git", "remote", "set-url", "--push", "origin", str(tmp_path / "missing.git")],
        cwd=tmp_git_repo,
        check=True,
    )

    result = graph_mcp._finalize_research_action_impl(
        _valid_report(),
        "push-fails",
        "retain local commit",
        ["doc_a"],
        root=tmp_git_repo,
        enabled=True,
    )

    assert result["git_status"] == "committed_not_pushed"
    assert result["commit"]


def test_finalize_is_disabled_by_default() -> None:
    result = graph_mcp._finalize_research_action_impl(
        _valid_report(),
        "disabled",
        "must not run",
        [],
        enabled=False,
    )

    assert result["git_status"] == "not_committed"
    assert result["reason"] == "remote_finalize_disabled"
