"""Provider-neutral outbound notification primitives."""

from .publisher import (
    DiscordWebhookTransport,
    DeliveryResult,
    NotificationEnvelope,
    NotificationSettings,
    NotificationPublisher,
    NotificationTransport,
    TransportSendResult,
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
    "TransportSendResult",
    "build_envelope",
    "load_settings",
]
