"""Portfolio models — dataclasses for holdings, watchlist, triggers, reports."""

from dataclasses import dataclass


@dataclass
class Holding:
    id: int = 0
    code: str = ""
    name: str = ""
    cost_price: float = 0.0
    shares: int = 0
    buy_date: str = ""
    created_at: str = ""


@dataclass
class WatchItem:
    id: int = 0
    code: str = ""
    name: str = ""
    added_at: str = ""


@dataclass
class TriggerCondition:
    id: int = 0
    code: str = ""
    name: str = ""
    type: str = ""
    value: float = 0.0
    description: str = ""
    active: bool = True
    created_at: str = ""


@dataclass
class Report:
    id: int = 0
    code: str = ""
    content: str = ""
    score: int = 0
    created_at: str = ""