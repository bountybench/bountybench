import http
from agents.base_agent import BaseAgent
from agents.simple_agent.prompt import INITIAL_PROMPT, STOP_TOKEN
from agents.dataclasses.agent_spec import AgentConfig
from agents.chat_chain import ChatChain
import logging
import os
import time
from typing import List

from models.query import query
from dataclasses import field

from responses.response import Response
from responses.observation import Observation
from responses.command_response import CommandResponse
from responses.command_response_interface import CommandResponseInterface
from responses.answer_response import AnswerResponse

from resources.kali_env_resource import KaliEnvResource
from models.query import get_model_provider, query


from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from requests.exceptions import ConnectionError, HTTPError, Timeout


from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TIMEOUT_PER_COMMAND = 120
MAX_HELM_RETRIES = 3
RETRY_DELAY = 30
TEMPERATURE = 0.5

class SimpleExecutorAgent(BaseAgent):
    memory: List[str] = []

    def __init__(self, config: AgentConfig, **kwargs):
        super().__init__()
        self.config = config
        self.initial_prompt = INITIAL_PROMPT.format(
            # TODO make defaults
            task_description=kwargs.get("task_description", "default_task_description"),
            answer_format=kwargs.get("answer_format", "default_answer_format"),
            stop_token=STOP_TOKEN,
            target_host=kwargs.get("target_host", "default_target_host"),
        )
        self.prompt = self.initial_prompt

        if KaliEnvResource in self.resource_dict.resource_type_to_resources:
            self.kali_env = self.resource_dict.get_items_of_resource_type(KaliEnvResource)[0]
        else:
            # kill the agent if no kali env is found - this should have happened earlier in the workflow
            raise RuntimeError("KaliEnvResource not found in resource_dict. Agent cannot start.")
    
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
            lm_executor_response.set_observation(observation) # only command response has set observation func
        logger.info(f"LM Response:\n{lm_executor_response.response}")
        return lm_executor_response

    def formulate_prompt(self, executor_response: CommandResponse) -> str:
        """
        Formulates the prompt by appending the new response to memory.
        """
        if len(self.memory) >= self.config.max_response_len:
            self.memory = self.memory[1:] + [executor_response.response] 
        else:
            self.memory.append(executor_response.response)

        truncated_input = self._truncate_input_to_max_tokens(
            str(self.memory)
        )
        prompt = self.initial_prompt + truncated_input
        self.prompt = prompt
        return prompt


    def _get_num_tokens(self, model_input: str) -> int:
        return get_model_provider(self.config.model, self.config.use_helm).get_num_tokens(self.config.model, model_input)

    
    @retry(
        stop=stop_after_attempt(30),
        wait=wait_exponential(multiplier=1, max=30),
        retry=retry_if_exception_type(
            (HTTPError, ConnectionError, Timeout, http.client.RemoteDisconnected)
        ),
    )
    def _tokenize_input(self, model_input: str) -> List[int]:
        return get_model_provider(self.config.model, self.config.use_helm).tokenize(self.config.model, model_input)
    
    
    @retry(
        stop=stop_after_attempt(30),
        wait=wait_exponential(multiplier=1, max=30),
        retry=retry_if_exception_type(
            (HTTPError, ConnectionError, Timeout, http.client.RemoteDisconnected)
        ),
    )
    def _decode_tokenized_inputs(self, tokens: List[int]) -> str:
        return get_model_provider(self.config.model, self.config.use_helm).decode(self.config.model, tokens)
    

    def _truncate_input_to_max_tokens(self, model_input: str) -> str:
        num_input_tokens = self._get_num_tokens(model_input)
        truncation_alert = "\n...TRUNCATED...\n"
        num_tokens_in_truncation_alert = self._get_num_tokens(truncation_alert)

        if num_input_tokens >= self.config.max_input_tokens - num_tokens_in_truncation_alert:
            self.logger.warning(
                f"Number of input tokens ({num_input_tokens}) exceeds max tokens ({self.config.max_input_tokens}). Truncating input."
            )
            tokens = self._tokenize_input(model_input=model_input)
            tokens_to_keep = self.config.max_input_tokens - num_tokens_in_truncation_alert
            half_tokens_to_keep = tokens_to_keep // 2
            beginning_tokens = tokens[:half_tokens_to_keep]
            end_tokens = tokens[-half_tokens_to_keep:]
            truncated_tokens = (
                beginning_tokens + self._tokenize_input(truncation_alert) + end_tokens
            )
            truncated_input = self._decode_tokenized_inputs(truncated_tokens)
            return truncated_input

        return model_input

    def _handle_request(self, model_input: str) -> str:
        model =  str(self.config.model)
        temperature = 1 if "o1" in model else TEMPERATURE
        max_tokens = self.config.max_output_tokens
        stop_sequences = [] if "o1" in model else [STOP_TOKEN]

        model_response = query(
            model=model,
            message=model_input,
            temperature=temperature,
            max_tokens=max_tokens,
            stop_sequences=stop_sequences,
            helm=self.config.use_helm
        )

        model_response.remove_hallucinations()

        return model_response.content  + f"\n{STOP_TOKEN}"

    
    def _parse_response(self, response: str) -> Response:
        """
        Attempts to parse the response into either AnswerResponse or CommandResponse.
        """
        try:
            return AnswerResponse(response)
        except:
            # print(f"Failed to parse as AnswerResponse")
            try:
                return CommandResponse(response)
            except:
                # print(f"Failed to parse as CommandResponse")
                raise Exception("Response could not be parsed as either an Answer or Command response.")

    def call_lm(self) -> Response:
        """
        Calls the language model and ensures the response is in valid format.
        Retries up to MAX_ITERATIONS if the response is invalid.
        """
        model_input = self.prompt
        logger.info(f"LM Input:\n{model_input}")
        iterations = 0
        while iterations < self.config.max_iterations:
            lm_response = self._handle_request(model_input)
            try:
                return self._parse_response(lm_response)
            except Exception as e:
                logger.error(f"Error: {str(e)}. Retrying...")
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
            # Use kali_env to execute the command inside the container
            stdout, stderr = self.kali_env.run_command(
                command, timeout=TIMEOUT_PER_COMMAND, workdir="/app/"
            )

            # Check for command execution without errors, even if no stdout was produced
            if stdout.strip():
                return Observation(f"Command succeeded: {stdout}")
            elif stderr.strip():
                # No stdout but there's stderr (may be an error or just output in stderr)
                return Observation(f"Command failed with error: {stderr}")
            else:
                # Neither stdout nor stderr indicates an empty but successful execution
                return Observation("Command succeeded with no output")
        except Exception as e:
            # If an actual exception occurred during execution, log it as a failure
            return Observation(f"Command execution failed: {str(e)}")