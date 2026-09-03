"""Durable, server-owned Research Actions for cross-session mobile intake.

The immutable payload is the approval boundary. Mutable execution and Git
publication receipts live beside it, but never participate in its digest.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import secrets
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

from intake.provenance import (
    MAX_EXTRACTION_CHARS,
    MAX_REPORT_CHARS,
    ROOT,
    validate_action_slug,
    validate_doc_id,
    validate_storage_permission,
)


ACTION_PAYLOAD_SCHEMA = "research-action/v1"
ACTION_RECORD_SCHEMA = "research-action-record/v1"
ACTION_ID_RE = re.compile(r"^ra_[0-9a-f]{32}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
REPORT_FIELDS = (
    "title",
    "why_now",
    "findings",
    "search_summary",
    "l8_notes",
    "counterevidence_and_gaps",
)
REPORT_HEADINGS = {
    "why_now": "為何此時入圖",
    "findings": "研究發現",
    "search_summary": "搜尋過程摘要",
    "l8_notes": "L8 確認備註",
    "counterevidence_and_gaps": "反向證據與缺口",
}
REQUEST_FIELDS = {"schema_version", "action_slug", "report", "documents"}
# 選填：這個 graph delta 完成後，唯一要建立／沿用哪個 Decision cohort。
# 從 lead 來的 RA 由綁定 lead 的 refs.focus_company_id 提供；從 decision gap
# work order 來的 RA 沒有 lead 可綁，必須在這裡自己聲明。
REQUEST_OPTIONAL_FIELDS = {"focus_company_id"}
DOCUMENT_REQUIRED_FIELDS = {
    "extraction_json",
    "storage_permission",
    "permission_basis",
}
DOCUMENT_OPTIONAL_FIELDS = {"raw_text", "raw_url", "raw_excerpt"}
NORMALIZED_DOCUMENT_FIELDS = {
    "doc_id",
    "extraction",
    "raw_payload",
    "storage_permission",
    "permission_basis",
    "validation_warnings",
}

MAX_DOCUMENTS = 10
MAX_ACTION_BYTES = 5 * 1024 * 1024
MAX_STAGED_BYTES = 100 * 1024 * 1024
MAX_NONTERMINAL_ACTIONS = 50
MAX_REPORT_FIELD_CHARS = 80_000
MAX_TITLE_CHARS = 500
READY_TTL = timedelta(days=30)
LOCK_TTL = timedelta(minutes=15)
LIST_LIMIT = 25
NONTERMINAL_STATES = {"ready", "applying", "partial"}
ACTIONABLE_STATES = {
    "ready",
    "applying",
    "partial",
    "applied",
    "committed_not_pushed",
}


class ActionBusyError(RuntimeError):
    """Raised when another process owns a live Research Action lock."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _parse_time(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO-8601 string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_action_digest(payload: dict) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def validate_action_id(action_id: str) -> str:
    if not isinstance(action_id, str) or not ACTION_ID_RE.fullmatch(action_id):
        raise ValueError("invalid action_id")
    return action_id


def validate_action_digest(action_digest: str) -> str:
    if not isinstance(action_digest, str) or not DIGEST_RE.fullmatch(action_digest):
        raise ValueError("invalid action_digest: expected 64 lowercase hex characters")
    return action_digest


def _require_exact_fields(value: dict, expected: set[str], label: str) -> None:
    missing = sorted(expected - set(value))
    extra = sorted(set(value) - expected)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing={missing}")
        if extra:
            details.append(f"unknown={extra}")
        raise ValueError(f"{label} fields invalid: {'; '.join(details)}")


def _require_allowed_fields(
    value: dict, required: set[str], optional: set[str], label: str
) -> None:
    """必填欄位一個不能少，另外只接受明確登記的選填欄位。"""

    missing = sorted(required - set(value))
    extra = sorted(set(value) - required - optional)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing={missing}")
        if extra:
            details.append(f"unknown={extra}")
        raise ValueError(f"{label} fields invalid: {'; '.join(details)}")


def _validate_focus_company_id(value: object) -> str:
    """只接受 registry 登記過的 company_id；不接受自由字串。"""

    from identity.registry import get_registry

    if not isinstance(value, str) or not value.strip():
        raise ValueError("focus_company_id must be a non-empty string")
    company_id = value.strip()
    if not get_registry().has_company(company_id):
        raise ValueError(f"focus_company_id 未在 registry 登記：{company_id}")
    return company_id


