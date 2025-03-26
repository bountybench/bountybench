from dataclasses import dataclass, field
from typing import Any, List

import tiktoken
import re

from messages.action_messages.action_message import ActionMessage
from messages.message import Message
from prompts.prompts import STOP_TOKEN
from resources.base_resource import BaseResourceConfig
from resources.model_resource.helm_models.helm_models import HelmModels
from resources.model_resource.model_provider import ModelProvider
from resources.model_resource.model_utils import truncate_input_to_max_tokens
from resources.model_resource.openai_models.openai_models import OpenAIModels
from resources.model_resource.services.api_key_service import verify_and_auth_api_key
from resources.runnable_base_resource import RunnableBaseResource
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

    model: str
    max_output_tokens: int = field(default=4096)
    max_input_tokens: int = field(default=8192)
    use_helm: bool = field(default=False)
    temperature: float = field(default=0.5)
    stop_sequences: List[str] = field(default_factory=lambda: [])
    use_mock_model: bool = field(default=False)

    @classmethod
    def create(cls, **kwargs):
        # If using a mock model but no model name provided, use a default name
        if kwargs.get("use_mock_model", False) and (
            "model" not in kwargs or kwargs.get("model") is None
        ):
            kwargs["model"] = "mock-model"
        return cls(**{k: v for k, v in kwargs.items() if v is not None})

    def copy_with_changes(self, **kwargs):
        """
        Returns a *new* ModelResourceConfig instance with only the specified fields modified.
        """
        config_dict = self.__dict__.copy()
        config_dict.update({k: v for k, v in kwargs.items() if v is not None})
        return self.__class__(**config_dict)

    def validate(self) -> None:
        """Validate LLMResource configuration"""
        if not self.model or len(self.model) < 1:
            raise ValueError("Model must be specified and nonempty")
        if self.max_input_tokens <= 0:
            raise ValueError("max_input_tokens must be positive")
        if self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be positive")
        if not self.use_mock_model:
            verify_and_auth_api_key(self.model, self.use_helm)


class ModelResource(RunnableBaseResource):
    """ModelResource"""

    def __init__(self, resource_id: str, config: ModelResourceConfig):
        super().__init__(resource_id, config)
        self.model = self._resource_config.model
        self.max_output_tokens = self._resource_config.max_output_tokens
        self.max_input_tokens = self._resource_config.max_input_tokens
        self.helm = self._resource_config.use_helm
        self.temperature = self._resource_config.temperature
        self.stop_sequences = self._resource_config.stop_sequences
        self.use_mock_model = self._resource_config.use_mock_model
        if not self.use_mock_model:
            self.model_provider: ModelProvider = self.get_model_provider()

    def get_model_provider(self) -> ModelProvider:
        """
        Get the appropriate model provider based on the model type.
        Returns:
            ModelProvider: An instance of the appropriate model provider class.
        """
        if self.use_mock_model:
            return None
        if self.helm:
            model_provider = HelmModels()
        else:
            # Select provider based on model name prefix
            model_prefix = self.model.split("/")[0].lower() if "/" in self.model else ""

            if model_prefix == "anthropic":
                from resources.model_resource.anthropic_models.anthropic_models import (
                    AnthropicModels,
                )

                model_provider = AnthropicModels()
            elif model_prefix == "google":
                from resources.model_resource.google_models.google_models import (
                    GoogleModels,
                )

                model_provider = GoogleModels()
            elif (
                # TODO: Remove this once we have a better way to handle model prefixes for Together models
                model_prefix == "meta-llama"
                or model_prefix == "mistralai"
                or model_prefix == "deepseek-ai"
            ):
                from resources.model_resource.together_models.together_models import (
                    TogetherModels,
                )

                model_provider = TogetherModels()
            elif model_prefix == "openai":
                model_provider = OpenAIModels()
            else:
                raise Exception(f"Unknown model type: {self.model}")
        return model_provider

    def remove_hallucinations(self, response: str):
        response = response.replace("----------Message from agent----------", "")
        for hallucination in HALLUCINATION_STRINGS:
            hallucination_index = response.find(hallucination)
            if hallucination_index != -1:
                response = response[:hallucination_index]
        return response.strip()

    def remove_stop_token(self, response: str):
        response = response.replace(STOP_TOKEN, "")
        return response.strip()

    def remove_deepseek_r1_thinking(self, response: str) -> str:
        if "<think>" not in response:
            return response

        if "</think>\n\n" in response:
            # The think block is usually followed by two newlines
            return re.sub("<think>.*</think>\n\n", "", response, flags=re.DOTALL)
        elif "</think>" in response:
            return re.sub("<think>.*</think>", "", response, flags=re.DOTALL)
        else:
            # Unclosed think block
            return ""

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

        assert (
            input_message.memory is not None
        ), "Message to model.run() should contain memory."
        model_input = input_message.memory
        if self.use_mock_model:
            return ActionMessage(
                resource_id=self.resource_id,
                message=input_message.message,
                additional_metadata=None,
                prev=prev_action_message,
            )

        model_input = truncate_input_to_max_tokens(
            max_input_tokens=self.max_input_tokens,
            model_input=model_input,
            model=self.model,
            use_helm=self.helm,
        )

        model_response = self.model_provider.make_request(
            model=self.model,
            message=model_input,
            temperature=self.temperature,
            max_tokens=self.max_output_tokens,
            stop_sequences=self.stop_sequences,
        )

        lm_response = self.remove_hallucinations(model_response.content)
        lm_response = self.remove_stop_token(lm_response)
        lm_response = self.remove_deepseek_r1_thinking(lm_response)
        lm_response = lm_response + f"\n{STOP_TOKEN}"
        metadata = (
            {
                "input": model_input,
                "model": self.model,
                "temperature": self.temperature,
                "max_input_tokens": self.max_input_tokens,
                "max_output_tokens": self.max_output_tokens,
                "stop_sequences": self.stop_sequences,
                "input_tokens": model_response.input_tokens,
                "output_tokens": model_response.output_tokens,
                "time_taken_in_ms": model_response.time_taken_in_ms,
            },
        )

        return ActionMessage(
            resource_id=self.resource_id,
            message=lm_response,
            additional_metadata=metadata,
            prev=prev_action_message,
        )

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
        base_dict = {"resource_id": self.resource_id}

        if not self.use_mock_model:
            base_dict["config"] = {
                "model": self.model,
                "max_output_tokens": self.max_output_tokens,
                "max_input_tokens": self.max_input_tokens,
                "helm": self.helm,
                "temperature": self.temperature,
                "stop_sequences": self.stop_sequences,
                "use_mock_model": self.use_mock_model,
            }
        else:
            base_dict["config"] = {"use_mock_model": self.use_mock_model}

        return base_dict
