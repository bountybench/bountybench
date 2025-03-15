from datetime import datetime
from typing import List

from together import Together

from resources.model_resource.model_provider import ModelProvider
from resources.model_resource.model_response import ModelResponse


class TogetherModels(ModelProvider):
    def __init__(self):
        self.client = self.create_client()

    def create_client(self) -> Together:
        return Together(api_key=self._api_key())

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
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop_sequences,
            )

            # For successful responses, check if we can extract status code
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
            # Extract status code from Together API errors
            try:
                # Together client exceptions might have status_code attribute
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

    def tokenize(self, model: str, message: str) -> List[int]:
        raise NotImplementedError("Tokenization is not supported for Together models")

    def decode(self, model: str, tokens: List[int]) -> str:
        raise NotImplementedError(
            "Decoding tokens is not supported for Together models"
        )

    def get_num_tokens(self, model: str, message: str) -> int:
        raise NotImplementedError(
            "Getting number of tokens is not supported for Together models"
        )