def _validate_report(report: object) -> dict[str, str]:
    if not isinstance(report, dict):
        raise ValueError("report must be an object")
    _require_exact_fields(report, set(REPORT_FIELDS), "report")
    normalized: dict[str, str] = {}
    for field in REPORT_FIELDS:
        value = report[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"report.{field} must be a non-empty string")
        limit = MAX_TITLE_CHARS if field == "title" else MAX_REPORT_FIELD_CHARS
        if len(value) > limit:
            raise ValueError(f"report.{field} exceeds {limit:,} characters")
        normalized[field] = value.strip()
    if sum(len(value) for value in normalized.values()) > MAX_REPORT_CHARS - 10_000:
        raise ValueError("combined report fields exceed the safe rendered report limit")
    return normalized


def parse_action_request(action_json: str) -> dict:
    """Parse the strict external v1 request without performing graph validation."""

    if not isinstance(action_json, str):
        raise ValueError("action_json must be a JSON string")
    if len(action_json.encode("utf-8")) > MAX_ACTION_BYTES:
        raise ValueError("action_json exceeds 5 MiB")
    try:
        request = json.loads(action_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"action_json is not valid JSON: {exc}") from exc
    if not isinstance(request, dict):
        raise ValueError("action_json must decode to an object")
    _require_allowed_fields(request, REQUEST_FIELDS, REQUEST_OPTIONAL_FIELDS, "action")
    if request["schema_version"] != ACTION_PAYLOAD_SCHEMA:
        raise ValueError(
            f"unsupported action schema: expected {ACTION_PAYLOAD_SCHEMA!r}"
        )
    action_slug = validate_action_slug(request["action_slug"])
    report = _validate_report(request["report"])
    focus_company_id = (
        _validate_focus_company_id(request["focus_company_id"])
        if request.get("focus_company_id") is not None
        else None
    )
    documents = request["documents"]
    if not isinstance(documents, list) or not documents:
        raise ValueError("documents must be a non-empty list")
    if len(documents) > MAX_DOCUMENTS:
        raise ValueError(f"documents exceeds the {MAX_DOCUMENTS}-document limit")

    normalized_documents = []
    allowed = DOCUMENT_REQUIRED_FIELDS | DOCUMENT_OPTIONAL_FIELDS
    for index, document in enumerate(documents):
        if not isinstance(document, dict):
            raise ValueError(f"documents[{index}] must be an object")
        missing = sorted(DOCUMENT_REQUIRED_FIELDS - set(document))
        extra = sorted(set(document) - allowed)
        if missing or extra:
            details = []
            if missing:
                details.append(f"missing={missing}")
            if extra:
                details.append(f"unknown={extra}")
            raise ValueError(
                f"documents[{index}] fields invalid: {'; '.join(details)}"
            )
        extraction_json = document["extraction_json"]
        if not isinstance(extraction_json, str):
            raise ValueError(f"documents[{index}].extraction_json must be a string")
        if len(extraction_json) > MAX_EXTRACTION_CHARS:
            raise ValueError(
                f"documents[{index}].extraction_json exceeds 1,000,000 characters"
            )
        validate_storage_permission(
            document["storage_permission"], document["permission_basis"]
        )
        for key in DOCUMENT_OPTIONAL_FIELDS:
            value = document.get(key)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"documents[{index}].{key} must be a string or null")
        normalized_documents.append(copy.deepcopy(document))

    parsed = {
        "schema_version": ACTION_PAYLOAD_SCHEMA,
        "action_slug": action_slug,
        "report": report,
        "documents": normalized_documents,
    }
    if focus_company_id is not None:
        parsed["focus_company_id"] = focus_company_id
    return parsed


