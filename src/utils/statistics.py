from src.interfaces.state_transition_info import StateTransitionInfo
from src.interfaces.state_transition_probability import StateTransitionProbability
from src.classes.std_state_transition_probability import StdStateTransitionProbability
from src.classes.standard_state import StandardState

# Iterates through the list of state transitions and finds all from states and their count
def __getFromStatesCount(stateTransitionInfoList: list[StateTransitionInfo]) -> dict[str, int]:
    # Will contain fromStates and their count
    fromStatesCount: dict[str, int] = {}
    
    for stateTransitionInfo in stateTransitionInfoList:
        fromStateName: str = stateTransitionInfo.getFromState()

        # If the entry exists increment the count by 1, else create the entry
        if fromStateName in fromStatesCount.keys():
            fromStatesCount[fromStateName] += 1
        else:
            fromStatesCount[fromStateName] = 1
        
    return fromStatesCount

def __getTransitionsCount(stateTransitionInfoList: list[StateTransitionInfo]) -> list[tuple[str,str,int]]:
    # Will contain fromState, toState and count as a list of tuple[str, str, int]
    transitions: list[tuple[str, str, int]] = []

    # Convert input list to list of triples - easier to work with
    for stateTransitionInfo in stateTransitionInfoList:
        fromState: StandardState = stateTransitionInfo.getFromState()
        fromStateName: str = fromState.getName()
        toState: StandardState = stateTransitionInfo.getToState()
        toStateName: str = toState.getName()
        transitionTriple: tuple[str, str, int] = (fromStateName, toStateName, 1)

        for triple in transitions:
            if fromStateName == triple[0]:
                if toStateName == triple[1]:
                    triple[2] += 1
            else:
                transitions.append(transitionTriple)

        
    
    # If the transition exists increment the count by one else create the entry
    print("Length of transitions:", len(transitions))
    return transitions

def calculatePDF(stateTransitionInfoList: list[StateTransitionInfo]) -> list[StateTransitionProbability]:
    # Return value
    print("Lenght of stateTransitionInfoList:", len(stateTransitionInfoList))
    stateTransitionProbabilityList: list[StdStateTransitionProbability] = []

    # Will contain fromStates and their count
    fromStatesCount: dict[str, int] = __getFromStatesCount(stateTransitionInfoList)

    # Will contain fromState, toState and count as a list of tuple[str, str, int]
    transitions: list[tuple[str, str, int]] = __getTransitionsCount(stateTransitionInfoList)

    # Iterate through transition and divide every trans. count with the correct fromState count
    for transition in transitions:
        # Fetch names
        fromStateName: str = transition[0]
        toStateName: str = transition[1]

        # Fetch counts and calculate probability
        denominator: int = fromStatesCount[fromStateName]
        numerator: int = transition[2]
        probability: float = numerator/denominator

        # Create proper instances of classes and append to result list
        fromState: StandardState = StandardState(fromStateName)
        toState: StandardState = StandardState(toStateName)
        stateTransitionProbabilityList.append(StdStateTransitionProbability(fromState, toState, probability))
    
    return stateTransitionProbabilityList