from datetime import datetime
from time import time
from typing import List

import tiktoken
from openai import OpenAI

from resources.model_resource.model_provider import ModelProvider
from resources.model_resource.model_response import ModelResponse
from utils.logger import get_main_logger

logger = get_main_logger(__name__)


class OpenAIModels(ModelProvider):
    def __init__(self):
        self.client = self.create_client()

    def create_client(self) -> OpenAI:
        return OpenAI(api_key=self._api_key())

    def request(
        self,
        model: str,
        message: str,
        temperature: float,
        max_tokens: int,
        # Unused by new responses api
        stop_sequences: List[str],
    ) -> ModelResponse:

        start_time = datetime.now()
        status_code = None

        try:
            # Extract base model name
            model_name = model.split("/")[1]
            reasoning_effort = None

            # Check for reasoning effort suffixes in o1, o3 models
            if model_name.startswith(("o1", "o3")):
                if model_name.endswith("-high-reasoning-effort"):
                    reasoning_effort = "high"
                    model_name = model_name[: -len("-high-reasoning-effort")]
                elif model_name.endswith("-low-reasoning-effort"):
                    reasoning_effort = "low"
                    model_name = model_name[: -len("-low-reasoning-effort")]

            # Prepare common parameters for all models
            params = {
                "model": model_name,
                "input": message,
                "max_output_tokens": max_tokens,
            }

            # Add temperature for non-o models (like gpt-4, etc.)
            if not model_name.startswith(("o1", "o3")):
                params["temperature"] = temperature

            # Add reasoning_effort parameter for o1, o3 models if specified
            if reasoning_effort and model_name.startswith(("o1", "o3")):
                params["reasoning"] = {"effort": reasoning_effort}

            response = self.client.responses.create(**params)

            # For successful responses, we don't typically get HTTP status code
            # from OpenAI client, but could try to extract if available
            if hasattr(response, "response") and hasattr(
                response.response, "status_code"
            ):
                status_code = response.response.status_code

            output_tokens = response.usage.output_tokens
            if model_name.startswith(("o1", "o3")):
                reasoning_tokens = response.usage.output_tokens_details.reasoning_tokens
                logger.info(f"reasoning tokens: {reasoning_tokens}")
                output_tokens += reasoning_tokens

            logger.info(
                f"max output tokens: {max_tokens} - total output tokens: {output_tokens}"
            )
            return ModelResponse(
                content=response.output_text,
                input_tokens=response.usage.input_tokens,
                output_tokens=output_tokens,
                time_taken_in_ms=float(time()) - response.created_at,
            )
        except Exception as e:
            # Extract status code from OpenAI errors
            try:
                # OpenAI client exceptions often have status_code attribute
                # or the error might be contained in e.response.status_code
                if hasattr(e, "status_code"):
                    status_code = e.status_code
                elif hasattr(e, "response") and hasattr(e.response, "status_code"):
                    status_code = e.response.status_code
                # If error is in the message as "Error code: XXX"
                elif "Error code:" in str(e):
                    error_parts = str(e).split("Error code:")
                    if len(error_parts) > 1:
                        code_part = error_parts[1].strip().split(" ")[0]
                        if code_part.isdigit():
                            status_code = int(code_part)
            except:
                pass  # If we can't extract the code, just continue

            # Attach status code to the exception
            if status_code is not None:
                e.status_code = status_code
            raise

    def tokenize(self, model: str, message: str) -> List[int]:
        encoding = tiktoken.encoding_for_model("gpt-4o")
        return encoding.encode(message)

    def decode(self, model: str, tokens: List[int]) -> str:
        encoding = tiktoken.encoding_for_model("gpt-4o")
        return encoding.decode(tokens)

    def get_num_tokens(self, model: str, message: str) -> int:
        encoding = tiktoken.encoding_for_model("gpt-4o")
        return len(encoding.encode(message))
