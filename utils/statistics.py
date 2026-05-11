import numpy as np
from dataclasses import dataclass, field
from scipy import stats

from src.interfaces.state_transition_info import StateTransitionInfo
from src.interfaces.state_transition_probability import StateTransitionProbability
from classes.std_state_transition_probability import StdStateTransitionProbability
from src.interfaces.state import State
from src.interfaces.state_transition_sojourn import StateTransitionSojourn
from classes.std_state_transition_sojourn import StdStateTransitionSojourn
from src.interfaces.state_transition_statistics import StateTransitionStatistics
from classes.std_state_transition_statistics import StdStateTransitionStatistics
from utils.enums import Distribution
from utils.outlier_detection import detect_outliers_with_scores


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

class QuarantinedEntry:
    def __init__(self, fromState: str, toState: str, sojournTime: float, outlierScore: float) -> None:
        self.fromState = fromState
        self.toState = toState
        self.sojournTime = sojournTime
        self.outlierScore = outlierScore


@dataclass
class GroupedTransitions:
    """Transitions grouped by (from_state, to_state) pair, with State objects preserved.

    state_objects retains the original State instances so they can be passed to
    StdStateTransitionStatistics without re-constructing them from string names.
    """
    groups: dict = field(default_factory=dict)          # (fn, tn) → list[StateTransitionInfo]
    state_objects: dict = field(default_factory=dict)   # state name → State instance


@dataclass
class PartitionResult:
    """Outcome of running outlier detection across all (from, to) transition pairs."""
    # Transitions that passed outlier detection, keyed by (from_state, to_state)
    clean_by_pair: dict = field(default_factory=dict)
    # Entries that were flagged as outliers and removed from the statistics
    quarantined: list = field(default_factory=list)


@dataclass
class StatisticsResult:
    """The complete output of calculateStatistics."""
    # One StdStateTransitionStatistics object per clean (from, to) pair
    statistics: list = field(default_factory=list)
    # Transition records that were excluded as sojourn-time outliers
    quarantined: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Legacy helpers (used by calculatePDF / calculateSojourn)
# ---------------------------------------------------------------------------

class PDFTransition:
    fromState: State
    toState: dict[State, float]
    totalTransitions: float

    def __init__(self, fromState: State):
        self.fromState: State = fromState
        self.toState = {}
        self.totalTransitions = 0

    def getFromState(self) -> State:
        return self.fromState

    def getToStateDict(self) -> dict[State, float]:
        return self.toState

    def getTotalTransitions(self) -> float:
        return self.totalTransitions

    def incrementTotalTransitions(self) -> None:
        self.totalTransitions += 1

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PDFTransition):
            return False
        return self.fromState == other.fromState

    def __hash__(self) -> int:
        return hash(self.fromState)


class SojournTransition:
    fromState: State
    toState: dict[State, list[int]]

    def __init__(self, fromState: State):
        self.fromState: State = fromState
        self.toState = {}
        self.totalTransitions = 0

    def getFromState(self) -> State:
        return self.fromState

    def getToStateDict(self) -> dict[State, list[int]]:
        return self.toState

    def getTotalTransitions(self) -> float:
        return self.totalTransitions

    def incrementTotalTransitions(self) -> None:
        self.totalTransitions += 1

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SojournTransition):
            return False
        return self.fromState == other.fromState

    def __hash__(self) -> int:
        return hash(self.fromState)


def calculatePDF(stateTransitionInfoList: list[StateTransitionInfo]) -> list[StateTransitionProbability]:
    transitionSet: set[PDFTransition] = set()

    for stateTransitionInfo in stateTransitionInfoList:
        fromState: State = stateTransitionInfo.getFromState()
        transition: PDFTransition = PDFTransition(fromState)
        transitionSet.add(transition)

    for transition in transitionSet:
        transFromState: State = transition.getFromState()

        for stateTransitionInfo in stateTransitionInfoList:
            fromState: State = stateTransitionInfo.getFromState()

            if fromState == transFromState:
                toState: State = stateTransitionInfo.getToState()
                transition.incrementTotalTransitions()

                toStateDict: dict[State, float] = transition.getToStateDict()
                if toState in toStateDict.keys():
                    toStateDict[toState] += 1
                else:
                    toStateDict[toState] = 1

    for transition in transitionSet:
        toStateDict: dict[State, float] = transition.getToStateDict()
        totalTransitions: float = transition.getTotalTransitions()

        for key in toStateDict.keys():
            toStateDict[key] = toStateDict[key] / totalTransitions

    result: list[StateTransitionProbability] = []
    for transition in transitionSet:
        fromState: State = transition.getFromState()
        toStateDict: dict[State, float] = transition.getToStateDict()

        for key in toStateDict.keys():
            probability: float = toStateDict[key]
            result.append(StdStateTransitionProbability(fromState, key, probability))

    return result


def calculateSojourn(stateTransitionInfoList: list[StateTransitionInfo]) -> list[StateTransitionSojourn]:
    transitionSet: set[SojournTransition] = set()

    for stateTransitionInfo in stateTransitionInfoList:
        fromState: State = stateTransitionInfo.getFromState()
        transition: SojournTransition = SojournTransition(fromState)
        transitionSet.add(transition)

    for transition in transitionSet:
        transFromState: State = transition.getFromState()

        for stateTransitionInfo in stateTransitionInfoList:
            fromState: State = stateTransitionInfo.getFromState()

            if fromState == transFromState:
                toState: State = stateTransitionInfo.getToState()
                toStateDict: dict[State, list[int]] = transition.getToStateDict()
                if toState in toStateDict.keys():
                    toStateDict[toState].append(stateTransitionInfo.getSojournTime())
                else:
                    toStateDict[toState] = [stateTransitionInfo.getSojournTime()]

    result: list[StateTransitionSojourn] = []
    for transition in transitionSet:
        fromState: State = transition.getFromState()
        toStateDict: dict[State, list[int]] = transition.getToStateDict()

        for key in toStateDict.keys():
            sojournTimes: list[int] = toStateDict[key]
            avg: float = np.average(sojournTimes)
            median: float = float(np.median(sojournTimes))
            distribution = find_distribution(sojournTimes)
            result.append(StdStateTransitionSojourn(fromState, key, sojournTimes, avg, median, distribution))

    return result


