"""Shared disk cache utility for data modules.

Provides a simple JSON-based disk cache with TTL expiration.
Used by industry, industry_chain, macro, and events modules.
"""

import json
import time
import logging
from pathlib import Path

log = logging.getLogger(__name__)


class DiskCache:
    """Disk cache backed by a JSON file with TTL-based expiration."""

    def __init__(self, cache_dir: Path, filename: str, ttl: int = 4 * 3600):
        self.cache_dir = cache_dir
        self.cache_file = cache_dir / filename
        self.ttl = ttl

    def save(self, data: dict):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        payload = {"timestamp": time.time(), "data": data}
        self.cache_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        log.info(f"Saved cache to {self.cache_file}")

    def load(self) -> dict | None:
        if not self.cache_file.exists():
            return None
        try:
            payload = json.loads(self.cache_file.read_text(encoding="utf-8"))
            if time.time() - payload.get("timestamp", 0) > self.ttl:
                log.info(f"Cache expired (TTL {self.ttl}s)")
                return None
            data = payload.get("data")
            if not data:
                return None
            age = int(time.time() - payload.get("timestamp", 0))
            log.info(f"Loaded cache (age: {age}s)")
            return data
        except Exception:
            return None