from typing import List
from models.model_provider import ModelProvider

from helm.common.authentication import Authentication
from helm.common.request import Request, RequestResult
from helm.common.tokenization_request import (
    DecodeRequest,
    TokenizationRequest,
    TokenizationRequestResult,
)
from helm.proxy.services.remote_service import RemoteService


class HelmModels(ModelProvider):
    def __init__(self):
        self.authentication = Authentication(
            api_key=self._get_env_var("HELM_API_KEY"))
        self.client = self.create_client()

    def create_client(self) -> RemoteService:
        remote_service = RemoteService(
            "https://crfm-models.stanford.edu")
        return remote_service

    def request(
        self,
        deployment_name: str,
        message: str,
        temperature: float,
        max_tokens: int,
        stop_sequences: List[str]
    ):
        if "o1" in deployment_name:  # o1 and o1-mini don't have stop argument
            request = Request(
                model=deployment_name,
                prompt=message,
                # o1 and o1-mini have fixed temperature=1 (see https://platform.openai.com/docs/guides/reasoning)
                temperature=1,
                echo_prompt=False,
                max_tokens=max_tokens,
            )
        else:
            request = Request(
                model=deployment_name,
                prompt=message,
                temperature=temperature,
                echo_prompt=False,
                max_tokens=max_tokens,
                stop_sequences=stop_sequences,
            )
        request_result: RequestResult = self.client.make_request(
            auth=self.authentication, request=request
        )
        return request_result.completions[0].text

    def tokenize(self, deployment_name: str, message: str) -> List[int]:
        tokenizer = ""  # TODO: Use ModelRegistry to get tokenizer name
        request = TokenizationRequest(
            tokenizer=tokenizer, text=message, encode=True)
        tokenization_result = self.client.tokenize(
            auth=self.authentication, request=request)
        return [int(token) for token in tokenization_result.raw_tokens]

    def decode_tokens(self, deployment_name: str, tokens: List[int]) -> str:
        tokenizer = ""  # TODO: Use ModelRegistry to get tokenizer name
        request = DecodeRequest(tokens=tokens, tokenizer=tokenizer)
        decoding_result = self.client.decode(
            auth=self.authentication, request=request)
        return decoding_result.text

    def get_num_tokens(self, deployment_name: str, message: str) -> int:
        tokenizer = ""  # TODO: Use ModelRegistry to get tokenizer name
        request = TokenizationRequest(
            test=message, tokenizer=tokenizer)
        tokenization_result: TokenizationRequestResult = self.client.tokenize(
            auth=self.authentication, request=request)
        return len(tokenization_result.tokens)