def validate_normalized_payload(payload: object) -> dict:
    """Validate the canonical internal payload produced by shared intake validation."""

    if not isinstance(payload, dict):
        raise ValueError("normalized action payload must be an object")
    _require_allowed_fields(
        payload, REQUEST_FIELDS, REQUEST_OPTIONAL_FIELDS, "normalized action"
    )
    if payload["schema_version"] != ACTION_PAYLOAD_SCHEMA:
        raise ValueError("unsupported normalized action schema")
    validate_action_slug(payload["action_slug"])
    _validate_report(payload["report"])
    if payload.get("focus_company_id") is not None:
        _validate_focus_company_id(payload["focus_company_id"])
    documents = payload["documents"]
    if not isinstance(documents, list) or not 1 <= len(documents) <= MAX_DOCUMENTS:
        raise ValueError("normalized documents count is invalid")
    seen = set()
    for index, document in enumerate(documents):
        if not isinstance(document, dict):
            raise ValueError(f"normalized documents[{index}] must be an object")
        _require_exact_fields(
            document, NORMALIZED_DOCUMENT_FIELDS, f"normalized documents[{index}]"
        )
        doc_id = validate_doc_id(document["doc_id"])
        if doc_id in seen:
            raise ValueError(f"duplicate document doc_id: {doc_id}")
        seen.add(doc_id)
        extraction = document["extraction"]
        if not isinstance(extraction, dict):
            raise ValueError(f"normalized documents[{index}].extraction must be an object")
        source_doc = extraction.get("source_doc")
        if not isinstance(source_doc, dict) or source_doc.get("doc_id") != doc_id:
            raise ValueError(f"normalized documents[{index}] doc_id mismatch")
        permission = validate_storage_permission(
            document["storage_permission"], document["permission_basis"]
        )
        if source_doc.get("storage_permission") != permission:
            raise ValueError(f"normalized documents[{index}] permission mismatch")
        if source_doc.get("permission_basis") != document["permission_basis"]:
            raise ValueError(f"normalized documents[{index}] permission basis mismatch")
        raw_payload = document["raw_payload"]
        if not isinstance(raw_payload, dict) or set(raw_payload) - DOCUMENT_OPTIONAL_FIELDS:
            raise ValueError(f"normalized documents[{index}].raw_payload is invalid")
        warnings = document["validation_warnings"]
        if not isinstance(warnings, list) or not all(
            isinstance(item, str) for item in warnings
        ):
            raise ValueError(
                f"normalized documents[{index}].validation_warnings is invalid"
            )
    if len(_canonical_bytes(payload)) > MAX_ACTION_BYTES:
        raise ValueError("normalized action exceeds 5 MiB")
    return copy.deepcopy(payload)


def _action_root(root: Path) -> Path:
    return root / "library" / "private" / "research_actions"


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


def _action_path(action_id: str, root: Path) -> Path:
    validate_action_id(action_id)
    parent = _action_root(root)
    path = parent / f"{action_id}.json"
    if not _inside(path, parent):
        raise ValueError("action path escapes private action root")
    return path


def _atomic_replace_json(path: Path, value: dict) -> None:
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
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def _write_new_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise RuntimeError("Research Action ID collision") from exc


def _lock_is_stale(path: Path, now: datetime) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        acquired_at = _parse_time(payload["acquired_at"])
    except (OSError, KeyError, ValueError, json.JSONDecodeError):
        try:
            modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        except OSError:
            return True
        return now - modified > LOCK_TTL
    return now - acquired_at > LOCK_TTL


@contextmanager
def _exclusive_lock(path: Path, *, now: datetime | None = None) -> Iterator[str]:
    current = now or _now()
    path.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_hex(16)
    payload = json.dumps(
        {"token": token, "pid": os.getpid(), "acquired_at": _iso(current)},
        sort_keys=True,
    )
    for attempt in range(2):
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if attempt == 0 and _lock_is_stale(path, current):
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
                continue
            raise ActionBusyError("Research Action is already being processed")
        else:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            break
    try:
        yield token
    finally:
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
        if existing.get("token") == token:
            path.unlink(missing_ok=True)


@contextmanager
def action_lock(
    action_id: str, *, root: Path = ROOT, now: datetime | None = None
) -> Iterator[str]:
    validate_action_id(action_id)
    lock_path = _action_root(root) / "locks" / f"{action_id}.lock"
    with _exclusive_lock(lock_path, now=now) as token:
        yield token


