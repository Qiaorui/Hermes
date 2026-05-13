"""Tests for hermes.factors._utils — weighted_avg, coverage_pct, unavailable_list."""

from hermes.factors._utils import weighted_avg, coverage_pct, unavailable_list
from hermes.factors.composite import DEFAULT_WEIGHTS


class TestWeightedAvg:
    def test_all_scores_present(self):
        scores = {"value": 8.0, "growth": 7.0, "quality": 6.0}
        weights = {"value": 0.5, "growth": 0.3, "quality": 0.2}
        result = weighted_avg(scores, weights)
        assert result == round(8.0 * 0.5 + 7.0 * 0.3 + 6.0 * 0.2, 1)

    def test_some_scores_none(self):
        scores = {"value": 8.0, "growth": None, "quality": 6.0}
        weights = {"value": 0.5, "growth": 0.3, "quality": 0.2}
        # Growth excluded, weights renormalized: value=0.5/(0.5+0.2)=5/7, quality=0.2/0.7=2/7
        result = weighted_avg(scores, weights)
        total_w = 0.5 + 0.2
        expected = round((8.0 * 0.5 + 6.0 * 0.2) / total_w, 1)
        assert result == expected

    def test_all_scores_none(self):
        scores = {"value": None, "growth": None}
        weights = {"value": 0.5, "growth": 0.5}
        assert weighted_avg(scores, weights) is None

    def test_single_score(self):
        scores = {"value": 9.0}
        weights = {"value": 1.0}
        assert weighted_avg(scores, weights) == 9.0

    def test_empty_scores(self):
        assert weighted_avg({}, {}) is None

    def test_zero_weights(self):
        scores = {"value": 5.0}
        weights = {"value": 0.0}
        assert weighted_avg(scores, weights) is None

    def test_default_weights_sum_to_one(self):
        total = sum(DEFAULT_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9


class TestCoveragePct:
    def test_all_present(self):
        assert coverage_pct({"a": 5, "b": 3, "c": 7}) == 100

    def test_partial_none(self):
        assert coverage_pct({"a": 5, "b": None, "c": 7}) == 67

    def test_all_none(self):
        assert coverage_pct({"a": None, "b": None}) == 0

    def test_empty_dict(self):
        assert coverage_pct({}) == 0


class TestUnavailableList:
    def test_no_unavailable(self):
        result = unavailable_list({"a": 5, "b": 3}, {})
        assert result == []

    def test_default_reason(self):
        result = unavailable_list({"a": None, "b": 3}, {})
        assert result == [{"sub_factor": "a", "reason": "data unavailable"}]

    def test_custom_reason(self):
        result = unavailable_list({"a": None}, {"a": "PE data unavailable"})
        assert result == [{"sub_factor": "a", "reason": "PE data unavailable"}]

    def test_none_reason(self):
        # When reasons dict has None for a key, .get returns None (not default)
        result = unavailable_list({"a": None}, {"a": None})
        assert result == [{"sub_factor": "a", "reason": None}]

    def test_multiple_unavailable(self):
        scores = {"a": None, "b": None, "c": 5}
        reasons = {"a": "reason_a", "b": "reason_b"}
        result = unavailable_list(scores, reasons)
        assert len(result) == 2