"""Filesystem and git safety primitives for remote research intake."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parent.parent
MAX_RAW_CHARS = 200_000
MAX_LOCAL_RAW_CHARS = 2_000_000
MAX_EXCERPT_CHARS = 50_000
MAX_EXTRACTION_CHARS = 1_000_000
MAX_PERMISSION_BASIS_CHARS = 2_000
MAX_REPORT_CHARS = 200_000
GRAPH_COMPLETION_SCHEMA = "1"
IDENTIFIER_RE = re.compile(r"^[a-z0-9_-]{1,64}$")
STORAGE_PERMISSIONS = {"repo_full", "repo_excerpt", "local_only"}
LEDGER_PREFIXES = ("library/raw/", "extractions/", "library/intake/")
SECRET_QUERY_KEYS = {"token", "access_token", "key", "sig", "signature", "auth"}
RAW_KEYS = {"raw_text", "raw_url", "raw_excerpt"}
FORBIDDEN_BASIS_ONLY = {
    "paid",
    "paid report",
    "已付費",
    "free",
    "free report",
    "免費",
    "publicly available",
}


def _validate_identifier(value: str, label: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"invalid {label}: use lowercase ASCII [a-z0-9_-], length 1-64")
    return value


def validate_doc_id(doc_id: str) -> str:
    return _validate_identifier(doc_id, "doc_id")


def validate_action_slug(slug: str) -> str:
    return _validate_identifier(slug, "action_slug")


def validate_storage_permission(permission: str, basis: str) -> str:
    if permission not in STORAGE_PERMISSIONS:
        raise ValueError(f"invalid storage_permission: {permission!r}")
    if not isinstance(basis, str) or not basis.strip():
        raise ValueError("permission_basis is required")
    if len(basis) > MAX_PERMISSION_BASIS_CHARS:
        raise ValueError("permission_basis exceeds 2,000 characters")
    if basis.strip().casefold() in FORBIDDEN_BASIS_ONLY:
        raise ValueError("permission_basis cannot be only a paid/free label")
    return permission


def sanitize_source_url(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise ValueError("raw_url must be a non-empty URL")
    parsed = urlsplit(url.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("raw_url must use http or https and include a hostname")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("raw_url must not contain username/password credentials")
    kept = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.casefold()
        if (
            lowered in SECRET_QUERY_KEYS
            or lowered.startswith("x-amz-")
            or lowered.startswith("x-goog-")
        ):
            continue
        kept.append((key, value))
    host = parsed.hostname.encode("idna").decode("ascii")
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urlunsplit(
        (parsed.scheme.lower(), host, parsed.path or "/", urlencode(kept), "")
    )


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_extraction_hash(extraction: dict) -> str:
    return hashlib.sha256(_canonical_json(extraction).encode("utf-8")).hexdigest()


def _normalise_raw_payload(permission: str, raw_payload: dict | None) -> dict:
    raw_payload = dict(raw_payload or {})
    extra = set(raw_payload) - RAW_KEYS
    if extra:
        raise ValueError(
            "raw payload must not contain cookie/header/credential fields: "
            f"{sorted(extra)}"
        )
    normalised = {
        key: value
        for key, value in raw_payload.items()
        if value is not None and value != ""
    }
    raw_text = normalised.get("raw_text")
    raw_url = normalised.get("raw_url")
    raw_excerpt = normalised.get("raw_excerpt")
    if raw_text is not None and (raw_url is not None or raw_excerpt is not None):
        raise ValueError("use raw_text or raw_url+raw_excerpt, not both")
    if raw_text is not None and not isinstance(raw_text, str):
        raise ValueError("raw_text must be a string")
    if raw_excerpt is not None and not isinstance(raw_excerpt, str):
        raise ValueError("raw_excerpt must be a string")
    if raw_url is not None:
        normalised["raw_url"] = sanitize_source_url(raw_url)
    if (raw_url is None) != (raw_excerpt is None):
        raise ValueError("raw_url and raw_excerpt must be provided together")

    if permission == "repo_full" and raw_text is not None and len(raw_text) > MAX_RAW_CHARS:
        raise ValueError(
            "raw_text exceeds 200,000 characters; use a sanitized URL and limited excerpt"
        )
    if permission == "repo_excerpt" and raw_text is not None:
        raise ValueError("repo_excerpt forbids full raw_text; use raw_url + raw_excerpt")
    if raw_text is not None and len(raw_text) > MAX_LOCAL_RAW_CHARS:
        raise ValueError("raw_text exceeds the 2,000,000 character intake limit")
    if raw_excerpt is not None and len(raw_excerpt) > MAX_EXCERPT_CHARS:
        raise ValueError("raw_excerpt exceeds 50,000 characters")
    return normalised


def _raw_artifact_text(raw_payload: dict) -> str | None:
    if not raw_payload:
        return None
    if "raw_text" in raw_payload:
        return raw_payload["raw_text"]
    return (
        f"Source URL: {raw_payload['raw_url']}\n\n"
        "Excerpt:\n"
        f"{raw_payload['raw_excerpt']}"
    )


def _prepare(
    doc_id: str,
    extraction: dict,
    raw_payload: dict | None,
) -> tuple[dict, dict, str, str | None]:
    validate_doc_id(doc_id)
    if not isinstance(extraction, dict):
        raise ValueError("extraction must be an object")
    prepared = copy.deepcopy(extraction)
    source_doc = prepared.get("source_doc")
    if not isinstance(source_doc, dict):
        raise ValueError("extraction.source_doc is required")
    if source_doc.get("doc_id") != doc_id:
        raise ValueError("doc_id does not match extraction.source_doc.doc_id")
    permission = validate_storage_permission(
        source_doc.get("storage_permission"),
        source_doc.get("permission_basis"),
    )
    normalised_raw = _normalise_raw_payload(permission, raw_payload)
    extraction_text = json.dumps(prepared, ensure_ascii=False, indent=2) + "\n"
    if len(extraction_text) > MAX_EXTRACTION_CHARS:
        raise ValueError("extraction exceeds 1,000,000 characters")
    return prepared, normalised_raw, extraction_text, _raw_artifact_text(normalised_raw)


def _target_paths(doc_id: str, permission: str, root: Path) -> tuple[Path, Path]:
    if permission == "local_only":
        return (
            root / "library" / "private" / "extractions" / f"{doc_id}.json",
            root / "library" / "private" / "raw" / f"{doc_id}.txt",
        )
    return (
        root / "extractions" / f"{doc_id}.json",
        root / "library" / "raw" / f"{doc_id}.txt",
    )


def _graph_completion_path(doc_id: str, root: Path) -> Path:
    return root / "library" / "private" / "intake_state" / f"{doc_id}.json"


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _relative(path: Path, root: Path) -> str:
    if not _inside(path, root):
        raise ValueError(f"path escapes repository root: {path}")
    return path.resolve().relative_to(root.resolve()).as_posix()


def inspect_provenance(
    doc_id: str,
    extraction: dict,
    raw_payload: dict | None,
    *,
    root: Path = ROOT,
) -> dict:
    prepared, normalised_raw, _, raw_text = _prepare(doc_id, extraction, raw_payload)
    permission = prepared["source_doc"]["storage_permission"]
    extraction_path, raw_path = _target_paths(doc_id, permission, root)
    conflicts: list[str] = []
    missing: list[str] = []

    alternate_permission = "repo_full" if permission == "local_only" else "local_only"
    alternate_extraction, _ = _target_paths(doc_id, alternate_permission, root)
    if alternate_extraction.exists():
        conflicts.append(_relative(alternate_extraction, root))

    if extraction_path.exists():
        try:
            current = json.loads(extraction_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            conflicts.append(_relative(extraction_path, root))
        else:
            if canonical_extraction_hash(current) != canonical_extraction_hash(prepared):
                conflicts.append(_relative(extraction_path, root))
    else:
        missing.append(_relative(extraction_path, root))

    if raw_text is not None:
        if raw_path.exists():
            if raw_path.read_text(encoding="utf-8") != raw_text:
                conflicts.append(_relative(raw_path, root))
        else:
            missing.append(_relative(raw_path, root))

    status = "conflict" if conflicts else ("absent" if missing else "matching")
    return {
        "status": status,
        "missing": missing,
        "conflicts": conflicts,
        "paths": [
            _relative(extraction_path, root),
            *([_relative(raw_path, root)] if raw_text is not None else []),
        ],
        "permission": permission,
        "finalize_eligible": permission != "local_only",
        "normalised_raw": normalised_raw,
    }


def _atomic_publish(path: Path, content: str) -> None:
    """Publish with a hard-link create, which is atomic and never clobbers."""

    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temp_path, path)
        except FileExistsError:
            if path.read_text(encoding="utf-8") != content:
                raise ValueError(f"no-clobber conflict at {path}")
    finally:
        temp_path.unlink(missing_ok=True)


def publish_provenance(
    doc_id: str,
    extraction: dict,
    raw_payload: dict | None,
    *,
    root: Path = ROOT,
) -> dict:
    prepared, _, extraction_text, raw_text = _prepare(doc_id, extraction, raw_payload)
    inspection = inspect_provenance(doc_id, prepared, raw_payload, root=root)
    if inspection["status"] == "conflict":
        raise ValueError(f"provenance conflict for {doc_id}: {inspection['conflicts']}")
    if inspection["status"] == "matching":
        return {**inspection, "doc_id": doc_id}

    permission = prepared["source_doc"]["storage_permission"]
    extraction_path, raw_path = _target_paths(doc_id, permission, root)
    if not extraction_path.exists():
        _atomic_publish(extraction_path, extraction_text)
    if raw_text is not None and not raw_path.exists():
        _atomic_publish(raw_path, raw_text)
    final = inspect_provenance(doc_id, prepared, raw_payload, root=root)
    if final["status"] != "matching":
        raise RuntimeError(f"provenance publication incomplete for {doc_id}: {final}")
    return {**final, "status": "published", "doc_id": doc_id}


def mark_graph_complete(
    doc_id: str,
    extraction: dict,
    *,
    root: Path = ROOT,
) -> dict:
    """Persist a local server-owned receipt after graph verify and projection."""

    validate_doc_id(doc_id)
    if not isinstance(extraction, dict):
        raise ValueError("extraction must be an object")
    source_doc = extraction.get("source_doc")
    if not isinstance(source_doc, dict) or source_doc.get("doc_id") != doc_id:
        raise ValueError("completion receipt doc_id mismatch")
    receipt = {
        "schema_version": GRAPH_COMPLETION_SCHEMA,
        "doc_id": doc_id,
        "extraction_sha256": canonical_extraction_hash(extraction),
    }
    path = _graph_completion_path(doc_id, root)
    _atomic_publish(path, json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n")
    return receipt


def verify_graph_complete(doc_id: str, extraction: dict, *, root: Path = ROOT) -> dict:
    """Require a server-owned receipt bound to the exact stored extraction."""

    path = _graph_completion_path(doc_id, root)
    if not path.exists() or not _inside(path, root / "library" / "private" / "intake_state"):
        raise ValueError(f"graph completion receipt not found for doc_id: {doc_id}")
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid graph completion receipt for doc_id: {doc_id}") from exc
    expected = canonical_extraction_hash(extraction)
    if (
        receipt.get("schema_version") != GRAPH_COMPLETION_SCHEMA
        or receipt.get("doc_id") != doc_id
        or receipt.get("extraction_sha256") != expected
    ):
        raise ValueError(f"stale graph completion receipt for doc_id: {doc_id}")
    return receipt


def resolve_action_paths(doc_ids: list[str], *, root: Path = ROOT) -> dict:
    if not doc_ids:
        return {"doc_ids": [], "paths": [], "documents": []}
    if len(doc_ids) != len(set(doc_ids)):
        raise ValueError("doc_ids must be unique")
    paths: list[str] = []
    documents: list[dict] = []
    for doc_id in doc_ids:
        validate_doc_id(doc_id)
        repo_path = root / "extractions" / f"{doc_id}.json"
        private_path = root / "library" / "private" / "extractions" / f"{doc_id}.json"
        if private_path.exists():
            raise ValueError(f"manifest contains local_only doc_id: {doc_id}")
        if not repo_path.exists() or not _inside(repo_path, root / "extractions"):
            raise ValueError(f"repo-eligible extraction not found for doc_id: {doc_id}")
        extraction = json.loads(repo_path.read_text(encoding="utf-8"))
        source_doc = extraction.get("source_doc") or {}
        if source_doc.get("doc_id") != doc_id:
            raise ValueError(f"stored extraction doc_id mismatch: {doc_id}")
        permission = validate_storage_permission(
            source_doc.get("storage_permission"),
            source_doc.get("permission_basis"),
        )
        if permission == "local_only":
            raise ValueError(f"manifest contains local_only doc_id: {doc_id}")
        verify_graph_complete(doc_id, extraction, root=root)
        extraction_relative = _relative(repo_path, root)
        paths.append(extraction_relative)
        raw_path = root / "library" / "raw" / f"{doc_id}.txt"
        raw_relative = None
        if raw_path.exists():
            if not _inside(raw_path, root / "library" / "raw"):
                raise ValueError(f"raw path escapes ledger root: {doc_id}")
            raw_relative = _relative(raw_path, root)
            paths.append(raw_relative)
        documents.append(
            {
                "doc_id": doc_id,
                "storage_permission": permission,
                "permission_basis": source_doc["permission_basis"],
                "url": source_doc.get("url"),
                "extraction_path": extraction_relative,
                "raw_path": raw_relative,
            }
        )
    return {"doc_ids": list(doc_ids), "paths": paths, "documents": documents}


def _run_git(args: list[str], *, root: Path, timeout: int = 20) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
    )


def pending_intake_files(*, root: Path = ROOT) -> dict:
    try:
        result = _run_git(
            [
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
                "--",
                "library/raw",
                "extractions",
                "library/intake",
            ],
            root=root,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"untracked": [], "modified": [], "error": str(exc)}
    if result.returncode != 0:
        return {
            "untracked": [],
            "modified": [],
            "error": result.stderr.strip() or "git status failed",
        }
    untracked: list[str] = []
    modified: list[str] = []
    for entry in result.stdout.split("\0"):
        if not entry:
            continue
        status, path = entry[:2], entry[3:].replace("\\", "/")
        if status == "??":
            untracked.append(path)
        else:
            modified.append(path)
    return {
        "untracked": sorted(untracked),
        "modified": sorted(modified),
        "error": None,
    }


def write_report(slug: str, report_markdown: str, *, root: Path = ROOT) -> Path:
    validate_action_slug(slug)
    if not isinstance(report_markdown, str) or not report_markdown.strip():
        raise ValueError("report_markdown is required")
    if len(report_markdown) > MAX_REPORT_CHARS:
        raise ValueError("report_markdown exceeds 200,000 characters")
    recorded_at = datetime.now(timezone.utc)
    report_root = root / "library" / "intake"
    report_root.mkdir(parents=True, exist_ok=True)
    base = f"{recorded_at.date().isoformat()}-{slug}"
    content = (
        f"<!-- intake_recorded_at: {recorded_at.isoformat()} -->\n\n"
        f"{report_markdown.rstrip()}\n"
    )
    for suffix in ("", *(f"-{index}" for index in range(2, 10_000))):
        candidate = report_root / f"{base}{suffix}.md"
        if not _inside(candidate, report_root):
            raise ValueError("report path escapes library/intake")
        try:
            with candidate.open("x", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            return candidate
        except FileExistsError:
            continue
    raise RuntimeError("could not allocate a unique intake report path")


def git_preflight(*, root: Path = ROOT) -> dict:
    try:
        branch = _run_git(["branch", "--show-current"], root=root)
        if branch.returncode != 0:
            return {"ok": False, "reason": "git_unavailable", "detail": branch.stderr.strip()}
        if branch.stdout.strip() != "master":
            return {"ok": False, "reason": "not_master", "detail": branch.stdout.strip()}

        staged = _run_git(["diff", "--cached", "--quiet"], root=root)
        if staged.returncode != 0:
            return {"ok": False, "reason": "index_not_clean", "detail": "staged changes exist"}

        fetched = _run_git(["fetch", "origin", "master"], root=root, timeout=30)
        if fetched.returncode != 0:
            return {"ok": False, "reason": "fetch_failed", "detail": fetched.stderr.strip()}
        head = _run_git(["rev-parse", "HEAD"], root=root)
        remote = _run_git(["rev-parse", "origin/master"], root=root)
        if head.returncode != 0 or remote.returncode != 0:
            return {"ok": False, "reason": "revision_lookup_failed", "detail": "cannot resolve HEAD/origin/master"}
        if head.stdout.strip() != remote.stdout.strip():
            return {
                "ok": False,
                "reason": "head_not_synced",
                "detail": f"HEAD={head.stdout.strip()} origin/master={remote.stdout.strip()}",
            }
        return {"ok": True, "reason": None, "head": head.stdout.strip()}
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "reason": "git_error", "detail": str(exc)}


def _validated_commit_paths(paths: list[str | Path], root: Path) -> list[str]:
    if not paths:
        raise ValueError("at least one exact path is required")
    result: list[str] = []
    for value in paths:
        path = Path(value)
        absolute = path if path.is_absolute() else root / path
        relative = _relative(absolute, root)
        if not any(relative.startswith(prefix) for prefix in LEDGER_PREFIXES):
            raise ValueError(f"path is outside intake ledger roots: {relative}")
        result.append(relative)
    if len(result) != len(set(result)):
        raise ValueError("commit paths must be unique")
    return result


def commit_and_push(
    paths: list[str | Path],
    message: str,
    *,
    root: Path = ROOT,
) -> dict:
    if not isinstance(message, str) or not message.strip():
        raise ValueError("commit message is required")
    exact_paths = _validated_commit_paths(paths, root)
    preflight = git_preflight(root=root)
    if not preflight["ok"]:
        return {"status": "not_committed", "preflight": preflight, "paths": exact_paths}
    staged = False
    try:
        added = _run_git(["add", "--", *exact_paths], root=root)
        if added.returncode != 0:
            return {"status": "not_committed", "error": added.stderr.strip(), "paths": exact_paths}
        staged = True
        committed = _run_git(["commit", "-m", message], root=root, timeout=30)
        if committed.returncode != 0:
            current = _run_git(["rev-parse", "HEAD"], root=root)
            if current.returncode == 0 and current.stdout.strip() != preflight["head"]:
                return {
                    "status": "committed_not_pushed",
                    "commit": current.stdout.strip(),
                    "error": committed.stderr.strip(),
                    "paths": exact_paths,
                }
            unstaged = _run_git(["restore", "--staged", "--", *exact_paths], root=root)
            return {
                "status": "not_committed",
                "error": committed.stderr.strip(),
                "cleanup_error": unstaged.stderr.strip() if unstaged.returncode else None,
                "paths": exact_paths,
            }
        commit_hash = _run_git(["rev-parse", "HEAD"], root=root).stdout.strip()
        pushed = _run_git(["push", "origin", "master"], root=root, timeout=60)
        if pushed.returncode != 0:
            return {
                "status": "committed_not_pushed",
                "commit": commit_hash,
                "push_error": pushed.stderr.strip(),
                "paths": exact_paths,
            }
        return {
            "status": "committed+pushed",
            "commit": commit_hash,
            "paths": exact_paths,
        }
    except (OSError, subprocess.SubprocessError) as exc:
        cleanup_error = None
        if staged:
            try:
                current = _run_git(["rev-parse", "HEAD"], root=root)
                if current.returncode == 0 and current.stdout.strip() != preflight["head"]:
                    return {
                        "status": "committed_not_pushed",
                        "commit": current.stdout.strip(),
                        "error": str(exc),
                        "paths": exact_paths,
                    }
                unstaged = _run_git(
                    ["restore", "--staged", "--", *exact_paths], root=root
                )
                cleanup_error = unstaged.stderr.strip() if unstaged.returncode else None
            except (OSError, subprocess.SubprocessError) as cleanup_exc:
                cleanup_error = str(cleanup_exc)
        return {
            "status": "not_committed",
            "error": str(exc),
            "cleanup_error": cleanup_error,
            "paths": exact_paths,
        }
