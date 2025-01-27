from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import tiktoken

from agents.prompts import STOP_TOKEN
from messages.action_messages.action_message import ActionMessage
from messages.action_messages.command_message import CommandMessage
from messages.message import Message
from resources.base_resource import BaseResource, BaseResourceConfig
from resources.model_resource.helm_models.helm_models import HelmModels
from resources.model_resource.model_provider import ModelProvider
from resources.model_resource.openai_models.openai_models import OpenAIModels
from resources.model_resource.services.api_key_service import verify_and_auth_api_key
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

HALLUCINATION_STRINGS = [
    "----------Message from assistant----------",
    "----------Message from system----------",
    "----------Message from assistant",
    "----------</assistant",
    "----------Message from agent",
]


@dataclass
class ModelResourceConfig(BaseResourceConfig):
    """Configuration for ModelResource"""

    model: str = field(default="openai/o3-mini-2025-01-14")
    max_output_tokens: int = field(default=4096)
    max_input_tokens: int = field(default=4096)
    max_iterations_stored_in_memory: int = field(default=3)
    use_helm: bool = field(default=False)
    temperature: float = field(default=0.5)
    stop_sequences: List[str] = field(default_factory=lambda: [STOP_TOKEN])

    @classmethod
    def create(cls, **kwargs):
        return cls(**{k: v for k, v in kwargs.items() if v is not None})

    def __post_init__(self):
        if "openai/o3" not in self.model.lower():
            self.use_helm = True
        self.validate()

    def validate(self) -> None:
        """Validate LLMResource configuration"""
        if not self.model:
            raise ValueError("Model must be specified")
        if self.max_input_tokens <= 0:
            raise ValueError("max_input_tokens must be positive")
        if self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be positive")
        verify_and_auth_api_key(self.model, self.use_helm)


class ModelResource(BaseResource):
    """ModelResource"""

    def __init__(self, resource_id: str, config: ModelResourceConfig):
        super().__init__(resource_id, config)
        self.model = self._resource_config.model
        self.max_output_tokens = self._resource_config.max_output_tokens
        self.max_input_tokens = self._resource_config.max_input_tokens
        self.max_iterations_stored_in_memory = (
            self._resource_config.max_iterations_stored_in_memory
        )
        self.helm = self._resource_config.use_helm
        self.temperature = self._resource_config.temperature
        self.stop_sequences = self._resource_config.stop_sequences
        self.model_provider: ModelProvider = self.get_model_provider()

    def get_model_provider(self) -> ModelProvider:
        """
        Get the appropriate model provider based on the model type.
        Returns:
            ModelProvider: An instance of the appropriate model provider class.
        """
        # TODO: Support Different Model Providers (Also handle Azure case)
        if self.helm:
            model_provider = HelmModels()
        else:
            model_provider = OpenAIModels()
        return model_provider

    def remove_hallucinations(self, response: str):
        response = response.replace("----------Message from agent----------", "")
        for hallucination in HALLUCINATION_STRINGS:
            hallucination_index = response.find(hallucination)
            if hallucination_index != -1:
                response = response[:hallucination_index]
        return response.strip()

    def parse_response(
        self,
        response: str,
        metadata: Dict[str, Any],
        prev_message: Optional[ActionMessage] = None,
    ) -> CommandMessage:
        """
        Attempts to parse the raw model string intoCommandMessage.

        """
        try:
            return CommandMessage(
                resource_id=self.resource_id,
                message=response,
                additional_metadata=metadata,
                prev=prev_message,
            )
        except:
            logger.info(f"LM responded with {response}.")
            logger.debug("Could not parse as CommandMessage.")
            raise Exception("Could not parse LM response as CommandMessage.")

    def tokenize(self, message: str) -> List[int]:
        """
        Tokenize the given message using the specified model's tokenizer.
        Args:
            message (str): The message to tokenize.
        Returns:
            List[int]: A list of token IDs representing the tokenized message.
        """
        try:
            return self.model_provider.tokenize(model=self.model, message=message)
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
        try:
            return self.model_provider.decode(model=self.model, tokens=tokens)
        except (NotImplementedError, KeyError):
            encoding = tiktoken.encoding_for_model("gpt-4")
            return encoding.decode(tokens)

    def generate_memory(self, message: Message) -> str:
        memory = []
        if isinstance(message, ActionMessage):
            while message:
                memory.append(message.message)
                message = message.prev
            current_agent_message = message.parent
            current_agent_message = current_agent_message.prev
        else:
            current_agent_message = message

        while current_agent_message:
            memory.append(current_agent_message.message)
            current_agent_message = current_agent_message.prev

        memory = list(reversed(memory))
        initial_prompt = memory[0]
        memory = memory[1:]
        if len(memory) > 3:
            memory = memory[-3:]

        str_memory = initial_prompt + "\n" + "\n".join(memory)
        return str_memory

    def run(self, input_message: Message) -> ActionMessage:
        """
        Send a query to the specified model and get a response.
        Args:
            input_message (ActionMessage): The input message to send to the model.
        Returns:
            ActionMessage: The response generated by the model.
        """
        prev_action_message = None
        if isinstance(input_message, ActionMessage):
            prev_action_message = input_message
        model_input = self.generate_memory(input_message)
        model_response = self.model_provider.make_request(
            model=self.model,
            message=model_input,
            temperature=self.temperature,
            max_tokens=self.max_output_tokens,
            stop_sequences=self.stop_sequences,
        )

        lm_response = self.remove_hallucinations(model_response.content)
        lm_response = lm_response + f"\n{STOP_TOKEN}"
        metadata = (
            {
                "input": model_input,
                "model": self.model,
                "temperature": self.temperature,
                "max_input_tokens": self.max_input_tokens,
                "stop_sequences": self.stop_sequences,
                "input_tokens": model_response.input_tokens,
                "output_tokens": model_response.output_tokens,
                "time_taken_in_ms": model_response.time_taken_in_ms,
            },
        )

        try:
            model_response = self.parse_response(
                lm_response, metadata, prev_action_message
            )
            return model_response
        except Exception as e:
            logger.warning(f"Unable to parse response as CommandResponse.")
            logger.critical(model_response)

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
            "resource_id": self.resource_id,
            "config": {
                "model": self.model,
                "max_output_tokens": self.max_output_tokens,
                "max_input_tokens": self.max_input_tokens,
                "max_iterations_stored_in_memory": self.max_iterations_stored_in_memory,
                "helm": self.helm,
                "temperature": self.temperature,
                "stop_sequences": self.stop_sequences,
            },
        }
