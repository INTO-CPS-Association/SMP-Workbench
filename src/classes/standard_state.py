from src.interfaces.state import State

class StandardState(State):
    def __init__(self, name: str) -> None:
        self.name: str = name

    def getName(self) -> str:
        return self.name
