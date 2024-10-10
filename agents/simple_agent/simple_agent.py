from executor_agent import ExecutorAgent
from responses.response import Response
from typing import List
from responses.executor_response_interface import ExecutorResponseInterface
from responses.executor_response import SimpleExecutorResponse
from responses.observation import Observation
from simple_agent.prompt import INITIAL_PROMPT


MAX_ITERATIONS = 5
class SimpleExecutionAgent(ExecutorAgent):

    def __init__(self, config):
        self.config = config
        self.max_response_len = 3
        self.memory = []
        #self.handle_request_func = handle_request_func or self._handle_request
        self.prompt = INITIAL_PROMPT



    def run(self, responses: List[Response]) -> Response:
        if len(responses) > 1:
            return Exception(f'Accepts at most a single response, you passed in {len(responses)} responses')
        
        if not responses:
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
        pass
    
    def parse_response(lm_response: str) -> SimpleExecutorResponse:
        executor_response = SimpleExecutorResponse(lm_response)
        if executor_response.command:
            return executor_response  # Return if a valid command is found
        print("Command is missing from the response.")
        return None

    
    def call_lm(self) -> Response:
        """
        Calls the language model and ensures the response is in valid format.
        Retries up to MAX_ITERATIONS if the response is invalid.
        """
        model_input = self.prompt
        iterations = 0
        while iterations < MAX_ITERATIONS:
            lm_response = self.handle_request_func(model_input)
            executor_response = self.parse_response(lm_response)
     
            if executor_response:
                return executor_response # Check if valid response was generated (None if not)
            
            # Log the error and retry if formatted response not generated
            print("Response is not formatted correctly. Retrying...")
            iterations += 1

        # Raise an exception if it exhausts the retries
        raise Exception("Maximum retries reached without a valid response.")

    def execute_in_env(self, executor_response: SimpleExecutorResponse) -> Observation:
        """
        Simulates executing the command in the environment based on the ExecutorResponse.
        """
        # Use the command from the ExecutorResponse for environment execution.        
        command = executor_response.command
        return Observation(f"Observation: {command} output test")