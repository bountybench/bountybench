from typing import List

import tiktoken

from models.helm_models.helm_models import HelmModels
from models.model_provider import ModelProvider
from models.openai_models.openai_models import OpenAIModels


def get_model_provider(model: str, helm: bool = False) -> ModelProvider:
    # TODO: Support Different Model Providers (Also handle Azure case)
    if helm:
        model_provider = HelmModels()
    else:
        model_provider = OpenAIModels()
    return model_provider


def get_num_tokens(model: str, message: str) -> int:
    """
    Get the number of tokens for the request.
    Defaults to GPT-4 via tiktoken if there isn't a native implementation
    """
    model_provider: ModelProvider
    model_provider = get_model_provider(model)
    try:
        return model_provider.get_num_tokens(
            model=model, message=message
        )
    except (NotImplementedError, KeyError):
        # Fallback to tiktoken
        encoding = tiktoken.encoding_for_model("gpt-4")
        return len(encoding.encode(message))


def tokenize(model: str, message: str) -> List[int]:
    """
    Get the number of tokens for the request.
    Defaults to GPT-4 via tiktoken if there isn't a native implementation
    """
    model_provider: ModelProvider
    model_provider = get_model_provider(model)
    try:
        return model_provider.tokenize(
            model=model, message=message
        )
    except (NotImplementedError, KeyError):
        encoding = tiktoken.encoding_for_model("gpt-4")
        return encoding.encode(message)


def decode(model: str, tokens: List[int]) -> str:
    """
    Get the number of tokens for the request.
    Defaults to GPT-4 via tiktoken if there isn't a native implementation
    """
    model_provider: ModelProvider
    model_provider = get_model_provider(model)
    try:
        return model_provider.decode(
            model=model, tokens=tokens
        )
    except (NotImplementedError, KeyError):
        encoding = tiktoken.encoding_for_model("gpt-4")
        return encoding.decode(tokens)


def query(
    model: str,
    message: str,
    temperature: float,
    max_tokens: int,
    stop_sequences: List[str],
    helm: bool,
) -> str:
    model_provider: ModelProvider
    model_provider = get_model_provider(model=model, helm=helm)
    return model_provider.request(
        model=model,
        message=message,
        temperature=temperature,
        max_tokens=max_tokens,
        stop_sequences=stop_sequences,
    )
