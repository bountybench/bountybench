from models.model_provider import ModelProvider
from together import Together
from typing import List


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
    ) -> str:
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop_sequences,
        )
        return response.choices[0].message.content


    def tokenize(self, model: str, message: str) -> List[int]:
        raise NotImplementedError("Tokenization is not supported for Together models")

    def decode_tokens(self, model: str, tokens: List[int]) -> str:
        raise NotImplementedError(
            "Decoding tokens is not supported for Together models"
        )
    def get_num_tokens(self, model: str, message: str) -> int:
        raise NotImplementedError(
            "Getting number of tokens is not supported for Together models"
        )