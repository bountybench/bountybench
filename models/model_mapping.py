from dataclasses import dataclass
from typing import ClassVar, Dict


@dataclass
class TokenizerMapping:
    mapping: ClassVar[Dict[str, str]] = {
        # OpenAI Models
        "openai/o1-mini-2024-09-12": "openai/cl100k_base",
        "openai/o1-preview-2024-09-12": "openai/cl100k_base",
        "openai/gpt-4-0613": "openai/cl100k_base",
        "openai/gpt-4-32k-0613": "openai/cl100k_base",
        "openai/gpt-4-turbo-2024-04-09": "openai/cl100k_base",
        "openai/gpt-4o-2024-05-13": "openai/o200k_base",
        "openai/gpt-3.5-turbo-0125": "openai/cl100k_base",

        # Together Models (LLAMA)
        "together/llama-3-8b": "meta/llama-3-8b",
        "together/llama-3-70b": "meta/llama-3-8b",
        "together/llama-3-70b-chat": "meta/llama-3-8b",
        "together/llama-3.1-70b-instruct-turbo": "meta/llama-3.1-8b",
        "together/llama-3.1-405b-instruct-turbo": "meta/llama-3.1-8b",

        # Mistral Models
        "mistralai/mistral-large-2407": "mistralai/Mistral-Large-Instruct-2407",
        "together/mixtral-8x22b": "mistralai/Mistral-7B-v0.1",
        "together/mixtral-8x22b-instruct-v0.1": "mistralai/Mistral-7B-v0.1",

        # Qwen Model
        "together/qwen2-72b-instruct": "qwen/qwen2-72b-instruct",

        # Anthropic Models (Claude)
        "anthropic/claude-3-haiku-20240307": "anthropic/claude",
        "anthropic/claude-3-opus-20240229": "anthropic/claude",
        "anthropic/claude-3-5-sonnet-20240620": "anthropic/claude",

        # Google Gemini Models
        "google/gemini-1.0-pro-001": "google/gemma-2b",
        "google/gemini-1.5-pro-001": "google/gemma-2b",
        "google/gemini-1.5-pro-preview-0409": "google/gemma-2b",

        # Other
        "01-ai/yi-large": "01-ai/Yi-6B"
    }


@dataclass
class HELMMapping:
    mapping: ClassVar[Dict[str, str]] = {
        # OpenAI Models
        "openai/o1-mini-2024-09-12": "openai/o1-mini-2024-09-12",
        "openai/o1-preview-2024-09-12": "openai/o1-preview-2024-09-12",
        "openai/gpt-4-0613": "openai/gpt-4-0613",
        "openai/gpt-4-32k-0613": "openai/gpt-4-32k-0613",
        "openai/gpt-4-turbo-2024-04-09": "openai/gpt-4-turbo-2024-04-09",
        "openai/gpt-4o-2024-05-13": "openai/gpt-4o-2024-05-13",
        "openai/gpt-3.5-turbo-0125": "openai/gpt-3.5-turbo-0125",

        # Together Models (LLAMA)
        "together/llama-3-8b": "meta/llama-3-8b",
        "together/llama-3-70b": "meta/llama-3-70b",
        "together/llama-3-70b-chat": "meta/llama-3-70b-chat",
        "together/llama-3.1-70b-instruct-turbo": "meta/llama-3.1-70b-instruct-turbo",
        "together/llama-3.1-405b-instruct-turbo": "meta/llama-3.1-405b-instruct-turbo",

        # Mistral Models
        "mistralai/mistral-large-2407": "mistralai/mistral-large-2407",
        "together/mixtral-8x22b": "mistralai/mixtral-8x22b",
        "together/mixtral-8x22b-instruct-v0.1": "mistralai/mixtral-8x22b-instruct-v0.1",

        # Qwen Model
        "together/qwen2-72b-instruct": "qwen/qwen2-72b-instruct",

        # Anthropic Models (Claude)
        "anthropic/claude-3-haiku-20240307": "anthropic/claude-3-haiku-20240307",
        "anthropic/claude-3-opus-20240229": "anthropic/claude-3-opus-20240229",
        "anthropic/claude-3-5-sonnet-20240620": "anthropic/claude-3-5-sonnet-20240620",

        # Google Gemini Models
        "google/gemini-1.0-pro-001": "google/gemini-1.0-pro-001",
        "google/gemini-1.5-pro-001": "google/gemini-1.5-pro-001",
        "google/gemini-1.5-pro-preview-0409": "google/gemini-1.5-pro-preview-0409",

        # Other
        "01-ai/yi-large": "01-ai/yi-large"
    }


@dataclass
class NonHELMMapping:
    mapping: ClassVar[Dict[str, str]] = {
        # OpenAI Models
        "openai/o1-mini-2024-09-12": "o1-mini-2024-09-12",
        "openai/o1-preview-2024-09-12": "o1-preview-2024-09-12",
        "openai/gpt-4o-2024-05-13": "gpt-4o-2024-05-13",

        # Anthropic Models (Claude)
        "anthropic/claude-3-5-sonnet-20240620": "claude-3-5-sonnet-20240620",
        "anthropic/claude-3-opus-20240229": "claude-3-opus-20240229",

        # Google Gemini Models
        "google/gemini-1.5-pro": "gemini-1.5-pro",

        # Together Models (LLAMA)
        "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "meta-llama/Meta-Llama-3-70B-Instruct-Turbo": "meta-llama/Meta-Llama-3-70B-Instruct-Turbo",

        # Mistral Models
        "mistralai/Mixtral-8x22B-Instruct-v0.1": "mistralai/Mixtral-8x22B-Instruct-v0.1"
    }


@dataclass
class ModelRegistry:
    tokenizers: ClassVar[TokenizerMapping] = TokenizerMapping()
    helm_models: ClassVar[HELMMapping] = HELMMapping()
    non_helm_models: ClassVar[NonHELMMapping] = NonHELMMapping()

    @classmethod
    def get_tokenizer(cls, model_name: str) -> str:
        try:
            return cls.tokenizers.mapping[model_name]
        except KeyError as err:
            raise ValueError(f"No tokenizer found for model name: {model_name}") from err

    @classmethod
    def get_model(cls, model_name: str) -> str:
        """
        Get the model either from HELM or non-HELM mappings.
        """
        try:
            # Try to find the model in HELM mappings first
            return cls.helm_models.mapping[model_name]
        except KeyError:
            # If not found in HELM, check non-HELM mappings
            try:
                return cls.non_helm_models.mapping[model_name]
            except KeyError as err:
                raise ValueError(f"No model found for model name: {model_name}") from err