from __future__ import annotations

from pathlib import Path
import json
from urllib.parse import parse_qs, urlparse

from notifications.publisher import (
    DiscordWebhookTransport,
    NotificationPublisher,
    NotificationSettings,
    TransportSendResult,
    build_envelope,
    publish_daily_brief,
)


class FakeTransport:
    def __init__(self, *, fail_calls: set[int] | None = None):
        self.calls: list[tuple[str, dict, str | None, str | None]] = []
        self.fail_calls = fail_calls or set()

    def send(
        self,
        content: str,
        *,
        allowed_mentions: dict,
        thread_name: str | None = None,
        thread_id: str | None = None,
    ) -> TransportSendResult:
        call_no = len(self.calls) + 1
        self.calls.append((content, allowed_mentions, thread_name, thread_id))
        if call_no in self.fail_calls:
            raise RuntimeError("simulated transport failure")
        return TransportSendResult(
            message_id=f"message-{call_no}",
            thread_id=thread_id or "thread-1",
        )


def _settings(**kwargs) -> NotificationSettings:
    values = {
        "enabled": True,
        "webhook_url": None,
        "tag_user_id": "356614259477839872",
        "channel_alias": "private-investing",
        "content_class": "full_private",
        "max_attempts": 3,
        "timeout_seconds": 1,
    }
    values.update(kwargs)
    return NotificationSettings(**values)


def _envelope(settings: NotificationSettings, text: str = "# Daily Brief 2026-08-04\n\nNO ACTION"):
    return build_envelope(
        text,
        summary="今日 Daily Brief：NO ACTION",
        settings=settings,
        claude_session_id="claude-session-1",
        codex_thread_id="codex-thread-1",
    )


def test_sends_summary_and_full_markdown_then_deduplicates(tmp_path: Path) -> None:
    transport = FakeTransport()
    settings = _settings()
    publisher = NotificationPublisher(
        repo_root=tmp_path,
        settings=settings,
        transport=transport,
    )
    try:
        envelope = _envelope(settings, "# Daily Brief 2026-08-04\n\n| A | B |\n|---|---|\n| 1 | 2 |")
        first = publisher.publish(envelope)
        second = publisher.publish(envelope)
    finally:
        publisher.close()

    assert first.status == "sent"
    assert first.total_parts == 2
    assert second.status == "deduplicated"
    assert len(transport.calls) == 2
    assert transport.calls[0][1] == {"users": ["356614259477839872"]}
    assert transport.calls[0][2] == "Daily Brief 2026-08-04"
    assert transport.calls[0][3] is None
    assert transport.calls[1][2] is None
    assert transport.calls[1][3] == "thread-1"
    assert first.thread_id == "thread-1"
    assert second.thread_id == "thread-1"
    assert "claude -r claude-session-1" in transport.calls[0][0]
    assert "codex-thread-1" in transport.calls[0][0]
    assert "| A | B |" in transport.calls[1][0]
    assert (tmp_path / "library" / "private" / "notifications" / "outbox.db").exists()


def test_same_digest_can_publish_to_a_different_logical_channel(tmp_path: Path) -> None:
    transport = FakeTransport()
    first_settings = _settings(channel_alias="private-investing")
    second_settings = _settings(channel_alias="private-investing-backup")
    p1 = NotificationPublisher(repo_root=tmp_path, settings=first_settings, transport=transport)
    p2 = NotificationPublisher(repo_root=tmp_path, settings=second_settings, transport=transport)
    try:
        assert p1.publish(_envelope(first_settings)).status == "sent"
        assert p2.publish(_envelope(second_settings)).status == "sent"
    finally:
        p1.close()
        p2.close()
    assert len(transport.calls) == 4


def test_failed_part_is_retried_and_later_call_resumes_sent_parts(tmp_path: Path) -> None:
    transport = FakeTransport(fail_calls={2, 3})
    first_settings = _settings(max_attempts=1)
    envelope = _envelope(first_settings)
    p1 = NotificationPublisher(repo_root=tmp_path, settings=first_settings, transport=transport)
    try:
        first = p1.publish(envelope)
    finally:
        p1.close()
    assert first.status == "delivery_failed"
    assert first.sent_parts == 1
    assert first.attempts == 2

    p2 = NotificationPublisher(repo_root=tmp_path, settings=_settings(), transport=transport)
    try:
        second = p2.publish(envelope)
    finally:
        p2.close()
    assert second.status == "sent"
    # The summary was not resent; only the failed full-content part was retried.
    assert len(transport.calls) == 4
    assert transport.calls[1][2] is None
    assert transport.calls[1][3] == "thread-1"
    assert transport.calls[2][2] is None
    assert transport.calls[2][3] == "thread-1"
    assert transport.calls[3][3] == "thread-1"


def test_discord_forum_transport_creates_then_targets_thread(monkeypatch) -> None:
    class FakeResponse:
        status = 200

        def __init__(self, payload: dict):
            self.payload = payload

        def read(self) -> bytes:
            return json.dumps(self.payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

    requests = []
    responses = iter([
        FakeResponse({"id": "message-1", "channel_id": "thread-1"}),
        FakeResponse({"id": "message-2", "channel_id": "thread-1"}),
    ])

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return next(responses)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    transport = DiscordWebhookTransport(
        "https://discord.com/api/webhooks/123/token",
        timeout_seconds=7,
    )

    first = transport.send(
        "summary",
        allowed_mentions={"parse": []},
        thread_name="Daily Brief 2026-08-04",
    )
    second = transport.send(
        "full brief",
        allowed_mentions={"parse": []},
        thread_id="thread-1",
    )

    assert first == TransportSendResult(message_id="message-1", thread_id="thread-1")
    assert second == TransportSendResult(message_id="message-2", thread_id="thread-1")
    first_request, first_timeout = requests[0]
    second_request, second_timeout = requests[1]
    assert first_timeout == second_timeout == 7
    assert parse_qs(urlparse(first_request.full_url).query) == {"wait": ["true"]}
    assert parse_qs(urlparse(second_request.full_url).query) == {
        "wait": ["true"],
        "thread_id": ["thread-1"],
    }
    assert json.loads(first_request.data) == {
        "content": "summary",
        "allowed_mentions": {"parse": []},
        "thread_name": "Daily Brief 2026-08-04",
    }
    assert json.loads(second_request.data) == {
        "content": "full brief",
        "allowed_mentions": {"parse": []},
    }


def test_disabled_publisher_does_not_call_transport(tmp_path: Path) -> None:
    transport = FakeTransport()
    settings = _settings(enabled=False)
    publisher = NotificationPublisher(repo_root=tmp_path, settings=settings, transport=transport)
    try:
        result = publisher.publish(_envelope(settings))
    finally:
        publisher.close()
    assert result.status == "disabled"
    assert transport.calls == []


def test_invalid_provider_configuration_is_best_effort(tmp_path: Path) -> None:
    settings = _settings(webhook_url="https://example.invalid/not-a-discord-webhook")
    result = publish_daily_brief(
        "# Daily Brief 2026-08-04\n\nNO ACTION",
        summary="smoke",
        repo_root=tmp_path,
        settings=settings,
    )
    assert result.status == "delivery_failed"
    assert result.error_code == "local_ValueError"
