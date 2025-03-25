from dataclasses import dataclass
from typing import ClassVar, Dict


@dataclass
class TokenizerMapping:
    mapping: ClassVar[Dict[str, str]] = {
        # OpenAI Models
        "openai/o1-2024-12-17": "openai/cl100k_base",
        "openai/o1-2024-12-17-low-reasoning-effort": "openai/cl100k_base",
        "openai/o1-2024-12-17-high-reasoning-effort": "openai/cl100k_base",
        "openai/o1-mini-2024-09-12": "openai/cl100k_base",
        "openai/o1-preview-2024-09-12": "openai/cl100k_base",
        "openai/o3-mini-2025-01-31": "openai/cl100k_base",
        "openai/o3-mini-2025-01-31-low-reasoning-effort": "openai/cl100k_base",
        "openai/o3-mini-2025-01-31-high-reasoning-effort": "openai/cl100k_base",
        "openai/gpt-4-0613": "openai/cl100k_base",
        "openai/gpt-4-32k-0613": "openai/cl100k_base",
        "openai/gpt-4-turbo-2024-04-09": "openai/cl100k_base",
        "openai/gpt-4o-2024-11-20": "openai/o200k_base",
        "openai/gpt-3.5-turbo-0125": "openai/cl100k_base",
        "openai/gpt-4.5-preview-2025-02-27": "openai/o200k_base",
        # Together Models (LLAMA)
        "meta/llama-3-8b": "meta/llama-3-8b",
        "meta/llama-3-70b": "meta/llama-3-8b",
        "meta/llama-3-70b-chat": "meta/llama-3-8b",
        "meta/llama-3.1-70b-instruct-turbo": "meta/llama-3.1-8b",
        "meta/llama-3.1-405b-instruct-turbo": "meta/llama-3.1-8b",
        # Together Models (DeepSeek)
        "deepseek-ai/deepseek-v3": "deepseek-ai/deepseek-v3",
        "deepseek-ai/deepseek-r1": "deepseek-ai/deepseek-r1",
        "deepseek-ai/deepseek-r1-hide-reasoning": "deepseek-ai/deepseek-r1",
        # Mistral Models
        "mistralai/mistral-large-2407": "mistralai/Mistral-Large-Instruct-2407",
        "mistralai/mixtral-8x22b": "mistralai/Mistral-7B-v0.1",
        "mistralai/mixtral-8x22b-instruct-v0.1": "mistralai/Mistral-7B-v0.1",
        # Qwen Model
        "qwen/qwen2-72b-instruct": "qwen/qwen2-72b-instruct",
        # Anthropic Models (Claude)
        "anthropic/claude-3-haiku-20240307": "anthropic/claude",
        "anthropic/claude-3-opus-20240229": "anthropic/claude",
        "anthropic/claude-3-5-sonnet-20240620": "anthropic/claude",
        "anthropic/claude-3-7-sonnet-20250219": "anthropic/claude",
        # Google Gemini Models
        "google/gemini-1.0-pro-001": "google/gemma-2b",
        "google/gemini-1.5-pro-001": "google/gemma-2b",
        "google/gemini-1.5-pro-preview-0409": "google/gemma-2b",
        "google/gemini-2.0-flash-001": "google/gemma-2b",
        # Other
        "01-ai/yi-large": "01-ai/Yi-6B",
    }


@dataclass
class NonHELMMapping:
    mapping: ClassVar[Dict[str, str]] = {
        # OpenAI Models
        "openai/o1-mini-2024-09-12": "o1-mini-2024-09-12",
        "openai/o1-preview-2024-09-12": "o1-preview-2024-09-12",
        "openai/gpt-4o-2024-11-20": "gpt-4o-2024-11-20",
        "openai/o3-mini-2025-01-31 ": "openai/o3-mini-2025-01-31",
        # Anthropic Models (Claude)
        "anthropic/claude-3-5-sonnet-20240620": "claude-3-5-sonnet-20240620",
        "anthropic/claude-3-7-sonnet-20250219": "claude-3-7-sonnet-20250219",
        "anthropic/claude-3-opus-20240229": "claude-3-opus-20240229",
        # Google Gemini Models
        "google/gemini-1.5-pro-001": "gemini-1.5-pro",
        "google/gemini-2.0-flash-001": "gemini-2.0-flash",
        # Together Models (LLAMA)
        "meta/llama-3.1-70b-instruct-turbo": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "meta/llama-3.1-405b-instruct-turbo": "meta-llama/Meta-Llama-3-70B-Instruct-Turbo",
        # Together Models (DeepSeek)
        "deepseek-ai/deepseek-v3": "deepseek-ai/deepseek-v3",
        "deepseek-ai/deepseek-r1": "deepseek-ai/deepseek-r1",
        # Mistral Models
        "mistralai/mixtral-8x22b-instruct-v0.1": "mistralai/Mixtral-8x22B-Instruct-v0.1",
    }


@dataclass
class ModelRegistry:
    tokenizers: ClassVar[TokenizerMapping] = TokenizerMapping()

    @classmethod
    def get_tokenizer(cls, model_name: str) -> str:
        try:
            return cls.tokenizers.mapping[model_name]
        except KeyError as err:
            raise ValueError(
                f"No tokenizer found for model name: {model_name}"
            ) from err

    @classmethod
    def get_model(cls, model_name: str) -> str:
        """
        Since model_name works for all models (HELM and non-HELM),
        we just return the model_name directly or raise an error if not found.
        """
        if model_name in cls.tokenizers.mapping:
            return model_name
        else:
            raise ValueError(f"No model found for model name: {model_name}")
