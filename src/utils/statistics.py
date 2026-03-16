from src.interfaces.state_transition_info import StateTransitionInfo
from src.interfaces.state_transition_probability import StateTransitionProbability
from src.classes.std_state_transition_probability import StdStateTransitionProbability
from src.interfaces.state import State
from src.interfaces.state_transition_sojourn import StateTransitionSojourn

# Uses this for more readable algorithm
class Transition:
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
        if not isinstance(other, Transition):
            return False
        
        return self.fromState == other.fromState

    def __hash__(self) -> int:
        return hash(self.fromState)
    

def calculatePDF(stateTransitionInfoList: list[StateTransitionInfo]) -> list[StateTransitionProbability]:
    transitionSet: set[Transition] = set()

    # Create a set of Transitions, initializing with the from state
    for stateTransitionInfo in stateTransitionInfoList:
        fromState: State = stateTransitionInfo.getFromState()

        transition: Transition = Transition(fromState)

        transitionSet.add(transition)

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
            result.append(StdStateTransitionProbability(fromState, toState, probability))
    
    return result

def calculateSojourn(stateTransitionInfoList: list[StateTransitionInfo]) -> list[StateTransitionSojourn]:
    raise NotImplementedError