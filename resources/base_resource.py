from abc import ABC, abstractmethod

class BaseResource(ABC):
    @abstractmethod
    def stop(*args, **kwargs):
        pass
