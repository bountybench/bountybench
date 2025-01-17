from typing import List

from anthropic import Anthropic

from resources.model_resource.model_provider import ModelProvider


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
    ) -> str:

        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": message}],
            stop_sequences=stop_sequences,
        )
        return response.content[0].text

    def tokenize(self, model: str, message: str) -> List[int]:
        raise NotImplementedError(
            "Tokenization is not supported for Anthropic models")

    def decode(self, model: str, tokens: List[int]) -> str:
        raise NotImplementedError(
            "Decoding tokens is not supported for Anthropic models")
    
    def get_num_tokens(self, model: str, message: str) -> int:
        token_count = self.client.count_tokens(
            message
        )  # Note: This isn't accurate for newer Anthropic models (i.e. Claude 3 or later) and can only be obtained in model response usage property.
        return token_count