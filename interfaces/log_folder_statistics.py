from abc import ABC, abstractmethod

class LogFolderStatistics(ABC):
    @abstractmethod
    def __init__(self) -> None:
        raise NotImplementedError