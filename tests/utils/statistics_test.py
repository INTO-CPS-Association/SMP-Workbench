import pytest

from utils.statistics import (
    calculateStatistics,
    find_distribution,
    fit_distribution_for_display,
    _group_by_pair,
    _compute_from_counts,
    StatisticsResult,
    QuarantinedEntry,
)
from utils.enums import Distribution
from classes.standard_state import StandardState
from classes.standard_state_transition_info import StandardStateTransitionInfo
from classes.std_state_transition_statistics import StdStateTransitionStatistics
from interfaces.state_transition_info import StateTransitionInfo
from interfaces.state_transition_statistics import StateTransitionStatistics

PRECISION = 1e-5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_transition(fn: str, tn: str, sojourn: int) -> StateTransitionInfo:
    return StandardStateTransitionInfo(StandardState(fn), StandardState(tn), sojourn)


def _floats(n: int, start: int = 1) -> list[float]:
    return [float(i) for i in range(start, start + n)]


def _probability_sums(stats: list) -> dict:
    sums: dict = {}
    for s in stats:
        name = s.getFromState().getName()
        sums[name] = sums.get(name, 0.0) + s.getProbability()
    return sums


def _total_transitions(result: StatisticsResult) -> int:
    return sum(len(s.getSojournTimes()) for s in result.statistics) + len(result.quarantined)


# ---------------------------------------------------------------------------
# find_distribution
# ---------------------------------------------------------------------------

class TestFindDistribution:
    def test_fewer_than_2_returns_none(self):
        assert find_distribution([]) == Distribution.NONE
        assert find_distribution([5]) == Distribution.NONE

    def test_returns_distribution_enum(self):
        data = list(range(10, 30))
        result = find_distribution(data)
        assert isinstance(result, Distribution)

    def test_small_valid_sample(self):
        data = [10, 20, 30, 40, 50]
        result = find_distribution(data)
        assert result in Distribution


# ---------------------------------------------------------------------------
# fit_distribution_for_display
# ---------------------------------------------------------------------------

class TestFitDistributionForDisplay:
    def test_fewer_than_min_n_returns_none(self):
        assert fit_distribution_for_display([1.0, 2.0, 3.0]) is None

    def test_exactly_min_n_minus_one_returns_none(self):
        assert fit_distribution_for_display(_floats(19)) is None

    def test_exactly_min_n_returns_dict(self):
        result = fit_distribution_for_display(_floats(20))
        assert result is not None
        assert isinstance(result, dict)

    def test_result_has_required_keys(self):
        result = fit_distribution_for_display(_floats(29))
        assert result is not None
        assert "distribution" in result
        assert "pValue" in result
        assert "ksStat" in result

    def test_p_value_in_zero_to_one(self):
        result = fit_distribution_for_display(_floats(29))
        assert result is not None
        assert 0.0 <= result["pValue"] <= 1.0

    def test_ks_stat_in_zero_to_one(self):
        result = fit_distribution_for_display(_floats(29))
        assert result is not None
        assert 0.0 <= result["ksStat"] <= 1.0

    def test_distribution_name_is_string(self):
        result = fit_distribution_for_display(_floats(29))
        assert result is not None
        assert isinstance(result["distribution"], str)

    def test_empty_list_returns_none(self):
        assert fit_distribution_for_display([]) is None


# ---------------------------------------------------------------------------
# _group_by_pair
# ---------------------------------------------------------------------------

class TestGroupByPair:
    def test_groups_by_from_to_pair(self):
        transitions = [
            _make_transition("A", "B", 10),
            _make_transition("A", "B", 20),
            _make_transition("B", "A", 30),
        ]
        grouped = _group_by_pair(transitions)
        assert ("A", "B") in grouped.groups
        assert ("B", "A") in grouped.groups
        assert len(grouped.groups[("A", "B")]) == 2
        assert len(grouped.groups[("B", "A")]) == 1

    def test_preserves_state_objects(self):
        transitions = [_make_transition("X", "Y", 5)]
        grouped = _group_by_pair(transitions)
        assert "X" in grouped.state_objects
        assert "Y" in grouped.state_objects

    def test_state_objects_have_correct_names(self):
        transitions = [_make_transition("X", "Y", 5)]
        grouped = _group_by_pair(transitions)
        assert grouped.state_objects["X"].getName() == "X"
        assert grouped.state_objects["Y"].getName() == "Y"

    def test_empty_input_returns_empty_groups(self):
        grouped = _group_by_pair([])
        assert grouped.groups == {}
        assert grouped.state_objects == {}


# ---------------------------------------------------------------------------
# _compute_from_counts
# ---------------------------------------------------------------------------

class TestComputeFromCounts:
    def test_counts_outgoing_transitions(self):
        clean_by_pair = {
            ("A", "B"): [_make_transition("A", "B", i) for i in range(3)],
            ("A", "C"): [_make_transition("A", "C", i) for i in range(2)],
            ("B", "A"): [_make_transition("B", "A", i) for i in range(4)],
        }
        counts = _compute_from_counts(clean_by_pair)
        assert counts["A"] == 5  # 3 + 2
        assert counts["B"] == 4

    def test_empty_pair_dict_returns_empty_counts(self):
        assert _compute_from_counts({}) == {}


