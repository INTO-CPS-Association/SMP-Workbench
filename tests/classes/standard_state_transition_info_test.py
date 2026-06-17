import pytest
from classes.standard_state import StandardState
from classes.standard_state_transition_info import StandardStateTransitionInfo
from interfaces.state_transition_info import StateTransitionInfo


@pytest.fixture
def a():
    return StandardState("A")


@pytest.fixture
def b():
    return StandardState("B")


@pytest.fixture
def c():
    return StandardState("C")


@pytest.fixture
def t_ab(a, b):
    return StandardStateTransitionInfo(a, b, 100)


class TestStandardStateTransitionInfoCreation:
    def test_is_state_transition_info_instance(self, t_ab):
        assert isinstance(t_ab, StateTransitionInfo)

    def test_get_from_state_returns_from(self, t_ab, a):
        assert t_ab.getFromState() == a

    def test_get_to_state_returns_to(self, t_ab, b):
        assert t_ab.getToState() == b

    def test_get_sojourn_time_returns_value(self, t_ab):
        assert t_ab.getSojournTime() == 100

    def test_sojourn_time_zero_is_valid(self, a, b):
        assert StandardStateTransitionInfo(a, b, 0).getSojournTime() == 0

    def test_large_sojourn_time(self, a, b):
        assert StandardStateTransitionInfo(a, b, 10**9).getSojournTime() == 10**9

    def test_from_state_name_accessible(self, t_ab):
        assert t_ab.getFromState().getName() == "A"

    def test_to_state_name_accessible(self, t_ab):
        assert t_ab.getToState().getName() == "B"


class TestStandardStateTransitionInfoEquality:
    def test_same_pair_same_sojourn_are_equal(self, a, b):
        assert StandardStateTransitionInfo(a, b, 100) == StandardStateTransitionInfo(a, b, 100)

    def test_same_pair_different_sojourn_are_equal(self, a, b):
        # Equality is (from, to) pair only â€” sojourn time is intentionally ignored
        assert StandardStateTransitionInfo(a, b, 1) == StandardStateTransitionInfo(a, b, 999)

    def test_different_from_state_not_equal(self, a, b, c):
        assert StandardStateTransitionInfo(a, b, 100) != StandardStateTransitionInfo(c, b, 100)

    def test_different_to_state_not_equal(self, a, b, c):
        assert StandardStateTransitionInfo(a, b, 100) != StandardStateTransitionInfo(a, c, 100)

    def test_swapped_pair_not_equal(self, a, b):
        assert StandardStateTransitionInfo(a, b, 100) != StandardStateTransitionInfo(b, a, 100)

    def test_not_equal_to_string(self, t_ab):
        assert t_ab != "A->B"

    def test_not_equal_to_none(self, t_ab):
        assert t_ab != None  # noqa: E711

    def test_not_equal_to_integer(self, t_ab):
        assert t_ab != 42

    def test_equal_to_itself(self, t_ab):
        assert t_ab == t_ab

    def test_equality_is_symmetric(self, a, b):
        t1 = StandardStateTransitionInfo(a, b, 50)
        t2 = StandardStateTransitionInfo(a, b, 99)
        assert (t1 == t2) == (t2 == t1)


class TestStandardStateTransitionInfoStatePreservation:
    def test_from_state_object_identity(self, a, b):
        t = StandardStateTransitionInfo(a, b, 10)
        assert t.getFromState() is a

    def test_to_state_object_identity(self, a, b):
        t = StandardStateTransitionInfo(a, b, 10)
        assert t.getToState() is b

    def test_sojourn_time_not_modified(self, a, b):
        for v in [0, 1, 50, 10000]:
            assert StandardStateTransitionInfo(a, b, v).getSojournTime() == v
