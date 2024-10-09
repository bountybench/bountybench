from agents.base_agent import BaseAgent
from responses.response import Response
from typing import List
from responses.executor_response_interface import ExecutorResponseInterface
from responses.executor_response import SimpleExecutorResponse
from responses.observation import Observation

class SimpleExecutionAgent(BaseAgent):
    def __init__(self, config, handle_request_func=None):
        self.config = config
        self.max_response_len = 3
        self.memory = []
        self.handle_request_func = handle_request_func or self._handle_request


    def run(self, responses: List[Response]) -> Response:
        if len(responses) > 1:
            return Exception(f'Accepts at most a single response, you passed in {len(responses)} responses')
        if not response:
            return self.execute()
        response = responses[0]
        if issubclass(response.__class__, ExecutorResponseInterface):
            self.formulate_prompt(response)
            return self.execute()
        else:
            raise Exception('Response not of an interpretable type. The response type is {response.__class__} but we expect a class of CommandResponseInterface')

    def execute(self):
        lm_executor_response = self.call_lm()
        observation = self.execute_in_env(lm_executor_response)
        lm_executor_response.set_observation(observation)
        return lm_executor_response

    def formulate_prompt(self, executor_response: SimpleExecutorResponse) -> str:
        """
        """
        if len(self.memory) >= self.max_response_len:
            self.memory = self.memory[1:] + executor_response 
        prompt = INITIAL_PROMPT + self.memory
        self.prompt = prompt
        return prompt
    
    def _handle_request(self, model_input: str) -> str:
        """
        Real implementation that calls the LM API.
        """
        # Code to make the real LM request
        response = None  # Actual API call goes here
        return response

    MAX_ITERATIONS = 5    
    def call_lm(self) -> SimpleExecutorResponse:
        """
        Calls the language model and ensures the response contains a valid command.
        Retries up to MAX_ITERATIONS if the response is missing a command.
        """
        model_input = self.prompt
        iterations = 0
        while iterations < self.MAX_ITERATIONS:
            lm_response = self.handle_request_func(model_input)
            executor_response = SimpleExecutorResponse(lm_response)
     
            # Check if the command exists
            if executor_response.command:
                return executor_response  # Return if a valid command is found
            
            # Log the error and retry if command is missing
            print("Command is missing from the response. Retrying...")
            iterations += 1

        # Raise an exception if it exhausts the retries
        raise Exception("Maximum retries reached without a valid command.")

    def execute_in_env(self, executor_response: SimpleExecutorResponse) -> Observation:
        """
        Simulates executing the command in the environment based on the ExecutorResponse.
        """
        # Use the command from the ExecutorResponse for environment execution.        
        command = executor_response.command
        return Observation(f"Observation: {command} output test")