from abc import ABC, abstractmethod

class BaseResource(ABC):
    @abstractmethod
    def stop(*args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()