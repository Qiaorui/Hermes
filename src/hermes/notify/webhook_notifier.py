"""Webhook notifier — push trigger alerts to external services (DingTalk, custom webhook).

Requires webhook_url in ~/.hermes/config.json:
  {"webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=xxx"}

When configured, alerts are sent both to terminal (cli_notifier) and to the webhook.
"""

import json
import logging
import urllib.request
from hermes.config import load_config
from hermes.notify.cli_notifier import notify, notify_trigger

log = logging.getLogger(__name__)


def _send_webhook(payload: dict) -> bool:
    cfg = load_config()
    url = cfg.get("webhook_url")
    if not url:
        return False

    try:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        log.warning(f"Webhook push failed: {e}")
        return False


def push_notify(code: str, name: str, signal: str, message: str) -> None:
    """Notify via terminal + webhook (if configured)."""
    notify(code, name, signal, message)
    sig = signal.upper()
    payload = {"msgtype": "text", "text": {"content": f"[{code} {name}] {sig}: {message}"}}
    _send_webhook(payload)


def push_trigger(code: str, name: str, trigger_type: str, value: float, message: str) -> None:
    """Notify trigger alert via terminal + webhook (if configured)."""
    notify_trigger(code, name, trigger_type, value, message)
    content = f"[{code} {name}] TRIGGER {trigger_type} (阈值 {value}): {message}"
    payload = {"msgtype": "text", "text": {"content": content}}
    _send_webhook(payload)