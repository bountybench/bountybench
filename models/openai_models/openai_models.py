from typing import List
from openai import OpenAI
import tiktoken
from models.model_provider import ModelProvider
from models.model_response import ModelResponse
from datetime import datetime




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
        response = self.client.Completion.create(
            model=model,
            prompt=message,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop_sequences,
        )   
        
        end_time = datetime.now()
        response_request_duration = (end_time - start_time).total_seconds() * 1000
    
        return ModelResponse(content=response.choices[0].text, 
                             input_tokens=response.usage.prompt_tokens, 
                             output_tokens=response.usage.completion_tokens,
                             time_taken_in_ms=response_request_duration)
    

    def tokenize(self, model: str, message: str) -> List[int]:
        encoding = tiktoken.encoding_for_model(model)
        return encoding.encode(message)

    def decode_tokens(self, model: str, tokens: List[int]) -> str:
        encoding = tiktoken.encoding_for_model(model)
        return encoding.decode(tokens)