def _validate_record(record: object) -> dict:
    if not isinstance(record, dict):
        raise ValueError("Research Action record must be an object")
    if record.get("schema_version") != ACTION_RECORD_SCHEMA:
        raise ValueError("unsupported Research Action record schema")
    validate_action_id(record.get("action_id"))
    validate_action_digest(record.get("action_digest"))
    if record.get("state") not in {
        "ready",
        "applying",
        "partial",
        "applied",
        "committed_not_pushed",
        "pushed",
        "expired",
    }:
        raise ValueError("unsupported Research Action state")
    _parse_time(record.get("created_at"))
    _parse_time(record.get("updated_at"))
    _parse_time(record.get("expires_at"))
    if not isinstance(record.get("revision"), int) or record["revision"] < 1:
        raise ValueError("invalid Research Action revision")
    if record.get("payload") is not None:
        validate_normalized_payload(record["payload"])
        if canonical_action_digest(record["payload"]) != record["action_digest"]:
            raise ValueError("Research Action payload digest mismatch")
    review = record.get("review")
    if review is not None:
        if not isinstance(review, dict):
            raise ValueError("Research Action review must be an object or null")
        if set(review) == {"title"}:
            if not isinstance(review["title"], str) or not review["title"].strip():
                raise ValueError("Research Action tombstone title is invalid")
        else:
            _validate_report(review)

    manifest = record.get("document_manifest")
    if not isinstance(manifest, list) or not manifest:
        raise ValueError("Research Action document manifest is invalid")
    for item in manifest:
        if not isinstance(item, dict):
            raise ValueError("Research Action document manifest item is invalid")
        required = {
            "doc_id",
            "title",
            "url",
            "storage_permission",
            "permission_basis",
            "node_count",
            "edge_count",
            "claim_count",
            "validation_warnings",
        }
        if required - set(item):
            raise ValueError("Research Action document manifest fields are incomplete")
        validate_doc_id(item["doc_id"])
        validate_storage_permission(
            item["storage_permission"], item["permission_basis"]
        )
        if not isinstance(item["title"], str) or not item["title"]:
            raise ValueError("Research Action document title is invalid")
        if item["url"] is not None and not isinstance(item["url"], str):
            raise ValueError("Research Action document URL is invalid")
        if any(
            not isinstance(item[key], int) or item[key] < 0
            for key in ("node_count", "edge_count", "claim_count")
        ):
            raise ValueError("Research Action document counts are invalid")
        if not isinstance(item["validation_warnings"], list) or not all(
            isinstance(warning, str) for warning in item["validation_warnings"]
        ):
            raise ValueError("Research Action document warnings are invalid")

    execution = record.get("execution")
    if not isinstance(execution, dict):
        raise ValueError("Research Action execution receipt is invalid")
    execution_documents = execution.get("documents")
    if not isinstance(execution_documents, list) or len(execution_documents) != len(
        manifest
    ):
        raise ValueError("Research Action execution document receipts are invalid")
    for expected, item in zip(manifest, execution_documents, strict=True):
        if not isinstance(item, dict) or item.get("doc_id") != expected["doc_id"]:
            raise ValueError("Research Action execution document identity is invalid")
        if item.get("status") not in {"pending", "complete", "failed"}:
            raise ValueError("Research Action execution document status is invalid")
        if item.get("result") is not None and not isinstance(item["result"], dict):
            raise ValueError("Research Action execution document result is invalid")
    report_receipt = execution.get("report")
    if not isinstance(report_receipt, dict) or report_receipt.get("status") not in {
        "pending",
        "failed",
        "complete",
    }:
        raise ValueError("Research Action report receipt is invalid")
    if execution.get("last_error") is not None and not isinstance(
        execution["last_error"], dict
    ):
        raise ValueError("Research Action last error is invalid")

    git = record.get("git")
    if not isinstance(git, dict) or git.get("status") not in {
        "waiting_for_apply",
        "not_required",
        "pending",
        "committed_not_pushed",
        "pushed",
    }:
        raise ValueError("Research Action Git receipt is invalid")
    if not isinstance(git.get("eligible_paths"), list) or not all(
        isinstance(path, str) for path in git["eligible_paths"]
    ):
        raise ValueError("Research Action eligible paths are invalid")
    if git.get("commit") is not None and not isinstance(git["commit"], str):
        raise ValueError("Research Action commit receipt is invalid")
    if record.get("final_result") is not None and not isinstance(
        record["final_result"], dict
    ):
        raise ValueError("Research Action final result is invalid")
    return record


def read_action(action_id: str, *, root: Path = ROOT) -> dict:
    path = _action_path(action_id, root)
    if not path.exists():
        raise FileNotFoundError(f"Research Action not found: {action_id}")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Research Action record is not valid JSON") from exc
    return copy.deepcopy(_validate_record(record))


def save_action(record: dict, *, root: Path = ROOT, now: datetime | None = None) -> dict:
    record = copy.deepcopy(_validate_record(record))
    record["revision"] += 1
    record["updated_at"] = _iso(now or _now())
    _validate_record(record)
    _atomic_replace_json(_action_path(record["action_id"], root), record)
    return record


def _document_summary(document: dict) -> dict:
    source_doc = document["extraction"].get("source_doc") or {}
    return {
        "doc_id": document["doc_id"],
        "title": source_doc.get("title") or document["doc_id"],
        "url": source_doc.get("url"),
        "storage_permission": document["storage_permission"],
        "permission_basis": document["permission_basis"],
        "node_count": len(document["extraction"].get("nodes") or []),
        "edge_count": len(document["extraction"].get("edges") or []),
        "claim_count": len(document["extraction"].get("claims") or []),
        "validation_warnings": list(document["validation_warnings"]),
    }


