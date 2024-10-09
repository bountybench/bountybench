from base_agent import BaseAgent
from responses.response import Response
from typing import List
from responses.executor_response_interface import ExecutorResponseInterface
from responses.executor_response import SimpleExecutorResponse
from responses.observation import Observation

class SimpleExecutionAgent(BaseAgent):
    def __init__(self, config):
        self.config = config
        self.max_response_len = 3
        self.memory = []

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

    MAX_ITERATIONS = 5    
    def call_lm(self) -> SimpleExecutorResponse:
        """
        Calls the language model and ensures the response contains a valid command.
        Currently retries up to MAX_ITERATIONS if the response is missing a command. 
        TODO: add dynamic stop condition
        """
        model_input = self.prompt
        iterations = 0
        while iterations < MAX_ITERATIONS:
            lm_response = self._handle_request(model_input)
            try:
                # Attempt to parse the response into SimpleExecutorResponse
                executor_response = SimpleExecutorResponse(lm_response)
                return executor_response  # Return if valid command is found
            except Exception as e:
                # Log the error and retry if command is missing
                print(f"Invalid response: {e}. Retrying...")
            iterations += 1

        # If we exhaust the retries, raise an exception or handle the failure
        raise Exception("Maximum retries reached without a valid command.")
    
    def execute_in_env(self, executor_response: SimpleExecutorResponse) -> Observation:
        """
        Simulates executing the command in the environment based on the ExecutorResponse.
        """
        # Use the command from the ExecutorResponse for environment execution.        
        command = executor_response.command
        return Observation(f"Observation: {command} output test")