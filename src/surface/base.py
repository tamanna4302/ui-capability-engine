from abc import ABC, abstractmethod
from typing import Any

from src.models.actions import Target


class Surface(ABC):
    @abstractmethod
    def open(self, target: str) -> None:
        pass

    @abstractmethod
    def observe(self) -> dict[str, Any]:
        pass

    @abstractmethod
    def click(self, target: Target) -> None:
        pass

    @abstractmethod
    def type_text(
        self,
        target: Target,
        value: str,
    ) -> None:
        pass

    @abstractmethod
    def read_text(self, target: Target) -> str:
        pass

    @abstractmethod
    def screenshot(self, path: str) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass