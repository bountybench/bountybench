from agents.base_agent import BaseAgent
from agents.simple_agent.prompt import INITIAL_PROMPT, STOP_TOKEN
from agents.dataclasses.agent_spec import AgentConfig

from responses.response import Response
from responses.observation import Observation
from responses.command_response import CommandResponse
from responses.command_response_interface import CommandResponseInterface
from responses.answer_response import AnswerResponse
import models.query import query
from models.model_response import ModelResponse


import os
import subprocess
from typing import List

TIMEOUT_PER_COMMAND = 120
MAX_HELM_RETRIES = 3
RETRY_DELAY = 30
TEMPERATURE = 0.5

class SimpleExecutionAgent(BaseAgent):
    config: AgentConfig
    prompt: str = INITIAL_PROMPT

    memory: List[str] = []
    handle_request_func: callable

    def __init__(self, config: AgentConfig):
        self.config = config
    
    def run(self, responses: List[Response]) -> Response:        
        if len(responses) > 1:
            return Exception(f'Accepts at most a single response, you passed in {len(responses)} responses')
        if len(responses) == 0:
            return self.execute()
        response = responses[0]
        if issubclass(response.__class__, CommandResponseInterface):
            self.formulate_prompt(response)
            return self.execute()
        else:
            raise Exception('Response not of an interpretable type. The response type is {response.__class__} but we expect a class of CommandResponseInterface')

    def execute(self) -> Response:
        lm_executor_response = self.call_lm()
        # if the action is command, execute the command in the environment, otherwise just submit
        if issubclass(lm_executor_response.__class__, CommandResponseInterface):
            observation = self.execute_in_env(lm_executor_response)
            lm_executor_response.set_observation(observation)
        return lm_executor_response

    def formulate_prompt(self, executor_response: CommandResponse) -> str:
        """
        Formulates the prompt by appending the new response to memory.
        """
        if len(self.memory) >= self.config.max_response_len:
            self.memory = self.memory[1:] + [executor_response] 
        else:
            self.memory.append(executor_response)
        
        # Convert memory list to string before concatenating with INITIAL_PROMPT
        prompt = INITIAL_PROMPT + ''.join(str(item) for item in self.memory)
        self.prompt = prompt
        return prompt
    
    def _handle_request(self, model_input: str) -> ModelResponse:

        model_name =  str(self.config.model_name)
        temperature = 1 if "o1" in model_name else TEMPERATURE
        max_tokens = self.config.max_output_tokens
        stop_sequences = [] if "o1" in model_name else [STOP_TOKEN]

        model_response = query(
            model=model_name,
            message=model_input,
            temperature=temperature,
            max_tokens=max_tokens,
            stop_sequences=stop_sequences,
            helm=self.config.use_helm
        )

        model_response.content = self.remove_hallucinations(model_response.content) + f"\n{STOP_TOKEN}"

        return model_response 

    
    def _parse_response(self, response: str) -> Response:
        """
        Attempts to parse the response into either AnswerResponse or CommandResponse.
        """
        try:
            return AnswerResponse(response)
        except:
            print(f"Failed to parse as AnswerResponse")
            try:
                return CommandResponse(response)
            except:
                print(f"Failed to parse as CommandResponse")
                raise Exception("Response could not be parsed as either an Answer or Command response.")

    def call_lm(self) -> Response:
        """
        Calls the language model and ensures the response is in valid format.
        Retries up to MAX_ITERATIONS if the response is invalid.
        """
        model_input = self.prompt
        iterations = 0
        while iterations < self.config.max_iterations:
            lm_response = self._handle_request(model_input)
            try:

                return self._parse_response(lm_response)
            except Exception as e:
                print(f"Error: {str(e)}. Retrying...")
                iterations += 1

        # Raise an exception if it exhausts the retries
        raise Exception("Call_lm error: Maximum retries reached without a valid response.")

    def execute_in_env(self, executor_response: CommandResponse) -> Observation:
        """
        Executes the command in the environment based on the ExecutorResponse.
        Captures the output and creates an observation based on command execution.
        """
        command = executor_response.command

        if command:
            try:
                # Run the command using subprocess, capturing output and errors
                process = subprocess.run(
                    ["bash", "-c", command],  
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                    cwd=os.getcwd(),
                    timeout=TIMEOUT_PER_COMMAND,
                )
                stdout = process.stdout.decode('utf-8').strip() # Clean the standard output
                stderr = process.stderr.decode('utf-8').strip() # Clean the error output (if any)

                if stdout:
                    # Command succeeded, return stdout as observation
                    return Observation(f"Command succeeded: {stdout}")
                else:
                    # Command failed, return stderr as observation\
                    return Observation(f"Command failed with error: {stderr}" if stderr else "Command failed with no output")

            except subprocess.TimeoutExpired as e:
                return Observation(f"Command timed out after {e.timeout} seconds")
            except subprocess.CalledProcessError as e:
                return Observation(f"Command failed with error: {e.stderr.decode('utf-8') if e.stderr else 'Unknown error'}")

        else:
            raise Exception("No command found to execute in the environment.")