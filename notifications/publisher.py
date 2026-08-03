"""Provider-neutral, outbound-only Daily Brief publisher.

The publisher owns delivery bookkeeping, not any StockBotv2 authority.  It
stores a private outbox/receipt database and delegates transport to an adapter.
The first adapter is a Discord webhook; adding another channel must not change
the Daily Brief or approval paths.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol

from storage.relational import (
    connect_sqlite,
    immediate_transaction,
    initialize_private_root,
    validate_private_destination,
)


ROOT = Path(__file__).resolve().parent.parent
_SCHEMA_VERSION = "1"
_DISCORD_MAX_CONTENT = 2_000
_PART_BUDGET = 1_850
_DISCORD_HOSTS = frozenset({"discord.com", "discordapp.com"})
_USER_ID_RE = re.compile(r"^[0-9]{2,32}$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_metadata(metadata: Mapping[str, Any] | None) -> str:
    payload = dict(metadata or {})
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return min(max(value, minimum), maximum)


@dataclass(frozen=True)
class NotificationSettings:
    """Configuration for the outbound adapter.

    The webhook is deliberately kept out of result objects and error strings.
    ``channel_alias`` is the provider-neutral logical destination key.
    """

    enabled: bool = True
    webhook_url: str | None = None
    tag_user_id: str | None = None
    channel_alias: str = "private-investing"
    content_class: str = "full_private"
    max_attempts: int = 3
    timeout_seconds: int = 15


def load_settings() -> NotificationSettings:
    """Load notifier settings from the process environment.

    Callers normally load ``.env`` before invoking the CLI.  This function does
    not print, persist, or validate the secret value beyond its URL shape.
    """

    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - optional import for library callers
        load_dotenv = None
    if load_dotenv is not None:
        load_dotenv(ROOT / ".env", override=False)
    webhook = (os.environ.get("NOTIFY_DISCORD_WEBHOOK_URL") or "").strip() or None
    tag = (os.environ.get("NOTIFY_DISCORD_TAG_USER_ID") or "").strip() or None
    return NotificationSettings(
        enabled=_bool_env("NOTIFY_ENABLED", True),
        webhook_url=webhook,
        tag_user_id=tag,
        channel_alias=(os.environ.get("NOTIFY_CHANNEL_ALIAS") or "private-investing").strip()
        or "private-investing",
        content_class=(os.environ.get("NOTIFY_CONTENT_CLASS") or "full_private").strip()
        or "full_private",
        max_attempts=_int_env("NOTIFY_MAX_ATTEMPTS", 3, minimum=1, maximum=10),
        timeout_seconds=_int_env("NOTIFY_TIMEOUT_SECONDS", 15, minimum=1, maximum=60),
    )


@dataclass(frozen=True)
class NotificationEnvelope:
    """Immutable handoff from an executor to the outbound publisher."""

    brief_text: str
    summary: str
    channel_alias: str
    content_class: str
    tag_user_id: str | None = None
    claude_share_url: str | None = None
    claude_session_id: str | None = None
    codex_thread_id: str | None = None
    created_at: str = ""

    @property
    def brief_digest(self) -> str:
        return _digest(self.brief_text)

    @property
    def delivery_key(self) -> str:
        return f"{self.brief_digest}:{self.channel_alias}"

    def metadata(self) -> dict[str, Any]:
        return {
            "claude_share_url": self.claude_share_url,
            "claude_session_id": self.claude_session_id,
            "codex_thread_id": self.codex_thread_id,
        }


def _validate_envelope(envelope: NotificationEnvelope) -> None:
    if not envelope.brief_text.strip():
        raise ValueError("brief_text is required")
    if not envelope.summary.strip():
        raise ValueError("summary is required")
    if not envelope.channel_alias.strip():
        raise ValueError("channel_alias is required")
    if envelope.content_class not in {"full_private", "redacted"}:
        raise ValueError("content_class must be full_private or redacted")
    if envelope.tag_user_id is not None and not _USER_ID_RE.fullmatch(envelope.tag_user_id):
        raise ValueError("tag_user_id must be a numeric Discord user id")
    if envelope.created_at:
        try:
            datetime.fromisoformat(envelope.created_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("created_at must be ISO-8601") from exc


def build_envelope(
    brief_text: str,
    *,
    summary: str,
    settings: NotificationSettings,
    claude_share_url: str | None = None,
    claude_session_id: str | None = None,
    codex_thread_id: str | None = None,
) -> NotificationEnvelope:
    """Build and validate the provider-neutral payload."""

    envelope = NotificationEnvelope(
        brief_text=brief_text,
        summary=summary,
        channel_alias=settings.channel_alias,
        content_class=settings.content_class,
        tag_user_id=settings.tag_user_id,
        claude_share_url=claude_share_url,
        claude_session_id=claude_session_id,
        codex_thread_id=codex_thread_id,
        created_at=_now(),
    )
    _validate_envelope(envelope)
    return envelope


class NotificationTransport(Protocol):
    """One outbound provider operation; no inbound command surface."""

    def send(self, content: str, *, allowed_mentions: dict[str, Any]) -> str | None:
        """Send one message and return the provider message id if available."""


class DiscordWebhookTransport:
    """Minimal Discord webhook adapter using the existing stdlib HTTP stack."""

    def __init__(self, webhook_url: str, *, timeout_seconds: int = 15):
        parsed = urllib.parse.urlparse(webhook_url)
        if parsed.scheme != "https" or parsed.hostname not in _DISCORD_HOSTS:
            raise ValueError("webhook_url must be an HTTPS Discord webhook URL")
        if not parsed.path.startswith("/api/webhooks/"):
            raise ValueError("webhook_url is not a Discord webhook path")
        self._url = webhook_url
        self._timeout_seconds = timeout_seconds

    def send(self, content: str, *, allowed_mentions: dict[str, Any]) -> str | None:
        if len(content) > _DISCORD_MAX_CONTENT:
            raise ValueError("discord_content_exceeds_2000_characters")
        url = self._url + ("&" if "?" in self._url else "?") + "wait=true"
        body = json.dumps(
            {
                "content": content,
                "allowed_mentions": allowed_mentions,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "StockBotv2-DailyBrief/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:  # noqa: S310
                raw = response.read().decode("utf-8", errors="replace")
                if response.status < 200 or response.status >= 300:
                    raise RuntimeError(f"discord_http_{response.status}")
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"discord_http_{exc.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"discord_transport_{type(exc).__name__}") from None
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {}
        message_id = payload.get("id") if isinstance(payload, dict) else None
        return str(message_id) if message_id else None


def _split_content(text: str) -> list[str]:
    """Split Markdown on line boundaries, preserving every source character."""

    if not text:
        return [""]
    chunks: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(line) <= _PART_BUDGET and len(current) + len(line) <= _PART_BUDGET:
            current += line
            continue
        if current:
            chunks.append(current)
            current = ""
        remaining = line
        while len(remaining) > _PART_BUDGET:
            chunks.append(remaining[:_PART_BUDGET])
            remaining = remaining[_PART_BUDGET:]
        current = remaining
    if current or not chunks:
        chunks.append(current)
    return chunks


def _summary_content(envelope: NotificationEnvelope) -> str:
    lines: list[str] = []
    if envelope.tag_user_id:
        lines.append(f"<@{envelope.tag_user_id}>")
    lines.append(envelope.summary.strip())
    links: list[str] = []
    if envelope.claude_share_url:
        links.append(f"Claude App：{envelope.claude_share_url}")
    if envelope.claude_session_id:
        links.append(f"Claude Code：`claude -r {envelope.claude_session_id}`")
    if envelope.codex_thread_id:
        links.append(f"Codex thread ID：`{envelope.codex_thread_id}`")
    if links:
        lines.extend(["", "Session：", *links])
    return "\n".join(lines)


@dataclass(frozen=True)
class DeliveryResult:
    status: str
    brief_digest: str
    channel_alias: str
    delivery_key: str
    sent_parts: int = 0
    total_parts: int = 0
    attempts: int = 0
    error_code: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "brief_digest": self.brief_digest,
            "channel_alias": self.channel_alias,
            "delivery_key": self.delivery_key,
            "sent_parts": self.sent_parts,
            "total_parts": self.total_parts,
            "attempts": self.attempts,
            "error_code": self.error_code,
        }


class NotificationPublisher:
    """Private outbox plus provider adapter, safe to call from either agent."""

    def __init__(
        self,
        *,
        repo_root: Path | str = ROOT,
        settings: NotificationSettings | None = None,
        transport: NotificationTransport | None = None,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.settings = settings or load_settings()
        private_root = initialize_private_root(
            self.repo_root / "library" / "private",
            repo_root=self.repo_root,
        )
        self.private_root = private_root
        self.db_path = validate_private_destination(
            private_root / "notifications" / "outbox.db",
            private_root=private_root,
            repo_root=self.repo_root,
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = connect_sqlite(self.db_path, create=True)
        self._init_schema()
        if transport is not None:
            self.transport = transport
        elif self.settings.webhook_url:
            self.transport = DiscordWebhookTransport(
                self.settings.webhook_url,
                timeout_seconds=self.settings.timeout_seconds,
            )
        else:
            self.transport = None

    def close(self) -> None:
        self.conn.close()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS notification_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS deliveries (
                delivery_key TEXT PRIMARY KEY,
                brief_digest TEXT NOT NULL,
                channel_alias TEXT NOT NULL,
                content_class TEXT NOT NULL,
                summary TEXT NOT NULL,
                brief_text TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                sent_at TEXT,
                status TEXT NOT NULL,
                last_error TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS deliveries_digest_channel
                ON deliveries (brief_digest, channel_alias);
            CREATE TABLE IF NOT EXISTS delivery_attempts (
                attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                delivery_key TEXT NOT NULL,
                part_index INTEGER NOT NULL,
                attempt_number INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                message_id TEXT,
                error_code TEXT,
                FOREIGN KEY(delivery_key) REFERENCES deliveries(delivery_key)
            );
            CREATE UNIQUE INDEX IF NOT EXISTS delivery_attempt_key
                ON delivery_attempts(delivery_key, part_index, attempt_number);
            INSERT OR IGNORE INTO notification_meta(key, value)
                VALUES ('schema_version', '1');
            """
        )
        self.conn.commit()

    def _ensure_delivery(self, envelope: NotificationEnvelope) -> sqlite3.Row:
        with immediate_transaction(self.conn):
            self.conn.execute(
                """
                INSERT OR IGNORE INTO deliveries(
                    delivery_key, brief_digest, channel_alias, content_class,
                    summary, brief_text, metadata_json, created_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """,
                (
                    envelope.delivery_key,
                    envelope.brief_digest,
                    envelope.channel_alias,
                    envelope.content_class,
                    envelope.summary,
                    envelope.brief_text,
                    _canonical_metadata(envelope.metadata()),
                    envelope.created_at or _now(),
                ),
            )
        row = self.conn.execute(
            "SELECT * FROM deliveries WHERE delivery_key = ?",
            (envelope.delivery_key,),
        ).fetchone()
        if row is None:
            raise RuntimeError("notification_delivery_not_created")
        return row

    def _parts(self, envelope: NotificationEnvelope) -> list[str]:
        full = _split_content(envelope.brief_text)
        total = len(full)
        return [f"Daily Brief 完整內容（第 {i}/{total} 段）\n{part}" for i, part in enumerate(full, 1)]

    def _sent_parts(self, delivery_key: str) -> set[int]:
        rows = self.conn.execute(
            "SELECT part_index FROM delivery_attempts WHERE delivery_key = ? AND status = 'sent'",
            (delivery_key,),
        ).fetchall()
        return {int(row[0]) for row in rows}

    def _attempt_count(self, delivery_key: str, part_index: int) -> int:
        row = self.conn.execute(
            """
            SELECT COUNT(*) FROM delivery_attempts
            WHERE delivery_key = ? AND part_index = ?
            """,
            (delivery_key, part_index),
        ).fetchone()
        return int(row[0]) if row else 0

    def _record_attempt(
        self,
        *,
        delivery_key: str,
        part_index: int,
        attempt_number: int,
        status: str,
        message_id: str | None = None,
        error_code: str | None = None,
    ) -> None:
        with immediate_transaction(self.conn):
            self.conn.execute(
                """
                INSERT INTO delivery_attempts(
                    delivery_key, part_index, attempt_number, started_at,
                    finished_at, status, message_id, error_code
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    delivery_key,
                    part_index,
                    attempt_number,
                    _now(),
                    _now(),
                    status,
                    message_id,
                    error_code,
                ),
            )

    def publish(self, envelope: NotificationEnvelope) -> DeliveryResult:
        """Best-effort publish; failures become a result and never raise."""

        try:
            _validate_envelope(envelope)
            row = self._ensure_delivery(envelope)
        except Exception as exc:
            return DeliveryResult(
                status="delivery_failed",
                brief_digest=envelope.brief_digest,
                channel_alias=envelope.channel_alias,
                delivery_key=envelope.delivery_key,
                error_code=f"local_{type(exc).__name__}",
            )

        if not self.settings.enabled:
            return DeliveryResult(
                status="disabled",
                brief_digest=envelope.brief_digest,
                channel_alias=envelope.channel_alias,
                delivery_key=envelope.delivery_key,
            )
        if row["status"] == "sent":
            total = len(self._parts(envelope)) + 1
            return DeliveryResult(
                status="deduplicated",
                brief_digest=envelope.brief_digest,
                channel_alias=envelope.channel_alias,
                delivery_key=envelope.delivery_key,
                sent_parts=total,
                total_parts=total,
            )
        if self.transport is None:
            self._mark_failed(envelope.delivery_key, "not_configured")
            return DeliveryResult(
                status="not_configured",
                brief_digest=envelope.brief_digest,
                channel_alias=envelope.channel_alias,
                delivery_key=envelope.delivery_key,
                error_code="not_configured",
            )

        summary_parts = _split_content(_summary_content(envelope))
        parts = [
            *[
                f"Daily Brief 摘要（第 {i}/{len(summary_parts)} 段）\n{part}"
                for i, part in enumerate(summary_parts, 1)
            ],
            *self._parts(envelope),
        ]
        sent = self._sent_parts(envelope.delivery_key)
        attempts = 0
        allowed_mentions: dict[str, Any] = {"parse": []}
        if envelope.tag_user_id:
            allowed_mentions = {"users": [envelope.tag_user_id]}

        for index, content in enumerate(parts):
            if index in sent:
                continue
            last_error: str | None = None
            for _ in range(self.settings.max_attempts):
                attempt_number = self._attempt_count(envelope.delivery_key, index) + 1
                attempts += 1
                try:
                    message_id = self.transport.send(
                        content,
                        allowed_mentions=allowed_mentions,
                    )
                except Exception as exc:
                    last_error = f"transport_{type(exc).__name__}"
                    self._record_attempt(
                        delivery_key=envelope.delivery_key,
                        part_index=index,
                        attempt_number=attempt_number,
                        status="delivery_failed",
                        error_code=last_error,
                    )
                    continue
                self._record_attempt(
                    delivery_key=envelope.delivery_key,
                    part_index=index,
                    attempt_number=attempt_number,
                    status="sent",
                    message_id=message_id,
                )
                sent.add(index)
                break
            else:
                self._mark_failed(envelope.delivery_key, last_error or "transport_failed")
                return DeliveryResult(
                    status="delivery_failed",
                    brief_digest=envelope.brief_digest,
                    channel_alias=envelope.channel_alias,
                    delivery_key=envelope.delivery_key,
                    sent_parts=len(sent),
                    total_parts=len(parts),
                    attempts=attempts,
                    error_code=last_error or "transport_failed",
                )

        with immediate_transaction(self.conn):
            self.conn.execute(
                "UPDATE deliveries SET status = 'sent', sent_at = ?, last_error = NULL WHERE delivery_key = ?",
                (_now(), envelope.delivery_key),
            )
        return DeliveryResult(
            status="sent",
            brief_digest=envelope.brief_digest,
            channel_alias=envelope.channel_alias,
            delivery_key=envelope.delivery_key,
            sent_parts=len(parts),
            total_parts=len(parts),
            attempts=attempts,
        )

    def _mark_failed(self, delivery_key: str, error_code: str) -> None:
        with immediate_transaction(self.conn):
            self.conn.execute(
                "UPDATE deliveries SET status = 'delivery_failed', last_error = ? WHERE delivery_key = ?",
                (error_code, delivery_key),
            )


def publish_daily_brief(
    brief_text: str,
    *,
    summary: str,
    repo_root: Path | str = ROOT,
    settings: NotificationSettings | None = None,
    transport: NotificationTransport | None = None,
    claude_share_url: str | None = None,
    claude_session_id: str | None = None,
    codex_thread_id: str | None = None,
) -> DeliveryResult:
    """Convenience entry point shared by Codex and Claude Code."""

    settings = settings or load_settings()
    try:
        envelope = build_envelope(
            brief_text,
            summary=summary,
            settings=settings,
            claude_share_url=claude_share_url,
            claude_session_id=claude_session_id,
            codex_thread_id=codex_thread_id,
        )
        publisher = NotificationPublisher(
            repo_root=repo_root,
            settings=settings,
            transport=transport,
        )
    except Exception as exc:
        digest = _digest(brief_text)
        return DeliveryResult(
            status="delivery_failed",
            brief_digest=digest,
            channel_alias=settings.channel_alias,
            delivery_key=f"{digest}:{settings.channel_alias}",
            error_code=f"local_{type(exc).__name__}",
        )
    try:
        return publisher.publish(envelope)
    finally:
        publisher.close()
