from abc import ABC, abstractmethod

class StateTransitionInfo(ABC):

    @abstractmethod
    def __init__(self, from_state: str):
        self.from_state: str = from_state
        self.to_states: dict[str, int] = {}

    @abstractmethod
    def getFromState(self) -> str:
        raise NotImplementedError
    
    @abstractmethod
    def getToStates(self) -> dict[str, int]:
        raise NotImplementedError
    
    @abstractmethod
    def setToStates(self, to_states: dict[str, int]) -> None:
        raise NotImplementedError