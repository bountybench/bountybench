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
