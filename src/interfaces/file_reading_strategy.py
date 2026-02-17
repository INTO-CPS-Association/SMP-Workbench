from abc import ABC, abstractmethod
import json

class FileReadingStrategy(ABC):
    @abstractmethod
    def read(self, path: str) -> str:
        raise NotImplementedError