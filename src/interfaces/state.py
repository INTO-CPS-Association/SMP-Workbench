from abc import ABC, abstractmethod

class State(ABC):
    @abstractmethod
    def __init__(self, name: str) -> None:
        raise NotImplementedError
    
    @abstractmethod
    def getName() -> str:
        raise NotImplementedError