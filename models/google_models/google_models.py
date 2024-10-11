from models.model_provider import ModelProvider
import google.generativeai as gemini
from typing import List



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
    ) -> str:
        if self.client is None or self.client.model_name != model:
            self.client = self.create_client(model)
        response = self.client.generate_content(
            contents=message,
            generation_config=gemini.types.GenerationConfig(
                temperature=temperature,
                stop_sequences=stop_sequences,
                max_output_tokens=max_tokens,
            )
        )
        return response.text,

    def tokenize(self, model: str, message: str) -> List[int]:
        raise NotImplementedError("Tokenization is not supported for Gemini models")

    def decode_tokens(self, model: str, tokens: List[int]) -> str:
        raise NotImplementedError("Decoding tokens is not supported for Gemini models")

    def get_num_tokens(self, model: str, message: str) -> int:
        if self.client is None or self.client.model_name != model:
            self.client = self.create_client(model)
        return self.client.count_tokens(input).total_tokens