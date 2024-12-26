"""
Is there a smart way to ensure any Resource always sets a resource_id / it exists statically in python (vs dynamic failure on access?)
"""
from abc import ABC, abstractmethod

class BaseResource(ABC):
    @abstractmethod
    def stop(*args, **kwargs):
        pass


    def __init__(self, resource_id, resource_config):
        self._resource_id = resource_id
        self._resource_config = resource_config

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    # if resource_id is relied on, then mandatory for all Resources
    @property
    def resource_id(self):
        return self._resource_id

    def __str__(self):
        return self._resource_id
