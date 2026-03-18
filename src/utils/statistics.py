import numpy as np
from scipy import stats

from src.interfaces.state_transition_info import StateTransitionInfo
from src.interfaces.state_transition_probability import StateTransitionProbability
from src.classes.std_state_transition_probability import StdStateTransitionProbability
from src.interfaces.state import State
from src.interfaces.state_transition_sojourn import StateTransitionSojourn
from src.classes.std_state_transition_sojourn import StdStateTransitionSojourn
from src.utils.enums import Distribution

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

    # Create a set of Transitions, initializing with the from state
    for stateTransitionInfo in stateTransitionInfoList:
        fromState: State = stateTransitionInfo.getFromState()

        transition: PDFTransition = PDFTransition(fromState)

        transitionSet.add(transition)

    print("Size of trans set:", len(transitionSet))
    # For each of the possible transitions, count the amount of occurances in the input list
    for transition in transitionSet:
        transFromState: State = transition.getFromState()

        for stateTransitionInfo in stateTransitionInfoList:
            fromState: State = stateTransitionInfo.getFromState()

            # If the from state is equal, then check the toState
            if fromState == transFromState:
                toState: State = stateTransitionInfo.getToState()

                # Increment the totalTransitionsCount
                transition.incrementTotalTransitions()

                # Get the toState dict and check if the key is already there. If it is, increment by 1
                # if it is not there, create it with a value of 1
                toStateDict: dict[State, float] = transition.getToStateDict()
                if toState in toStateDict.keys():
                    toStateDict[toState] += 1
                else:
                    toStateDict[toState] = 1
    
    # Calculate the probability for each toState in every Transition
    for transition in transitionSet:
        toStateDict: dict[State, float] = transition.getToStateDict()
        totalTransitions: float = transition.getTotalTransitions()

        for key in toStateDict.keys():
            toStateDict[key] = toStateDict[key] / totalTransitions
    
    # Create the final result list
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

    # Create a set of Transitions, initializing with the from state
    for stateTransitionInfo in stateTransitionInfoList:
        fromState: State = stateTransitionInfo.getFromState()

        transition: SojournTransition = SojournTransition(fromState)

        transitionSet.add(transition)
    
    print("Size of trans set:", len(transitionSet))
    # For each of the transitions add the toState to the dictionary, such that we can record the sojourn time.
    # If there is no entry, create it and if there is an entry, append the sojourn time
    for transition in transitionSet:
        transFromState: State = transition.getFromState()

        for stateTransitionInfo in stateTransitionInfoList:
            fromState: State = stateTransitionInfo.getFromState()

            # If the from state is equal, then check the toState
            if fromState == transFromState:
                toState: State = stateTransitionInfo.getToState()

                # Get the toState dict and check if the key is already there. If it is, append the sojourn time
                # if it is not there, create a list with the sojourn time in it
                toStateDict: dict[State, list[int]] = transition.getToStateDict()
                if toState in toStateDict.keys():
                    toStateDict[toState].append(stateTransitionInfo.getSojournTime())
                else:
                    toStateDict[toState] = [stateTransitionInfo.getSojournTime()]

    # Create the final result list
    result: list[StateTransitionSojourn] = []
    for transition in transitionSet:
        fromState: State = transition.getFromState()
        toStateDict: dict[State, list[int]] = transition.getToStateDict()

        for key in toStateDict.keys():
            sojournTimes: list[int] = toStateDict[key]
            avg: float = np.average(sojournTimes)
            median: float = np.median(sojournTimes)
            distribution = find_distribution(sojournTimes)
            result.append(StdStateTransitionSojourn(fromState, key, sojournTimes, avg, median, distribution))
    
    return result


def find_distribution(input: list[int]) -> Distribution:
    # If there are less than 2 data points, return immediately
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
    
    # Default case
    return Distribution.NONE