"""Tests for hermes.portfolio.models — dataclass construction and defaults."""

from hermes.portfolio.models import Holding, WatchItem, TriggerCondition, Report, Transaction


class TestHolding:
    def test_construction(self):
        h = Holding(id=1, code="002352", name="顺丰控股", cost_price=40.5, shares=100, buy_date="2024-01-01", created_at="2024-01-01 10:00:00")
        assert h.code == "002352"
        assert h.cost_price == 40.5
        assert h.shares == 100

    def test_market_value(self):
        h = Holding(id=1, code="002352", name="顺丰控股", cost_price=40.5, shares=100, buy_date="2024-01-01", created_at="2024-01-01")
        assert h.cost_price * h.shares == 4050


class TestWatchItem:
    def test_construction(self):
        w = WatchItem(id=1, code="000001", name="平安银行", added_at="2024-01-01")
        assert w.code == "000001"


class TestTriggerCondition:
    def test_default_active(self):
        t = TriggerCondition(id=1, code="002352", name="顺丰控股", type="price_stop_loss", value=36.0, description="止损", active=True, source="auto", created_at="2024-01-01")
        assert t.active is True

    def test_type_varieties(self):
        types = ["price_stop_loss", "price_stop_profit", "pe_high", "near_52w_low"]
        for tp in types:
            t = TriggerCondition(id=1, code="002352", name="test", type=tp, value=10.0, description="", active=True, source="auto", created_at="2024-01-01")
            assert t.type == tp


class TestTransaction:
    def test_construction(self):
        t = Transaction(id=1, code="002352", name="顺丰控股", action="buy", price=40.5, shares=100, amount=4050.0, note="", created_at="2024-01-01")
        assert t.action == "buy"
        assert t.amount == 4050.0

    def test_sell_action(self):
        t = Transaction(id=2, code="002352", name="顺丰控股", action="sell", price=45.0, shares=100, amount=4500.0, note="清仓", created_at="2024-01-02")
        assert t.action == "sell"


class TestReport:
    def test_construction(self):
        r = Report(id=1, code="002352", content="report text", score=22, created_at="2024-01-01")
        assert r.code == "002352"
        assert r.score == 22