def _effective_state(record: dict, now: datetime) -> str:
    if record["state"] == "ready" and now >= _parse_time(record["expires_at"]):
        return "expired"
    return record["state"]


def _age_seconds(record: dict, now: datetime) -> int:
    return max(0, int((now - _parse_time(record["created_at"])).total_seconds()))


def _next_action(state: str, git_status: str | None = None) -> str:
    if state == "ready":
        return "Review the exact packet; apply only after explicit user approval."
    if state in {"applying", "partial"}:
        return "Inspect status and retry the same action ID and digest."
    if state == "expired":
        return "Prepare a fresh Research Action before approval."
    if state == "applied" and git_status == "pending":
        return "Open a local Codex or Claude Code session and publish pending intake."
    if state == "applied" and git_status == "not_required":
        return "No action required; this local-only action is complete."
    if state == "committed_not_pushed":
        return "Retry the local publish command after verifying origin/master."
    if state == "pushed":
        return "No action required."
    return "Inspect the local Research Action record."


def render_review_packet(record: dict, *, now: datetime | None = None) -> str | None:
    payload = record.get("payload")
    report = payload.get("report") if payload else record.get("review")
    if not isinstance(report, dict) or set(REPORT_FIELDS) - set(report):
        return None
    documents = record.get("document_manifest") or []
    lines = [
        f"# {report['title']}",
        "",
        f"- Research Action: `{record['action_id']}`",
        f"- Digest: `{record['action_digest']}`",
        f"- Prepared (UTC): `{record['created_at']}`",
        f"- Approval expires (UTC): `{record['expires_at']}`",
    ]
    for field in ("why_now", "findings"):
        lines.extend(["", f"## {REPORT_HEADINGS[field]}", "", report[field]])
    lines.extend(["", "## 文件清單", ""])
    for document in documents:
        counts = (
            f"nodes={document['node_count']}, edges={document['edge_count']}, "
            f"claims={document['claim_count']}"
        )
        lines.append(
            f"- `{document['doc_id']}` — {document['title']}; "
            f"storage=`{document['storage_permission']}`; {counts}"
        )
        if document.get("url"):
            lines.append(f"  - URL: {document['url']}")
        for warning in document.get("validation_warnings") or []:
            lines.append(f"  - Validation warning: {warning}")
    for field in ("search_summary", "l8_notes", "counterevidence_and_gaps"):
        lines.extend(["", f"## {REPORT_HEADINGS[field]}", "", report[field]])
    lines.extend(
        [
            "",
            "## 核准指示",
            "",
            f"若核准，請明確回覆同意套用 `{record['action_id']}`；"
            "session 必須使用上方完整 digest 呼叫 apply。",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _compact_expired_actions(root: Path, now: datetime) -> int:
    parent = _action_root(root)
    if not parent.exists():
        return 0
    compacted = 0
    lock_root = parent / "locks"
    for path in sorted(parent.glob("ra_*.json")):
        action_id = path.stem
        if (lock_root / f"{action_id}.lock").exists():
            continue
        try:
            record = read_action(action_id, root=root)
        except (OSError, ValueError):
            continue
        if (
            record["state"] == "ready"
            and record.get("payload") is not None
            and now >= _parse_time(record["expires_at"])
        ):
            report = record["payload"]["report"]
            record["state"] = "expired"
            record["review"] = {"title": report["title"]}
            record["payload"] = None
            record["compacted_at"] = _iso(now)
            save_action(record, root=root, now=now)
            compacted += 1
    return compacted


def cleanup_expired_actions(
    *, root: Path = ROOT, now: datetime | None = None
) -> dict:
    """Compact expired, never-applied payloads without touching graph or Git."""

    current = now or _now()
    parent = _action_root(root)
    with _exclusive_lock(parent / "locks" / ".store.lock", now=current):
        compacted = _compact_expired_actions(root, current)
    return {"status": "ok", "compacted_count": compacted}


def _quota_usage(root: Path) -> tuple[int, int]:
    count = 0
    total_bytes = 0
    parent = _action_root(root)
    if not parent.exists():
        return count, total_bytes
    for path in parent.glob("ra_*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            _validate_record(record)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if record["state"] in NONTERMINAL_STATES and record.get("payload") is not None:
            count += 1
            total_bytes += len(_canonical_bytes(record["payload"]))
    return count, total_bytes


def create_action(
    payload: dict, *, root: Path = ROOT, now: datetime | None = None
) -> dict:
    """Persist a validated immutable action and return its full record."""

    current = now or _now()
    normalized = validate_normalized_payload(payload)
    payload_bytes = len(_canonical_bytes(normalized))
    parent = _action_root(root)
    with _exclusive_lock(parent / "locks" / ".store.lock", now=current):
        _compact_expired_actions(root, current)
        active_count, staged_bytes = _quota_usage(root)
        if active_count >= MAX_NONTERMINAL_ACTIONS:
            raise ValueError(
                "Research Action staging is full (50 nonterminal actions); "
                "apply pending actions or run "
                "`python scripts/commit_pending_intake.py --cleanup-expired` first"
            )
        if staged_bytes + payload_bytes > MAX_STAGED_BYTES:
            raise ValueError(
                "Research Action staging exceeds 100 MiB; apply pending actions or run "
                "`python scripts/commit_pending_intake.py --cleanup-expired` before "
                "preparing another"
            )
        action_id = f"ra_{secrets.token_hex(16)}"
        created_at = _iso(current)
        expires_at = _iso(current + READY_TTL)
        manifest = [_document_summary(item) for item in normalized["documents"]]
        has_repo = any(
            item["storage_permission"] != "local_only" for item in manifest
        )
        record = {
            "schema_version": ACTION_RECORD_SCHEMA,
            "action_id": action_id,
            "action_digest": canonical_action_digest(normalized),
            "state": "ready",
            "created_at": created_at,
            "updated_at": created_at,
            "expires_at": expires_at,
            "revision": 1,
            "payload": normalized,
            "review": None,
            "document_manifest": manifest,
            "execution": {
                "documents": [
                    {
                        "doc_id": item["doc_id"],
                        "status": "pending",
                        "result": None,
                    }
                    for item in manifest
                ],
                "report": {"status": "pending"},
                "last_error": None,
            },
            "git": {
                "status": "waiting_for_apply" if has_repo else "not_required",
                "eligible_paths": [],
                "commit": None,
            },
        }
        _write_new_json(_action_path(action_id, root), record)
    return copy.deepcopy(record)


def compact_applied_payload(record: dict) -> dict:
    """Drop duplicated source bodies after durable apply receipts exist."""

    if record.get("state") != "applied":
        raise ValueError("only an applied action can compact its payload")
    payload = record.get("payload")
    if payload is None:
        return record
    if record.get("execution", {}).get("report", {}).get("status") != "complete":
        raise ValueError("cannot compact before report publication completes")
    if any(
        item.get("status") != "complete"
        for item in record.get("execution", {}).get("documents", [])
    ):
        raise ValueError("cannot compact before every document completes")
    record["review"] = copy.deepcopy(payload["report"])
    # focus_company_id 是 Decision handoff 的收據，不是可重建的來源正文——compaction
    # 丟掉它，pq2 結案時就再也查不到「這批 delta 要沿用哪個 cohort」。從 lead 來的
    # RA 還能回頭問 lead，decision gap 來的 RA 沒有 lead 可問，會直接卡死。
    if payload.get("focus_company_id"):
        record["focus_company_id"] = payload["focus_company_id"]
    record["payload"] = None
    record["compacted_at"] = _iso(_now())
    return record


def _safe_execution(record: dict) -> dict:
    return {
        "documents": [
            {
                "doc_id": item.get("doc_id"),
                "status": item.get("status"),
                "open_conflict_ids": (
                    (item.get("result") or {}).get("open_conflict_ids") or []
                ),
            }
            for item in record.get("execution", {}).get("documents", [])
        ],
        "report": copy.deepcopy(record.get("execution", {}).get("report") or {}),
        "last_error": copy.deepcopy(record.get("execution", {}).get("last_error")),
    }


def action_status(
    action_id: str, *, root: Path = ROOT, now: datetime | None = None
) -> dict:
    current = now or _now()
    record = read_action(action_id, root=root)
    state = _effective_state(record, current)
    completed = sum(
        item.get("status") == "complete"
        for item in record.get("execution", {}).get("documents", [])
    )
    return {
        "status": "ok",
        "action_id": action_id,
        "action_digest": record["action_digest"],
        "state": state,
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
        "expires_at": record["expires_at"],
        "age_seconds": _age_seconds(record, current),
        "title": (
            (record.get("payload") or {}).get("report", {}).get("title")
            or (record.get("review") or {}).get("title")
        ),
        "document_count": len(record.get("document_manifest") or []),
        "completed_document_count": completed,
        "documents": copy.deepcopy(record.get("document_manifest") or []),
        "execution": _safe_execution(record),
        "git": copy.deepcopy(record.get("git") or {}),
        "next_action": _next_action(state, (record.get("git") or {}).get("status")),
        "review_packet": render_review_packet(record, now=current),
    }


def list_action_statuses(
    *, root: Path = ROOT, now: datetime | None = None, limit: int = LIST_LIMIT
) -> dict:
    current = now or _now()
    if not isinstance(limit, int) or not 1 <= limit <= LIST_LIMIT:
        raise ValueError(f"limit must be between 1 and {LIST_LIMIT}")
    rows = []
    parent = _action_root(root)
    for path in parent.glob("ra_*.json") if parent.exists() else []:
        try:
            record = read_action(path.stem, root=root)
            state = _effective_state(record, current)
        except (OSError, ValueError):
            continue
        if state not in ACTIONABLE_STATES:
            continue
        git_status = (record.get("git") or {}).get("status")
        if state == "applied" and git_status != "pending":
            continue
        title = (
            (record.get("payload") or {}).get("report", {}).get("title")
            or (record.get("review") or {}).get("title")
        )
        completed = sum(
            item.get("status") == "complete"
            for item in record.get("execution", {}).get("documents", [])
        )
        rows.append(
            {
                "action_id": record["action_id"],
                "title": title,
                "state": state,
                "created_at": record["created_at"],
                "updated_at": record["updated_at"],
                "age_seconds": _age_seconds(record, current),
                "digest_prefix": record["action_digest"][:12],
                "document_count": len(record.get("document_manifest") or []),
                "completed_document_count": completed,
                "next_action": _next_action(
                    state, git_status
                ),
            }
        )
    rows.sort(key=lambda item: item["updated_at"], reverse=True)
    return {"status": "ok", "count": min(len(rows), limit), "actions": rows[:limit]}


def count_action_states(*, root: Path = ROOT, now: datetime | None = None) -> dict:
    current = now or _now()
    counts = {
        "ready_for_approval": 0,
        "partial_apply": 0,
        "uncommitted": 0,
        "committed_not_pushed": 0,
    }
    parent = _action_root(root)
    for path in parent.glob("ra_*.json") if parent.exists() else []:
        try:
            record = read_action(path.stem, root=root)
            state = _effective_state(record, current)
        except (OSError, ValueError):
            continue
        if state == "ready":
            counts["ready_for_approval"] += 1
        elif state in {"applying", "partial"}:
            counts["partial_apply"] += 1
        elif state == "applied" and record.get("git", {}).get("status") == "pending":
            counts["uncommitted"] += 1
        elif state == "committed_not_pushed":
            counts["committed_not_pushed"] += 1
    counts["total"] = sum(counts.values())
    return counts


def _write_exact(path: Path, content: str) -> tuple[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing != content:
            raise ValueError(f"no-clobber report conflict at {path.name}")
    else:
        try:
            with path.open("x", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError:
            if path.read_text(encoding="utf-8") != content:
                raise ValueError(f"no-clobber report conflict at {path.name}")
    return path.as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()


def _full_report(record: dict) -> str:
    payload = record.get("payload")
    report = payload.get("report") if payload else record.get("review")
    if not isinstance(report, dict) or set(REPORT_FIELDS) - set(report):
        raise ValueError("Research Action review fields are unavailable")
    lines = [
        f"# {report['title']}",
        "",
        f"- Research Action: `{record['action_id']}`",
        f"- Approved digest: `{record['action_digest']}`",
        f"- Prepared (UTC): `{record['created_at']}`",
    ]
    for field in ("why_now", "findings"):
        lines.extend(["", f"## {REPORT_HEADINGS[field]}", "", report[field]])
    lines.extend(["", "## 文件清單", ""])
    for document in record.get("document_manifest") or []:
        counts = (
            f"nodes={document['node_count']}, edges={document['edge_count']}, "
            f"claims={document['claim_count']}"
        )
        lines.append(
            f"- `{document['doc_id']}` — {document['title']}; "
            f"storage=`{document['storage_permission']}`; {counts}"
        )
        if document.get("url"):
            lines.append(f"  - URL: {document['url']}")
        for warning in document.get("validation_warnings") or []:
            lines.append(f"  - Validation warning: {warning}")
    for field in ("search_summary", "l8_notes", "counterevidence_and_gaps"):
        lines.extend(["", f"## {REPORT_HEADINGS[field]}", "", report[field]])

    conflict_ids = sorted(
        {
            conflict_id
            for item in record["execution"]["documents"]
            for conflict_id in ((item.get("result") or {}).get("open_conflict_ids") or [])
        }
    )
    lines.extend(["", "## Server-verified apply receipt", ""])
    lines.append(f"- Applied documents: {len(record['document_manifest'])}")
    lines.append(
        "- Open graph conflict IDs: "
        + (", ".join(f"`{item}`" for item in conflict_ids) if conflict_ids else "none")
    )
    for document, execution in zip(
        record["document_manifest"], record["execution"]["documents"], strict=True
    ):
        result = execution.get("result") or {}
        lines.append(
            f"- `{document['doc_id']}` — graph status=`{result.get('status')}`; "
            f"storage=`{document['storage_permission']}`"
        )
    return "\n".join(lines).rstrip() + "\n"


def _redacted_stub(record: dict) -> str:
    eligible = [
        item
        for item in record["document_manifest"]
        if item["storage_permission"] != "local_only"
    ]
    lines = [
        f"# Research Action {record['action_id']}",
        "",
        "This server-generated ledger stub intentionally omits all client-authored "
        "report text because the action also contains local-only material.",
        "",
        f"- Action digest: `{record['action_digest']}`",
        f"- Created (UTC): `{record['created_at']}`",
        "- Repo-eligible document IDs:",
    ]
    lines.extend(
        f"  - `{item['doc_id']}` (`{item['storage_permission']}`)" for item in eligible
    )
    return "\n".join(lines).rstrip() + "\n"


def publish_action_reports(record: dict, *, root: Path = ROOT) -> dict:
    """Publish deterministic full/private reports and a mixed-action safe stub."""

    _validate_record(record)
    if record["state"] not in {"applying", "partial"}:
        raise ValueError("reports can only publish while an action is applying or partial")
    if any(item.get("status") != "complete" for item in record["execution"]["documents"]):
        raise ValueError("reports cannot publish before every document completes")
    permissions = {
        item["storage_permission"] for item in record["document_manifest"]
    }
    has_local = "local_only" in permissions
    has_repo = bool(permissions - {"local_only"})
    date = _parse_time(record["created_at"]).date().isoformat()
    filename = f"{date}-{record['action_id']}.md"
    result = {
        "status": "complete",
        "public_path": None,
        "public_sha256": None,
        "private_path": None,
        "private_sha256": None,
    }
    full = _full_report(record)
    if has_local:
        private_path = root / "library" / "private" / "intake" / filename
        _, digest = _write_exact(private_path, full)
        result["private_path"] = _relative(private_path, root)
        result["private_sha256"] = digest
    else:
        public_path = root / "library" / "intake" / filename
        _, digest = _write_exact(public_path, full)
        result["public_path"] = _relative(public_path, root)
        result["public_sha256"] = digest
    if has_local and has_repo:
        public_path = root / "library" / "intake" / filename
        _, digest = _write_exact(public_path, _redacted_stub(record))
        result["public_path"] = _relative(public_path, root)
        result["public_sha256"] = digest
    return result


def verify_action_reports(record: dict, *, root: Path = ROOT) -> None:
    report = record.get("execution", {}).get("report") or {}
    if report.get("status") != "complete":
        raise ValueError("Research Action report receipt is incomplete")
    for path_key, digest_key in (
        ("public_path", "public_sha256"),
        ("private_path", "private_sha256"),
    ):
        relative = report.get(path_key)
        expected = report.get(digest_key)
        if not relative:
            continue
        path = root / relative
        if not _inside(path, root) or not path.exists():
            raise ValueError(f"Research Action report is missing: {path_key}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Research Action report receipt is stale: {path_key}")


def eligible_action_paths(record: dict) -> list[str]:
    paths = []
    for document, execution in zip(
        record.get("document_manifest") or [],
        record.get("execution", {}).get("documents") or [],
        strict=True,
    ):
        if document["storage_permission"] == "local_only":
            continue
        paths.extend((execution.get("result") or {}).get("resolved_paths") or [])
    public_report = (record.get("execution", {}).get("report") or {}).get("public_path")
    if public_report:
        paths.append(public_report)
    return sorted(set(paths))


def iter_actions(*, root: Path = ROOT) -> Iterator[dict]:
    parent = _action_root(root)
    paths = sorted(parent.glob("ra_*.json")) if parent.exists() else []
    for path in paths:
        try:
            yield read_action(path.stem, root=root)
        except (OSError, ValueError):
            continue
