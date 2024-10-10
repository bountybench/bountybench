from typing import List
from openai import OpenAI
import tiktoken
from models.model_provider import ModelProvider


class OpenAIModels(ModelProvider):
    def __init__(self):
        self.client = self.create_client()

    def create_client(self) -> OpenAI:
        return OpenAI(api_key=self._api_key())
    
    def request(
        self,
        deployment_name: str,
        message: str,
        temperature: float,
        max_tokens: int,
        stop_sequences: List[str],
    ) -> str:
        completion = self.client.Completion.create(
            model=deployment_name,
            prompt=message,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop_sequences,
        )
        return completion.choices[0].text

    def tokenize(self, deployment_name: str, message: str) -> List[int]:
        encoding = tiktoken.encoding_for_model(deployment_name)
        return encoding.encode(message)

    def decode_tokens(self, deployment_name: str, tokens: List[int]) -> str:
        encoding = tiktoken.encoding_for_model(deployment_name)
        return encoding.decode(tokens)

    def get_num_tokens(self, deployment_name: str, message: str) -> int:
        encoding = tiktoken.encoding_for_model(deployment_name)
        return len(encoding.encode(message))