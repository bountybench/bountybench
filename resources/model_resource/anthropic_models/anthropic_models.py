from typing import List
from datetime import datetime

import tiktoken
from anthropic import Anthropic

from resources.model_resource.model_provider import ModelProvider
from resources.model_resource.model_response import ModelResponse


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
        clean_model_name = self.clean_model_name(model)
        response = self.client.messages.create(
            model=clean_model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": message}],
            stop_sequences=stop_sequences,
        )
        end_time = datetime.now()
        response_request_duration = (
            end_time - start_time).total_seconds() * 1000
        return ModelResponse(
            content=response.content[0].text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            time_taken_in_ms=response_request_duration
        )
    
    def clean_model_name(self, model_name: str) -> str:
        prefix = "anthropic/"
        if model_name.startswith(prefix):
            return model_name[len(prefix):]
        return model_name

    def tokenize(self, model: str, message: str) -> List[int]:
        #Note: Anthropic doesn't have a public tokenizer, here we use the tiktoken encoding to get a rough estimate
        encoding = tiktoken.encoding_for_model("gpt-4o")
        return encoding.encode(message)

    def decode(self, model: str, tokens: List[int]) -> str:
        #Note: Anthropic doesn't have a public tokenizer, here we use the tiktoken encoding to get a rough estimate
        encoding = tiktoken.encoding_for_model("gpt-4o")
        return encoding.decode(tokens)
    
    def get_num_tokens(self, model: str, message: str) -> int:
        encoding = tiktoken.encoding_for_model("gpt-4o")
        return len(encoding.encode(message))