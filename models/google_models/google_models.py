from models.model_provider import ModelProvider
import google.generativeai as gemini
from typing import List
from models.model_response import ModelResponse
from datetime import datetime



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
        response = self.client.generate_content(
            contents=message,
            generation_config=gemini.types.GenerationConfig(
                temperature=temperature,
                stop_sequences=stop_sequences,
                max_output_tokens=max_tokens,
            )
        )
        end_time = datetime.now()
        response_request_duration = (end_time - start_time).total_seconds() * 1000

    
        return ModelResponse(content=response.text,
                             input_tokens=self.client.count_tokens(message).total_tokens, 
                             output_tokens=response.usage_metadata.candidates_token_count,
                             time_taken_in_ms=response_request_duration)
    

    def tokenize(self, model: str, message: str) -> List[int]:
        raise NotImplementedError("Tokenization is not supported for Gemini models")

    def decode_tokens(self, model: str, tokens: List[int]) -> str:
        raise NotImplementedError("Decoding tokens is not supported for Gemini models")

