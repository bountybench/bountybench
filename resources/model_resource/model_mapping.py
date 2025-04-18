from dataclasses import dataclass
from typing import ClassVar, Dict


@dataclass(frozen=True)
class HelmModelInfo:
    tokenizer: str
    is_legacy: bool = False


@dataclass(frozen=True)
class NonHelmModelInfo:
    tokenizer: str
    provider: str
    is_legacy: bool = False


@dataclass
class HelmTokenizerMapping:
    mapping: ClassVar[Dict[str, HelmModelInfo]] = {
        # ------------------------
        # OpenAI Models
        # ------------------------
        "openai/gpt-4.1-2025-04-14": HelmModelInfo(tokenizer="openai/o200k_base"),
        "openai/gpt-4.5-preview-2025-02-27": HelmModelInfo(
            tokenizer="openai/o200k_base"
        ),
        "openai/o1-2024-12-17": HelmModelInfo(tokenizer="openai/cl100k_base"),
        "openai/o1-2024-12-17-low-reasoning-effort": HelmModelInfo(
            tokenizer="openai/cl100k_base"
        ),
        "openai/o1-2024-12-17-high-reasoning-effort": HelmModelInfo(
            tokenizer="openai/cl100k_base"
        ),
        "openai/o1-mini-2024-09-12": HelmModelInfo(tokenizer="openai/cl100k_base"),
        "openai/o1-preview-2024-09-12": HelmModelInfo(tokenizer="openai/cl100k_base"),
        "openai/o3-mini-2025-01-31": HelmModelInfo(tokenizer="openai/cl100k_base"),
        "openai/o3-mini-2025-01-31-low-reasoning-effort": HelmModelInfo(
            tokenizer="openai/cl100k_base"
        ),
        "openai/o3-mini-2025-01-31-high-reasoning-effort": HelmModelInfo(
            tokenizer="openai/cl100k_base"
        ),
        "openai/o4-mini-2025-04-16": HelmModelInfo(tokenizer="openai/cl100k_base"),
        "openai/o4-mini-2025-04-16-low-reasoning-effort": HelmModelInfo(
            tokenizer="openai/cl100k_base"
        ),
        "openai/o4-mini-2025-04-16-high-reasoning-effort": HelmModelInfo(
            tokenizer="openai/cl100k_base"
        ),
        "openai/o3-2025-04-03": HelmModelInfo(tokenizer="openai/cl100k_base"),
        "openai/o3-2025-04-03-low-reasoning-effort": HelmModelInfo(
            tokenizer="openai/cl100k_base"
        ),
        "openai/o3-2025-04-03-high-reasoning-effort": HelmModelInfo(
            tokenizer="openai/cl100k_base"
        ),
        "openai/o3-2025-04-16": HelmModelInfo(tokenizer="openai/cl100k_base"),
        "openai/o3-2025-04-16-low-reasoning-effort": HelmModelInfo(
            tokenizer="openai/cl100k_base"
        ),
        "openai/o3-2025-04-16-high-reasoning-effort": HelmModelInfo(
            tokenizer="openai/cl100k_base"
        ),
        "openai/gpt-4o-2024-11-20": HelmModelInfo(tokenizer="openai/o200k_base"),
        "openai/gpt-4-0613": HelmModelInfo(
            tokenizer="openai/cl100k_base", is_legacy=True
        ),
        "openai/gpt-4-32k-0613": HelmModelInfo(
            tokenizer="openai/cl100k_base", is_legacy=True
        ),
        "openai/gpt-4-turbo-2024-04-09": HelmModelInfo(
            tokenizer="openai/cl100k_base", is_legacy=True
        ),
        "openai/gpt-3.5-turbo-0125": HelmModelInfo(
            tokenizer="openai/cl100k_base", is_legacy=True
        ),
        # ------------------------
        # Together Models (LLAMA)
        # ------------------------
        "meta/llama-4-maverick-17b-128e-instruct-fp8": HelmModelInfo(
            tokenizer="meta/llama-4-scout-17b-16e-instruct"
        ),
        "meta/llama-3-8b": HelmModelInfo(tokenizer="meta/llama-3-8b", is_legacy=True),
        "meta/llama-3-70b": HelmModelInfo(tokenizer="meta/llama-3-8b", is_legacy=True),
        "meta/llama-3-70b-chat": HelmModelInfo(
            tokenizer="meta/llama-3-8b", is_legacy=True
        ),
        "meta/llama-3.1-70b-instruct-turbo": HelmModelInfo(
            tokenizer="meta/llama-3.1-8b", is_legacy=True
        ),
        "meta/llama-3.1-405b-instruct-turbo": HelmModelInfo(
            tokenizer="meta/llama-3.1-8b", is_legacy=True
        ),
        # ------------------------
        # Together Models (DeepSeek)
        # ------------------------
        "deepseek-ai/deepseek-v3": HelmModelInfo(tokenizer="deepseek-ai/deepseek-v3"),
        "deepseek-ai/deepseek-r1": HelmModelInfo(tokenizer="deepseek-ai/deepseek-r1"),
        "deepseek-ai/deepseek-r1-hide-reasoning": HelmModelInfo(
            tokenizer="deepseek-ai/deepseek-r1"
        ),
        # ------------------------
        # Mistral Models
        # ------------------------
        "mistralai/mistral-large-2407": HelmModelInfo(
            tokenizer="mistralai/Mistral-Large-Instruct-2407", is_legacy=True
        ),
        "mistralai/mixtral-8x22b": HelmModelInfo(
            tokenizer="mistralai/Mistral-7B-v0.1", is_legacy=True
        ),
        "mistralai/mixtral-8x22b-instruct-v0.1": HelmModelInfo(
            tokenizer="mistralai/Mistral-7B-v0.1", is_legacy=True
        ),
        # ------------------------
        # Qwen Models
        # ------------------------
        "qwen/qwen2-72b-instruct": HelmModelInfo(tokenizer="qwen/qwen2-72b-instruct"),
        "qwen/qwq-32b-preview": HelmModelInfo(tokenizer="qwen/qwq-32b-preview"),
        # ------------------------
        # Anthropic Models (Claude)
        # ------------------------
        "anthropic/claude-3-7-sonnet-20250219": HelmModelInfo(
            tokenizer="anthropic/claude"
        ),
        "anthropic/claude-3-haiku-20240307": HelmModelInfo(
            tokenizer="anthropic/claude", is_legacy=True
        ),
        "anthropic/claude-3-opus-20240229": HelmModelInfo(
            tokenizer="anthropic/claude", is_legacy=True
        ),
        "anthropic/claude-3-5-sonnet-20241022": HelmModelInfo(
            tokenizer="anthropic/claude", is_legacy=True
        ),
        # ------------------------
        # Google Gemini Models
        # ------------------------
        "google/gemini-1.5-pro-001": HelmModelInfo(tokenizer="google/gemma-2b"),
        "google/gemini-2.0-flash-001": HelmModelInfo(tokenizer="google/gemma-2b"),
        "google/gemini-2.0-flash-thinking-exp-01-21": HelmModelInfo(
            tokenizer="google/gemma-2b"
        ),
        "google/gemini-1.0-pro-001": HelmModelInfo(
            tokenizer="google/gemma-2b", is_legacy=True
        ),
        "google/gemini-1.5-pro-preview-0409": HelmModelInfo(
            tokenizer="google/gemma-2b", is_legacy=True
        ),
        # ------------------------
        # Other Models
        # ------------------------
        "01-ai/yi-large": HelmModelInfo(tokenizer="01-ai/Yi-6B", is_legacy=True),
    }


