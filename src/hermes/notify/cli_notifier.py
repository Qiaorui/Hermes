"""CLI notifier — print signals and trigger alerts to terminal."""

import sys


def notify(code: str, name: str, signal: str, message: str) -> None:
    icon = {"buy": "▲", "sell": "▼", "hold": "●", "watch": "◇"}
    sym = icon.get(signal, "?")
    print(f"{sym} [{code} {name}] {signal.upper()}: {message}", file=sys.stdout)


def notify_trigger(code: str, name: str, trigger_type: str, value: float, message: str) -> None:
    print(f"⚠ [{code} {name}] TRIGGER {trigger_type} (阈值 {value}): {message}", file=sys.stdout)