from datetime import datetime
from typing import List

import google.generativeai as gemini

from resources.model_resource.model_provider import ModelProvider
from resources.model_resource.model_response import ModelResponse


class GoogleModels(ModelProvider):
    def __init__(self):
        self.client = None  # We'll initialize this later with the specific model

    def create_client(self, model: str) -> gemini.GenerativeModel:
        gemini.configure(api_key=self._api_key())
        return gemini.GenerativeModel(model)

    def request(
        self,
        model: str,
        message: str,
        temperature: float,
        max_tokens: int,
        stop_sequences: List[str],
    ) -> ModelResponse:
        if self.client is None or self.client.model_name != model:
            self.client = self.create_client(model)

        start_time = datetime.now()
        status_code = None

        try:
            response = self.client.generate_content(
                contents=message,
                generation_config=gemini.types.GenerationConfig(
                    temperature=temperature,
                    stop_sequences=stop_sequences,
                    max_output_tokens=max_tokens,
                ),
            )

            # For successful responses, check if we can extract status code
            if hasattr(response, "response") and hasattr(
                response.response, "status_code"
            ):
                status_code = response.response.status_code

            end_time = datetime.now()
            response_request_duration = (end_time - start_time).total_seconds() * 1000

            return ModelResponse(
                content=response.text,
                input_tokens=self.client.count_tokens(message).total_tokens,
                output_tokens=response.usage_metadata.candidates_token_count,
                time_taken_in_ms=response_request_duration,
                status_code=status_code,
            )
        except Exception as e:
            # Extract status code from Google API errors
            try:
                # Google API exceptions might have status_code attribute
                if hasattr(e, "status_code"):
                    status_code = e.status_code
                elif hasattr(e, "response") and hasattr(e.response, "status_code"):
                    status_code = e.response.status_code
                # Sometimes errors are included in error.details
                elif hasattr(e, "details") and isinstance(e.details, list):
                    for detail in e.details:
                        if hasattr(detail, "status") and detail.status.isdigit():
                            status_code = int(detail.status)
                            break
            except:
                pass  # If we can't extract the code, just continue

            # Attach status code to the exception
            if status_code is not None:
                e.status_code = status_code
            raise

    def tokenize(self, model: str, message: str) -> List[int]:
        raise NotImplementedError("Tokenization is not supported for Gemini models")

    def decode(self, model: str, tokens: List[int]) -> str:
        raise NotImplementedError("Decoding tokens is not supported for Gemini models")

    def get_num_tokens(self, model: str, message: str) -> int:
        if self.client is None or self.client.model_name != model:
            self.client = self.create_client(model)
        return self.client.count_tokens(input).total_tokens
