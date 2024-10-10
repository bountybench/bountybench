from base_agent import BaseAgent
from abc import ABC, abstractmethod
from responses.response import Response
from typing import List
from responses.executor_response import SimpleExecutorResponse
from responses.observation import Observation

class ExecuterAgent(BaseAgent, ABC):
    def __init__(self, config):
         super().__init__(config)

    @abstractmethod
    def execute(self) -> Response:
         pass

    @abstractmethod
    def formulate_prompt(self, executor_response: SimpleExecutorResponse) -> str:
        pass


    @abstractmethod
    def execute_in_env(self, executor_response: SimpleExecutorResponse) -> Observation:
         pass