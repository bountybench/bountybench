import http
from typing import List

from requests.exceptions import ConnectionError, HTTPError, Timeout
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from resources.model_resource.helm_models.helm_models import HelmModels
from resources.model_resource.model_provider import ModelProvider
from resources.model_resource.openai_models.openai_models import OpenAIModels
from utils.logger import get_main_logger

logger = get_main_logger(__name__)


def get_model_provider(use_helm: bool = False) -> ModelProvider:
    """
    Get the appropriate model provider based on the model type.
    Returns:
        ModelProvider: An instance of the appropriate model provider class.
    """
    # TODO: Support Different Model Providers (Also handle Azure case)
    if use_helm:
        model_provider = HelmModels()
    else:
        model_provider = OpenAIModels()
    return model_provider


def get_num_tokens(model_input: str, model: str, use_helm: bool = False) -> int:
    """
    Returns the number of tokens for the given model input.

    Parameters:
    model_input (str): The input string to be tokenized.
    model (str): The model to be used for tokenization.
    use_helm (bool): Flag to indicate whether to use Helm provider. Default is False.

    Returns:
    int: The number of tokens in the model input.
    """
    return get_model_provider(use_helm).get_num_tokens(model, model_input)


@retry(
    stop=stop_after_attempt(30),
    wait=wait_exponential(multiplier=1, max=30),
    retry=retry_if_exception_type(
        (HTTPError, ConnectionError, Timeout, http.client.RemoteDisconnected)
    ),
)
def tokenize_input(model_input: str, model: str, use_helm: bool = False) -> List[int]:
    """
    Tokenizes the model input and returns the list of token IDs.
    Retries up to 30 times in case of certain connection errors.

    Parameters:
    model_input (str): The input string to be tokenized.
    model (str): The model to be used for tokenization.
    use_helm (bool): Flag to indicate whether to use Helm provider. Default is False.

    Returns:
    List[int]: A list of token IDs representing the tokenized input.
    """
    return get_model_provider(use_helm).tokenize(model, model_input)


@retry(
    stop=stop_after_attempt(30),
    wait=wait_exponential(multiplier=1, max=30),
    retry=retry_if_exception_type(
        (HTTPError, ConnectionError, Timeout, http.client.RemoteDisconnected)
    ),
)
def decode_tokenized_inputs(
    tokens: List[int], model: str, use_helm: bool = False
) -> str:
    """
    Decodes the list of token IDs back into a string.
    Retries up to 30 times in case of certain connection errors.

    Parameters:
    tokens (List[int]): A list of token IDs to be decoded.
    model (str): The model to be used for decoding.
    use_helm (bool): Flag to indicate whether to use Helm provider. Default is False.

    Returns:
    str: The decoded string from the token IDs.
    """
    return get_model_provider(use_helm).decode(model, tokens)


def truncate_input_to_max_tokens(
    max_input_tokens: int, model_input: str, model: str, use_helm: bool = False
) -> str:
    num_input_tokens = get_num_tokens(model_input, model, use_helm)
    truncation_alert = "\n...TRUNCATED...\n"
    num_tokens_in_truncation_alert = get_num_tokens(truncation_alert, model, use_helm)

    if num_input_tokens >= max_input_tokens - num_tokens_in_truncation_alert:
        logger.warning(
            f"Number of input tokens ({num_input_tokens}) exceeds max tokens ({max_input_tokens}). Truncating input."
        )
        tokens = tokenize_input(model_input, model, use_helm)
        tokens_to_keep = max_input_tokens - num_tokens_in_truncation_alert
        half_tokens_to_keep = tokens_to_keep // 2
        beginning_tokens = tokens[:half_tokens_to_keep]
        end_tokens = tokens[-half_tokens_to_keep:]
        truncated_tokens = (
            beginning_tokens
            + tokenize_input(truncation_alert, model, use_helm)
            + end_tokens
        )
        truncated_input = decode_tokenized_inputs(truncated_tokens, model, use_helm)
        return truncated_input

    return model_input
