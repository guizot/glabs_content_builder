from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseFeature(ABC):
    """
    Abstract base class for all plug-and-play features in the pipeline.
    Each feature should take inputs, execute its logic, and return outputs
    that can be piped into the next feature.
    """

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """
        Execute the primary logic of the feature.
        Must be implemented by subclasses.
        """
        pass
