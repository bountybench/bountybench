from dataclasses import dataclass, field
from typing import List, Optional, Union

import tiktoken

from agents.prompts import STOP_TOKEN
from messages.action_messages.action_message import ActionMessage
from messages.
from messages.agent_messages.executor_agent_message import ExecutorAgentMessage
from messages.action_messages.answer_message import AnswerMessage
from messages.action_messages.command_message import CommandMessage
from resources.model_resource.model_provider import ModelProvider
from resources.base_resource import BaseResource, BaseResourceConfig
from utils import workflow_logger
from resources.model_resource.model_utils import get_model_provider, truncate_input_to_max_tokens
from utils.logger import get_main_logger



HALLUCINATION_STRINGS = [
    "----------Message from assistant----------",
    "----------Message from system----------",
    "----------Message from assistant",
    "----------</assistant",
    "----------Message from agent",
]




logger = get_main_logger(__name__)


@dataclass
class ModelResourceConfig(BaseResourceConfig):
    """Configuration for ModelResource"""
    model: str = field(default='openai/o3-mini-2024-12-17')
    max_output_tokens: int = field(default=4096)
    max_input_tokens: int = field(default=4096)
    max_iterations_stored_in_memory: int = field(default=3)
    use_helm: bool = field(default=False)
    temperature: float = field(default=0.5)
    stop_sequences: List[str] = field(default_factory=lambda: [STOP_TOKEN])
    initial_prompt: Optional[str] = None

    @classmethod
    def create(cls, **kwargs):
        return cls(**{k: v for k, v in kwargs.items() if v is not None})

    def __post_init__(self):
        if 'openai/o3' not in self.model.lower():
            self.use_helm = True

    def validate(self) -> None:
        """Validate LLMResource configuration"""
        if not self.model:
            raise ValueError("Model must be specified")
        if self.max_input_tokens <= 0:
            raise ValueError("max_input_tokens must be positive")
        if self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be positive")
    

class ModelResource(BaseResource):
    """ModelResource"""

    def __init__(self, resource_id: str, config: ModelResourceConfig):
        super().__init__(resource_id, config)
        self.model = self._resource_config.model
        self.max_output_tokens = self._resource_config.max_output_tokens
        self.max_input_tokens = self._resource_config.max_input_tokens
        self.max_iterations_stored_in_memory = self._resource_config.max_iterations_stored_in_memory
        self.helm = self._resource_config.use_helm
        self.temperature = self._resource_config.temperature
        self.stop_sequences = self._resource_config.stop_sequences
        self.prompt = self._resource_config.initial_prompt
        self.memory = []


    def remove_hallucinations(self, response: str):
        response = response.replace("----------Message from agent----------", "")
        for hallucination in HALLUCINATION_STRINGS:
            hallucination_index = response.find(hallucination)
            if hallucination_index != -1:
                response = response[:hallucination_index]
        return response.strip()
    
    def parse_response(self, response: str) -> Union[AnswerMessage, CommandMessage]:
        """
        Attempts to parse the raw model string into either AnswerMessage or CommandMessage.
        """
        try:
            return AnswerMessage(response)
        except:
            logger.debug("Not an AnswerMessage, trying CommandMessage.")
            try:
                return CommandMessage(response)
            except:
                logger.debug("Could not parse as CommandMessage.")
                raise Exception("Could not parse LM response as AnswerMessage or CommandMessage.")

    def update_memory(self, message_str: str) -> None:
        """Update model's memory with new message"""
        if len(self.memory) >= self.max_iterations_stored_in_memory:
            self.memory = self.memory[1:] + [message_str]
        else:
            self.memory.append(message_str)

    def formulate_prompt(self, message: Optional[ExecutorAgentMessage] = None) -> str:
        """
        Formulates the prompt, including the truncated memory.
        """
        if message:
            if self.initial_prompt:
                self.update_memory(message)
            else:
                self.initial_prompt = message._response 
    

        truncated_input = truncate_input_to_max_tokens(
            max_input_tokens=self.max_input_tokens,
            model_input="\n".join(self.memory),
            model=self.model,
            use_helm=self.helm,
        )
        prompt = self.initial_prompt + truncated_input
        self.prompt = prompt
        return prompt
    
    
    def clear_memory(self) -> None:
        """Clear model's memory"""
        self.memory = []

    def tokenize(self, message: str) -> List[int]:
        """
        Tokenize the given message using the specified model's tokenizer.
        Args:
            message (str): The message to tokenize.
        Returns:
            List[int]: A list of token IDs representing the tokenized message.
        """
        model_provider: ModelProvider
        model_provider = get_model_provider(self.helm)
        try:
            return model_provider.tokenize(
                model=self.model, message=message
            )
        except (NotImplementedError, KeyError):
            encoding = tiktoken.encoding_for_model("gpt-4")
            return encoding.encode(message)


    def decode(self, tokens: List[int]) -> str:
        """
        Decode a list of token IDs back into a string using the specified model's tokenizer.
        Args:
            tokens (List[int]): A list of token IDs to decode.
        Returns:
            str: The decoded string representation of the tokens.
        """
        model_provider: ModelProvider
        model_provider = self.get_model_provider(self.helm)
        try:
            return model_provider.decode(
                model=self.model, tokens=tokens
            )
        except (NotImplementedError, KeyError):
            encoding = tiktoken.encoding_for_model("gpt-4")
            return encoding.decode(tokens)

    def run(
        self,
        message: Optional[ActionMessage] = None
    ) -> ActionMessage:
        """
        Send a query to the specified model and get a response.
        Args:
            message (str): The input message to send to the model.
        Returns:
            ActionMessage: The response generated by the model.
        """       
        self.formulate_prompt(message)
        model_input = self.prompt
        model_provider: ModelProvider
        model_provider = get_model_provider(self.helm)
        model_response = model_provider.request(
            model=self.model,
            message=model_input,
            temperature=self.temperature,
            max_tokens=self.max_output_tokens,
            stop_sequences=self.stop_sequences,
        )

        model_response._message = self.model.remove_hallucinations(model_response._message)
        model_response = model_response._message + f"\n{STOP_TOKEN}"

        try:
            model_response = self.model.parse_response(model_response)
            return model_response
        except Exception as e:
            logger.warning(f"Unable to parse response as CommandResponse or ActionResponse")

    def stop(self) -> None:
        """
        Stop/cleanup method for LLM resource.
        
        LLM resources don't maintain persistent connections or state,
        so this is a no-op implementation to satisfy the BaseResource interface.
        """
        logger.debug(f"Stopping LLM resource {self.resource_id} (no cleanup required)")
    

    def to_dict(self) -> dict:
        """
        Serialize the ModelResource to a dictionary.
        Includes both instance state and configuration.
        """
        return {
            'resource_id': self.resource_id,
            'config': {
                'model': self.model,
                'max_output_tokens': self.max_output_tokens,
                'max_input_tokens': self.max_input_tokens,
                'max_iterations_stored_in_memory': self.max_iterations_stored_in_memory,
                'helm': self.helm,
                'temperature': self.temperature,
                'stop_sequences': self.stop_sequences
            }
        }