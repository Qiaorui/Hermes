"""Tests for hermes.factors._ctx — DataContext."""

from hermes.factors._ctx import DataContext


class TestDataContextInit:
    def test_empty_init(self):
        ctx = DataContext()
        assert ctx.get("quote") is None

    def test_init_with_data(self):
        ctx = DataContext({"quote": {"price": 10.0}})
        assert ctx.get("quote") == {"price": 10.0}


class TestDataContextGet:
    def test_existing_key(self):
        ctx = DataContext({"quote": {"price": 10}})
        assert ctx.get("quote") == {"price": 10}

    def test_missing_key(self):
        ctx = DataContext({"quote": {"price": 10}})
        assert ctx.get("kline") is None

    def test_default_value(self):
        ctx = DataContext()
        assert ctx.get("missing", "default") == "default"


class TestDataContextHas:
    def test_normal_data(self):
        ctx = DataContext({"quote": {"price": 10}})
        assert ctx.has("quote") is True

    def test_error_dict(self):
        ctx = DataContext({"quote": {"error": "Failed", "code": "000001"}})
        assert ctx.has("quote") is False

    def test_missing_key(self):
        ctx = DataContext({"quote": {"price": 10}})
        assert ctx.has("kline") is False

    def test_empty_data(self):
        ctx = DataContext()
        assert ctx.has("quote") is False


class TestDataContextSet:
    def test_set_new_key(self):
        ctx = DataContext()
        ctx.set("quote", {"price": 10})
        assert ctx.has("quote") is True
        assert ctx.get("quote") == {"price": 10}

    def test_set_overwrite(self):
        ctx = DataContext({"quote": {"price": 10}})
        ctx.set("quote", {"price": 20})
        assert ctx.get("quote") == {"price": 20}


class TestDataContextMerge:
    def test_merge_adds_keys(self):
        ctx = DataContext({"quote": {"price": 10}})
        ctx.merge({"kline": {"klines": []}})
        assert ctx.has("quote") is True
        assert ctx.has("kline") is True

    def test_merge_overwrites(self):
        ctx = DataContext({"quote": {"price": 10}})
        ctx.merge({"quote": {"price": 20}})
        assert ctx.get("quote") == {"price": 20}