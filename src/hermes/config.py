"""User configuration — ~/.hermes/config.json with sensible defaults."""

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".hermes"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "factor_weights": {
        "value": 0.20,
        "growth": 0.20,
        "quality": 0.20,
        "dividend": 0.15,
        "momentum": 0.06,
        "capital_flow": 0.06,
        "volatility": 0.06,
        "liquidity": 0.07,
    },
    "reports_dir": str(Path.home() / ".hermes" / "reports"),
}


def load_config() -> dict:
    """Load config from disk, merging with defaults for missing keys."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    merged = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        try:
            user = json.loads(CONFIG_FILE.read_text())
            merged.update(user)
            # Deep merge factor_weights
            if "factor_weights" in user:
                merged["factor_weights"] = {**DEFAULT_CONFIG["factor_weights"], **user["factor_weights"]}
        except Exception:
            pass
    return merged


def save_config(data: dict) -> None:
    """Save config to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def get_factor_weights() -> dict[str, float]:
    """Get factor weights from config (user override + defaults)."""
    return load_config()["factor_weights"]


def get_reports_dir() -> Path:
    """Get reports output directory from config."""
    return Path(load_config()["reports_dir"])