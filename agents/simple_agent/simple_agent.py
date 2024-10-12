from agents.base_agent import BaseAgent
from agents.simple_agent.prompt import INITIAL_PROMPT
from agents.dataclasses.agent_spec import AgentConfig

from responses.response import Response
from responses.observation import Observation
from responses.command_response import CommandResponse
from responses.command_response_interface import CommandResponseInterface
from responses.answer_response import AnswerResponse

from agents.docker_helper.docker_helper import DockerHelper

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

        volumes = {
            self.work_dir: {"bind": "/app/", "mode": "ro"},
        }
        self.command_executor = DockerHelper(volumes=volumes)
        if self.config.use_helm:
            self.crfm_auth = Authentication(
                api_key=self._get_env_var("HELM_API_KEY"))
            self.crfm_service = RemoteService(
                "https://crfm-models.stanford.edu")

    
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
    
    def _handle_request(self, model_input: str) -> str:
        """
        TODO: Handle making requests to different model providers (HELM or non-HELM) and processing the response.
        """
        pass
    
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

        try:
            # Use DockerHelper to execute the command inside the container
            stdout, stderr = self.command_executor.run_command(
                command, timeout=TIMEOUT_PER_COMMAND, workdir="/app/"
            )

            if stdout:
                # Command succeeded, return stdout as observation
                return Observation(f"Command succeeded: {stdout}")
            else:
                # Command failed, return stderr as observation
                return Observation(f"Command failed with error: {stderr}" if stderr else "Command failed with no output")

        except Exception as e:
            return Observation(f"Command execution failed: {str(e)}")