from models.model_provider import ModelProvider
from anthropic import Anthropic
from typing import List



class AnthropicModels(ModelProvider):
    def __init__(self):
        self.client = self.create_client()

    def create_client(self) -> Anthropic:
        return Anthropic(api_key=self._api_key())

    def request(
        self,
        deployment_name: str,
        message: str,
        temperature: float,
        max_tokens: int,
        stop_sequences: List[str],
    ) -> str:
        
        return self.client.messages.create(
            model=deployment_name,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": message}],
            stop_sequences=stop_sequences,
        )
    
    def tokenize(self, deployment_name: str, message: str) -> List[int]:
        raise NotImplementedError("Tokenization is not supported for Anthropic models")

    def decode_tokens(self, deployment_name: str, tokens: List[int]) -> str:
        raise NotImplementedError("Decoding tokens is not supported for Anthropic models")

    def get_num_tokens(self, deployment_name: str, message: str) -> int:
        client = self.create_client()
        token_count = client.count_tokens(message)
        return token_count