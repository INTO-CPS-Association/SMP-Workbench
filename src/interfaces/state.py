from abc import ABC, abstractmethod

class State(ABC):
    @abstractmethod
    def __init__(self, name: str) -> None:
        raise NotImplementedError
    
    @abstractmethod
    def getName() -> str:
        raise NotImplementedError
    
    @abstractmethod
    def __eq__(self, other) -> bool:
        raise NotImplementedError

    @abstractmethod
    def __hash__(self):
        raise NotImplementedError