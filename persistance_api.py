from abc import ABC, abstractmethod
from pathlib import Path
import pickle
from typing import Any, Optional

class Repository(ABC):
    """Interfaz abstracta para persistencia"""

    @abstractmethod
    def save(self, key: str, obj: Any) -> None:
        pass

    @abstractmethod
    def load(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        pass