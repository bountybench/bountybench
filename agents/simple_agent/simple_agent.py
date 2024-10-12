from agent import BaseAgent
from chat_chain import ChatChain
import logging
import os
import time

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from requests.exceptions import ConnectionError, HTTPError, Timeout

from models.model_mapping import ModelRegistry 
from models.query import get_model_provider


HALLUCINATION_STRINGS = [
    "----------Message from assistant----------",
    "----------Message from system----------",
    "----------Message from assistant",
    "----------</assistant",
    "----------Message from agent",
]

MAX_HELM_RETRIES = 3
RETRY_DELAY = 30
NUM_RESPONSE_TO_KEEP = 3
#TEMPERATURE = 0.5

class SimpleExecutionAgent(BaseAgent):
    def __init__(self, config):
        self.config = config
        self.max_response_len = 3
        self.memory = []
        self.chat_chain = ChatChain()
        self.truncated_chat_chain = ChatChain()

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
        lm_response = self.call_lm()
        observation = self.execute_in_env(lm_response)
        return format_response(lm_response, observation)

    def formulate_prompt(self, executor_response: ExecutorResponse) -> str:
        """
        """
        if len(self.memory) >= self.max_response_len:
            self.memory = self.memory[1:] + executor_response 
        prompt = INITIAL_PROMPT + self.memory
        self.prompt = prompt
        return prompt
    
    def call_lm(self):
        model_input = self.prompt
        return self._handle_request(model_input)
    

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(__name__)
        logger.setLevel(level=logging.INFO)

        log_file = os.path.join(self.log_dir, "agent.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        formatter = logging.Formatter("%(message)s\n")

        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

        return logger

    def remove_hallucinations(self, response: str):
        response = response.replace("----------Message from agent----------", "")
        for hallucination in HALLUCINATION_STRINGS:
            hallucination_index = response.find(hallucination)
            if hallucination_index != -1:
                response = response[:hallucination_index]
        return response.strip()

    
    def _handle_request_error(self, attempt: int, e: Exception) -> None:
        self.logger.error(f"Error while making request to HELM API: {str(e)}")
        if attempt < MAX_HELM_RETRIES - 1:
            self.logger.info(f"Retrying HELM request in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)
        else:
            self.logger.error("All retries failed. Stopping the task run.")
            raise RuntimeError(
                f"Connection error or timeout when querying HELM API: {str(e)}. No more retries left."
            ) from e
        
    
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
    
    
    def _truncate_chat_chain(self) -> None:
        self.truncated_chat_chain.clear()
        idx_to_ignore = []
        num_responses = len(self.chat_chain.model_response_index)
        num_observations = len(self.chat_chain.assistant_observation_index)
        if num_responses > NUM_RESPONSE_TO_KEEP:
            idx_to_ignore.extend(
                self.chat_chain.model_response_index[
                    : num_responses - self.responses_to_keep
                ]
            )
        if num_observations > NUM_RESPONSE_TO_KEEP:
            idx_to_ignore.extend(
                self.chat_chain.assistant_observation_index[
                    : num_observations - self.observations_to_keep
                ]
            )
        for idx, msg in enumerate(self.chat_chain.chain):
            if idx not in idx_to_ignore:
                self.truncated_chat_chain.chain.append(msg)