# ---------------------------------------------------------------------------
# Distribution fitting
# ---------------------------------------------------------------------------

_DIST_MAP = {
    "norm":     Distribution.NORMAL,
    "expon":    Distribution.EXPONENTIAL,
    "gamma":    Distribution.GAMMA,
    "lognorm":  Distribution.LOGNORMAL,
}


def find_distribution(sojourn_times: list[int]) -> Distribution:
    """Fits four candidate distributions to sojourn_times and returns the best by KS p-value.

    The Kolmogorov-Smirnov test measures how well the fitted parameters match the
    observed data; the distribution with the highest p-value (least evidence against
    the null hypothesis) is returned.
    """
    if len(sojourn_times) < 2:
        return Distribution.NONE

    data = np.array(sojourn_times)
    best_dist = None
    best_p = 0.0

    for dist in [stats.norm, stats.expon, stats.gamma, stats.lognorm]:
        try:
            params = dist.fit(data)
            _, p = stats.kstest(data, dist.name, args=params)
            if p > best_p:
                best_p = p
                best_dist = dist
        except Exception:
            continue

    if best_dist is None:
        return Distribution.NONE
    return _DIST_MAP.get(best_dist.name, Distribution.NONE)


# ---------------------------------------------------------------------------
# calculateStatistics helpers
# ---------------------------------------------------------------------------

def _group_by_pair(transitions: list[StateTransitionInfo]) -> GroupedTransitions:
    """Groups transitions by (from_state, to_state) and collects State instances by name.

    State instances are preserved here so downstream helpers can reference the
    original objects without re-constructing them from bare name strings.
    """
    groups: dict[tuple[str, str], list[StateTransitionInfo]] = {}
    state_objects: dict[str, State] = {}

    for info in transitions:
        fn = info.getFromState().getName()
        tn = info.getToState().getName()
        state_objects[fn] = info.getFromState()
        state_objects[tn] = info.getToState()
        key = (fn, tn)
        if key not in groups:
            groups[key] = []
        groups[key].append(info)

    return GroupedTransitions(groups=groups, state_objects=state_objects)


def _partition_outliers(
    groups: dict[tuple[str, str], list[StateTransitionInfo]],
) -> PartitionResult:
    """Splits each pair's transitions into clean and quarantined using the LOF ensemble.

    If every entry for a pair is flagged as an outlier, all entries are kept as clean
    to prevent that transition pair from disappearing from the statistics entirely.
    """
    clean_by_pair: dict[tuple[str, str], list[StateTransitionInfo]] = {}
    quarantined: list[QuarantinedEntry] = []

    for (fn, tn), entries in groups.items():
        sojourn_times = [e.getSojournTime() for e in entries]
        result = detect_outliers_with_scores(sojourn_times)

        clean = [e for e, flag in zip(entries, result.is_outlier) if not flag]
        quarantined.extend(
            QuarantinedEntry(fn, tn, float(e.getSojournTime()), score)
            for e, flag, score in zip(entries, result.is_outlier, result.scores)
            if flag
        )
        clean_by_pair[(fn, tn)] = clean if clean else list(entries)

    return PartitionResult(clean_by_pair=clean_by_pair, quarantined=quarantined)


def _compute_from_counts(
    clean_by_pair: dict[tuple[str, str], list[StateTransitionInfo]],
) -> dict[str, int]:
    """Counts total clean transitions leaving each from-state.

    Used as the denominator when computing transition probabilities so that all
    outgoing edges from a state sum to 1.
    """
    from_counts: dict[str, int] = {}
    for (fn, _), entries in clean_by_pair.items():
        from_counts[fn] = from_counts.get(fn, 0) + len(entries)
    return from_counts


def _build_statistics(
    clean_by_pair: dict[tuple[str, str], list[StateTransitionInfo]],
    from_counts: dict[str, int],
    state_objects: dict[str, State],
) -> list[StateTransitionStatistics]:
    """Builds one StdStateTransitionStatistics object per clean (from, to) pair."""
    result: list[StateTransitionStatistics] = []
    for (fn, tn), entries in clean_by_pair.items():
        sojourn_times = [e.getSojournTime() for e in entries]
        result.append(StdStateTransitionStatistics(
            state_objects[fn],
            state_objects[tn],
            sojourn_times,
            float(np.average(sojourn_times)),
            float(np.median(sojourn_times)),
            find_distribution(sojourn_times),
            len(entries) / from_counts[fn],
        ))
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculateStatistics(
    stateTransitionInfoList: list[StateTransitionInfo],
) -> StatisticsResult:
    """Computes transition statistics with outlier-based sojourn-time quarantine.

    Returns a StatisticsResult containing the computed statistics for every clean
    (from, to) pair and the list of entries that were excluded as outliers.
    """
    grouped = _group_by_pair(stateTransitionInfoList)
    partitioned = _partition_outliers(grouped.groups)
    from_counts = _compute_from_counts(partitioned.clean_by_pair)
    statistics = _build_statistics(partitioned.clean_by_pair, from_counts, grouped.state_objects)
    return StatisticsResult(statistics=statistics, quarantined=partitioned.quarantined)
