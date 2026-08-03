"""Provider-neutral outbound notification primitives."""

from .publisher import (
    DiscordWebhookTransport,
    DeliveryResult,
    NotificationEnvelope,
    NotificationSettings,
    NotificationPublisher,
    NotificationTransport,
    build_envelope,
    load_settings,
)

__all__ = [
    "DeliveryResult",
    "DiscordWebhookTransport",
    "NotificationEnvelope",
    "NotificationPublisher",
    "NotificationSettings",
    "NotificationTransport",
    "build_envelope",
    "load_settings",
]
