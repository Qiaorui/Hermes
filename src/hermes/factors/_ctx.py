"""DataContext — pre-fetched data container to avoid redundant API calls.

Passed from evaluate → composite → individual factors, so each factor
reads pre-fetched data instead of making independent network calls.
"""

from __future__ import annotations


class DataContext:
    """Stores pre-fetched data dicts keyed by module name.
    Factors call ctx.get("quote") instead of stock_quote(code) etc.
    """

    def __init__(self, data: dict[str, dict] | None = None):
        self._data: dict[str, dict] = data or {}

    def get(self, key: str, default=None):
        """Get pre-fetched data by key (e.g. 'quote', 'kline', 'income')."""
        return self._data.get(key, default)

    def has(self, key: str) -> bool:
        """Check if key exists and is not an error dict."""
        val = self._data.get(key)
        return val is not None and "error" not in val

    def set(self, key: str, value):
        """Store data by key."""
        self._data[key] = value

    def merge(self, extra: dict[str, dict]):
        """Merge additional data into this context."""
        self._data.update(extra)