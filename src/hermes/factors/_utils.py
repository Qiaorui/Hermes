"""Shared utilities for factor modules."""

from typing import Any


def weighted_avg(scores: dict[str, float | None], weights: dict[str, float]) -> float | None:
    """Compute weighted average only from available (non-None) scores.
    Renormalizes weights so total equals 1.0 for available scores.
    Returns None if no scores are available.
    """
    available = {k: v for k, v in scores.items() if v is not None}
    if not available:
        return None
    total_w = sum(weights.get(k, 0) for k in available)
    if total_w == 0:
        return None
    return round(sum(v * weights.get(k, 0) for k, v in available.items()) / total_w, 1)


def coverage_pct(scores: dict[str, float | None]) -> float:
    """Percentage of sub-factors with available (non-None) scores."""
    available = sum(1 for v in scores.values() if v is not None)
    return round(available / len(scores) * 100, 0) if scores else 0


def unavailable_list(scores: dict[str, float | None], reasons: dict[str, str] | None = None) -> list[dict[str, str]]:
    """Build a list of unavailable sub-factors with reasons."""
    result = []
    for k, v in scores.items():
        if v is None:
            reason = (reasons or {}).get(k, "data unavailable")
            result.append({"sub_factor": k, "reason": reason})
    return result