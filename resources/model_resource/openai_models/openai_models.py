from datetime import datetime
from typing import List

import tiktoken
from openai import OpenAI

from resources.model_resource.model_provider import ModelProvider
from resources.model_resource.model_response import ModelResponse


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
        stop_sequences: List[str],
    ) -> ModelResponse:

        start_time = datetime.now()
        status_code = None

        try:
            model_name = model.split("/")[1]

            # Prepare common parameters for all models
            params = {
                "model": model_name,
                "messages": [{"role": "user", "content": message}],
                "max_completion_tokens": max_tokens,
                "stop": stop_sequences,
            }

            # Add temperature for non-o models (like gpt-4, etc.)
            if model_name[0] != "o":
                params["temperature"] = temperature

            response = self.client.chat.completions.create(**params)

            # For successful responses, we don't typically get HTTP status code
            # from OpenAI client, but could try to extract if available
            if hasattr(response, "response") and hasattr(
                response.response, "status_code"
            ):
                status_code = response.response.status_code

            end_time = datetime.now()
            response_request_duration = (end_time - start_time).total_seconds() * 1000

            return ModelResponse(
                content=response.choices[0].message.content,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                time_taken_in_ms=response_request_duration,
                status_code=status_code,
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
