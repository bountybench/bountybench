from datetime import datetime
from typing import List

import tiktoken
from openai import OpenAI

from models.model_provider import ModelProvider
from models.model_response import ModelResponse


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

        model_name = model.split("/")[1]
        if model_name[0] == 'o':
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": message},
                ],
                max_completion_tokens=max_tokens,
                stop=stop_sequences,
            )
        else:
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": message},
                ],
                temperature=temperature,
                max_completion_tokens=max_tokens,
                stop=stop_sequences,
            )

        end_time = datetime.now()
        response_request_duration = (
            end_time - start_time).total_seconds() * 1000

        return ModelResponse(content=response.choices[0].message.content,
                             input_tokens=response.usage.prompt_tokens,
                             output_tokens=response.usage.completion_tokens,
                             time_taken_in_ms=response_request_duration)

    def tokenize(self, model: str, message: str) -> List[int]:
        encoding = tiktoken.encoding_for_model(model)
        return encoding.encode(message)

    def decode(self, model: str, tokens: List[int]) -> str:
        encoding = tiktoken.encoding_for_model(model)
        return encoding.decode(tokens)
    
    def get_num_tokens(self, model: str, message: str) -> int:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(message))
