import pytest
from classes.standard_state import StandardState
from interfaces.state import State


class TestStandardStateCreation:
    def test_is_state_instance(self):
        assert isinstance(StandardState("X"), State)

    def test_get_name_returns_given_name(self):
        assert StandardState("Idle").getName() == "Idle"

    def test_empty_name_is_valid(self):
        assert StandardState("").getName() == ""

    def test_name_with_spaces(self):
        assert StandardState("Idle State").getName() == "Idle State"

    def test_name_with_digits(self):
        assert StandardState("state1").getName() == "state1"

    def test_name_is_stored_exactly(self):
        name = "MixingTime"
        assert StandardState(name).getName() is name


class TestStandardStateEquality:
    def test_same_name_are_equal(self):
        assert StandardState("A") == StandardState("A")

    def test_different_names_are_not_equal(self):
        assert StandardState("A") != StandardState("B")

    def test_not_equal_to_plain_string(self):
        assert StandardState("A") != "A"

    def test_not_equal_to_none(self):
        assert StandardState("A") != None  # noqa: E711

    def test_not_equal_to_integer(self):
        assert StandardState("A") != 1

    def test_equality_is_symmetric(self):
        a1, a2 = StandardState("A"), StandardState("A")
        assert (a1 == a2) == (a2 == a1)

    def test_inequality_is_symmetric(self):
        a, b = StandardState("A"), StandardState("B")
        assert (a != b) == (b != a)

    def test_equal_to_itself(self):
        s = StandardState("X")
        assert s == s

    def test_case_sensitive(self):
        assert StandardState("idle") != StandardState("Idle")


class TestStandardStateHashing:
    def test_same_name_same_hash(self):
        assert hash(StandardState("A")) == hash(StandardState("A"))

    def test_different_names_typically_different_hash(self):
        # True for all reasonable single-character names (Python string hash is injective here)
        assert hash(StandardState("A")) != hash(StandardState("B"))

    def test_usable_as_dict_key(self):
        d = {StandardState("A"): 1, StandardState("B"): 2}
        assert d[StandardState("A")] == 1
        assert d[StandardState("B")] == 2

    def test_same_name_overwrites_in_dict(self):
        d: dict = {}
        d[StandardState("X")] = 10
        d[StandardState("X")] = 20
        assert len(d) == 1
        assert d[StandardState("X")] == 20

    def test_usable_in_set_deduplicates(self):
        s = {StandardState("A"), StandardState("A"), StandardState("B")}
        assert len(s) == 2

    def test_set_membership(self):
        s = {StandardState("A"), StandardState("B")}
        assert StandardState("A") in s
        assert StandardState("C") not in s
