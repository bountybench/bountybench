from datetime import datetime
from typing import List

from helm.common.authentication import Authentication
from helm.common.request import Request, RequestResult
from helm.common.tokenization_request import (
    DecodeRequest,
    TokenizationRequest,
    TokenizationRequestResult,
)
from helm.proxy.services.remote_service import RemoteService

from messages.action_messages.action_message import ActionMessage
from resources.model_resource.model_mapping import ModelRegistry
from resources.model_resource.model_provider import ModelProvider
from resources.model_resource.model_response import ModelResponse


class HelmModels(ModelProvider):
    def __init__(self):
        self.authentication = Authentication(api_key=self._api_key())
        self.client = self.create_client()

    def create_client(self) -> RemoteService:
        remote_service = RemoteService("https://crfm-models.stanford.edu")
        return remote_service

    def request(
        self,
        model: str,
        message: str,
        temperature: float,
        max_tokens: int,
        stop_sequences: List[str],
    ) -> ModelResponse:
        mapped_model = ModelRegistry.get_model(model)

        if "o1" in model:  # o1 and o1-mini don't have stop argument
            request = Request(
                model=mapped_model,
                prompt=message,
                # o1 and o1-mini have fixed temperature=1 (see https://platform.openai.com/docs/guides/reasoning)
                temperature=1,
                echo_prompt=False,
                max_tokens=max_tokens,
            )
        elif model == "deepseek-ai/deepseek-r1":
            request = Request(
                model_deployment="together/deepseek-r1",
                model=model,
                prompt=message,
                temperature=temperature,
                echo_prompt=False,
                max_tokens=max_tokens,
                stop_sequences=stop_sequences,
            )
        else:
            request = Request(
                model=mapped_model,
                prompt=message,
                temperature=temperature,
                echo_prompt=False,
                max_tokens=max_tokens,
                stop_sequences=stop_sequences,
            )

        start_time = datetime.now()
        status_code = None

        try:
            request_result: RequestResult = self.client.make_request(
                auth=self.authentication, request=request
            )

            # For successful responses, try to extract status code if available
            if hasattr(request_result, "response") and hasattr(
                request_result.response, "status_code"
            ):
                status_code = request_result.response.status_code

            end_time = datetime.now()
            response_request_duration = (end_time - start_time).total_seconds() * 1000

            return ModelResponse(
                content=request_result.completions[0].text,
                input_tokens=len(self.tokenize(model, message)),
                output_tokens=len(
                    self.tokenize(model, request_result.completions[0].text)
                ),
                time_taken_in_ms=response_request_duration,
                status_code=status_code,
            )
        except Exception as e:
            # Extract status code from Helm API errors
            try:
                # Helm exceptions might have status_code or http_status
                if hasattr(e, "status_code"):
                    status_code = e.status_code
                elif hasattr(e, "http_status"):
                    status_code = e.http_status
                elif hasattr(e, "response") and hasattr(e.response, "status_code"):
                    status_code = e.response.status_code
            except:
                pass  # If we can't extract the code, just continue

            # Attach status code to the exception
            if status_code is not None:
                e.status_code = status_code
            raise

    def tokenize(self, model: str, message: str) -> List[int]:
        tokenizer = ModelRegistry.get_tokenizer(model)
        request = TokenizationRequest(tokenizer=tokenizer, text=message, encode=True)
        tokenization_result = self.client.tokenize(
            auth=self.authentication, request=request
        )
        return [int(token) for token in tokenization_result.raw_tokens]

    def decode(self, model: str, tokens: List[int]) -> str:
        tokenizer = ModelRegistry.get_tokenizer(model)
        request = DecodeRequest(tokens=tokens, tokenizer=tokenizer)
        decoding_result = self.client.decode(auth=self.authentication, request=request)
        return decoding_result.text

    def get_num_tokens(self, model: str, message: str) -> int:
        tokenizer_name = ModelRegistry.get_tokenizer(model)
        request = TokenizationRequest(tokenizer=tokenizer_name, text=message)
        tokenization_result: TokenizationRequestResult = self.client.tokenize(
            auth=self.authentication, request=request
        )
        return len(tokenization_result.tokens)
