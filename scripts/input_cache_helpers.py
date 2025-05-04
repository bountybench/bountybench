import os
from pathlib import Path

import anthropic
import tiktoken
from dotenv import find_dotenv, load_dotenv
from google import genai

ANTHROPIC_COUNT_TOKENS_CACHE = {}
GOOGLE_COUNT_TOKENS_CACHE = {}

env_path = Path(find_dotenv())
if env_path.is_file():
    load_dotenv(dotenv_path=env_path)
else:
    raise FileNotFoundError("Could not find .env file in project directory.")


def get_openai_cached_input_length(repeated_model_input):
    """
    https://openai.com/index/api-prompt-caching/
    API calls to supported models will automatically benefit from Prompt Caching on prompts longer than 1,024 tokens.
    The API caches the longest prefix of a prompt that has been previously computed,
    starting at 1,024 tokens and increasing in 128-token increments.
    If you reuse prompts with common prefixes, we will automatically apply the Prompt Caching discount
    without requiring you to make any changes to your API integration.

    Returns:
        cached_length (int): The length of the cached part of the input.
        non_cached_length (int): The length of the non-cached part of the input.
    """
    repeated_model_input = tiktoken.encoding_for_model("gpt-4o").encode(
        repeated_model_input
    )
    if len(repeated_model_input) < 1024:
        return 0, len(repeated_model_input)
    cached_length = 1024 + ((len(repeated_model_input) - 1024) // 128) * 128
    non_cached_length = len(repeated_model_input) - cached_length
    return cached_length, non_cached_length


def get_anthropic_cached_input_length(repeated_model_input):
    """
    https://www.anthropic.com/news/prompt-caching
    """

    global ANTHROPIC_COUNT_TOKENS_CACHE
    if repeated_model_input in ANTHROPIC_COUNT_TOKENS_CACHE:
        return ANTHROPIC_COUNT_TOKENS_CACHE[repeated_model_input]
    else:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.count_tokens(
            model="claude-3-7-sonnet-20250219",
            system="",
            messages=[{"role": "user", "content": repeated_model_input}],
        )
        ANTHROPIC_COUNT_TOKENS_CACHE[repeated_model_input] = (response.input_tokens, 0)
        return ANTHROPIC_COUNT_TOKENS_CACHE[repeated_model_input]


def get_google_cached_input_length(repeated_model_input):
    """
    https://ai.google.dev/gemini-api/docs/caching?lang=python
    """
    global GOOGLE_COUNT_TOKENS_CACHE

    if repeated_model_input in GOOGLE_COUNT_TOKENS_CACHE:
        return GOOGLE_COUNT_TOKENS_CACHE[repeated_model_input]
    else:
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        response = client.models.count_tokens(
            model="gemini-2.5-pro-preview-03-25", contents=repeated_model_input
        )
        repeated_model_input_length = response.total_tokens

        if repeated_model_input_length < 4096:
            GOOGLE_COUNT_TOKENS_CACHE[repeated_model_input] = (
                0,
                repeated_model_input_length,
            )
        else:
            GOOGLE_COUNT_TOKENS_CACHE[repeated_model_input] = (
                repeated_model_input_length,
                0,
            )

        return GOOGLE_COUNT_TOKENS_CACHE[repeated_model_input]


def get_deepseek_cached_input_length(repeated_model_input):
    """
    Together.ai does not have a caching mechanism for input tokens.
    """
    return 0, len(
        tiktoken.encoding_for_model("deepseek-r1").encode(repeated_model_input)
    )


INPUT_CACHE_HELPERS = {
    "openai": get_openai_cached_input_length,
    "anthropic": get_anthropic_cached_input_length,
    "google": get_google_cached_input_length,
    "deepseek-ai": get_deepseek_cached_input_length,
}