@dataclass
class NonHelmTokenizerMapping:
    mapping: ClassVar[Dict[str, NonHelmModelInfo]] = {
        # ------------------------
        # OpenAI Models
        # ------------------------
        "openai/o1-2024-12-17": NonHelmModelInfo(
            tokenizer="o1-2024-12-17", provider="openai"
        ),
        "openai/o1-2024-12-17-low-reasoning-effort": NonHelmModelInfo(
            tokenizer="o1-2024-12-17-low-reasoning-effort", provider="openai"
        ),
        "openai/o1-2024-12-17-high-reasoning-effort": NonHelmModelInfo(
            tokenizer="o1-2024-12-17-high-reasoning-effort", provider="openai"
        ),
        "openai/o1-mini-2024-09-12": NonHelmModelInfo(
            tokenizer="o1-mini-2024-09-12", provider="openai"
        ),
        "openai/o1-preview-2024-09-12": NonHelmModelInfo(
            tokenizer="o1-preview-2024-09-12", provider="openai"
        ),
        "openai/o3-mini-2025-01-31": NonHelmModelInfo(
            tokenizer="o3-mini-2025-01-31", provider="openai"
        ),
        "openai/o3-mini-2025-01-31-low-reasoning-effort": NonHelmModelInfo(
            tokenizer="o3-mini-2025-01-31-low-reasoning-effort", provider="openai"
        ),
        "openai/o3-mini-2025-01-31-high-reasoning-effort": NonHelmModelInfo(
            tokenizer="o3-mini-2025-01-31-high-reasoning-effort", provider="openai"
        ),
        "openai/o4-mini-2025-04-16": NonHelmModelInfo(
            tokenizer="o4-mini-2025-04-16", provider="openai"
        ),
        "openai/o4-mini-2025-04-16-low-reasoning-effort": NonHelmModelInfo(
            tokenizer="o4-mini-2025-04-16-low-reasoning-effort", provider="openai"
        ),
        "openai/o4-mini-2025-04-16-high-reasoning-effort": NonHelmModelInfo(
            tokenizer="o4-mini-2025-04-16-high-reasoning-effort", provider="openai"
        ),
        "openai/o3-2025-04-03": NonHelmModelInfo(
            tokenizer="o3-2025-04-03", provider="openai"
        ),
        "openai/o3-2025-04-03-low-reasoning-effort": NonHelmModelInfo(
            tokenizer="o3-2025-04-03-low-reasoning-effort", provider="openai"
        ),
        "openai/o3-2025-04-03-high-reasoning-effort": NonHelmModelInfo(
            tokenizer="o3-2025-04-03-high-reasoning-effort", provider="openai"
        ),
        "openai/o3-2025-04-16": NonHelmModelInfo(
            tokenizer="o3-2025-04-16", provider="openai"
        ),
        "openai/o3-2025-04-16-low-reasoning-effort": NonHelmModelInfo(
            tokenizer="o3-2025-04-16-low-reasoning-effort", provider="openai"
        ),
        "openai/o3-2025-04-16-high-reasoning-effort": NonHelmModelInfo(
            tokenizer="o3-2025-04-16-high-reasoning-effort", provider="openai"
        ),
        "openai/gpt-4o-2024-11-20": NonHelmModelInfo(
            tokenizer="gpt-4o-2024-11-20", provider="openai"
        ),
        "openai/gpt-4.5-preview-2025-02-27": NonHelmModelInfo(
            tokenizer="gpt-4.5-preview-2025-02-27", provider="openai"
        ),
        "openai/gpt-4.1-2025-04-14": NonHelmModelInfo(
            tokenizer="gpt-4.1-2025-04-14", provider="openai"
        ),
        # ------------------------
        # Anthropic Models (Claude)
        # ------------------------
        "anthropic/claude-3-7-sonnet-20250219": NonHelmModelInfo(
            tokenizer="claude-3-7-sonnet-20241022", provider="anthropic"
        ),
        "anthropic/claude-3-5-sonnet-20241022": NonHelmModelInfo(
            tokenizer="claude-3-5-sonnet-20250219", provider="anthropic", is_legacy=True
        ),
        "anthropic/claude-3-opus-20240229": NonHelmModelInfo(
            tokenizer="claude-3-opus-20240229", provider="anthropic", is_legacy=True
        ),
        # ------------------------
        # Google Gemini Models
        # ------------------------
        "google/gemini-1.5-pro-001": NonHelmModelInfo(
            tokenizer="gemini-1.5-pro", provider="google"
        ),
        "google/gemini-2.0-flash-001": NonHelmModelInfo(
            tokenizer="gemini-2.0-flash", provider="google"
        ),
        # ------------------------
        # Together Models (LLAMA)
        # ------------------------
        "meta/llama-4-maverick-17b-128e-instruct-fp8": NonHelmModelInfo(
            tokenizer="meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
            provider="together",
        ),
        "meta/llama-3.1-70b-instruct-turbo": NonHelmModelInfo(
            tokenizer="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
            provider="together",
            is_legacy=True,
        ),
        "meta/llama-3.1-405b-instruct-turbo": NonHelmModelInfo(
            tokenizer="meta-llama/Meta-Llama-3-70B-Instruct-Turbo",
            provider="together",
            is_legacy=True,
        ),
        # ------------------------
        # Together Models (DeepSeek)
        # ------------------------
        "deepseek-ai/deepseek-v3": NonHelmModelInfo(
            tokenizer="deepseek-ai/deepseek-v3", provider="together"
        ),
        "deepseek-ai/deepseek-r1": NonHelmModelInfo(
            tokenizer="deepseek-ai/deepseek-r1", provider="together"
        ),
        # ------------------------
        # Mistral Models
        # ------------------------
        "mistralai/mixtral-8x22b-instruct-v0.1": NonHelmModelInfo(
            tokenizer="mistralai/Mixtral-8x22B-Instruct-v0.1",
            provider="together",
            is_legacy=True,
        ),
    }


@dataclass
class ModelRegistry:
    tokenizers: ClassVar[HelmTokenizerMapping] = HelmTokenizerMapping()

    @classmethod
    def get_tokenizer(cls, model_name: str) -> str:
        try:
            return cls.tokenizers.mapping[model_name].tokenizer
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
