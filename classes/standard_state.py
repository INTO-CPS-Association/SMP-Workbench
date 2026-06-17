from interfaces.state import State

class StandardState(State):
    def __init__(self, name: str) -> None:
        self.name: str = name

    def getName(self) -> str:
        return self.name
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StandardState):
            return False
        
        return self.name == other.name
    
    def __hash__(self) -> int:
        return hash(self.name)