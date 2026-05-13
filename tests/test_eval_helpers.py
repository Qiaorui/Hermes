"""Tests for hermes.strategy.eval pure helper functions."""

from hermes.strategy.eval import _num, _pct, _yi, _wan, _rating_label


class TestNum:
    def test_normal(self):
        assert _num(100) == "100.00"

    def test_none(self):
        assert _num(None) == "N/A"

    def test_zero(self):
        assert _num(0) == "0.00"

    def test_negative(self):
        assert _num(-5) == "-5.00"

    def test_float(self):
        assert _num(3.14) == "3.14"


class TestPct:
    def test_normal(self):
        assert _pct(15.5) == "15.50%"

    def test_none(self):
        assert _pct(None) == "N/A"

    def test_zero(self):
        assert _pct(0) == "0.00%"

    def test_negative(self):
        assert _pct(-5) == "-5.00%"


class TestYi:
    def test_normal(self):
        assert _yi(123456789) == "1.23亿"

    def test_none(self):
        assert _yi(None) == "N/A"

    def test_zero(self):
        assert _yi(0) == "0.00亿"

    def test_small_value(self):
        # 500000 < 1e6 threshold, so no division — formatted directly
        assert _yi(500000) == "500000.00亿"

    def test_large_value(self):
        # Values > 1e6 are divided by 1e8
        assert _yi(500000000) == "5.00亿"


class TestWan:
    def test_normal(self):
        assert _wan(50000) == "5.00万"

    def test_none(self):
        assert _wan(None) == "N/A"

    def test_zero(self):
        assert _wan(0) == "0.00万"


class TestRatingLabel:
    def test_score_7(self):
        assert _rating_label(7) == "优秀"

    def test_score_5(self):
        assert _rating_label(5) == "良好"

    def test_score_3(self):
        assert _rating_label(3) == "一般"

    def test_score_1(self):
        assert _rating_label(1) == "较差"

    def test_score_0(self):
        assert _rating_label(0) == "较差"

    def test_boundary_7(self):
        assert _rating_label(7.0) == "优秀"

    def test_boundary_5(self):
        assert _rating_label(5.0) == "良好"