
from typing import List, Optional

from agents.base_agent import BaseAgent
from agents.dataclasses.agent_spec import AgentConfig
from agents.executor_agent.prompt import INITIAL_PROMPT, STOP_TOKEN
from agents.utils import truncate_input_to_max_tokens
from models.model_response import ModelResponse
from models.query import query
from resources.init_files_resource import InitFilesResource
from resources.kali_env_resource import KaliEnvResource
from resources.setup_resource import SetupResource
from responses.answer_response import AnswerResponse
from responses.command_response import CommandResponse
from responses.command_response_interface import CommandResponseInterface
from responses.observation import Observation
from responses.response import Response
from utils.logger import get_main_logger
from utils.workflow_logger import WorkflowLogger

logger = get_main_logger(__name__)

TIMEOUT_PER_COMMAND = 120
MAX_RETRIES = 3
RETRY_DELAY = 30
TEMPERATURE = 0.5


class ExecutorAgent(BaseAgent):
    memory: List[str] = []    
    REQUIRED_RESOURCES = [InitFilesResource, SetupResource, KaliEnvResource]
    OPTIONAL_RESOURCES = []
    ACCESSIBLE_RESOURCES = [KaliEnvResource]

    def __init__(self, config: AgentConfig, initial_prompt: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config

        self.initial_prompt = initial_prompt
        self.prompt = self.initial_prompt

        if kwargs.get("target_host", ""):
            self.kali_env.health_check(kwargs.get("target_host", ""))

    def run(self, responses: List[Response]) -> Response:
        if len(responses) > 1:
            raise Exception(f'Accepts at most a single response, you passed in {len(responses)} responses')
        
        # When no external information is given, e.g. first run or no additional agents
        if len(responses) == 0:        
            self.formulate_prompt()
        else:
            response = responses[0]
            self.formulate_prompt(response)

        executor_response = self.execute()
        self._update_memory(executor_response)

        return executor_response
            
    def _update_memory(self, response) -> str:
        if len(self.memory) >= self.config.max_response_len:
            self.memory = self.memory[1:] + [response.response]
        else:
            self.memory.append(response.response)

    def formulate_prompt(self, response: Optional[Response] = None) -> str:
        """
        Formulates the prompt.
        """
        if response:
            self._update_memory(response)

        truncated_input = truncate_input_to_max_tokens(
            max_input_tokens=self.config.max_input_tokens,
            model_input="\n".join(self.memory),
            model=self.config.model,
            use_helm=self.config.use_helm,
        )
        prompt = self.initial_prompt + truncated_input
        self.prompt = prompt
        return prompt

    def execute(self) -> Response:
        lm_executor_response = self.call_lm()
        # if the action is command, execute the command in the environment, otherwise just submit
        if issubclass(lm_executor_response.__class__, CommandResponseInterface):
            observation = self.execute_in_env(lm_executor_response)
            # only command response has set observation func
            lm_executor_response.set_observation(observation)
        logger.info(f"LM Response:\n{lm_executor_response.response}")
        return lm_executor_response

    def _parse_response(self, response: str) -> Response:
        """
        Attempts to parse the response into either AnswerResponse or CommandResponse.
        """
        try:
            return AnswerResponse(response)
        except:
            logger.debug(
                "LM response not an AnswerResponse type. Attempting to parse as CommandResponse.")
            try:
                return CommandResponse(response)
            except:
                logger.debug("LM response not an CommandResponse type.")
                raise Exception(
                    "Response could not be parsed as either an Answer or Command response.")

    def call_lm(self) -> Response:
        """
        Calls the language model and ensures the response is in valid format.
        Retries up to MAX_ITERATIONS if the response is invalid.
        """
        model_input = self.prompt
        iterations = 0
        while iterations < MAX_RETRIES:
            model_response: ModelResponse = query(
                model=self.config.model,
                message=model_input,
                temperature=TEMPERATURE,
                max_tokens=self.config.max_output_tokens,
                stop_sequences=[STOP_TOKEN],
                helm=self.config.use_helm
            )

            model_response = model_response.remove_hallucinations()

            lm_response = model_response + f"\n{STOP_TOKEN}"
            try:
                return self._parse_response(lm_response)
            except Exception as e:
                logger.warning(
                    f"Retrying {iterations}/{MAX_RETRIES} after error: {e}")
                iterations += 1

        # Raise an exception if it exhausts the retries
        raise Exception(
            "Call_lm error: Maximum retries reached without a valid response.")

    def execute_in_env(self, executor_response: CommandResponse) -> Observation:
        """
        Executes the command in the environment based on the ExecutorResponse.
        Captures the output and creates an observation based on command execution.
        """
        command = executor_response.command
        try:
            # Use kali_env to execute the command inside the container
            stdout, stderr = self.kali_env.run_command(
                command, timeout=TIMEOUT_PER_COMMAND, workdir="/app/", logging=True
            )

            # Check for command execution without errors, even if no stdout was produced
            observation = stdout.strip() + stderr.strip()
            logger.info(f"Executed the command in agent environment: {command}.\n\nstdout: {stdout.strip()}\n\nstderr: {stderr.strip()}")

            return Observation(observation)
        except Exception as e:
            # If an actual exception occurred during execution, log it as a failure
            logger.exception(
                f"Failed to execute command in agent environment: {command}.\n\n Exception: {str(e)}")
            return Observation(str(e))