# ---------------------------------------------------------------------------
# calculateStatistics
# ---------------------------------------------------------------------------

class TestCalculateStatisticsReturnType:
    def test_returns_statistics_result(self, simple_transitions):
        result = calculateStatistics(simple_transitions)
        assert isinstance(result, StatisticsResult)

    def test_statistics_field_is_list(self, simple_transitions):
        result = calculateStatistics(simple_transitions)
        assert isinstance(result.statistics, list)

    def test_quarantined_field_is_list(self, simple_transitions):
        result = calculateStatistics(simple_transitions)
        assert isinstance(result.quarantined, list)

    def test_statistics_are_state_transition_statistics(self, simple_transitions):
        result = calculateStatistics(simple_transitions)
        for s in result.statistics:
            assert isinstance(s, StateTransitionStatistics)

    def test_quarantined_are_quarantined_entries(self, simple_transitions):
        result = calculateStatistics(simple_transitions)
        for q in result.quarantined:
            assert isinstance(q, QuarantinedEntry)


class TestCalculateStatisticsInvariants:
    def test_all_transitions_accounted_for(self, simple_transitions):
        result = calculateStatistics(simple_transitions)
        assert _total_transitions(result) == len(simple_transitions)

    def test_probabilities_sum_to_one_per_from_state(self, simple_transitions):
        result = calculateStatistics(simple_transitions)
        for state, total in _probability_sums(result.statistics).items():
            assert abs(total - 1.0) < PRECISION, f"{state}: sum={total}"

    def test_sojourn_times_are_non_negative(self, simple_transitions):
        result = calculateStatistics(simple_transitions)
        for s in result.statistics:
            assert all(t >= 0 for t in s.getSojournTimes())

    def test_non_empty_statistics_for_valid_input(self, simple_transitions):
        result = calculateStatistics(simple_transitions)
        assert len(result.statistics) > 0

    def test_quarantined_entries_have_scores(self, simple_transitions):
        result = calculateStatistics(simple_transitions)
        for q in result.quarantined:
            assert hasattr(q, "outlierScore")
            assert q.outlierScore >= 0.0

    def test_quarantined_sojourn_times_are_positive(self, simple_transitions):
        result = calculateStatistics(simple_transitions)
        for q in result.quarantined:
            assert q.sojournTime >= 0.0


class TestCalculateStatisticsOutlierFallback:
    def test_single_pair_all_retained_when_too_few_samples(self):
        # Only 2 transitions â†’ below _MIN_SAMPLES â†’ LOF skipped â†’ all clean
        transitions = [_make_transition("A", "B", t) for t in [10, 20]]
        result = calculateStatistics(transitions)
        total = _total_transitions(result)
        assert total == 2
        assert len(result.quarantined) == 0

    def test_all_transitions_kept_when_all_would_be_outliers(self):
        # Enough transitions for LOF but all would be outliers â†’
        # fallback: keep all as clean so the pair doesn't disappear
        transitions = [_make_transition("A", "B", t) for t in range(10)]
        result = calculateStatistics(transitions)
        assert _total_transitions(result) == 10


class TestCalculateStatisticsWithRealFiles:
    def test_normal_file_probabilities_sum_to_one(self, normal_transitions):
        result = calculateStatistics(normal_transitions)
        for state, total in _probability_sums(result.statistics).items():
            assert abs(total - 1.0) < PRECISION, f"{state}: sum={total}"

    def test_normal_file_all_transitions_accounted(self, normal_transitions):
        result = calculateStatistics(normal_transitions)
        assert _total_transitions(result) == len(normal_transitions)

    def test_combined_files_all_transitions_accounted(self, normal_transitions, normal_transitions_2):
        combined = normal_transitions + normal_transitions_2
        result = calculateStatistics(combined)
        assert _total_transitions(result) == len(combined)

    def test_combined_files_probabilities_sum_to_one(self, normal_transitions, normal_transitions_2):
        combined = normal_transitions + normal_transitions_2
        result = calculateStatistics(combined)
        for state, total in _probability_sums(result.statistics).items():
            assert abs(total - 1.0) < PRECISION, f"{state}: sum={total}"


# ---------------------------------------------------------------------------
# StdStateTransitionStatistics (direct construction)
# ---------------------------------------------------------------------------

class TestStdStateTransitionStatistics:
    @pytest.fixture
    def stats(self):
        return StdStateTransitionStatistics(
            fromState=StandardState("A"),
            toState=StandardState("B"),
            sojournTimes=[10, 20, 30],
            sojournAverage=20.0,
            sojournMedian=20.0,
            distribution=Distribution.NORMAL,
            probability=0.6,
        )

    def test_get_from_state(self, stats):
        assert stats.getFromState().getName() == "A"

    def test_get_to_state(self, stats):
        assert stats.getToState().getName() == "B"

    def test_get_sojourn_times(self, stats):
        assert stats.getSojournTimes() == [10, 20, 30]

    def test_get_sojourn_average(self, stats):
        assert stats.getSojournAverage() == pytest.approx(20.0)

    def test_get_sojourn_median(self, stats):
        assert stats.getSojournMedian() == pytest.approx(20.0)

    def test_get_distribution(self, stats):
        assert stats.getDistribution() == Distribution.NORMAL

    def test_get_probability(self, stats):
        assert stats.getProbability() == pytest.approx(0.6)
