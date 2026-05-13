"""User configuration — project-local .hermes/config.json with sensible defaults."""

import json
from pathlib import Path

# Project-local data directory (next to pyproject.toml, not in home dir)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / ".hermes"
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
    "trigger_defaults": {
        "pe_high_threshold": 50,
        "stop_loss_pct": {
            "high_vol": 0.85,
            "medium_vol": 0.90,
            "low_vol": 0.93,
            "default": 0.90,
        },
        "stop_profit_pct": {
            "high_valuation": 1.10,
            "low_valuation": 1.25,
            "neutral": 1.20,
            "default": 1.20,
        },
    },
    "signal_thresholds": {
        "buy": 7,
        "hold": 5,
        "watch": 3,
    },
    "reports_dir": str(PROJECT_ROOT / ".hermes" / "reports"),
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


def set_nested_config(cfg: dict, key: str, value: str) -> tuple[dict, any]:
    """Set a nested config value using dot-notation path (e.g. 'factor_weights.value').
    Returns (updated_config, parsed_value). Raises ValueError if path invalid.
    """
    # Parse numeric value
    try:
        parsed = float(value)
        # Keep as float if original string has decimal point
        if "." not in value:
            parsed = int(parsed)
    except ValueError:
        parsed = value

    # Walk dot-notation path
    keys = key.split(".")
    target = cfg
    for k in keys[:-1]:
        if k not in target or not isinstance(target[k], dict):
            raise ValueError(f"Path {key} does not exist")
        target = target[k]

    final_key = keys[-1]
    if final_key not in target:
        raise ValueError(f"Path {key} does not exist")
    target[final_key] = parsed
    return cfg, parsed