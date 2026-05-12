"""Strategy protocol definition."""

from typing import Protocol


class Strategy(Protocol):
    """Base strategy interface. All strategies must implement analyze() and get_triggers()."""

    def analyze(self, code: str) -> dict:
        """Analyze a stock. Return dict with 'signal', 'report', 'score' keys."""
        ...

    def get_triggers(self, code: str, analysis: dict) -> list[dict]:
        """Extract trigger conditions from analysis. Return list of trigger dicts."""
        ...


# Signal values
BUY = "buy"
SELL = "sell"
HOLD = "hold"
WATCH = "watch"