import numpy as np
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


class QuarantinedEntry:
    def __init__(self, fromState: str, toState: str, sojournTime: float, outlierScore: float) -> None:
        self.fromState = fromState
        self.toState = toState
        self.sojournTime = sojournTime
        self.outlierScore = outlierScore


# Uses this for more readable algorithm
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


def find_distribution(input: list[int]) -> Distribution:
    if len(input) < 2:
        return Distribution.NONE

    distributions = [stats.norm, stats.expon, stats.gamma, stats.lognorm]

    best_dist = None
    best_p = 0

    data = np.array(input)

    for dist in distributions:
        try:
            params = dist.fit(data)
            _, p = stats.kstest(data, dist.name, args=params)
            if p > best_p:
                best_p = p
                best_dist = dist
        except:
            continue
    if best_dist == None:
        return Distribution.NONE

    if best_dist.name == "norm":
        return Distribution.NORMAL
    elif best_dist.name == "expon":
        return Distribution.EXPONENTIAL
    elif best_dist.name == "gamma":
        return Distribution.GAMMA
    elif best_dist.name == "lognorm":
        return Distribution.LOGNORMAL

    return Distribution.NONE


def _group_by_pair(
    transitions: list[StateTransitionInfo],
) -> tuple[dict[tuple[str, str], list[StateTransitionInfo]], dict[str, State]]:
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
    return groups, state_objects


def _partition_outliers(
    groups: dict[tuple[str, str], list[StateTransitionInfo]],
) -> tuple[dict[tuple[str, str], list[StateTransitionInfo]], list[QuarantinedEntry]]:
    clean_by_pair: dict[tuple[str, str], list[StateTransitionInfo]] = {}
    quarantined: list[QuarantinedEntry] = []
    for (fn, tn), entries in groups.items():
        sojourn_times = [e.getSojournTime() for e in entries]
        is_outlier, scores = detect_outliers_with_scores(sojourn_times)
        clean = [e for e, flag in zip(entries, is_outlier) if not flag]
        quarantined.extend(
            QuarantinedEntry(fn, tn, float(e.getSojournTime()), score)
            for e, flag, score in zip(entries, is_outlier, scores) if flag
        )
        # If every entry was flagged the pair would vanish from statistics;
        # fall back to keeping all entries so there is always something to show.
        clean_by_pair[(fn, tn)] = clean if clean else list(entries)
    return clean_by_pair, quarantined


def _compute_from_counts(
    clean_by_pair: dict[tuple[str, str], list[StateTransitionInfo]],
) -> dict[str, int]:
    from_counts: dict[str, int] = {}
    for (fn, _), entries in clean_by_pair.items():
        from_counts[fn] = from_counts.get(fn, 0) + len(entries)
    return from_counts


def _build_statistics(
    clean_by_pair: dict[tuple[str, str], list[StateTransitionInfo]],
    from_counts: dict[str, int],
    state_objects: dict[str, State],
) -> list[StateTransitionStatistics]:
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


def calculateStatistics(
    stateTransitionInfoList: list[StateTransitionInfo],
) -> tuple[list[StateTransitionStatistics], list[QuarantinedEntry]]:
    groups, state_objects = _group_by_pair(stateTransitionInfoList)
    clean_by_pair, quarantined = _partition_outliers(groups)
    from_counts = _compute_from_counts(clean_by_pair)
    return _build_statistics(clean_by_pair, from_counts, state_objects), quarantined
