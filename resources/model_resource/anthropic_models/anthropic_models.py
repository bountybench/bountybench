from datetime import datetime
from typing import List

import tiktoken
from anthropic import Anthropic

from resources.model_resource.model_provider import ModelProvider
from resources.model_resource.model_response import ModelResponse

EXTENDED_THINKING_SUFFIX = "-extended-thinking"
DEFAULT_THINKING_BUDGET = 1024  # Minimum budget for extended thinking in tokens


class AnthropicModels(ModelProvider):
    def __init__(self):
        self.client = self.create_client()

    def create_client(self) -> Anthropic:
        return Anthropic(api_key=self._api_key())

    def request(
        self,
        model: str,
        message: str,
        temperature: float,
        max_tokens: int,
        stop_sequences: List[str],
    ) -> ModelResponse:
        start_time = datetime.now()
        status_code = None

        try:
            clean_model_name = self.clean_model_name(model)
            is_thinking: bool = clean_model_name.endswith(EXTENDED_THINKING_SUFFIX)
            if not is_thinking:
                response = self.client.messages.create(
                    model=clean_model_name,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{"role": "user", "content": message}],
                    stop_sequences=stop_sequences,
                )
                full_response = response.content[0].text
            else:
                # https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/extended-thinking-tips#technical-considerations-for-extended-thinking
                # - Thinking tokens have a minimum budget of 1024 tokens.
                # - We recommend that you start with the minimum thinking budget and incrementally increase to adjust based on your needs and task complexity.
                clean_model_name = clean_model_name[: -len(EXTENDED_THINKING_SUFFIX)]
                response = self.client.messages.create(
                    model=clean_model_name,
                    max_tokens=max_tokens,
                    temperature=1,  # `temperature` may only be set to 1 when thinking is enabled
                    messages=[{"role": "user", "content": message}],
                    stop_sequences=stop_sequences,
                    thinking={
                        "type": "enabled",
                        "budget_tokens": max(int(max_tokens * 0.1), 1024),
                    },
                )

                thinking_block = response.content[0].thinking
                text_block = response.content[1].text
                full_response = (
                    "<think>\n" + thinking_block + "\n</think>\n\n" + text_block
                )

            # For successful responses, we don't typically get HTTP status code
            # from Anthropic client, but could try to extract if available
            if hasattr(response, "response") and hasattr(
                response.response, "status_code"
            ):
                status_code = response.response.status_code

            end_time = datetime.now()
            response_request_duration = (end_time - start_time).total_seconds() * 1000
            return ModelResponse(
                content=full_response,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                time_taken_in_ms=response_request_duration,
                status_code=status_code,
            )
        except Exception as e:
            # Extract status code from Anthropic errors
            try:
                # Anthropic client exceptions might have status_code attribute
                # or the error might be contained in e.response.status_code
                if hasattr(e, "status_code"):
                    status_code = e.status_code
                elif hasattr(e, "response") and hasattr(e.response, "status_code"):
                    status_code = e.response.status_code
            except:
                pass  # If we can't extract the code, just continue

            # Attach status code to the exception
            if status_code is not None:
                e.status_code = status_code
            raise

    def clean_model_name(self, model_name: str) -> str:
        prefix = "anthropic/"
        if model_name.startswith(prefix):
            return model_name[len(prefix) :]
        return model_name

    def tokenize(self, model: str, message: str) -> List[int]:
        # Note: Anthropic doesn't have a public tokenizer, here we use the tiktoken encoding to get a rough estimate
        encoding = tiktoken.encoding_for_model("gpt-4o")
        return encoding.encode(message)

    def decode(self, model: str, tokens: List[int]) -> str:
        # Note: Anthropic doesn't have a public tokenizer, here we use the tiktoken encoding to get a rough estimate
        encoding = tiktoken.encoding_for_model("gpt-4o")
        return encoding.decode(tokens)

    def get_num_tokens(self, model: str, message: str) -> int:
        encoding = tiktoken.encoding_for_model("gpt-4o")
        return len(encoding.encode(message))
