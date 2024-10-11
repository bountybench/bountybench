from models.model_provider import ModelProvider
from together import Together
from typing import List
from models.model_response import ModelResponse
from datetime import datetime


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
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop_sequences,
        )
        
        end_time = datetime.now()

    
        response_request_duration = (end_time - start_time).total_seconds() * 1000

    
        return ModelResponse(content=response.choices[0].message.content,
                             input_tokens=response.usage.prompt_tokens, 
                             output_tokens=response.usage.completion_tokens,
                             time_taken_in_ms=response_request_duration)
    


    def tokenize(self, model: str, message: str) -> List[int]:
        raise NotImplementedError("Tokenization is not supported for Together models")

    def decode_tokens(self, model: str, tokens: List[int]) -> str:
        raise NotImplementedError(
            "Decoding tokens is not supported for Together models"
        )
