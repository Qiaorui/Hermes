"""Tests for hermes.config — _deep_merge, set_nested_config."""

from hermes.config import _deep_merge, set_nested_config, DEFAULT_CONFIG


class TestDeepMerge:
    def test_flat_merge(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        base = {"weights": {"a": 0.5, "b": 0.5}}
        override = {"weights": {"b": 0.3, "c": 0.2}}
        result = _deep_merge(base, override)
        assert result == {"weights": {"a": 0.5, "b": 0.3, "c": 0.2}}

    def test_deep_nested_merge(self):
        base = {"triggers": {"stop": {"high": 0.85, "low": 0.93}}}
        override = {"triggers": {"stop": {"low": 0.95}}}
        result = _deep_merge(base, override)
        assert result == {"triggers": {"stop": {"high": 0.85, "low": 0.95}}}

    def test_override_scalar_with_dict(self):
        base = {"key": "old_string"}
        override = {"key": {"nested": True}}
        result = _deep_merge(base, override)
        assert result == {"key": {"nested": True}}

    def test_override_dict_with_scalar(self):
        base = {"key": {"nested": True}}
        override = {"key": "new_string"}
        result = _deep_merge(base, override)
        assert result == {"key": "new_string"}

    def test_empty_override(self):
        base = {"a": 1}
        result = _deep_merge(base, {})
        assert result == {"a": 1}

    def test_empty_base(self):
        result = _deep_merge({}, {"a": 1})
        assert result == {"a": 1}


class TestSetNestedConfig:
    def test_simple_key(self):
        cfg = {"a": 1}
        cfg, parsed = set_nested_config(cfg, "a", "2")
        assert parsed == 2
        assert cfg["a"] == 2

    def test_float_value(self):
        cfg = {"weights": {"value": 0.20}}
        cfg, parsed = set_nested_config(cfg, "weights.value", "0.30")
        assert parsed == 0.30
        assert cfg["weights"]["value"] == 0.30

    def test_int_value(self):
        cfg = {"thresholds": {"buy": 7}}
        cfg, parsed = set_nested_config(cfg, "thresholds.buy", "8")
        assert parsed == 8

    def test_string_value(self):
        cfg = {"webhook_url": ""}
        cfg, parsed = set_nested_config(cfg, "webhook_url", "https://example.com")
        assert parsed == "https://example.com"

    def test_invalid_path_raises(self):
        cfg = {"a": 1}
        try:
            set_nested_config(cfg, "b.c", "1")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_deep_path(self):
        cfg = {"triggers": {"stop": {"high": 0.85}}}
        cfg, parsed = set_nested_config(cfg, "triggers.stop.high", "0.80")
        assert parsed == 0.80
        assert cfg["triggers"]["stop"]["high"] == 0.80


class TestDefaultConfig:
    def test_weights_sum(self):
        weights = DEFAULT_CONFIG["factor_weights"]
        assert abs(sum(weights.values()) - 1.0) < 1e-9

    def test_signal_thresholds_present(self):
        assert "signal_thresholds" in DEFAULT_CONFIG
        assert DEFAULT_CONFIG["signal_thresholds"]["buy"] == 7

    def test_trigger_defaults_present(self):
        assert "trigger_defaults" in DEFAULT_CONFIG
        assert "stop_loss_pct" in DEFAULT_CONFIG["trigger_defaults"]