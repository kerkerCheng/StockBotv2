from __future__ import annotations

from pathlib import Path

from notifications.publisher import (
    NotificationPublisher,
    NotificationSettings,
    build_envelope,
    publish_daily_brief,
)


class FakeTransport:
    def __init__(self, *, fail_calls: set[int] | None = None):
        self.calls: list[tuple[str, dict]] = []
        self.fail_calls = fail_calls or set()

    def send(self, content: str, *, allowed_mentions: dict) -> str:
        call_no = len(self.calls) + 1
        self.calls.append((content, allowed_mentions))
        if call_no in self.fail_calls:
            raise RuntimeError("simulated transport failure")
        return f"message-{call_no}"


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
