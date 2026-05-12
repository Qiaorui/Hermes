"""Notifier protocol definition."""

from typing import Protocol


class Notifier(Protocol):
    """Send notifications for strategy signals."""

    def notify(self, code: str, name: str, signal: str, message: str) -> None:
        ...

    def notify_trigger(self, code: str, name: str, trigger_type: str, value: float, message: str) -> None:
        ...